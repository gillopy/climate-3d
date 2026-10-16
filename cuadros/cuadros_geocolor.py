"""Renderiza los cuadros de una animación GeoColor (GOES-East) desde los crudos.

La descarga vive aparte, en `descargar/geocolor.py`; acá sólo se leen los
`crudo_NNN.jpg` que esa carpeta deja y se guardan como `cuadro_NNN.png` con el vestuario
del póster (costas, borde destacado y rótulos). Si falta algún crudo, aborta nombrando el
comando de descarga.

El warping a Orthographic se hace a mano con numpy (mapeo inverso + interpolación
bilineal) porque el `warp_array` de cartopy exige `pykdtree` o `scipy`, que este venv no
trae; con la imagen ya en la proyección del eje, `imshow` recibe el atajo y no importa
`img_transform`.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe cuadros\\cuadros_geocolor.py --desde 2026-10-04T00:00 --n 432 --px 2048 --globo
    .venv\\Scripts\\python.exe cuadros\\cuadros_geocolor.py --help
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from rutas import SALIDAS  # noqa: E402

# Sudamérica + Caribe: Paraguay entra cómodo y el terminador barre el dominio entero.
BBOX = (-85.0, -40.0, -35.0, 15.0)      # oeste, sur, este, norte
# Para el globo hay que cubrir el hemisferio visible centrado en Paraguay: si la caja
# es más chica, el limbo queda recortado y el globo sale incompleto.
BBOX_GLOBO = (-160.0, -80.0, 15.0, 80.0)
GLOBO_LON, GLOBO_LAT = -58.0, -23.0     # mismo centro por defecto del resto del repo
# Dos líneas, como el subtítulo del póster: en una sola se sale del cuadro.
SUBTITULO = "G19 GOES-EAST · GEOCOLOR\nCOLOR REAL (DÍA) · IR Y LUCES (NOCHE)"
FUENTE = "SOURCE: NOAA/NESDIS/STAR GEOCOLOR · NASA GIBS"
# Los rótulos están calibrados a la animación de 720 px del repo (19 pt de título), pero
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
    """Primera tipografía TrueType disponible; si no hay, la bitmap de Pillow."""
    for ruta in FUENTES:
        if Path(ruta).exists():
            try:
                return ImageFont.truetype(ruta, px)
            except OSError:
                continue
    return ImageFont.load_default()


def etiquetar(img: Image.Image, t: datetime, credito: str) -> Image.Image:
    """Marca de agua discreta: fecha/hora UTC abajo a la izquierda, crédito a la derecha."""
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


def _warp_ortho(rgb, bbox, centro, lado):
    """Reproyecta una imagen lon/lat a Orthographic (mapeo inverso, con numpy).

    Para cada píxel del disco de destino se calcula su (lon, lat) y se muestrea la
    imagen de origen con interpolación bilineal. Fuera del disco, o donde la caja de
    origen no tiene dato, el alfa queda en 0 y se ve el fondo.

    ¿Por qué a mano y no con `imshow(transform=PlateCarree)`? Porque el warping de
    cartopy importa `warp_array`, que exige `pykdtree` o `scipy` — y este venv no los
    tiene. Haciendo el warp nosotros, `imshow` recibe la imagen ya en la proyección del
    eje y cartopy toma el atajo (no importa `img_transform`).
    """
    o, s, e, n = bbox
    lon0, lat0 = np.radians(centro[0]), np.radians(centro[1])
    alto_o, ancho_o = rgb.shape[:2]

    # Disco normalizado: x, y en [-1, 1], radio 1 = 90° de distancia al centro.
    y = np.linspace(1.0, -1.0, lado)        # la fila 0 es el norte
    x = np.linspace(-1.0, 1.0, lado)
    X, Y = np.meshgrid(x, y)
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
    lat_deg = np.degrees(lat)

    # Posición de muestreo en la imagen de origen (plate carrée).
    col = (lon_deg - o) / (e - o) * (ancho_o - 1)
    fila = (n - lat_deg) / (n - s) * (alto_o - 1)
    valido = (dentro & (col >= 0) & (col <= ancho_o - 1)
              & (fila >= 0) & (fila <= alto_o - 1))

    c0 = np.clip(np.floor(col), 0, ancho_o - 2).astype(np.intp)
    f0 = np.clip(np.floor(fila), 0, alto_o - 2).astype(np.intp)
    fc = np.clip(col - c0, 0.0, 1.0)[..., None]
    ff = np.clip(fila - f0, 0.0, 1.0)[..., None]
    a = rgb[f0, c0].astype(np.float32)
    b = rgb[f0, c0 + 1].astype(np.float32)
    cc = rgb[f0 + 1, c0].astype(np.float32)
    d = rgb[f0 + 1, c0 + 1].astype(np.float32)
    mezcla = (a * (1 - fc) + b * fc) * (1 - ff) + (cc * (1 - fc) + d * fc) * ff

    alfa = np.where(valido, 255, 0).astype(np.uint8)[..., None]
    return np.concatenate([np.clip(mezcla, 0, 255).astype(np.uint8), alfa], axis=2)


def render_globo(crudo: Path, t: datetime, args, destino: Path) -> Path:
    """Reproyecta el snapshot (lat/lon) a Orthographic, con el vestuario del póster.

    El snapshot llega en EPSG:4326 (plano lon/lat) y `_warp_ortho` lo lleva al disco
    Orthographic; acá sólo se dibuja, con las costas, el borde y el rótulo del póster.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    BG, TXT, TXT_DIM, WM_COLOR, MONTHS_EN = _estilo_poster()
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
    # El warp va antes y en coordenadas de la proyección del eje: así cartopy no
    # reproyecta nada y evita el import de `img_transform` (que pide scipy/pykdtree).
    disco = _warp_ortho(rgb, args.bbox, args.centro, args.px)
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
    fig.text(0.026, 0.944, t.strftime("%d %b %Y · %H:%M UTC").upper(), color=TXT,
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


def _sello_render(args, salida_alto: int) -> str:
    """Huella de los parámetros que cambian el aspecto del cuadro.

    Los PNG se reutilizan por fecha de mtime, así que si cambiás el texto, el borde o la
    escala, los viejos quedarían con el aspecto anterior sin que nadie lo note.
    """
    import hashlib
    import json
    datos = {
        "px": args.px, "dpi": args.dpi, "globo": args.globo, "alto": salida_alto,
        "centro": list(args.centro), "bbox": list(args.bbox), "credito": args.credito,
        "sin_fecha": args.sin_fecha, "geojson": args.geojson or "",
        "borde_color": args.borde_color, "borde_ancho": args.borde_ancho,
        "escala_texto": ESCALA_TEXTO, "subtitulo": SUBTITULO,
    }
    return hashlib.sha256(json.dumps(datos, sort_keys=True).encode()).hexdigest()[:16]


def _comando_descarga(t0: datetime, args) -> str:
    """Comando de `descargar/geocolor.py` que genera los crudos de esta corrida."""
    cmd = (f".venv\\Scripts\\python.exe descargar\\geocolor.py "
           f"--desde {t0:%Y-%m-%dT%H:%M} --n {args.n} --px {args.px}")
    return cmd + (" --globo" if args.globo else "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Cuadros (PNG) de una animación GeoColor (GOES-East) desde los crudos.")
    ap.add_argument("--desde", default=DESDE,
                    help=f"primer cuadro, UTC (por defecto {DESDE})")
    ap.add_argument("--n", type=int, default=N, help=f"cantidad de cuadros (por defecto {N})")
    ap.add_argument("--paso", type=int, default=PASO_MIN,
                    help=f"minutos entre cuadros (por defecto {PASO_MIN})")
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("O", "S", "E", "N"),
                    help="caja lon/lat de origen (por defecto, Sudamérica; con --globo, "
                         "la que cubre el hemisferio visible)")
    ap.add_argument("--globo", action="store_true",
                    help="reproyectar a Orthographic centrado en --centro (aspecto 'planeta')")
    ap.add_argument("--centro", nargs=2, type=float, metavar=("LON", "LAT"),
                    default=[GLOBO_LON, GLOBO_LAT],
                    help=f"centro del globo (por defecto {GLOBO_LON} {GLOBO_LAT})")
    ap.add_argument("--dpi", type=int, default=140, help="dpi del render del globo")
    ap.add_argument("--src-px", type=int,
                    help="ancho de la imagen de origen; por defecto, según el modo")
    ap.add_argument("--geojson", default=str(RAIZ / "datos" / "paraguay_gadm.json"),
                    help="borde destacado en el globo (GeoJSON); vacío = sin borde")
    ap.add_argument("--borde-color", default="#000000", help="color del borde destacado")
    ap.add_argument("--borde-ancho", type=float, default=0.8,
                    help="grosor del borde destacado")
    ap.add_argument("--px", type=int, default=PX,
                    help=f"ancho de cada cuadro en píxeles (por defecto {PX})")
    ap.add_argument("--alto", type=int, help="alto en píxeles (por defecto, según la caja)")
    ap.add_argument("--credito", default=CREDITO, help="crédito de la marca de agua")
    ap.add_argument("--sin-fecha", action="store_true",
                    help="no estampar la fecha/hora en el cuadro")
    ap.add_argument("--out", help="carpeta de salida (por defecto, comun.rutas.SALIDAS)")
    args = ap.parse_args(argv)

    if args.bbox is None:
        args.bbox = list(BBOX_GLOBO if args.globo else BBOX)
    o, s, e, n = args.bbox
    if not (o < e and s < n):
        raise SystemExit(f"caja inválida: {args.bbox}")

    # El origen se pide con la proporción de la caja. En modo globo se pide más grande que
    # la salida: el warping a Orthographic remuestrea y conviene tener de dónde tirar.
    src_px = args.src_px or (max(1200, args.px * 2) if args.globo else args.px)
    src_alto = args.alto or round(src_px * (n - s) / (e - o))
    salida_alto = args.px if args.globo else src_alto

    t0 = datetime.fromisoformat(args.desde)
    salida = Path(args.out) if args.out else SALIDAS
    vista = "globo" if args.globo else "plano"
    etiqueta = f"geocolor_{vista}_{t0:%Y-%m-%dT%H%M}_{args.n}f_{args.px}px"
    frames_dir = salida / f"frames_{etiqueta}"

    if not frames_dir.exists():
        raise SystemExit(f"No existe {frames_dir}. Descargá los cuadros con:\n"
                         f"  {_comando_descarga(t0, args)}")

    # Si cambió algo del aspecto, los cuadros ya renderizados quedaron viejos: se borran,
    # así se rehacen en vez de reutilizarse con el rótulo anterior.
    sello = _sello_render(args, salida_alto)
    archivo_sello = frames_dir / ".sello_render"
    previo = (archivo_sello.read_text(encoding="utf-8").strip()
              if archivo_sello.exists() else None)
    if previo is not None and previo != sello:
        viejos = list(frames_dir.glob("cuadro_*.png"))
        for p in viejos:
            p.unlink()
        print(f"Cambiaron los parámetros de render -> se descartan {len(viejos)} cuadros")
    archivo_sello.write_text(sello, encoding="utf-8")

    tiempos = [t0 + timedelta(minutes=args.paso * i) for i in range(args.n)]

    # Sólo se leen los crudos: si falta alguno no se puede renderizar la secuencia, y el
    # que corresponda se nombra con el comando exacto que los genera.
    faltan = [i for i in range(1, args.n + 1)
              if not (frames_dir / f"crudo_{i:03d}.jpg").exists()]
    if faltan:
        raise SystemExit(
            f"Faltan {len(faltan)} crudos ({faltan[:12]}...). Generálos con:\n"
            f"  {_comando_descarga(t0, args)}")

    print(f"GeoColor {vista} | {args.n} cuadros desde {t0:%Y-%m-%d %H:%M} UTC | "
          f"salida {args.px}x{salida_alto} px | frames en {frames_dir}")
    inicio = time.time()
    hechos = 0
    for i, t in enumerate(tiempos, 1):
        crudo = frames_dir / f"crudo_{i:03d}.jpg"
        destino = frames_dir / f"cuadro_{i:03d}.png"
        if destino.exists() and destino.stat().st_mtime >= crudo.stat().st_mtime:
            pass                       # ya renderizado con estos parámetros
        elif args.globo:
            render_globo(crudo, t, args, destino)
        else:
            img = Image.open(crudo)
            img = img if args.sin_fecha else etiquetar(img, t, args.credito)
            parcial = destino.with_suffix(".png.parcial")
            img.convert("RGB").save(parcial)
            parcial.replace(destino)
        hechos += 1
        print(f"  {hechos}/{args.n} listos ({time.time() - inicio:.0f}s)", flush=True)

    print(f"{len(tiempos)} cuadros en {frames_dir}")
    print(f"Armá el video con: .venv\\Scripts\\python.exe animar\\armar.py "
          f"--frames \"{frames_dir}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
