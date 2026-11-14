"""Indices espectrales de Sentinel-2 L2A: NDVI, NDBI y NDWI, antes y despues.

Lee B04/B03/B08/B11, compone por mediana, enmascara nubes con SCL y escribe:
- un PNG por indice y fecha,
- un PNG por delta,
- una figura 2x3 con el color real y los tres cambios.

Uso:
    .venv\\Scripts\\python.exe demo\\caso-chaco\\tools\\s2indices.py ^
        --antes 2026-01-22 --despues 2026-03-27 ^
        --bbox "-61.12896,-20.856085,-61.062527,-20.81036" ^
        --out-dir D:\\temp\\caso\\indices
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import matplotlib
import numpy as np
import planetary_computer as pc
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "comun"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import optico  # noqa: E402
import sentinel2  # noqa: E402
from s2cambio import caja, grilla  # noqa: E402
from s2rgb import _banda, _scl, estirar, rango_comun  # noqa: E402

BANDAS = ("B04", "B03", "B08", "B11")


def leer(bbox, centro: date, dias: int, nubes: float, px: int):
    forma, transform, crs = grilla(bbox, px)
    items = sentinel2.buscar_items(bbox, centro, dias, nubes, max_items=8)
    if not items:
        raise SystemExit(f"Sin Sentinel-2 cerca de {centro}.")

    rgb_pila, ndvi_pila, ndbi_pila, ndwi_pila = [], [], [], []
    usados = []
    for item in items:
        firmado = pc.sign(item)
        try:
            capas = [_banda(firmado, clave, bbox, forma, transform, crs, px) for clave in BANDAS]
            scl = _scl(firmado, bbox, forma)
        except Exception as exc:  # noqa: BLE001
            print(f"  {item.id}: {exc}")
            continue
        valida = optico.mascara_scl(scl)
        rojo, verde, nir, swir = capas
        for capa in capas:
            capa[~valida] = np.nan
        ndvi = (nir - rojo) / (nir + rojo + 1e-6)
        ndbi = (swir - nir) / (swir + nir + 1e-6)
        ndwi = (verde - nir) / (verde + nir + 1e-6)
        ndvi[~valida] = np.nan
        ndbi[~valida] = np.nan
        ndwi[~valida] = np.nan
        ndvi_pila.append(ndvi)
        ndbi_pila.append(ndbi)
        ndwi_pila.append(ndwi)
        usados.append({"fecha": item.datetime.strftime("%Y-%m-%d"),
                       "nubes": round(float(item.properties.get("eo:cloud_cover", 100.0)), 1)})
        print(f"  {item.datetime:%Y-%m-%d} | nubes {usados[-1]['nubes']}%")

    if not ndvi_pila:
        raise SystemExit("Ningun item dejo pixeles validos.")

    with np.errstate(invalid="ignore"):
        ndvi = np.nanmedian(np.stack(ndvi_pila, axis=0), axis=0)
        ndbi = np.nanmedian(np.stack(ndbi_pila, axis=0), axis=0)
        ndwi = np.nanmedian(np.stack(ndwi_pila, axis=0), axis=0)
    return ndvi, ndbi, ndwi, usados, forma, transform


def colorear(capa, cmap, vmin, vmax):
    mapa = matplotlib.colormaps[cmap]
    norma = np.clip((np.nan_to_num(capa, nan=vmin) - vmin) / (vmax - vmin), 0, 1)
    rgb = mapa(norma)[..., :3]
    rgb[~np.isfinite(capa)] = 0.0
    return rgb


def guardar(capa, ruta: Path):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((np.clip(capa, 0, 1) * 255).astype(np.uint8)).save(ruta, "PNG", optimize=True)


def panel(rgb, etiqueta, fuente):
    img = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))
    lienzo = Image.new("RGB", (img.width, img.height + 28), (8, 8, 10))
    lienzo.paste(img, (0, 28))
    ImageDraw.Draw(lienzo).text((8, 7), etiqueta, fill=(236, 236, 241), font=fuente)
    return lienzo


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--antes", required=True)
    ap.add_argument("--despues", required=True)
    ap.add_argument("--bbox", required=True)
    ap.add_argument("--dias", type=int, default=15)
    ap.add_argument("--nubes", type=float, default=35.0)
    ap.add_argument("--px", type=int, default=900)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    bbox = caja(args.bbox)
    antes = date.fromisoformat(args.antes)
    despues = date.fromisoformat(args.despues)
    salida = Path(args.out_dir)
    salida.mkdir(parents=True, exist_ok=True)

    print(f"indices {antes} -> {despues}")
    ndvi_a, ndbi_a, ndwi_a, usados_a, forma, transform = leer(bbox, antes, args.dias, args.nubes, args.px)
    ndvi_d, ndbi_d, ndwi_d, usados_d, _, _ = leer(bbox, despues, args.dias, args.nubes, args.px)

    d_ndvi = ndvi_d - ndvi_a
    d_ndbi = ndbi_d - ndbi_a
    d_ndwi = ndwi_d - ndwi_a

    guardar(colorear(ndvi_a, "RdYlGn", -0.2, 0.9), salida / "ndvi_antes.png")
    guardar(colorear(ndvi_d, "RdYlGn", -0.2, 0.9), salida / "ndvi_despues.png")
    guardar(colorear(d_ndvi, "RdBu", -0.6, 0.6), salida / "delta_ndvi.png")
    guardar(colorear(d_ndbi, "RdBu", -0.5, 0.5), salida / "delta_ndbi.png")
    guardar(colorear(d_ndwi, "RdBu", -0.5, 0.5), salida / "delta_ndwi.png")

    try:
        fuente = ImageFont.truetype("arial.ttf", 16)
        chica = ImageFont.truetype("arial.ttf", 12)
    except OSError:
        fuente = ImageFont.load_default()
        chica = fuente

    paneles = [
        panel(colorear(ndvi_a, "RdYlGn", -0.2, 0.9), f"NDVI {usados_a[0]['fecha']}", fuente),
        panel(colorear(ndvi_d, "RdYlGn", -0.2, 0.9), f"NDVI {usados_d[0]['fecha']}", fuente),
        panel(colorear(d_ndvi, "RdBu", -0.6, 0.6), "delta NDVI", fuente),
        panel(colorear(d_ndbi, "RdBu", -0.5, 0.5), "delta NDBI", fuente),
        panel(colorear(d_ndwi, "RdBu", -0.5, 0.5), "delta NDWI", fuente),
    ]

    sep = 6
    columnas = 3
    filas = 2
    ancho = paneles[0].width
    alto = paneles[0].height
    lienzo = Image.new("RGB", (ancho * columnas + sep * (columnas - 1),
                               alto * filas + sep + 34), (8, 8, 10))
    for i, p in enumerate(paneles):
        fila, col = divmod(i, columnas)
        lienzo.paste(p, (col * (ancho + sep), fila * (alto + sep)))
    ImageDraw.Draw(lienzo).text(
        (8, alto * filas + sep + 8),
        "Sentinel-2 L2A | rojo = caida, azul = suba | NDVI (B08,B04) | NDBI (B11,B08) | NDWI (B03,B08)",
        fill=(150, 150, 160), font=chica,
    )
    lienzo.save(salida / "indices.png", "PNG", optimize=True)

    datos = {
        "sensor": "Sentinel-2 L2A",
        "antes": usados_a,
        "despues": usados_d,
        "bbox": list(bbox),
        "px": args.px,
        "ndvi_medio_antes": round(float(np.nanmean(ndvi_a)), 3),
        "ndvi_medio_despues": round(float(np.nanmean(ndvi_d)), 3),
        "ndbi_medio_antes": round(float(np.nanmean(ndbi_a)), 3),
        "ndbi_medio_despues": round(float(np.nanmean(ndbi_d)), 3),
        "ndwi_medio_antes": round(float(np.nanmean(ndwi_a)), 3),
        "ndwi_medio_despues": round(float(np.nanmean(ndwi_d)), 3),
    }
    (salida / "indices.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"listo: {salida} ({lienzo.width}x{lienzo.height})")
    print(f"  NDVI {datos['ndvi_medio_antes']} -> {datos['ndvi_medio_despues']}")
    print(f"  NDBI {datos['ndbi_medio_antes']} -> {datos['ndbi_medio_despues']}")
    print(f"  NDWI {datos['ndwi_medio_antes']} -> {datos['ndwi_medio_despues']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
