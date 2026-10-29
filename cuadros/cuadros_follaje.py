"""Renderiza los cuadros de la animación del **follaje de otoño** (PACE/OCI LANDVI).

La descarga vive aparte, en `descargar/pace_landvi.py`; acá sólo se leen los gránulos
diarios que esa carpeta deja y se guardan como `cuadro_NNN.png` en
`SALIDAS/frames_follaje_pace_<inicio>_<n>f_<px>px/`, con el vestuario del póster
(Robinson, fondo blanco, océano celeste, barra 1.00-3.00).

**Cada cuadro es un compuesto móvil de N días** (`--ventana`, por defecto 7) terminado
en la fecha del cuadro: un día suelto de LANDVI tiene demasiados huecos de nubes, y el
compuesto los rellena. El cálculo del índice, las máscaras, la paleta y el compuesto
móvil están en [`../comun/follaje.py`](../comun/follaje.py), compartidos con el póster.

Para la versión en globo Orthographic está
[`cuadros_follaje_globo.py`](./cuadros_follaje_globo.py).

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe cuadros\\cuadros_follaje.py --desde 2026-08-07 --hasta 2026-10-11
    .venv\\Scripts\\python.exe cuadros\\cuadros_follaje.py --px 1920 --ventana 7 --res 0p1deg
    .venv\\Scripts\\python.exe animar\\armar.py --frames <carpeta> --fps 6
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import matplotlib
from matplotlib.figure import Figure

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
sys.path.insert(0, str(RAIZ / "prototipos"))     # reusa el mapa del póster
from follaje import (COSTA, TINTA, TINTA_SUAVE, VMAX, VMIN,  # noqa: E402
                     dias_moviles, movil, rango_corto, ruta_dia)
from poster_follaje import mapa_global  # noqa: E402
from rutas import SALIDAS  # noqa: E402
from series import etiqueta_frames  # noqa: E402

DESDE = "2026-08-07"                    # primer cuadro (ya con la ventana completa)
HASTA = "2026-10-11"                    # último cuadro
VENTANA = 7                             # días del compuesto móvil
RES = "0p1deg"                          # 0p1deg: liviano y de sobra para 1920 px
PX = 1920
FPS_SUGERIDO = 6


def _tablero(px: int) -> Figure:
    """Figure con el vestuario fijo: fondo blanco, título y créditos."""
    alto = int(px * 0.563)
    dpi = 200
    fig = Figure(figsize=(px / dpi, alto / dpi), dpi=dpi, facecolor="white")
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    fig.text(0.035, 0.955, "HUNTING RED LEAVES", color=TINTA, fontsize=12,
             fontweight="bold", ha="left", va="center", family="DejaVu Sans")
    fig.text(0.965, 0.955, "PACE · OCI · LANDVI · 7-day composite",
             color=TINTA_SUAVE, fontsize=7.5, ha="right", va="center",
             family="DejaVu Sans Mono")
    return fig


def _barra(fig, malla) -> None:
    cax = fig.add_axes([0.30, 0.058, 0.40, 0.014])
    cb = fig.colorbar(malla, cax=cax, orientation="horizontal",
                      extend="both", extendfrac=0.012)
    cb.set_ticks([1.0, 1.5, 2.0, 2.5, 3.0])
    cb.ax.set_xticklabels([f"{v:.2f}" for v in cb.get_ticks()], fontsize=6.5,
                          color=TINTA_SUAVE)
    cb.outline.set_edgecolor(COSTA)
    cb.outline.set_linewidth(0.5)
    cb.ax.tick_params(length=2, width=0.5, color=COSTA)
    fig.text(0.5, 0.016, "RELATIVE ANTHOCYANIN / CHLOROPHYLL  ·  mARI ÷ CIRE",
             color=TINTA_SUAVE, fontsize=6, ha="center", va="center")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--desde", default=DESDE, help=f"primer cuadro (default {DESDE})")
    ap.add_argument("--hasta", default=HASTA, help=f"último cuadro (default {HASTA})")
    ap.add_argument("--ventana", type=int, default=VENTANA,
                    help=f"días del compuesto móvil (default {VENTANA})")
    ap.add_argument("--res", default=RES, choices=("4km", "2km", "0p1deg"),
                    help=f"resolución del insumo (default {RES})")
    ap.add_argument("--px", type=int, default=PX, help=f"ancho del cuadro (default {PX})")
    ap.add_argument("--paso", type=int, default=None,
                    help="submuestreo antes del warp (default: 3 en 4km, 1 en 0p1deg)")
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

    etiqueta = etiqueta_frames("follaje_pace", "global", d0, dias, args.px)
    carpeta = Path(args.out) if args.out else SALIDAS / f"frames_{etiqueta}"
    carpeta.mkdir(parents=True, exist_ok=True)
    paso = args.paso if args.paso else (3 if args.res == "4km" else 1)
    print(f"{dias} cuadros -> {carpeta}")

    for i, (dia, rojez, lat, lon) in enumerate(
            movil(fechas, args.ventana, args.res), start=1):
        t0 = time.time()
        inicio = dia - timedelta(days=args.ventana - 1)
        fig = _tablero(args.px)
        ax, malla = mapa_global(fig, [0.01, 0.105, 0.98, 0.82], rojez, lat, lon,
                                paso=paso)
        ax.text(0.006, 0.995, rango_corto(inicio.isoformat(), dia.isoformat()).upper(),
                transform=ax.transAxes, color=TINTA, fontsize=9,
                fontweight="bold", ha="left", va="top")
        _barra(fig, malla)
        fig.savefig(carpeta / f"cuadro_{i:03d}.png", dpi=200, facecolor="white")
        del rojez
        print(f"  cuadro_{i:03d}.png  {rango_corto(inicio.isoformat(), dia.isoformat())}"
              f"  ({time.time() - t0:.1f}s)")

    print("\nListo. Armá el video con:")
    print(f'  .venv\\Scripts\\python.exe animar\\armar.py --frames "{carpeta}" '
          f"--fps {FPS_SUGERIDO}")
    return 0


if __name__ == "__main__":
    matplotlib.use("Agg")
    raise SystemExit(main())
