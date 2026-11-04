"""Resolución de los slots GeoColor más nuevos ya publicados en NASA GIBS.

GIBS no expone un "último" consultable: para un instante sin gránulo contesta
200 con una imagen negra. Este módulo camina hacia atrás pidiendo una miniatura
(64x64) y valida que tenga color, igual que `descargar/geocolor.valida`, pero sin
traer `requests` (el `.venv` de la API no lo tiene).

Solo stdlib + Pillow, que ya está en los dos entornos.
"""
from __future__ import annotations

import io
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://wvs.earthdata.nasa.gov/api/v1/snapshot"

#: Capa ya mezclada de GIBS por satélite.
CAPAS = {
    "G19": "GOES-East_ABI_GeoColor",
    "G16": "GOES-East_ABI_GeoColor",
    "G18": "GOES-West_ABI_GeoColor",
}

PASO = 10                        # minutos entre gránulos
MARGEN = timedelta(minutes=40)   # latencia típica de GIBS
INTENTOS = 36                    # 6 h hacia atrás

#: Caja sobre Sudamérica (sur, oeste, norte, este): GeoColor la cubre de día y de
#: noche, así que una miniatura negra significa "sin gránulo", no "sin luz".
CAJA = (-40.0, -70.0, -10.0, -40.0)


def piso_slot(t: datetime, paso: int = PASO) -> datetime:
    """Baja `t` al múltiplo de `paso` minutos ya cumplido."""
    return t.replace(second=0, microsecond=0, minute=t.minute - t.minute % paso)


def _valido(t: datetime, capa: str, timeout: int = 20) -> bool:
    """True si GIBS devuelve una imagen con dato para ese instante."""
    momento = t.strftime("%Y-%m-%dT%H:%M:%SZ")
    sur, oeste, norte, este = CAJA
    url = (f"{API}?REQUEST=GetSnapshot&TIME={momento}"
           f"&BBOX={sur},{oeste},{norte},{este}&CRS=EPSG:4326"
           f"&LAYERS={capa}&FORMAT=image/jpeg&WIDTH=64&HEIGHT=64")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as respuesta:
            datos = respuesta.read()
    except Exception:
        return False
    if len(datos) < 400:
        return False
    try:
        from PIL import Image

        with Image.open(io.BytesIO(datos)) as imagen:
            return max(imagen.convert("L").getdata()) > 8
    except Exception:
        return False


def ultimos_slots(sat: str, n: int, ahora: datetime | None = None,
                  paso: int = PASO, intentos: int = INTENTOS) -> list[datetime]:
    """Los `n` slots GeoColor más nuevos publicados, del más viejo al más nuevo."""
    if n <= 0:
        return []
    capa = CAPAS.get(sat.upper(), CAPAS["G19"])
    t = piso_slot((ahora or datetime.now(timezone.utc).replace(tzinfo=None)) - MARGEN, paso)
    ultimo: datetime | None = None
    for _ in range(intentos):
        if _valido(t, capa):
            ultimo = t
            break
        t -= timedelta(minutes=paso)
    if ultimo is None:
        raise LookupError(
            f"No encontré ningún GeoColor publicado de {sat} en las últimas "
            f"{intentos * paso // 60} h. Revisá la conexión o pedí una fecha explícita."
        )
    return [ultimo - timedelta(minutes=paso * (n - 1 - i)) for i in range(n)]
