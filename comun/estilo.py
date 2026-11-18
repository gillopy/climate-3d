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

#: Tipografías en orden de preferencia. Arial y Helvetica son las que traen
#: Windows y macOS; DejaVu Sans viaja dentro de matplotlib, así que el render
#: nunca depende de una fuente instalada en la máquina que lo corre.
TIPOGRAFIAS = ("Arial", "Helvetica", "DejaVu Sans")


def tipografia() -> str:
    """Primera tipografía de `TIPOGRAFIAS` que esté instalada.

    Se resuelve una vez, al importar: pedirle a matplotlib una familia ausente
    sólo deja un warning y cae al default, y acá se quiere el control explícito.
    """
    from matplotlib import font_manager

    instaladas = {fuente.name for fuente in font_manager.fontManager.ttflist}
    for nombre in TIPOGRAFIAS:
        if nombre in instaladas:
            return nombre
    return "DejaVu Sans"


FUENTE = tipografia()


def ruta_fuente(negrita: bool = False) -> str:
    """Ruta del TTF de `FUENTE` para Pillow, resuelta igual que en matplotlib.

    Evita los `C:\\Windows\\Fonts\\...` fijos: en otra máquina ese camino no
    existe y Pillow caía a su fuente bitmap, que a tamaño de póster se ve
    horrible.
    """
    from matplotlib import font_manager

    peso = "bold" if negrita else "normal"
    return font_manager.findfont(
        font_manager.FontProperties(family=FUENTE, weight=peso),
        fallback_to_default=True)


# Paleta muestreada píxel a píxel de la barra de color de la referencia
ANOM_COLORS = [
    (0 / 12,  "#02091b"), (1 / 12,  "#041f4c"), (2 / 12,  "#0a3874"),
    (3 / 12,  "#165696"), (4 / 12,  "#2d77b6"), (5 / 12,  "#91b8d7"),
    (6 / 12,  "#f7f8fa"), (7 / 12,  "#f5a099"), (8 / 12,  "#f0493a"),
    (9 / 12,  "#b7231c"), (10 / 12, "#780912"), (11 / 12, "#47000a"),
    (12 / 12, "#1b0002"),
]
ANOM_CMAP = LinearSegmentedColormap.from_list("anomaly_ref", ANOM_COLORS)
