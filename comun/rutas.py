"""Rutas del proyecto en un solo lugar.

Única fuente de las raíces de Climate 3D: todos los demás módulos importan de acá.

    DATOS    datos crudos del pipeline (.nc, .npz, .h5) + SALIDAS (los cuadros)
    MEDIA    artefactos de los jobs de la consola, historial y cachés
    NISAR    los .h5 de NISAR (~1.9 GB cada uno), separados por tamaño

La precedencia es la misma para las tres: **variable de entorno → archivo de
configuración → default de la plataforma**.

- ``CLIMATE3D_DATOS``, ``CLIMATE3D_MEDIA`` y ``CLIMATE3D_NISAR``.
- El archivo de configuración (``%LOCALAPPDATA%\\climate3d\\config.json`` en Windows,
  ``~/.config/climate3d/config.json`` fuera) lo escribe el asistente de arranque con lo
  que el usuario elige. ``CLIMATE3D_CONFIG`` lo puede mover. Sin archivo, todo sigue
  funcionando como siempre.
- En Windows el default es el histórico: ``D:\\Users\\guill\\dataset era5``, con
  ``<DATOS>\\.media`` para los artefactos y ``<DATOS>\\nisar`` para los ``.h5``: una sola
  carpeta para todo. En el contenedor, ``/data`` y ``/data/.media``.

``CLIMATE3D_EXTRA_DIRS`` agrega ubicaciones alternativas separadas por ``os.pathsep``.

La consola del archivo también sirve para el asistente de arranque::

    .venv\\Scripts\\python.exe comun\\rutas.py --show
    .venv\\Scripts\\python.exe comun\\rutas.py --datos "D:\\climate3d" --media "D:\\climate3d\\.media"
"""
from __future__ import annotations

import json
import os
import sys
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

#: Claves válidas del archivo de configuración.
CLAVES_CONFIG = ("datos", "media", "nisar")

#: Nombre del archivo dentro de la carpeta de configuración del usuario.
NOMBRE_CONFIG = "config.json"


def _entorno(entorno: Mapping[str, str] | None) -> Mapping[str, str]:
    return os.environ if entorno is None else entorno


def _plataforma(plataforma: str | None) -> str:
    return os.name if plataforma is None else plataforma


# --- configuración persistida ---------------------------------------------


def ruta_config(entorno: Mapping[str, str] | None = None) -> Path:
    """Dónde vive el archivo de configuración en esta máquina.

    Fuera del repo a propósito: el repo está en OneDrive y viaja entre máquinas, pero
    las raíces son de este equipo. ``CLIMATE3D_CONFIG`` la puede apuntar a otro lado.
    """
    valores = _entorno(entorno)
    elegido = (valores.get("CLIMATE3D_CONFIG") or "").strip()
    if elegido:
        return Path(elegido).expanduser()
    if _plataforma(entorno) == "nt":
        base = (valores.get("LOCALAPPDATA") or "").strip() or (
            valores.get("APPDATA") or ""
        ).strip()
        if base:
            return Path(base) / "climate3d" / NOMBRE_CONFIG
    xdg = (valores.get("XDG_CONFIG_HOME") or "").strip()
    if xdg:
        return Path(xdg) / "climate3d" / NOMBRE_CONFIG
    return Path.home() / ".config" / "climate3d" / NOMBRE_CONFIG


def leer_config(entorno: Mapping[str, str] | None = None) -> dict[str, str]:
    """Configuración guardada. Un archivo ausente, ilegible o roto devuelve ``{}``.

    Nunca levanta: un archivo corrupto no puede dejar la app sin arrancar; se usa el
    default de la plataforma como si no hubiera nada configurado.
    """
    try:
        crudo = json.loads(ruta_config(entorno).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(crudo, dict):
        return {}
    leido: dict[str, str] = {}
    for clave in CLAVES_CONFIG:
        valor = crudo.get(clave)
        if isinstance(valor, str) and valor.strip():
            leido[clave] = valor.strip()
    return leido


def guardar_config(
    datos: str | Path | None = None,
    media: str | Path | None = None,
    nisar: str | Path | None = None,
    entorno: Mapping[str, str] | None = None,
) -> Path:
    """Guarda (o actualiza) las raíces elegidas. Sólo pisa las claves que recibe."""
    destino = ruta_config(entorno)
    actual = leer_config(entorno)
    for clave, valor in (("datos", datos), ("media", media), ("nisar", nisar)):
        if valor is None or not str(valor).strip():
            continue
        actual[clave] = str(Path(str(valor).strip()))
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(actual, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return destino


def _config(
    entorno: Mapping[str, str] | None, config: Mapping[str, str] | None
) -> Mapping[str, str]:
    """La configuración a usar.

    Un ``entorno`` explícito significa resolución **pura**: nada de leer el disco. Es lo
    que usan las pruebas y lo que hace que el mismo código se comporte igual en el
    contenedor. Sin ``entorno`` se resuelve contra la máquina.
    """
    if config is not None:
        return config
    if entorno is not None:
        return {}
    return leer_config()


# --- raíces ---------------------------------------------------------------


def raiz_datos(
    entorno: Mapping[str, str] | None = None,
    plataforma: str | None = None,
    config: Mapping[str, str] | None = None,
) -> Path:
    """Raíz de datos: ``CLIMATE3D_DATOS`` manda; después la configuración guardada."""
    valor = (_entorno(entorno).get("CLIMATE3D_DATOS") or "").strip()
    if valor:
        return Path(valor).expanduser()
    guardado = _config(entorno, config).get("datos")
    if guardado:
        return Path(guardado).expanduser()
    return Path(RUTA_LEGADA) if _plataforma(plataforma) == "nt" else Path(RUTA_CONTENEDOR)


def raiz_media(
    entorno: Mapping[str, str] | None = None,
    config: Mapping[str, str] | None = None,
) -> Path:
    """Raíz de artefactos y cachés: ``CLIMATE3D_MEDIA`` manda.

    Sin variable ni configuración queda debajo de los datos (``<DATOS>/.media``), que es
    el mismo acuerdo que usa el contenedor: una sola carpeta para todos los productos.
    """
    valor = (_entorno(entorno).get("CLIMATE3D_MEDIA") or "").strip()
    if valor:
        return Path(valor).expanduser()
    guardado = _config(entorno, config)
    if guardado.get("media"):
        return Path(guardado["media"]).expanduser()
    return raiz_datos(entorno, None, guardado) / ".media"


def raiz_nisar(
    entorno: Mapping[str, str] | None = None,
    plataforma: str | None = None,
    config: Mapping[str, str] | None = None,
) -> Path:
    """Raíz de los ``.h5`` de NISAR: ``CLIMATE3D_NISAR`` manda.

    Sin variable ni configuración queda adentro de la raíz de datos
    (``<datos>/nisar``): una sola carpeta para descargas, salidas y los ~1.9 GB de
    cada escena. ``CLIMATE3D_NISAR`` existe para quien quiera los ``.h5`` en otro
    disco, que es lo que hacía el default viejo.
    """
    valor = (_entorno(entorno).get("CLIMATE3D_NISAR") or "").strip()
    if valor:
        return Path(valor).expanduser()
    guardado = _config(entorno, config)
    if guardado.get("nisar"):
        return Path(guardado["nisar"]).expanduser()
    return raiz_datos(entorno, plataforma, guardado) / "nisar"


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

# Artefactos de los jobs de la consola: work de cada receta, historial y cachés. Nunca
# dentro del repo: el repo está en OneDrive y la caché de renders crece sin techo.
MEDIA = raiz_media()
CACHE = MEDIA / "cache"

# Raíz de los .h5 NISAR: separada de DATOS por tamaño (ver `raiz_nisar`).
NISAR = raiz_nisar()

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


def resumen(entorno: Mapping[str, str] | None = None) -> dict[str, str]:
    """Raíces efectivas, para que el asistente de arranque las muestre."""
    return {
        "config": str(ruta_config(entorno)),
        "datos": str(raiz_datos(entorno)),
        "salidas": str(raiz_datos(entorno) / "salidas"),
        "media": str(raiz_media(entorno)),
        "nisar": str(raiz_nisar(entorno)),
    }


def _cli(argv: list[str] | None = None) -> int:
    """Lee o escribe la configuración desde un script: lo usa el asistente de arranque."""
    import argparse

    ap = argparse.ArgumentParser(description="Raíces de trabajo de Climate 3D")
    ap.add_argument("--show", action="store_true", help="imprime lo que resuelve hoy")
    ap.add_argument("--datos", help="raíz de datos, salidas incluidas (a guardar)")
    ap.add_argument("--media", help="raíz de artefactos y cachés (a guardar)")
    ap.add_argument("--nisar", help="raíz de los .h5 de NISAR (a guardar)")
    args = ap.parse_args(argv)

    if args.datos or args.media or args.nisar:
        ruta = guardar_config(args.datos, args.media, args.nisar)
        print(f"configuración guardada en {ruta}", file=sys.stderr)

    print(json.dumps(resumen(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
