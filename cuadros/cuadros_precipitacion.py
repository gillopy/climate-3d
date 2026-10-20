"""Renderiza la **precipitación total acumulada** de ECMWF IFS 0.25° en un globo 3D.

Lee `serie_tp_mm.npz` (lo deja `descargar/precipitacion_ecmwf.py`) o, si sólo hay los
`.grib2` crudos, los decodifica al vuelo. Cada paso se reproyecta a un disco Orthographic
con un warp escalar precomputado **una sola vez** y se pinta con la paleta discreta de
Tropical Tidbits (30 niveles, `0.2` a `500+ mm`).

El disco se dibuja con `imshow` en la proyección del eje (no `contourf`): el campo se
interpola bilinealmente a resolución de píxel y recién después se mapea a la paleta, así
los bordes de cada intervalo quedan nítidos y el render es rápido. Donde llueve menos de
`0.2 mm` el alfa queda en 0: se ve la superficie base del globo (océano + tierra) con su
sombreado esférico 3D hacia el limbo.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe cuadros\\cuadros_precipitacion.py --solo-poster --px 1400
    .venv\\Scripts\\python.exe cuadros\\cuadros_precipitacion.py --hasta-hora 144 --paso 3
    .venv\\Scripts\\python.exe cuadros\\cuadros_precipitacion.py --help   # no toca la red

Salidas: `poster_precip_ecmwf_<fecha>_<ciclo>z_fh<hora>.png` y, en la corrida completa,
`frames_<etiqueta>/cuadro_NNN.png` (1-based, como espera `animar/armar.py`).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
sys.path.insert(0, str(RAIZ))
from rutas import DATOS, SALIDAS  # noqa: E402
from series import etiqueta_frames  # noqa: E402

# ---------------------------------------------------------------- escala y paleta
# 30 bordes = 29 intervalos entre 0.2 y 500 mm, más el extension "max" (>= 500 mm).
NIVELES_MM = [0.2, 1, 2, 3, 6, 9, 12, 15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90,
              100, 125, 150, 175, 200, 225, 250, 300, 350, 400, 500]

# Paleta discreta muestreada de la barra de Tropical Tidbits: verdes -> azules ->
# violetas -> bordó/rojos -> naranjas/amarillos. Un color por intervalo (29) y el
# último para el extension >= 500 mm (30 en total).
COLORES_TT = [
    # verdes 0.2-15 mm (7)
    "#c2f0d8", "#9be2bf", "#75d4a6", "#52c48d", "#3ab176", "#24985f", "#147e49",
    # azules 15-45 mm (6)
    "#166c8a", "#2480a3", "#3895bd", "#51aad4", "#71bfe8", "#95d4f7",
    # violetas 45-150 mm (8)
    "#e8d5ed", "#d8bfe0", "#c7a6d1", "#b68cc2", "#a373b2", "#8f59a0", "#7b408c", "#662777",
    # bordó/rojos 150-250 mm (4)
    "#780f3c", "#99243c", "#b53d3b", "#cc563b",
    # naranjas/amarillos 250-500+ mm (5)
    "#df743c", "#ed9246", "#f6b055", "#fad368", "#fff184",
]
COLORES_U8 = np.array([[int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)]
                       for c in COLORES_TT], dtype=np.uint8)
TICKS_LEYENDA = [0.2, 1, 2, 3, 6, 9, 12, 15, 20, 25, 30, 40, 50, 60, 80, 100, 125,
                 150, 175, 200, 250, 300, 400, 500]

# ------------------------------------------------------------------ configuración
FECHA = "2026-10-20"                   # UTC: día de la corrida
CICLO = "06"                           # UTC: 00, 06, 12 o 18
HASTA_HORA = 144                       # último paso de pronóstico (6 días)
PASO_HORA = 3                          # horas entre pasos
PX = 2712                              # lado del rectángulo donde se warpea el disco
DPI = 140
CENTRO = [-58.0, -23.0]                # Paraguay / corazón de Sudamérica
RADIO = 58.0                           # grados al borde del disco (90 = hemisferio)
FONDO_GLOBO = "claro"
CREDITO = "Graphic by @Gillo97"

# Rejilla del IFS 0.25°: 1440 x 721, de 90°N a 90°S y de 180°W a 179.75°E.
FILAS, COLUMNAS = 721, 1440

# Caja de Sudamérica/Paraguay para el "Peak SA" del pie (oeste, este, sur, norte).
CAJA_SA = (-65.0, -45.0, -32.0, -18.0)

# Fondo y vestuario del póster (compartidos en comun/estilo.py).
BG = "#0c1014"
TXT, TXT_DIM = "#ffffff", "#c9cfd6"
ESPESOR_BORDE_PY = 1.1
BORDE_SA = str(RAIZ / "datos" / "paraguay_gadm.json")


# ------------------------------------------------------------------ geometría warp
class _Geometria:
    """Índices y pesos del warp inverso Orthographic, precomputados una sola vez.

    Para cada píxel del disco guarda las cuatro esquinas del campo origen
    (`f0/f1` filas, `c0/c1` columnas) y los pesos bilineales (`ff`, `fc`), más la
    máscara del disco y el factor de luz esférico. Con esto cada cuadro cuesta sólo
    cuatro lecturas + una mezcla, sin recalcular trigonometría.
    """

    __slots__ = ("lado", "f0", "f1", "c0", "c1", "ff", "fc", "luz", "dentro", "rho")

    def __init__(self, lado, centro, radio, filas, columnas):
        lon0, lat0 = np.radians(centro[0]), np.radians(centro[1])

        # Disco normalizado: X, Y en [-1, 1]; rho = 1 cae sobre `radio` grados.
        y = np.linspace(1.0, -1.0, lado)
        x = np.linspace(-1.0, 1.0, lado)
        X, Y = np.meshgrid(x, y)
        rho = np.hypot(X, Y)
        dentro = rho <= 1.0

        rho_s = np.where(dentro & (rho > 1e-12), rho, 1.0)   # evita 0/0 en el centro
        c = np.arcsin(np.clip(rho_s * np.sin(np.radians(radio)), 0.0, 1.0))
        sin_c, cos_c = np.sin(c), np.cos(c)

        lat = np.arcsin(np.clip(cos_c * np.sin(lat0)
                                + (Y * sin_c * np.cos(lat0)) / rho_s, -1.0, 1.0))
        lon = lon0 + np.arctan2(X * sin_c,
                                rho_s * np.cos(lat0) * cos_c - Y * np.sin(lat0) * sin_c)
        es_centro = dentro & (rho <= 1e-12)
        lat = np.where(es_centro, lat0, lat)
        lon = np.where(es_centro, lon0, lon)

        lon_deg = (np.degrees(lon) + 180.0) % 360.0 - 180.0
        lat_deg = np.degrees(lat)

        # Posición de muestreo en la rejilla global (lat 90->-90, lon -180->179.75).
        col = (lon_deg + 180.0) / 360.0 * columnas
        fila = (90.0 - lat_deg) / 180.0 * (filas - 1)
        c0 = np.floor(col).astype(np.intp) % columnas
        fc = (col - np.floor(col)).astype(np.float32)
        f0 = np.clip(np.floor(fila), 0, filas - 2).astype(np.intp)
        ff = np.clip(fila - f0, 0.0, 1.0).astype(np.float32)

        self.lado = lado
        self.f0 = f0
        self.f1 = f0 + 1
        # La columna siguiente envuelve en la costura 179.75 -> -180: ahí se
        # interpola entre el último y el primer píxel, no contra un borde falso.
        self.c0 = c0
        self.c1 = (c0 + 1) % columnas
        self.ff = ff
        self.fc = fc
        self.dentro = dentro
        self.rho = rho.astype(np.float32)
        self.luz = np.where(dentro, 0.78 + 0.22 * cos_c, 0.0).astype(np.float32)

        # La geometría ya no se usa: liberar antes de que el render aloque los RGB.
        del X, Y, rho, rho_s, c, sin_c, cos_c, lat, lon, lon_deg, lat_deg, col, fila

    def muestrear(self, campo):
        """Interpola `campo` (filas x columnas) al disco y devuelve el mm por píxel."""
        a = campo[self.f0, self.c0]
        b = campo[self.f0, self.c1]
        cc = campo[self.f1, self.c0]
        d = campo[self.f1, self.c1]
        return ((a * (1.0 - self.fc) + b * self.fc) * (1.0 - self.ff)
                + (cc * (1.0 - self.fc) + d * self.fc) * self.ff)

    def disco_rgba(self, campo):
        """RGBA del campo: color discreto + luz 3D donde llueve, transparente si < 0.2."""
        mm = self.muestrear(campo)
        rgba = np.zeros((self.lado, self.lado, 4), dtype=np.uint8)
        sel = self.dentro & (mm >= NIVELES_MM[0])
        if sel.any():
            idx = np.searchsorted(NIVELES_MM, mm[sel], side="right") - 1
            idx = np.clip(idx, 0, len(COLORES_TT) - 1)
            rgb = COLORES_U8[idx].astype(np.float32) * self.luz[sel, None]
            rgba[sel, :3] = np.clip(rgb, 0.0, 255.0).astype(np.uint8)
            rgba[sel, 3] = 255
        return rgba


# ----------------------------------------------------------------------- datos
def _ciclo_valido(texto: str) -> str:
    """Ciclo como `00`, `06`, `12` u `18`; aborta si no es uno de ellos."""
    try:
        ciclo = f"{int(texto):02d}"
    except ValueError:
        raise SystemExit(f"--ciclo inválido: {texto!r} (se espera 00, 06, 12 o 18).")
    if ciclo not in ("00", "06", "12", "18"):
        raise SystemExit(f"--ciclo inválido: {texto!r} (se espera 00, 06, 12 o 18).")
    return ciclo


def _pasos(hasta_hora: int, paso: int) -> list[int]:
    """Pasos 0, paso, 2·paso, ..., hasta_hora."""
    if paso <= 0:
        raise SystemExit(f"--paso debe ser positivo (recibí {paso}).")
    if hasta_hora < 0:
        raise SystemExit(f"--hasta-hora debe ser >= 0 (recibí {hasta_hora}).")
    return list(range(0, hasta_hora + 1, paso))


def _parece_crudos(p: Path) -> bool:
    """True si `p` es una carpeta con `serie_tp_mm.npz` o con GRIB2 de la corrida."""
    if not p.is_dir():
        return False
    return ((p / "serie_tp_mm.npz").exists()
            or any(p.glob("crudo_*_fh*.grib2")))


def _dir_crudos(args, ciclo: str) -> Path:
    """Carpeta de entrada: `--crudos` > `--out-crudos` > `--out` (si es de crudos)."""
    if args.crudos:
        return Path(args.crudos)
    if args.out_crudos:
        return Path(args.out_crudos)
    if args.out and _parece_crudos(Path(args.out)):
        return Path(args.out)
    return DATOS / f"crudos_precip_ecmwf_{args.fecha}_{ciclo}z"


def _dir_salidas(args) -> Path:
    """Carpeta de salida: `--salidas` > `--out` (si no apunta a los crudos) > SALIDAS."""
    if args.salidas:
        return Path(args.salidas)
    if args.out and not _parece_crudos(Path(args.out)):
        return Path(args.out)
    return SALIDAS


def _validar_rejilla(lat, lon) -> None:
    """La rejilla debe ser la global regular que asume el warp."""
    if lat.size < 2 or lon.size < 2:
        raise SystemExit(f"Rejilla inválida: {lon.size}x{lat.size}.")
    if not (np.isclose(lat[0], 90.0) and np.isclose(lat[-1], -90.0)):
        raise SystemExit(f"Latitud inesperada: {lat[0]}→{lat[-1]} (se espera 90→-90).")
    if not (np.isclose(lon[0], -180.0) and np.isclose(lon[-1], 179.75)):
        raise SystemExit(f"Longitud inesperada: {lon[0]}→{lon[-1]} "
                         "(se espera -180→179.75).")


def _parse_init(texto) -> datetime | None:
    """`2026-10-20T06:00Z` -> datetime (con zona UTC si trae la Z)."""
    if not texto:
        return None
    try:
        return datetime.fromisoformat(str(texto).replace("Z", "+00:00"))
    except ValueError:
        return None


def _cargar_npz(ruta: Path):
    """Lee `tp_mm`, `lat`, `lon`, `horas` y `fecha_init` de un `.npz`."""
    with np.load(ruta, allow_pickle=False) as d:
        nombre = "tp_mm" if "tp_mm" in d.files else "tp"
        if nombre not in d.files:
            raise SystemExit(f"{ruta.name}: no trae 'tp_mm' ni 'tp'.")
        tp = np.asarray(d[nombre], dtype=np.float32)
        lat = np.asarray(d["lat"], dtype=np.float32)
        lon = np.asarray(d["lon"], dtype=np.float32)
        if "horas" in d.files:
            horas = np.asarray(d["horas"], dtype=np.int32)
        else:
            horas = np.arange(tp.shape[0], dtype=np.int32)
        fecha_init = str(d["fecha_init"]) if "fecha_init" in d.files else None
    return tp, lat, lon, horas, fecha_init


def _cargar_netcdf(ruta: Path):
    """Best-effort para ERA5 NetCDF (requiere `xarray`, que no está en el venv base)."""
    try:
        import xarray as xr
    except ImportError:
        raise SystemExit("--nc con NetCDF necesita `xarray` instalado en .venv; "
                         "mientras tanto usá el .npz que deja el descargador.")
    ds = xr.open_dataset(ruta)
    nombre = next((v for v in ("tp_mm", "tp", "total_precipitation", "precipitation")
                   if v in ds), None)
    if nombre is None:
        raise SystemExit(f"{ruta.name}: no contiene ninguna variable de precipitación.")
    da = ds[nombre]
    for dim in list(da.dims):
        if dim not in ("time", "valid_time", "latitude", "longitude", "lat", "lon"):
            da = da.isel({dim: 0})
    tdim = "valid_time" if "valid_time" in da.dims else ("time" if "time" in da.dims else None)
    lat_name = "latitude" if "latitude" in da.coords else "lat"
    lon_name = "longitude" if "longitude" in da.coords else "lon"
    tp = np.asarray(da.values, dtype=np.float32)
    if tdim is None:
        tp = tp[None]
        horas = np.array([0], dtype=np.int32)
        fecha_init = None
    else:
        tiempos = np.asarray(da[tdim].values)
        horas = ((tiempos - tiempos[0]) / np.timedelta64(1, "h")).astype(np.int32)
        fecha_init = np.datetime_as_string(tiempos[0], unit="m") + "Z"
    lat = np.asarray(da[lat_name].values, dtype=np.float32)
    lon = np.asarray(da[lon_name].values, dtype=np.float32)
    # ERA5 suele venir 0..360 y con latitud descendente: normalizar como el IFS.
    lon_norm = (lon + 180.0) % 360.0 - 180.0
    orden = np.argsort(lon_norm, kind="stable")
    if not np.array_equal(orden, np.arange(lon.size)):
        tp = tp[:, :, orden] if tp.ndim == 3 else tp[:, orden]
        lon_norm = lon_norm[orden]
    lon = lon_norm
    if lat[0] < lat[-1]:
        tp = tp[:, ::-1, :]
        lat = lat[::-1]
    # ERA5 publica `tp` en metros acumulados: a mm si el orden de magnitud lo delata.
    if nombre in ("tp", "total_precipitation") and float(np.nanmax(tp)) < 50.0:
        tp = tp * 1000.0
    ds.close()
    return tp, lat, lon, horas, fecha_init


def _fh_de(ruta: Path) -> int:
    """Número de paso (`..._fh144.grib2`) de un crudo GRIB2."""
    partes = ruta.stem.split("_fh")
    return int(partes[-1]) if len(partes) == 2 else -1


def _cargar_gribs(crudos: Path, horas_pedidas: list[int]):
    """Decodifica sólo los GRIB2 de los pasos pedidos con el lector del descargador."""
    from descargar.precipitacion_ecmwf import leer_tp_mm

    rutas = {_fh_de(p): p for p in crudos.glob("crudo_*_fh*.grib2")}
    faltan = [h for h in horas_pedidas if h not in rutas]
    if faltan:
        raise SystemExit(f"Faltan los GRIB2 de los pasos {faltan} en {crudos}.")
    serie = np.empty((len(horas_pedidas), FILAS, COLUMNAS), dtype=np.float32)
    lat = lon = None
    for i, h in enumerate(horas_pedidas):
        serie[i], lat, lon = leer_tp_mm(rutas[h])
    return serie, lat, lon


def cargar_serie(args, ciclo: str):
    """Devuelve `(serie mm, lat, lon, horas, fecha_init)` de NPZ, GRIB2 o `--nc`."""
    if args.nc:
        ruta = Path(args.nc)
        if not ruta.exists():
            raise SystemExit(f"No existe el archivo indicado: {ruta}")
        if ruta.suffix.lower() == ".npz":
            tp, lat, lon, horas, fecha_init = _cargar_npz(ruta)
        else:
            tp, lat, lon, horas, fecha_init = _cargar_netcdf(ruta)
        _validar_rejilla(lat, lon)
        print(f"Datos: {ruta} | {tp.shape[0]} pasos | rejilla {lon.size}x{lat.size}")
        return tp, lat, lon, horas, fecha_init

    crudos = _dir_crudos(args, ciclo)
    cache = crudos / "serie_tp_mm.npz"
    if cache.exists():
        tp, lat, lon, horas, fecha_init = _cargar_npz(cache)
        _validar_rejilla(lat, lon)
        print(f"Datos: {cache} | {tp.shape[0]} pasos | rejilla {lon.size}x{lat.size}")
        return tp, lat, lon, horas, fecha_init

    pedidas = _pasos(args.hasta_hora, args.paso)
    if _parece_crudos(crudos):
        print(f"Sin serie consolidada: decodificando GRIB2 de {crudos}...")
        tp, lat, lon = _cargar_gribs(crudos, pedidas)
        _validar_rejilla(lat, lon)
        return tp, lat, lon, np.asarray(pedidas, dtype=np.int32), None

    raise SystemExit(
        f"No hay datos en {crudos}.\n"
        f"Descargalos con:\n  {_comando_descarga(args)}")


def _comando_descarga(args) -> str:
    return (f".venv\\Scripts\\python.exe descargar\\precipitacion_ecmwf.py "
            f"--fecha {args.fecha} --ciclo {args.ciclo} "
            f"--hasta-hora {args.hasta_hora} --paso {args.paso}")


def _seleccionar(horas, hasta_hora: int, paso: int):
    """Índices de los pasos pedidos dentro de la serie, en orden; aborta si faltan."""
    pedidas = _pasos(hasta_hora, paso)
    indice: dict[int, int] = {}
    for i, h in enumerate(np.asarray(horas).ravel()):
        indice.setdefault(int(h), i)
    faltan = [h for h in pedidas if h not in indice]
    if faltan:
        raise SystemExit(f"La serie no tiene los pasos {faltan}. Revisá --hasta-hora/"
                         "--paso o volvé a descargar.")
    return [indice[h] for h in pedidas], pedidas


def _mascara_caja(lat, lon, caja):
    """Máscaras de filas y columnas de la caja (oeste, este, sur, norte)."""
    oeste, este, sur, norte = caja
    return (lat <= norte) & (lat >= sur), (lon >= oeste) & (lon <= este)


def _max_caja(campo, filas, columnas) -> float:
    """Máximo del campo dentro de la caja; 0 si la caja no toca la rejilla."""
    sub = campo[np.ix_(filas, columnas)]
    if not sub.size:
        return 0.0
    valor = float(np.nanmax(sub))
    return valor if np.isfinite(valor) else 0.0


# ------------------------------------------------------------------------ render
def _borde_geojson(ax, ruta, color, ancho, zorder=5):
    """Contorno destacado (Paraguay) sobre el globo; devuelve la colección o None."""
    if not ruta:
        return None
    from matplotlib.collections import LineCollection
    import cartopy.crs as ccrs
    try:
        with open(ruta, encoding="utf-8") as f:
            gj = json.load(f)
    except Exception as exc:
        print(f"AVISO: borde omitido ({exc})")
        return None
    feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
    segs = []
    for f in feats:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            for ring in poly:
                segs.append(np.asarray(ring, dtype=float))
    if not segs:
        return None
    return ax.add_collection(LineCollection(segs, transform=ccrs.PlateCarree(),
                                            colors=color, linewidths=ancho,
                                            zorder=zorder))


def _vignette(geo, lado):
    """Sombreado radial tenue hacia el limbo, para que la tierra no quede plana."""
    rgba = np.zeros((lado, lado, 4), dtype=np.uint8)
    t = np.clip((geo.rho - 0.70) / 0.30, 0.0, 1.0) * geo.dentro
    rgba[..., 0] = 10
    rgba[..., 1] = 16
    rgba[..., 2] = 26
    rgba[..., 3] = (t * 24.0).astype(np.uint8)
    return rgba


def render_globo(campo, t_init: datetime, t_valid: datetime, hora: int, max_sa: float,
                 args, geo: _Geometria, destino: Path) -> Path:
    """Dibuja un cuadro/póster completo del globo y lo guarda en `destino`."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.colors import BoundaryNorm, ListedColormap
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    from estilo import MONTHS_EN

    lon0, lat0 = args.centro
    lado_fig = args.px / args.dpi
    fig = plt.figure(figsize=(lado_fig, lado_fig), dpi=args.dpi)
    fig.patch.set_facecolor(BG)

    ax = fig.add_axes([0.014, 0.014, 0.972, 0.972],
                      projection=ccrs.Orthographic(central_longitude=lon0,
                                                   central_latitude=lat0))
    ax.set_facecolor(BG)
    ax.spines["geo"].set_visible(False)

    # Geometría del recorte: el borde del disco cae a `radio` grados del centro.
    # `x_limits` hay que leerlo ANTES de achicar la vista (después devuelve el nuevo).
    R = float(ax.projection.x_limits[1])
    r_m = R * np.sin(np.radians(args.radio))
    ax.set_xlim(-r_m, r_m)
    ax.set_ylim(-r_m, r_m)
    # El círculo de recorte se instala como *boundary* del eje: `FeatureArtist.draw`
    # reemplaza cualquier `set_clip_path` propio por `axes.patch`, así que la única forma
    # de recortar costas/fronteras/tierra al disco es que el patch del eje sea el círculo.
    ang = np.linspace(0.0, 2.0 * np.pi, 361)
    from matplotlib.path import Path as MplPath
    ax.set_boundary(MplPath(np.column_stack([r_m * np.cos(ang), r_m * np.sin(ang)])),
                    transform=ax.transData)
    # Mismo círculo para recortar colecciones que no pasan por `FeatureArtist`
    # (el contorno de Paraguay): hay que atarlo al eje para resolver su transform.
    clip = mpatches.Circle((0.0, 0.0), radius=r_m, transform=ax.projection)
    ax.add_patch(clip)
    clip.set_visible(False)

    if args.fondo_globo == "oscuro":
        oceano, tierra = "#101720", "#1b2430"
    else:
        oceano, tierra = "#dce6f0", "#f4f6f8"

    # Superficie base: océano + continentes. El campo de lluvia se pinta encima y deja
    # transparentes las zonas secas, así se ve este globo (con el sombreado radial).
    ax.add_patch(mpatches.Circle((0.0, 0.0), radius=r_m, transform=ax.projection,
                                 facecolor=oceano, edgecolor="none", zorder=1))
    try:
        ax.add_feature(cfeature.LAND.with_scale("110m"), facecolor=tierra,
                       edgecolor="none", zorder=2)
    except Exception as exc:
        print(f"AVISO: tierra omitida ({exc})")
    if args.fondo_globo != "oscuro":
        ax.imshow(_vignette(geo, args.px), origin="upper",
                  extent=[-r_m, r_m, -r_m, r_m], transform=ax.projection,
                  interpolation="bilinear", zorder=2.5)

    # Campo de precipitación ya warpeado, a resolución plena y con bordes nítidos.
    ax.imshow(geo.disco_rgba(campo), origin="upper",
              extent=[-r_m, r_m, -r_m, r_m], transform=ax.projection,
              interpolation="nearest", zorder=3)

    try:
        ax.add_feature(cfeature.COASTLINE.with_scale("110m"), linewidth=0.65,
                       edgecolor="#111111", zorder=4)
        ax.add_feature(cfeature.BORDERS.with_scale("110m"), linewidth=0.45,
                       edgecolor="#222222", zorder=4)
    except Exception as exc:
        print(f"AVISO: costas/fronteras omitidas ({exc})")
    borde = _borde_geojson(ax, BORDE_SA, "#000000", ESPESOR_BORDE_PY)
    if borde is not None:
        borde.set_clip_path(clip)

    # Aro exterior del globo, para separar el disco del fondo del póster.
    ax.add_patch(mpatches.Circle((0.0, 0.0), radius=r_m, transform=ax.projection,
                                 facecolor="none", edgecolor="#3a4659",
                                 linewidth=1.0, zorder=6))

    # --------------------------------------------------------------- vestuario
    import matplotlib.patheffects as patheffects
    esc = 0.8 * (args.px / 720.0) ** 0.45
    halo = [patheffects.withStroke(linewidth=3.2 * esc, foreground=BG)]
    fig.text(0.026, 0.985, f"{MONTHS_EN[t_valid.month - 1]} {t_valid.year}", color=TXT,
             fontsize=19 * esc, fontweight="bold", ha="left", va="top",
             path_effects=halo, zorder=11)
    fig.text(0.026, 0.946,
             f"Init {t_init:%d %b %Y %H:%M} UTC · Valid {t_valid:%d %b %Y %H:%M} UTC "
             f"(FH +{hora:03d}h)",
             color=TXT, fontsize=13.5 * esc, fontweight="bold", ha="left", va="top",
             path_effects=halo, zorder=11)
    fig.text(0.026, 0.912, "ECMWF IFS 0.25° · TOTAL ACCUMULATED PRECIPITATION (mm)",
             color=TXT_DIM, fontsize=11.5 * esc, fontweight="bold", ha="left", va="top",
             path_effects=halo, zorder=11)
    fig.text(0.983, 0.983, args.credito, color=TXT_DIM, fontsize=12 * esc,
             ha="right", va="top", path_effects=halo, zorder=11)

    # Barra de color horizontal sobre el tramo inferior del póster, con pastilla
    # oscura traslúcida para que los ticks se lean limpios sobre el borde del globo.
    fondo_cbar = mpatches.FancyBboxPatch(
        (0.050, 0.030), 0.900, 0.055,
        boxstyle="round,pad=0.006,rounding_size=0.010",
        transform=fig.transFigure, facecolor=(0.047, 0.063, 0.078, 0.86),
        edgecolor="#2a3442", linewidth=0.8, zorder=9,
    )
    fig.add_artist(fondo_cbar)
    cax = fig.add_axes([0.066, 0.055, 0.822, 0.017], zorder=10)
    cmap = ListedColormap(COLORES_TT[:-1])
    cmap.set_over(COLORES_TT[-1])
    # `ncolors` debe cubrir los 30 bins (29 intervalos + extensión); si se pasa 29,
    # matplotlib 3.11 levanta ValueError. El color de "over" sigue siendo el último.
    norm = BoundaryNorm(NIVELES_MM, len(NIVELES_MM), extend="max")
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=cax, orientation="horizontal", extend="max")
    cbar.outline.set_visible(True)
    cbar.outline.set_edgecolor("#1e2631")
    cbar.outline.set_linewidth(0.6)
    cbar.set_ticks(TICKS_LEYENDA)
    cbar.set_ticklabels([f"{v:g}" for v in TICKS_LEYENDA])
    cbar.ax.tick_params(colors=TXT, length=3, width=0.8,
                        labelsize=max(6.5, 8.8 * esc), pad=2)
    fig.text(0.916, 0.0635, "mm", color=TXT,
             fontsize=max(7.0, 9.8 * esc), fontweight="bold",
             ha="left", va="center", zorder=11)

    fig.text(0.026, 0.012, "Source: ECMWF Open Data · IFS HRES 0.25° (oper)",
             color=TXT_DIM, fontsize=7.4 * esc, ha="left", va="bottom")
    fig.text(0.980, 0.012,
             f"Accumulated from {t_init:%Y-%m-%d %H:%M} UTC · Peak SA: {max_sa:.0f} mm",
             color=TXT_DIM, fontsize=7.4 * esc, ha="right", va="bottom")

    # Guardado atómico: nunca queda un PNG truncado que después se reutilice.
    parcial = destino.with_suffix(".png.parcial")
    fig.savefig(parcial, format="png", facecolor=BG)
    plt.close(fig)
    parcial.replace(destino)
    return destino


def _sello_render(args) -> str:
    """Huella de los parámetros que cambian el aspecto; invalida cuadros viejos."""
    import hashlib
    datos = {
        "px": args.px, "dpi": args.dpi, "centro": list(args.centro),
        "radio": args.radio, "fondo": args.fondo_globo, "credito": args.credito,
        "niveles": NIVELES_MM, "colores": COLORES_TT,
    }
    return hashlib.sha256(json.dumps(datos, sort_keys=True).encode()).hexdigest()[:16]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Globo Orthographic de precipitación total acumulada (mm) de "
                    "ECMWF IFS 0.25°, con paleta discreta y barra de colores.")
    ap.add_argument("--fecha", default=FECHA,
                    help=f"día UTC de la corrida, YYYY-MM-DD (por defecto {FECHA})")
    ap.add_argument("--ciclo", default=CICLO,
                    help=f"ciclo UTC de la corrida: 00, 06, 12 o 18 (por defecto {CICLO})")
    ap.add_argument("--hasta-hora", type=int, default=HASTA_HORA,
                    help=f"último paso de pronóstico en horas (por defecto {HASTA_HORA})")
    ap.add_argument("--paso", type=int, default=PASO_HORA,
                    help=f"horas entre pasos (por defecto {PASO_HORA})")
    ap.add_argument("--crudos", help="carpeta de crudos/serie de entrada (por defecto, "
                                     "DATOS/crudos_precip_ecmwf_<fecha>_<ciclo>z)")
    ap.add_argument("--out-crudos", help="alias de --crudos")
    ap.add_argument("--nc", help="archivo ERA5 (.nc/.npz) alternativo a los crudos")
    ap.add_argument("--px", type=int, default=PX,
                    help=f"lado del rectángulo donde se warpea el disco "
                         f"(por defecto {PX})")
    ap.add_argument("--dpi", type=int, default=DPI, help=f"dpi del render (por defecto {DPI})")
    ap.add_argument("--centro", nargs=2, type=float, metavar=("LON", "LAT"),
                    default=list(CENTRO),
                    help=f"centro del globo (por defecto {CENTRO[0]} {CENTRO[1]})")
    ap.add_argument("--radio", type=float, default=RADIO,
                    help=f"grados al borde del disco; 90 = hemisferio (por defecto {RADIO})")
    ap.add_argument("--fondo-globo", choices=["claro", "oscuro"], default=FONDO_GLOBO,
                    help=f"fondo del globo (por defecto {FONDO_GLOBO})")
    ap.add_argument("--credito", default=CREDITO, help="crédito de la esquina superior")
    ap.add_argument("--solo-poster", action="store_true",
                    help="renderiza sólo el póster estático del último paso")
    ap.add_argument("--forzar", action="store_true",
                    help="vuelve a renderizar los cuadros aunque los PNG ya existan")
    ap.add_argument("--salidas", help="carpeta de salida (por defecto comun.rutas.SALIDAS)")
    ap.add_argument("--out", help="alias de --salidas; si apunta a los crudos, se "
                                  "interpreta como entrada (compatibilidad)")
    args = ap.parse_args(argv)

    ciclo = _ciclo_valido(args.ciclo)
    try:
        datetime.fromisoformat(args.fecha)
    except ValueError:
        raise SystemExit(f"--fecha inválida: {args.fecha!r} (se espera YYYY-MM-DD).")
    if not (0.0 < args.radio <= 90.0):
        raise SystemExit(f"--radio debe estar en (0, 90] (recibí {args.radio}).")
    if args.px < 64 or args.dpi < 24:
        raise SystemExit("--px/--dpi demasiado chicos.")
    _pasos(args.hasta_hora, args.paso)

    salidas = _dir_salidas(args)
    salidas.mkdir(parents=True, exist_ok=True)
    poster = salidas / (f"poster_precip_ecmwf_{args.fecha}_{ciclo}z_"
                        f"fh{args.hasta_hora:03d}.png")

    serie, lat, lon, horas, fecha_init = cargar_serie(args, ciclo)
    indices, horas_pedidas = _seleccionar(horas, args.hasta_hora, args.paso)

    t_init = _parse_init(fecha_init)
    if t_init is None:
        t_init = datetime.fromisoformat(args.fecha).replace(hour=int(ciclo))
    filas_sa, cols_sa = _mascara_caja(lat, lon, CAJA_SA)

    geo = _Geometria(args.px, args.centro, args.radio, lat.size, lon.size)
    ultimo = indices[-1]
    hora_final = horas_pedidas[-1]
    max_sa = _max_caja(serie[ultimo], filas_sa, cols_sa)
    t_valid = t_init + timedelta(hours=hora_final)

    if args.solo_poster:
        inicio = time.time()
        render_globo(serie[ultimo], t_init, t_valid, hora_final, max_sa, args, geo, poster)
        print(f"Póster FH +{hora_final}h: {poster} "
              f"({args.px}x{args.px} px, {time.time() - inicio:.1f}s)")
        return 0

    n = len(indices)
    frames_dir = salidas / f"frames_{etiqueta_frames('precipitacion', 'globo', t_init, n, args.px)}"
    frames_dir.mkdir(parents=True, exist_ok=True)

    # Si cambió el aspecto, los cuadros viejos quedaron obsoletos: se rehacen.
    sello = _sello_render(args)
    archivo_sello = frames_dir / ".sello_render"
    previo = (archivo_sello.read_text(encoding="utf-8").strip()
              if archivo_sello.exists() else None)
    forzar = args.forzar or (previo is not None and previo != sello)
    if forzar and previo is not None and previo != sello:
        print("Cambiaron los parámetros de render -> se rehacen los cuadros")
    archivo_sello.write_text(sello, encoding="utf-8")

    print(f"Precipitación ECMWF | {n} cuadros | init {t_init:%Y-%m-%d %H:%M} UTC | "
          f"centro {args.centro[0]} {args.centro[1]} | radio {args.radio:g}° | "
          f"{args.px}x{args.px} px | frames en {frames_dir}")

    inicio = time.time()
    hechos = 0
    for i, (idx, hora) in enumerate(zip(indices, horas_pedidas), 1):
        destino = frames_dir / f"cuadro_{i:03d}.png"
        if not forzar and destino.exists():
            continue
        t_valid_i = t_init + timedelta(hours=hora)
        max_sa_i = _max_caja(serie[idx], filas_sa, cols_sa)
        render_globo(serie[idx], t_init, t_valid_i, hora, max_sa_i, args, geo, destino)
        hechos += 1
        print(f"  {i}/{n} listos ({time.time() - inicio:.0f}s)", flush=True)

    # El póster de cierre se escribe siempre, aun cuando los cuadros ya existían.
    render_globo(serie[ultimo], t_init, t_valid, hora_final, max_sa, args, geo, poster)
    print(f"{n} cuadros en {frames_dir} ({hechos} renderizados)")
    print(f"Póster FH +{hora_final}h: {poster}")
    print(f"Armá el video con: .venv\\Scripts\\python.exe animar\\armar.py "
          f"--frames \"{frames_dir}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
