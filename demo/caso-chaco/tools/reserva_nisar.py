"""Renderiza la comparacion NISAR de la caja de la reserva Mbaracayu.

Produce las tres imagenes que usa la pagina y un JSON con las hectareas:

- ``reserva_nisar_antes.png``   HV de la fecha anterior, escala de grises,
- ``reserva_nisar_despues.png`` HV de la fecha posterior, misma escala,
- ``reserva_nisar_mascara.png`` HV posterior con los bloques de perdida que
  superan la unidad minima de mapeo.

Uso:
    .venv\\Scripts\\python.exe demo\\caso-chaco\\tools\\reserva_nisar.py ^
        --antes  "...\\...20260628....h5" ^
        --despues "...\\...20260827....h5" ^
        --out-dir demo\\caso-chaco\\img
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

CAJA = "-55.444565,-24.066058,-55.321484,-23.995819"


def _bloques(mascara: np.ndarray, mpp: float, mmu_ha: float) -> tuple[np.ndarray, dict]:
    """Etiqueta componentes 8-conectadas y devuelve solo las que superan la MMU.

    Usa union-find sobre la lista de pixeles encendidos: la mascara de perdida
    es dispersa (decenas de miles de pixeles sobre millones), asi que recorrer
    solo esos pixeles cuesta nada y no requiere scipy.
    """
    minimo_px = max(1, int(round(mmu_ha * 10000.0 / (mpp * mpp))))
    filas, columnas = np.nonzero(mascara)
    total_px = int(filas.size)
    if total_px == 0:
        return np.zeros_like(mascara, dtype=bool), {
            "componentes": 0, "bloques": 0, "minimo_px": minimo_px, "mayor_ha": 0.0,
        }

    indice = {(int(f), int(c)): i for i, (f, c) in enumerate(zip(filas, columnas))}
    padre = list(range(total_px))

    def raiz(i: int) -> int:
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    def unir(a: int, b: int) -> None:
        ra, rb = raiz(a), raiz(b)
        if ra != rb:
            padre[rb] = ra

    for i, (f, c) in enumerate(zip(filas.tolist(), columnas.tolist())):
        for df, dc in ((-1, -1), (-1, 0), (-1, 1), (0, -1)):
            j = indice.get((f + df, c + dc))
            if j is not None:
                unir(i, j)

    tamano: dict[int, int] = {}
    for i in range(total_px):
        r = raiz(i)
        tamano[r] = tamano.get(r, 0) + 1

    validas = {r for r, n in tamano.items() if n >= minimo_px}
    filtrada = np.zeros_like(mascara, dtype=bool)
    for i, (f, c) in enumerate(zip(filas.tolist(), columnas.tolist())):
        if raiz(i) in validas:
            filtrada[f, c] = True

    mayor_px = max((tamano[r] for r in validas), default=0)
    return filtrada, {
        "componentes": int(len(tamano)),
        "bloques": int(len(validas)),
        "minimo_px": minimo_px,
        "mayor_ha": round(float(mayor_px) * mpp * mpp / 10000.0, 2),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--antes", required=True)
    ap.add_argument("--despues", required=True)
    ap.add_argument("--bbox", default=CAJA)
    ap.add_argument("--umbral", type=float, default=3.0, help="caida minima de HV en dB")
    ap.add_argument("--hv-min", type=float, default=-15.5, help="HV minimo para bosque")
    ap.add_argument("--mmu", type=float, default=0.5, help="unidad minima de mapeo en ha")
    ap.add_argument("--px", type=int, default=2400)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    salida = Path(args.out_dir)
    salida.mkdir(parents=True, exist_ok=True)

    with nisar.Escena(args.antes) as antes, nisar.Escena(args.despues) as despues:
        rec_a = antes.recortar("HV", args.bbox, args.px)
        rec_d = despues.recortar("HV", args.bbox, args.px)
        if not nisar.compatibles(rec_a, rec_d):
            raise SystemExit("Las dos escenas no comparten grilla.")

        hv_a, xs, _ = nisar.orientar(rec_a)
        hv_d, _, _ = nisar.orientar(rec_d)
        db_a = nisar.a_db(hv_a)
        db_d = nisar.a_db(hv_d)
        delta = db_d - db_a
        valido = np.isfinite(delta)
        mpp = abs(float(xs[1] - xs[0])) if len(xs) > 1 else 10.0

        pre_bosque = valido & (db_a > args.hv_min)
        perdida = nisar.mayoria3(valido & pre_bosque & (delta < -args.umbral)) & valido
        perdida_mmu, info = _bloques(perdida, mpp, args.mmu)

        ha = lambda px: nisar.hectareas(int(px), mpp, mpp)  # noqa: E731
        datos = {
            "bbox": [float(v) for v in args.bbox.split(",")],
            "fecha_antes": antes.fecha,
            "fecha_despues": despues.fecha,
            "mpp": round(mpp, 2),
            "umbral_db": args.umbral,
            "hv_min_db": args.hv_min,
            "mmu_ha": args.mmu,
            "area_ha": round(ha(valido.sum()), 1),
            "perdida_ha": round(ha(perdida.sum()), 1),
            "perdida_mmu_ha": round(ha(perdida_mmu.sum()), 1),
            "bloques": info["bloques"],
            "componentes": info["componentes"],
            "mayor_ha": info["mayor_ha"],
        }

        vmin = float(np.nanpercentile(db_a[valido], 2))
        vmax = float(np.nanpercentile(db_a[valido], 98))
        vmin = min(vmin, float(np.nanpercentile(db_d[valido], 2)))
        vmax = max(vmax, float(np.nanpercentile(db_d[valido], 98)))

        def gris(db: np.ndarray) -> np.ndarray:
            base = nisar.paleta("gray", nisar.normalizar(db, vmin, vmax))
            return np.where(valido[..., None], base, 0)

        comun = [f"reserva Mbaracayu · caja {args.bbox}", f"HV · {mpp:.0f} m/px · EPSG:{rec_a.epsg}"]

        nisar.guardar(
            gris(db_a), salida / "reserva_nisar_antes.png",
            [f"NISAR GCOV · HV · {antes.fecha}", *comun,
             f"escala {vmin:.0f} a {vmax:.0f} dB"],
            mpp, args.px, epsg=rec_a.epsg,
            x0=rec_a.x0, x1=rec_a.x1, y0=rec_a.y0, y1=rec_a.y1,
        )
        nisar.guardar(
            gris(db_d), salida / "reserva_nisar_despues.png",
            [f"NISAR GCOV · HV · {despues.fecha}", *comun,
             f"escala {vmin:.0f} a {vmax:.0f} dB"],
            mpp, args.px, epsg=rec_d.epsg,
            x0=rec_d.x0, x1=rec_d.x1, y0=rec_d.y0, y1=rec_d.y1,
        )

        mascara = gris(db_d)
        mascara = np.where(
            perdida_mmu[..., None], np.array([205, 35, 35], dtype=np.uint8), mascara
        )
        nisar.guardar(
            mascara, salida / "reserva_nisar_mascara.png",
            [f"NISAR GCOV · perdida HV · {antes.fecha} -> {despues.fecha}", *comun,
             f"{datos['perdida_mmu_ha']:.1f} ha en {info['bloques']} bloques >= {args.mmu:g} ha "
             f"(crudo {datos['perdida_ha']:.0f} ha)"],
            mpp, args.px, epsg=rec_d.epsg,
            x0=rec_d.x0, x1=rec_d.x1, y0=rec_d.y0, y1=rec_d.y1,
        )

    (salida.parent / "reserva_nisar.json").write_text(
        json.dumps(datos, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    print(
        f"perdida cruda {datos['perdida_ha']} ha | con MMU {datos['perdida_mmu_ha']} ha "
        f"en {info['bloques']} bloques | mayor {info['mayor_ha']} ha"
    )
    print(f"listo: {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
