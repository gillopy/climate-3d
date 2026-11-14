"""Poster of the GOES-R ABI L2 Land Surface Temperature (LST 2 km full disk).

The ABI L2 LST product is **hourly** (one granule per hour, ~10 minutes of scan).
The `.nc` carries a packed `LST` variable (`scale_factor=0.0025`,
`add_offset=190`, so xarray returns Kelvin already unpacked) and a `DQF` quality
flag. A pixel is shown only when `LST` is not NaN and `DQF != 3` (3 = no
retrieval): the product only retrieves clear land, so open ocean and cloudy
pixels stay transparent, like the reference image.

The design is the one from `poster_goes_truecolor.py` (white page, inscribed
Orthographic globe, thin halo, no graticule), with a product-specific cold-to-warm
ramp and a two-scale legend: Fahrenheit above the bar, Celsius below it.

Reused from shared code (never modified here):

  * `poster_goes_truecolor` — `_orto_franja`, `_alfa`, `FILAS`, `dibujar`, `WHITE`.
  * `poster_goes_banda` — `_muestrear_banda`, `CORTE_PLANETA`.
  * `poster_goes_realista` — `radio_visible`.

`fecha_de` / `time_label_nc` from `poster_goes_realista` are not reused: they
parse the CMIP name with `goes_lectura.PATRON`, which does not match the
`OR_ABI-L2-LST2KMF-...` granule. This module parses the LST scan stamp itself and
formats the same `DD MON YYYY · HH:MM UTC-3` label.

Usage (from the project root):

    .venv\\Scripts\\python.exe prototipos\\poster_goes_lst.py
    .venv\\Scripts\\python.exe prototipos\\poster_goes_lst.py --desde 2026-11-13T22:00 --n 1
    .venv\\Scripts\\python.exe prototipos\\poster_goes_lst.py --px 1400 --out lst.png
    .venv\\Scripts\\python.exe prototipos\\poster_goes_lst.py --help   # no network
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
sys.path.insert(0, str(RAIZ / "prototipos"))

import poster_goes_truecolor as tc  # noqa: E402
from poster_goes_banda import CORTE_PLANETA, _muestrear_banda  # noqa: E402
from poster_goes_realista import radio_visible  # noqa: E402
from rutas import DATOS, SALIDAS  # noqa: E402

SAT = "G19"
PX = 2712
TOPE = 5424                       # native LST 2 km grid: 5424 x 5424
CENTRO = (-75.2, 0.0)
VMIN, VMAX = -53.0, 67.0          # degrees C, the reference image scale

#: Product ramp, cold to warm, in the exact order the spec fixes.
PALETA = (
    (0.00, "#2b2b9e"),
    (0.10, "#2f6fd0"),
    (0.20, "#37c8e8"),
    (0.32, "#5fd48a"),
    (0.44, "#b7e05a"),
    (0.54, "#f2e04e"),
    (0.66, "#f5a53c"),
    (0.78, "#ec6a2f"),
    (0.88, "#d4342a"),
    (1.00, "#8f1212"),
)

#: LST scan stamp: `s20263172200207` -> 2026, day 317, 22:00:20.7 UTC.
_PATRON_LST = re.compile(r"_s(\d{4})(\d{3})(\d{2})(\d{2})(\d{2})")

_CMAP = None


def carpeta(sat: str = SAT) -> Path:
    """Data folder of the product: ``goes_lst_<sat>`` under ``comun.rutas.DATOS``."""
    return DATOS / f"goes_lst_{sat.lower()}"


def fecha_de(nc: Path) -> datetime | None:
    """Scan hour (UTC) parsed from the LST granule name, or None if it is not one."""
    match = _PATRON_LST.search(Path(nc).name)
    if not match:
        return None
    anio, dia, hora, minuto = (int(g) for g in match.groups()[:4])
    return datetime(anio, 1, 1) + timedelta(days=dia - 1, hours=hora, minutes=minuto)


def time_label_nc(nc: Path) -> str:
    """Slot label in UTC-3, the same format as the other posters."""
    meses = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN",
             "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
    t = (fecha_de(nc) or datetime.fromtimestamp(Path(nc).stat().st_mtime))
    t = t - timedelta(hours=3)
    return f"{t.day:02d} {meses[t.month - 1]} {t.year} \u00b7 {t:%H:%M} UTC-3"


def slots(sat: str, desde: datetime | None, n: int, paso: int,
          ultimos: int = 0) -> list[tuple[datetime, Path]]:
    """LST granules on disk, hourly.

    - `ultimos > 0`: the N newest, ending at the newest one on disk.
    - `desde`: the series starting at that instant.
    - neither: the last frame.
    """
    encontrados: dict[datetime, Path] = {}
    for archivo in carpeta(sat).glob("*.nc"):
        instante = fecha_de(archivo)
        if instante is not None:
            encontrados[instante] = archivo
    if not encontrados:
        raise SystemExit(
            f"No LST .nc for {sat} in {carpeta(sat)}. "
            "Download them with descargar/descargar_goes_lst.py."
        )
    if ultimos > 0:
        n = ultimos
        t0 = max(encontrados) - timedelta(minutes=paso * (ultimos - 1))
    else:
        t0 = desde or max(encontrados)
    lista: list[tuple[datetime, Path]] = []
    for i in range(n):
        instante = t0 + timedelta(minutes=paso * i)
        if instante in encontrados:
            lista.append((instante, encontrados[instante]))
    if not lista:
        raise SystemExit(f"No .nc for any requested slot from {t0:%Y-%m-%d %H:%M} UTC.")
    return lista


def _lut() -> np.ndarray:
    """Dip the product ramp into a lookup table (nearest index per pixel)."""
    global _CMAP
    if _CMAP is None:
        from matplotlib.colors import LinearSegmentedColormap

        _CMAP = LinearSegmentedColormap.from_list("goes_lst", PALETA, N=512)
    n = int(getattr(_CMAP, "N", 256))
    return (np.asarray(_CMAP(np.linspace(0.0, 1.0, n)))[:, :3] * 255.0).astype(np.uint8)


def _campo_lst(nc: Path, tope: int):
    """LST in degrees C plus its scan grid; NaN where there is no good retrieval.

    xarray unpacks `scale_factor` / `add_offset` and turns `_FillValue` into NaN
    on open. A pixel is valid only when `LST` is finite and `DQF != 3`.
    """
    import xarray as xr

    with xr.open_dataset(nc, engine="h5netcdf") as ds:
        gp = ds["goes_imager_projection"].attrs
        h = float(gp["perspective_point_height"])
        lon0 = float(gp["longitude_of_projection_origin"])
        alto, ancho = ds["LST"].shape
        paso = max(1, int(np.ceil(max(alto, ancho) / tope))) if tope else 1
        x = ds["x"].values[::paso] * h
        y = ds["y"].values[::paso] * h
        lst = np.asarray(ds["LST"].values[::paso, ::paso], dtype=np.float32)
        dqf = np.asarray(ds["DQF"].values[::paso, ::paso], dtype=np.float32)

    valido = np.isfinite(lst) & (dqf != 3)
    campo = np.where(valido, lst - 273.15, np.nan).astype(np.float32)
    del lst, dqf, valido
    return campo, x, y, h, lon0


def componer_lst(nc: Path, args) -> tuple[np.ndarray, float, dict]:
    """LST granule -> RGBA of the Orthographic globe, with the true color geometry."""
    campo, x, y, h, lon0 = _campo_lst(nc, args.tope)

    finitos = np.isfinite(campo)
    datos = campo[finitos]
    if datos.size:
        estadisticas = {
            "min": float(datos.min()),
            "mean": float(datos.mean()),
            "max": float(datos.max()),
        }
    else:
        estadisticas = {"min": float("nan"), "mean": float("nan"), "max": float("nan")}
    cobertura = float(datos.size) / float(campo.size) if campo.size else 0.0
    del datos, finitos

    escala, _h, _lon0 = radio_visible(nc, tuple(args.centro), args.recorte)
    lut = _lut()
    px = args.px
    centro = tuple(args.centro)

    rgb = np.zeros((px, px, 3), dtype=np.uint8)
    alfa = np.zeros((px, px), dtype=np.uint8)
    validos = 0

    for f0 in range(0, px, tc.FILAS):
        f1 = min(f0 + tc.FILAS, px)
        lon, lat, rho, dentro = tc._orto_franja(px, escala, centro, f0, f1)
        valores = _muestrear_banda(campo, x, y, lon0, h, lon, lat)
        a = tc._alfa(rho, px, escala) * dentro
        # The planet edge, not the frame: same analytic 1.5 px ramp as the RGBs.
        a = a * tc._alfa(rho, px, 1.0 / CORTE_PLANETA)

        normalizado = np.clip((valores - args.vmin) / (args.vmax - args.vmin), 0.0, 1.0)
        # NaN (no retrieval) must not reach the integer cast: quiet it first.
        normalizado = np.nan_to_num(normalizado, nan=0.0)
        n = len(lut)
        indice = (normalizado * (n - 1)).astype(np.uint16 if n > 256 else np.uint8)
        bloque = lut[indice]
        bloque[~np.isfinite(valores)] = 0

        rgb[f0:f1] = bloque
        alfa[f0:f1] = (a * 255.0).astype(np.uint8)
        validos += int(np.count_nonzero(np.isfinite(valores) & (a > 0)))
        print(f"  strip {f1:5d}/{px}", flush=True)

    # No bright rim: bilinear display instead of lanczos (no overshoot).
    args.interp = "bilinear"
    stats = {"px": px, "validos": validos, "cobertura": cobertura, **estadisticas}
    return np.dstack([rgb, alfa]), escala, stats


def _numero(v: float) -> str:
    """Number with a typographic minus, like the other poster legends."""
    return f"{v:g}".replace("-", "\u2212")


def _leyenda(fig, args) -> None:
    """Two-scale horizontal legend: Fahrenheit above, Celsius below the bar."""
    if args.limpio:
        return
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize

    _lut()  # make sure the product ramp is built before the legend samples it
    cax = fig.add_axes([0.615, 0.965, 0.325, 0.009], zorder=9)
    sm = plt.cm.ScalarMappable(norm=Normalize(args.vmin, args.vmax), cmap=_CMAP)
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=cax, orientation="horizontal")
    cbar.outline.set_visible(False)

    ticks = []
    valor = args.vmin
    while valor <= args.vmax + 1e-9:
        ticks.append(valor)
        valor += 20.0
    cbar.set_ticks(ticks)
    celsius = [
        f"{_numero(t)} \u00b0C" if i == len(ticks) - 1 else _numero(t)
        for i, t in enumerate(ticks)
    ]
    cbar.set_ticklabels(celsius)
    cbar.ax.tick_params(length=0, labelsize=8.2, colors=tc.INK_SOFT, pad=3)
    for etiqueta in cbar.ax.get_xticklabels():
        etiqueta.set_fontfamily("Segoe UI")

    for i, t in enumerate(ticks):
        fahrenheit = int(np.floor(t * 9.0 / 5.0 + 32.0))
        texto = (f"{_numero(fahrenheit)} \u00b0F" if i == len(ticks) - 1
                 else _numero(fahrenheit))
        cbar.ax.text(t, 1.65, texto, transform=cbar.ax.get_xaxis_transform(),
                     ha="center", va="bottom", fontsize=8.0, color=tc.INK_SOFT,
                     fontfamily="Segoe UI", clip_on=False)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Poster of the ABI L2 Land Surface Temperature (LST 2 km full "
                    "disk) with the true color design.")
    ap.add_argument("--sat", default=SAT, help=f"satellite (default {SAT})")
    ap.add_argument("--desde", help="UTC slot ISO (default: the last .nc on disk)")
    ap.add_argument("--n", type=int, default=1, help="number of frames")
    ap.add_argument("--paso", type=int, default=60,
                    help="minutes between frames (default 60: LST is hourly)")
    ap.add_argument("--ultimos", type=int, default=0, metavar="N",
                    help="the N newest .nc on disk (ignores --desde)")
    ap.add_argument("--px", type=int, default=PX,
                    help=f"globe diameter in px (default {PX})")
    ap.add_argument("--dpi", type=int, help="dpi; inferred from --px when omitted")
    ap.add_argument("--tope", type=int, default=TOPE,
                    help=f"source grid of the field (default {TOPE}, native 2 km)")
    ap.add_argument("--centro", nargs=2, type=float, metavar=("LON", "LAT"),
                    default=list(CENTRO), help="globe center")
    ap.add_argument("--recorte", type=float, default=1.0,
                    help="fraction of the visible radius (1 = full disk)")
    ap.add_argument("--vmin", type=float, default=VMIN, help="scale minimum in C")
    ap.add_argument("--vmax", type=float, default=VMAX, help="scale maximum in C")
    ap.add_argument("--titulo", default=None, help="poster title")
    ap.add_argument("--fuente", default=None, help="source line at the bottom")
    ap.add_argument("--credito", default="Graphic by @Gillo97")
    ap.add_argument("--limpio", action="store_true",
                    help="clean capture: no titles, credits, halo or edge shading")
    ap.add_argument("--lineas", action=argparse.BooleanOptionalAction, default=False,
                    help="graticule and coastlines (default: off)")
    ap.add_argument("--fronteras", action=argparse.BooleanOptionalAction, default=False,
                    help="dotted political borders (default: off)")
    ap.add_argument("--borde", nargs="?", const="", default="",
                    help="highlighted outline over the globe (empty = none)")
    ap.add_argument("--sombra-borde", type=float, default=0.0,
                    help="edge shading depth 0..0.8 (default 0: keep the values)")
    ap.add_argument("--out", help="output PNG")
    ap.add_argument("--frames", help="frame folder: render a numbered series")
    ap.add_argument("--forzar", action="store_true", help="redo existing frames")
    args = ap.parse_args(argv)

    args.titulo = args.titulo or f"{args.sat} \u00b7 LST \u00b7 SURFACE TEMPERATURE"
    args.fuente = args.fuente or (
        f"SOURCE: NOAA/NESDIS {args.sat} ABI L2 LST | 2 KM FULL DISK"
    )

    desde = datetime.fromisoformat(args.desde) if args.desde else None
    lista = slots(args.sat, desde, args.n, args.paso, args.ultimos)

    if args.frames:
        salida = Path(args.frames)
        salida.mkdir(parents=True, exist_ok=True)
        print(f"{len(lista)} frames -> {salida}", flush=True)
        for i, (instante, nc) in enumerate(lista, 1):
            destino = salida / f"cuadro_{i:03d}.png"
            if destino.exists() and not args.forzar:
                continue
            disco, escala, _ = componer_lst(nc, args)
            fig = tc.dibujar(disco, escala, args.titulo, time_label_nc(nc),
                             args.fuente, args, args.px)
            _leyenda(fig, args)
            parcial = destino.with_suffix(".png.parcial")
            fig.savefig(parcial, format="png", facecolor=tc.WHITE)
            import matplotlib.pyplot as plt
            plt.close(fig)
            parcial.replace(destino)
            print(f"  [{i}/{len(lista)}] {instante:%Y-%m-%d %H:%M} UTC", flush=True)
        print(f"Frames in {salida}")
        return 0

    instante, nc = lista[0]
    print(f"{nc.name}\nslot: {instante:%Y-%m-%d %H:%M} UTC | globe {args.px} px | "
          f"center {tuple(args.centro)} | scale {args.vmin:g} to {args.vmax:g} C",
          flush=True)
    disco, escala, stats = componer_lst(nc, args)
    print(f"globe {stats['px']} px | {stats['validos']:,} px with data")
    print(f"field {stats['min']:.1f} to {stats['max']:.1f} C | "
          f"mean {stats['mean']:.1f} C | {stats['cobertura'] * 100.0:.1f} % of the grid")

    fig = tc.dibujar(disco, escala, args.titulo, time_label_nc(nc), args.fuente,
                     args, args.px)
    _leyenda(fig, args)
    out = Path(args.out) if args.out else (
        SALIDAS / f"poster_{args.sat}_LST_{instante:%Y-%m-%dT%H%M}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    parcial = out.with_suffix(".png.parcial")
    fig.savefig(parcial, format="png", facecolor=tc.WHITE)
    import matplotlib.pyplot as plt
    plt.close(fig)
    parcial.replace(out)
    print(f"PNG: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
