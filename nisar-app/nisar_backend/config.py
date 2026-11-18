"""Rutas y entorno del backend NISAR en un solo lugar.

La app vive en ``nisar-app/`` pero no duplica el pipeline: los scripts de
``descargar/``, ``comun/`` y ``prototipos/`` se siguen ejecutando desde la raiz
del repo. Lo propio de esta app son sus raices de estado (media de los jobs y
cache de browse), separadas de las de la app general.

Variables de entorno:

- ``CLIMATE3D_PYTHON``: interprete que corre los scripts (default: ``.venv`` del repo).
- ``CLIMATE3D_NISAR``: raiz de los ``.h5`` (default: ``E:\\nisar`` en Windows).
- ``NISAR_MEDIA``: raiz de artefactos de jobs (default: ``nisar-app/var/media``).
"""
from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

RAIZ_BACKEND = Path(__file__).resolve().parent
RAIZ_APP = RAIZ_BACKEND.parent
RAIZ_REPO = RAIZ_APP.parent

#: Artefactos de los jobs (imagenes, JSON, GeoTIFF) y cache de browse.
MEDIA = Path(os.environ.get("NISAR_MEDIA") or RAIZ_APP / "var" / "media")
CACHE = Path(os.environ.get("NISAR_BROWSE_CACHE") or RAIZ_APP / "var" / "nisar" / "cache")

#: Contorno del pais que dibujan los productos y el mapa.
PARAGUAY = RAIZ_REPO / "datos" / "paraguay_gadm.json"

#: Credenciales locales de esta app. El repo tiene su propio ``.env``.
ENV_APP = RAIZ_APP / ".env"
ENV_REPO = RAIZ_REPO / ".env"

#: Donde puede estar el interprete del pipeline dentro del repo. En Windows el
#: venv deja ``Scripts/python.exe``; en POSIX, ``bin/python``.
_VENV_RELATIVOS = ((".venv", "Scripts", "python.exe"), (".venv", "bin", "python"))


def _python_repo(entorno: Mapping[str, str] | None = None) -> Path:
    """Interprete que corre los scripts del pipeline.

    ``CLIMATE3D_PYTHON`` manda: es lo que usa el contenedor, donde el venv vive en
    ``/app/.venv`` y no tiene sentido adivinar la distribucion de carpetas.
    """
    valor = ((os.environ if entorno is None else entorno).get("CLIMATE3D_PYTHON") or "").strip()
    if valor:
        return Path(valor)
    for relativo in _VENV_RELATIVOS:
        candidato = RAIZ_REPO.joinpath(*relativo)
        if candidato.is_file():
            return candidato
    return RAIZ_REPO.joinpath(*_VENV_RELATIVOS[0 if os.name == "nt" else 1])


PYTHON_REPO = _python_repo()


def python_repo() -> Path:
    return PYTHON_REPO


def repo_listo() -> bool:
    return PYTHON_REPO.is_file()


def leer_env(archivo: Path) -> dict[str, str]:
    """Lee un ``.env`` sin imprimir valores. Lineas vacias y comentarios se saltean."""
    valores: dict[str, str] = {}
    try:
        for linea in archivo.read_text(encoding="utf-8-sig").splitlines():
            limpia = linea.strip()
            if not limpia or limpia.startswith("#") or "=" not in limpia:
                continue
            clave, valor = limpia.split("=", 1)
            valores[clave.strip()] = valor.strip().strip('"').strip("'")
    except OSError:
        pass
    return valores


def variables_env() -> dict[str, str]:
    """Variables del ``.env``: primero el del repo y despues el de la app (gana la app)."""
    valores = leer_env(ENV_REPO)
    valores.update(leer_env(ENV_APP))
    return valores


def earthdata_configurada(entorno: Mapping[str, str] | None = None) -> bool:
    """True si hay usuario de Earthdata en el entorno o en alguno de los ``.env``."""
    actual = os.environ if entorno is None else entorno
    if (actual.get("EARTHDATA_USER") or "").strip():
        return True
    return bool((variables_env().get("EARTHDATA_USER") or "").strip())


def entorno_pipeline() -> dict[str, str]:
    """Entorno de un subproceso del pipeline.

    El proceso manda (login explicito); lo que falte se completa con el ``.env``
    de la app y, despues, con el del repo. Asi el script de descarga encuentra
    las credenciales sin que esta app las reimplemente.
    """
    entorno = os.environ.copy()
    entorno.update(
        PYTHONUTF8="1",
        PYTHONIOENCODING="utf-8",
        PYTHONUNBUFFERED="1",
    )
    # La cache de Sentinel-2 vive con los artefactos: la misma caja y la misma
    # fecha no se vuelven a bajar entre corridas. NISAR_S2_CACHE explicito manda.
    entorno.setdefault("NISAR_S2_CACHE", str(MEDIA / "cache" / "s2"))
    for clave, valor in variables_env().items():
        entorno.setdefault(clave, valor)
    return entorno
