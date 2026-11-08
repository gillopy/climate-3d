"""Paleta IR oficial de la pagina de GOES para el vapor de agua (bandas 8 a 10).

NOAA STAR publica una sola barra para las tres bandas de vapor:
`images/colorbars/ColorBar450Bands8-10_horz.png`, la que muestran las fichas
de las bandas 8 (6.2 um), 9 (6.9) y 10 (7.3). 450 px, de -93 a 7 C.

La barra NO es lineal en temperatura: las marcas (-93, -54, -30, -18, -5, 7)
estan a ~88 px una de otra, asi que cada tramo ocupa un ancho distinto en
grados. Cada nodo se leyo del PNG (fila 35, fuera del glifo "C") y se convirtio
con esa escala por tramos.

Lectura de la barra (ficha de la banda):
- rojo a amarillo: atmosfera seca;
- amarillo, blanco y azul: relativamente humeda;
- mas frio que el blanco, incluido el verde: nubes.

Distribucion medida (de frio a calido):

- -93 a -74: cian -> verde oscuro (nubes).
- -74 a -41: verde -> blanco (topes nubosos muy frios).
- -41 a -24: blanco -> violeta/azul profundo (lo mas humedo).
- -24 a -16: violeta -> amarillo.
- -16 a  +2: amarillo -> naranja -> rojo (seco).
-  +2 a  +7: negro (reserva de la barra).

Escala fija: VMIN = -93.0, VMAX = 7.0 (C).
"""
from __future__ import annotations

from matplotlib.colors import LinearSegmentedColormap

#: Extremos de la escala de la barra oficial.
VMIN, VMAX = -93.0, 7.0

#: Nombre para trazar el origen en la UI / pie del poster.
NOMBRE_IR_VAPOR = "IR_Vapor_Oficial_GOES_v1"

#: Nodos `(temp_C, (r, g, b))` muestreados del PNG oficial en la fila 5 (por
#: encima del glifo "C" y de las marcas). Hay un nodo en cada quiebre de color
#: y en cada marca de la escala: como el eje del grafico es por tramos, sin el
#: nodo en la marca la interpolacion lineal no reproduce la barra.
NODOS_TEMP = [
    (-93.0, (0x00, 0xFF, 0xFF)),  # cian (x = 1)
    (-74.3, (0x43, 0x82, 0x22)),  # verde oscuro, fin del tramo de nubes (x = 46)
    (-54.0, (0xA4, 0xC2, 0x94)),  # marca -54 (x = 95)
    (-41.3, (0xFF, 0xFF, 0xFF)),  # blanco (x = 141)
    (-30.0, (0x88, 0x88, 0xBE)),  # marca -30 (x = 182)
    (-23.7, (0x00, 0x00, 0x73)),  # violeta/azul profundo, lo mas humedo (x = 228)
    (-18.0, (0xC8, 0xC8, 0x19)),  # marca -18 (x = 270)
    (-16.2, (0xFF, 0xFF, 0x00)),  # amarillo (x = 282)
    ( -5.0, (0xFF, 0x6D, 0x00)),  # marca -5, naranja (x = 357)
    (  2.3, (0xFF, 0x00, 0x00)),  # rojo (x = 412)
    (  2.5, (0x00, 0x00, 0x00)),  # negro: corte duro del extremo seco (x = 414)
    (  7.0, (0x00, 0x00, 0x00)),  # negro hasta el final (x = 448)
]

#: Nodos `(pos_normalizada, (r, g, b))` derivados de las temperaturas.
NODOS_IR_VAPOR = [((t - VMIN) / (VMAX - VMIN), rgb) for t, rgb in NODOS_TEMP]


def _cmap():
    """Rampa oficial de vapor de agua (100 C de escala).

    Con N=2048 son 0.05 C por bin: el tramo humedo (blanco-violeta) y el seco
    (amarillo-rojo) conservan los degradados de la barra.
    """
    colores = [tuple(c / 255.0 for c in rgb) for _, rgb in NODOS_IR_VAPOR]
    posiciones = [pos for pos, _ in NODOS_IR_VAPOR]
    # `from_list` interpola lineal entre nodos: dentro de cada tramo de la
    # barra el color tambien es lineal, asi que la rampa coincide.
    return LinearSegmentedColormap.from_list(
        "ir_vapor_oficial", list(zip(posiciones, colores)), N=2048
    )


#: Colormap listo para usar (equivale a la barra oficial de vapor de agua).
CMAP_IR_VAPOR = _cmap()
