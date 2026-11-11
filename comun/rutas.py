"""Rutas del proyecto en un solo lugar.

Única fuente de la raíz de datos: todos los demás módulos importan de acá. La raíz de
datos se puede sobreescribir con la variable de entorno ``CLIMATE3D_DATOS``.

Sin la variable el default depende de la plataforma: en Windows se mantiene el valor
histórico ``D:\\Users\\guill\\dataset era5`` —para no cambiarle el flujo a quien ya lo
tenía andando— y en el resto, donde corre el contenedor, se usa ``/data``, que es el
punto de montaje del volumen.

``CLIMATE3D_EXTRA_DIRS`` agrega ubicaciones alternativas separadas por ``os.pathsep``.
"""
from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

# Raíz del repositorio: este archivo vive en comun/, un nivel por debajo.
RAIZ = Path(__file__).resolve().parents[1]

#: Valor histórico: lo que el repo usaba antes de que esto fuera configurable.
RUTA_LEGADA = r"D:\Users\guill\dataset era5"

#: Punto de montaje del volumen en el contenedor (y default fuera de Windows).
RUTA_CONTENEDOR = "/data"

#: Ubicaciones históricas donde se buscaba el NetCDF de ERA5.
_EXTRA_LEGADAS = (Path(r"D:\Users\guill\Desktop"), RAIZ)


def _entorno(entorno: Mapping[str, str] | None) -> Mapping[str, str]:
    return os.environ if entorno is None else entorno


def _plataforma(plataforma: str | None) -> str:
    return os.name if plataforma is None else plataforma


def raiz_datos(
    entorno: Mapping[str, str] | None = None,
    plataforma: str | None = None,
) -> Path:
    """Raíz de datos: ``CLIMATE3D_DATOS`` manda; si no, el default de la plataforma."""
    valor = (_entorno(entorno).get("CLIMATE3D_DATOS") or "").strip()
    if valor:
        return Path(valor)
    return Path(RUTA_LEGADA) if _plataforma(plataforma) == "nt" else Path(RUTA_CONTENEDOR)


def carpetas_extra(
    entorno: Mapping[str, str] | None = None,
    plataforma: str | None = None,
) -> tuple[Path, ...]:
    """Ubicaciones alternativas para `find_data_file`.

    Primero las de ``CLIMATE3D_EXTRA_DIRS`` (separadas por ``os.pathsep``), después las
    históricas de la plataforma y siempre la raíz del repo. Sin repetir: la primera gana.
    """
    crudas = (_entorno(entorno).get("CLIMATE3D_EXTRA_DIRS") or "").split(os.pathsep)
    elegidas = [Path(p).expanduser() for p in crudas if p.strip()]
    if _plataforma(plataforma) == "nt":
        elegidas.extend(_EXTRA_LEGADAS)
    elegidas.append(RAIZ)
    return tuple(dict.fromkeys(elegidas))


# Raíz de datos: los .nc (varios GB) y las salidas viven fuera del repositorio.
DATOS = raiz_datos()
SALIDAS = DATOS / "salidas"

# El NetCDF de ERA5 puede haberse movido fuera de DATOS: se buscan también estas
# ubicaciones (no recursivas) para no caer en datos sintéticos sin darse cuenta.
ERA5_EXTRA_DIRS = carpetas_extra()


def find_data_file(data_dir: Path, explicit: str | None) -> Path | None:
    """Archivo de entrada: el indicado, o el .nc/.grib más grande que se encuentre.

    Busca en `data_dir` en profundidad (por si el .nc vive en una subcarpeta) y
    además en las ubicaciones alternativas de `ERA5_EXTRA_DIRS`.
    """
    if explicit:
        p = Path(explicit)
        if not p.exists():
            raise SystemExit(f"No existe el archivo indicado: {p}")
        return p
    exts = ("*.nc", "*.grib", "*.grib2")
    found = [f for pat in exts for f in data_dir.rglob(pat)]
    for extra in ERA5_EXTRA_DIRS:
        found += [f for pat in exts for f in extra.glob(pat)]
    # Los OR_ABI-* son GOES (otra proyección y otras variables): no son ERA5.
    found = [f for f in found if f.is_file() and not f.name.startswith("OR_ABI")]
    return max(found, key=lambda p: p.stat().st_size) if found else None
