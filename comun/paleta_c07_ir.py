"""Paleta IR oficial de la pagina de GOES, banda 7 (ABI C07, 3.9 um).

NOAA STAR publica una barra propia para la banda 7 ("shortwave window"):
`images/colorbars/ColorBar450Band7_horz.png`. 450 px, de -83 a 127 C.

La barra NO es lineal en temperatura: las marcas (-83, -42, -13, 13, 38, 127)
estan a ~89 px una de otra, asi que cada tramo ocupa un ancho distinto en
grados. Cada nodo se leyo del PNG (fila 5, fuera del glifo "C" y de las
marcas) y se convirtio con esa escala por tramos.

Distribucion medida (de frio a calido):

-  -83 a -61: gris medio -> gris muy oscuro (topes frios).
-  -61 a -60: caida a negro (la barra comprime ahi los ultimos grises).
-  -60 a -53: negro -> rojo puro.
-  -53 a -45: rojo -> amarillo.
-  -45 a -38: amarillo -> verde.
-  -38 a -33: verde -> azul oscuro.
-  -33 a -26: azul oscuro -> cian.
-  -26 a -25: salto cian -> gris claro (fin del tramo de color).
-  -25 a  127: rampa gris claro -> negro, con gris medio en -13, gris en 13
  y gris oscuro en 38.

Escala fija: VMIN = -83.0, VMAX = 127.0 (C).
"""
from __future__ import annotations

from matplotlib.colors import LinearSegmentedColormap

#: Extremos de la escala de la barra oficial.
VMIN, VMAX = -83.0, 127.0

#: Nombre para trazar el origen en la UI / pie del poster.
NOMBRE_C07_IR = "C07_IR_Oficial_GOES_v1"

#: Nodos `(temp_C, (r, g, b))` muestreados del PNG oficial en la fila 5.
#: El comentario dice en que pixel se midio cada uno.
NODOS_TEMP = [
    ( -83.0, (0x7C, 0x7C, 0x7C)),  # gris medio, extremo frio (x = 1)
    ( -60.8, (0x19, 0x19, 0x19)),  # ultimo gris antes del negro (x = 50)
    ( -59.9, (0x00, 0x00, 0x00)),  # negro (x = 52)
    ( -52.9, (0xFF, 0x00, 0x00)),  # rojo puro (x = 67.5)
    ( -45.0, (0xFF, 0xFF, 0x00)),  # amarillo (x = 85)
    ( -42.0, (0xA7, 0xFF, 0x00)),  # marca -42, el eje cambia de pendiente (x = 91.5)
    ( -38.4, (0x00, 0xFF, 0x00)),  # verde (x = 102.5)
    ( -33.4, (0x00, 0x03, 0x71)),  # quiebre del azul: el verde deja de caer (x = 118)
    ( -32.6, (0x00, 0x01, 0x73)),  # azul profundo, minimo de la barra (x = 120.5)
    ( -25.8, (0x00, 0xFF, 0xFF)),  # cian (x = 141.3)
    ( -24.6, (0xBD, 0xBD, 0xBD)),  # arranca el gris (x = 145)
    ( -13.0, (0xA7, 0xA7, 0xA7)),  # gris medio, marca -13 (x = 180.5)
    (  13.0, (0x70, 0x70, 0x70)),  # gris, marca 13 (x = 268.5)
    (  38.0, (0x38, 0x38, 0x38)),  # gris oscuro, marca 38 (x = 357)
    ( 127.0, (0x00, 0x00, 0x00)),  # negro, marca 127 (x = 448)
]

#: Nodos `(pos_normalizada, (r, g, b))` derivados de las temperaturas.
NODOS_C07_IR = [((t - VMIN) / (VMAX - VMIN), rgb) for t, rgb in NODOS_TEMP]


def _cmap():
    """Rampa oficial de la banda 7 (210 C de escala).

    Con N=2048 son 0.10 C por bin: el tramo de color (-60 a -25) conserva los
    degradados de la barra y el gris calido degrada sin escalones.
    """
    colores = [tuple(c / 255.0 for c in rgb) for _, rgb in NODOS_C07_IR]
    posiciones = [pos for pos, _ in NODOS_C07_IR]
    # `from_list` interpola lineal entre nodos: dentro de cada tramo de la
    # barra el color tambien es lineal, asi que la rampa coincide.
    return LinearSegmentedColormap.from_list(
        "c07_ir_oficial", list(zip(posiciones, colores)), N=2048
    )


#: Colormap listo para usar (equivale a la barra oficial de la banda 7).
CMAP_C07_IR_OFICIAL = _cmap()
