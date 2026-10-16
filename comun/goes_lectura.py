"""Lectura local de archivos GOES-R ABI L2 CMIP (sin red).

Parte local de lo que antes era `lib/goes_fetch.py`; la descarga (que sí toca la red)
vive aparte, en `descargar/goes_descarga.py`.

  * `PATRON` — regex del nombre de archivo ABI (banda, satélite, inicio de escaneo).
  * `ruta_local` — reutiliza el .nc si ya está en la carpeta, sin copiarlo.
  * `cargar` — disco completo (con submuestreo opcional) o recorte a una caja lon/lat,
    listo para `draw_goes_poster`.
  * `cuadros_con_fundido` (streaming, poca RAM) y `fundido_desde_imagenes` (en memoria)
    — fotogramas con fundido para armar el GIF.

Requiere `prototipos/` en el `sys.path` (importa de `poster_goes`).
"""
from __future__ import annotations

import gc
import re
import sys
from pathlib import Path

# `cargar` reutiliza los rótulos y el render del póster GOES (prototipos/).
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "prototipos"))

import numpy as np  # noqa: E402
import xarray as xr  # noqa: E402
import cartopy.crs as ccrs  # noqa: E402
from PIL import Image  # noqa: E402

from poster_goes import box_indices, caption_lines, time_label, to_display  # noqa: E402

PATRON = re.compile(r"OR_ABI-L2-CMIPF-M6(?P<banda>C\d+)_(?P<sat>G\d+)_s(?P<s>\d{14})_")


def ruta_local(datos_dir, clave: str) -> Path:
    """Si el .nc ya está en la carpeta del proyecto, se reutiliza sin copiarlo."""
    datos_dir = Path(datos_dir)
    nombre = clave.rsplit("/", 1)[-1]
    for candidato in (Path(nombre), datos_dir / nombre):
        if candidato.exists():
            return candidato
    return datos_dir / nombre


def cargar(nc, tope_px=None, caja=None, escena="FULL DISK"):
    """Campo listo para dibujar: `(campo, x, y, proj, unidad, rotulos)`.

    `tope_px` submuestrea el disco (None = resolución nativa). `caja` recorta a una
    caja lon/lat `(oeste, este, sur, norte)`. `escena` es la etiqueta del póster.
    `rotulos` es `(titulo, subtitulo, fuente, datos, tiempo)`: el último es la
    fecha/hora del cuadro para el rótulo grande (`time_line` de `draw_goes_poster`).
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
            crudo = np.asarray(cmi[j0:j1, i0:i1].values, dtype=np.float64)
            campo, unidad, tipo = to_display(crudo, cmi)
            rotulos = (*caption_lines(ds, cmi, tipo, escena), time_label(ds))
            return campo, x[i0:i1], y[j0:j1], proj, unidad, rotulos
        crudo = np.asarray(cmi[::paso, ::paso].values, dtype=np.float64)
        campo, unidad, tipo = to_display(crudo, cmi)
        rotulos = (*caption_lines(ds, cmi, tipo, escena), time_label(ds))
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
