"""ValidaciÃ³n de deforestaciÃ³n en el Este contra una referencia Ã³ptica pre/post.

No hay verdad de campo: la referencia es el cambio de NDVI de Sentinel-2 entre
una ventana previa y una posterior, enmascarado con SCL. Es una referencia
independiente del radar, pero no perfecta: una cosecha o un anegamiento tambiÃ©n
pueden bajar el NDVI. El informe lo dice y separa lo que se puede afirmar.

Salidas en ``--out``:
- ``ndvi_pre.npy`` / ``ndvi_post.npy`` (cachÃ© de los compuestos),
- ``muestras.csv`` (puntos ciegos con etiqueta y predicciÃ³n),
- ``metricas.json`` y ``informe.md``,
- ``comparacion.png``, ``errores.png``, ``curva.png``, ``dispersion.png``.

    .venv\\Scripts\\python.exe validacion\\deforestacion_este.py \
        --antes ANTES.h5 --despues DESPUES.h5
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from affine import Affine  # noqa: E402
from pyproj import Transformer  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
sys.path.insert(0, str(RAIZ / "prototipos"))

import nisar  # noqa: E402
import sentinel2  # noqa: E402
import validacion  # noqa: E402


def compuesto_ndvi(
    bbox, desde: str, hasta: str, nubes: float, forma, transform, crs, px: int,
    max_items: int = 12,
) -> tuple[np.ndarray, list[dict]]:
    """NDVI mediano de Sentinel-2 en la ventana, en la grilla del radar."""
    inicio = date.fromisoformat(desde[:10])
    fin = date.fromisoformat(hasta[:10])
    if fin < inicio:
        inicio, fin = fin, inicio
    centro = inicio + (fin - inicio) / 2
    dias = max(1, (fin - inicio).days // 2 + 1)
    items = sentinel2.buscar_items(bbox, centro, dias, nubes, max_items)
    if not items:
        raise SystemExit(
            f"No hay Sentinel-2 entre {desde} y {hasta} con nubes < {nubes:g}%."
        )
    ndvi, usados = sentinel2.componer_ndvi(
        items, bbox, forma, transform, crs, px
    )
    if ndvi is None or not np.isfinite(ndvi).any():
        raise SystemExit("NingÃºn Ã­tem dejÃ³ NDVI vÃ¡lido.")
    return ndvi, usados


def _cache_npy(ruta: Path, calcular, refrescar: bool):
    if ruta.is_file() and not refrescar:
        print(f"usando cachÃ© {ruta.name}")
        return np.load(ruta)
    valor = calcular()
    np.save(ruta, valor)
    return valor


def _metricas_fila(nombre: str, tp, fp, fn, tn) -> dict:
    fila = validacion.metricas(tp, fp, fn, tn)
    fila["conjunto"] = nombre
    return fila


def _tabla_md(filas: list[dict]) -> str:
    cabecera = "| Conjunto | TP | FP | FN | TN | PrecisiÃ³n | Recall | F1 | IoU |\n"
    cabecera += "|---|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    cuerpo = ""
    for fila in filas:
        cuerpo += (
            f"| {fila['conjunto']} | {int(fila['tp'])} | {int(fila['fp'])} | "
            f"{int(fila['fn'])} | {int(fila['tn'])} | {fila['precision']:.2f} | "
            f"{fila['recall']:.2f} | {fila['f1']:.2f} | {fila['iou']:.2f} |\n"
        )
    return cabecera + cuerpo


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--antes", required=True)
    ap.add_argument("--despues", required=True)
    ap.add_argument("--bbox", default="-55.8,-24.8,-55.0,-23.8")
    ap.add_argument("--px", type=int, default=1200)
    ap.add_argument("--pre-desde", default="2026-06-01")
    ap.add_argument("--pre-hasta", default="2026-06-30")
    ap.add_argument("--post-desde", default="2026-10-01")
    ap.add_argument("--post-hasta", default="2026-10-31")
    ap.add_argument("--nubes", type=float, default=40.0)
    ap.add_argument("--ndvi-bosque", type=float, default=0.50)
    ap.add_argument("--ndvi-perdida", type=float, default=0.30)
    ap.add_argument("--dndvi-perdida", type=float, default=0.20)
    ap.add_argument("--estable", type=float, default=0.10)
    ap.add_argument("--hv-min", type=float, default=-15.5)
    ap.add_argument("--umbral", type=float, default=2.0)
    ap.add_argument("--ml", type=int, default=0, help="0 = multilook automatico (~50 m)")
    ap.add_argument(
        "--sin-normalizar",
        action="store_true",
        help="no restar el corrimiento global de ΔHV (producto viejo)",
    )
    ap.add_argument("--muestras", type=int, default=250)
    ap.add_argument("--separacion", type=int, default=2)
    ap.add_argument(
        "--bloque-validacion",
        type=int,
        default=8,
        help="tamano de bloque en pixeles para IC y metricas espaciales",
    )
    ap.add_argument("--out", default=str(RAIZ / "validacion" / "este_2026"))
    ap.add_argument("--refrescar", action="store_true", help="ignora la cachÃ© de NDVI")
    args = ap.parse_args()

    salida = Path(args.out)
    salida.mkdir(parents=True, exist_ok=True)
    px = max(800, min(int(args.px), 2000))
    oeste, sur, este, norte = nisar.caja(args.bbox)

    print(f"NISAR antes={Path(args.antes).name}")
    print(f"NISAR despues={Path(args.despues).name}")
    with nisar.Escena(args.antes) as antes, nisar.Escena(args.despues) as despues:
        if (antes.track, antes.frame) != (despues.track, despues.frame):
            raise SystemExit("Las escenas no son del mismo track/frame.")
        rec_antes = antes.recortar("HV", args.bbox, px)
        rec_despues = despues.recortar("HV", args.bbox, px)
        if not nisar.compatibles(rec_antes, rec_despues):
            raise SystemExit("Las escenas no comparten grilla.")
        hv_antes, xs, ys = nisar.orientar(rec_antes)
        hv_despues, _, _ = nisar.orientar(rec_despues)
        mpp_x = abs(float(xs[-1] - xs[0])) / max(1, len(xs) - 1)
        mpp_y = abs(float(ys[0] - ys[-1])) / max(1, len(ys) - 1)
        ml = max(1, int(args.ml)) if args.ml > 0 else nisar.ventana_para(mpp_x, 50.0, 5)
        if ml > 1:
            hv_antes = nisar.multilook(hv_antes, ml)
            hv_despues = nisar.multilook(hv_despues, ml)
        db_antes = nisar.a_db(hv_antes)
        db_despues = nisar.a_db(hv_despues)
        offset_db = 0.0
        if not args.sin_normalizar:
            offset_db = nisar.corrimiento_db(db_despues - db_antes)
        dhv = db_despues - db_antes - offset_db
        track, frame = antes.track, antes.frame
        fecha_antes, fecha_despues = antes.fecha, despues.fecha
        epsg = rec_antes.epsg

    forma = dhv.shape
    transform = Affine.translation(
        float(xs[0]) - mpp_x / 2.0, float(ys[0]) + mpp_y / 2.0
    ) * Affine.scale(mpp_x, -mpp_y)
    crs = f"EPSG:{epsg}"
    print(f"grilla {forma[0]}x{forma[1]} · {mpp_x:.0f} m/px · track {track} frame {frame}")
    print(
        f"producto: dHV < -{args.umbral:g} dB - multilook {ml} - "
        f"offset {offset_db:+.2f} dB"
        + (" (sin normalizar)" if args.sin_normalizar else "")
    )

    print(f"NDVI previo {args.pre_desde} a {args.pre_hasta}")
    ndvi_pre = _cache_npy(
        salida / "ndvi_pre.npy",
        lambda: compuesto_ndvi(
            (oeste, sur, este, norte), args.pre_desde, args.pre_hasta, args.nubes,
            forma, transform, crs, px,
        )[0],
        args.refrescar,
    )
    print(f"NDVI posterior {args.post_desde} a {args.post_hasta}")
    ndvi_post = _cache_npy(
        salida / "ndvi_post.npy",
        lambda: compuesto_ndvi(
            (oeste, sur, este, norte), args.post_desde, args.post_hasta, args.nubes,
            forma, transform, crs, px,
        )[0],
        args.refrescar,
    )

    valido = (
        np.isfinite(db_antes) & np.isfinite(db_despues)
        & np.isfinite(ndvi_pre) & np.isfinite(ndvi_post)
    )
    dndvi = ndvi_post - ndvi_pre
    perdida_ref = (
        valido
        & (ndvi_pre >= args.ndvi_bosque)
        & (ndvi_post <= args.ndvi_perdida)
        & (dndvi <= -args.dndvi_perdida)
    )
    estable_ref = (
        valido
        & (np.abs(dndvi) <= args.estable)
        & (ndvi_pre >= args.ndvi_bosque - 0.10)
    )
    perdida_ref = nisar.mayoria3(perdida_ref) & valido
    estable_ref = nisar.mayoria3(estable_ref) & valido & ~perdida_ref

    pred = nisar.mayoria3(valido & (db_antes > args.hv_min) & (dhv < -args.umbral)) & valido

    # Muestreo ciego: puntos de pÃ©rdida y de estabilidad, separados en la grilla.
    muestras = validacion.muestreo_estratificado(
        {"perdida": perdida_ref, "estable": estable_ref},
        max(20, int(args.muestras)),
        seed=42,
        separacion=max(1, int(args.separacion)),
    )
    filas: list[int] = []
    columnas: list[int] = []
    refs: list[bool] = []
    preds: list[bool] = []
    for nombre, (fs, cs) in muestras.items():
        etiqueta = nombre == "perdida"
        for fila, columna in zip(fs, cs):
            filas.append(int(fila))
            columnas.append(int(columna))
            refs.append(etiqueta)
            preds.append(bool(pred[fila, columna]))
    ref_m = np.array(refs, dtype=bool)
    pred_m = np.array(preds, dtype=bool)
    if ref_m.size == 0:
        raise SystemExit("La referencia no dejÃ³ puntos; revisÃ¡ los umbrales de NDVI.")

    tp, fp, fn, tn = validacion.matriz_confusion(ref_m, pred_m)
    n_pos_total = int(perdida_ref.sum())
    n_neg_total = int(estable_ref.sum())
    n_pos_m = int(ref_m.sum())
    n_neg_m = int((~ref_m).sum())
    ponderada = validacion.metricas_ponderadas(
        tp,
        fp,
        fn,
        tn,
        n_pos_total / max(1, n_pos_m),
        n_neg_total / max(1, n_neg_m),
    )
    ponderada["conjunto"] = "muestra ponderada"
    tabla = [
        _metricas_fila("muestra balanceada", tp, fp, fn, tn),
        ponderada,
        _metricas_fila(
            "denso (operativo)", *validacion.matriz_confusion(perdida_ref, pred)
        ),
    ]
    ic = validacion.bootstrap_ic(ref_m, pred_m, n=500)
    bloque_validacion = max(1, int(args.bloque_validacion))
    metricas_bloques = validacion.metricas_por_bloques(
        perdida_ref, pred, bloque=bloque_validacion
    )
    ic_bloques = validacion.bootstrap_bloques_ic(
        perdida_ref, pred, bloque=bloque_validacion, n=500
    )
    area_ref = float(perdida_ref.sum()) * mpp_x * mpp_y / 10000.0
    area_pred = float(pred.sum()) * mpp_x * mpp_y / 10000.0
    area_valida = float(valido.sum()) * mpp_x * mpp_y / 10000.0
    sesgo = (area_pred - area_ref) / area_ref * 100.0 if area_ref else 0.0

    # Curva de umbral sobre el mapa denso (la muestra balanceada no da precisiÃ³n).
    # Sobre ΔHV ya normalizado y con multilook, el piso de ruido baja a ~1,5 dB.
    umbrales = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    curva = []
    for umbral in umbrales:
        mascara = (
            nisar.mayoria3(valido & (db_antes > args.hv_min) & (dhv < -umbral))
            & valido
        )
        fila = validacion.metricas(
            *validacion.matriz_confusion(perdida_ref, mascara)
        )
        fila["umbral_db"] = umbral
        curva.append(fila)

    # Split espacial: oeste/east de la caja, para ver estabilidad.
    mitad = forma[1] // 2
    split = {}
    for nombre, condicion in (
        ("oeste", np.array(columnas) < mitad),
        ("este", np.array(columnas) >= mitad),
    ):
        if condicion.sum() == 0:
            continue
        split[nombre] = validacion.metricas(
            *validacion.matriz_confusion(ref_m[condicion], pred_m[condicion])
        )
        split[nombre]["n"] = int(condicion.sum())

    # CSV de muestras, con lon/lat para abrirlo en QGIS.
    transformador = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    with (salida / "muestras.csv").open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(
            ["fila", "columna", "lon", "lat", "referencia", "prediccion",
             "ndvi_pre", "ndvi_post", "dndvi", "hv_antes_db", "dhv_db"]
        )
        for fila, columna, ref, pr in zip(filas, columnas, refs, preds):
            lon, lat = transformador.transform(float(xs[columna]), float(ys[fila]))
            escritor.writerow([
                fila, columna, f"{lon:.6f}", f"{lat:.6f}",
                "perdida" if ref else "estable",
                "perdida" if pr else "no",
                f"{ndvi_pre[fila, columna]:.3f}",
                f"{ndvi_post[fila, columna]:.3f}",
                f"{dndvi[fila, columna]:.3f}",
                f"{db_antes[fila, columna]:.2f}",
                f"{dhv[fila, columna]:.2f}",
            ])

    # Figuras.
    _comparacion(salida / "comparacion.png", ndvi_pre, ndvi_post, dndvi, dhv)
    _errores(salida / "errores.png", db_antes, perdida_ref, pred)
    _curva(salida / "curva.png", curva)
    _dispersion(salida / "dispersion.png", ref_m, db_antes, dndvi, filas, columnas)

    metricas_json = {
        "caso": "deforestacion_este",
        "nisar": {
            "antes": fecha_antes, "despues": fecha_despues,
            "track": track, "frame": frame, "epsg": epsg,
            "mpp": [round(mpp_x, 3), round(mpp_y, 3)],
        },
        "ventanas": {
            "pre": [args.pre_desde, args.pre_hasta],
            "post": [args.post_desde, args.post_hasta],
            "nubes_max": args.nubes,
        },
        "referencia": {
            "tipo": "NDVI optico pre/post; no es verdad de campo",
            "es_verdad_de_campo": False,
            "ndvi_bosque": args.ndvi_bosque,
            "ndvi_perdida": args.ndvi_perdida,
            "dndvi_perdida": args.dndvi_perdida,
            "estable": args.estable,
        },
        "producto": {
            "hv_min_db": args.hv_min,
            "umbral_db": args.umbral,
            "multilook": ml,
            "normalizado": not args.sin_normalizar,
            "offset_db": round(offset_db, 2),
        },
        "pixeles": {
            "validos": int(valido.sum()),
            "referencia_perdida": int(perdida_ref.sum()),
            "referencia_estable": int(estable_ref.sum()),
            "prediccion_perdida": int(pred.sum()),
        },
        "areas_ha": {
            "valida": round(area_valida, 1),
            "referencia_perdida": round(area_ref, 1),
            "prediccion_perdida": round(area_pred, 1),
            "sesgo_pct": round(sesgo, 1),
        },
        "metricas": {
            "denso": tabla[2],
            "bloques_espaciales": metricas_bloques,
            "muestra_balanceada": tabla[0],
            "muestra_ponderada": tabla[1],
            "bootstrap_muestra": ic,
            "bootstrap_bloques": ic_bloques,
        },
        "incertidumbre": {
            "unidad": "bloques espaciales",
            "tamano_bloque_pixeles": bloque_validacion,
            "nota": "El IC por bloques reduce la independencia ficticia de pixeles vecinos.",
        },
        "split_espacial": split,
        "curva_umbral": curva,
        "muestras": int(ref_m.size),
    }
    (salida / "metricas.json").write_text(
        json.dumps(metricas_json, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    _informe(salida / "informe.md", metricas_json, tabla, ic, split, curva)

    denso = tabla[2]
    print(
        f"muestras {ref_m.size} | denso F1 {denso['f1']:.2f} "
        f"(P {denso['precision']:.2f}, R {denso['recall']:.2f}) | "
        f"ponderada F1 {tabla[1]['f1']:.2f}"
    )
    print(f"Ã¡rea ref {area_ref:.0f} ha | pred {area_pred:.0f} ha | sesgo {sesgo:+.1f}%")
    print(f"listo: {salida}")
    return 0


def _comparacion(salida, ndvi_pre, ndvi_post, dndvi, dhv):
    fig, axes = plt.subplots(2, 2, figsize=(14, 11), dpi=140)
    fig.patch.set_facecolor("#0b0c0d")
    datos = [
        (ndvi_pre, "NDVI previo", "RdYlGn", -0.2, 0.8),
        (ndvi_post, "NDVI posterior", "RdYlGn", -0.2, 0.8),
        (dndvi, "Î”NDVI (post - pre)", "RdBu", -0.5, 0.5),
        (dhv, "NISAR Î”HV (dB)", "RdBu", -6, 6),
    ]
    for ax, (dato, titulo, mapa, vmin, vmax) in zip(axes.ravel(), datos):
        ax.set_facecolor("#0b0c0d")
        ax.set_xticks([])
        ax.set_yticks([])
        for borde in ax.spines.values():
            borde.set_color("#23252a")
        im = ax.imshow(dato, cmap=mapa, vmin=vmin, vmax=vmax)
        ax.set_title(titulo, color="#f7f8f8", fontsize=10)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02).ax.tick_params(
            colors="#d0d6e0", labelsize=8
        )
    fig.suptitle("ValidaciÃ³n deforestaciÃ³n Este Â· referencia Ã³ptica vs NISAR",
                 color="#f7f8f8", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(salida, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def _errores(salida, base, referencia, prediccion):
    gris = np.nan_to_num(base, nan=np.nanmin(base) if np.isfinite(base).any() else -30)
    lo, hi = np.nanpercentile(gris, [2, 98]) if np.isfinite(gris).any() else (-25, -5)
    norm = np.clip((gris - lo) / max(1e-9, hi - lo), 0, 1)
    rgb = (np.dstack([norm, norm, norm]) * 255).astype(np.uint8)
    tp = referencia & prediccion
    fp = ~referencia & prediccion
    fn = referencia & ~prediccion
    rgb[tp] = [40, 190, 90]
    rgb[fp] = [230, 60, 45]
    rgb[fn] = [60, 110, 230]
    fig, ax = plt.subplots(figsize=(10, 11), dpi=140)
    fig.patch.set_facecolor("#0b0c0d")
    ax.set_facecolor("#0b0c0d")
    ax.imshow(rgb)
    ax.set_xticks([])
    ax.set_yticks([])
    for borde in ax.spines.values():
        borde.set_color("#23252a")
    ax.set_title(
        f"Errores Â· TP {int(tp.sum())} Â· FP {int(fp.sum())} Â· FN {int(fn.sum())}",
        color="#f7f8f8", fontsize=10,
    )
    fig.text(0.01, 0.01, "verde = acierto Â· rojo = falso positivo Â· azul = falso negativo",
             color="#8a8f98", fontsize=8)
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(salida, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def _curva(salida, curva):
    umbrales = [fila["umbral_db"] for fila in curva]
    fig, ax = plt.subplots(figsize=(9, 5), dpi=140)
    fig.patch.set_facecolor("#0b0c0d")
    ax.set_facecolor("#0b0c0d")
    for clave, color in (("f1", "#3fb950"), ("precision", "#5e6ad2"), ("recall", "#d29922")):
        ax.plot(umbrales, [fila[clave] for fila in curva], marker="o", label=clave, color=color)
    ax.set_xlabel("umbral de caÃ­da HV (dB)", color="#d0d6e0")
    ax.set_ylabel("mÃ©trica", color="#d0d6e0")
    ax.set_ylim(0, 1)
    ax.tick_params(colors="#8a8f98")
    ax.grid(color="#23252a", alpha=0.7)
    for borde in ax.spines.values():
        borde.set_color("#23252a")
    ax.legend(facecolor="#161718", edgecolor="#23252a", labelcolor="#d0d6e0")
    ax.set_title("Curva de umbral sobre el mapa denso", color="#f7f8f8", fontsize=10)
    fig.tight_layout()
    fig.savefig(salida, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def _dispersion(salida, ref_m, db_antes, dndvi, filas, columnas):
    fig, ax = plt.subplots(figsize=(8, 6), dpi=140)
    fig.patch.set_facecolor("#0b0c0d")
    ax.set_facecolor("#0b0c0d")
    hv = np.array([db_antes[f, c] for f, c in zip(filas, columnas)])
    dn = np.array([dndvi[f, c] for f, c in zip(filas, columnas)])
    for etiqueta, color, nombre in (
        (True, "#f85149", "pÃ©rdida Ã³ptica"),
        (False, "#3fb950", "estable Ã³ptico"),
    ):
        mascara = ref_m == etiqueta
        ax.scatter(hv[mascara], dn[mascara], s=9, alpha=0.7, color=color, label=nombre)
    ax.axhline(0, color="#34343a", linewidth=1)
    ax.set_xlabel("HV antes (dB)", color="#d0d6e0")
    ax.set_ylabel("Î”NDVI", color="#d0d6e0")
    ax.tick_params(colors="#8a8f98")
    ax.grid(color="#23252a", alpha=0.6)
    for borde in ax.spines.values():
        borde.set_color("#23252a")
    ax.legend(facecolor="#161718", edgecolor="#23252a", labelcolor="#d0d6e0")
    ax.set_title("Muestra ciega: HV vs Î”NDVI", color="#f7f8f8", fontsize=10)
    fig.tight_layout()
    fig.savefig(salida, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def _informe(ruta, meta, tabla, ic, split, curva):
    lineas = [
        "# ValidaciÃ³n Â· deforestaciÃ³n en el Este",
        "",
        f"- NISAR: {meta['nisar']['antes']} â†’ {meta['nisar']['despues']}",
        f"- Track/frame: {meta['nisar']['track']}/{meta['nisar']['frame']}",
        f"- Grilla: {meta['nisar']['mpp'][0]:.0f} m/px Â· EPSG:{meta['nisar']['epsg']}",
        f"- Sentinel-2: {meta['ventanas']['pre'][0]} a {meta['ventanas']['pre'][1]} "
        f"(previo) y {meta['ventanas']['post'][0]} a {meta['ventanas']['post'][1]} "
        f"(posterior), nubes < {meta['ventanas']['nubes_max']:g}%",
        f"- Referencia: NDVI previo â‰¥ {meta['referencia']['ndvi_bosque']:.2f}, "
        f"posterior â‰¤ {meta['referencia']['ndvi_perdida']:.2f}, "
        f"Î”NDVI â‰¤ -{meta['referencia']['dndvi_perdida']:.2f}; "
        f"estable: |Î”NDVI| â‰¤ {meta['referencia']['estable']:.2f}",
        f"- Tipo de referencia: {meta['referencia']['tipo']}.",
        f"- Producto: HV antes > {meta['producto']['hv_min_db']:g} dB y "
        f"Î”HV < -{meta['producto']['umbral_db']:g} dB, mayorÃ­a 3Ã—3, "
        f"multilook {meta['producto']['multilook']}, "
        f"offset del par {meta['producto']['offset_db']:+.2f} dB"
        f"{' (sin normalizar)' if not meta['producto']['normalizado'] else ''}",
        f"- Muestras ciegas: {meta['muestras']}",
        "",
        "## MÃ©tricas",
        "",
        _tabla_md(tabla),
        "",
        "La fila **denso** es la operativa. La muestra balanceada (mitad pÃ©rdida, "
        "mitad estable) infla la precisiÃ³n; sirve para el recall y el IC.",
        "",
        "## IC bootstrap (95 %, muestra balanceada)",
        "",
        f"- PrecisiÃ³n: {ic['precision']['mean']:.2f} "
        f"[{ic['precision']['p2_5']:.2f}, {ic['precision']['p97_5']:.2f}]",
        f"- Recall: {ic['recall']['mean']:.2f} "
        f"[{ic['recall']['p2_5']:.2f}, {ic['recall']['p97_5']:.2f}]",
        f"- F1: {ic['f1']['mean']:.2f} "
        f"[{ic['f1']['p2_5']:.2f}, {ic['f1']['p97_5']:.2f}]",
        "",
        "## MÃ©tricas e IC por bloques espaciales",
        "",
        f"- TamaÃ±o de bloque: {meta['incertidumbre']['tamano_bloque_pixeles']} pÃ­xeles",
        f"- Bloques: {int(meta['metricas']['bloques_espaciales']['bloques'])}",
        f"- F1 por bloques: {meta['metricas']['bloques_espaciales']['f1']:.2f}",
        f"- IC F1 por bloques: {meta['metricas']['bootstrap_bloques']['f1']['mean']:.2f} "
        f"[{meta['metricas']['bootstrap_bloques']['f1']['p2_5']:.2f}, "
        f"{meta['metricas']['bootstrap_bloques']['f1']['p97_5']:.2f}]",
        "",
        "## Ãrea",
        "",
        f"- Referencia: {meta['areas_ha']['referencia_perdida']:.0f} ha",
        f"- PredicciÃ³n: {meta['areas_ha']['prediccion_perdida']:.0f} ha",
        f"- Sesgo: {meta['areas_ha']['sesgo_pct']:+.1f} %",
        "",
        "## Split espacial (muestra balanceada)",
        "",
    ]
    for nombre, fila in split.items():
        lineas.append(
            f"- {nombre} (n={fila['n']}): F1 {fila['f1']:.2f}, "
            f"precisiÃ³n {fila['precision']:.2f}, recall {fila['recall']:.2f}"
        )
    lineas += ["", "## Curva de umbral (mapa denso)", ""]
    lineas.append("| Umbral (dB) | PrecisiÃ³n | Recall | F1 |")
    lineas.append("|---:|---:|---:|---:|")
    for fila in curva:
        lineas.append(
            f"| {fila['umbral_db']:g} | {fila['precision']:.2f} | "
            f"{fila['recall']:.2f} | {fila['f1']:.2f} |"
        )
    lineas += [
        "",
        "## LÃ­mites",
        "",
        "- La referencia es **Ã³ptica**, no verdad de campo: una cosecha, un anegamiento "
        "o un cambio de manejo tambiÃ©n bajan el NDVI. No distingue deforestaciÃ³n de "
        "otras pÃ©rdidas de vegetaciÃ³n.",
        "- Las ventanas de junio y octubre incluyen estacionalidad; parte del cambio "
        "Ã³ptico y del HV puede ser humedad, no cobertura.",
        "- El bootstrap remuestrea pÃ­xeles y no corrige del todo la autocorrelaciÃ³n "
        "espacial; el muestreo ya adelgaza la grilla.",
        "- NISAR tiene repeticiÃ³n de 12 dÃ­as: la fecha de cambio no es diaria.",
    ]
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
