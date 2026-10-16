"""Descarga cuadros GeoColor (GOES-East) desde NASA GIBS.

GeoColor **no es una banda cruda**: es un producto RGB ya mezclado por NOAA/CIRA
(color real de día; IR multiespectral + luces de ciudad de noche). Por eso no se lee con
xarray como los `.nc` de los GOES ABI: se pide ya rasterizado, en un JPEG, contra un
servicio de teselas.

Fuente (Worldview Snapshots API — un GET por cuadro):

    https://wvs.earthdata.nasa.gov/api/v1/snapshot
      ?REQUEST=GetSnapshot&TIME=<ISO8601>Z&BBOX=<o>,<s>,<e>,<n>&CRS=EPSG:4326
      &LAYERS=GOES-East_ABI_GeoColor&FORMAT=image/jpeg&WIDTH=<px>&HEIGHT=<alto>

Deja los cuadros crudos como `crudo_NNN.jpg` en `frames_<etiqueta>/`. El render (recorte,
rótulos y guardado del PNG) vive aparte, en `cuadros/cuadros_geocolor.py`; sólo hay que
pedir las dos cosas con los mismos `--desde/--n/--px/--globo`.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe descargar\\geocolor.py --desde 2026-10-15T20:00 --n 24 --px 480
    .venv\\Scripts\\python.exe descargar\\geocolor.py --globo --desde 2026-10-04T00:00 --n 432 --px 2048 --hilos 32
    .venv\\Scripts\\python.exe descargar\\geocolor.py --help   # no toca la red
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from rutas import SALIDAS  # noqa: E402

API = "https://wvs.earthdata.nasa.gov/api/v1/snapshot"
CAPA = "GOES-East_ABI_GeoColor"

# Sudamérica + Caribe: Paraguay entra cómodo y el terminador barre el dominio entero.
BBOX = (-85.0, -40.0, -35.0, 15.0)      # oeste, sur, este, norte
# Para el globo hay que cubrir el hemisferio visible centrado en Paraguay: si la caja
# es más chica, el limbo queda recortado y el globo sale incompleto.
BBOX_GLOBO = (-160.0, -80.0, 15.0, 80.0)
GLOBO_LON, GLOBO_LAT = -58.0, -23.0     # mismo centro por defecto del resto del repo

DESDE = "2026-10-15T20:00"              # UTC
N = 24
PASO_MIN = 10
PX = 480


def url_cuadro(t: datetime, bbox, ancho: int, alto: int) -> str:
    """URL del snapshot para el instante `t` (se pide en JPEG: pesa menos que PNG)."""
    momento = t.strftime("%Y-%m-%dT%H:%M:%SZ")
    o, s, e, n = bbox
    return (f"{API}?REQUEST=GetSnapshot&TIME={momento}"
            f"&BBOX={s},{o},{n},{e}&CRS=EPSG:4326"
            f"&LAYERS={CAPA}&FORMAT=image/jpeg&WIDTH={ancho}&HEIGHT={alto}")


# Una sesión por hilo: reutiliza la conexión TLS entre pedidos. Abrir una conexión nueva
# por cuadro obliga a un handshake por archivo y se come el ancho de banda en latencia.
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


def descargar_cuadro(t: datetime, bbox, ancho: int, alto: int, destino: Path,
                     reintentos: int = 4) -> Path:
    """Baja el cuadro a `destino`; lo reutiliza si ya está (reanudable)."""
    if destino.exists() and destino.stat().st_size > 5_000:
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    url = url_cuadro(t, bbox, ancho, alto)
    espera = 2.0
    for intento in range(1, reintentos + 1):
        try:
            r = _sesion().get(url, timeout=90)
            r.raise_for_status()
            if len(r.content) < 5_000:
                raise ValueError(f"respuesta demasiado chica ({len(r.content)} B)")
            tmp = destino.with_suffix(destino.suffix + ".parcial")
            tmp.write_bytes(r.content)
            tmp.replace(destino)
            return destino
        except Exception as exc:                       # red o corte del servicio
            if intento == reintentos:
                raise
            print(f"    reintento {intento}/{reintentos - 1} ({exc})", flush=True)
            time.sleep(espera)
            espera *= 2
    return destino


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Descarga cuadros GeoColor (GOES-East) desde NASA GIBS.")
    ap.add_argument("--desde", default=DESDE,
                    help=f"primer cuadro, UTC (por defecto {DESDE})")
    ap.add_argument("--n", type=int, default=N, help=f"cantidad de cuadros (por defecto {N})")
    ap.add_argument("--paso", type=int, default=PASO_MIN,
                    help=f"minutos entre cuadros (por defecto {PASO_MIN})")
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("O", "S", "E", "N"),
                    help="caja lon/lat de origen (por defecto, Sudamérica; con --globo, "
                         "la que cubre el hemisferio visible)")
    ap.add_argument("--globo", action="store_true",
                    help="origen que cubre el hemisferio visible (para render en globo)")
    ap.add_argument("--centro", nargs=2, type=float, metavar=("LON", "LAT"),
                    default=[GLOBO_LON, GLOBO_LAT],
                    help=f"centro del globo (por defecto {GLOBO_LON} {GLOBO_LAT})")
    ap.add_argument("--px", type=int, default=PX,
                    help=f"ancho de cada cuadro en píxeles (por defecto {PX})")
    ap.add_argument("--alto", type=int, help="alto en píxeles (por defecto, según la caja)")
    ap.add_argument("--src-px", type=int,
                    help="ancho de la imagen de origen; por defecto, según el modo")
    ap.add_argument("--hilos", type=int, default=16,
                    help="descargas simultáneas (por defecto 16, para saturar el enlace; "
                         "bajalo si el servicio devuelve 429)")
    ap.add_argument("--out", help="carpeta de salida (por defecto, comun.rutas.SALIDAS)")
    args = ap.parse_args(argv)

    if args.bbox is None:
        args.bbox = list(BBOX_GLOBO if args.globo else BBOX)
    o, s, e, n = args.bbox
    if not (o < e and s < n):
        raise SystemExit(f"caja inválida: {args.bbox}")

    # El origen se pide con la proporción de la caja. En modo globo se pide más grande que
    # la salida: el warping a Orthographic remuestrea y conviene tener de dónde tirar.
    src_px = args.src_px or (max(1200, args.px * 2) if args.globo else args.px)
    src_alto = args.alto or round(src_px * (n - s) / (e - o))

    t0 = datetime.fromisoformat(args.desde)
    salida = Path(args.out) if args.out else SALIDAS
    vista = "globo" if args.globo else "plano"
    etiqueta = f"geocolor_{vista}_{t0:%Y-%m-%dT%H%M}_{args.n}f_{args.px}px"
    frames_dir = salida / f"frames_{etiqueta}"
    frames_dir.mkdir(parents=True, exist_ok=True)

    print(f"GeoColor {vista} | {args.n} cuadros desde {t0:%Y-%m-%d %H:%M} UTC | "
          f"paso {args.paso} min | origen {src_px}x{src_alto} px")
    print(f"caja {o},{s},{e},{n} | frames en {frames_dir}")

    tiempos = [t0 + timedelta(minutes=args.paso * i) for i in range(args.n)]
    inicio = time.time()

    # Cada cuadro es un GET independiente: se bajan en paralelo. Si el servicio devuelve
    # 429, bajá --hilos.
    hechos = 0
    fallidos = 0
    with ThreadPoolExecutor(max_workers=args.hilos) as pool:
        futuros = {
            pool.submit(descargar_cuadro, t, (o, s, e, n), src_px, src_alto,
                        frames_dir / f"crudo_{i:03d}.jpg"): (i, t)
            for i, t in enumerate(tiempos, 1)
        }
        for fut in as_completed(futuros):
            i, t = futuros[fut]
            try:
                fut.result()
            except Exception as exc:
                fallidos += 1
                print(f"[{i}/{args.n}] {t:%Y-%m-%d %H:%M} UTC  ERROR: {exc}", flush=True)
                continue
            hechos += 1
            print(f"  {hechos}/{args.n} listos (errores {fallidos}) {time.time() - inicio:.0f}s",
                  flush=True)

    print(f"{hechos} cuadros listos en {time.time() - inicio:.0f}s")
    if fallidos:
        raise SystemExit(f"Faltan {fallidos} cuadros. Volvé a correr el mismo comando: "
                         "los que ya están se reutilizan y sólo se reintentan los que faltan.")
    print("Ahora renderizá con: "
          f".venv\\Scripts\\python.exe cuadros\\cuadros_geocolor.py "
          f"--desde {t0:%Y-%m-%dT%H:%M} --n {args.n} --px {args.px}"
          + (" --globo" if args.globo else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
