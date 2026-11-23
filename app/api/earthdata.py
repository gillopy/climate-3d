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
from urllib.parse import quote

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

        # Esperar a que el usuario complete el login. Señal de éxito: presencia
        # de GETFILE_APP (oceandata) o de una cookie de sesión URS, y salida de
        # la pantalla de login.
        max_espera = 300  # 5 minutos
        inicio = time.time()
        capturadas: list[dict[str, Any]] = []

        while time.time() - inicio < max_espera:
            utiles = _cookies_utiles(contexto.cookies())
            tiene_getfile = any(
                "getfile" in c.get("name", "").lower() for c in utiles
            )
            en_login = "urs.earthdata.nasa.gov/login" in (pagina.url or "")
            if utiles and (tiene_getfile or not en_login):
                capturadas = utiles
                # Si ya tenemos GETFILE_APP, listo. Si no, esperamos un poco más
                # a que el redirect final la asiente.
                if tiene_getfile:
                    break
            time.sleep(2)

        # Último intento: ensure GETFILE_APP tras navegar de nuevo a getfile.
        if capturadas and not any("getfile" in c.get("name", "").lower() for c in capturadas):
            try:
                pagina.goto(GETFILE, wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)
                capturadas = _cookies_utiles(contexto.cookies()) or capturadas
            except Exception:
                pass

        navegador.close()

    if not capturadas:
        raise HTTPException(
            status_code=408,
            detail=(
                "Tiempo agotado esperando el login. Completá el inicio de sesión "
                "en la ventana del navegador cuando aparezca."
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
    """Devuelve si hay cookies guardadas, cuántas y si incluyen GETFILE_APP."""
    cookies_path = ruta_cookies_earthdata()
    if not cookies_path.is_file():
        return {"ok": True, "configured": False, "cookies_count": 0, "file": str(cookies_path)}

    try:
        cookies = json.loads(cookies_path.read_text(encoding="utf-8"))
        return {
            "ok": True,
            "configured": bool(cookies),
            "cookies_count": len(cookies),
            "getfile": any("getfile" in c.get("name", "").lower() for c in cookies),
            "file": str(cookies_path),
        }
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "configured": False, "error": str(exc), "file": str(cookies_path)}


@router.post("/cookies-clear")
def cookies_clear() -> dict[str, Any]:
    """Borra el archivo de cookies guardado."""
    cookies_path = ruta_cookies_earthdata()
    if cookies_path.is_file():
        cookies_path.unlink()
    return {"ok": True, "message": "Cookies de Earthdata eliminadas"}
