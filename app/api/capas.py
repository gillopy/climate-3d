"""Capas ambientales del visor NISAR: areas protegidas, Ramsar, biosfera,
territorios indigenas, ecorregiones y otras areas de conservacion.

Las fuentes son servicios ArcGIS REST publicos (WDPA/UNEP-WCMC, LandMark/WRI y
RESOLVE Ecoregions). Este modulo hace de proxy: consulta solo la caja visible del
mapa, normaliza los atributos a un GeoJSON chico y cachea la respuesta para no
golpear los servidores publicos en cada paneo.

Ninguna capa se inventa ni se completa con datos locales: si una fuente no
responde, la capa devuelve el error (o un aviso parcial) y la UI lo muestra.
"""
from __future__ import annotations

import json
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from threading import Lock
from typing import Any

from fastapi import APIRouter, HTTPException, Query

USER_AGENT = "climate3d-capas/0.1 (+local)"
CACHE_TTL = 6 * 3600.0
CACHE_MAX = 64
MAX_FEATURES = 2600
MAX_BYTES = 24 * 1024 * 1024
PAGINA_LANDMARK = 1000

WDPA_URL = (
    "https://data-gis.unep-wcmc.org/server/rest/services/ProtectedSites/"
    "The_World_Database_of_Protected_Areas/FeatureServer/1/query"
)
LANDMARK = "https://gis.wri.org/server/rest/services/LandMark"
RESOLVE_URL = (
    "https://services.arcgis.com/P3ePLMYs2RVChkJx/ArcGIS/rest/services/"
    "Resolve_Ecoregions/FeatureServer/0/query"
)

#: WDPA mezcla designaciones en el idioma local y en ingles. Las exclusiones se
#: hacen sobre ambos campos para que la misma categoria no aparezca dos veces.
_WDPA_AREAS = (
    "desig_type='National' AND NOT ("
    "desig_eng LIKE '%Biosphere%' OR desig LIKE '%Biosfera%' OR desig LIKE '%Biosph%' "
    "OR desig_eng LIKE '%Ramsar%' OR desig LIKE '%Ramsar%' "
    "OR desig_eng LIKE '%Private%' OR desig LIKE '%Privada%' OR desig LIKE '%Privé%' "
    "OR desig_eng LIKE '%Other Categor%' OR desig LIKE '%Otras Categor%' "
    "OR desig_eng LIKE '%Binational%' OR desig LIKE '%Binacional%')"
)
_WDPA_RAMSAR = "desig_eng LIKE '%Ramsar%' OR desig LIKE '%Ramsar%'"
_WDPA_BIOSFERA = (
    "desig_eng LIKE '%Biosphere%' OR desig LIKE '%Biosfera%' OR desig LIKE '%Biosph%'"
)
_WDPA_OTRAS = (
    "desig_eng LIKE '%Private%' OR desig LIKE '%Privada%' OR desig LIKE '%Privé%' "
    "OR desig_eng LIKE '%Other Categor%' OR desig LIKE '%Otras Categor%' "
    "OR desig_eng LIKE '%Binational%' OR desig LIKE '%Binacional%'"
)

_WDPA_CAMPOS = (
    "name_eng,name,desig_eng,desig,desig_type,iucn_cat,status_yr,gis_area,iso3,site_id"
)
_LANDMARK_CAMPOS = (
    "Name,Category,Doc_Status,Stat_Note,Country,ISO_Code,Area_GIS,Data_Ctrb"
)
_ECORREGIONES_CAMPOS = "ECO_NAME,BIOME_NAME,COLOR"


@dataclass(frozen=True)
class Consulta:
    """Un pedido ArcGIS concreto. Varias consultas forman una capa."""

    url: str
    where: str
    campos: str
    #: Etiqueta para distinguir el origen cuando una capa une varios servicios.
    origen: str | None = None
    #: La mayoria de los servicios devuelven su propio maxRecordCount y avisan.
    pagina: int = 2000
    paginar: bool = False


@dataclass(frozen=True)
class Capa:
    id: str
    nombre: str
    descripcion: str
    fuente: str
    fuente_url: str
    atribucion: str
    color: str
    min_zoom: int
    consultas: tuple[Consulta, ...]
    dedupe: str | None = None
    max_features: int = MAX_FEATURES


CAPAS: tuple[Capa, ...] = (
    Capa(
        id="areas-protegidas",
        nombre="Áreas silvestres protegidas",
        descripcion=(
            "SINASIP: parques nacionales, reservas, monumentos y paisajes protegidos."
        ),
        fuente="WDPA · UNEP-WCMC e IUCN (Protected Planet)",
        fuente_url="https://www.protectedplanet.net/",
        atribucion="© UNEP-WCMC and IUCN · Protected Planet: The World Database of Protected Areas (WDPA)",
        color="#4ade80",
        min_zoom=5,
        consultas=(
            Consulta(WDPA_URL, _WDPA_AREAS, _WDPA_CAMPOS, pagina=2000),
        ),
    ),
    Capa(
        id="ramsar",
        nombre="Sitios Ramsar",
        descripcion="Humedales de importancia internacional.",
        fuente="WDPA · UNEP-WCMC e IUCN",
        fuente_url="https://rsis.ramsar.org/",
        atribucion="© UNEP-WCMC and IUCN · Ramsar Sites Information Service / WDPA",
        color="#22d3ee",
        min_zoom=4,
        consultas=(
            Consulta(WDPA_URL, _WDPA_RAMSAR, _WDPA_CAMPOS, pagina=2000),
        ),
    ),
    Capa(
        id="biosfera",
        nombre="Reservas de biosfera",
        descripcion=(
            "Programa MAB de la UNESCO y reservas nacionales de biosfera."
        ),
        fuente="WDPA · UNEP-WCMC e IUCN",
        fuente_url="https://www.unesco.org/es/mab",
        atribucion="© UNEP-WCMC and IUCN · UNESCO Man and the Biosphere (MAB) / WDPA",
        color="#facc15",
        min_zoom=3,
        consultas=(
            Consulta(WDPA_URL, _WDPA_BIOSFERA, _WDPA_CAMPOS, pagina=2000),
        ),
        dedupe="biosfera",
    ),
    Capa(
        id="territorios-indigenas",
        nombre="Territorios indígenas",
        descripcion="Tierras indígenas tituladas y en trámite.",
        fuente="LandMark (WRI) · datos de FAPI y DGEEC",
        fuente_url="https://landmarkmap.org/map",
        atribucion=(
            "© LandMark (World Resources Institute) · tierras indígenas y comunitarias; "
            "en Paraguay, FAPI y DGEEC"
        ),
        color="#f472b6",
        min_zoom=5,
        consultas=(
            Consulta(
                f"{LANDMARK}/comm_ind_Documented/MapServer/1/query",
                "1=1",
                _LANDMARK_CAMPOS,
                origen="Documentado",
                pagina=PAGINA_LANDMARK,
                paginar=True,
            ),
            Consulta(
                f"{LANDMARK}/comm_ind_NotDocumented/MapServer/1/query",
                "1=1",
                _LANDMARK_CAMPOS,
                origen="No documentado",
                pagina=PAGINA_LANDMARK,
                paginar=True,
            ),
            Consulta(
                f"{LANDMARK}/comm_ind_FormalLandClaim/MapServer/1/query",
                "1=1",
                _LANDMARK_CAMPOS,
                origen="Reclamo formal",
                pagina=PAGINA_LANDMARK,
                paginar=True,
            ),
            Consulta(
                f"{LANDMARK}/comm_ind_CustomaryTenure/MapServer/1/query",
                "1=1",
                _LANDMARK_CAMPOS,
                origen="Tenencia consuetudinaria",
                pagina=PAGINA_LANDMARK,
                paginar=True,
            ),
        ),
        max_features=1500,
    ),
    Capa(
        id="ecorregiones",
        nombre="Ecorregiones",
        descripcion=(
            "Chaco seco y húmedo, Pantanal, Cerrado, Bosque Atlántico y otras."
        ),
        fuente="RESOLVE Ecoregions 2017 (Esri Living Atlas)",
        fuente_url="https://ecoregions.appspot.com/",
        atribucion="© RESOLVE Ecoregions 2017 · Esri Living Atlas",
        color="#94a3b8",
        min_zoom=4,
        consultas=(
            Consulta(RESOLVE_URL, "1=1", _ECORREGIONES_CAMPOS, pagina=2000),
        ),
    ),
    Capa(
        id="otras-conservacion",
        nombre="Otras áreas de conservación",
        descripcion=(
            "Reservas privadas, de las entidades binacionales y otras categorías."
        ),
        fuente="WDPA · UNEP-WCMC e IUCN",
        fuente_url="https://www.protectedplanet.net/",
        atribucion="© UNEP-WCMC and IUCN · Protected Planet: The World Database of Protected Areas (WDPA)",
        color="#fb923c",
        min_zoom=5,
        consultas=(
            Consulta(WDPA_URL, _WDPA_OTRAS, _WDPA_CAMPOS, pagina=2000),
        ),
    ),
)

POR_ID = {capa.id: capa for capa in CAPAS}


class ErrorFuente(Exception):
    """La fuente remota no respondio o devolvio algo ilegible."""


# --- cache ---------------------------------------------------------------
_CACHE: dict[tuple[str, tuple[float, float, float, float], int], tuple[float, dict[str, Any]]] = {}
_CACHE_LOCK = Lock()


def _cache_leer(clave: tuple[str, tuple[float, float, float, float], int]) -> dict[str, Any] | None:
    with _CACHE_LOCK:
        guardado = _CACHE.get(clave)
        if guardado is None:
            return None
        creado, valor = guardado
        if time.monotonic() - creado > CACHE_TTL:
            _CACHE.pop(clave, None)
            return None
        return valor


def _cache_guardar(
    clave: tuple[str, tuple[float, float, float, float], int], valor: dict[str, Any]
) -> None:
    with _CACHE_LOCK:
        if len(_CACHE) >= CACHE_MAX:
            viejas = sorted(_CACHE.items(), key=lambda item: item[1][0])
            for vieja, _ in viejas[: max(1, CACHE_MAX // 4)]:
                _CACHE.pop(vieja, None)
        _CACHE[clave] = (time.monotonic(), valor)


def limpiar_cache() -> None:
    """Para tests: deja la cache como recien arrancada."""
    with _CACHE_LOCK:
        _CACHE.clear()


# --- validacion ----------------------------------------------------------
def _caja(bruto: str) -> tuple[float, float, float, float]:
    try:
        partes = [float(valor) for valor in bruto.split(",")]
    except (AttributeError, ValueError) as exc:
        raise HTTPException(
            status_code=400, detail="bbox debe ser oeste,sur,este,norte"
        ) from exc
    if len(partes) != 4:
        raise HTTPException(status_code=400, detail="bbox debe tener 4 numeros")
    oeste, sur, este, norte = partes
    if not (-180.0 <= oeste < este <= 180.0):
        raise HTTPException(status_code=400, detail="longitudes invalidas o invertidas")
    if not (-90.0 <= sur < norte <= 90.0):
        raise HTTPException(status_code=400, detail="latitudes invalidas o invertidas")
    return (
        round(oeste, 4),
        round(sur, 4),
        round(este, 4),
        round(norte, 4),
    )


def _offset(zoom: int, capa: Capa) -> float:
    """Simplificacion en grados: mas fina cuanto mas cerca se mira."""
    if capa.id == "ecorregiones":
        tabla = {4: 0.2, 5: 0.08, 6: 0.04, 7: 0.02}
        return tabla.get(zoom, 0.01 if zoom >= 8 else 0.2)
    if zoom <= 4:
        return 0.05
    if zoom == 5:
        return 0.02
    if zoom == 6:
        return 0.01
    if zoom <= 8:
        return 0.005
    if zoom <= 10:
        return 0.002
    return 0.001 if zoom <= 12 else 0.0005


def _precision(capa: Capa, zoom: int) -> int:
    if capa.id == "ecorregiones" and zoom <= 6:
        return 3
    return 4


# --- HTTP ----------------------------------------------------------------
def _pedir(url: str, params: dict[str, str], timeout: float = 45.0) -> dict[str, Any]:
    completo = f"{url}?{urllib.parse.urlencode(params)}"
    pedido = urllib.request.Request(
        completo,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/geo+json, application/json",
        },
    )
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as respuesta:
            crudo = respuesta.read(MAX_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ErrorFuente(f"{type(exc).__name__}: {exc}") from exc
    if len(crudo) > MAX_BYTES:
        raise ErrorFuente(
            f"la respuesta superó el máximo de {MAX_BYTES // (1024 * 1024)} MB"
        )
    try:
        datos = json.loads(crudo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ErrorFuente("la respuesta no es JSON") from exc
    if isinstance(datos, dict) and datos.get("error"):
        detalle = datos["error"]
        mensaje = detalle.get("message") if isinstance(detalle, dict) else detalle
        raise ErrorFuente(f"ArcGIS: {mensaje}")
    return datos


def _pedir_consulta(
    consulta: Consulta,
    caja: tuple[float, float, float, float],
    zoom: int,
    capa: Capa,
    limite: int = MAX_FEATURES,
) -> tuple[list[dict[str, Any]], bool]:
    """Devuelve las features crudas y si el servicio aviso que recorto."""
    oeste, sur, este, norte = caja
    # La tolerancia no puede depender solo del zoom que manda el cliente: una
    # caja mundial con zoom 22 pediria detalle de 50 m sobre 360 grados. Se
    # acota tambien por el tamaño de la caja (~2000 muestras por lado).
    extension = max(este - oeste, norte - sur)
    tolerancia = max(_offset(zoom, capa), extension / 2000.0)
    geometria = json.dumps(
        {
            "xmin": oeste,
            "ymin": sur,
            "xmax": este,
            "ymax": norte,
            "spatialReference": {"wkid": 4326},
        },
        separators=(",", ":"),
    )
    base: dict[str, str] = {
        "where": consulta.where,
        "geometry": geometria,
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": consulta.campos,
        "returnGeometry": "true",
        "outSR": "4326",
        "maxAllowableOffset": f"{tolerancia:g}",
        "geometryPrecision": str(_precision(capa, zoom)),
        "returnZ": "false",
        "returnM": "false",
        "f": "geojson",
    }

    features: list[dict[str, Any]] = []
    excedido = False
    offset = 0
    while True:
        params = dict(base)
        params["resultOffset"] = str(offset)
        params["resultRecordCount"] = str(consulta.pagina)
        datos = _pedir(consulta.url, params)
        lote = datos.get("features") or []
        if not isinstance(lote, list):
            raise ErrorFuente("GeoJSON sin lista de features")
        features.extend(lote)
        if datos.get("exceededTransferLimit"):
            excedido = True
        if (
            not consulta.paginar
            or len(lote) < consulta.pagina
            or len(features) >= limite
        ):
            break
        offset += len(lote)
    return features, excedido


# --- normalizacion ------------------------------------------------------
def _texto(valor: Any) -> str:
    if valor is None:
        return ""
    return str(valor).strip()


def _numero(valor: Any) -> float | None:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _entero(valor: Any) -> int | None:
    numero = _numero(valor)
    return int(numero) if numero is not None else None


def _sin_acentos(valor: str) -> str:
    normal = unicodedata.normalize("NFKD", valor)
    return "".join(c for c in normal if not unicodedata.combining(c)).lower().strip()


def _props_wdpa(props: dict[str, Any]) -> dict[str, Any]:
    nombre = _texto(props.get("name_eng")) or _texto(props.get("name"))
    area_km2 = _numero(props.get("gis_area"))
    return {
        "nombre": nombre or "Sin nombre",
        "categoria": _texto(props.get("desig_eng")) or _texto(props.get("desig")),
        "designacion": _texto(props.get("desig")),
        "tipo": _texto(props.get("desig_type")),
        "iucn": _texto(props.get("iucn_cat")),
        "anio": _entero(props.get("status_yr")),
        # WDPA publica GIS_AREA en km2; la UI trabaja en hectareas.
        "area_ha": round(area_km2 * 100) if area_km2 is not None else None,
        "pais": _texto(props.get("iso3")),
        "sitio": _entero(props.get("site_id")),
    }


def _props_landmark(props: dict[str, Any], origen: str | None) -> dict[str, Any]:
    area_ha = _numero(props.get("Area_GIS"))
    return {
        "nombre": _texto(props.get("Name")) or "Sin nombre",
        "categoria": _texto(props.get("Category")),
        "situacion": _texto(props.get("Doc_Status")),
        "nota": _texto(props.get("Stat_Note")),
        "pais": _texto(props.get("Country")),
        "iso": _texto(props.get("ISO_Code")),
        # LandMark publica Area_GIS en hectareas.
        "area_ha": round(area_ha) if area_ha is not None else None,
        "origen": origen or "",
    }


def _props_eco(props: dict[str, Any]) -> dict[str, Any]:
    color = _texto(props.get("COLOR")).lower()
    if not (len(color) == 7 and color.startswith("#")):
        color = "#94a3b8"
    return {
        "nombre": _texto(props.get("ECO_NAME")) or "Sin nombre",
        "categoria": _texto(props.get("BIOME_NAME")),
        "color": color,
    }


def _normalizar(
    capa: Capa, consulta: Consulta, cruda: dict[str, Any]
) -> dict[str, Any] | None:
    props = cruda.get("properties")
    if not isinstance(props, dict):
        return None
    if capa.id == "ecorregiones":
        normalizadas = _props_eco(props)
    elif capa.id == "territorios-indigenas":
        normalizadas = _props_landmark(props, consulta.origen)
    else:
        normalizadas = _props_wdpa(props)
    return {
        "type": "Feature",
        "geometry": cruda.get("geometry"),
        "properties": normalizadas,
    }


def _dedupe_biosfera(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """WDPA trae el mismo sitio como reserva nacional y como reserva MAB.

    Sólo se colapsa el par nacional/internacional del mismo sitio (nombre y
    área): dos sitios distintos que casualmente compartan nombre y área se
    conservan. Si hay registro UNESCO, se prefiere ése.
    """
    grupos: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for feature in features:
        props = feature["properties"]
        area = int(round((props.get("area_ha") or 0) / 100.0)) * 100
        clave = (_sin_acentos(props.get("nombre") or ""), area)
        grupos.setdefault(clave, []).append(feature)

    unicas: list[dict[str, Any]] = []
    for grupo in grupos.values():
        internacionales = [
            feature
            for feature in grupo
            if feature["properties"].get("tipo") == "International"
        ]
        unicas.extend(internacionales or grupo)
    return unicas


# --- armado de la capa ---------------------------------------------------
def _vacio(
    capa: Capa,
    caja: tuple[float, float, float, float],
    zoom: int,
    *,
    requiere_zoom: bool,
    avisos: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "capa": capa.id,
        "nombre": capa.nombre,
        "bbox": list(caja),
        "zoom": zoom,
        "min_zoom": capa.min_zoom,
        "fuente": {"nombre": capa.fuente, "url": capa.fuente_url},
        "atribucion": capa.atribucion,
        "total": 0,
        "excedido": False,
        "requiere_zoom": requiere_zoom,
        "avisos": avisos or [],
        "features": [],
    }


def _armar(
    capa: Capa, caja: tuple[float, float, float, float], zoom: int
) -> dict[str, Any]:
    if zoom < capa.min_zoom:
        return _vacio(capa, caja, zoom, requiere_zoom=True)

    features: list[dict[str, Any]] = []
    excedido = False
    avisos: list[str] = []
    errores: list[str] = []
    limite = capa.max_features

    for consulta in capa.consultas:
        try:
            crudas, recortado = _pedir_consulta(
                consulta, caja, zoom, capa, limite=limite
            )
        except ErrorFuente as exc:
            errores.append(f"{consulta.origen or capa.fuente}: {exc}")
            continue
        excedido = excedido or recortado
        for cruda in crudas:
            normalizada = _normalizar(capa, consulta, cruda)
            if normalizada is not None:
                features.append(normalizada)
        if len(features) >= limite:
            excedido = True
            features = features[:limite]
            break

    if not features and errores:
        raise HTTPException(
            status_code=502,
            detail=f"{capa.nombre}: la fuente no respondió ({'; '.join(errores)})",
        )
    if errores:
        avisos.extend(f"Fuente parcial: {error}" for error in errores)

    if capa.dedupe == "biosfera":
        features = _dedupe_biosfera(features)

    respuesta = _vacio(capa, caja, zoom, requiere_zoom=False, avisos=avisos)
    respuesta["total"] = len(features)
    respuesta["excedido"] = excedido
    respuesta["features"] = features
    return respuesta


# --- router --------------------------------------------------------------
router = APIRouter()


@router.get("")
def catalogo() -> dict[str, Any]:
    return {
        "capas": [
            {
                "id": capa.id,
                "nombre": capa.nombre,
                "descripcion": capa.descripcion,
                "fuente": capa.fuente,
                "fuente_url": capa.fuente_url,
                "atribucion": capa.atribucion,
                "color": capa.color,
                "min_zoom": capa.min_zoom,
            }
            for capa in CAPAS
        ],
        "fuentes": [
            "WDPA · UNEP-WCMC e IUCN (Protected Planet)",
            "LandMark (WRI) · FAPI y DGEEC",
            "RESOLVE Ecoregions 2017 (Esri Living Atlas)",
        ],
    }


@router.get("/{capa_id}")
def capa(
    capa_id: str,
    bbox: str = Query(..., description="oeste,sur,este,norte en grados"),
    zoom: int = Query(6, ge=0, le=22),
) -> dict[str, Any]:
    definicion = POR_ID.get(capa_id)
    if definicion is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Capa desconocida: {capa_id}. Opciones: "
                + ", ".join(capa.id for capa in CAPAS)
            ),
        )
    caja = _caja(bbox)
    clave = (definicion.id, caja, zoom)
    guardada = _cache_leer(clave)
    if guardada is not None:
        return guardada
    respuesta = _armar(definicion, caja, zoom)
    if not respuesta["avisos"]:
        _cache_guardar(clave, respuesta)
    return respuesta
