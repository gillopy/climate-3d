"""Prueba con Sentinel-2 L1C (techo de atmosfera, sin mascara de nubes).

Lee los JP2 de Earth Search por S3 anonimo (`AWS_NO_SIGN_REQUEST=YES`), arma la
mediana temporal SIN enmascarar nubes y renderiza RGB + NDVI. Sirve para comparar
contra el L2A, que si trae la capa SCL.

Uso:
    .venv\\Scripts\\python.exe demo\\caso-chaco\\tools\\s2l1c.py ^
        --antes 2026-01-22 --despues 2026-03-27 ^
        --bbox "-61.12896,-20.856085,-61.062527,-20.81036" ^
        --out-dir D:\\temp\\caso\\l1c
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path

os.environ.setdefault("AWS_NO_SIGN_REQUEST", "YES")

import matplotlib
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds
from PIL import Image, ImageDraw, ImageFont
from pystac_client import Client

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "comun"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from s2cambio import caja  # noqa: E402

STAC = "https://earth-search.aws.element84.com/v1"
COLOR = ("red", "green", "blue")
TODAS = COLOR + ("nir",)


def _ventana(src, bbox):
    b = transform_bounds("EPSG:4326", src.crs, *bbox)
    return rasterio.windows.from_bounds(*b, transform=src.transform)


def grilla(item, bbox):
    with rasterio.open(item.assets["red"].href) as src:
        ventana = _ventana(src, bbox)
        return (int(round(ventana.height)), int(round(ventana.width)),
                src.window_transform(ventana), src.crs)


def leer(item, clave, bbox, alto, ancho, transform, crs):
    with rasterio.open(item.assets[clave].href) as src:
        ventana = _ventana(src, bbox)
        return src.read(1, window=ventana, out_shape=(alto, ancho),
                        resampling=Resampling.bilinear).astype(np.float32) / 10000.0


def compuesto(bbox, centro: date, dias: int, nubes: float):
    cliente = Client.open(STAC)
    bus = cliente.search(collections=["sentinel-2-l1c"], bbox=bbox,
                         datetime=f"{centro - timedelta(days=dias)}/{centro + timedelta(days=dias)}",
                         query={"eo:cloud_cover": {"lt": float(nubes)}})
    items = list(bus.items())
    if not items:
        raise SystemExit(f"Sin L1C cerca de {centro}.")
    print(f"  L1C: {len(items)} escena(s)")

    alto, ancho, transform, crs = grilla(items[0], bbox)
    pilas = {k: [] for k in TODAS}
    for item in items:
        try:
            for clave in TODAS:
                pilas[clave].append(leer(item, clave, bbox, alto, ancho, transform, crs))
        except Exception as exc:  # noqa: BLE001
            print(f"  {item.id}: {exc}")

    if not pilas["red"]:
        raise SystemExit("Ningun item dejo pixeles validos.")

    comp = {}
    for clave in TODAS:
        pila = np.stack(pilas[clave], axis=0)
        con_dato = np.where(pila > 0, pila, np.nan)
        with np.errstate(invalid="ignore"):
            comp[clave] = np.nanmedian(con_dato, axis=0)
    print(f"  grilla {ancho}x{alto} | {len(pilas['red'])} usadas")
    return comp, len(pilas["red"]), alto, ancho


def colorear(capa, cmap, vmin, vmax):
    mapa = matplotlib.colormaps[cmap]
    norma = np.clip((np.nan_to_num(capa, nan=vmin) - vmin) / (vmax - vmin), 0, 1)
    rgb = mapa(norma)[..., :3]
    rgb[~np.isfinite(capa)] = 0.0
    return rgb


def guardar(capa, ruta: Path, escala: int = 2):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    img = Image.fromarray((np.clip(capa, 0, 1) * 255).astype(np.uint8))
    if escala > 1:
        img = img.resize((img.width * escala, img.height * escala), Image.LANCZOS)
    img.save(ruta, "PNG", optimize=True)
    return img


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--antes", required=True)
    ap.add_argument("--despues", required=True)
    ap.add_argument("--bbox", required=True)
    ap.add_argument("--dias", type=int, default=15)
    ap.add_argument("--nubes", type=float, default=35.0)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    bbox = caja(args.bbox)
    antes = date.fromisoformat(args.antes)
    despues = date.fromisoformat(args.despues)
    salida = Path(args.out_dir)
    salida.mkdir(parents=True, exist_ok=True)

    print(f"L1C {antes} -> {despues}")
    a, n_a, _, _ = compuesto(bbox, antes, args.dias, args.nubes)
    d, n_d, _, _ = compuesto(bbox, despues, args.dias, args.nubes)

    rgb_a_raw = np.dstack([a["red"], a["green"], a["blue"]])
    rgb_d_raw = np.dstack([d["red"], d["green"], d["blue"]])
    validos = np.concatenate([rgb_a_raw[np.isfinite(rgb_a_raw)], rgb_d_raw[np.isfinite(rgb_d_raw)]])
    bajo, alto = np.percentile(validos, [2, 98])
    def estirar(x):
        return np.clip((np.nan_to_num(x, nan=0.0) - bajo) / max(alto - bajo, 1e-6), 0, 1) ** (1 / 1.15)

    guardar(estirar(rgb_a_raw), salida / "rgb_antes.png")
    guardar(estirar(rgb_d_raw), salida / "rgb_despues.png")

    ndvi_a = (a["nir"] - a["red"]) / (a["nir"] + a["red"] + 1e-6)
    ndvi_d = (d["nir"] - d["red"]) / (d["nir"] + d["red"] + 1e-6)
    guardar(colorear(ndvi_a, "RdYlGn", -0.2, 0.9), salida / "ndvi_antes.png")
    guardar(colorear(ndvi_d, "RdYlGn", -0.2, 0.9), salida / "ndvi_despues.png")

    print(f"listo: {salida} | escenas {n_a} / {n_d} | NDVI medio {np.nanmean(ndvi_a):.3f} -> {np.nanmean(ndvi_d):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
