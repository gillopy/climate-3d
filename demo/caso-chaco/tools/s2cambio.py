"""Cambio de NDVI con Sentinel-2 L2A para una caja, sin NISAR.

Sirve para el perÃ­odo en que NISAR todavia no tenia datos. Usa el modulo
`comun/sentinel2.py` del repo (Planetary Computer + rasterio) y la misma
logica de coherencia espacial que el analisis de radar: voto de mayoria 3x3
y unidad minima de mapeo por componentes conexas.

Uso:
    .venv\\Scripts\\python.exe demo\\caso-chaco\\tools\\optico.py ^
        --antes 2025-07-03 --despues 2025-10-31 ^
        --bbox "-55.444565,-24.066058,-55.321484,-23.995819" ^
        --control "-55.500,-24.200,-55.440,-24.160" ^
        --out D:\\temp\\caso\\optico.js --png D:\\temp\\caso\\optico.png
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from rasterio.features import rasterize
from rasterio.transform import from_bounds

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "comun"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import sentinel2  # noqa: E402
from tecnico import componentes  # noqa: E402

UMBRALES = (0.08, 0.12, 0.16, 0.20, 0.25)


def caja(texto: str) -> tuple[float, float, float, float]:
    oeste, sur, este, norte = (float(v) for v in texto.split(","))
    if oeste >= este or sur >= norte:
        raise SystemExit(f"caja invalida: {texto}")
    return oeste, sur, este, norte


def grilla(bbox, px: int):
    oeste, sur, este, norte = bbox
    ancho = int(px)
    alto = max(1, int(round(px * (norte - sur) / (este - oeste))))
    transform = from_bounds(oeste, sur, este, norte, ancho, alto)
    return (alto, ancho), transform, "EPSG:4326"


def area_pixel_m2(bbox, forma) -> float:
    oeste, sur, este, norte = bbox
    alto, ancho = forma
    midlat = (sur + norte) / 2
    m_lon = 111320.0 * np.cos(np.radians(midlat))
    m_lat = 110574.0
    return ((este - oeste) / ancho * m_lon) * ((norte - sur) / alto * m_lat)


def mascara_poligono(ruta: Path, forma, transform) -> np.ndarray:
    """Rasteriza un GeoJSON (lon/lat) sobre la grilla de destino."""
    datos = json.loads(Path(ruta).read_text(encoding="utf-8-sig"))
    geom = datos.get("geometry", datos)
    capa = rasterize(
        [(geom, 1)],
        out_shape=forma,
        transform=transform,
        fill=0,
        dtype="uint8",
        all_touched=False,
    )
    return capa.astype(bool)


def ndvi_de(bbox, centro: date, dias: int, nubes: float, px: int):
    forma, transform, crs = grilla(bbox, px)
    items = sentinel2.buscar_items(bbox, centro, dias, nubes, max_items=8)
    if not items:
        raise SystemExit(
            f"Sin Sentinel-2 L2A cerca de {centro} con menos de {nubes:g}% de nubes."
        )
    ndvi, usados = sentinel2.componer_ndvi(items, bbox, forma, transform, crs, px)
    if ndvi is None:
        raise SystemExit(f"Ningun item de Sentinel-2 dejo pixeles validos cerca de {centro}.")
    return ndvi, usados


def mayoria(mascara: np.ndarray) -> np.ndarray:
    """Voto de mayoria 3x3: sobrevive con 5 de 9 vecinos."""
    p = np.pad(mascara.astype(np.uint8), 1)
    suma = np.zeros_like(mascara, dtype=np.uint8)
    for dy in range(3):
        for dx in range(3):
            suma += p[dy:dy + mascara.shape[0], dx:dx + mascara.shape[1]]
    return suma >= 5


def analizar(ndvi_a, ndvi_d, bbox, umbral, mmu_ha, bosque_ndvi, poligono=None, min_ndvi=0.0):
    delta = ndvi_d - ndvi_a
    valido = np.isfinite(delta)
    if poligono is not None:
        bosque = valido & poligono & (ndvi_a > min_ndvi)
    else:
        bosque = valido & (ndvi_a > bosque_ndvi)
    perdida = mayoria(valido & bosque & (delta < -umbral)) & valido

    m2 = area_pixel_m2(bbox, delta.shape)
    px_bosque = int(bosque.sum())
    px_perdida = int(perdida.sum())

    sensibilidad = []
    for t in UMBRALES:
        m = mayoria(valido & bosque & (delta < -t)) & valido
        sensibilidad.append({"ndvi": t, "ha": round(int(m.sum()) * m2 / 10000.0, 1),
                             "px": int(m.sum())})

    comp = componentes(perdida, np.sqrt(m2))
    areas = comp["areas_ha"] if comp else []
    conservadas = [a for a in areas if a >= mmu_ha]

    return {
        "area_ha": round(valido.sum() * m2 / 10000.0, 1),
        "bosque_ha": round(px_bosque * m2 / 10000.0, 1),
        "perdida_ha": round(px_perdida * m2 / 10000.0, 1),
        "px_perdida": px_perdida,
        "px_bosque": px_bosque,
        "ndvi_antes_medio": round(float(np.nanmean(ndvi_a[bosque])), 3) if px_bosque else 0.0,
        "ndvi_despues_medio": round(float(np.nanmean(ndvi_d[bosque])), 3) if px_bosque else 0.0,
        "delta_medio_db": round(float(np.nanmean(delta[perdida])), 3) if px_perdida else 0.0,
        "sensibilidad": sensibilidad,
        "mmu": {
            "umbral_ha": mmu_ha,
            "componentes": comp["total"] if comp else 0,
            "componentes_validos": len(conservadas),
            "ha_sin_mmu": round(float(sum(areas)), 1),
            "ha_con_mmu": round(float(sum(conservadas)), 1),
            "componente_mayor_ha": round(float(max(areas)), 1) if areas else 0.0,
        },
    }


def densidad(perdida: np.ndarray, bbox, m2: float, n: int = 12) -> None:
    """Imprime un mapa ASCII de densidad de perdida y las celdas mas cargadas."""
    alto, ancho = perdida.shape
    h, w = alto // n, ancho // n
    if h < 1 or w < 1:
        return
    celdas = perdida[:h * n, :w * n].reshape(n, h, n, w).sum(axis=(1, 3))
    area_celda_ha = h * w * m2 / 10000.0
    pct = 100.0 * celdas * m2 / 10000.0 / area_celda_ha

    oeste, sur, este, norte = bbox
    print(f"\ngrilla {n}x{n} | celda {h * np.sqrt(m2) / 1000:.1f} x {w * np.sqrt(m2) / 1000:.1f} km")
    for r in range(n):
        linea = ""
        for c in range(n):
            linea += " .:-=+*#%@"[min(9, int(pct[r, c] / 2.5))]
        print("  " + linea)

    orden = np.dstack(np.unravel_index(np.argsort(celdas.ravel())[::-1], celdas.shape))[0]
    print("\ntop 5 celdas:")
    for r, c in orden[:5]:
        lon = oeste + (c + 0.5) * (este - oeste) / n
        lat = norte - (r + 0.5) * (norte - sur) / n
        print(f"  {celdas[r, c] * m2 / 10000:7.1f} ha  {pct[r, c]:5.1f}%  "
              f"lon {lon:.5f}  lat {lat:.5f}")


def pintar(png: Path, base, perdida, meta: dict, transform=None, borde=None) -> None:
    """Imagen mas antigua en gris, con la perdida de dosel en rojo encima."""
    alto, ancho = base.shape
    gris = np.clip(np.nan_to_num(base, nan=0.05), 0, 0.9) / 0.9
    rgb = np.dstack([gris, gris, gris])
    rojo = np.array([1.0, 0.28, 0.12])
    rgb[perdida] = rgb[perdida] * 0.15 + rojo * 0.85
    rgb[~np.isfinite(base)] = 0.0
    escala = 2
    img = Image.fromarray((rgb * 255).astype(np.uint8)).resize(
        (ancho * escala, alto * escala), Image.BILINEAR
    )
    lienzo = Image.new("RGB", (img.width, img.height + 58), (8, 8, 10))
    lienzo.paste(img, (0, 0))
    dibujo = ImageDraw.Draw(lienzo)
    if borde and transform is not None:
        puntos = []
        for lon, lat in borde:
            col, fila = ~transform * (lon, lat)
            puntos.append((col * escala, fila * escala))
        if len(puntos) > 2:
            dibujo.line(puntos, fill=(120, 200, 255), width=2)
    try:
        fuente = ImageFont.truetype("arial.ttf", 15)
        chica = ImageFont.truetype("arial.ttf", 12)
    except OSError:
        fuente = ImageFont.load_default()
        chica = fuente
    y = img.height + 8
    dibujo.text((12, y), meta["titulo"], fill=(236, 236, 241), font=fuente)
    dibujo.text((12, y + 20), meta["detalle"], fill=(150, 150, 160), font=chica)
    dibujo.text((12, y + 36), "rojo = perdida de dosel | azul = limite del area protegida",
                fill=(255, 138, 110), font=chica)
    png.parent.mkdir(parents=True, exist_ok=True)
    lienzo.save(png, "PNG", optimize=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--antes", required=True, help="fecha central AAAA-MM-DD")
    ap.add_argument("--despues", required=True)
    ap.add_argument("--bbox", required=True)
    ap.add_argument("--control", required=True)
    ap.add_argument("--dias", type=int, default=15, help="ventana alrededor de cada fecha")
    ap.add_argument("--nubes", type=float, default=25.0)
    ap.add_argument("--umbral", type=float, default=0.16, help="caida minima de NDVI")
    ap.add_argument("--bosque-ndvi", type=float, default=0.55)
    ap.add_argument("--mmu", type=float, default=0.5)
    ap.add_argument("--px", type=int, default=1600)
    ap.add_argument("--var", default="OPTICO")
    ap.add_argument("--out", required=True)
    ap.add_argument("--png", default=None)
    ap.add_argument("--grilla", type=int, default=0, help="imprime mapa de densidad NxN")
    ap.add_argument("--mascara-geojson", default=None, help="poligono que define el area analizada")
    ap.add_argument("--min-ndvi", type=float, default=0.25, help="NDVI previo minimo dentro de la mascara")
    args = ap.parse_args()

    bbox = caja(args.bbox)
    control = caja(args.control)
    antes = date.fromisoformat(args.antes)
    despues = date.fromisoformat(args.despues)

    forma, transform, _crs = grilla(bbox, args.px)
    poligono = None
    borde = None
    if args.mascara_geojson:
        poligono = mascara_poligono(args.mascara_geojson, forma, transform)
        datos_geo = json.loads(Path(args.mascara_geojson).read_text(encoding="utf-8-sig"))
        geom = datos_geo.get("geometry", datos_geo)
        if geom.get("type") == "Polygon":
            borde = geom["coordinates"][0]
        elif geom.get("type") == "MultiPolygon":
            borde = geom["coordinates"][0][0]
        print(f"mascara: {int(poligono.sum())} px dentro del poligono")

    print(f"caso: Sentinel-2 {antes} -> {despues}")
    nd_a, usados_a = ndvi_de(bbox, antes, args.dias, args.nubes, args.px)
    nd_d, usados_d = ndvi_de(bbox, despues, args.dias, args.nubes, args.px)
    caso = analizar(nd_a, nd_d, bbox, args.umbral, args.mmu, args.bosque_ndvi,
                    poligono=poligono, min_ndvi=args.min_ndvi)

    print("control")
    nc_a, _ = ndvi_de(control, antes, args.dias, args.nubes, args.px)
    nc_d, _ = ndvi_de(control, despues, args.dias, args.nubes, args.px)
    poligono_ctrl = None
    if args.mascara_geojson:
        forma_c, transform_c, _ = grilla(control, args.px)
        poligono_ctrl = mascara_poligono(args.mascara_geojson, forma_c, transform_c)
    ctrl = analizar(nc_a, nc_d, control, args.umbral, args.mmu, args.bosque_ndvi,
                    poligono=poligono_ctrl, min_ndvi=args.min_ndvi)

    delta = nd_d - nd_a
    valido = np.isfinite(delta)
    if poligono is not None:
        bosque = valido & poligono & (nd_a > args.min_ndvi)
    else:
        bosque = valido & (nd_a > args.bosque_ndvi)
    perdida = mayoria(valido & bosque & (delta < -args.umbral)) & valido

    datos = {
        "producto": "optico",
        "sensor": "Sentinel-2 L2A",
        "parametros": {
            "fecha_antes": antes.isoformat(),
            "fecha_despues": despues.isoformat(),
            "dias": args.dias,
            "nubes_max_pct": args.nubes,
            "umbral_ndvi": args.umbral,
            "bosque_ndvi": args.bosque_ndvi,
            "mmu_ha": args.mmu,
            "mascara_geojson": args.mascara_geojson,
            "min_ndvi": args.min_ndvi,
        },
        "items": {"antes": usados_a, "despues": usados_d},
        "caso": caso,
        "control": ctrl,
        "bbox": list(bbox),
        "control_bbox": list(control),
    }

    salida = Path(args.out)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(
        f"window.{args.var} = " + json.dumps(datos, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )

    if args.png:
        pintar(
            Path(args.png), nd_a, perdida,
            {
                "titulo": f"NDVI {antes} -> {despues} | base: imagen mas antigua",
                "detalle": (
                    f"perdida {caso['perdida_ha']} ha de {caso['area_ha']} ha | "
                    f"umbral {args.umbral:g} NDVI | MMU {args.mmu:g} ha"
                ),
            },
            transform=transform,
            borde=borde,
        )

    print(f"listo: {salida}")
    if args.grilla:
        densidad(perdida, bbox, area_pixel_m2(bbox, delta.shape), args.grilla)
    print(f"  caso {caso['perdida_ha']} ha brutas | {caso['mmu']['ha_con_mmu']} ha con MMU | "
          f"{caso['mmu']['componentes']} componentes")
    print(f"  control {ctrl['perdida_ha']} ha brutas | {ctrl['mmu']['ha_con_mmu']} ha con MMU")
    print(f"  NDVI bosque: {caso['ndvi_antes_medio']} -> {caso['ndvi_despues_medio']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
