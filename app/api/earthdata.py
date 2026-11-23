"""Earthdata Login interactivo: abre navegador, captura cookies, las guarda.

OB.DAAC (oceandata.sci.gsfc.nasa.gov) exige la cookie de sesión `GETFILE_APP`,
que solo se obtiene completando el flujo OAuth de Earthdata (URS) en un navegador
real. Este módulo abre Chromium en modo visible, deja al usuario loguearse y
captura las cookies resultantes para reutilizarlas en `descargar/pace_landvi.py`.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

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
# el handshake OAuth ocurre igual.
GETFILE = (
    "https://oceandata.sci.gsfc.nasa.gov/getfile/"
    "PACE_OCI.20260929.L3m.DAY.LANDVI.V3_1.4km.NRT.nc"
)

DOMINIOS = ("urs.earthdata.nasa.gov", "oceandata.sci.gsfc.nasa.gov", "earthdata.nasa.gov")


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


def _getfile_valido(cookies: list[dict[str, Any]]) -> bool:
    """Comprueba que las cookies realmente autentican contra OB.DAAC.

    Una cookie `GETFILE_APP` con `urs_token: 0` se setea apenas se toca getfile,
    antes del login: esa seguiría devolviendo la página de login. Solo la damos
    por válida si un request de prueba NO cae en HTML de autenticación.
    """
    sesion = requests.Session()
    sesion.headers["User-Agent"] = "climate3d/1.0"
    sesion.trust_env = False
    for c in cookies:
        sesion.cookies.set(
            c["name"], c["value"], domain=c.get("domain", ""), path=c.get("path", "/")
        )
    try:
        respuesta = sesion.get(GETFILE, stream=True, timeout=(15, 45), allow_redirects=True)
        tipo = respuesta.headers.get("Content-Type", "")
        respuesta.close()
        # NetCDF/octet-stream = autenticado. text/html = página de login.
        return "text/html" not in tipo.lower()
    except requests.RequestException:
        return False


def _chromium_instalado() -> Path | None:
    """Busca un chrome.exe ya instalado en el cache de Playwright.

    El paquete Python puede esperar una revisión distinta de la que hay en disco;
    apuntar al ejecutable existente evita tener que descargar otro navegador.
    """
    cache = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")) if os.environ.get("PLAYWRIGHT_BROWSERS_PATH") else (Path.home() / "AppData" / "Local" / "ms-playwright")
    if not cache.is_dir():
        return None
    for carpeta in sorted(cache.glob("chromium*"), reverse=True):
        candidato = next(carpeta.rglob("chrome.exe"), None)
        if candidato is not None and candidato.is_file():
            return candidato
    return None


@router.get("/login", response_model=LoginResponse)
def login_earthdata_interactive() -> LoginResponse:
    """Abre Chromium visible, espera el login y guarda las cookies de sesión."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Playwright no está instalado en el entorno de la app. "
                "Ejecutá: `.venv\\Scripts\\python.exe -m pip install playwright` "
                "y luego `.venv\\Scripts\\python.exe -m playwright install chromium`"
            ),
        ) from exc

    cookies_path = ruta_cookies_earthdata()
    cookies_path.parent.mkdir(parents=True, exist_ok=True)

    # Usar cualquier Chromium ya instalado en el cache de Playwright, sin exigir
    # la revision exacta que espera el paquete (evita descargas innecesarias).
    chrome_path = _chromium_instalado()
    opciones_lanzamiento: dict[str, Any] = {
        "headless": False,
        "args": ["--start-maximized"],
    }
    if chrome_path is not None:
        opciones_lanzamiento["executable_path"] = str(chrome_path)

    with sync_playwright() as p:
        navegador = None
        try:
            navegador = p.chromium.launch(**opciones_lanzamiento)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=(
                    "No se pudo abrir Chromium. Instalalo con: "
                    "`.venv\\Scripts\\python.exe -m playwright install chromium`. "
                    f"Detalle: {exc}"
                ),
            ) from exc

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
        # prueba hasta que NO caiga en HTML de autenticación.
        max_espera = 300  # 5 minutos
        inicio = time.time()
        capturadas: list[dict[str, Any]] = []
        # Espacio entre validaciones: cada una hace un GET a OB.DAAC.
        siguiente_validacion = 0.0

        while time.time() - inicio < max_espera:
            transcurrido = time.time() - inicio
            if transcurrido >= siguiente_validacion:
                utiles = _cookies_utiles(contexto.cookies())
                if utiles and _getfile_valido(utiles):
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
    """Devuelve si hay una sesión de Earthdata válida (verificada contra OB.DAAC)."""
    cookies_path = ruta_cookies_earthdata()
    if not cookies_path.is_file():
        return {"ok": True, "configured": False, "cookies_count": 0, "file": str(cookies_path)}

    try:
        cookies = json.loads(cookies_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "configured": False, "error": str(exc), "file": str(cookies_path)}

    valido = bool(cookies) and _getfile_valido(cookies)
    if cookies and not valido:
        # Cookie vencida/incompleta: la descartamos para no dar un falso "conectado".
        cookies_path.unlink(missing_ok=True)
    return {
        "ok": True,
        "configured": valido,
        "cookies_count": len(cookies) if valido else 0,
        "getfile": valido,
        "file": str(cookies_path),
    }


@router.post("/cookies-clear")
def cookies_clear() -> dict[str, Any]:
    """Borra el archivo de cookies guardado."""
    cookies_path = ruta_cookies_earthdata()
    if cookies_path.is_file():
        cookies_path.unlink()
    return {"ok": True, "message": "Cookies de Earthdata eliminadas"}
