"""Póster *realista* de la banda 13 de GOES-19, con el diseño nuevo del MUR.

Archivo NUEVO: no modifica el pipeline existente (`poster_goes.py`, `cuadros_c13_ir.py`
y compañía siguen igual). Toma el diseño aprobado en `prototipos/poster_mur_realista.py`
—fondo blanco, globo Orthographic inscripto, sombra exterior difusa, limbo sombreado,
retículo tenue y tarjeta de leyenda con la distribución y la barra de color— y lo aplica
a la temperatura de brillo del ABI en lugar de la anomalía de SST.

Diferencias con el póster MUR (las impone el dato):

  * El insumo no es un JPEG de GIBS sino el `.nc` ABI L2 CMIP: el campo se colorea y se
    reproyecta a mano (mismo mapeo inverso que el MUR), sin pasar por `pcolormesh`.
  * El disco de un geostacionario no llega al horizonte Orthographic y en el limbo el
    dato se estira y se corta en escalera. El encuadre se deduce del centro elegido
    (`--centro`, por defecto el aprobado -73 / -18) para que TODO el disco caiga en la
    zona con dato completo: así el borde es un círculo limpio.
  * La rampa por defecto es `clean_ir` (la de NASA Worldview) con su rango físico fijo,
    para que los frames de la animación no cambien de escala.

Reutiliza `comun/goes_lectura.py` (lectura + rótulos), `comun/paleta_gibs.py` (rampa) y el
sombreado y la sombra del prototipo MUR (misma familia visual, una sola fuente).

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe prototipos\\poster_goes_realista.py
    .venv\\Scripts\\python.exe prototipos\\poster_goes_realista.py --nc "...\\OR_ABI-....nc"
    .venv\\Scripts\\python.exe prototipos\\poster_goes_realista.py --px 2712 --paleta clean_ir
    .venv\\Scripts\\python.exe prototipos\\poster_goes_realista.py --frames "D:\\...\\frames_x" --n 24
    .venv\\Scripts\\python.exe prototipos\\poster_goes_realista.py --help   # no toca la red
"""
from __future__ import annotations

import argparse
import gc
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
sys.path.insert(0, str(RAIZ / "prototipos"))

from goes_lectura import PATRON, cargar  # noqa: E402
from paleta_gibs import CMAP_GIBS_CLEAN_IR, VMAX as VMAX_GIBS, VMIN as VMIN_GIBS  # noqa: E402
from poster_mur_realista import sombra_exterior  # noqa: E402
from rutas import DATOS, SALIDAS  # noqa: E402

# ------------------------------------------------------------------------ constantes
# Geometría del elipsoide/satélite: el ABI publica la altura del punto de perspectiva.
R_EARTH = 6_378_137.0
SAT, BANDA = "G19", "C13"

# Proporción del radio visible (horizonte geostacionario) que se conserva cuando se
# fuerza `--recorte`. Por defecto se deduce del encuadre (ver `radio_visible`).
RECORTE = None

# Hasta dónde llega el borde del disco, medido como ángulo central desde el subpunto
# del satélite. El full disk tiene el 100 % de los píxeles válidos hasta ~75.6°
# (medido sobre el slot 2026-10-24 18:00); 73.3° deja margen para que el borde no toque
# la franja de píxeles mezclados con espacio.
LIMBO_DEG = 73.3

# Encuadre: la proyección del póster anterior (centro -73/-8) con un giro leve hacia el
# este y el sur, para que Paraguay quede un poco más al centro sin ser el centro.
CENTRO = (-71.0, -10.0)

PX, DPI = 2400, None
TOPE = 2712                     # resolución del campo leído del .nc
CREDITO = "Graphic by @Gillo97"
TITULO = "Brightness temperature, band 13"

# Profundidad del borde: máximo de la caída radial extra (0 = el póster MUR tal cual).
SOMBRA_BORDE = 0.55

# Paleta: el rango físico de la rampa GIBS, para que la animación no salte de escala.
PALETAS = {
    "clean_ir": (CMAP_GIBS_CLEAN_IR, VMIN_GIBS, VMAX_GIBS),
}

# Vestuario calcado del póster MUR (misma familia visual).
WHITE = "#ffffff"
INK = "#30353a"
INK_SOFT = "#6d7378"
COAST = "#20262c"
BORDER = "#20262c"
GRID = "#2f3a44"
LIMB = "#c6d8e4"
CARD_FACE = "#fcfdfe"
CARD_EDGE = "#e5e9ed"

BORDE_SA = RAIZ / "datos" / "paraguay_gadm.json"


# ------------------------------------------------------------------------ archivos
def carpeta_datos(sat: str = SAT, banda: str = BANDA) -> Path:
    """Carpeta del dataset: `goes_<banda>_<sat>` bajo `comun.rutas.DATOS`."""
    return DATOS / f"goes_c{banda[1:].lower()}_{sat.lower()}"


def fecha_de(nc: Path) -> datetime:
    """Fecha/hora UTC del slot, leída del nombre (`_sAAAADDDHHMMSS_`)."""
    m = PATRON.search(Path(nc).name)
    if not m:
        return datetime.fromtimestamp(Path(nc).stat().st_mtime)
    s = m.group("s")
    return (datetime(int(s[:4]), 1, 1)
            + timedelta(days=int(s[4:7]) - 1, hours=int(s[7:9]), minutes=int(s[9:11])))


def nc_mas_reciente(datos: Path) -> Path:
    """Último `.nc` del dataset (por el sello de escaneo del nombre, no por mtime)."""
    archivos = [f for f in Path(datos).glob("OR_ABI-*.nc") if PATRON.search(f.name)]
    if not archivos:
        raise SystemExit(f"No hay .nc de ABI en {datos}. "
                         "Bajalos con descargar/descargar_goes.py.")
    return max(archivos, key=fecha_de)


def slots(datos: Path, t0: datetime, n: int, paso: int) -> list[Path]:
    """Los `n` slots con `.nc` local a partir de `t0` (corridos, sin huecos)."""
    mapa = {fecha_de(f): f for f in Path(datos).glob("OR_ABI-*.nc") if PATRON.search(f.name)}
    salida, t = [], t0
    while len(salida) < n:
        clave = t.replace(second=0, microsecond=0)
        if clave in mapa:
            salida.append(mapa[clave])
        t += timedelta(minutes=paso)
        if (t - t0) > timedelta(days=30):
            break
    return salida


# ------------------------------------------------------------------------ geometría
def radio_visible(nc: Path, centro: tuple[float, float], recorte: float | None = None):
    """Radio del disco, en unidades de `sin(ángulo central)`, y datos del satélite.

    El horizonte geostacionario está a `acos(R/(R+h))` del subpunto del satélite. El
    disco se inscribe en el cuadrado, así que el encuadre lo fija cuánto ángulo central
    entra: con el centro en `centro`, el borde más lejano queda a
    `distancia(centro, subpunto) + radio`. Para que ningún borde caiga en la franja
    estirada del limbo, el radio se limita a `LIMBO_DEG` menos esa distancia: cuanto
    más descentrado el globo, más cerrado el encuadre (y más grande se ve el país).
    """
    import xarray as xr
    with xr.open_dataset(nc, engine="h5netcdf") as ds:
        gp = ds["goes_imager_projection"].attrs
        h = float(gp["perspective_point_height"])
        lon0 = float(gp["longitude_of_projection_origin"])
    sin_h = np.sqrt(1.0 - (R_EARTH / (R_EARTH + h)) ** 2)
    if recorte is not None:
        return sin_h * recorte, h, lon0
    phi0, phi1 = np.radians(centro[1]), 0.0
    d = np.degrees(np.arccos(np.clip(
        np.cos(phi1) * np.cos(phi0)
        + np.sin(phi1) * np.sin(phi0) * np.cos(np.radians(centro[0] - lon0)),
        -1.0, 1.0)))
    c_max = float(np.clip(LIMBO_DEG - d, 12.0, 85.0))
    return float(np.sin(np.radians(c_max))), h, lon0


def _orto_inverso(px: int, escala: float, centro: tuple[float, float]):
    """(lon, lat) de cada píxel del disco: mismo mapeo que `poster_mur_realista`."""
    lon0, lat0 = np.radians(centro[0]), np.radians(centro[1])
    y = np.linspace(1.0, -1.0, px)
    x = np.linspace(-1.0, 1.0, px)
    X, Y = np.meshgrid(x, y)
    rho = np.hypot(X, Y)
    dentro = rho <= 1.0
    rho_s = np.where(dentro & (rho > 1e-12), rho, 1.0)
    # `escala` es el seno del ángulo central en el borde del disco (radio 1). Con
    # `escala = 1` esto es el hemisferio completo del póster MUR.
    sin_c = np.clip(rho_s * escala, 0.0, 1.0)
    cos_c = np.sqrt(np.clip(1.0 - sin_c ** 2, 0.0, 1.0))
    lat = np.arcsin(np.clip(cos_c * np.sin(lat0)
                            + (Y * sin_c * np.cos(lat0)) / rho_s, -1.0, 1.0))
    lon = lon0 + np.arctan2(X * sin_c,
                            rho_s * np.cos(lat0) * cos_c - Y * sin_c * np.sin(lat0))
    es_centro = dentro & (rho <= 1e-12)
    lat = np.where(es_centro, lat0, lat)
    lon = np.where(es_centro, lon0, lon)
    return np.degrees(lon), np.degrees(lat), rho, dentro


def _geo_scan(lon, lat, lon0: float, h: float):
    """Ángulos de escaneo del ABI para un (lon, lat), en metros (x = ángulo * h).

    Esfera de radio ecuatorial: el ABI navega sobre el elipsoide, pero como el mapa y
    las costas usan el mismo modelo, la alineación entre dato y geografía se mantiene
    (la diferencia es de ~0.1 px en el interior y ~2 px en el limbo, que se recorta).
    """
    H = R_EARTH + h
    d = np.radians(lon - lon0)
    phi = np.radians(lat)
    cphi = np.cos(phi)
    vx = R_EARTH * cphi * np.cos(d) - H
    vy = R_EARTH * cphi * np.sin(d)
    vz = R_EARTH * np.sin(phi)
    return np.arctan2(vy, -vx) * h, np.arctan2(vz, np.hypot(vx, vy)) * h


def _orto_directo(lon, lat, centro: tuple[float, float], escala: float):
    """Coordenadas del disco (-1..1) para una polilínea lon/lat; NaN si no se ve."""
    lon0, lat0 = np.radians(centro[0]), np.radians(centro[1])
    lam = np.radians(np.asarray(lon, dtype=np.float64) - centro[0])
    phi = np.radians(np.asarray(lat, dtype=np.float64))
    cosc = np.sin(lat0) * np.sin(phi) + np.cos(lat0) * np.cos(phi) * np.cos(lam)
    X = np.cos(phi) * np.sin(lam)
    Y = np.cos(lat0) * np.sin(phi) - np.sin(lat0) * np.cos(phi) * np.cos(lam)
    X = X / escala
    Y = Y / escala
    invisible = (cosc <= 0.0) | (np.hypot(X, Y) > 1.0)
    X[invisible] = np.nan
    Y[invisible] = np.nan
    return X, Y


# ------------------------------------------------------------------------ muestreo
def componer_disco(campo, x, y, lon0, h, escala, centro, px):
    """Reproyecta el campo al disco pedido: (valores, alfa, radio de cada píxel).

    Para cada píxel del disco: Orthographic inverso -> (lon, lat) -> ángulos de escaneo
    -> índice fraccionario en la grilla del `.nc` -> muestreo bilineal. Se conserva el
    valor numérico además del color, para la media de la consola.
    """
    lon, lat, rho, dentro = _orto_inverso(px, escala, centro)
    xs, ys = _geo_scan(lon, lat, lon0, h)
    del lon, lat
    gc.collect()

    dx = float(x[1] - x[0])
    dy = float(y[1] - y[0])
    col = (xs - float(x[0])) / dx
    fila = (ys - float(y[0])) / dy
    del xs, ys
    gc.collect()

    alto, ancho = campo.shape
    ok = (col >= 0) & (col <= ancho - 1) & (fila >= 0) & (fila <= alto - 1)
    c0 = np.clip(np.floor(col), 0, ancho - 2).astype(np.intp)
    f0 = np.clip(np.floor(fila), 0, alto - 2).astype(np.intp)
    fc = np.clip(col - c0, 0.0, 1.0)
    ff = np.clip(fila - f0, 0.0, 1.0)
    del col, fila

    def _bilineal(a):
        v = ((a[f0, c0] * (1 - fc) + a[f0, c0 + 1] * fc) * (1 - ff)
             + (a[f0 + 1, c0] * (1 - fc) + a[f0 + 1, c0 + 1] * fc) * ff)
        return v

    # El campo trae NaN en el espacio: se muestrea una copia sin NaN (la validez la
    # decide `dato_ok`) para que un vecino inválido no envenene el promedio.
    valores = _bilineal(np.nan_to_num(campo, nan=0.0))
    dato_ok = _bilineal(np.isfinite(campo).astype(np.float32)) > 0.9999

    # Borde del disco: antialias de ~1.5 px sobre el radio 1. El alfa es geométrico
    # (el disco entero es opaco); los píxeles sin dato quedan marcados en `valores`
    # como NaN y el borde se rellena después con el color vecino (sin agujeros blancos).
    alfa = np.clip((1.0 - rho) * (px / 2.0) / 1.5, 0.0, 1.0) * dentro
    valores = np.where(ok & dato_ok & (alfa > 0.0), valores, np.nan).astype(np.float32)
    return valores, alfa.astype(np.float32), rho


def _rellenar_huecos(rgb, valido, radio=4.0):
    """Rellena los píxeles sin dato con el promedio de sus vecinos válidos.

    Convolución normalizada: se desenfoca el color ponderado por la validez y se
    divide por la validez desenfocada. No cambia el brillo ni el color del mapa, sólo
    cierra los huecos del limbo (donde el full disk se mezcla con el espacio) con el
    tono que efectivamente hay al lado.
    """
    from PIL import Image as _Image
    from PIL import ImageFilter as _Filter

    peso = valido.astype(np.float32)
    den = np.asarray(_Image.fromarray(peso, mode="F").filter(
        _Filter.GaussianBlur(radio)), dtype=np.float32)
    salida = rgb.astype(np.float32)
    seguro = den > 1e-3
    for k in range(3):
        num = np.asarray(_Image.fromarray((rgb[..., k].astype(np.float32) * peso),
                                         mode="F").filter(
            _Filter.GaussianBlur(radio)), dtype=np.float32)
        salida[..., k] = np.where(seguro, num / np.maximum(den, 1e-6), salida[..., k])
    return np.clip(salida, 0, 255).astype(np.uint8)


def colorear(valores, alfa, cmap, vmin, vmax):
    """Valores -> RGBA uint8 con la rampa dada (alfa 0 fuera del disco).

    Donde el disco no tiene dato (la franja del limbo geostacionario que no cubre el
    recorte) se rellena con el color vecino: el borde queda continuo, sin dientes.
    """
    from matplotlib.colors import Normalize
    norm = Normalize(vmin, vmax)
    rgba = cmap(norm(np.nan_to_num(valores, nan=vmin)))
    rgb = (rgba[..., :3] * 255).astype(np.uint8)
    valido = np.isfinite(valores)
    if np.any(~valido & (alfa > 0)):
        rgb = _rellenar_huecos(rgb, valido)
    return np.dstack([rgb, (alfa * 255).astype(np.uint8)])


# ------------------------------------------------------------------------ tarjeta
def estadisticas(valores, alfa):
    """Media y desvío de la temperatura de brillo sobre el dato real (para la consola)."""
    m = (alfa > 0.5) & np.isfinite(valores)
    v = valores[m]
    if v.size == 0:
        return {"mu": 0.0, "sigma": 0.0, "n": 0}
    v = v.astype(np.float64)
    return {"mu": float(v.mean()), "sigma": float(v.std()), "n": int(v.size)}


def sombrear_borde(rgba, fuerza):
    """Oscurecimiento radial hacia el borde: profundidad de esfera, sin luz inventada.

    Dos términos, los dos simétricos (no hay dirección de luz, que era lo que hacía
    ruido): el limbo leve del póster MUR —10 % en `rho` alto— y una caída extra
    concentrada en el 20 % exterior del radio. `fuerza` es el máximo de esa caída
    extra: 0 deja el póster MUR tal cual, 0.5 es una esfera bien marcada.
    """
    if fuerza <= 0.0:
        return rgba
    alto, ancho = rgba.shape[:2]
    y = np.linspace(1.0, -1.0, alto)
    x = np.linspace(-1.0, 1.0, ancho)
    X, Y = np.meshgrid(x, y)
    rho = np.clip(np.hypot(X, Y), 0.0, 1.0)
    limbo = 1.0 - 0.10 * rho ** 1.3
    borde = np.clip((rho - 0.80) / 0.20, 0.0, 1.0) ** 1.6
    factor = limbo * (1.0 - fuerza * borde)
    salida = rgba.astype(np.float32)
    salida[..., :3] *= factor[..., None]
    return np.clip(salida, 0, 255).astype(np.uint8)


def _etiqueta_eje(v: float) -> str:
    """Número con signo menos tipográfico, como en la barra del póster MUR."""
    texto = f"{v:g}"
    return texto.replace("-", "\u2212")


def _geometria_figura(px, dpi):
    """Layout del póster: el disco llena el ancho y deja el pie para la tarjeta.

    El globo ocupa el 97 % del ancho (antes 92.5 %): con un disco inscripto, los
    márgenes de la página son lo único que se puede recortar sin tocar el planeta.
    """
    ancho_in, alto_in = 10.4, 11.3
    lado_in = 0.97 * ancho_in
    dpi = dpi or (px / lado_in)
    gw, gh = lado_in / ancho_in, lado_in / alto_in
    return ancho_in, alto_in, dpi, (1 - gw) / 2, 0.094, gw, gh


def dibujar(disco, centro, escala, titulo, tiempo, fuente, cmap, vmin, vmax,
            args, px) -> "object":
    """Dibuja el globo con el diseño MUR y devuelve la figura de matplotlib."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.collections import LineCollection
    from matplotlib.colors import Normalize

    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"],
                         "axes.unicode_minus": False})
    ancho_in, alto_in, dpi, gx, gy, gw, gh = _geometria_figura(px, args.dpi)
    fig = plt.figure(figsize=(ancho_in, alto_in), dpi=dpi)
    fig.patch.set_facecolor(WHITE)

    ax = fig.add_axes([gx, gy, gw, gh])
    ax.set_xlim(-1.0, 1.0)
    ax.set_ylim(-1.0, 1.0)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_facecolor("none")

    # Halo exterior en un axes normal: `imshow` no intenta reproyectar nada.
    halo, ext = sombra_exterior(px)
    pad = (ext - 1.0) / 2.0
    ax_halo = fig.add_axes([gx - pad * gw, gy - pad * gh, ext * gw, ext * gh])
    ax_halo.set_zorder(-1)
    ax_halo.set_axis_off()
    ax_halo.patch.set_alpha(0.0)
    ax_halo.imshow(halo, origin="upper", extent=[0, 1, 0, 1], interpolation="bilinear")

    # Profundidad: el limbo leve del MUR más una caída radial extra en el borde. Es
    # simétrico a propósito; la esfera la da la proyección, no una luz direccional.
    ax.imshow(sombrear_borde(disco, args.sombra_borde), origin="upper",
              extent=[-1, 1, -1, 1], interpolation="lanczos", zorder=2)

    # Retículo tenue (meridianos/paralelos cada 30°) y costas finas: dan escala sin
    # competir con el dato. Se dibujan con el mismo mapeo que el campo.
    meridianos, paralelos = [], []
    for lon in np.arange(-180.0, 180.01, 30.0):
        la = np.linspace(-90.0, 90.0, 181)
        meridianos.append(np.column_stack(_orto_directo(np.full_like(la, lon), la,
                                                        centro, escala)))
    for lat in np.arange(-90.0, 90.01, 30.0):
        lo = np.linspace(-180.0, 180.0, 361)
        paralelos.append(np.column_stack(_orto_directo(lo, np.full_like(lo, lat),
                                                       centro, escala)))
    for segs in (paralelos, meridianos):
        ax.add_collection(LineCollection(segs, colors=GRID, linewidths=0.45,
                                         alpha=0.24, zorder=5, capstyle="round"))

    lineas = _lineas_natural_earth("physical", "coastline", "50m")
    if lineas:
        ax.add_collection(LineCollection(
            [np.column_stack(_orto_directo(np.asarray(s)[:, 0], np.asarray(s)[:, 1],
                                           centro, escala)) for s in lineas],
                colors=COAST, linewidths=0.55, alpha=0.62, zorder=6))
    if args.fronteras:
        bordes = _lineas_natural_earth("cultural", "admin_0_boundary_lines_land", "50m")
        if bordes:
            ax.add_collection(LineCollection(
                [np.column_stack(_orto_directo(np.asarray(s)[:, 0], np.asarray(s)[:, 1],
                                               centro, escala)) for s in bordes],
                colors=BORDER, linewidths=0.35, alpha=0.30,
                linestyles=(0, (2, 2)), zorder=6))
    if args.borde:
        py = _lineas_geojson(args.borde)
        if py:
            segs = [np.column_stack(_orto_directo(np.asarray(s)[:, 0], np.asarray(s)[:, 1],
                                                  centro, escala)) for s in py]
            # Blanco con canto oscuro: se lee tanto sobre el gris del dato como sobre
            # las nubes frías (mismo recurso que el halo de los rótulos viejos).
            ax.add_collection(LineCollection(segs, colors="#10161b", linewidths=2.4,
                                             alpha=0.45, zorder=7))
            ax.add_collection(LineCollection(segs, colors="#ffffff", linewidths=1.0,
                                             alpha=0.95, zorder=8))

    # Limbo azulado muy fino: la "atmósfera" que remata la esfera (igual que el MUR).
    ax.add_patch(mpatches.Circle((0, 0), 1.0, fill=False, edgecolor=LIMB,
                                     linewidth=1.0, zorder=7))

    # ---------------------------------------------------------------- tarjeta
    # Sólo la barra de color: la tarjeta queda como un pie limpio, sin distribución.
    card_x, card_y, card_w, card_h = 0.205, 0.040, 0.590, 0.040
    fig.add_artist(mpatches.FancyBboxPatch(
        (card_x, card_y - 0.0022), card_w, card_h,
        boxstyle="round,pad=0.0,rounding_size=0.010",
        transform=fig.transFigure, facecolor="#000000", alpha=0.035,
        edgecolor="none", zorder=7))
    fig.add_artist(mpatches.FancyBboxPatch(
        (card_x, card_y), card_w, card_h,
        boxstyle="round,pad=0.0,rounding_size=0.010",
        transform=fig.transFigure, facecolor=CARD_FACE, edgecolor=CARD_EDGE,
        linewidth=0.7, zorder=8))

    cax = fig.add_axes([0.225, 0.0630, 0.550, 0.011], zorder=9)
    sm = plt.cm.ScalarMappable(norm=Normalize(vmin, vmax), cmap=cmap)
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=cax, orientation="horizontal")
    cbar.outline.set_visible(False)
    ticks = list(range(int(np.ceil(vmin / 20.0) * 20), int(vmax) + 1, 20))
    cbar.set_ticks(ticks)
    rotulos = [_etiqueta_eje(t) for t in ticks]
    rotulos[-1] = f"{rotulos[-1]} \u00b0C"
    cbar.set_ticklabels(rotulos)
    cbar.ax.tick_params(length=0, labelsize=9.5, colors=INK_SOFT, pad=4)
    for etiqueta in cbar.ax.get_xticklabels():
        etiqueta.set_fontfamily("Segoe UI")

    # Marca de agua sobre el globo: gris medio translúcido, sin contorno (como el MUR).
    if args.credito:
        fig.text(0.5, gy + 0.021, " ".join(args.credito.upper()), ha="center",
                 va="center", fontsize=8.6, color=(0.31, 0.35, 0.39, 0.32),
                 fontfamily="Segoe UI", zorder=10)

    # Título y fecha arriba a la izquierda; la fecha ya viene en UTC-3.
    fig.text(0.027, 0.990, titulo, ha="left", va="top", fontsize=14.5, color=INK,
             fontfamily="Segoe UI")
    fig.text(0.027, 0.962, tiempo.upper(), ha="left", va="top", fontsize=9.2,
             color=INK_SOFT, fontfamily="Segoe UI")

    # Fuente y crédito al pie.
    fig.text(0.027, 0.012, fuente, ha="left", va="bottom", fontsize=8.2,
             color="#a3a8ad", fontfamily="Segoe UI")
    if args.credito:
        fig.text(0.973, 0.012, args.credito, ha="right", va="bottom", fontsize=8.4,
                 color="#a3a8ad", fontfamily="Segoe UI")
    return fig


# ------------------------------------------------------------------------ geografía
_CACHE_LINEAS: dict = {}


def _lineas_natural_earth(categoria: str, nombre: str, resolucion: str) -> list:
    """Anillos/polilíneas de Natural Earth como listas de pares (lon, lat)."""
    clave = (categoria, nombre, resolucion)
    if clave in _CACHE_LINEAS:
        return _CACHE_LINEAS[clave]
    import cartopy.io.shapereader as shpreader
    from shapely.geometry import (GeometryCollection, LinearRing, LineString,
                                  MultiLineString, MultiPolygon, Polygon)

    try:
        ruta = shpreader.natural_earth(resolucion, categoria, nombre)
        lector = list(shpreader.Reader(ruta).geometries())
    except Exception as exc:                                   # sin red / sin caché
        print(f"AVISO: Natural Earth {nombre} omitido ({exc})")
        _CACHE_LINEAS[clave] = []
        return []

    salida = []

    def _agregar(geom):
        if isinstance(geom, (Polygon,)):
            salida.append(np.asarray(geom.exterior.coords))
        elif isinstance(geom, (MultiPolygon, GeometryCollection)):
            for g in geom.geoms:
                _agregar(g)
        elif isinstance(geom, (LineString, LinearRing)):
            salida.append(np.asarray(geom.coords))
        elif isinstance(geom, MultiLineString):
            for g in geom.geoms:
                salida.append(np.asarray(g.coords))

    for geom in lector:
        _agregar(geom)
    _CACHE_LINEAS[clave] = salida
    return salida


def _lineas_geojson(ruta) -> list:
    """Anillos de un GeoJSON local (para el contorno destacado, p. ej. Paraguay)."""
    import json
    try:
        gj = json.load(open(ruta, encoding="utf-8"))
    except Exception as exc:
        print(f"AVISO: borde omitido ({exc})")
        return []
    feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
    salida = []
    for f in feats:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            for anillo in poly:
                salida.append(np.asarray(anillo))
    return salida


# ------------------------------------------------------------------------ render
def render(nc: Path, args) -> tuple:
    """Campo -> disco RGBA -> figura. Devuelve (fig, valores, alfa, estadísticas)."""
    campo, x, y, _proj, unidad, rotulos = cargar(nc, tope_px=args.tope,
                                                 escena="FULL DISK")
    if unidad != "\u00b0C":
        raise SystemExit(f"Esta banda no es temperatura de brillo (unidad {unidad!r}); "
                         "el póster está pensado para C13.")
    escala, h, lon0 = radio_visible(nc, tuple(args.centro), args.recorte)

    cmap, vmin_def, vmax_def = PALETAS[args.paleta]
    vmin = args.vmin if args.vmin is not None else vmin_def
    vmax = args.vmax if args.vmax is not None else vmax_def
    if args.porcentiles:
        vmin, vmax = (float(v) for v in np.nanpercentile(campo, [0.5, 99.5]))

    # float32 una sola vez: el .nc llega en float64 y el muestreo no necesita más.
    campo = np.asarray(campo, dtype=np.float32)
    valores, alfa, _ = componer_disco(campo, x, y, lon0, h, escala, args.centro,
                                      args.px)
    del campo
    gc.collect()
    disco = colorear(valores, alfa, cmap, vmin, vmax)
    stats = estadisticas(valores, alfa)

    titulo = args.titulo
    tiempo = time_label_nc(nc)
    fuente = rotulos[2] if len(rotulos) > 2 else f"SOURCE: NOAA/NESDIS {SAT} ABI L2 CMIP"
    fig = dibujar(disco, tuple(args.centro), escala, titulo, tiempo, fuente, cmap,
                  vmin, vmax, args, args.px)
    return fig, valores, alfa, stats, (vmin, vmax)


def time_label_nc(nc: Path) -> str:
    """Fecha del slot en UTC-3 con el formato del póster ('24 OCT 2026 · 15:00 UTC-3')."""
    meses = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN",
             "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
    t = fecha_de(nc) - timedelta(hours=3)
    return f"{t.day:02d} {meses[t.month - 1]} {t.year} \u00b7 {t:%H:%M} UTC-3"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Póster realista (globo Orthographic, fondo blanco) de la banda 13 "
                    "de GOES-19, con el diseño del prototipo MUR.")
    ap.add_argument("--nc", help="archivo ABI L2 CMIP (por defecto, el más reciente)")
    ap.add_argument("--datos", help="carpeta de los .nc (por defecto, la del satélite/banda)")
    ap.add_argument("--px", type=int, default=PX, help=f"diámetro del globo (por defecto {PX})")
    ap.add_argument("--dpi", type=int, default=DPI, help="dpi; si se omite se deduce de --px")
    ap.add_argument("--tope", type=int, default=TOPE,
                    help=f"resolución del campo leído del .nc (por defecto {TOPE})")
    ap.add_argument("--recorte", type=float, default=RECORTE,
                    help="fuerza la fracción del radio visible (por defecto se deduce "
                         "del centro para no tocar la franja estirada del limbo)")
    ap.add_argument("--centro", nargs=2, type=float, metavar=("LON", "LAT"),
                    default=list(CENTRO),
                    help=f"centro del globo (por defecto {CENTRO})")
    ap.add_argument("--paleta", choices=sorted(PALETAS), default="clean_ir",
                    help="rampa de color (por defecto clean_ir, la de Worldview)")
    ap.add_argument("--vmin", type=float, help="mínimo de la escala (°C)")
    ap.add_argument("--vmax", type=float, help="máximo de la escala (°C)")
    ap.add_argument("--porcentiles", action="store_true",
                    help="escala por percentiles 0.5/99.5 en vez del rango de la rampa")
    ap.add_argument("--titulo", default=TITULO, help="título del póster")
    ap.add_argument("--sombra-borde", type=float, default=SOMBRA_BORDE,
                    help=f"profundidad del borde 0..0.8 (por defecto {SOMBRA_BORDE}); "
                         "0 deja el limbo del póster MUR")
    ap.add_argument("--credito", default=CREDITO, help="crédito al pie; vacío = sin crédito")
    ap.add_argument("--borde", nargs="?", const=str(BORDE_SA), default=str(BORDE_SA),
                    help="contorno destacado sobre el globo (por defecto, Paraguay); "
                         "pasá --borde \"\" para sacarlo")
    ap.add_argument("--fronteras", action=argparse.BooleanOptionalAction, default=True,
                    help="límites políticos punteados (por defecto, sí)")
    ap.add_argument("--out", help="PNG de salida (por defecto, en comun.rutas.SALIDAS)")
    ap.add_argument("--frames", help="carpeta de cuadros: renderiza una serie numerada")
    ap.add_argument("--desde", help="primer cuadro de la serie, UTC")
    ap.add_argument("--n", type=int, default=24, help="cantidad de cuadros de la serie")
    ap.add_argument("--paso", type=int, default=10, help="minutos entre cuadros")
    ap.add_argument("--forzar", action="store_true", help="rehace cuadros ya existentes")
    args = ap.parse_args(argv)

    datos = Path(args.datos) if args.datos else carpeta_datos()
    if not args.nc and not datos.exists():
        raise SystemExit(f"No existe {datos}. Bajá los .nc con "
                         "descargar/descargar_goes.py.")

    if args.frames:
        return _serie(datos, args)

    nc = Path(args.nc) if args.nc else nc_mas_reciente(datos)

    print(f"{nc.name}\nslot: {fecha_de(nc):%Y-%m-%d %H:%M} UTC | globo {args.px} px | "
          f"centro {tuple(args.centro)} | paleta {args.paleta}", flush=True)
    fig, valores, alfa, stats, (vmin, vmax) = render(nc, args)
    print(f"escala {vmin:.1f} a {vmax:.1f} \u00b0C | disco mu {stats['mu']:+.2f} "
          f"sigma {stats['sigma']:.2f} \u00b0C ({stats['n']:,} px)")

    t = fecha_de(nc)
    out = Path(args.out) if args.out else (
        SALIDAS / f"poster_G19_C13_realista_{t:%Y-%m-%dT%H%M}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    parcial = out.with_suffix(".png.parcial")
    fig.savefig(parcial, format="png", facecolor=WHITE)
    import matplotlib.pyplot as plt
    plt.close(fig)
    parcial.replace(out)
    print(f"PNG: {out}")
    print(f"Serie de cuadros: .venv\\Scripts\\python.exe prototipos\\poster_goes_realista.py "
          f"--frames \"{SALIDAS / 'frames_G19_C13_realista'}\" --n 24")
    return 0


def _serie(datos: Path, args) -> int:
    """Renderiza una serie de cuadros con el mismo diseño (insumo de la animación)."""
    t0 = datetime.fromisoformat(args.desde) if args.desde else None
    if t0 is None:
        todos = sorted((f for f in datos.glob("OR_ABI-*.nc") if PATRON.search(f.name)),
                       key=fecha_de)
        if not todos:
            raise SystemExit(f"No hay .nc de ABI en {datos}.")
        ultimo = fecha_de(todos[-1])
        t0 = ultimo - timedelta(minutes=args.paso * (args.n - 1))
    lista = slots(datos, t0, args.n, args.paso)
    if not lista:
        raise SystemExit("Ninguno de los slots pedidos tiene .nc local.")

    salida = Path(args.frames)
    salida.mkdir(parents=True, exist_ok=True)
    print(f"{len(lista)} cuadros desde {fecha_de(lista[0]):%Y-%m-%d %H:%M} UTC -> {salida}",
          flush=True)
    for i, nc in enumerate(lista, 1):
        destino = salida / f"cuadro_{i:03d}.png"
        if destino.exists() and not args.forzar:
            continue
        fig, *_ = render(nc, args)
        import matplotlib.pyplot as plt
        parcial = destino.with_suffix(".png.parcial")
        fig.savefig(parcial, format="png", facecolor=WHITE)
        plt.close(fig)
        parcial.replace(destino)
        print(f"  [{i}/{len(lista)}] {fecha_de(nc):%Y-%m-%d %H:%M} UTC", flush=True)
    print(f"Cuadros en {salida}")
    print(f"Armá el video con: .venv\\Scripts\\python.exe animar\\armar.py --frames \"{salida}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
