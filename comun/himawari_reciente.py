"""Resolución del slot Himawari-9 más nuevo publicado en el bucket de NOAA.

El AHI publica cada 10 minutos en `noaa-himawari9` y cada slot son 10 segmentos.
"El más nuevo" no se calcula con el reloj: se camina hacia atrás listando el
prefijo de cada hora y se exige que estén los 10 segmentos. Solo stdlib.
"""
from __future__ import annotations

import re
import urllib.request
from datetime import datetime, timedelta, timezone

BUCKET = "https://noaa-himawari9.s3.amazonaws.com"
PREFIJO = "AHI-L1b-FLDK"
RESOLUCION = "R20"
BANDA = 13
SEGMENTOS = 10
PASO = 10
INTENTOS_HORAS = 6

_CLAVE = re.compile(r"<Key>([^<]+)</Key>")
_SLOT = re.compile(
    rf"HS_H09_(\d{{8}})_(\d{{4}})_B{BANDA:02d}_FLDK_{RESOLUCION}_S(\d{{2}})10\.DAT\.bz2$"
)


def piso_slot(t: datetime, paso: int = PASO) -> datetime:
    """Baja `t` al múltiplo de `paso` minutos ya cumplido."""
    return t.replace(second=0, microsecond=0, minute=t.minute - t.minute % paso)


def _slots_de_la_hora(hora: datetime, timeout: int = 60) -> dict[datetime, set[int]]:
    """{instante: {segmentos publicados}} de esa hora del bucket."""
    url = f"{BUCKET}/?list-type=2&prefix={PREFIJO}/{hora:%Y/%m/%d/%H}/"
    with urllib.request.urlopen(url, timeout=timeout) as respuesta:
        xml = respuesta.read().decode()
    salida: dict[datetime, set[int]] = {}
    for clave in _CLAVE.findall(xml):
        match = _SLOT.search(clave)
        if not match:
            continue
        instante = datetime.strptime(match.group(1) + match.group(2), "%Y%m%d%H%M")
        salida.setdefault(instante, set()).add(int(match.group(3)))
    return salida


def ultimos_slots(n: int, ahora: datetime | None = None, paso: int = PASO,
                  intentos_horas: int = INTENTOS_HORAS) -> list[datetime]:
    """Los `n` slots más nuevos con los 10 segmentos, del más viejo al más nuevo."""
    if n <= 0:
        return []
    t = piso_slot(ahora or datetime.now(timezone.utc).replace(tzinfo=None), paso)
    por_hora: dict[datetime, dict[datetime, set[int]]] = {}
    encontrados: list[datetime] = []
    for _ in range(intentos_horas * 60 // paso):
        hora = t.replace(minute=0)
        if hora not in por_hora:
            try:
                por_hora[hora] = _slots_de_la_hora(hora)
            except Exception:  # red: se sigue con la hora anterior
                por_hora[hora] = {}
        if len(por_hora[hora].get(t, set())) == SEGMENTOS:
            encontrados.append(t)
            if len(encontrados) == n:
                break
        t -= timedelta(minutes=paso)
    return sorted(encontrados)
