"""Sentinel-2 L2A sobre un recorte NISAR: indices sin nubes en la grilla del radar.

Busca en Planetary Computer alrededor de una fecha, lee las bandas pedidas y la
clasificacion de escena (SCL), enmascara nubes/sombras, compone la mediana pixel a
pixel y reproyecta a la grilla del recorte NISAR.

Lo comparten la fusion optico-radar, la mascara de bosque del cambio de cobertura
y el panel de indices: en L-band el HV solo no separa bosque de cultivo, asi que
el NDVI es el que decide donde habia dosel.

Las lecturas son remotas y caras (una apertura por banda y por item). Por eso el
resultado compuesto se guarda en disco y se reutiliza: la misma caja y la misma
fecha no se vuelven a bajar.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from copy import deepcopy
from datetime import timedelta
from pathlib import Path

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
except ImportError as _exc:  # pragma: no cover - depende del venv de los scripts
    # Se guarda el motivo real: en el contenedor el paquete estaba instalado pero
    # le faltaba una libreria del sistema (libexpat), y el mensaje generico mandaba
    # a buscar el problema en el lugar equivocado.
    DISPONIBLE = False
    MOTIVO = str(_exc) or "import fallo sin detalle"

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"

#: Conjunto minimo para NDVI: rojo, infrarrojo cercano y la mascara de escena.
BANDAS_NDVI = ("B04", "B08", "SCL")

#: Conjunto para los indices: verde, rojo, NIR, SWIR1, SWIR2 y la mascara.
#: SWIR2 (B12) entra por NBR: es la banda que separa dosel de suelo desnudo.
BANDAS_INDICES = ("B03", "B04", "B08", "B11", "B12", "SCL")

#: Color real: azul (B02), verde (B03), rojo (B04) y la mascara de escena.
BANDAS_COLOR = ("B02", "B03", "B04", "SCL")

#: Subir esto invalida toda la cache en disco (cambia el prefijo de la clave).
CACHE_VERSION = 1


def _ventana(src, bbox):
    b = transform_bounds("EPSG:4326", src.crs, *bbox)
    return from_bounds(*b, transform=src.transform)


def grilla(xs: np.ndarray, ys: np.ndarray, epsg: int):
    """Transform afín y CRS de un recorte ya orientado (oeste->este, norte->sur)."""
    if not DISPONIBLE:
        raise RuntimeError(f"no puedo usar la grilla optica: {MOTIVO}")
    mpp_x = abs(float(xs[-1] - xs[0])) / max(1, len(xs) - 1)
    mpp_y = abs(float(ys[0] - ys[-1])) / max(1, len(ys) - 1)
    transform = Affine.translation(
        float(xs[0]) - mpp_x / 2.0, float(ys[0]) + mpp_y / 2.0
    ) * Affine.scale(mpp_x, -mpp_y)
    return transform, f"EPSG:{epsg}"


# ---------------------------------------------------------------------------
# Cache en disco
# ---------------------------------------------------------------------------


def carpeta_cache() -> Path:
    """Donde se guardan los compuestos: NISAR_S2_CACHE, o al lado de los artefactos."""
    valor = (os.environ.get("NISAR_S2_CACHE") or "").strip()
    if valor:
        return Path(valor)
    media = (os.environ.get("NISAR_MEDIA") or "").strip()
    if media:
        return Path(media) / "cache" / "s2"
    return Path(tempfile.gettempdir()) / "nisar-s2-cache"


def _clave_cache(bbox, forma, transform, crs, px, bandas, items) -> str:
    # Los ids de los items van en la clave: si cambia la busqueda (nubes, dias,
    # max-items) cambia la lista y por lo tanto el resultado. Asi una cache vieja
    # nunca se devuelve para una busqueda distinta.
    partes = [
        f"v{CACHE_VERSION}",
        ",".join(f"{v:.6f}" for v in bbox),
        f"{int(forma[0])}x{int(forma[1])}",
        ",".join(f"{float(v):.4f}" for v in tuple(transform)[:6]),
        str(crs),
        str(int(px)),
        ",".join(bandas),
        "\n".join(str(getattr(item, "id", "")) for item in items),
    ]
    return hashlib.sha1("|".join(partes).encode("utf-8")).hexdigest()[:20]


def _leer_cache(clave):
    ruta = carpeta_cache() / f"{clave}.npz"
    if not ruta.exists():
        return None
    try:
        with np.load(ruta, allow_pickle=False) as guardado:
            salida = {k: guardado[k] for k in guardado.files if k != "usados"}
            usados = json.loads(str(guardado["usados"])) if "usados" in guardado.files else []
        return salida, usados
    except Exception as exc:  # noqa: BLE001 - una cache rota no corta el producto
        print(f"aviso: cache ilegible ({type(exc).__name__}); se recalcula")
        return None


def _guardar_cache(clave, salida, usados) -> None:
    try:
        carpeta = carpeta_cache()
        carpeta.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            carpeta / f"{clave}.npz",
            usados=np.array(json.dumps(usados)),
            **{k: v for k, v in salida.items()},
        )
    except Exception as exc:  # noqa: BLE001 - sin cache se sigue igual
        print(f"aviso: no pude guardar la cache ({type(exc).__name__}: {exc})")


# ---------------------------------------------------------------------------
# Lectura de bandas
# ---------------------------------------------------------------------------


def _leer_bandas(item, bbox, bandas, px):
    """Lee las bandas pedidas sobre `bbox`. Devuelve (dict, transform, crs, nubes).

    Firma sobre una **copia**: `pc.sign` muta el item y re-firmar uno ya firmado
    arrastra el token viejo. Con la copia cada reintento sale con un token nuevo,
    que es lo que arregla los 403 intermitentes de Planetary Computer.
    """
    item = pc.sign(deepcopy(item))
    faltan = [banda for banda in bandas if banda not in item.assets]
    if faltan:
        print(f"aviso: {item.id} sin assets {faltan}; se omite")
        return None

    datos: dict[str, np.ndarray] = {}
    transform_origen = None
    crs_origen = None
    alto = ancho = 0

    # Lectura de COG remoto: sin esto GDAL intenta listar el "directorio" del blob,
    # no reintenta los cortes de red y falla con "Read failed" / "not recognized as
    # being in a supported file format" en medio de un item que ya venia bien.
    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.TIF",
        GDAL_HTTP_MULTIPLEX="YES",
        GDAL_HTTP_MAX_RETRY="4",
        GDAL_HTTP_RETRY_DELAY="2",
    ):
        for banda in bandas:
            with rasterio.open(item.assets[banda].href) as src:
                ventana = _ventana(src, bbox)
                if transform_origen is None:
                    # La resolucion de trabajo sale de la primera banda: las demas se
                    # leen con la misma forma, aunque tengan otro tamano de pixel.
                    escala = max(
                        1,
                        int(
                            math.ceil(
                                max(ventana.width, ventana.height) / max(1, int(px * 1.5))
                            )
                        ),
                    )
                    alto = max(1, int(round(ventana.height / escala)))
                    ancho = max(1, int(round(ventana.width / escala)))
                    transform_origen = src.window_transform(ventana) * Affine.scale(
                        ventana.width / ancho, ventana.height / alto
                    )
                    crs_origen = src.crs
                remuestreo = Resampling.nearest if banda == "SCL" else Resampling.bilinear
                datos[banda] = src.read(
                    1,
                    window=ventana,
                    out_shape=(alto, ancho),
                    resampling=remuestreo,
                ).astype(np.float32)

    nubes = float(item.properties.get("eo:cloud_cover", 100.0))
    return datos, transform_origen, crs_origen, nubes


def buscar_items(
    bbox: tuple[float, float, float, float],
    centro,
    dias: int,
    nubes_max: float,
    max_items: int = 8,
    cliente=None,
):
    """Items L2A con menos nubes que `nubes_max` en +-`dias` de `centro`."""
    if not DISPONIBLE:
        raise RuntimeError(f"no puedo leer Sentinel-2: {MOTIVO}")
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
    print(f"Sentinel-2: {len(items)} item(s)")
    return items


# ---------------------------------------------------------------------------
# Composicion
# ---------------------------------------------------------------------------


def _componer(
    items,
    bbox,
    destino_forma,
    destino_transform,
    destino_crs,
    px,
    bandas,
    calcular,
    etiqueta,
):
    """Compone (mediana) los indices que devuelve `calcular` sobre los items.

    Devuelve ``(dict, usados)`` o ``(None, usados)`` si ningun item dejo pixeles.
    """
    clave = _clave_cache(
        bbox, destino_forma, destino_transform, destino_crs, px, bandas, items
    )
    cacheado = _leer_cache(clave)
    if cacheado is not None:
        print(f"  cache: reuso {etiqueta} ({len(cacheado[1])} item(s))")
        return cacheado

    pilas: dict[str, list[np.ndarray]] = {}
    usados: list[dict] = []

    for item in items:
        leido = None
        for intento in range(2):
            try:
                leido = _leer_bandas(item, bbox, bandas, px)
                break
            except Exception as exc:  # noqa: BLE001 - un item roto no mata el producto
                if intento == 0:
                    # Los assets remotos fallan con 403/Read failed cuando el token
                    # de un item viejo ya no sirve: se reintenta con firma nueva.
                    print(f"  {item.id}: {type(exc).__name__}; se reintenta con firma nueva")
                    continue
                print(
                    f"aviso: {item.id} fallo al leer/reproyectar "
                    f"({type(exc).__name__}: {exc}); se omite"
                )
        if leido is None:
            continue

        datos, transform_origen, crs_origen, nubes = leido
        indices = calcular(datos)

        reproyectados: dict[str, np.ndarray] = {}
        con_datos = False
        for nombre, capa in indices.items():
            destino = np.full(destino_forma, np.nan, dtype=np.float32)
            reproject(
                source=capa,
                destination=destino,
                src_transform=transform_origen,
                src_crs=crs_origen,
                dst_transform=destino_transform,
                dst_crs=destino_crs,
                resampling=Resampling.bilinear,
                src_nodata=np.nan,
                dst_nodata=np.nan,
            )
            reproyectados[nombre] = destino
            if np.isfinite(destino).any():
                con_datos = True

        if not con_datos:
            print(f"  {item.id}: sin pixeles validos tras SCL")
            continue

        for nombre, capa in reproyectados.items():
            pilas.setdefault(nombre, []).append(capa)
        usados.append({"id": item.id, "cloud": round(nubes, 2)})
        principal = next(iter(reproyectados.values()))
        print(
            f"  {item.id}: {nubes:.1f}% nubes · "
            f"{int(np.isfinite(principal).sum())} px"
        )

    if not pilas:
        return None, usados

    salida = {nombre: optico.compuesto_mediana(capas) for nombre, capas in pilas.items()}
    _guardar_cache(clave, salida, usados)
    return salida, usados


def _calcular_ndvi(datos):
    nd = optico.ndvi(datos["B04"], datos["B08"])
    nd[~optico.mascara_scl(datos["SCL"])] = np.nan
    return {"ndvi": nd}


def _calcular_indices(datos):
    valida = optico.mascara_scl(datos["SCL"])
    ndvi = optico.ndvi(datos["B04"], datos["B08"])
    ndbi = optico.ndbi(datos["B11"], datos["B08"])
    ndwi = optico.ndwi(datos["B03"], datos["B08"])
    nbr = optico.nbr(datos["B08"], datos["B12"])
    for capa in (ndvi, ndbi, ndwi, nbr):
        capa[~valida] = np.nan
    return {"ndvi": ndvi, "ndbi": ndbi, "ndwi": ndwi, "nbr": nbr}


def _calcular_color(datos):
    """Reflectancia R/G/B enmascarada con SCL, todavia sin estirar.

    La mediana entre items va sobre reflectancia cruda: el estirado a 8 bits
    se hace despues para que dos fechas comparables salgan con la misma escala.
    """
    valida = optico.mascara_scl(datos["SCL"])
    return {
        "R": np.where(valida, datos["B04"], np.nan).astype(np.float32),
        "G": np.where(valida, datos["B03"], np.nan).astype(np.float32),
        "B": np.where(valida, datos["B02"], np.nan).astype(np.float32),
    }


def componer_ndvi(
    items,
    bbox: tuple[float, float, float, float],
    destino_forma: tuple[int, int],
    destino_transform,
    destino_crs,
    px: int,
) -> tuple[np.ndarray | None, list[dict]]:
    """NDVI mediano de todos los items que se puedan leer.

    Devuelve ``(None, usados)`` si ningun item dejo pixeles validos: el llamador
    decide si cae a otro metodo o corta.
    """
    salida, usados = _componer(
        items,
        bbox,
        destino_forma,
        destino_transform,
        destino_crs,
        px,
        BANDAS_NDVI,
        _calcular_ndvi,
        "ndvi",
    )
    if salida is None:
        return None, usados
    return salida["ndvi"], usados


def componer_indices(
    items,
    bbox: tuple[float, float, float, float],
    destino_forma: tuple[int, int],
    destino_transform,
    destino_crs,
    px: int,
) -> tuple[dict[str, np.ndarray] | None, list[dict]]:
    """NDVI, NDBI, NDWI y NBR medianos, alineados a la grilla del recorte NISAR.

    Cuesta tres aperturas remotas mas por item que `componer_ndvi` (verde, SWIR1
    y SWIR2), por eso vive en su propia entrada de cache.
    """
    return _componer(
        items,
        bbox,
        destino_forma,
        destino_transform,
        destino_crs,
        px,
        BANDAS_INDICES,
        _calcular_indices,
        "indices",
    )


def componer_color(
    items,
    bbox: tuple[float, float, float, float],
    destino_forma: tuple[int, int],
    destino_transform,
    destino_crs,
    px: int,
) -> tuple[np.ndarray | None, list[dict]]:
    """Color real (mediana de reflectancia R/G/B) alineado a la grilla destino.

    El estirado 2-98% va DESPUES de la mediana y sobre los tres canales juntos
    (no por canal), para que el balance de color no se tiña y dos fechas
    comparables salgan con la misma escala. Devuelve RGB uint8 o ``(None,
    usados)`` si ningun item dejo pixeles.
    """
    salida, usados = _componer(
        items,
        bbox,
        destino_forma,
        destino_transform,
        destino_crs,
        px,
        BANDAS_COLOR,
        _calcular_color,
        "color",
    )
    if salida is None:
        return None, usados
    apilado = np.stack([salida["R"], salida["G"], salida["B"]])  # (3, H, W)
    con_dato = np.isfinite(apilado).all(axis=0)
    muestra = apilado[np.isfinite(apilado)]
    if muestra.size == 0:
        return None, usados
    lo, hi = np.percentile(muestra, [2, 98])
    if hi <= lo:
        hi = lo + 1.0
    norm = np.clip((apilado - lo) / (hi - lo), 0.0, 1.0)
    rgb = (np.moveaxis(np.nan_to_num(norm, nan=0.0), 0, -1) * 255.0).astype(np.uint8)
    rgb[~con_dato] = (8, 9, 10)
    return rgb, usados
