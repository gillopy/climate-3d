"""Serie temporal y etiqueta de carpeta, compartidas entre descarga y render.

Una misma corrida (descarga + render) tiene que coincidir en dos cosas que no pueden
desincronizarse: **qué instantes** forman la animación y **cómo se llama la carpeta** de
cuadros. Si cada script las calculara por su cuenta, alcanzaría con cambiar el paso o el
formato de la etiqueta en un solo lado para que el render salga a buscar una carpeta que
no existe. Por eso viven acá, en un único lugar, y no dentro de cada par descarga/render.
"""
from __future__ import annotations

from datetime import datetime, timedelta


def serie_fechas(desde: str, hasta: str, paso_min: int) -> list[datetime]:
    """Instantes desde `desde` hasta `hasta` (inclusive), cada `paso_min` minutos.

    Ambos extremos se parsean con `datetime.fromisoformat`, así que aceptan ``AAAA-MM-DD``
    o ``AAAA-MM-DDTHH:MM``. El borde superior entra si cae justo sobre ``hasta``; si el
    siguiente instante ya lo pasa, la serie corta antes.
    """
    inicio = datetime.fromisoformat(desde)
    fin = datetime.fromisoformat(hasta)
    paso = timedelta(minutes=paso_min)
    fechas: list[datetime] = []
    t = inicio
    while t <= fin:
        fechas.append(t)
        t += paso
    return fechas


def etiqueta_frames(producto: str, vista: str, t0: datetime, n: int, px: int) -> str:
    """Etiqueta de la carpeta de cuadros: producto, vista, inicio, cantidad y px.

    Incluye inicio + cantidad + px para que una corrida no pise a otra ventana o
    resolución. La descarga y el render la piden con los mismos argumentos y obtienen
    exactamente la misma cadena, que es lo que evita que se desincronicen.
    """
    return f"{producto}_{vista}_{t0:%Y-%m-%dT%H%M}_{n}f_{px}px"
