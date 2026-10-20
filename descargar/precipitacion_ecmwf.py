"""Descarga la precipitación total acumulada (`tp`) de ECMWF IFS 0.25° para una corrida.

Producto: **Total Precipitation** acumulada desde el inicio de la corrida, en metros de
agua equivalente. La fuente es el **ECMWF Open Data** del determinístico IFS a 0.25°
(`oper`), que publica por cada paso de pronóstico dos archivos:

    https://data.ecmwf.int/forecasts/<yyyymmdd>/<ciclo>z/ifs/0p25/oper/
        <yyyymmdd><ciclo>0000-<paso>h-oper-fc.index    (JSON Lines: un mensaje por línea)
        <yyyymmdd><ciclo>0000-<paso>h-oper-fc.grib2    (todos los campos del paso)

Bajar el `.grib2` completo de cada paso son ~98 MB (≈4,8 GB para 49 pasos). Como el
`.index` publica `_offset` y `_length` de cada mensaje, acá se pide **sólo el rango de
bytes** de `param="tp", levtype="sfc"` (~220 B a ~0.5 MB por paso, ≈20 MB en total).

Los GRIB2 de ECMWF usan `dataRepresentationTemplateNumber = 42` (empaquetado CCSDS/AEC),
que las herramientas viejas de GRIB no decodifican. Por eso el lector es **eccodes** (el
paquete de PyPI trae la librería compilada; verificado con los pasos 0h y 144h de esta
corrida). El paso 0h llega como campo constante de 224 B y decodifica a 0 mm.

Los crudos quedan como `crudo_NNN_fhHHH.grib2` (NNN arranca en 1, convención `crudo_NNN`
del repo; `HHH` es el paso en horas) y el resultado consolidado en `serie_tp_mm.npz`, ya
en **mm** y con la rejilla en el orden que espera el render (lat 90→-90, lon -180→179.75),
para que `cuadros/cuadros_precipitacion.py` no vuelva a decodificar GRIB.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe descargar\\precipitacion_ecmwf.py
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
BASE = "https://data.ecmwf.int/forecasts/{ymd}/{ciclo}z/ifs/0p25/oper"

FECHA = "2026-10-20"                    # UTC: día de la corrida
CICLO = "06"                            # UTC: 00, 06, 12 o 18
HASTA_HORA = 144                        # último paso de pronóstico (6 días)
PASO_HORA = 3                           # horas entre pasos
HILOS = 6                               # descargas simultáneas

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


def url_archivo(ymd: str, ciclo: str, hora: int, extension: str) -> str:
    """URL del `.index` (JSONL) o del `.grib2` del paso `hora`."""
    nombre = f"{ymd}{ciclo}0000-{hora}h-oper-fc.{extension}"
    return f"{BASE.format(ymd=ymd, ciclo=ciclo)}/{nombre}"


def pasos(hasta_hora: int, paso_hora: int) -> list[int]:
    """Pasos de pronóstico `0, paso, 2*paso, ..., hasta_hora`."""
    if paso_hora <= 0:
        raise SystemExit(f"--paso debe ser positivo (recibí {paso_hora}).")
    if hasta_hora < 0:
        raise SystemExit(f"--hasta-hora debe ser >= 0 (recibí {hasta_hora}).")
    return list(range(0, hasta_hora + 1, paso_hora))


def rango_tp(ymd: str, ciclo: str, hora: int) -> tuple[int, int]:
    """`(offset, length)` del mensaje `tp`/`sfc` en el `.grib2` de `hora`.

    El índice es JSON Lines con un mensaje por línea, e incluye **todos** los campos del
    paso (superficie, niveles de presión, suelo...). Se busca la entrada exacta por
    `param` y `levtype`: pedir `tp` sin filtrar `levtype` también agarraría el de otros
    niveles.
    """
    r = _sesion().get(url_archivo(ymd, ciclo, hora, "index"), timeout=90)
    r.raise_for_status()
    for linea in r.text.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        try:
            entrada = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if entrada.get("param") == PARAM and entrada.get("levtype") == LEVTYPE:
            return int(entrada["_offset"]), int(entrada["_length"])
    raise LookupError(f"{ymd} {ciclo}z {hora}h: el índice no trae {PARAM}/{LEVTYPE}")


def _reutilizable(destino: Path, largo: int) -> bool:
    """True si `destino` ya es el mensaje completo (mismo tamaño y marco GRIB válido)."""
    if not destino.exists() or destino.stat().st_size != largo:
        return False
    with destino.open("rb") as f:
        cabecera = f.read(4)
        f.seek(-4, 2)
        cola = f.read(4)
    return cabecera == b"GRIB" and cola == b"7777"


def descargar_paso(ymd: str, ciclo: str, hora: int, destino: Path, forzar: bool = False,
                   reintentos: int = 4) -> tuple[Path, bool]:
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
            # el medio de los 49 pasos conviene reintentar este en vez de abortar.
            offset, largo = rango_tp(ymd, ciclo, hora)
            if not forzar and _reutilizable(destino, largo):
                return destino, True
            cabecera = {"Range": f"bytes={offset}-{offset + largo - 1}"}
            r = _sesion().get(url_archivo(ymd, ciclo, hora, "grib2"),
                              headers=cabecera, timeout=120)
            r.raise_for_status()
            # El servidor responde 206 con exactamente el rango pedido. Cualquier otro
            # tamaño es una respuesta completa (Range ignorado) o un corte: no se guarda.
            if len(r.content) != largo:
                raise ValueError(f"rango incompleto ({len(r.content)} B de {largo})")
            if r.content[:4] != b"GRIB" or r.content[-4:] != b"7777":
                raise ValueError("el rango no es un mensaje GRIB2 completo")
            tmp = destino.with_suffix(destino.suffix + ".parcial")
            tmp.write_bytes(r.content)
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


def leer_tp_mm(ruta: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Decodifica el GRIB2 y devuelve `(campo mm, lat, lon)` ya orientados.

    El campo sale `float32` (721, 1440) en **mm**, con lat 90→-90 y lon -180→179.75.
    `tp` viene acumulado desde el inicio de la corrida en metros: `mm = tp * 1000`, con
    el piso en 0 para no arrastrar negativos de redondeo del empaquetado.
    """
    with ruta.open("rb") as f:
        gid = eccodes.codes_grib_new_from_file(f)
        if gid is None:
            raise ValueError(f"{ruta.name}: no contiene ningún mensaje GRIB")
        try:
            nombre = eccodes.codes_get(gid, "shortName")
            if nombre != PARAM:
                raise ValueError(f"{ruta.name}: se esperaba {PARAM}, vino {nombre}")
            ni = int(eccodes.codes_get(gid, "Ni"))
            nj = int(eccodes.codes_get(gid, "Nj"))
            inc_i = float(eccodes.codes_get(gid, "iDirectionIncrementInDegrees"))
            inc_j = float(eccodes.codes_get(gid, "jDirectionIncrementInDegrees"))
            lat0 = float(eccodes.codes_get(gid, "latitudeOfFirstGridPointInDegrees"))
            lon0 = float(eccodes.codes_get(gid, "longitudeOfFirstGridPointInDegrees"))
            modo = int(eccodes.codes_get(gid, "scanningMode"))
            valores = eccodes.codes_get_values(gid)
        finally:
            eccodes.codes_release(gid)

    if valores.size != ni * nj:
        raise ValueError(f"{ruta.name}: {valores.size} valores para una rejilla "
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

    # El IFS publica la grilla empezando en 180°E: las longitudes ya salen -180..179.75,
    # pero se ordenan igual por si el origen viniera con otro barrido.
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
    campo_mm = np.maximum(campo.astype(np.float32) * 1000.0, 0.0).astype(np.float32)
    return campo_mm, lat, lon


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


def _comando_extra(args) -> str:
    return f' --out "{args.out}"' if args.out else ""


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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Descarga la precipitación total acumulada (`tp`) de ECMWF IFS "
                    "0.25° por HTTP Range y deja una serie consolidada en mm.")
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
                                  "DATOS/crudos_precip_ecmwf_<fecha>_<ciclo>z)")
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
    salida = Path(args.out) if args.out else \
        DATOS / f"crudos_precip_ecmwf_{args.fecha}_{ciclo}z"
    salida.mkdir(parents=True, exist_ok=True)

    print(f"Precipitación total ECMWF IFS 0.25° | {args.fecha} {ciclo}z | "
          f"{len(horas)} pasos ({horas[0]}h..{horas[-1]}h cada {args.paso} h)")
    print(f"fuente: {BASE.format(ymd=ymd, ciclo=ciclo)}/")
    print(f"crudos en {salida}")

    inicio = time.time()
    reutilizados = 0
    fallidos: list[int] = []
    with ThreadPoolExecutor(max_workers=args.hilos) as pool:
        futuros = {
            pool.submit(descargar_paso, ymd, ciclo, h,
                        salida / f"crudo_{i + 1:03d}_fh{h:03d}.grib2",
                        args.forzar): h
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

    print(f"{len(horas)} GRIB2 listos en {time.time() - inicio:.0f}s "
          f"({reutilizados} reutilizados). Decodificando...")

    inicio_dec = time.time()
    serie = np.empty((len(horas), FILAS, COLUMNAS), dtype=np.float32)
    lat = lon = None
    for i, h in enumerate(horas):
        ruta = salida / f"crudo_{i + 1:03d}_fh{h:03d}.grib2"
        serie[i], lat, lon = leer_tp_mm(ruta)
        if (i + 1) % 10 == 0 or i + 1 == len(horas):
            print(f"  {i + 1}/{len(horas)} pasos decodificados "
                  f"({time.time() - inicio_dec:.0f}s)", flush=True)

    # El acumulado desde el inicio de la corrida tiene que arrancar en 0. Si no, el
    # recorte por bytes o la orientación de la rejilla están mal: mejor abortar acá que
    # guardar una serie silenciosamente corrida.
    if horas[0] == 0 and float(serie[0].max()) > 1e-6:
        raise SystemExit(f"El paso 0h no es cero ({float(serie[0].max()):.3f} mm): "
                         "revisá el rango descargado y la decodificación.")

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

    cache = salida / "serie_tp_mm.npz"
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
