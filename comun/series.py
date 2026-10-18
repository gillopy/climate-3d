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


def serie_diurna(desde: str, hasta: str, hora_desde: int, hora_hasta: int,
                 paso_min: int) -> list[datetime]:
    """Instantes del tramo diurno de cada día de `desde` a `hasta` (inclusive).

    Devuelve, para cada día del rango, los instantes desde `hora_desde` hasta
    `hora_hasta` UTC cada `paso_min` minutos, en orden cronológico y sin huecos dentro
    de cada tramo. El borde `hora_hasta` entra sólo si cae justo sobre un paso (igual
    que `serie_fechas` con su borde superior).

    `desde`/`hasta` se parsean con `datetime.fromisoformat`, pero de ellos sólo importa
    la **fecha**: la hora de esos dos strings se ignora, porque el tramo de cada día lo
    fijan `hora_desde`/`hora_hasta`. Sirve para productos que sólo tienen sentido de día
    (p. ej. el Sandwich, cuyo visible viene negro de noche): en vez de correr las 48 h
    seguidas se toma el tramo iluminado de cada jornada, con el mismo `paso_min` en los
    dos extremos para que la descarga y el render calculen exactamente la misma lista.
    """
    inicio = datetime.fromisoformat(desde).date()
    fin = datetime.fromisoformat(hasta).date()
    paso = timedelta(minutes=paso_min)
    fechas: list[datetime] = []
    dia = inicio
    while dia <= fin:
        t = datetime(dia.year, dia.month, dia.day, hora_desde, 0)
        limite = datetime(dia.year, dia.month, dia.day, hora_hasta, 0)
        while t <= limite:
            fechas.append(t)
            t += paso
        dia += timedelta(days=1)
    return fechas


def etiqueta_frames(producto: str, vista: str, t0: datetime, n: int, px: int) -> str:
    """Etiqueta de la carpeta de cuadros: producto, vista, inicio, cantidad y px.

    Incluye inicio + cantidad + px para que una corrida no pise a otra ventana o
    resolución. La descarga y el render la piden con los mismos argumentos y obtienen
    exactamente la misma cadena, que es lo que evita que se desincronicen.
    """
    return f"{producto}_{vista}_{t0:%Y-%m-%dT%H%M}_{n}f_{px}px"
