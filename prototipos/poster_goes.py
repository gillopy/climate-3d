"""Póster estilo *satellite full disk* desde un archivo GOES-R ABI L2 CMIP.

A diferencia del póster de anomalías (que usa una grilla global lat/lon sobre
ERA5), un archivo ABI trae el **disco completo en su grilla geoestacionaria**: hay
que dibujarlo con `cartopy.crs.Geostationary` (misma proyección que los datos, así
`pcolormesh` no necesita reproyectar nada). Se reutiliza el mismo vestuario visual
del póster: fondo casi negro, barra de color fina al pie, grilla tenue, crédito,
fuente, datos y marca de agua.

La variable se detecta sola:
  * reflectancia (units "1") -> se muestra en % (0-100)
  * temperatura de brillo (units "K") -> se muestra en °C

La paleta también: gris normal para reflectancia (0 = negro) y gris invertido para
temperatura (frío = blanco, como en las imágenes IR de siempre). Se puede forzar
con --paleta.

Uso (desde la carpeta del proyecto):

    .venv\\Scripts\\python.exe prototipos\\poster_goes.py                       # disco completo, gris
    .venv\\Scripts\\python.exe prototipos\\poster_goes.py --paleta anomalia     # paleta del póster
    .venv\\Scripts\\python.exe prototipos\\poster_goes.py --paleta anomalia --vmin 0 --vmax 45
        # disco completo cirrus C04 (1.4 µm) como en la referencia
    .venv\\Scripts\\python.exe prototipos\\poster_goes.py --globo --zona sa    # globo entero, Sudamérica
    .venv\\Scripts\\python.exe prototipos\\poster_goes.py --zona sa             # encuadre regional
    .venv\\Scripts\\python.exe prototipos\\poster_goes.py --zona py --paleta anomalia
    .venv\\Scripts\\python.exe prototipos\\poster_goes.py --lat -25.3 --lon -57.6 --ancho 20
    .venv\\Scripts\\python.exe prototipos\\poster_goes.py --extent -63 -53 -30 -18
    .venv\\Scripts\\python.exe prototipos\\poster_goes.py --nc OR_ABI-L2-CMIPF-M6C13_G19_....nc

Zonas predefinidas: py (Paraguay), br (Brasil), sa (Sudamérica), conus (EE.UU.),
caribe. Ojo: un archivo de GOES-West (G18, satélite en -137°) apenas alcanza
Paraguay, que cae al borde del disco; para Sudamérica conviene GOES-East
(G16/G19, satélite en -75.2°).

Salida: poster_goes_<PLATAFORMA>_C<banda>[_<zona>].png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import xarray as xr

import matplotlib

if "--show" not in sys.argv:
    matplotlib.use("Agg")

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from matplotlib.colors import LinearSegmentedColormap

# Bootstrap de imports: `estilo` y `rutas` viven en comun/.
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))

from estilo import (ANOM_CMAP, BG, MONTHS_EN, POSTER_DPI, POSTER_SIZE,  # noqa: E402
                    TXT, TXT_DIM, WM_COLOR)
from rutas import DATOS, SALIDAS  # noqa: E402

# Rampa IR con realce (estilo la referencia del usuario): colores para los topes
# fríos (nubes) y gris para el fondo cálido. Ojo con el orden: la posición 0 es
# el vmin (lo más frío) y la 1 el vmax (lo más cálido).
IR_REALCE_COLORS = [
    (0.00, "#ff2020"), (0.08, "#e00000"), (0.14, "#ff8000"),
    (0.20, "#f0f000"), (0.26, "#00e000"), (0.32, "#00c8ff"),
    (0.38, "#0050ff"), (0.45, "#0a2a8f"),
    (0.55, "#b0b0b0"), (0.70, "#8c8c8c"), (1.00, "#5a5a5a"),
]
IR_REALCE_CMAP = LinearSegmentedColormap.from_list("ir_realce", IR_REALCE_COLORS)

# Paletas disponibles: la del póster de anomalías y las clásicas de satélite.
PALETTES = {
    "gris": "Greys_r",       # reflectancia: 0 = negro (espacio/mar), 1 = blanco (nubes)
    "termico": "Greys",      # IR: frío (nube alta) = blanco, cálido (superficie) = negro
    "anomalia": ANOM_CMAP,   # la muestreada de la imagen de referencia
    "ir_realce": IR_REALCE_CMAP,  # IR con realce de color en los topes fríos
    "magma": "magma",
    "inferno": "inferno",
    "turbo": "turbo",
}
# Paleta por defecto según el tipo de variable: reflectancia vs temperatura de brillo.
def default_palette(unit_label):
    """Gris invertido para temperatura (frío = blanco); gris normal para reflectancia."""
    return "termico" if unit_label == "°C" else "gris"


# Zonas predefinidas: (oeste, este, sur, norte) en grados lon/lat.
ZONES = {
    "py": (-63.0, -53.0, -30.0, -18.0),      # Paraguay y alrededores
    "br": (-75.0, -33.0, -34.0, 6.0),        # Brasil
    "sa": (-92.0, -30.0, -58.0, 14.0),       # Sudamérica
    "conus": (-130.0, -60.0, 20.0, 55.0),    # EE.UU. contiguo
    "caribe": (-90.0, -55.0, 8.0, 28.0),     # Caribe
}

# Centro por defecto del globo Orthographic (mismo del póster de ERA5).
GLOBE_LON, GLOBE_LAT = -58.0, -23.0

# Borde destacado por defecto: el contorno de Paraguay (el póster es de Paraguay).
BORDE_DEFAULT = Path(__file__).resolve().parent.parent / "datos" / "paraguay_gadm.json"


# ------------------------------------------------------------------- lectura
def find_goes_file(data_dir: Path, explicit: str | None) -> Path:
    """Archivo ABI a usar: el de `--nc`, o el más reciente bajo `data_dir`.

    Busca recursivamente porque los .nc están en subcarpetas por satélite
    (`goes_c13_g19`, `goes_c04_g18`, ...).
    """
    if explicit:
        p = Path(explicit)
        if not p.exists():
            raise SystemExit(f"No existe el archivo indicado: {p}")
        return p
    found = list(data_dir.rglob("OR_ABI-L2-CMIP*.nc"))
    if not found:
        raise SystemExit(f"No hay archivos OR_ABI-L2-CMIP*.nc bajo {data_dir} "
                         "(pasá uno con --nc).")
    return max(found, key=lambda p: (p.stat().st_mtime, p.stat().st_size))


def sat_longitude(ds) -> float:
    """Longitud de proyección: la del metadato o la del subpunto del satélite."""
    proj = ds["goes_imager_projection"]
    lon = proj.attrs.get("longitude_of_projection_origin")
    if lon is None:
        lon = float(ds["nominal_satellite_subpoint_lon"])
    return float(lon)


def to_display(raw, cmi):
    """Convierte el campo crudo a las unidades de pantalla.

    Reflectancia (units "1") -> % ; temperatura de brillo (units "K") -> °C.
    """
    units = str(cmi.attrs.get("units", "")).strip()
    if units == "K":
        return raw - 273.15, "°C", "Temperatura de brillo"
    if units in ("1", ""):
        return raw * 100.0, "%", "Reflectancia"
    return raw, units, "Valor"


def band_name(ds, cmi) -> str:
    """Nombre corto de la variable para el rótulo (según la banda)."""
    wl = float(np.ravel(ds["band_wavelength"].values)[0])
    rid = int(np.ravel(ds["band_id"].values)[0])
    if str(cmi.attrs.get("units", "")).strip() == "K":
        return f"BANDA {rid:02d} ({wl:.1f} µm)"
    if 1.3 < wl < 1.5:
        return f"CIRRUS C{rid:02d} ({wl:.1f} µm)"
    return f"BANDA {rid:02d} ({wl:.2f} µm)"


def box_indices(proj, x, y, box):
    """Índices de la grilla dentro de la caja (oeste, este, sur, norte).

    Usa máscaras porque el eje `y` de ABI viene descendente (norte primero).
    """
    w, e, s, n = box
    pts = proj.transform_points(ccrs.PlateCarree(),
                                np.array([w, w, e, e]), np.array([s, n, s, n]))
    pts = pts[np.isfinite(pts).all(axis=1)]
    if not pts.size:
        return None
    imask = (x >= pts[:, 0].min()) & (x <= pts[:, 0].max())
    jmask = (y >= pts[:, 1].min()) & (y <= pts[:, 1].max())
    if not imask.any() or not jmask.any():
        return None
    i0, i1 = np.flatnonzero(imask)[[0, -1]]
    j0, j1 = np.flatnonzero(jmask)[[0, -1]]
    if int(i1) - int(i0) < 2 or int(j1) - int(j0) < 2:
        return None
    return int(i0), int(i1) + 1, int(j0), int(j1) + 1


def resolve_extent(args):
    """Caja lon/lat a mostrar: --lat/--lon, --extent o --zona (None = disco entero)."""
    if (args.lat is None) != (args.lon is None):
        raise SystemExit("--lat y --lon van juntos.")
    if args.lat is not None:
        half = args.ancho / 2
        # Se corrige por el coseno para que la ventana sea cuadrada en km.
        half_lat = half * np.cos(np.radians(args.lat))
        return ((args.lon - half, args.lon + half,
                 args.lat - half_lat, args.lat + half_lat),
                f"CENTRADA EN {args.lat:.1f}, {args.lon:.1f} ({args.ancho:.0f}°)")
    if args.extent:
        return tuple(float(v) for v in args.extent), None
    if args.zona:
        return ZONES[args.zona], f"ZONA {args.zona.upper()}"
    return None, None


# ------------------------------------------------------------------- póster
def draw_goes_poster(field, *, x, y, proj, title, subtitle, unit_label,
                     src_line="", data_line="", credit="", cmap="Greys_r",
                     vmin=None, vmax=None, borders=True, xlim=None, ylim=None,
                     globe_center=None, size=None, dpi=None, grid=False,
                     highlight_geojson=None, highlight_color="#000000",
                     highlight_width=0.8, time_line=""):
    """Disco completo ABI (o zona de él) con el vestuario del póster de referencia.

    Con `globe_center` se reproyecta a Orthographic: el hemisferio entero llenando
    el cuadro, centrado en (lon, lat) — el aspecto "planeta" del póster de ERA5.
    `size`/`dpi` permiten bajar la resolución: útil para los cuadros de una animación.
    `grid` dibuja el retículo tenue (por defecto apagado).
    `highlight_geojson` dibuja un borde destacado (p. ej. Paraguay, GeoJSON Polygon/
    MultiPolygon en lon/lat) con `highlight_color` y `highlight_width`.
    `time_line`, si viene, se rotula grande y en blanco debajo del título (fecha y
    hora del cuadro) y empuja el subtítulo hacia abajo.
    """
    fig = plt.figure(figsize=(size or POSTER_SIZE, size or POSTER_SIZE),
                     dpi=dpi or POSTER_DPI)
    fig.patch.set_facecolor(BG)

    if globe_center is None:
        ax = fig.add_axes([0.014, 0.014, 0.972, 0.972], projection=proj)
    else:
        ax = fig.add_axes([0.014, 0.014, 0.972, 0.972],
                          projection=ccrs.Orthographic(central_longitude=globe_center[0],
                                                       central_latitude=globe_center[1]))
    ax.set_facecolor(BG)
    ax.spines["geo"].set_visible(False)

    mesh = ax.pcolormesh(x, y, field, transform=proj, cmap=cmap,
                         vmin=vmin, vmax=vmax, shading="auto", zorder=2)
    if globe_center is not None:
        ax.set_global()
    elif xlim is None:
        # El disco inscribe en la grilla de escaneo: estos límites lo encuadran entero.
        ax.set_xlim(float(x.min()), float(x.max()))
        ax.set_ylim(float(y.min()), float(y.max()))
    else:
        ax.set_xlim(min(xlim), max(xlim))
        ax.set_ylim(min(ylim), max(ylim))

    if grid:
        ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=False,
                     linewidth=0.35, color=TXT, alpha=0.3, zorder=3)
    if highlight_geojson is not None:
        import json
        from matplotlib.collections import LineCollection
        gj = json.load(open(highlight_geojson, encoding="utf-8"))
        feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
        segs = []
        for f in feats:
            g = f["geometry"]
            polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            for poly in polys:
                for ring in poly:
                    segs.append(np.asarray(ring, dtype=float))
        ax.add_collection(LineCollection(segs, transform=ccrs.PlateCarree(),
                                         colors=highlight_color,
                                         linewidths=highlight_width, zorder=5))
    if borders:
        try:
            ax.add_feature(cfeature.COASTLINE.with_scale("110m"), linewidth=0.5,
                           edgecolor="#0b0b0b", zorder=4)
            if xlim is not None or globe_center is not None:
                ax.add_feature(cfeature.BORDERS.with_scale("110m"), linewidth=0.35,
                               edgecolor="#0b0b0b", linestyle=":", zorder=4)
        except Exception as exc:
            print(f"AVISO: costas omitidas ({exc})")

    cax = fig.add_axes([0.096, 0.067, 0.812, 0.019])
    cbar = fig.colorbar(mesh, cax=cax, orientation="horizontal")
    cbar.outline.set_visible(False)
    cbar.ax.tick_params(colors=TXT, length=3, width=0.8, labelsize=10.5, pad=3)

    fig.text(0.026, 0.985, title, color=TXT, fontsize=19,
             fontweight="bold", ha="left", va="top")
    sub_y = 0.945
    if time_line:
        fig.text(0.026, 0.944, time_line, color=TXT, fontsize=16,
                 fontweight="bold", ha="left", va="top")
        sub_y = 0.898
    fig.text(0.026, sub_y, subtitle, color=TXT_DIM, fontsize=13.5,
             fontweight="bold", ha="left", va="top", linespacing=1.12)
    fig.text(0.983, 0.983, credit, color=TXT_DIM, fontsize=12, ha="right", va="top")
    fig.text(0.096, 0.105, unit_label, color=TXT, fontsize=24, fontweight="bold",
             ha="left", va="bottom")
    fig.text(0.026, 0.012, src_line, color=TXT_DIM, fontsize=7.4, ha="left", va="bottom")
    fig.text(0.980, 0.012, data_line, color=TXT_DIM, fontsize=7.4, ha="right", va="bottom")
    if credit:
        fig.text(0.5, 0.150, " ".join(credit.upper()), color=WM_COLOR, fontsize=8.5,
                 ha="center", va="bottom")
    return fig, ax, mesh


def caption_lines(ds, cmi, kind, scene_label):
    """Título, subtítulo, fuente y datos del póster, leídos del archivo ABI.

    Se centraliza acá para que el póster fijo y la animación rotulen idéntico.
    Devuelve (title, subtitle, src_line, data_line).
    """
    platform = ds.attrs.get("platform_ID", "GOES")
    slot = ds.attrs.get("orbital_slot", "")
    band = band_name(ds, cmi)
    t = np.datetime64(ds["t"].values) if "t" in ds else None
    if t is not None:
        month = MONTHS_EN[int(str(t.astype("datetime64[M]")).split("-")[1]) - 1]
        title = f"{month} {t.astype('datetime64[Y]')}"
        data_line = (f"DATA: {platform} | {np.datetime_as_string(t, unit='m')} UTC | "
                     f"MODO {ds.attrs.get('timeline_id', '').replace('ABI ', '')}")
    else:
        title = platform
        data_line = f"DATA: {platform}"
    subtitle = f"{platform} {slot}\n{kind.upper()} · {band}"
    src_line = f"SOURCE: NOAA/NESDIS {platform} ABI L2 CMIP | {scene_label}"
    return title, subtitle, src_line, data_line


def time_label(ds) -> str:
    """Fecha y hora del cuadro para el rótulo grande (p. ej. '04 OCT 2026 · 19:00 UTC')."""
    if "t" not in ds:
        return ""
    t = np.datetime64(ds["t"].values)
    month = MONTHS_EN[int(str(t.astype("datetime64[M]")).split("-")[1]) - 1][:3]
    day = int(str(t.astype("datetime64[D]")).split("-")[2])
    year = int(str(t.astype("datetime64[Y]")))
    hhmm = np.datetime_as_string(t, unit="m").split("T")[1]
    return f"{day:02d} {month} {year} · {hhmm} UTC"


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Póster de disco completo desde un archivo GOES-R ABI L2 CMIP.")
    ap.add_argument("--nc", help="archivo ABI L2 CMIP (.nc) a usar")
    ap.add_argument("--paleta", choices=sorted(PALETTES),
                    help="paleta de color; por defecto gris (invertida si es temperatura)")
    ap.add_argument("--vmin", type=float, help="mínimo del colorbar (por defecto, auto)")
    ap.add_argument("--vmax", type=float, help="máximo del colorbar (por defecto, auto)")
    ap.add_argument("--stride", type=int, default=0,
                    help="submuestreo de la grilla; 0 = automático (~1200 px de lado)")
    ap.add_argument("--credito", default="Graphic by @Gillo97",
                    help="crédito y marca de agua central")
    ap.add_argument("--zona", choices=sorted(ZONES),
                    help="encuadre regional predefinido (si no, disco completo)")
    ap.add_argument("--globo", action="store_true",
                    help="reproyectar a Orthographic: el globo entero llenando el cuadro, "
                         "centrado en la zona (o en --lat/--lon)")
    ap.add_argument("--extent", nargs=4, metavar=("O", "E", "S", "N"),
                    help="caja lon/lat explícita, p. ej. --extent -63 -53 -30 -18")
    ap.add_argument("--lat", type=float, help="latitud del centro de la vista")
    ap.add_argument("--lon", type=float, help="longitud del centro de la vista")
    ap.add_argument("--ancho", type=float, default=20.0,
                    help="ancho de la vista en grados cuando se usa --lat/--lon")
    ap.add_argument("--sin-costas", action="store_true", help="no dibujar costas")
    ap.add_argument("--geojson", default=str(BORDE_DEFAULT),
                    help="borde a destacar (GeoJSON Polygon/MultiPolygon); "
                         "por defecto, el de Paraguay")
    ap.add_argument("--borde-color", default="#000000", help="color del borde destacado")
    ap.add_argument("--borde-ancho", type=float, default=0.8,
                    help="grosor del borde destacado (fino = sutil)")
    ap.add_argument("--sin-borde", action="store_true", help="no dibujar el borde destacado")
    ap.add_argument("--size", type=float, default=POSTER_SIZE, help="lado en pulgadas")
    ap.add_argument("--dpi", type=int, default=POSTER_DPI, help="resolución")
    ap.add_argument("--out", help="PNG de salida (por defecto, nombre automático)")
    ap.add_argument("--show", action="store_true", help="abrir la ventana al final")
    args = ap.parse_args(argv)

    SALIDAS.mkdir(parents=True, exist_ok=True)
    nc = find_goes_file(DATOS, args.nc)
    ds = xr.open_dataset(nc)
    cmi = ds["CMI"]

    # Se submuestrea ANTES de convertir: el disco completo son 5424x5424.
    # El globo reproyectado necesita menos puntos que una vista a resolución plena.
    tope = 700 if args.globo else 1200
    stride = args.stride or max(1, int(np.ceil(max(cmi.shape) / tope)))
    raw = np.asarray(cmi.values[::stride, ::stride], dtype=np.float64)
    field, unit_label, kind = to_display(raw, cmi)
    paleta = args.paleta or default_palette(unit_label)
    # cartopy espera "ángulo de escaneo x altura del satélite" (no radianes).
    gp = ds["goes_imager_projection"].attrs
    h = float(gp["perspective_point_height"])
    x = ds["x"].values[::stride] * h
    y = ds["y"].values[::stride] * h
    sweep = str(gp.get("sweep_angle_axis", "x"))
    lon0 = sat_longitude(ds)
    proj = ccrs.Geostationary(central_longitude=lon0, satellite_height=h, sweep_axis=sweep)

    vmin = args.vmin
    vmax = args.vmax
    extent, vista = resolve_extent(args)
    centro_globo = None
    if args.globo:
        if args.lat is not None:
            centro_globo = (args.lon, args.lat)
        elif args.zona:
            w, e, s, n = ZONES[args.zona]
            centro_globo = ((w + e) / 2, (s + n) / 2)
        else:
            centro_globo = (GLOBE_LON, GLOBE_LAT)
        print(f"Globo (Orthographic) centrado en lon {centro_globo[0]:.1f}, "
              f"lat {centro_globo[1]:.1f}")
    xlim = ylim = None
    if extent is not None:
        idx = box_indices(proj, x, y, extent)
        if idx is None:
            raise SystemExit(f"La vista {extent} no tiene datos en el disco de este satélite.")
        i0, i1, j0, j1 = idx
        recorte = field[j0:j1, i0:i1]
        # Los límites salen de los índices (no de set_extent): así una caja que se
        # pasa del limbo queda recortada al disco en vez de devolver un encuadre raro.
        xlim = (float(x[i0]), float(x[i1 - 1]))
        ylim = (float(y[j0]), float(y[j1 - 1]))
        print(f"Vista: {vista or extent} | caja lon/lat "
              f"{tuple(round(v, 1) for v in extent)} | recorte {recorte.shape}")
    else:
        recorte = field
    if vmin is None or vmax is None:
        lo, hi = np.nanpercentile(recorte, 0.5), np.nanpercentile(recorte, 99.5)
        vmin = float(lo) if vmin is None else vmin
        vmax = float(hi) if vmax is None else vmax

    platform = ds.attrs.get("platform_ID", "GOES")
    slot = ds.attrs.get("orbital_slot", "")
    scene = ds.attrs.get("scene_id", "Full Disk")
    band = band_name(ds, cmi)
    title, subtitle, src_line, data_line = caption_lines(
        ds, cmi, kind, vista or scene.upper())

    print(f"Archivo: {nc.name}")
    print(f"{platform} {slot} | {scene} | {band} | {kind} en {unit_label}")
    print(f"Proyección geoestacionaria {lon0:.1f}° | grilla {cmi.shape} -> "
          f"{field.shape} (stride {stride})")
    print(f"Rango mostrado: {vmin:.2f} a {vmax:.2f} {unit_label} | paleta {paleta}")

    fig, ax, _ = draw_goes_poster(field, x=x, y=y, proj=proj, title=title,
                                  subtitle=subtitle, unit_label=unit_label,
                                  src_line=src_line, data_line=data_line,
                                  credit=args.credito, cmap=PALETTES[paleta],
                                  vmin=vmin, vmax=vmax, borders=not args.sin_costas,
                                  xlim=xlim, ylim=ylim, globe_center=centro_globo,
                                  size=args.size, dpi=args.dpi,
                                  time_line=time_label(ds),
                                  highlight_geojson=None if (args.sin_borde or not args.geojson)
                                  else args.geojson,
                                  highlight_color=args.borde_color,
                                  highlight_width=args.borde_ancho)
    bid = int(np.ravel(ds["band_id"].values)[0])
    tag = "" if paleta == default_palette(unit_label) else f"_{paleta}"
    tag += "_globo" if args.globo else ""
    tag += f"_{args.zona}" if args.zona else ""
    tag += "_centro" if args.lat is not None else ""
    tag += "_extent" if args.extent else ""
    out = (Path(args.out) if args.out
           else SALIDAS / f"poster_goes_{platform}_C{bid:02d}{tag}.png")
    fig.savefig(out, facecolor=BG)
    print("PNG:", out)

    if args.show:
        plt.show()
    else:
        plt.close(fig)


if __name__ == "__main__":
    main()
