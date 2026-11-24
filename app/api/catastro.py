"""Catastro de Paraguay en el mapa del visor NISAR.

El shapefile del SNC (1.062.544 parcelas, EPSG:32721) no se puede servir crudo:
pesa 167 MB más 1,7 GB de DBF y ningún navegador dibuja un millón de polígonos.
Se convierte **una vez** a un índice SQLite con R-tree (geometría en EPSG:4326 y
área en m²) en la raíz de cachés, y después cada vista se resuelve por la caja
visible con simplificación por zoom.

El cuadro ROI del visor se cruza con las parcelas (`POST /afectadas`): devuelve
cada inmueble con su superficie afectada y la fracción del predio, que es lo que
permite pasar de "acá hubo pérdida de bosque" a "este padrón / esta finca".

Sin dataset configurado el módulo no inventa nada: el estado explica dónde se
esperaba el ``.shp`` y la capa queda apagada.

    CLIMATE3D_CATASTRO=<carpeta o .shp>   (o `comun/rutas.py --catastro ...`)
"""
from __future__ import annotations

import sqlite3
import struct
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import shapely
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from pyproj import Transformer
from shapely import wkb
from shapely.geometry import Polygon, box, shape
from shapely.ops import unary_union

from comun.rutas import raiz_catastro, raiz_media

#: Versión del esquema del índice: cambiarla obliga a reconstruirlo.
ESQUEMA = 3

#: CRS del shapefile del SNC (UTM 21S).
EPSG_CATASTRO = 32721

#: Zoom mínimo de la capa. A z5 una parcela de ~8.000 ha ya se distingue.
ZOOM_MIN = 5

#: Parcelas por respuesta: con más, el GeoJSON tapa el mapa y el navegador sufre.
LIMITE_DIBUJO = 1200
LIMITE_AFECTADAS = 500

#: Tolerancia de simplificación en grados por zoom (~3 m a 14, ~0,5 m a 17).
SIMPLIFICACION = {
    5: 1e-3,
    6: 8e-4,
    7: 6e-4,
    8: 4e-4,
    9: 2.5e-4,
    10: 1.6e-4,
    11: 1e-4,
    12: 6e-5,
    13: 4e-5,
    14: 3e-5,
    15: 1.5e-5,
    16: 8e-6,
    17: 4e-6,
}

#: Constante de escala: a la latitud de Paraguay, un píxel mide ~143 km / 2^z.
_METROS_POR_ZOOM = 143_000.0
#: Lado mínimo en píxeles para que la parcela se distinga del resto.
_PIXELES_MINIMOS = 2.0

#: Ventana plausible de UTM 21S para Paraguay. Fuera de esto la geometría es basura.
_UTM_X = (-300_000.0, 1_100_000.0)
_UTM_Y = (6_200_000.0, 8_100_000.0)

#: Letra de departamento del SNC -> nombre. Derivada de la distribución espacial
#: del propio dataset y contrastada con la cantidad de distritos de cada uno: no
#: viene de un campo del DBF. La letra O no aparece.
DEPARTAMENTOS = {
    "A": "Asunción",
    "B": "Concepción",
    "C": "San Pedro",
    "D": "Cordillera",
    "E": "Guairá",
    "F": "Caaguazú",
    "G": "Caazapá",
    "H": "Itapúa",
    "I": "Misiones",
    "J": "Paraguarí",
    "K": "Alto Paraná",
    "L": "Central",
    "M": "Ñeembucú",
    "N": "Amambay",
    "P": "Presidente Hayes",
    "Q": "Boquerón",
    "R": "Alto Paraguay",
    "S": "Canindeyú",
}

FUENTE = "SNC · Servicio Nacional de Catastro (Paraguay)"
ATRIBUCION = (
    "Catastro: Servicio Nacional de Catastro (SNC, Paraguay) · export shapefile "
    "enero 2026 · polígonos y datos registrales"
)

_A_4326 = Transformer.from_crs(EPSG_CATASTRO, 4326, always_xy=True)
_A_UTM = Transformer.from_crs(4326, EPSG_CATASTRO, always_xy=True)

_CAMPOS = (
    "ccatastral",
    "dpto",
    "dist",
    "padron",
    "zona",
    "mz",
    "lote",
    "finca",
    "matricula",
    "colonia",
    "reg_prof",
    "nombre_obj",
    "tipo",
    "zona_urban",
    "sup_legal",
    "sup_sig_m2",
)

#: Columnas del SELECT en el mismo orden que `_props` espera.
_COLUMNAS = (
    "p.id, p.ccatastral, p.dpto, p.dist, p.padron, p.zona, p.mz, p.lote, "
    "p.finca, p.matricula, p.colonia, p.reg_prof, p.nombre_obj, p.tipo, "
    "p.zona_urban, p.sup_legal, p.sup_sig_m2, p.area_m2, p.geometria"
)


# --- estado de la construcción -------------------------------------------
_ESTADO: dict[str, Any] = {
    "construyendo": False,
    "progreso": 0.0,
    "mensaje": "",
    "error": None,
    "inicio": None,
}
_CANDADO = threading.Lock()


def _marcar(**cambios: Any) -> None:
    with _CANDADO:
        _ESTADO.update(cambios)


def _estado_construccion() -> dict[str, Any]:
    with _CANDADO:
        return dict(_ESTADO)


# --- rutas ----------------------------------------------------------------
def ruta_indice() -> Path:
    """Índice SQLite del catastro. Vive con las cachés, nunca en el repo."""
    return raiz_media() / "catastro" / "catastro.sqlite3"


def origen() -> Path | None:
    """El `.shp` configurado: el archivo, el más grande de la carpeta o de un nivel."""
    raiz = raiz_catastro()
    if raiz.is_file() and raiz.suffix.lower() == ".shp":
        return raiz
    if not raiz.is_dir():
        return None
    candidatos = sorted(raiz.glob("*.shp"))
    if not candidatos:
        candidatos = sorted(raiz.glob("*/*.shp"))
    if not candidatos:
        return None
    return max(candidatos, key=lambda ruta: ruta.stat().st_size)


def _firma(shp: Path) -> str:
    datos = shp.stat()
    return f"{datos.st_size}:{datos.st_mtime_ns}"


# --- lectura del shapefile -------------------------------------------------
# Sin pyshp: el DBF pesa 1,7 GB y de sus 33 campos sólo se guardan 16. Leer los
# bytes necesarios (y las geometrías) recorta la construcción de minutos a uno.


def _campos_dbf(ruta: Path) -> tuple[dict[str, tuple[int, int]], int, int, int]:
    if not ruta.is_file():
        raise FileNotFoundError(f"falta el DBF del catastro: {ruta}")
    with ruta.open("rb") as archivo:
        cabecera = archivo.read(32)
        if len(cabecera) < 32:
            raise ValueError(f"DBF truncado: {ruta}")
        total = struct.unpack("<I", cabecera[4:8])[0]
        inicio = struct.unpack("<H", cabecera[8:10])[0]
        largo = struct.unpack("<H", cabecera[10:12])[0]
        archivo.seek(32)
        campos: dict[str, tuple[int, int]] = {}
        posicion = 1
        for _ in range(max(0, (inicio - 32 - 1) // 32)):
            descriptor = archivo.read(32)
            if len(descriptor) < 32:
                break
            nombre = (
                descriptor[0:11].split(b"\x00")[0]
                .decode("ascii", "ignore")
                .strip()
                .lower()
            )
            campos[nombre] = (posicion, descriptor[16])
            posicion += descriptor[16]
    return campos, total, inicio, largo


def _leer_dbf(ruta: Path) -> tuple[int, Iterator[dict[str, str]]]:
    campos, total, inicio, largo = _campos_dbf(ruta)
    usados = [(nombre, *campos[nombre]) for nombre in _CAMPOS if nombre in campos]

    def generar() -> Iterator[dict[str, str]]:
        with ruta.open("rb") as archivo:
            archivo.seek(inicio)
            for _ in range(total):
                registro = archivo.read(largo)
                if len(registro) < largo:
                    return
                yield {
                    nombre: registro[pos : pos + ancho]
                    .decode("utf-8", "replace")
                    .strip()
                    for nombre, pos, ancho in usados
                }

    return total, generar()


def _leer_shapes(ruta: Path) -> Iterator[tuple[tuple[int, ...], tuple[float, ...]] | None]:
    """Partes y puntos de cada polígono, en el orden del DBF (registros alineados)."""
    with ruta.open("rb") as archivo:
        archivo.seek(100)
        while True:
            cabecera = archivo.read(8)
            if len(cabecera) < 8:
                return
            _, palabras = struct.unpack(">ii", cabecera)
            contenido = archivo.read(max(0, palabras * 2))
            if len(contenido) < palabras * 2:
                return
            if struct.unpack("<i", contenido[0:4])[0] != 5:
                yield None
                continue
            partes_n, puntos_n = struct.unpack("<2i", contenido[36:44])
            if partes_n <= 0 or puntos_n <= 0:
                yield None
                continue
            partes = struct.unpack(f"<{partes_n}i", contenido[44 : 44 + 4 * partes_n])
            inicio = 44 + 4 * partes_n
            puntos = struct.unpack(
                f"<{2 * puntos_n}d", contenido[inicio : inicio + 16 * puntos_n]
            )
            yield partes, puntos


# --- índice ---------------------------------------------------------------
_ESQUEMA_SQL = """
PRAGMA journal_mode = OFF;
PRAGMA synchronous = OFF;
CREATE TABLE parcelas (
    id INTEGER PRIMARY KEY,
    ccatastral TEXT NOT NULL,
    dpto TEXT,
    dist TEXT,
    padron TEXT,
    zona TEXT,
    mz TEXT,
    lote TEXT,
    finca TEXT,
    matricula TEXT,
    colonia TEXT,
    reg_prof TEXT,
    nombre_obj TEXT,
    tipo TEXT,
    zona_urban TEXT,
    sup_legal REAL,
    sup_sig_m2 REAL,
    area_m2 REAL,
    geometria BLOB NOT NULL
);
CREATE VIRTUAL TABLE parcelas_geo USING rtree(id, minx, maxx, miny, maxy);
CREATE TABLE meta (clave TEXT PRIMARY KEY, valor TEXT NOT NULL);
"""

_SQL_INSERT = (
    "INSERT INTO parcelas VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
)
_SQL_INSERT_GEO = "INSERT INTO parcelas_geo VALUES (?,?,?,?,?)"


def _texto(valor: Any) -> str:
    """Campo de texto limpio. El SNC rellena con asteriscos los campos vacíos."""
    if valor is None:
        return ""
    limpio = str(valor).strip()
    if not limpio or set(limpio) <= {"*"}:
        return ""
    return limpio


def _numero(valor: Any) -> float | None:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _proyectar(geom: Any, transformer: Transformer) -> Any:
    """Pyproj sobre la geometría entera, con las coordenadas en bloque."""
    return shapely.transform(
        geom,
        lambda coords: np.column_stack(
            transformer.transform(coords[:, 0], coords[:, 1])
        ),
    )


def _anillos(
    partes: tuple[int, ...], puntos: tuple[float, ...]
) -> list[list[tuple[float, float]]]:
    cortes = list(partes) + [len(puntos) // 2]
    return [
        [(puntos[2 * i], puntos[2 * i + 1]) for i in range(cortes[k], cortes[k + 1])]
        for k in range(len(cortes) - 1)
    ]


def _dentro_utm(xs: list[float], ys: list[float]) -> bool:
    return (
        _UTM_X[0] <= min(xs)
        and max(xs) <= _UTM_X[1]
        and _UTM_Y[0] <= min(ys)
        and max(ys) <= _UTM_Y[1]
    )


def _geometria(
    partes: tuple[int, ...], puntos: tuple[float, ...]
) -> tuple[Any | None, float, bool]:
    """Geometría en EPSG:4326, área en m² y si hubo que reparar el registro.

    Un puñado de registros del export viene guardado en grados dentro de un
    shapefile declarado en UTM: se detectan por rango y se conservan. Los que
    caen fuera de la ventana de Paraguay se descartan (``None``).
    """
    anillos = _anillos(partes, puntos)
    if not anillos:
        return None, 0.0, False
    x0, y0 = anillos[0][0]
    en_grados = abs(x0) <= 180.0 and abs(y0) <= 90.0
    partes: list[Any] = []
    area = 0.0
    for anillo in anillos:
        if len(anillo) < 3:
            return None, 0.0, en_grados
        if en_grados:
            pol = Polygon([(float(x), float(y)) for x, y in anillo])
            pol_utm = _proyectar(pol, _A_UTM)
        else:
            xs = [float(p[0]) for p in anillo]
            ys = [float(p[1]) for p in anillo]
            if not _dentro_utm(xs, ys):
                return None, 0.0, en_grados
            pol_utm = Polygon(list(zip(xs, ys)))
            lon, lat = _A_4326.transform(xs, ys)
            pol = Polygon(list(zip(lon, lat)))
        if pol_utm.is_empty or pol_utm.area <= 0.0 or pol.is_empty:
            return None, 0.0, en_grados
        area += pol_utm.area
        if not pol.is_valid:
            pol = pol.buffer(0)
        if pol.is_empty or pol.geom_type not in ("Polygon", "MultiPolygon"):
            return None, 0.0, en_grados
        partes.append(pol)
    geom = partes[0] if len(partes) == 1 else unary_union(partes)
    if geom.is_empty or geom.geom_type not in ("Polygon", "MultiPolygon"):
        return None, 0.0, en_grados
    return geom, area, en_grados


def _fila(indice: int, registro: Any, geom: Any, area: float) -> tuple[Any, ...]:
    valores = [_texto(registro[nombre]) for nombre in _CAMPOS]
    sup_legal = _numero(registro["sup_legal"])
    sup_sig = _numero(registro["sup_sig_m2"])
    return (
        indice,
        *valores[:14],
        sup_legal,
        sup_sig,
        round(area, 2),
        geom.wkb,
    )


def construir_indice(shp: Path, db: Path, avisar: Any = None) -> dict[str, Any]:
    """Convierte el shapefile en el índice. Lento a propósito: se hace una vez."""
    db.parent.mkdir(parents=True, exist_ok=True)
    parcial = db.with_name(f"{db.name}.parcial")
    parcial.unlink(missing_ok=True)

    total, registros = _leer_dbf(shp.with_suffix(".dbf"))
    formas = _leer_shapes(shp)
    invalidas = 0
    reparadas = 0
    usadas = 0
    procesadas = 0
    momento = time.time()

    con = sqlite3.connect(str(parcial))
    try:
        con.executescript(_ESQUEMA_SQL)
        filas: list[tuple[Any, ...]] = []
        cajas: list[tuple[Any, ...]] = []
        for indice, par in enumerate(zip(formas, registros)):
            forma, registro = par
            procesadas = indice + 1
            if indice % 4096 == 0 and avisar is not None:
                avisar(
                    min(0.99, indice / max(1, total)),
                    f"Leyendo parcelas {indice:,} de {total:,}",
                )
            if forma is None:
                invalidas += 1
                continue
            geom, area, reparada = _geometria(*forma)
            if geom is None:
                invalidas += 1
                continue
            reparadas += int(reparada)
            minx, miny, maxx, maxy = geom.bounds
            filas.append(_fila(indice, registro, geom, area))
            cajas.append((indice, minx, maxx, miny, maxy))
            usadas += 1
            if len(filas) >= 4000:
                con.executemany(_SQL_INSERT, filas)
                con.executemany(_SQL_INSERT_GEO, cajas)
                filas, cajas = [], []
        if filas:
            con.executemany(_SQL_INSERT, filas)
            con.executemany(_SQL_INSERT_GEO, cajas)
        con.commit()
        if avisar is not None:
            avisar(0.99, "Cerrando el índice")
        con.execute("CREATE INDEX parcelas_ccatastral ON parcelas(ccatastral)")
        con.execute("CREATE INDEX parcelas_finca ON parcelas(finca)")
        con.execute("CREATE INDEX parcelas_area ON parcelas(area_m2)")
        meta = {
            "esquema": str(ESQUEMA),
            "firma": _firma(shp),
            "origen": str(shp),
            "construido": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "segundos": round(time.time() - momento, 1),
            "total": str(total),
            "procesadas": str(procesadas),
            "usadas": str(usadas),
            "invalidas": str(invalidas),
            "reparadas": str(reparadas),
            "epsg_origen": str(EPSG_CATASTRO),
            "fuente": FUENTE,
        }
        con.executemany(
            "INSERT OR REPLACE INTO meta (clave, valor) VALUES (?, ?)",
            list(meta.items()),
        )
        con.commit()
    finally:
        con.close()
    # El reemplazo es atómico: si algo falló, el índice anterior sigue en pie.
    # En Windows un lector abierto (la app sirviendo el mapa) puede bloquear el
    # reemplazo: se reintenta hasta ~20 s antes de darse por vencido.
    for intento in range(50):
        try:
            parcial.replace(db)
            break
        except PermissionError:
            if intento == 49:
                raise
            time.sleep(0.4)
    return {clave: valor for clave, valor in meta.items()}


def _leer_meta(db: Path) -> dict[str, str]:
    if not db.is_file():
        return {}
    try:
        con = sqlite3.connect(f"{db.as_uri()}?mode=ro", uri=True, timeout=5.0)
    except sqlite3.Error:
        return {}
    try:
        filas = con.execute("SELECT clave, valor FROM meta").fetchall()
    except sqlite3.Error:
        return {}
    finally:
        con.close()
    return {str(clave): str(valor) for clave, valor in filas}


def _vigente(meta: dict[str, str], firma: str) -> bool:
    return bool(meta) and meta.get("esquema") == str(ESQUEMA) and meta.get("firma") == firma


def _construir_en_hilo(shp: Path, db: Path, firma: str) -> None:
    try:
        construir_indice(
            shp, db, avisar=lambda fraccion, mensaje: _marcar(
                progreso=round(fraccion, 3), mensaje=mensaje
            )
        )
        _marcar(
            construyendo=False,
            progreso=1.0,
            mensaje="Índice de catastro listo",
            error=None,
        )
    except Exception as exc:  # noqa: BLE001 - el estado debe contar cualquier falla
        _marcar(
            construyendo=False,
            mensaje="No se pudo construir el índice de catastro",
            error=f"{type(exc).__name__}: {exc}",
        )
    finally:
        with _CANDADO:
            _ESTADO["inicio"] = None


def asegurar_indice() -> dict[str, str]:
    """Meta del índice vigente; si falta o está viejo, lo construye en segundo plano."""
    shp = origen()
    if shp is None:
        return {}
    db = ruta_indice()
    firma = _firma(shp)
    meta = _leer_meta(db)
    if _vigente(meta, firma):
        return meta
    with _CANDADO:
        if _ESTADO["construyendo"]:
            return {}
        _ESTADO.update(
            construyendo=True,
            progreso=0.0,
            mensaje="Preparando el índice de catastro",
            error=None,
            inicio=time.time(),
        )
    hilo = threading.Thread(
        target=_construir_en_hilo,
        args=(shp, db, firma),
        name="catastro-indice",
        daemon=True,
    )
    hilo.start()
    return {}


# --- normalización --------------------------------------------------------
def _props(fila: tuple[Any, ...]) -> dict[str, Any]:
    (
        ccatastral,
        dpto,
        dist,
        padron,
        zona,
        mz,
        lote,
        finca,
        matricula,
        colonia,
        reg_prof,
        nombre_obj,
        tipo,
        zona_urban,
        sup_legal,
        sup_sig,
        area_m2,
    ) = fila[1:18]
    return {
        "ccatastral": ccatastral,
        "departamento": DEPARTAMENTOS.get(dpto, dpto),
        "dpto": dpto,
        "dist": dist,
        "padron": padron,
        "zona": zona,
        "mz": mz,
        "lote": lote,
        "finca": finca,
        "matricula": matricula,
        "colonia": colonia,
        "reg_prof": reg_prof,
        "nombre_obj": nombre_obj,
        "tipo": tipo,
        "zona_urban": zona_urban,
        "sup_legal": sup_legal,
        "sup_sig_m2": sup_sig,
        "area_ha": round(area_m2 / 10_000.0, 4) if area_m2 else None,
    }


def _coordenadas(geom: Any, precision: int = 6) -> dict[str, Any]:
    """GeoJSON con las coordenadas redondeadas: menos bytes, mismo dibujo."""
    interfaz = geom.__geo_interface__
    tipo = interfaz["type"]

    def anillo(valores: Any) -> list[list[float]]:
        return [[round(float(x), precision), round(float(y), precision)] for x, y in valores]

    if tipo == "Polygon":
        return {"type": tipo, "coordinates": [anillo(a) for a in interfaz["coordinates"]]}
    if tipo == "MultiPolygon":
        return {
            "type": tipo,
            "coordinates": [
                [anillo(a) for a in poligono] for poligono in interfaz["coordinates"]
            ],
        }
    return {"type": tipo, "coordinates": interfaz["coordinates"]}


def _caja(bruto: str) -> tuple[float, float, float, float]:
    try:
        partes = [float(valor) for valor in bruto.split(",")]
    except (AttributeError, ValueError) as exc:
        raise HTTPException(
            status_code=400, detail="bbox debe ser oeste,sur,este,norte"
        ) from exc
    if len(partes) != 4:
        raise HTTPException(status_code=400, detail="bbox debe tener 4 numeros")
    oeste, sur, este, norte = partes
    if not (-180.0 <= oeste < este <= 180.0):
        raise HTTPException(status_code=400, detail="longitudes invalidas o invertidas")
    if not (-90.0 <= sur < norte <= 90.0):
        raise HTTPException(status_code=400, detail="latitudes invalidas o invertidas")
    return (round(oeste, 5), round(sur, 5), round(este, 5), round(norte, 5))


def _conectar() -> sqlite3.Connection:
    return sqlite3.connect(f"{ruta_indice().as_uri()}?mode=ro", uri=True, timeout=10.0)


def _vacio(
    caja: tuple[float, float, float, float],
    zoom: int,
    *,
    requiere_zoom: bool,
    estado: dict[str, Any],
    avisos: list[str] | None = None,
    area_min: float = 0.0,
) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "capa": "catastro",
        "nombre": "Parcelas catastrales",
        "bbox": list(caja),
        "zoom": zoom,
        "min_zoom": ZOOM_MIN,
        "area_min_m2": area_min,
        "area_min_ha": round(area_min / 10_000.0, 2),
        "fuente": {"nombre": FUENTE, "url": "https://www.snc.gov.py/"},
        "atribucion": ATRIBUCION,
        "total": 0,
        "excedido": False,
        "requiere_zoom": requiere_zoom,
        "requiere_indice": not estado.get("disponible", False),
        "indexando": bool(estado.get("indexando")),
        "progreso": float(estado.get("progreso") or 0.0),
        "mensaje": estado.get("mensaje") or "",
        "avisos": avisos or [],
        "features": [],
    }


# --- consultas ------------------------------------------------------------
def _estado_actual() -> dict[str, Any]:
    shp = origen()
    db = ruta_indice()
    corrida = _estado_construccion()
    meta = _leer_meta(db)
    disponible = bool(meta) and shp is not None and _vigente(meta, _firma(shp))
    if shp is None:
        mensaje = (
            "No hay dataset de catastro configurado. Apuntá CLIMATE3D_CATASTRO "
            f"al .shp o a su carpeta (hoy: {raiz_catastro()})."
        )
    elif meta and not disponible and not corrida["construyendo"]:
        mensaje = "El shapefile cambió: hay que reconstruir el índice."
    else:
        mensaje = corrida["mensaje"] or (
            "Índice de catastro listo" if disponible else "Sin índice de catastro"
        )
    return {
        "disponible": disponible,
        "indexando": bool(corrida["construyendo"]),
        "progreso": float(corrida["progreso"]),
        "mensaje": mensaje,
        "error": corrida["error"],
        "ruta_origen": str(shp) if shp is not None else "",
        "ruta_configurada": str(raiz_catastro()),
        "ruta_indice": str(db),
        "parcelas": int(meta.get("usadas", 0)) if disponible else 0,
        "total_origen": int(meta.get("total", 0)) if meta else 0,
        "invalidas": int(meta.get("invalidas", 0)) if disponible else 0,
        "reparadas": int(meta.get("reparadas", 0)) if disponible else 0,
        "construido": meta.get("construido"),
        "segundos": float(meta.get("segundos", 0.0)) if meta else 0.0,
        "bytes_indice": db.stat().st_size if db.is_file() else 0,
        "zoom_min": ZOOM_MIN,
        "fuente": FUENTE,
        "atribucion": ATRIBUCION,
        "departamentos": DEPARTAMENTOS,
    }


def _offset_zoom(zoom: int) -> float:
    return SIMPLIFICACION.get(zoom, 4e-6 if zoom >= 17 else 2e-4)


def area_minima(zoom: int) -> float:
    """Área mínima (m²) para que una parcela ocupe ~2 px a este zoom.

    Al alejarse se descartan las parcelas chicas (lotes urbanos, que se
    superpondrían en una mancha) y quedan las grandes, que son las que se leen
    a esa escala.
    """
    if zoom >= 14:
        return 0.0
    lado = _PIXELES_MINIMOS * _METROS_POR_ZOOM / (2**zoom)
    return round(lado * lado, 1)


def parcelas(caja: tuple[float, float, float, float], zoom: int) -> dict[str, Any]:
    estado = _estado_actual()
    if zoom < ZOOM_MIN:
        return _vacio(caja, zoom, requiere_zoom=True, estado=estado)
    if not estado["disponible"]:
        if origen() is not None:
            asegurar_indice()
            estado = _estado_actual()
        return _vacio(caja, zoom, requiere_zoom=False, estado=estado)

    area_min = area_minima(zoom)
    tolerancia = _offset_zoom(zoom)
    oeste, sur, este, norte = caja
    # Las cajas del R-tree son float32: el margen evita perder el borde.
    margen = 2e-5
    izquierda, derecha = oeste - margen, este + margen
    abajo, arriba = sur - margen, norte + margen
    # Una vista de más de un grado de ancho no es la de este zoom: si igual se
    # pidió, conviene devolver las más grandes en vez de ordenar un millón.
    ancha = max(este - oeste, norte - sur) > 1.0
    con = _conectar()
    try:
        if area_min > 0 or ancha:
            # Vista de país o departamento: el R-tree devuelve cientos de miles
            # de lotes y ordenarlos tarda minutos. Conviene recorrer el índice
            # de área de mayor a menor y quedarse con las que caen en la vista:
            # son justo las estancias grandes que se leen a esta escala.
            filas = con.execute(
                f"SELECT {_COLUMNAS} FROM parcelas AS p INDEXED BY parcelas_area "
                "JOIN parcelas_geo AS g ON g.id = p.id "
                "WHERE p.area_m2 >= ? "
                "AND g.maxx >= ? AND g.minx <= ? AND g.maxy >= ? AND g.miny <= ? "
                "ORDER BY p.area_m2 DESC LIMIT ?",
                (
                    area_min,
                    izquierda,
                    derecha,
                    abajo,
                    arriba,
                    LIMITE_DIBUJO + 1,
                ),
            ).fetchall()
        else:
            filas = con.execute(
                f"SELECT {_COLUMNAS} FROM parcelas_geo AS g "
                "JOIN parcelas AS p ON p.id = g.id "
                "WHERE g.maxx >= ? AND g.minx <= ? AND g.maxy >= ? AND g.miny <= ? "
                "ORDER BY p.area_m2 DESC LIMIT ?",
                (izquierda, derecha, abajo, arriba, LIMITE_DIBUJO + 1),
            ).fetchall()
    finally:
        con.close()

    excedido = len(filas) > LIMITE_DIBUJO
    filas = filas[:LIMITE_DIBUJO]
    features = []
    for fila in filas:
        geom = wkb.loads(fila[18])
        simple = geom.simplify(tolerancia, preserve_topology=False)
        if simple.is_empty:
            simple = geom
        features.append(
            {
                "type": "Feature",
                "geometry": _coordenadas(simple),
                "properties": _props(fila),
            }
        )
    respuesta = _vacio(
        caja, zoom, requiere_zoom=False, estado=estado, area_min=area_min
    )
    respuesta["total"] = len(features)
    respuesta["excedido"] = excedido
    respuesta["features"] = features
    respuesta["simplificado_grados"] = tolerancia
    if excedido:
        respuesta["avisos"] = [
            "Se muestran las parcelas más grandes de la vista: acercate para ver todas."
        ]
    return respuesta


class PedidoAfectadas(BaseModel):
    """Caja del visor (o polígono GeoJSON) a cruzar con las parcelas."""

    bbox: list[float] | None = Field(
        default=None, description="oeste,sur,este,norte en grados"
    )
    poligono: dict[str, Any] | None = Field(
        default=None, description="GeoJSON Polygon o MultiPolygon en EPSG:4326"
    )
    limite: int = Field(default=LIMITE_AFECTADAS, ge=1, le=LIMITE_AFECTADAS)


def _pedido_geometria(pedido: PedidoAfectadas) -> tuple[Any, list[float]]:
    if pedido.poligono is not None:
        try:
            geom = shape(pedido.poligono)
        except (ValueError, TypeError, AttributeError) as exc:
            raise HTTPException(status_code=400, detail="poligono GeoJSON invalido") from exc
        if geom.geom_type not in ("Polygon", "MultiPolygon") or geom.is_empty:
            raise HTTPException(status_code=400, detail="se esperaba un Polygon GeoJSON")
        if not geom.is_valid:
            geom = geom.buffer(0)
        if geom.is_empty or geom.geom_type not in ("Polygon", "MultiPolygon"):
            raise HTTPException(status_code=400, detail="el poligono no tiene superficie")
        return geom, [round(valor, 6) for valor in geom.bounds]
    if pedido.bbox is None or len(pedido.bbox) != 4:
        raise HTTPException(
            status_code=400, detail="mandá bbox de 4 numeros o un poligono GeoJSON"
        )
    caja = _caja(",".join(str(valor) for valor in pedido.bbox))
    return box(*caja), list(caja)


def afectadas(pedido: PedidoAfectadas) -> dict[str, Any]:
    estado = _estado_actual()
    geom, caja = _pedido_geometria(pedido)
    geom_utm = _proyectar(geom, _A_UTM)
    base = {
        "type": "FeatureCollection",
        "caja": caja,
        "area_ha": round(geom_utm.area / 10_000.0, 2),
        "total": 0,
        "excedido": False,
        "cubierto_ha": 0.0,
        "cubierto_pct": 0.0,
        "requiere_indice": not estado["disponible"],
        "indexando": estado["indexando"],
        "progreso": estado["progreso"],
        "mensaje": estado["mensaje"],
        "atribucion": ATRIBUCION,
        "features": [],
        "avisos": [],
    }
    if not estado["disponible"]:
        if origen() is not None:
            asegurar_indice()
            estado = _estado_actual()
            base.update(
                requiere_indice=not estado["disponible"],
                indexando=estado["indexando"],
                progreso=estado["progreso"],
                mensaje=estado["mensaje"],
            )
        return base

    oeste, sur, este, norte = caja
    con = _conectar()
    try:
        filas = con.execute(
            f"SELECT {_COLUMNAS} FROM parcelas_geo AS g "
            "JOIN parcelas AS p ON p.id = g.id "
            "WHERE g.maxx >= ? AND g.minx <= ? AND g.maxy >= ? AND g.miny <= ? "
            "LIMIT 20000",
            (oeste, este, sur, norte),
        ).fetchall()
    finally:
        con.close()

    encontradas: list[tuple[float, tuple[Any, ...], Any]] = []
    for fila in filas:
        par_utm = _proyectar(wkb.loads(fila[18]), _A_UTM)
        if not par_utm.is_valid:
            par_utm = par_utm.buffer(0)
        if par_utm.is_empty or par_utm.geom_type not in ("Polygon", "MultiPolygon"):
            continue
        if not par_utm.intersects(geom_utm):
            continue
        area = par_utm.intersection(geom_utm).area
        if area >= 1.0:
            encontradas.append((area, fila, par_utm))
    encontradas.sort(key=lambda item: item[0], reverse=True)
    excedido = len(encontradas) > pedido.limite
    encontradas = encontradas[: pedido.limite]

    features = []
    cubierto = 0.0
    for area, fila, _ in encontradas:
        props = _props(fila)
        area_parcela = fila[17] or 0.0
        props["afectado_m2"] = round(area, 1)
        props["afectado_ha"] = round(area / 10_000.0, 4)
        props["fraccion"] = (
            round(min(1.0, area / area_parcela), 4) if area_parcela else None
        )
        cubierto += area
        features.append(
            {
                "type": "Feature",
                "geometry": _coordenadas(wkb.loads(fila[18])),
                "properties": props,
            }
        )
    base["total"] = len(features)
    base["excedido"] = excedido
    base["cubierto_ha"] = round(cubierto / 10_000.0, 2)
    area_caja = geom_utm.area / 10_000.0
    base["cubierto_pct"] = (
        round(100.0 * base["cubierto_ha"] / area_caja, 1) if area_caja else 0.0
    )
    if excedido:
        base["avisos"] = [
            f"Hay más de {pedido.limite} parcelas en el cuadro: se listan las de "
            "mayor superficie afectada. Achicá el cuadro o subí el límite."
        ]
    base["features"] = features
    return base


# --- router ---------------------------------------------------------------
router = APIRouter()


@router.get("")
def estado() -> dict[str, Any]:
    """Estado del dataset y del índice. Arranca la construcción si hace falta."""
    datos = _estado_actual()
    if origen() is not None and not datos["disponible"] and not datos["indexando"]:
        asegurar_indice()
        datos = _estado_actual()
    return datos


@router.get("/parcelas")
def capa_parcelas(
    bbox: str = Query(..., description="oeste,sur,este,norte en grados"),
    zoom: int = Query(ZOOM_MIN, ge=0, le=22),
) -> dict[str, Any]:
    return parcelas(_caja(bbox), zoom)


@router.post("/afectadas")
def parcelas_afectadas(pedido: PedidoAfectadas) -> dict[str, Any]:
    return afectadas(pedido)
