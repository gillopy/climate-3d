"""Constantes visuales compartidas de los pósteres.

Valores idénticos a los que estaban inline en `poster_anomalia.py`: fondo, colores de
texto, marca de agua, nombres de meses y la rampa divergente de anomalía. Se centralizan
acá para que el póster de ERA5, el de GOES y las animaciones usen el mismo vestuario.
"""
from __future__ import annotations

from matplotlib.colors import LinearSegmentedColormap

MONTHS_EN = ("JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
             "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER")

POSTER_SIZE, POSTER_DPI = 8.4, 140     # 1176 px de lado

BG = "#0c1014"                        # fondo del póster (muestreado de la referencia)
TXT, TXT_DIM = "#ffffff", "#c9cfd6"
WM_COLOR = "#46536b"                  # marca de agua, discreta sobre el mapa

# Paleta muestreada píxel a píxel de la barra de color de la referencia
ANOM_COLORS = [
    (0 / 12,  "#02091b"), (1 / 12,  "#041f4c"), (2 / 12,  "#0a3874"),
    (3 / 12,  "#165696"), (4 / 12,  "#2d77b6"), (5 / 12,  "#91b8d7"),
    (6 / 12,  "#f7f8fa"), (7 / 12,  "#f5a099"), (8 / 12,  "#f0493a"),
    (9 / 12,  "#b7231c"), (10 / 12, "#780912"), (11 / 12, "#47000a"),
    (12 / 12, "#1b0002"),
]
ANOM_CMAP = LinearSegmentedColormap.from_list("anomaly_ref", ANOM_COLORS)
