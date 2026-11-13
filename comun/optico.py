"""Utilidades ópticas puras (numpy) para la fusión con NISAR.

Acá no hay rasterio ni STAC: solo NDVI, la máscara de clases SCL de Sentinel-2,
el compuesto mediano y la clasificación rule-based. Así se puede probar sin red
ni dependencias pesadas; el script `nisar_fusion.py` se encarga de bajar y
reproyectar las imágenes.
"""
from __future__ import annotations

import numpy as np

#: Clases SCL que no sirven para NDVI: nodata, saturado, sombra, nubes, cirrus,
#: nieve. El agua (6) se conserva: es una clase válida para NDVI y para el mapa.
SCL_MALOS = (0, 1, 3, 8, 9, 10, 11)

CLASES = {
    0: "sin dato",
    1: "agua",
    2: "bosque",
    3: "cultivo / vegetación",
    4: "suelo / urbano",
}

#: Color RGB por índice de clase (0..4).
COLORES = np.array(
    [
        [0, 0, 0],
        [25, 105, 220],
        [20, 90, 45],
        [190, 200, 80],
        [150, 130, 110],
    ],
    dtype=np.uint8,
)


def ndvi(rojo: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """NDVI = (NIR - rojo) / (NIR + rojo), NaN donde la suma no es positiva."""
    rojo = np.asarray(rojo, dtype=np.float32)
    nir = np.asarray(nir, dtype=np.float32)
    suma = nir + rojo
    salida = np.full(suma.shape, np.nan, dtype=np.float32)
    np.divide(nir - rojo, suma, out=salida, where=suma > 0)
    return salida


def mascara_scl(scl: np.ndarray) -> np.ndarray:
    """True en las clases SCL utilizables (no nube/sombra/nodata/nieve)."""
    return ~np.isin(np.asarray(scl), SCL_MALOS)


def compuesto_mediana(ndvis: list[np.ndarray]) -> np.ndarray:
    """Mediana pixel a pixel de los NDVI ya alineados a la misma grilla."""
    if not ndvis:
        raise ValueError("No hay NDVI para componer")
    pila = np.stack([np.asarray(valor, dtype=np.float32) for valor in ndvis])
    return np.nanmedian(pila, axis=0).astype(np.float32)


def clasificar(
    hv_db: np.ndarray,
    ndvi_comp: np.ndarray,
    *,
    ndvi_bosque: float = 0.55,
    ndvi_cultivo: float = 0.25,
    hv_bosque: float = -15.5,
    hv_agua: float = -20.0,
) -> np.ndarray:
    """Clasificación rule-based en 4 clases (1 agua, 2 bosque, 3 cultivo, 4 suelo).

    No es un modelo entrenado: es una regla interpretable para explorar la fusión.
    Los umbrales se exponen en la UI porque cambian con la estación y la región.
    """
    hv = np.asarray(hv_db, dtype=np.float32)
    nd = np.asarray(ndvi_comp, dtype=np.float32)
    clases = np.zeros(hv.shape, dtype=np.uint8)
    valido = np.isfinite(hv) & np.isfinite(nd)
    agua = valido & (nd < 0.10) & (hv < hv_agua)
    bosque = valido & ~agua & (nd > ndvi_bosque) & (hv > hv_bosque)
    cultivo = valido & ~agua & ~bosque & (nd > ndvi_cultivo)
    suelo = valido & ~agua & ~bosque & ~cultivo
    clases[agua] = 1
    clases[bosque] = 2
    clases[cultivo] = 3
    clases[suelo] = 4
    return clases
