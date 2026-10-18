"""Descarga cuadros diarios de True Color (Corrected Reflectance) desde NASA GIBS.

MODIS y VIIRS True Color no son una banda cruda: son la **composición de color real**
del día, con la reflectancia corregida de los canales visibles. GIBS la sirve ya
rasterizada, así que —igual que GeoColor y MUR— se pide un JPEG por cuadro contra la
Worldview Snapshots API, sin `.nc` que leer.

Fuente:

    https://wvs.earthdata.nasa.gov/api/v1/snapshot
      ?REQUEST=GetSnapshot&TIME=<AAAA-MM-DD>&BBOX=<sur>,<oeste>,<norte>,<este>
      &CRS=EPSG:4326&LAYERS=<capa>&FORMAT=image/jpeg&WIDTH=<ancho>&HEIGHT=<alto>

A diferencia de GeoColor (que es un disco GOES), estas capas son **globales**, y a
diferencia de MUR (semanal), la cadencia es **diaria** (`P1D`, composición del día): para
estas capas diarias el `TIME` va como fecha sola `AAAA-MM-DD` (verificado contra el
servicio). La serie y la etiqueta de la carpeta salen de `comun/series.py`, para que el
render (`cuadros/cuadros_truecolor.py`) busque exactamente lo mismo. Deja los crudos como
`crudo_NNN.jpg` en `frames_truecolor_<sensor>_globo_<t0>_<n>f_<px>px/`.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe descargar\\truecolor.py --desde 2024-07-11 --hasta 2024-10-30 --paso 1 --px 2711
    .venv\\Scripts\\python.exe descargar\\truecolor.py --help   # no toca la red
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import requests
from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from rutas import SALIDAS  # noqa: E402
from series import etiqueta_frames, serie_fechas  # noqa: E402

API = "https://wvs.earthdata.nasa.gov/api/v1/snapshot"

# Capa GIBS -> nombre corto. El MISMO dict vive en `cuadros/cuadros_truecolor.py`: el repo
# duplica las constantes entre el par descarga/render (lo compartido de verdad, como la
# serie de fechas y la etiqueta, está en `comun/series.py`). El nombre corto tiene que
# coincidir en los dos lados: es lo que hace que descarga y render apunten a la misma
# carpeta de frames.
#
# No se ofrece `VIIRS_SNPP_CorrectedReflectance_TrueColor`: tiene un hueco de archivo
# (2024-07-12..15 devuelve un placeholder), justo dentro de la ventana de los incendios.
#
# El default es VIIRS NOAA-20, NO MODIS: las composiciones diarias de MODIS (Terra y Aqua)
# dejan cuñas de barrido (swaths) cerca del ecuador —el ancho de barrido de MODIS es menor
# que la separación de órbitas—, que en el globo se ven como franjas/cuñas negras
# diagonales. VIIRS NOAA-20 no las tiene (su barrido cubre la separación orbital) y el
# globo sale limpio, así que es la capa por defecto de la descarga y del render.
CAPAS = {
    "MODIS_Terra_CorrectedReflectance_TrueColor": "terra",
    "MODIS_Aqua_CorrectedReflectance_TrueColor": "aqua",
    "VIIRS_NOAA20_CorrectedReflectance_TrueColor": "noaa20",
}
CAPA_DEFECTO = "VIIRS_NOAA20_CorrectedReflectance_TrueColor"

# Las capas son globales: la caja cubre todo el planeta (oeste, sur, este, norte).
BBOX = (-180.0, -90.0, 180.0, 90.0)

DESDE = "2024-07-11"                    # UTC
HASTA = "2024-10-30"                    # UTC, inclusive
PASO_DIAS = 1                           # composición diaria: un cuadro por día
PX = 2711                               # ancho de SALIDA del cuadro (globo)
# El origen global 2:1 se pide a la máxima resolución del servicio (8192x4096): cada
# crudo pesa ~1,5 MB y el globo de 2711 px queda con detalle de sobra al remuestrear.
SRC_PX = 8192
# Por debajo de esto el archivo no es un cuadro: es un error del servicio disfrazado.
MIN_BYTES = 20_000


def url_cuadro(t, bbox, ancho: int, alto: int, capa: str) -> str:
    """URL del snapshot para el día `t` (se pide en JPEG: pesa menos que PNG).

    Estas capas son **diarias**, así que el `TIME` va como fecha sola `AAAA-MM-DD` (no el
    ISO8601 completo con hora que usan los productos sub-diarios). Ojo con el orden de la
    caja: la API recibe BBOX como ``sur,oeste,norte,este``.
    """
    momento = t.strftime("%Y-%m-%d")
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


def _uniforme(ruta: Path, umbral: float = 5.0) -> bool:
    """True si el JPEG es (casi) de un solo color, o sea un cuadro **sin dato**.

    En estas capas **diarias** el día puede no existir —un hueco de procesamiento, o una
    fecha todavía sin composición publicada— y GIBS responde igual un JPEG perfectamente
    válido pero en blanco/negro: no es un error de red y `raise_for_status` no lo ve. Si se
    dejara pasar, quedaría un cuadro vacío que rompería la animación (o mostraría un globo
    negro como si fuera dato). La desviación estándar de los píxeles separa ese caso del de
    una imagen real: una foto con océano y nubes tiene std alto; un cuadro vacío, casi cero.
    """
    arr = np.asarray(Image.open(ruta).convert("RGB"))
    # Se evalúa sobre una submuestra (1 de cada 8 px por eje): `arr.std()` completo
    # promueve a float64 y con el origen global (8192x4096) son ~800 MiB por hilo, que
    # con 16 hilos agotan la RAM. Una imagen uniforme sigue siéndolo al submuestrearla.
    return float(arr[::8, ::8].std()) < umbral


def descargar_cuadro(t, bbox, ancho: int, alto: int, capa: str, destino: Path,
                     reintentos: int = 4) -> Path:
    """Baja el cuadro a `destino`; lo reutiliza si ya está (reanudable)."""
    if destino.exists() and destino.stat().st_size > MIN_BYTES:
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    url = url_cuadro(t, bbox, ancho, alto, capa)
    espera = 2.0
    for intento in range(1, reintentos + 1):
        try:
            r = _sesion().get(url, timeout=90)
            r.raise_for_status()
            if len(r.content) < MIN_BYTES:
                raise ValueError(f"respuesta demasiado chica ({len(r.content)} B)")
            tmp = destino.with_suffix(destino.suffix + ".parcial")
            tmp.write_bytes(r.content)
            # Guarda de vacío: un JPEG válido pero uniforme es un cuadro sin dato, no un
            # cuadro real. Se borra lo parcial y se cuenta como intento fallido para que
            # el backoff lo reintente en vez de dejar un hueco silencioso.
            if _uniforme(tmp):
                tmp.unlink(missing_ok=True)
                raise ValueError("cuadro sin dato (imagen uniforme)")
            tmp.replace(destino)
            return destino
        except Exception as exc:                       # red o corte del servicio
            if intento == reintentos:
                raise
            print(f"    reintento {intento}/{reintentos - 1} ({exc})", flush=True)
            time.sleep(espera)
            espera *= 2
    return destino


def _cmd_extra(args) -> str:
    """Sufijo `--out` común a los comandos de descarga y render."""
    return f' --out "{args.out}"' if args.out else ""


def _comando_descarga(args) -> str:
    """El mismo comando de descarga, para reintentar sólo los cuadros que faltan."""
    return (f".venv\\Scripts\\python.exe descargar\\truecolor.py "
            f"--desde {args.desde} --hasta {args.hasta} --paso {args.paso} "
            f"--capa {args.capa} --px {args.px}") + _cmd_extra(args)


def _comando_render(args) -> str:
    """El comando EXACTO de render que consume estos crudos."""
    return (f".venv\\Scripts\\python.exe cuadros\\cuadros_truecolor.py "
            f"--desde {args.desde} --hasta {args.hasta} --paso {args.paso} "
            f"--capa {args.capa} --px {args.px}") + _cmd_extra(args)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Descarga cuadros diarios de True Color (Corrected Reflectance) de "
                    "MODIS/VIIRS desde NASA GIBS.")
    ap.add_argument("--desde", default=DESDE,
                    help=f"primer cuadro, UTC (por defecto {DESDE})")
    ap.add_argument("--hasta", default=HASTA,
                    help=f"último cuadro, UTC inclusive (por defecto {HASTA})")
    ap.add_argument("--paso", type=int, default=PASO_DIAS,
                    help=f"días entre cuadros (por defecto {PASO_DIAS}: composición diaria)")
    ap.add_argument("--capa", default=CAPA_DEFECTO,
                    help=f"capa GIBS (por defecto {CAPA_DEFECTO}; alternativas: "
                         + ", ".join(c for c in CAPAS if c != CAPA_DEFECTO) + ")")
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("O", "S", "E", "N"),
                    default=list(BBOX),
                    help=f"caja lon/lat de origen (por defecto, global {BBOX})")
    ap.add_argument("--px", type=int, default=PX,
                    help=f"ancho de SALIDA en píxeles (por defecto {PX})")
    ap.add_argument("--src-px", type=int, default=SRC_PX,
                    help=f"ancho de la imagen de origen (por defecto {SRC_PX}, la máxima "
                         "del servicio; ~1,5 MB por cuadro)")
    ap.add_argument("--alto", type=int, help="alto del origen en píxeles (por defecto, "
                                             "según la caja)")
    ap.add_argument("--hilos", type=int, default=16,
                    help="descargas simultáneas (por defecto 16, para saturar el enlace; "
                         "bajalo si el servicio devuelve 429)")
    ap.add_argument("--out", help="carpeta de salida (por defecto, comun.rutas.SALIDAS)")
    args = ap.parse_args(argv)

    if args.capa not in CAPAS:
        raise SystemExit(f"capa desconocida: {args.capa}\n  Válidas: "
                         + ", ".join(CAPAS))
    short = CAPAS[args.capa]

    o, s, e, n = args.bbox
    if not (o < e and s < n):
        raise SystemExit(f"caja inválida: {args.bbox}")

    # El origen se pide con la proporción de la caja; para el globo global es 2:1. Se pide
    # más grande que la salida porque el warping a Orthographic remuestrea y conviene
    # tener de dónde tirar.
    src_px = args.src_px
    src_alto = args.alto or round(src_px * (n - s) / (e - o))

    # La serie y la etiqueta salen de comun/series.py: el render las recalcula igual.
    fechas = serie_fechas(args.desde, args.hasta, args.paso * 1440)
    if not fechas:
        raise SystemExit("La serie de fechas está vacía: revisá --desde/--hasta/--paso.")
    t0, n_cuadros = fechas[0], len(fechas)

    salida = Path(args.out) if args.out else SALIDAS
    frames_dir = salida / f"frames_{etiqueta_frames('truecolor_' + short, 'globo', t0, n_cuadros, args.px)}"
    frames_dir.mkdir(parents=True, exist_ok=True)

    print(f"True Color {short} (globo) | {n_cuadros} cuadros desde {t0:%Y-%m-%d} UTC | "
          f"paso {args.paso} d | origen {src_px}x{src_alto} px")
    print(f"capa {args.capa} | caja {o},{s},{e},{n} | frames en {frames_dir}")

    inicio = time.time()

    # Cada cuadro es un GET independiente: se bajan en paralelo. Si el servicio devuelve
    # 429, bajá --hilos.
    hechos = 0
    faltantes: list[tuple[int, object]] = []
    with ThreadPoolExecutor(max_workers=args.hilos) as pool:
        futuros = {
            pool.submit(descargar_cuadro, t, (o, s, e, n), src_px, src_alto, args.capa,
                        frames_dir / f"crudo_{i:03d}.jpg"): (i, t)
            for i, t in enumerate(fechas, 1)
        }
        for fut in as_completed(futuros):
            i, t = futuros[fut]
            try:
                fut.result()
            except Exception as exc:
                faltantes.append((i, t))
                print(f"[{i}/{n_cuadros}] {t:%Y-%m-%d} UTC  ERROR: {exc}", flush=True)
                continue
            hechos += 1
            print(f"  {hechos}/{n_cuadros} listos (errores {len(faltantes)}) "
                  f"{time.time() - inicio:.0f}s", flush=True)

    print(f"{hechos} cuadros listos en {time.time() - inicio:.0f}s")
    if faltantes:
        # Se listan las FECHAS exactas que faltan (no sólo la cantidad): con ellas se ve de
        # un vistazo si es un hueco del archivo (p. ej. un día sin composición) o un fallo
        # de red que vale la pena reintentar.
        detalle = "\n".join(f"  - {t:%Y-%m-%d}" for _, t in sorted(faltantes))
        raise SystemExit(f"Faltan {len(faltantes)} cuadros:\n{detalle}\n"
                         f"Reintentá con:\n  {_comando_descarga(args)}")
    print("Ahora renderizá con: " + _comando_render(args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
