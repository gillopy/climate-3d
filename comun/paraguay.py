"""Cobertura y nombres de la captura (snapshot) de Paraguay.

Lo comparten el descargador y el compositor: la caja sale del GeoJSON y el nombre del
crudo se calcula igual en los dos lados, así no hay que adivinar rutas.

La cobertura es una caja geográfica (EPSG:4326) porque la API de snapshots de GIBS
recibe `BBOX` en lon/lat: se toma el rectángulo que encierra al país y se agranda con
un margen para que el contorno no toque el borde de la imagen.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

MARGEN = 0.06                          # 6 % del lado, por defecto


def puntos(objeto):
    """Itera todos los pares (lon, lat) de un GeoJSON, sin importar la profundidad."""
    if isinstance(objeto, (list, tuple)) and objeto and isinstance(objeto[0], (int, float)):
        yield float(objeto[0]), float(objeto[1])
    elif isinstance(objeto, (list, tuple)):
        for hijo in objeto:
            yield from puntos(hijo)


def caja_geojson(ruta: Path, margen: float = MARGEN) -> tuple[float, float, float, float]:
    """`(oeste, sur, este, norte)` del país, con `margen` como fracción del lado."""
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    encontrados = []
    for feature in datos.get("features", []):
        encontrados.extend(puntos(feature.get("geometry", {}).get("coordinates", [])))
    if not encontrados:
        raise SystemExit(f"{ruta}: no encontré coordenadas.")
    oeste = min(p[0] for p in encontrados)
    este = max(p[0] for p in encontrados)
    sur = min(p[1] for p in encontrados)
    norte = max(p[1] for p in encontrados)
    dx = (este - oeste) * margen
    dy = (norte - sur) * margen
    return (oeste - dx, sur - dy, este + dx, norte + dy)


def nombre_crudo(t: datetime, px: int) -> str:
    """Nombre fijo del crudo: descarga y composición lo calculan igual."""
    return f"crudo_snapshot_{t:%Y%m%dT%H%M}_{px}px.png"


def nombre_captura(t: datetime, px: int) -> str:
    """Nombre de la captura final."""
    return f"snapshot_paraguay_{t:%Y-%m-%dT%H%M}_{px}px.png"
