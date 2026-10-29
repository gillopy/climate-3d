"""Póster global del **follaje de otoño** medido por PACE/OCI (índice de rojez).

Lee los gránulos diarios L3M de **LANDVI** ya bajados por `descargar/pace_landvi.py`,
arma el compuesto de la ventana y dibuja un mapa global en proyección Robinson con el
mismo lenguaje visual que el mapa de NASA Earth Observatory ("Hunting Red Leaves with
Satellites"): fondo blanco, océano celeste pálido, continentes en gris claro donde el
satélite no ve vegetación y la vegetación coloreada de verde a rojo.

Todo lo que define **qué se pinta** (el cociente, las máscaras, la paleta y la escala
1.00-3.00) vive en [`../comun/follaje.py`](../comun/follaje.py), compartido con
[`../cuadros/cuadros_follaje.py`](../cuadros/cuadros_follaje.py). Acá sólo queda el dibujo.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe prototipos\\poster_follaje.py
    .venv\\Scripts\\python.exe prototipos\\poster_follaje.py --doble
    .venv\\Scripts\\python.exe prototipos\\poster_follaje.py --dia 2026-10-04 --px 2712
    .venv\\Scripts\\python.exe prototipos\\poster_follaje.py --help   # no toca el disco
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib
import numpy as np
from matplotlib.colors import Normalize
from matplotlib.figure import Figure

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from follaje import (BORDE, COSTA, OCEANO, ROJEZ, TIERRA, TINTA,  # noqa: E402
                     TINTA_SUAVE, VMAX, VMIN, compuesto, fecha_larga, rango_corto)
from rutas import SALIDAS  # noqa: E402

DESDE = "2026-09-29"                    # ventana del mapa de referencia
HASTA = "2026-10-04"
RES = "4km"                             # resolución del insumo
PX = 2712                               # ancho del póster en píxeles
PASO = 3                                # submuestreo antes del warp (ver _mapa)


# ------------------------------------------------------------------ dibujo
def mapa_global(fig, rect: list[float], rojez: np.ndarray, lat: np.ndarray,
          lon: np.ndarray, paso: int = PASO):
    """Dibuja un mapa global Robinson y devuelve el mapeable de la capa de datos.

    La grilla de 4 km es de 4320x8640; deformarla entera pide ~1.5 GB de RAM por las
    matrices temporales de `warp_array`. Un submuestreo por 3 deja 1440x2880, que ya
    rinde ~1 muestra por píxel del póster y entra holgado en memoria.
    """
    rojez = rojez[::paso, ::paso]
    lat = lat[::paso]
    lon = lon[::paso]

    ax = fig.add_axes(rect, projection=ccrs.Robinson(central_longitude=0))
    ax.set_global()
    ax.set_facecolor(OCEANO)
    ax.spines["geo"].set_visible(False)

    ax.add_feature(cfeature.LAND.with_scale("110m"), facecolor=TIERRA,
                   edgecolor="none", zorder=1)
    ax.add_feature(cfeature.LAKES.with_scale("110m"), facecolor=OCEANO,
                   edgecolor="none", zorder=2)
    malla = ax.imshow(
        np.ma.masked_invalid(rojez), origin="lower",
        extent=(float(lon[0]), float(lon[-1]), float(lat[0]), float(lat[-1])),
        transform=ccrs.PlateCarree(), cmap=ROJEZ,
        norm=Normalize(VMIN, VMAX), interpolation="nearest", zorder=3,
    )
    ax.add_feature(cfeature.COASTLINE.with_scale("110m"), edgecolor=COSTA,
                   linewidth=0.35, zorder=4)
    ax.add_feature(cfeature.BORDERS.with_scale("110m"), edgecolor=BORDE,
                   linewidth=0.3, zorder=4)
    return ax, malla


def _barra(fig, malla, rect, y_texto: float, tam: float = 7.5) -> None:
    cax = fig.add_axes(rect)
    cb = fig.colorbar(malla, cax=cax, orientation="horizontal",
                      extend="both", extendfrac=0.012)
    cb.set_ticks([1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0])
    cb.ax.set_xticklabels([f"{v:.2f}" for v in cb.get_ticks()], fontsize=tam,
                          color=TINTA_SUAVE)
    cb.outline.set_edgecolor(COSTA)
    cb.outline.set_linewidth(0.5)
    cb.ax.tick_params(length=2, width=0.5, color=COSTA)
    fig.text(0.5, y_texto, "RELATIVE ANTHOCYANIN / CHLOROPHYLL  ·  mARI ÷ CIRE",
             color=TINTA_SUAVE, fontsize=tam, ha="center", va="center")


def _creditos(fig, y: float, tam: float = 6.5) -> None:
    fig.text(0.055, y,
             "Data: NASA PACE/OCI L3M LANDVI (OB.DAAC)  ·  Render: climate 3d",
             color=TINTA_SUAVE, fontsize=tam, ha="left", va="center")


def poster(rojez: np.ndarray, lat: np.ndarray, lon: np.ndarray,
           desde: str, hasta: str, px: int, salida: Path) -> Path:
    alto = int(px * 0.62)
    dpi = 200
    fig = Figure(figsize=(px / dpi, alto / dpi), dpi=dpi, facecolor="white")
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    _, malla = mapa_global(fig, [0.02, 0.145, 0.96, 0.75], rojez, lat, lon)

    fig.text(0.055, 0.965, "HUNTING RED LEAVES", color=TINTA, fontsize=19,
             fontweight="bold", ha="left", va="center", family="DejaVu Sans")
    fig.text(0.055, 0.928,
             "Relative anthocyanin to chlorophyll in vegetation - "
             f"{fecha_larga(desde)} to {fecha_larga(hasta)}",
             color=TINTA_SUAVE, fontsize=9.5, ha="left", va="center")
    fig.text(0.945, 0.965, "PACE · OCI · LANDVI · 4 km", color=TINTA_SUAVE,
             fontsize=8.5, ha="right", va="center", family="DejaVu Sans Mono")

    _barra(fig, malla, [0.26, 0.062, 0.48, 0.022], 0.018)
    _creditos(fig, 0.018)

    salida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(salida, dpi=dpi, facecolor="white")
    return salida


def poster_doble(semanas: list[tuple], px: int, salida: Path) -> Path:
    """Dos ventanas de una semana, una arriba de la otra, con barra compartida."""
    alto = int(px * 1.12)
    dpi = 200
    fig = Figure(figsize=(px / dpi, alto / dpi), dpi=dpi, facecolor="white")
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    fig.text(0.045, 0.982, "HUNTING RED LEAVES", color=TINTA, fontsize=17,
             fontweight="bold", ha="left", va="center", family="DejaVu Sans")
    fig.text(0.955, 0.982, "PACE · OCI · LANDVI · 4 km", color=TINTA_SUAVE,
             fontsize=8, ha="right", va="center", family="DejaVu Sans Mono")

    rects = ([0.02, 0.520, 0.96, 0.435], [0.02, 0.075, 0.96, 0.435])
    malla = None
    for (rojez, lat, lon, desde, hasta), rect in zip(semanas, rects):
        ax, malla = mapa_global(fig, rect, rojez, lat, lon)
        ax.text(0.006, 0.995, rango_corto(desde, hasta).upper(), transform=ax.transAxes,
                color=TINTA, fontsize=10.5, fontweight="bold", ha="left", va="top")

    _barra(fig, malla, [0.31, 0.042, 0.38, 0.010], 0.022, tam=6.8)
    _creditos(fig, 0.022, tam=6.2)

    salida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(salida, dpi=dpi, facecolor="white")
    return salida


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--desde", default=DESDE)
    ap.add_argument("--hasta", default=HASTA)
    ap.add_argument("--dia", default=None, help="un solo día YYYY-MM-DD (ignora la ventana)")
    ap.add_argument("--doble", action="store_true",
                    help="dos paneles: la ventana y la semana siguiente")
    ap.add_argument("--desde2", default=None, help="inicio del segundo panel")
    ap.add_argument("--hasta2", default=None, help="fin del segundo panel")
    ap.add_argument("--res", default=RES, choices=("4km", "2km", "0p1deg"),
                    help=f"resolución del insumo (default {RES})")
    ap.add_argument("--px", type=int, default=PX, help=f"ancho del póster (default {PX})")
    ap.add_argument("--salida", default=None, help="PNG de salida")
    ap.add_argument("--rehacer", action="store_true", help="ignora el compuesto cacheado")
    args = ap.parse_args()

    desde, hasta = (args.dia, args.dia) if args.dia else (args.desde, args.hasta)

    def ventana(d0: str, d1: str):
        print(f"Compuesto {d0} -> {d1} ({args.res})")
        rojez, lat, lon = compuesto(d0, d1, args.res, args.rehacer)
        buenos = int(np.isfinite(rojez).sum())
        print(f"  pixeles con dato: {buenos:,} ({buenos / rojez.size:.1%} del globo)")
        return rojez, lat, lon

    if not args.doble:
        rojez, lat, lon = ventana(desde, hasta)
        etiqueta = f"{desde}_{hasta}".replace("-", "")
        salida = Path(args.salida) if args.salida else (
            SALIDAS / f"poster_follaje_pace_{etiqueta}_{args.px}px.png")
        poster(rojez, lat, lon, desde, hasta, args.px, salida)
    else:
        # Por defecto el segundo panel es la semana inmediatamente posterior.
        d1 = date.fromisoformat(hasta)
        desde2 = args.desde2 or (d1 + timedelta(days=1)).isoformat()
        hasta2 = args.hasta2 or (d1 + timedelta(days=7)).isoformat()
        semanas = [(*ventana(desde, hasta), desde, hasta),
                   (*ventana(desde2, hasta2), desde2, hasta2)]
        etiqueta = f"{desde}_{hasta2}".replace("-", "")
        salida = Path(args.salida) if args.salida else (
            SALIDAS / f"poster_follaje_pace_doble_{etiqueta}_{args.px}px.png")
        poster_doble(semanas, args.px, salida)

    print(f"Poster: {salida}")
    return 0


if __name__ == "__main__":
    matplotlib.use("Agg")
    raise SystemExit(main())
