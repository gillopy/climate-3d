"""Prototipo de póster *realista* (estilo NASA Earth Observatory) desde un crudo MUR.

Este archivo es NUEVO y no toca el pipeline existente: sólo lee un `crudo_NNN.jpg`
de MUR SST (GIBS) y arma un póster cuadrado con:

  * globo Orthographic sobre fondo blanco,
  * continentes en escala de grises con relieve (Blue Marble + Natural Earth),
  * océano coloreado con una rampa divergente azul-blanco-rojo (por defecto),
  * retículo tenue y costas finas,
  * barra de color horizontal al pie con título y tres marcas.

La base de relieve y la leyenda de la rampa de GIBS se bajan una sola vez y quedan
cacheadas en `SALIDAS/_poster_realista/`. El crudo de MUR ya existe: el prototipo
usa por defecto el primer cuadro de la serie semanal 2025-01-01.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe prototipos\\poster_mur_realista.py
    .venv\\Scripts\\python.exe prototipos\\poster_mur_realista.py --px 2711 --centro -125 0
    .venv\\Scripts\\python.exe prototipos\\poster_mur_realista.py --paleta gibs
    .venv\\Scripts\\python.exe prototipos\\poster_mur_realista.py --help
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from rutas import SALIDAS  # noqa: E402

# ------------------------------------------------------------------ contratos GIBS
API = "https://wvs.earthdata.nasa.gov/api/v1/snapshot"
BASE_LAYER = "BlueMarble_ShadedRelief_Bathymetry"
LEGEND_URL = ("https://gibs.earthdata.nasa.gov/legends/"
              "GHRSST_Sea_Surface_Temperature_Anomalies_H.png")
# La capa de anomalía de GIBS satura en ±3 °C (ver la leyenda oficial).
VMIN, VMAX = -3.0, 3.0
BBOX = (-180.0, -90.0, 180.0, 90.0)
# Caché local de los insumos estáticos (no se versiona: vive en SALIDAS).
CACHE = SALIDAS / "_poster_realista"

# El crudo de prueba: la serie semanal MUR que ya está en el dataset.
CRUDO_DEFAULT = (SALIDAS / "frames_mur_globo_2025-01-01T0000_94f_2711px" /
                 "crudo_001.jpg")
# Centro del globo por defecto: Pacífico ecuatorial (mismo del render MUR del repo).
CENTRO_DEFAULT = (-125.0, 0.0)

# Rampa nueva: azul frío -> blanco neutro -> rojo cálido. La rampa de GIBS se puede
# recuperar con --paleta gibs para comparar.
COOL_WARM = [
    (0.00, "#053061"), (0.15, "#2166ac"), (0.35, "#92c5de"),
    (0.50, "#f7f7f7"), (0.65, "#f4a582"), (0.85, "#b2182b"),
    (1.00, "#67001f"),
]
OCEAN_BASE = np.array([228, 235, 240], dtype=np.uint8)   # sólo se ve en huecos
WHITE = "#ffffff"
INK = "#30353a"
INK_SOFT = "#6d7378"
INK_FAINT = "#92979c"


# ------------------------------------------------------------------------ descargas
def _bajar(url: str, destino: Path, min_bytes: int = 20_000) -> Path:
    """Baja `url` a `destino` si no está; escritura atómica y reanudable."""
    if destino.exists() and destino.stat().st_size > min_bytes:
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, timeout=120, headers={"User-Agent": "climate3d/1.0"})
    r.raise_for_status()
    if len(r.content) < min_bytes:
        raise RuntimeError(f"respuesta demasiado chica ({len(r.content)} B): {url}")
    tmp = destino.with_suffix(destino.suffix + ".parcial")
    tmp.write_bytes(r.content)
    tmp.replace(destino)
    return destino


def _url_base(fecha: datetime, ancho: int) -> str:
    """Blue Marble es estático: la hora sólo viaja para completar el contrato GIBS."""
    o, s, e, n = BBOX
    momento = fecha.strftime("%Y-%m-%dT%H:%M:%SZ")
    return (f"{API}?REQUEST=GetSnapshot&TIME={momento}"
            f"&BBOX={s},{o},{n},{e}&CRS=EPSG:4326&LAYERS={BASE_LAYER}"
            f"&FORMAT=image/jpeg&WIDTH={ancho}&HEIGHT={ancho // 2}")


# ------------------------------------------------------------------------ lectura
def buscar_crudo(explicito: str | None) -> tuple[Path, datetime]:
    """Crudo a usar y su fecha.

    Con `--crudo` se usa ése; si no, se busca el primer `crudo_001.jpg` de la serie
    MUR más reciente bajo SALIDAS. La fecha sale del nombre de la carpeta
    (`frames_mur_globo_YYYY-MM-DDTHHMM_...`) y, si no, del mtime del archivo.
    """
    if explicito:
        p = Path(explicito)
        if not p.exists():
            raise SystemExit(f"No existe el crudo indicado: {p}")
        carpeta = p.parent.name
    else:
        carpetas = sorted(SALIDAS.glob("frames_mur_globo_*"),
                          key=lambda d: d.stat().st_mtime)
        if not carpetas:
            raise SystemExit(f"No hay frames MUR bajo {SALIDAS}. Pasá uno con --crudo.")
        p = None
        for carpeta in reversed(carpetas):
            for nombre in ("crudo_001.jpg", "crudo_01.jpg"):
                candidato = carpeta / nombre
                if candidato.exists():
                    p = candidato
                    break
            if p is not None:
                break
        if p is None:
            raise SystemExit(f"No encontré crudos en {carpetas[-1]}. Pasá uno con --crudo.")

    m = re.search(r"frames_mur_globo_(\d{4}-\d{2}-\d{2})T(\d{2})(\d{2})", p.parent.name)
    if m:
        fecha = datetime.strptime(f"{m.group(1)} {m.group(2)}:{m.group(3)}",
                                  "%Y-%m-%d %H:%M")
    else:
        fecha = datetime.fromtimestamp(p.stat().st_mtime)
    return p, fecha


def cargar_rgb(ruta: Path, ancho: int) -> np.ndarray:
    """Imagen RGB remuestreada al ancho de trabajo (alto = ancho/2 para 2:1)."""
    alto = ancho // 2
    with Image.open(ruta) as im:
        return np.asarray(im.convert("RGB").resize((ancho, alto), Image.LANCZOS))


def paleta_gibs(ruta: Path) -> tuple[np.ndarray, np.ndarray]:
    """Colores y valores de la barra de la leyenda oficial de GIBS.

    La leyenda es una imagen de 378x86: se busca la fila con más colores (la barra),
    se recorta el marco negro y se mapea el degradé a -3..+3 °C. La rampa es
    discreta (64 pasos), así que se conservan los duplicados con su valor lineal.
    """
    leg = np.asarray(Image.open(ruta).convert("RGB"))
    mejor_y, mejor_n = 0, -1
    for y in range(leg.shape[0]):
        n = len(np.unique(leg[y], axis=0))
        if n > mejor_n:
            mejor_y, mejor_n = y, n
    fila = leg[mejor_y]
    idx = np.where(~np.all(fila > 245, axis=1))[0]
    if idx.size < 10:
        raise RuntimeError("No pude leer la barra de la leyenda de GIBS.")
    x0, x1 = int(idx[0]), int(idx[-1])
    # Recorta el marco negro de 1-2 px a cada lado.
    while x0 < x1 and int(fila[x0].max()) < 20:
        x0 += 1
    while x1 > x0 and int(fila[x1].max()) < 20:
        x1 -= 1
    cols = fila[x0:x1 + 1].astype(np.float32)
    vals = np.linspace(VMIN, VMAX, len(cols), dtype=np.float32)
    return cols, vals


# ------------------------------------------------------------------ máscara de tierra
def mascara_tierra(shape: tuple[int, int]) -> np.ndarray:
    """Máscara booleana de continentes rasterizando Natural Earth (50m, fallback 110m).

    Se dibuja en lon/lat (PlateCarree) con PIL: cada anillo exterior se proyecta a
    píxeles y se rellena. Así el relieve de la base queda sólo sobre tierra y el
    océano puede llevar el color de los datos (o el gris muy claro de los huecos).
    """
    import cartopy.io.shapereader as shpreader
    from shapely.geometry import MultiPolygon, Polygon

    try:
        shp = shpreader.natural_earth("50m", "physical", "land")
    except Exception:
        shp = shpreader.natural_earth("110m", "physical", "land")

    alto, ancho = shape
    lienzo = Image.new("L", (ancho, alto), 0)
    lapiz = ImageDraw.Draw(lienzo)
    o, s, e, n = BBOX
    for geom in shpreader.Reader(shp).geometries():
        if isinstance(geom, Polygon):
            polys = [geom]
        elif isinstance(geom, MultiPolygon):
            polys = list(geom.geoms)
        else:
            continue
        for poly in polys:
            pts = [((lon - o) / (e - o) * (ancho - 1),
                    (n - lat) / (n - s) * (alto - 1))
                   for lon, lat in poly.exterior.coords]
            if len(pts) >= 3:
                lapiz.polygon(pts, fill=255)
    return np.asarray(lienzo) > 127


# --------------------------------------------------------------------- decodificación
def _lut_6bits(cols: np.ndarray) -> np.ndarray:
    """LUT color cuantizado (6 bits/canal) -> índice de la paleta más cercana.

    262 144 entradas contra 356 colores de la leyenda: es rápido, y evita recorrer
    33 M de píxeles contra la paleta completa. La cuantización a 6 bits introduce un
    error menor a 2/255, imperceptible después de aplicar la rampa nueva.
    """
    niveles = np.arange(64, dtype=np.float32) * 4.0 + 2.0
    r, g, b = np.meshgrid(niveles, niveles, niveles, indexing="ij")
    grid = np.stack([r, g, b], axis=-1).reshape(-1, 3)          # (262144, 3)
    # Distancia al cuadrado contra cada color de la paleta, por bloques (memoria).
    valores = np.empty(grid.shape[0], dtype=np.float32)
    paso = 8192
    for i in range(0, grid.shape[0], paso):
        bloque = grid[i:i + paso]
        d = ((bloque[:, None, :] - cols[None, :, :]) ** 2).sum(axis=2)
        valores[i:i + paso] = d.argmin(axis=1)
    return valores


def decodificar(data: np.ndarray, cols: np.ndarray,
                vals: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Valor de anomalía por píxel y máscara de validez.

    El JPEG viene con tierra y huecos en negro; además hay un borde antialiasado
    oscuro contra la costa. Se descarta todo color con max(canal) < 50 y toda
    coincidencia que quede lejos de la paleta (> 55 en distancia RGB): esos píxeles
    no son dato y se rellenan con la base.
    """
    idx_pal = _lut_6bits(cols)
    q = (data >> 2).astype(np.int32)
    clave = (q[..., 0] << 12) | (q[..., 1] << 6) | q[..., 2]
    indice = idx_pal[clave].astype(np.intp)
    valores = vals[indice]

    # Distancia real del color original al color elegido: descarta antialias/JPEG.
    cercano = cols[indice]
    dist = np.sqrt(((data.astype(np.float32) - cercano) ** 2).sum(axis=2))
    valido = (data.max(axis=2) > 50) & (dist < 55.0)
    return valores, valido


def aplicar_rampa(valores: np.ndarray, valido: np.ndarray, cmap) -> np.ndarray:
    """Convierte valores a RGB con la rampa nueva."""
    from matplotlib.colors import Normalize
    rgba = cmap(Normalize(VMIN, VMAX)(valores))
    out = (rgba[..., :3] * 255).astype(np.uint8)
    out[~valido] = OCEAN_BASE
    return out


# -------------------------------------------------------------------------- warping
def warp_ortho(rgba: np.ndarray, centro: tuple[float, float], lado: int) -> np.ndarray:
    """Reproyecta una imagen global lon/lat (2:1) a Orthographic.

    Mismo mapeo inverso que `cuadros/cuadros_mur.py` (para no depender de scipy),
    pero conservando el canal alfa. Para cada píxel del disco se calcula su
    (lon, lat) y se muestrea la imagen de origen con interpolación bilineal.
    """
    o, s, e, n = BBOX
    lon0, lat0 = np.radians(centro[0]), np.radians(centro[1])
    alto_o, ancho_o = rgba.shape[:2]

    y = np.linspace(1.0, -1.0, lado)
    x = np.linspace(-1.0, 1.0, lado)
    X, Y = np.meshgrid(x, y)
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
    valido = (dentro & (col >= 0) & (col <= ancho_o - 1)
              & (fila >= 0) & (fila <= alto_o - 1))

    c0 = np.clip(np.floor(col), 0, ancho_o - 2).astype(np.intp)
    f0 = np.clip(np.floor(fila), 0, alto_o - 2).astype(np.intp)
    fc = np.clip(col - c0, 0.0, 1.0)[..., None]
    ff = np.clip(fila - f0, 0.0, 1.0)[..., None]
    a = rgba[f0, c0].astype(np.float32)
    b = rgba[f0, c0 + 1].astype(np.float32)
    cc = rgba[f0 + 1, c0].astype(np.float32)
    d = rgba[f0 + 1, c0 + 1].astype(np.float32)
    mezcla = (a * (1 - fc) + b * fc) * (1 - ff) + (cc * (1 - fc) + d * fc) * ff
    mezcla[..., 3] = mezcla[..., 3] * valido
    return np.clip(mezcla, 0, 255).astype(np.uint8)


def sombrear_disco(rgba: np.ndarray) -> np.ndarray:
    """Luz esférica sutil: oscurece el limbo y da un brillo suave arriba-izquierda.

    Sin esto el disco queda plano (los colores del dato son uniformes). El factor
    combina un *limb darkening* radial con una lambertiana muy leve: el centro
    conserva su color y el borde se hunde, que es la señal visual de esfera.
    """
    alto, ancho = rgba.shape[:2]
    y = np.linspace(1.0, -1.0, alto)
    x = np.linspace(-1.0, 1.0, ancho)
    X, Y = np.meshgrid(x, y)
    rho2 = np.clip(X * X + Y * Y, 0.0, 1.0)
    z = np.sqrt(np.clip(1.0 - rho2, 0.0, 1.0))

    luz = np.array([-0.42, 0.52, 0.74])
    luz /= np.linalg.norm(luz)
    lam = np.clip(X * luz[0] + Y * luz[1] + z * luz[2], 0.0, 1.0)

    # Limbo al 88 % y brillo direccional suave: esfera, sin apagar el dato del borde.
    sombra = (1.0 - 0.10 * rho2 ** 1.3) * (0.97 + 0.03 * lam)
    salida = rgba.astype(np.float32)
    salida[..., :3] *= sombra[..., None]
    return np.clip(salida, 0, 255).astype(np.uint8)


def sombra_exterior(lado: int, alfa: float = 0.16) -> tuple[np.ndarray, float]:
    """Sombra difusa y corrida abajo-derecha para despegar el globo del blanco.

    Un disco negro desplazado, desenfocado con GaussianBlur: la parte que queda
    debajo del globo no se ve (el globo es opaco) y sólo asoma un halo suave por el
    borde inferior derecho. No es un contorno: no dibuja un anillo.
    """
    from PIL import Image as _Image, ImageFilter as _Filter

    ext = 1.14
    n = max(64, int(lado * ext))
    y = np.linspace(ext, -ext, n)
    x = np.linspace(-ext, ext, n)
    X, Y = np.meshgrid(x, y)
    # Sombra corrida abajo-derecha, como si la luz viniera de arriba-izquierda.
    r = np.hypot(X - 0.032, Y + 0.046)
    disco = (r <= 1.0).astype(np.uint8) * 255
    borroso = _Image.fromarray(disco).filter(
        _Filter.GaussianBlur(radius=max(2.0, n * 0.008)))
    a = (np.asarray(borroso, dtype=np.float32) / 255.0) * alfa
    img = np.zeros((n, n, 4), dtype=np.uint8)
    img[..., 3] = (a * 255).astype(np.uint8)
    return img, ext


# --------------------------------------------------------------------------- render
def componer(data: np.ndarray, base: np.ndarray, tierra: np.ndarray,
             recolor: bool, cols: np.ndarray, vals: np.ndarray, cmap):
    """Arma el raster global: relieve gris en tierra, dato (o gris claro) en océano.

    El gris se estira con los percentiles de la tierra (no del océano, que es casi
    negro en Blue Marble): así los relieves y las sombras de montaña se ven, en vez
    de quedar un gris plano.
    """
    gris = 0.299 * base[..., 0] + 0.587 * base[..., 1] + 0.114 * base[..., 2]
    g = gris / 255.0
    lo, hi = np.percentile(g[tierra], (3, 97))
    g = np.clip((g - lo) / max(float(hi - lo), 1e-6), 0.0, 1.0)
    gris = np.clip(0.42 + 0.58 * g, 0.0, 1.0)
    terreno = (gris * 255).astype(np.uint8)
    rgb = np.empty_like(base)
    rgb[:] = OCEAN_BASE
    rgb[tierra] = terreno[tierra][:, None]

    # El mismo decodificado alimenta la rampa nueva, la original y la campana.
    valores, valido = decodificar(data, cols, vals)
    if recolor:
        dato = aplicar_rampa(valores, valido, cmap)
    else:
        # Rampa original de GIBS: se conserva el color tal como llega.
        import matplotlib.colors as mcolors
        dato = data.copy()
        cmap = mcolors.ListedColormap(cols / 255.0, name="gibs_mur")

    # La capa de MUR trae la tierra en negro, pero el JPEG deja esquirlas de color
    # sobre la costa y algunos lagos: la máscara Natural Earth manda sobre el dato.
    valido &= ~tierra

    comp = rgb.copy()
    comp[valido] = dato[valido]
    alfa = np.full(comp.shape[:2], 255, dtype=np.uint8)
    return np.dstack([comp, alfa]), cmap, estadisticas(valores, valido)


def estadisticas(valores: np.ndarray, valido: np.ndarray) -> dict:
    """Media, desvío, p95 e histograma area-ponderados por cos(lat).

    Se pondera porque una grilla equirectangular sobre-representa los polos; sin
    peso, la cola fría de altas latitudes falsea la media y el desvío. El p95 es
    la métrica que sí muestra el calentamiento de la cola cálida.
    """
    alto, ancho = valido.shape
    lat = np.linspace(90.0, -90.0, alto)
    peso = np.cos(np.radians(lat))[:, None] * np.ones((1, ancho), dtype=np.float32)
    if not np.any(valido):
        return {"mu": 0.0, "sigma": 1.0, "p95": 0.0,
                "hist": np.zeros(96), "centros": np.linspace(VMIN, VMAX, 96)}
    vv = valores[valido].astype(np.float64)
    ww = peso[valido].astype(np.float64)
    mu = float(np.average(vv, weights=ww))
    sigma = max(float(np.sqrt(np.average((vv - mu) ** 2, weights=ww))), 0.05)
    # Percentil 95 ponderado: ordena por valor y acumula peso hasta el 95 %.
    orden = np.argsort(vv)
    acum = np.cumsum(ww[orden])
    acum /= acum[-1]
    p95 = float(vv[orden][min(int(np.searchsorted(acum, 0.95)), len(vv) - 1)])
    hist, bordes = np.histogram(vv, bins=96, range=(VMIN, VMAX),
                                weights=ww, density=True)
    # Suavizado leve: el histograma crudo tiene dientes por la cuantización
    # de la paleta de GIBS (64 pasos), no por estructura física.
    nucleo = np.exp(-0.5 * np.linspace(-2.5, 2.5, 11) ** 2)
    hist = np.convolve(hist, nucleo / nucleo.sum(), mode="same")
    centros = (bordes[:-1] + bordes[1:]) / 2.0
    return {"mu": mu, "sigma": sigma, "p95": p95,
            "hist": hist, "centros": centros}


def estadisticas_serie(crudos: list[Path], tierra: np.ndarray,
                       cols: np.ndarray, vals: np.ndarray,
                       ancho: int) -> list[dict]:
    """Estadísticas de toda la serie, para el mini trend de μ y p95.

    Sólo decodifica y agrega; no compone ni reproyecta, así que es mucho más
    liviano que renderizar cada cuadro. Se calcula una vez y se pasa al dibujo.
    """
    serie = []
    for crudo in crudos:
        data = cargar_rgb(crudo, ancho)
        valores, valido = decodificar(data, cols, vals)
        valido &= ~tierra
        serie.append(estadisticas(valores, valido))
    return serie


def dibujar(disco: np.ndarray, centro: tuple[float, float], fecha: datetime,
            cmap, stats: dict, args, serie: list[dict] | None = None,
            idx: int | None = None) -> tuple:
    """Dibuja el globo y la tarjeta de leyenda (campana + barra de color).

    Con `serie` (estadísticas de toda la animación) agrega el mini trend de μ y
    p95 y la marca de la media; sin `serie` queda el diseño fijo ya aprobado.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    from matplotlib.colors import Normalize

    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"],
                         "axes.unicode_minus": False})
    ancho_in, alto_in = 10.4, 11.4
    dpi = args.dpi or (args.px / (0.925 * ancho_in))
    fig = plt.figure(figsize=(ancho_in, alto_in), dpi=dpi)
    fig.patch.set_facecolor(WHITE)

    # El rectángulo es cuadrado en pulgadas: el disco llena el ancho y deja el pie
    # para la tarjeta de leyenda (como en la referencia de NASA).
    lado_in = 0.925 * ancho_in
    gw, gh = lado_in / ancho_in, lado_in / alto_in
    gx, gy = (1 - gw) / 2, 0.140
    ax = fig.add_axes([gx, gy, gw, gh],
                      projection=ccrs.Orthographic(central_longitude=centro[0],
                                                   central_latitude=centro[1]))
    ax.set_facecolor(WHITE)
    ax.set_global()

    # Halo exterior en un axes normal (no cartopy): así `imshow` no intenta
    # reproyectar y no pide scipy/pykdtree. Va detrás del globo.
    halo, ext = sombra_exterior(args.px)
    pad = (ext - 1.0) / 2.0
    ax_halo = fig.add_axes([gx - pad * gw, gy - pad * gh, ext * gw, ext * gh])
    ax_halo.set_zorder(-1)
    ax_halo.set_axis_off()
    ax_halo.patch.set_alpha(0.0)
    ax_halo.imshow(halo, origin="upper", extent=[0, 1, 0, 1],
                   interpolation="bilinear")

    xl, yl = ax.projection.x_limits, ax.projection.y_limits
    ax.imshow(sombrear_disco(disco), origin="upper",
              extent=[xl[0], xl[1], yl[0], yl[1]],
              transform=ax.projection, interpolation="lanczos", zorder=2)
    ax.set_global()

    # Retículo tenue y costas finas: dan escala sin competir con el dato.
    ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=False,
                 xlocs=np.arange(-180, 181, 30), ylocs=np.arange(-90, 91, 30),
                 linewidth=0.45, color="#3d4a54", alpha=0.24, zorder=5)
    try:
        ax.add_feature(cfeature.COASTLINE.with_scale("50m"), linewidth=0.5,
                       edgecolor="#666b70", alpha=0.55, zorder=6)
    except Exception:
        ax.add_feature(cfeature.COASTLINE.with_scale("110m"), linewidth=0.5,
                       edgecolor="#666b70", alpha=0.55, zorder=6)
    # Limbo azulado muy fino: la "atmósfera" que remata la esfera.
    ax.spines["geo"].set_edgecolor("#c6d8e4")
    ax.spines["geo"].set_linewidth(1.0)

    # ---------------------------------------------------------------- tarjeta
    card_x, card_y, card_w, card_h = 0.210, 0.038, 0.580, 0.080
    sombra_card = mpatches.FancyBboxPatch(
        (card_x, card_y - 0.0022), card_w, card_h,
        boxstyle="round,pad=0.0,rounding_size=0.010",
        transform=fig.transFigure, facecolor="#000000", alpha=0.035,
        edgecolor="none", zorder=7)
    fig.add_artist(sombra_card)
    card = mpatches.FancyBboxPatch(
        (card_x, card_y), card_w, card_h,
        boxstyle="round,pad=0.0,rounding_size=0.010",
        transform=fig.transFigure, facecolor="#fcfdfe",
        edgecolor="#e5e9ed", linewidth=0.7, zorder=8)
    fig.add_artist(card)

    # Distribución real (área-ponderada) + ajuste normal como referencia. La
    # campana sola no alcanza: la distribución tiene más kurtosis que una normal,
    # así que se muestran las dos y se rotula el ajuste.
    cax_curva = fig.add_axes([0.230, 0.079, 0.540, 0.032], zorder=9)
    cax_curva.set_facecolor("none")
    cax_curva.set_xlim(VMIN, VMAX)
    cax_curva.set_ylim(0, 1.12)
    cax_curva.axis("off")
    mu, sigma = stats["mu"], stats["sigma"]
    hist, centros = stats["hist"], stats["centros"]
    x = np.linspace(VMIN, VMAX, 512)
    normal = np.exp(-0.5 * ((x - mu) / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi))
    escala = max(float(np.max(hist)), float(np.max(normal)), 1e-9)
    y_emp = hist / escala
    y_nor = normal / escala

    grad = np.linspace(0, 1, 256).reshape(1, -1)
    im = cax_curva.imshow(grad, extent=[VMIN, VMAX, 0, 1.0], aspect="auto",
                          cmap=cmap, alpha=0.18, origin="lower", zorder=1)
    poly = cax_curva.fill_between(centros, 0, y_emp, facecolor="none",
                                  edgecolor="none")
    try:
        im.set_clip_path(poly.get_paths()[0], transform=cax_curva.transData)
    except Exception:
        pass
    cax_curva.plot(centros, y_emp, color="#7a858f", lw=0.9, zorder=2)
    cax_curva.plot(x, y_nor, color="#4f5b66", lw=0.8, ls=(0, (3, 2)), zorder=3)
    cax_curva.axvline(0, color="#cbd1d6", lw=0.6, ls=(0, (2, 2)), zorder=1)
    # Marca de la media: la línea se corre con μ aunque el pico de la
    # distribución empírica quede casi fijo (el calentamiento está en la cola).
    cax_curva.axvline(mu, color="#2f3a44", lw=0.7, alpha=0.55, zorder=4)
    y_mu = float(np.interp(mu, x, y_nor))
    cax_curva.plot([mu], [y_mu], marker="o", ms=2.0, color="#2f3a44", zorder=5)
    cax_curva.text(VMIN + 0.06, 1.08,
                   f"normal fit  μ {mu:+.1f} · σ {sigma:.1f} °C",
                   ha="left", va="top", fontsize=6.8, color="#9aa0a5",
                   fontfamily="Segoe UI")

    if serie is not None and len(serie) > 1 and idx is not None:
        # Mini trend de toda la serie: μ (sólida) y p95 (a trazos). Cada una se
        # normaliza a su propio rango para que la tendencia se lea; el punto
        # lleno marca el cuadro actual.
        ax_t = fig.add_axes([0.675, 0.090, 0.090, 0.019], zorder=10)
        ax_t.set_facecolor("none")
        ax_t.axis("off")
        mus = np.array([s["mu"] for s in serie], dtype=float)
        p95 = np.array([s["p95"] for s in serie], dtype=float)
        n = len(serie)
        xv = np.arange(n)

        def _norm(v):
            lo, hi = float(np.min(v)), float(np.max(v))
            return (v - lo) / max(hi - lo, 1e-9)

        ym, yp = _norm(mus), _norm(p95)
        ax_t.plot(xv, ym, color="#4f5b66", lw=0.7, zorder=2)
        ax_t.plot(xv, yp, color="#9aa0a5", lw=0.6, ls=(0, (2, 1.5)), zorder=2)
        ax_t.axvline(idx, color="#c3c9ce", lw=0.5, alpha=0.8, zorder=1)
        ax_t.plot([idx], [ym[idx]], marker="o", ms=1.7, color="#4f5b66", zorder=3)
        ax_t.plot([idx], [yp[idx]], marker="o", ms=1.7, color="#9aa0a5", zorder=3)
        ax_t.set_xlim(0, n - 1)
        ax_t.set_ylim(-0.08, 1.08)
        ax_t.text(1.03, 0.82, "μ", transform=ax_t.transAxes, fontsize=5.2,
                  color="#4f5b66", ha="left", va="center")
        ax_t.text(1.03, 0.22, "p95", transform=ax_t.transAxes, fontsize=5.2,
                  color="#9aa0a5", ha="left", va="center")
    else:
        cax_curva.text(VMAX - 0.06, 1.08, "ocean pixels · area-weighted",
                       ha="right", va="top", fontsize=6.8, color="#9aa0a5",
                       fontfamily="Segoe UI")

    # Barra de color alineada con la campana.
    cax = fig.add_axes([0.230, 0.055, 0.540, 0.010], zorder=9)
    sm = plt.cm.ScalarMappable(norm=Normalize(VMIN, VMAX), cmap=cmap)
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=cax, orientation="horizontal")
    cbar.outline.set_visible(False)
    cbar.set_ticks([VMIN, 0.0, VMAX])
    cbar.set_ticklabels(["−3", "0", "+3 °C"])
    cbar.ax.tick_params(length=0, labelsize=9.5, colors=INK_SOFT, pad=4)
    for etiqueta in cbar.ax.get_xticklabels():
        etiqueta.set_fontfamily("Segoe UI")

    # Marca de agua sobre el globo: gris medio translúcido, sin contorno. Más
    # oscura que la versión blanca anterior, pero todavía discreta.
    if args.credito:
        marca = " ".join(args.credito.upper())
        fig.text(0.5, 0.163, marca, ha="center", va="center", fontsize=8.6,
                 color=(0.31, 0.35, 0.39, 0.32), fontfamily="Segoe UI",
                 zorder=10)

    # Título y fecha en el ángulo superior izquierdo, con el mismo estilo de
    # fuente que el resto de los rótulos. La fecha se muestra en GMT-3.
    fecha_local = fecha - timedelta(hours=3)
    fig.text(0.027, 0.986, "Sea surface temperature anomaly",
             ha="left", va="top", fontsize=14.5, color=INK,
             fontfamily="Segoe UI")
    fig.text(0.027, 0.958,
             fecha_local.strftime("%d %b %Y  ·  %H:%M GMT-3").upper(),
             ha="left", va="top", fontsize=9.2, color=INK_SOFT,
             fontfamily="Segoe UI")

    # Fuente y crédito al pie, un poco más grandes que en la primera versión.
    fig.text(0.027, 0.008,
             "DATA: NASA GIBS · GHRSST MUR v4.1 · SST ANOMALY",
             ha="left", va="bottom", fontsize=8.2, color="#a3a8ad",
             fontfamily="Segoe UI")
    if args.credito:
        fig.text(0.973, 0.008, args.credito, ha="right", va="bottom",
                 fontsize=8.4, color="#a3a8ad", fontfamily="Segoe UI")
    return fig, ax


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Póster realista (globo Orthographic, fondo blanco) desde un "
                    "crudo MUR SST de GIBS.")
    ap.add_argument("--crudo", help="JPEG crudo de MUR (por defecto, el primero de "
                                    "la serie semanal 2025-01-01)")
    ap.add_argument("--centro", nargs=2, type=float, metavar=("LON", "LAT"),
                    default=list(CENTRO_DEFAULT), help="centro del globo")
    ap.add_argument("--px", type=int, default=2400,
                    help="diámetro del globo en píxeles (por defecto 2400)")
    ap.add_argument("--dpi", type=int, help="dpi; si se omite se deduce de --px")
    ap.add_argument("--base-px", type=int, default=4096,
                    help="ancho de la base Blue Marble y del raster de trabajo")
    ap.add_argument("--paleta", choices=("realista", "gibs"), default="realista",
                    help="realista = azul-blanco-rojo; gibs = rampa original")
    ap.add_argument("--credito", default="Graphic by @Gillo97",
                    help="crédito al pie; vacío = sin crédito")
    ap.add_argument("--trend", action="store_true",
                    help="agregar marca de la media y mini trend de media/p95 de la serie")
    ap.add_argument("--out", help="PNG de salida")
    args = ap.parse_args(argv)

    crudo, fecha = buscar_crudo(args.crudo)
    if args.base_px % 2:
        args.base_px += 1
    ancho_trabajo = min(args.base_px, 8192)

    CACHE.mkdir(parents=True, exist_ok=True)
    base_path = CACHE / f"base_{ancho_trabajo}.jpg"
    legend_path = CACHE / "legend_mur.png"
    _bajar(_url_base(fecha, ancho_trabajo), base_path)
    _bajar(LEGEND_URL, legend_path, min_bytes=1000)

    print(f"Crudo: {crudo}")
    print(f"Fecha: {fecha:%Y-%m-%d %H:%M} UTC | centro {tuple(args.centro)} | "
          f"globo {args.px} px | paleta {args.paleta}")

    data = cargar_rgb(crudo, ancho_trabajo)
    base = cargar_rgb(base_path, ancho_trabajo)
    tierra = mascara_tierra(data.shape[:2])
    cols, vals = paleta_gibs(legend_path)

    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("sst_anomaly", COOL_WARM)
    comp, cmap_usada, stats = componer(
        data, base, tierra, args.paleta == "realista", cols, vals, cmap)
    print(f"Distribucion area-ponderada: media {stats['mu']:+.2f} C | "
          f"desvio {stats['sigma']:.2f} C")
    print("Reproyectando a Orthographic...", flush=True)
    disco = warp_ortho(comp, tuple(args.centro), args.px)

    serie = None
    idx = None
    if args.trend:
        crudos = sorted(crudo.parent.glob("crudo_*.jpg"))
        if crudo in crudos:
            idx = crudos.index(crudo)
            # El mini trend no necesita resolución plena: 2048 alcanza y evita
            # decodificar 94 crudos de 8192 px para un sparkline de 1 cm.
            ancho_trend = min(ancho_trabajo, 2048)
            tierra_trend = (tierra if ancho_trend == ancho_trabajo
                            else mascara_tierra((ancho_trend // 2, ancho_trend)))
            print(f"Calculando trend de {len(crudos)} cuadros...", flush=True)
            serie = estadisticas_serie(crudos, tierra_trend, cols, vals, ancho_trend)

    fig, _ = dibujar(disco, tuple(args.centro), fecha, cmap_usada, stats, args,
                     serie=serie, idx=idx)

    etiqueta = "trend_" if args.trend else ""
    out = Path(args.out) if args.out else (
        SALIDAS / f"poster_mur_realista_{etiqueta}{fecha:%Y-%m-%d}"
                  f"_{int(args.centro[0]):+04d}_{int(args.centro[1]):+03d}.png")
    fig.savefig(out, facecolor=WHITE)
    import matplotlib.pyplot as plt
    plt.close(fig)
    print("PNG:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
