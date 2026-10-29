"""Póster de color real de **PACE / OCI** desde un L3M SFREFL (RHOS).

Archivo NUEVO. No toca nada del pipeline de GOES ni del de follaje.

Qué cambia respecto de GOES:

  * OCI **sí tiene banda verde real** (555 nm). El RGB es (670, 555, 443) medido, sin
    la síntesis 0.45·rojo + 0.10·veggie + 0.45·azul que necesita el ABI.
  * ``rhos`` ya viene corregido por Rayleigh, así que no hace falta pedestal
    atmosférico: se usa la reflectancia tal cual, sólo con estirado y gamma.
  * PACE es polar (676 km) y su compuesto L3M es una grilla lat/lon equirectangular,
    no un disco geoestacionario. El globo se arma reproyectando esa grilla.

Los huecos (NaN) son datos que no existen: nubes o falta de cobertura. En un compuesto
diario son ~62 % del planeta; en 8 días, ~23 %. Sobre fondo negro se leen como zonas
sin dato, no como un error de render.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe prototipos\\poster_pace.py --nc "...\\PACE_OCI...nc"
    .venv\\Scripts\\python.exe prototipos\\poster_pace.py --help   # no toca la red
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from rutas import SALIDAS  # noqa: E402

# Longitudes de OCI para el color real (nm). Se busca la más cercana en el eje
# `wavelength`, que trae 122 longitudes de 346 a 2258 nm.
BANDAS = {"rojo": 670.0, "verde": 555.0, "azul": 443.0}

PX = 2000
CENTRO = (-58.0, -10.0)      # América del Sur y el Atlántico, como la referencia de NASA
SATURACION = 1.10
GAMMA = 0.85
PCT_LO, PCT_HI = 0.5, 99.5

BG = "#000000"
INK = "#f2f5f8"
INK_SOFT = "#b9c1c9"
INK_FAINT = "#7e8790"
CREDITO = "Graphic by @Gillo97"


# ------------------------------------------------------------------------ lectura
def cargar_bandas(nc: Path) -> tuple[dict, np.ndarray, np.ndarray, str]:
    """Reflectancias de las tres longitudes de color, lat y lon.

    ``rhos`` tiene forma (lat, lon, wavelength): se lee una sola longitud por vez para
    no traer los 122 canales a memoria.
    """
    import xarray as xr

    with xr.open_dataset(nc, engine="h5netcdf") as ds:
        wl = ds["wavelength"].values
        bandas = {}
        for nombre, objetivo in BANDAS.items():
            i = int(np.abs(wl - objetivo).argmin())
            bandas[nombre] = np.asarray(ds["rhos"].isel(wavelength=i).values,
                                        dtype=np.float32)
            print(f"  {nombre}: {wl[i]:.0f} nm (índice {i})")
        lat = np.asarray(ds["lat"].values, dtype=np.float64)
        lon = np.asarray(ds["lon"].values, dtype=np.float64)
        rango = ""
        if "time_coverage_start" in ds.attrs:
            rango = f"{ds.attrs['time_coverage_start'][:10]} a {ds.attrs.get('time_coverage_end', '')[:10]}"
        elif "temporal_range" in ds.attrs:
            rango = ds.attrs["temporal_range"]
    return bandas, lat, lon, rango


# ------------------------------------------------------------------------ geometría
def ortho_inverso(px: int, escala: float, centro: tuple[float, float]):
    """(lon, lat, rho, dentro) por píxel del disco.

    Misma proyección inversa que ``poster_goes_realista._orto_inverso``: acá el origen
    es una grilla lat/lon, así que sirve tal cual.
    """
    lon0, lat0 = np.radians(centro[0]), np.radians(centro[1])
    y = np.linspace(1.0, -1.0, px)
    x = np.linspace(-1.0, 1.0, px)
    X, Y = np.meshgrid(x, y)
    rho = np.hypot(X, Y)
    dentro = rho <= 1.0
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


def muestrear(campo, lat_vals, lon_vals, lon, lat):
    """Bilineal sobre la grilla equirectangular; NaN fuera del rango o sin dato."""
    alto, ancho = campo.shape
    dlat = lat_vals[0] - lat_vals[1]          # positivo: lat decrece con la fila
    dlon = lon_vals[1] - lon_vals[0]
    fila = (lat_vals[0] - lat) / dlat
    col = (lon - lon_vals[0]) / dlon

    ok = (fila >= 0) & (fila <= alto - 1) & (np.abs(lat) <= 89.95)
    col = np.mod(col, ancho)
    c0 = np.clip(np.floor(col).astype(np.intp), 0, ancho - 1)
    c1 = (c0 + 1) % ancho
    f0 = np.clip(np.floor(fila).astype(np.intp), 0, alto - 2)
    fc = np.clip(col - c0, 0.0, 1.0).astype(np.float32)
    ff = np.clip(fila - f0, 0.0, 1.0).astype(np.float32)

    v00, v01 = campo[f0, c0], campo[f0, c1]
    v10, v11 = campo[f0 + 1, c0], campo[f0 + 1, c1]
    valores = ((v00 * (1 - fc) + v01 * fc) * (1 - ff)
               + (v10 * (1 - fc) + v11 * fc) * ff)
    # Si algún vecino es NaN, el píxel cae en el borde de un hueco: se descarta.
    valido = np.isfinite(v00) & np.isfinite(v01) & np.isfinite(v10) & np.isfinite(v11)
    return np.where(ok & valido, valores, np.nan).astype(np.float32)


# ------------------------------------------------------------------------ color
def componer(bandas: dict, lat_vals, lon_vals, escala, centro, px, args):
    """Tres reflectancias -> RGBA del disco (sin síntesis de verde)."""
    lon, lat, rho, dentro = ortho_inverso(px, escala, centro)
    rgb = {}
    for nombre in ("rojo", "verde", "azul"):
        rgb[nombre] = muestrear(bandas[nombre], lat_vals, lon_vals, lon, lat)
    del lon, lat

    valido = np.isfinite(rgb["rojo"]) & np.isfinite(rgb["verde"]) & np.isfinite(rgb["azul"])
    if not np.any(valido):
        raise SystemExit("El disco no tiene ni un píxel válido para ese centro.")
    print(f"  disco: {valido.mean() * 100:.1f} % con dato")

    # rhos ya viene corregido por Rayleigh: sólo estirado por luminancia compartida.
    pila = np.dstack([rgb["rojo"], rgb["verde"], rgb["azul"]]).astype(np.float32)
    lum = 0.2126 * pila[..., 0] + 0.7152 * pila[..., 1] + 0.0722 * pila[..., 2]
    muestra = lum[valido]
    lo, hi = np.percentile(muestra, [args.pct_lo, args.pct_hi])
    pila = (pila - float(lo)) / max(float(hi) - float(lo), 1e-6)

    lum = 0.2126 * pila[..., 0] + 0.7152 * pila[..., 1] + 0.0722 * pila[..., 2]
    pila = lum[..., None] + (pila - lum[..., None]) * args.saturacion
    pila = np.clip(pila, 0.0, 1.0) ** args.gamma
    pila = np.nan_to_num(pila, nan=0.0)

    rgb8 = np.clip(pila * 255.0, 0, 255).astype(np.uint8)
    # Alfa con el borde del disco suavizado (el disco es un círculo geométrico).
    alfa = np.clip((1.0 - rho) * (px / 2.0) / 1.5, 0.0, 1.0) * dentro
    alfa = (alfa * 255).astype(np.uint8)
    return np.dstack([rgb8, alfa]), valido


# ------------------------------------------------------------------------ figura
def dibujar(disco, titulo, subtitulo, fuente, args, px):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"]})
    lado_in = 10.4
    disco_in = 0.97 * lado_in
    dpi = args.dpi or (px / disco_in)
    g = disco_in / lado_in
    fig = plt.figure(figsize=(lado_in, lado_in), dpi=dpi)
    fig.patch.set_facecolor(BG)

    ax = fig.add_axes([(1 - g) / 2, (1 - g) / 2, g, g])
    ax.set_xlim(-1.0, 1.0)
    ax.set_ylim(-1.0, 1.0)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_facecolor("none")
    ax.imshow(disco, origin="upper", extent=[-1, 1, -1, 1],
              interpolation="none", zorder=2)

    fig.text(0.016, 0.984, titulo, ha="left", va="top", fontsize=13.0, color=INK,
             fontfamily="Segoe UI")
    fig.text(0.016, 0.957, subtitulo.upper(), ha="left", va="top", fontsize=8.6,
             color=INK_SOFT, fontfamily="Segoe UI")
    fig.text(0.016, 0.016, fuente, ha="left", va="bottom", fontsize=7.4,
             color=INK_FAINT, fontfamily="Segoe UI")
    if args.credito:
        fig.text(0.984, 0.016, args.credito, ha="right", va="bottom", fontsize=7.8,
                 color=INK_FAINT, fontfamily="Segoe UI")
    return fig


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Póster de color real de PACE/OCI desde un L3M SFREFL (rhos).")
    ap.add_argument("--nc", required=True, help="archivo L3M SFREFL .nc")
    ap.add_argument("--px", type=int, default=PX, help=f"diámetro del globo (default {PX})")
    ap.add_argument("--dpi", type=int, default=None, help="dpi; si se omite se deduce de --px")
    ap.add_argument("--centro", nargs=2, type=float, metavar=("LON", "LAT"),
                    default=list(CENTRO), help=f"centro del globo (default {CENTRO})")
    ap.add_argument("--escala", type=float, default=1.0,
                    help="seno del ángulo central en el borde: 1 = hemisferio completo")
    ap.add_argument("--saturacion", type=float, default=SATURACION)
    ap.add_argument("--gamma", type=float, default=GAMMA)
    ap.add_argument("--pct-lo", type=float, default=PCT_LO)
    ap.add_argument("--pct-hi", type=float, default=PCT_HI)
    ap.add_argument("--credito", default=CREDITO)
    ap.add_argument("--out", help="PNG de salida")
    args = ap.parse_args(argv)

    nc = Path(args.nc)
    print(f"{nc.name} ({nc.stat().st_size / 1e6:.0f} MB)")
    bandas, lat_vals, lon_vals, rango = cargar_bandas(nc)

    disco, valido = componer(bandas, lat_vals, lon_vals, args.escala,
                             tuple(args.centro), args.px, args)

    titulo = "PACE · OCI true color"
    subtitulo = f"{rango} · 670/555/443 nm · L3M SFREFL (rhos)"
    fuente = "SOURCE: NASA PACE OCI L3M SFREFL V3.1 (OB.DAAC) · B1+B2+B3 REALES"
    fig = dibujar(disco, titulo, subtitulo, fuente, args, args.px)

    out = Path(args.out) if args.out else (
        SALIDAS / f"poster_PACE_truecolor_{datetime.now():%Y-%m-%dT%H%M}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    parcial = out.with_suffix(".png.parcial")
    fig.savefig(parcial, format="png", facecolor=BG)
    import matplotlib.pyplot as plt
    plt.close(fig)
    parcial.replace(out)
    print(f"PNG: {out}  ({out.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
