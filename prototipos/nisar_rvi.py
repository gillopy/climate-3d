"""Mapa RVI (Radar Vegetation Index) de una escena NISAR GCOV.

RVI dual-pol, adaptado del notebook de Sentinel-1:

    dop = HH / (HH + HV)
    RVI = sqrt(dop) * (4 * HV / (HH + HV))

Se calcula en potencia lineal (como viene GCOV), se enmascara con la capa `mask`
de la escena y se guarda un PNG con escala y pie. El JSON al lado trae media,
percentiles y area valida.

    .venv\\Scripts\\python.exe prototipos\\nisar_rvi.py --h5 ESCENA.h5 \
        --bbox -55.6,-24.5,-55.2,-23.9 --px 2400 --out rvi.png
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
    ap.add_argument("--h5", required=True, help="escena NISAR GCOV (.h5)")
    ap.add_argument("--bbox", required=True, help="oeste,sur,este,norte")
    ap.add_argument("--px", type=int, default=2400)
    ap.add_argument(
        "--ventana",
        type=int,
        default=0,
        help="lado del multilook (impar); 0 = automatico para ~50 m",
    )
    ap.add_argument("--out", required=True)
    ap.add_argument("--geojson", default=None)
    args = ap.parse_args()

    px = max(800, min(int(args.px), 4096))
    salida = Path(args.out)

    print(f"abriendo {Path(args.h5).name}")
    with nisar.Escena(args.h5) as escena:
        if "HH" not in escena.pols or "HV" not in escena.pols:
            raise SystemExit(
                f"RVI necesita HH y HV; la escena tiene {', '.join(escena.pols) or 'ninguna'}."
            )
        rec_hh = escena.recortar("HH", args.bbox, px)
        rec_hv = escena.recortar("HV", args.bbox, px)
        if rec_hh.datos.shape != rec_hv.datos.shape:
            raise SystemExit("HH y HV no comparten grilla en esta escena.")

        hh, xs, ys = nisar.orientar(rec_hh)
        hv, _, _ = nisar.orientar(rec_hv)
        mpp = abs(float(xs[-1] - xs[0])) / max(1, len(xs) - 1)
        ventana = int(args.ventana) if args.ventana > 1 else nisar.ventana_para(mpp)
        if ventana % 2 == 0:
            ventana += 1
        hh_suave = nisar.multilook(hh, ventana)
        hv_suave = nisar.multilook(hv, ventana)
        valores = nisar.rvi(hh_suave, hv_suave)
        validos = valores[np.isfinite(valores)]
        if validos.size == 0:
            raise SystemExit("La caja no tiene pixeles validos para RVI.")

        p10, p50, p90 = [float(v) for v in np.percentile(validos, [10, 50, 90])]
        media = float(np.mean(validos))
        area_ha = validos.size * mpp * mpp / 10000.0
        vmin, vmax = nisar.limites(valores)

        # Secuencial en verde: la escala categorica rojo-verde hacia ruido.
        rgb = nisar.paleta("YlGn", nisar.normalizar(valores, vmin, vmax))
        rgb = np.where(np.isfinite(valores)[..., None], rgb, 0)
        resolucion = f"multilook {ventana}x{ventana} (~{ventana * mpp:.0f} m)" if ventana > 1 else "sin multilook"
        lineas = [
            f"NISAR GCOV · RVI · {escena.fecha or escena.ruta.stem}",
            f"medio {media:.2f} · rango {vmin:.2f} a {vmax:.2f} · "
            f"{area_ha:.0f} ha · {mpp:.0f} m/px · EPSG:{rec_hh.epsg}",
            f"{resolucion} · claro = más RVI · oscuro = menos",
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
            "producto": "rvi",
            "escena": escena.ruta.stem,
            "fecha": escena.fecha,
            "track": escena.track,
            "frame": escena.frame,
            "bbox": [float(v) for v in args.bbox.split(",")],
            "px": [ancho, alto],
            "epsg": rec_hh.epsg,
            "mpp": round(mpp, 3),
            "multilook": ventana,
            "multilook_m": round(ventana * mpp, 1),
            "rvi_medio": round(media, 4),
            "rvi_p10": round(p10, 4),
            "rvi_p50": round(p50, 4),
            "rvi_p90": round(p90, 4),
            "rvi_rango": [round(vmin, 4), round(vmax, 4)],
            "area_ha": round(area_ha, 1),
            "pixeles": int(validos.size),
        }
        nisar.guardar_json(salida, meta)

    print(f"RVI medio {media:.2f} | rango {vmin:.2f}-{vmax:.2f} | multilook {ventana}x{ventana} | {area_ha:.0f} ha")
    print(f"listo: {salida} ({ancho}x{alto} px)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
