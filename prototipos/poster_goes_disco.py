"""Póster de color real de GOES-19 en la **proyección nativa del satélite**.

Archivo NUEVO. A diferencia de `poster_goes_truecolor.py` —que reproyecta el disco a
un globo Orthographic visto desde afuera— acá **no se rota ni se reproyecta nada**: se
usa la grilla de escaneo tal como la entrega el ABI. El resultado es el encuadre que el
satélite le da al planeta: disco completo, limbo a ~81° del subpunto (se ve bastante
más de la Tierra que en un Orthographic) y las deformaciones reales de la perspectiva
geoestacionaria.

El color es el mismo pipeline ya validado en `poster_goes_truecolor.py` (se importa, no
se copia): normalización solar con mezcla, pedestal atmosférico, verde sintético
CIMSS (0.45·rojo + 0.10·veggie + 0.45·azul), estirado por luminancia, mediana 3×3,
saturación, gamma y rampa de noche.

Lo único propio de este archivo es la geolocalización *inversa* (ángulo de escaneo ->
lon/lat) para calcular el sol y para dibujar costas, retículo y el borde de Paraguay
sobre la grilla nativa.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe prototipos\\poster_goes_disco.py
    .venv\\Scripts\\python.exe prototipos\\poster_goes_disco.py --desde 2026-10-24T16:40 --px 3000
    .venv\\Scripts\\python.exe prototipos\\poster_goes_disco.py --help   # no toca la red
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
sys.path.insert(0, str(RAIZ / "prototipos"))

from poster_goes_realista import (  # noqa: E402
    _geo_scan,
    _lineas_geojson,
    _lineas_natural_earth,
    sombrear_borde,
)
from poster_goes_truecolor import (  # noqa: E402
    BANDAS,
    BORDE_SA,
    CREDITO,
    ESCALA_Q,
    GAMMA,
    MU_ALTO,
    MU_MIN,
    MU_NOCHE,
    NOMBRE,
    PCT_HI,
    PCT_LO,
    PEDESTAL,
    SATURACION,
    SUAVIZADO,
    TITULO,
    _componer,
    _desenfoque,
    _factor_solar,
    _mediana,
    _parametros,
    _plano,
    carpeta,
    cos_cenital,
    fecha_de,
    slots_comunes,
    time_label_nc,
)
from rutas import SALIDAS  # noqa: E402

R_EARTH = 6_378_137.0

PX = 5424                 # 1:1 con la grilla de origen (10848/2 y 21696/4)
TOPE = 5424                # grilla de origen: mitad de la nativa, las tres alinean
SOMBRA_BORDE = 0.0         # sin darkening de limbo: el borde lo define el dato
LIMITE_LINEAS = 78.0       # ángulo central máximo para las líneas (si se dibujan)
LIMBO_COMP = 0.25          # exponente de compensación del limbo (0 = sin compensar)
# Medios tonos: el GeoColor oficial tiene el centro en ~111 de luminancia y nosotros
# salíamos en ~70, y eso hacía que el limbo (que es real, ~128 en los dos) resaltara
# como si fuera un aro inventado. Gamma más bajo y pedestal más suave emparejan la curva.
GAMMA_DEF = 0.80
PCT_LO_DEF = 0.2
FUENTE = "NOAA/NESDIS GOES-19 ABI L2 CMIP · B1+B2+B3"

BG = "#000000"
INK = "#f2f5f8"
INK_SOFT = "#b9c1c9"
INK_FAINT = "#7e8790"
COAST = "#d7dee5"
BORDER = "#d7dee5"
GRID = "#8fa0ad"


# ------------------------------------------------------------------------ geometría
def geo_scan_inverso(xs, ys, lon0: float, h: float):
    """(lon, lat) de cada píxel a partir de sus ángulos de escaneo, en grados.

    Es la inversa exacta de `poster_goes_realista._geo_scan` (misma esfera de radio
    ecuatorial), para que el dato, el sol y las costas usen un único modelo geométrico.
    Devuelve NaN fuera del disco (rayos que no tocan la Tierra) y la máscara del disco.
    """
    H = R_EARTH + h
    a = np.asarray(xs, dtype=np.float64) / h
    b = np.asarray(ys, dtype=np.float64) / h
    t = np.tan(a)
    u = np.tan(b)
    T = t * t + (1.0 / np.cos(a)) ** 2 * u * u
    disc = H * H - (1.0 + T) * (H * H - R_EARTH * R_EARTH)
    valido = disc > 0.0
    k = np.where(valido, (H - np.sqrt(np.maximum(disc, 0.0))) / (1.0 + T), np.nan)
    d = np.arctan2(k * t, H - k)
    vz = k / np.cos(a) * u
    lat = np.degrees(np.arcsin(np.clip(vz / R_EARTH, -1.0, 1.0)))
    lon = lon0 + np.degrees(d)
    return (np.where(valido, lon, np.nan), np.where(valido, lat, np.nan), valido)


def _comp_limbo(mu, xs, ys, h, exponente: float):
    """Ganancia que compensa el camino atmosférico creciente hacia el limbo.

    El ABI entrega la reflectancia tal como la ve el sensor: en visión oblicua el
    camino óptico crece como ``1/cos(vza)`` y eso levanta un anillo claro en todo el
    borde. La corrección es la de masa de aire estándar, normalizada al nadir:

        am = 1/cos(vza) + 1/cos(sza)      am0 = 1 + 1/cos(sza)      gan = (am0/am)^k

    ``cos(vza)`` sale del ángulo de escaneo β del propio píxel (``tan β = r/h``) con
    ``sin(vza) = ((R+h)/R)·sin(β)``; es exacto, no una aproximación por el ángulo
    central. Con ``k = 0`` no se toca nada; 1 apagaría de más el limbo; 0.25 empareja
    el perfil con el del GeoColor oficial de CIRA (medido: ~127 de luminancia en
    rho 0.96 en los dos).
    """
    if exponente <= 0.0:
        return 1.0
    t = np.hypot(xs, ys) / h
    sin_beta = t / np.sqrt(1.0 + t * t)
    sin_vza = ((R_EARTH + h) / R_EARTH) * sin_beta
    cos_vza = np.sqrt(np.clip(1.0 - sin_vza ** 2, 1e-4, 1.0))
    mu_e = np.clip(mu, 0.05, 1.0)
    am = 1.0 / cos_vza + 1.0 / mu_e
    am0 = 1.0 + 1.0 / mu_e
    return ((am0 / am) ** exponente).astype(np.float32)


def _borde(dentro):
    """Alfa del disco desde la máscara geométrica: círculo limpio, sin dientes.

    La máscara de dato llega con el borde en escalera (un píxel de la grilla de
    escaneo) y con las últimas filas del limbo muy estiradas. Se erosiona un par de
    píxeles para comerse esa franja y se suaviza 1 px para el antialias.
    """
    from PIL import Image as _Image, ImageFilter as _Filter

    m = _Image.fromarray((np.asarray(dentro) * 255).astype(np.uint8), mode="L")
    m = m.filter(_Filter.MinFilter(9)).filter(_Filter.GaussianBlur(1.2))
    return np.asarray(m)


def _alinear(planos: dict) -> dict:
    """Recorta las tres bandas a la grilla de C01 (C02 viene al doble de resolución)."""
    forma = planos["C01"][0].shape
    salida = {}
    for banda in BANDAS:
        plano, x, y, h, lon0 = planos[banda]
        if plano.shape != forma:
            from PIL import Image as _Image
            img = _Image.fromarray(plano.astype(np.float32) / 65535.0, mode="F")
            img = img.resize((forma[1], forma[0]), _Image.LANCZOS)
            plano = np.clip(np.asarray(img, dtype=np.float32) * 65535.0,
                            0, 65535).astype(np.uint16)
            x = np.linspace(x[0], x[-1], forma[1])
            y = np.linspace(y[0], y[-1], forma[0])
        salida[banda] = (plano, x, y, h, lon0)
    return salida


def componer(planos: dict, t: datetime, args):
    """Grilla nativa -> RGBA del disco (sin reproyectar) + máscara de validez."""
    plano, x, y, h, lon0 = planos["C01"]
    alto, ancho = plano.shape
    xs = np.broadcast_to(x[None, :], (alto, ancho))
    ys = np.broadcast_to(y[:, None], (alto, ancho))
    lon, lat, dentro = geo_scan_inverso(xs, ys, lon0, h)
    mu, decl = cos_cenital(lon, lat, t)
    gan = _comp_limbo(mu, xs, ys, h, args.limbo)
    del lon, lat

    factor = _factor_solar(mu, args) * gan
    del gan, xs, ys
    refs = {}
    valido = np.ones(plano.shape, dtype=bool)
    for banda in BANDAS:
        crudo = planos[banda][0].astype(np.float32) * (ESCALA_Q / 65535.0)
        refs[NOMBRE[banda]] = crudo * factor
        valido &= crudo > 0.0
        del crudo
    refs = {c: np.where(valido, v, np.nan).astype(np.float32) for c, v in refs.items()}

    params = _parametros(refs, valido, mu, args)
    rgb = _componer(refs, mu, params, args)
    del refs, factor

    alfa = _borde(dentro)
    rgb8 = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)
    del rgb, dentro

    if args.mediana:
        rgb8 = _mediana(rgb8)
    if args.suavizado > 0:
        rgb8 = _desenfoque(rgb8, args.suavizado * ancho / 2400.0)
    rgba = np.dstack([rgb8, alfa])
    if args.sombra_borde > 0:
        rgba = sombrear_borde(rgba, args.sombra_borde)
    return rgba, valido, params, decl


# ------------------------------------------------------------------------ figura
def _geometria(px: int, dpi: int | None):
    """Página cuadrada con el disco ocupando el 97 % del ancho.

    Los textos van sobre las esquinas negras: es el único lugar donde no tapan al
    planeta y, como el fondo ya es negro, no hace falta reservar margen para ellos.
    """
    lado_in = 10.4
    disco_in = 0.97 * lado_in
    dpi = dpi or (px / disco_in)
    g = disco_in / lado_in
    return lado_in, lado_in, dpi, (1 - g) / 2, (1 - g) / 2, g, g


def _a_ejes(lon, lat, x, y, lon0, h, forma, limite: float | None = None):
    """lon/lat -> coordenadas de los ejes (-1..1) de la grilla nativa ya dibujada.

    ``limite`` es el ángulo central máximo (grados desde el subpunto) que se dibuja:
    pegado al limbo la proyección comprime tanto las costas del Ártico que se apilan
    en una banda oscura ilegible.
    """
    lon = np.asarray(lon, dtype=np.float64)
    lat = np.asarray(lat, dtype=np.float64)
    xs, ys = _geo_scan(lon, lat, lon0, h)
    alto, ancho = forma
    col = (xs - x[0]) / (x[1] - x[0])
    fila = (ys - y[0]) / (y[1] - y[0])
    X = -1.0 + 2.0 * col / (ancho - 1)
    Y = 1.0 - 2.0 * fila / (alto - 1)
    fuera = (col < 0) | (col > ancho - 1) | (fila < 0) | (fila > alto - 1)
    if limite is not None:
        cosc = np.cos(np.radians(lat)) * np.cos(np.radians(lon - lon0))
        fuera = fuera | (np.degrees(np.arccos(np.clip(cosc, -1.0, 1.0))) > limite)
    X[fuera] = np.nan
    Y[fuera] = np.nan
    return X, Y


def dibujar(disco, x, y, lon0, h, forma, titulo, tiempo, fuente, args, px):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection

    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"]})
    ancho_in, alto_in, dpi, gx, gy, gw, gh = _geometria(px, args.dpi)
    fig = plt.figure(figsize=(ancho_in, alto_in), dpi=dpi)
    fig.patch.set_facecolor(BG)

    ax = fig.add_axes([gx, gy, gw, gh])
    ax.set_xlim(-1.0, 1.0)
    ax.set_ylim(-1.0, 1.0)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_facecolor("none")

    # Sin halo ni sombra exterior: el fondo es negro y el borde del disco lo cierra el
    # propio dato. Cualquier degradado alrededor se lee como una luz inventada.
    ax.imshow(disco, origin="upper", extent=[-1, 1, -1, 1],
              interpolation="none", zorder=2)

    if args.reticula:
        meridianos, paralelos = [], []
        for lo in np.arange(-180.0, 180.01, 30.0):
            la = np.linspace(-90.0, 90.0, 181)
            meridianos.append(np.column_stack(
                _a_ejes(np.full_like(la, lo), la, x, y, lon0, h, forma, args.limite)))
        for la in np.arange(-60.0, 60.01, 30.0):
            lo = np.linspace(-180.0, 180.0, 361)
            paralelos.append(np.column_stack(
                _a_ejes(lo, np.full_like(lo, la), x, y, lon0, h, forma, args.limite)))
        for segs in (paralelos, meridianos):
            ax.add_collection(LineCollection(segs, colors=GRID, linewidths=0.45,
                                             alpha=0.22, zorder=5, capstyle="round"))

    if args.costas:
        lineas = _lineas_natural_earth("physical", "coastline", "50m")
        if lineas:
            ax.add_collection(LineCollection(
                [np.column_stack(_a_ejes(np.asarray(s)[:, 0], np.asarray(s)[:, 1],
                                         x, y, lon0, h, forma, args.limite)) for s in lineas],
                colors=COAST, linewidths=0.4, alpha=0.32, zorder=6))
    if args.fronteras:
        bordes = _lineas_natural_earth("cultural", "admin_0_boundary_lines_land", "50m")
        if bordes:
            ax.add_collection(LineCollection(
                [np.column_stack(_a_ejes(np.asarray(s)[:, 0], np.asarray(s)[:, 1],
                                         x, y, lon0, h, forma, args.limite)) for s in bordes],
                colors=BORDER, linewidths=0.32, alpha=0.22,
                linestyles=(0, (2, 2)), zorder=6))
    if args.borde:
        poly = _lineas_geojson(args.borde)
        if poly:
            segs = [np.column_stack(_a_ejes(np.asarray(s)[:, 0], np.asarray(s)[:, 1],
                                            x, y, lon0, h, forma, args.limite)) for s in poly]
            ax.add_collection(LineCollection(segs, colors="#10161b", linewidths=1.4,
                                             alpha=0.45, zorder=7))
            ax.add_collection(LineCollection(segs, colors="#ffffff", linewidths=0.55,
                                             alpha=0.95, zorder=8))

    # Textos en las esquinas negras: el disco ocupa el 97 % del cuadro y no hay margen
    # reservado, así que cualquier rótulo tiene que caer fuera del planeta.
    fig.text(0.016, 0.984, titulo, ha="left", va="top", fontsize=13.0, color=INK,
             fontfamily="Segoe UI")
    fig.text(0.016, 0.957, tiempo.upper(), ha="left", va="top", fontsize=8.6,
             color=INK_SOFT, fontfamily="Segoe UI")
    fig.text(0.016, 0.016, fuente, ha="left", va="bottom", fontsize=7.4,
             color=INK_FAINT, fontfamily="Segoe UI")
    if args.credito:
        fig.text(0.984, 0.016, args.credito, ha="right", va="bottom", fontsize=7.8,
                 color=INK_FAINT, fontfamily="Segoe UI")
    return fig


# ------------------------------------------------------------------------ CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Póster de color real de GOES-19 en la grilla nativa del satélite "
                    "(sin reproyectar), compuesto con las bandas visibles B1+B2+B3.")
    ap.add_argument("--desde", help="slot UTC ISO (por defecto, el último completo)")
    ap.add_argument("--sat", default=None, help="satélite (por defecto G19)")
    ap.add_argument("--px", type=int, default=PX,
                    help=f"diámetro del disco en px (por defecto {PX})")
    ap.add_argument("--dpi", type=int, default=None, help="dpi; si se omite se deduce de --px")
    ap.add_argument("--tope", type=int, default=TOPE,
                    help=f"grilla de origen de cada banda (por defecto {TOPE})")
    ap.add_argument("--saturacion", type=float, default=SATURACION,
                    help=f"saturación del color, 1 = neutra (por defecto {SATURACION})")
    ap.add_argument("--gamma", type=float, default=GAMMA_DEF,
                    help=f"gamma del RGB (por defecto {GAMMA_DEF})")
    ap.add_argument("--pedestal", type=float, default=PEDESTAL,
                    help=f"percentil del pedestal atmosférico (por defecto {PEDESTAL})")
    ap.add_argument("--pct-lo", type=float, default=PCT_LO_DEF,
                    help=f"percentil bajo (por defecto {PCT_LO_DEF})")
    ap.add_argument("--pct-hi", type=float, default=PCT_HI, help=f"percentil alto (por defecto {PCT_HI})")
    ap.add_argument("--mu-min", type=float, default=MU_MIN, help="piso de cos(cenital)")
    ap.add_argument("--mu-alto", type=float, default=MU_ALTO, help="cos(cenital) con sol alto")
    ap.add_argument("--mu-noche", type=float, default=MU_NOCHE, help="fin de la rampa de noche")
    ap.add_argument("--suavizado", type=float, default=SUAVIZADO, help="desenfoque final (px)")
    ap.add_argument("--mediana", action=argparse.BooleanOptionalAction, default=True,
                    help="mediana 3x3 contra el píxel suelto (por defecto, sí)")
    ap.add_argument("--sombra-borde", type=float, default=SOMBRA_BORDE,
                    help=f"oscurecimiento del limbo 0..0.8 (por defecto {SOMBRA_BORDE})")
    ap.add_argument("--limite", type=float, default=LIMITE_LINEAS,
                    help=f"ángulo central máximo para dibujar costas y retículo "
                         f"(por defecto {LIMITE_LINEAS}°); más allá las líneas se apilan")
    ap.add_argument("--limbo", type=float, default=LIMBO_COMP,
                    help=f"compensación del camino atmosférico en el limbo, 0 = sin "
                         f"compensar (por defecto {LIMBO_COMP})")
    ap.add_argument("--titulo", default=TITULO, help="título del póster")
    ap.add_argument("--fuente", default=FUENTE, help="línea de fuente al pie")
    ap.add_argument("--credito", default=CREDITO, help="crédito al pie; vacío = sin crédito")
    ap.add_argument("--borde", nargs="?", const=str(BORDE_SA), default="",
                    help="contorno destacado opcional: pasá un GeoJSON, o '--borde' solo "
                         "para el de Paraguay; por defecto no se dibuja ninguno")
    ap.add_argument("--fronteras", action=argparse.BooleanOptionalAction, default=False,
                    help="límites políticos punteados (por defecto, NO: sólo queda el "
                         "contorno de Paraguay)")
    ap.add_argument("--costas", action=argparse.BooleanOptionalAction, default=False,
                    help="costas dibujadas sobre el disco (por defecto, NO)")
    ap.add_argument("--reticula", action=argparse.BooleanOptionalAction, default=False,
                    help="meridianos y paralelos cada 30° (por defecto, NO)")
    ap.add_argument("--out", help="PNG de salida (por defecto, en comun.rutas.SALIDAS)")
    args = ap.parse_args(argv)

    sat = args.sat or "G19"
    desde = datetime.fromisoformat(args.desde) if args.desde else None
    nc_bandas = slots_comunes(desde, 1, 10, BANDAS, sat)[0]
    nc01 = nc_bandas["C01"]
    t0 = fecha_de(nc01)
    print(f"{Path(nc01).name}\nslot: {t0:%Y-%m-%d %H:%M} UTC | disco nativo {args.px} px | "
          f"saturación {args.saturacion} | gamma {args.gamma}", flush=True)

    planos = {}
    for banda in BANDAS:
        print(f"  leyendo {banda}...", flush=True)
        planos[banda] = _plano(nc_bandas[banda], args.tope)
    planos = _alinear(planos)
    _plano01, x, y, h, lon0 = planos["C01"]
    forma = _plano01.shape
    print(f"  grilla nativa {forma[1]}x{forma[0]}", flush=True)

    disco, valido, _params, decl = componer(planos, t0 + timedelta(minutes=5), args)
    del planos
    print(f"  disco {args.px} px | {int(valido.sum()):,} px con dato | "
          f"declinación {np.degrees(decl):+.1f}°", flush=True)

    fig = dibujar(disco, x, y, lon0, h, forma, args.titulo, time_label_nc(nc01),
                  args.fuente, args, args.px)

    out = Path(args.out) if args.out else (
        SALIDAS / f"poster_G19_truecolor_nativo_{t0:%Y-%m-%dT%H%M}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    parcial = out.with_suffix(".png.parcial")
    fig.savefig(parcial, format="png", facecolor=BG)
    import matplotlib.pyplot as plt
    plt.close(fig)
    parcial.replace(out)
    peso = out.stat().st_size / 1e6
    print(f"PNG: {out}  ({peso:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
