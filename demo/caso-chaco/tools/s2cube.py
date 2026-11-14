"""Sentinel-2 L2A con el flujo del cuaderno de EY: stac_load + mediana + indices.

Sigue el mismo camino que `Sentinel2_GeoTIFF.ipynb`:
  1. pystac_client.search sobre el catalogo de Planetary Computer.
  2. planetary_computer.sign y odc.stac.stac_load a 10 m en EPSG:4326.
  3. Mascara de nubes con la banda SCL, pixel por escena.
  4. Mediana temporal (elimina nubes estadisticamente).
  5. NDVI / NDBI / NDWI, GeoTIFF y PNG.

odc-stac no esta en el entorno del pipeline: se carga desde una carpeta aparte
para no tocar el .venv del repo.

Uso:
    .venv\\Scripts\\python.exe demo\\caso-chaco\\tools\\s2cube.py ^
        --antes 2026-01-22 --despues 2026-03-27 ^
        --bbox "-61.12896,-20.856085,-61.062527,-20.81036" ^
        --out-dir D:\\temp\\caso\\cubo
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

EXTRA = Path(r"D:\temp\py-odc")
if EXTRA.is_dir():
    sys.path.insert(0, str(EXTRA))

import matplotlib
import numpy as np
import planetary_computer as pc
import pystac_client
import rasterio
from odc.stac import stac_load
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "comun"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import optico  # noqa: E402
from s2cambio import caja  # noqa: E402

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
BANDAS = ["B02", "B03", "B04", "B08", "B11"]
RESOLUCION = 10 / 111320.0  # 10 m expresados en grados


def cubo(bbox, centro: date, dias: int, nubes: float):
    cliente = pystac_client.Client.open(STAC)
    desde = centro - timedelta(days=dias)
    hasta = centro + timedelta(days=dias)
    busqueda = cliente.search(
        bbox=bbox,
        datetime=f"{desde}/{hasta}",
        collections=["sentinel-2-l2a"],
        query={"eo:cloud_cover": {"lt": float(nubes)}},
    )
    items = list(busqueda.items())
    if not items:
        raise SystemExit(f"Sin Sentinel-2 cerca de {centro}.")
    print(f"  {len(items)} escena(s) para {centro}")

    datos = stac_load(
        items,
        bands=BANDAS + ["SCL"],
        crs="EPSG:4326",
        resolution=RESOLUCION,
        chunks=None,
        dtype="uint16",
        patch_url=pc.sign,
        bbox=bbox,
    )

    valida = optico.mascara_scl(datos["SCL"].values)
    for banda in BANDAS:
        arreglo = datos[banda].values.astype(np.float32)
        arreglo[~valida] = np.nan
        datos[banda] = (datos[banda].dims, arreglo)

    mediana = datos[BANDAS].median(dim="time", skipna=True)
    return mediana, len(items)


def indices(mediana):
    rojo = mediana["B04"].values
    verde = mediana["B03"].values
    nir = mediana["B08"].values
    swir = mediana["B11"].values
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


def guardar(capa, ruta: Path, escala: int = 2):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    img = Image.fromarray((np.clip(capa, 0, 1) * 255).astype(np.uint8))
    if escala > 1:
        img = img.resize((img.width * escala, img.height * escala), Image.LANCZOS)
    img.save(ruta, "PNG", optimize=True)


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

    print(f"cubo {antes} -> {despues}")
    med_a, n_a = cubo(bbox, antes, args.dias, args.nubes)
    med_d, n_d = cubo(bbox, despues, args.dias, args.nubes)

    alto = med_a["B04"].shape[0]
    ancho = med_a["B04"].shape[1]
    print(f"  grilla {ancho}x{alto}")

    ndvi_a, ndbi_a, ndwi_a = indices(med_a)
    ndvi_d, ndbi_d, ndwi_d = indices(med_d)

    # RGB con el mismo estiramiento en las dos fechas.
    def rgb_de(med):
        capas = np.dstack([med[k].values for k in ("B04", "B03", "B02")]).astype(np.float32) / 10000.0
        return capas

    rgb_a_raw, rgb_d_raw = rgb_de(med_a), rgb_de(med_d)
    validos = np.concatenate([rgb_a_raw[np.isfinite(rgb_a_raw)], rgb_d_raw[np.isfinite(rgb_d_raw)]])
    bajo, alto_r = np.percentile(validos, [2, 98])
    def estirar(x):
        return np.clip((np.nan_to_num(x, nan=0.0) - bajo) / max(alto_r - bajo, 1e-6), 0, 1) ** (1 / 1.15)

    rgb_a = estirar(rgb_a_raw)
    rgb_d = estirar(rgb_d_raw)

    guardar(rgb_a, salida / "rgb_antes.png")
    guardar(rgb_d, salida / "rgb_despues.png")
    guardar(colorear(ndvi_a, "RdYlGn", -0.2, 0.9), salida / "ndvi_antes.png")
    guardar(colorear(ndvi_d, "RdYlGn", -0.2, 0.9), salida / "ndvi_despues.png")
    guardar(colorear(ndvi_d - ndvi_a, "RdBu", -0.6, 0.6), salida / "delta_ndvi.png")
    guardar(colorear(ndbi_d - ndbi_a, "RdBu", -0.4, 0.4), salida / "delta_ndbi.png")
    guardar(colorear(ndwi_d - ndwi_a, "RdBu", -0.4, 0.4), salida / "delta_ndwi.png")

    # GeoTIFF con las bandas medianas.
    for nombre, med in (("bandas_antes.tif", med_a), ("bandas_despues.tif", med_d)):
        lon = med["longitude"].values if "longitude" in med.coords else med["x"].values
        lat = med["latitude"].values if "latitude" in med.coords else med["y"].values
        ancho_px = lon[1] - lon[0]
        alto_px = lat[1] - lat[0]
        transform = rasterio.transform.from_origin(
            float(lon.min() - ancho_px / 2), float(lat.max() - alto_px / 2), float(ancho_px), float(abs(alto_px))
        )
        with rasterio.open(
            salida / nombre, "w", driver="GTiff", height=med["B04"].shape[0],
            width=med["B04"].shape[1], count=len(BANDAS), dtype="float32",
            crs="EPSG:4326", transform=transform, nodata=np.nan, compress="deflate",
        ) as dst:
            for i, banda in enumerate(BANDAS, start=1):
                dst.write(med[banda].values.astype(np.float32), i)
                dst.set_band_description(i, banda)

    try:
        fuente = ImageFont.truetype("arial.ttf", 16)
        chica = ImageFont.truetype("arial.ttf", 12)
    except OSError:
        fuente = ImageFont.load_default()
        chica = fuente

    paneles = [
        panel(rgb_a, f"color {antes}", fuente),
        panel(rgb_d, f"color {despues}", fuente),
        panel(colorear(ndvi_d - ndvi_a, "RdBu", -0.6, 0.6), "delta NDVI", fuente),
        panel(colorear(ndbi_d - ndbi_a, "RdBu", -0.4, 0.4), "delta NDBI", fuente),
        panel(colorear(ndwi_d - ndwi_a, "RdBu", -0.4, 0.4), "delta NDWI", fuente),
        panel(colorear(ndvi_d, "RdYlGn", -0.2, 0.9), f"NDVI {despues}", fuente),
    ]
    sep = 6
    pw, ph = paneles[0].width, paneles[0].height
    lienzo = Image.new("RGB", (pw * 3 + sep * 2, ph * 2 + sep + 34), (8, 8, 10))
    for i, p in enumerate(paneles):
        fila, col = divmod(i, 3)
        lienzo.paste(p, (col * (pw + sep), fila * (ph + sep)))
    ImageDraw.Draw(lienzo).text(
        (8, ph * 2 + sep + 8),
        "Sentinel-2 L2A 10 m | mediana temporal | rojo = caida, azul = suba | "
        "NDVI (B08,B04) | NDBI (B11,B08) | NDWI (B03,B08)",
        fill=(150, 150, 160), font=chica,
    )
    lienzo.save(salida / "indices.png", "PNG", optimize=True)

    datos = {
        "sensor": "Sentinel-2 L2A (odc.stac)",
        "antes": {"fecha": antes.isoformat(), "escenas": n_a},
        "despues": {"fecha": despues.isoformat(), "escenas": n_d},
        "bbox": list(bbox),
        "grilla": {"alto": int(alto), "ancho": int(ancho), "resolucion_m": 10},
        "ndvi": [round(float(np.nanmean(ndvi_a)), 3), round(float(np.nanmean(ndvi_d)), 3)],
        "ndbi": [round(float(np.nanmean(ndbi_a)), 3), round(float(np.nanmean(ndbi_d)), 3)],
        "ndwi": [round(float(np.nanmean(ndwi_a)), 3), round(float(np.nanmean(ndwi_d)), 3)],
    }
    (salida / "datos.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"listo: {salida}")
    print(f"  NDVI {datos['ndvi']} | NDBI {datos['ndbi']} | NDWI {datos['ndwi']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
