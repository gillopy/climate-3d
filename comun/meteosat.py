"""Meteosat-12 (MTG-I1) por EUMETView: slots y URL del WMS.

EUMETSAT publica el disco completo del FCI ya **pintado** (GeoColour, True
Colour) en EUMETView, un GeoServer abierto y sin clave. No hace falta bajar el
NetCDF ni reproyectar la proyeccion geoestacionaria: se pide un PNG en
``CRS:84`` (lon/lat) y el render lo lleva a globo.

Este modulo es stdlib puro (lo importa la API, que no tiene Pillow ni cartopy en
su camino de planificacion). La validacion de pixeles vive en el descargador.

Fuente y licencia: EUMETSAT Meteosat (Core, CC-BY 4.0). Atribucion obligatoria.
"""
from __future__ import annotations

import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

WMS = "https://view.eumetsat.int/geoserver/wms"
CAPACIDADES = f"{WMS}?service=WMS&version=1.3.0&request=GetCapabilities"

#: Capas pintadas que ofrece EUMETView para el disco completo de MTG-I1.
CAPAS = {
    "geocolour": "mtg_fd:rgb_geocolour",     # color real de dia + IR y luces de noche
    "truecolour": "mtg_fd:rgb_truecolour",   # color real, solo lado diurno
    "ir": "mtg_fd:ir105_hrfi",               # IR 10.5 um, dia y noche
}

#: Caja del disco en lon/lat (la que declara el WMS: -81.28..81.28, -77.36..77.36).
BBOX = (-81.28, -77.36, 81.28, 77.36)

#: Caja de "Solo Paraguay": 1000 km de lado centrada en el país. Se elige
#: cuadrada en kilómetros, no en grados, para que el póster no salga deformado:
#: a 23.4° de latitud un grado de longitud mide 102 km y uno de latitud 111 km.
BBOX_PARAGUAY = (-63.34, -27.97, -53.55, -18.92)

#: Encuadres del producto: el disco entero o el recorte del país.
#: Desde 0° el país queda a 58° del subpunto satelital, en el limbo.
ENCUADRES = {"globo": BBOX, "paraguay": BBOX_PARAGUAY}

PASO = 10                       # minutos entre cuadros del FCI
INTENTOS = 24                   # 4 h hacia atras si el WMS no dice la ultima
TIMEOUT = 45

_ISO = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})")


def caja(encuadre: str = "globo") -> tuple[float, float, float, float]:
    """Caja lon/lat del encuadre pedido; un nombre desconocido cae al disco."""
    return ENCUADRES.get(encuadre, BBOX)


def normaliza_encuadre(encuadre: str | None = None, globo: bool = False,
                       defecto: str = "globo") -> str:
    """Encuadre pedido por CLI, aceptando el flag viejo ``--globo``.

    ``defecto`` es lo que vale sin flags: ``globo`` en el descargador (siempre
    bajó el disco) y ``plano`` en el render (dibuja el crudo tal cual).
    """
    if encuadre in ENCUADRES:
        return encuadre
    if encuadre:
        return defecto
    return "globo" if globo else defecto



def piso_slot(t: datetime, paso: int = PASO) -> datetime:
    """Baja `t` al multiplo de `paso` minutos ya cumplido (UTC naive)."""
    return t.replace(second=0, microsecond=0,
                     minute=t.minute - t.minute % paso)


def url_cuadro(t: datetime, capa: str = "geocolour", ancho: int = 1600,
               alto: int | None = None, bbox=BBOX) -> str:
    """URL del `GetMap` para el instante `t` (UTC naive)."""
    o, s, e, n = bbox
    ancho = max(200, min(4000, int(ancho)))
    if alto is None:
        alto = round(ancho * (n - s) / (e - o))
    alto = max(200, min(4000, int(alto)))
    parametros = {
        "service": "WMS",
        "version": "1.3.0",
        "request": "GetMap",
        "layers": CAPAS.get(capa, CAPAS["geocolour"]),
        "styles": "",
        "crs": "CRS:84",
        "bbox": f"{o:g},{s:g},{e:g},{n:g}",
        "width": str(ancho),
        "height": str(alto),
        "format": "image/png",
        # Con alfa, el borde del disco llega limpio: el render lo usa como
        # mascara y no aparecen las esquinas negras de la caja lon/lat.
        "transparent": "true",
        "time": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return f"{WMS}?{urllib.parse.urlencode(parametros)}"


def _leer(url: str, timeout: int = TIMEOUT) -> bytes:
    pedido = urllib.request.Request(url, headers={"User-Agent": "climate3d/1.0"})
    with urllib.request.urlopen(pedido, timeout=timeout) as respuesta:
        return respuesta.read()


def _bloque_capa(xml: str, capa: str) -> str:
    """Trozo del XML que describe la capa pedida (hasta cerrar su `<Layer>`)."""
    inicio = xml.find(f"<Name>{capa}</Name>")
    if inicio < 0:
        return ""
    fin = xml.find("</Layer>", inicio)
    return xml[inicio:fin if fin >= 0 else inicio + 6000]


def ultimo_publicado(capa: str = "geocolour", timeout: int = TIMEOUT) -> datetime | None:
    """Ultima marca que declara el `Dimension time` de la capa, o None.

    Es una sola consulta (el capabilities pesa unos cientos de KB) y evita
    caminar hacia atras pidiendo miniaturas. Si el XML cambia de forma, el
    llamador cae al sondeo por miniaturas.
    """
    nombre = CAPAS.get(capa, CAPAS["geocolour"])
    try:
        xml = _leer(CAPACIDADES, timeout=timeout).decode("utf-8", "replace")
    except Exception:
        return None
    bloque = _bloque_capa(xml, nombre)
    if not bloque:
        return None
    match = re.search(r'<Dimension name="time"[^>]*default="([^"]+)"', bloque)
    if not match:
        return None
    marca = _ISO.search(match.group(1))
    if not marca:
        return None
    try:
        return datetime.strptime(marca.group(1), "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None


def ultimos_slots(n: int, capa: str = "geocolour",
                  ahora: datetime | None = None,
                  paso: int = PASO) -> list[datetime]:
    """Los `n` slots mas nuevos publicados, del mas viejo al mas nuevo.

    Primero usa el `default` del capabilities (exacto). Si no esta, camina hacia
    atras desde ahora menos 20 min, sin validar contra la red: el descargador
    reintenta y retrocede si el slot no tiene dato.
    """
    if n <= 0:
        return []
    ultimo = ultimo_publicado(capa)
    if ultimo is None:
        base = (ahora or datetime.now(timezone.utc).replace(tzinfo=None)) - timedelta(minutes=20)
        ultimo = piso_slot(base, paso)
    return [ultimo - timedelta(minutes=paso * (n - 1 - i)) for i in range(n)]
