"""Cobertura y nombres de la captura (snapshot) de Paraguay.

Lo comparten el descargador y el compositor: la caja sale del GeoJSON y el nombre del
crudo se calcula igual en los dos lados, así no hay que adivinar rutas.

La cobertura es una caja geográfica (EPSG:4326) porque la API de snapshots de GIBS
recibe `BBOX` en lon/lat: se toma el rectángulo que encierra al país y se agranda con
un margen para que el contorno no toque el borde de la imagen.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

MARGEN = 0.06                          # 6 % del lado, por defecto

#: GeoJSON con el contorno del país (cobertura y borde de los encuadres).
GEOJSON = Path(__file__).resolve().parents[1] / "datos" / "paraguay_gadm.json"

API = "https://wvs.earthdata.nasa.gov/api/v1/snapshot"

# Capas disponibles: (id de GIBS, es un compuesto diario).
#   truecolor  VIIRS NOAA-20 a 250 m, sólo de día: es la que trae detalle real.
#   geocolor   GOES-19 ABI a ~2 km, día/noche; pedir más píxeles sólo la agranda.
CAPAS = {
    # True Color corregido: compuesto diario a 250 m, sólo de día.
    "truecolor": ("VIIRS_NOAA20_CorrectedReflectance_TrueColor", True),
    "snpp": ("VIIRS_SNPP_CorrectedReflectance_TrueColor", True),
    "aqua": ("MODIS_Aqua_CorrectedReflectance_TrueColor", True),
    "terra": ("MODIS_Terra_CorrectedReflectance_TrueColor", True),
    # GeoColor: día/noche, pero a ~2 km.
    "geocolor": ("GOES-East_ABI_GeoColor", False),
}
CAPA = "truecolor"

# Cada cuánto publica: los compuestos diarios (VIIRS, MODIS) arman uno por día;
# las capas del geoestacionario (GeoColor), cada 10 minutos.
PASO_DIARIO = timedelta(days=1)
PASO_SLOT = timedelta(minutes=10)
# Cuánto se puede retroceder buscando el último gránulo publicado: una semana de
# días o 6 horas de slots. Sale del tipo de capa y no de una tabla aparte: si se
# agrega una capa a CAPAS, ya hereda la cadencia correcta.
INTENTOS_DIARIA = 8
INTENTOS_SLOT = 36


def es_diaria(capa: str) -> bool:
    """True si la capa es un compuesto diario (TIME=AAAA-MM-DD)."""
    return CAPAS[capa][1]


def paso(capa: str) -> timedelta:
    """Intervalo entre gránulos de la capa."""
    return PASO_DIARIO if es_diaria(capa) else PASO_SLOT


def intentos(capa: str) -> int:
    """Cuántos gránulos hacia atrás se sondean buscando el último."""
    return INTENTOS_DIARIA if es_diaria(capa) else INTENTOS_SLOT


def techo(capa: str, ahora: datetime) -> datetime:
    """Último instante posible: ahora (UTC, sin segundos) alineado al intervalo."""
    base = ahora.replace(second=0, microsecond=0)
    intervalo = paso(capa)
    if intervalo < timedelta(days=1):
        minutos = int(intervalo.total_seconds() // 60)
        return base.replace(minute=base.minute - base.minute % minutos)
    return base.replace(hour=0, minute=0)


_RE_CRUDO = re.compile(r"crudo_snapshot_[a-z]+_(\d{8}T\d{4})_\d+px\.png$")


def ts_de_crudo(nombre: str) -> datetime | None:
    """Instante que codifica el nombre del crudo (`..._20261101T1750_3200px.png`)."""
    match = _RE_CRUDO.search(nombre)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y%m%dT%H%M")
    except ValueError:
        return None


def url_snapshot(t: datetime, caja, px: int, capa: str = CAPA) -> str:
    """URL del snapshot para el instante `t`.

    Las capas diarias (VIIRS) esperan `TIME=AAAA-MM-DD`; las del satélite
    geoestacionario, el instante completo en ISO 8601.
    """
    o, s, e, n = caja
    capa_gibs, diaria = CAPAS[capa]
    momento = t.strftime("%Y-%m-%d") if diaria else t.strftime("%Y-%m-%dT%H:%M:%SZ")
    return (f"{API}?REQUEST=GetSnapshot&TIME={momento}"
            f"&BBOX={s},{o},{n},{e}&CRS=EPSG:4326"
            f"&LAYERS={capa_gibs}&FORMAT=image/png&WIDTH={px}&HEIGHT={px}")


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


def encuadre(margen: float = MARGEN,
             geojson: Path | None = None) -> dict[str, float]:
    """Centro y radio (grados) del encuadre Paraguay, con `margen` del lado.

    `radio` es la mitad del lado mayor de la caja expandida: el encuadre cuadrado
    que entra tal cual en los renderizadores con `--radio` (grados) o, dividido
    por 90, en los que usan `--recorte` (fracción del hemisferio).
    """
    o, s, e, n = caja_geojson(geojson or GEOJSON, margen)
    return {
        "oeste": o,
        "sur": s,
        "este": e,
        "norte": n,
        "lon": (o + e) / 2.0,
        "lat": (s + n) / 2.0,
        "radio": max((e - o) / 2.0, (n - s) / 2.0),
    }


# Detalle real de cada capa, en metros por píxel (medido sobre este encuadre).
# Por debajo de esto GIBS interpola: el archivo crece y la imagen no gana nada.
MPP_NATIVO = {
    "truecolor": 250,
    "snpp": 250,
    "aqua": 250,
    "terra": 250,
    "geocolor": 700,
}

# Tope de lado: 8000 px alcanza para 125 m/px sobre Paraguay sin comerse la RAM.
LADO_MAX = 8000
METROS_POR_GRADO = 111_320.0


def px_para_mpp(caja, mpp: float, tope: int = LADO_MAX) -> int:
    """Lado en píxeles para un detalle de `mpp` metros por píxel.

    Se toma el lado mayor de la caja: así el encuadre entra completo en una imagen
    cuadrada (el bbox de Paraguay es casi cuadrado). Es equirectangular, igual que
    el pedido a GIBS (`CRS=EPSG:4326`).
    """
    if mpp <= 0:
        raise SystemExit(f"--mpp debe ser positivo (recibí {mpp}).")
    o, s, e, n = caja
    lado_deg = max(e - o, n - s)
    return int(min(tope, max(256, round(lado_deg * METROS_POR_GRADO / mpp))))


def aviso_de_detalle(capa: str, mpp: float) -> str | None:
    """Aviso cuando se pide más detalle del que la capa tiene."""
    nativo = MPP_NATIVO.get(capa)
    if nativo is None or mpp >= nativo:
        return None
    return (f"{capa} tiene ~{nativo} m/px: pedir {mpp:g} m/px sólo interpola "
            f"(el archivo pesa más y no agrega detalle)")


def nombre_crudo(capa: str, t: datetime, px: int) -> str:
    """Nombre fijo del crudo: descarga y composición lo calculan igual.

    Lleva la capa y el instante: dos capas del mismo día no se pisan.
    """
    return f"crudo_snapshot_{capa}_{t:%Y%m%dT%H%M}_{px}px.png"


def nombre_captura(capa: str, t: datetime, px: int) -> str:
    """Nombre de la captura final."""
    return f"snapshot_paraguay_{capa}_{t:%Y-%m-%dT%H%M}_{px}px.png"
