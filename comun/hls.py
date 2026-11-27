"""Optional HLS L30/S30 optical composites for NISAR confirmation.

HLS is used as an optical provider, not as ground truth.  L30 supplies Landsat
8/9 observations and S30 supplies Sentinel-2 observations on the harmonized
30 m grid.  The module deliberately mirrors the small provider surface used by
``comun.sentinel2`` so callers can fall back without changing the radar path.
"""
from __future__ import annotations

from datetime import timedelta
from copy import deepcopy
import warnings

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
except ImportError:  # pragma: no cover - optional runtime dependency
    DISPONIBLE = False


STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
COLECCIONES = {"l30": "hls2-l30", "s30": "hls2-s30"}
BANDAS = {
    "l30": ("B04", "B05", "Fmask"),  # red, NIR
    "s30": ("B04", "B08", "Fmask"),  # red, NIR
}
#: Color real en la grilla armonizada: azul, verde, rojo y la mascara Fmask.
BANDAS_COLOR = {
    "l30": ("B02", "B03", "B04", "Fmask"),
    "s30": ("B02", "B03", "B04", "Fmask"),
}
ESCALA_REFLECTANCIA = 0.0001
MASCARA_CALIDAD = (1 << 1) | (1 << 2) | (1 << 3) | (1 << 4) | (1 << 5)


def grilla(xs: np.ndarray, ys: np.ndarray, epsg: int):
    """Return the affine transform for an oriented NISAR target grid."""
    if not DISPONIBLE:
        raise RuntimeError("faltan rasterio/pystac-client/planetary-computer")
    mpp_x = abs(float(xs[-1] - xs[0])) / max(1, len(xs) - 1)
    mpp_y = abs(float(ys[0] - ys[-1])) / max(1, len(ys) - 1)
    transform = Affine.translation(
        float(xs[0]) - mpp_x / 2.0, float(ys[0]) + mpp_y / 2.0
    ) * Affine.scale(mpp_x, -mpp_y)
    return transform, f"EPSG:{epsg}"


def mascara_fmask(fmask: np.ndarray) -> np.ndarray:
    """Accept clear, non-water pixels and reject cloud/shadow/snow/high aerosol."""
    qa = np.asarray(fmask, dtype=np.uint16)
    valido = np.isfinite(qa) & (qa != 255)
    sin_nubes = (qa & MASCARA_CALIDAD) == 0
    aerosol = (qa >> 6) & 0b11
    return valido & sin_nubes & (aerosol != 0b11)


def _ventana(src, bbox):
    bounds = transform_bounds("EPSG:4326", src.crs, *bbox)
    return from_bounds(*bounds, transform=src.transform)


def buscar_items(
    bbox: tuple[float, float, float, float],
    centro,
    dias: int,
    nubes_max: float,
    max_items: int = 8,
    cliente=None,
    sensor: str = "l30",
    orden: str = "nubes",
):
    """Find HLS L30/S30 items around a date.

    ``orden="nubes"`` (default) keeps the cleanest scene of the window;
    ``orden="cercania"`` keeps the scene closest in date and uses cloud cover
    only as a tie-break, which is what true color needs.
    """
    if not DISPONIBLE:
        raise RuntimeError("faltan rasterio/pystac-client/planetary-computer")
    if orden not in ("nubes", "cercania"):
        raise ValueError(f"orden desconocido: {orden}")
    clave = str(sensor).lower()
    if clave not in COLECCIONES:
        raise ValueError(f"sensor HLS desconocido: {sensor}")
    desde = centro - timedelta(days=max(1, int(dias)))
    hasta = centro + timedelta(days=max(1, int(dias)))
    catalogo = cliente or Client.open(STAC)
    busqueda = catalogo.search(
        collections=[COLECCIONES[clave]],
        bbox=bbox,
        datetime=f"{desde}/{hasta}",
        query={"eo:cloud_cover": {"lt": float(nubes_max)}},
    )
    items = list(busqueda.items())
    if orden == "cercania":
        items = optico.ordenar_por_cercania(items, centro)
    else:
        items = sorted(
            items,
            key=lambda item: float(item.properties.get("eo:cloud_cover", 100.0)),
        )
    return items[: max(1, int(max_items))]


def _leer_bandas(item, bbox, sensor: str, bandas=None):
    item = pc.sign(deepcopy(item))
    bandas = bandas or BANDAS[sensor]
    faltan = [banda for banda in bandas if banda not in item.assets]
    if faltan:
        raise ValueError(f"{item.id} sin assets HLS {faltan}")
    datos = {}
    transform_origen = None
    crs_origen = None
    for banda in bandas:
        with rasterio.open(item.assets[banda].href) as src:
            ventana = _ventana(src, bbox)
            if transform_origen is None:
                transform_origen = src.window_transform(ventana)
                crs_origen = src.crs
            datos[banda] = src.read(1, window=ventana)
    # Fmask es un entero de calidad; el resto son reflectancia escalada. Escalar
    # todas las bandas aca evita que cada compuesto lo repita (y lo olvide).
    for banda in datos:
        if banda != "Fmask":
            datos[banda] = datos[banda].astype(np.float32) * ESCALA_REFLECTANCIA
    return datos, transform_origen, crs_origen


def componer_ndvi(
    items,
    bbox: tuple[float, float, float, float],
    destino_forma: tuple[int, int],
    destino_transform,
    destino_crs,
    px: int,
    sensor: str = "l30",
):
    """Compose HLS NDVI on the NISAR grid, returning ``(array, used_items)``."""
    if not DISPONIBLE:
        raise RuntimeError("faltan rasterio/pystac-client/planetary-computer")
    capas = []
    usados = []
    nir = "B05" if sensor == "l30" else "B08"
    for item in items:
        try:
            datos, transform, crs = _leer_bandas(item, bbox, sensor)
            ndvi = (datos[nir] - datos["B04"]) / np.maximum(
                datos[nir] + datos["B04"], 1e-6
            )
            ndvi[~mascara_fmask(datos["Fmask"])] = np.nan
            destino = np.full(destino_forma, np.nan, dtype=np.float32)
            reproject(
                source=ndvi.astype(np.float32),
                destination=destino,
                src_transform=transform,
                src_crs=crs,
                dst_transform=destino_transform,
                dst_crs=destino_crs,
                resampling=Resampling.bilinear,
                src_nodata=np.nan,
                dst_nodata=np.nan,
            )
            if np.isfinite(destino).any():
                capas.append(destino)
                usados.append({
                    "id": item.id,
                    "cloud": round(float(item.properties.get("eo:cloud_cover", 100.0)), 2),
                    "sensor": sensor,
                })
        except Exception as exc:  # noqa: BLE001 - optional provider is best effort
            print(f"aviso: HLS {getattr(item, 'id', 'item')} omitido ({type(exc).__name__}: {exc})")
    if not capas:
        return None, usados
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        compuesto = np.nanmedian(np.stack(capas), axis=0).astype(np.float32)
    return compuesto, usados


def componer_color_reflectancia(
    items,
    bbox: tuple[float, float, float, float],
    destino_forma: tuple[int, int],
    destino_transform,
    destino_crs,
    px: int,
    sensor: str = "l30",
):
    """R/G/B mediano en reflectancia sobre la grilla del recorte NISAR.

    HLS no traia color: el modulo solo leia rojo y NIR para el NDVI. L30 y S30
    publican B02/B03/B04 en la misma grilla armonizada de 30 m, asi que el color
    real sale del mismo item que confirma el cambio. Devuelve los canales sin
    estirar para que el llamador comparta la escala entre dos fechas.
    """
    if not DISPONIBLE:
        raise RuntimeError("faltan rasterio/pystac-client/planetary-computer")
    pilas: dict[str, list[np.ndarray]] = {"R": [], "G": [], "B": []}
    usados = []
    for item in items:
        try:
            datos, transform, crs = _leer_bandas(
                item, bbox, sensor, bandas=BANDAS_COLOR[sensor]
            )
            valido = mascara_fmask(datos["Fmask"])
            canales = {}
            for canal, banda in (("R", "B04"), ("G", "B03"), ("B", "B02")):
                capa = np.where(valido, datos[banda], np.nan).astype(np.float32)
                destino = np.full(destino_forma, np.nan, dtype=np.float32)
                reproject(
                    source=capa,
                    destination=destino,
                    src_transform=transform,
                    src_crs=crs,
                    dst_transform=destino_transform,
                    dst_crs=destino_crs,
                    resampling=Resampling.bilinear,
                    src_nodata=np.nan,
                    dst_nodata=np.nan,
                )
                canales[canal] = destino
            if not all(np.isfinite(capa).any() for capa in canales.values()):
                continue
            for canal, capa in canales.items():
                pilas[canal].append(capa)
            usados.append({
                "id": item.id,
                "cloud": round(float(item.properties.get("eo:cloud_cover", 100.0)), 2),
                "sensor": sensor,
            })
        except Exception as exc:  # noqa: BLE001 - optional provider is best effort
            print(f"aviso: HLS {getattr(item, 'id', 'item')} sin color ({type(exc).__name__}: {exc})")
    if not all(pilas[canal] for canal in ("R", "G", "B")):
        return None, usados
    return {canal: optico.compuesto_mediana(capas) for canal, capas in pilas.items()}, usados
