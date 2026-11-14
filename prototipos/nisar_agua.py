"""Agua / inundación en una escena NISAR GCOV.

El agua abierta es oscura en HH y HV (scattering especular). Con dos umbrales en
dB se arma una máscara de agua, se limpia con una mayoría 3×3 y se superpone en
azul sobre la imagen HH. También reporta hectáreas y el porcentaje del área.

Ojo: el bosque inundado puede BRILLAR en HH por doble rebote; este producto está
pensado para agua abierta, no para anegamiento bajo dosel.

    .venv\\Scripts\\python.exe prototipos\\nisar_agua.py --h5 ESCENA.h5 \
        --bbox -55.6,-24.5,-55.2,-23.9 --px 1400 --out agua.png
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
    ap.add_argument("--px", type=int, default=1400)
    ap.add_argument("--hh-max", type=float, default=-20.0, help="umbral de agua en HH (dB)")
    ap.add_argument("--hv-max", type=float, default=-25.0, help="umbral de agua en HV (dB)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--geojson", default=None)
    args = ap.parse_args(nisar.argv_bbox(sys.argv[1:]))

    px = max(800, min(int(args.px), 4096))
    salida = Path(args.out)
    hh_max = float(args.hh_max)
    hv_max = float(args.hv_max)

    print(f"abriendo {Path(args.h5).name}")
    with nisar.Escena(args.h5) as escena:
        if "HH" not in escena.pols or "HV" not in escena.pols:
            raise SystemExit(
                f"Agua necesita HH y HV; la escena tiene {', '.join(escena.pols) or 'ninguna'}."
            )
        rec_hh = escena.recortar("HH", args.bbox, px)
        rec_hv = escena.recortar("HV", args.bbox, px)
        if not nisar.compatibles(rec_hh, rec_hv):
            raise SystemExit("HH y HV no comparten grilla en esta escena.")

        hh, xs, ys = nisar.orientar(rec_hh)
        hv, _, _ = nisar.orientar(rec_hv)
        db_hh = nisar.a_db(hh)
        db_hv = nisar.a_db(hv)
        valido = np.isfinite(db_hh) & np.isfinite(db_hv)
        agua = nisar.mayoria3(
            valido & (db_hh < hh_max) & (db_hv < hv_max)
        ) & valido

        mpp_x = abs(float(xs[-1] - xs[0])) / max(1, len(xs) - 1)
        mpp_y = abs(float(ys[0] - ys[-1])) / max(1, len(ys) - 1)
        mpp = mpp_x
        agua_px = int(agua.sum())
        valido_px = int(valido.sum())
        if valido_px == 0:
            raise SystemExit("La caja no tiene píxeles válidos.")
        agua_ha = nisar.hectareas(agua_px, mpp_x, mpp_y)
        area_ha = nisar.hectareas(valido_px, mpp_x, mpp_y)
        agua_pct = 100.0 * agua_px / valido_px
        hh_media = float(np.nanmean(db_hh[agua])) if agua_px else 0.0
        hv_media = float(np.nanmean(db_hv[agua])) if agua_px else 0.0

        vmin, vmax = nisar.limites(db_hh)
        rgb = nisar.paleta("gray", nisar.normalizar(db_hh, vmin, vmax))
        rgb = np.where(valido[..., None], rgb, 0)
        rgb = np.where(
            agua[..., None],
            np.array([25, 105, 220], dtype=np.uint8),
            rgb,
        )
        lineas = [
            f"NISAR GCOV · agua · {escena.fecha or escena.ruta.stem}",
            f"agua {agua_ha:.0f} ha ({agua_pct:.1f}%) · HH<{hh_max:g} · "
            f"HV<{hv_max:g} dB · {mpp:.0f} m/px · EPSG:{rec_hh.epsg}",
            "azul = agua abierta (HH y HV bajos)",
        ]
        ancho, alto = nisar.guardar(
            rgb,
            salida,
            lineas,
            mpp,
            px,
            geojson=args.geojson,
            epsg=rec_hh.epsg,
            x0=rec_hh.x0,
            x1=rec_hh.x1,
            y0=rec_hh.y0,
            y1=rec_hh.y1,
        )
        meta = {
            "producto": "agua",
            "escena": escena.ruta.stem,
            "fecha": escena.fecha,
            "track": escena.track,
            "frame": escena.frame,
            "bbox": [float(v) for v in args.bbox.split(",")],
            "epsg": rec_hh.epsg,
            "mpp": round(mpp, 3),
            "px": [ancho, alto],
            "hh_max_db": hh_max,
            "hv_max_db": hv_max,
            "area_ha": round(area_ha, 1),
            "agua_ha": round(agua_ha, 1),
            "agua_pct": round(agua_pct, 2),
            "hh_medio_agua_db": round(hh_media, 2),
            "hv_medio_agua_db": round(hv_media, 2),
            "pixeles_validos": valido_px,
        }
        nisar.guardar_json(salida, meta)

    print(f"agua {agua_ha:.0f} ha ({agua_pct:.1f}%) | HH medio {hh_media:.1f} dB")
    print(f"listo: {salida} ({ancho}x{alto} px)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
