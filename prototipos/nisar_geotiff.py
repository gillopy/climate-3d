"""Exporta un recorte NISAR GCOV como GeoTIFF georreferenciado (sin GDAL).

La banda sale en la UTM de la escena, norte arriba, float32. En modo ``db``
guarda 10*log10(potencia); en ``lineal`` guarda la potencia gamma0 original.
Ademas deja un PNG de vista previa y un JSON con la metadata.

    .venv\\Scripts\\python.exe prototipos\\nisar_geotiff.py --h5 ESCENA.h5 \
        --bbox -55.6,-24.5,-55.2,-23.9 --pol hv --px 2400 --out recorte.tif
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))

import nisar  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--h5", required=True)
    ap.add_argument("--bbox", required=True)
    ap.add_argument("--pol", default="auto", choices=("auto", "hh", "hv", "vv", "vh"))
    ap.add_argument("--px", type=int, default=2400)
    ap.add_argument("--modo", default="db", choices=("db", "lineal"))
    ap.add_argument("--out", required=True, help="ruta del .tif")
    ap.add_argument("--geojson", default=None)
    args = ap.parse_args()

    px = max(800, min(int(args.px), 4096))
    salida = Path(args.out)
    if salida.suffix.lower() not in (".tif", ".tiff"):
        salida = salida.with_suffix(".tif")
    preview = salida.with_name(salida.stem + "_preview.png")

    print(f"abriendo {Path(args.h5).name}")
    with nisar.Escena(args.h5) as escena:
        pol = args.pol.upper() if args.pol != "auto" else "auto"
        if pol == "auto":
            pol = "HV" if "HV" in escena.pols else (escena.pols[0] if escena.pols else "")
        if pol not in escena.pols:
            raise SystemExit(
                f"La escena no tiene {pol}; tiene {', '.join(escena.pols) or 'ninguna'}."
            )

        recorte = escena.recortar(pol, args.bbox, px)
        datos, xs, ys = nisar.orientar(recorte)
        mpp_x = abs(float(xs[-1] - xs[0])) / max(1, len(xs) - 1)
        mpp_y = abs(float(ys[0] - ys[-1])) / max(1, len(ys) - 1)
        if args.modo == "db":
            banda = nisar.a_db(datos)
        else:
            banda = np.asarray(datos, dtype=np.float32)

        nisar.guardar_geotiff(
            salida,
            banda,
            x0=float(xs[0]) - mpp_x / 2.0,
            y1=float(ys[0]) + mpp_y / 2.0,
            mpp_x=mpp_x,
            mpp_y=mpp_y,
            epsg=recorte.epsg,
            descripcion=f"NISAR GCOV {pol} {args.modo} EPSG:{recorte.epsg}",
        )

        # Vista previa en dB, siempre; el GeoTIFF puede ser lineal.
        db = nisar.a_db(datos)
        vmin, vmax = nisar.limites(db)
        rgb = nisar.paleta("gray", nisar.normalizar(db, vmin, vmax))
        rgb = np.where(np.isfinite(db)[..., None], rgb, 0)
        lineas = [
            f"NISAR GCOV · {pol} · GeoTIFF ({args.modo}) · {escena.fecha or escena.ruta.stem}",
            f"dB {vmin:.1f} a {vmax:.1f} · {mpp_x:.0f} m/px · EPSG:{recorte.epsg}",
            "gris = dB (vista previa) · el .tif tiene los datos",
        ]
        ancho, alto = nisar.guardar(
            rgb,
            preview,
            lineas,
            mpp_x,
            px,
            geojson=args.geojson,
            epsg=recorte.epsg,
            x0=recorte.x0,
            x1=recorte.x1,
            y0=recorte.y0,
            y1=recorte.y1,
        )
        meta = {
            "producto": "geotiff",
            "escena": escena.ruta.stem,
            "fecha": escena.fecha,
            "track": escena.track,
            "frame": escena.frame,
            "polarizacion": pol,
            "modo": args.modo,
            "bbox": [float(v) for v in args.bbox.split(",")],
            "epsg": recorte.epsg,
            "mpp": [round(mpp_x, 3), round(mpp_y, 3)],
            "forma": [int(banda.shape[0]), int(banda.shape[1])],
            "geotiff": str(salida),
            "preview": str(preview),
            "preview_px": [ancho, alto],
        }
        nisar.guardar_json(salida, meta)

    print(f"GeoTIFF: {salida}")
    print(f"preview: {preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
