"""Póster de **color real** de GOES-19 con el diseño de `poster_goes_realista`.

Archivo NUEVO: no modifica el pipeline de la C13 (`poster_goes_realista.py`), ni el
de GeoColor (`cuadros/cuadros_geocolor.py`), ni el de true color de GIBS
(`cuadros/cuadros_truecolor.py`). Toma el vestuario aprobado del póster realista
—fondo blanco, globo Orthographic inscripto, sombra exterior, retículo tenue,
costas finas, borde de Paraguay— y le cambia el insumo: en lugar de una banda
térmica coloreada con una rampa, compone **tres canales visibles** en un RGB.

Por qué hacen falta tres bandas y no una:

  * El ABI no tiene banda verde. Se sintetiza con la receta oficial de CIMSS/Unidata:
    ``Green = 0.45·RED(0.64) + 0.10·VEGGIE(0.86) + 0.45·BLUE(0.47)``. El peso del
    0.86 µm es **bajo a propósito**: "veggie" mide clorofila, no luz verde; usarlo al
    45 % (el error fácil de cometer) pinta la vegetación de esmeralda y vuelve verde
    la Patagonia.
  * Con una sola banda visible (lo único que lleva HRIT) no hay color posible: sólo
    gris o falso color con un mapa de fondo pegado. Ese es el motivo por el que las
    imágenes de GOES por RTL-SDR nunca se ven "naturales".

El pipeline, en orden (cada paso es una decisión explícita, no un ajuste a ojo):

  1. Normalización solar: la reflectancia se mezcla entre cruda y dividida por
     cos(cenital solar) según altura solar. Cerca del terminador la división amplifica
     el ruido hasta romper el color (moteado en el limbo), así que ahí manda la cruda.
  2. Pedestal atmosférico (DOS, *dark object subtraction*): se resta a cada canal su
     percentil bajo sobre los píxeles iluminados. Es la corrección más simple que quita
     la neblina azul y devuelve el océano oscuro; no pretende ser un Rayleigh completo.
  3. Verde sintético (receta CIMSS) y estirado por luminancia, con percentiles
     compartidos para no romper el balance de color.
  4. Mediana 3×3 (mata el píxel suelto), saturación, gamma y desenfoque sub-píxel.
  5. Rampa de noche: el disco se apaga del lado sin sol, que es lo que produce el
     terminador de la referencia.

Resolución: el muestreo va **por franjas de filas**. Así el pico de memoria no crece
con el cuadrado del tamaño y el póster se puede sacar a resolución nativa del sensor
(~8360 px de diámetro, 1 km por píxel en las tres bandas) en una máquina de 8 GB.

Reutiliza `comun/goes_lectura.py` (patrón de nombre), `poster_goes_realista.py`
(geometría geostacionaria, sombreado del borde, relleno de huecos, rótulos) y
`poster_mur_realista.py` (sombra exterior): una sola fuente por pieza.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe prototipos\\poster_goes_truecolor.py
    .venv\\Scripts\\python.exe prototipos\\poster_goes_truecolor.py --desde 2026-10-24T16:40
    .venv\\Scripts\\python.exe prototipos\\poster_goes_truecolor.py --px 1200   # borrador rápido
    .venv\\Scripts\\python.exe prototipos\\poster_goes_truecolor.py --help   # no toca la red
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

from goes_lectura import PATRON  # noqa: E402
from poster_goes_realista import (  # noqa: E402
    _geo_scan,
    _lineas_geojson,
    _lineas_natural_earth,
    _orto_directo,
    _rellenar_huecos,
    fecha_de,
    radio_visible,
    sombrear_borde,
    time_label_nc,
)
from poster_mur_realista import sombra_exterior  # noqa: E402
from firms import (RADIO_FOCO, VENTANAS, color_hex, factor_gravedad,  # noqa: E402
                   filtrar, leer_carpeta, ventana)
from rutas import DATOS, SALIDAS  # noqa: E402

# ------------------------------------------------------------------------ constantes
SAT = "G19"
BANDAS = ("C01", "C02", "C03")          # azul, rojo, veggie
NOMBRE = {"C01": "azul", "C02": "rojo", "C03": "nir"}   # canal -> componente RGB
CENTRO = (-71.0, -10.0)                 # mismo encuadre que el póster de la C13

# 8360 px de diámetro es la resolución nativa de 1 km: el disco visible abarca ~125°
# de ángulo central y la grilla de 1 km del ABI tiene 66.7 px por grado. Más que eso
# empieza a interpolar el azul y el verde (el rojo, a 0.5 km, todavía aguantaría).
PX = 8360
TOPE = 10848                            # grilla de origen: nativa en C01/C03, 2x en C02
FILAS = 256                             # alto de franja del muestreo
ESCALA_Q = 1.5                          # fondo de escala de la reflectancia al cuantizar

# Ajustes del color. Los valores por defecto están pensados para que el póster salga
# "fotográfico" sin tocar nada; todos son ajustables por consola.
SATURACION = 1.10
GAMMA = 0.85
PEDESTAL = 0.2                          # percentil del pedestal atmosférico
PCT_LO, PCT_HI = 0.5, 99.5              # estirado por luminancia
MU_MIN = 0.10                           # piso de cos(cenital) para no amplificar ruido
MU_ALTO = 0.45                          # sol "alto": ahí la normalización pesa entera
MU_NOCHE = 0.12                         # cos(cenital) donde termina la rampa de noche
SUAVIZADO = 0.8                         # px de desenfoque final (limpia el moteado del limbo)

TITULO = "True color"
CREDITO = "Graphic by @Gillo97"
FUENTE = "SOURCE: NOAA/NESDIS {sat} ABI L2 CMIP | B1+B2+B3 COMPOSITE"

# Vestuario, calcado del póster realista (misma familia visual).
WHITE = "#ffffff"
INK = "#30353a"
INK_SOFT = "#6d7378"
COAST = "#20262c"
BORDER = "#20262c"
GRID = "#2f3a44"

BORDE_SA = RAIZ / "datos" / "paraguay_gadm.json"


# ------------------------------------------------------------------------ archivos
def carpeta(banda: str, sat: str = SAT) -> Path:
    """Carpeta de una banda: ``goes_c01_g19`` bajo ``comun.rutas.DATOS``."""
    return DATOS / f"goes_c{banda[1:].lower()}_{sat.lower()}"


def nc_de(banda: str, t: datetime, sat: str = SAT) -> Path:
    """El ``.nc`` local de esa banda cuyo escaneo arranca en el slot ``t``."""
    objetivo = t.replace(second=0, microsecond=0)
    for f in carpeta(banda, sat).glob("OR_ABI-L2-CMIP*.nc"):
        m = PATRON.search(f.name)
        if not m or m["banda"] != banda or m["sat"] != sat:
            continue
        if fecha_de(f).replace(second=0, microsecond=0) == objetivo:
            return f
    raise SystemExit(f"Falta {banda} para {t:%Y-%m-%d %H:%M} UTC en "
                     f"{carpeta(banda, sat)}. Bajalo con descargar/truecolor_goes.py "
                     f"--desde {t:%Y-%m-%dT%H:%M}")


def slots_comunes(desde: datetime | None, n: int, paso: int,
                  bandas=BANDAS, sat: str = SAT) -> list[dict[str, Path]]:
    """Los ``n`` slots (corridos, sin huecos) con las tres bandas presentes."""
    disponibles = []
    for banda in bandas:
        raiz = carpeta(banda, sat)
        if not raiz.exists():
            continue
        disponibles.append({fecha_de(f).replace(second=0, microsecond=0)
                            for f in raiz.glob("OR_ABI-L2-CMIP*.nc") if PATRON.search(f.name)})
    if len(disponibles) != len(bandas):
        raise SystemExit(f"No están todas las bandas bajo {DATOS}. "
                         "Bajalas con descargar/truecolor_goes.py.")
    comunes = set.intersection(*disponibles)
    if not comunes:
        raise SystemExit("Ningún slot tiene las tres bandas. "
                         "Bajá un slot completo con descargar/truecolor_goes.py.")

    base = desde or max(comunes)
    t = base
    salida: list[dict[str, Path]] = []
    while len(salida) < n:
        clave = t.replace(second=0, microsecond=0)
        if clave in comunes:
            salida.append({b: nc_de(b, clave, sat) for b in bandas})
        t += timedelta(minutes=paso)
        if (t - base) > timedelta(days=30):
            break
    if not salida:
        raise SystemExit("Ninguno de los slots pedidos está completo en disco.")
    return salida


def _plano(nc: Path, tope: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    """Reflectancia de una banda como ``uint16`` (0..65535) y su grilla de escaneo.

    Se lee el ``.nc`` submuestreando con ``paso`` (``TOPE`` es la grilla nativa de
    C01/C03, así que en esas bandas ``paso == 1`` y no hay pérdida) y se cuantiza en
    el lugar: el pico de memoria es un plano de origen más su versión uint16, no dos
    copias float64. Devuelve ``(plano, x, y, altura_satélite, longitud_subpunto)``.
    """
    import xarray as xr

    with xr.open_dataset(nc, engine="h5netcdf") as ds:
        cmi = ds["CMI"]
        gp = ds["goes_imager_projection"].attrs
        h = float(gp["perspective_point_height"])
        lon0 = float(gp["longitude_of_projection_origin"])
        paso = max(1, int(np.ceil(max(cmi.shape) / tope)))
        x = ds["x"].values[::paso] * h
        y = ds["y"].values[::paso] * h
        if paso == 1:
            crudo = np.asarray(cmi.values, dtype=np.float32)
        else:
            # Promedio de bloques paso x paso, leído por franjas de filas: el decimado
            # puro (``[::paso]``) aliasa la textura de la tierra y deja un moteado
            # regular que después el estirado convierte en puntos de color.
            alto_out = int(np.ceil(cmi.shape[0] / paso))
            ancho_out = int(np.ceil(cmi.shape[1] / paso))
            crudo = np.zeros((alto_out, ancho_out), dtype=np.float32)
            ancho_util = (cmi.shape[1] // paso) * paso
            for r0 in range(0, cmi.shape[0], paso * 256):
                r1 = min(r0 + paso * 256, cmi.shape[0])
                bloque = np.asarray(cmi[r0:r1, :ancho_util].values, dtype=np.float32)
                nb = bloque.shape[0] // paso
                if nb == 0:
                    break
                bloque = bloque[:nb * paso].reshape(nb, paso, ancho_util // paso, paso)
                f0 = r0 // paso
                crudo[f0:f0 + nb] = bloque.mean(axis=(1, 3), dtype=np.float32)

    np.nan_to_num(crudo, copy=False, nan=0.0)
    np.multiply(crudo, 65535.0 / ESCALA_Q, out=crudo)
    np.clip(crudo, 0.0, 65535.0, out=crudo)
    plano = crudo.astype(np.uint16)
    del crudo
    return plano, x, y, h, lon0


# ------------------------------------------------------------------------ geometría
def _orto_franja(px: int, escala: float, centro: tuple[float, float], f0: int, f1: int):
    """(lon, lat, rho, dentro) de las filas ``f0:f1`` del disco.

    Misma proyección inversa que ``poster_goes_realista._orto_inverso``; acá se pide
    sólo una franja de filas para que los temporales en float64 no crezcan con ``px``.
    """
    lon0, lat0 = np.radians(centro[0]), np.radians(centro[1])
    y = np.linspace(1.0, -1.0, px)[f0:f1]
    x = np.linspace(-1.0, 1.0, px)
    X, Y = np.meshgrid(x, y)
    rho = np.hypot(X, Y)
    # Con zoom (`escala < 1`) el borde visible del disco cae FUERA del cuadro: el
    # encuadre regional entra completo y no quedan esquinas negras. Con escala = 1
    # (globo completo) el círculo inscripto recorta las esquinas, como siempre.
    dentro = (rho * escala) <= 1.0
    rho_s = np.where(dentro & (rho > 1e-12), rho, 1.0)
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


def _alfa(rho, px: int, escala: float = 1.0):
    """Alfa geométrico del disco: antialias de ~1.5 px sobre el borde visible.

    El borde visible está en `rho * escala = 1`. Con el globo completo (`escala=1`)
    es el círculo inscripto; con zoom cae fuera del cuadro y toda la imagen queda
    opaca.
    """
    return np.clip((1.0 - rho * escala) * (px / 2.0) / 1.5, 0.0, 1.0)


def _muestrear(plano, x, y, lon0: float, h: float, lon, lat):
    """Reflectancia muestreada en el disco para una franja; NaN donde no hay dato.

    Bilineal sobre la grilla de escaneo, igual que ``componer_disco``, pero recibiendo
    ``lon``/``lat`` ya calculados (la trigonometría se hace una sola vez por franja) y
    tocando sólo los vecinos de la franja: nunca se copia el plano entero.
    """
    xs, ys = _geo_scan(lon, lat, lon0, h)
    dx = float(x[1] - x[0])
    dy = float(y[1] - y[0])
    col = (xs - float(x[0])) / dx
    fila = (ys - float(y[0])) / dy
    del xs, ys

    alto, ancho = plano.shape
    ok = (col >= 0) & (col <= ancho - 1) & (fila >= 0) & (fila <= alto - 1)
    c0 = np.clip(np.floor(col), 0, ancho - 2).astype(np.intp)
    f0 = np.clip(np.floor(fila), 0, alto - 2).astype(np.intp)
    fc = np.clip(col - c0, 0.0, 1.0).astype(np.float32)
    ff = np.clip(fila - f0, 0.0, 1.0).astype(np.float32)
    del col, fila

    v00, v01 = plano[f0, c0], plano[f0, c0 + 1]
    v10, v11 = plano[f0 + 1, c0], plano[f0 + 1, c0 + 1]
    valores = ((v00 * (1 - fc) + v01 * fc) * (1 - ff)
               + (v10 * (1 - fc) + v11 * fc) * ff)
    # El plano trae 0 en el espacio: si algún vecino del entorno es 0, el píxel está en
    # la franja mezclada del limbo y no se usa.
    valido = np.minimum(np.minimum(v00, v01), np.minimum(v10, v11)) > 0
    valores *= ESCALA_Q / 65535.0
    return np.where(ok & valido, valores, np.nan).astype(np.float32)


# ------------------------------------------------------------------------ sol
def cos_cenital(lon, lat, t: datetime):
    """cos(ángulo cenital solar) por píxel (serie de Fourier de NOAA/Spencer).

    Error típico < 0.5° en la posición del terminador, suficiente para un póster y
    sin dependencias externas. Devuelve también la declinación usada (para el rótulo).
    """
    doy = t.timetuple().tm_yday
    frac = (t.hour + t.minute / 60.0) / 24.0
    g = 2.0 * np.pi / 365.0 * (doy - 1 + frac)
    decl = (0.006918 - 0.399912 * np.cos(g) + 0.070257 * np.sin(g)
            - 0.006758 * np.cos(2 * g) + 0.000907 * np.sin(2 * g)
            - 0.002697 * np.cos(3 * g) + 0.00148 * np.sin(3 * g))
    eqtime = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g)
                       - 0.014615 * np.cos(2 * g) - 0.040849 * np.sin(2 * g))
    minutos = t.hour * 60.0 + t.minute + eqtime + 4.0 * np.asarray(lon, dtype=np.float64)
    hora_angulo = np.radians(minutos / 4.0 - 180.0)
    phi = np.radians(np.asarray(lat, dtype=np.float64))
    return (np.sin(phi) * np.sin(decl)
            + np.cos(phi) * np.cos(decl) * np.cos(hora_angulo)).astype(np.float32), decl


def _suave(x, a: float, b: float):
    """Rampa 0..1 con derivada nula en los extremos (terminador sin escalón)."""
    u = np.clip((x - a) / (b - a), 0.0, 1.0)
    return u * u * (3.0 - 2.0 * u)


def _factor_solar(mu, args):
    """Peso de la normalización solar: 1 con sol alto, 0 pegado al terminador."""
    mu_ef = np.clip(mu, args.mu_min, 1.0)
    peso = _suave(mu, args.mu_min, args.mu_alto)
    return (1.0 - peso) + peso / mu_ef


# ------------------------------------------------------------------------ color
def _verde(rojo, nir, azul):
    """Verde sintético del ABI (receta CIMSS/Unidata). El peso del NIR es 0.10."""
    return 0.45 * rojo + 0.10 * nir + 0.45 * azul


def _luminancia(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def _parametros(refs, valido, mu, args) -> dict:
    """Pedestales por canal y percentiles del estirado, medidos sobre el disco."""
    dia = valido & (mu > 0.35)
    if not np.any(dia):
        dia = valido
    base = {c: float(np.percentile(v[dia], args.pedestal)) for c, v in refs.items()}
    rojo = np.clip(refs["rojo"] - base["rojo"], 0.0, None)
    nir = np.clip(refs["nir"] - base["nir"], 0.0, None)
    azul = np.clip(refs["azul"] - base["azul"], 0.0, None)
    rgb = np.dstack([rojo, _verde(rojo, nir, azul), azul])
    lum = _luminancia(rgb)
    muestra = lum[valido & (mu > 0.30)]
    if muestra.size == 0:
        muestra = lum[valido]
    lo, hi = np.percentile(muestra, [args.pct_lo, args.pct_hi])
    return {"base": base, "lo": float(lo), "hi": float(hi)}


def _componer(refs, mu, params, args):
    """Reflectancias -> RGB float 0..1 (pedestal, verde, estirado, saturación, noche)."""
    rojo = np.clip(refs["rojo"] - params["base"]["rojo"], 0.0, None)
    nir = np.clip(refs["nir"] - params["base"]["nir"], 0.0, None)
    azul = np.clip(refs["azul"] - params["base"]["azul"], 0.0, None)
    rgb = np.dstack([rojo, _verde(rojo, nir, azul), azul])
    del rojo, nir, azul

    rgb = (rgb - params["lo"]) / max(params["hi"] - params["lo"], 1e-6)
    lum = _luminancia(rgb)
    rgb = lum[..., None] + (rgb - lum[..., None]) * args.saturacion
    del lum
    rgb = np.clip(rgb, 0.0, 1.0) ** args.gamma
    rgb *= _suave(mu, -0.04, args.mu_noche)[..., None]
    return np.nan_to_num(rgb, nan=0.0)


def _mediana(rgb: np.ndarray) -> np.ndarray:
    """Mediana 3x3 por canal: mata el píxel suelto sin tocar bordes de nubes.

    Sobre océano oscuro y en el limbo el ABI entrega señal muy baja, y el estirado
    convierte cada píxel fuera de rango en un punto de color. La mediana los elimina
    de raíz (un desenfoque no: promedia y deja el punto).
    """
    from PIL import Image as _Image, ImageFilter as _Filter

    salida = np.empty_like(rgb, dtype=np.uint8)
    for k in range(3):
        canal = _Image.fromarray(rgb[..., k].astype(np.uint8), mode="L")
        salida[..., k] = np.asarray(canal.filter(_Filter.MedianFilter(3)),
                                    dtype=np.uint8)
    return salida


def _desenfoque(rgb: np.ndarray, radio: float) -> np.ndarray:
    """Desenfoque gaussiano por canal de un RGB uint8 (PIL, sin scipy).

    Pillow no soporta ``GaussianBlur`` sobre modo ``F``: se desenfoca el RGB ya
    cuantizado a 8 bits, que es la profundidad final del póster.
    """
    from PIL import Image as _Image, ImageFilter as _Filter

    salida = np.empty_like(rgb, dtype=np.uint8)
    for k in range(3):
        canal = _Image.fromarray(rgb[..., k].astype(np.uint8), mode="L")
        salida[..., k] = np.asarray(canal.filter(_Filter.GaussianBlur(radio)),
                                    dtype=np.uint8)
    return salida


# ------------------------------------------------------------------------ render
def componer_disco(planos, escala, centro, px: int, t: datetime, args):
    """Los tres planos -> RGBA del disco, franja por franja.

    Dos pasadas: la primera muestrea una malla gruesa para fijar pedestales y
    percentiles (que son globales), la segunda recorre el disco completo y escribe el
    RGBA. Así el pico de memoria no depende de ``px``.
    """
    pm = int(np.clip(px // 8, 256, 1400))
    lon, lat, rho, dentro = _orto_franja(pm, escala, centro, 0, pm)
    mu, _decl = cos_cenital(lon, lat, t)
    alfa_m = _alfa(rho, pm, escala) * dentro
    factor = _factor_solar(mu, args)
    valido = alfa_m > 0
    refs = {}
    for banda in BANDAS:
        plano, x, y, h, lon0 = planos[banda]
        refs[NOMBRE[banda]] = _muestrear(plano, x, y, lon0, h, lon, lat) * factor
        valido = valido & np.isfinite(refs[NOMBRE[banda]])
    params = _parametros(refs, valido, mu, args)
    del lon, lat, rho, dentro, mu, alfa_m, factor, valido, refs

    rgb = np.zeros((px, px, 3), dtype=np.uint8)
    alfa = np.zeros((px, px), dtype=np.uint8)
    for f0 in range(0, px, FILAS):
        f1 = min(f0 + FILAS, px)
        lon, lat, rho, dentro = _orto_franja(px, escala, centro, f0, f1)
        mu, _decl = cos_cenital(lon, lat, t)
        a = _alfa(rho, px, escala) * dentro
        factor = _factor_solar(mu, args)
        refs = {}
        for banda in BANDAS:
            plano, x, y, h, lon0 = planos[banda]
            refs[NOMBRE[banda]] = _muestrear(plano, x, y, lon0, h, lon, lat) * factor
        bloque = _componer(refs, mu, params, args)
        del refs, lon, lat, rho, dentro, mu, factor
        rgb[f0:f1] = np.clip(bloque * 255.0, 0, 255).astype(np.uint8)
        alfa[f0:f1] = (a * 255.0).astype(np.uint8)
        print(f"  franja {f1:5d}/{px}", flush=True)

    valido = alfa > 0
    if args.mediana:
        rgb = _mediana(rgb)
    if np.any(~valido & (alfa > 0)):
        rgb = _rellenar_huecos(rgb, valido)
    if args.suavizado > 0:
        rgb = _desenfoque(rgb, args.suavizado * px / 2400.0)
    # RGBA: sin el canal alfa el recuadro negro del array taparía el halo y el fondo.
    return np.dstack([rgb, alfa]), alfa, params


def render(nc_bandas: dict[str, Path], args) -> tuple:
    """Tres bandas -> disco RGB -> figura. Devuelve (fig, rgba, alfa, stats)."""
    nc01 = nc_bandas["C01"]
    escala, _h, _lon0 = radio_visible(nc01, tuple(args.centro), args.recorte)

    planos = {}
    for banda in BANDAS:
        print(f"  leyendo {banda}...", flush=True)
        planos[banda] = _plano(nc_bandas[banda], args.tope)

    t_slot = fecha_de(nc01) + timedelta(minutes=5)
    rgba, alfa, _params = componer_disco(planos, escala, tuple(args.centro),
                                         args.px, t_slot, args)
    del planos

    stats = {
        "validos": int((alfa > 0.5).sum()),
        "px": args.px,
    }
    fig = dibujar(rgba, escala, args.titulo, time_label_nc(nc01), args.fuente, args,
                  args.px, _focos_de(args, t_slot))
    return fig, rgba, alfa, stats


def _geometria(px: int, dpi: int | None):
    """Layout del póster: el disco llena el ancho y deja el pie para los créditos.

    El disco queda al 93 % del ancho (no al 96.5 % del póster térmico): sin tarjeta de
    leyenda, el margen superior es lo único que separa el planeta del título.
    """
    ancho_in, alto_in = 10.4, 11.0
    lado_in = 0.93 * ancho_in
    dpi = dpi or (px / lado_in)
    gw, gh = lado_in / ancho_in, lado_in / alto_in
    return ancho_in, alto_in, dpi, (1 - gw) / 2, 0.058, gw, gh


_CACHE_FOCOS: dict[str, list] = {}


def _focos_de(args, cuando: datetime) -> list:
    """Focos de FIRMS de este cuadro, o [] si el toggle está apagado.

    El CSV se lee una sola vez por carpeta: una serie de 24 cuadros no vuelve a
    abrir el archivo 24 veces.
    """
    carpeta = getattr(args, "firms_entrada", None)
    if not getattr(args, "firms", False) or not carpeta:
        return []
    if carpeta not in _CACHE_FOCOS:
        _CACHE_FOCOS[carpeta] = leer_carpeta(carpeta)
    desde, hasta = ventana(cuando, getattr(args, "firms_ventana", "dia"))
    focos = filtrar(_CACHE_FOCOS[carpeta], desde, hasta)
    if getattr(args, "firms_alcance", "completo") == "paraguay":
        from paraguay import dentro

        focos = [foco for foco in focos if dentro(foco.lon, foco.lat)]
    return focos


def _pintar_focos(ax, focos, centro, escala, px: int, dpi: float) -> None:
    """Marca los focos sobre el globo con la misma proyección que el contorno.

    `px` es el diámetro del disco en píxeles y el eje va de -1 a 1: el marcador se
    calcula en puntos, así se ve igual a cualquier `--px`.
    """
    if not focos:
        return
    x, y = _orto_directo(np.array([f.lon for f in focos], dtype=float),
                         np.array([f.lat for f in focos], dtype=float),
                         centro, escala)
    x, y = np.asarray(x), np.asarray(y)
    # Fuera del disco visible no se dibuja: ese foco está del otro lado del planeta.
    visible = np.hypot(x, y) <= 1.0
    if not visible.any():
        return
    colores = [color_hex(f.confianza) for f, dentro in zip(focos, visible) if dentro]
    factores = np.array([factor_gravedad(f) for f, dentro in zip(focos, visible)
                         if dentro])
    diametro = max(3.0, px * RADIO_FOCO * 2) * 72.0 / dpi
    ax.scatter(x[visible], y[visible], s=((diametro * 1.75) * factores) ** 2,
               c="#000000", alpha=0.30, linewidths=0, zorder=8.6)
    ax.scatter(x[visible], y[visible], s=(diametro * factores) ** 2, c=colores,
               alpha=0.90, linewidths=0, zorder=9)
    ax.scatter(x[visible], y[visible], s=((diametro * 0.42) * factores) ** 2,
               c="#fff8dc", alpha=0.92, linewidths=0, zorder=9.1)


def dibujar(disco, escala, titulo, tiempo, fuente, args, px, focos=()):
    """Dibuja el globo con el diseño del póster realista (sin tarjeta: no hay escala)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection

    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"]})
    ancho_in, alto_in, dpi, gx, gy, gw, gh = _geometria(px, args.dpi)

    if getattr(args, "limpio", False):
        # Modo "captura limpia": sin halo, sin sombreado de borde y sin rótulos.
        # El recorte entra de borde a borde y sólo queda la imagen (y el contorno).
        fig = plt.figure(figsize=(px / dpi, px / dpi), dpi=dpi)
        fig.patch.set_facecolor(WHITE)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(-1.0, 1.0)
        ax.set_ylim(-1.0, 1.0)
        ax.set_aspect("equal")
        ax.set_axis_off()
        ax.set_facecolor("none")
        # El RGB puede pedir bilinear: sin filo que rescatar, lanczos sumaría
        # un anillo brillante (por defecto, lanczos como siempre).
        interp = getattr(args, "interp", "lanczos")
        ax.imshow(disco, origin="upper", extent=[-1, 1, -1, 1],
                  interpolation=interp, zorder=2)
        centro = tuple(args.centro)
        if args.borde:
            poly = _lineas_geojson(args.borde)
            if poly:
                segs = [
                    np.column_stack(_orto_directo(
                        np.asarray(s)[:, 0], np.asarray(s)[:, 1], centro, escala))
                    for s in poly
                ]
                ax.add_collection(LineCollection(segs, colors="#10161b", linewidths=2.4,
                                                 alpha=0.45, zorder=7))
                ax.add_collection(LineCollection(segs, colors="#ffffff", linewidths=1.0,
                                                 alpha=0.95, zorder=8))
        _pintar_focos(ax, focos, centro, escala, px, dpi)
        return fig

    fig = plt.figure(figsize=(ancho_in, alto_in), dpi=dpi)
    fig.patch.set_facecolor(WHITE)

    ax = fig.add_axes([gx, gy, gw, gh])
    ax.set_xlim(-1.0, 1.0)
    ax.set_ylim(-1.0, 1.0)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_facecolor("none")

    halo, ext = sombra_exterior(px)
    pad = (ext - 1.0) / 2.0
    ax_halo = fig.add_axes([gx - pad * gw, gy - pad * gh, ext * gw, ext * gh])
    ax_halo.set_zorder(-1)
    ax_halo.set_axis_off()
    ax_halo.patch.set_alpha(0.0)
    ax_halo.imshow(halo, origin="upper", extent=[0, 1, 0, 1], interpolation="bilinear")

    ax.imshow(sombrear_borde(disco, args.sombra_borde), origin="upper",
              extent=[-1, 1, -1, 1],
              interpolation=getattr(args, "interp", "lanczos"), zorder=2)

    centro = tuple(args.centro)
    if args.lineas:
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
                colors=COAST, linewidths=0.55, alpha=0.55, zorder=6))
    if args.fronteras:
        bordes = _lineas_natural_earth("cultural", "admin_0_boundary_lines_land", "50m")
        if bordes:
            ax.add_collection(LineCollection(
                [np.column_stack(_orto_directo(np.asarray(s)[:, 0], np.asarray(s)[:, 1],
                                               centro, escala)) for s in bordes],
                colors=BORDER, linewidths=0.35, alpha=0.26,
                linestyles=(0, (2, 2)), zorder=6))
    if args.borde:
        poly = _lineas_geojson(args.borde)
        if poly:
            segs = [np.column_stack(_orto_directo(np.asarray(s)[:, 0], np.asarray(s)[:, 1],
                                                  centro, escala)) for s in poly]
            ax.add_collection(LineCollection(segs, colors="#10161b", linewidths=2.4,
                                             alpha=0.45, zorder=7))
            ax.add_collection(LineCollection(segs, colors="#ffffff", linewidths=1.0,
                                             alpha=0.95, zorder=8))

    _pintar_focos(ax, focos, centro, escala, px, dpi)

    # Sin aro de limbo: en un póster de color real el borde lo define el alfa del disco.
    # El círculo del póster térmico, sobre el negro de la noche, se leía como un aro
    # blanco flotando fuera del planeta.
    # Marca de agua sobre el margen inferior del globo, no encima del disco: en color
    # real la mitad sur del planeta es océano casi negro y el texto desaparecía.
    if args.credito:
        fig.text(0.5, gy - 0.010, " ".join(args.credito.upper()), ha="center",
                 va="center", fontsize=8.6, color=(0.31, 0.35, 0.39, 0.40),
                 fontfamily="Segoe UI", zorder=10)

    fig.text(0.027, 0.988, titulo, ha="left", va="top", fontsize=14.5, color=INK,
             fontfamily="Segoe UI")
    fig.text(0.027, 0.960, tiempo.upper(), ha="left", va="top", fontsize=9.2,
             color=INK_SOFT, fontfamily="Segoe UI")
    fig.text(0.027, 0.012, fuente, ha="left", va="bottom", fontsize=8.2,
             color="#a3a8ad", fontfamily="Segoe UI")
    if args.credito:
        fig.text(0.973, 0.012, args.credito, ha="right", va="bottom", fontsize=8.4,
                 color="#a3a8ad", fontfamily="Segoe UI")
    return fig


# ------------------------------------------------------------------------ CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Póster de color real (globo Orthographic, fondo blanco) de GOES-19 "
                    "compuesto con las bandas visibles B1+B2+B3.")
    ap.add_argument("--desde", help="slot UTC ISO (por defecto, el último completo)")
    ap.add_argument("--sat", default=SAT, help=f"satélite (por defecto {SAT})")
    ap.add_argument("--px", type=int, default=PX,
                    help=f"diámetro del globo en px (por defecto {PX}, la resolución "
                         "nativa de 1 km)")
    ap.add_argument("--dpi", type=int, default=None, help="dpi; si se omite se deduce de --px")
    ap.add_argument("--tope", type=int, default=TOPE,
                    help=f"grilla de origen de cada banda (por defecto {TOPE}: nativa "
                         "en C01/C03 y 2x en C02)")
    ap.add_argument("--centro", nargs=2, type=float, metavar=("LON", "LAT"),
                    default=list(CENTRO), help=f"centro del globo (por defecto {CENTRO})")
    ap.add_argument("--recorte", type=float, default=None,
                    help="fuerza la fracción del radio visible (por defecto se deduce "
                         "del centro para no tocar la franja estirada del limbo)")
    ap.add_argument("--saturacion", type=float, default=SATURACION,
                    help=f"saturación del color, 1 = neutra (por defecto {SATURACION})")
    ap.add_argument("--gamma", type=float, default=GAMMA,
                    help=f"gamma del RGB (por defecto {GAMMA})")
    ap.add_argument("--pedestal", type=float, default=PEDESTAL,
                    help=f"percentil del pedestal atmosférico (por defecto {PEDESTAL})")
    ap.add_argument("--pct-lo", type=float, default=PCT_LO,
                    help=f"percentil bajo del estirado (por defecto {PCT_LO})")
    ap.add_argument("--pct-hi", type=float, default=PCT_HI,
                    help=f"percentil alto del estirado (por defecto {PCT_HI})")
    ap.add_argument("--mu-min", type=float, default=MU_MIN,
                    help=f"piso de cos(cenital) en la normalización solar (por defecto {MU_MIN})")
    ap.add_argument("--mu-alto", type=float, default=MU_ALTO,
                    help=f"cos(cenital) con sol alto: normalización completa "
                         f"(por defecto {MU_ALTO})")
    ap.add_argument("--mu-noche", type=float, default=MU_NOCHE,
                    help=f"cos(cenital) donde termina la rampa de noche (por defecto {MU_NOCHE})")
    ap.add_argument("--suavizado", type=float, default=SUAVIZADO,
                    help=f"desenfoque final en px del disco de 2400 (por defecto {SUAVIZADO}); "
                         "0 lo apaga")
    ap.add_argument("--mediana", action=argparse.BooleanOptionalAction, default=True,
                    help="mediana 3x3 contra el píxel suelto (por defecto, sí)")
    ap.add_argument("--sombra-borde", type=float, default=0.18,
                    help="profundidad del borde 0..0.8 (por defecto 0.18)")
    ap.add_argument("--titulo", default=TITULO, help="título del póster")
    ap.add_argument("--fuente", default=FUENTE, help="línea de fuente al pie")
    ap.add_argument("--credito", default=CREDITO, help="crédito al pie; vacío = sin crédito")
    ap.add_argument("--borde", nargs="?", const=str(BORDE_SA), default=str(BORDE_SA),
                    help="contorno destacado sobre el globo (por defecto, Paraguay); "
                         "pasá --borde \"\" para sacarlo")
    ap.add_argument("--fronteras", action=argparse.BooleanOptionalAction, default=True,
                    help="límites políticos punteados (por defecto, sí)")
    ap.add_argument("--limpio", action="store_true",
                    help="captura limpia: sin titulos, creditos, halo ni sombreado de borde")
    ap.add_argument("--out", help="PNG de salida (por defecto, en comun.rutas.SALIDAS)")
    ap.add_argument("--fondo", choices=["claro", "oscuro"], default="claro",
                    help="fondo del poster (por defecto, claro)")
    ap.add_argument("--lineas", action=argparse.BooleanOptionalAction, default=True,
                    help="reticula y costas (por defecto, si); --no-lineas deja la imagen limpia")
    ap.add_argument("--frames", help="carpeta de cuadros: renderiza una serie numerada")
    ap.add_argument("--n", type=int, default=1, help="cantidad de cuadros de la serie")
    ap.add_argument("--paso", type=int, default=10, help="minutos entre cuadros")
    ap.add_argument("--forzar", action="store_true", help="rehace cuadros ya existentes")
    ap.add_argument("--firms", action="store_true",
                    help="superpone los focos de calor de NASA FIRMS")
    ap.add_argument("--firms-ventana", default=VENTANAS[0], choices=VENTANAS,
                    help="ventana de focos: dia = dia UTC completo (default)")
    ap.add_argument("--firms-entrada",
                    help="carpeta con los CSV de focos (los deja descargar/firms.py)")
    ap.add_argument("--firms-alcance", default="completo",
                    choices=("completo", "paraguay"),
                    help="completo = todos los focos del area; paraguay = solo los "
                         "que caen dentro del pais")
    args = ap.parse_args(argv)
    args.fuente = args.fuente.replace("{sat}", args.sat)
    if args.firms:
        args.fuente = f"{args.fuente} | FIRMS hotspots"

    if args.fondo == "oscuro":
        # Mismo póster, tinta invertida: sobre negro la tinta oscura no se lee.
        global WHITE, INK, INK_SOFT, COAST, BORDER, GRID
        WHITE = "#000000"
        INK = "#eef2f5"
        INK_SOFT = "#9aa0a6"
        COAST = "#cfd6dc"
        BORDER = "#cfd6dc"
        GRID = "#5a6672"

    desde = datetime.fromisoformat(args.desde) if args.desde else None
    lista = slots_comunes(desde, args.n if args.frames else 1, args.paso,
                          BANDAS, args.sat)

    if args.frames:
        return _serie(lista, args)

    nc_bandas = lista[0]
    t0 = fecha_de(nc_bandas["C01"])
    print(f"{Path(nc_bandas['C01']).name}\nslot: {t0:%Y-%m-%d %H:%M} UTC | "
          f"globo {args.px} px | centro {tuple(args.centro)} | "
          f"saturación {args.saturacion} | gamma {args.gamma}", flush=True)

    fig, _rgba, _alfa, stats = render(nc_bandas, args)
    print(f"disco {stats['px']} px | {stats['validos']:,} px con dato")

    out = Path(args.out) if args.out else (
        SALIDAS / f"poster_G19_truecolor_{t0:%Y-%m-%dT%H%M}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    parcial = out.with_suffix(".png.parcial")
    fig.savefig(parcial, format="png", facecolor=WHITE)
    import matplotlib.pyplot as plt
    plt.close(fig)
    parcial.replace(out)
    print(f"PNG: {out}")
    print("Serie de cuadros: .venv\\Scripts\\python.exe "
          "prototipos\\poster_goes_truecolor.py "
          f"--frames \"{SALIDAS / 'frames_G19_truecolor'}\" --n 24")
    return 0


def _serie(lista: list[dict[str, Path]], args) -> int:
    """Renderiza una serie de cuadros con el mismo diseño (insumo de la animación)."""
    salida = Path(args.frames)
    salida.mkdir(parents=True, exist_ok=True)
    print(f"{len(lista)} cuadros desde {fecha_de(lista[0]['C01']):%Y-%m-%d %H:%M} UTC "
          f"-> {salida}", flush=True)
    for i, nc_bandas in enumerate(lista, 1):
        destino = salida / f"cuadro_{i:03d}.png"
        if destino.exists() and not args.forzar:
            continue
        fig, *_ = render(nc_bandas, args)
        import matplotlib.pyplot as plt
        parcial = destino.with_suffix(".png.parcial")
        fig.savefig(parcial, format="png", facecolor=WHITE)
        plt.close(fig)
        parcial.replace(destino)
        print(f"  [{i}/{len(lista)}] {fecha_de(nc_bandas['C01']):%Y-%m-%d %H:%M} UTC",
              flush=True)
    print(f"Cuadros en {salida}")
    print(f"Armá el video con: .venv\\Scripts\\python.exe animar\\armar.py --frames "
          f"\"{salida}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
