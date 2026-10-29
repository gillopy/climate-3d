"""Animación del follaje de otoño en **globo Orthographic realista** (PACE/OCI LANDVI).

Misma data y mismo índice que el póster y que la versión plana
([`cuadros_follaje.py`](./cuadros_follaje.py)), pero con el tratamiento de globo que quedó
aprobado en [`../prototipos/poster_mur_realista.py`](../prototipos/poster_mur_realista.py):

  * **base de relieve real** (Blue Marble Shaded Relief + Bathymetry de NASA GIBS): la
    textura de montañas y fondos oceánicos se ve aunque no haya dato;
  * el color del índice va **modulado por la luminancia del relieve**, así el terreno
    aparece a través de la vegetación en vez de quedar tapado por una mancha plana;
  * **sombreado de esfera** sobre el disco ya proyectado (limb darkening + lambertiana
    leve): es lo que hace que se lea como una esfera y no como un círculo pintado.

Encima de eso, **rotación**: el globo arranca mirando al **Pacífico ecuatorial** y da una
vuelta completa a lo largo de la serie, mientras el compuesto móvil de 7 días avanza un día
por cuadro. Es decir, en el mismo video pasan las dos cosas: la estación y el giro.

El compuesto, las máscaras y la paleta viven en [`../comun/follaje.py`](../comun/follaje.py);
la base y el warp, en [`../comun/globo3d.py`](../comun/globo3d.py).

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe cuadros\\cuadros_follaje_globo.py
    .venv\\Scripts\\python.exe cuadros\\cuadros_follaje_globo.py --giro 0 --centro -73 -18
    .venv\\Scripts\\python.exe cuadros\\cuadros_follaje_globo.py --giro 360 --centro -125 0
    .venv\\Scripts\\python.exe animar\\armar.py --frames <carpeta> --fps 5
"""
from __future__ import annotations

import argparse
import gc
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import matplotlib
import numpy as np
from matplotlib.colors import Normalize
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from estilo import BG, TXT, TXT_DIM, WM_COLOR  # noqa: E402
from follaje import (ROJEZ, VMAX, VMIN, dias_moviles, movil,  # noqa: E402
                     rango_corto, ruta_dia)
from globo3d import base_mundi, iluminar, luminancia, warp_ortho  # noqa: E402
from rutas import SALIDAS  # noqa: E402
from series import etiqueta_frames  # noqa: E402

DESDE = "2026-06-01"
HASTA = "2026-10-11"
VENTANA = 7
RES = "0p1deg"
PX = 1440
CENTRO = (-125.0, 0.0)                  # Pacífico ecuatorial, como el globo de MUR
GIRO = 360.0                            # grados que recorre el centro a lo largo de la serie
SUB = 3                                 # cuadros por día: interpola el giro, no la fecha
BASE_PX = 3600                          # ancho de la grilla global de trabajo
FPS_SUGERIDO = 8
LIMBO = "#8fa3ad"
BG_RGB = np.array([int(BG[1:3], 16), int(BG[3:5], 16), int(BG[5:7], 16)],
                  dtype=np.float32) / 255.0


def _global(base: np.ndarray, rojez: np.ndarray) -> np.ndarray:
    """Compone el raster global lon/lat: relieve oscuro + color del índice modulado.

    Donde no hay dato queda la base apenas iluminada (se distinguen océano y relieve);
    donde hay vegetación manda la rampa, pero escalada por la luminancia del terreno para
    que las montañas y los valles se sigan leyendo.
    """
    if rojez.shape != base.shape[:2]:
        # El insumo puede venir en otra grilla (p. ej. 4 km): se remuestrea el índice.
        im = Image.fromarray(np.nan_to_num(rojez, nan=-1.0).astype(np.float32))
        rojez = np.asarray(im.resize((base.shape[1], base.shape[0]), Image.BILINEAR))
        rojez = np.where(rojez < 0, np.nan, rojez)

    lum = luminancia(base)
    rgb = base * 0.72                                  # sin dato: relieve apagado

    valido = np.isfinite(rojez)
    if valido.any():
        color = ROJEZ(Normalize(VMIN, VMAX)(rojez[valido]))[..., :3]
        # 0.65 en las sombras del terreno, 1.35 en las laderas iluminadas.
        factor = (0.72 + 0.62 * lum[valido])[..., None]
        rgb[valido] = np.clip(color * factor, 0.0, 1.0)
    return rgb


def _barra(fig, malla) -> None:
    cax = fig.add_axes([0.30, 0.070, 0.40, 0.012])
    cb = fig.colorbar(malla, cax=cax, orientation="horizontal",
                      extend="both", extendfrac=0.012)
    cb.set_ticks([1.0, 1.5, 2.0, 2.5, 3.0])
    cb.ax.set_xticklabels([f"{v:.2f}" for v in cb.get_ticks()], fontsize=6.5,
                          color=TXT_DIM)
    cb.outline.set_edgecolor("#3a464d")
    cb.outline.set_linewidth(0.5)
    cb.ax.tick_params(length=2, width=0.5, color="#3a464d")
    fig.text(0.5, 0.042, "RELATIVE ANTHOCYANIN / CHLOROPHYLL  ·  mARI ÷ CIRE",
             color=TXT_DIM, fontsize=6, ha="center", va="center")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--desde", default=DESDE, help=f"primer cuadro (default {DESDE})")
    ap.add_argument("--hasta", default=HASTA, help=f"último cuadro (default {HASTA})")
    ap.add_argument("--ventana", type=int, default=VENTANA,
                    help=f"días del compuesto móvil (default {VENTANA})")
    ap.add_argument("--res", default=RES, choices=("4km", "2km", "0p1deg"),
                    help=f"resolución del insumo (default {RES})")
    ap.add_argument("--px", type=int, default=PX, help=f"lado del cuadro (default {PX})")
    ap.add_argument("--base-px", type=int, default=BASE_PX,
                    help=f"ancho de la grilla global de trabajo (default {BASE_PX})")
    ap.add_argument("--centro", type=float, nargs=2, default=list(CENTRO),
                    metavar=("LON", "LAT"),
                    help=f"centro inicial del globo (default {CENTRO})")
    ap.add_argument("--giro", type=float, default=GIRO,
                    help=f"grados de rotación a lo largo de la serie (default {GIRO}; 0 = fijo)")
    ap.add_argument("--sub", type=int, default=SUB,
                    help=f"cuadros por día: interpola el giro sin adelantar la fecha "
                         f"(default {SUB})")
    ap.add_argument("--rehacer", action="store_true",
                    help="vuelve a renderizar los cuadros que ya existen")
    ap.add_argument("--max-cuadros", type=int, default=0,
                    help="corta después de N cuadros nuevos (0 = todos); para renderizar "
                         "por tandas en máquinas con poca RAM")
    ap.add_argument("--out", default=None, help="carpeta de cuadros")
    args = ap.parse_args()

    d0, d1 = date.fromisoformat(args.desde), date.fromisoformat(args.hasta)
    faltan = [d for d in (d0, d1) if ruta_dia(d, args.res) is None]
    if faltan:
        raise SystemExit(
            f"Faltan gránulos ({faltan[0]} ...). Corré descargar/pace_landvi.py "
            f"--res {args.res} --desde {args.desde} --hasta {args.hasta}"
        )
    fechas = dias_moviles(d0, d1, args.ventana, args.res)
    dias = len(fechas)
    total = dias * args.sub

    etiqueta = etiqueta_frames("follaje_pace_globo", "ortho3d", d0, total, args.px)
    carpeta = Path(args.out) if args.out else SALIDAS / f"frames_{etiqueta}"
    carpeta.mkdir(parents=True, exist_ok=True)
    print(f"{total} cuadros ({dias} días x {args.sub}) -> {carpeta}")
    print(f"  centro {args.centro[0]:g},{args.centro[1]:g}  giro {args.giro:g}°"
          f"  = {args.giro / max(total - 1, 1):.2f}°/cuadro")

    base = base_mundi(args.base_px)

    n = 0
    nuevos = 0
    for dia, rojez, lat, lon in movil(fechas, args.ventana, args.res):
        t0 = time.time()
        inicio = dia - timedelta(days=args.ventana - 1)
        # El compuesto se arma una vez por día: los sub-cuadros sólo interpolan el giro.
        rgb = _global(base, rojez)
        for _ in range(args.sub):
            n += 1
            lon_c = args.centro[0] + args.giro * (n - 1) / max(total - 1, 1)
            destino = carpeta / f"cuadro_{n:03d}.png"
            if destino.exists() and not args.rehacer:
                continue                     # corrida retomada: no re-renderiza
            if args.max_cuadros and nuevos >= args.max_cuadros:
                print(f"\nCorte por --max-cuadros: {nuevos} cuadros nuevos en esta tanda.")
                print(f'  .venv\\Scripts\\python.exe animar\\armar.py --frames "{carpeta}" '
                      f"--fps {FPS_SUGERIDO}")
                return 0
            nuevos += 1
            disco, dentro = warp_ortho(rgb, (lon_c, args.centro[1]), args.px)
            disco = iluminar(disco, dentro)
            # Fuera del disco se pinta el fondo del póster: si quedara negro, se vería
            # el cuadrado del `imshow` recortado contra el gris azulado del fondo.
            disco[~dentro] = BG_RGB

            dpi = 200
            fig = Figure(figsize=(args.px / dpi, args.px / dpi), dpi=dpi, facecolor=BG)
            fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
            ax = fig.add_axes([0.03, 0.095, 0.94, 0.81])
            ax.set_facecolor(BG)
            ax.axis("off")
            ax.imshow(disco, interpolation="nearest", zorder=2)
            ax.add_patch(Circle((0.5, 0.5), 0.5, transform=ax.transAxes,
                                facecolor="none", edgecolor=LIMBO, linewidth=0.7,
                                alpha=0.5, zorder=3))

            fig.text(0.04, 0.955, "HUNTING RED LEAVES", color=TXT, fontsize=12,
                     fontweight="bold", ha="left", va="center", family="DejaVu Sans")
            fig.text(0.04, 0.925, f"{rango_corto(inicio.isoformat(), dia.isoformat())}"
                     "  ·  7-day composite", color=TXT_DIM, fontsize=7,
                     ha="left", va="center")
            fig.text(0.96, 0.955, "PACE · OCI · LANDVI", color=TXT_DIM, fontsize=7,
                     ha="right", va="center", family="DejaVu Sans Mono")
            # La barra necesita un mapeable con norma: el disco es una imagen RGB.
            from matplotlib.cm import ScalarMappable
            barra = ScalarMappable(norm=Normalize(VMIN, VMAX), cmap=ROJEZ)
            barra.set_array([])
            _barra(fig, barra)
            fig.text(0.5, 0.018, "Data: NASA PACE/OCI L3M LANDVI (OB.DAAC)  ·  "
                     "Relief: NASA Blue Marble", color=WM_COLOR, fontsize=5.8,
                     ha="center", va="center")

            fig.savefig(destino, dpi=dpi, facecolor=BG)
            fig.clear()
            del fig, disco, dentro
            gc.collect()                     # devuelve al SO los buffers de matplotlib
            print(f"  cuadro_{n:03d}.png  "
                  f"{rango_corto(inicio.isoformat(), dia.isoformat())}"
                  f"  lon {((lon_c + 180) % 360) - 180:6.1f}  ({time.time() - t0:.1f}s)")
        del rgb, rojez

    print("\nListo. Armá el video con:")
    print(f'  .venv\\Scripts\\python.exe animar\\armar.py --frames "{carpeta}" '
          f"--fps {FPS_SUGERIDO}")
    return 0


if __name__ == "__main__":
    matplotlib.use("Agg")
    raise SystemExit(main())
