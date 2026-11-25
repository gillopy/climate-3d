"""Earthdata Login interactivo: abre navegador, captura cookies, las guarda.

OB.DAAC (oceandata.sci.gsfc.nasa.gov) exige la cookie de sesión `GETFILE_APP`,
que solo se obtiene completando el flujo OAuth de Earthdata (URS) en un navegador
real. Este módulo abre Chrome/Edge en modo visible, deja al usuario loguearse y
captura las cookies resultantes para reutilizarlas en `descargar/pace_landvi.py`.

El navegador se abre en la máquina donde corre la API: funciona con la app nativa
(`ARRANCAR.bat`). Dentro de Docker no hay display, así que el endpoint responde
409 y las cookies se llevan desde la app nativa o vía `~/.netrc`.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

RAIZ_APP = Path(__file__).resolve().parents[1]
RAIZ_REPO = RAIZ_APP.parent
if str(RAIZ_REPO) not in sys.path:
    sys.path.insert(0, str(RAIZ_REPO))

from comun.rutas import ruta_cookies_earthdata  # noqa: E402

router = APIRouter(prefix="/api/earthdata", tags=["earthdata"])

# URL de getfile que dispara el redirect a URS y, tras el login, devuelve la
# cookie GETFILE_APP en el dominio oceandata. No importa que el archivo exista:
# el handshake OAuth ocurre igual y, ya autenticado, un 404 sigue viniendo de
# oceandata (sirve para distinguir la sesión válida de la página de login).
GETFILE = (
    "https://oceandata.sci.gsfc.nasa.gov/getfile/"
    "PACE_OCI.20260929.L3m.DAY.LANDVI.V3_1.4km.NRT.nc"
)

DOMINIOS = ("urs.earthdata.nasa.gov", "oceandata.sci.gsfc.nasa.gov", "earthdata.nasa.gov")
HOST_OBDAAC = "oceandata.sci.gsfc.nasa.gov"


class LoginResponse(BaseModel):
    ok: bool
    cookies_file: str
    cookies_count: int
    message: str


def _cookies_utiles(cookies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filtra las cookies de los dominios de Earthdata/OB.DAAC."""
    return [
        c for c in cookies
        if any(dominio in c.get("domain", "") for dominio in DOMINIOS)
    ]


def _pedir_prueba(cookies: list[dict[str, Any]], timeout: tuple[float, float]):
    """GET a OB.DAAC con las cookies dadas, sin descargar el cuerpo."""
    sesion = requests.Session()
    sesion.headers["User-Agent"] = "climate3d/1.0"
    sesion.trust_env = False
    for c in cookies:
        sesion.cookies.set(
            c["name"], c["value"], domain=c.get("domain", ""), path=c.get("path", "/")
        )
    return sesion.get(GETFILE, stream=True, timeout=timeout, allow_redirects=True)


def _estado_sesion(
    cookies: list[dict[str, Any]], timeout: tuple[float, float] = (10, 30)
) -> bool | None:
    """¿Las cookies autentican contra OB.DAAC?

    ``True`` = sesión válida, ``False`` = el redirect terminó en URS (login),
    ``None`` = no se pudo comprobar por un error de red. El host final es la
    señal: autenticado, OB.DAAC responde 200 (gránulo real) o 404 (nombre que no
    existe) **desde oceandata**; sin sesión, redirige a `urs.earthdata.nasa.gov`.
    Así la prueba no depende de que un gránulo puntual siga publicado.
    """
    try:
        respuesta = _pedir_prueba(cookies, timeout)
    except requests.RequestException:
        return None
    host = urlparse(respuesta.url or "").netloc.lower()
    respuesta.close()
    return host == HOST_OBDAAC


def _chromium_instalado() -> Path | None:
    """Busca un chrome.exe ya instalado en el cache de Playwright.

    El paquete Python puede esperar una revisión distinta de la que hay en disco;
    apuntar al ejecutable existente evita tener que descargar otro navegador.
    """
    ruta_cache = os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or ""
    cache = (
        Path(ruta_cache) if ruta_cache
        else Path.home() / "AppData" / "Local" / "ms-playwright"
    )
    if not cache.is_dir():
        return None
    for carpeta in sorted(cache.glob("chromium*"), reverse=True):
        candidato = next(carpeta.rglob("chrome.exe"), None)
        if candidato is not None and candidato.is_file():
            return candidato
    return None


@router.get("/login", response_model=LoginResponse)
def login_earthdata_interactive() -> LoginResponse:
    """Abre Chrome/Edge visible, espera el login y guarda las cookies de sesión."""
    if os.environ.get("CLIMATE3D_CONTENEDOR"):
        raise HTTPException(
            status_code=409,
            detail=(
                "El login con navegador no está disponible dentro de Docker: la "
                "ventana se abriría en el contenedor, sin pantalla. Corré una vez la "
                "app nativa (ARRANCAR.bat), usá 'Login Earthdata' y copiá "
                "earthdata_cookies.json a la carpeta de configuración del contenedor. "
                "Usuario/clave y ~/.netrc no sirven para getfile."
            ),
        )

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Falta la dependencia opcional `browser`. No instales paquetes a mano "
                "en el .venv: corré `uv sync --group browser` y reiniciá la consola "
                "(eso deja la versión y el hash en uv.lock). Si tenés Chrome o Edge "
                "instalado, no hace falta bajar un Chromium aparte."
            ),
        ) from exc

    cookies_path = ruta_cookies_earthdata()
    cookies_path.parent.mkdir(parents=True, exist_ok=True)

    opciones_base: dict[str, Any] = {
        "headless": False,
        "args": ["--start-maximized"],
    }

    with sync_playwright() as p:
        navegador = None
        # Preferir el navegador real del usuario (Chrome/Edge instalados) para
        # que no parezca un "navegador de testing". `channel` usa el ejecutable
        # del sistema; si no está, caemos al Chromium del cache de Playwright.
        canals = ["chrome", "msedge"]
        ultimo_error: Exception | None = None
        for canal in canals:
            try:
                navegador = p.chromium.launch(channel=canal, **opciones_base)
                break
            except Exception as exc:  # canal no instalado
                ultimo_error = exc
        if navegador is None:
            chrome_path = _chromium_instalado()
            opciones = dict(opciones_base)
            if chrome_path is not None:
                opciones["executable_path"] = str(chrome_path)
            try:
                navegador = p.chromium.launch(**opciones)
            except Exception as exc:
                ultimo_error = exc
        if navegador is None:
            raise HTTPException(
                status_code=500,
                detail=(
                    "No se pudo abrir el navegador. Instalá Chrome o Edge, o el "
                    "Chromium de Playwright. "
                    f"Detalle: {ultimo_error}"
                ),
            ) from ultimo_error

        contexto = navegador.new_context(no_viewport=True)
        pagina = contexto.new_page()

        # Arrancar desde getfile: redirige a URS para loguearse y, al volver,
        # OB.DAAC asienta la cookie GETFILE_APP que necesita el descargador.
        try:
            pagina.goto(GETFILE, wait_until="domcontentloaded", timeout=60000)
        except Exception as exc:
            navegador.close()
            raise HTTPException(
                status_code=500, detail=f"No se pudo abrir la página de login: {exc}"
            ) from exc

        # Esperar a que el usuario complete el login. No basta con que exista
        # GETFILE_APP: apenas se toca getfile se setea con urs_token=0 y sigue
        # devolviendo la página de login. Validamos de verdad con un request de
        # prueba hasta que el redirect ya no caiga en URS.
        max_espera = 300  # 5 minutos
        inicio = time.time()
        capturadas: list[dict[str, Any]] = []
        # Espacio entre validaciones: cada una hace un GET a OB.DAAC.
        siguiente_validacion = 0.0

        while time.time() - inicio < max_espera:
            transcurrido = time.time() - inicio
            if transcurrido >= siguiente_validacion:
                utiles = _cookies_utiles(contexto.cookies())
                if utiles and _estado_sesion(utiles) is True:
                    capturadas = utiles
                    break
                siguiente_validacion = transcurrido + 3
            time.sleep(1)

        navegador.close()

    if not capturadas:
        raise HTTPException(
            status_code=408,
            detail=(
                "No se pudo verificar la sesión de Earthdata. Asegurate de "
                "completar el login en la ventana del navegador y de tener una "
                "conexión estable. Probá de nuevo."
            ),
        )

    cookies_path.write_text(
        json.dumps(capturadas, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    try:
        # Las cookies son una sesión viva: que no las lea cualquiera en POSIX.
        os.chmod(cookies_path, 0o600)
    except OSError:
        pass

    return LoginResponse(
        ok=True,
        cookies_file=str(cookies_path),
        cookies_count=len(capturadas),
        message=(
            f"Sesión guardada: {len(capturadas)} cookies de Earthdata. "
            "Ya podés generar PACE LANDVI."
        ),
    )


@router.get("/cookies-status")
def cookies_status() -> dict[str, Any]:
    """Devuelve si hay una sesión de Earthdata válida (verificada contra OB.DAAC).

    Un error de red **no** invalida las cookies: se informa ``verified: False`` y
    se conservan. Sólo se descarta el archivo cuando OB.DAAC confirma que la
    sesión ya no autentica (el redirect vuelve a URS).
    """
    cookies_path = ruta_cookies_earthdata()
    if not cookies_path.is_file():
        return {"ok": True, "configured": False, "cookies_count": 0, "file": str(cookies_path)}

    try:
        cookies = json.loads(cookies_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "configured": False, "error": str(exc), "file": str(cookies_path)}

    if not cookies:
        return {"ok": True, "configured": False, "cookies_count": 0, "file": str(cookies_path)}

    estado = _estado_sesion(cookies, timeout=(3, 8))
    if estado is None:
        # Sin red no se puede afirmar que venció: no se borra nada.
        return {
            "ok": True,
            "configured": True,
            "verified": False,
            "cookies_count": len(cookies),
            "file": str(cookies_path),
        }

    if not estado:
        cookies_path.unlink(missing_ok=True)
        return {
            "ok": True,
            "configured": False,
            "verified": True,
            "cookies_count": 0,
            "file": str(cookies_path),
        }

    return {
        "ok": True,
        "configured": True,
        "verified": True,
        "cookies_count": len(cookies),
        "getfile": True,
        "file": str(cookies_path),
    }


@router.post("/cookies-clear")
def cookies_clear() -> dict[str, Any]:
    """Borra el archivo de cookies guardado."""
    cookies_path = ruta_cookies_earthdata()
    if cookies_path.is_file():
        cookies_path.unlink()
    return {"ok": True, "message": "Cookies de Earthdata eliminadas"}
