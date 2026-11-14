"""Calcula los indicadores tecnicos del caso de estudio.

Lee el mismo par de escenas que usa el pipeline y agrega lo que la pagina
necesita para dejar de ser un visor:

- sensibilidad de la superficie al umbral de HV,
- unidad minima de mapeo por componentes conexas,
- firma polarimetrica (HV contra HH) en el desmonte y en el control,
- distribucion de delta HV,
- correccion por la tasa de falsos positivos medida en el control.

Escribe un `tecnico.js` con `window.TECNICO = {...}` para que la pagina
funcione sin servidor ni fetch.

Uso:
    .venv\\Scripts\\python.exe demo\\caso-chaco\\tools\\tecnico.py ^
        --antes  "...\\...20260120....h5" ^
        --despues "...\\...20260321....h5" ^
        --out demo\\caso-chaco\\tecnico.js
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "comun"))

import nisar  # noqa: E402

UMBRALES = (2.0, 2.5, 3.0, 3.5, 4.0, 5.0)
BINS = np.arange(-12.0, 6.01, 0.5)


def _etiquetar_numpy(mascara: np.ndarray) -> np.ndarray:
    """Componentes conexas 8-conectadas sin scipy.

    Propagacion de etiquetas por maximo hasta converger. Lento en teoria
    (una iteracion por pixel de diametro) pero de sobra para recortes de
    este tamano y sin sumar dependencias al repo.
    """
    alto, ancho = mascara.shape
    ids = np.arange(1, alto * ancho + 1, dtype=np.int64).reshape(alto, ancho)
    lab = np.where(mascara, ids, 0)
    desplazamientos = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))

    for _ in range(alto + ancho):
        relleno = np.pad(lab, 1)
        nuevo = lab.copy()
        for dy, dx in desplazamientos:
            vecino = relleno[1 + dy:1 + dy + alto, 1 + dx:1 + dx + ancho]
            np.maximum(nuevo, vecino, out=nuevo)
        nuevo = np.where(mascara, nuevo, 0)
        if np.array_equal(nuevo, lab):
            break
        lab = nuevo

    return lab


def componentes(mascara: np.ndarray, mpp: float):
    """Devuelve las areas (ha) de cada componente conexa de la mascara."""
    if not mascara.any():
        return {"total": 0, "areas_ha": []}

    try:
        from scipy import ndimage  # type: ignore
        etiquetas, total = ndimage.label(mascara, structure=np.ones((3, 3), dtype=bool))
        areas_px = np.bincount(etiquetas.ravel())[1:]
    except Exception:  # noqa: BLE001
        etiquetas = _etiquetar_numpy(mascara)
        areas_px = np.bincount(etiquetas[mascara].ravel())
        areas_px = areas_px[areas_px > 0]
        total = int(areas_px.size)

    areas_ha = areas_px * mpp * mpp / 10000.0
    return {"total": int(total), "areas_ha": areas_ha.tolist()}


def analizar(ev, ea, bbox: str, umbral: float, hv_min: float, mmu_ha: float) -> dict:
    hv_a, _, _ = nisar.orientar(ea.recortar("HV", bbox))
    hv_d, _, _ = nisar.orientar(ev.recortar("HV", bbox))
    hh_a, _, _ = nisar.orientar(ea.recortar("HH", bbox))
    hh_d, _, _ = nisar.orientar(ev.recortar("HH", bbox))

    if hv_a.shape != hv_d.shape:
        raise SystemExit(f"Grillas incompatibles en {bbox}")

    rec = ea.recortar("HV", bbox)
    mpp = float(rec.metros_por_px)

    db_a = nisar.a_db(hv_a)
    db_d = nisar.a_db(hv_d)
    dh_a = nisar.a_db(hh_a)
    dh_d = nisar.a_db(hh_d)

    delta = db_d - db_a
    delta_hh = dh_d - dh_a

    valido = np.isfinite(delta) & np.isfinite(delta_hh)
    bosque = valido & (db_a > hv_min)

    perdida = nisar.mayoria3(valido & bosque & (delta < -umbral)) & valido

    px_total = int(valido.sum())
    px_bosque = int(bosque.sum())
    px_perdida = int(perdida.sum())

    def ha(px: int) -> float:
        return nisar.hectareas(px, mpp, mpp)

    # --- sensibilidad al umbral ---
    sensibilidad = []
    for t in UMBRALES:
        m = nisar.mayoria3(valido & bosque & (delta < -t)) & valido
        sensibilidad.append({"db": t, "ha": round(ha(int(m.sum())), 1), "px": int(m.sum())})

    # --- unidad minima de mapeo ---
    mmu_px = mmu_ha * 10000.0 / (mpp * mpp)
    comp = componentes(perdida, mpp)
    mmu_info = {"umbral_ha": mmu_ha, "aplicable": True, "mmu_px": round(mmu_px, 1)}
    if comp is not None:
        areas = comp["areas_ha"]
        conservadas = [a for a in areas if a >= mmu_ha]
        mmu_info.update({
            "componentes": comp["total"],
            "componentes_validos": len(conservadas),
            "ha_sin_mmu": round(sum(areas), 1),
            "ha_con_mmu": round(float(sum(conservadas)), 1),
            "componente_mayor_ha": round(float(max(areas)), 1) if areas else 0.0,
            "componente_mediana_ha": round(float(np.median(areas)), 2) if areas else 0.0,
        })

        # Cuantas manchas hay de cada tamano: es lo que separa senal de speckle.
        tramos = ((0.5, 1.0), (1.0, 2.0), (2.0, 5.0), (5.0, 10.0), (10.0, 25.0), (25.0, float("inf")))
        distribucion = []
        for bajo, alto in tramos:
            dentro = [a for a in conservadas if bajo <= a < alto]
            etiqueta = f"{bajo:g}-{alto:g}" if alto != float("inf") else f"{bajo:g}+"
            distribucion.append({
                "rango": etiqueta,
                "componentes": len(dentro),
                "ha": round(float(sum(dentro)), 1),
            })
        mmu_info["distribucion"] = distribucion

    # --- firma polarimetrica ---
    # En el desmonte se mide sobre los pixeles clasificados como perdida.
    firma = {
        "delta_hv_db": round(float(np.nanmean(delta[perdida])), 2) if px_perdida else 0.0,
        "delta_hh_db": round(float(np.nanmean(delta_hh[perdida])), 2) if px_perdida else 0.0,
        "pixeles": px_perdida,
    }
    firma["delta_ratio_db"] = round(firma["delta_hv_db"] - firma["delta_hh_db"], 2)

    # --- distribucion de delta HV sobre bosque ---
    hist_caso, _ = np.histogram(delta[bosque], bins=BINS)
    hist_caso = hist_caso / max(1, px_bosque)

    return {
        "bbox": bbox,
        "mpp": mpp,
        "px_total": px_total,
        "px_bosque": px_bosque,
        "px_perdida": px_perdida,
        "area_ha": round(ha(px_total), 1),
        "bosque_ha": round(ha(px_bosque), 1),
        "perdida_ha": round(ha(px_perdida), 1),
        "delta_hv_medio_db": round(float(np.nanmean(delta[bosque])), 2) if px_bosque else 0.0,
        "delta_hh_medio_db": round(float(np.nanmean(delta_hh[bosque])), 2) if px_bosque else 0.0,
        "sensibilidad": sensibilidad,
        "mmu": mmu_info,
        "firma": firma,
        "hist": hist_caso.tolist(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--antes", required=True)
    ap.add_argument("--despues", required=True)
    ap.add_argument("--bbox", default="-61.12896,-20.856085,-61.062527,-20.81036")
    ap.add_argument("--control", default="-61.182518,-20.938034,-61.099777,-20.883834")
    ap.add_argument("--umbral", type=float, default=3.0)
    ap.add_argument("--hv-min", type=float, default=-15.5)
    ap.add_argument("--mmu", type=float, default=0.5, help="unidad minima de mapeo en ha")
    ap.add_argument("--var", default="TECNICO", help="nombre de la global que escribe el JS")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with nisar.Escena(Path(args.antes)) as ea, nisar.Escena(Path(args.despues)) as ev:
        caso = analizar(ev, ea, args.bbox, args.umbral, args.hv_min, args.mmu)
        control = analizar(ev, ea, args.control, args.umbral, args.hv_min, args.mmu)

        # Correccion por falsos positivos medidos en el control.
        p_ctrl = control["px_perdida"] / max(1, control["px_bosque"])
        fp_esperados_px = p_ctrl * caso["px_bosque"]
        fp_esperados_ha = nisar.hectareas(int(round(fp_esperados_px)), caso["mpp"], caso["mpp"])
        corregido = max(0.0, caso["perdida_ha"] - fp_esperados_ha)

        datos = {
            "parametros": {
                "umbral_db": args.umbral,
                "hv_min_db": args.hv_min,
                "mmu_ha": args.mmu,
                "mpp": caso["mpp"],
                "m2_por_pixel": round(caso["mpp"] * caso["mpp"], 1),
                "pixeles_por_ha": round(10000.0 / (caso["mpp"] * caso["mpp"]), 2),
            },
            "caso": caso,
            "control": control,
            "correccion": {
                "tasa_control_pct": round(100.0 * p_ctrl, 4),
                "fp_esperados_ha": round(fp_esperados_ha, 1),
                "perdida_corregida_ha": round(corregido, 1),
            },
            "bins": BINS.tolist(),
        }

    salida = Path(args.out)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(
        f"window.{args.var} = " + json.dumps(datos, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )

    print(f"listo: {salida}")
    print(f"  umbral {args.umbral:g} dB | caso {caso['perdida_ha']} ha | control {control['perdida_ha']} ha")
    if caso["mmu"]["aplicable"]:
        print(f"  mmu {args.mmu:g} ha: {caso['mmu']['componentes']} componentes -> "
              f"{caso['mmu']['ha_con_mmu']} ha")
    print(f"  firma: dHV {caso['firma']['delta_hv_db']} dB | "
          f"dHH {caso['firma']['delta_hh_db']} dB | "
          f"d(HV-HH) {caso['firma']['delta_ratio_db']} dB")
    print(f"  corregido por control: {corregido:.1f} ha "
          f"(fp esperados {fp_esperados_ha:.1f} ha)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
