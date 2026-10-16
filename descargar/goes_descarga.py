"""Descarga de archivos GOES-R ABI L2 CMIP desde el bucket público de NOAA S3.

Parte de red extraída de lo que antes era `lib/goes_fetch.py`. Arma la clave S3 a partir
del slot de 10 min (modo 6) y baja sólo lo que falta; reutiliza el .nc local si ya está.

  * `claves_de_la_hora` / `clave_de` — claves S3 de una hora y de una banda.
  * `descargar` — devuelve el .nc local, o lo baja del bucket si falta.

La lectura y el recorte del archivo quedan en `comun/goes_lectura.py` (sin red).
"""
from __future__ import annotations

import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

# `ruta_local` y `PATRON` viven en comun/ (parte local compartida).
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))

from goes_lectura import PATRON, ruta_local  # noqa: E402

# Caché de listados S3 por (satélite, hora): una sola consulta por hora.
_POR_HORA: dict = {}


def claves_de_la_hora(sat: str, t) -> list[str]:
    """Claves S3 de la hora de `t` (una sola consulta por hora y satélite)."""
    hora = t.replace(minute=0, second=0, microsecond=0)
    clave_cache = (sat, hora)
    if clave_cache not in _POR_HORA:
        pref = (f"ABI-L2-CMIPF/{hora.year}/{int(hora.strftime('%j')):03d}/"
                f"{hora.hour:02d}/")
        url = f"https://noaa-goes{sat[1:]}.s3.amazonaws.com/?list-type=2&prefix={pref}"
        xml = urllib.request.urlopen(url, timeout=120).read().decode()
        _POR_HORA[clave_cache] = re.findall(r"<Key>([^<]+)</Key>", xml)
    return _POR_HORA[clave_cache]


def clave_de(sat: str, banda: str, t) -> str:
    """Clave del archivo cuyo escaneo arranca en el slot de 10 min de `t`."""
    for clave in claves_de_la_hora(sat, t):
        m = PATRON.search(clave)
        if not m or m["banda"] != banda or m["sat"] != sat:
            continue
        inicio = datetime.strptime(m["s"][:13], "%Y%j%H%M%S")
        if (inicio.hour, inicio.minute) == (t.hour, t.minute):
            return clave
    raise LookupError(f"Sin archivo {sat} {banda} para {t:%Y-%m-%d %H:%M} UTC")


def descargar(datos_dir, sat: str, clave: str, permitir_red: bool = True,
              minimo_bytes: int = 1_000_000) -> Path:
    """Devuelve el .nc de `clave`: el local si existe, o el recién bajado de S3."""
    datos_dir = Path(datos_dir)
    datos_dir.mkdir(exist_ok=True)
    destino = ruta_local(datos_dir, clave)
    if destino.exists() and destino.stat().st_size > minimo_bytes:
        return destino
    if not permitir_red:
        raise SystemExit(f"Falta {destino.name} y DESCARGAR=False: "
                         "poné DESCARGAR=True para bajarlo de S3.")
    url = f"https://noaa-goes{sat[1:]}.s3.amazonaws.com/{clave}"
    with urllib.request.urlopen(url, timeout=300) as respuesta:
        with open(destino, "wb") as salida:
            while True:
                trozo = respuesta.read(1 << 20)
                if not trozo:
                    break
                salida.write(trozo)
    return destino
