"""Renderiza los cuadros de una animación **Sandwich RGB** (GOES-19) desde los crudos.

La descarga vive aparte, en `descargar/sandwich.py`; acá se leen los **dos** crudos de
cada cuadro (`crudo_NNN_vis.jpg` + `crudo_NNN_ir.jpg`), se **componen** en el Sandwich y
recién después se reproyectan al globo. Se guardan como `cuadro_NNN.png` con el vestuario
del póster (costas, borde destacado y rótulos). Si falta algún crudo, aborta nombrando el
comando de descarga.

El Sandwich **no es un RGB de tres bandas**: mezcla dos imágenes. La fórmula (validada con
prototipo e inspección visual) es `salida = alpha · visible + (1 - alpha) · IR_realzado`,
con el IR pasado por una rampa de color (frío -> rojo/naranja/amarillo/verde/cian) de la
misma familia que `poster_goes.IR_REALCE_COLORS`. Sirve para monitorear convección
profunda: el visible aporta la **morfología** del tope nuboso y el IR, su **temperatura**.
Es un producto **sólo diurno** (el visible necesita sol), por eso la serie son los tramos
diurnos de cada día (`serie_diurna`, de `comun/series.py`).

El warping a Orthographic se hace a mano con numpy (mapeo inverso + interpolación
bilineal) porque el `warp_array` de cartopy exige `pykdtree` o `scipy`, que este venv no
trae; con la imagen ya en la proyección del eje, `imshow` recibe el atajo y no importa
`img_transform`.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe cuadros\\cuadros_sandwich.py --desde 2026-10-04 --hasta 2026-10-05 --hora-desde 10 --hora-hasta 22 --paso 10 --px 2048
    .venv\\Scripts\\python.exe cuadros\\cuadros_sandwich.py --help
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from rutas import SALIDAS  # noqa: E402
from series import etiqueta_frames, serie_diurna  # noqa: E402

# Rol -> capa GIBS. El MISMO par vive en `descargar/sandwich.py`: el repo duplica las
# constantes entre descarga y render y los roles (`vis`/`ir`) tienen que coincidir para
# que las dos apunten a los mismos archivos `crudo_NNN_vis.jpg` / `crudo_NNN_ir.jpg`.
CAPAS = {
    "vis": "GOES-East_ABI_Band2_Red_Visible_1km",
    "ir": "GOES-East_ABI_Band13_Clean_Infrared",
}

# Caja de globo: la misma de la descarga y de geocolor. Si no coincidiera con la caja con
# la que se bajaron los crudos, el warp muestrearía la imagen equivocada.
BBOX_GLOBO = (-160.0, -80.0, 15.0, 80.0)        # oeste, sur, este, norte
# Mismo centro por defecto del resto del repo (Paraguay).
GLOBO_LON, GLOBO_LAT = -58.0, -23.0

# Rampa del IR realzado: posición 0 = lo más frío (tope de convección), 1 = lo más cálido.
# Misma familia que `poster_goes.IR_REALCE_COLORS`, coherente con el resto del repo.
RAMPA_IR = [
    (0.00, (255, 32, 32)), (0.08, (224, 0, 0)), (0.14, (255, 128, 0)),
    (0.20, (240, 240, 0)), (0.26, (0, 224, 0)), (0.32, (0, 200, 255)),
    (0.38, (0, 80, 255)), (0.45, (10, 42, 143)),
    (0.55, (176, 176, 176)), (0.70, (140, 140, 140)), (1.00, (90, 90, 90)),
]
# Posiciones y colores de la rampa, separados por canal, para interpolar con np.interp.
_POS_IR = np.array([p for p, _ in RAMPA_IR], dtype=np.float32)
_COL_IR = np.array([c for _, c in RAMPA_IR], dtype=np.float32)   # (N, 3)

# Dos líneas, como el subtítulo del póster: en una sola se sale del cuadro.
SUBTITULO = "G19 GOES-EAST · SANDWICH RGB\nVISIBLE (0.64 µm) + IR REALZADO (10.3 µm)"
FUENTE = "SOURCE: NOAA/NESDIS GOES-19 ABI · NASA GIBS"
# Abreviatura de mes para la línea de tiempo (sub-diaria, con hora), coherente con
# MONTHS_EN de comun/estilo.py.
MESES_ABREV = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN",
               "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
# Los rótulos están calibrados a la animación de 720 px del repo (19 pt de título), pero
# escalarlos linealmente hace que a 2048 px dominen el cuadro. Crecen sub-lineal (exponente
# 0.45) y con este factor: legibles en chico, discretos en grande.
ESCALA_TEXTO = 0.8
DESDE = "2026-10-04"                    # UTC (fecha)
HASTA = "2026-10-05"                    # UTC, inclusive (fecha)
HORA_DESDE = 10                         # UTC
HORA_HASTA = 22                         # UTC
PASO_MIN = 10                           # minutos
PX = 2048                               # lado del globo en píxeles
ALPHA = 0.5                             # mezcla del Sandwich (50/50 es el clásico)
# Radio del disco en grados: 90 = el hemisferio entero. GOES-East cubre ~81° desde su
# punto subsatelital, así que un globo de 90° centrado en Paraguay deja un gajo sin dato
# al este; con ~53° el disco entra entero y no se ve ningún hueco.
RADIO = 90.0
CREDITO = "Graphic by @Gillo97"

FUENTES = [
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\arial.ttf",
]


def _fuente(px: int) -> ImageFont.ImageFont:
    """Primera tipografía TrueType disponible; si no hay, la bitmap de Pillow."""
    for ruta in FUENTES:
        if Path(ruta).exists():
            try:
                return ImageFont.truetype(ruta, px)
            except OSError:
                continue
    return ImageFont.load_default()


def _rampa_ir(t: np.ndarray) -> np.ndarray:
    """Color RGB del IR realzado para la posición `t` (0 = más frío, 1 = más cálido).

    Interpolación lineal por canal entre los nodos de `RAMPA_IR`. Devuelve float32 HxWx3
    (sin recortar ni castear: `componer` hace el clip y el uint8 al final).
    """
    r = np.interp(t, _POS_IR, _COL_IR[:, 0]).astype(np.float32)
    g = np.interp(t, _POS_IR, _COL_IR[:, 1]).astype(np.float32)
    b = np.interp(t, _POS_IR, _COL_IR[:, 2]).astype(np.float32)
    return np.stack([r, g, b], axis=-1)


def componer(vis_path: Path, ir_path: Path, alpha: float) -> np.ndarray:
    """Arma el Sandwich RGB (uint8 HxWx3) a partir del visible y el IR en gris.

    `vis` y `ir` llegan como gris 0–255. El IR se normaliza (`t = 1 - ir/255`, así 0 =
    más frío) y se colorea con la rampa; el visible se replica a tres canales. La salida
    mezcla ambos con `alpha` (1 = sólo visible, 0 = sólo IR realzado).
    """
    vis = np.asarray(Image.open(vis_path).convert("L"), dtype=np.float32)
    ir = np.asarray(Image.open(ir_path).convert("L"), dtype=np.float32)
    if vis.shape != ir.shape:
        raise ValueError(f"tamaños distintos: vis {vis.shape} vs ir {ir.shape}")
    t = 1.0 - ir / 255.0
    ir_color = _rampa_ir(t)
    # Liberar el IR crudo antes de armar el RGB del visible: son dos temporales grandes.
    del ir
    vis_rgb = np.repeat(vis[..., None], 3, axis=2)
    del vis
    salida = alpha * vis_rgb + (1.0 - alpha) * ir_color
    return np.clip(salida, 0.0, 255.0).astype(np.uint8)


def etiquetar(img: Image.Image, t: datetime, credito: str) -> Image.Image:
    """Marca de agua discreta: fecha/hora UTC abajo a la izquierda, crédito a la derecha."""
    img = img.convert("RGB")
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    ancho, alto = img.size
    texto = t.strftime("%Y-%m-%d %H:%M UTC")
    f = _fuente(max(11, ancho // 34))
    margen = max(8, ancho // 60)
    # Sombra + texto, para que se lea tanto sobre nubes claras como sobre el gris del IR.
    for dx, dy in ((0, 1), (1, 0), (0, 0)):
        d.text((margen + dx, alto - margen - 18 + dy), texto, font=f, fill=(0, 0, 0, 190))
    d.text((margen, alto - margen - 18), texto, font=f, fill=(255, 255, 255, 235))
    if credito:
        f2 = _fuente(max(10, ancho // 42))
        caja = d.textbbox((0, 0), credito, font=f2)
        ancho_c = caja[2] - caja[0]
        x = ancho - margen - ancho_c
        y = alto - margen - 16
        for dx, dy in ((0, 1), (1, 0), (0, 0)):
            d.text((x + dx, y + dy), credito, font=f2, fill=(0, 0, 0, 190))
        d.text((x, y), credito, font=f2, fill=(255, 255, 255, 220))
    return Image.alpha_composite(img.convert("RGBA"), capa).convert("RGB")


def _estilo_poster():
    """Constantes del póster del repo, compartidas en `comun/estilo.py`."""
    from estilo import BG, MONTHS_EN, TXT, TXT_DIM, WM_COLOR
    return BG, TXT, TXT_DIM, WM_COLOR, MONTHS_EN


def _borde_geojson(ax, ruta, color, ancho):
    """Contorno destacado (p. ej. Paraguay) sobre el globo."""
    if not ruta:
        return
    import json
    from matplotlib.collections import LineCollection
    import cartopy.crs as ccrs
    try:
        gj = json.load(open(ruta, encoding="utf-8"))
    except Exception as exc:
        print(f"AVISO: borde omitido ({exc})")
        return
    feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
    segs = []
    for f in feats:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            for ring in poly:
                segs.append(np.asarray(ring, dtype=float))
    if segs:
        ax.add_collection(LineCollection(segs, transform=ccrs.PlateCarree(),
                                         colors=color, linewidths=ancho, zorder=5))


def _warp_ortho(rgb, bbox, centro, lado, radio_grados=90.0):
    """Reproyecta una imagen lon/lat a Orthographic (mapeo inverso, con numpy).

    Para cada píxel del disco de destino se calcula su (lon, lat) y se muestrea la
    imagen de origen con interpolación bilineal. Fuera del disco, o donde la caja de
    origen no tiene dato, el alfa queda en 0 y se ve el fondo.

    `radio_grados` es la distancia angular al centro que cae en el **borde** del disco
    dibujado. Con 90° (el default) el disco es el globo entero —el hemisferio—; con
    menos, el mismo cuadro muestra un recorte más chico (un zoom). Sirve para que la
    imagen entre entera dentro de lo que ve el satélite: el disco de GOES-East cubre
    ~81° desde su punto subsatelital, así que un globo de 90° centrado en Paraguay deja
    un gajo sin dato al este; con un radio más chico, ese gajo queda fuera del cuadro.

    ¿Por qué a mano y no con `imshow(transform=PlateCarree)`? Porque el warping de
    cartopy importa `warp_array`, que exige `pykdtree` o `scipy` — y este venv no los
    tiene. Haciendo el warp nosotros, `imshow` recibe la imagen ya en la proyección del
    eje y cartopy toma el atajo (no importa `img_transform`).
    """
    o, s, e, n = bbox
    lon0, lat0 = np.radians(centro[0]), np.radians(centro[1])
    alto_o, ancho_o = rgb.shape[:2]

    # Disco normalizado: x, y en [-1, 1], radio 1 = `radio_grados` de distancia al centro.
    y = np.linspace(1.0, -1.0, lado)        # la fila 0 es el norte
    x = np.linspace(-1.0, 1.0, lado)
    X, Y = np.meshgrid(x, y)
    rho = np.hypot(X, Y)
    dentro = rho <= 1.0

    rho_s = np.where(dentro & (rho > 1e-12), rho, 1.0)   # evita 0/0 en el centro
    # rho = 1 cae sobre `radio_grados`: el seno sale del mapeo inverso de la Orthographic
    # (sin(c) = rho · sin(radio)), no de un factor de zoom suelto.
    c = np.arcsin(np.clip(rho_s * np.sin(np.radians(radio_grados)), 0.0, 1.0))
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

    # Posición de muestreo en la imagen de origen (plate carrée).
    col = (lon_deg - o) / (e - o) * (ancho_o - 1)
    fila = (n - lat_deg) / (n - s) * (alto_o - 1)
    valido = (dentro & (col >= 0) & (col <= ancho_o - 1)
              & (fila >= 0) & (fila <= alto_o - 1))

    c0 = np.clip(np.floor(col), 0, ancho_o - 2).astype(np.intp)
    f0 = np.clip(np.floor(fila), 0, alto_o - 2).astype(np.intp)
    # Los pesos de la interpolación van en float32: en float64 el mezclado aloca
    # temporales enormes y, con un origen grande, el proceso se queda sin RAM a mitad
    # del lote.
    fc = np.clip(col - c0, 0.0, 1.0).astype(np.float32)[..., None]
    ff = np.clip(fila - f0, 0.0, 1.0).astype(np.float32)[..., None]
    # La geometría ya no se usa: liberarla antes del mezclado deja lugar para los
    # temporales (son varias matrices de lado x lado en float64).
    del X, Y, rho, rho_s, c, sin_c, cos_c, lon, lat, lon_deg, lat_deg, col, fila
    a = rgb[f0, c0].astype(np.float32)
    b = rgb[f0, c0 + 1].astype(np.float32)
    cc = rgb[f0 + 1, c0].astype(np.float32)
    d = rgb[f0 + 1, c0 + 1].astype(np.float32)
    mezcla = (a * (1 - fc) + b * fc) * (1 - ff) + (cc * (1 - fc) + d * fc) * ff

    alfa = np.where(valido, 255, 0).astype(np.uint8)[..., None]
    return np.concatenate([np.clip(mezcla, 0, 255).astype(np.uint8), alfa], axis=2)


def render_globo(vis_crudo: Path, ir_crudo: Path, t: datetime, args, destino: Path) -> Path:
    """Compone el Sandwich, lo reproyecta a Orthographic y dibuja el vestuario del póster.

    Los dos crudos llegan en EPSG:4326 (plano lon/lat); `componer` los mezcla y
    `_warp_ortho` lleva el composite al disco Orthographic. Acá sólo se dibuja, con las
    costas, el borde y el rótulo del póster.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    BG, TXT, TXT_DIM, WM_COLOR, MONTHS_EN = _estilo_poster()
    lon0, lat0 = args.centro
    # El composite se arma ANTES de warpear: el warp trabaja sobre una sola imagen (la
    # mezcla), no sobre dos, así no se reproyecta dos veces lo mismo.
    comp = componer(vis_crudo, ir_crudo, args.alpha)

    lado = args.px / args.dpi
    fig = plt.figure(figsize=(lado, lado), dpi=args.dpi)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0.014, 0.014, 0.972, 0.972],
                      projection=ccrs.Orthographic(central_longitude=lon0,
                                                   central_latitude=lat0))
    ax.set_facecolor(BG)
    ax.spines["geo"].set_visible(False)
    # El warp va antes y en coordenadas de la proyección del eje: así cartopy no
    # reproyecta nada y evita el import de `img_transform` (que pide scipy/pykdtree).
    disco = _warp_ortho(comp, args.bbox, args.centro, args.px, args.radio)
    xl, yl = ax.projection.x_limits, ax.projection.y_limits
    ax.imshow(disco, origin="upper", extent=[xl[0], xl[1], yl[0], yl[1]],
              transform=ax.projection, zorder=2)
    ax.set_global()
    try:
        ax.add_feature(cfeature.COASTLINE.with_scale("110m"), linewidth=0.5,
                       edgecolor="#0b0b0b", zorder=4)
        ax.add_feature(cfeature.BORDERS.with_scale("110m"), linewidth=0.35,
                       edgecolor="#0b0b0b", linestyle=":", zorder=4)
    except Exception as exc:
        print(f"AVISO: costas omitidas ({exc})")
    _borde_geojson(ax, args.geojson, args.borde_color, args.borde_ancho)

    # Referencia: la animación de 720 px del repo, pero sub-lineal (ver ESCALA_TEXTO).
    esc = ESCALA_TEXTO * (args.px / 720.0) ** 0.45
    fig.text(0.026, 0.985, f"{MONTHS_EN[t.month - 1]} {t.year}", color=TXT,
             fontsize=19 * esc, fontweight="bold", ha="left", va="top")
    # El Sandwich es sub-diario, así que la fecha va con hora (a diferencia de True Color,
    # que es una composición diaria).
    if not args.sin_fecha:
        fig.text(0.026, 0.944,
                 f"{t:%d} {MESES_ABREV[t.month - 1]} {t:%Y} · {t:%H:%M} UTC", color=TXT,
                 fontsize=16 * esc, fontweight="bold", ha="left", va="top")
    fig.text(0.026, 0.898, SUBTITULO, color=TXT_DIM, fontsize=13.5 * esc,
             fontweight="bold", ha="left", va="top", linespacing=1.12)
    fig.text(0.983, 0.983, args.credito, color=TXT_DIM, fontsize=12 * esc,
             ha="right", va="top")
    fig.text(0.026, 0.012, FUENTE, color=TXT_DIM, fontsize=7.4 * esc, ha="left",
             va="bottom")
    fig.text(0.980, 0.012, f"DATA: {t:%Y-%m-%dT%H:%M} UTC · ZONA SA", color=TXT_DIM,
             fontsize=7.4 * esc, ha="right", va="bottom")
    if args.credito:
        fig.text(0.5, 0.150, " ".join(args.credito.upper()), color=WM_COLOR,
                 fontsize=8.5 * esc, ha="center", va="bottom")

    # Guardado atómico: si el proceso se corta a mitad, no queda un PNG corrupto que
    # después se reutilice como si estuviera bueno.
    parcial = destino.with_suffix(".png.parcial")
    fig.savefig(parcial, format="png", facecolor=BG)
    plt.close(fig)
    parcial.replace(destino)
    return destino


def _sello_render(args) -> str:
    """Huella de los parámetros que cambian el aspecto del cuadro.

    Los PNG se reutilizan por fecha de mtime, así que si cambiás el texto, el borde, la
    escala o el `alpha` de la mezcla, los viejos quedarían con el aspecto anterior sin que
    nadie lo note. Incluye el `alpha`: cambiar la mezcla visible/IR tiene que descartar
    los PNG viejos, no reutilizarlos.
    """
    import hashlib
    import json
    datos = {
        "px": args.px, "dpi": args.dpi, "alto": args.px, "centro": list(args.centro),
        "bbox": list(args.bbox), "alpha": args.alpha, "radio": args.radio,
        "credito": args.credito,
        "sin_fecha": args.sin_fecha, "geojson": args.geojson or "",
        "borde_color": args.borde_color, "borde_ancho": args.borde_ancho,
        "escala_texto": ESCALA_TEXTO, "subtitulo": SUBTITULO, "fuente": FUENTE,
    }
    return hashlib.sha256(json.dumps(datos, sort_keys=True).encode()).hexdigest()[:16]


def _comando_descarga(args) -> str:
    """Comando de `descargar/sandwich.py` que genera los crudos de esta corrida."""
    cmd = (f".venv\\Scripts\\python.exe descargar\\sandwich.py "
           f"--desde {args.desde} --hasta {args.hasta} "
           f"--hora-desde {args.hora_desde} --hora-hasta {args.hora_hasta} "
           f"--paso {args.paso} --px {args.px}")
    return cmd + (f' --out "{args.out}"' if args.out else "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Cuadros (PNG) de una animación Sandwich RGB (GOES-19) desde los "
                    "crudos de visible + IR.")
    ap.add_argument("--desde", default=DESDE,
                    help=f"primer día, UTC (por defecto {DESDE})")
    ap.add_argument("--hasta", default=HASTA,
                    help=f"último día, UTC inclusive (por defecto {HASTA})")
    ap.add_argument("--hora-desde", type=int, default=HORA_DESDE,
                    help=f"hora UTC de arranque de cada tramo diurno (por defecto "
                         f"{HORA_DESDE})")
    ap.add_argument("--hora-hasta", type=int, default=HORA_HASTA,
                    help=f"hora UTC de fin de cada tramo diurno (por defecto {HORA_HASTA})")
    ap.add_argument("--paso", type=int, default=PASO_MIN,
                    help=f"minutos entre cuadros (por defecto {PASO_MIN})")
    ap.add_argument("--px", type=int, default=PX,
                    help=f"lado del globo en píxeles (por defecto {PX})")
    ap.add_argument("--dpi", type=int, default=140, help="dpi del render del globo")
    ap.add_argument("--centro", nargs=2, type=float, metavar=("LON", "LAT"),
                    default=[GLOBO_LON, GLOBO_LAT],
                    help=f"centro del globo (por defecto {GLOBO_LON} {GLOBO_LAT})")
    ap.add_argument("--radio", type=float, default=RADIO,
                    help=f"grados de distancia al centro que abarca el borde del disco "
                         f"(por defecto {RADIO:.0f}: el hemisferio entero). Bajalo para "
                         "achicar el encuadre y que no entre el gajo sin dato de GOES")
    ap.add_argument("--alpha", type=float, default=ALPHA,
                    help=f"mezcla del Sandwich: 1 = sólo visible, 0 = sólo IR realzado "
                         f"(por defecto {ALPHA})")
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("O", "S", "E", "N"),
                    default=list(BBOX_GLOBO),
                    help=f"caja lon/lat de origen (por defecto, el globo {BBOX_GLOBO})")
    ap.add_argument("--geojson", default=str(RAIZ / "datos" / "paraguay_gadm.json"),
                    help="borde destacado en el globo (GeoJSON); vacío = sin borde")
    ap.add_argument("--borde-color", default="#000000", help="color del borde destacado")
    ap.add_argument("--borde-ancho", type=float, default=0.8,
                    help="grosor del borde destacado")
    ap.add_argument("--credito", default=CREDITO, help="crédito de la marca de agua")
    ap.add_argument("--sin-fecha", action="store_true",
                    help="no estampar la fecha/hora en el cuadro")
    ap.add_argument("--out", help="carpeta de salida (por defecto, comun.rutas.SALIDAS)")
    args = ap.parse_args(argv)

    if not (0.0 <= args.alpha <= 1.0):
        raise SystemExit(f"--alpha fuera de [0, 1]: {args.alpha}")

    o, s, e, n = args.bbox
    if not (o < e and s < n):
        raise SystemExit(f"caja inválida: {args.bbox}")

    # La serie y la etiqueta salen de comun/series.py: la descarga calculó lo mismo.
    fechas = serie_diurna(args.desde, args.hasta, args.hora_desde, args.hora_hasta,
                          args.paso)
    if not fechas:
        raise SystemExit("La serie de cuadros está vacía: revisá --desde/--hasta/"
                         "--hora-desde/--hora-hasta/--paso.")
    t0, n_cuadros = fechas[0], len(fechas)

    salida = Path(args.out) if args.out else SALIDAS
    frames_dir = salida / f"frames_{etiqueta_frames('sandwich', 'globo', t0, n_cuadros, args.px)}"

    if not frames_dir.exists():
        raise SystemExit(f"No existe {frames_dir}. Descargá los cuadros con:\n"
                         f"  {_comando_descarga(args)}")

    # Si cambió algo del aspecto, los cuadros ya renderizados quedaron viejos: se borran,
    # así se rehacen en vez de reutilizarse con el rótulo anterior.
    sello = _sello_render(args)
    archivo_sello = frames_dir / ".sello_render"
    previo = (archivo_sello.read_text(encoding="utf-8").strip()
              if archivo_sello.exists() else None)
    if previo is not None and previo != sello:
        viejos = list(frames_dir.glob("cuadro_*.png"))
        for p in viejos:
            p.unlink()
        print(f"Cambiaron los parámetros de render -> se descartan {len(viejos)} cuadros")
    archivo_sello.write_text(sello, encoding="utf-8")

    # Sólo se leen los crudos: si falta alguno no se puede armar la secuencia, y el
    # comando que los genera se nombra tal cual (la descarga calcula los mismos cuadros).
    faltan = [i for i in range(1, n_cuadros + 1)
              if not (frames_dir / f"crudo_{i:03d}_vis.jpg").exists()
              or not (frames_dir / f"crudo_{i:03d}_ir.jpg").exists()]
    if faltan:
        raise SystemExit(
            f"Faltan {len(faltan)} cuadros ({faltan[:12]}...). Generálos con:\n"
            f"  {_comando_descarga(args)}")

    print(f"Sandwich RGB globo | {n_cuadros} cuadros desde {t0:%Y-%m-%d %H:%M} UTC | "
          f"alpha {args.alpha} | salida {args.px}x{args.px} px | frames en {frames_dir}")
    inicio = time.time()
    hechos = 0
    for i, t in enumerate(fechas, 1):
        vis = frames_dir / f"crudo_{i:03d}_vis.jpg"
        ir = frames_dir / f"crudo_{i:03d}_ir.jpg"
        destino = frames_dir / f"cuadro_{i:03d}.png"
        # Reutilizar sólo si el PNG es más nuevo que los DOS crudos que lo componen.
        ref = max(vis.stat().st_mtime, ir.stat().st_mtime)
        if destino.exists() and destino.stat().st_mtime >= ref:
            pass                       # ya renderizado con estos parámetros
        else:
            render_globo(vis, ir, t, args, destino)
        hechos += 1
        print(f"  {hechos}/{n_cuadros} listos ({time.time() - inicio:.0f}s)", flush=True)

    print(f"{len(fechas)} cuadros en {frames_dir}")
    print(f"Armá el video con: .venv\\Scripts\\python.exe animar\\armar.py "
          f"--frames \"{frames_dir}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
