"""Busca la firma de doble rebote (posible inundacion) entre dos fechas.

La caida de HV con subida de HH es la firma del agua bajo el dosel: el error
#1 que el paper de L-band (Flores-Anderson et al., RSE 333, 2026) admite para
sus detecciones. El guardia del producto (`--guardia-hh`) aparta esa firma de
la perdida; este script dice DONDE esta y que tan compacta es, para elegir
una caja donde valga la pena probarlo.

Escanea la escena a ~100 m/px, normaliza ΔHH y ΔHV con su mediana y reporta
la firma y la ventana de `--ventana-km` con mas firma. La ventana importa: la
caja del centro de masa engana cuando la distribucion es multimodal (el
centroide cae entre los modos y la caja sale casi vacia).

    .venv\\Scripts\\python.exe validacion\\buscar_doble_rebote.py `
        --antes ANTES.h5 --despues DESPUES.h5 `
        --bbox -63.0,-22.4,-60.0,-19.65
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))

import nisar  # noqa: E402
from pyproj import Transformer  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--antes", required=True)
    ap.add_argument("--despues", required=True)
    ap.add_argument("--bbox", required=True)
    ap.add_argument("--px", type=int, default=2400)
    ap.add_argument("--umbral-hh", type=float, default=3.0)
    ap.add_argument("--umbral-hv", type=float, default=3.0)
    ap.add_argument("--ventana-km", type=float, default=30.0)
    args = ap.parse_args()

    with nisar.Escena(args.antes) as antes, nisar.Escena(args.despues) as despues:
        if (antes.track, antes.frame) != (despues.track, despues.frame):
            raise SystemExit("Las escenas no son del mismo track/frame.")
        rec_hh = antes.recortar("HH", args.bbox, args.px)
        hh_antes, xs, ys = nisar.orientar(rec_hh)
        hh_despues, _, _ = nisar.orientar(despues.recortar("HH", args.bbox, args.px))
        hv_antes = nisar.orientar(antes.recortar("HV", args.bbox, args.px))[0]
        hv_despues = nisar.orientar(despues.recortar("HV", args.bbox, args.px))[0]

        mpp = abs(float(xs[-1] - xs[0])) / max(1, len(xs) - 1)
        d_hh = nisar.a_db(hh_despues) - nisar.a_db(hh_antes)
        d_hv = nisar.a_db(hv_despues) - nisar.a_db(hv_antes)
        valido = np.isfinite(d_hh) & np.isfinite(d_hv)
        d_hh = d_hh - nisar.corrimiento_db(d_hh, valido)
        d_hv = d_hv - nisar.corrimiento_db(d_hv, valido)
        firma = (
            valido
            & (d_hh > abs(float(args.umbral_hh)))
            & (d_hv < -abs(float(args.umbral_hv)))
        ).astype(np.float64)

        total = int(firma.sum())
        area_ha = total * mpp * mpp / 10000.0
        print(
            f"mpp {mpp:.0f} m | firma en la escena: {total} px "
            f"({area_ha:.0f} ha, {100.0 * total / max(1, int(valido.sum())):.2f}%)"
        )
        if total == 0:
            print("no hay firma: el guard no tendria nada que apartar aca")
            return 0

        # Ventana mas densa por suma acumulativa: el centro de masa engana
        # con distribuciones multimodales, la ventana no.
        alto, ancho = firma.shape
        ventana = max(1, int(round(float(args.ventana_km) * 1000.0 / mpp)))
        acum = np.zeros((alto + 1, ancho + 1))
        acum[1:, 1:] = np.cumsum(np.cumsum(firma, axis=0), axis=1)
        mejor, mejor_f, mejor_c = 0, 0, 0
        paso = max(1, ventana // 3)
        for f0 in range(0, max(1, alto - ventana), paso):
            for c0 in range(0, max(1, ancho - ventana), paso):
                f1, c1 = min(f0 + ventana, alto), min(c0 + ventana, ancho)
                suma = acum[f1, c1] - acum[f0, c1] - acum[f1, c0] + acum[f0, c0]
                if suma > mejor:
                    mejor, mejor_f, mejor_c = suma, f0, c0

        tr = Transformer.from_crs(f"EPSG:{rec_hh.epsg}", "EPSG:4326", always_xy=True)
        x0, x1 = float(xs[mejor_c]), float(xs[min(mejor_c + ventana, ancho - 1)])
        y1, y0 = float(ys[mejor_f]), float(ys[min(mejor_f + ventana, alto - 1)])
        o, s = tr.transform(min(x0, x1), min(y0, y1))
        e, n = tr.transform(max(x0, x1), max(y0, y1))
        sub = firma[mejor_f:mejor_f + ventana, mejor_c:mejor_c + ventana]
        ha_sub = float(sub.sum()) * mpp * mpp / 10000.0
        print(
            f"mejor ventana ~{args.ventana_km:g} km: {int(sub.sum())} px de firma "
            f"({ha_sub:.0f} ha, {100.0 * sub.mean():.2f}% de densidad)"
        )
        print(f"caja: {o:.5f},{s:.5f},{e:.5f},{n:.5f}")
        print(
            "densidad baja = firma difusa (no hay pulso compacto); "
            "alta = caja candidata para probar --guardia-hh"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
