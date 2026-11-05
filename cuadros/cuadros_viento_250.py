"""Renderiza el **viento en 250 mb** y los **extremos de MSLP** de ECMWF en un globo 3D.

Producto: velocidad del viento en 250 mb (en nudos) coloreada con una escala discreta de
10 kt entre 20 y 250, con **streamlines** (líneas de corriente con puntas de flecha) y los
**extremos de la presión a nivel del mar** marcados con `L` (rojo) y `H` (azul).

Lee `serie_viento_250.npz` (lo deja `descargar/viento_250_mslp.py`) con `u_ms`, `v_ms` y
`msl_hpa`. Cada paso se reproyecta a un disco Orthographic con un warp escalar
precomputado **una sola vez** y se pinta con la paleta discreta de la referencia.

El disco se dibuja con `imshow` en la proyección del eje (no `contourf`): el campo se
interpola bilinealmente a resolución de píxel y recién después se mapea a la paleta, así
los bordes de cada intervalo quedan nítidos y el render es rápido. Todo el disco es
opaco: las zonas de viento débil toman el color "under" (el claro de la referencia).

Las streamlines se calculan con `matplotlib.pyplot.streamplot` sobre una rejilla
regular de ~1° y una **figura temporal** (no sobre los ejes de cartopy): los segmentos
se transforman a coordenadas de proyección y se dibujan como un único `LineCollection`
en el disco, con las puntas de flecha dibujadas a mano como un `PathPatch` compuesto.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe cuadros\\cuadros_viento_250.py --solo-poster --px 2712
    .venv\\Scripts\\python.exe cuadros\\cuadros_viento_250.py --hasta-hora 144 --paso 6
    .venv\\Scripts\\python.exe cuadros\\cuadros_viento_250.py --help   # no toca la red

Salidas: `poster_viento250_<fecha>_<ciclo>z_fh<hora>.png` y, en la corrida completa,
`frames_<etiqueta>/cuadro_NNN.png` (1-based, como espera `animar/armar.py`).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
sys.path.insert(0, str(RAIZ))
from rutas import DATOS, SALIDAS  # noqa: E402
from series import etiqueta_frames  # noqa: E402

# ---------------------------------------------------------------- escala y paleta
# 24 bordes = 23 intervalos entre 20 y 250 kt, más under (< 20) y over (> 250).
NIVELES_KT = [20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 170,
              180, 190, 200, 210, 220, 230, 240, 250]
NIVELES_KT_F32 = np.asarray(NIVELES_KT, dtype=np.float32)

# Paleta discreta de la imagen de referencia: cian -> verde -> amarillo -> naranja ->
# rojo -> bordó -> violeta -> magenta -> rosa -> marrón. Son 25 colores: [0] under
# (< 20 kt), [1..23] los 23 intervalos, [24] over (> 250 kt).
COLORES_KT = [
    "#e8f2f6",                                                        # under (< 20)
    # cian -> verde -> amarillo 20..90 kt (7)
    "#8ce8ec", "#3ed2e4", "#20b4d0", "#28b878", "#1f9c50", "#6cc800", "#c8d400",
    # naranja -> rojo -> bordó 90..150 kt (6)
    "#f0bc00", "#f08c00", "#ee5c00", "#e02000", "#a80018", "#78007a",
    # violeta -> magenta -> rosa 150..220 kt (9)
    "#9a1cb8", "#b84ad0", "#d478c4", "#e69ac8", "#eeb4cc", "#dcb2b8", "#a47a80",
    "#5e3030", "#401c1c",
    # marrón 220..250 kt (2) + over (> 250)
    "#2a1010", "#1a0a0a",
]
COLORES_U8 = np.array([[int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)]
                       for c in COLORES_KT], dtype=np.uint8)
# Tabla RGBA (26 x 4): 0..24 son los colores de la paleta, 25 = fuera del disco.
TABLA_RGBA = np.zeros((len(COLORES_KT) + 1, 4), dtype=np.uint8)
TABLA_RGBA[:len(COLORES_KT), :3] = COLORES_U8
TABLA_RGBA[:len(COLORES_KT), 3] = 255
TICKS_LEYENDA = [20, 40, 60, 80, 100, 120, 140, 160, 180, 200, 220, 240, 250]

# ------------------------------------------------------------------ configuración
FECHA = "2026-10-20"                   # UTC: día de la corrida
CICLO = "18"                           # UTC: 00, 06, 12 o 18
HASTA_HORA = 144                       # último paso de pronóstico (6 días)
PASO_HORA = 6                          # horas entre pasos
PX = 2712                              # lado del rectángulo donde se warpea el disco
DPI = 140
CENTRO = [-58.0, -23.0]                # Paraguay / corazón de Sudamérica
RADIO = 58.0                           # grados al borde del disco (90 = hemisferio)
FONDO_GLOBO = "claro"
CREDITO = "Graphic by @Gillo97"

# Rótulos y carpeta de crudos por fuente. El render es el mismo para las dos.
FUENTES = {
    "ifs": {
        "etiqueta": "IFS 0.25°",
        "subtitulo": "ECMWF IFS 0.25° · 250 mb WIND SPEED (kt) & MSLP EXTREMA",
        "fuente": "Source: ECMWF Open Data · IFS HRES 0.25° (oper)",
        "carpeta": "crudos_viento250_{fecha}_{ciclo}z",
    },
    "gfs": {
        "etiqueta": "GFS 0.25°",
        "subtitulo": "GFS 0.25° · 250 mb WIND SPEED (kt) & MSLP EXTREMA",
        "fuente": "Source: NOAA GFS 0.25° · AWS Open Data",
        "carpeta": "crudos_viento250_gfs_{fecha}_{ciclo}z",
    },
}

# Rejilla del IFS 0.25°: 1440 x 721, de 90°N a 90°S y de 180°W a 179.75°E.
FILAS, COLUMNAS = 721, 1440

# Factor de m/s a nudos (1 kn = 0.514444 m/s).
MS_A_KT = 1.9438445

# Streamlines: rejilla regular de ~1°, densidad y tamaño de las puntas de flecha.
PASO_FLUJO = 4                         # 4 celdas de 0.25° = 1°
DENSIDAD_FLUJO = 4.0
CADA_PUNTA = 26                        # puntos entre puntas de flecha
LARGO_PUNTA_PX = 11.0                  # largo de la punta de flecha (px a 2712)
ANCHO_PUNTA_PX = 4.0                   # semi-ancho de la punta de flecha (px a 2712)
COLOR_FLUJO = "#22303c"

# Extremos de MSLP: sólo los más significativos, con separación mínima.
UMBRAL_BAJO = 1002.0                   # hPa: un L por debajo de esto cuenta
UMBRAL_ALTO = 1016.0                   # hPa: un H por encima de esto cuenta
MAX_EXTREMOS = 6                       # como mucho 6 L y 6 H
SEPARACION_EXTREMOS = 4.0              # grados entre dos marcadores
VECINDAD_EXTREMOS = 1.5                # grados de la ventana de mínimo/máximo local
COLOR_BAJO, COLOR_ALTO = "#d02020", "#2050d0"

# Fondo y vestuario del póster (compartidos en comun/estilo.py).
BG = "#0c1014"
TXT, TXT_DIM = "#ffffff", "#c9cfd6"
ESPESOR_BORDE_PY = 1.1
BORDE_SA = str(RAIZ / "datos" / "paraguay_gadm.json")

# Filas por bloque en el warp: acota el pico de RAM del blend bilineal.
BLOQUE = 512


# ------------------------------------------------------------------ geometría warp
class _Geometria:
    """Índices y pesos del warp inverso Orthographic, precomputados una sola vez.

    Para cada píxel del disco guarda las cuatro esquinas del campo origen
    (`f0/f1` filas, `c0/c1` columnas) y los pesos bilineales (`ff`, `fc`), más la
    máscara del disco. Con esto cada cuadro cuesta sólo cuatro lecturas + una mezcla,
    sin recalcular trigonometría.

    Todo es **float32** y la mezcla va **por bloques de filas**: a 2712x2712 px, un
    blend entero en float64 dispara el consumo de RAM (y el OOM) por los temporales.
    """

    __slots__ = ("lado", "f0", "f1", "c0", "c1", "ff", "fc", "dentro", "rho")

    def __init__(self, lado, centro, radio, filas, columnas, cuadrado=False):
        lon0 = np.float32(np.radians(centro[0]))
        lat0 = np.float32(np.radians(centro[1]))

        # Disco normalizado en float32 para no saturar RAM/swap en resoluciones 2712x2712.
        # Con `cuadrado` se muestrea todo el cuadro (las esquinas incluidas): es el
        # encuadre plano de "Solo Paraguay", sin el recorte circular del globo.
        y = np.linspace(1.0, -1.0, lado, dtype=np.float32)
        x = np.linspace(-1.0, 1.0, lado, dtype=np.float32)
        X, Y = np.meshgrid(x, y)
        rho = np.hypot(X, Y)
        dentro = np.ones_like(rho, dtype=bool) if cuadrado else (rho <= 1.0)

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
        """RGBA del campo: color discreto de la paleta, opaco dentro del disco.

        Indexado directo 2D sobre `TABLA_RGBA` (sin máscaras booleanas 1D) y por bloques
        de filas, para que el consumo de RAM sea plano a 2712x2712 px.
        """
        lado = self.lado
        rgba = np.zeros((lado, lado, 4), dtype=np.uint8)
        for ini in range(0, lado, BLOQUE):
            fin = min(ini + BLOQUE, lado)
            vals = self._bloque(campo, ini, fin)
            # `searchsorted(..., "right")` ya da 0 (under) .. 24 (over).
            idx = np.searchsorted(NIVELES_KT_F32, vals, side="right")
            idx[~self.dentro[ini:fin]] = len(COLORES_KT)   # fuera del disco
            rgba[ini:fin] = TABLA_RGBA[idx]
            del vals, idx
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
    """Carpeta de entrada: `--crudos` > valor por defecto (uno por modelo)."""
    if args.crudos:
        return Path(args.crudos)
    carpeta = FUENTES[args.modelo]["carpeta"].format(fecha=args.fecha, ciclo=ciclo)
    return DATOS / carpeta


def _dir_salidas(args) -> Path:
    """Carpeta de salida: `--salidas` > SALIDAS."""
    if args.salidas:
        return Path(args.salidas)
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
    """`2026-10-20T18:00Z` -> datetime (con zona UTC si trae la Z)."""
    if not texto:
        return None
    try:
        return datetime.fromisoformat(str(texto).replace("Z", "+00:00"))
    except ValueError:
        return None


def _cargar_npz(ruta: Path):
    """Lee `u_ms`, `v_ms`, `msl_hpa`, `lat`, `lon`, `horas` y `fecha_init` de un `.npz`."""
    with np.load(ruta, allow_pickle=False) as d:
        for clave in ("u_ms", "v_ms", "msl_hpa"):
            if clave not in d.files:
                raise SystemExit(f"{ruta.name}: no trae {clave!r}.")
        u = np.asarray(d["u_ms"], dtype=np.float32)
        v = np.asarray(d["v_ms"], dtype=np.float32)
        msl = np.asarray(d["msl_hpa"], dtype=np.float32)
        lat = np.asarray(d["lat"], dtype=np.float32)
        lon = np.asarray(d["lon"], dtype=np.float32)
        if "horas" in d.files:
            horas = np.asarray(d["horas"], dtype=np.int32)
        else:
            horas = np.arange(u.shape[0], dtype=np.int32)
        fecha_init = str(d["fecha_init"]) if "fecha_init" in d.files else None
    return u, v, msl, lat, lon, horas, fecha_init


def cargar_serie(args, ciclo: str):
    """Devuelve `(u, v, msl, lat, lon, horas, fecha_init)` de `serie_viento_250.npz`."""
    crudos = _dir_crudos(args, ciclo)
    cache = crudos / "serie_viento_250.npz"
    if not cache.exists():
        raise SystemExit(
            f"No hay datos en {crudos}.\n"
            f"Descargalos con:\n  {_comando_descarga(args)}")
    u, v, msl, lat, lon, horas, fecha_init = _cargar_npz(cache)
    _validar_rejilla(lat, lon)
    print(f"Datos: {cache} | {u.shape[0]} pasos | rejilla {lon.size}x{lat.size}")
    return u, v, msl, lat, lon, horas, fecha_init


def _comando_descarga(args) -> str:
    return (f".venv\\Scripts\\python.exe descargar\\viento_250_mslp.py "
            f"--fecha {args.fecha} --ciclo {args.ciclo} "
            f"--hasta-hora {args.hasta_hora} --paso {args.paso}")


def _kt_de(u: np.ndarray, v: np.ndarray, idx: int) -> np.ndarray:
    """Velocidad del viento (kt) del paso `idx`: `hypot(u, v)` en m/s -> nudos."""
    return np.hypot(u[idx], v[idx]).astype(np.float32) * np.float32(MS_A_KT)


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


# ------------------------------------------------------------------- streamlines
def _segmentos_flujo(u_ms: np.ndarray, v_ms: np.ndarray, lat: np.ndarray,
                      lon: np.ndarray) -> list[np.ndarray]:
    """Streamlines del viento en (lon, lat) sobre una rejilla regular de ~1°.

    `streamplot` se corre sobre una **figura temporal** (no sobre los ejes de
    cartopy): se le pasa la rejilla global en lon/lat y después se leen los segmentos.
    `arrowsize=0` desactiva las flechas de matplotlib: las puntas se dibujan a mano
    (en coordenadas de proyección) para que respeten la escala del disco.
    """
    import matplotlib.pyplot as plt

    # `u[::-1][::PASO, ::PASO]`: primero se da vuelta la latitud (de 90→-90 a -90→90) y
    # después se submuestrea en ambos ejes (cada 4 celdas de 0.25° = 1°).
    u = np.ascontiguousarray(u_ms[::-1][::PASO_FLUJO, ::PASO_FLUJO], dtype=np.float32)
    v = np.ascontiguousarray(v_ms[::-1][::PASO_FLUJO, ::PASO_FLUJO], dtype=np.float32)
    lat_g = np.ascontiguousarray(lat[::-1][::PASO_FLUJO], dtype=np.float64)
    lon_g = np.ascontiguousarray(lon[::PASO_FLUJO], dtype=np.float64)

    fig = plt.figure(figsize=(8.0, 4.0), dpi=100)
    eje = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    try:
        with warnings.catch_warnings():
            # `arrowsize=0` hace que matplotlib divida por cero al armar la flecha
            # (que no se ve nunca): el aviso es ruido, no un problema.
            warnings.simplefilter("ignore", RuntimeWarning)
            sp = eje.streamplot(lon_g, lat_g, u, v, density=DENSIDAD_FLUJO,
                                 arrowsize=0)
        segmentos = [np.asarray(s, dtype=np.float64) for s in sp.lines.get_segments()]
    finally:
        plt.close(fig)
    return [s for s in segmentos if s.shape[0] >= 2]


def _transformar_segmentos(ax, segmentos: list[np.ndarray]) -> list[np.ndarray]:
    """Pasa los segmentos de (lon, lat) a coordenadas de proyección.

    Los puntos del hemisferio invisible salen como NaN: esos segmentos se descartan
    (quedaría una línea cortada al borde del disco).
    """
    import cartopy.crs as ccrs

    fuera: list[np.ndarray] = []
    for seg in segmentos:
        res = ax.projection.transform_points(ccrs.PlateCarree(), seg[:, 0], seg[:, 1])
        x, y = res[:, 0], res[:, 1]
        if not (np.isfinite(x).all() and np.isfinite(y).all()):
            continue
        fuera.append(np.column_stack([x, y]))
    return fuera


def _vertices_puntas(segmentos: list[np.ndarray], px_por_unidad: float,
                     cada: int = CADA_PUNTA) -> tuple[np.ndarray, np.ndarray]:
    """Vértices y códigos de un `Path` compuesto con todas las puntas de flecha.

    Cada punta es un triángulo lleno, orientado en la dirección local de la línea: la
    punta ahead del avance y la base atrás. El tamaño se define en **píxeles** (a
    2712 px) y se convierte a datos con la escala real de los ejes.
    """
    from matplotlib.path import Path as MplPath

    largo = LARGO_PUNTA_PX / px_por_unidad
    semi = ANCHO_PUNTA_PX / px_por_unidad
    vertices: list[tuple[float, float]] = []
    codes: list[int] = []
    for seg in segmentos:
        n = seg.shape[0]
        for i in range(cada, n - 1, cada):
            p = seg[i]
            if i > 0:
                d = seg[i + 1] - seg[i - 1]
            else:
                d = seg[i + 1] - seg[i]
            norma = float(np.hypot(d[0], d[1]))
            if not np.isfinite(norma) or norma <= 0.0:
                continue
            d = d / norma
            perp = np.array([-d[1], d[0]])
            punta = p + d * (largo * 0.5)
            base = p - d * (largo * 0.5)
            b1 = base + perp * semi
            b2 = base - perp * semi
            vertices.extend([(float(punta[0]), float(punta[1])),
                             (float(b1[0]), float(b1[1])),
                             (float(b2[0]), float(b2[1])),
                             (float(punta[0]), float(punta[1]))])
            codes.extend([MplPath.MOVETO, MplPath.LINETO, MplPath.LINETO,
                          MplPath.CLOSEPOLY])
    if not vertices:
        return np.zeros((0, 2), dtype=np.float64), np.zeros(0, dtype=np.uint8)
    return (np.asarray(vertices, dtype=np.float64),
            np.asarray(codes, dtype=np.uint8))


# ------------------------------------------------------------------ extremos MSLP
def _suavizar_3x3(campo: np.ndarray) -> np.ndarray:
    """Filtro de caja 3x3 (borde por extensión) sobre el campo de presión."""
    p = np.pad(campo, 1, mode="edge")
    filas, columnas = campo.shape
    acc = np.zeros((filas, columnas), dtype=np.float32)
    for di in (0, 1, 2):
        for dj in (0, 1, 2):
            acc += p[di:di + filas, dj:dj + columnas]
    return (acc / np.float32(9.0)).astype(np.float32)


def _filtro_ventana(campo: np.ndarray, r: int, es_max: bool) -> np.ndarray:
    """Máximo (o mínimo) en una ventana cuadrada de `(2r+1)x(2r+1)` celdas.

    El filtro es **separable** (primero en longitud, después en latitud), así que
    cuesta 4·r comparaciones en vez de (2r+1)². La longitud es periódica (la rejilla
    es global) y la latitud se trata con borde.
    """
    op = np.maximum if es_max else np.minimum
    acc = campo
    for k in range(1, r + 1):
        acc = op(acc, np.roll(campo, k, axis=1))
        acc = op(acc, np.roll(campo, -k, axis=1))
    p = np.pad(acc, ((r, r), (0, 0)), mode="edge")
    filas = campo.shape[0]
    out = p[r:r + filas, :]
    for k in range(1, r + 1):
        out = op(out, p[r - k:r - k + filas, :])
        out = op(out, p[r + k:r + k + filas, :])
    return out


def _separacion_grados(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia angular en grados entre dos puntos de la esfera."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dl = np.radians(lon2 - lon1)
    a = (np.sin((p2 - p1) * 0.5) ** 2
         + np.cos(p1) * np.cos(p2) * np.sin(dl * 0.5) ** 2)
    return float(2.0 * np.degrees(np.arcsin(min(1.0, np.sqrt(a)))))


def _dentro_disco(lon: float, lat: float, centro, radio: float) -> bool:
    """True si el punto cae dentro del disco visible (distancia angular < radio)."""
    c = np.radians(centro[1])
    l = np.radians(lat)
    dl = np.radians(lon - centro[0])
    cos_c = np.sin(c) * np.sin(l) + np.cos(c) * np.cos(l) * np.cos(dl)
    return bool(cos_c >= np.cos(np.radians(radio)))


def _extremos_mslp(msl_hpa: np.ndarray, lat: np.ndarray, lon: np.ndarray, centro,
                   radio: float):
    """`(lista de L, lista de H)` con `(valor hPa, lat, lon)`.

    Se suaviza la presión con un filtro de caja 3x3 y se buscan los mínimos y máximos
    locales en una ventana de ~1.5°. Sólo pasan los L por debajo de 1002 hPa y los H
    por encima de 1016 hPa, y de cada tipo se quedan los más intensos (con separación
    mínima entre ellos) y como mucho 6.
    """
    suave = _suavizar_3x3(msl_hpa)
    paso_celda = 0.25
    r = max(1, int(round(VECINDAD_EXTREMOS / paso_celda)))
    min_vent = _filtro_ventana(suave, r, es_max=False)
    max_vent = _filtro_ventana(suave, r, es_max=True)
    es_min = (suave <= min_vent + np.float32(1e-3)) & (suave < np.float32(UMBRAL_BAJO))
    es_max = (suave >= max_vent - np.float32(1e-3)) & (suave > np.float32(UMBRAL_ALTO))

    salida: dict[str, list[tuple[float, float, float]]] = {"L": [], "H": []}
    for tipo, mascara, orden in (("L", es_min, True), ("H", es_max, False)):
        for fila, columna in np.argwhere(mascara):
            valor = float(suave[fila, columna])
            la = float(lat[fila])
            lo = float(lon[columna])
            # Fuera del disco visible no se dibuja el marcador: no se cuenta.
            if not _dentro_disco(lo, la, centro, radio):
                continue
            salida[tipo].append((valor, la, lo))
        # Más intenso primero: el L más bajo, el H más alto.
        salida[tipo].sort(key=lambda t: t[0], reverse=not orden)
        elegidos: list[tuple[float, float, float]] = []
        for valor, la, lo in salida[tipo]:
            if len(elegidos) >= MAX_EXTREMOS:
                break
            if any(_separacion_grados(la, lo, la2, lo2) < SEPARACION_EXTREMOS
                   for _, la2, lo2 in elegidos):
                continue
            elegidos.append((valor, la, lo))
        salida[tipo] = elegidos
    return salida["L"], salida["H"]


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


def render_globo(u_ms: np.ndarray, v_ms: np.ndarray, msl_hpa: np.ndarray,
                 lat: np.ndarray, lon: np.ndarray, t_init: datetime,
                 t_valid: datetime, hora: int, max_kt: float, args, geo: _Geometria,
                 destino: Path) -> Path:
    """Dibuja un cuadro/póster completo del globo y lo guarda en `destino`."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import matplotlib.patheffects as patheffects
    from matplotlib.collections import LineCollection
    from matplotlib.colors import BoundaryNorm, ListedColormap
    from matplotlib.path import Path as MplPath
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    from estilo import MONTHS_EN

    lon0, lat0 = args.centro
    limpio = getattr(args, "limpio", False)
    lado_fig = args.px / args.dpi
    fig = plt.figure(figsize=(lado_fig, lado_fig), dpi=args.dpi)
    fig.patch.set_facecolor(BG)

    if args.fondo_globo == "oscuro":
        oceano, tierra = "#101720", "#1b2430"
    else:
        oceano, tierra = "#dce6f0", "#f4f6f8"

    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0] if limpio
                      else [0.014, 0.014, 0.972, 0.972],
                      projection=ccrs.Orthographic(central_longitude=lon0,
                                                   central_latitude=lat0))
    # En limpio el cuadro se llena con el océano: las esquinas del recorte plano
    # quedan fuera del disco y tienen que verse como superficie, no como fondo negro.
    ax.set_facecolor(oceano if limpio else BG)
    ax.spines["geo"].set_visible(False)

    # Geometría del recorte: el borde del disco cae a `radio` grados del centro.
    # `x_limits` hay que leerlo ANTES de achicar la vista (después devuelve el nuevo).
    R = float(ax.projection.x_limits[1])
    r_m = R * np.sin(np.radians(args.radio))
    ax.set_xlim(-r_m, r_m)
    ax.set_ylim(-r_m, r_m)
    clip = None
    if not limpio:
        # El círculo de recorte se instala como *boundary* del eje: `FeatureArtist.draw`
        # reemplaza cualquier `set_clip_path` propio por `axes.patch`, así que la única forma
        # de recortar costas/fronteras/tierra al disco es que el patch del eje sea el círculo.
        ang = np.linspace(0.0, 2.0 * np.pi, 361)
        ax.set_boundary(MplPath(np.column_stack([r_m * np.cos(ang), r_m * np.sin(ang)])),
                        transform=ax.transData)
        # Mismo círculo para recortar colecciones que no pasan por `FeatureArtist`
        # (el contorno de Paraguay, las streamlines): hay que atarlo al eje para resolver
        # su transform.
        clip = mpatches.Circle((0.0, 0.0), radius=r_m, transform=ax.projection)
        ax.add_patch(clip)
        clip.set_visible(False)

    # Superficie base: océano + continentes (queda tapada por el campo de viento, que
    # es opaco, pero delimita el limbo del disco).
    if not limpio:
        ax.add_patch(mpatches.Circle((0.0, 0.0), radius=r_m, transform=ax.projection,
                                     facecolor=oceano, edgecolor="none", zorder=1))
    try:
        ax.add_feature(cfeature.LAND.with_scale("110m"), facecolor=tierra,
                       edgecolor="none", zorder=2)
    except Exception as exc:
        print(f"AVISO: tierra omitida ({exc})")

    # Velocidad del viento ya warpeada, a resolución plena y con bordes nítidos.
    kt = (np.hypot(u_ms, v_ms).astype(np.float32) * np.float32(MS_A_KT))
    ax.imshow(geo.disco_rgba(kt), origin="upper",
              extent=[-r_m, r_m, -r_m, r_m], transform=ax.projection,
              interpolation="nearest", zorder=3)

    if not limpio:
        try:
            ax.add_feature(cfeature.COASTLINE.with_scale("110m"), linewidth=0.65,
                           edgecolor="#111111", zorder=3.5)
            ax.add_feature(cfeature.BORDERS.with_scale("110m"), linewidth=0.45,
                           edgecolor="#222222", zorder=3.5)
        except Exception as exc:
            print(f"AVISO: costas/fronteras omitidas ({exc})")

    # ---------------------------------------------------------------- streamlines
    segmentos = _segmentos_flujo(u_ms, v_ms, lat, lon)
    transformados = _transformar_segmentos(ax, segmentos)
    if transformados:
        flujo = LineCollection(transformados, colors=COLOR_FLUJO, linewidths=0.35,
                              transform=ax.transData, zorder=4)
        if clip is not None:
            flujo.set_clip_path(clip)
        ax.add_collection(flujo)

        # Escala real de los ejes: px por unidad de dato (para las puntas de flecha).
        p0 = ax.transData.transform((0.0, 0.0))
        p1 = ax.transData.transform((1.0, 0.0))
        px_por_unidad = abs(float(p1[0] - p0[0])) or 1.0
        vertices, codigos = _vertices_puntas(transformados, px_por_unidad)
        if vertices.size:
            puntas = mpatches.PathPatch(MplPath(vertices, codigos),
                                        facecolor=COLOR_FLUJO, edgecolor="none",
                                        zorder=5, transform=ax.transData)
            if clip is not None:
                puntas.set_clip_path(clip)
            ax.add_patch(puntas)

    borde = _borde_geojson(ax, BORDE_SA, "#000000", ESPESOR_BORDE_PY, zorder=6)
    if borde is not None and clip is not None:
        borde.set_clip_path(clip)

    if not limpio:
        # Aro exterior del globo, para separar el disco del fondo del póster.
        ax.add_patch(mpatches.Circle((0.0, 0.0), radius=r_m, transform=ax.projection,
                                     facecolor="none", edgecolor="#3a4659",
                                     linewidth=1.0, zorder=6))

    # ------------------------------------------------------------ extremos MSLP
    lows, highs = _extremos_mslp(msl_hpa, lat, lon, args.centro, args.radio)
    esc = 0.8 * (args.px / 720.0) ** 0.45
    trazo = [patheffects.withStroke(linewidth=1.8, foreground="#ffffff")]
    for tipo, lista, color in (("L", lows, COLOR_BAJO), ("H", highs, COLOR_ALTO)):
        for valor, la, lo in lista:
            res = ax.projection.transform_points(ccrs.PlateCarree(),
                                                  np.array([lo]), np.array([la]))
            x, y = float(res[0, 0]), float(res[0, 1])
            if not (np.isfinite(x) and np.isfinite(y)):
                continue
            ax.annotate(f"{valor:.0f}", xy=(x, y), xytext=(0, 7),
                        textcoords="offset points", color=color,
                        fontsize=10.5 * esc, fontweight="bold", ha="center",
                        va="bottom", zorder=7, path_effects=trazo)
            ax.annotate(tipo, xy=(x, y), xytext=(0, -7),
                        textcoords="offset points", color=color,
                        fontsize=13.0 * esc, fontweight="bold", ha="center",
                        va="top", zorder=7, path_effects=trazo)

    if limpio:
        # Captura limpia: el campo, el flujo y el contorno del país; sin aro, leyenda
        # ni rótulos de póster.
        import gc
        parcial = destino.with_suffix(".png.parcial")
        fig.savefig(parcial, format="png", facecolor=BG)
        ax.cla()
        plt.close(fig)
        del fig, ax
        gc.collect()
        parcial.replace(destino)
        return destino

    # --------------------------------------------------------------- vestuario
    halo = [patheffects.withStroke(linewidth=3.2 * esc, foreground=BG)]
    fig.text(0.026, 0.985, f"{MONTHS_EN[t_valid.month - 1]} {t_valid.year}", color=TXT,
             fontsize=19 * esc, fontweight="bold", ha="left", va="top",
             path_effects=halo, zorder=11)
    fig.text(0.026, 0.946,
             f"Init {t_init:%d %b %Y %H:%M} UTC · Valid {t_valid:%d %b %Y %H:%M} UTC "
             f"(FH +{hora:03d}h)",
             color=TXT, fontsize=13.5 * esc, fontweight="bold", ha="left", va="top",
             path_effects=halo, zorder=11)
    fig.text(0.026, 0.912, FUENTES[args.modelo]["subtitulo"],
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
    cmap = ListedColormap(COLORES_KT[1:-1])
    cmap.set_under(COLORES_KT[0])
    cmap.set_over(COLORES_KT[-1])
    norm = BoundaryNorm(NIVELES_KT, cmap.N)
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
    fig.text(0.916, 0.0635, "kt", color=TXT,
             fontsize=max(7.0, 9.8 * esc), fontweight="bold",
             ha="left", va="center", zorder=11)

    fig.text(0.026, 0.012, FUENTES[args.modelo]["fuente"], color=TXT_DIM,
             fontsize=7.4 * esc,
             ha="left", va="bottom")
    fig.text(0.980, 0.012,
             f"Valid {t_valid:%Y-%m-%d %H:%M} UTC · Max wind: {max_kt:.0f} kt",
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
        "px": args.px, "dpi": args.dpi,
        "centro": list(args.centro), "radio": args.radio,
        "fondo": args.fondo_globo, "credito": args.credito,
        "limpio": getattr(args, "limpio", False),
        "niveles": NIVELES_KT, "colores": COLORES_KT,
        "densidad": DENSIDAD_FLUJO, "umbrales": [UMBRAL_BAJO, UMBRAL_ALTO],
    }
    return hashlib.sha256(json.dumps(datos, sort_keys=True).encode()).hexdigest()[:16]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Globo Orthographic del viento en 250 mb (kt) de ECMWF IFS 0.25° "
                    "con streamlines y extremos de MSLP (L/H).")
    ap.add_argument("--modelo", choices=tuple(FUENTES), default="ifs",
                    help="fuente del pronóstico: ifs (ECMWF) o gfs (NOAA)")
    ap.add_argument("--fecha", default=FECHA,
                    help=f"día UTC de la corrida, YYYY-MM-DD (por defecto {FECHA})")
    ap.add_argument("--ciclo", default=CICLO,
                    help=f"ciclo UTC de la corrida: 00, 06, 12 o 18 (por defecto {CICLO})")
    ap.add_argument("--hasta-hora", type=int, default=HASTA_HORA,
                    help=f"último paso de pronóstico en horas (por defecto {HASTA_HORA})")
    ap.add_argument("--paso", type=int, default=PASO_HORA,
                    help=f"horas entre pasos (por defecto {PASO_HORA})")
    ap.add_argument("--crudos", help="carpeta de crudos/serie de entrada (por defecto, "
                                     "DATOS/crudos_viento250[_<modelo>]_<fecha>_<ciclo>z)")
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
    ap.add_argument("--limpio", action="store_true",
                    help="captura limpia: sólo el dato y el contorno, sin títulos, "
                         "leyenda, costas ni aro")
    ap.add_argument("--credito", default=CREDITO, help="crédito de la esquina superior")
    ap.add_argument("--solo-poster", action="store_true",
                    help="renderiza sólo el póster estático del último paso")
    ap.add_argument("--forzar", action="store_true",
                    help="vuelve a renderizar los cuadros aunque los PNG ya existan")
    ap.add_argument("--salidas", help="carpeta de salida (por defecto comun.rutas.SALIDAS)")
    args = ap.parse_args(argv)

    ciclo = _ciclo_valido(args.ciclo)
    try:
        datetime.fromisoformat(args.fecha)
    except ValueError:
        raise SystemExit(f"--fecha inválido: {args.fecha!r} (se espera YYYY-MM-DD).")
    if not (0.0 < args.radio <= 90.0):
        raise SystemExit(f"--radio debe estar en (0, 90] (recibí {args.radio}).")
    if args.px < 64 or args.dpi < 24:
        raise SystemExit("--px/--dpi demasiado chicos.")
    _pasos(args.hasta_hora, args.paso)

    salidas = _dir_salidas(args)
    salidas.mkdir(parents=True, exist_ok=True)
    sufijo_modelo = "" if args.modelo == "ifs" else f"_{args.modelo}"
    poster = salidas / (f"poster_viento250{sufijo_modelo}_{args.fecha}_{ciclo}z_"
                        f"fh{args.hasta_hora:03d}.png")

    u, v, msl, lat, lon, horas, fecha_init = cargar_serie(args, ciclo)
    indices, horas_pedidas = _seleccionar(horas, args.hasta_hora, args.paso)

    t_init = _parse_init(fecha_init)
    if t_init is None:
        t_init = datetime.fromisoformat(args.fecha).replace(hour=int(ciclo))

    geo = _Geometria(args.px, args.centro, args.radio, lat.size, lon.size,
                     cuadrado=getattr(args, "limpio", False))
    ultimo = indices[-1]
    hora_final = horas_pedidas[-1]
    t_valid = t_init + timedelta(hours=hora_final)

    if args.solo_poster:
        inicio = time.time()
        kt = _kt_de(u, v, ultimo)
        render_globo(u[ultimo], v[ultimo], msl[ultimo], lat, lon, t_init, t_valid,
                     hora_final, float(kt.max()), args, geo, poster)
        print(f"Póster FH +{hora_final}h: {poster} "
              f"({args.px}x{args.px} px, {time.time() - inicio:.1f}s)")
        return 0

    n = len(indices)
    frames_dir = salidas / (
        f"frames_{etiqueta_frames('viento_250' + sufijo_modelo, 'globo', t_init, n, args.px)}"
    )
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

    print(f"Viento 250 mb {FUENTES[args.modelo]['etiqueta']} | {n} cuadros | "
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
        kt = _kt_de(u, v, idx)
        render_globo(u[idx], v[idx], msl[idx], lat, lon, t_init, t_valid_i, hora,
                     float(kt.max()), args, geo, destino)
        hechos += 1
        print(f"  {i}/{n} listos ({time.time() - inicio:.0f}s)", flush=True)

    # El póster de cierre se escribe siempre, aun cuando los cuadros ya existían.
    kt = _kt_de(u, v, ultimo)
    render_globo(u[ultimo], v[ultimo], msl[ultimo], lat, lon, t_init, t_valid,
                 hora_final, float(kt.max()), args, geo, poster)
    print(f"{n} cuadros en {frames_dir} ({hechos} renderizados)")
    print(f"Póster FH +{hora_final}h: {poster}")
    print(f"Armá el video con: .venv\\Scripts\\python.exe animar\\armar.py "
          f"--frames \"{frames_dir}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
