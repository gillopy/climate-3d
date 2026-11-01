"""Descarga el viento en 250 mb (`u`, `v`) y la presión a nivel del mar (`msl`) de ECMWF.

Producto: **velocidad del viento en 250 mb** (en nudos) y **campo de MSLP** (en hPa) del
IFS HRES 0.25° de ECMWF Open Data:

    https://data.ecmwf.int/forecasts/<yyyymmdd>/<ciclo>z/ifs/0p25/oper/
        <yyyymmdd><ciclo>0000-<paso>h-oper-fc.index    (JSON Lines: un mensaje por línea)
        <yyyymmdd><ciclo>0000-<paso>h-oper-fc.grib2    (todos los campos del paso)

Bajar el `.grib2` completo de cada paso son decenas de MB. Como el `.index` publica
`_offset` y `_length` de cada mensaje, acá se piden **sólo los rangos de bytes** de los
tres campos que interesan:

| Variable | Índice                  | Unidades | Uso                          |
| -------- | ----------------------- | -------- | ---------------------------- |
| `u`      | `levtype="pl"`, 250 hPa | m s**-1  | viento zonal a 250 mb        |
| `v`      | `levtype="pl"`, 250 hPa | m s**-1  | viento meridional a 250 mb   |
| `msl`    | `levtype="sfc"`         | Pa       | presión a nivel del mar       |

**Ojo**: en el `.index`, `levelist` viene como **string** (`"250"`), hay que castear antes
de comparar. Además `u`/`v` aparecen en muchos niveles de presión: sin filtrar por
`levtype` + `levelist` se agarra el nivel equivocado.

Los GRIB2 de ECMWF usan `dataRepresentationTemplateNumber = 42` (empaquetado CCSDS/AEC),
que las herramientas viejas de GRIB no decodifican. Por eso el lector es **eccodes** (el
paquete de PyPI trae la librería compilada).

Unidades de salida: `u`/`v` en **m/s** (el render multiplica por 1.9438445 para obtener
nudos) y `msl` en **hPa** (`Pa / 100`).

Crudos y consolidado:

- `crudo_NNN_fhHHH_u.grib2`, `crudo_NNN_fhHHH_v.grib2`, `crudo_NNN_fhHHH_msl.grib2` por
  paso (reanudable: se reutiliza si el tamaño coincide con `_length` y el marco GRIB
  está sano).
- `serie_viento_250.npz`, en el orden que espera el render (lat 90→-90, lon -180→179.75),
  con `u_ms`, `v_ms`, `msl_hpa` (`(pasos, 721, 1440)` float32), `lat`, `lon`, `horas` y
  `fecha_init`.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe descargar\\viento_250_mslp.py
    .venv\\Scripts\\python.exe descargar\\viento_250_mslp.py --fecha 2026-10-20 --ciclo 18 --hasta-hora 144 --paso 6
    .venv\\Scripts\\python.exe descargar\\viento_250_mslp.py --help   # no toca la red
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

# Fuentes: ECMWF Open Data (JSONL `.index`) y GFS 0.25 de AWS Open Data (`.idx`).
BASES = {
    "ifs": "https://data.ecmwf.int/forecasts/{ymd}/{ciclo}z/ifs/0p25/oper",
    "gfs": "https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.{ymd}/{ciclo}/atmos",
}
MODELOS = ("ifs", "gfs")
ETIQUETAS = {
    "ifs": "ECMWF IFS 0.25°",
    "gfs": "GFS 0.25°",
}

# Nombre del parámetro en el índice de cada fuente. En el GRIB, el shortName de
# PRMSL es `prmsl` (no `msl`): el decodificador acepta los dos.
PARAMS_ECMWF = {"u": "u", "v": "v", "msl": "msl"}
PARAMS_GFS = {"u": "UGRD", "v": "VGRD", "msl": "PRMSL"}
NIVEL_GFS = "250 mb"
NOMBRES_GRIB = {"u": ("u",), "v": ("v",), "msl": ("msl", "prmsl")}

# Variables del producto: nombre del parámetro en el índice -> unidades esperadas.
VARIABLES = ("u", "v", "msl")
UNIDADES = {
    "u": ("m s**-1", "m s-1", "m/s"),
    "v": ("m s**-1", "m s-1", "m/s"),
    "msl": ("Pa",),
}
# msl viene en Pa; el render y el poster trabajan en hPa.
ESCALA_MSL = 0.01

# Nivel de presión del viento (hPa). En el índice `levelist` es un string.
NIVEL_VENTO = "250"

FECHA = "2026-10-20"                    # UTC: día de la corrida
CICLO = "18"                            # UTC: 00, 06, 12 o 18
HASTA_HORA = 144                        # último paso de pronóstico (6 días)
PASO_HORA = 6                           # horas entre pasos
HILOS = 8                               # descargas simultáneas

# Rejilla nativa del IFS 0.25°: 1440 x 721, de 90°N a 90°S y de 180°W a 179.75°E.
FILAS, COLUMNAS = 721, 1440
LAT_DESDE, LAT_HASTA = 90.0, -90.0
LON_DESDE, LON_HASTA = -180.0, 179.75

# Factor de m/s a nudos (1 kn = 0.514444 m/s).
MS_A_KT = 1.9438445

# Caja de verificación de Sudamérica / Paraguay (oeste, este, sur, norte).
CAJA_SA = (-65.0, -45.0, -32.0, -18.0)

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


def url_archivo(ymd: str, ciclo: str, hora: int, extension: str,
                modelo: str = "ifs") -> str:
    """URL del índice (`.index`/`.idx`) o del GRIB del paso `hora`."""
    if modelo == "gfs":
        sufijo = ".idx" if extension == "index" else ""
        nombre = f"gfs.t{ciclo}z.pgrb2.0p25.f{hora:03d}{sufijo}"
    else:
        nombre = f"{ymd}{ciclo}0000-{hora}h-oper-fc.{extension}"
    return f"{BASES[modelo].format(ymd=ymd, ciclo=ciclo)}/{nombre}"


def pasos(hasta_hora: int, paso_hora: int) -> list[int]:
    """Pasos de pronóstico `0, paso, 2*paso, ..., hasta_hora`."""
    if paso_hora <= 0:
        raise SystemExit(f"--paso debe ser positivo (recibí {paso_hora}).")
    if hasta_hora < 0:
        raise SystemExit(f"--hasta-hora debe ser >= 0 (recibí {hasta_hora}).")
    return list(range(0, hasta_hora + 1, paso_hora))


def _largo_remoto(url: str) -> int:
    """Tamaño del GRIB remoto. El `.idx` de GFS no publica el largo del registro."""
    r = _sesion().head(url, timeout=60, allow_redirects=True)
    r.raise_for_status()
    largo = r.headers.get("Content-Length")
    if not largo:
        raise ValueError(f"{url.rsplit('/', 1)[-1]}: sin Content-Length")
    return int(largo)


def _leer_indice_gfs(url: str) -> list[dict]:
    """Entradas del `.idx` de GFS: `n:offset:d=fecha:PARAM:nivel:fcst:`.

    El `.idx` no trae el largo de cada mensaje, así que se calcula con el offset
    del siguiente; el último llega hasta el final del GRIB (HEAD Content-Length).
    """
    r = _sesion().get(url, timeout=120)
    r.raise_for_status()
    filas: list[dict] = []
    for linea in r.text.splitlines():
        partes = linea.split(":")
        if len(partes) < 5:
            continue
        try:
            offset = int(partes[1])
        except ValueError:
            continue
        filas.append({"param": partes[3].strip(), "levelist": partes[4].strip(),
                      "levtype": "", "_offset": offset})
    if not filas:
        return []
    total = _largo_remoto(url[: -len(".idx")])
    for i, fila in enumerate(filas):
        fin = filas[i + 1]["_offset"] if i + 1 < len(filas) else total
        fila["_length"] = fin - fila["_offset"]
    return filas


def _leer_indice(url: str, modelo: str = "ifs") -> list[dict]:
    """Entradas del índice del paso, normalizadas para las dos fuentes."""
    if modelo == "gfs":
        return _leer_indice_gfs(url)
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


def _entradas_var(entradas: list[dict], variable: str,
                  modelo: str = "ifs") -> list[dict]:
    """Entradas del índice que corresponden a `variable`.

    `u`/`v` viven en niveles de presión: hay que filtrar por nivel, que en el índice
    de ECMWF viene como string (`"250"`) y en el de GFS como `250 mb`. `msl` es de
    superficie (`msl` en ECMWF, `PRMSL` en GFS).
    """
    if modelo == "gfs":
        param = PARAMS_GFS[variable]
        nivel = "mean sea level" if variable == "msl" else NIVEL_GFS
        return [e for e in entradas
                if e.get("param") == param and e.get("levelist") == nivel]
    if variable == "msl":
        return [e for e in entradas
                if e.get("param") == "msl" and e.get("levtype") == "sfc"]
    return [e for e in entradas
            if e.get("param") == variable and e.get("levtype") == "pl"
            and str(e.get("levelist")) == NIVEL_VENTO]


def rangos_paso(ymd: str, ciclo: str, hora: int,
                modelo: str = "ifs") -> dict[str, tuple[int, int]]:
    """`{variable: (offset, length)}` de los tres campos del paso `hora`."""
    entradas = _leer_indice(url_archivo(ymd, ciclo, hora, "index", modelo), modelo)
    rangos: dict[str, tuple[int, int]] = {}
    for variable in VARIABLES:
        candidatas = _entradas_var(entradas, variable, modelo)
        if not candidatas:
            raise LookupError(f"{ymd} {ciclo}z {hora}h: el índice no trae {variable} "
                              f"({'sfc' if variable == 'msl' else 'pl/' + NIVEL_VENTO})")
        e = candidatas[0]
        rangos[variable] = (int(e["_offset"]), int(e["_length"]))
    return rangos


def _reutilizable(destino: Path, largo: int) -> bool:
    """True si `destino` ya es el mensaje completo (mismo tamaño y marco GRIB válido)."""
    if not destino.exists() or destino.stat().st_size != largo:
        return False
    with destino.open("rb") as f:
        cabecera = f.read(4)
        f.seek(-4, 2)
        cola = f.read(4)
    return cabecera == b"GRIB" and cola == b"7777"


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


def descargar_paso(ymd: str, ciclo: str, hora: int, idx: int, salida: Path,
                   forzar: bool = False, reintentos: int = 4,
                   modelo: str = "ifs") -> tuple[list[Path], int]:
    """Baja `u`, `v` y `msl` del paso `hora`; devuelve `(rutas, reutilizados)`.

    Reanudable: si el mensaje ya existe con el tamaño exacto que publica el índice (y
    `forzar` está apagado), no se vuelve a pedir. Se valida además el marco GRIB
    (`GRIB`...`7777`) para no reutilizar una descarga cortada.
    """
    salida.mkdir(parents=True, exist_ok=True)
    espera = 2.0
    for intento in range(1, reintentos + 1):
        try:
            # El índice también se reintenta: es un GET chico, pero si se cae la red en
            # el medio de la corrida conviene reintentar este en vez de abortar.
            rangos = rangos_paso(ymd, ciclo, hora, modelo)
            rutas: list[Path] = []
            reutilizados = 0
            for variable in VARIABLES:
                offset, largo = rangos[variable]
                destino = salida / f"crudo_{idx:03d}_fh{hora:03d}_{variable}.grib2"
                if not forzar and _reutilizable(destino, largo):
                    reutilizados += 1
                    rutas.append(destino)
                    continue
                contenido = _bajar_rango(
                    url_archivo(ymd, ciclo, hora, "grib2", modelo), offset, largo)
                tmp = destino.with_suffix(destino.suffix + ".parcial")
                tmp.write_bytes(contenido)
                # Escritura atómica: si el proceso se corta a mitad, no queda un GRIB
                # truncado que después se reutilice como si estuviera bueno.
                tmp.replace(destino)
                rutas.append(destino)
            return rutas, reutilizados
        except Exception as exc:                       # red, corte o respuesta rara
            if intento == reintentos:
                raise
            print(f"    reintento {intento}/{reintentos - 1} (paso {hora}h: {exc})",
                  flush=True)
            time.sleep(espera)
            espera *= 2
    # Inalcanzable: el último intento siempre retorna o propaga la excepción.
    raise AssertionError("bucle de reintentos sin retorno")


# --------------------------------------------------------------- decodificación GRIB
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


def _factor_unidades(gid, variable: str, origen: str) -> float:
    """Factor a la unidad de salida según la unidad que declara el GRIB.

    `u`/`v` salen en m/s (factor 1) y `msl` en Pa (factor 0.01, para hPa).
    """
    unidades = str(eccodes.codes_get(gid, "units")).strip()
    if unidades in UNIDADES[variable]:
        return ESCALA_MSL if variable == "msl" else 1.0
    raise ValueError(f"{origen}: unidades desconocidas {unidades!r} para {variable}")


# `eccodes` comparte estado interno en la librería C: la decodificación se serializa
# aunque las descargas sigan en paralelo (decodificar un mensaje es cuestión de ms).
_ECCODES = threading.Lock()


def _decodificar_gid(gid, variable: str, origen: str) -> tuple[np.ndarray, np.ndarray,
                                                             np.ndarray]:
    """Decodifica un `gid` abierto y devuelve `(campo, lat, lon)` ya orientados."""
    nombre = str(eccodes.codes_get(gid, "shortName"))
    if nombre not in NOMBRES_GRIB[variable]:
        raise ValueError(f"{origen}: se esperaba {variable}, vino {nombre}")
    ni = int(eccodes.codes_get(gid, "Ni"))
    nj = int(eccodes.codes_get(gid, "Nj"))
    inc_i = float(eccodes.codes_get(gid, "iDirectionIncrementInDegrees"))
    inc_j = float(eccodes.codes_get(gid, "jDirectionIncrementInDegrees"))
    lat0 = float(eccodes.codes_get(gid, "latitudeOfFirstGridPointInDegrees"))
    lon0 = float(eccodes.codes_get(gid, "longitudeOfFirstGridPointInDegrees"))
    modo = int(eccodes.codes_get(gid, "scanningMode"))
    factor = _factor_unidades(gid, variable, origen)
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
    campo = np.ascontiguousarray(campo.astype(np.float32) * np.float32(factor),
                                 dtype=np.float32)
    return campo, lat, lon


def _decodificar_bytes(datos: bytes, variable: str, origen: str) -> tuple[np.ndarray,
                                                                          np.ndarray,
                                                                          np.ndarray]:
    """Decodifica un mensaje GRIB2 en memoria (`codes_new_from_message`)."""
    with _ECCODES:
        gid = eccodes.codes_new_from_message(datos)
        if gid is None:
            raise ValueError(f"{origen}: el rango no contiene un mensaje GRIB")
        try:
            return _decodificar_gid(gid, variable, origen)
        finally:
            eccodes.codes_release(gid)


def leer_campo(ruta: Path, variable: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Decodifica un GRIB2 crudo y devuelve `(campo, lat, lon)` ya orientados."""
    return _decodificar_bytes(ruta.read_bytes(), variable, ruta.name)


# ---------------------------------------------------------------------- reportes
def _caja(lat: np.ndarray, lon: np.ndarray,
          oeste: float, este: float, sur: float, norte: float):
    """Máscaras de filas y columnas de la caja lon/lat pedida."""
    return (lat <= norte) & (lat >= sur), (lon >= oeste) & (lon <= este)


def _max_caja(campo: np.ndarray, lat: np.ndarray, lon: np.ndarray, caja,
              ) -> tuple[float, float, float]:
    """`(máximo, lat, lon)` dentro de la caja."""
    filas, cols = _caja(lat, lon, *caja)
    sub = campo[np.ix_(filas, cols)]
    j, i = np.unravel_index(int(np.argmax(sub)), sub.shape)
    return float(sub[j, i]), float(lat[filas][j]), float(lon[cols][i])


def _tabla_resumen(serie_kt: np.ndarray, serie_msl: np.ndarray, horas: np.ndarray,
                   lat: np.ndarray, lon: np.ndarray) -> None:
    """Tabla compacta: cada 24 h más el último paso, con el máximo de la caja SA."""
    print("\nViento en 250 mb (kt) y MSLP (hPa):")
    print("  paso   máx global   máx Sudamérica   MSLP mín/máx global")
    elegidos = [int(h) for h in horas if int(h) % 24 == 0]
    if int(horas[-1]) not in elegidos:
        elegidos.append(int(horas[-1]))
    for h in elegidos:
        i = int(np.where(horas == h)[0][0])
        kt = serie_kt[i]
        msl = serie_msl[i]
        global_kt = float(kt.max())
        sa_kt, _, _ = _max_caja(kt, lat, lon, CAJA_SA)
        print(f"  {h:3d} h  {global_kt:9.1f}   {sa_kt:11.1f}      "
              f"{float(msl.min()):7.1f} / {float(msl.max()):7.1f}")


def _reporte_final(serie_kt: np.ndarray, serie_msl: np.ndarray, horas: list[int],
                   lat: np.ndarray, lon: np.ndarray) -> None:
    """Tabla de resumen y máximos de la caja SA para el último paso."""
    _tabla_resumen(serie_kt, serie_msl, np.asarray(horas, dtype=np.int32), lat, lon)
    ultimo = len(horas) - 1
    global_kt, glat, glon = _max_caja(serie_kt[ultimo], lat, lon,
                                      (LON_DESDE, LON_HASTA, LAT_HASTA, LAT_DESDE))
    sa_kt, salat, salon = _max_caja(serie_kt[ultimo], lat, lon, CAJA_SA)
    msl = serie_msl[ultimo]
    print(f"\nFH {horas[ultimo]}h: máx global {global_kt:.1f} kt en "
          f"lat {glat:.2f}, lon {glon:.2f}")
    print(f"FH {horas[ultimo]}h: máx Sudamérica (lon {CAJA_SA[0]:g}..{CAJA_SA[1]:g}, "
          f"lat {CAJA_SA[2]:g}..{CAJA_SA[3]:g}) {sa_kt:.1f} kt en "
          f"lat {salat:.2f}, lon {salon:.2f}")
    print(f"FH {horas[ultimo]}h: MSLP global {float(msl.min()):.1f} .. "
          f"{float(msl.max()):.1f} hPa")


def _comando_extra(args) -> str:
    extras = []
    if args.modelo != "ifs":
        extras.append(f"--modelo {args.modelo}")
    if args.out:
        extras.append(f'--out "{args.out}"')
    return (" " + " ".join(extras)) if extras else ""


def _comando_descarga(args) -> str:
    """El mismo comando, para reintentar sólo los pasos que faltan."""
    return (f".venv\\Scripts\\python.exe descargar\\viento_250_mslp.py "
            f"--fecha {args.fecha} --ciclo {args.ciclo} --hasta-hora {args.hasta_hora} "
            f"--paso {args.paso} --hilos {args.hilos}") + _comando_extra(args)


def _comando_render(args) -> str:
    """El comando EXACTO de render que consume `serie_viento_250.npz`."""
    return (f".venv\\Scripts\\python.exe cuadros\\cuadros_viento_250.py "
            f"--fecha {args.fecha} --ciclo {args.ciclo} --hasta-hora {args.hasta_hora} "
            f"--paso {args.paso}") + _comando_extra(args)


def _dir_salida(args, ciclo: str) -> Path:
    """Carpeta de crudos por defecto: el IFS conserva el nombre viejo."""
    if args.out:
        return Path(args.out)
    if args.modelo == "ifs":
        return DATOS / f"crudos_viento250_{args.fecha}_{ciclo}z"
    return DATOS / f"crudos_viento250_{args.modelo}_{args.fecha}_{ciclo}z"


def _npz_completo(cache: Path, horas: list[int]):
    """Lee `serie_viento_250.npz` si ya cubre exactamente los pasos pedidos; si no, None."""
    if not cache.exists():
        return None
    try:
        with np.load(cache, allow_pickle=False) as d:
            if not all(k in d.files for k in ("u_ms", "v_ms", "msl_hpa", "horas")):
                return None
            u = np.asarray(d["u_ms"], dtype=np.float32)
            v = np.asarray(d["v_ms"], dtype=np.float32)
            msl = np.asarray(d["msl_hpa"], dtype=np.float32)
            guardadas = [int(h) for h in np.asarray(d["horas"]).ravel()]
            lat = np.asarray(d["lat"], dtype=np.float32)
            lon = np.asarray(d["lon"], dtype=np.float32)
    except Exception:
        return None
    if guardadas != horas or u.shape != (len(horas), FILAS, COLUMNAS):
        return None
    _verificar_rejilla(lat, lon)
    return u, v, msl, lat, lon


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Descarga `u`, `v` (250 mb) y `msl` de ECMWF IFS 0.25° o de GFS "
                    "0.25° por HTTP Range y deja una serie consolidada (m/s, hPa).")
    ap.add_argument("--modelo", choices=MODELOS, default="ifs",
                    help="fuente del pronóstico: ifs (ECMWF) o gfs (NOAA)")
    ap.add_argument("--fecha", default=FECHA,
                    help=f"día UTC de la corrida, YYYY-MM-DD (por defecto {FECHA})")
    ap.add_argument("--ciclo", default=CICLO,
                    help=f"ciclo UTC de la corrida: 00, 06, 12 o 18 (por defecto {CICLO})")
    ap.add_argument("--hasta-hora", type=int, default=HASTA_HORA,
                    help=f"último paso de pronóstico en horas (por defecto {HASTA_HORA})")
    ap.add_argument("--paso", type=int, default=PASO_HORA,
                    help=f"horas entre pasos (por defecto {PASO_HORA})")
    ap.add_argument("--hilos", type=int, default=HILOS,
                    help=f"descargas simultáneas (por defecto {HILOS})")
    ap.add_argument("--forzar", action="store_true",
                    help="vuelve a bajar los pasos aunque ya estén completos")
    ap.add_argument("--out", help="carpeta de salida (por defecto, "
                                  "DATOS/crudos_viento250[_<modelo>]_<fecha>_<ciclo>z)")
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
    if args.hilos < 1:
        raise SystemExit(f"--hilos debe ser >= 1 (recibí {args.hilos}).")

    ymd = fecha.strftime("%Y%m%d")
    horas = pasos(args.hasta_hora, args.paso)
    salida = _dir_salida(args, ciclo)
    salida.mkdir(parents=True, exist_ok=True)
    cache = salida / "serie_viento_250.npz"

    if not args.forzar:
        previo = _npz_completo(cache, horas)
        if previo is not None:
            u, v, msl, lat, lon = previo
            serie_kt = (np.hypot(u, v) * np.float32(MS_A_KT)).astype(np.float32)
            print(f"Serie ya completa: {cache} ({u.shape[0]}, {FILAS}, "
                  f"{COLUMNAS})")
            _reporte_final(serie_kt, msl, horas, lat, lon)
            print("Ahora renderizá con: " + _comando_render(args))
            return 0

    print(f"Viento 250 mb + MSLP {ETIQUETAS[args.modelo]} | {args.fecha} {ciclo}z | "
          f"{len(horas)} pasos ({horas[0]}h..{horas[-1]}h cada {args.paso} h)")
    print(f"fuente: {url_archivo(ymd, ciclo, horas[0], 'index', args.modelo)}")
    print(f"crudos en {salida} | {args.hilos} hilos")

    inicio = time.time()
    reutilizados = 0
    fallidos: list[int] = []
    with ThreadPoolExecutor(max_workers=args.hilos) as pool:
        futuros = {
            pool.submit(descargar_paso, ymd, ciclo, h, i + 1, salida,
                        args.forzar, 4, args.modelo): h
            for i, h in enumerate(horas)
        }
        hechos = 0
        for fut in as_completed(futuros):
            h = futuros[fut]
            try:
                _, reusados = fut.result()
            except Exception as exc:
                fallidos.append(h)
                print(f"  paso {h:3d}h  ERROR: {exc}", flush=True)
                continue
            hechos += 1
            reutilizados += int(reusados)
            print(f"  {hechos}/{len(horas)} pasos listos ({reutilizados} reutilizados, "
                  f"errores {len(fallidos)}) {time.time() - inicio:.0f}s", flush=True)

    if fallidos:
        raise SystemExit(f"Faltan {len(fallidos)} pasos: "
                         f"{', '.join(f'{h}h' for h in sorted(fallidos))}\n"
                         f"Reintentá con:\n  {_comando_descarga(args)}")

    print(f"{len(horas)} pasos listos en {time.time() - inicio:.0f}s "
          f"({reutilizados} reutilizados). Consolidando...")

    inicio_dec = time.time()
    serie_u = np.empty((len(horas), FILAS, COLUMNAS), dtype=np.float32)
    serie_v = np.empty((len(horas), FILAS, COLUMNAS), dtype=np.float32)
    serie_msl = np.empty((len(horas), FILAS, COLUMNAS), dtype=np.float32)
    lat = lon = None
    for i, h in enumerate(horas):
        for variable, destino in (("u", serie_u), ("v", serie_v), ("msl", serie_msl)):
            ruta = salida / f"crudo_{i + 1:03d}_fh{h:03d}_{variable}.grib2"
            campo, lat_i, lon_i = leer_campo(ruta, variable)
            destino[i] = campo
            if variable == "u":
                lat, lon = lat_i, lon_i
        if (i + 1) % 10 == 0 or i + 1 == len(horas):
            print(f"  {i + 1}/{len(horas)} pasos consolidados "
                  f"({time.time() - inicio_dec:.0f}s)", flush=True)

    _verificar_rejilla(lat, lon)
    serie_kt = (np.hypot(serie_u, serie_v) * np.float32(MS_A_KT)).astype(np.float32)
    _reporte_final(serie_kt, serie_msl, horas, lat, lon)

    tmp = cache.with_suffix(cache.suffix + ".parcial")
    with tmp.open("wb") as f:
        np.savez(f, u_ms=serie_u, v_ms=serie_v, msl_hpa=serie_msl,
                 lat=lat, lon=lon,
                 horas=np.asarray(horas, dtype=np.int32),
                 fecha_init=f"{args.fecha}T{ciclo}:00Z",
                 modelo=args.modelo)
    tmp.replace(cache)
    print(f"\nSerie consolidada: {cache} ({serie_u.shape[0]}, {FILAS}, {COLUMNAS}) "
          f"float32 | horas {horas[0]}..{horas[-1]} cada {args.paso} h")
    print("Ahora renderizá con: " + _comando_render(args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
