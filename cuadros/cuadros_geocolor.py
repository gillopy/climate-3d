"""Renderiza los cuadros de una animaci?n GeoColor (GOES-East) desde los crudos.

La descarga vive aparte, en `descargar/geocolor.py`; ac? s?lo se leen los
`crudo_NNN.jpg` que esa carpeta deja y se guardan como `cuadro_NNN.png` con el vestuario
del p?ster (costas, borde destacado y r?tulos). Si falta alg?n crudo, aborta nombrando el
comando de descarga.

El warping a Orthographic se hace a mano con numpy (mapeo inverso + interpolaci?n
bilineal) porque el `warp_array` de cartopy exige `pykdtree` o `scipy`, que este venv no
trae; con la imagen ya en la proyecci?n del eje, `imshow` recibe el atajo y no importa
`img_transform`.

Uso (desde la ra?z del proyecto):

    .venv\\Scripts\\python.exe cuadros\\cuadros_geocolor.py --desde 2026-10-04T00:00 --n 432 --px 2048 --globo
    .venv\\Scripts\\python.exe cuadros\\cuadros_geocolor.py --help
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from firms import (RADIO_FOCO, VENTANAS, color_foco, color_hex,  # noqa: E402
                   factor_gravedad, filtrar, leer_carpeta, ventana)
from rutas import SALIDAS  # noqa: E402
from paraguay import dentro  # noqa: E402
from snapshot_paraguay import dibujar_focos  # noqa: E402

# Sudam?rica + Caribe: Paraguay entra c?modo y el terminador barre el dominio entero.
BBOX = (-85.0, -40.0, -35.0, 15.0)      # oeste, sur, este, norte
# Para el globo hay que cubrir el hemisferio visible centrado en Paraguay: si la caja
# es m?s chica, el limbo queda recortado y el globo sale incompleto.
BBOX_GLOBO = (-160.0, -80.0, 15.0, 80.0)
GLOBO_LON, GLOBO_LAT = -58.0, -23.0     # mismo centro por defecto del resto del repo
# Dos l?neas, como el subt?tulo del p?ster: en una sola se sale del cuadro.
_SUBTITULOS = {
    "G19": "G19 GOES-EAST ? GEOCOLOR",
    "G16": "G16 GOES-EAST ? GEOCOLOR",
    "G18": "G18 GOES-WEST ? GEOCOLOR",
}
SUBTITULO = _SUBTITULOS["G19"] + "\nCOLOR REAL (D?A) ? IR Y LUCES (NOCHE)"
FUENTE = "SOURCE: NOAA/NESDIS/STAR GEOCOLOR ? NASA GIBS"
# Los r?tulos est?n calibrados a la animaci?n de 720 px del repo (19 pt de t?tulo), pero
# escalarlos linealmente hace que a 2048 px dominen el cuadro. Crecen sub-lineal (exponente
# 0.45) y con este factor: legibles en chico, discretos en grande.
ESCALA_TEXTO = 0.8
DESDE = "2026-10-15T20:00"              # UTC
N = 24
PASO_MIN = 10
PX = 480
CREDITO = "Graphic by @Gillo97"

FUENTES = [
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\arial.ttf",
]


def _fuente(px: int) -> ImageFont.ImageFont:
    """Primera tipograf?a TrueType disponible; si no hay, la bitmap de Pillow."""
    for ruta in FUENTES:
        if Path(ruta).exists():
            try:
                return ImageFont.truetype(ruta, px)
            except OSError:
                continue
    return ImageFont.load_default()


def etiquetar(img: Image.Image, t: datetime, credito: str) -> Image.Image:
    """Marca de agua discreta: fecha/hora UTC abajo a la izquierda, cr?dito a la derecha."""
    img = img.convert("RGB")
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    ancho, alto = img.size
    texto = t.strftime("%Y-%m-%d %H:%M UTC")
    f = _fuente(max(11, ancho // 34))
    margen = max(8, ancho // 60)
    # Sombra + texto, para que se lea tanto sobre nubes claras como sobre el negro del IR.
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


def _borde_plano(img: Image.Image, caja, ruta, color=(255, 255, 255),
                 ancho: int = 2) -> Image.Image:
    """Contorno del pa?s sobre una imagen plana lon/lat (modo sin `--globo`).

    Es el equivalente de `_borde_geojson` para el recorte regional: el contorno
    se proyecta con la misma caja que la imagen, sin cartopy.
    """
    if not ruta:
        return img
    import json

    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    o, s, e, n = caja
    ancho_px, alto_px = img.size
    base = img.convert("RGBA")
    capa = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)

    def anillos(objeto):
        if not isinstance(objeto, (list, tuple)):
            return
        if len(objeto) >= 2 and all(
            isinstance(p, (list, tuple)) and len(p) >= 2
            and isinstance(p[0], (int, float)) and isinstance(p[1], (int, float))
            for p in objeto
        ):
            yield objeto
            return
        for hijo in objeto:
            yield from anillos(hijo)

    for feature in datos.get("features", []):
        for anillo in anillos(feature.get("geometry", {}).get("coordinates", [])):
            puntos = [
                ((float(p[0]) - o) / (e - o) * ancho_px,
                 (n - float(p[1])) / (n - s) * alto_px)
                for p in anillo
            ]
            if len(puntos) < 2:
                continue
            d.line(puntos, fill=(0, 0, 0, 210), width=ancho + 2, joint="curve")
            d.line(puntos, fill=(*color, 235), width=ancho, joint="curve")
    return Image.alpha_composite(base, capa).convert("RGB")


_CACHE_FOCOS: dict[str, list] = {}


def _focos_de(args, t: datetime) -> list:
    """Focos de FIRMS del cuadro `t`, o [] si el toggle est? apagado.

    La ventana se filtra **por cuadro**: en una animaci?n con `3h`, los focos
    aparecen cuando el sat?lite pasa, no quedan fijos todo el d?a.
    """
    carpeta = getattr(args, "firms_entrada", None)
    if not getattr(args, "firms", False) or not carpeta:
        return []
    if carpeta not in _CACHE_FOCOS:
        _CACHE_FOCOS[carpeta] = leer_carpeta(carpeta)
    focos = filtrar(_CACHE_FOCOS[carpeta],
                    *ventana(t, getattr(args, "firms_ventana", "dia")))
    if getattr(args, "firms_alcance", "completo") == "paraguay":
        focos = [foco for foco in focos if dentro(foco.lon, foco.lat)]
    return focos


def _focos_globo(ax, focos, args) -> None:
    """Marca los focos sobre el globo con la proyecci?n del eje (cartopy)."""
    import cartopy.crs as ccrs

    lon0, lat0 = np.radians(args.centro[0]), np.radians(args.centro[1])
    lon = np.radians(np.array([foco.lon for foco in focos], dtype=float))
    lat = np.radians(np.array([foco.lat for foco in focos], dtype=float))
    # S?lo la cara visible: en orthographic los puntos del otro lado se espejan.
    cos_c = (np.sin(lat0) * np.sin(lat)
             + np.cos(lat0) * np.cos(lat) * np.cos(lon - lon0))
    visible = cos_c > 1e-6
    if not visible.any():
        return
    dentro_disco = [foco for foco, ok in zip(focos, visible) if ok]
    # El tamaño sigue la gravedad del incendio, no la cantidad de puntos.
    factores = np.array([factor_gravedad(foco) for foco in dentro_disco])
    diametro = max(3.0, args.px * RADIO_FOCO * 2) * 72.0 / args.dpi
    for tamano, color, alpha, orden in (
        (diametro * 1.75, "#000000", 0.28, 7.6),
        (diametro, None, 0.90, 8.0),
        (diametro * 0.42, "#fff8dc", 0.92, 8.1),
    ):
        ax.scatter([foco.lon for foco in dentro_disco],
                   [foco.lat for foco in dentro_disco],
                   s=(tamano * factores) ** 2,
                   c=(color if color
                      else [color_hex(f.confianza) for f in dentro_disco]),
                   alpha=alpha, linewidths=0,
                   transform=ccrs.PlateCarree(), zorder=orden)


_RE_FRAMES = re.compile(
    r"frames_geocolor_(?:plano|globo)_[A-Za-z0-9]+_(\d{4}-\d{2}-\d{2}T\d{4})_")


def ts_de_frames(nombre: str) -> datetime | None:
    """Instante que codifica el nombre de la carpeta de cuadros."""
    match = _RE_FRAMES.search(nombre)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%dT%H%M")
    except ValueError:
        return None


def _carpeta_de_frames(salida: Path, vista: str, sat: str, t0: datetime,
                       args) -> Path:
    """La carpeta que dej? el descargador para este cuadro.

    Con un snapshot el descargador puede haber retrocedido un slot (GIBS devuelve
    negro para un gr?nulo cuya miniatura exist?a), as? que no alcanza con recalcular
    el nombre: se busca la del slot pedido y, si no tiene cuadros, la m?s nueva.
    """
    exacta = salida / (f"frames_geocolor_{vista}_{sat}_{t0:%Y-%m-%dT%H%M}"
                       f"_{args.n}f_{args.px}px")
    if next(exacta.glob("crudo_*.jpg"), None) is not None:
        return exacta
    patron = f"frames_geocolor_{vista}_{sat}_*_{args.n}f_{args.px}px"
    con_cuadros = [carpeta for carpeta in salida.glob(patron)
                   if next(carpeta.glob("crudo_*.jpg"), None) is not None]
    return max(con_cuadros, key=lambda carpeta: carpeta.name) if con_cuadros else exacta


def _estilo_poster():
    """Constantes del p?ster del repo, compartidas en `comun/estilo.py`."""
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


def _warp_ortho(rgb, bbox, centro, lado, banda=256):
    """Reproyecta una imagen lon/lat a Orthographic (mapeo inverso, con numpy).

    Para cada p?xel del disco de destino se calcula su (lon, lat) y se muestrea la
    imagen de origen con interpolaci?n bilineal. Fuera del disco, o donde la caja de
    origen no tiene dato, el alfa queda en 0 y se ve el fondo.

    ?Por qu? a mano y no con `imshow(transform=PlateCarree)`? Porque el warping de
    cartopy importa `warp_array`, que exige `pykdtree` o `scipy` ? y este venv no los
    tiene. Haciendo el warp nosotros, `imshow` recibe la imagen ya en la proyecci?n del
    eje y cartopy toma el atajo (no importa `img_transform`).

    El c?lculo va **por franjas de filas**: como es por p?xel, el resultado es id?ntico
    al de una sola pasada, pero el pico de memoria deja de crecer con el cuadrado de
    `lado`. A 2712 px la versi?n de una sola pasada pide ~1.5 GB de arrays flotantes y
    revienta con `MemoryError` en m?quinas de 8 GB; por franjas el pico es ~250 MB.
    """
    o, s, e, n = bbox
    lon0, lat0 = np.radians(centro[0]), np.radians(centro[1])
    alto_o, ancho_o = rgb.shape[:2]

    # Disco normalizado: x, y en [-1, 1], radio 1 = 90? de distancia al centro.
    y = np.linspace(1.0, -1.0, lado)        # la fila 0 es el norte
    x = np.linspace(-1.0, 1.0, lado)
    salida = np.zeros((lado, lado, 4), dtype=np.uint8)

    for i0 in range(0, lado, banda):
        i1 = min(i0 + banda, lado)
        filas = i1 - i0
        # Mismas grillas que `np.meshgrid(x, y)`, pero de la franja sola y sin copia.
        X = np.broadcast_to(x, (filas, lado))
        Y = np.broadcast_to(y[i0:i1, None], (filas, lado))
        rho = np.hypot(X, Y)
        dentro = rho <= 1.0

        rho_s = np.where(dentro & (rho > 1e-12), rho, 1.0)   # evita 0/0 en el centro
        c = np.arcsin(np.clip(rho_s, 0.0, 1.0))
        sin_c, cos_c = np.sin(c), np.cos(c)

        lat = np.arcsin(np.clip(cos_c * np.sin(lat0)
                                + (Y * sin_c * np.cos(lat0)) / rho_s, -1.0, 1.0))
        lon = lon0 + np.arctan2(X * sin_c,
                                rho_s * np.cos(lat0) * cos_c - Y * np.sin(lat0) * sin_c)
        es_centro = dentro & (rho <= 1e-12)
        lat = np.where(es_centro, lat0, lat)
        lon = np.where(es_centro, lon0, lon)

        lon_deg = (np.degrees(lon) + 180.0) % 360.0 - 180.0
        # GOES-West ve un hemisferio que cruza el antimeridiano: la caja puede
        # empezar en -227, as? que la longitud se lleva al marco de la caja.
        if o < -180.0:
            lon_deg = np.where(lon_deg > e, lon_deg - 360.0, lon_deg)

        lat_deg = np.degrees(lat)

        # Posici?n de muestreo en la imagen de origen (plate carr?e).
        col = (lon_deg - o) / (e - o) * (ancho_o - 1)
        fila = (n - lat_deg) / (n - s) * (alto_o - 1)

        c0 = np.clip(np.floor(col), 0, ancho_o - 2).astype(np.intp)
        f0 = np.clip(np.floor(fila), 0, alto_o - 2).astype(np.intp)
        fc = np.clip(col - c0, 0.0, 1.0)[..., None]
        ff = np.clip(fila - f0, 0.0, 1.0)[..., None]
        a = rgb[f0, c0].astype(np.float32)
        b = rgb[f0, c0 + 1].astype(np.float32)
        cc = rgb[f0 + 1, c0].astype(np.float32)
        d = rgb[f0 + 1, c0 + 1].astype(np.float32)
        mezcla = (a * (1 - fc) + b * fc) * (1 - ff) + (cc * (1 - fc) + d * fc) * ff

        # Alfa geom?trico con antialias (~1.5 px): el c?rculo del limbo sale
        # suave. La m?scara por grilla de origen dejaba el borde en escalera
        # porque las celdas se estiran much?simo en el limbo.
        alfa = np.clip((1.0 - rho) * (lado / 2.0) / 1.5, 0.0, 1.0)
        salida[i0:i1, :, :3] = np.clip(mezcla, 0, 255).astype(np.uint8)
        salida[i0:i1, :, 3] = (alfa * 255.0).astype(np.uint8)

    return salida


def render_globo(crudo: Path, t: datetime, args, destino: Path,
                 focos=()) -> Path:
    """Reproyecta el snapshot (lat/lon) a Orthographic, con el vestuario del p?ster.

    El snapshot llega en EPSG:4326 (plano lon/lat) y `_warp_ortho` lo lleva al disco
    Orthographic; ac? s?lo se dibuja, con las costas, el borde y el r?tulo del p?ster.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patheffects as patheffects
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    BG, TXT, TXT_DIM, WM_COLOR, MONTHS_EN = _estilo_poster()
    BG = "#000000"                     # fondo negro puro (s?lo GeoColor)
    lon0, lat0 = args.centro
    rgb = np.asarray(Image.open(crudo).convert("RGB"))

    lado = args.px / args.dpi
    fig = plt.figure(figsize=(lado, lado), dpi=args.dpi)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0.014, 0.014, 0.972, 0.972],
                      projection=ccrs.Orthographic(central_longitude=lon0,
                                                   central_latitude=lat0))
    ax.set_facecolor(BG)
    ax.spines["geo"].set_visible(False)
    # El warp va antes y en coordenadas de la proyecci?n del eje: as? cartopy no
    # reproyecta nada y evita el import de `img_transform` (que pide scipy/pykdtree).
    disco = _warp_ortho(rgb, args.bbox, args.centro, args.px)
    # La imagen de origen (80 MB a 5424 px) ya no se usa: se suelta antes de `imshow`,
    # que copia el disco a float32 y es el pico de memoria del render.
    del rgb
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
    if focos:
        _focos_globo(ax, focos, args)

    # Referencia: la animaci?n de 720 px del repo, pero sub-lineal (ver ESCALA_TEXTO).
    esc = ESCALA_TEXTO * (args.px / 720.0) ** 0.45
    # Halo bajo el texto (no caja): se lee sobre el planeta sin taparlo.
    halo = [patheffects.withStroke(linewidth=3.2 * esc, foreground=BG)]
    fig.text(0.026, 0.985, f"{MONTHS_EN[t.month - 1]} {t.year}", color=TXT,
             fontsize=19 * esc, fontweight="bold", ha="left", va="top",
             path_effects=halo, zorder=11)
    fig.text(0.026, 0.944, t.strftime("%d %b %Y ? %H:%M UTC").upper(), color=TXT,
             fontsize=16 * esc, fontweight="bold", ha="left", va="top",
             path_effects=halo, zorder=11)
    fig.text(0.026, 0.898, SUBTITULO, color=TXT_DIM, fontsize=13.5 * esc,
             fontweight="bold", ha="left", va="top", linespacing=1.12,
             path_effects=halo, zorder=11)
    fig.text(0.983, 0.983, args.credito, color=TXT_DIM, fontsize=12 * esc,
             ha="right", va="top", path_effects=halo, zorder=11)
    fig.text(0.026, 0.012, FUENTE, color=TXT_DIM, fontsize=7.4 * esc, ha="left",
             va="bottom")
    fig.text(0.980, 0.012, f"DATA: {t:%Y-%m-%dT%H:%M} UTC ? ZONA SA", color=TXT_DIM,
             fontsize=7.4 * esc, ha="right", va="bottom")
    if args.credito:
        fig.text(0.5, 0.150, " ".join(args.credito.upper()), color=WM_COLOR,
                 fontsize=8.5 * esc, ha="center", va="bottom")

    # Guardado at?mico: si el proceso se corta a mitad, no queda un PNG corrupto que
    # despu?s se reutilice como si estuviera bueno.
    parcial = destino.with_suffix(".png.parcial")
    fig.savefig(parcial, format="png", facecolor=BG)
    plt.close(fig)
    parcial.replace(destino)
    return destino


def _sello_render(args, salida_alto: int) -> str:
    """Huella de los par?metros que cambian el aspecto del cuadro.

    Los PNG se reutilizan por fecha de mtime, as? que si cambi?s el texto, el borde o la
    escala, los viejos quedar?an con el aspecto anterior sin que nadie lo note.
    """
    import hashlib
    import json
    datos = {
        "px": args.px, "dpi": args.dpi, "globo": args.globo, "alto": salida_alto,
        "centro": list(args.centro), "bbox": list(args.bbox), "credito": args.credito,
        "sin_fecha": args.sin_fecha, "geojson": args.geojson or "",
        "borde_color": args.borde_color, "borde_ancho": args.borde_ancho,
        "escala_texto": ESCALA_TEXTO, "subtitulo": SUBTITULO,
        "fondo": "#000000",
        "alfa": "circulo-suave",
    }
    return hashlib.sha256(json.dumps(datos, sort_keys=True).encode()).hexdigest()[:16]


def _comando_descarga(t0: datetime, args) -> str:
    """Comando de `descargar/geocolor.py` que genera los crudos de esta corrida."""
    cmd = (f".venv\\Scripts\\python.exe descargar\\geocolor.py "
           f"--desde {t0:%Y-%m-%dT%H:%M} --n {args.n} --px {args.px}"
           f" --sat {args.sat.upper()}")
    return cmd + (" --globo" if args.globo else "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Cuadros (PNG) de una animaci?n GeoColor (GOES-East) desde los crudos.")
    ap.add_argument("--desde", default=DESDE,
                    help=f"primer cuadro, UTC (por defecto {DESDE})")
    ap.add_argument("--n", type=int, default=N, help=f"cantidad de cuadros (por defecto {N})")
    ap.add_argument("--paso", type=int, default=PASO_MIN,
                    help=f"minutos entre cuadros (por defecto {PASO_MIN})")
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("O", "S", "E", "N"),
                    help="caja lon/lat de origen (por defecto, Sudam?rica; con --globo, "
                         "la que cubre el hemisferio visible)")
    ap.add_argument("--sat", default="G19",
                    help="sat?lite del r?tulo: G19/G16 = GOES-East, G18 = GOES-West")
    ap.add_argument("--globo", action="store_true",
                    help="reproyectar a Orthographic centrado en --centro (aspecto 'planeta')")
    ap.add_argument("--centro", nargs=2, type=float, metavar=("LON", "LAT"),
                    default=[GLOBO_LON, GLOBO_LAT],
                    help=f"centro del globo (por defecto {GLOBO_LON} {GLOBO_LAT})")
    ap.add_argument("--dpi", type=int, default=140, help="dpi del render del globo")
    ap.add_argument("--src-px", type=int,
                    help="ancho de la imagen de origen; por defecto, seg?n el modo")
    ap.add_argument("--geojson", default=str(RAIZ / "datos" / "paraguay_gadm.json"),
                    help="borde destacado en el globo (GeoJSON); vac?o = sin borde")
    ap.add_argument("--borde-color", default="#000000", help="color del borde destacado")
    ap.add_argument("--borde-ancho", type=float, default=0.8,
                    help="grosor del borde destacado")
    ap.add_argument("--px", type=int, default=PX,
                    help=f"ancho de cada cuadro en p?xeles (por defecto {PX})")
    ap.add_argument("--alto", type=int, help="alto en p?xeles (por defecto, seg?n la caja)")
    ap.add_argument("--credito", default=CREDITO, help="cr?dito de la marca de agua")
    ap.add_argument("--sin-fecha", action="store_true",
                    help="no estampar la fecha/hora en el cuadro")
    ap.add_argument("--firms", action="store_true",
                    help="superpone los focos de calor de NASA FIRMS")
    ap.add_argument("--firms-ventana", default=VENTANAS[0], choices=VENTANAS,
                    help="ventana de focos alrededor de cada cuadro")
    ap.add_argument("--firms-entrada",
                    help="carpeta con los CSV de focos (los deja descargar/firms.py)")
    ap.add_argument("--firms-alcance", default="completo",
                    choices=("completo", "paraguay"),
                    help="completo = todos los focos del área; paraguay = sólo los "
                         "que caen dentro del país")
    ap.add_argument("--out", help="carpeta de salida (por defecto, comun.rutas.SALIDAS)")
    args = ap.parse_args(argv)

    global SUBTITULO
    sat = args.sat.upper()
    SUBTITULO = (f"{_SUBTITULOS.get(sat, _SUBTITULOS['G19'])}\n"
                 "COLOR REAL (D?A) ? IR Y LUCES (NOCHE)")

    if args.bbox is None:
        # Mismo criterio que la descarga: el globo se centra en el sat?lite.
        args.bbox = ([args.centro[0] - 90.0, -80.0, args.centro[0] + 90.0, 80.0]
                     if args.globo else list(BBOX))
    o, s, e, n = args.bbox
    if not (o < e and s < n):
        raise SystemExit(f"caja inv?lida: {args.bbox}")

    # El origen se pide con la proporci?n de la caja. En modo globo se pide m?s grande que
    # la salida: el warping a Orthographic remuestrea y conviene tener de d?nde tirar.
    src_px = args.src_px or (max(1200, args.px * 2) if args.globo else args.px)
    src_alto = args.alto or round(src_px * (n - s) / (e - o))
    salida_alto = args.px if args.globo else src_alto

    t0 = datetime.fromisoformat(args.desde)
    salida = Path(args.out) if args.out else SALIDAS
    vista = "globo" if args.globo else "plano"
    frames_dir = _carpeta_de_frames(salida, vista, sat, t0, args)
    # El descargador pudo retroceder un slot (GIBS sin dato): manda su nombre.
    ajustado = ts_de_frames(frames_dir.name)
    if ajustado is not None:
        t0 = ajustado

    if not frames_dir.exists():
        raise SystemExit(f"No existe {frames_dir}. Descarg? los cuadros con:\n"
                         f"  {_comando_descarga(t0, args)}")

    # Si cambi? algo del aspecto, los cuadros ya renderizados quedaron viejos: se borran,
    # as? se rehacen en vez de reutilizarse con el r?tulo anterior.
    sello = _sello_render(args, salida_alto)
    archivo_sello = frames_dir / ".sello_render"
    previo = (archivo_sello.read_text(encoding="utf-8").strip()
              if archivo_sello.exists() else None)
    if previo is not None and previo != sello:
        viejos = list(frames_dir.glob("cuadro_*.png"))
        for p in viejos:
            p.unlink()
        print(f"Cambiaron los par?metros de render -> se descartan {len(viejos)} cuadros")
    archivo_sello.write_text(sello, encoding="utf-8")

    tiempos = [t0 + timedelta(minutes=args.paso * i) for i in range(args.n)]

    # S?lo se leen los crudos: si falta alguno no se puede renderizar la secuencia, y el
    # que corresponda se nombra con el comando exacto que los genera.
    faltan = [i for i in range(1, args.n + 1)
              if not (frames_dir / f"crudo_{i:03d}.jpg").exists()]
    if len(faltan) == args.n:
        raise SystemExit(
            f"No hay ning?n crudo en {frames_dir}. Gener?los con:\n"
            f"  {_comando_descarga(t0, args)}\n"
            "Si el slot elegido todav?a no est? publicado (GIBS publica con retraso), "
            "marc? ??ltimo cuadro disponible?.")
    if faltan:
        # GIBS tiene huecos de 10-20 min: se saltean esos cuadros en vez de tirar
        # abajo la animaci?n entera.
        print(f"  aviso: {len(faltan)} cuadro(s) sin dato de GIBS "
              f"({faltan[:12]}...); se saltean", flush=True)

    print(f"GeoColor {vista} | {args.n} cuadros desde {t0:%Y-%m-%d %H:%M} UTC | "
          f"salida {args.px}x{salida_alto} px | frames en {frames_dir}")
    inicio = time.time()
    hechos = 0
    for i, t in enumerate(tiempos, 1):
        crudo = frames_dir / f"crudo_{i:03d}.jpg"
        destino = frames_dir / f"cuadro_{i:03d}.png"
        if not crudo.exists():
            continue                   # hueco de GIBS: la serie sigue sin ese cuadro
        if destino.exists() and destino.stat().st_mtime >= crudo.stat().st_mtime:
            pass                       # ya renderizado con estos par?metros
        elif args.globo:
            render_globo(crudo, t, args, destino, _focos_de(args, t))
        else:
            img = Image.open(crudo)
            img = img if args.sin_fecha else etiquetar(img, t, args.credito)
            img = _borde_plano(img, args.bbox, args.geojson)
            focos = _focos_de(args, t)
            if focos:
                img = dibujar_focos(img, tuple(args.bbox), focos,
                                    img.width, img.height)
            parcial = destino.with_suffix(".png.parcial")
            img.convert("RGB").save(parcial, format="PNG")
            parcial.replace(destino)
        hechos += 1
        print(f"  {hechos}/{args.n} listos ({time.time() - inicio:.0f}s)", flush=True)

    print(f"{len(tiempos)} cuadros en {frames_dir}")
    print(f"Arm? el video con: .venv\\Scripts\\python.exe animar\\armar.py "
          f"--frames \"{frames_dir}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
