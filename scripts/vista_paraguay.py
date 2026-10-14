"""Cuadro fijo del globo G19 C13 centrado en Paraguay (vista giro7).

Reproduce el encuadre aprobado: Orthographic con centro en lon -73, lat -18,
paleta IR con realce, borde de Paraguay (GADM) y sin grilla ni recortes.

Uso (desde la carpeta del proyecto):

    .venv\\Scripts\\python.exe vista_paraguay.py
    .venv\\Scripts\\python.exe vista_paraguay.py --nc OR_ABI-L2-CMIPF-M6C13_G19_....nc
    .venv\\Scripts\\python.exe vista_paraguay.py --lon -70 --lat -20
    .venv\\Scripts\\python.exe vista_paraguay.py --show

Salida: vista_paraguay_<AAAA-MM-DDTHHMM>.png (tamaño completo, 1176 px).
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

import cartopy.crs as ccrs
import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "lib"))
from poster_goes import (BG, PALETTES, caption_lines, draw_goes_poster,
                         to_display)

DATOS_D = Path(r"D:\Users\guill\dataset era5\goes_c13_g19")
SALIDAS_D = Path(r"D:\Users\guill\dataset era5\salidas")
CENTRO_LON, CENTRO_LAT = -73.0, -18.0
GEOJSON = str(RAIZ / "datos" / "paraguay_gadm.json")
PALETA = "ir_realce"
CREDITO = "Graphic by @tu_usuario"


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Cuadro fijo del globo G19 C13 centrado en Paraguay.")
    ap.add_argument("--nc", help="archivo ABI L2 CMIP (.nc) a usar")
    ap.add_argument("--lon", type=float, default=CENTRO_LON,
                    help="longitud del centro Orthographic")
    ap.add_argument("--lat", type=float, default=CENTRO_LAT,
                    help="latitud del centro Orthographic")
    ap.add_argument("--credito", default=CREDITO)
    ap.add_argument("--show", action="store_true", help="abrir la ventana al final")
    args = ap.parse_args(argv)

    if args.nc:
        nc = Path(args.nc)
        if not nc.exists():
            raise SystemExit(f"No existe el archivo indicado: {nc}")
    else:
        candidatos = sorted(DATOS_D.glob("*.nc"))
        if not candidatos:
            raise SystemExit("No hay archivos .nc en D:\\Users\\guill\\dataset era5\\goes_c13_g19 "
                             "(pasá uno con --nc).")
        nc = max(candidatos, key=lambda p: p.stat().st_size)

    ds = xr.open_dataset(nc)
    cmi = ds["CMI"]
    paso = max(1, int(np.ceil(max(cmi.shape) / 1200)))
    crudo = np.asarray(cmi.values[::paso, ::paso], dtype=np.float64)
    campo, unidad, tipo = to_display(crudo, cmi)
    gp = ds["goes_imager_projection"].attrs
    h = float(gp["perspective_point_height"])
    x = ds["x"].values[::paso] * h
    y = ds["y"].values[::paso] * h
    proj = ccrs.Geostationary(
        central_longitude=float(gp["longitude_of_projection_origin"]),
        satellite_height=h, sweep_axis=str(gp.get("sweep_angle_axis", "x")))
    titulo, subtitulo, fuente, datos = caption_lines(ds, cmi, tipo, "FULL DISK")
    lo, hi = np.nanpercentile(campo, [0.5, 99.5])

    fig, _, _ = draw_goes_poster(
        campo, x=x, y=y, proj=proj, title=titulo, subtitle=subtitulo,
        unit_label=unidad, src_line=fuente, data_line=datos, credit=args.credito,
        cmap=PALETTES[PALETA], vmin=float(lo), vmax=float(hi),
        highlight_geojson=GEOJSON,
        globe_center=(args.lon, args.lat))
    t = np.datetime64(ds["t"].values) if "t" in ds else None
    sello = np.datetime_as_string(t, unit="m").replace(":", "") if t is not None else "sin-fecha"
    SALIDAS_D.mkdir(parents=True, exist_ok=True)
    out = SALIDAS_D / f"vista_paraguay_{sello}.png"
    fig.savefig(out, facecolor=BG)
    print("PNG:", out)

    if args.show:
        plt.show()
    else:
        plt.close(fig)


if __name__ == "__main__":
    main()
