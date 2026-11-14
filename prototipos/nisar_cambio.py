"""Cambio de cobertura NISAR: ΔHV entre dos fechas del mismo track/frame.

La deforestacion y la cicatriz de incendio se ven como una caida del
backscatter cross-pol (HV) cuando el volumen del dosel pasa a superficie. El
script recorta las dos escenas en la misma grilla, calcula ΔHV en dB, aplica
una mayoria 3x3 para no contar pixeles aislados y escribe:

- un PNG (delta, mascara sobre HV o composicion RGB),
- un JSON con hectareas de perdida/ganancia y los umbrales usados.

Ojo: un incendio puede iluminar HH al principio; este producto mira HV, que es
la banda que el SAR Handbook marca como sensible al volumen del bosque.

    .venv\\Scripts\\python.exe prototipos\\nisar_cambio.py \
        --antes ANTES.h5 --despues DESPUES.h5 \
        --bbox -55.6,-24.5,-55.2,-23.9 --px 2400 --out cambio.png
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))

import nisar  # noqa: E402
import sentinel2  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--antes", required=True)
    ap.add_argument("--despues", required=True)
    ap.add_argument("--bbox", required=True)
    ap.add_argument("--px", type=int, default=2400)
    ap.add_argument(
        "--modo",
        default="mascara",
        choices=("delta", "mascara", "rgb", "comparar"),
        help="comparar = antes | despues con la mascara encima",
    )
    ap.add_argument("--umbral", type=float, default=3.0, help="caida minima de HV en dB")
    ap.add_argument("--hv-min", type=float, default=-15.5, help="HV minimo para considerar bosque")
    ap.add_argument(
        "--bosque",
        default="hv",
        choices=("ndvi", "hv"),
        help="como decidir donde habia dosel antes del cambio",
    )
    ap.add_argument("--ndvi-bosque", type=float, default=0.55, help="NDVI minimo de bosque")
    ap.add_argument(
        "--verificar-s2",
        action="store_true",
        help="confirmar la caida de HV con NDVI de Sentinel-2 (pre y post)",
    )
    ap.add_argument(
        "--dndvi",
        type=float,
        default=0.20,
        help="caida minima de NDVI para confirmar la perdida",
    )
    ap.add_argument(
        "--mmu-ha",
        type=float,
        default=0.0,
        help="unidad minima de mapeo: descarta parches menores a estas hectareas",
    )
    ap.add_argument("--dias", type=int, default=15, help="ventana de Sentinel-2 en dias")
    ap.add_argument("--nubes", type=float, default=40.0, help="nubes maximas de Sentinel-2")
    ap.add_argument("--max-items", type=int, default=8, help="items maximos de Sentinel-2")
    ap.add_argument("--rango", type=float, default=6.0, help="rango de la paleta de delta en dB")
    ap.add_argument("--out", required=True)
    ap.add_argument("--geojson", default=None)
    args = ap.parse_args()

    px = max(800, min(int(args.px), 4096))
    salida = Path(args.out)
    umbral = abs(float(args.umbral))
    rango = max(0.5, float(args.rango))
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
                "Las dos escenas no comparten grilla. Usa dos fechas del mismo "
                "track/frame y la misma version de procesamiento."
            )

        hv_antes, xs, ys = nisar.orientar(rec_antes)
        hv_despues, _, _ = nisar.orientar(rec_despues)
        db_antes = nisar.a_db(hv_antes)
        db_despues = nisar.a_db(hv_despues)
        delta = db_despues - db_antes
        valido = np.isfinite(delta)

        bosque_meta: dict = {"fuente": "hv", "ndvi_umbral": None, "items": []}
        pre_bosque = valido & (db_antes > float(args.hv_min))
        ndvi_pre = None
        ndvi_post = None
        optico_meta: dict = {
            "disponible": False,
            "motivo": "",
            "dndvi_umbral": float(args.dndvi),
            "items_post": [],
        }
        transform, crs = sentinel2.grilla(xs, ys, rec_antes.epsg)

        def _ndvi(fecha_texto: str) -> tuple[np.ndarray | None, list[dict], str]:
            """NDVI compuesto alrededor de una fecha; (None, [], motivo) si falla."""
            if not sentinel2.DISPONIBLE:
                return None, [], "faltan rasterio/pystac-client"
            try:
                fecha = datetime.strptime(fecha_texto[:10], "%Y-%m-%d").date()
                items = sentinel2.buscar_items(
                    (oeste, sur, este, norte),
                    fecha,
                    int(args.dias),
                    float(args.nubes),
                    int(args.max_items),
                )
                if not items:
                    return None, [], f"sin Sentinel-2 cerca de {fecha_texto[:10]}"
                ndvi, usados = sentinel2.componer_ndvi(
                    items,
                    (oeste, sur, este, norte),
                    db_antes.shape,
                    transform,
                    crs,
                    px,
                )
                if ndvi is None or not np.isfinite(ndvi).any():
                    return None, usados, "el compuesto NDVI quedo vacio"
                return ndvi, usados, ""
            except Exception as exc:  # noqa: BLE001 - sin optico se sigue con HV
                return None, [], f"{type(exc).__name__}: {exc}"

        if args.bosque == "ndvi" or args.verificar_s2:
            motivo = ""
            ndvi_pre, usados_pre, motivo = _ndvi(antes.fecha)
            bosque_meta["items"] = usados_pre
            if ndvi_pre is not None:
                pre_bosque = (
                    valido & np.isfinite(ndvi_pre) & (ndvi_pre > float(args.ndvi_bosque))
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
                optico_meta["motivo"] = motivo

        perdida_radar = nisar.mayoria3(valido & pre_bosque & (delta < -umbral)) & valido
        perdida = perdida_radar
        if args.verificar_s2:
            if ndvi_pre is None or not np.isfinite(ndvi_pre).any():
                optico_meta["motivo"] = optico_meta["motivo"] or "sin NDVI previo"
            else:
                ndvi_post, usados_post, motivo = _ndvi(despues.fecha)
                optico_meta["items_post"] = usados_post
                if ndvi_post is not None:
                    confirmado = (
                        np.isfinite(ndvi_pre)
                        & np.isfinite(ndvi_post)
                        & (ndvi_pre >= float(args.ndvi_bosque))
                        & ((ndvi_post - ndvi_pre) <= -float(args.dndvi))
                    )
                    perdida = perdida_radar & confirmado
                    optico_meta["disponible"] = True
                    print(
                        f"optico: NDVI cae >= {args.dndvi:g} en "
                        f"{100.0 * (perdida.sum() / max(1, perdida_radar.sum())):.0f}% "
                        "de la perdida radar"
                    )
                else:
                    optico_meta["motivo"] = motivo
        if not args.verificar_s2 or not optico_meta["disponible"]:
            optico_meta["motivo"] = optico_meta["motivo"] or "sin verificar"
        ganancia = nisar.mayoria3(valido & (delta > umbral)) & valido

        mpp_x = abs(float(xs[-1] - xs[0])) / max(1, len(xs) - 1)
        mpp_y = abs(float(ys[-1] - ys[0])) / max(1, len(ys) - 1)
        mpp = mpp_x

        pixeles_validos = int(valido.sum())
        if pixeles_validos == 0:
            raise SystemExit("La caja no tiene pixeles validos en las dos fechas.")
        area_px_ha = mpp_x * mpp_y / 10000.0
        minimo_px = 0
        if float(args.mmu_ha) > 0:
            minimo_px = max(1, int(round(float(args.mmu_ha) / area_px_ha)))
            perdida = nisar.filtrar_mmu(perdida, minimo_px)
            ganancia = nisar.filtrar_mmu(ganancia, minimo_px)
        perdida_px = int(perdida.sum())
        perdida_radar_ha = nisar.hectareas(int(perdida_radar.sum()), mpp_x, mpp_y)
        ganancia_px = int(ganancia.sum())
        bosque_px = int(pre_bosque.sum())
        area_ha = nisar.hectareas(pixeles_validos, mpp_x, mpp_y)
        perdida_ha = nisar.hectareas(perdida_px, mpp_x, mpp_y)
        ganancia_ha = nisar.hectareas(ganancia_px, mpp_x, mpp_y)
        bosque_ha = nisar.hectareas(bosque_px, mpp_x, mpp_y)
        perdida_pct = 100.0 * perdida_px / pixeles_validos
        perdida_bosque_pct = 100.0 * perdida_px / max(1, bosque_px)
        delta_medio = float(np.nanmean(delta[perdida])) if perdida_px else 0.0

        if args.modo == "delta":
            norm = np.clip((delta + rango) / (2.0 * rango), 0.0, 1.0)
            rgb = nisar.paleta("RdBu", norm)
            rgb = np.where(valido[..., None], rgb, 0)
        elif args.modo == "rgb":
            vmin_a, vmax_a = nisar.limites(db_antes)
            vmin_d, vmax_d = nisar.limites(db_despues)
            rojo = nisar.normalizar(db_antes, vmin_a, vmax_a)
            verde = nisar.normalizar(db_despues, vmin_d, vmax_d)
            azul = np.clip((delta + rango) / (2.0 * rango), 0.0, 1.0)
            rgb = (np.dstack([rojo, verde, azul]) * 255.0).astype(np.uint8)
            rgb = np.where(valido[..., None], rgb, 0)
        elif args.modo == "comparar":
            # Dos paneles con la MISMA escala de grises: antes | despues+mascara.
            juntos = np.concatenate(
                [db_antes[np.isfinite(db_antes)], db_despues[np.isfinite(db_despues)]]
            )
            vmin, vmax = nisar.limites(juntos)
            gris_antes = nisar.paleta("gray", nisar.normalizar(db_antes, vmin, vmax))
            gris_antes = np.where(np.isfinite(db_antes)[..., None], gris_antes, 0)
            gris_despues = nisar.paleta(
                "gray", nisar.normalizar(db_despues, vmin, vmax)
            )
            gris_despues = np.where(np.isfinite(db_despues)[..., None], gris_despues, 0)
            gris_despues = np.where(
                perdida[..., None],
                np.array([205, 35, 35], dtype=np.uint8),
                gris_despues,
            )
            gris_despues = np.where(
                ganancia[..., None],
                np.array([45, 95, 205], dtype=np.uint8),
                gris_despues,
            )
            alto_panel, ancho_panel = gris_antes.shape[:2]
            separacion = max(6, ancho_panel // 150)
            hueco = np.zeros((alto_panel, separacion, 3), dtype=np.uint8)
            hueco[:, :] = (8, 9, 10)
            rgb = np.concatenate([gris_antes, hueco, gris_despues], axis=1)
            # Etiquetas de panel dibujadas sobre el compuesto antes de guardarlo.
            from PIL import Image, ImageDraw  # import local: solo lo usa este modo

            lienzo = Image.fromarray(rgb)
            dibujo = ImageDraw.Draw(lienzo)
            fuente = nisar._fuente(max(12, int(alto_panel * 0.022)))
            verificado = bool(args.verificar_s2 and optico_meta["disponible"])
            etiqueta_despues = (
                "rojo = pérdida confirmada" if verificado else "rojo = pérdida"
            )
            for x0_panel, texto in (
                (0, f"ANTES  {(antes.fecha or antes.ruta.stem)[:10]}"),
                (
                    ancho_panel + separacion,
                    f"DESPUÉS  {(despues.fecha or despues.ruta.stem)[:10]}"
                    f"  ·  {etiqueta_despues}",
                ),
            ):
                caja = dibujo.textbbox((0, 0), texto, font=fuente)
                dibujo.rectangle(
                    [
                        x0_panel + 4,
                        6,
                        x0_panel + 12 + (caja[2] - caja[0]),
                        14 + (caja[3] - caja[1]),
                    ],
                    fill=(8, 9, 10),
                )
                dibujo.text(
                    (x0_panel + 8, 8), texto, font=fuente, fill=(247, 248, 248)
                )
            rgb = np.asarray(lienzo)
            px = min(4096, rgb.shape[1])
        else:
            vmin, vmax = nisar.limites(db_despues)
            base = nisar.paleta("gray", nisar.normalizar(db_despues, vmin, vmax))
            rgb = np.where(valido[..., None], base, 0)
            rgb = np.where(
                perdida[..., None],
                np.array([205, 35, 35], dtype=np.uint8),
                rgb,
            )
            rgb = np.where(
                ganancia[..., None],
                np.array([45, 95, 205], dtype=np.uint8),
                rgb,
            )

        confirmado = args.verificar_s2 and optico_meta["disponible"]
        lineas = [
            f"NISAR GCOV · cambio HV · {antes.fecha or antes.ruta.stem} -> "
            f"{despues.fecha or despues.ruta.stem}",
            f"perdida {perdida_ha:.0f} ha ({perdida_pct:.1f}%) · "
            f"umbral {umbral:g} dB · {mpp:.0f} m/px · EPSG:{rec_antes.epsg}",
            {
                "mascara": (
                    "rojo = pérdida confirmada con NDVI · azul = ganancia"
                    if confirmado
                    else "rojo = pérdida · azul = ganancia"
                ),
                "delta": "rojo = caída de HV · azul = aumento",
                "rgb": "R = antes · G = después · B = ΔHV",
                "comparar": "izquierda = antes · derecha = después con el cambio encima",
            }[args.modo],
        ]
        ancho, alto = nisar.guardar(
            rgb,
            salida,
            lineas,
            mpp,
            px,
            geojson=None if args.modo == "comparar" else args.geojson,
            epsg=rec_antes.epsg,
            x0=rec_antes.x0,
            x1=rec_antes.x1,
            y0=rec_antes.y0,
            y1=rec_antes.y1,
        )
        meta = {
            "producto": "cambio",
            "antes": antes.ruta.stem,
            "despues": despues.ruta.stem,
            "fecha_antes": antes.fecha,
            "fecha_despues": despues.fecha,
            "coleccion_antes": antes.ruta.parent.name,
            "coleccion_despues": despues.ruta.parent.name,
            "track": antes.track,
            "frame": antes.frame,
            "bbox": [float(v) for v in args.bbox.split(",")],
            "px": [ancho, alto],
            "epsg": rec_antes.epsg,
            "mpp": round(mpp, 3),
            "modo": args.modo,
            "umbral_db": umbral,
            "hv_min_db": float(args.hv_min),
            "area_ha": round(area_ha, 1),
            "bosque_ha": round(bosque_ha, 1),
            "bosque": {
                **bosque_meta,
                "bosque_ha": round(bosque_ha, 1),
                "fraccion_area_pct": round(
                    100.0 * bosque_px / max(1, pixeles_validos), 2
                ),
            },
            "perdida_ha": round(perdida_ha, 1),
            "perdida_radar_ha": round(perdida_radar_ha, 1),
            "perdida_pct": round(perdida_pct, 2),
            "perdida_bosque_pct": round(perdida_bosque_pct, 2),
            "ganancia_ha": round(ganancia_ha, 1),
            "delta_medio_perdida_db": round(delta_medio, 2),
            "optico": {
                **optico_meta,
                "verificado": bool(confirmado),
            },
            "mmu_ha": float(args.mmu_ha),
            "mmu_px": minimo_px,
            "pixeles_validos": pixeles_validos,
        }
        nisar.guardar_json(salida, meta)

    print(
        f"perdida {perdida_ha:.0f} ha ({perdida_pct:.1f}% del area, "
        f"{perdida_bosque_pct:.1f}% del bosque) | ganancia {ganancia_ha:.0f} ha"
    )
    if confirmado:
        print(
            f"optico: {perdida_ha:.0f} ha confirmadas de {perdida_radar_ha:.0f} ha "
            f"radar ({100.0 * perdida_ha / max(1e-9, perdida_radar_ha):.0f}%)"
        )
    elif args.verificar_s2:
        print(f"aviso: sin confirmacion optica ({optico_meta.get('motivo')})")
    print(f"listo: {salida} ({ancho}x{alto} px)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
