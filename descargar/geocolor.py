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
import io
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import requests
from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from rutas import SALIDAS  # noqa: E402

API = "https://wvs.earthdata.nasa.gov/api/v1/snapshot"

# Cada satélite tiene su capa ya mezclada por NOAA/CIRA: el producto es el mismo,
# la fuente cambia. Antes se pedía siempre la de GOES-East aunque se eligiera G18.
CAPAS = {
    "G19": "GOES-East_ABI_GeoColor",
    "G16": "GOES-East_ABI_GeoColor",
    "G18": "GOES-West_ABI_GeoColor",
}
CAPA = CAPAS["G19"]
# El renderizador de GIBS puede colgarse: mejor cortar a los 30 s que esperar 90.
TIMEOUT = 30

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


def url_cuadro(t: datetime, bbox, ancho: int, alto: int, capa: str = CAPA) -> str:
    """URL del snapshot para el instante `t` (se pide en JPEG: pesa menos que PNG)."""
    momento = t.strftime("%Y-%m-%dT%H:%M:%SZ")
    o, s, e, n = bbox
    return (f"{API}?REQUEST=GetSnapshot&TIME={momento}"
            f"&BBOX={s},{o},{n},{e}&CRS=EPSG:4326"
            f"&LAYERS={capa}&FORMAT=image/jpeg&WIDTH={ancho}&HEIGHT={alto}")


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


def valida(datos: bytes) -> bool:
    """True si la respuesta trae imagen de verdad.

    GIBS contesta `200` con una imagen negra cuando el instante no tiene gránulo
    o cuando el servicio está a medio recuperar. Mirar sólo el status y el peso
    deja cuadros negros que después el render publica como si fueran buenos.
    """
    if len(datos) < 5_000:
        return False
    try:
        with Image.open(io.BytesIO(datos)) as imagen:
            pixeles = np.asarray(imagen.convert("RGB"), dtype=np.uint8)
    except Exception:
        return False
    return int(pixeles.max()) > 8


def caja_globo(centro_lon: float) -> list[float]:
    """Caja que cubre el hemisferio visible del satélite, centrada en él."""
    return [centro_lon - 90.0, -80.0, centro_lon + 90.0, 80.0]


def partes(bbox, ancho: int) -> list[tuple[tuple[float, float, float, float], int]]:
    """La caja partida si cruza el antimeridiano (caso GOES-West).

    GIBS rechaza longitudes fuera de -180..180, así que el hemisferio de G18
    (centrado en -137) se pide en dos mitades y se pega después.
    """
    o, s, e, n = bbox
    if o >= -180.0:
        return [((o, s, e, n), ancho)]
    corte = o + 360.0
    fraccion = (180.0 - corte) / (e - o)
    ancho1 = max(1, min(ancho - 1, round(ancho * fraccion)))
    return [((corte, s, 180.0, n), ancho1), ((-180.0, s, e, n), ancho - ancho1)]


def _bajar(t: datetime, bbox, ancho: int, alto: int, capa: str) -> bytes:
    """Baja el cuadro (una o dos mitades) y devuelve el JPEG ya armado."""
    crudos: list[bytes] = []
    imagenes: list[Image.Image] = []
    for caja, ancho_parte in partes(bbox, ancho):
        r = _sesion().get(url_cuadro(t, caja, ancho_parte, alto, capa), timeout=TIMEOUT)
        r.raise_for_status()
        if not valida(r.content):
            raise ValueError(f"cuadro sin dato ({len(r.content)} B)")
        crudos.append(r.content)
        imagenes.append(Image.open(io.BytesIO(r.content)).convert("RGB"))
    if len(crudos) == 1:
        return crudos[0]
    lienzo = Image.new("RGB", (sum(im.width for im in imagenes), imagenes[0].height))
    x = 0
    for im in imagenes:
        lienzo.paste(im, (x, 0))
        x += im.width
    buf = io.BytesIO()
    lienzo.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def descargar_cuadro(t: datetime, bbox, ancho: int, alto: int, destino: Path,
                     capa: str = CAPA, reintentos: int = 3) -> Path:
    """Baja el cuadro a `destino`; lo reutiliza si ya está (reanudable)."""
    if destino.exists() and destino.stat().st_size > 5_000:
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    espera = 2.0
    for intento in range(1, reintentos + 1):
        try:
            datos = _bajar(t, bbox, ancho, alto, capa)
            tmp = destino.with_suffix(destino.suffix + ".parcial")
            tmp.write_bytes(datos)
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
    ap.add_argument("--hilos", type=int, default=6,
                    help="descargas simultáneas (por defecto 6: con más, GIBS empieza a "
                         "devolver cuadros negros)")
    ap.add_argument("--sat", default="G19",
                    help="satélite: G19/G16 = GOES-East, G18 = GOES-West (por defecto G19)")
    ap.add_argument("--out", help="carpeta de salida (por defecto, comun.rutas.SALIDAS)")
    args = ap.parse_args(argv)

    sat = args.sat.upper()
    if sat not in CAPAS:
        raise SystemExit(f"--sat inválido: {args.sat} (se espera G16, G18 o G19).")
    capa = CAPAS[sat]

    if args.bbox is None:
        # El globo se pide centrado en el satélite: cada uno ve su hemisferio.
        args.bbox = caja_globo(args.centro[0]) if args.globo else list(BBOX)
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
    etiqueta = f"geocolor_{vista}_{sat}_{t0:%Y-%m-%dT%H%M}_{args.n}f_{args.px}px"
    frames_dir = salida / f"frames_{etiqueta}"
    frames_dir.mkdir(parents=True, exist_ok=True)

    print(f"GeoColor {vista} | {sat} ({capa}) | {args.n} cuadros desde "
          f"{t0:%Y-%m-%d %H:%M} UTC | paso {args.paso} min | "
          f"origen {src_px}x{src_alto} px")
    print(f"caja {o},{s},{e},{n} | frames en {frames_dir}")

    tiempos = [t0 + timedelta(minutes=args.paso * i) for i in range(args.n)]
    inicio = time.time()

    # Cada cuadro es un GET independiente: se bajan en paralelo. Si el servicio devuelve
    # 429, bajá --hilos.
    hechos = 0
    pendientes: list[tuple[int, datetime]] = []
    with ThreadPoolExecutor(max_workers=args.hilos) as pool:
        futuros = {
            pool.submit(descargar_cuadro, t, (o, s, e, n), src_px, src_alto,
                        frames_dir / f"crudo_{i:03d}.jpg", capa): (i, t)
            for i, t in enumerate(tiempos, 1)
        }
        for fut in as_completed(futuros):
            i, t = futuros[fut]
            try:
                fut.result()
            except Exception as exc:
                pendientes.append((i, t))
                print(f"[{i}/{args.n}] {t:%Y-%m-%d %H:%M} UTC  ERROR: {exc}", flush=True)
                continue
            hechos += 1
            print(f"  {hechos}/{args.n} listos (errores {len(pendientes)}) "
                  f"{time.time() - inicio:.0f}s", flush=True)

    # Los huecos de GIBS son de minutos: una segunda pasada, de a uno, los recupera.
    if pendientes:
        print(f"Segunda pasada: {len(pendientes)} cuadro(s) sin dato", flush=True)
        time.sleep(3)
        for i, t in pendientes:
            try:
                descargar_cuadro(t, (o, s, e, n), src_px, src_alto,
                                 frames_dir / f"crudo_{i:03d}.jpg", capa)
                hechos += 1
            except Exception as exc:
                print(f"  [{i}] sigue sin dato: {exc}", flush=True)
        pendientes = [(i, t) for i, t in pendientes
                      if not (frames_dir / f"crudo_{i:03d}.jpg").exists()]

    print(f"{hechos} cuadros listos en {time.time() - inicio:.0f}s")
    if pendientes:
        raise SystemExit(
            f"Faltan {len(pendientes)} cuadro(s) que GIBS no tiene publicados: "
            f"{[i for i, _ in pendientes][:12]}. Se puede renderizar el resto igual: "
            "volvé a correr y los que ya están se reutilizan.")
    print("Ahora renderizá con: "
          f".venv\\Scripts\\python.exe cuadros\\cuadros_geocolor.py "
          f"--desde {t0:%Y-%m-%dT%H:%M} --n {args.n} --px {args.px}"
          + (" --globo" if args.globo else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
