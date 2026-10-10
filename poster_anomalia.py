"""Póster de anomalía de temperatura (estilo @climatejulien) a partir de ERA5.

Genera una imagen tipo *temperature anomaly map*: globo Orthographic a pantalla
completa sobre fondo casi negro, paleta divergente de -6 a +6 °C, grilla tenue,
barra de color fina al pie con ticks enteros y rótulos (mes, TEMPERATURE ANOMALY,
crédito, fuente, datos, °C, marca de agua).

La anomalía es la temperatura media del mes elegido menos la climatología de ese
mes calculada con los DEMÁS años del propio archivo (excluir el año objetivo evita
diluir la anomalía consigo misma).

Uso (desde la carpeta del proyecto):

    .venv\\Scripts\\python.exe poster_anomalia.py                    # PNG del mes por defecto
    .venv\\Scripts\\python.exe poster_anomalia.py --mes 2026-09      # otro mes
    .venv\\Scripts\\python.exe poster_anomalia.py --credito "@miuser"
    .venv\\Scripts\\python.exe poster_anomalia.py --gif              # PNG + GIF rotando 360°
    .venv\\Scripts\\python.exe poster_anomalia.py --show             # abre la ventana al final

Salidas: planeta_anomalia_<AAAA-MM>.png y (con --gif) planeta_anomalia_rotando.gif
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import xarray as xr

import matplotlib

if "--show" not in sys.argv:          # sin --show no abre ventana (útil en headless)
    matplotlib.use("Agg")

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.colors import LinearSegmentedColormap

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

try:                                  # consola Windows puede no ser UTF-8
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ---------------------------------------------------------------- configuración
VAR_CANDIDATES = ("t2m", "stl2", "t")
MONTHS_EN = ("JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
             "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER")

ANOM_VMIN, ANOM_VMAX = -6.0, 6.0      # rango de la anomalía, en °C
POSTER_LON, POSTER_LAT = -45.0, -15.0  # centro del globo
POSTER_SIZE, POSTER_DPI = 8.4, 140     # 1176 px de lado
CHUNK = 24                            # pasos por lectura del NetCDF (~36 MB en ERA5 0.25°)

BG = "#0c1014"                        # fondo del póster (muestreado de la referencia)
TXT, TXT_DIM = "#ffffff", "#c9cfd6"
WM_COLOR = "#46536b"                  # marca de agua, discreta sobre el mapa

# Paleta muestreada píxel a píxel de la barra de color de la referencia
ANOM_COLORS = [
    (0 / 12,  "#02091b"), (1 / 12,  "#041f4c"), (2 / 12,  "#0a3874"),
    (3 / 12,  "#165696"), (4 / 12,  "#2d77b6"), (5 / 12,  "#91b8d7"),
    (6 / 12,  "#f7f8fa"), (7 / 12,  "#f5a099"), (8 / 12,  "#f0493a"),
    (9 / 12,  "#b7231c"), (10 / 12, "#780912"), (11 / 12, "#47000a"),
    (12 / 12, "#1b0002"),
]
ANOM_CMAP = LinearSegmentedColormap.from_list("anomaly_ref", ANOM_COLORS)


# ---------------------------------------------------------------------- datos
def synthetic_field(nlat=181, nlon=360, seed=0):
    """Campo global sintético en **Kelvin** (fallback sin archivo real).

    Imita la estructura temporal del request ERA5 (un día de cada mes, a las
    00/06/12/18 UTC de 2024-2026) con ciclo diurno, ciclo estacional, tendencia y
    ruido sinóptico, para que climatología y anomalía sean significativas.
    """
    lat = np.linspace(90, -90, nlat)
    lon = np.linspace(0, 359, nlon)
    LAT, LON = np.meshgrid(lat, lon, indexing="ij")
    rng = np.random.default_rng(seed)

    times = np.array([np.datetime64(f"{y}-{m:02d}-15T{h:02d}:00")
                      for y in (2024, 2025, 2026) for m in range(1, 13)
                      for h in (0, 6, 12, 18)])
    doy = (times - times.astype("datetime64[Y]").astype("datetime64[D]")).astype(int)
    year = times.astype("datetime64[Y]").astype(int) + 1970
    hour = (times - times.astype("datetime64[D]")).astype("timedelta64[h]").astype(int)

    base = 30 * np.cos(np.deg2rad(LAT)) ** 2 - 17
    relief = (8 * np.sin(np.deg2rad(LON * 3)) * np.cos(np.deg2rad(LAT * 2))
              + 4 * np.sin(np.deg2rad(LON * 7 + 40)))
    seasonal = (-11.0 * np.cos(2 * np.pi * (doy - 15) / 365.0)[:, None, None]
                * np.sin(np.deg2rad(LAT))[None])
    trend = 0.20 * (year + doy / 365.0 - 2024)[:, None, None]
    diurnal = 8 * np.sin(2 * np.pi * hour[:, None, None] / 24
                         - 2 * np.pi * LON[None] / 360)

    n_modes = 14
    kx, ky = rng.integers(1, 6, n_modes), rng.integers(1, 5, n_modes)
    px, py = rng.uniform(0, 2 * np.pi, (2, n_modes))
    state = rng.standard_normal(n_modes)
    noise = np.empty((times.size, nlat, nlon))
    for t in range(times.size):
        state = 0.85 * state + 0.55 * rng.standard_normal(n_modes)
        noise[t] = sum(state[m] * np.sin(np.deg2rad(kx[m] * LON) + px[m])
                       * np.cos(np.deg2rad(ky[m] * LAT) + py[m])
                       for m in range(n_modes))
    noise *= 1.5 / noise.std()

    data = base[None] + relief[None] + seasonal + trend + diurnal + noise + 273.15
    return xr.DataArray(data.astype("float32"),
                        dims=("valid_time", "latitude", "longitude"),
                        coords={"valid_time": times, "latitude": lat, "longitude": lon})


def find_data_file(data_dir: Path, explicit: str | None) -> Path | None:
    """Archivo de entrada: el indicado, o el .nc/.grib más grande de la carpeta."""
    if explicit:
        p = Path(explicit)
        if not p.exists():
            raise SystemExit(f"No existe el archivo indicado: {p}")
        return p
    found = (list(data_dir.glob("*.nc")) + list(data_dir.glob("*.grib"))
             + list(data_dir.glob("*.grib2")))
    # Los OR_ABI-* son GOES (otra proyección y otras variables): no son ERA5.
    found = [f for f in found if f.is_file() and not f.name.startswith("OR_ABI")]
    return max(found, key=lambda p: p.stat().st_size) if found else None


def load_field(data_dir: Path, explicit: str | None):
    """Devuelve (DataArray 3D en Kelvin, tiempos, es_sintetico).

    Con archivo real la lectura es lazy (`open_dataset` sin `.load()`); sin archivo
    cae a datos sintéticos para que el póster siempre se pueda generar.
    """
    f = find_data_file(data_dir, explicit)
    if f is not None:
        try:
            ds = xr.open_dataset(f)
        except Exception as exc:                       # archivo corrupto/parcial
            print(f"No se pudo abrir {f.name}: {exc}")
            ds = None
        if ds is not None:
            for name in VAR_CANDIDATES:
                if name not in ds:
                    continue
                da = ds[name]
                keep = ("valid_time", "time", "latitude", "longitude")
                da = da.isel({d: 0 for d in da.dims if d not in keep})   # expver, number...
                tdim = "valid_time" if "valid_time" in da.dims else "time"
                if tdim not in da.dims:                 # archivo 2D -> eje de tiempo trivial
                    da = da.expand_dims({tdim: [np.datetime64("NaT")]})
                size_gb = f.stat().st_size / 1e9
                print(f"Archivo: {f.name} ({size_gb:.2f} GB) | variable '{name}' | "
                      f"{da.sizes[tdim]} pasos | grilla "
                      f"{da.sizes['latitude']}x{da.sizes['longitude']}")
                # Se deja en Kelvin: restar 273.15 aquí leería el archivo completo
                # (sin dask la aritmética lazy sobre todo el array no está soportada).
                return da, da[tdim].values, False
            print(f"{f.name} no contiene ninguna de {VAR_CANDIDATES}")
    print("AVISO: no hay archivo ERA5 en la carpeta -> datos SINTÉTICOS.\n"
          "       Descargalo con: .venv\\Scripts\\python.exe descargar_era5.py")
    da = synthetic_field()
    return da, da["valid_time"].values, True


# --------------------------------------------------------- climatología/anomalía
def months_years(times):
    """Años y meses enteros (1-12) de cada paso; 0 donde la fecha es inválida."""
    valid = ~np.isnat(times)
    month = np.zeros(times.size, dtype=int)
    year = np.zeros(times.size, dtype=int)
    month[valid] = times[valid].astype("datetime64[M]").astype(int) % 12 + 1
    year[valid] = times[valid].astype("datetime64[Y]").astype(int) + 1970
    return month, year, valid


def mean_steps(da, tdim, idx, chunk=CHUNK):
    """Media (K) de los pasos `idx`, leída por bloques para no cargar todo en RAM."""
    total = None
    for a in range(0, len(idx), chunk):
        block = np.asarray(da.isel({tdim: idx[a:a + chunk]}).values, dtype=np.float64)
        partial = block.sum(axis=0)
        total = partial if total is None else total + partial
    return total / len(idx)


def month_climatology(da, tdim, times, exclude_years=()):
    """Climatología mensual (K, forma 12xlatxlon) del propio archivo, por bloques.

    Omite los años indicados (p. ej. el año objetivo) para que la anomalía no se
    diluya contra sí misma.
    """
    month, year, valid = months_years(times)
    shape = (12, da.sizes["latitude"], da.sizes["longitude"])
    sums = np.zeros(shape)
    counts = np.zeros(12, dtype=int)
    used: set[int] = set()
    for a in range(0, times.size, CHUNK):
        b = min(a + CHUNK, times.size)
        block = np.asarray(da.isel({tdim: slice(a, b)}).values, dtype=np.float64)
        for j, i in enumerate(range(a, b)):
            if valid[i] and int(year[i]) not in exclude_years:
                sums[month[i] - 1] += block[j]
                counts[month[i] - 1] += 1
                used.add(int(year[i]))
    clim = np.divide(sums, counts[:, None, None], np.full(shape, np.nan),
                     where=counts[:, None, None] > 0)
    return clim, counts, used


def resolve_target(times, target: str | None):
    """Mes objetivo -> (mes 1-12, año, máscara de pasos, etiqueta).

    Si el mes pedido no está en el archivo se usa el último disponible.
    """
    month, year, valid = months_years(times)
    if not valid.any():
        print("AVISO: el archivo no tiene fechas válidas; se trata como un único mes.")
        return 1, 1970, np.ones(times.size, bool)
    t_month = np.full(times.size, np.datetime64("NaT", "M"), dtype="datetime64[M]")
    t_month[valid] = times[valid].astype("datetime64[M]")
    last = t_month[valid].max()
    want = np.datetime64(target, "M") if target else last
    if not (t_month == want).any():
        print(f"AVISO: no hay datos en {want}; se usa {last}.")
        want = last
    return (int(want.astype(int) % 12 + 1), int(want.astype(int) // 12 + 1970),
            t_month == want)


# ------------------------------------------------------------------- póster
def draw_poster(field, month_label, *, src_line="", data_line="", credit="",
                stride=1, center_lon=POSTER_LON, center_lat=POSTER_LAT,
                lon, lat, fig=None, size=POSTER_SIZE, dpi=POSTER_DPI):
    """Globo Orthographic con el campo y el estilo del póster de referencia.

    Si se pasa `fig`, se limpia y se redibuja encima (rotación de cámara).
    """
    if fig is None:
        fig = plt.figure(figsize=(size, size), dpi=dpi)
    fig.clf()
    fig.patch.set_facecolor(BG)

    ax = fig.add_axes([0.008, 0.05, 0.912, 0.94],
                      projection=ccrs.Orthographic(central_longitude=center_lon,
                                                   central_latitude=center_lat))
    ax.set_facecolor(BG)
    ax.set_global()
    ax.spines["geo"].set_visible(False)

    mesh = ax.pcolormesh(lon[::stride], lat[::stride], field[::stride, ::stride],
                         transform=ccrs.PlateCarree(), cmap=ANOM_CMAP,
                         vmin=ANOM_VMIN, vmax=ANOM_VMAX, shading="auto", zorder=2)
    ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=False,
                 linewidth=0.35, color=TXT, alpha=0.3, zorder=3)
    try:
        ax.add_feature(cfeature.COASTLINE.with_scale("110m"), linewidth=0.55,
                       edgecolor="black", zorder=4)
        ax.add_feature(cfeature.BORDERS.with_scale("110m"), linewidth=0.35,
                       edgecolor="black", zorder=4)
    except Exception as exc:                          # sin Natural Earth cacheado
        print(f"AVISO: costas/fronteras omitidas ({exc})")

    cax = fig.add_axes([0.096, 0.067, 0.812, 0.019])
    cbar = fig.colorbar(mesh, cax=cax, orientation="horizontal")
    cbar.outline.set_visible(False)
    cbar.set_ticks(np.arange(ANOM_VMIN, ANOM_VMAX + 1, 1.0))
    cbar.ax.tick_params(colors=TXT, length=3, width=0.8, labelsize=10.5, pad=3)

    fig.text(0.026, 0.985, month_label, color=TXT, fontsize=19,
             fontweight="bold", ha="left", va="top")
    fig.text(0.026, 0.950, "TEMPERATURE\nANOMALY", color=TXT_DIM, fontsize=16.5,
             fontweight="bold", ha="left", va="top", linespacing=0.82)
    fig.text(0.983, 0.983, credit, color=TXT_DIM, fontsize=5.8, ha="right", va="top")
    fig.text(0.096, 0.105, "°C", color=TXT, fontsize=24, fontweight="bold",
             ha="left", va="bottom")
    fig.text(0.026, 0.012, src_line, color=TXT_DIM, fontsize=7.4, ha="left", va="bottom")
    fig.text(0.980, 0.012, data_line, color=TXT_DIM, fontsize=7.4, ha="right", va="bottom")
    if credit:
        fig.text(0.5, 0.150, " ".join(credit.upper()), color=WM_COLOR, fontsize=8.5,
                 ha="center", va="bottom")
    return fig, ax, mesh


def main(argv=None):
    global ANOM_VMIN, ANOM_VMAX
    ap = argparse.ArgumentParser(
        description="Póster de anomalía de temperatura (estilo climatejulien) desde ERA5.")
    ap.add_argument("--nc", help="archivo ERA5 (.nc/.grib) a usar")
    ap.add_argument("--mes", help="mes a retratar, AAAA-MM (por defecto, el último del archivo)")
    ap.add_argument("--credito", default="Graphic by @tu_usuario",
                    help="texto del crédito (arriba a la derecha y marca de agua central)")
    ap.add_argument("--lat", type=float, default=POSTER_LAT, help="latitud central del globo")
    ap.add_argument("--lon", type=float, default=POSTER_LON, help="longitud central del globo")
    ap.add_argument("--vmin", type=float, default=ANOM_VMIN, help="mínimo de la escala (°C)")
    ap.add_argument("--vmax", type=float, default=ANOM_VMAX, help="máximo de la escala (°C)")
    ap.add_argument("--stride", type=int, default=1, help="submuestreo de la grilla en el PNG")
    ap.add_argument("--gif", action="store_true", help="además, GIF con el globo rotando 360°")
    ap.add_argument("--frames", type=int, default=36, help="frames del GIF")
    ap.add_argument("--fps", type=int, default=8, help="velocidad del GIF")
    ap.add_argument("--show", action="store_true", help="abrir la ventana al final")
    args = ap.parse_args(argv)

    ANOM_VMIN, ANOM_VMAX = args.vmin, args.vmax

    data_dir = Path(__file__).resolve().parent
    da, times, synthetic = load_field(data_dir, args.nc)
    tdim = "valid_time" if "valid_time" in da.dims else "time"
    to_c = lambda arr: np.asarray(arr, dtype=np.float64) - 273.15

    m_t, y_t, mask_t = resolve_target(times, args.mes)
    if mask_t.sum() == 0:
        raise SystemExit("No hay pasos para el mes objetivo.")

    clim, counts, used_years = month_climatology(da, tdim, times, exclude_years=(y_t,))
    if counts[m_t - 1] == 0:                    # no hay otros años con ese mes
        print(f"AVISO: sin otros años con {MONTHS_EN[m_t - 1].title()}; "
              "climatología con la serie completa.")
        clim, counts, used_years = month_climatology(da, tdim, times)

    field_c = to_c(mean_steps(da, tdim, np.flatnonzero(mask_t)))
    anom_c = field_c - to_c(clim[m_t - 1])
    clim_label = ", ".join(str(y) for y in sorted(used_years)) or "n/d"

    print(f"Mes: {MONTHS_EN[m_t - 1].title()} {y_t} | pasos promediados: {int(mask_t.sum())}")
    print(f"Climatología: {counts[m_t - 1]} pasos de {clim_label}"
          f" (el año objetivo se excluye)")
    print(f"Anomalía: min {np.nanmin(anom_c):+.1f} | max {np.nanmax(anom_c):+.1f} | "
          f"media {np.nanmean(anom_c):+.2f} °C")

    month_label = f"{MONTHS_EN[m_t - 1]} {y_t}"
    origen = "SINTÉTICO" if synthetic else "ERA5"
    src_line = (f"SOURCE: climate.copernicus.eu / {origen} | "
                f"MEDIA MENSUAL {MONTHS_EN[m_t - 1][:3]} {y_t}")
    data_line = (f"DATA: {origen}{' (PRELIMINAR)' if y_t >= 2026 and not synthetic else ''}"
                 f" | CLIMATOLOGÍA {clim_label} (DERIVADA DEL ARCHIVO)")

    fig, _, _ = draw_poster(anom_c, month_label, src_line=src_line, data_line=data_line,
                            credit=args.credito, stride=max(1, args.stride),
                            center_lon=args.lon, center_lat=args.lat,
                            lon=da.longitude.values, lat=da.latitude.values)
    png = data_dir / f"planeta_anomalia_{y_t}-{m_t:02d}.png"
    fig.savefig(png, facecolor=BG)
    print("PNG:", png)

    if args.gif:
        size, dpi = 7, 100
        stride = max(2, da.sizes["longitude"] // 720)      # grilla ~0.5° -> ágil
        gif_fig = plt.figure(figsize=(size, size), dpi=dpi)

        def update(frame):
            ang = frame * 360 / args.frames
            draw_poster(anom_c, month_label, src_line=src_line, data_line=data_line,
                        credit=args.credito, stride=stride, center_lon=ang,
                        center_lat=args.lat, lon=da.longitude.values,
                        lat=da.latitude.values, fig=gif_fig, size=size, dpi=dpi)
            return ()

        anim = animation.FuncAnimation(gif_fig, update, frames=args.frames,
                                       interval=1000 / args.fps, blit=False)
        gif = data_dir / "planeta_anomalia_rotando.gif"
        anim.save(gif, writer=animation.PillowWriter(fps=args.fps))
        plt.close(gif_fig)
        print("GIF:", gif)

    if args.show:
        plt.show()
    else:
        plt.close(fig)


if __name__ == "__main__":
    main()
