"""Mapa del interferograma NISAR GUNW recortado a una caja.

GUNW trae la fase desenvuelta (80 m) y la coherencia del par de fechas, ya
geocodificadas en UTM/polar stereographic. Se recorta por la caja del visor y se
dibujan dos paneles: coherencia (0 a 1) y fase desenvuelta (radianes). La fase
es la del producto: no se aplican correcciones atmosfericas ni ionosfericas.

    .venv\\Scripts\\python.exe prototipos\\nisar_gunw.py --h5 ESCENA.h5 \
        --bbox -61.5,-21.5,-60.5,-20.5 --px 2400 --out gunw.png
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
from pyproj import Transformer  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))

import nisar  # noqa: E402  (argv_bbox: la caja empieza con "-")

FONDO = "#0b0c0d"
TINTA = "#d0d6e0"
TENUE = "#8a8f98"
FILETE = "#23252a"
LUZ = 299_792_458.0
RELLENO_CC = 65535


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


def _texto(valor) -> str:
    if isinstance(valor, (bytes, np.bytes_)):
        return valor.decode("utf-8", "replace")
    return str(valor)


def _fecha(valor: str) -> str:
    return (valor or "")[:10]


def _par_track_frame(nombre: str) -> tuple[int | None, int | None]:
    encontrado = re.search(r"_(\d{3})_(\d{3})_[AD]_(\d{3})_", nombre)
    if not encontrado:
        return None, None
    return int(encontrado.group(2)), int(encontrado.group(3))


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
        poligonos = [coordenadas] if tipo == "Polygon" else coordenadas if tipo == "MultiPolygon" else []
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
    ap.add_argument("--h5", required=True, help="escena NISAR GUNW (.h5)")
    ap.add_argument("--bbox", required=True, help="oeste,sur,este,norte")
    ap.add_argument("--px", type=int, default=2400)
    ap.add_argument("--out", required=True)
    ap.add_argument("--geojson", default=None)
    args = ap.parse_args(nisar.argv_bbox(sys.argv[1:]))

    oeste, sur, este, norte = _caja(args.bbox)
    ancho = max(1200, min(int(args.px), 4096))
    salida = Path(args.out)
    escena = Path(args.h5)
    track, frame = _par_track_frame(escena.stem)

    print(f"abriendo {escena.name}")
    with h5py.File(escena, "r") as f:
        rejilla = f["science/LSAR/GUNW/grids/frequencyA"]
        interferograma = rejilla["unwrappedInterferogram"]
        polarizaciones = [
            nombre
            for nombre in interferograma.keys()
            if nombre in ("HH", "HV", "VV", "VH")
        ]
        if not polarizaciones:
            raise SystemExit("El GUNW no declara una polarizacion HH/VV para la fase.")
        pol = polarizaciones[0]
        grupo = interferograma[pol]
        x = np.asarray(interferograma["xCoordinates"][...], dtype=float)
        y = np.asarray(interferograma["yCoordinates"][...], dtype=float)
        epsg = int(interferograma["projection"].attrs.get("epsg_code", 32721))
        frecuencia = float(rejilla["centerFrequency"][()])
        longitud_onda = LUZ / frecuencia
        franja_cm = longitud_onda / 2.0 * 100.0

        # La caja lon/lat se transforma al UTM del producto y se recorta con
        # slices contiguos: leer con dos arrays de indices es mucho mas lento.
        proyector = Transformer.from_crs(4326, epsg, always_xy=True)
        xs, ys = proyector.transform(
            [oeste, este, oeste, este], [sur, sur, norte, norte]
        )
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        columnas = np.where((x >= x0) & (x <= x1))[0]
        filas = np.where((y >= y0) & (y <= y1))[0]
        if columnas.size == 0 or filas.size == 0:
            raise SystemExit("La caja no intersecta la escena GUNW.")
        c0, c1 = int(columnas[0]), int(columnas[-1]) + 1
        r0, r1 = int(filas[0]), int(filas[-1]) + 1

        print(f"recortando caja {oeste:g},{sur:g},{este:g},{norte:g}")
        fase = np.asarray(grupo["unwrappedPhase"][r0:r1, c0:c1], dtype=float)
        coherencia = np.asarray(grupo["coherenceMagnitude"][r0:r1, c0:c1], dtype=float)
        componentes = np.asarray(grupo["connectedComponents"][r0:r1, c0:c1])
        y = y[r0:r1]

        # Filas de norte a sur para que imshow(origin="upper") quede derecho.
        if y.size > 1 and y[0] < y[-1]:
            y = y[::-1]
            fase = fase[::-1, :]
            coherencia = coherencia[::-1, :]
            componentes = componentes[::-1, :]

        # Fase envuelta: la grilla de 20 m se decima a ~80 m para el panel.
        fase_envuelta = None
        try:
            envuelto = rejilla["wrappedInterferogram"][pol]
            xw = np.asarray(envuelto["xCoordinates"][...], dtype=float)
            yw = np.asarray(envuelto["yCoordinates"][...], dtype=float)
            colw = np.where((xw >= x0) & (xw <= x1))[0]
            filw = np.where((yw >= y0) & (yw <= y1))[0]
            if colw.size and filw.size:
                c0w, c1w = int(colw[0]), int(colw[-1]) + 1
                r0w, r1w = int(filw[0]), int(filw[-1]) + 1
                paso = max(1, int(round(abs(xw[1] - xw[0]) / 80.0))) if xw.size > 1 else 1
                # Leer ya decimado: la grilla de 20 m completa no entra comoda.
                complejo = np.asarray(
                    envuelto["wrappedInterferogram"][
                        r0w:r1w:paso, c0w:c1w:paso
                    ]
                )
                fase_envuelta = np.angle(complejo)
                if yw.size > 1 and yw[0] < yw[-1]:
                    fase_envuelta = fase_envuelta[::-1, :]
        except (KeyError, ValueError):
            fase_envuelta = None

        valido = np.isfinite(fase) & np.isfinite(coherencia)
        if not valido.any():
            raise SystemExit("La caja no tiene pixeles validos de fase/coherencia.")
        fase_v = fase[valido]
        coh_v = coherencia[valido]
        fase_p10, fase_p50, fase_p90 = [
            float(v) for v in np.percentile(fase_v, [10, 50, 90])
        ]
        coh_p10, coh_p50, coh_p90 = [
            float(v) for v in np.percentile(coh_v, [10, 50, 90])
        ]
        # Desplazamiento relativo a la mediana de la caja: el offset absoluto del
        # producto no es un desplazamiento (faltan correcciones atmosfericas).
        desplazamiento_rel = -(fase_v - fase_p50) * longitud_onda / (4.0 * np.pi) * 100.0
        disp_p10, disp_p90 = [float(v) for v in np.percentile(desplazamiento_rel, [10, 90])]
        coh_media = float(np.mean(coh_v))
        cc_v = componentes[valido]
        etiquetas = np.unique(cc_v[(cc_v > 0) & (cc_v != RELLENO_CC)])
        mayor_pct = 0.0
        if etiquetas.size:
            mayor = max(int((cc_v == etiqueta).sum()) for etiqueta in etiquetas)
            mayor_pct = 100.0 * mayor / max(1, int(valido.sum()))
        agua_pct = 100.0 * float(interferograma["mask"].attrs.get("percentage_water", 0.0))
        cobertura = 100.0 * float(valido.sum()) / float(valido.size)

        # Fechas del par desde los metadatos del producto.
        parametros = f["science/LSAR/GUNW/metadata/processingInformation/parameters"]
        try:
            fecha_ref = _fecha(
                _texto(parametros["reference/frequencyA/zeroDopplerStartTime"][()])
            )
            fecha_sec = _fecha(
                _texto(parametros["secondary/frequencyA/zeroDopplerStartTime"][()])
            )
        except (KeyError, TypeError, ValueError):
            fecha_ref = fecha_sec = ""
        print(
            f"estadisticas: {valido.sum()} px validos, coherencia media "
            f"{coh_p50:.2f}, fase p10-p90 {fase_p10:.1f}-{fase_p90:.1f} rad"
        )

        paneles = [
            (
                np.ma.masked_where(~valido, coherencia),
                dict(cmap="magma", vmin=0.0, vmax=1.0),
                "Coherencia",
                "0 = sin coherencia · 1 = estable",
            ),
        ]
        if fase_envuelta is not None:
            paneles.append(
                (
                    np.ma.masked_invalid(fase_envuelta),
                    dict(cmap="twilight_shifted", vmin=-np.pi, vmax=np.pi),
                    "Fase envuelta",
                    "20 m (decimada a 80 m) · 1 franja = 2π",
                )
            )
        paneles.append(
            (
                np.ma.masked_where(~valido, fase),
                dict(cmap="viridis", vmin=fase_p10, vmax=fase_p90),
                "Fase desenvuelta",
                f"80 m · 1 franja (2π) ≈ {franja_cm:.1f} cm LOS",
            )
        )
        ancho_panel = max(600, ancho // max(1, len(paneles)))
        alto_panel = max(
            420,
            int(ancho_panel * max(1, fase.shape[0]) / max(1, fase.shape[1])),
        )
        fig, ejes = plt.subplots(
            1,
            len(paneles),
            figsize=(ancho / 100.0, alto_panel / 100.0),
            dpi=100,
        )
        fig.patch.set_facecolor(FONDO)
        if len(paneles) == 1:
            ejes = [ejes]
        for ax, (datos, estilo, titulo, subtitulo) in zip(ejes, paneles):
            mapa = ax.imshow(
                datos,
                extent=[oeste, este, sur, norte],
                origin="upper",
                aspect="auto",
                interpolation="nearest",
                **estilo,
            )
            mapa.cmap.set_bad(FONDO)
            _borde(ax, args.geojson)
            # El borde de Paraguay es mas grande que la caja: se vuelve a fijar.
            ax.set_xlim(oeste, este)
            ax.set_ylim(sur, norte)
            ax.set_facecolor(FONDO)
            ax.set_title(titulo, color=TINTA, fontsize=12, loc="left", pad=18)
            ax.set_xlabel("longitud", color=TENUE, fontsize=8.5)
            ax.set_ylabel("latitud", color=TENUE, fontsize=8.5)
            ax.tick_params(colors=TENUE, labelsize=8)
            for borde_ax in ax.spines.values():
                borde_ax.set_color(FILETE)
            ax.text(
                0.0,
                1.012,
                subtitulo,
                transform=ax.transAxes,
                color=TENUE,
                fontsize=7.5,
                ha="left",
            )
            barra = fig.colorbar(mapa, ax=ax, fraction=0.035, pad=0.01)
            barra.ax.tick_params(colors=TENUE, labelsize=7.5)
            barra.outline.set_edgecolor(FILETE)
        fig.suptitle(
            f"NISAR GUNW · {pol} · {fecha_ref or '?'} → {fecha_sec or '?'} · "
            f"track {track} frame {frame}",
            color=TINTA,
            fontsize=13,
            x=0.01,
            ha="left",
        )
        fig.text(
            0.01,
            0.005,
            f"coherencia media {coh_media:.2f} · fase p10-p90 {fase_p10:.0f}-"
            f"{fase_p90:.0f} rad · desplaz. rel. p10-p90 {disp_p10:+.0f} a "
            f"{disp_p90:+.0f} cm (sin correcciones) · {cobertura:.0f}% valido · "
            f"{agua_pct:.0f}% agua · PROVISIONAL",
            color=TENUE,
            fontsize=8,
        )
        print("dibujando mapa")
        fig.tight_layout(rect=(0, 0.02, 1, 0.96))
        salida.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(salida, facecolor=FONDO, bbox_inches="tight")
        plt.close(fig)

    ancho_img, alto_img = Image.open(salida).size
    meta = {
        "producto": "gunw",
        "escena": escena.stem,
        "fecha": fecha_ref,
        "fecha_ref": fecha_ref,
        "fecha_sec": fecha_sec,
        "track": track,
        "frame": frame,
        "polarizacion": pol,
        "bbox": [oeste, sur, este, norte],
        "px": [int(ancho_img), int(alto_img)],
        "epsg": epsg,
        "mpp": 80.0,
        "longitud_onda_cm": round(longitud_onda * 100.0, 2),
        "franja_cm": round(franja_cm, 2),
        "coherencia_media": round(coh_media, 3),
        "coherencia_p10": round(coh_p10, 3),
        "coherencia_p50": round(coh_p50, 3),
        "coherencia_p90": round(coh_p90, 3),
        "fase_p10": round(fase_p10, 2),
        "fase_p50": round(fase_p50, 2),
        "fase_p90": round(fase_p90, 2),
        "desplazamiento_rel_p10_cm": round(disp_p10, 2),
        "desplazamiento_rel_p90_cm": round(disp_p90, 2),
        "desplazamiento_rel_nota": "relativo a la mediana; sin correcciones atmosfericas",
        "componentes": int(etiquetas.size),
        "mayor_componente_pct": round(mayor_pct, 1),
        "cobertura_valida_pct": round(cobertura, 1),
        "agua_pct_escena": round(agua_pct, 1),
        "pixeles": int(valido.sum()),
    }
    salida.with_suffix(".json").write_text(
        json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    print(
        f"listo: {salida} ({ancho_img}x{alto_img} px, {valido.sum()} px, "
        f"coherencia {coh_p50:.2f}, fase {fase_p50:.1f} rad)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
