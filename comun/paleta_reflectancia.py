"""Paleta de reflectancia de la pagina de GOES (bandas ABI 1 a 6).

Las bandas 1-6 no miden temperatura: miden reflectancia (0 a 100 %), asi que
NOAA no publica una barra de color para ellas. Las imagenes de disco completo
de la pagina (C01 azul 0.47 um, C02 rojo 0.64, C03 veggie 0.86, C04 cirrus
1.37, C05 nieve 1.61, C06 particula de nube 2.24) van en una rampa de negro a
blanco: poco reflectante = negro (oceano, noche), muy reflectante = blanco
(nubes, nieve).

La rampa no es lineal. Comparando nuestras salidas con las imagenes oficiales
de la misma hora (C06 y C02 del 2026-11-08 16:10Z) por cuantiles, el gris de
NOAA sigue una gamma ~0.70 sobre la reflectancia normalizada: un cielo de 12 %
sale en 0.23 en vez de 0.12, y una nube de 50 % en 0.62. Ajustada sobre las dos
bandas, el error medio queda en 1.7 % del rango.

Escala fija: VMIN = 0.0, VMAX = 100.0 (por ciento de reflectancia).
"""
from __future__ import annotations

import numpy as np
from matplotlib.colors import ListedColormap

#: Extremos de la escala (por ciento de reflectancia).
VMIN, VMAX = 0.0, 100.0

#: Gamma de la rampa: el gris es `(reflectancia normalizada) ** GAMMA`.
GAMMA = 0.70

#: Nombre para trazar el origen en la UI / pie del poster.
NOMBRE_REFLECTANCIA = "Reflectancia_GOES_v1"


def _cmap() -> ListedColormap:
    """Rampa negro -> blanco con la gamma medida en las imagenes oficiales.

    Se arma como tabla (ListedColormap) en vez de interpolar dos extremos:
    la gamma es justamente la no linealidad entre negro y blanco.
    """
    x = np.linspace(0.0, 1.0, 2048)
    gris = np.clip(x, 0.0, 1.0) ** GAMMA
    return ListedColormap(np.stack([gris, gris, gris], axis=1),
                          name="reflectancia", N=2048)


#: Colormap listo para usar (rampa de reflectancia de la pagina de GOES).
CMAP_REFLECTANCIA = _cmap()
