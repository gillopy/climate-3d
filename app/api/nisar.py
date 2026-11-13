"""Visor NISAR (Fase 1): busqueda en ASF y browse publico cacheado.

La app no baja los ``.h5``: un GCOV pesa ~1.9 GB y exige Earthdata Login. Para
elegir una escena alcanza con lo que ASF ya publica: la busqueda por caja,
el poligono de cada granulo y sus imagenes browse, que son publicas.

Ninguna imagen se inventa: el backend proxya el PNG de ASF tal cual y lo cachea
en ``app/var/nisar``. Solo se aceptan URLs del host de browse de ASF, asi el
proxy no sirve para leer cualquier cosa de internet.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

ASF_SEARCH = "https://api.daac.asf.alaska.edu/services/search/param"
BROWSE_HOST = "nisar.asf.earthdatacloud.nasa.gov"
BROWSE_PREFIX = "/BROWSE/"
USER_AGENT = "climate3d-nisar/0.1 (+local)"
MAX_BROWSE_BYTES = 40 * 1024 * 1024
MAX_RESULTADOS = 500
MAX_DIAS = 366
MAX_LADO_GRADOS = 20.0

RAIZ_APP = Path(__file__).resolve().parents[1]
RAIZ_REPO = RAIZ_APP.parent
CACHE = RAIZ_APP / "var" / "nisar" / "cache"
PARAGUAY = RAIZ_REPO / "datos" / "paraguay_gadm.json"

#: Caja por defecto: Paraguay continental con un margen comodo.
CAJA_PARAGUAY = [-62.7, -27.7, -54.2, -19.2]

#: En el nombre del granulo: ciclo, track, direccion y frame.
_TRACK_FRAME = re.compile(r"_(\d{3})_(\d{3})_[AD]_(\d{3})_")
_FECHA_NISAR = re.compile(r"(\d{8})T(\d{6})")

#: Niveles que tienen sentido para un visor de imagenes. RSLC (L1) queda afuera:
#: no esta geocodificado y no se puede superponer a un mapa.
NIVELES: tuple[tuple[str, str, str], ...] = (
    (
        "GCOV",
        "GCOV - covarianza geocodificada",
        "Backscatter RTC gamma0 a 10/20 m. Es el producto para analisis de imagenes.",
    ),
    (
        "GSLC",
        "GSLC - SLC geocodificado",
        "Amplitud compleja por polarizacion, ya geocodificada.",
    ),
    (
        "GUNW",
        "GUNW - interferograma geocodificado",
        "Interferograma desenvuelto: deformacion del terreno y coherencia.",
    ),
    (
        "SME2",
        "SME2 - humedad del suelo",
        "Humedad del suelo en EASE-Grid 2.0, ~200 m. Suele no traer browse.",
    ),
)
NIVELES_VALIDOS = {valor for valor, _, _ in NIVELES}
POLARIZACIONES_VALIDAS = {"HH", "HV", "VV", "VH"}


class NivelNisar(BaseModel):
    value: str
    label: str
    detail: str


class NisarCatalog(BaseModel):
    levels: list[NivelNisar]
    default_bbox: list[float]
    default_days: int
    earthdata_configured: bool
    data_root: str


class GranuleImage(BaseModel):
    label: str
    url: str


class Granule(BaseModel):
    id: str
    level: str
    start: str
    stop: str
    direction: str
    path: int | None = None
    frame: int | None = None
    polarization: list[str] = Field(default_factory=list)
    collection: str = ""
    size_mb: float | None = None
    footprint: list[list[float]] = Field(default_factory=list)
    thumbnail: str | None = None
    images: list[GranuleImage] = Field(default_factory=list)
    download: str = ""
    asf_url: str = ""


class LocalScene(BaseModel):
    id: str
    date: str
    size_mb: float


class LocalScenes(BaseModel):
    track: int
    frame: int
    collection: str
    total: int
    scenes: list[LocalScene]


class NisarSearch(BaseModel):
    bbox: list[float]
    start: str
    end: str
    level: str
    polarization: str | None = None
    total: int
    returned: int
    granules: list[Granule]
    notes: list[str] = Field(default_factory=list)


router = APIRouter()


# --- utilidades HTTP ----------------------------------------------------
def _consultar(params: dict[str, str], timeout: float = 30.0) -> bytes:
    url = f"{ASF_SEARCH}?{urllib.parse.urlencode(params)}"
    pedido = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as respuesta:
            return respuesta.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"ASF no respondio: {type(exc).__name__}: {exc}",
        ) from exc


def _json_asf(params: dict[str, str]) -> Any:
    crudo = _consultar(params)
    try:
        return json.loads(crudo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=502, detail="ASF devolvio una respuesta que no es JSON"
        ) from exc


def _contar(params: dict[str, str]) -> int:
    crudo = _consultar({**params, "output": "count"})
    try:
        return int(crudo.decode("utf-8").strip().strip('"'))
    except (UnicodeDecodeError, ValueError):
        return 0


# --- validacion de pedidos ---------------------------------------------
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
    if este - oeste > MAX_LADO_GRADOS or norte - sur > MAX_LADO_GRADOS:
        raise HTTPException(
            status_code=400,
            detail=f"caja demasiado grande: maximo {MAX_LADO_GRADOS:g} grados por lado",
        )
    return oeste, sur, este, norte


def _fecha(valor: str | None, por_defecto: date) -> date:
    if not valor:
        return por_defecto
    try:
        return date.fromisoformat(valor[:10])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"fecha invalida: {valor}") from exc


def _ventana(inicio: str | None, fin: str | None) -> tuple[date, date]:
    hoy = datetime.now(timezone.utc).date()
    desde = _fecha(inicio, hoy - timedelta(days=29))
    hasta = _fecha(fin, hoy)
    if hasta < desde:
        desde, hasta = hasta, desde
    if (hasta - desde).days > MAX_DIAS:
        raise HTTPException(
            status_code=400, detail=f"ventana demasiado larga: maximo {MAX_DIAS} dias"
        )
    return desde, hasta


def _nivel(valor: str) -> str:
    nivel = (valor or "GCOV").upper()
    if nivel not in NIVELES_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"nivel desconocido: {valor}. Opciones: {', '.join(sorted(NIVELES_VALIDOS))}",
        )
    return nivel


def _polarizacion(valor: str | None) -> str | None:
    if not valor:
        return None
    pol = valor.upper()
    if pol not in POLARIZACIONES_VALIDAS:
        raise HTTPException(
            status_code=400,
            detail=f"polarizacion desconocida: {valor}. Opciones: HH, HV, VV, VH",
        )
    return pol


# --- browse: proxy restringido y cacheado -------------------------------
def _url_browse(valor: str) -> str:
    partes = urllib.parse.urlsplit(valor)
    if partes.scheme != "https":
        raise HTTPException(status_code=400, detail="solo se aceptan URLs https")
    if partes.hostname != BROWSE_HOST:
        raise HTTPException(status_code=400, detail="host de browse no permitido")
    if partes.username or partes.password:
        raise HTTPException(status_code=400, detail="la URL no puede traer credenciales")
    if not partes.path.startswith(BROWSE_PREFIX):
        raise HTTPException(status_code=400, detail="ruta de browse no permitida")
    if not partes.path.lower().endswith(".png"):
        raise HTTPException(status_code=400, detail="solo se sirven PNG de browse")
    return valor


def _destino_final_permitido(url: str) -> bool:
    """ASF sirve el browse directo o via su CDN firmado (CloudFront/S3).

    El redirect no puede sacarnos del browse de NISAR: se acepta el host de ASF
    y los hosts de AWS cuyo path sea el bucket `nisar-browse`.
    """
    partes = urllib.parse.urlsplit(url)
    if partes.scheme != "https":
        return False
    host = partes.hostname or ""
    if host == BROWSE_HOST:
        return partes.path.startswith(BROWSE_PREFIX)
    if host.endswith(".cloudfront.net") or host.endswith(".amazonaws.com"):
        return "nisar-browse" in partes.path
    return False


def _descargar_png(url: str) -> bytes:
    pedido = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(pedido, timeout=60) as respuesta:
            if not _destino_final_permitido(respuesta.geturl()):
                raise HTTPException(
                    status_code=502,
                    detail="ASF redirigio fuera del browse permitido",
                )
            datos = respuesta.read(MAX_BROWSE_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo bajar el browse de ASF: {type(exc).__name__}: {exc}",
        ) from exc
    if len(datos) > MAX_BROWSE_BYTES:
        raise HTTPException(status_code=502, detail="el browse supera el limite de 40 MB")
    if not datos.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(status_code=502, detail="ASF no devolvio un PNG")
    return datos


def _proxy(url: str) -> str:
    """URL local del proxy para una imagen browse de ASF."""
    return "/api/nisar/browse?url=" + urllib.parse.quote(url, safe="")


def _etiqueta(url: str) -> str:
    nombre = url.rsplit("/", 1)[-1]
    conocidas = {
        "_LATLON.png": "Mapa (lat/lon)",
        "_NATIVE.png": "Vista nativa",
        "_NATIVE_A_HHHH.png": "HH",
        "_NATIVE_A_HVHV.png": "HV",
        "_NATIVE_A_VVVV.png": "VV",
        "_NATIVE_A_VHVH.png": "VH",
        "_NATIVE_B_HHHH.png": "Banda B - HH",
        "_NATIVE_B_HVHV.png": "Banda B - HV",
    }
    for sufijo, etiqueta in conocidas.items():
        if nombre.endswith(sufijo):
            return etiqueta
    return nombre.rsplit("_", 1)[-1].removesuffix(".png")


def _orden_imagen(url: str) -> int:
    nombre = url.rsplit("/", 1)[-1]
    orden = (
        "_LATLON.png",
        "_NATIVE_A_HHHH.png",
        "_NATIVE_A_HVHV.png",
        "_NATIVE_A_VVVV.png",
        "_NATIVE_A_VHVH.png",
        "_NATIVE_B_HHHH.png",
        "_NATIVE_B_HVHV.png",
        "_NATIVE.png",
    )
    for posicion, sufijo in enumerate(orden):
        if nombre.endswith(sufijo):
            return posicion
    return len(orden)


def _tamano_mb(props: dict[str, Any]) -> float | None:
    info = props.get("bytes")
    if not isinstance(info, dict):
        return None
    principal = props.get("fileName")
    candidatos = [principal] if isinstance(principal, str) else []
    candidatos += [
        nombre
        for nombre in info
        if nombre.endswith(".h5") and not nombre.endswith("_QA_STATS.h5")
    ]
    for nombre in candidatos:
        dato = info.get(nombre)
        if isinstance(dato, dict):
            valor = dato.get("bytes")
            if isinstance(valor, int) and valor > 0:
                return round(valor / 1e6, 1)
    return None


def _granulo(feature: dict[str, Any]) -> Granule:
    props = feature.get("properties") or {}
    geometria = feature.get("geometry") or {}
    anillos = geometria.get("coordinates") or []
    anillo = anillos[0] if anillos and isinstance(anillos[0], list) else []
    huella = [
        [float(punto[0]), float(punto[1])]
        for punto in anillo
        if isinstance(punto, list) and len(punto) >= 2
    ]

    browse = [
        url
        for url in (props.get("browse") or [])
        if isinstance(url, str) and url.lower().endswith(".png")
    ]
    miniatura = next((url for url in browse if url.endswith("_thumbnail.png")), None)
    imagenes = sorted((url for url in browse if url != miniatura), key=_orden_imagen)

    pol = props.get("mainBandPolarization") or []
    if isinstance(pol, str):
        pol = [pol]

    granulo_id = str(props.get("fileID") or props.get("sceneName") or "")
    coleccion = str(props.get("collectionName") or "")
    if not coleccion:
        # El JSON de ASF puede dejar collectionName vacio; la URL manda.
        url = str(props.get("url") or "")
        if "/NISAR/" in url:
            coleccion = url.split("/NISAR/", 1)[1].split("/", 1)[0]
    return Granule(
        id=granulo_id,
        level=str(props.get("processingLevel") or ""),
        start=str(props.get("startTime") or ""),
        stop=str(props.get("stopTime") or ""),
        direction=str(props.get("flightDirection") or ""),
        path=_entero(props.get("pathNumber")),
        frame=_entero(props.get("frameNumber")),
        polarization=[str(valor) for valor in pol],
        collection=coleccion,
        size_mb=_tamano_mb(props),
        footprint=huella,
        thumbnail=_proxy(miniatura) if miniatura else None,
        images=[GranuleImage(label=_etiqueta(url), url=_proxy(url)) for url in imagenes],
        download=str(props.get("url") or ""),
        asf_url=(
            "https://search.asf.alaska.edu/#/?dataset=NISAR&granule="
            + urllib.parse.quote(granulo_id, safe="")
        ),
    )


def _entero(valor: Any) -> int | None:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _datos() -> Path:
    """Raiz de datos del pipeline (``CLIMATE3D_DATOS`` o el default)."""
    comun = RAIZ_REPO / "comun"
    if str(comun) not in sys.path:
        sys.path.insert(0, str(comun))
    from rutas import DATOS

    return DATOS


def _earthdata_configurada() -> bool:
    if os.environ.get("EARTHDATA_USER"):
        return True
    env = RAIZ_REPO / ".env"
    try:
        for linea in env.read_text(encoding="utf-8").splitlines():
            limpia = linea.strip()
            if limpia.startswith("EARTHDATA_USER="):
                return bool(limpia.split("=", 1)[1].strip())
    except OSError:
        return False
    return False


# --- endpoints ----------------------------------------------------------
@router.get("/catalog", response_model=NisarCatalog)
def catalogo() -> NisarCatalog:
    return NisarCatalog(
        levels=[
            NivelNisar(value=valor, label=etiqueta, detail=detalle)
            for valor, etiqueta, detalle in NIVELES
        ],
        default_bbox=CAJA_PARAGUAY,
        default_days=30,
        earthdata_configured=_earthdata_configurada(),
        data_root=str(_datos()),
    )


@router.get("/search", response_model=NisarSearch)
def buscar(
    bbox: str = Query(..., description="oeste,sur,este,norte"),
    start: str | None = None,
    end: str | None = None,
    level: str = "GCOV",
    polarization: str | None = None,
    max_resultados: int = Query(250, alias="max", ge=1, le=MAX_RESULTADOS),
) -> NisarSearch:
    oeste, sur, este, norte = _caja(bbox)
    desde, hasta = _ventana(start, end)
    nivel = _nivel(level)
    pol = _polarizacion(polarization)

    base = {
        "dataset": "NISAR",
        "processingLevel": nivel,
        "bbox": f"{oeste:g},{sur:g},{este:g},{norte:g}",
        "start": desde.isoformat(),
        "end": hasta.isoformat(),
    }
    if pol:
        base["mainBandPolarization"] = pol

    total = _contar(base)
    datos = _json_asf({**base, "output": "geojson", "maxResults": str(max_resultados)})
    features = datos.get("features") if isinstance(datos, dict) else None
    granulos = [_granulo(feature) for feature in (features or []) if isinstance(feature, dict)]
    granulos.sort(key=lambda granulo: granulo.start, reverse=True)

    notas: list[str] = []
    if total > len(granulos):
        notas.append(
            f"Se muestran los primeros {len(granulos)} de {total}. "
            "Achicá la caja o la ventana para ver el resto."
        )
    if not granulos:
        notas.append(f"No hay escenas NISAR {nivel} en esa caja y ventana.")
    if nivel == "SME2":
        notas.append("SME2 suele publicarse sin imagen browse.")
    if not _earthdata_configurada():
        notas.append(
            "Los .h5 no se descargan en esta fase; el browse no necesita credenciales."
        )

    return NisarSearch(
        bbox=[oeste, sur, este, norte],
        start=desde.isoformat(),
        end=hasta.isoformat(),
        level=nivel,
        polarization=pol,
        total=total,
        returned=len(granulos),
        granules=granulos,
        notes=notas,
    )


@router.get("/browse")
def browse(url: str = Query(..., min_length=10)) -> Response:
    destino = _url_browse(url)
    cache = CACHE / (hashlib.sha256(destino.encode("utf-8")).hexdigest() + ".png")
    cabeceras = {"Cache-Control": "public, max-age=86400"}
    if cache.is_file() and cache.stat().st_size > 0:
        return FileResponse(cache, media_type="image/png", headers=cabeceras)

    datos = _descargar_png(destino)
    cache.parent.mkdir(parents=True, exist_ok=True)
    parcial = cache.with_suffix(f".{os.getpid()}.part")
    parcial.write_bytes(datos)
    os.replace(parcial, cache)
    return Response(content=datos, media_type="image/png", headers=cabeceras)


@router.get("/local", response_model=LocalScenes)
def locales(
    track: int = Query(..., ge=1, le=999),
    frame: int = Query(..., ge=1, le=999),
    coleccion: str = Query(..., min_length=1, max_length=80),
) -> LocalScenes:
    """Escenas .h5 ya bajadas para un track/frame/colección.

    No abre los HDF5: alcanza con el nombre (ciclo/track/frame/fecha) que
    escribe ASF. Así el endpoint vive en el venv de la API, sin h5py.
    """
    if any(c in coleccion for c in '\\/:*?"<>|'):
        raise HTTPException(status_code=400, detail="coleccion invalida")
    carpeta = _datos() / "nisar" / coleccion
    escenas: list[LocalScene] = []
    if carpeta.is_dir():
        for ruta in sorted(carpeta.glob("*.h5")):
            partes = _TRACK_FRAME.search(ruta.stem)
            if (
                not partes
                or int(partes.group(2)) != track
                or int(partes.group(3)) != frame
            ):
                continue
            fecha = _FECHA_NISAR.search(ruta.stem)
            if not fecha:
                continue
            dia, hora = fecha.groups()
            escenas.append(
                LocalScene(
                    id=ruta.stem,
                    date=f"{dia[:4]}-{dia[4:6]}-{dia[6:]} {hora[:2]}:{hora[2:4]} UTC",
                    size_mb=round(ruta.stat().st_size / 1e6, 1),
                )
            )
    escenas.sort(key=lambda escena: escena.date)
    return LocalScenes(
        track=track,
        frame=frame,
        collection=coleccion,
        total=len(escenas),
        scenes=escenas,
    )


@router.get("/paraguay")
def paraguay() -> Response:
    if not PARAGUAY.is_file():
        raise HTTPException(status_code=404, detail="Falta datos/paraguay_gadm.json")
    return Response(
        content=PARAGUAY.read_bytes(),
        media_type="application/json",
        headers={"Cache-Control": "public, max-age=86400"},
    )
