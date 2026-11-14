"""Poster of the GOES-R ABI L2 Land Surface Temperature (LST 2 km full disk).

The ABI L2 LST product is **hourly** (one granule per hour, ~10 minutes of scan).
The `.nc` carries a packed `LST` variable (`scale_factor=0.0025`,
`add_offset=190`, so xarray returns Kelvin already unpacked) and a `DQF` quality
flag. A pixel is shown only when `LST` is not NaN and `DQF != 3` (3 = no
retrieval): the product only retrieves clear land, so open ocean and cloudy
pixels stay transparent, like the reference image.

The design is the one from `poster_goes_truecolor.py` (white page, inscribed
Orthographic globe, thin halo, no graticule), with a product-specific cold-to-warm
ramp and a two-scale legend: Fahrenheit above the bar, Celsius below it.

Two controls close the holes the retrieval leaves, without inventing weather:

  * `--fondo base` paints the Blue Marble (ocean + shaded relief) under the data,
    so "no retrieval" reads as terrain instead of a black hole. The base is
    fetched once from GIBS and cached, then sampled with the same lon/lat grid
    the data uses, so it costs nothing per animation frame.
  * `--relleno N` grows the field up to N output-grid pixels into the gaps with
    the mean of its valid neighbours. At 2 km per pixel, 2 px is a 4 km bridge:
    enough to close the salt-and-pepper texture, not enough to fake a cloud deck.

`--compuesto H` averages the H hours ending at the frame (poster only: it would
flatten the diurnal cycle if used across an hourly animation).

Reused from shared code (never modified here):

  * `poster_goes_truecolor` — `_orto_franja`, `_alfa`, `FILAS`, `dibujar`, `WHITE`.
  * `poster_goes_banda` — `_muestrear_banda`, `CORTE_PLANETA`.
  * `poster_goes_realista` — `radio_visible`.

`fecha_de` / `time_label_nc` from `poster_goes_realista` are not reused: they
parse the CMIP name with `goes_lectura.PATRON`, which does not match the
`OR_ABI-L2-LST2KMF-...` granule. This module parses the LST scan stamp itself and
formats the same `DD MON YYYY · HH:MM UTC-3` label.

Usage (from the project root):

    .venv\\Scripts\\python.exe prototipos\\poster_goes_lst.py
    .venv\\Scripts\\python.exe prototipos\\poster_goes_lst.py --desde 2026-11-13T22:00 --n 1
    .venv\\Scripts\\python.exe prototipos\\poster_goes_lst.py --px 1400 --out lst.png
    .venv\\Scripts\\python.exe prototipos\\poster_goes_lst.py --help   # no network
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
sys.path.insert(0, str(RAIZ / "prototipos"))

import poster_goes_truecolor as tc  # noqa: E402
from poster_goes_banda import CORTE_PLANETA, _muestrear_banda  # noqa: E402
from poster_goes_realista import _lineas_geojson, radio_visible  # noqa: E402
from rutas import DATOS, SALIDAS  # noqa: E402

SAT = "G19"
PX = 2712
TOPE = 5424                       # native LST 2 km grid: 5424 x 5424
CENTRO = (-75.2, 0.0)
VMIN, VMAX = -53.0, 67.0          # degrees C, the reference image scale

#: Base map under the data: ocean + shaded relief, a static GIBS layer.
CAPA_FONDO = "BlueMarble_ShadedRelief_Bathymetry"
GIBS = "https://wvs.earthdata.nasa.gov/api/v1/snapshot"
CACHE_FONDO = SALIDAS / "_fondo_lst"
ANCHO_FONDO = 4096               # 4096x2048 is enough for a 2712 px globe

#: Product ramp, cold to warm, in the exact order the spec fixes.
PALETA = (
    (0.00, "#2b2b9e"),
    (0.10, "#2f6fd0"),
    (0.20, "#37c8e8"),
    (0.32, "#5fd48a"),
    (0.44, "#b7e05a"),
    (0.54, "#f2e04e"),
    (0.66, "#f5a53c"),
    (0.78, "#ec6a2f"),
    (0.88, "#d4342a"),
    (1.00, "#8f1212"),
)

#: LST scan stamp: `s20263172200207` -> 2026, day 317, 22:00:20.7 UTC.
_PATRON_LST = re.compile(r"_s(\d{4})(\d{3})(\d{2})(\d{2})(\d{2})")

_CMAP = None


def carpeta(sat: str = SAT) -> Path:
    """Data folder of the product: ``goes_lst_<sat>`` under ``comun.rutas.DATOS``."""
    return DATOS / f"goes_lst_{sat.lower()}"


def fecha_de(nc: Path) -> datetime | None:
    """Scan hour (UTC) parsed from the LST granule name, or None if it is not one."""
    match = _PATRON_LST.search(Path(nc).name)
    if not match:
        return None
    anio, dia, hora, minuto = (int(g) for g in match.groups()[:4])
    return datetime(anio, 1, 1) + timedelta(days=dia - 1, hours=hora, minutes=minuto)


def time_label_nc(nc: Path) -> str:
    """Slot label in UTC-3, the same format as the other posters."""
    meses = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN",
             "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
    t = (fecha_de(nc) or datetime.fromtimestamp(Path(nc).stat().st_mtime))
    t = t - timedelta(hours=3)
    return f"{t.day:02d} {meses[t.month - 1]} {t.year} \u00b7 {t:%H:%M} UTC-3"


def slots(sat: str, desde: datetime | None, n: int, paso: int,
          ultimos: int = 0) -> list[tuple[datetime, Path]]:
    """LST granules on disk, hourly.

    - `ultimos > 0`: the N newest, ending at the newest one on disk.
    - `desde`: the series starting at that instant.
    - neither: the last frame.
    """
    encontrados: dict[datetime, Path] = {}
    for archivo in carpeta(sat).glob("*.nc"):
        instante = fecha_de(archivo)
        if instante is not None:
            encontrados[instante] = archivo
    if not encontrados:
        raise SystemExit(
            f"No LST .nc for {sat} in {carpeta(sat)}. "
            "Download them with descargar/descargar_goes_lst.py."
        )
    if ultimos > 0:
        n = ultimos
        t0 = max(encontrados) - timedelta(minutes=paso * (ultimos - 1))
    else:
        t0 = desde or max(encontrados)
    lista: list[tuple[datetime, Path]] = []
    for i in range(n):
        instante = t0 + timedelta(minutes=paso * i)
        if instante in encontrados:
            lista.append((instante, encontrados[instante]))
    if not lista:
        raise SystemExit(f"No .nc for any requested slot from {t0:%Y-%m-%d %H:%M} UTC.")
    return lista


def _lut() -> np.ndarray:
    """Dip the product ramp into a lookup table (nearest index per pixel)."""
    global _CMAP
    if _CMAP is None:
        from matplotlib.colors import LinearSegmentedColormap

        _CMAP = LinearSegmentedColormap.from_list("goes_lst", PALETA, N=512)
    n = int(getattr(_CMAP, "N", 256))
    return (np.asarray(_CMAP(np.linspace(0.0, 1.0, n)))[:, :3] * 255.0).astype(np.uint8)


def _campo_lst(nc: Path, tope: int):
    """LST in degrees C plus its scan grid; NaN where there is no good retrieval.

    xarray unpacks `scale_factor` / `add_offset` and turns `_FillValue` into NaN
    on open. A pixel is valid only when `LST` is finite and `DQF != 3`.
    """
    import xarray as xr

    with xr.open_dataset(nc, engine="h5netcdf") as ds:
        gp = ds["goes_imager_projection"].attrs
        h = float(gp["perspective_point_height"])
        lon0 = float(gp["longitude_of_projection_origin"])
        alto, ancho = ds["LST"].shape
        paso = max(1, int(np.ceil(max(alto, ancho) / tope))) if tope else 1
        x = ds["x"].values[::paso] * h
        y = ds["y"].values[::paso] * h
        lst = np.asarray(ds["LST"].values[::paso, ::paso], dtype=np.float32)
        dqf = np.asarray(ds["DQF"].values[::paso, ::paso], dtype=np.float32)

    valido = np.isfinite(lst) & (dqf != 3)
    campo = np.where(valido, lst - 273.15, np.nan).astype(np.float32)
    del lst, dqf, valido
    return campo, x, y, h, lon0


def _leer_base(ancho: int, capa: str = CAPA_FONDO) -> np.ndarray:
    """Blue Marble plate carree (2:1), downloaded once and cached in SALIDAS."""
    destino = CACHE_FONDO / f"{capa}_{ancho}.jpg"
    if not (destino.exists() and destino.stat().st_size > 50_000):
        destino.parent.mkdir(parents=True, exist_ok=True)
        url = (f"{GIBS}?REQUEST=GetSnapshot&TIME=2020-01-01T00:00:00Z"
               "&BBOX=-90,-180,90,180&CRS=EPSG:4326"
               f"&LAYERS={capa}&FORMAT=image/jpeg"
               f"&WIDTH={ancho}&HEIGHT={ancho // 2}")
        with urllib.request.urlopen(url, timeout=180) as respuesta:
            datos = respuesta.read()
        if len(datos) < 50_000:
            raise RuntimeError(
                f"GIBS devolvio {len(datos)} B para el fondo: no es una imagen")
        parcial = destino.with_suffix(".jpg.parcial")
        parcial.write_bytes(datos)
        parcial.replace(destino)
    with Image.open(destino) as imagen:
        return np.asarray(imagen.convert("RGB"))


def _muestrear_base(base: np.ndarray, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """Bilinear sample of the plate carree base at the globe lon/lat grid."""
    alto, ancho = base.shape[:2]
    lon = np.where(np.isfinite(lon), ((np.asarray(lon, np.float64) + 180.0) % 360.0) - 180.0,
                   np.nan)
    u = (lon + 180.0) / 360.0 * (ancho - 1)
    v = (90.0 - np.asarray(lat, np.float64)) / 180.0 * (alto - 1)
    # Off-globe pixels land on the frame edge: the disk alpha hides them anyway.
    u = np.clip(np.nan_to_num(u, nan=0.0), 0.0, ancho - 1.000001)
    v = np.clip(np.nan_to_num(v, nan=0.0), 0.0, alto - 1.000001)
    x0 = u.astype(np.int32)
    y0 = v.astype(np.int32)
    x1 = np.minimum(x0 + 1, ancho - 1)
    y1 = np.minimum(y0 + 1, alto - 1)
    fx = (u - x0)[..., None]
    fy = (v - y0)[..., None]
    b = base.astype(np.float32)
    arriba = b[y0, x0] * (1.0 - fx) + b[y0, x1] * fx
    abajo = b[y1, x0] * (1.0 - fx) + b[y1, x1] * fx
    return (arriba * (1.0 - fy) + abajo * fy).astype(np.uint8)


def _fondo_globo(nc: Path, sat: str, px: int, centro: tuple[float, float],
                 recorte: float, ancho: int, capa: str = CAPA_FONDO) -> np.ndarray:
    """Blue Marble painted on the same orthographic disk the data uses.

    The geometry is the one already in the output space (`_orto_franja`), so the
    base lines up with the field pixel for pixel and no re-projection runs per
    frame: the result is cached as a PNG for the whole animation.
    """
    llave = (f"fondo_{sat}_{capa}_{px}_{centro[0]:g}_{centro[1]:g}"
             f"_{recorte:g}_{ancho}.png")
    cacheado = CACHE_FONDO / llave
    if cacheado.exists():
        with Image.open(cacheado) as imagen:
            return np.asarray(imagen.convert("RGB"))

    base = _leer_base(ancho, capa)
    escala, _h, _lon0 = radio_visible(nc, centro, recorte)
    salida = np.zeros((px, px, 3), np.uint8)
    for f0 in range(0, px, tc.FILAS):
        f1 = min(f0 + tc.FILAS, px)
        lon, lat, _rho, _dentro = tc._orto_franja(px, escala, centro, f0, f1)
        salida[f0:f1] = _muestrear_base(base, lon, lat)
    del base

    cacheado.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(salida).save(cacheado)
    return salida


def _rellenar(campo: np.ndarray, pasadas: int) -> np.ndarray:
    """Grow the field up to `pasadas` grid pixels into the gaps.

    Each pass fills an empty pixel with the mean of its valid 8-neighbours, so
    the bridge follows the surrounding temperature instead of a flat colour. It
    never touches ocean: that has no neighbour with data, ever.
    """
    if pasadas <= 0:
        return campo
    salida = campo.copy()
    alto, ancho = salida.shape
    for _ in range(pasadas):
        vacio = ~np.isfinite(salida)
        if not vacio.any():
            break
        borde = np.pad(salida, 1, constant_values=np.nan)
        suma = np.zeros_like(salida)
        cuenta = np.zeros(salida.shape, np.float32)
        for dy in range(3):
            for dx in range(3):
                if dy == 1 and dx == 1:
                    continue
                vecino = borde[dy:dy + alto, dx:dx + ancho]
                valido = np.isfinite(vecino)
                suma += np.where(valido, vecino, 0.0)
                cuenta += valido
        relleno = vacio & (cuenta > 0)
        salida[relleno] = suma[relleno] / cuenta[relleno]
    return salida


def _campo_compuesto(nc: Path, tope: int, horas: int, sat: str):
    """Mean LST of the `horas` hours ending at this granule (1 = the granule).

    Returns `(campo, x, y, h, lon0, usadas)`. Only the hours already on disk take
    part: a missing granule just narrows the window instead of killing the
    render, and one available hour behaves exactly like `--compuesto 1`.
    """
    if horas <= 1:
        campo, x, y, h, lon0 = _campo_lst(nc, tope)
        return campo, x, y, h, lon0, 1
    instante = fecha_de(nc)
    if instante is None:
        campo, x, y, h, lon0 = _campo_lst(nc, tope)
        return campo, x, y, h, lon0, 1
    por_hora = {fecha_de(f): f for f in carpeta(sat).glob("*.nc") if fecha_de(f)}
    campos = []
    x = y = h = lon0 = None
    for i in range(horas):
        archivo = por_hora.get(instante - timedelta(hours=horas - 1 - i))
        if archivo is None:
            continue
        campo, x, y, h, lon0 = _campo_lst(archivo, tope)
        campos.append(campo)
    if not campos:
        campo, x, y, h, lon0 = _campo_lst(nc, tope)
        return campo, x, y, h, lon0, 1
    if len(campos) == 1:
        return campos[0], x, y, h, lon0, 1
    with np.errstate(invalid="ignore"):
        media = np.nanmean(np.stack(campos), axis=0).astype(np.float32)
    usadas = len(campos)
    del campos
    return media, x, y, h, lon0, usadas


def _componer_plano(nc: Path, args) -> tuple[np.ndarray, dict]:
    """Square map of a lon/lat box: the Paraguay capture, like the other products.

    No globe and no disk alpha: every pixel of the frame is a lon/lat pair inside
    `--bbox`, so the result is a plain square map with the base map under the
    gaps, exactly like the precipitation snapshot.
    """
    horas = int(getattr(args, "compuesto", 1) or 1)
    campo, x, y, h, lon0, usadas = _campo_compuesto(nc, args.tope, horas, args.sat)
    relleno = int(getattr(args, "relleno", 0) or 0)
    if relleno > 0:
        campo = _rellenar(campo, relleno)

    o, s, e, n = (float(v) for v in args.bbox)
    o, e = min(o, e), max(o, e)
    s, n = min(s, n), max(s, n)
    px = int(args.px)
    alto = max(1, int(round(px * (n - s) / (e - o)))) if e > o else px
    # Caja casi cuadrada: se fuerza el cuadrado, como el snapshot de lluvia.
    if abs(alto - px) <= px * 0.12:
        alto = px

    lut = _lut()
    base = None
    if getattr(args, "mapa", "base") == "base":
        base = _leer_base(int(getattr(args, "fondo_ancho", ANCHO_FONDO)),
                          getattr(args, "capa_fondo", CAPA_FONDO))

    lon = np.linspace(o, e, px)
    lat = np.linspace(n, s, alto)
    rgb = np.zeros((alto, px, 3), np.uint8)
    for f0 in range(0, alto, tc.FILAS):
        f1 = min(f0 + tc.FILAS, alto)
        lon2d, lat2d = np.meshgrid(lon, lat[f0:f1])
        valores = _muestrear_banda(campo, x, y, lon0, h, lon2d, lat2d)
        normalizado = np.clip((valores - args.vmin) / (args.vmax - args.vmin), 0.0, 1.0)
        normalizado = np.nan_to_num(normalizado, nan=0.0)
        indice = (normalizado * (len(lut) - 1)).astype(np.uint16)
        bloque = lut[indice]
        vacio = ~np.isfinite(valores)
        if base is None:
            bloque[vacio] = 0
        else:
            bloque[vacio] = _muestrear_base(base, lon2d, lat2d)[vacio]
        rgb[f0:f1] = bloque

    finitos = np.isfinite(campo)
    datos = campo[finitos]
    stats = {
        "px": px, "alto": alto,
        "cobertura": float(datos.size) / float(campo.size) if campo.size else 0.0,
        "cubiertos": float(finitos.sum()) / float(campo.size) if campo.size else 0.0,
        "relleno": relleno, "compuesto": usadas,
        "fondo": getattr(args, "mapa", "base"),
        "min": float(datos.min()) if datos.size else float("nan"),
        "mean": float(datos.mean()) if datos.size else float("nan"),
        "max": float(datos.max()) if datos.size else float("nan"),
    }
    del datos, finitos
    return rgb, stats


def _guardar_plano(rgb: np.ndarray, args, destino: Path) -> None:
    """Write the square map; the outlined border goes on top when asked."""
    imagen = Image.fromarray(rgb)
    alto, ancho = rgb.shape[:2]
    if args.borde:
        anillos = _lineas_geojson(args.borde)
        if anillos:
            o, s, e, n = (float(v) for v in args.bbox)
            o, e = min(o, e), max(o, e)
            s, n = min(s, n), max(s, n)
            lapiz = ImageDraw.Draw(imagen)
            grosor = max(1, ancho // 900)
            for anillo in anillos:
                puntos = [((lon - o) / (e - o) * (ancho - 1),
                           (n - lat) / (n - s) * (alto - 1))
                          for lon, lat in anillo]
                if len(puntos) >= 3:
                    lapiz.line(puntos + [puntos[0]], fill=(18, 22, 26), width=grosor)
    destino.parent.mkdir(parents=True, exist_ok=True)
    parcial = destino.with_suffix(".png.parcial")
    imagen.save(parcial, format="png")
    parcial.replace(destino)


def componer_lst(nc: Path, args) -> tuple[np.ndarray, float, dict]:
    """LST granule -> RGBA of the Orthographic globe, with the true color geometry."""
    horas = int(getattr(args, "compuesto", 1) or 1)
    campo, x, y, h, lon0, usadas = _campo_compuesto(nc, args.tope, horas, args.sat)

    finitos = np.isfinite(campo)
    datos = campo[finitos]
    if datos.size:
        estadisticas = {
            "min": float(datos.min()),
            "mean": float(datos.mean()),
            "max": float(datos.max()),
        }
    else:
        estadisticas = {"min": float("nan"), "mean": float("nan"), "max": float("nan")}
    cobertura = float(datos.size) / float(campo.size) if campo.size else 0.0
    del datos, finitos

    relleno = int(getattr(args, "relleno", 0) or 0)
    if relleno > 0:
        campo = _rellenar(campo, relleno)
    cubiertos = float(np.isfinite(campo).sum()) / float(campo.size) if campo.size else 0.0

    fondo = None
    if getattr(args, "mapa", "base") == "base":
        fondo = _fondo_globo(nc, args.sat, args.px, tuple(args.centro),
                             args.recorte,
                             int(getattr(args, "fondo_ancho", ANCHO_FONDO)),
                             getattr(args, "capa_fondo", CAPA_FONDO))

    escala, _h, _lon0 = radio_visible(nc, tuple(args.centro), args.recorte)
    lut = _lut()
    px = args.px
    centro = tuple(args.centro)

    rgb = np.zeros((px, px, 3), dtype=np.uint8)
    alfa = np.zeros((px, px), dtype=np.uint8)
    validos = 0

    for f0 in range(0, px, tc.FILAS):
        f1 = min(f0 + tc.FILAS, px)
        lon, lat, rho, dentro = tc._orto_franja(px, escala, centro, f0, f1)
        valores = _muestrear_banda(campo, x, y, lon0, h, lon, lat)
        a = tc._alfa(rho, px, escala) * dentro
        # The planet edge, not the frame: same analytic 1.5 px ramp as the RGBs.
        a = a * tc._alfa(rho, px, 1.0 / CORTE_PLANETA)

        normalizado = np.clip((valores - args.vmin) / (args.vmax - args.vmin), 0.0, 1.0)
        # NaN (no retrieval) must not reach the integer cast: quiet it first.
        normalizado = np.nan_to_num(normalizado, nan=0.0)
        n = len(lut)
        indice = (normalizado * (n - 1)).astype(np.uint16 if n > 256 else np.uint8)
        bloque = lut[indice]
        vacio = ~np.isfinite(valores)
        if fondo is None:
            bloque[vacio] = 0
        else:
            bloque[vacio] = fondo[f0:f1][vacio]

        rgb[f0:f1] = bloque
        alfa[f0:f1] = (a * 255.0).astype(np.uint8)
        validos += int(np.count_nonzero(np.isfinite(valores) & (a > 0)))
        print(f"  strip {f1:5d}/{px}", flush=True)

    # No bright rim: bilinear display instead of lanczos (no overshoot).
    args.interp = "bilinear"
    stats = {"px": px, "validos": validos, "cobertura": cobertura,
             "cubiertos": cubiertos, "relleno": relleno, "compuesto": usadas,
             "fondo": getattr(args, "mapa", "base"), **estadisticas}
    return np.dstack([rgb, alfa]), escala, stats


def _numero(v: float) -> str:
    """Number with a typographic minus, like the other poster legends."""
    return f"{v:g}".replace("-", "\u2212")


def _etiqueta_tiempo(nc: Path, horas: int) -> str:
    """Slot label; with a temporal composite the window is spelled out."""
    if horas <= 1:
        return time_label_nc(nc)
    fin = fecha_de(nc)
    if fin is None:
        return time_label_nc(nc)
    inicio = fin - timedelta(hours=horas - 1) - timedelta(hours=3)
    final = fin - timedelta(hours=3)
    fecha = time_label_nc(nc).split(" \u00b7 ")[0]
    return f"{fecha} \u00b7 COMPUESTO {inicio:%H:%M}\u2013{final:%H:%M} UTC-3"


def _tinta_oscura() -> None:
    """Black page with light ink: the house style of the other GOES snapshots.

    `poster_goes_truecolor.dibujar` reads `WHITE` / `INK` / `INK_SOFT` from its
    own module at call time, so inverting those globals here is the same switch
    the color-real poster uses for `--fondo oscuro`.
    """
    tc.WHITE = "#000000"
    tc.INK = "#eef2f5"
    tc.INK_SOFT = "#9aa0a6"


def _leyenda(fig, args) -> None:
    """Two-scale horizontal legend: Fahrenheit above, Celsius below the bar."""
    if args.limpio:
        return
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize

    _lut()  # make sure the product ramp is built before the legend samples it
    cax = fig.add_axes([0.105, 0.072, 0.790, 0.011], zorder=9)
    sm = plt.cm.ScalarMappable(norm=Normalize(args.vmin, args.vmax), cmap=_CMAP)
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=cax, orientation="horizontal")
    cbar.outline.set_visible(False)

    ticks = []
    valor = args.vmin
    while valor <= args.vmax + 1e-9:
        ticks.append(valor)
        valor += 20.0
    cbar.set_ticks(ticks)
    celsius = [
        f"{_numero(t)} \u00b0C" if i == len(ticks) - 1 else _numero(t)
        for i, t in enumerate(ticks)
    ]
    cbar.set_ticklabels(celsius)
    cbar.ax.tick_params(length=0, labelsize=8.2, colors=tc.INK_SOFT, pad=3)
    for etiqueta in cbar.ax.get_xticklabels():
        etiqueta.set_fontfamily("Segoe UI")

    for i, t in enumerate(ticks):
        fahrenheit = int(np.floor(t * 9.0 / 5.0 + 32.0))
        texto = (f"{_numero(fahrenheit)} \u00b0F" if i == len(ticks) - 1
                 else _numero(fahrenheit))
        cbar.ax.text(t, 1.65, texto, transform=cbar.ax.get_xaxis_transform(),
                     ha="center", va="bottom", fontsize=8.0, color=tc.INK_SOFT,
                     fontfamily="Segoe UI", clip_on=False)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Poster of the ABI L2 Land Surface Temperature (LST 2 km full "
                    "disk) with the true color design.")
    ap.add_argument("--sat", default=SAT, help=f"satellite (default {SAT})")
    ap.add_argument("--desde", help="UTC slot ISO (default: the last .nc on disk)")
    ap.add_argument("--n", type=int, default=1, help="number of frames")
    ap.add_argument("--paso", type=int, default=60,
                    help="minutes between frames (default 60: LST is hourly)")
    ap.add_argument("--ultimos", type=int, default=0, metavar="N",
                    help="the N newest .nc on disk (ignores --desde)")
    ap.add_argument("--px", type=int, default=PX,
                    help=f"globe diameter in px (default {PX})")
    ap.add_argument("--dpi", type=int, help="dpi; inferred from --px when omitted")
    ap.add_argument("--tope", type=int, default=TOPE,
                    help=f"source grid of the field (default {TOPE}, native 2 km)")
    ap.add_argument("--mapa", choices=("base", "negro"), default="base",
                    help="under the data: the Blue Marble base map or black "
                         "(default base: no black holes)")
    ap.add_argument("--fondo", choices=("claro", "oscuro"), default="oscuro",
                    help="page background, like the other GOES snapshots "
                         "(default oscuro: black, full-bleed globe)")
    ap.add_argument("--fondo-ancho", type=int, default=ANCHO_FONDO,
                    help=f"width of the cached base map (default {ANCHO_FONDO})")
    ap.add_argument("--capa-fondo", default=CAPA_FONDO,
                    help=f"GIBS layer used as the base map (default {CAPA_FONDO})")
    ap.add_argument("--relleno", type=int, default=2, metavar="N",
                    help="grid pixels to grow the field into the gaps "
                         "(default 2; 0 = off)")
    ap.add_argument("--compuesto", type=int, default=1, metavar="H",
                    help="average the H hours ending at the frame "
                         "(default 1: this frame only; >1 is poster-only)")
    ap.add_argument("--centro", nargs=2, type=float, metavar=("LON", "LAT"),
                    default=list(CENTRO), help="globe center")
    ap.add_argument("--recorte", type=float, default=1.0,
                    help="fraction of the visible radius (1 = full disk)")
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("O", "S", "E", "N"),
                    help="square flat map of that lon/lat box instead of the globe "
                         "(the Paraguay capture of the other products)")
    ap.add_argument("--vmin", type=float, default=VMIN, help="scale minimum in C")
    ap.add_argument("--vmax", type=float, default=VMAX, help="scale maximum in C")
    ap.add_argument("--titulo", default=None, help="poster title")
    ap.add_argument("--fuente", default=None, help="source line at the bottom")
    ap.add_argument("--credito", default="Graphic by @Gillo97")
    ap.add_argument("--limpio", action="store_true",
                    help="clean capture: no titles, credits, halo or edge shading")
    ap.add_argument("--lineas", action=argparse.BooleanOptionalAction, default=False,
                    help="graticule and coastlines (default: off)")
    ap.add_argument("--fronteras", action=argparse.BooleanOptionalAction, default=False,
                    help="dotted political borders (default: off)")
    ap.add_argument("--borde", nargs="?", const="", default="",
                    help="highlighted outline over the globe (empty = none)")
    ap.add_argument("--sombra-borde", type=float, default=0.0,
                    help="edge shading depth 0..0.8 (default 0: keep the values)")
    ap.add_argument("--out", help="output PNG")
    ap.add_argument("--frames", help="frame folder: render a numbered series")
    ap.add_argument("--forzar", action="store_true", help="redo existing frames")
    args = ap.parse_args(argv)

    args.titulo = args.titulo or f"{args.sat} \u00b7 LST \u00b7 SURFACE TEMPERATURE"
    args.fuente = args.fuente or (
        f"SOURCE: NOAA/NESDIS {args.sat} ABI L2 LST | 2 KM FULL DISK"
    )
    if args.fondo == "oscuro":
        _tinta_oscura()

    desde = datetime.fromisoformat(args.desde) if args.desde else None
    lista = slots(args.sat, desde, args.n, args.paso, args.ultimos)

    if args.frames:
        salida = Path(args.frames)
        salida.mkdir(parents=True, exist_ok=True)
        print(f"{len(lista)} frames -> {salida}", flush=True)
        for i, (instante, nc) in enumerate(lista, 1):
            destino = salida / f"cuadro_{i:03d}.png"
            if destino.exists() and not args.forzar:
                continue
            if args.bbox:
                rgb, _ = _componer_plano(nc, args)
                _guardar_plano(rgb, args, destino)
                print(f"  [{i}/{len(lista)}] {instante:%Y-%m-%d %H:%M} UTC", flush=True)
                continue
            disco, escala, cuadro = componer_lst(nc, args)
            fig = tc.dibujar(disco, escala, args.titulo,
                             _etiqueta_tiempo(nc, cuadro["compuesto"]),
                             args.fuente, args, args.px)
            _leyenda(fig, args)
            parcial = destino.with_suffix(".png.parcial")
            fig.savefig(parcial, format="png", facecolor=tc.WHITE)
            import matplotlib.pyplot as plt
            plt.close(fig)
            parcial.replace(destino)
            print(f"  [{i}/{len(lista)}] {instante:%Y-%m-%d %H:%M} UTC", flush=True)
        print(f"Frames in {salida}")
        return 0

    instante, nc = lista[0]
    print(f"{nc.name}\nslot: {instante:%Y-%m-%d %H:%M} UTC | globe {args.px} px | "
          f"center {tuple(args.centro)} | scale {args.vmin:g} to {args.vmax:g} C",
          flush=True)
    out = Path(args.out) if args.out else (
        SALIDAS / f"poster_{args.sat}_LST_{instante:%Y-%m-%dT%H%M}.png")
    if args.bbox:
        rgb, plano = _componer_plano(nc, args)
        print(f"map {plano['px']}x{plano['alto']} px | box {tuple(args.bbox)}")
        print(f"field {plano['min']:.1f} to {plano['max']:.1f} C | "
              f"mean {plano['mean']:.1f} C | {plano['cobertura'] * 100.0:.1f} % "
              "of the grid")
        print(f"fondo {plano['fondo']} | relleno {plano['relleno']} px | "
              f"compuesto {plano['compuesto']} h", flush=True)
        _guardar_plano(rgb, args, out)
        print(f"PNG: {out}")
        return 0

    disco, escala, stats = componer_lst(nc, args)
    print(f"globe {stats['px']} px | {stats['validos']:,} px with data")
    print(f"field {stats['min']:.1f} to {stats['max']:.1f} C | "
          f"mean {stats['mean']:.1f} C | {stats['cobertura'] * 100.0:.1f} % of the grid")
    print(f"fondo {stats['fondo']} | relleno {stats['relleno']} px | "
          f"compuesto {stats['compuesto']} h | con dato tras relleno "
          f"{stats['cubiertos'] * 100.0:.1f} %", flush=True)

    fig = tc.dibujar(disco, escala, args.titulo,
                     _etiqueta_tiempo(nc, stats["compuesto"]),
                     args.fuente, args, args.px)
    _leyenda(fig, args)
    out = Path(args.out) if args.out else (
        SALIDAS / f"poster_{args.sat}_LST_{instante:%Y-%m-%dT%H%M}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    parcial = out.with_suffix(".png.parcial")
    fig.savefig(parcial, format="png", facecolor=tc.WHITE)
    import matplotlib.pyplot as plt
    plt.close(fig)
    parcial.replace(out)
    print(f"PNG: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
