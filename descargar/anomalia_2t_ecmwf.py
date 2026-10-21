"""Descarga la temperatura a 2 m (`2t`) de ECMWF y calcula su anomalía vs ERA5.

Producto: **anomalía de temperatura a 2 metros** (`2t`, °C) respecto de una climatología
diurna mensual construida con ERA5. Se soportan los dos determinísticos de ECMWF Open
Data a 0.25°:

    ifs           ifs/0p25/oper           IFS HRES determinístico (`oper-fc`)
    aifs-single   aifs-single/0p25/oper   AIFS determinístico (`oper-fc`)

La estructura de URL es la misma que la de precipitación:

    https://data.ecmwf.int/forecasts/<yyyymmdd>/<ciclo>z/<ruta-modelo>/
        <yyyymmdd><ciclo>0000-<paso>h-oper-fc.index    (JSON Lines: un mensaje por línea)
        <yyyymmdd><ciclo>0000-<paso>h-oper-fc.grib2    (todos los campos del paso)

Bajar el `.grib2` completo de cada paso son cientos de MB. Como el `.index` publica
`_offset` y `_length` de cada mensaje, acá se pide **sólo el rango de bytes** de
`param="2t", levtype="sfc"` y se decodifica con `eccodes`.

Climatología (`climatologia_era5_t2m_mes_hora.npz`)
---------------------------------------------------
El NetCDF de ERA5 (`era5_t2m_2024-2026.nc`, 1464 instantes cada 6 h, `t2m` en K, rejilla
0.25° de 90→-90 y 0→359.75) se lee directamente con **h5py** (es HDF5/NetCDF4, sin
`xarray`). Para cada mes `m` y cada hora UTC `h ∈ {0, 6, 12, 18}` se promedia
`t2m - 273.15` en °C, se rota la longitud de `0..359.75` a `-180..179.75` (para calzar 1:1
con ECMWF Open Data) y se suaviza con un Gaussiano separable de `σ = 1.0` celda
(`0.25°`): los Andes tienen celdas de orografía muy distintas entre ERA5 e IFS HRES y el
suavizado evita picos aislados sin borrar ninguna estructura sinóptica.

El campo se interpola **en hora** entre los dos slots UTC que lo rodean (con vuelta
`18 → 0`) y **en mes** entre los centros `15 → 16` de los meses vecinos, así la
transición 31 de octubre → 1 de noviembre no tiene salto.

Salidas
-------
- `crudo_NNN_fhHHH.grib2` por paso (reanudable: se reutiliza si el tamaño coincide con
  `_length` y el marco GRIB está sano).
- `serie_anom_2t_c.npz` con `anom_c` (`(pasos, 721, 1440)` float32, °C), `lat`, `lon`,
  `horas`, `fecha_init` y `modelo`, en el orden que espera el render (lat 90→-90,
  lon -180→179.75).

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe descargar\\anomalia_2t_ecmwf.py
    .venv\\Scripts\\python.exe descargar\\anomalia_2t_ecmwf.py --fecha 2026-10-20 --ciclo 12 --hasta-hora 360 --paso 6
    .venv\\Scripts\\python.exe descargar\\anomalia_2t_ecmwf.py --forzar-climatologia
    .venv\\Scripts\\python.exe descargar\\anomalia_2t_ecmwf.py --help   # no toca la red
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import eccodes
import h5py
import numpy as np
import requests

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from rutas import DATOS, find_data_file  # noqa: E402

PARAM = "2t"
LEVTYPE = "sfc"
BASE = "https://data.ecmwf.int/forecasts/{ymd}/{ciclo}z"

MODELOS = ("ifs", "aifs-single")
RUTAS_MODELO = {
    "ifs": "ifs/0p25/oper",
    "aifs-single": "aifs-single/0p25/oper",
}

FECHA = "2026-10-20"                    # UTC: día de la corrida
CICLO = "12"                            # UTC: 00, 06, 12 o 18
HASTA_HORA = 360                        # último paso de pronóstico (15 días)
PASO_HORA = 6                           # horas entre pasos
HILOS = 8                               # descargas simultáneas

# Rejilla nativa del IFS 0.25°: 1440 x 721, de 90°N a 90°S y de 180°W a 179.75°E.
FILAS, COLUMNAS = 721, 1440
LAT_DESDE, LAT_HASTA = 90.0, -90.0
LON_DESDE, LON_HASTA = -180.0, 179.75

HORAS_UTC = (0, 6, 12, 18)              # slots diurnos de la climatología
KELVIN = 273.15
SIGMA_SUAVIZADO = 1.0                   # celdas (0.25°); Gaussiano separable 5x5

# Nombre fijo de la climatología cacheada (se reutiliza entre corridas).
CLIMATOLOGIA = DATOS / "climatologia_era5_t2m_mes_hora.npz"

# Caja de verificación de Sudamérica / Paraguay (oeste, este, sur, norte).
CAJA_SA = (-65.0, -45.0, -32.0, -18.0)

# Una sesión por hilo: reutiliza la conexión TLS entre pedidos.
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
    """URL del `.index` (JSONL) o del `.grib2` del paso `hora`."""
    if modelo not in RUTAS_MODELO:
        raise ValueError(f"modelo desconocido: {modelo!r}")
    nombre = f"{ymd}{ciclo}0000-{hora}h-oper-fc.{extension}"
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


def _entradas_2t(entradas: list[dict]) -> list[dict]:
    """Sólo los mensajes `2t`/`sfc` del índice (no los de presión o suelo)."""
    return [e for e in entradas
            if e.get("param") == PARAM and e.get("levtype") == LEVTYPE]


def rango_2t(ymd: str, ciclo: str, hora: int, modelo: str = "ifs") -> tuple[int, int]:
    """`(offset, length)` del mensaje `2t`/`sfc` en el `.grib2` de `hora`."""
    entradas = _entradas_2t(_leer_indice(
        url_archivo(ymd, ciclo, hora, "index", modelo=modelo)))
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


def _bajar_rango(url: str, offset: int, largo: int, reintentos: int = 4) -> bytes:
    """Baja exactamente `[offset, offset + largo)` de `url` y valida el marco GRIB."""
    espera = 2.0
    for intento in range(1, reintentos + 1):
        try:
            cabecera = {"Range": f"bytes={offset}-{offset + largo - 1}"}
            r = _sesion().get(url, headers=cabecera, timeout=120)
            r.raise_for_status()
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
    """Baja el mensaje `2t` de `hora` a `destino`; devuelve `(ruta, reutilizado)`."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    espera = 2.0
    for intento in range(1, reintentos + 1):
        try:
            offset, largo = rango_2t(ymd, ciclo, hora, modelo=modelo)
            if not forzar and _reutilizable(destino, largo):
                return destino, True
            contenido = _bajar_rango(url_archivo(ymd, ciclo, hora, "grib2", modelo=modelo),
                                     offset, largo)
            tmp = destino.with_suffix(destino.suffix + ".parcial")
            tmp.write_bytes(contenido)
            tmp.replace(destino)
            return destino, False
        except Exception as exc:                       # red, corte o respuesta rara
            if intento == reintentos:
                raise
            print(f"    reintento {intento}/{reintentos - 1} (paso {hora}h: {exc})",
                  flush=True)
            time.sleep(espera)
            espera *= 2
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


def _a_celsius(valores: np.ndarray, unidades: str, origen: str) -> np.ndarray:
    """Pasa los valores del mensaje a °C según la unidad que declara el GRIB."""
    unidades = unidades.strip()
    if unidades == "K":
        return valores - np.float32(KELVIN)
    if unidades in ("deg C", "C", "celsius"):
        return valores
    raise ValueError(f"{origen}: unidades desconocidas {unidades!r} para {PARAM}")


# `eccodes` comparte estado interno en la librería C: la decodificación se serializa
# aunque las descargas sigan en paralelo (decodificar un mensaje es cuestión de ms).
_ECCODES = threading.Lock()


def _decodificar_gid(gid, origen: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Decodifica un `gid` abierto y devuelve `(campo °C, lat, lon)` ya orientados."""
    nombre = str(eccodes.codes_get(gid, "shortName"))
    if nombre not in (PARAM, "t2m"):
        raise ValueError(f"{origen}: se esperaba {PARAM}, vino {nombre}")
    ni = int(eccodes.codes_get(gid, "Ni"))
    nj = int(eccodes.codes_get(gid, "Nj"))
    inc_i = float(eccodes.codes_get(gid, "iDirectionIncrementInDegrees"))
    inc_j = float(eccodes.codes_get(gid, "jDirectionIncrementInDegrees"))
    lat0 = float(eccodes.codes_get(gid, "latitudeOfFirstGridPointInDegrees"))
    lon0 = float(eccodes.codes_get(gid, "longitudeOfFirstGridPointInDegrees"))
    modo = int(eccodes.codes_get(gid, "scanningMode"))
    unidades = str(eccodes.codes_get(gid, "units"))
    valores = eccodes.codes_get_values(gid)

    if valores.size != ni * nj:
        raise ValueError(f"{origen}: {valores.size} valores para una rejilla "
                         f"{ni}x{nj}")

    # scanningMode (flag table 3.4): bit 0x20 APAGADO = los puntos consecutivos avanzan
    # en i (fila a fila, lo normal en una rejilla regular); encendido = avanzan en j.
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
    campo_c = np.ascontiguousarray(_a_celsius(campo.astype(np.float32), unidades,
                                              origen), dtype=np.float32)
    return campo_c, lat, lon


def leer_2t_c(ruta: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Decodifica el GRIB2 y devuelve `(campo °C, lat, lon)` ya orientados."""
    with ruta.open("rb") as f:
        gid = eccodes.codes_grib_new_from_file(f)
        if gid is None:
            raise ValueError(f"{ruta.name}: no contiene ningún mensaje GRIB")
        try:
            return _decodificar_gid(gid, ruta.name)
        finally:
            eccodes.codes_release(gid)


# ------------------------------------------------------------------ climatología ERA5
def _suavizar_gaussiano(campo: np.ndarray, sigma: float = SIGMA_SUAVIZADO) -> np.ndarray:
    """Gaussiano separable (σ en celdas); envuelve longitud y refleja en los polos.

    El objetivo es quitar picos de una sola celda que aparecen al restar dos orografías
    distintas (ERA5 vs IFS HRES) cerca de los Andes, sin tocar las estructuras
    sinópticas, que ocupan muchas celdas.
    """
    radio = max(1, int(np.ceil(3.0 * sigma)))
    x = np.arange(-radio, radio + 1, dtype=np.float32)
    nucleo = np.exp(-0.5 * (x / np.float32(sigma)) ** 2)
    nucleo /= nucleo.sum()

    # Longitud: roll (la rejilla es global y periódica).
    salida = np.zeros_like(campo, dtype=np.float32)
    for i, w in enumerate(nucleo):
        salida += np.float32(w) * np.roll(campo, i - radio, axis=1)

    # Latitud: padding de borde para no inventar valores fuera de los polos.
    acolchado = np.pad(salida, ((radio, radio), (0, 0)), mode="edge")
    final = np.zeros_like(salida, dtype=np.float32)
    for i, w in enumerate(nucleo):
        final += np.float32(w) * acolchado[i:i + campo.shape[0], :]
    return final


def _climatologia_desde_era5(ruta: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Construye `clim_c` (12, 4, 721, 1440) desde el NetCDF/HDF5 de ERA5.

    Lee el archivo **mes por mes** para que el pico de RAM quede en ~200 MB (un mes de
    `t2m` float32) en vez de cargar los 6 GB completos. Cada mes se promedia por hora
    UTC, se pasa a °C, se rota la longitud a -180..179.75 y se suaviza.
    """
    with h5py.File(ruta, "r") as f:
        for clave in ("valid_time", "latitude", "longitude", "t2m"):
            if clave not in f:
                raise SystemExit(f"{ruta.name}: falta la variable {clave!r}.")
        vt = np.asarray(f["valid_time"][:], dtype=np.int64)
        lat = np.asarray(f["latitude"][:], dtype=np.float32)
        lon = np.asarray(f["longitude"][:], dtype=np.float32)
        ds = f["t2m"]
        if ds.shape != (vt.size, lat.size, lon.size):
            raise SystemExit(f"{ruta.name}: t2m {ds.shape} no coincide con "
                             f"({vt.size}, {lat.size}, {lon.size}).")
        if (lat.size, lon.size) != (FILAS, COLUMNAS):
            raise SystemExit(f"{ruta.name}: rejilla {lon.size}x{lat.size}; se esperaba "
                             f"{COLUMNAS}x{FILAS} (0.25°).")
        if not (np.isclose(lat[0], LAT_DESDE) and np.isclose(lat[-1], LAT_HASTA)
                and np.isclose(lon[0], 0.0) and np.isclose(lon[-1], 359.75)):
            raise SystemExit(f"{ruta.name}: rejilla inesperada (lat {lat[0]}→{lat[-1]}, "
                             f"lon {lon[0]}→{lon[-1]}).")

        instantes = [datetime.fromtimestamp(int(t), timezone.utc) for t in vt]
        meses = np.array([d.month - 1 for d in instantes], dtype=np.int8)
        horas = np.array([d.hour for d in instantes], dtype=np.int8)
        indice_hora = {h: i for i, h in enumerate(HORAS_UTC)}

        clim = np.zeros((12, len(HORAS_UTC), FILAS, COLUMNAS), dtype=np.float32)
        for mes in range(12):
            seleccion = np.flatnonzero(meses == mes)
            if seleccion.size == 0:
                raise SystemExit(f"{ruta.name}: no hay datos para el mes {mes + 1}.")
            # Índices contiguos: h5py lee el bloque del mes de una sola pasada.
            bloque = np.asarray(ds[seleccion, :, :], dtype=np.float32)
            horas_mes = horas[seleccion]
            for hora, hi in indice_hora.items():
                sub = bloque[horas_mes == hora]
                if sub.size == 0:
                    raise SystemExit(f"{ruta.name}: no hay datos para "
                                     f"mes {mes + 1} hora {hora:02d} UTC.")
                media = sub.mean(axis=0, dtype=np.float64).astype(np.float32)
                # 0..359.75 -> -180..179.75 (calza 1:1 con ECMWF Open Data).
                media = np.roll(media - np.float32(KELVIN), -COLUMNAS // 2, axis=-1)
                clim[mes, hi] = _suavizar_gaussiano(media)
            print(f"  climatología mes {mes + 1:02d}/12: {seleccion.size} instantes",
                  flush=True)

    lon_roll = ((np.roll(lon, -COLUMNAS // 2) + 180.0) % 360.0
                - 180.0).astype(np.float32)
    lat = np.ascontiguousarray(lat, dtype=np.float32)
    lon_roll = np.ascontiguousarray(lon_roll, dtype=np.float32)
    _verificar_rejilla(lat, lon_roll)
    return clim, lat, lon_roll


def _cargar_climatologia(cache: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Lee y valida la climatología `.npz` cacheada."""
    with np.load(cache, allow_pickle=False) as d:
        if "clim_c" not in d.files:
            raise SystemExit(f"{cache.name}: no trae 'clim_c'.")
        clim = np.asarray(d["clim_c"], dtype=np.float32)
        lat = np.asarray(d["lat"], dtype=np.float32)
        lon = np.asarray(d["lon"], dtype=np.float32)
    if clim.shape != (12, len(HORAS_UTC), FILAS, COLUMNAS):
        raise SystemExit(f"{cache.name}: clim_c {clim.shape}; se esperaba "
                         f"{(12, len(HORAS_UTC), FILAS, COLUMNAS)}.")
    _verificar_rejilla(lat, lon)
    return clim, lat, lon


def construir_o_cargar_climatologia(args) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Devuelve `(clim_c, lat, lon)` de la caché o la construye desde ERA5."""
    if CLIMATOLOGIA.exists() and not args.forzar_climatologia:
        clim, lat, lon = _cargar_climatologia(CLIMATOLOGIA)
        print(f"Climatología en caché: {CLIMATOLOGIA} "
              f"({clim.shape[0]} meses x {clim.shape[1]} horas)")
        return clim, lat, lon

    ruta = find_data_file(DATOS, args.era5_nc)
    if ruta is None:
        raise SystemExit(
            "No encontré el NetCDF de ERA5. Pasalo con --era5-nc o dejalo en "
            f"{DATOS} / D:\\Users\\guill\\Desktop.")
    print(f"Construyendo climatología diurna desde {ruta} "
          f"({ruta.stat().st_size / 1e9:.2f} GB)...")
    inicio = time.time()
    clim, lat, lon = _climatologia_desde_era5(ruta)
    CLIMATOLOGIA.parent.mkdir(parents=True, exist_ok=True)
    tmp = CLIMATOLOGIA.with_suffix(CLIMATOLOGIA.suffix + ".parcial")
    with tmp.open("wb") as f:
        np.savez(f, clim_c=clim, lat=lat, lon=lon,
                 horas_utc=np.asarray(HORAS_UTC, dtype=np.int16))
    tmp.replace(CLIMATOLOGIA)
    print(f"Climatología guardada: {CLIMATOLOGIA} ({time.time() - inicio:.0f}s)")
    return clim, lat, lon


# ------------------------------------------------------------- interpolación temporal
def _pesos_hora(hora_utc: float) -> tuple[int, int, float]:
    """Slots `(i0, i1, w)` que rodean `hora_utc`, con vuelta 18 → 0."""
    h = float(hora_utc) % 24.0
    horas = np.asarray(HORAS_UTC, dtype=np.float64)
    if h >= horas[-1]:
        i0, i1 = len(HORAS_UTC) - 1, 0
        t0, t1 = horas[-1], 24.0
    else:
        i0 = max(0, int(np.searchsorted(horas, h, side="right") - 1))
        i1 = (i0 + 1) % len(HORAS_UTC)
        t0 = horas[i0]
        t1 = horas[i1] if i1 != 0 else 24.0
    w = 0.0 if t1 == t0 else (h - t0) / (t1 - t0)
    return i0, i1, float(np.clip(w, 0.0, 1.0))


def _pesos_mes(t: datetime) -> tuple[int, int, float]:
    """Meses `(m0, m1, w)` que rodean `t`, con centros en el 15 a las 12 UTC."""
    if t.tzinfo is not None:
        t = t.astimezone(timezone.utc).replace(tzinfo=None)
    centros: list[tuple[int, datetime]] = []
    for anio in (t.year - 1, t.year, t.year + 1):
        for mes in range(1, 13):
            centros.append((mes - 1, datetime(anio, mes, 15, 12)))
    centros.sort(key=lambda par: par[1])
    for (m0, c0), (m1, c1) in zip(centros, centros[1:]):
        if c0 <= t <= c1:
            w = (t - c0).total_seconds() / (c1 - c0).total_seconds()
            return m0, m1, float(np.clip(w, 0.0, 1.0))
    # Fuera de rango (no debería ocurrir con year-1..year+1): usar el centro más cercano.
    m, c = min(centros, key=lambda par: abs(par[1] - t))
    return m, m, 0.0


def climatologia_en(clim_c: np.ndarray, t_valid: datetime) -> np.ndarray:
    """Climatología (°C) interpolada linealmente en hora UTC y en mes.

    Primero interpola los dos slots UTC que rodean `t_valid` (0, 6, 12, 18, con vuelta
    18 → 0) y después mezcla los dos meses cuyos centros (día 15, 12 UTC) rodean la
    fecha. Así el 31 de octubre 18 UTC y el 1 de noviembre 00 UTC caen sobre la misma
    recta y la animación no salta en el cambio de mes.
    """
    hora = t_valid.hour + t_valid.minute / 60.0 + t_valid.second / 3600.0
    h0, h1, wh = _pesos_hora(hora)
    m0, m1, wm = _pesos_mes(t_valid)

    def campo_hora(mes: int) -> np.ndarray:
        a = np.asarray(clim_c[mes, h0], dtype=np.float32)
        if wh <= 0.0 or h1 == h0:
            return a
        b = np.asarray(clim_c[mes, h1], dtype=np.float32)
        return (a + (b - a) * np.float32(wh)).astype(np.float32)

    c0 = campo_hora(m0)
    if wm <= 0.0 or m1 == m0:
        return c0
    c1 = campo_hora(m1)
    return (c0 + (c1 - c0) * np.float32(wm)).astype(np.float32)


# ------------------------------------------------------------------------ reportes
def _caja(lat: np.ndarray, lon: np.ndarray,
          oeste: float, este: float, sur: float, norte: float):
    """Máscaras de filas y columnas de la caja lon/lat pedida."""
    return (lat <= norte) & (lat >= sur), (lon >= oeste) & (lon <= este)


def _rango_caja(campo: np.ndarray, lat: np.ndarray, lon: np.ndarray, caja,
                ) -> tuple[float, float]:
    """`(mínimo °C, máximo °C)` dentro de la caja."""
    filas, cols = _caja(lat, lon, *caja)
    sub = campo[np.ix_(filas, cols)]
    return float(np.nanmin(sub)), float(np.nanmax(sub))


def _tabla_resumen(serie: np.ndarray, horas: np.ndarray, lat: np.ndarray,
                   lon: np.ndarray) -> None:
    """Tabla compacta: cada 24 h más el último paso, con min/máx de la caja SA."""
    print("\nAnomalía de temperatura a 2 m (°C):")
    print("  paso   mín global   máx global   mín Sudamérica   máx Sudamérica")
    elegidos = [int(h) for h in horas if int(h) % 24 == 0]
    if int(horas[-1]) not in elegidos:
        elegidos.append(int(horas[-1]))
    for h in elegidos:
        i = int(np.where(horas == h)[0][0])
        min_g, max_g = float(serie[i].min()), float(serie[i].max())
        min_sa, max_sa = _rango_caja(serie[i], lat, lon, CAJA_SA)
        print(f"  {h:3d} h  {min_g:+8.1f}     {max_g:+8.1f}     "
              f"{min_sa:+8.1f}        {max_sa:+8.1f}")


def _reporte_final(serie: np.ndarray, horas: list[int], lat: np.ndarray,
                   lon: np.ndarray) -> None:
    """Tabla de resumen y rango SA del último paso."""
    _tabla_resumen(serie, np.asarray(horas, dtype=np.int32), lat, lon)
    min_sa, max_sa = _rango_caja(serie[-1], lat, lon, CAJA_SA)
    print(f"\nFH {horas[-1]}h: Sudamérica (lon {CAJA_SA[0]:g}..{CAJA_SA[1]:g}, "
          f"lat {CAJA_SA[2]:g}..{CAJA_SA[3]:g}) {min_sa:+.1f} °C a {max_sa:+.1f} °C")


def _comando_extra(args) -> str:
    extras = []
    if args.modelo != "ifs":
        extras.append(f"--modelo {args.modelo}")
    if args.out:
        extras.append(f'--out "{args.out}"')
    return (" " + " ".join(extras)) if extras else ""


def _comando_descarga(args) -> str:
    """El mismo comando, para reintentar sólo los pasos que faltan."""
    return (f".venv\\Scripts\\python.exe descargar\\anomalia_2t_ecmwf.py "
            f"--fecha {args.fecha} --ciclo {args.ciclo} --hasta-hora {args.hasta_hora} "
            f"--paso {args.paso} --hilos {args.hilos}") + _comando_extra(args)


def _comando_render(args) -> str:
    """El comando EXACTO de render que consume `serie_anom_2t_c.npz`."""
    return (f".venv\\Scripts\\python.exe cuadros\\cuadros_anomalia_2t.py "
            f"--fecha {args.fecha} --ciclo {args.ciclo} --hasta-hora {args.hasta_hora} "
            f"--paso {args.paso}") + _comando_extra(args)


def _dir_salida(args, ciclo: str) -> Path:
    """Carpeta de crudos por defecto."""
    if args.out:
        return Path(args.out)
    return DATOS / f"crudos_anom2t_{args.modelo}_{args.fecha}_{ciclo}z"


def _npz_completo(cache: Path, horas: list[int]):
    """Lee `serie_anom_2t_c.npz` si ya cubre exactamente los pasos pedidos; si no, None."""
    if not cache.exists():
        return None
    try:
        with np.load(cache, allow_pickle=False) as d:
            if "anom_c" not in d.files or "horas" not in d.files:
                return None
            anom = np.asarray(d["anom_c"], dtype=np.float32)
            guardadas = [int(h) for h in np.asarray(d["horas"]).ravel()]
            lat = np.asarray(d["lat"], dtype=np.float32)
            lon = np.asarray(d["lon"], dtype=np.float32)
    except Exception:
        return None
    if guardadas != horas or anom.shape != (len(horas), FILAS, COLUMNAS):
        return None
    _verificar_rejilla(lat, lon)
    return anom, lat, lon


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Descarga `2t` de ECMWF (IFS o AIFS-SINGLE) 0.25° por HTTP Range, "
                    "calcula la anomalía contra la climatología diurna de ERA5 y deja "
                    "una serie consolidada en °C.")
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
    ap.add_argument("--hilos", type=int, default=HILOS,
                    help=f"descargas simultáneas (por defecto {HILOS})")
    ap.add_argument("--era5-nc", help="NetCDF/HDF5 de ERA5 con `t2m` (por defecto se "
                                      "busca con comun.rutas.find_data_file)")
    ap.add_argument("--forzar-climatologia", action="store_true",
                    help="reconstruye la climatología aunque el .npz ya exista")
    ap.add_argument("--forzar", action="store_true",
                    help="vuelve a bajar los pasos aunque ya estén completos")
    ap.add_argument("--out", help="carpeta de salida (por defecto, "
                                  "DATOS/crudos_anom2t_<modelo>_<fecha>_<ciclo>z)")
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
    cache = salida / "serie_anom_2t_c.npz"

    if not args.forzar:
        previo = _npz_completo(cache, horas)
        if previo is not None:
            serie, lat, lon = previo
            print(f"Serie ya completa: {cache} ({serie.shape[0]}, {FILAS}, "
                  f"{COLUMNAS})")
            _reporte_final(serie, horas, lat, lon)
            print("Ahora renderizá con: " + _comando_render(args))
            return 0

    clim_c, _, _ = construir_o_cargar_climatologia(args)

    print(f"Temperatura a 2 m {args.modelo.upper()} | {args.fecha} {ciclo}z | "
          f"{len(horas)} pasos ({horas[0]}h..{horas[-1]}h cada {args.paso} h)")
    print(f"fuente: {url_archivo(ymd, ciclo, horas[0], 'index', modelo=args.modelo)}")
    print(f"crudos en {salida} | {args.hilos} hilos")

    inicio = time.time()
    reutilizados = 0
    fallidos: list[int] = []
    with ThreadPoolExecutor(max_workers=args.hilos) as pool:
        futuros = {
            pool.submit(descargar_paso, ymd, ciclo, h,
                        salida / f"crudo_{i + 1:03d}_fh{h:03d}.grib2",
                        args.forzar, 4, args.modelo): h
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
          f"({reutilizados} reutilizados). Calculando anomalías...")

    # t_init en UTC con zona, para que `climatologia_en` compare sin ambigüedad.
    t_init = datetime.fromisoformat(f"{args.fecha}T{ciclo}:00:00+00:00")
    inicio_dec = time.time()
    serie = np.empty((len(horas), FILAS, COLUMNAS), dtype=np.float32)
    lat = lon = None
    for i, h in enumerate(horas):
        ruta = salida / f"crudo_{i + 1:03d}_fh{h:03d}.grib2"
        campo_c, lat, lon = leer_2t_c(ruta)
        clim_t = climatologia_en(clim_c, t_init + timedelta(hours=h))
        serie[i] = campo_c - clim_t
        if (i + 1) % 10 == 0 or i + 1 == len(horas):
            print(f"  {i + 1}/{len(horas)} pasos consolidados "
                  f"({time.time() - inicio_dec:.0f}s)", flush=True)

    _reporte_final(serie, horas, lat, lon)

    tmp = cache.with_suffix(cache.suffix + ".parcial")
    with tmp.open("wb") as f:
        np.savez(f, anom_c=serie, lat=lat, lon=lon,
                 horas=np.asarray(horas, dtype=np.int32),
                 fecha_init=f"{args.fecha}T{ciclo}:00Z", modelo=args.modelo)
    tmp.replace(cache)
    print(f"\nSerie consolidada: {cache} ({serie.shape[0]}, {FILAS}, {COLUMNAS}) "
          f"float32 | horas {horas[0]}..{horas[-1]} cada {args.paso} h")
    print("Ahora renderizá con: " + _comando_render(args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
