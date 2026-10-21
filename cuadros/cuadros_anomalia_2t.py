"""Renderiza la **anomalía de temperatura a 2 m** de ECMWF en un globo 3D Orthographic.

Soporta IFS 0.25° (`--modelo ifs`, por defecto) y AIFS-SINGLE 0.25° (`aifs-single`). Lee
`serie_anom_2t_c.npz` (lo deja `descargar/anomalia_2t_ecmwf.py`) con la anomalía ya en °C
respecto de la climatología diurna de ERA5. Cada paso se reproyecta a un disco
Orthographic con un warp escalar precomputado **una sola vez** y se pinta con la paleta
divergente discreta de Tropical Tidbits (35 intervalos entre `-28` y `+28 °C`, con
extensiones `under` y `over`).

La banda neutra (`|anomalía| < 0.5 °C`) queda **transparente en el globo**: se ve la
superficie base (océano + tierra + sombreado esférico), igual que en la referencia. En la
barra de colores esa misma banda es blanca.

El disco se dibuja con `imshow` en la proyección del eje (no `contourf`): el campo se
interpola bilinealmente a resolución de píxel y recién después se mapea a la paleta, así
los bordes de cada intervalo quedan nítidos y el render es rápido.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe cuadros\\cuadros_anomalia_2t.py --solo-poster --px 2712
    .venv\\Scripts\\python.exe cuadros\\cuadros_anomalia_2t.py --hasta-hora 360 --paso 6
    .venv\\Scripts\\python.exe cuadros\\cuadros_anomalia_2t.py --help   # no toca la red

Salidas: `poster_anom2t_<modelo>_<fecha>_<ciclo>z_fh<hora>.png` y, en la corrida
completa, `frames_<etiqueta>/cuadro_NNN.png` (1-based, como espera `animar/armar.py`).
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
# 36 bordes = 35 intervalos entre -28 y +28 °C, más under (< -28) y over (>= 28).
NIVELES_C = [-28, -24, -20, -16, -14, -12, -10, -8, -7, -6, -5, -4, -3, -2.5, -2, -1.5,
             -1, -0.5, 0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8, 10, 12, 14, 16, 20, 24, 28]

# Paleta discreta muestreada de la barra de Tropical Tidbits (2 m Temperature Anomaly).
# 37 colores: [0] under, [1..35] los 35 intervalos, [36] over. El índice 18 (banda
# neutra -0.5..0.5 °C) es blanco en la barra y transparente sobre el globo.
COLORES_ANOM = [
    "#f5c6e0",                                                        # under (< -28)
    # frío rosa/violeta -28..-10 (6)
    "#f0aad2", "#e688c2", "#db60b8", "#cc3dd4", "#a32ec9", "#7326b3",
    # frío azul/cian -10..-0.5 (11)
    "#362b9e", "#233da8", "#1c50b8", "#1c64c7", "#247ad4", "#3390e0",
    "#4ba5eb", "#69baf2", "#87cef7", "#a6e0fc", "#c7f0ff",
    # neutro -0.5..0.5 (1)
    "#ffffff",
    # cálido amarillo/naranja/rojo/carmesí 0.5..10 (11)
    "#fff6bd", "#ffea96", "#ffd96e", "#f7c04d", "#f0a235", "#e88023",
    "#de5b1b", "#cf3317", "#b51819", "#8f0c16", "#b82e56",
    # cálido extremo rosa/malva/marrón 10..28 (6)
    "#d65682", "#eb80a8", "#f2a7c6", "#c793ad", "#9c707d", "#754f46",
    "#57382c",                                                        # over (>= 28)
]
COLORES_U8 = np.array([[int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)]
                       for c in COLORES_ANOM], dtype=np.uint8)
NIVELES_C_F32 = np.asarray(NIVELES_C, dtype=np.float32)
# Tabla RGBA (38 x 4): 0..36 son los intervalos (18 = neutro transparente), 37 = fuera del disco.
TABLA_RGBA = np.zeros((len(COLORES_ANOM) + 1, 4), dtype=np.uint8)
TABLA_RGBA[:len(COLORES_ANOM), :3] = COLORES_U8
TABLA_RGBA[:len(COLORES_ANOM), 3] = 255
TABLA_RGBA[18, 3] = 0  # banda neutra [-0.5, 0.5] °C deja ver tierra/océano del globo
IDX_NEUTRO = 18
TICKS_LEYENDA = [-28, -20, -16, -12, -8, -6, -4, -2.5, -1.5, -0.5,
                 0.5, 1.5, 2.5, 4, 6, 8, 12, 16, 20, 28]

# Banda neutra: en el globo se deja ver la superficie base.
BANDA_NEUTRA = 0.5

# Filas por bloque en el warp: acota el pico de RAM del blend bilineal.
BLOQUE = 512

# ------------------------------------------------------------------ configuración
MODELOS = ("ifs", "aifs-single")
TITULOS_MODELO = {
    "ifs": "ECMWF IFS 0.25° · 2-METER TEMPERATURE ANOMALY (°C)",
    "aifs-single": "ECMWF AIFS-SINGLE 0.25° · 2-METER TEMPERATURE ANOMALY (°C)",
}
FUENTES_MODELO = {
    "ifs": "Source: ECMWF Open Data · IFS HRES 0.25° (vs ERA5 Diurnal Climatology)",
    "aifs-single": "Source: ECMWF Open Data · AIFS-SINGLE 0.25° "
                   "(vs ERA5 Diurnal Climatology)",
}

FECHA = "2026-10-20"                   # UTC: día de la corrida
CICLO = "12"                           # UTC: 00, 06, 12 o 18
HASTA_HORA = 360                       # último paso de pronóstico (15 días)
PASO_HORA = 6                          # horas entre pasos
PX = 2712                              # lado del rectángulo donde se warpea el disco
DPI = 140
CENTRO = [-58.0, -23.0]                # Paraguay / corazón de Sudamérica
RADIO = 58.0                           # grados al borde del disco (90 = hemisferio)
FONDO_GLOBO = "claro"
CREDITO = "Graphic by @Gillo97"

# Rejilla del IFS 0.25°: 1440 x 721, de 90°N a 90°S y de 180°W a 179.75°E.
FILAS, COLUMNAS = 721, 1440

# Caja de Sudamérica/Paraguay para el "SA Range" del pie (oeste, este, sur, norte).
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
    máscara del disco. Con esto cada cuadro cuesta sólo cuatro lecturas + una mezcla,
    sin recalcular trigonometría.
    """

    __slots__ = ("lado", "f0", "f1", "c0", "c1", "ff", "fc", "dentro", "rho")

    def __init__(self, lado, centro, radio, filas, columnas):
        lon0 = np.float32(np.radians(centro[0]))
        lat0 = np.float32(np.radians(centro[1]))

        # Disco normalizado en float32 para no saturar RAM/swap en resoluciones 2712x2712.
        y = np.linspace(1.0, -1.0, lado, dtype=np.float32)
        x = np.linspace(-1.0, 1.0, lado, dtype=np.float32)
        X, Y = np.meshgrid(x, y)
        rho = np.hypot(X, Y)
        dentro = rho <= 1.0

        rho_s = np.where(dentro & (rho > 1e-6), rho, np.float32(1.0))
        sin_rad = np.float32(np.sin(np.radians(radio)))
        c = np.arcsin(np.clip(rho_s * sin_rad, np.float32(0.0), np.float32(1.0)))
        sin_c, cos_c = np.sin(c), np.cos(c)

        lat = np.arcsin(np.clip(cos_c * np.sin(lat0)
                                + (Y * sin_c * np.cos(lat0)) / rho_s,
                                np.float32(-1.0), np.float32(1.0)))
        lon = lon0 + np.arctan2(X * sin_c,
                                rho_s * np.cos(lat0) * cos_c - Y * np.sin(lat0) * sin_c)
        es_centro = dentro & (rho <= 1e-6)
        lat = np.where(es_centro, lat0, lat)
        lon = np.where(es_centro, lon0, lon)
        del X, Y, rho_s, c, sin_c

        lon_deg = (np.degrees(lon) + np.float32(180.0)) % np.float32(360.0) - np.float32(180.0)
        lat_deg = np.degrees(lat)
        del lon, lat

        # Posición de muestreo en la rejilla global (lat 90->-90, lon -180->179.75).
        col = (lon_deg + np.float32(180.0)) / np.float32(360.0) * np.float32(columnas)
        fila = (np.float32(90.0) - lat_deg) / np.float32(180.0) * np.float32(filas - 1)
        del lon_deg, lat_deg

        col_floor = np.floor(col)
        fc = (col - col_floor).astype(np.float32)
        c0 = (col_floor.astype(np.int32) % columnas).astype(np.int16)
        del col, col_floor

        fila_floor = np.clip(np.floor(fila), 0.0, float(filas - 2))
        ff = np.clip(fila - fila_floor, np.float32(0.0), np.float32(1.0)).astype(np.float32)
        f0 = fila_floor.astype(np.int16)
        del fila, fila_floor

        self.lado = lado
        self.f0 = f0
        self.f1 = (f0 + np.int16(1)).astype(np.int16)
        self.c0 = c0
        self.c1 = ((c0.astype(np.int32) + 1) % columnas).astype(np.int16)
        self.ff = ff
        self.fc = fc
        self.dentro = dentro
        self.rho = rho
        del cos_c

    def _bloque(self, campo, ini, fin):
        """Valores interpolados de las filas `ini:fin` del disco (float32)."""
        f0 = self.f0[ini:fin]
        f1 = self.f1[ini:fin]
        c0 = self.c0[ini:fin]
        c1 = self.c1[ini:fin]
        ff = self.ff[ini:fin]
        fc = self.fc[ini:fin]
        a = campo[f0, c0]
        b = campo[f0, c1]
        cc = campo[f1, c0]
        d = campo[f1, c1]
        omc = np.subtract(np.float32(1.0), fc, dtype=np.float32)
        omm = np.subtract(np.float32(1.0), ff, dtype=np.float32)
        tmp = a * omc
        tmp += b * fc
        tmp *= omm
        tmp2 = cc * omc
        tmp2 += d * fc
        tmp2 *= ff
        tmp += tmp2
        return tmp

    def muestrear(self, campo):
        """Interpola `campo` (filas x columnas) al disco y devuelve el valor por píxel.

        Va por bloques de filas: a 2712x2712 px, hacer el blend entero de una vez
        dispara el consumo de RAM (y el OOM) por los temporales float64.
        """
        lado = self.lado
        out = np.empty((lado, lado), dtype=np.float32)
        for ini in range(0, lado, BLOQUE):
            fin = min(ini + BLOQUE, lado)
            out[ini:fin] = self._bloque(campo, ini, fin)
        return out

    def disco_rgba(self, campo):
        """RGBA del campo: color discreto donde hay anomalía, viñeta en la neutra.

        Indexado directo 2D sobre `TABLA_RGBA` (sin máscaras booleanas 1D) y por bloques
        de filas, para que el consumo de RAM sea plano a 2712x2712 px. La viñeta radial
        va horneada en la banda neutra: mismo look que antes, con un solo `imshow`.
        """
        lado = self.lado
        rgba = np.zeros((lado, lado, 4), dtype=np.uint8)
        for ini in range(0, lado, BLOQUE):
            fin = min(ini + BLOQUE, lado)
            vals = self._bloque(campo, ini, fin)
            idx = np.searchsorted(NIVELES_C_F32, vals, side="right")
            idx[~self.dentro[ini:fin]] = len(COLORES_ANOM)   # fuera del disco
            rgb = TABLA_RGBA[idx]
            neutra = idx == IDX_NEUTRO
            if neutra.any():
                t = np.clip((self.rho[ini:fin] - np.float32(0.70)) / np.float32(0.30),
                            np.float32(0.0), np.float32(1.0)) * self.dentro[ini:fin]
                rgb[neutra, 0] = 10
                rgb[neutra, 1] = 16
                rgb[neutra, 2] = 26
                rgb[neutra, 3] = (t[neutra] * np.float32(24.0)).astype(np.uint8)
            rgba[ini:fin] = rgb
            del vals, idx, rgb
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


def _dir_crudos(args, ciclo: str) -> Path:
    """Carpeta de entrada: `--crudos` > `--out-crudos` > valor por defecto."""
    if args.crudos:
        return Path(args.crudos)
    if args.out_crudos:
        return Path(args.out_crudos)
    return DATOS / f"crudos_anom2t_{args.modelo}_{args.fecha}_{ciclo}z"


def _dir_salidas(args) -> Path:
    """Carpeta de salida: `--salidas` > `--out` > SALIDAS."""
    if args.salidas:
        return Path(args.salidas)
    if args.out:
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
    """`2026-10-20T12:00Z` -> datetime (con zona UTC si trae la Z)."""
    if not texto:
        return None
    try:
        return datetime.fromisoformat(str(texto).replace("Z", "+00:00"))
    except ValueError:
        return None


def _cargar_npz(ruta: Path):
    """Lee `anom_c`, `lat`, `lon`, `horas` y `fecha_init` de un `.npz`."""
    with np.load(ruta, allow_pickle=False) as d:
        if "anom_c" not in d.files:
            raise SystemExit(f"{ruta.name}: no trae 'anom_c'.")
        anom = np.asarray(d["anom_c"], dtype=np.float32)
        lat = np.asarray(d["lat"], dtype=np.float32)
        lon = np.asarray(d["lon"], dtype=np.float32)
        if "horas" in d.files:
            horas = np.asarray(d["horas"], dtype=np.int32)
        else:
            horas = np.arange(anom.shape[0], dtype=np.int32)
        fecha_init = str(d["fecha_init"]) if "fecha_init" in d.files else None
    return anom, lat, lon, horas, fecha_init


def cargar_serie(args, ciclo: str):
    """Devuelve `(serie °C, lat, lon, horas, fecha_init)` de `serie_anom_2t_c.npz`."""
    crudos = _dir_crudos(args, ciclo)
    cache = crudos / "serie_anom_2t_c.npz"
    if not cache.exists():
        raise SystemExit(
            f"No hay datos en {crudos}.\n"
            f"Descargalos con:\n  {_comando_descarga(args)}")
    anom, lat, lon, horas, fecha_init = _cargar_npz(cache)
    _validar_rejilla(lat, lon)
    print(f"Datos: {cache} | {anom.shape[0]} pasos | rejilla {lon.size}x{lat.size}")
    return anom, lat, lon, horas, fecha_init


def _comando_descarga(args) -> str:
    modelo = f"--modelo {args.modelo} " if args.modelo != "ifs" else ""
    return (f".venv\\Scripts\\python.exe descargar\\anomalia_2t_ecmwf.py "
            f"{modelo}--fecha {args.fecha} --ciclo {args.ciclo} "
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


def _rango_caja(campo, filas, columnas) -> tuple[float, float]:
    """Mínimo y máximo del campo dentro de la caja; `(0, 0)` si no la toca."""
    sub = campo[np.ix_(filas, columnas)]
    if not sub.size:
        return 0.0, 0.0
    minimo, maximo = float(np.nanmin(sub)), float(np.nanmax(sub))
    if not (np.isfinite(minimo) and np.isfinite(maximo)):
        return 0.0, 0.0
    return minimo, maximo


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


def render_globo(campo, t_init: datetime, t_valid: datetime, hora: int, min_sa: float,
                 max_sa: float, args, geo: _Geometria, destino: Path) -> Path:
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

    # Superficie base: océano + continentes. La anomalía se pinta encima y deja
    # transparente la banda neutra, así se ve este globo (con el sombreado radial).
    ax.add_patch(mpatches.Circle((0.0, 0.0), radius=r_m, transform=ax.projection,
                                 facecolor=oceano, edgecolor="none", zorder=1))
    try:
        ax.add_feature(cfeature.LAND.with_scale("110m"), facecolor=tierra,
                       edgecolor="none", zorder=2)
    except Exception as exc:
        print(f"AVISO: tierra omitida ({exc})")
    # Anomalía ya warpeada (incluye viñeta en zona neutra), en un único imshow.
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
    fig.text(0.026, 0.912, TITULOS_MODELO[args.modelo],
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
    cmap = ListedColormap(COLORES_ANOM[1:-1])
    cmap.set_under(COLORES_ANOM[0])
    cmap.set_over(COLORES_ANOM[-1])
    norm = BoundaryNorm(NIVELES_C, cmap.N)
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=cax, orientation="horizontal", extend="both")
    cbar.outline.set_visible(True)
    cbar.outline.set_edgecolor("#1e2631")
    cbar.outline.set_linewidth(0.6)
    cbar.set_ticks(TICKS_LEYENDA)
    cbar.set_ticklabels([f"{v:g}" for v in TICKS_LEYENDA])
    cbar.ax.tick_params(colors=TXT, length=3, width=0.8,
                        labelsize=max(6.5, 8.8 * esc), pad=2)
    fig.text(0.916, 0.0635, "°C", color=TXT,
             fontsize=max(7.0, 9.8 * esc), fontweight="bold",
             ha="left", va="center", zorder=11)

    fig.text(0.026, 0.012, FUENTES_MODELO[args.modelo],
             color=TXT_DIM, fontsize=7.4 * esc, ha="left", va="bottom")
    fig.text(0.980, 0.012,
             f"Valid {t_valid:%Y-%m-%d %H:%M} UTC · "
             f"SA Range: {min_sa:+.1f}°C to {max_sa:+.1f}°C",
             color=TXT_DIM, fontsize=7.4 * esc, ha="right", va="bottom")

    # Guardado atómico: nunca queda un PNG truncado que después se reutilice.
    import gc
    parcial = destino.with_suffix(".png.parcial")
    fig.savefig(parcial, format="png", facecolor=BG)
    ax.cla()
    plt.close(fig)
    del fig, ax
    gc.collect()
    parcial.replace(destino)
    return destino


def _sello_render(args) -> str:
    """Huella de los parámetros que cambian el aspecto; invalida cuadros viejos."""
    import hashlib
    datos = {
        "modelo": args.modelo, "px": args.px, "dpi": args.dpi,
        "centro": list(args.centro), "radio": args.radio,
        "fondo": args.fondo_globo, "credito": args.credito,
        "niveles": NIVELES_C, "colores": COLORES_ANOM,
        "banda_neutra": BANDA_NEUTRA,
    }
    return hashlib.sha256(json.dumps(datos, sort_keys=True).encode()).hexdigest()[:16]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Globo Orthographic de anomalía de temperatura a 2 m (°C) de "
                    "ECMWF (IFS o AIFS-SINGLE) 0.25°, con paleta divergente discreta "
                    "y barra de colores.")
    ap.add_argument("--modelo", choices=MODELOS, default="ifs",
                    help="modelo de ECMWF Open Data (por defecto ifs)")
    ap.add_argument("--fecha", default=FECHA,
                    help=f"día UTC de la corrida, YYYY-MM-DD (por defecto {FECHA})")
    ap.add_argument("--ciclo", default=CICLO,
                    help=f"ciclo UTC de la corrida: 00, 06, 12 o 18 (por defecto {CICLO})")
    ap.add_argument("--hasta-hora", type=int, default=HASTA_HORA,
                    help=f"último paso de pronóstico en horas (por defecto {HASTA_HORA})")
    ap.add_argument("--paso", type=int, default=PASO_HORA,
                    help=f"horas entre pasos (por defecto {PASO_HORA})")
    ap.add_argument("--crudos", help="carpeta de crudos/serie de entrada (por defecto, "
                                     "DATOS/crudos_anom2t_<modelo>_<fecha>_<ciclo>z)")
    ap.add_argument("--out-crudos", help="alias de --crudos")
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
    ap.add_argument("--out", help="alias de --salidas")
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
    poster = salidas / (f"poster_anom2t_{args.modelo}_{args.fecha}_{ciclo}z_"
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
    min_sa, max_sa = _rango_caja(serie[ultimo], filas_sa, cols_sa)
    t_valid = t_init + timedelta(hours=hora_final)

    if args.solo_poster:
        inicio = time.time()
        render_globo(serie[ultimo], t_init, t_valid, hora_final, min_sa, max_sa, args,
                     geo, poster)
        print(f"Póster FH +{hora_final}h: {poster} "
              f"({args.px}x{args.px} px, {time.time() - inicio:.1f}s)")
        return 0

    n = len(indices)
    producto = f"anomalia_2t_{args.modelo}"
    frames_dir = salidas / f"frames_{etiqueta_frames(producto, 'globo', t_init, n, args.px)}"
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

    print(f"Anomalía 2t {args.modelo.upper()} | {n} cuadros | "
          f"init {t_init:%Y-%m-%d %H:%M} UTC | "
          f"centro {args.centro[0]} {args.centro[1]} | radio {args.radio:g}° | "
          f"{args.px}x{args.px} px | frames en {frames_dir}")

    inicio = time.time()
    hechos = 0
    for i, (idx, hora) in enumerate(zip(indices, horas_pedidas), 1):
        destino = frames_dir / f"cuadro_{i:03d}.png"
        if not forzar and destino.exists():
            continue
        t_valid_i = t_init + timedelta(hours=hora)
        min_sa_i, max_sa_i = _rango_caja(serie[idx], filas_sa, cols_sa)
        render_globo(serie[idx], t_init, t_valid_i, hora, min_sa_i, max_sa_i, args, geo,
                     destino)
        hechos += 1
        print(f"  {i}/{n} listos ({time.time() - inicio:.0f}s)", flush=True)

    # El póster de cierre se escribe siempre, aun cuando los cuadros ya existían.
    render_globo(serie[ultimo], t_init, t_valid, hora_final, min_sa, max_sa, args, geo,
                 poster)
    print(f"{n} cuadros en {frames_dir} ({hechos} renderizados)")
    print(f"Póster FH +{hora_final}h: {poster}")
    print(f"Armá el video con: .venv\\Scripts\\python.exe animar\\armar.py "
          f"--frames \"{frames_dir}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
