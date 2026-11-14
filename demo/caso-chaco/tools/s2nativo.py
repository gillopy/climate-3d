"""Sentinel-2 L2A a resolucion nativa: lee la ventana original y guarda GeoTIFF.

A diferencia de s2rgb/s2indices, este modulo NO reproyecta a una grilla en
grados: toma la ventana nativa en la UTM de origen (10 m por pixel para
B02/B03/B04/B08, 20 m para B11) y compone la mediana sin remuestrear.

Salidas:
    bandas_antes.tif   / bandas_despues.tif   (azul, verde, rojo, nir, swir)
    rgb_antes.png      / rgb_despues.png
    ndvi_antes.png     / ndvi_despues.png
    delta_ndvi.png / delta_ndbi.png / delta_ndwi.png
    indices.png        (figura 2x3)
    datos.json

Uso:
    .venv\\Scripts\\python.exe demo\\caso-chaco\\tools\\s2nativo.py ^
        --antes 2026-01-22 --despues 2026-03-27 ^
        --bbox "-61.12896,-20.856085,-61.062527,-20.81036" ^
        --out-dir D:\\temp\\caso\\nativo
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import matplotlib
import numpy as np
import planetary_computer as pc
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject, transform_bounds
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "comun"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import optico  # noqa: E402
import sentinel2  # noqa: E402
from s2cambio import caja  # noqa: E402
from s2rgb import estirar, rango_comun  # noqa: E402

BANDAS = ("B02", "B03", "B04", "B08", "B11")
NOMBRES = ("azul", "verde", "rojo", "nir", "swir")


def _ventana(src, bbox):
    b = transform_bounds("EPSG:4326", src.crs, *bbox)
    return rasterio.windows.from_bounds(*b, transform=src.transform)


def grilla_nativa(item, bbox):
    """Shape, transform y CRS de la ventana nativa del item."""
    with rasterio.open(item.assets["B04"].href) as src:
        ventana = _ventana(src, bbox)
        alto = int(round(ventana.height))
        ancho = int(round(ventana.width))
        transform = src.window_transform(ventana)
        return alto, ancho, transform, src.crs


def leer_banda(item, clave, bbox, alto, ancho, transform, crs):
    with rasterio.open(item.assets[clave].href) as src:
        ventana = _ventana(src, bbox)
        datos = src.read(1, window=ventana, out_shape=(alto, ancho),
                         resampling=Resampling.bilinear).astype(np.float32)
        origen = src.window_transform(ventana) * (
            rasterio.Affine.scale(ventana.width / ancho, ventana.height / alto))
        crs_origen = src.crs

    destino = np.full((alto, ancho), np.nan, dtype=np.float32)
    reproject(
        source=datos,
        destination=destino,
        src_transform=origen,
        src_crs=crs_origen,
        dst_transform=transform,
        dst_crs=crs,
        resampling=Resampling.bilinear,
        src_nodata=np.nan,
        dst_nodata=np.nan,
    )
    return destino


def leer_nativo(bbox, centro: date, dias: int, nubes: float):
    cliente_items = sentinel2.buscar_items(bbox, centro, dias, nubes, max_items=8)
    if not cliente_items:
        raise SystemExit(f"Sin Sentinel-2 cerca de {centro}.")

    alto, ancho, transform, crs = grilla_nativa(cliente_items[0], bbox)
    print(f"  grilla nativa: {ancho}x{alto} px | {crs}")

    pilas = {clave: [] for clave in BANDAS}
    usados = []
    for item in cliente_items:
        firmado = pc.sign(item)
        try:
            capas = {clave: leer_banda(firmado, clave, bbox, alto, ancho, transform, crs)
                     for clave in BANDAS}
            with rasterio.open(firmado.assets["SCL"].href) as src:
                ventana = _ventana(src, bbox)
                scl = src.read(1, window=ventana, out_shape=(alto, ancho),
                               resampling=Resampling.nearest)
        except Exception as exc:  # noqa: BLE001
            print(f"  {item.id}: {exc}")
            continue
        valida = optico.mascara_scl(scl)
        for clave in BANDAS:
            capas[clave][~valida] = np.nan
            pilas[clave].append(capas[clave])
        usados.append({"fecha": item.datetime.strftime("%Y-%m-%d"),
                       "nubes": round(float(item.properties.get("eo:cloud_cover", 100.0)), 1)})
        print(f"  {item.datetime:%Y-%m-%d} | nubes {usados[-1]['nubes']}%")

    if not usados:
        raise SystemExit("Ningun item dejo pixeles validos.")

    with np.errstate(invalid="ignore"):
        comp = {clave: np.nanmedian(np.stack(pilas[clave], axis=0), axis=0) for clave in BANDAS}
    return comp, usados, alto, ancho, transform, crs


def indices(comp):
    azul, verde, rojo, nir, swir = (comp[k] for k in BANDAS)
    ndvi = (nir - rojo) / (nir + rojo + 1e-6)
    ndbi = (swir - nir) / (swir + nir + 1e-6)
    ndwi = (verde - nir) / (verde + nir + 1e-6)
    return ndvi, ndbi, ndwi


def colorear(capa, cmap, vmin, vmax):
    mapa = matplotlib.colormaps[cmap]
    norma = np.clip((np.nan_to_num(capa, nan=vmin) - vmin) / (vmax - vmin), 0, 1)
    rgb = mapa(norma)[..., :3]
    rgb[~np.isfinite(capa)] = 0.0
    return rgb


def guardar_png(capa, ruta: Path, escala: int = 2):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    img = Image.fromarray((np.clip(capa, 0, 1) * 255).astype(np.uint8))
    if escala > 1:
        img = img.resize((img.width * escala, img.height * escala), Image.LANCZOS)
    img.save(ruta, "PNG", optimize=True)


def guardar_tif(comp, ruta: Path, transform, crs):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    alto = comp["azul"].shape[0]
    ancho = comp["azul"].shape[1]
    with rasterio.open(
        ruta, "w", driver="GTiff", height=alto, width=ancho, count=len(BANDAS),
        dtype="float32", crs=crs, transform=transform, nodata=np.nan, compress="deflate",
    ) as dst:
        for i, clave in enumerate(BANDAS, start=1):
            dst.write(comp[clave].astype(np.float32), i)
            dst.set_band_description(i, f"{clave} ({NOMBRES[i - 1]})")


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
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    bbox = caja(args.bbox)
    antes = date.fromisoformat(args.antes)
    despues = date.fromisoformat(args.despues)
    salida = Path(args.out_dir)
    salida.mkdir(parents=True, exist_ok=True)

    print(f"nativo {antes} -> {despues}")
    comp_a, usados_a, alto, ancho, transform, crs = leer_nativo(bbox, antes, args.dias, args.nubes)
    comp_d, usados_d, _, _, _, _ = leer_nativo(bbox, despues, args.dias, args.nubes)

    ndvi_a, ndbi_a, ndwi_a = indices(comp_a)
    ndvi_d, ndbi_d, ndwi_d = indices(comp_d)

    guardar_tif(comp_a, salida / "bandas_antes.tif", transform, crs)
    guardar_tif(comp_d, salida / "bandas_despues.tif", transform, crs)

    rango = rango_comun(
        np.dstack([comp_a["rojo"], comp_a["verde"], comp_a["azul"]]),
        np.dstack([comp_d["rojo"], comp_d["verde"], comp_d["azul"]]),
    )
    rgb_a = estirar(np.dstack([comp_a["rojo"], comp_a["verde"], comp_a["azul"]]), rango)
    rgb_d = estirar(np.dstack([comp_d["rojo"], comp_d["verde"], comp_d["azul"]]), rango)

    guardar_png(rgb_a, salida / "rgb_antes.png")
    guardar_png(rgb_d, salida / "rgb_despues.png")
    guardar_png(colorear(ndvi_a, "RdYlGn", -0.2, 0.9), salida / "ndvi_antes.png")
    guardar_png(colorear(ndvi_d, "RdYlGn", -0.2, 0.9), salida / "ndvi_despues.png")
    guardar_png(colorear(ndvi_d - ndvi_a, "RdBu", -0.6, 0.6), salida / "delta_ndvi.png")
    guardar_png(colorear(ndbi_d - ndbi_a, "RdBu", -0.5, 0.5), salida / "delta_ndbi.png")
    guardar_png(colorear(ndwi_d - ndwi_a, "RdBu", -0.5, 0.5), salida / "delta_ndwi.png")

    try:
        fuente = ImageFont.truetype("arial.ttf", 16)
        chica = ImageFont.truetype("arial.ttf", 12)
    except OSError:
        fuente = ImageFont.load_default()
        chica = fuente

    paneles = [
        panel(rgb_a, f"color {usados_a[0]['fecha']}", fuente),
        panel(rgb_d, f"color {usados_d[0]['fecha']}", fuente),
        panel(colorear(ndvi_a, "RdYlGn", -0.2, 0.9), f"NDVI {usados_a[0]['fecha']}", fuente),
        panel(colorear(ndvi_d, "RdYlGn", -0.2, 0.9), f"NDVI {usados_d[0]['fecha']}", fuente),
        panel(colorear(ndvi_d - ndvi_a, "RdBu", -0.6, 0.6), "delta NDVI", fuente),
        panel(colorear(ndbi_d - ndbi_a, "RdBu", -0.4, 0.4), "delta NDBI", fuente),
    ]
    sep = 6
    columnas, filas = 3, 2
    pw, ph = paneles[0].width, paneles[0].height
    lienzo = Image.new("RGB", (pw * columnas + sep * (columnas - 1),
                               ph * filas + sep + 34), (8, 8, 10))
    for i, p in enumerate(paneles):
        fila, col = divmod(i, columnas)
        lienzo.paste(p, (col * (pw + sep), fila * (ph + sep)))
    ImageDraw.Draw(lienzo).text(
        (8, ph * filas + sep + 8),
        "Sentinel-2 L2A nativo | rojo = caida, azul = suba | NDVI (B08,B04) | NDBI (B11,B08)",
        fill=(150, 150, 160), font=chica,
    )
    lienzo.save(salida / "indices.png", "PNG", optimize=True)

    datos = {
        "sensor": "Sentinel-2 L2A (nativo)",
        "antes": usados_a,
        "despues": usados_d,
        "bbox": list(bbox),
        "grilla": {"alto": alto, "ancho": ancho, "crs": str(crs)},
        "ndvi": [round(float(np.nanmean(ndvi_a)), 3), round(float(np.nanmean(ndvi_d)), 3)],
        "ndbi": [round(float(np.nanmean(ndbi_a)), 3), round(float(np.nanmean(ndbi_d)), 3)],
        "ndwi": [round(float(np.nanmean(ndwi_a)), 3), round(float(np.nanmean(ndwi_d)), 3)],
    }
    (salida / "datos.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"listo: {salida}")
    print(f"  grilla {ancho}x{alto} | NDVI {datos['ndvi']} | NDBI {datos['ndbi']} | NDWI {datos['ndwi']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
