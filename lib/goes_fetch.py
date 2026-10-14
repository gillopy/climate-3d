"""Acceso a archivos GOES-R ABI L2 CMIP: claves S3, descarga y lectura.

Centraliza lo que antes estaba duplicado en los tres notebooks de animación y en
`scripts/descargar_goes_c04.py`:

  * `claves_de_la_hora` / `clave_de` — arman la clave S3 a partir del slot de 10 min
    (modo 6); no hace falta escribir el nombre del archivo a mano.
  * `ruta_local` / `descargar` — reutilizan el .nc si ya está y bajan solo lo que falta.
  * `cargar` — disco completo (con submuestreo opcional) o recorte a una caja lon/lat,
    listo para `draw_goes_poster`.
  * `cuadros_con_fundido` (streaming, poca RAM) y `fundido_desde_imagenes` (en memoria)
    — fotogramas con fundido para armar el GIF.

Requiere que `lib/` esté en el `sys.path` (importa `poster_goes`).
"""
from __future__ import annotations

import gc
import re
import urllib.request
from datetime import datetime
from pathlib import Path

import numpy as np
import xarray as xr
import cartopy.crs as ccrs
from PIL import Image

from poster_goes import box_indices, caption_lines, to_display

PATRON = re.compile(r"OR_ABI-L2-CMIPF-M6(?P<banda>C\d+)_(?P<sat>G\d+)_s(?P<s>\d{14})_")

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


def ruta_local(datos_dir, clave: str) -> Path:
    """Si el .nc ya está en la carpeta del proyecto, se reutiliza sin copiarlo."""
    datos_dir = Path(datos_dir)
    nombre = clave.rsplit("/", 1)[-1]
    for candidato in (Path(nombre), datos_dir / nombre):
        if candidato.exists():
            return candidato
    return datos_dir / nombre


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


def cargar(nc, tope_px=None, caja=None, escena="FULL DISK"):
    """Campo listo para dibujar: `(campo, x, y, proj, unidad, rotulos)`.

    `tope_px` submuestrea el disco (None = resolución nativa). `caja` recorta a una
    caja lon/lat `(oeste, este, sur, norte)`. `escena` es la etiqueta del póster.
    """
    with xr.open_dataset(nc) as ds:
        cmi = ds["CMI"]
        gp = ds["goes_imager_projection"].attrs
        h = float(gp["perspective_point_height"])
        paso = max(1, int(np.ceil(max(cmi.shape) / tope_px))) if tope_px else 1
        x = ds["x"].values[::paso] * h
        y = ds["y"].values[::paso] * h
        proj = ccrs.Geostationary(
            central_longitude=float(gp["longitude_of_projection_origin"]),
            satellite_height=h, sweep_axis=str(gp.get("sweep_angle_axis", "x")))
        if caja is not None:
            i0, i1, j0, j1 = box_indices(proj, x, y, caja)
            crudo = np.asarray(cmi.values[j0:j1, i0:i1], dtype=np.float64)
            campo, unidad, tipo = to_display(crudo, cmi)
            rotulos = caption_lines(ds, cmi, tipo, escena)
            return campo, x[i0:i1], y[j0:j1], proj, unidad, rotulos
        crudo = np.asarray(cmi.values[::paso, ::paso], dtype=np.float64)
        campo, unidad, tipo = to_display(crudo, cmi)
        rotulos = caption_lines(ds, cmi, tipo, escena)
        return campo, x, y, proj, unidad, rotulos


def _fundido(a0: np.ndarray, a1: np.ndarray, pasos: int):
    """Imágenes RGB intermedias entre dos cuadros (alfa creciente)."""
    for k in range(1, pasos + 1):
        alfa = k / (pasos + 1)
        yield Image.fromarray(((1 - alfa) * a0 + alfa * a1).astype(np.uint8))


def cuadros_con_fundido(paths, pasos, ms_cuadro, ms_fundido):
    """Genera `(imagen P, duración_ms)` leyendo de a dos cuadros por vez (poca RAM)."""
    prev = Image.open(paths[0]).convert("RGB")
    yield prev.convert("P", palette=Image.ADAPTIVE), ms_cuadro
    for q in paths[1:]:
        cur = Image.open(q).convert("RGB")
        if pasos:
            a0 = np.asarray(prev, dtype=np.float32)
            a1 = np.asarray(cur, dtype=np.float32)
            for mezcla in _fundido(a0, a1, pasos):
                yield mezcla.convert("P", palette=Image.ADAPTIVE), ms_fundido
        yield cur.convert("P", palette=Image.ADAPTIVE), ms_cuadro
        del prev
        prev = cur
        gc.collect()


def fundido_desde_imagenes(cuadros, pasos, ms_cuadro, ms_fundido):
    """Pares `(imagen, duración_ms)`: cuadros reales + intermedios interpolados.

    Variante en memoria para animaciones cortas (el disco completo usa la de
    streaming, `cuadros_con_fundido`).
    """
    salida = []
    for i, img in enumerate(cuadros):
        salida.append((img, ms_cuadro))
        if pasos and i + 1 < len(cuadros):
            a0 = np.asarray(img, dtype=np.float32)
            a1 = np.asarray(cuadros[i + 1], dtype=np.float32)
            salida += [(m, ms_fundido) for m in _fundido(a0, a1, pasos)]
    return salida
