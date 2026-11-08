"""Paleta IR oficial de la pagina de GOES para la ventana IR (bandas 11 a 15).

NOAA STAR publica una sola barra para toda la familia: el PNG
`images/colorbars/ColorBar450Bands11-15_horz.png` es el que muestran las
fichas de las bandas 11 (8.5 um), 12 (9.6), 13 (10.3), 14 (11.2) y 15 (12.3).
La banda 16 tiene su propia barra y vive en `paleta_c16_ir.py`.

450 px, de -110 a 57 C. Lo que cambia entre bandas es el canal fisico (µm),
no la rampa de color.

La barra NO es lineal en temperatura: las seis marcas (-110, -59, -20, 6, 31,
57) estan a ~89 px una de otra, asi que cada tramo ocupa un ancho distinto en
grados. Cada nodo de abajo se leyo del PNG y se convirtio con esa escala por
tramos, para que el color caiga en la misma temperatura que en el original.

Distribucion medida (de frio a calido):

- -110 a -93: blanco liso (topes nubosos mas frios).
-  -93 a -80: rampa blanca -> negra.
-  -80 a -71: negro -> rojo puro.
-  -71 a -61: rojo -> amarillo pasando por naranja.
-  -61 a -53: amarillo -> verde.
-  -53 a -46: verde -> azul oscuro.
-  -46 a -36: azul oscuro -> cian.
-  -36 a -34: salto cian -> gris claro (fin del tramo de color).
-  -34 a  57: rampa gris claro -> negro, con gris medio en -20, gris en 6 y
  gris oscuro en 31.

Escala fija: VMIN = -110.0, VMAX = 57.0 (C).
"""
from __future__ import annotations

from matplotlib.colors import LinearSegmentedColormap

#: Extremos de la escala de la barra oficial.
VMIN, VMAX = -110.0, 57.0

#: Nombre para trazar el origen en la UI / pie del poster.
NOMBRE_IR_VENTANA = "IR_Ventana_Oficial_GOES_v1"

#: Nodos `(temp_C, (r, g, b))` muestreados del PNG oficial en la fila central
#: de la barra (y = 20). El comentario dice en que pixel se midio cada uno.
NODOS_TEMP = [
    (-110.0, (0xFF, 0xFF, 0xFF)),  # blanco liso (x = 1)
    ( -92.8, (0xFF, 0xFF, 0xFF)),  # fin del blanco (x = 32)
    ( -80.2, (0x00, 0x00, 0x00)),  # negro (x = 54)
    ( -71.0, (0xFF, 0x05, 0x00)),  # rojo puro (x = 70)
    ( -61.0, (0xF4, 0xFF, 0x00)),  # amarillo (x = 88)
    ( -53.1, (0x06, 0xFF, 0x00)),  # verde (x = 104)
    ( -46.1, (0x00, 0x03, 0x71)),  # azul oscuro (x = 120)
    ( -36.2, (0x00, 0xFF, 0xFF)),  # cian (x = 143)
    ( -34.5, (0xBD, 0xBD, 0xBD)),  # arranca el gris (x = 147)
    ( -20.0, (0xA8, 0xA8, 0xA8)),  # gris medio, marca -20 (x = 180)
    (   6.0, (0x71, 0x71, 0x71)),  # gris, marca 6 (x = 268)
    (  31.0, (0x39, 0x39, 0x39)),  # gris oscuro, marca 31 (x = 357)
    (  57.0, (0x00, 0x00, 0x00)),  # negro, marca 57 (x = 448)
]

#: Nodos `(pos_normalizada, (r, g, b))` derivados de las temperaturas.
NODOS_IR_VENTANA = [((t - VMIN) / (VMAX - VMIN), rgb) for t, rgb in NODOS_TEMP]


def _cmap():
    """Rampa oficial para la banda 15 (167 C de escala).

    Con N=2048 son 0.08 C por bin: el tramo de color (36 C) conserva los
    degradados de la barra y el gris calido degrada sin escalones.
    """
    colores = [tuple(c / 255.0 for c in rgb) for _, rgb in NODOS_IR_VENTANA]
    posiciones = [pos for pos, _ in NODOS_IR_VENTANA]
    # `from_list` interpola lineal entre nodos: dentro de cada tramo de la
    # barra el color tambien es lineal, asi que la rampa coincide.
    return LinearSegmentedColormap.from_list(
        "ir_ventana_oficial", list(zip(posiciones, colores)), N=2048
    )


#: Colormap listo para usar (equivale a la barra oficial de la banda 15).
CMAP_IR_VENTANA = _cmap()
