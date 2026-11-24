"""Descarga un recorte de CBERS-4A desde el STAC del INPE.

Tres caminos, todos abiertos y sin clave (licencia CC-BY 4.0, atribución a INPE):

* ``--detalle 2``  WPM PCA RGB fusionado, 2 m. COG con teselas y overviews;
  cobertura parcial (``comun.cbers.ZONAS_2M``).
* ``--detalle 8``  WPM L4-DN (BAND1-3), 8 m. TIFF en tiras: se lee una ventana
  chica, por eso el recorte se mantiene acotado.
* ``--detalle 16`` MUX L4-DN (BAND5-7), 16 m.

Deja ``crudo_cbers.png`` (RGB) y ``crudo_cbers.json`` (metadatos para el
póster). El render vive en ``cuadros/cuadros_cbers.py``.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe descargar\\cbers.py --zona encarnacion --km 16 --detalle 2
    .venv\\Scripts\\python.exe descargar\\cbers.py --zona asuncion --km 16 --detalle 8 --dias 120
    .venv\\Scripts\\python.exe descargar\\cbers.py --help   # no toca la red
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

# Antes de importar rasterio: sin esto GDAL intenta listar el directorio remoto
# y multiplica los pedidos HTTP.
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")
os.environ.setdefault("GDAL_HTTP_MULTIRANGE", "YES")
os.environ.setdefault("GDAL_HTTP_MERGE_CONSECUTIVE_RANGES", "YES")
os.environ.setdefault("VSI_CACHE", "TRUE")

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from rasterio.enums import Resampling  # noqa: E402
from rasterio.warp import transform_bounds  # noqa: E402
from rasterio.windows import Window, bounds as ventana_bounds, from_bounds  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from cbers import (BANDAS, MPP, ZONAS, ZONAS_2M, buscar, cobertura,  # noqa: E402
                   etiqueta_zona, recorte)
from rutas import SALIDAS  # noqa: E402

ATRIBUCION = "INPE · CBERS-4A · CC-BY 4.0"


def _a_uint8(banda: np.ndarray) -> np.ndarray:
    """Estira una banda DN al rango 0..255 ignorando el nodata (0)."""
    valido = np.asarray(banda) > 0
    if not valido.any():
        return np.zeros(np.asarray(banda).shape, dtype=np.uint8)
    datos = np.asarray(banda, dtype=np.float32)
    lo, hi = np.percentile(datos[valido], [2, 98])
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        lo, hi = float(datos[valido].min()), float(datos[valido].max())
    if hi <= lo:
        hi = lo + 1.0
    salida = np.clip((datos - lo) / (hi - lo) * 255.0, 0, 255)
    # Gamma suave: el DN de 10 bits del CBERS sale oscuro en los valles y en el
    # agua; 1.12 levanta los medios tonos sin quemar las nubes.
    salida = (salida / 255.0) ** (1.0 / 1.12) * 255.0
    salida[~valido] = 0
    return salida.astype(np.uint8)


def _ventana(src, bbox):
    """Ventana en el CRS del archivo para la caja lon/lat, recortada al raster."""
    b = transform_bounds("EPSG:4326", src.crs, *bbox)
    win = from_bounds(*b, transform=src.transform)
    win = win.round_offsets().round_lengths()
    return win.intersection(Window(0, 0, src.width, src.height))


def _resampling(mpp: float, src) -> Resampling:
    return Resampling.average if mpp > float(src.res[0]) else Resampling.bilinear


def _leer_banda(href: str, bbox, px: int, mpp: float) -> np.ndarray:
    with rasterio.open(href) as src:
        win = _ventana(src, bbox)
        if win.width < 1 or win.height < 1:
            raise ValueError("la escena no cubre la zona pedida")
        return src.read(1, window=win, out_shape=(px, px),
                        resampling=_resampling(mpp, src))


def _leer_rgb(item: dict, detalle: str, bbox, px: int,
              mpp: float) -> tuple[np.ndarray, tuple[float, float, float, float]]:
    """Devuelve el RGB uint8 y la caja lon/lat efectivamente leída."""
    claves = BANDAS[detalle]
    if detalle == "2":
        href = item["assets"][claves[0]]["href"]
        with rasterio.open(href) as src:
            win = _ventana(src, bbox)
            if win.width < 1 or win.height < 1:
                raise ValueError("la escena no cubre la zona pedida")
            datos = src.read(window=win, out_shape=(3, px, px),
                             resampling=_resampling(mpp, src))
            efectiva = transform_bounds(src.crs, "EPSG:4326",
                                        *ventana_bounds(win, src.transform))
        rgb = np.moveaxis(datos, 0, -1)
        if rgb.dtype != np.uint8:
            rgb = np.stack([_a_uint8(rgb[..., i]) for i in range(3)], axis=-1)
        else:
            rgb = rgb.copy()
            rgb[rgb.max(axis=2) == 0] = 0
        return rgb, efectiva

    hrefs = [item["assets"][clave]["href"] for clave in claves]
    with ThreadPoolExecutor(max_workers=3) as pool:
        futuros = [pool.submit(_leer_banda, href, bbox, px, mpp) for href in hrefs]
        bandas = [fut.result() for fut in futuros]
    # La caja efectiva se toma de la primera banda (todas comparten grilla).
    with rasterio.open(hrefs[0]) as src:
        win = _ventana(src, bbox)
        efectiva = transform_bounds(src.crs, "EPSG:4326", *ventana_bounds(win, src.transform))
    rgb = np.stack([_a_uint8(b) for b in bandas], axis=-1)
    return rgb, efectiva


def _probe_valida(item: dict, detalle: str, bbox) -> float:
    """Fracción de píxeles con dato en una muestra chica del recorte.

    El `bbox`/`geometry` del STAC es el sobre de la escena, no el polígono del
    swath: una escena puede declarar cobertura 100% y estar toda negra en la
    zona pedida. Se lee una muestra de 48x48 y se mide el dato real.
    """
    claves = BANDAS[detalle]
    try:
        with rasterio.open(item["assets"][claves[0]]["href"]) as src:
            win = _ventana(src, bbox)
            if win.width < 1 or win.height < 1:
                return 0.0
            if detalle == "2":
                datos = src.read(window=win, out_shape=(3, 48, 48),
                                 resampling=Resampling.bilinear)
                valido = datos.max(axis=0) > 0
            else:
                datos = src.read(1, window=win, out_shape=(48, 48),
                                 resampling=Resampling.average)
                valido = datos > 0
        return float(np.asarray(valido).mean())
    except Exception:
        return 0.0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Descarga un recorte de CBERS-4A desde el STAC del INPE.")
    ap.add_argument("--zona", default="asuncion", choices=tuple(ZONAS),
                    help="zona preset (por defecto asuncion)")
    ap.add_argument("--km", type=float, default=16.0,
                    help="lado del recorte en km (por defecto 16)")
    ap.add_argument("--detalle", default="8", choices=tuple(MPP),
                    help="2 m (sólo zonas cubiertas), 8 m o 16 m (por defecto 8)")
    ap.add_argument("--desde", help="primer día de búsqueda (AAAA-MM-DD)")
    ap.add_argument("--hasta", help="último día de búsqueda (AAAA-MM-DD)")
    ap.add_argument("--dias", type=int, default=120,
                    help="ventana hacia atrás si no se pasa --desde (por defecto 120)")
    ap.add_argument("--item", help="id de escena exacta (para reproducir)")
    ap.add_argument("--out", help="carpeta de salida (por defecto comun.rutas.SALIDAS)")
    args = ap.parse_args(argv)

    if args.detalle == "2" and args.zona not in ZONAS_2M:
        raise SystemExit(
            f"{etiqueta_zona(args.zona)} no tiene 2 m publicados en el STAC. "
            f"Zonas con 2 m: {', '.join(ZONAS_2M)}. Usá --detalle 8 o 16.")
    if args.detalle != "2" and args.zona in ZONAS_2M:
        print(f"  aviso: {etiqueta_zona(args.zona)} también tiene 2 m; "
              f"podés pedirlo con --detalle 2", flush=True)

    hasta = date.fromisoformat(args.hasta) if args.hasta else date.today()
    desde = date.fromisoformat(args.desde) if args.desde else hasta - timedelta(days=args.dias)
    if desde > hasta:
        desde, hasta = hasta, desde

    corte = recorte(args.zona, args.km, args.detalle)
    print(f"CBERS-4A {corte['coleccion']} | {etiqueta_zona(args.zona)} | "
          f"{corte['km']:.1f} km | {corte['px']}px @ {corte['mpp']:.2f} m/px | "
          f"{desde}..{hasta}", flush=True)

    items = buscar(corte["bbox"], desde, hasta, args.detalle)
    if args.item:
        items = [i for i in items if i.get("id") == args.item] or items
    if not items:
        raise SystemExit(
            f"No hay escenas de {corte['coleccion']} sobre {etiqueta_zona(args.zona)} "
            f"entre {desde} y {hasta}. Probá una ventana más larga (--dias 365) u "
            "otra zona.")

    # El sobre del STAC no dice si el swath tiene dato en la zona: se prueba.
    candidatos = sorted(
        items,
        key=lambda i: str(i.get("properties", {}).get("datetime") or ""),
        reverse=True,
    )
    item = None
    mejor = -1.0
    for cand in candidatos[:8]:
        valor = _probe_valida(cand, args.detalle, corte["bbox"])
        fecha_cand = str(cand.get("properties", {}).get("datetime") or "")[:10]
        print(f"  probando {cand['id']} ({fecha_cand}): {valor:.0%} con dato",
              flush=True)
        if valor > mejor:
            item, mejor = cand, valor
        if valor >= 0.6:
            break
    if item is None or mejor <= 0.0:
        raise SystemExit(
            f"Ninguna escena de {corte['coleccion']} tiene dato sobre "
            f"{etiqueta_zona(args.zona)} en {desde}..{hasta}. Probá --dias 730, "
            "otra zona o --detalle 8.")
    if mejor < 0.5:
        print(f"  aviso: la mejor escena sólo tiene {mejor:.0%} de dato; el resto "
              "sale negro", flush=True)

    cob = cobertura(item, corte["bbox"])
    fecha = str(item.get("properties", {}).get("datetime") or "")[:10]
    print(f"  escena {item['id']} ({fecha}) cobertura {cob:.0%}", flush=True)

    t0 = time.time()
    rgb, efectiva = _leer_rgb(item, args.detalle, corte["bbox"], corte["px"],
                              corte["mpp"])
    if rgb.max() == 0:
        raise SystemExit("La ventana quedó vacía: la escena no tiene dato en la zona.")

    salida = Path(args.out) if args.out else SALIDAS
    salida.mkdir(parents=True, exist_ok=True)
    png = salida / "crudo_cbers.png"
    from PIL import Image

    Image.fromarray(rgb).save(png)
    meta = {
        "item": item["id"],
        "datetime": item.get("properties", {}).get("datetime"),
        "coleccion": corte["coleccion"],
        "zona": corte["zona"],
        "zona_label": etiqueta_zona(corte["zona"]),
        "detalle": args.detalle,
        "km": round(corte["km"], 3),
        "px": corte["px"],
        "mpp": round(corte["mpp"], 4),
        "bbox": [round(v, 6) for v in efectiva],
        "atribucion": ATRIBUCION,
    }
    (salida / "crudo_cbers.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  listo en {time.time() - t0:.0f}s: {png}", flush=True)
    print(f"Ahora renderiza con: .venv\\Scripts\\python.exe cuadros\\cuadros_cbers.py "
          f"--entrada \"{salida}\" --out \"{salida}\"", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

