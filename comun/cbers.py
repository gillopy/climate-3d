"""CBERS-4A: zonas, colecciones del STAC del INPE y elección de escena.

El INPE publica CBERS-4A en un STAC abierto (``data.inpe.br/bdc/stac/v1``) con
licencia CC-BY 4.0. Hay tres caminos según el detalle pedido:

* ``2``  — WPM PCA RGB fusionado, 2 m, COG con teselas y overviews. Cobertura
  parcial: sólo algunas órbitas/puntos (ver ``ZONAS_2M``).
* ``8``  — WPM L4-DN multiespectral (BAND1-3), 8 m. TIFF en tiras: se lee una
  ventana y por eso el recorte se mantiene chico.
* ``16`` — MUX L4-DN (BAND5-7), 16 m. Misma mecánica.

Este módulo es stdlib puro: lo importa la API para armar la receta. La lectura
de los COG vive en ``descargar/cbers.py``.
"""
from __future__ import annotations

import json
import math
import urllib.request
from datetime import date, datetime

STAC = "https://data.inpe.br/bdc/stac/v1/search"

COLECCIONES = {
    "2": "CB4A-WPM-PCA-FUSED-1",
    "8": "CB4A-WPM-L4-DN-1",
    "16": "CB4A-MUX-L4-DN-1",
}

#: Metros por píxel nativo de cada camino.
MPP = {"2": 2.0, "8": 8.0, "16": 16.0}

#: Bandas a leer, en orden R, G, B. En 2 m el asset ya es un RGB uint8.
BANDAS = {
    "2": ("tci",),
    "8": ("BAND3", "BAND2", "BAND1"),   # rojo, verde, azul del WPM
    "16": ("BAND7", "BAND6", "BAND5"),  # rojo, verde, azul del MUX
}

#: Zonas con recorte cuadrado. `lon`/`lat` son el centro.
ZONAS = {
    "asuncion": ("Asunción", -57.6359, -25.2637),
    "encarnacion": ("Encarnación", -55.8667, -27.3333),
    "cdeleste": ("Ciudad del Este", -54.6111, -25.5097),
    "pjc": ("Pedro Juan Caballero", -55.7333, -22.5500),
    "concepcion": ("Concepción", -57.4333, -23.4167),
    "filadelfia": ("Filadelfia (Chaco)", -60.0333, -22.3500),
    "salto": ("Salto del Guairá", -54.3167, -24.0667),
    "pilar": ("Pilar", -58.2833, -26.8667),
    "mcal": ("Mariscal Estigarribia", -60.6167, -22.0333),
    "caacupe": ("Caacupé", -57.1333, -25.3833),
}

#: Zonas donde el PCA fusionado 2 m tiene escenas con dato (verificado leyendo
#: el swath real: la caja del STAC es el sobre, no el polígono válido).
ZONAS_2M = ("cdeleste", "salto", "encarnacion")

#: Tope de píxeles del recorte: un póster no necesita más.
MAX_PX = 4000


def zona_valida(valor: str) -> str:
    return valor if valor in ZONAS else "asuncion"


def etiqueta_zona(valor: str) -> str:
    return ZONAS[zona_valida(valor)][0]


def bbox_zona(zona: str, km: float) -> tuple[float, float, float, float]:
    """Caja lon/lat de `km` de lado centrada en la zona."""
    _, lon, lat = ZONAS[zona_valida(zona)]
    lado = max(2.0, float(km)) * 1000.0 / 2.0
    dlat = lado / 111_320.0
    dlon = lado / (111_320.0 * max(0.2, math.cos(math.radians(lat))))
    return (lon - dlon, lat - dlat, lon + dlon, lat + dlat)


def recorte(zona: str, km: float, detalle: str) -> dict:
    """Caja efectiva y metros/píxel reales después del tope de 4000 px."""
    detalle = detalle if detalle in MPP else "8"
    km = max(2.0, min(120.0, float(km)))
    km_eff = min(km, MAX_PX * MPP[detalle] / 1000.0)
    px = max(200, min(MAX_PX, int(round(km_eff * 1000.0 / MPP[detalle]))))
    mpp = km_eff * 1000.0 / px
    return {
        "zona": zona_valida(zona),
        "detalle": detalle,
        "km": km_eff,
        "km_pedido": km,
        "px": px,
        "mpp": mpp,
        "bbox": bbox_zona(zona, km_eff),
        "coleccion": COLECCIONES[detalle],
    }


def _iso(valor: str | date | datetime) -> str:
    if isinstance(valor, datetime):
        return valor.strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(valor, date):
        return valor.isoformat()
    return str(valor)


def buscar(bbox, desde, hasta, detalle: str = "8", limite: int = 40,
           timeout: int = 60) -> list[dict]:
    """Escenas del STAC que intersectan la caja y la ventana pedida."""
    detalle = detalle if detalle in COLECCIONES else "8"
    cuerpo = {
        "collections": [COLECCIONES[detalle]],
        "bbox": list(bbox),
        "limit": int(limite),
        "datetime": f"{_iso(desde)}T00:00:00Z/{_iso(hasta)}T23:59:59Z",
    }
    pedido = urllib.request.Request(
        STAC,
        data=json.dumps(cuerpo).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "climate3d/1.0"},
    )
    with urllib.request.urlopen(pedido, timeout=timeout) as respuesta:
        return json.load(respuesta).get("features", [])


def cobertura(item: dict, bbox) -> float:
    """Fracción de la caja que cubre el item (0..1)."""
    b = item.get("bbox") or []
    if len(b) < 4:
        return 0.0
    ancho = max(1e-9, bbox[2] - bbox[0])
    alto = max(1e-9, bbox[3] - bbox[1])
    cruce_x = max(0.0, min(bbox[2], b[2]) - max(bbox[0], b[0]))
    cruce_y = max(0.0, min(bbox[3], b[3]) - max(bbox[1], b[1]))
    return (cruce_x * cruce_y) / (ancho * alto)


def elegir(items: list[dict], bbox) -> dict | None:
    """La escena con mejor cobertura; a igual cobertura, la más nueva."""
    if not items:
        return None

    def clave(item):
        fecha = str(item.get("properties", {}).get("datetime") or "")
        return (round(cobertura(item, bbox), 3), fecha)

    mejores = [item for item in items if cobertura(item, bbox) > 0.05]
    return max(mejores or items, key=clave)
