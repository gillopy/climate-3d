"""Póster de color real de **PACE / OCI** desde el compuesto oficial de NASA GIBS.

Archivo NUEVO. Complementa a `poster_pace.py` (que lee el L3M SFREFL en NetCDF):

  * `poster_pace.py` usa las bandas crudas pero SFREFL es reflectancia **de
    superficie**: las nubes vienen enmascaradas y queda una Tierra sin nubes.
  * Este script baja el producto **OCI_PACE_True_Color** de GIBS, que es el render
    oficial de las capturas reales del OCI (con nubes, aerosoles y sombras). No es un
    JPEG inventado: es el mismo pipeline de imagen de NASA Worldview sobre los gránulos
    L2 `rhos` del satélite.

PACE es polar y su swath no cubre el planeta de una vez, así que un día suelto deja
huecos. Se bajan varios días y se rellenan por prioridad temporal: el primer píxel con
dato gana.

Teselas WMTS (EPSG:4326, conjunto `1km`): nivel 4 = 20x10 teselas de 512 px, o sea
10240x5120 de equirectangular, ~3.9 km por píxel en el ecuador.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe prototipos\\poster_pace_gibs.py --hasta 2026-10-24 --dias 8
    .venv\\Scripts\\python.exe prototipos\\poster_pace_gibs.py --help   # no toca la red
"""
from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
sys.path.insert(0, str(RAIZ / "prototipos"))

from poster_pace import ortho_inverso, muestrear  # noqa: E402
from rutas import SALIDAS  # noqa: E402

BASE = "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best"
CAPA = "OCI_PACE_True_Color"
NIVEL = 4                      # 20 x 10 teselas de 512 px -> 10240 x 5120
TESELA = 512

PX = 3000
CENTRO = (-58.0, -10.0)
SATURACION = 1.05
GAMMA = 1.0

BG = "#000000"
INK = "#f2f5f8"
INK_SOFT = "#b9c1c9"
INK_FAINT = "#7e8790"
CREDITO = "Graphic by @Gillo97"
CACHE = SALIDAS / "teselas_pace"


def _matriz(nivel: int) -> tuple[int, int]:
    """(columnas, filas) de teselas del conjunto `1km` para ese nivel.

    Se lee de las capacidades WMTS en vez de calcularlo: la grilla de GIBS no es una
    potencia de dos limpia (nivel 0 = 2x1, nivel 1 = 3x2, nivel 4 = 20x10).
    """
    import re
    import requests

    if _matriz.cache is None:
        xml = requests.get(f"{BASE}/1.0.0/WMTSCapabilities.xml", timeout=120).text
        i = xml.find("<TileMatrixSet><ows:Identifier>1km</ows:Identifier>")
        bloque = xml[i:i + 20000]
        cache = {}
        for m in re.finditer(
                r"<ows:Identifier>(\d+)</ows:Identifier>.*?"
                r"<MatrixWidth>(\d+)</MatrixWidth>.*?<MatrixHeight>(\d+)</MatrixHeight>",
                bloque, re.S):
            cache[int(m.group(1))] = (int(m.group(2)), int(m.group(3)))
        _matriz.cache = cache
    return _matriz.cache[nivel]


_matriz.cache = None


def _url(d: date, nivel: int, fila: int, col: int) -> str:
    return (f"{BASE}/{CAPA}/default/{d:%Y-%m-%d}/1km/{nivel}/{fila}/{col}.jpeg")


def bajar_tesela(args) -> tuple[int, int, Path | None]:
    """Baja una tesela; devuelve (fila, col, ruta) o ruta None si vino vacía."""
    import requests

    d, nivel, fila, col, carpeta = args
    destino = carpeta / f"{d:%Y%m%d}_{nivel}_{fila}_{col}.jpg"
    if destino.exists() and destino.stat().st_size > 512:
        return fila, col, destino
    try:
        r = requests.get(_url(d, nivel, fila, col), timeout=60)
        r.raise_for_status()
        destino.write_bytes(r.content)
        return fila, col, destino
    except Exception:
        return fila, col, None


def mosaico_dia(d: date, nivel: int, ancho: int, alto: int, hilos: int = 16):
    """Arma el mosaico equirectangular de un día (uint8 HxWx3), None si no hay dato."""
    from PIL import Image

    carpeta = CACHE / f"{d:%Y%m%d}_{nivel}"
    carpeta.mkdir(parents=True, exist_ok=True)
    trabajos = [(d, nivel, f, c, carpeta)
                for f in range(alto // TESELA) for c in range(ancho // TESELA)]
    salida = np.zeros((alto, ancho, 3), dtype=np.uint8)
    con_dato = 0
    with ThreadPoolExecutor(max_workers=hilos) as pool:
        for fila, col, ruta in pool.map(bajar_tesela, trabajos):
            if ruta is None:
                continue
            img = np.asarray(Image.open(ruta).convert("RGB"), dtype=np.uint8)
            if img.shape[:2] != (TESELA, TESELA):
                continue
            y0, x0 = fila * TESELA, col * TESELA
            salida[y0:y0 + TESELA, x0:x0 + TESELA] = img
            con_dato += int((img.sum(axis=2) > 12).any())
    cobertura = float((salida.sum(axis=2) > 12).mean())
    print(f"  {d}: {con_dato} teselas con dato | cobertura {cobertura * 100:.1f} %")
    return salida if cobertura > 0.01 else None


def componer_globo(equirect, px: int, centro, escala: float, args):
    """Equirectangular -> disco Orthographic RGBA."""
    alto, ancho = equirect.shape[:2]
    lat_vals = 90.0 - (np.arange(alto) + 0.5) * 180.0 / alto
    lon_vals = -180.0 + (np.arange(ancho) + 0.5) * 360.0 / ancho

    lon, lat, rho, dentro = ortho_inverso(px, escala, centro)
    rgb = {}
    for k, nombre in enumerate(("rojo", "verde", "azul")):
        campo = equirect[..., k].astype(np.float32) / 255.0
        rgb[nombre] = muestrear(campo, lat_vals, lon_vals, lon, lat)
    del lon, lat

    pila = np.dstack([rgb["rojo"], rgb["verde"], rgb["azul"]]).astype(np.float32)
    pila = np.nan_to_num(pila, nan=0.0)
    if args.saturacion != 1.0:
        lum = 0.2126 * pila[..., 0] + 0.7152 * pila[..., 1] + 0.0722 * pila[..., 2]
        pila = lum[..., None] + (pila - lum[..., None]) * args.saturacion
    if args.gamma != 1.0:
        pila = np.clip(pila, 0.0, 1.0) ** args.gamma

    rgb8 = np.clip(pila * 255.0, 0, 255).astype(np.uint8)
    alfa = np.clip((1.0 - rho) * (px / 2.0) / 1.5, 0.0, 1.0) * dentro
    alfa = (alfa * 255).astype(np.uint8)
    return np.dstack([rgb8, alfa])


def dibujar(disco, titulo, subtitulo, fuente, args, px):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"]})
    lado_in = 10.4
    disco_in = 0.97 * lado_in
    dpi = args.dpi or (px / disco_in)
    g = disco_in / lado_in
    fig = plt.figure(figsize=(lado_in, lado_in), dpi=dpi)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([(1 - g) / 2, (1 - g) / 2, g, g])
    ax.set_xlim(-1.0, 1.0)
    ax.set_ylim(-1.0, 1.0)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_facecolor("none")
    ax.imshow(disco, origin="upper", extent=[-1, 1, -1, 1],
              interpolation="none", zorder=2)

    fig.text(0.016, 0.984, titulo, ha="left", va="top", fontsize=13.0, color=INK,
             fontfamily="Segoe UI")
    fig.text(0.016, 0.957, subtitulo.upper(), ha="left", va="top", fontsize=8.6,
             color=INK_SOFT, fontfamily="Segoe UI")
    fig.text(0.016, 0.016, fuente, ha="left", va="bottom", fontsize=7.4,
             color=INK_FAINT, fontfamily="Segoe UI")
    if args.credito:
        fig.text(0.984, 0.016, args.credito, ha="right", va="bottom", fontsize=7.8,
                 color=INK_FAINT, fontfamily="Segoe UI")
    return fig


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Póster de color real de PACE/OCI desde OCI_PACE_True_Color (GIBS).")
    ap.add_argument("--hasta", default="2026-10-24", help="último día del compuesto")
    ap.add_argument("--dias", type=int, default=8, help="días hacia atrás a combinar")
    ap.add_argument("--nivel", type=int, default=NIVEL, help=f"nivel WMTS (default {NIVEL})")
    ap.add_argument("--px", type=int, default=PX, help=f"diámetro del globo (default {PX})")
    ap.add_argument("--dpi", type=int, default=None)
    ap.add_argument("--centro", nargs=2, type=float, metavar=("LON", "LAT"),
                    default=list(CENTRO))
    ap.add_argument("--escala", type=float, default=1.0)
    ap.add_argument("--saturacion", type=float, default=SATURACION)
    ap.add_argument("--gamma", type=float, default=GAMMA)
    ap.add_argument("--credito", default=CREDITO)
    ap.add_argument("--out", help="PNG de salida")
    args = ap.parse_args(argv)

    nivel = args.nivel
    cols, filas = _matriz(nivel)
    ancho, alto = cols * TESELA, filas * TESELA

    fin = date.fromisoformat(args.hasta)
    dias = [fin - timedelta(days=i) for i in range(args.dias)]
    print(f"PACE true color: {len(dias)} día(s) hasta {fin} | nivel {nivel} "
          f"({ancho}x{alto} px) | globo {args.px} px")

    equirect = None
    for d in dias:
        mosaico = mosaico_dia(d, nivel, ancho, alto)
        if mosaico is None:
            continue
        if equirect is None:
            equirect = mosaico
        else:
            vacio = equirect.sum(axis=2) <= 12
            equirect[vacio] = mosaico[vacio]
        faltan = float((equirect.sum(axis=2) <= 12).mean())
        print(f"    acumulado: {100 * (1 - faltan):.1f} % del planeta con dato")
        if faltan < 0.02:
            break
    if equirect is None:
        raise SystemExit("Ningún día devolvió datos. Revisá --hasta/--dias.")

    cabecera = f"{dias[-1]:%Y-%m-%d} a {fin:%Y-%m-%d}"
    disco = componer_globo(equirect, args.px, tuple(args.centro), args.escala, args)
    fig = dibujar(disco, "PACE · OCI true color",
                  f"{cabecera} · OCI 670/555/443 nm",
                  "SOURCE: NASA GIBS · OCI_PACE_True_Color · L2 rhos", args, args.px)

    out = Path(args.out) if args.out else (
        SALIDAS / f"poster_PACE_truecolor_{fin:%Y%m%d}_{args.px}px.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    parcial = out.with_suffix(".png.parcial")
    fig.savefig(parcial, format="png", facecolor=BG)
    import matplotlib.pyplot as plt
    plt.close(fig)
    parcial.replace(out)
    print(f"PNG: {out}  ({out.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
