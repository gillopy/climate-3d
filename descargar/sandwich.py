"""Descarga los dos crudos del producto **Sandwich RGB** de GOES-19 desde NASA GIBS.

El Sandwich no es un RGB de tres bandas: son **dos imágenes** que después se mezclan en
el render. El fondo es el **visible** (gris) y encima va el **IR 10.8 µm realzado en
color**. Por eso este descargador baja **dos JPEG por cuadro**: `crudo_NNN_vis.jpg` y
`crudo_NNN_ir.jpg`. La composición vive aparte, en `cuadros/cuadros_sandwich.py`.

Fuente (Worldview Snapshots API — un GET por cuadro y por capa):

    https://wvs.earthdata.nasa.gov/api/v1/snapshot
      ?REQUEST=GetSnapshot&TIME=<ISO8601>Z&BBOX=<sur>,<oeste>,<norte>,<este>
      &CRS=EPSG:4326&LAYERS=<capa>&FORMAT=image/jpeg&WIDTH=<w>&HEIGHT=<h>

**Por qué GIBS y no el `.nc` de NOAA S3** (`descargar_goes.py`): la banda visible de ABI
(C02) es de 0.5 km y cada `OR_ABI-L2-CMIPF-M6C02_*.nc` pesa ~200–228 MB. Para 2 días a
10 min serían ~288 archivos ≈ 57 GB: inviable. GIBS sirve las mismas bandas ya
rasterizadas a 1 km (~90–200 KB por cuadro), que sobra para la salida del repo. Además
no existe una capa `Sandwich` en GIBS: el producto se arma acá arriba.

**Sólo de día**: el visible necesita sol, así que la serie son los **tramos diurnos** de
cada jornada (`serie_diurna`, de `comun/series.py`), no las 48 h corridas.

**GIBS rate-limitea**: se manda `User-Agent`, se usan pocos hilos (`--hilos 8` por
defecto) y se reintenta con backoff. Sin `User-Agent` el servicio devuelve un XML
`ServiceExceptionReport` **con HTTP 200** en vez de la imagen; por eso se chequea el
`Content-Type` (y la guarda de imagen uniforme) y se reintenta.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe descargar\\sandwich.py --desde 2026-10-04 --hasta 2026-10-05 --hora-desde 10 --hora-hasta 22 --paso 10 --px 2048
    .venv\\Scripts\\python.exe descargar\\sandwich.py --help   # no toca la red
"""
from __future__ import annotations

import argparse
import shutil
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
from series import etiqueta_frames, serie_diurna  # noqa: E402

API = "https://wvs.earthdata.nasa.gov/api/v1/snapshot"

# Rol -> capa GIBS. Dos capas por cuadro: el visible (fondo) y el IR (color).
#   - Band2  = ABI C02 (0.64 µm): visible de día, se ve la morfología del tope nuboso.
#   - Band13 = ABI C13 (10.3 µm): ventana limpia de IR, la temperatura del tope.
# El MISMO par vive en `cuadros/cuadros_sandwich.py`: el repo duplica las constantes
# entre descarga y render (lo compartido de verdad, la serie y la etiqueta, está en
# `comun/series.py`).
CAPAS = {
    "vis": "GOES-East_ABI_Band2_Red_Visible_1km",
    "ir": "GOES-East_ABI_Band13_Clean_Infrared",
}

# Caja de globo: cubre el hemisferio visible centrado en Paraguay (misma que geocolor).
# Si la caja es más chica, el limbo queda recortado y el globo sale incompleto.
BBOX_GLOBO = (-160.0, -80.0, 15.0, 80.0)        # oeste, sur, este, norte

DESDE = "2026-10-04"                    # UTC (fecha)
HASTA = "2026-10-05"                    # UTC, inclusive (fecha)
HORA_DESDE = 10                         # UTC: arranque del tramo diurno (~07:00 en PY)
HORA_HASTA = 22                         # UTC: fin del tramo diurno (~19:00 en PY)
PASO_MIN = 10                           # minutos: la cadencia nativa de ABI
PX = 2048                               # ancho de SALIDA del cuadro (globo)
# El origen se pide más grande que la salida porque el warping a Orthographic
# remuestrea y conviene tener de dónde tirar.
MIN_SRC_PX = 1200
# Por debajo de esto el archivo no es un cuadro: es un error del servicio disfrazado.
MIN_BYTES = 20_000


def url_cuadro(t, bbox, ancho: int, alto: int, capa: str) -> str:
    """URL del snapshot del instante `t` para `capa` (se pide en JPEG: pesa menos).

    Estas capas son **sub-diarias**, así que el `TIME` va con hora (ISO8601 `...Z`), a
    diferencia de las composiciones diarias de True Color. Ojo con el orden de la caja:
    la API recibe el BBOX como ``sur,oeste,norte,este``.
    """
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
        # El User-Agent es obligatorio: sin él GIBS responde un XML de error con HTTP 200.
        ses.headers["User-Agent"] = "climate3d/1.0"
        adaptador = requests.adapters.HTTPAdapter(pool_connections=8, pool_maxsize=16,
                                                  max_retries=0)
        ses.mount("https://", adaptador)
        ses.mount("http://", adaptador)
        _LOCAL.sesion = ses
    return ses


def _uniforme(ruta: Path, umbral: float = 5.0) -> bool:
    """True si el JPEG es (casi) de un solo color, o sea un cuadro **sin dato**.

    En estas capas un slot puede no tener dato —un hueco de procesamiento, o el visible
    de noche— y GIBS responde igual un JPEG perfectamente válido pero en blanco/negro: no
    es un error de red y `raise_for_status` no lo ve. Si se dejara pasar, quedaría un
    cuadro vacío que rompería la animación (o un globo negro como si fuera dato). La
    desviación estándar de los píxeles separa ese caso del de una imagen real: una foto
    con océano y nubes tiene std alto; un cuadro vacío, casi cero.
    """
    arr = np.asarray(Image.open(ruta).convert("RGB"))
    # Se evalúa sobre una submuestra (1 de cada 8 px por eje): `arr.std()` completo
    # promueve a float64 y con el origen grande son cientos de MiB por hilo, que con
    # varios hilos agotan la RAM. Una imagen uniforme sigue siéndolo al submuestrearla.
    return float(arr[::8, ::8].std()) < umbral


def descargar_cuadro(t, bbox, ancho: int, alto: int, capa: str, destino: Path,
                     reintentos: int = 4) -> Path:
    """Baja la capa `capa` del instante `t` a `destino`; reutiliza si ya está.

    Reanudable: si `destino` existe y pesa más de `MIN_BYTES`, no se vuelve a pedir.
    """
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
            # Sin User-Agent (o cuando el servicio se enoja) GIBS devuelve un XML de
            # error **con HTTP 200**: no es una imagen. Se detecta por el Content-Type
            # antes de intentar abrirla y se reintenta, en vez de guardar un XML.
            ct = r.headers.get("Content-Type", "").lower()
            if "jpeg" not in ct and "jpg" not in ct:
                raise ValueError(f"respuesta no-JPEG (Content-Type {ct!r})")
            tmp = destino.with_suffix(destino.suffix + ".parcial")
            tmp.write_bytes(r.content)
            # Guarda de vacío: un JPEG válido pero uniforme es un cuadro sin dato, no un
            # cuadro real. Se borra lo parcial y se cuenta como intento fallido para que
            # el backoff lo reintente en vez de dejar un hueco silencioso.
            if _uniforme(tmp):
                tmp.unlink(missing_ok=True)
                raise ValueError("cuadro sin dato (imagen uniforme)")
            # Escritura atómica: si el proceso se corta a mitad, no queda un JPEG
            # corrupto que después se reutilice como si estuviera bueno.
            tmp.replace(destino)
            return destino
        except Exception as exc:                       # red, rate-limit o corte del servicio
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
    return (f".venv\\Scripts\\python.exe descargar\\sandwich.py "
            f"--desde {args.desde} --hasta {args.hasta} "
            f"--hora-desde {args.hora_desde} --hora-hasta {args.hora_hasta} "
            f"--paso {args.paso} --px {args.px}") + _cmd_extra(args)


def _comando_render(args) -> str:
    """El comando EXACTO de render que consume estos crudos."""
    return (f".venv\\Scripts\\python.exe cuadros\\cuadros_sandwich.py "
            f"--desde {args.desde} --hasta {args.hasta} "
            f"--hora-desde {args.hora_desde} --hora-hasta {args.hora_hasta} "
            f"--paso {args.paso} --px {args.px}") + _cmd_extra(args)


def _rellenar_con_vecino(frames_dir: Path, n_cuadros: int) -> list[tuple[int, str, int]]:
    """Sostiene los crudos que GIBS no tiene copiando el vecino más cercano de su capa.

    GIBS tiene **huecos de archivo puntuales**: en algunos slots exactos devuelve un JPEG
    válido pero **negro** (~4,5 KB, desvío 0) que la guarda de cuadro vacío rechaza. No es
    un fallo de red: reintentar no cambia nada (verificado contra el servicio, con los
    vecinos de ±10 min sanos y el slot exacto negro). Un hueco suelto se puede **sostener**
    con el cuadro anterior: en el video es un fotograma repetido, imperceptible.

    Devuelve `(índice, rol, índice de origen)` por cada crudo rellenado, para dejar
    asentado qué se sostuvo y con qué.
    """
    rellenos = []
    for rol in CAPAS:
        presentes = [i for i in range(1, n_cuadros + 1)
                     if (frames_dir / f"crudo_{i:03d}_{rol}.jpg").exists()]
        if not presentes:
            raise SystemExit(f"No hay ningún crudo {rol} bajo {frames_dir}: "
                             "no hay con qué rellenar.")
        for i in range(1, n_cuadros + 1):
            destino = frames_dir / f"crudo_{i:03d}_{rol}.jpg"
            if destino.exists():
                continue
            origen = min(presentes, key=lambda j: (abs(j - i), j))
            shutil.copyfile(frames_dir / f"crudo_{origen:03d}_{rol}.jpg", destino)
            rellenos.append((i, rol, origen))
    return rellenos


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Descarga los dos crudos del Sandwich RGB de GOES-19 (visible + IR "
                    "realzado) desde NASA GIBS.")
    ap.add_argument("--desde", default=DESDE,
                    help=f"primer día, UTC (por defecto {DESDE})")
    ap.add_argument("--hasta", default=HASTA,
                    help=f"último día, UTC inclusive (por defecto {HASTA})")
    ap.add_argument("--hora-desde", type=int, default=HORA_DESDE,
                    help=f"hora UTC de arranque de cada tramo diurno (por defecto "
                         f"{HORA_DESDE}: ~07:00 en Paraguay)")
    ap.add_argument("--hora-hasta", type=int, default=HORA_HASTA,
                    help=f"hora UTC de fin de cada tramo diurno (por defecto "
                         f"{HORA_HASTA}: ~19:00 en Paraguay)")
    ap.add_argument("--paso", type=int, default=PASO_MIN,
                    help=f"minutos entre cuadros (por defecto {PASO_MIN}: la cadencia "
                         "nativa de ABI)")
    ap.add_argument("--px", type=int, default=PX,
                    help=f"ancho de SALIDA en píxeles (por defecto {PX})")
    ap.add_argument("--src-px", type=int,
                    help=f"ancho de la imagen de origen (por defecto, "
                         f"max({MIN_SRC_PX}, px*2))")
    ap.add_argument("--alto", type=int, help="alto del origen en píxeles (por defecto, "
                                             "según la caja)")
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("O", "S", "E", "N"),
                    default=list(BBOX_GLOBO),
                    help=f"caja lon/lat de origen (por defecto, el globo {BBOX_GLOBO})")
    ap.add_argument("--hilos", type=int, default=8,
                    help="descargas simultáneas (por defecto 8: GIBS rate-limitea; "
                         "bajalo si el servicio devuelve un XML de error)")
    ap.add_argument("--out", help="carpeta de salida (por defecto, comun.rutas.SALIDAS)")
    ap.add_argument("--rellenar-huecos", action="store_true",
                    help="en vez de abortar por los slots que GIBS no tiene (JPEG negro), "
                         "los sostiene copiando el vecino más cercano de la misma capa")
    args = ap.parse_args(argv)

    o, s, e, n = args.bbox
    if not (o < e and s < n):
        raise SystemExit(f"caja inválida: {args.bbox}")

    # El origen se pide con la proporción de la caja y más grande que la salida: el
    # warping a Orthographic remuestrea y conviene tener de dónde tirar.
    src_px = args.src_px or max(MIN_SRC_PX, args.px * 2)
    src_alto = args.alto or round(src_px * (n - s) / (e - o))

    # La serie y la etiqueta salen de comun/series.py: el render las recalcula igual.
    fechas = serie_diurna(args.desde, args.hasta, args.hora_desde, args.hora_hasta,
                          args.paso)
    if not fechas:
        raise SystemExit("La serie de cuadros está vacía: revisá --desde/--hasta/"
                         "--hora-desde/--hora-hasta/--paso.")
    t0, n_cuadros = fechas[0], len(fechas)

    salida = Path(args.out) if args.out else SALIDAS
    frames_dir = salida / f"frames_{etiqueta_frames('sandwich', 'globo', t0, n_cuadros, args.px)}"
    frames_dir.mkdir(parents=True, exist_ok=True)

    print(f"Sandwich RGB (globo) | {n_cuadros} cuadros desde {t0:%Y-%m-%d %H:%M} UTC | "
          f"tramo {args.hora_desde:02d}-{args.hora_hasta:02d} UTC paso {args.paso} min | "
          f"origen {src_px}x{src_alto} px")
    print(f"dos capas por cuadro ({', '.join(CAPAS.values())}) | caja {o},{s},{e},{n}")
    print(f"frames en {frames_dir}")

    inicio = time.time()
    total = n_cuadros * len(CAPAS)

    # Cada (cuadro, rol) es un GET independiente: se bajan en paralelo. Si el servicio
    # devuelve 429 (o el XML de rate-limit), bajá --hilos.
    hechos = 0
    faltantes: list[tuple[int, object, str]] = []
    with ThreadPoolExecutor(max_workers=args.hilos) as pool:
        futuros = {}
        for i, t in enumerate(fechas, 1):
            for rol, capa in CAPAS.items():
                destino = frames_dir / f"crudo_{i:03d}_{rol}.jpg"
                fut = pool.submit(descargar_cuadro, t, (o, s, e, n), src_px, src_alto,
                                  capa, destino)
                futuros[fut] = (i, t, rol)
        for fut in as_completed(futuros):
            i, t, rol = futuros[fut]
            try:
                fut.result()
            except Exception as exc:
                faltantes.append((i, t, rol))
                print(f"[{i}/{n_cuadros}] {t:%Y-%m-%d %H:%M} UTC {rol}  ERROR: {exc}",
                      flush=True)
                continue
            hechos += 1
            print(f"  {hechos}/{total} archivos listos (errores {len(faltantes)}) "
                  f"{time.time() - inicio:.0f}s", flush=True)

    print(f"{hechos} archivos listos en {time.time() - inicio:.0f}s "
          f"({n_cuadros} cuadros x {len(CAPAS)} capas)")
    if faltantes and args.rellenar_huecos:
        rellenos = _rellenar_con_vecino(frames_dir, n_cuadros)
        for i, rol, origen in sorted(rellenos, key=lambda x: (x[0], x[1])):
            print(f"  hueco {i:03d} ({rol}): sostenido con el cuadro {origen:03d}")
        print(f"{len(rellenos)} crudos rellenados con el vecino (huecos de archivo de GIBS).")
        faltantes = []
    if faltantes:
        # Se listan las FECHAS y HORAS exactas que faltan (con su capa): con ellas se ve
        # de un vistazo si es un hueco del archivo (p. ej. el visible de noche) o un
        # fallo de red que vale la pena reintentar.
        detalle = "\n".join(f"  - {t:%Y-%m-%d %H:%M} UTC ({rol})"
                            for _, t, rol in sorted(faltantes, key=lambda x: (x[0], x[2])))
        raise SystemExit(f"Faltan {len(faltantes)} cuadros:\n{detalle}\n"
                         f"Reintentá con:\n  {_comando_descarga(args)}")
    print("Ahora renderizá con: " + _comando_render(args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
