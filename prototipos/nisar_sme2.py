"""Mapa de humedad del suelo NISAR SME2 recortado a una caja.

SME2 viene en EASE-Grid 2.0 (EPSG:6933) a 200 m, con tres estimaciones de
humedad: DSG (desagregacion), PMI (inversion de modelo fisico) y TSR (razon de
series temporales). Se recorta por los ejes de longitud/latitud que trae el
producto y se dibuja la capa elegida. El relleno -9999 se descarta y,
opcionalmente, se ocultan los pixeles con quality flag distinto de 0.

    .venv\\Scripts\\python.exe prototipos\\nisar_sme2.py --h5 ESCENA.h5 \
        --bbox -58.2,-26.5,-54.9,-23.6 --algoritmo DSG --out sme2.png
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import h5py
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))

import nisar  # noqa: E402  (argv_bbox: la caja empieza con "-")

FONDO = "#0b0c0d"
TINTA = "#d0d6e0"
TENUE = "#8a8f98"
FILETE = "#23252a"
RELLENO = -9999.0
ALGORITMOS = ("DSG", "PMI", "TSR")


def _caja(texto: str) -> tuple[float, float, float, float]:
    try:
        partes = [float(valor) for valor in texto.split(",")]
    except (AttributeError, ValueError) as exc:
        raise SystemExit("--bbox debe ser oeste,sur,este,norte") from exc
    if len(partes) != 4:
        raise SystemExit("--bbox debe tener 4 numeros")
    oeste, sur, este, norte = partes
    if not (-180 <= oeste < este <= 180 and -90 <= sur < norte <= 90):
        raise SystemExit("--bbox esta fuera de rango o invertida")
    return oeste, sur, este, norte


def _fecha(nombre: str) -> str:
    encontrado = re.search(r"_(\d{8})T", nombre)
    if not encontrado:
        return ""
    dia = encontrado.group(1)
    return f"{dia[:4]}-{dia[4:6]}-{dia[6:]}"


def _borde(ax, ruta: str | None) -> None:
    """Dibuja el contorno de Paraguay si el GeoJSON esta disponible."""
    if not ruta:
        return
    try:
        datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    for feature in datos.get("features", []):
        geometria = feature.get("geometry") or {}
        tipo = geometria.get("type")
        coordenadas = geometria.get("coordinates") or []
        if tipo == "Polygon":
            poligonos = [coordenadas]
        elif tipo == "MultiPolygon":
            poligonos = coordenadas
        else:
            continue
        for poligono in poligonos:
            for anillo in poligono:
                if len(anillo) < 2:
                    continue
                ax.plot(
                    [punto[0] for punto in anillo],
                    [punto[1] for punto in anillo],
                    color="#f7f8f8",
                    linewidth=0.8,
                    alpha=0.65,
                    zorder=5,
                )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--h5", required=True, help="escena NISAR SME2 (.h5)")
    ap.add_argument("--bbox", required=True, help="oeste,sur,este,norte")
    ap.add_argument("--algoritmo", default="DSG", choices=ALGORITMOS)
    ap.add_argument(
        "--solo-calidad",
        action="store_true",
        help="oculta los pixeles con retrievalQualityFlag distinto de 0",
    )
    ap.add_argument("--px", type=int, default=2400)
    ap.add_argument("--out", required=True)
    ap.add_argument("--geojson", default=None)
    args = ap.parse_args(nisar.argv_bbox(sys.argv[1:]))

    oeste, sur, este, norte = _caja(args.bbox)
    algoritmo = args.algoritmo.upper()
    ancho_px = max(800, min(int(args.px), 4096))
    salida = Path(args.out)
    escena = Path(args.h5)

    print(f"abriendo {escena.name}")
    with h5py.File(escena, "r") as f:
        rejilla = f["science/LSAR/SME2/grids"]
        lon = np.asarray(rejilla["longitude"][...], dtype=float)
        lat = np.asarray(rejilla["latitude"][...], dtype=float)
        grupo = rejilla[f"algorithmCandidates/{algoritmo}"]
        humedad = np.asarray(grupo["soilMoisture"][...], dtype=float)
        calidad = np.asarray(grupo["retrievalQualityFlag"][...])
        incertidumbre = np.asarray(
            grupo["soilMoistureUncertainty"][...], dtype=float
        )
        try:
            mpp_x = abs(float(grupo["xCoordinateSpacing"][()]))
            mpp_y = abs(float(grupo["yCoordinateSpacing"][()]))
        except (KeyError, TypeError, ValueError):
            mpp_x = mpp_y = 200.0
        try:
            epsg = int(rejilla["projection"].attrs.get("epsg_code", 6933))
        except (KeyError, TypeError, ValueError):
            epsg = 6933

        print(f"recortando caja {oeste:g},{sur:g},{este:g},{norte:g}")
        filas = np.where((lat >= sur) & (lat <= norte))[0]
        columnas = np.where((lon >= oeste) & (lon <= este))[0]
        if filas.size == 0 or columnas.size == 0:
            raise SystemExit("La caja no intersecta la escena SME2.")
        humedad = humedad[np.ix_(filas, columnas)]
        calidad = calidad[np.ix_(filas, columnas)]
        incertidumbre = incertidumbre[np.ix_(filas, columnas)]
        lon_c = lon[columnas]
        lat_c = lat[filas]

        # Ejes ascendentes: pcolormesh espera coordenadas ordenadas.
        if lon_c.size > 1 and lon_c[0] > lon_c[-1]:
            lon_c = lon_c[::-1]
            humedad = humedad[:, ::-1]
            calidad = calidad[:, ::-1]
            incertidumbre = incertidumbre[:, ::-1]
        if lat_c.size > 1 and lat_c[0] > lat_c[-1]:
            lat_c = lat_c[::-1]
            humedad = humedad[::-1, :]
            calidad = calidad[::-1, :]
            incertidumbre = incertidumbre[::-1, :]

        valido = np.isfinite(humedad) & (humedad != RELLENO)
        if not valido.any():
            raise SystemExit("La caja no tiene pixeles validos de humedad.")
        limpio = valido & (calidad == 0)
        analisis = limpio if args.solo_calidad else valido
        if not analisis.any():
            raise SystemExit(
                "La caja no tiene pixeles con calidad limpia; proba sin "
                "--solo-calidad."
            )

        valores = humedad[analisis]
        media = float(np.mean(valores))
        p10, p50, p90 = [float(v) for v in np.percentile(valores, [10, 50, 90])]
        area_px = mpp_x * mpp_y / 10000.0
        area_ha = float(analisis.sum()) * area_px
        cobertura = 100.0 * float(valido.sum()) / float(valido.size)
        calidad_pct = 100.0 * float(limpio.sum()) / float(max(1, valido.sum()))
        incertidumbre_media = 0.0
        inc_validas = incertidumbre[analisis]
        inc_validas = inc_validas[
            np.isfinite(inc_validas) & (inc_validas != RELLENO)
        ]
        if inc_validas.size:
            incertidumbre_media = float(np.mean(inc_validas))
        fecha = _fecha(escena.stem)
        print(
            f"estadisticas: {analisis.sum()} px validos, media {media:.3f} m3/m3, "
            f"calidad limpia {calidad_pct:.1f}%"
        )

        datos = np.ma.masked_where(~analisis, humedad)
        alto_px = max(500, int(ancho_px * max(1, datos.shape[0]) / max(1, datos.shape[1])))
        fig, ax = plt.subplots(
            figsize=(ancho_px / 100.0, alto_px / 100.0), dpi=100
        )
        fig.patch.set_facecolor(FONDO)
        ax.set_facecolor(FONDO)
        mapa_cmap = plt.get_cmap("YlGnBu").copy()
        mapa_cmap.set_bad(FONDO)
        mapa = ax.pcolormesh(
            lon_c,
            lat_c,
            datos,
            shading="auto",
            cmap=mapa_cmap,
            vmin=0.0,
            vmax=0.6,
        )
        _borde(ax, args.geojson)
        ax.set_xlim(float(lon_c.min()), float(lon_c.max()))
        ax.set_ylim(float(lat_c.min()), float(lat_c.max()))
        ax.set_xlabel("longitud", color=TENUE, fontsize=9)
        ax.set_ylabel("latitud", color=TENUE, fontsize=9)
        ax.tick_params(colors=TENUE, labelsize=8)
        for borde_ax in ax.spines.values():
            borde_ax.set_color(FILETE)
        barra = fig.colorbar(mapa, ax=ax, fraction=0.04, pad=0.02)
        barra.set_label("m³/m³", color=TENUE, fontsize=9)
        barra.ax.tick_params(colors=TENUE, labelsize=8)
        barra.outline.set_edgecolor(FILETE)
        ax.set_title(
            f"NISAR SME2 · humedad del suelo ({algoritmo})",
            color=TINTA,
            fontsize=13,
            loc="left",
        )
        ax.text(
            0.0,
            1.015,
            f"{fecha or escena.stem[:24]} · {mpp_x:.0f} m/px · EASE-Grid 2.0 "
            f"(EPSG:{epsg}) · {cobertura:.0f}% con dato",
            transform=ax.transAxes,
            color=TENUE,
            fontsize=8.5,
            ha="left",
        )
        fig.text(
            0.01,
            0.005,
            f"medio {media:.3f} · p10-p90 {p10:.3f}-{p90:.3f} · "
            f"{area_ha:.0f} ha validas · incertidumbre media "
            f"{incertidumbre_media:.3f} · PROVISIONAL",
            color=TENUE,
            fontsize=8,
        )
        print("dibujando mapa")
        fig.tight_layout(rect=(0, 0.02, 1, 0.98))
        salida.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(salida, facecolor=FONDO, bbox_inches="tight")
        plt.close(fig)

    ancho, alto = Image.open(salida).size
    meta = {
        "producto": "sme2",
        "escena": escena.stem,
        "fecha": fecha,
        "algoritmo": algoritmo,
        "solo_calidad": bool(args.solo_calidad),
        "bbox": [oeste, sur, este, norte],
        "px": [int(ancho), int(alto)],
        "epsg": epsg,
        "mpp": round(mpp_x, 1),
        "humedad_media": round(media, 4),
        "humedad_p10": round(p10, 4),
        "humedad_p50": round(p50, 4),
        "humedad_p90": round(p90, 4),
        "humedad_rango": [0.0, 0.6],
        "incertidumbre_media": round(incertidumbre_media, 4),
        "cobertura_valida_pct": round(cobertura, 1),
        "calidad_limpia_pct": round(calidad_pct, 1),
        "area_valida_ha": round(area_ha, 1),
        "pixeles": int(analisis.sum()),
    }
    salida.with_suffix(".json").write_text(
        json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    print(
        f"listo: {salida} ({ancho}x{alto} px, {area_ha:.0f} ha, "
        f"media {media:.3f} m3/m3)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
