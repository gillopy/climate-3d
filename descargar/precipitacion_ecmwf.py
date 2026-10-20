"""Descarga la precipitación total acumulada (`tp`) de ECMWF para una corrida.

Producto: **Total Precipitation** acumulada desde el inicio de la corrida. Se soportan
tres modelos de ECMWF Open Data a 0.25°:

    ifs           ifs/0p25/oper           determinístico IFS (`oper-fc`)
    aifs-single   aifs-single/0p25/oper   AIFS determinístico (`oper-fc`)
    aifs-ens      aifs-ens/0p25/enfo      AIFS ensamble (`enfo-cf` + `enfo-pf`)

La estructura de URL es:

    https://data.ecmwf.int/forecasts/<yyyymmdd>/<ciclo>z/<ruta-modelo>/
        <yyyymmdd><ciclo>0000-<paso>h-<sufijo>.index    (JSON Lines: un mensaje por línea)
        <yyyymmdd><ciclo>0000-<paso>h-<sufijo>.grib2    (todos los campos del paso)

En `ifs` y `aifs-single` el sufijo es `oper-fc`. En `aifs-ens` los archivos vienen
partidos en dos: `enfo-cf` (control) y `enfo-pf` (50 miembros perturbados); el `.index`
`pf` publica `number` (1..50) por mensaje.

Bajar el `.grib2` completo de cada paso son cientos de MB. Como el `.index` publica
`_offset` y `_length` de cada mensaje, acá se pide **sólo el rango de bytes** de
`param="tp", levtype="sfc"`.

Unidades: el IFS `oper` publica `tp` en **metros** (`m`); `aifs-single` y `aifs-ens`
publican en **kg m**-2** (numéricamente igual a mm). El lector consulta `units` en cada
mensaje y aplica el factor 1000 sólo cuando corresponde, así los tres modelos quedan en
la misma escala.

Los GRIB2 de ECMWF usan `dataRepresentationTemplateNumber = 42` (empaquetado CCSDS/AEC),
que las herramientas viejas de GRIB no decodifican. Por eso el lector es **eccodes** (el
paquete de PyPI trae la librería compilada). El paso 0h llega como campo constante y
decodifica a 0 mm.

Crudos y consolidado:

- `ifs` / `aifs-single`: `crudo_NNN_fhHHH.grib2` por paso.
- `aifs-ens`: `crudo_NNN_fhHHH.npy` con la **media del ensamble** (cf + miembros pf) ya
  en mm y float32. No se guardan los 11 GRIB de cada paso.
- Todos: `serie_tp_mm.npz`, en **mm** y con la rejilla en el orden que espera el render
  (lat 90→-90, lon -180→179.75), para que `cuadros/cuadros_precipitacion.py` no vuelva a
  decodificar GRIB.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe descargar\\precipitacion_ecmwf.py
    .venv\\Scripts\\python.exe descargar\\precipitacion_ecmwf.py --modelo aifs-ens --fecha 2026-10-20 --ciclo 12 --hasta-hora 360 --paso 6
    .venv\\Scripts\\python.exe descargar\\precipitacion_ecmwf.py --fecha 2026-10-20 --ciclo 06 --hasta-hora 144 --paso 3
    .venv\\Scripts\\python.exe descargar\\precipitacion_ecmwf.py --help   # no toca la red
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import eccodes
import numpy as np
import requests

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from rutas import DATOS  # noqa: E402

PARAM = "tp"
LEVTYPE = "sfc"
BASE = "https://data.ecmwf.int/forecasts/{ymd}/{ciclo}z"

MODELOS = ("ifs", "aifs-ens", "aifs-single")
RUTAS_MODELO = {
    "ifs": "ifs/0p25/oper",
    "aifs-single": "aifs-single/0p25/oper",
    "aifs-ens": "aifs-ens/0p25/enfo",
}

FECHA = "2026-10-20"                    # UTC: día de la corrida
CICLO = "06"                            # UTC: 00, 06, 12 o 18
HASTA_HORA = 144                        # último paso de pronóstico (6 días)
PASO_HORA = 3                           # horas entre pasos
HILOS = 6                               # descargas simultáneas (IFS/AIFS-single)
HILOS_ENS = 12                          # descargas simultáneas (aifs-ens)
MIEMBROS = 11                           # cf + 10 pf equiespaciados (media del ensamble)

# Rejilla nativa del IFS 0.25°: 1440 x 721, de 90°N a 90°S y de 180°W a 179.75°E.
FILAS, COLUMNAS = 721, 1440
LAT_DESDE, LAT_HASTA = 90.0, -90.0
LON_DESDE, LON_HASTA = -180.0, 179.75

# Cajas de verificación (oeste, este, sur, norte).
CAJA_SA = (-65.0, -45.0, -32.0, -18.0)   # Sudamérica / Paraguay
CAJA_PY = (-62.0, -54.0, -28.0, -19.0)   # Paraguay y sur de Brasil

# Una sesión por hilo: reutiliza la conexión TLS entre pedidos. Abrir una conexión nueva
# por paso obliga a un handshake por archivo y se come el ancho de banda en latencia.
_LOCAL = threading.local()


def _sesion() -> requests.Session:
    ses = getattr(_LOCAL, "sesion", None)
    if ses is None:
        ses = requests.Session()
        ses.headers["User-Agent"] = "climate3d/1.0"
        adaptador = requests.adapters.HTTPAdapter(pool_connections=8, pool_maxsize=16,
                                                  max_retries=0)
        ses.mount("https://", adaptador)
        ses.mount("http://", adaptador)
        _LOCAL.sesion = ses
    return ses


def _sufijo(modelo: str, hora: int, tipo: str | None = None) -> str:
    """Sufijo del archivo del paso: `oper-fc`, `enfo-cf` o `enfo-pf`."""
    if modelo == "aifs-ens":
        return f"{hora}h-enfo-{tipo or 'cf'}"
    return f"{hora}h-oper-fc"


def url_archivo(ymd: str, ciclo: str, hora: int, extension: str,
                modelo: str = "ifs", tipo: str | None = None) -> str:
    """URL del `.index` (JSONL) o del `.grib2` del paso `hora`.

    `tipo` elige `cf` o `pf` en `aifs-ens`; en los determinísticos se ignora.
    """
    if modelo not in RUTAS_MODELO:
        raise ValueError(f"modelo desconocido: {modelo!r}")
    nombre = f"{ymd}{ciclo}0000-{_sufijo(modelo, hora, tipo)}.{extension}"
    return f"{BASE.format(ymd=ymd, ciclo=ciclo)}/{RUTAS_MODELO[modelo]}/{nombre}"


def pasos(hasta_hora: int, paso_hora: int) -> list[int]:
    """Pasos de pronóstico `0, paso, 2*paso, ..., hasta_hora`."""
    if paso_hora <= 0:
        raise SystemExit(f"--paso debe ser positivo (recibí {paso_hora}).")
    if hasta_hora < 0:
        raise SystemExit(f"--hasta-hora debe ser >= 0 (recibí {hasta_hora}).")
    return list(range(0, hasta_hora + 1, paso_hora))


def _leer_indice(url: str) -> list[dict]:
    """Entradas del `.index` (JSON Lines) del paso."""
    r = _sesion().get(url, timeout=120)
    r.raise_for_status()
    entradas: list[dict] = []
    for linea in r.text.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        try:
            entradas.append(json.loads(linea))
        except json.JSONDecodeError:
            continue
    return entradas


def _entradas_tp(entradas: list[dict]) -> list[dict]:
    """Sólo los mensajes `tp`/`sfc` del índice (no los de presión o suelo)."""
    return [e for e in entradas
            if e.get("param") == PARAM and e.get("levtype") == LEVTYPE]


def rango_tp(ymd: str, ciclo: str, hora: int, modelo: str = "ifs",
             tipo: str | None = None) -> tuple[int, int]:
    """`(offset, length)` del mensaje `tp`/`sfc` en el `.grib2` de `hora`.

    El índice es JSON Lines con un mensaje por línea, e incluye **todos** los campos del
    paso (superficie, niveles de presión, suelo...). Se busca la entrada exacta por
    `param` y `levtype`: pedir `tp` sin filtrar `levtype` también agarraría el de otros
    niveles.
    """
    entradas = _entradas_tp(_leer_indice(
        url_archivo(ymd, ciclo, hora, "index", modelo=modelo, tipo=tipo)))
    if not entradas:
        raise LookupError(f"{ymd} {ciclo}z {hora}h: el índice no trae {PARAM}/{LEVTYPE}")
    primera = entradas[0]
    return int(primera["_offset"]), int(primera["_length"])


def _reutilizable(destino: Path, largo: int) -> bool:
    """True si `destino` ya es el mensaje completo (mismo tamaño y marco GRIB válido)."""
    if not destino.exists() or destino.stat().st_size != largo:
        return False
    with destino.open("rb") as f:
        cabecera = f.read(4)
        f.seek(-4, 2)
        cola = f.read(4)
    return cabecera == b"GRIB" and cola == b"7777"


def _npy_reutilizable(destino: Path) -> bool:
    """True si `destino` es un `.npy` con la rejilla y el dtype esperados."""
    if not destino.exists() or destino.stat().st_size == 0:
        return False
    try:
        campo = np.load(destino, mmap_mode="r")
    except Exception:
        return False
    return (campo.shape == (FILAS, COLUMNAS)
            and np.issubdtype(campo.dtype, np.floating))


def _bajar_rango(url: str, offset: int, largo: int, reintentos: int = 4) -> bytes:
    """Baja exactamente `[offset, offset + largo)` de `url` y valida el marco GRIB."""
    espera = 2.0
    for intento in range(1, reintentos + 1):
        try:
            cabecera = {"Range": f"bytes={offset}-{offset + largo - 1}"}
            r = _sesion().get(url, headers=cabecera, timeout=120)
            r.raise_for_status()
            # El servidor responde 206 con exactamente el rango pedido. Cualquier otro
            # tamaño es una respuesta completa (Range ignorado) o un corte: no se usa.
            if len(r.content) != largo:
                raise ValueError(f"rango incompleto ({len(r.content)} B de {largo})")
            if r.content[:4] != b"GRIB" or r.content[-4:] != b"7777":
                raise ValueError("el rango no es un mensaje GRIB2 completo")
            return r.content
        except Exception as exc:
            if intento == reintentos:
                raise
            print(f"    reintento {intento}/{reintentos - 1} ({url.rsplit('/', 1)[-1]}: "
                  f"{exc})", flush=True)
            time.sleep(espera)
            espera *= 2
    raise AssertionError("bucle de reintentos sin retorno")


def descargar_paso(ymd: str, ciclo: str, hora: int, destino: Path, forzar: bool = False,
                   reintentos: int = 4, modelo: str = "ifs") -> tuple[Path, bool]:
    """Baja el mensaje `tp` de `hora` a `destino`; devuelve `(ruta, reutilizado)`.

    Reanudable: si el archivo ya existe con el tamaño exacto que publica el índice (y
    `forzar` está apagado), no se vuelve a pedir. Se valida además el marco GRIB
    (`GRIB`...`7777`) para no reutilizar una descarga cortada.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    espera = 2.0
    for intento in range(1, reintentos + 1):
        try:
            # El índice también se reintenta: es un GET chico, pero si se cae la red en
            # el medio de la corrida conviene reintentar este en vez de abortar.
            offset, largo = rango_tp(ymd, ciclo, hora, modelo=modelo)
            if not forzar and _reutilizable(destino, largo):
                return destino, True
            contenido = _bajar_rango(url_archivo(ymd, ciclo, hora, "grib2", modelo=modelo),
                                     offset, largo)
            tmp = destino.with_suffix(destino.suffix + ".parcial")
            tmp.write_bytes(contenido)
            # Escritura atómica: si el proceso se corta a mitad, no queda un GRIB
            # truncado que después se reutilice como si estuviera bueno.
            tmp.replace(destino)
            return destino, False
        except Exception as exc:                       # red, corte o respuesta rara
            if intento == reintentos:
                raise
            print(f"    reintento {intento}/{reintentos - 1} (paso {hora}h: {exc})",
                  flush=True)
            time.sleep(espera)
            espera *= 2
    # Inalcanzable: el último intento siempre retorna o propaga la excepción.
    raise AssertionError("bucle de reintentos sin retorno")


def miembros_pf(miembros: int) -> list[int]:
    """Números de miembros `pf` a promediar para `--miembros` (cf aparte).

    `--miembros 1` no pide ningún `pf` (sólo el control). `--miembros 11` usa los 10
    equiespaciados `5, 10, ..., 50`, que dan una media suave y barata. `--miembros 51`
    usa los 50. Para otros valores se reparten los 50 miembros en partes iguales.
    """
    if not 1 <= miembros <= 51:
        raise ValueError(f"--miembros debe estar entre 1 y 51 (recibí {miembros}).")
    n_pf = miembros - 1
    if n_pf == 0:
        return []
    if n_pf >= 50:
        return list(range(1, 51))
    # `round(k * 50 / n_pf)` termina siempre en 50 y, con n_pf = 10, da 5, 10, ..., 50.
    elegidos = [max(1, min(50, int(round(k * 50.0 / n_pf))))
                for k in range(1, n_pf + 1)]
    return list(dict.fromkeys(elegidos))


def descargar_paso_ens(ymd: str, ciclo: str, hora: int, destino: Path, miembros: int,
                       forzar: bool = False, reintentos: int = 2) -> tuple[Path, bool]:
    """Baja `tp` de cf + los pf pedidos, los promedia y guarda `destino` (`.npy`).

    El `.index` de cada paso se lee una sola vez para `cf` y una para `pf`; después se
    piden únicamente los rangos de `tp`/`sfc` de los miembros elegidos. Los mensajes se
    decodifican en memoria y la media (float32, en mm) queda cacheada como `.npy`.
    """
    if not forzar and _npy_reutilizable(destino):
        return destino, True
    destino.parent.mkdir(parents=True, exist_ok=True)
    pedidos = miembros_pf(miembros)
    espera = 2.0
    for intento in range(1, reintentos + 1):
        try:
            entradas_cf = _entradas_tp(_leer_indice(
                url_archivo(ymd, ciclo, hora, "index", modelo="aifs-ens", tipo="cf")))
            if len(entradas_cf) != 1:
                raise LookupError(f"{hora}h: el índice cf trae {len(entradas_cf)} "
                                  f"mensajes {PARAM}/{LEVTYPE}, se esperaba 1")
            por_miembro = {
                int(e["number"]): e for e in _entradas_tp(_leer_indice(
                    url_archivo(ymd, ciclo, hora, "index", modelo="aifs-ens", tipo="pf")))
                if e.get("number") is not None
            }
            faltan = [m for m in pedidos if m not in por_miembro]
            if faltan:
                raise LookupError(f"{hora}h: el índice pf no trae los miembros {faltan}")

            url_cf = url_archivo(ymd, ciclo, hora, "grib2", modelo="aifs-ens", tipo="cf")
            url_pf = url_archivo(ymd, ciclo, hora, "grib2", modelo="aifs-ens", tipo="pf")
            cf = entradas_cf[0]
            suma, _, _ = _decodificar_bytes(
                _bajar_rango(url_cf, int(cf["_offset"]), int(cf["_length"])),
                f"{hora}h cf")
            n = 1
            for numero in pedidos:
                entrada = por_miembro[numero]
                campo, _, _ = _decodificar_bytes(
                    _bajar_rango(url_pf, int(entrada["_offset"]),
                                 int(entrada["_length"])),
                    f"{hora}h pf {numero}")
                suma += campo
                n += 1
            media = (suma / n).astype(np.float32)
            tmp = destino.with_suffix(destino.suffix + ".parcial")
            with tmp.open("wb") as f:
                np.save(f, media)
            tmp.replace(destino)
            return destino, False
        except Exception as exc:
            if intento == reintentos:
                raise
            print(f"    reintento {intento}/{reintentos - 1} (paso {hora}h: {exc})",
                  flush=True)
            time.sleep(espera)
            espera *= 2
    raise AssertionError("bucle de reintentos sin retorno")


def _normalizar_lon(lon: np.ndarray) -> np.ndarray:
    """Convierte longitudes 0..360 a -180..180 (179.75 queda, 180 se vuelve -180)."""
    lon = np.round(np.mod(lon, 360.0), 6)
    return np.where(lon >= 180.0, lon - 360.0, lon)


def _verificar_rejilla(lat: np.ndarray, lon: np.ndarray) -> None:
    """La rejilla debe ser la del IFS 0.25° en el orden que espera el render."""
    if (lat.size, lon.size) != (FILAS, COLUMNAS):
        raise SystemExit(f"Rejilla inesperada: {lon.size}x{lat.size}; se esperaba "
                         f"{COLUMNAS}x{FILAS} (IFS 0.25°).")
    if (not np.isclose(lat[0], LAT_DESDE) or not np.isclose(lat[-1], LAT_HASTA)
            or not np.isclose(lon[0], LON_DESDE) or not np.isclose(lon[-1], LON_HASTA)):
        raise SystemExit(f"Rejilla desalineada: lat {lat[0]}→{lat[-1]}, "
                         f"lon {lon[0]}→{lon[-1]}; se esperaba lat {LAT_DESDE}→"
                         f"{LAT_HASTA} y lon {LON_DESDE}→{LON_HASTA}.")


def _factor_unidades(gid, origen: str) -> float:
    """Factor a mm según la unidad que declara el GRIB.

    El IFS `oper` publica `tp` en metros (`m`), mientras que `aifs-single` y `aifs-ens`
    ya vienen en `kg m**-2`, que es numéricamente idéntico a mm. Escalar todo por 1000
    (o nada) dejaría el render con un factor 1000 de error en dos de los tres productos.
    """
    unidades = str(eccodes.codes_get(gid, "units")).strip()
    if unidades == "m":
        return 1000.0
    if unidades in ("kg m**-2", "kg m-2", "mm"):
        return 1.0
    raise ValueError(f"{origen}: unidades desconocidas {unidades!r} para {PARAM}")


# `eccodes` comparte estado interno en la librería C: la decodificación se serializa
# aunque las descargas sigan en paralelo (decodificar un mensaje es cuestión de ms).
_ECCODES = threading.Lock()


def _decodificar_gid(gid, origen: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Decodifica un `gid` abierto y devuelve `(campo mm, lat, lon)` ya orientados."""
    nombre = eccodes.codes_get(gid, "shortName")
    if nombre != PARAM:
        raise ValueError(f"{origen}: se esperaba {PARAM}, vino {nombre}")
    ni = int(eccodes.codes_get(gid, "Ni"))
    nj = int(eccodes.codes_get(gid, "Nj"))
    inc_i = float(eccodes.codes_get(gid, "iDirectionIncrementInDegrees"))
    inc_j = float(eccodes.codes_get(gid, "jDirectionIncrementInDegrees"))
    lat0 = float(eccodes.codes_get(gid, "latitudeOfFirstGridPointInDegrees"))
    lon0 = float(eccodes.codes_get(gid, "longitudeOfFirstGridPointInDegrees"))
    modo = int(eccodes.codes_get(gid, "scanningMode"))
    factor = _factor_unidades(gid, origen)
    valores = eccodes.codes_get_values(gid)

    if valores.size != ni * nj:
        raise ValueError(f"{origen}: {valores.size} valores para una rejilla "
                         f"{ni}x{nj}")

    # scanningMode (flag table 3.4): bit 0x20 APAGADO = los puntos consecutivos avanzan
    # en i (fila a fila, lo normal en una rejilla regular); encendido = avanzan en j
    # (columna a columna). bit 0x80 = i decrece; bit 0x40 = j crece (sur a norte).
    if modo & 0x20:
        campo = valores.reshape(ni, nj).T
    else:
        campo = valores.reshape(nj, ni)
    dlon = -inc_i if modo & 0x80 else inc_i
    dlat = inc_j if modo & 0x40 else -inc_j
    lon = _normalizar_lon(lon0 + dlon * np.arange(ni))
    lat = lat0 + dlat * np.arange(nj)

    # Los modelos publican la grilla empezando en 180°E: las longitudes ya salen
    # -180..179.75, pero se ordenan igual por si el origen viniera con otro barrido.
    orden = np.argsort(lon, kind="stable")
    if not np.array_equal(orden, np.arange(ni)):
        campo = campo[:, orden]
        lon = lon[orden]
    if lat[0] < lat[-1]:
        campo = campo[::-1]
        lat = lat[::-1]

    lon = np.ascontiguousarray(lon, dtype=np.float32)
    lat = np.ascontiguousarray(lat, dtype=np.float32)
    _verificar_rejilla(lat, lon)
    campo_mm = np.maximum(campo.astype(np.float32) * factor, 0.0).astype(np.float32)
    return campo_mm, lat, lon


def _decodificar_bytes(datos: bytes, origen: str) -> tuple[np.ndarray, np.ndarray,
                                                          np.ndarray]:
    """Decodifica un mensaje GRIB2 en memoria (`codes_new_from_message`)."""
    with _ECCODES:
        gid = eccodes.codes_new_from_message(datos)
        if gid is None:
            raise ValueError(f"{origen}: el rango no contiene un mensaje GRIB")
        try:
            return _decodificar_gid(gid, origen)
        finally:
            eccodes.codes_release(gid)


def _rejilla_estandar() -> tuple[np.ndarray, np.ndarray]:
    """Lat/lon de la rejilla global 0.25° en el orden del render."""
    lat = np.linspace(LAT_DESDE, LAT_HASTA, FILAS, dtype=np.float32)
    lon = np.linspace(LON_DESDE, LON_HASTA, COLUMNAS, dtype=np.float32)
    return lat, lon


def leer_tp_mm(ruta: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Decodifica el GRIB2 y devuelve `(campo mm, lat, lon)` ya orientados.

    El campo sale `float32` (721, 1440) en **mm**, con lat 90→-90 y lon -180→179.75.
    El factor a mm lo decide la unidad del mensaje (ver `_factor_unidades`); `tp` viene
    acumulado desde el inicio de la corrida y se aplica piso en 0 para no arrastrar
    negativos de redondeo del empaquetado.
    """
    with ruta.open("rb") as f:
        gid = eccodes.codes_grib_new_from_file(f)
        if gid is None:
            raise ValueError(f"{ruta.name}: no contiene ningún mensaje GRIB")
        try:
            return _decodificar_gid(gid, ruta.name)
        finally:
            eccodes.codes_release(gid)


def _caja(lat: np.ndarray, lon: np.ndarray,
          oeste: float, este: float, sur: float, norte: float):
    """Máscaras de filas y columnas de la caja lon/lat pedida."""
    return (lat <= norte) & (lat >= sur), (lon >= oeste) & (lon <= este)


def _max_caja(campo: np.ndarray, lat: np.ndarray, lon: np.ndarray, caja,
              ) -> tuple[float, float, float]:
    """`(máximo mm, lat, lon)` dentro de la caja."""
    filas, cols = _caja(lat, lon, *caja)
    sub = campo[np.ix_(filas, cols)]
    j, i = np.unravel_index(int(np.argmax(sub)), sub.shape)
    return float(sub[j, i]), float(lat[filas][j]), float(lon[cols][i])


def _tabla_resumen(serie: np.ndarray, horas: np.ndarray, lat: np.ndarray,
                   lon: np.ndarray) -> None:
    """Tabla compacta: cada 24 h más el último paso, con el máximo de la caja SA."""
    print("\nPrecipitación acumulada (mm):")
    print("  paso   máx global   máx Sudamérica (lon -65..-45, lat -32..-18)")
    elegidos = [int(h) for h in horas if int(h) % 24 == 0]
    if int(horas[-1]) not in elegidos:
        elegidos.append(int(horas[-1]))
    for h in elegidos:
        i = int(np.where(horas == h)[0][0])
        global_mm = float(serie[i].max())
        sa_mm, _, _ = _max_caja(serie[i], lat, lon, CAJA_SA)
        print(f"  {h:3d} h  {global_mm:9.1f} mm  {sa_mm:9.1f} mm")


ETIQUETAS_MODELO = {
    "ifs": "ECMWF IFS 0.25°",
    "aifs-ens": "ECMWF AIFS-ENS 0.25°",
    "aifs-single": "ECMWF AIFS-SINGLE 0.25°",
}


def _reporte_final(serie: np.ndarray, horas: list[int], lat: np.ndarray,
                   lon: np.ndarray) -> None:
    """Tabla de resumen y máximos de la caja SA/PY para el último paso."""
    _tabla_resumen(serie, np.asarray(horas, dtype=np.int32), lat, lon)
    ultimo = len(horas) - 1
    global_mm, glat, glon = _max_caja(serie[ultimo], lat, lon,
                                      (LON_DESDE, LON_HASTA, LAT_HASTA, LAT_DESDE))
    sa_mm, salat, salon = _max_caja(serie[ultimo], lat, lon, CAJA_SA)
    py_mm, pylat, pylon = _max_caja(serie[ultimo], lat, lon, CAJA_PY)
    print(f"\nFH {horas[ultimo]}h: máx global {global_mm:.1f} mm en "
          f"lat {glat:.2f}, lon {glon:.2f}")
    print(f"FH {horas[ultimo]}h: máx Sudamérica (lon {CAJA_SA[0]:g}..{CAJA_SA[1]:g}, "
          f"lat {CAJA_SA[2]:g}..{CAJA_SA[3]:g}) {sa_mm:.1f} mm en "
          f"lat {salat:.2f}, lon {salon:.2f}")
    print(f"FH {horas[ultimo]}h: máx Paraguay / Sur de Brasil (lon {CAJA_PY[0]:g}.."
          f"{CAJA_PY[1]:g}, lat {CAJA_PY[2]:g}..{CAJA_PY[3]:g}) {py_mm:.1f} mm en "
          f"lat {pylat:.2f}, lon {pylon:.2f}")


def _comando_extra(args) -> str:
    extras = []
    if args.modelo != "ifs":
        extras.append(f"--modelo {args.modelo}")
    if args.out:
        extras.append(f'--out "{args.out}"')
    return (" " + " ".join(extras)) if extras else ""


def _comando_descarga(args) -> str:
    """El mismo comando, para reintentar sólo los pasos que faltan."""
    return (f".venv\\Scripts\\python.exe descargar\\precipitacion_ecmwf.py "
            f"--fecha {args.fecha} --ciclo {args.ciclo} --hasta-hora {args.hasta_hora} "
            f"--paso {args.paso} --hilos {args.hilos}") + _comando_extra(args)


def _comando_render(args) -> str:
    """El comando EXACTO de render que consume `serie_tp_mm.npz`."""
    return (f".venv\\Scripts\\python.exe cuadros\\cuadros_precipitacion.py "
            f"--fecha {args.fecha} --ciclo {args.ciclo} --hasta-hora {args.hasta_hora} "
            f"--paso {args.paso}") + _comando_extra(args)


def _dir_salida(args, ciclo: str) -> Path:
    """Carpeta de crudos por defecto, distinta para el determinístico y los AIFS."""
    if args.out:
        return Path(args.out)
    if args.modelo == "ifs":
        return DATOS / f"crudos_precip_ecmwf_{args.fecha}_{ciclo}z"
    return DATOS / f"crudos_precip_{args.modelo}_{args.fecha}_{ciclo}z"


def _npz_completo(cache: Path, horas: list[int]):
    """Lee `serie_tp_mm.npz` si ya cubre exactamente los pasos pedidos; si no, None."""
    if not cache.exists():
        return None
    try:
        with np.load(cache, allow_pickle=False) as d:
            nombre = "tp_mm" if "tp_mm" in d.files else "tp"
            if nombre not in d.files or "horas" not in d.files:
                return None
            tp = np.asarray(d[nombre], dtype=np.float32)
            guardadas = [int(h) for h in np.asarray(d["horas"]).ravel()]
            lat = np.asarray(d["lat"], dtype=np.float32)
            lon = np.asarray(d["lon"], dtype=np.float32)
    except Exception:
        return None
    if guardadas != horas or tp.shape != (len(horas), FILAS, COLUMNAS):
        return None
    _verificar_rejilla(lat, lon)
    return tp, lat, lon


def _meta_ens(salida: Path) -> Path:
    return salida / "_seleccion_miembros.json"


def _miembros_previos(salida: Path) -> int | None:
    ruta = _meta_ens(salida)
    if not ruta.exists():
        return None
    try:
        return int(json.loads(ruta.read_text(encoding="utf-8"))["miembros"])
    except Exception:
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Descarga la precipitación total acumulada (`tp`) de ECMWF "
                    "(IFS, AIFS-ENS o AIFS-SINGLE) 0.25° por HTTP Range y deja una "
                    "serie consolidada en mm.")
    ap.add_argument("--modelo", choices=MODELOS, default="ifs",
                    help="modelo de ECMWF Open Data (por defecto ifs)")
    ap.add_argument("--fecha", default=FECHA,
                    help=f"día UTC de la corrida, YYYY-MM-DD (por defecto {FECHA})")
    ap.add_argument("--ciclo", default=CICLO,
                    help=f"ciclo UTC de la corrida: 00, 06, 12 o 18 (por defecto {CICLO})")
    ap.add_argument("--hasta-hora", type=int, default=HASTA_HORA,
                    help=f"último paso de pronóstico en horas (por defecto {HASTA_HORA})")
    ap.add_argument("--paso", type=int, default=PASO_HORA,
                    help=f"horas entre pasos (por defecto {PASO_HORA})")
    ap.add_argument("--hilos", type=int, default=None,
                    help=f"descargas simultáneas (por defecto {HILOS_ENS} para aifs-ens "
                         f"y {HILOS} para el resto)")
    ap.add_argument("--miembros", type=int, default=MIEMBROS,
                    help=f"miembros del ensamble en aifs-ens: 1 = sólo cf, 11 = cf + 10 "
                         f"pf equiespaciados, 51 = cf + los 50 pf (por defecto {MIEMBROS})")
    ap.add_argument("--forzar", action="store_true",
                    help="vuelve a bajar los pasos aunque ya estén completos")
    ap.add_argument("--out", help="carpeta de salida (por defecto, "
                                  "DATOS/crudos_precip_ecmwf_<fecha>_<ciclo>z para ifs "
                                  "o DATOS/crudos_precip_<modelo>_<fecha>_<ciclo>z "
                                  "para aifs-ens/aifs-single)")
    args = ap.parse_args(argv)

    try:
        fecha = date.fromisoformat(args.fecha)
    except ValueError:
        raise SystemExit(f"--fecha inválida: {args.fecha!r} (se espera YYYY-MM-DD).")
    try:
        ciclo = f"{int(args.ciclo):02d}"
    except ValueError:
        raise SystemExit(f"--ciclo inválido: {args.ciclo!r} (se espera 00, 06, 12 o 18).")
    if ciclo not in ("00", "06", "12", "18"):
        raise SystemExit(f"--ciclo inválido: {args.ciclo!r} (se espera 00, 06, 12 o 18).")
    if args.hilos is None:
        args.hilos = HILOS_ENS if args.modelo == "aifs-ens" else HILOS
    if args.hilos < 1:
        raise SystemExit(f"--hilos debe ser >= 1 (recibí {args.hilos}).")
    try:
        pf_pedidos = miembros_pf(args.miembros)
    except ValueError as exc:
        raise SystemExit(str(exc))

    ymd = fecha.strftime("%Y%m%d")
    horas = pasos(args.hasta_hora, args.paso)
    salida = _dir_salida(args, ciclo)
    salida.mkdir(parents=True, exist_ok=True)
    cache = salida / "serie_tp_mm.npz"

    # Si los crudos se generaron con otra cantidad de miembros, la media cacheada no
    # representa lo pedido: se ignoran los .npy y se vuelve a promediar el ensamble.
    forzar = args.forzar
    if args.modelo == "aifs-ens":
        previos = _miembros_previos(salida)
        if previos is not None and previos != args.miembros and not forzar:
            print(f"Cambió --miembros ({previos} -> {args.miembros}): se rehace la media")
            forzar = True
        _meta_ens(salida).write_text(
            json.dumps({"modelo": args.modelo, "miembros": args.miembros}),
            encoding="utf-8")

    if args.modelo == "aifs-ens" and not forzar:
        previo = _npz_completo(cache, horas)
        if previo is not None:
            serie, lat, lon = previo
            print(f"Serie ya completa: {cache} ({serie.shape[0]}, {FILAS}, "
                  f"{COLUMNAS}) | {len(pf_pedidos)} miembros pf + cf")
            _reporte_final(serie, horas, lat, lon)
            print("Ahora renderizá con: " + _comando_render(args))
            return 0

    print(f"Precipitación total {ETIQUETAS_MODELO[args.modelo]} | {args.fecha} "
          f"{ciclo}z | {len(horas)} pasos ({horas[0]}h..{horas[-1]}h cada {args.paso} h)")
    print(f"fuente: {url_archivo(ymd, ciclo, horas[0], 'index', modelo=args.modelo)}")
    if args.modelo == "aifs-ens":
        print(f"media de cf + {len(pf_pedidos)} miembros pf {pf_pedidos} | "
              f"{args.hilos} hilos")
    print(f"crudos en {salida}")

    inicio = time.time()
    reutilizados = 0
    fallidos: list[int] = []
    with ThreadPoolExecutor(max_workers=args.hilos) as pool:
        if args.modelo == "aifs-ens":
            futuros = {
                pool.submit(descargar_paso_ens, ymd, ciclo, h,
                            salida / f"crudo_{i + 1:03d}_fh{h:03d}.npy",
                            args.miembros, forzar): h
                for i, h in enumerate(horas)
            }
        else:
            futuros = {
                pool.submit(descargar_paso, ymd, ciclo, h,
                            salida / f"crudo_{i + 1:03d}_fh{h:03d}.grib2",
                            forzar, 4, args.modelo): h
                for i, h in enumerate(horas)
            }
        hechos = 0
        for fut in as_completed(futuros):
            h = futuros[fut]
            try:
                _, reutilizado = fut.result()
            except Exception as exc:
                fallidos.append(h)
                print(f"  paso {h:3d}h  ERROR: {exc}", flush=True)
                continue
            hechos += 1
            reutilizados += int(reutilizado)
            print(f"  {hechos}/{len(horas)} pasos listos ({reutilizados} reutilizados, "
                  f"errores {len(fallidos)}) {time.time() - inicio:.0f}s", flush=True)

    if fallidos:
        raise SystemExit(f"Faltan {len(fallidos)} pasos: "
                         f"{', '.join(f'{h}h' for h in sorted(fallidos))}\n"
                         f"Reintentá con:\n  {_comando_descarga(args)}")

    print(f"{len(horas)} pasos listos en {time.time() - inicio:.0f}s "
          f"({reutilizados} reutilizados). Consolidando...")

    inicio_dec = time.time()
    serie = np.empty((len(horas), FILAS, COLUMNAS), dtype=np.float32)
    if args.modelo == "aifs-ens":
        lat, lon = _rejilla_estandar()
        for i, h in enumerate(horas):
            ruta = salida / f"crudo_{i + 1:03d}_fh{h:03d}.npy"
            campo = np.asarray(np.load(ruta), dtype=np.float32)
            if campo.shape != (FILAS, COLUMNAS):
                raise SystemExit(f"{ruta.name}: forma {campo.shape}, se esperaba "
                                 f"({FILAS}, {COLUMNAS}).")
            serie[i] = campo
    else:
        lat = lon = None
        for i, h in enumerate(horas):
            ruta = salida / f"crudo_{i + 1:03d}_fh{h:03d}.grib2"
            serie[i], lat, lon = leer_tp_mm(ruta)
            if (i + 1) % 10 == 0 or i + 1 == len(horas):
                print(f"  {i + 1}/{len(horas)} pasos consolidados "
                      f"({time.time() - inicio_dec:.0f}s)", flush=True)
    if args.modelo == "aifs-ens":
        print(f"  {len(horas)}/{len(horas)} pasos consolidados "
              f"({time.time() - inicio_dec:.0f}s)", flush=True)

    # El acumulado desde el inicio de la corrida tiene que arrancar en 0. Si no, el
    # recorte por bytes o la orientación de la rejilla están mal: mejor abortar acá que
    # guardar una serie silenciosamente corrida.
    if horas[0] == 0 and float(serie[0].max()) > 1e-6:
        raise SystemExit(f"El paso 0h no es cero ({float(serie[0].max()):.3f} mm): "
                         "revisá el rango descargado y la decodificación.")

    _reporte_final(serie, horas, lat, lon)

    tmp = cache.with_suffix(cache.suffix + ".parcial")
    with tmp.open("wb") as f:
        np.savez(f, tp_mm=serie, lat=lat, lon=lon,
                 horas=np.asarray(horas, dtype=np.int32),
                 fecha_init=f"{args.fecha}T{ciclo}:00Z")
    tmp.replace(cache)
    print(f"\nSerie consolidada: {cache} ({serie.shape[0]}, {FILAS}, {COLUMNAS}) "
          f"float32 | horas {horas[0]}..{horas[-1]} cada {args.paso} h")
    print("Ahora renderizá con: " + _comando_render(args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
