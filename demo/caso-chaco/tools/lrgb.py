"""Comparacion en color real con Landsat 8/9 (C2 L2) de dos fechas.

Mismo esquema que s2rgb.py pero leyendo Landsat: bandas red/green/blue/nir08,
mascara de nubes con qa_pixel, escala de reflectancia superficial y compuesto
por mediana. Escribe la figura de tres paneles y los dos recortes limpios para
el deslizador.

Uso:
    .venv\\Scripts\\python.exe demo\\caso-chaco\\tools\\lrgb.py ^
        --antes 2026-01-22 --despues 2026-03-21 ^
        --bbox "-61.12896,-20.856085,-61.062527,-20.81036" ^
        --out-dir D:\\temp\\caso\\landsat
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
from pystac_client import Client
import planetary_computer as pc
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "comun"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import optico  # noqa: E402
from s2cambio import area_pixel_m2, caja, grilla, mayoria  # noqa: E402
from s2rgb import estirar, rango_comun  # noqa: E402

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
ESCALA = 0.0000275
OFFSET = -0.2
COLOR = ("red", "green", "blue")
TODAS = COLOR + ("nir08",)


def buscar(bbox, centro: date, dias: int, nubes: float, max_items: int = 6):
    from datetime import timedelta
    cliente = Client.open(STAC)
    desde = centro - timedelta(days=dias)
    hasta = centro + timedelta(days=dias)
    bus = cliente.search(
        collections=["landsat-c2-l2"],
        bbox=bbox,
        datetime=f"{desde}/{hasta}",
        query={"eo:cloud_cover": {"lt": float(nubes)}},
    )
    items = sorted(bus.items(), key=lambda i: abs((i.datetime.date() - centro).days))
    return items[:max_items]


def _ventana(src, bbox):
    from rasterio.warp import transform_bounds
    b = transform_bounds("EPSG:4326", src.crs, *bbox)
    return rasterio.windows.from_bounds(*b, transform=src.transform)


def _banda(item, clave, bbox, forma, transform, crs, px):
    with rasterio.open(item.assets[clave].href) as src:
        ventana = _ventana(src, bbox)
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
    return destino * ESCALA + OFFSET


def _limpio(item, bbox, forma):
    with rasterio.open(item.assets["qa_pixel"].href) as src:
        ventana = _ventana(src, bbox)
        qa = src.read(1, window=ventana, out_shape=forma, resampling=Resampling.nearest)
    malo = ((qa & 0b11110) != 0) | ((qa & 0b1) != 0)
    return ~malo


def leer(bbox, centro: date, dias: int, nubes: float, px: int):
    forma, transform, crs = grilla(bbox, px)
    items = buscar(bbox, centro, dias, nubes)
    if not items:
        raise SystemExit(f"Sin Landsat cerca de {centro}.")

    rgb_pila, ndvi_pila, usados = [], [], []
    for item in items:
        firmado = pc.sign(item)
        try:
            capas = [_banda(firmado, clave, bbox, forma, transform, crs, px) for clave in TODAS]
            limpio = _limpio(firmado, bbox, forma)
        except Exception as exc:  # noqa: BLE001
            print(f"  {item.id}: {exc}")
            continue
        rojo, verde, azul, nir = capas
        for capa in capas:
            capa[~limpio] = np.nan
        nd = (nir - rojo) / (nir + rojo + 1e-6)
        nd[~limpio] = np.nan
        rgb_pila.append(np.dstack([rojo, verde, azul]))
        ndvi_pila.append(nd)
        usados.append({"fecha": item.datetime.strftime("%Y-%m-%d"),
                       "nubes": round(float(item.properties.get("eo:cloud_cover", 100.0)), 1),
                       "id": item.id})
        print(f"  {item.datetime:%Y-%m-%d} | nubes {usados[-1]['nubes']}%")

    if not rgb_pila:
        raise SystemExit("Ningun item dejo pixeles validos.")

    with np.errstate(invalid="ignore"):
        rgb = np.nanmedian(np.stack(rgb_pila, axis=0), axis=0)
        ndvi = np.nanmedian(np.stack(ndvi_pila, axis=0), axis=0)
    return rgb, ndvi, usados, forma, transform


def guardar(capa, ruta: Path):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((capa * 255).astype(np.uint8)).save(ruta, "PNG", optimize=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--antes", required=True)
    ap.add_argument("--despues", required=True)
    ap.add_argument("--bbox", required=True)
    ap.add_argument("--dias", type=int, default=20)
    ap.add_argument("--nubes", type=float, default=40.0)
    ap.add_argument("--min-ndvi", type=float, default=0.5)
    ap.add_argument("--umbral", type=float, default=0.20)
    ap.add_argument("--px", type=int, default=1000)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    bbox = caja(args.bbox)
    antes = date.fromisoformat(args.antes)
    despues = date.fromisoformat(args.despues)
    salida = Path(args.out_dir)
    salida.mkdir(parents=True, exist_ok=True)

    print(f"Landsat {antes} -> {despues}")
    rgb_a, nd_a, usados_a, forma, transform = leer(bbox, antes, args.dias, args.nubes, args.px)
    rgb_d, nd_d, usados_d, _, _ = leer(bbox, despues, args.dias, args.nubes, args.px)

    delta = nd_d - nd_a
    valido = np.isfinite(delta)
    bosque = valido & (nd_a > args.min_ndvi)
    perdida = mayoria(valido & bosque & (delta < -args.umbral)) & valido

    rango = rango_comun(rgb_a, rgb_d)
    antes8 = estirar(rgb_a, rango)
    despues8 = estirar(rgb_d, rango)
    con_rojo = despues8.copy()
    rojo = np.array([1.0, 0.22, 0.10])
    con_rojo[perdida] = con_rojo[perdida] * 0.15 + rojo * 0.85

    guardar(antes8, salida / "antes.png")
    guardar(despues8, salida / "despues.png")
    guardar(con_rojo, salida / "perdida.png")

    try:
        fuente = ImageFont.truetype("arial.ttf", 16)
        chica = ImageFont.truetype("arial.ttf", 12)
    except OSError:
        fuente = ImageFont.load_default()
        chica = fuente

    alto, ancho = antes8.shape[0], antes8.shape[1]
    extra, sep = 32, 6
    lienzo = Image.new("RGB", (ancho * 3 + sep * 2, alto + extra + 28), (8, 8, 10))
    dibujo = ImageDraw.Draw(lienzo)
    for i, (capa, etiqueta) in enumerate((
        (antes8, f"{usados_a[0]['fecha']}"),
        (despues8, f"{usados_d[0]['fecha']}"),
        (con_rojo, "p\u00e9rdida de dosel"),
    )):
        x = i * (ancho + sep)
        lienzo.paste(Image.fromarray((capa * 255).astype(np.uint8)), (x, extra))
        dibujo.text((x + 8, 8), etiqueta, fill=(236, 236, 241), font=fuente)

    ha = float(perdida.sum()) * area_pixel_m2(bbox, perdida.shape) / 10000.0
    dibujo.text((8, alto + extra + 4),
                f"Landsat 8/9 C2 L2, color real, mediana | nubes enmascaradas con qa_pixel | "
                f"p\u00e9rdida {ha:.1f} ha a umbral {args.umbral:g}",
                fill=(150, 150, 160), font=chica)
    lienzo.save(salida / "comparacion.png", "PNG", optimize=True)

    datos = {
        "sensor": "Landsat 8/9 C2 L2",
        "antes": usados_a,
        "despues": usados_d,
        "bbox": list(bbox),
        "umbral": args.umbral,
        "min_ndvi": args.min_ndvi,
        "perdida_ha": round(ha, 1),
        "px": args.px,
    }
    (salida / "datos.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"listo: {salida} | perdida {ha:.1f} ha")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
