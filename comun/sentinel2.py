"""Sentinel-2 L2A sobre un recorte NISAR: NDVI sin nubes en la grilla del radar.

Busca en Planetary Computer alrededor de una fecha, lee rojo (B04), NIR (B08) y
la clasificación de escena (SCL), enmascara nubes/sombras, compone el NDVI
mediano y lo reproyecta a la grilla del recorte NISAR.

Lo comparten la fusión óptico-radar y la máscara de bosque del cambio de
cobertura: en L-band el HV solo no separa bosque de cultivo, así que el NDVI es
el que decide dónde había dosel.
"""
from __future__ import annotations

import math
from datetime import timedelta

import numpy as np

try:
    from comun import optico
except ImportError:  # los scripts corren con `comun` en el sys.path
    import optico  # type: ignore[no-redef]

try:
    import planetary_computer as pc
    import rasterio
    from affine import Affine
    from pystac_client import Client
    from rasterio.enums import Resampling
    from rasterio.warp import reproject, transform_bounds
    from rasterio.windows import from_bounds

    DISPONIBLE = True
except ImportError:  # pragma: no cover - depende del venv de los scripts
    DISPONIBLE = False

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"


def _ventana(src, bbox):
    b = transform_bounds("EPSG:4326", src.crs, *bbox)
    return from_bounds(*b, transform=src.transform)


def grilla(xs: np.ndarray, ys: np.ndarray, epsg: int):
    """Transform afín y CRS de un recorte ya orientado (oeste->este, norte->sur)."""
    if not DISPONIBLE:
        raise RuntimeError("faltan rasterio/pystac-client/planetary-computer")
    mpp_x = abs(float(xs[-1] - xs[0])) / max(1, len(xs) - 1)
    mpp_y = abs(float(ys[0] - ys[-1])) / max(1, len(ys) - 1)
    transform = Affine.translation(
        float(xs[0]) - mpp_x / 2.0, float(ys[0]) + mpp_y / 2.0
    ) * Affine.scale(mpp_x, -mpp_y)
    return transform, f"EPSG:{epsg}"


def _ndvi_item(item, bbox, destino_forma, destino_transform, destino_crs, px):
    """NDVI de un ítem, enmascarado por SCL y reproyectado a la grilla NISAR."""
    item = pc.sign(item)
    faltan = [clave for clave in ("B04", "B08", "SCL") if clave not in item.assets]
    if faltan:
        print(f"aviso: {item.id} sin assets {faltan}; se omite")
        return None

    with rasterio.open(item.assets["B04"].href) as src_b04:
        win_b04 = _ventana(src_b04, bbox)
        escala = max(
            1,
            int(
                math.ceil(
                    max(win_b04.width, win_b04.height) / max(1, int(px * 1.5))
                )
            ),
        )
        alto = max(1, int(round(win_b04.height / escala)))
        ancho = max(1, int(round(win_b04.width / escala)))
        rojo = src_b04.read(
            1,
            window=win_b04,
            out_shape=(alto, ancho),
            resampling=Resampling.bilinear,
        ).astype(np.float32)
        transform_origen = src_b04.window_transform(win_b04) * Affine.scale(
            win_b04.width / ancho, win_b04.height / alto
        )
        crs_origen = src_b04.crs

    with rasterio.open(item.assets["B08"].href) as src_b08:
        win_b08 = _ventana(src_b08, bbox)
        nir = src_b08.read(
            1,
            window=win_b08,
            out_shape=(alto, ancho),
            resampling=Resampling.bilinear,
        ).astype(np.float32)

    with rasterio.open(item.assets["SCL"].href) as src_scl:
        win_scl = _ventana(src_scl, bbox)
        scl = src_scl.read(
            1,
            window=win_scl,
            out_shape=(alto, ancho),
            resampling=Resampling.nearest,
        )

    nd = optico.ndvi(rojo, nir)
    nd[~optico.mascara_scl(scl)] = np.nan

    destino = np.full(destino_forma, np.nan, dtype=np.float32)
    reproject(
        source=nd,
        destination=destino,
        src_transform=transform_origen,
        src_crs=crs_origen,
        dst_transform=destino_transform,
        dst_crs=destino_crs,
        resampling=Resampling.bilinear,
        src_nodata=np.nan,
        dst_nodata=np.nan,
    )
    return destino, float(item.properties.get("eo:cloud_cover", 100.0))


def buscar_items(
    bbox: tuple[float, float, float, float],
    centro,
    dias: int,
    nubes_max: float,
    max_items: int = 8,
    cliente=None,
):
    """Ítems L2A con menos nubes que ``nubes_max`` en ±``dias`` de ``centro``."""
    if not DISPONIBLE:
        raise RuntimeError("faltan rasterio/pystac-client/planetary-computer")
    desde = centro - timedelta(days=max(1, int(dias)))
    hasta = centro + timedelta(days=max(1, int(dias)))
    print(f"buscando Sentinel-2 del {desde} al {hasta} (nubes < {nubes_max:g}%)")
    catalogo = cliente or Client.open(STAC)
    busqueda = catalogo.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime=f"{desde}/{hasta}",
        query={"eo:cloud_cover": {"lt": float(nubes_max)}},
    )
    items = sorted(
        list(busqueda.items()),
        key=lambda item: float(item.properties.get("eo:cloud_cover", 100.0)),
    )[: max(1, int(max_items))]
    print(f"Sentinel-2: {len(items)} ítem(s)")
    return items


def componer_ndvi(
    items,
    bbox: tuple[float, float, float, float],
    destino_forma: tuple[int, int],
    destino_transform,
    destino_crs,
    px: int,
) -> tuple[np.ndarray | None, list[dict]]:
    """NDVI mediano de todos los ítems que se puedan leer.

    Devuelve ``(None, [])`` si ningún ítem dejó píxeles válidos: el llamador
    decide si cae a otro método o corta.
    """
    ndvis: list[np.ndarray] = []
    usados: list[dict] = []
    for item in items:
        try:
            resultado = _ndvi_item(
                item, bbox, destino_forma, destino_transform, destino_crs, px
            )
        except Exception as exc:  # noqa: BLE001 - un ítem roto no mata el producto
            print(
                f"aviso: {item.id} fallo al leer/reproyectar "
                f"({type(exc).__name__}: {exc}); se omite"
            )
            continue
        if resultado is None:
            continue
        nd, nubes = resultado
        validos = int(np.isfinite(nd).sum())
        if validos == 0:
            print(f"  {item.id}: sin píxeles válidos tras SCL")
            continue
        ndvis.append(nd)
        usados.append({"id": item.id, "cloud": round(nubes, 2)})
        print(f"  {item.id}: {nubes:.1f}% nubes · {validos} px")
    if not ndvis:
        return None, usados
    return optico.compuesto_mediana(ndvis), usados
