"""Reuso de cuadros ya renderizados: nombre por instante y almacén compartido.

Un cuadro se identifica por su **instante UTC**, no por su posición en la serie.
Así el mismo slot, con el mismo aspecto, es el mismo archivo en cualquier
ventana: pedir 22→24 y después 22→26 reusa lo que ya está en vez de renumerar y
rehacerlo todo. Con nombres posicionales (`cuadro_001.png`) un hueco recuperado
corre todos los índices y el reuso devuelve cuadros con el timestamp equivocado.

El almacén vive fuera de la carpeta del job::

    <DATOS>\\cuadros_render\\<producto>\\<sat>\\<sello>\\cuadro_20261122T0040.png

`<sello>` es la huella de aspecto que calcula cada renderer (px, dpi, encuadre,
escala, paleta, versión de diseño): dos aspectos distintos NUNCA comparten
carpeta, porque mezclar 1400 con 2712 px (o `clean_ir` con `c13_ir`) cambia los
colores y las escalas del video.

La carpeta del job no copia bytes: enlaza (`os.link`) cada cuadro de SU ventana y
sólo cae a copia cuando el sistema de archivos no permite enlaces duros (otro
volumen, FAT). Borrar el job libera su enlace, nunca el cuadro del almacén.
"""
from __future__ import annotations

import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Sequence

#: Nombre canónico de un cuadro: el instante UTC, ordenable como texto.
PATRON = "cuadro_%Y%m%dT%H%M.png"

_RE_INSTANTE = re.compile(r"^cuadro_(\d{8})T(\d{4})\.png$")


def nombre_cuadro(instante: datetime) -> str:
    """Nombre del cuadro para ese instante UTC (`cuadro_20261122T0040.png`)."""
    return instante.strftime(PATRON)


def instante_de(nombre: str) -> datetime | None:
    """Instante del nombre, o `None` si el nombre es de los viejos (`cuadro_001`)."""
    match = _RE_INSTANTE.match(Path(nombre).name)
    if match is None:
        return None
    return datetime.strptime(match.group(1) + match.group(2), "%Y%m%d%H%M")


def es_de_instante(nombre: str) -> bool:
    """True si el nombre sigue el patrón por instante (no el numerado viejo)."""
    return _RE_INSTANTE.match(Path(nombre).name) is not None


def carpeta_almacen(raiz: Path | str, sello: str) -> Path:
    """Carpeta del almacén para un aspecto: `raiz/<sello>`."""
    return Path(raiz) / sello


def plan_de_reuso(
    almacen: Path, instantes: Sequence[datetime]
) -> tuple[list[datetime], list[datetime]]:
    """Separa los instantes pedidos en (ya renderizados, hay que renderizar)."""
    listos: list[datetime] = []
    faltan: list[datetime] = []
    for instante in instantes:
        if (Path(almacen) / nombre_cuadro(instante)).is_file():
            listos.append(instante)
        else:
            faltan.append(instante)
    return listos, faltan


def enlazar(origen: Path | str, destino: Path | str) -> None:
    """Deja `destino` con el mismo contenido, sin copiar bytes cuando se puede.

    Un enlace duro es el mismo archivo con dos nombres: no ocupa más disco y la
    edición de uno se ve en el otro (los PNG son inmutables, así que no importa).
    Si el enlace falla —otro volumen, sistema de archivos sin soporte— se copia.
    """
    origen = Path(origen)
    destino = Path(destino)
    if destino.exists():
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(origen, destino)
    except OSError:
        shutil.copy2(origen, destino)
