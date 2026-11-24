"""Renderiza cuadros de Meteosat-12 (MTG-I1): globo, Paraguay o crudo.

La descarga vive en ``descargar/meteosat.py``: deja ``crudo_NNN.png`` ya
pintados por EUMETView. Aca se dibuja el póster. En ``globo`` se reproyecta la
imagen lon/lat a un disco Orthographic; en ``paraguay`` sólo se enmarca el
recorte cuadrado del país, que ya viene en lon/lat; sin encuadre se dibuja el
crudo tal cual con la fecha.

El warping se hace a mano con numpy (mapeo inverso + interpolacion bilineal),
igual que en ``cuadros_geocolor.py``: el ``warp_array`` de cartopy pide
``pykdtree``/``scipy`` y no hace falta para una imagen ya equirectangular.

Uso (desde la raiz del proyecto):

    .venv\\Scripts\\python.exe cuadros\\cuadros_meteosat.py --desde 2026-11-23T12:00 --n 1 --px 1400 --encuadre globo
    .venv\\Scripts\\python.exe cuadros\\cuadros_meteosat.py --desde 2026-11-23T15:00 --n 1 --px 1400 --encuadre paraguay --capa truecolour
    .venv\\Scripts\\python.exe cuadros\\cuadros_meteosat.py --help
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from estilo import BG, FUENTE, TXT, TXT_DIM, WM_COLOR, tipografia  # noqa: E402
from meteosat import BBOX, CAPAS, PASO, normaliza_encuadre  # noqa: E402
from rutas import SALIDAS  # noqa: E402

PX = 1400
DPI = 140
N = 1
PASO_MIN = PASO
CENTRO = (0.0, 0.0)
CREDITO = "Graphic by @Gillo97"
ESCALA_TEXTO = 0.8

_FUENTES = {
    "geocolour": ("MTG-I1 · GEOCOLOUR", "COLOR REAL (DÍA) · IR Y LUCES (NOCHE)"),
    "truecolour": ("MTG-I1 · TRUE COLOUR", "COLOR REAL · SOLO LADO DIURNO"),
    "ir": ("MTG-I1 · IR 10.5 µm", "TEMPERATURA DE BRILLO · DÍA Y NOCHE"),
}
_FUENTE = "EUMETSAT · EUMETView · CC-BY 4.0"

_RE_FRAMES = re.compile(
    r"frames_meteosat_(?:plano|globo|paraguay)_(\d{4}-\d{2}-\d{2}T\d{4})_")


def ts_de_frames(nombre: str) -> datetime | None:
    match = _RE_FRAMES.search(nombre)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%dT%H%M")
    except ValueError:
        return None


def _carpeta_de_frames(salida: Path, vista: str, t0: datetime, n: int,
                       px: int) -> Path:
    exacta = salida / (f"frames_meteosat_{vista}_{t0:%Y-%m-%dT%H%M}"
                       f"_{n}f_{px}px")
    if next(exacta.glob("crudo_*.png"), None) is not None:
        return exacta
    patron = f"frames_meteosat_{vista}_*_{n}f_{px}px"
    con_crudos = [carpeta for carpeta in salida.glob(patron)
                  if next(carpeta.glob("crudo_*.png"), None) is not None]
    return max(con_crudos, key=lambda c: c.name) if con_crudos else exacta


def _warp_ortho(rgba: np.ndarray, bbox, centro, lado: int,
                banda: int = 256) -> np.ndarray:
    """Reproyecta RGBA lon/lat a Orthographic, por franjas de filas.

    Devuelve un RGBA del lado pedido. El alfa combina el de la imagen de origen
    (EUMETView recorta el disco) con un antialias geometrico en el limbo.
    """
    o, s, e, n = bbox
    lon0, lat0 = np.radians(centro[0]), np.radians(centro[1])
    alto_o, ancho_o = rgba.shape[:2]
    origen = rgba.astype(np.float32)

    y = np.linspace(1.0, -1.0, lado)
    x = np.linspace(-1.0, 1.0, lado)
    salida = np.zeros((lado, lado, 4), dtype=np.uint8)

    for i0 in range(0, lado, banda):
        i1 = min(i0 + banda, lado)
        filas = i1 - i0
        X = np.broadcast_to(x, (filas, lado))
        Y = np.broadcast_to(y[i0:i1, None], (filas, lado))
        rho = np.hypot(X, Y)
        dentro = rho <= 1.0

        rho_s = np.where(dentro & (rho > 1e-12), rho, 1.0)
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

        col = (lon_deg - o) / (e - o) * (ancho_o - 1)
        fila = (n - lat_deg) / (n - s) * (alto_o - 1)

        c0 = np.clip(np.floor(col), 0, ancho_o - 2).astype(np.intp)
        f0 = np.clip(np.floor(fila), 0, alto_o - 2).astype(np.intp)
        fc = np.clip(col - c0, 0.0, 1.0)[..., None]
        ff = np.clip(fila - f0, 0.0, 1.0)[..., None]
        a = origen[f0, c0]
        b = origen[f0, c0 + 1]
        cc = origen[f0 + 1, c0]
        d = origen[f0 + 1, c0 + 1]
        mezcla = (a * (1 - fc) + b * fc) * (1 - ff) + (cc * (1 - fc) + d * fc) * ff

        # Borde geometrico suave (~1.5 px) y recorte por el alfa de EUMETView.
        # El color se interpola premultiplicado: si no, el RGB blanco del borde
        # transparente del PNG deja una franja blanca en el limbo.
        alfa_geo = np.clip((1.0 - rho) * (lado / 2.0) / 1.5, 0.0, 1.0)
        alfa_src = mezcla[..., 3:4] / 255.0
        alfa = np.minimum(alfa_geo[..., None], alfa_src)
        color = (mezcla[..., :3] * alfa_src) / np.maximum(alfa, 1e-6)
        salida[i0:i1, :, :3] = np.clip(color, 0, 255).astype(np.uint8)
        salida[i0:i1, :, 3] = (alfa[..., 0] * 255.0).astype(np.uint8)

    return salida


def _sello(args, salida_alto: int) -> str:
    # `encuadre` ya dice globo/paraguay/plano: el flag viejo no entra, si no
    # `--globo` y `--encuadre globo` generarían dos firmas para el mismo dibujo.
    datos = {
        "px": args.px, "dpi": args.dpi,
        "encuadre": args.encuadre,
        "centro": list(args.centro), "capa": args.capa,
        "credito": args.credito, "sin_fecha": args.sin_fecha,
        "escala_texto": ESCALA_TEXTO, "fuente": tipografia(), "fondo": BG,
        "diseno": 2,
    }
    return hashlib.sha256(json.dumps(datos, sort_keys=True).encode()).hexdigest()[:16]


def etiquetar_plano(img: Image.Image, t: datetime, credito: str) -> Image.Image:
    """Fecha/hora abajo a la izquierda y credito a la derecha (modo plano)."""
    from PIL import ImageDraw, ImageFont
    from estilo import ruta_fuente

    def fuente(px: int):
        try:
            return ImageFont.truetype(ruta_fuente(False), px)
        except OSError:
            return ImageFont.load_default()

    img = img.convert("RGB")
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    ancho, alto = img.size
    texto = t.strftime("%Y-%m-%d %H:%M UTC")
    f = fuente(max(11, ancho // 34))
    margen = max(8, ancho // 60)
    for dx, dy in ((0, 1), (1, 0), (0, 0)):
        d.text((margen + dx, alto - margen - 18 + dy), texto, font=f,
               fill=(0, 0, 0, 190))
    d.text((margen, alto - margen - 18), texto, font=f, fill=(255, 255, 255, 235))
    if credito:
        f2 = fuente(max(10, ancho // 42))
        caja = d.textbbox((0, 0), credito, font=f2)
        x = ancho - margen - (caja[2] - caja[0])
        y = alto - margen - 16
        for dx, dy in ((0, 1), (1, 0), (0, 0)):
            d.text((x + dx, y + dy), credito, font=f2, fill=(0, 0, 0, 190))
        d.text((x, y), credito, font=f2, fill=(255, 255, 255, 220))
    return Image.alpha_composite(img.convert("RGBA"), capa).convert("RGB")


def render_globo(crudo: Path, t: datetime, args, destino: Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patheffects as patheffects
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    rgba = np.asarray(Image.open(crudo).convert("RGBA"))
    lon0, lat0 = args.centro
    lado = args.px / args.dpi
    fig = plt.figure(figsize=(lado, lado), dpi=args.dpi)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0.014, 0.014, 0.972, 0.972],
                      projection=ccrs.Orthographic(central_longitude=lon0,
                                                   central_latitude=lat0))
    ax.set_facecolor(BG)
    ax.spines["geo"].set_visible(False)
    disco = _warp_ortho(rgba, args.bbox, args.centro, args.px)
    del rgba
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

    titulo, descripcion = _FUENTES.get(args.capa, _FUENTES["geocolour"])
    plt.rcParams.update({"font.family": FUENTE})
    esc = ESCALA_TEXTO * (args.px / 720.0) ** 0.45
    halo = [patheffects.withStroke(linewidth=2.4 * esc, foreground=BG)]
    fig.text(0.026, 0.985, titulo, color=TXT, fontsize=18 * esc, ha="left",
             va="top", path_effects=halo, zorder=11)
    if not args.sin_fecha:
        fig.text(0.026, 0.948, t.strftime("%d %b %Y · %H:%M UTC").upper(),
                 color=TXT_DIM, fontsize=11.5 * esc, ha="left", va="top",
                 path_effects=halo, zorder=11)
    fig.text(0.974, 0.985, descripcion, color=TXT_DIM, fontsize=8.6 * esc,
             ha="right", va="top", path_effects=halo, zorder=11)
    fig.text(0.026, 0.012, _FUENTE, color=TXT_DIM, fontsize=10 * esc,
             ha="left", va="bottom")
    if args.credito:
        fig.text(0.974, 0.012, args.credito, color=TXT_DIM, fontsize=10 * esc,
                 ha="right", va="bottom")
        fig.text(0.5, 0.150, " ".join(args.credito.upper()), color=WM_COLOR,
                 fontsize=8.5 * esc, ha="center", va="bottom")

    parcial = destino.with_suffix(".png.parcial")
    fig.savefig(parcial, format="png", facecolor=BG)
    plt.close(fig)
    parcial.replace(destino)
    return destino


def render_paraguay(crudo: Path, t: datetime, args, destino: Path) -> Path:
    """Póster del recorte "Solo Paraguay".

    El WMS ya entrega el recorte en lon/lat, cuadrado en kilómetros: no hay
    reproyección, sólo el marco del póster. Desde 0° el país queda a 58° del
    subpunto satelital, así que el píxel viene estirado y el Rayleigh lava el
    color: es la vista real del MTG sobre Paraguay, no un defecto del render.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patheffects as patheffects

    rgba = np.asarray(Image.open(crudo).convert("RGBA"))
    lado = args.px / args.dpi
    fig = plt.figure(figsize=(lado, lado), dpi=args.dpi)
    fig.patch.set_facecolor(BG)
    # Cuadrado y centrado: deja la banda del título arriba y la de fuentes abajo.
    ancho_img = 0.84
    ax = fig.add_axes([0.5 - ancho_img / 2, 0.075, ancho_img, ancho_img])
    ax.set_facecolor(BG)
    ax.imshow(rgba, origin="upper", interpolation="bilinear")
    ax.set_axis_off()

    titulo, descripcion = _FUENTES.get(args.capa, _FUENTES["geocolour"])
    plt.rcParams.update({"font.family": FUENTE})
    esc = ESCALA_TEXTO * (args.px / 720.0) ** 0.45
    halo = [patheffects.withStroke(linewidth=2.4 * esc, foreground=BG)]
    fig.text(0.026, 0.985, titulo, color=TXT, fontsize=18 * esc, ha="left",
             va="top", path_effects=halo, zorder=11)
    if not args.sin_fecha:
        fig.text(0.026, 0.948, f"PARAGUAY · {t:%d %b %Y · %H:%M} UTC".upper(),
                 color=TXT_DIM, fontsize=11.5 * esc, ha="left", va="top",
                 path_effects=halo, zorder=11)
    fig.text(0.974, 0.985, descripcion, color=TXT_DIM, fontsize=8.6 * esc,
             ha="right", va="top", path_effects=halo, zorder=11)
    fig.text(0.026, 0.012, _FUENTE, color=TXT_DIM, fontsize=10 * esc,
             ha="left", va="bottom")
    if args.credito:
        fig.text(0.974, 0.012, args.credito, color=TXT_DIM, fontsize=10 * esc,
                 ha="right", va="bottom")

    parcial = destino.with_suffix(".png.parcial")
    fig.savefig(parcial, format="png", facecolor=BG)
    plt.close(fig)
    parcial.replace(destino)
    return destino


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Cuadros (PNG) de Meteosat-12 desde los crudos de EUMETView.")
    ap.add_argument("--desde", default="",
                    help="primer cuadro UTC (vacio = el que codifica la carpeta)")
    ap.add_argument("--n", type=int, default=N, help=f"cantidad de cuadros (por defecto {N})")
    ap.add_argument("--paso", type=int, default=PASO_MIN,
                    help=f"minutos entre cuadros (por defecto {PASO_MIN})")
    ap.add_argument("--px", type=int, default=PX,
                    help=f"lado del cuadro en pixeles (por defecto {PX})")
    ap.add_argument("--dpi", type=int, default=DPI, help="dpi del render")
    ap.add_argument("--globo", action="store_true",
                    help="reproyectar a Orthographic (aspecto planeta)")
    ap.add_argument("--encuadre", choices=("plano", "globo", "paraguay"),
                    default=None,
                    help="plano (crudo tal cual), globo (Orthographic) o paraguay "
                         "(recorte del país en el limbo)")
    ap.add_argument("--centro", nargs=2, type=float, metavar=("LON", "LAT"),
                    default=list(CENTRO),
                    help=f"centro del globo (por defecto {CENTRO[0]:g} {CENTRO[1]:g})")
    ap.add_argument("--capa", default="geocolour", choices=tuple(CAPAS),
                    help="producto pintado (define titulo y descripcion)")
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("O", "S", "E", "N"),
                    default=list(BBOX), help="caja lon/lat del crudo")
    ap.add_argument("--credito", default=CREDITO, help="credito de la marca de agua")
    ap.add_argument("--sin-fecha", action="store_true",
                    help="no estampar la fecha/hora en el cuadro")
    ap.add_argument("--out", help="carpeta de salida (por defecto, comun.rutas.SALIDAS)")
    ap.add_argument("--frames", help="carpeta de cuadros (default: frames_meteosat_*)")
    args = ap.parse_args(argv)

    if args.px < 200:
        raise SystemExit("--px tiene que ser >= 200.")
    o, s, e, n = args.bbox
    if not (o < e and s < n):
        raise SystemExit(f"caja invalida: {args.bbox}")

    # Sin flags se dibuja el crudo tal cual; `--globo` es el alias viejo de
    # `--encuadre globo`, para que los comandos ya documentados sigan andando.
    args.encuadre = normaliza_encuadre(args.encuadre, args.globo, defecto="plano")

    salida = Path(args.out) if args.out else SALIDAS
    vista = args.encuadre
    if args.frames:
        frames_dir = Path(args.frames)
    else:
        if not args.desde:
            raise SystemExit("Con --frames vacio hace falta --desde para ubicar la carpeta.")
        t0 = datetime.fromisoformat(args.desde)
        frames_dir = _carpeta_de_frames(salida, vista, t0, args.n, args.px)

    t0 = ts_de_frames(frames_dir.name) or (
        datetime.fromisoformat(args.desde) if args.desde else datetime.now())
    if not frames_dir.exists():
        raise SystemExit(
            f"No existe {frames_dir}. Descarga los cuadros con:\n"
            f"  .venv\\Scripts\\python.exe descargar\\meteosat.py "
            f"--desde {t0:%Y-%m-%dT%H:%M} --n {args.n} --px {args.px} "
            f"--capa {args.capa} --encuadre {args.encuadre}")

    sello = _sello(args, args.px)
    archivo_sello = frames_dir / ".sello_render"
    previo = (archivo_sello.read_text(encoding="utf-8").strip()
              if archivo_sello.exists() else None)
    if previo is not None and previo != sello:
        viejos = list(frames_dir.glob("cuadro_*.png"))
        for p in viejos:
            p.unlink()
        print(f"Cambiaron los parametros de render -> se descartan {len(viejos)} cuadros")
    archivo_sello.write_text(sello, encoding="utf-8")

    tiempos = [t0 + timedelta(minutes=args.paso * i) for i in range(args.n)]
    print(f"Meteosat-12 {vista} | {args.n} cuadro(s) desde {t0:%Y-%m-%d %H:%M} UTC | "
          f"salida {args.px}px | frames en {frames_dir}")
    inicio = time.time()
    hechos = 0
    for i, t in enumerate(tiempos, 1):
        crudo = frames_dir / f"crudo_{i:03d}.png"
        destino = frames_dir / f"cuadro_{i:03d}.png"
        if not crudo.exists():
            print(f"  aviso: falta {crudo.name}; se saltea", flush=True)
            continue
        if destino.exists() and destino.stat().st_mtime >= crudo.stat().st_mtime:
            pass
        elif args.encuadre == "paraguay":
            render_paraguay(crudo, t, args, destino)
        elif args.encuadre == "globo":
            render_globo(crudo, t, args, destino)
        else:
            img = Image.open(crudo).convert("RGBA")
            fondo = Image.new("RGBA", img.size, (0, 0, 0, 255))
            img = Image.alpha_composite(fondo, img)
            if not args.sin_fecha:
                img = etiquetar_plano(img, t, args.credito)
            parcial = destino.with_suffix(".png.parcial")
            img.convert("RGB").save(parcial, format="PNG")
            parcial.replace(destino)
        hechos += 1
        print(f"  {hechos}/{args.n} listos ({time.time() - inicio:.0f}s)", flush=True)

    print(f"{hechos} cuadro(s) en {frames_dir}")
    print(f"Arma el video con: .venv\\Scripts\\python.exe animar\\armar.py "
          f"--frames \"{frames_dir}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
