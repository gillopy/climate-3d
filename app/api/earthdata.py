"""Earthdata Login sin automatizar navegador: cookie pegada a mano, como respaldo.

OB.DAAC (oceandata.sci.gsfc.nasa.gov) acepta dos formas de autenticación:

* Usuario y clave de Earthdata (`EARTHDATA_USER`/`EARTHDATA_PASSWORD`): es el camino
  que usa `descargar/pace_landvi.py`. No necesita esta pantalla.
* La cookie de sesión `GETFILE_APP`, que sólo deja el flujo OAuth completado en un
  navegador real. Este módulo existe para esa alternativa.

Antes el flujo con cookie se automatizaba abriendo Chrome/Edge con Playwright: una
dependencia pesada (navegador incluido) al servicio de una sola pantalla, y además
inservible dentro de Docker, donde no hay display.

Ahora es manual y funciona igual en nativo y en contenedor:

1. La UI te manda a `GETFILE` en tu navegador y te pide iniciar sesión en URS.
2. Copiás la cookie `GETFILE_APP` desde las herramientas de desarrollo (o el
   contenido de `earthdata_cookies.json` si ya lo tenés) y la pegás en la consola.
3. `POST /api/earthdata/cookies` la verifica contra OB.DAAC y, sólo si autentica,
   la guarda con permisos de dueño para que la use `descargar/pace_landvi.py`.
"""
from __future__ import annotations

import json
import os
import sys
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

#: Nombre de la cookie que OB.DAAC usa como sesión para `getfile`.
COOKIE_SESION = "GETFILE_APP"

#: Dominio de la cookie pegada a mano. `GETFILE_APP` la emite OB.DAAC para el host de
#: `getfile`: si se guardara con dominio earthdata.nasa.gov el jar de requests no la
#: enviaría a oceandata y la verificación fallaría con una cookie perfectamente válida.
DOMINIO_COOKIE = HOST_OBDAAC


class LoginResponse(BaseModel):
    ok: bool
    cookies_file: str
    cookies_count: int
    message: str


class CookiesRequest(BaseModel):
    """Cookie pegada a mano.

    Acepta las dos formas cómodas: el valor pelado de `GETFILE_APP` (o
    `GETFILE_APP=valor`, tal como se copia del navegador) o la lista completa de
    cookies de un `earthdata_cookies.json` exportado.
    """

    cookie: str | None = None
    cookies: list[dict[str, Any]] | None = None


def _cookies_utiles(cookies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filtra las cookies de los dominios de Earthdata/OB.DAAC."""
    return [
        c for c in cookies
        if any(dominio in c.get("domain", "") for dominio in DOMINIOS)
    ]


def _normalizar(peticion: CookiesRequest) -> list[dict[str, Any]]:
    """Convierte lo que pegó el operador en la lista de cookies de la sesión."""
    if peticion.cookies:
        limpias: list[dict[str, Any]] = []
        for cruda in peticion.cookies:
            if not isinstance(cruda, dict):
                raise HTTPException(status_code=400, detail="Cada cookie debe ser un objeto")
            nombre, valor = cruda.get("name"), cruda.get("value")
            if not isinstance(nombre, str) or not isinstance(valor, str) or not nombre:
                raise HTTPException(
                    status_code=400, detail="Cada cookie necesita `name` y `value` de texto"
                )
            dominio = str(cruda.get("domain") or DOMINIO_COOKIE)
            if nombre == COOKIE_SESION:
                # La sesión de `getfile` sólo vale para OB.DAAC: se re-ancla ahí aunque
                # el export la haya traído con el dominio del portal de Earthdata.
                dominio = DOMINIO_COOKIE
            limpias.append({
                "name": nombre,
                "value": valor,
                "domain": dominio,
                "path": str(cruda.get("path") or "/"),
            })
        utiles = _cookies_utiles(limpias)
        if not utiles:
            raise HTTPException(
                status_code=400,
                detail="Esas cookies no son de Earthdata/OB.DAAC: falta el dominio correcto.",
            )
        return utiles

    pegada = (peticion.cookie or "").strip()
    if not pegada:
        raise HTTPException(
            status_code=400,
            detail="Pegá el valor de la cookie GETFILE_APP (o el contenido de earthdata_cookies.json).",
        )
    if "=" in pegada and "\n" not in pegada:
        nombre, _, valor = pegada.partition("=")
        if nombre.strip().upper() == COOKIE_SESION:
            pegada = valor.strip()
    return [{"name": COOKIE_SESION, "value": pegada, "domain": DOMINIO_COOKIE, "path": "/"}]


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


@router.post("/cookies", response_model=LoginResponse)
def guardar_cookies(peticion: CookiesRequest) -> LoginResponse:
    """Verifica y guarda la cookie de sesión que pegó el operador.

    Nunca guarda algo sin verificar: si OB.DAAC no confirma la sesión, responde
    400 (cookie vencida o equivocada) o 503 (no se pudo comprobar por red) y el
    archivo anterior queda intacto.
    """
    cookies = _normalizar(peticion)
    estado = _estado_sesion(cookies)
    if estado is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "No se pudo verificar la cookie contra OB.DAAC (sin red o el sitio no "
                "respondió). Probá de nuevo en un rato: no se guardó nada."
            ),
        )
    if not estado:
        raise HTTPException(
            status_code=400,
            detail=(
                "La cookie no autentica contra OB.DAAC. Copiá de nuevo `GETFILE_APP` "
                "después de iniciar sesión en https://urs.earthdata.nasa.gov."
            ),
        )

    cookies_path = ruta_cookies_earthdata()
    cookies_path.parent.mkdir(parents=True, exist_ok=True)
    datos = json.dumps(cookies, ensure_ascii=False, indent=2).encode("utf-8")
    # Se escribe en un temporal con modo 0600 desde el dia cero y recien despues se
    # publica: si el chmod fallara, la cookie anterior queda intacta y la nueva nunca
    # existio con permisos amplios.
    temporal = cookies_path.with_suffix(cookies_path.suffix + ".nuevo")
    try:
        descriptor = os.open(temporal, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "wb") as fh:
            fh.write(datos)
        os.replace(temporal, cookies_path)
    except OSError as exc:  # pragma: no cover - plataformas sin chmod
        temporal.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo guardar {cookies_path} con permisos de dueño: {exc}",
        ) from exc

    return LoginResponse(
        ok=True,
        cookies_file=str(cookies_path),
        cookies_count=len(cookies),
        message=(
            f"Sesión guardada: {len(cookies)} cookie(s) de Earthdata. "
            "Ya podés generar PACE LANDVI."
        ),
    )


def _hay_credenciales() -> bool:
    """Si hay usuario y clave de Earthdata en el entorno.

    Con eso `descargar/pace_landvi.py` baja de OB.DAAC sin cookie, así que la
    consola no tiene por qué ofrecer el flujo de la cookie. `ARRANCAR.ps1` y el
    `env_file` de compose exportan las dos variables al proceso.
    """
    return bool(
        os.environ.get("EARTHDATA_USER") and os.environ.get("EARTHDATA_PASSWORD")
    )


@router.get("/cookies-status")
def cookies_status() -> dict[str, Any]:
    """Informa si hay una sesión guardada y si todavía autentica.

    Sólo lee: un GET no borra nada. Si la sesión venció se informa
    ``verified: false`` con ``stale: true`` y el operador decide (volver a pegar
    la cookie o usar `POST /api/earthdata/cookies-clear`). ``credenciales`` dice
    si el entorno ya tiene usuario y clave, en cuyo caso la cookie no hace falta.
    """
    credenciales = _hay_credenciales()
    cookies_path = ruta_cookies_earthdata()
    if not cookies_path.is_file():
        return {
            "ok": True,
            "configured": False,
            "credenciales": credenciales,
            "cookies_count": 0,
            "file": str(cookies_path),
        }

    try:
        cookies = json.loads(cookies_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "configured": False,
            "credenciales": credenciales,
            "error": str(exc),
            "file": str(cookies_path),
        }

    if not cookies:
        return {
            "ok": True,
            "configured": False,
            "credenciales": credenciales,
            "cookies_count": 0,
            "file": str(cookies_path),
        }

    estado = _estado_sesion(cookies, timeout=(3, 8))
    if estado is None:
        # Sin red no se puede afirmar que venció: se informa sin veredicto.
        return {
            "ok": True,
            "configured": True,
            "credenciales": credenciales,
            "verified": False,
            "cookies_count": len(cookies),
            "file": str(cookies_path),
        }

    return {
        "ok": True,
        "configured": True,
        "credenciales": credenciales,
        "verified": estado,
        "stale": not estado,
        "cookies_count": len(cookies),
        "getfile": estado,
        "file": str(cookies_path),
    }


@router.post("/cookies-clear")
def cookies_clear() -> dict[str, Any]:
    """Borra el archivo de cookies guardado."""
    cookies_path = ruta_cookies_earthdata()
    if cookies_path.is_file():
        cookies_path.unlink()
    return {"ok": True, "message": "Cookies de Earthdata eliminadas"}
