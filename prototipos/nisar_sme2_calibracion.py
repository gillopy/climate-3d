"""Comparacion/validacion interna de las tres capas de humedad NISAR SME2.

No inventa una capa calibrada: recorta la misma caja sobre DSG, PMI y TSR y
escribe un informe con cobertura, calidad, medianas y comparaciones por pares
(bias, RMSE y correlacion). Sirve para decidir que capa usar y para documentar
por que el producto PROVISIONAL no se puede calibrar en absoluto sin verdad de
campo.

    .venv\\Scripts\\python.exe prototipos\\nisar_sme2_calibracion.py \
        --h5 ESCENA.h5 --bbox -55.491943,-25.083111,-54.610291,-24.246965 \
        --out sme2_calibracion.png
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


def _comparar(
    escena: Path,
    oeste: float,
    sur: float,
    este: float,
    norte: float,
    ancho_px: int,
    salida: Path,
    geojson: str | None,
) -> int:
    print(f"abriendo {escena.name}")
    with h5py.File(escena, "r") as f:
        rejilla = f["science/LSAR/SME2/grids"]
        lon = np.asarray(rejilla["longitude"][...], dtype=float)
        lat = np.asarray(rejilla["latitude"][...], dtype=float)
        filas = np.where((lat >= sur) & (lat <= norte))[0]
        columnas = np.where((lon >= oeste) & (lon <= este))[0]
        if filas.size == 0 or columnas.size == 0:
            raise SystemExit("La caja no intersecta la escena SME2.")
        r0, r1 = int(filas[0]), int(filas[-1]) + 1
        c0, c1 = int(columnas[0]), int(columnas[-1]) + 1
        lon_c = lon[c0:c1]
        lat_c = lat[r0:r1]
        invertir_lon = lon_c.size > 1 and lon_c[0] > lon_c[-1]
        invertir_lat = lat_c.size > 1 and lat_c[0] > lat_c[-1]
        if invertir_lon:
            lon_c = lon_c[::-1]
        if invertir_lat:
            lat_c = lat_c[::-1]

        datos: dict[str, dict] = {}
        for algoritmo in ALGORITMOS:
            grupo = rejilla[f"algorithmCandidates/{algoritmo}"]
            humedad = np.asarray(
                grupo["soilMoisture"][r0:r1, c0:c1], dtype=float
            )
            calidad = np.asarray(grupo["retrievalQualityFlag"][r0:r1, c0:c1])
            incertidumbre = np.asarray(
                grupo["soilMoistureUncertainty"][r0:r1, c0:c1], dtype=float
            )
            if invertir_lon:
                humedad = humedad[:, ::-1]
                calidad = calidad[:, ::-1]
                incertidumbre = incertidumbre[:, ::-1]
            if invertir_lat:
                humedad = humedad[::-1, :]
                calidad = calidad[::-1, :]
                incertidumbre = incertidumbre[::-1, :]
            valido = np.isfinite(humedad) & (humedad != RELLENO)
            limpio = valido & (calidad == 0)
            valores = humedad[valido]
            inc_validas = incertidumbre[
                valido & np.isfinite(incertidumbre) & (incertidumbre != RELLENO)
            ]
            mediana = float(np.median(valores)) if valores.size else None
            p10 = float(np.percentile(valores, 10)) if valores.size else None
            p90 = float(np.percentile(valores, 90)) if valores.size else None
            datos[algoritmo] = {
                "humedad": humedad,
                "valido": valido,
                "limpio": limpio,
                "mediana": mediana,
                "p10": p10,
                "p90": p90,
                "valido_pct": 100.0 * float(valido.mean()),
                "limpio_pct": 100.0 * float(limpio.sum()) / max(1, valido.sum()),
                "incertidumbre_media": (
                    float(inc_validas.mean()) if inc_validas.size else None
                ),
            }
            print(
                f"{algoritmo}: mediana {mediana:.3f} · "
                f"{datos[algoritmo]['valido_pct']:.1f}% valido · "
                f"{datos[algoritmo]['limpio_pct']:.1f}% limpio"
            )

        def comparar(a: str, b: str, solo_limpio: bool) -> dict | None:
            A, B = datos[a], datos[b]
            mascara = (
                (A["limpio"] & B["limpio"])
                if solo_limpio
                else (A["valido"] & B["valido"])
            )
            if int(mascara.sum()) < 2:
                return None
            va = A["humedad"][mascara]
            vb = B["humedad"][mascara]
            diferencia = va - vb
            correlacion = (
                float(np.corrcoef(va, vb)[0, 1])
                if float(np.std(va)) > 0 and float(np.std(vb)) > 0
                else 0.0
            )
            return {
                "n": int(mascara.sum()),
                "bias": float(np.mean(diferencia)),
                "mediana": float(np.median(diferencia)),
                "rmse": float(np.sqrt(np.mean(diferencia * diferencia))),
                "corr": correlacion,
            }

        pares: dict[str, dict] = {}
        for a, b in (("DSG", "PMI"), ("TSR", "PMI"), ("DSG", "TSR")):
            clave = f"{a.lower()}_{b.lower()}"
            pares[clave] = {
                "validos": comparar(a, b, False),
                "limpios": comparar(a, b, True),
            }
            print(f"{a}-{b}: validos {pares[clave]['validos']} · limpios {pares[clave]['limpios']}")

        mpp_x = 200.0
        try:
            mpp_x = abs(
                float(rejilla["algorithmCandidates/DSG/xCoordinateSpacing"][()])
            )
        except (KeyError, TypeError, ValueError):
            pass
        try:
            epsg = int(rejilla["projection"].attrs.get("epsg_code", 6933))
        except (KeyError, TypeError, ValueError):
            epsg = 6933
        fecha = _fecha(escena.stem)

        dsg_pmi = pares["dsg_pmi"]["limpios"] or pares["dsg_pmi"]["validos"] or {}
        if dsg_pmi:
            recomendacion = (
                "PMI con quality flag 0 es la capa recomendada para esta caja. "
                f"DSG-PMI: bias {dsg_pmi['bias']:+.3f} m3/m3, RMSE "
                f"{dsg_pmi['rmse']:.3f}, correlacion {dsg_pmi['corr']:.2f}. "
                "Las capas no coinciden pixel a pixel y TSR no trae pixeles con "
                "quality flag 0 en esta escena. El producto es PROVISIONAL y no "
                "hay verdad de campo: es una validacion interna, no una "
                "calibracion absoluta."
            )
        else:
            recomendacion = (
                "No hay suficientes pixeles para comparar DSG contra PMI en esta "
                "caja. El producto es PROVISIONAL: revisar cobertura y calidad "
                "antes de usarlo."
            )
        print(f"recomendacion: {recomendacion}")

        cmap = plt.get_cmap("YlGnBu").copy()
        cmap.set_bad(FONDO)
        ancho_panel = max(600, ancho_px // 3)
        alto_panel = max(420, int(ancho_panel * (r1 - r0) / max(1, c1 - c0)))
        fig, ejes = plt.subplots(
            1,
            3,
            figsize=(ancho_px / 100.0, alto_panel / 100.0),
            dpi=100,
        )
        fig.patch.set_facecolor(FONDO)
        mapa = None
        for ax, algoritmo in zip(ejes, ALGORITMOS):
            info = datos[algoritmo]
            plot = np.ma.masked_where(~info["valido"], info["humedad"])
            mapa = ax.pcolormesh(
                lon_c,
                lat_c,
                plot,
                shading="auto",
                cmap=cmap,
                vmin=0.0,
                vmax=0.6,
            )
            _borde(ax, geojson)
            ax.set_xlim(float(lon_c.min()), float(lon_c.max()))
            ax.set_ylim(float(lat_c.min()), float(lat_c.max()))
            ax.set_facecolor(FONDO)
            ax.set_xlabel("longitud", color=TENUE, fontsize=8.5)
            ax.set_ylabel("latitud", color=TENUE, fontsize=8.5)
            ax.tick_params(colors=TENUE, labelsize=8)
            for borde_ax in ax.spines.values():
                borde_ax.set_color(FILETE)
            ax.set_title(
                f"{algoritmo} · mediana {info['mediana']:.3f} · "
                f"{info['limpio_pct']:.0f}% limpio",
                color=TINTA,
                fontsize=11,
                loc="left",
            )
        if mapa is not None:
            cax = fig.add_axes([0.915, 0.12, 0.012, 0.72])
            barra = fig.colorbar(mapa, cax=cax)
            barra.set_label("m³/m³", color=TENUE, fontsize=9)
            barra.ax.tick_params(colors=TENUE, labelsize=8)
            barra.outline.set_edgecolor(FILETE)
        fig.suptitle(
            f"NISAR SME2 · comparacion de algoritmos · {fecha or escena.stem[:24]}",
            color=TINTA,
            fontsize=13,
            x=0.01,
            ha="left",
        )
        fig.text(
            0.01,
            0.005,
            f"DSG {datos['DSG']['mediana']:.3f} · PMI {datos['PMI']['mediana']:.3f} "
            f"· TSR {datos['TSR']['mediana']:.3f} m3/m3 · "
            f"{mpp_x:.0f} m/px · EPSG:{epsg} · PROVISIONAL",
            color=TENUE,
            fontsize=8,
        )
        print("dibujando comparacion")
        fig.subplots_adjust(
            left=0.035, right=0.9, top=0.88, bottom=0.09, wspace=0.16
        )
        salida.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(salida, facecolor=FONDO, bbox_inches="tight")
        plt.close(fig)

    ancho, alto = Image.open(salida).size
    flat: dict[str, object] = {
        "producto": "sme2",
        "modo": "comparar",
        "algoritmo": "COMPARAR",
        "escena": escena.stem,
        "fecha": fecha,
        "bbox": [oeste, sur, este, norte],
        "px": [int(ancho), int(alto)],
        "epsg": epsg,
        "mpp": round(mpp_x, 1),
        "algoritmos": {
            algoritmo: {
                clave: (round(valor, 4) if isinstance(valor, float) else valor)
                for clave, valor in info.items()
                if clave not in ("humedad", "valido", "limpio")
            }
            for algoritmo, info in datos.items()
        },
        "comparaciones": pares,
        "recomendacion": recomendacion,
        "dsg_mediana": round(datos["DSG"]["mediana"], 4),
        "pmi_mediana": round(datos["PMI"]["mediana"], 4),
        "tsr_mediana": round(datos["TSR"]["mediana"], 4),
        "dsg_limpio_pct": round(datos["DSG"]["limpio_pct"], 1),
        "pmi_limpio_pct": round(datos["PMI"]["limpio_pct"], 1),
        "tsr_limpio_pct": round(datos["TSR"]["limpio_pct"], 1),
    }
    if dsg_pmi:
        flat.update(
            {
                "dsg_pmi_bias_limpio": round(dsg_pmi["bias"], 4),
                "dsg_pmi_rmse_limpio": round(dsg_pmi["rmse"], 4),
                "dsg_pmi_corr_limpio": round(dsg_pmi["corr"], 3),
            }
        )
    salida.with_suffix(".json").write_text(
        json.dumps(flat, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    print(f"listo: {salida} ({ancho}x{alto} px) · {recomendacion[:80]}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--h5", required=True, help="escena NISAR SME2 (.h5)")
    ap.add_argument("--bbox", required=True, help="oeste,sur,este,norte")
    ap.add_argument("--px", type=int, default=2400)
    ap.add_argument("--out", required=True)
    ap.add_argument("--geojson", default=None)
    args = ap.parse_args(nisar.argv_bbox(sys.argv[1:]))
    oeste, sur, este, norte = _caja(args.bbox)
    return _comparar(
        Path(args.h5),
        oeste,
        sur,
        este,
        norte,
        max(800, min(int(args.px), 4096)),
        Path(args.out),
        args.geojson,
    )


if __name__ == "__main__":
    raise SystemExit(main())
