"""Rutas del proyecto en un solo lugar.

Única fuente de la raíz de datos: todos los demás módulos importan de acá. La raíz de
datos se puede sobreescribir con la variable de entorno ``CLIMATE3D_DATOS``; si no está
definida, se usa el valor histórico ``D:\\Users\\guill\\dataset era5``.
"""
from __future__ import annotations

import os
from pathlib import Path

# Raíz del repositorio: este archivo vive en comun/, un nivel por debajo.
RAIZ = Path(__file__).resolve().parents[1]

# Raíz de datos: los .nc (varios GB) y las salidas viven fuera del repositorio.
DATOS = Path(os.environ.get("CLIMATE3D_DATOS", r"D:\Users\guill\dataset era5"))
SALIDAS = DATOS / "salidas"

# El NetCDF de ERA5 puede haberse movido fuera de DATOS: se buscan también estas
# ubicaciones (no recursivas) para no caer en datos sintéticos sin darse cuenta.
ERA5_EXTRA_DIRS = (
    Path(r"D:\Users\guill\Desktop"),
    RAIZ,
)


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
