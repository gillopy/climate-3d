"""Cambio de cobertura NISAR: ΔHV entre dos fechas del mismo track/frame.

La deforestacion y la cicatriz de incendio se ven como una caida del
backscatter cross-pol (HV) cuando el volumen del dosel pasa a superficie. El
script recorta las dos escenas en la misma grilla, promedia speckle (multilook
en potencia), calcula ΔHV en dB, le resta el corrimiento global del par, aplica
una mayoria 3x3 para no contar pixeles aislados y escribe:

- un PNG (delta, mascara sobre HV o composicion RGB),
- en el modo ``comparar``, las dos capas sueltas (``*_antes.png`` y
  ``*_despues.png``) que alimentan el comparador de barrido del visor,
- un JSON con hectareas de perdida/ganancia y los umbrales usados.

Dos cosas que el producto anterior no hacia y que dominan el resultado:

1. **Normalizacion por el corrimiento del par.** Dos pasadas no salen con el
   mismo nivel: calibracion, humedad y version de procesamiento mueven el
   histograma 3-4 dB. Un umbral fijo sin restar ese offset pinta el offset
   como perdida (el par 2026-06-28 -> 2026-08-27 venia 3,7 dB mas oscuro y
   marcaba el 37 % del area). La mediana de ΔHV es el offset.
2. **Multilook.** A 10 m el pixel es de una sola mirada: el ruido de speckle
   tiene σ ≈ 3-4 dB, mas grande que cualquier umbral util. Promediar en
   potencia (nunca en dB) a ~50 m baja σ a ~1,5 dB y deja el umbral por
   encima del piso de ruido.
3. **Confirmacion temporal.** Un desmonte no vuelve. `--confirmar-temporal N`
   vuelve a medir la caida contra la misma escena base en las N fechas
   posteriores del mismo track/frame que ya estan en disco (no descarga nada):
   el pixel sobrevive solo si sigue `--umbral` dB por debajo. `--recuperacion-db`
   permite aflojar cuanto puede achicarse la caida.

El indice de cambio sigue siendo ΔHV: medido contra la referencia NDVI de
Sentinel-2 en la caja del Este, da AUC 0,71 con multilook 5x5. RFDI (el indice
que la literatura L-band prefiere sobre bosque amazonico denso) aca discrimina
peor que el azar (AUC 0,41-0,47), asi que no se usa como detector.

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
import hls  # noqa: E402
import sentinel2  # noqa: E402

ROJO = np.array([205, 35, 35], dtype=np.uint8)
NARANJA = np.array([222, 138, 58], dtype=np.uint8)
AZUL = np.array([45, 95, 205], dtype=np.uint8)


def nivel_evidencia(optico_confirmado: bool, persistente: bool) -> tuple[str, str]:
    """Return an evidence label without presenting it as ground truth."""
    if optico_confirmado and persistente:
        return "high_confidence_candidate", "radar persistent + optical-supported; not field truth"
    if optico_confirmado:
        return "optical_supported", "radar change supported by optical vegetation loss; not field truth"
    if persistente:
        return "persistent_radar_candidate", "radar change persists in later local observations"
    return "radar_candidate", "single radar pair; no persistence or optical support"


def _guardar_panel(ruta: Path, rgb: np.ndarray, px: int) -> Path:
    """Guarda una capa suelta del comparador: sin pie ni barra de escala.

    El compuesto lleva las dos capas juntas y un pie con la leyenda; el visor
    necesita cada capa por separado para el barrido. Se guardan al tamano que
    ocupan dentro del compuesto para no duplicar el peso del PNG.
    """
    from PIL import Image  # import local: solo lo usa el modo comparar

    alto, ancho = rgb.shape[:2]
    ancho_salida, alto_salida = nisar.dimensiones(ancho, alto, px)
    imagen = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")
    if (ancho_salida, alto_salida) != (ancho, alto):
        imagen = imagen.resize((ancho_salida, alto_salida), Image.LANCZOS)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    imagen.save(ruta, "PNG", optimize=True)
    return ruta


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
    ap.add_argument("--umbral", type=float, default=2.0, help="caida minima de HV en dB")
    ap.add_argument("--hv-min", type=float, default=-15.5, help="HV minimo para considerar bosque")
    ap.add_argument(
        "--ml",
        type=int,
        default=0,
        help="ventana de multilook en potencia; 0 = automatica (~50 m de pixel)",
    )
    ap.add_argument(
        "--sin-normalizar",
        action="store_true",
        help="no restar el corrimiento global de ΔHV (solo para reproducir corridas viejas)",
    )
    ap.add_argument(
        "--bosque",
        default="hv",
        choices=("ndvi", "hv"),
        help="como decidir donde habia dosel antes del cambio",
    )
    ap.add_argument("--ndvi-bosque", type=float, default=0.50, help="NDVI minimo de bosque")
    ap.add_argument(
        "--ndvi-piso",
        type=float,
        default=0.30,
        help="NDVI minimo previo para confirmar una caida (descarta suelo ya desnudo)",
    )
    ap.add_argument(
        "--verificar-s2",
        action="store_true",
        help="confirmar la caida de HV con NDVI de Sentinel-2 (pre y post)",
    )
    ap.add_argument(
        "--optico",
        choices=("sentinel2", "hls", "auto"),
        default="sentinel2",
        help="proveedor óptico para NDVI: Sentinel-2, HLS L30/S30 o auto",
    )
    ap.add_argument(
        "--indices",
        default=None,
        help="ademas del cambio, escribir un panel NDVI/NDBI/NDWI/NBR (antes, despues, delta)",
    )
    ap.add_argument(
        "--confirmar-temporal",
        type=int,
        default=0,
        help="cuantas fechas posteriores exigir sin recuperacion de HV (0 = no)",
    )
    ap.add_argument(
        "--recuperacion-db",
        type=float,
        default=0.0,
        help="cuanto puede achicarse la caida original y seguir contando como perdida",
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
    ap.add_argument(
        "--ganancia",
        action="store_true",
        help="pintar y contar tambien el aumento de HV (por defecto solo perdida)",
    )
    ap.add_argument("--dias", type=int, default=15, help="ventana de Sentinel-2 en dias")
    ap.add_argument("--nubes", type=float, default=40.0, help="nubes maximas de Sentinel-2")
    ap.add_argument(
        "--max-items",
        type=int,
        default=4,
        help=(
            "items maximos de Sentinel-2 (medido: 2 items dan 97.4%% de cobertura "
            "y 8 dan 97.8%% por 65%% mas de tiempo)"
        ),
    )
    ap.add_argument("--rango", type=float, default=6.0, help="rango de la paleta de delta en dB")
    ap.add_argument("--out", required=True)
    ap.add_argument("--geojson", default=None)
    args = ap.parse_args(nisar.argv_bbox(sys.argv[1:]))

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

        mpp_x = abs(float(xs[-1] - xs[0])) / max(1, len(xs) - 1)
        mpp_y = abs(float(ys[-1] - ys[0])) / max(1, len(ys) - 1)
        mpp = mpp_x
        ml = max(1, int(args.ml)) if args.ml > 0 else nisar.ventana_para(mpp, 50.0, 5)
        if ml > 1:
            hv_antes = nisar.multilook(hv_antes, ml)
            hv_despues = nisar.multilook(hv_despues, ml)
            print(f"multilook {ml}x{ml} en potencia (~{ml * mpp:.0f} m de pixel)")

        db_antes = nisar.a_db(hv_antes)
        db_despues = nisar.a_db(hv_despues)
        delta = db_despues - db_antes
        valido = np.isfinite(delta)
        if not valido.any():
            px_antes = int(np.isfinite(db_antes).sum())
            px_despues = int(np.isfinite(db_despues).sum())
            detalle = (
                "La caja no tiene pixeles validos en las dos fechas.\n"
                f"  antes   ({Path(args.antes).name}): {px_antes} de {db_antes.size} px\n"
                f"  despues ({Path(args.despues).name}): {px_despues} de {db_despues.size} px\n"
            )
            if px_antes == 0 or px_despues == 0:
                detalle += (
                    "  Una escena no tiene datos en esa caja: pasa cuando la caja cae\n"
                    "  fuera de la huella con datos del granulo, o el producto la enmascara.\n"
                    "  Movela o achicala hacia el centro de la escena."
                )
            else:
                detalle += (
                    "  Las dos tienen datos pero no quedan alineados despues del\n"
                    "  multilook: revisa que sean el mismo track/frame y la misma version."
                )
            raise SystemExit(detalle)
        offset_db = 0.0
        if not args.sin_normalizar:
            offset_db = nisar.corrimiento_db(delta, valido)
            delta = delta - offset_db
            print(f"corrimiento del par: {offset_db:+.2f} dB (restado)")
            if abs(offset_db) >= 2.0:
                print(
                    "aviso: las dos fechas no estan al mismo nivel radiometrico "
                    f"({offset_db:+.2f} dB). Se normalizo, pero conviene revisar la "
                    "version de procesamiento de cada escena."
                )

        bosque_meta: dict = {"fuente": "hv", "ndvi_umbral": None, "items": []}
        pre_bosque = valido & (db_antes > float(args.hv_min))
        ndvi_pre = None
        ndvi_post = None
        optico_meta: dict = {
            "disponible": False,
            "fuente": None,
            "proveedor_solicitado": args.optico,
            "motivo": "",
            "dndvi_umbral": float(args.dndvi),
            "items_post": [],
        }
        modulo_grilla = hls if hls.DISPONIBLE else sentinel2
        transform, crs = modulo_grilla.grilla(xs, ys, rec_antes.epsg)

        def _proveedores_opticos():
            if args.optico == "sentinel2":
                return [("sentinel2", sentinel2, None)]
            if args.optico == "hls":
                return [("hls_l30", hls, "l30"), ("hls_s30", hls, "s30")]
            return [
                ("hls_l30", hls, "l30"),
                ("hls_s30", hls, "s30"),
                ("sentinel2", sentinel2, None),
            ]

        def _ndvi(fecha_texto: str) -> tuple[np.ndarray | None, list[dict], str]:
            """NDVI compuesto alrededor de una fecha; (None, [], motivo) si falla."""
            motivos = []
            for nombre, modulo, sensor in _proveedores_opticos():
                if not modulo.DISPONIBLE:
                    motivos.append(f"{nombre}: faltan dependencias")
                    continue
                try:
                    fecha = datetime.strptime(fecha_texto[:10], "%Y-%m-%d").date()
                    kwargs = {"sensor": sensor} if sensor else {}
                    items = modulo.buscar_items(
                        (oeste, sur, este, norte),
                        fecha,
                        int(args.dias),
                        float(args.nubes),
                        int(args.max_items),
                        **kwargs,
                    )
                    if not items:
                        motivos.append(f"sin {nombre} cerca de {fecha_texto[:10]}")
                        continue
                    ndvi, usados = modulo.componer_ndvi(
                        items,
                        (oeste, sur, este, norte),
                        db_antes.shape,
                        transform,
                        crs,
                        px,
                        **kwargs,
                    )
                    if ndvi is None or not np.isfinite(ndvi).any():
                        motivos.append(f"{nombre}: compuesto NDVI vacio")
                        continue
                    optico_meta["fuente"] = nombre
                    return ndvi, usados, ""
                except Exception as exc:  # noqa: BLE001 - provider optional
                    motivos.append(f"{nombre}: {type(exc).__name__}: {exc}")
            return None, [], "; ".join(motivos) or "sin proveedor óptico disponible"

        def _indices(fecha_texto: str):
            """NDVI, NDBI, NDWI y NBR compuestos; (None, [], motivo) si falla."""
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
                capas, usados = sentinel2.componer_indices(
                    items,
                    (oeste, sur, este, norte),
                    db_antes.shape,
                    transform,
                    crs,
                    px,
                )
                if not capas:
                    return None, usados, "el compuesto de indices quedo vacio"
                return capas, usados, ""
            except Exception as exc:  # noqa: BLE001 - el panel es opcional
                return None, [], f"{type(exc).__name__}: {exc}"

        if args.bosque == "ndvi" or args.verificar_s2:
            motivo = ""
            ndvi_pre, usados_pre, motivo = _ndvi(antes.fecha)
            bosque_meta["items"] = usados_pre
            if args.bosque == "ndvi":
                if ndvi_pre is not None:
                    pre_bosque = (
                        valido
                        & np.isfinite(ndvi_pre)
                        & (ndvi_pre > float(args.ndvi_bosque))
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
            elif motivo:
                # Verificar no debe cambiar la mascara de bosque: solo confirma.
                optico_meta["motivo"] = motivo

        perdida_radar = nisar.mayoria3(valido & pre_bosque & (delta < -umbral)) & valido

        temporal_meta: dict = {
            "solicitadas": max(0, int(args.confirmar_temporal)),
            "disponible": False,
            "motivo": "",
            "fechas": [],
            "umbral_db": umbral,
            "tolerancia_db": max(0.0, umbral - float(args.recuperacion_db)),
            "recuperados_ha": 0.0,
        }
        if temporal_meta["solicitadas"] > 0:
            posteriores = nisar.escenas_posteriores(
                despues.ruta, temporal_meta["solicitadas"]
            )
            if not posteriores:
                temporal_meta["motivo"] = (
                    "no hay fechas posteriores del mismo track/frame en la carpeta"
                )
                print(
                    "aviso: no hay fecha posterior para confirmar; la perdida "
                    "radar queda sin persistencia"
                )
            else:
                sobrevive = np.ones(valido.shape, dtype=bool)
                for ruta in posteriores:
                    with nisar.Escena(ruta) as conf:
                        if "HV" not in conf.pols:
                            temporal_meta["motivo"] = f"{ruta.stem} no tiene HV"
                            continue
                        rec_conf = conf.recortar("HV", args.bbox, px)
                        if not nisar.compatibles(rec_antes, rec_conf):
                            temporal_meta["motivo"] = f"{ruta.stem} no comparte grilla"
                            continue
                        hv_conf, _, _ = nisar.orientar(rec_conf)
                        if ml > 1:
                            hv_conf = nisar.multilook(hv_conf, ml)
                        db_conf = nisar.a_db(hv_conf)
                        # La caida se vuelve a medir contra la MISMA escena base.
                        # Si el pixel recupero, la caida se achica y deja de
                        # pasar el umbral; si sigue desmontado, sigue igual.
                        caida_conf = db_antes - db_conf
                        caida_conf = caida_conf - nisar.corrimiento_db(
                            caida_conf, np.isfinite(caida_conf)
                        )
                        # Sin dato en la fecha de control no se puede afirmar
                        # que recupero: se deja pasar en vez de descartar.
                        vigente = ~np.isfinite(caida_conf) | (
                            caida_conf > temporal_meta["tolerancia_db"]
                        )
                        sobrevive &= vigente
                        recuperado = ~vigente
                        temporal_meta["fechas"].append(
                            {
                                "granulo": ruta.stem,
                                "fecha": conf.fecha,
                                "recuperado_ha": round(
                                    nisar.hectareas(
                                        int((recuperado & perdida_radar).sum()),
                                        mpp_x,
                                        mpp_y,
                                    ),
                                    1,
                                ),
                            }
                        )
                if temporal_meta["fechas"]:
                    antes_px = int(perdida_radar.sum())
                    perdida_radar = perdida_radar & sobrevive
                    # La persistencia es pixel a pixel y deja huecos de 1 px
                    # dentro de un bloque que si siguio: se cierra con la misma
                    # mayoria 3x3 que ya usa el producto.
                    perdida_radar = nisar.mayoria3(perdida_radar) & valido
                    temporal_meta["disponible"] = True
                    temporal_meta["recuperados_ha"] = round(
                        nisar.hectareas(
                            antes_px - int(perdida_radar.sum()), mpp_x, mpp_y
                        ),
                        1,
                    )
                    print(
                        "temporal: HV sin recuperar en "
                        f"{len(temporal_meta['fechas'])} fecha(s) "
                        f"({', '.join(f['fecha'][:10] for f in temporal_meta['fechas'])}); "
                        f"se descartan {temporal_meta['recuperados_ha']:.0f} ha"
                    )
                elif not temporal_meta["motivo"]:
                    temporal_meta["motivo"] = "ninguna fecha posterior sirvio"
                    print(
                        "aviso: ninguna fecha posterior sirvio para confirmar; "
                        "la perdida radar queda sin persistencia"
                    )

        perdida = perdida_radar
        if args.verificar_s2:
            if ndvi_pre is None or not np.isfinite(ndvi_pre).any():
                optico_meta["motivo"] = optico_meta["motivo"] or "sin NDVI previo"
            else:
                ndvi_post, usados_post, motivo = _ndvi(despues.fecha)
                optico_meta["items_post"] = usados_post
                if ndvi_post is not None:
                    # La confirmacion es la CAIDA de NDVI, no un NDVI absoluto:
                    # en el Este la referencia de bosque da 0,45 de mediana en la
                    # estacion seca, asi que exigir NDVI > 0,55 dejaba pasar solo
                    # el 6 % del area. El piso solo descarta pixeles ya desnudos.
                    vegetado = ndvi_pre >= float(args.ndvi_piso)
                    confirmado = (
                        np.isfinite(ndvi_pre)
                        & np.isfinite(ndvi_post)
                        & vegetado
                        & ((ndvi_post - ndvi_pre) <= -float(args.dndvi))
                    )
                    perdida = perdida_radar & confirmado
                    optico_meta["disponible"] = True
                    optico_meta["ndvi_piso"] = float(args.ndvi_piso)
                    optico_meta["vegetado_pct"] = round(
                        100.0 * float(vegetado.sum()) / max(1, int(valido.sum())), 2
                    )
                    print(
                        f"optico: NDVI cae >= {args.dndvi:g} en "
                        f"{100.0 * (perdida.sum() / max(1, perdida_radar.sum())):.0f}% "
                        f"de la perdida radar (piso NDVI {args.ndvi_piso:g})"
                    )
                else:
                    optico_meta["motivo"] = motivo
        if not args.verificar_s2 or not optico_meta["disponible"]:
            optico_meta["motivo"] = optico_meta["motivo"] or "sin verificar"

        confirmado = args.verificar_s2 and optico_meta["disponible"]
        persistente = bool(temporal_meta["disponible"])
        nivel, nivel_explicacion = nivel_evidencia(confirmado, persistente)

        if args.indices:
            capas_antes, usados_a, motivo_a = _indices(antes.fecha)
            capas_despues, usados_d, motivo_d = _indices(despues.fecha)
            if capas_antes is None or capas_despues is None:
                print(
                    "aviso: sin panel de indices "
                    f"({motivo_a or motivo_d or 'sin datos'})"
                )
            else:
                try:
                    import poster_indices

                    titulo = (
                        f"Sentinel-2 L2A · {antes.fecha[:10]} vs {despues.fecha[:10]} · "
                        f"{len(usados_a)}+{len(usados_d)} item(s)"
                    )
                    panel = poster_indices.dibujar_panel(
                        capas_antes, capas_despues, args.indices, titulo=titulo
                    )
                    print(f"indices: {panel}")
                except Exception as exc:  # noqa: BLE001 - el panel es opcional
                    print(
                        "aviso: no pude dibujar el panel "
                        f"({type(exc).__name__}: {exc})"
                    )

        candidato_mask = perdida_radar & ~perdida
        if args.ganancia:
            ganancia = nisar.mayoria3(valido & (delta > umbral)) & valido
        else:
            # El aumento de HV simetrico es casi todo speckle: pintarlo llena el
            # mapa de azul y tapa la perdida. Se cuenta solo si se pide.
            ganancia = np.zeros(valido.shape, dtype=bool)

        pixeles_validos = int(valido.sum())
        area_px_ha = mpp_x * mpp_y / 10000.0
        minimo_px = 0
        candidato = candidato_mask
        if float(args.mmu_ha) > 0:
            minimo_px = max(1, int(round(float(args.mmu_ha) / area_px_ha)))
            perdida = nisar.filtrar_mmu(perdida, minimo_px)
            candidato = nisar.filtrar_mmu(candidato, minimo_px)
            ganancia = nisar.filtrar_mmu(ganancia, minimo_px)
        perdida_px = int(perdida.sum())
        candidato_px = int(candidato.sum())
        perdida_radar_ha = nisar.hectareas(int(perdida_radar.sum()), mpp_x, mpp_y)
        ganancia_px = int(ganancia.sum())
        bosque_px = int(pre_bosque.sum())
        area_ha = nisar.hectareas(pixeles_validos, mpp_x, mpp_y)
        perdida_ha = nisar.hectareas(perdida_px, mpp_x, mpp_y)
        candidato_ha = nisar.hectareas(candidato_px, mpp_x, mpp_y)
        ganancia_ha = nisar.hectareas(ganancia_px, mpp_x, mpp_y)
        bosque_ha = nisar.hectareas(bosque_px, mpp_x, mpp_y)
        perdida_pct = 100.0 * perdida_px / pixeles_validos
        perdida_bosque_pct = 100.0 * perdida_px / max(1, bosque_px)
        delta_medio = float(np.nanmean(delta[perdida])) if perdida_px else 0.0

        paneles_meta: dict[str, str] = {}
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
            gris_despues = np.where(candidato[..., None], NARANJA, gris_despues)
            gris_despues = np.where(perdida[..., None], ROJO, gris_despues)
            gris_despues = np.where(ganancia[..., None], AZUL, gris_despues)
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
            for x0_panel, texto in (
                (0, f"ANTES  {(antes.fecha or antes.ruta.stem)[:10]}"),
                (
                    ancho_panel + separacion,
                    f"DESPUÉS  {(despues.fecha or despues.ruta.stem)[:10]}",
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
            # Capas sueltas para el comparador de barrido del visor. El nombre
            # (``_antes``/``_despues``) es el contrato con el frontend: no corta
            # el compuesto, apila las dos capas y las arrastra.
            paneles_meta = {
                "antes": _guardar_panel(
                    salida.with_name(f"{salida.stem}_antes.png"),
                    gris_antes,
                    max(1, px // 2),
                ).name,
                "despues": _guardar_panel(
                    salida.with_name(f"{salida.stem}_despues.png"),
                    gris_despues,
                    max(1, px // 2),
                ).name,
            }
        else:
            vmin, vmax = nisar.limites(db_despues)
            base = nisar.paleta("gray", nisar.normalizar(db_despues, vmin, vmax))
            rgb = np.where(valido[..., None], base, 0)
            rgb = np.where(candidato[..., None], NARANJA, rgb)
            rgb = np.where(perdida[..., None], ROJO, rgb)
            rgb = np.where(ganancia[..., None], AZUL, rgb)

        if confirmado and persistente:
            leyenda_mascara = (
                "rojo = pérdida confirmada y persistente · naranja = candidata"
            )
        elif confirmado:
            leyenda_mascara = "rojo = pérdida confirmada · naranja = candidata"
        elif persistente:
            leyenda_mascara = "rojo = cambio persistente (sin confirmar óptico)"
        else:
            leyenda_mascara = "rojo = pérdida (cambio de HV, sin confirmar)"
        lineas = [
            f"NISAR GCOV · cambio HV · {antes.fecha or antes.ruta.stem} -> "
            f"{despues.fecha or despues.ruta.stem}",
            f"perdida {perdida_ha:.0f} ha ({perdida_pct:.1f}%) · "
            f"dHV < -{umbral:g} dB · offset {offset_db:+.1f} dB · "
            f"{mpp:.0f} m/px · ml {ml}",
            {
                "mascara": leyenda_mascara,
                "delta": "rojo = caída de HV · azul = aumento",
                "rgb": "R = antes · G = después · B = ΔHV",
                "comparar": f"izquierda = antes · derecha = después · {leyenda_mascara}",
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
            **({"paneles": paneles_meta} if paneles_meta else {}),
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
            "indice": "dHV",
            "umbral_db": umbral,
            "hv_min_db": float(args.hv_min),
            "multilook": ml,
            "normalizado": not args.sin_normalizar,
            "offset_db": round(offset_db, 2),
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
            "perdida_candidata_ha": round(candidato_ha, 1),
            "perdida_radar_ha": round(perdida_radar_ha, 1),
            "perdida_pct": round(perdida_pct, 2),
            "perdida_bosque_pct": round(perdida_bosque_pct, 2),
            "ganancia_ha": round(ganancia_ha, 1),
            "ganancia_activa": bool(args.ganancia),
            "delta_medio_perdida_db": round(delta_medio, 2),
            "optico": {
                **optico_meta,
                "verificado": bool(confirmado),
            },
            "evidencia": {
                "nivel": nivel,
                "explicacion": nivel_explicacion,
                "es_verdad_de_campo": False,
            },
            "temporal": temporal_meta,
            "mmu_ha": float(args.mmu_ha),
            "mmu_px": minimo_px,
            "pixeles_validos": pixeles_validos,
        }
        nisar.guardar_json(salida, meta)

    print(
        f"perdida {perdida_ha:.0f} ha ({perdida_pct:.1f}% del area, "
        f"{perdida_bosque_pct:.1f}% del bosque) | ganancia {ganancia_ha:.0f} ha"
    )
    print(f"evidencia: {nivel} (no es verdad de campo)")
    if confirmado:
        print(
            f"optico: {perdida_ha:.0f} ha confirmadas + {candidato_ha:.0f} ha "
            f"candidatas de {perdida_radar_ha:.0f} ha radar"
        )
    elif args.verificar_s2:
        print(f"aviso: sin confirmacion optica ({optico_meta.get('motivo')})")
    print(f"listo: {salida} ({ancho}x{alto} px)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
