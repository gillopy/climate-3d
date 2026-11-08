"""Paleta IR oficial de la pagina de GOES, banda 16 (ABI C16, 13.3 um).

Receta dictada por el usuario desde la barra oficial (-128 a 128 C):

- -128: negro -> -93: blanco (rampa de grises, tope frio extremo).
- -93: blanco -> -30: azul (degradado directo; en -60 no hay tono
  propio, el celeste que se ve es el punto medio del degradado).
- -30 -> 0 -> 30: degradado continuo azul -> bordo -> amarillo.
  En el 0 no hay corte: es la MEZCLA del azul que viene de -30 con el
  amarillo que viene de 30 (por eso se ve bordo: el tramo pasa por
  purpura/bordo antes del naranja y el amarillo).
- 30: amarillo -> 60: rojo (lado calido).
- 60: rojo -> 83: gris -> 128: negro (reserva de escala).

Todo degradados, sin cortes ni bins discretos como GIBS: se arma con
`LinearSegmentedColormap.from_list`.

Escala fija: VMIN = -128.0, VMAX = 128.0 (C).
"""
from __future__ import annotations

from matplotlib.colors import LinearSegmentedColormap

#: Extremos de la escala oficial (segun la barra de la pagina de GOES).
VMIN, VMAX = -128.0, 128.0

#: Nombre para trazar el origen en la UI / pie del poster.
NOMBRE_C16_IR = "C16_IR_Oficial_GOES_v20"

#: Nodos `(temp_C, (r, g, b))`: los MISMOS tonos de la barra oficial,
# repartidos segun los datos crudos del cuadro (BT en C derivada de la
# radiancia a 13.3 um por Planck: la escala sigue fisica y monotona).
# Distribucion medida (5.76 Mpx): -15..0 = 44 % del disco, 0..+5 = 17 %.
# En v13 el 0..+6 entero caia en amarillo (un color para un rango enorme:
# ahi se perdia el detalle). En v14 el calido vuelve a degradar
# bordo(-7) -> naranja(-1) -> amarillo(+2): cada sub-rango tiene su tono.
# Lado frio literal a la barra; rojo/gris/negro como reserva (C16 no llega).
NODOS_TEMP = [
    (-128, (0x00, 0x00, 0x00)),  # negro
    ( -93, (0xFF, 0xFF, 0xFF)),  # blanco (nucleos)
    ( -85, (0xE2, 0xE6, 0xF0)),  # hielo (blanco amplio)
    ( -70, (0xB4, 0xB8, 0xC4)),  # gris (area ampliada, cubre como el blanco)
    ( -25, (0x00, 0x00, 0xFF)),  # azul (nubes en degradado vivo)
    ( -20, (0x4A, 0x2A, 0x8C)),  # purpura (azul mezclando calido)
    ( -13, (0x70, 0x41, 0x40)),  # mezcla #704140 (banda parda ancha)
    (  -7, (0x7D, 0x12, 0x0A)),  # bordo v16 apagado (era #89140B)
    (   0, (0xC7, 0x48, 0x00)),  # naranja v16 apagado (era #D84E00)
    (  +4, (0xEB, 0xD4, 0x00)),  # amarillo v16 apagado (era #FFE800)
    ( +60, (0xFF, 0x00, 0x00)),  # rojo (reserva)
    ( +83, (0x80, 0x80, 0x80)),  # gris (reserva)
    (+128, (0x00, 0x00, 0x00)),  # negro (reserva)
]

#: Nodos `(pos_normalizada, (r, g, b))` derivados de las temperaturas.
# Posicion = (t - VMIN) / (VMAX - VMIN), con VMIN = -128 y VMAX = 128.
NODOS_C16_IR = [((t - VMIN) / (VMAX - VMIN), rgb) for t, rgb in NODOS_TEMP]


def _cmap():
    """Rampa oficial v20 para la banda 16 (gris amplio).

    Con N=256 la escala (-128 a 128 C) da 1 C por bin y todo el degradado
    calido (0 a +4 C) entraba en 4 escalones: de ahi el rango corto.
    Con N=2048 son 0.125 C por bin y el tropico degrada suave.
    """
    colores = [tuple(c / 255.0 for c in rgb) for _, rgb in NODOS_C16_IR]
    posiciones = [pos for pos, _ in NODOS_C16_IR]
    # `from_list` interpola lineal entre nodos: coincide con la barra
    # continua de la pagina (no con los bins discretos de GIBS).
    return LinearSegmentedColormap.from_list(
        "c16_ir_oficial", list(zip(posiciones, colores)), N=2048
    )


#: Colormap listo para usar (equivale a la barra oficial v20).
CMAP_C16_IR_OFICIAL = _cmap()
