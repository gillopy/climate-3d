"""Serie temporal NISAR GCOV + CUSUM para saber *cuándo* cambió el HV.

Descubre todas las escenas locales del mismo track/frame en la carpeta de la
coleccion, las apila en la misma grilla y produce:

- ``*_serie.png``: HV/HH medio en dB, RVI medio y hectareas de cambio por fecha.
- ``*_mediana.png``: compuesto mediano de HV (potencia) en dB.
- ``*_cusum.png``: mapa de fecha de cambio (color = momento) sobre la mediana.
- ``*.json``: serie, umbrales, hectareas y distribucion por fecha.

El CUSUM sigue la idea del SAR Handbook: para cada corte entre fechas se compara
la media de HV antes y despues; el corte con la caida mas fuerte es la fecha de
cambio. Todo se promedia en potencia, nunca en dB.

    .venv\\Scripts\\python.exe prototipos\\nisar_serie.py --h5 ESCENA.h5 \
        --coleccion-dir DATOS/nisar/NISAR_L2_GCOV_V1 --track 82 --frame 101 \
        --bbox -55.6,-24.5,-55.2,-23.9 --px 1200 --out serie
"""
from __future__ import annotations

import argparse
import re
import sys
import warnings
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))

import nisar  # noqa: E402
import sentinel2  # noqa: E402

warnings.filterwarnings("ignore", category=RuntimeWarning)

_PATRON = re.compile(r"_(\d{3})_(\d{3})_([AD])_(\d{3})_")


def _track_frame(nombre: str) -> tuple[int, int] | None:
    encontrado = _PATRON.search(nombre)
    if not encontrado:
        return None
    _, track, _, frame = encontrado.groups()
    return int(track), int(frame)


def _escenas_locales(
    carpetas: list[Path],
    seleccionada: Path,
    track: int,
    frame: int,
    maximo: int,
    seleccionadas: set[str] | None = None,
) -> list[Path]:
    """Escenas .h5 del track/frame en las carpetas, en orden cronologico.

    Se pueden pasar varias carpetas porque NISAR publica las fechas viejas como
    PROVISIONAL y las nuevas como VALIDATED: una serie de meses mezcla las dos.

    Con ``--fechas`` se filtran sobre *todas* las escenas del track/frame, no
    sobre las ultimas ``maximo``: una fecha vieja elegida a mano tambien tiene que
    entrar aunque haya muchas mas nuevas en disco.
    """
    candidatas: list[Path] = []
    for carpeta in carpetas:
        if carpeta.is_dir():
            candidatas.extend(sorted(carpeta.glob("*.h5")))
    candidatas.append(seleccionada)
    vistas: dict[str, Path] = {}
    for ruta in candidatas:
        if not ruta.is_file():
            continue
        par = _track_frame(ruta.stem)
        if par is None or par != (track, frame):
            continue
        vistas[ruta.stem] = ruta
    ordenadas = sorted(vistas.values(), key=lambda r: r.stem)
    if seleccionadas:
        return [ruta for ruta in ordenadas if ruta.stem in seleccionadas]
    return ordenadas[-maximo:]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--h5", required=True, help="escena seleccionada")
    ap.add_argument(
        "--coleccion-dir",
        action="append",
        required=True,
        help="carpeta con los .h5 de una coleccion (repetible)",
    )
    ap.add_argument("--track", type=int, default=0)
    ap.add_argument("--frame", type=int, default=0)
    ap.add_argument("--bbox", required=True)
    ap.add_argument("--px", type=int, default=1200)
    ap.add_argument("--umbral", type=float, default=3.0)
    ap.add_argument("--hv-min", type=float, default=-15.5)
    ap.add_argument(
        "--bosque",
        default="hv",
        choices=("ndvi", "hv"),
        help="como decidir donde habia dosel antes del cambio",
    )
    ap.add_argument("--ndvi-bosque", type=float, default=0.55, help="NDVI minimo de bosque")
    ap.add_argument("--dias", type=int, default=15, help="ventana de Sentinel-2 en dias")
    ap.add_argument("--nubes", type=float, default=40.0, help="nubes maximas de Sentinel-2")
    ap.add_argument("--max-items", type=int, default=8, help="items maximos de Sentinel-2")
    ap.add_argument("--max", type=int, default=12)
    ap.add_argument("--out", required=True, help="prefijo de salida (sin extension)")
    ap.add_argument("--fechas", default="", help="IDs separados por coma; vacío = todas")
    ap.add_argument("--geojson", default=None)
    args = ap.parse_args()

    seleccionada = Path(args.h5)
    track, frame = int(args.track), int(args.frame)
    if not track or not frame:
        par = _track_frame(seleccionada.stem)
        if par is None:
            raise SystemExit("No pude deducir track/frame del nombre; pasalos con --track/--frame")
        track, frame = par

    px = max(800, min(int(args.px), 1600))
    umbral = abs(float(args.umbral))
    hv_min = float(args.hv_min)
    oeste, sur, este, norte = nisar.caja(args.bbox)
    prefijo = Path(args.out)
    if prefijo.suffix:
        prefijo = prefijo.with_suffix("")
    chart = prefijo.with_name(prefijo.name + "_serie.png")
    mediana_png = prefijo.with_name(prefijo.name + "_mediana.png")
    cusum_png = prefijo.with_name(prefijo.name + "_cusum.png")

    seleccionadas = {parte.strip() for parte in args.fechas.split(",") if parte.strip()}
    escenas = _escenas_locales(
        [Path(carpeta) for carpeta in args.coleccion_dir],
        seleccionada,
        track,
        frame,
        max(2, int(args.max)),
        seleccionadas,
    )
    if len(escenas) < 2:
        raise SystemExit(
            f"Hay {len(escenas)} escena(s) local(es) para track {track} frame {frame} "
            "con la selección actual. Elegí al menos dos fechas de la misma colección."
        )

    fechas: list[str] = []
    ids: list[str] = []
    hv_stack: list[np.ndarray] = []
    hh_stack: list[np.ndarray] = []
    xs: np.ndarray | None = None
    ys: np.ndarray | None = None
    epsg: int | None = None
    referencia: tuple[int, int] | None = None

    for ruta in escenas:
        print(f"leyendo {ruta.stem}")
        with nisar.Escena(ruta) as escena:
            if "HV" not in escena.pols:
                raise SystemExit(f"{ruta.name} no tiene HV.")
            rec_hv = escena.recortar("HV", args.bbox, px)
            hv, xs_actual, ys_actual = nisar.orientar(rec_hv)
            rec_hh = None
            if "HH" in escena.pols:
                rec_hh = escena.recortar("HH", args.bbox, px)
                hh, _, _ = nisar.orientar(rec_hh)
                if hh.shape != hv.shape:
                    raise SystemExit(f"HH y HV no coinciden en {ruta.name}.")
            else:
                hh = None

            if referencia is None:
                referencia = hv.shape
                xs, ys, epsg = xs_actual, ys_actual, rec_hv.epsg
            elif hv.shape != referencia:
                raise SystemExit(
                    f"{ruta.name} no comparte la grilla de las otras escenas. "
                    "Usá fechas del mismo track/frame y misma colección."
                )
            fechas.append(escena.fecha or ruta.stem)
            ids.append(ruta.stem)
            hv_stack.append(hv.astype(np.float32))
            hh_stack.append(hh.astype(np.float32) if hh is not None else None)  # type: ignore[arg-type]

    if xs is None or ys is None or epsg is None:
        raise SystemExit("No pude leer ninguna escena.")

    hv_pila = np.stack(hv_stack)  # (N, H, W) potencia lineal
    tiene_hh = all(hh is not None for hh in hh_stack)
    hh_pila = np.stack(hh_stack) if tiene_hh else None  # type: ignore[arg-type]

    mpp_x = abs(float(xs[-1] - xs[0])) / max(1, len(xs) - 1)
    mpp_y = abs(float(ys[0] - ys[-1])) / max(1, len(ys) - 1)
    area_px_ha = mpp_x * mpp_y / 10000.0

    # --- serie por fecha (promedios en potencia) --------------------------
    hv_medio = np.nanmean(hv_pila, axis=(1, 2))
    hv_db = 10.0 * np.log10(np.where(hv_medio > 0, hv_medio, np.nan))
    hh_db = None
    if hh_pila is not None:
        hh_medio = np.nanmean(hh_pila, axis=(1, 2))
        hh_db = 10.0 * np.log10(np.where(hh_medio > 0, hh_medio, np.nan))
    rvi_medio = np.full(len(fechas), np.nan, dtype=np.float64)
    if hh_pila is not None:
        for indice in range(len(fechas)):
            valores = nisar.rvi(hh_pila[indice], hv_pila[indice])
            validos = valores[np.isfinite(valores)]
            if validos.size:
                rvi_medio[indice] = float(np.mean(validos))

    # --- CUSUM: caida de HV antes/despues de cada corte -------------------
    n = len(fechas)
    valido = np.isfinite(hv_pila).sum(axis=0) >= max(2, n - 1)
    mejor_caida = np.full(hv_pila.shape[1:], np.inf, dtype=np.float32)
    mejor_corte = np.zeros(hv_pila.shape[1:], dtype=np.int16)
    for corte in range(1, n):
        antes = np.nanmean(hv_pila[:corte], axis=0)
        despues = np.nanmean(hv_pila[corte:], axis=0)
        caida = nisar.a_db(despues) - nisar.a_db(antes)
        mejores = np.isfinite(caida) & (caida < mejor_caida)
        mejor_caida = np.where(mejores, caida, mejor_caida)
        mejor_corte = np.where(mejores, corte, mejor_corte)

    # La mascara de bosque sale del promedio en potencia de las dos primeras
    # fechas: una sola escena tiene demasiado speckle para decidir donde hay
    # dosel. Si hay Sentinel-2, el NDVI manda: el HV solo no separa bosque de
    # cultivo.
    base = np.nanmean(hv_pila[: min(2, n)], axis=0)
    bosque_meta: dict = {"fuente": "hv", "ndvi_umbral": None, "items": []}
    pre_bosque = np.isfinite(base) & (nisar.a_db(base) > hv_min)
    if args.bosque == "ndvi":
        ndvi = None
        motivo = ""
        if not sentinel2.DISPONIBLE:
            motivo = "faltan rasterio/pystac-client"
        else:
            try:
                fecha = datetime.strptime(fechas[0][:10], "%Y-%m-%d").date()
                transform, crs = sentinel2.grilla(xs, ys, epsg)
                items = sentinel2.buscar_items(
                    (oeste, sur, este, norte),
                    fecha,
                    int(args.dias),
                    float(args.nubes),
                    int(args.max_items),
                )
                if items:
                    ndvi, usados = sentinel2.componer_ndvi(
                        items,
                        (oeste, sur, este, norte),
                        base.shape,
                        transform,
                        crs,
                        px,
                    )
                    bosque_meta["items"] = usados
                else:
                    motivo = "sin Sentinel-2 en la ventana"
            except Exception as exc:  # noqa: BLE001 - sin optico se sigue con HV
                motivo = f"{type(exc).__name__}: {exc}"
        if ndvi is not None and np.isfinite(ndvi).any():
            pre_bosque = (
                np.isfinite(base)
                & np.isfinite(ndvi)
                & (ndvi > float(args.ndvi_bosque))
            )
            bosque_meta["fuente"] = "ndvi"
            bosque_meta["ndvi_umbral"] = float(args.ndvi_bosque)
            print(
                f"bosque: NDVI > {args.ndvi_bosque:g} "
                f"({100.0 * pre_bosque.sum() / max(1, int(valido.sum())):.1f}% del area)"
            )
        else:
            bosque_meta["fuente"] = f"hv (sin NDVI: {motivo or 'sin datos'})"
            print(f"aviso: mascara de bosque por HV ({motivo or 'sin datos'})")
    cambio = (
        nisar.mayoria3(
            valido & pre_bosque & np.isfinite(mejor_caida) & (mejor_caida < -umbral)
        )
        & valido
    )
    cambio_ha = float(cambio.sum()) * area_px_ha
    area_ha = float(valido.sum()) * area_px_ha
    por_fecha: dict[str, float] = {}
    for corte in range(1, n):
        hectareas = float(((mejor_corte == corte) & cambio).sum()) * area_px_ha
        if hectareas > 0:
            por_fecha[fechas[corte]] = round(hectareas, 1)

    # --- compuesto mediano y mapa CUSUM -----------------------------------
    hv_mediana = np.nanmedian(hv_pila, axis=0)
    db_mediana = nisar.a_db(hv_mediana)
    vmin, vmax = nisar.limites(db_mediana)
    rgb_mediana = nisar.paleta("gray", nisar.normalizar(db_mediana, vmin, vmax))
    rgb_mediana = np.where(np.isfinite(db_mediana)[..., None], rgb_mediana, 0)
    lineas_mediana = [
        f"NISAR GCOV · HV mediana de {n} fechas · {fechas[0]} -> {fechas[-1]}",
        f"dB {vmin:.1f} a {vmax:.1f} · {mpp_x:.0f} m/px · EPSG:{epsg}",
        "gris = HV mediana (potencia)",
    ]
    ancho, alto = nisar.guardar(
        rgb_mediana,
        mediana_png,
        lineas_mediana,
        mpp_x,
        px,
        geojson=args.geojson,
        epsg=epsg,
        x0=float(min(xs[0], xs[-1])),
        x1=float(max(xs[0], xs[-1])),
        y0=float(min(ys[0], ys[-1])),
        y1=float(max(ys[0], ys[-1])),
    )

    rgb_cusum = nisar.paleta("gray", nisar.normalizar(db_mediana, vmin, vmax))
    rgb_cusum = np.where(np.isfinite(db_mediana)[..., None], rgb_cusum, 0)
    if cambio.any():
        if n == 2:
            color = np.array([220, 45, 45], dtype=np.uint8)
            rgb_cusum = np.where(cambio[..., None], color, rgb_cusum)
        else:
            indice = 0.1 + 0.8 * (
                (mejor_corte.astype(np.float32) - 1.0) / max(1, n - 2)
            )
            color = nisar.paleta("turbo", np.clip(indice, 0.0, 1.0))
            rgb_cusum = np.where(cambio[..., None], color, rgb_cusum)
    lineas_cusum = [
        f"NISAR GCOV · CUSUM HV · cambio {cambio_ha:.0f} ha · umbral {umbral:g} dB",
        f"{n} fechas · {fechas[0]} -> {fechas[-1]} · {mpp_x:.0f} m/px · EPSG:{epsg}",
        "color = fecha de cambio (temprano -> tarde)",
    ]
    nisar.guardar(
        rgb_cusum,
        cusum_png,
        lineas_cusum,
        mpp_x,
        px,
        geojson=args.geojson,
        epsg=epsg,
        x0=float(min(xs[0], xs[-1])),
        x1=float(max(xs[0], xs[-1])),
        y0=float(min(ys[0], ys[-1])),
        y1=float(max(ys[0], ys[-1])),
    )

    # --- grafico: HV/HH, RVI y cambio por fecha ---------------------------
    fig, (ax1, ax2, ax3) = plt.subplots(
        3, 1, figsize=(12, 8.5), dpi=150, sharex=True,
        gridspec_kw={"height_ratios": [2.2, 1.6, 1.4]},
    )
    fig.patch.set_facecolor("#0b0c0d")
    for ax in (ax1, ax2, ax3):
        ax.set_facecolor("#0b0c0d")
        ax.tick_params(colors="#8a8f98", labelsize=8)
        for borde in ax.spines.values():
            borde.set_color("#23252a")
        ax.grid(color="#23252a", linewidth=0.7, alpha=0.7)
    x = np.arange(n)
    ax1.plot(x, hv_db, color="#3fb950", marker="o", linewidth=1.6, label="HV")
    if hh_db is not None:
        ax1.plot(x, hh_db, color="#5e6ad2", marker="o", linewidth=1.4, label="HH")
    ax1.set_ylabel("backscatter (dB)", color="#d0d6e0", fontsize=8)
    ax1.legend(facecolor="#161718", edgecolor="#23252a", labelcolor="#d0d6e0", fontsize=8)
    ax2.plot(x, rvi_medio, color="#d29922", marker="o", linewidth=1.6)
    ax2.set_ylabel("RVI medio", color="#d0d6e0", fontsize=8)
    ax2.set_ylim(0, max(1.5, float(np.nanmax(rvi_medio)) * 1.1 if np.isfinite(rvi_medio).any() else 1.5))
    barras = [por_fecha.get(fecha, 0.0) for fecha in fechas]
    ax3.bar(x, barras, color="#f85149", width=0.7)
    ax3.set_ylabel("cambio (ha)", color="#d0d6e0", fontsize=8)
    if not any(barras):
        ax3.text(0.5, 0.5, "sin cambios sobre el umbral", transform=ax3.transAxes,
                 ha="center", va="center", color="#8a8f98", fontsize=9)
    etiquetas = [fecha[:10] for fecha in fechas]
    ax3.set_xticks(x)
    ax3.set_xticklabels(etiquetas, rotation=45, ha="right", color="#d0d6e0", fontsize=7)
    fig.suptitle(
        f"NISAR GCOV · serie temporal · track {track} frame {frame} · {n} fechas",
        color="#f7f8f8", fontsize=11,
    )
    fig.tight_layout()
    chart.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(chart, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)

    meta = {
        "producto": "serie",
        "track": track,
        "frame": frame,
        "coleccion": Path(args.coleccion_dir[0]).name,
        "colecciones": sorted({ruta.parent.name for ruta in escenas}),
        "fechas": fechas,
        "escenas": ids,
        "bbox": [float(v) for v in args.bbox.split(",")],
        "epsg": epsg,
        "mpp": [round(mpp_x, 3), round(mpp_y, 3)],
        "px": [ancho, alto],
        "serie": [
            {
                "fecha": fechas[i],
                "hv_db": round(float(hv_db[i]), 2) if np.isfinite(hv_db[i]) else None,
                "hh_db": round(float(hh_db[i]), 2) if hh_db is not None and np.isfinite(hh_db[i]) else None,
                "rvi": round(float(rvi_medio[i]), 3) if np.isfinite(rvi_medio[i]) else None,
            }
            for i in range(n)
        ],
        "cusum": {
            "umbral_db": umbral,
            "hv_min_db": hv_min,
            "area_ha": round(area_ha, 1),
            "cambio_ha": round(cambio_ha, 1),
            "por_fecha": por_fecha,
        },
        "bosque": {
            **bosque_meta,
            "fraccion_area_pct": round(
                100.0 * float(pre_bosque.sum()) / max(1, int(valido.sum())), 2
            ),
        },
        "archivos": {
            "serie": str(chart),
            "mediana": str(mediana_png),
            "cusum": str(cusum_png),
        },
    }
    nisar.guardar_json(prefijo, meta)

    print(f"serie: {n} fechas | HV {hv_db[0]:.1f} -> {hv_db[-1]:.1f} dB")
    print(f"cusum: cambio {cambio_ha:.0f} ha ({100 * cambio_ha / max(1e-9, area_ha):.1f}%)")
    print(f"listo: {chart} | {mediana_png} | {cusum_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
