"""Resolución de los slots GOES más nuevos publicados en NOAA S3.

Solo stdlib a propósito: lo usan tanto los scripts de descarga (`.venv` del repo,
con xarray/cartopy) como la API de la app (`app\\.venv`, que no los tiene).

El ABI publica cada 10 minutos con ~20 minutos de retraso, y a veces se saltea un
slot. Por eso "el más nuevo" no se calcula con `ahora`: se camina hacia atrás
consultando el listado del bucket, una sola vez por hora.

  * `listar_hora` — claves S3 de una hora (una consulta HTTP).
  * `ultimos_slots` — los `n` instantes publicados más nuevos, en orden.
  * `ventana_ultimos` / `ventana_ultimas` — rangos `[desde, hasta)` que consumen
    `descargar_goes.py` y la app.
  * `ultimos_de` — recorte de la cola para los renderers (leen disco, sin red).
"""
from __future__ import annotations

import re
import urllib.request
from datetime import datetime, timedelta, timezone

PASO = 10                    # minutos entre slots: la cadencia real del ABI
INTENTOS_HORAS = 24          # cuántas horas hacia atrás se buscan como máximo

_CLAVE = re.compile(r"<Key>([^<]+)</Key>")
_ABI = re.compile(r"OR_ABI-L2-CMIPF-M6(?P<banda>C\d+)_(?P<sat>G\d+)_s(?P<s>\d{14})_")


def ahora_utc() -> datetime:
    """Ahora en UTC, sin `tzinfo` (como el resto de los scripts)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def piso_slot(t: datetime, paso: int = PASO) -> datetime:
    """Baja `t` al múltiplo de `paso` minutos ya cumplido."""
    return t.replace(second=0, microsecond=0, minute=t.minute - t.minute % paso)


def listar_hora(sat: str, hora: datetime, timeout: int = 60) -> list[str]:
    """Claves del prefijo de una hora del bucket público de NOAA."""
    pref = (f"ABI-L2-CMIPF/{hora.year}/{int(hora.strftime('%j')):03d}/"
            f"{hora.hour:02d}/")
    url = f"https://noaa-goes{sat[1:]}.s3.amazonaws.com/?list-type=2&prefix={pref}"
    with urllib.request.urlopen(url, timeout=timeout) as respuesta:
        xml = respuesta.read().decode()
    return _CLAVE.findall(xml)


def _por_instante(sat: str, banda: str, hora: datetime) -> dict[datetime, str]:
    """{instante de escaneo: clave} de esa hora, sólo de esa banda y satélite."""
    salida: dict[datetime, str] = {}
    for clave in listar_hora(sat, hora):
        match = _ABI.search(clave)
        if not match or match["banda"] != banda or match["sat"] != sat:
            continue
        # El nombre trae 14 dígitos: los 13 primeros son YYYYJJJHHMMSS y el
        # último, las décimas de segundo del inicio de escaneo.
        instante = datetime.strptime(match["s"][:13], "%Y%j%H%M%S").replace(second=0)
        salida[instante] = clave
    return salida


def ultimos_slots(sat: str, banda: str, n: int, ahora: datetime | None = None,
                  paso: int = PASO, intentos_horas: int = INTENTOS_HORAS) -> list[datetime]:
    """Los `n` instantes publicados más nuevos, del más viejo al más nuevo.

    Camina hacia atrás desde `ahora` en pasos de `paso` minutos y consulta el
    listado una vez por hora. Si `n` no se completa en `intentos_horas`, devuelve
    los que haya (nunca inventa slots).
    """
    if n <= 0:
        return []
    ahora = ahora or ahora_utc()
    t = piso_slot(ahora, paso)
    por_hora: dict[datetime, dict[datetime, str]] = {}
    encontrados: list[datetime] = []
    for _ in range(intentos_horas * 60 // paso):
        hora = t.replace(minute=0)
        if hora not in por_hora:
            por_hora[hora] = _por_instante(sat, banda, hora)
        if t in por_hora[hora]:
            encontrados.append(t)
            if len(encontrados) == n:
                break
        t -= timedelta(minutes=paso)
    return sorted(encontrados)


def ventana_ultimos(n: int, sat: str, banda: str, ahora: datetime | None = None,
                    paso: int = PASO) -> tuple[datetime, datetime]:
    """`[desde, hasta)` que cubre los `n` slots más nuevos publicados."""
    slots = ultimos_slots(sat, banda, n, ahora=ahora, paso=paso)
    if not slots:
        raise LookupError(
            f"No hay gránulos nuevos de {sat} {banda} en NOAA S3. "
            "Revisá la conexión o pedí una fecha explícita."
        )
    return slots[0], slots[-1] + timedelta(minutes=paso)


def ventana_ultimas(horas: int, sat: str, banda: str, ahora: datetime | None = None,
                    paso: int = PASO) -> tuple[datetime, datetime]:
    """`[desde, hasta)` de las últimas `horas` que terminan en el slot más nuevo."""
    _, hasta = ventana_ultimos(1, sat, banda, ahora=ahora, paso=paso)
    return hasta - timedelta(hours=horas), hasta


def ultimos_de(instantes, n: int) -> list:
    """Los `n` instantes más nuevos de una colección (la cola, en orden)."""
    if n <= 0:
        return []
    return sorted(instantes)[-n:]
