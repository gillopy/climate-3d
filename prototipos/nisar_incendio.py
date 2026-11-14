"""Cicatriz de incendio NISAR: caída de HV pre/post + focos FIRMS encima.

El radar no ve fuego activo: ve la cicatriz cuando el volumen del dosel pasa a
superficie. Este producto compara HV entre dos fechas del mismo track/frame,
marca la pérdida y, si se pide, superpone los focos de calor de NASA FIRMS del
intervalo entre las dos fechas. Los focos son contexto: la cicatriz es NISAR.

Ojo: un incendio puede BRILLAR en HH al principio (suelo y doble rebote); por eso
se mira HV y se exige que la fecha "antes" tenga dosel.

    .venv\\Scripts\\python.exe prototipos\\nisar_incendio.py \
        --antes ANTES.h5 --despues DESPUES.h5 --bbox -55.6,-24.5,-55.2,-23.9 \
        --px 1400 --firms --out cicatriz.png
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
sys.path.insert(0, str(RAIZ))

import nisar  # noqa: E402
import sentinel2  # noqa: E402
from firms import color_foco  # noqa: E402


def _dia(fecha: str) -> datetime | None:
    """Fecha naive, como las usa el módulo de FIRMS."""
    try:
        return datetime.strptime(fecha[:10], "%Y-%m-%d")
    except (TypeError, ValueError):
        return None


def _bajar_focos(caja, desde: datetime, hasta: datetime, destino: Path):
    """Focos FIRMS del intervalo; nunca rompe el producto si falla."""
    try:
        from descargar.firms import descargar as bajar_firms

        _, focos = bajar_firms(
            caja,
            None,
            destino,
            fuente="viirs",
            desde=desde,
            hasta=hasta,
        )
        return focos
    except SystemExit as exc:
        print(f"aviso: FIRMS no disponible ({exc}); sigo sin focos")
    except Exception as exc:  # noqa: BLE001 - red o API
        print(f"aviso: FIRMS fallo ({type(exc).__name__}: {exc}); sigo sin focos")
    return []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--antes", required=True)
    ap.add_argument("--despues", required=True)
    ap.add_argument("--bbox", required=True)
    ap.add_argument("--px", type=int, default=1400)
    ap.add_argument("--umbral", type=float, default=3.0, help="caída mínima de HV en dB")
    ap.add_argument("--hv-min", type=float, default=-15.5, help="HV mínimo para dosel")
    ap.add_argument(
        "--bosque",
        default="hv",
        choices=("ndvi", "hv"),
        help="cómo decidir dónde había dosel antes del fuego",
    )
    ap.add_argument("--ndvi-bosque", type=float, default=0.55, help="NDVI mínimo de bosque")
    ap.add_argument("--dias", type=int, default=15, help="ventana de Sentinel-2 en días")
    ap.add_argument("--nubes", type=float, default=40.0, help="nubes máximas de Sentinel-2")
    ap.add_argument("--max-items", type=int, default=8, help="ítems máximos de Sentinel-2")
    ap.add_argument("--firms", action="store_true", help="superponer focos FIRMS")
    ap.add_argument("--out", required=True)
    ap.add_argument("--geojson", default=None)
    args = ap.parse_args(nisar.argv_bbox(sys.argv[1:]))

    px = max(800, min(int(args.px), 4096))
    salida = Path(args.out)
    umbral = abs(float(args.umbral))
    hv_min = float(args.hv_min)
    oeste, sur, este, norte = nisar.caja(args.bbox)

    print(f"abriendo antes={Path(args.antes).name}")
    print(f"abriendo despues={Path(args.despues).name}")
    with nisar.Escena(args.antes) as antes, nisar.Escena(args.despues) as despues:
        for escena, nombre in ((antes, "antes"), (despues, "despues")):
            if "HV" not in escena.pols:
                raise SystemExit(f"La escena {nombre} no tiene HV.")
        if (antes.track, antes.frame) != (despues.track, despues.frame):
            raise SystemExit(
                f"Las escenas no son del mismo track/frame: "
                f"{antes.track}/{antes.frame} vs {despues.track}/{despues.frame}."
            )

        rec_antes = antes.recortar("HV", args.bbox, px)
        rec_despues = despues.recortar("HV", args.bbox, px)
        if not nisar.compatibles(rec_antes, rec_despues):
            raise SystemExit(
                "Las dos escenas no comparten grilla. Usá dos fechas del mismo "
                "track/frame y de la misma colección."
            )

        hv_antes, xs, ys = nisar.orientar(rec_antes)
        hv_despues, _, _ = nisar.orientar(rec_despues)
        db_antes = nisar.a_db(hv_antes)
        db_despues = nisar.a_db(hv_despues)
        delta = db_despues - db_antes
        valido = np.isfinite(delta)
        bosque_meta: dict = {"fuente": "hv", "ndvi_umbral": None, "items": []}
        pre_bosque = valido & (db_antes > hv_min)
        if args.bosque == "ndvi":
            ndvi = None
            motivo = ""
            if not sentinel2.DISPONIBLE:
                motivo = "faltan rasterio/pystac-client"
            else:
                try:
                    fecha = datetime.strptime(antes.fecha[:10], "%Y-%m-%d").date()
                    transform, crs = sentinel2.grilla(xs, ys, rec_antes.epsg)
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
                            db_antes.shape,
                            transform,
                            crs,
                            px,
                        )
                        bosque_meta["items"] = usados
                    else:
                        motivo = "sin Sentinel-2 en la ventana"
                except Exception as exc:  # noqa: BLE001 - sin óptico se sigue con HV
                    motivo = f"{type(exc).__name__}: {exc}"
            if ndvi is not None and np.isfinite(ndvi).any():
                pre_bosque = (
                    valido & np.isfinite(ndvi) & (ndvi > float(args.ndvi_bosque))
                )
                bosque_meta["fuente"] = "ndvi"
                bosque_meta["ndvi_umbral"] = float(args.ndvi_bosque)
                print(
                    f"bosque: NDVI > {args.ndvi_bosque:g} "
                    f"({100.0 * pre_bosque.sum() / max(1, int(valido.sum())):.1f}% del área)"
                )
            else:
                bosque_meta["fuente"] = f"hv (sin NDVI: {motivo or 'sin datos'})"
                print(f"aviso: máscara de bosque por HV ({motivo or 'sin datos'})")

        cicatriz = (
            nisar.mayoria3(valido & pre_bosque & (delta < -umbral)) & valido
        )

        mpp_x = abs(float(xs[-1] - xs[0])) / max(1, len(xs) - 1)
        mpp_y = abs(float(ys[0] - ys[-1])) / max(1, len(ys) - 1)
        cicatriz_px = int(cicatriz.sum())
        valido_px = int(valido.sum())
        if valido_px == 0:
            raise SystemExit("La caja no tiene píxeles válidos.")
        cicatriz_ha = nisar.hectareas(cicatriz_px, mpp_x, mpp_y)
        area_ha = nisar.hectareas(valido_px, mpp_x, mpp_y)
        cicatriz_pct = 100.0 * cicatriz_px / valido_px
        delta_medio = float(np.nanmean(delta[cicatriz])) if cicatriz_px else 0.0

        focos = []
        confianzas_lista: list[str] = []
        if args.firms:
            desde = _dia(antes.fecha)
            hasta = _dia(despues.fecha)
            if desde and hasta:
                hasta = hasta + timedelta(days=1)
                print(f"FIRMS {desde:%Y-%m-%d} a {hasta:%Y-%m-%d}")
                crudos = _bajar_focos(
                    (oeste, sur, este, norte),
                    desde,
                    hasta,
                    salida.with_name(salida.stem + "_firms.csv"),
                )
                vistos = set()
                for foco in crudos:
                    clave = (round(foco.lon, 3), round(foco.lat, 3))
                    if clave in vistos:
                        continue
                    vistos.add(clave)
                    focos.append((foco.lon, foco.lat, color_foco(foco.confianza)))
                    confianzas_lista.append(foco.confianza)
                print(f"FIRMS: {len(focos)} focos únicos")
            else:
                print("aviso: no pude leer las fechas; sigo sin FIRMS")

        vmin, vmax = nisar.limites(db_despues)
        rgb = nisar.paleta("gray", nisar.normalizar(db_despues, vmin, vmax))
        rgb = np.where(valido[..., None], rgb, 0)
        rgb = np.where(
            cicatriz[..., None],
            np.array([210, 45, 30], dtype=np.uint8),
            rgb,
        )
        lineas = [
            f"NISAR GCOV · cicatriz de incendio · {antes.fecha or antes.ruta.stem} -> "
            f"{despues.fecha or despues.ruta.stem}",
            f"cicatriz {cicatriz_ha:.0f} ha ({cicatriz_pct:.1f}%) · "
            f"{len(focos)} focos FIRMS · umbral {umbral:g} dB · {mpp_x:.0f} m/px",
            "rojo = cicatriz · puntos = focos FIRMS"
            if args.firms
            else "rojo = cicatriz (FIRMS apagado)",
        ]
        ancho, alto = nisar.guardar(
            rgb,
            salida,
            lineas,
            mpp_x,
            px,
            geojson=args.geojson,
            epsg=rec_antes.epsg,
            x0=rec_antes.x0,
            x1=rec_antes.x1,
            y0=rec_antes.y0,
            y1=rec_antes.y1,
            focos=focos,
        )
        confianzas = Counter(confianzas_lista)
        meta = {
            "producto": "incendio",
            "antes": antes.ruta.stem,
            "despues": despues.ruta.stem,
            "fecha_antes": antes.fecha,
            "fecha_despues": despues.fecha,
            "track": antes.track,
            "frame": antes.frame,
            "bbox": [oeste, sur, este, norte],
            "epsg": rec_antes.epsg,
            "mpp": round(mpp_x, 3),
            "px": [ancho, alto],
            "umbral_db": umbral,
            "hv_min_db": hv_min,
            "area_ha": round(area_ha, 1),
            "cicatriz_ha": round(cicatriz_ha, 1),
            "cicatriz_pct": round(cicatriz_pct, 2),
            "bosque": {
                **bosque_meta,
                "fraccion_area_pct": round(
                    100.0 * float(pre_bosque.sum()) / max(1, valido_px), 2
                ),
            },
            "delta_medio_db": round(delta_medio, 2),
            "firms": bool(args.firms),
            "focos": len(focos),
            "focos_por_confianza": dict(confianzas),
        }
        nisar.guardar_json(salida, meta)

    print(
        f"cicatriz {cicatriz_ha:.0f} ha ({cicatriz_pct:.1f}%) | "
        f"{len(focos)} focos FIRMS | dHV {delta_medio:.1f} dB"
    )
    print(f"listo: {salida} ({ancho}x{alto} px)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
