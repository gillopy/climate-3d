"""Comparacion en color real (Sentinel-2 L2A) de dos fechas, con la perdida encima.

Compone un RGB mediano por fecha leyendo B04/B03/B02, calcula NDVI con B08,
enmascara nubes con SCL y arma una figura de tres paneles: antes, despues, y
despues con la perdida de dosel en rojo. Es la evidencia visual del cambio que
detecta el analisis de NDVI.

Uso:
    .venv\\Scripts\\python.exe demo\\caso-chaco\\tools\\s2rgb.py ^
        --antes 2025-07-03 --despues 2025-10-31 ^
        --bbox "-55.444565,-24.066058,-55.321484,-23.995819" ^
        --mascara-geojson demo\\caso-chaco\\datos\\mbaracayu.geojson ^
        --out D:\\temp\\caso\\color.png
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date
from pathlib import Path

import numpy as np
from affine import Affine
from PIL import Image, ImageDraw, ImageFont
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "comun"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import optico  # noqa: E402
import planetary_computer as pc  # noqa: E402
import sentinel2  # noqa: E402
from s2cambio import area_pixel_m2, caja, grilla, mascara_poligono, mayoria  # noqa: E402

COLOR = ("B04", "B03", "B02")
TODAS = COLOR + ("B08",)


def _banda(item, clave, bbox, forma, transform, crs, px):
    with rasterio.open(item.assets[clave].href) as src:
        ventana = sentinel2._ventana(src, bbox)
        escala = max(1, int(math.ceil(max(ventana.width, ventana.height) / max(1, int(px * 1.5)))))
        alto = max(1, int(round(ventana.height / escala)))
        ancho = max(1, int(round(ventana.width / escala)))
        datos = src.read(1, window=ventana, out_shape=(alto, ancho),
                         resampling=Resampling.bilinear).astype(np.float32)
        origen = src.window_transform(ventana) * Affine.scale(ventana.width / ancho, ventana.height / alto)
        crs_origen = src.crs

    destino = np.full(forma, np.nan, dtype=np.float32)
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


def _scl(item, bbox, forma):
    with rasterio.open(item.assets["SCL"].href) as src:
        ventana = sentinel2._ventana(src, bbox)
        return src.read(1, window=ventana, out_shape=forma, resampling=Resampling.nearest)


def leer(bbox, centro: date, dias: int, nubes: float, px: int):
    forma, transform, crs = grilla(bbox, px)
    items = sentinel2.buscar_items(bbox, centro, dias, nubes, max_items=8)
    if not items:
        raise SystemExit(f"Sin Sentinel-2 cerca de {centro}.")

    rgb_pila = []
    ndvi_pila = []
    usados = []
    for item in items:
        firmado = pc.sign(item)
        try:
            capas = [_banda(firmado, clave, bbox, forma, transform, crs, px) for clave in TODAS]
            scl = _scl(firmado, bbox, forma)
        except Exception as exc:  # noqa: BLE001
            print(f"  {item.id}: {exc}")
            continue
        valida = optico.mascara_scl(scl)
        rojo, verde, azul, nir = capas
        for capa in capas:
            capa[~valida] = np.nan
        nd = optico.ndvi(rojo, nir)
        nd[~valida] = np.nan
        rgb_pila.append(np.dstack([rojo, verde, azul]))
        ndvi_pila.append(nd)
        usados.append(round(float(item.properties.get("eo:cloud_cover", 100.0)), 1))
        print(f"  {item.id}: {usados[-1]}% nubes")

    if not rgb_pila:
        raise SystemExit("Ningun item dejo pixeles validos.")

    with np.errstate(invalid="ignore"):
        rgb = np.nanmedian(np.stack(rgb_pila, axis=0), axis=0)
        ndvi = np.nanmedian(np.stack(ndvi_pila, axis=0), axis=0)
    return rgb, ndvi, usados, forma, transform


def rango_comun(*capas):
    """Percentiles 2-98 sobre todas las fechas juntas: mismo estiramiento para ambas."""
    validos = np.concatenate([c[np.isfinite(c)] for c in capas])
    if validos.size == 0:
        return (0.0, 1.0)
    bajo, alto = np.percentile(validos, [2, 98])
    if alto <= bajo:
        alto = bajo + 1e-6
    return (float(bajo), float(alto))


def estirar(rgb, rango):
    bajo, alto = rango
    salida = np.clip((np.nan_to_num(rgb, nan=0.0) - bajo) / (alto - bajo), 0, 1)
    return salida ** (1 / 1.15)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--antes", required=True)
    ap.add_argument("--despues", required=True)
    ap.add_argument("--bbox", required=True)
    ap.add_argument("--mascara-geojson", default=None)
    ap.add_argument("--min-ndvi", type=float, default=0.25)
    ap.add_argument("--umbral", type=float, default=0.16)
    ap.add_argument("--dias", type=int, default=15)
    ap.add_argument("--nubes", type=float, default=25.0)
    ap.add_argument("--px", type=int, default=1000)
    ap.add_argument("--out", required=True)
    ap.add_argument("--datos", default=None)
    args = ap.parse_args()

    bbox = caja(args.bbox)
    antes = date.fromisoformat(args.antes)
    despues = date.fromisoformat(args.despues)

    print(f"RGB {antes} -> {despues}")
    rgb_a, nd_a, usados_a, forma, transform = leer(bbox, antes, args.dias, args.nubes, args.px)
    rgb_d, nd_d, usados_d, _, _ = leer(bbox, despues, args.dias, args.nubes, args.px)

    delta = nd_d - nd_a
    valido = np.isfinite(delta)
    poligono = None
    borde = None
    if args.mascara_geojson:
        poligono = mascara_poligono(args.mascara_geojson, forma, transform)
        datos_geo = json.loads(Path(args.mascara_geojson).read_text(encoding="utf-8-sig"))
        geom = datos_geo.get("geometry", datos_geo)
        borde = geom["coordinates"][0] if geom.get("type") == "Polygon" else geom["coordinates"][0][0]
        bosque = valido & poligono & (nd_a > args.min_ndvi)
    else:
        bosque = valido & (nd_a > 0.5)
    perdida = mayoria(valido & bosque & (delta < -args.umbral)) & valido

    rango = rango_comun(rgb_a, rgb_d)
    antes8 = estirar(rgb_a, rango)
    despues8 = estirar(rgb_d, rango)
    con_rojo = despues8.copy()
    rojo = np.array([1.0, 0.22, 0.10])
    con_rojo[perdida] = con_rojo[perdida] * 0.15 + rojo * 0.85

    try:
        fuente = ImageFont.truetype("arial.ttf", 16)
        chica = ImageFont.truetype("arial.ttf", 12)
    except OSError:
        fuente = ImageFont.load_default()
        chica = fuente

    ancho, alto = antes8.shape[1], antes8.shape[0]
    extra = 32
    separacion = 6
    lienzo = Image.new("RGB", (ancho * 3 + separacion * 2, alto + extra + 28), (8, 8, 10))
    dibujo = ImageDraw.Draw(lienzo)

    for i, (capa, etiqueta) in enumerate((
        (antes8, f"{antes.isoformat()}"),
        (despues8, f"{despues.isoformat()}"),
        (con_rojo, "perdida de dosel en rojo"),
    )):
        x = i * (ancho + separacion)
        lienzo.paste(Image.fromarray((capa * 255).astype(np.uint8)), (x, extra))
        dibujo.text((x + 8, 8), etiqueta, fill=(236, 236, 241), font=fuente)

    if borde:
        puntos = []
        for lon, lat in borde:
            col, fila = ~transform * (lon, lat)
            puntos.append((col + 2 * (ancho + separacion), fila + extra))
        if len(puntos) > 2:
            dibujo.line(puntos, fill=(90, 180, 255), width=2)

    dibujo.text(
        (8, alto + extra + 4),
        f"Sentinel-2 L2A, color real, mediana de la ventana | nubes enmascaradas con SCL | "
        f"perdida {float(perdida.sum()) * area_pixel_m2(bbox, perdida.shape) / 10000:.1f} ha a umbral {args.umbral:g}",
        fill=(150, 150, 160), font=chica,
    )

    salida = Path(args.out)
    salida.parent.mkdir(parents=True, exist_ok=True)
    lienzo.save(salida, "PNG", optimize=True)

    if args.datos:
        Path(args.datos).write_text(
            "window.COLOR = " + json.dumps({
                "antes": antes.isoformat(),
                "despues": despues.isoformat(),
                "bbox": list(bbox),
                "items_antes": usados_a,
                "items_despues": usados_d,
                "px": args.px,
                "mascara_geojson": args.mascara_geojson,
            }, ensure_ascii=False, indent=2) + ";\n",
            encoding="utf-8",
        )

    print(f"listo: {salida} ({lienzo.width}x{lienzo.height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
