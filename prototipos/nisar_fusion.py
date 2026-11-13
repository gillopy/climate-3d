"""Fusión Sentinel-2 L2A + NISAR GCOV: NDVI, composición y clasificación.

Toma una escena NISAR, busca Sentinel-2 L2A en Planetary Computer alrededor de su
fecha, lee rojo (B04), NIR (B08) y la clasificación de escena (SCL), enmascara
nubes/sombras, compone el NDVI mediano y lo reproyecta a la grilla de la escena
NISAR. Después:

- ``*_fusion.png``: HV, NDVI, RGB de fusión y mapa de clases;
- ``*_clasificacion.png``: mapa de clases con leyenda y hectáreas;
- ``*_ndvi.tif``: NDVI compuesto en la UTM de la escena (GeoTIFF);
- ``*.json``: estadísticas, correlación HV↔NDVI, ítems y áreas.

La clasificación es rule-based (agua/bosque/cultivo/suelo), no un modelo
entrenado: es una herramienta de exploración con umbrales visibles.

    .venv\\Scripts\\python.exe prototipos\\nisar_fusion.py --h5 ESCENA.h5 \
        --bbox -55.6,-24.5,-55.2,-23.9 --px 1200 --dias 15 --nubes 40 \
        --out fusion
"""
from __future__ import annotations

import argparse
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import planetary_computer as pc  # noqa: E402
import rasterio  # noqa: E402
from affine import Affine  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from pystac_client import Client  # noqa: E402
from rasterio.enums import Resampling  # noqa: E402
from rasterio.warp import reproject, transform_bounds  # noqa: E402
from rasterio.windows import from_bounds  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))

import nisar  # noqa: E402
import optico  # noqa: E402

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"


def _ventana(src, bbox):
    b = transform_bounds("EPSG:4326", src.crs, *bbox)
    return from_bounds(*b, transform=src.transform)


def _ndvi_item(item, bbox, destino_forma, destino_transform, destino_crs, px):
    """NDVI de un ítem, enmascarado por SCL y reproyectado a la grilla NISAR."""
    item = pc.sign(item)
    faltan = [clave for clave in ("B04", "B08", "SCL") if clave not in item.assets]
    if faltan:
        print(f"aviso: {item.id} sin assets {faltan}; se omite")
        return None

    with rasterio.open(item.assets["B04"].href) as src_b04:
        win_b04 = _ventana(src_b04, bbox)
        escala = max(
            1,
            int(
                math.ceil(
                    max(win_b04.width, win_b04.height) / max(1, int(px * 1.5))
                )
            ),
        )
        alto = max(1, int(round(win_b04.height / escala)))
        ancho = max(1, int(round(win_b04.width / escala)))
        rojo = src_b04.read(
            1,
            window=win_b04,
            out_shape=(alto, ancho),
            resampling=Resampling.bilinear,
        ).astype(np.float32)
        transform_origen = src_b04.window_transform(win_b04) * Affine.scale(
            win_b04.width / ancho, win_b04.height / alto
        )
        crs_origen = src_b04.crs

    with rasterio.open(item.assets["B08"].href) as src_b08:
        win_b08 = _ventana(src_b08, bbox)
        nir = src_b08.read(
            1,
            window=win_b08,
            out_shape=(alto, ancho),
            resampling=Resampling.bilinear,
        ).astype(np.float32)

    with rasterio.open(item.assets["SCL"].href) as src_scl:
        win_scl = _ventana(src_scl, bbox)
        scl = src_scl.read(
            1,
            window=win_scl,
            out_shape=(alto, ancho),
            resampling=Resampling.nearest,
        )

    nd = optico.ndvi(rojo, nir)
    nd[~optico.mascara_scl(scl)] = np.nan

    destino = np.full(destino_forma, np.nan, dtype=np.float32)
    reproject(
        source=nd,
        destination=destino,
        src_transform=transform_origen,
        src_crs=crs_origen,
        dst_transform=destino_transform,
        dst_crs=destino_crs,
        resampling=Resampling.bilinear,
        src_nodata=np.nan,
        dst_nodata=np.nan,
    )
    return destino, float(item.properties.get("eo:cloud_cover", 100.0))


def _figura_fusion(salida, hv_db, hh_db, ndvi_comp, clases, areas, meta):
    colores = optico.COLORES.astype(np.float32) / 255.0
    mapa_clases = ListedColormap(colores)
    fig, axes = plt.subplots(2, 2, figsize=(14, 11), dpi=150)
    fig.patch.set_facecolor("#0b0c0d")

    for ax in axes.ravel():
        ax.set_facecolor("#0b0c0d")
        ax.set_xticks([])
        ax.set_yticks([])
        for borde in ax.spines.values():
            borde.set_color("#23252a")

    vmin, vmax = nisar.limites(hv_db)
    im = axes[0, 0].imshow(hv_db, cmap="gray", vmin=vmin, vmax=vmax)
    axes[0, 0].set_title("NISAR HV (dB)", color="#f7f8f8", fontsize=10)
    fig.colorbar(im, ax=axes[0, 0], fraction=0.046, pad=0.02).ax.tick_params(
        colors="#d0d6e0", labelsize=8
    )

    im = axes[0, 1].imshow(ndvi_comp, cmap="RdYlGn", vmin=-0.2, vmax=0.8)
    axes[0, 1].set_title("Sentinel-2 NDVI (mediana)", color="#f7f8f8", fontsize=10)
    fig.colorbar(im, ax=axes[0, 1], fraction=0.046, pad=0.02).ax.tick_params(
        colors="#d0d6e0", labelsize=8
    )

    rojo = nisar.normalizar(np.nan_to_num(ndvi_comp, nan=0.0), 0.0, 0.8)
    verde = nisar.normalizar(np.nan_to_num(hv_db, nan=vmin), vmin, vmax)
    diferencia = hh_db - hv_db
    azul = nisar.normalizar(
        np.nan_to_num(diferencia, nan=np.nanmedian(diferencia)), *nisar.limites(diferencia)
    )
    rgb = (np.dstack([rojo, verde, azul]) * 255.0).astype(np.uint8)
    rgb[~(np.isfinite(ndvi_comp) & np.isfinite(hv_db))] = 0
    axes[1, 0].imshow(rgb)
    axes[1, 0].set_title("Fusión RGB: NDVI / HV / HH-HV", color="#f7f8f8", fontsize=10)

    axes[1, 1].imshow(clases, cmap=mapa_clases, vmin=0, vmax=4, interpolation="nearest")
    axes[1, 1].set_title("Clasificación rule-based", color="#f7f8f8", fontsize=10)
    leyenda = [
        Patch(
            facecolor=colores[indice],
            edgecolor="#23252a",
            label=f"{optico.CLASES[indice]} · {areas.get(optico.CLASES[indice], 0):.0f} ha",
        )
        for indice in (1, 2, 3, 4)
    ]
    axes[1, 1].legend(
        handles=leyenda,
        loc="lower left",
        frameon=True,
        facecolor="#161718",
        edgecolor="#23252a",
        labelcolor="#d0d6e0",
        fontsize=8,
    )

    fig.suptitle(
        f"Fusión Sentinel-2 + NISAR · {meta['nisar']['fecha']} · "
        f"{meta['optico']['items']} ítem(s) S2 · corr HV/NDVI {meta['correlacion']:.2f}",
        color="#f7f8f8",
        fontsize=12,
    )
    fig.text(
        0.01,
        0.01,
        f"NDVI medio {meta['ndvi']['medio']:.2f} · p10 {meta['ndvi']['p10']:.2f} · "
        f"p90 {meta['ndvi']['p90']:.2f} · bbox "
        f"{', '.join(f'{v:g}' for v in meta['bbox'])} · {meta['mpp']:.0f} m/px",
        color="#8a8f98",
        fontsize=8,
    )
    fig.tight_layout(rect=[0, 0.02, 1, 0.96])
    fig.savefig(salida, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def _figura_clases(salida, clases, areas, meta):
    colores = optico.COLORES.astype(np.float32) / 255.0
    fig, ax = plt.subplots(figsize=(9, 10), dpi=150)
    fig.patch.set_facecolor("#0b0c0d")
    ax.set_facecolor("#0b0c0d")
    ax.imshow(
        clases,
        cmap=ListedColormap(colores),
        vmin=0,
        vmax=4,
        interpolation="nearest",
    )
    ax.set_xticks([])
    ax.set_yticks([])
    for borde in ax.spines.values():
        borde.set_color("#23252a")
    leyenda = [
        Patch(
            facecolor=colores[indice],
            edgecolor="#23252a",
            label=f"{optico.CLASES[indice]} · {areas.get(optico.CLASES[indice], 0):.0f} ha",
        )
        for indice in (1, 2, 3, 4)
    ]
    ax.legend(
        handles=leyenda,
        loc="lower left",
        frameon=True,
        facecolor="#161718",
        edgecolor="#23252a",
        labelcolor="#d0d6e0",
        fontsize=9,
    )
    ax.set_title(
        f"Clasificación NISAR + Sentinel-2 · {meta['nisar']['fecha']}",
        color="#f7f8f8",
        fontsize=11,
    )
    fig.text(
        0.01,
        0.01,
        "Regla: agua (NDVI bajo, HV bajo) · bosque (NDVI y HV altos) · "
        "cultivo/vegetación · suelo/urbano. No es un modelo entrenado.",
        color="#8a8f98",
        fontsize=7.5,
    )
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(salida, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--h5", required=True)
    ap.add_argument("--bbox", required=True)
    ap.add_argument("--px", type=int, default=1200)
    ap.add_argument("--dias", type=int, default=15, help="ventana óptica ± días")
    ap.add_argument("--nubes", type=float, default=40.0, help="cobertura máxima de nubes")
    ap.add_argument("--max-items", type=int, default=12)
    ap.add_argument("--out", required=True, help="prefijo de salida")
    ap.add_argument("--geojson", default=None)
    ap.add_argument("--ndvi-bosque", type=float, default=0.55)
    ap.add_argument("--ndvi-cultivo", type=float, default=0.25)
    ap.add_argument("--hv-bosque", type=float, default=-15.5)
    ap.add_argument("--hv-agua", type=float, default=-20.0)
    args = ap.parse_args()

    px = max(800, min(int(args.px), 2000))
    oeste, sur, este, norte = nisar.caja(args.bbox)
    prefijo = Path(args.out)
    if prefijo.suffix:
        prefijo = prefijo.with_suffix("")
    fusion_png = prefijo.with_name(prefijo.name + "_fusion.png")
    clases_png = prefijo.with_name(prefijo.name + "_clasificacion.png")
    ndvi_tif = prefijo.with_name(prefijo.name + "_ndvi.tif")

    print(f"abriendo {Path(args.h5).name}")
    with nisar.Escena(args.h5) as escena:
        if "HV" not in escena.pols:
            raise SystemExit("La escena NISAR no tiene HV.")
        rec_hv = escena.recortar("HV", args.bbox, px)
        hv, xs, ys = nisar.orientar(rec_hv)
        hv_db = nisar.a_db(hv)
        alto_nisar, ancho_nisar = hv_db.shape
        if "HH" in escena.pols:
            hh, _, _ = nisar.orientar(escena.recortar("HH", args.bbox, px))
            hh_db = nisar.a_db(hh)
        else:
            hh_db = np.full_like(hv_db, np.nan)

        mpp_x = abs(float(xs[-1] - xs[0])) / max(1, len(xs) - 1)
        mpp_y = abs(float(ys[0] - ys[-1])) / max(1, len(ys) - 1)
        destino_transform = Affine.translation(
            float(xs[0]) - mpp_x / 2.0, float(ys[0]) + mpp_y / 2.0
        ) * Affine.scale(mpp_x, -mpp_y)
        destino_crs = f"EPSG:{rec_hv.epsg}"
        try:
            fecha = datetime.strptime(escena.fecha[:10], "%Y-%m-%d").date()
        except (TypeError, ValueError):
            raise SystemExit("No pude leer la fecha de la escena NISAR.")
        print(
            f"NISAR {escena.fecha} · {alto_nisar}x{ancho_nisar} px · "
            f"{mpp_x:.0f} m/px · EPSG:{rec_hv.epsg}"
        )

        desde = fecha - timedelta(days=max(1, int(args.dias)))
        hasta = fecha + timedelta(days=max(1, int(args.dias)))
        print(f"buscando Sentinel-2 del {desde} al {hasta} (nubes < {args.nubes:g}%)")
        catalogo = Client.open(STAC)
        busqueda = catalogo.search(
            collections=["sentinel-2-l2a"],
            bbox=(oeste, sur, este, norte),
            datetime=f"{desde}/{hasta}",
            query={"eo:cloud_cover": {"lt": float(args.nubes)}},
        )
        items = sorted(
            list(busqueda.items()),
            key=lambda item: float(item.properties.get("eo:cloud_cover", 100.0)),
        )[: max(1, int(args.max_items))]
        if not items:
            raise SystemExit(
                "No hay Sentinel-2 L2A en esa ventana con ese límite de nubes. "
                "Ampliá --dias o subí --nubes."
            )
        print(f"Sentinel-2: {len(items)} ítem(s)")

        ndvis: list[np.ndarray] = []
        usados: list[dict] = []
        for item in items:
            try:
                nd, nubes = _ndvi_item(
                    item,
                    (oeste, sur, este, norte),
                    (alto_nisar, ancho_nisar),
                    destino_transform,
                    destino_crs,
                    px,
                )
            except Exception as exc:  # noqa: BLE001 - un ítem roto no mata la fusión
                print(
                    f"aviso: {item.id} fallo al leer/reproyectar "
                    f"({type(exc).__name__}: {exc}); se omite"
                )
                continue
            if nd is None:
                continue
            validos = int(np.isfinite(nd).sum())
            if validos == 0:
                print(f"  {item.id}: sin píxeles válidos tras SCL")
                continue
            ndvis.append(nd)
            usados.append({"id": item.id, "cloud": round(nubes, 2)})
            print(f"  {item.id}: {nubes:.1f}% nubes · {validos} px")

        if not ndvis:
            raise SystemExit("Ningún ítem dejó píxeles válidos después de enmascarar.")
        ndvi_comp = optico.compuesto_mediana(ndvis)
        validos_ndvi = int(np.isfinite(ndvi_comp).sum())
        total = int(ndvi_comp.size)
        p10, p50, p90 = [float(np.nanpercentile(ndvi_comp, p)) for p in (10, 50, 90)]
        ndvi_medio = float(np.nanmean(ndvi_comp))
        correlacion = float("nan")
        par = np.isfinite(hv_db) & np.isfinite(ndvi_comp)
        if par.sum() > 10:
            correlacion = float(np.corrcoef(hv_db[par], ndvi_comp[par])[0, 1])

        clases = optico.suavizar_clases(
            optico.clasificar(
                hv_db,
                ndvi_comp,
                ndvi_bosque=float(args.ndvi_bosque),
                ndvi_cultivo=float(args.ndvi_cultivo),
                hv_bosque=float(args.hv_bosque),
                hv_agua=float(args.hv_agua),
            )
        )
        conteo = np.bincount(clases.ravel(), minlength=5)
        areas = {
            optico.CLASES[indice]: round(
                nisar.hectareas(int(conteo[indice]), mpp_x, mpp_y), 1
            )
            for indice in (1, 2, 3, 4)
        }

        meta = {
            "producto": "fusion",
            "nisar": {
                "escena": escena.ruta.stem,
                "fecha": escena.fecha,
                "track": escena.track,
                "frame": escena.frame,
            },
            "optico": {
                "coleccion": "sentinel-2-l2a",
                "desde": desde.isoformat(),
                "hasta": hasta.isoformat(),
                "nubes_max": float(args.nubes),
                "items": len(usados),
                "detalle": usados,
                "cobertura_valida_pct": round(100.0 * validos_ndvi / max(1, total), 2),
            },
            "bbox": [oeste, sur, este, norte],
            "epsg": rec_hv.epsg,
            "mpp": round(mpp_x, 3),
            "px": [ancho_nisar, alto_nisar],
            "ndvi": {
                "medio": round(ndvi_medio, 3),
                "p10": round(p10, 3),
                "p50": round(p50, 3),
                "p90": round(p90, 3),
            },
            "correlacion": round(correlacion, 3),
            "clases": areas,
            "archivos": {
                "fusion": str(fusion_png),
                "clasificacion": str(clases_png),
                "ndvi_tif": str(ndvi_tif),
            },
        }

        _figura_fusion(fusion_png, hv_db, hh_db, ndvi_comp, clases, areas, meta)
        _figura_clases(clases_png, clases, areas, meta)
        nisar.guardar_geotiff(
            ndvi_tif,
            ndvi_comp,
            x0=float(xs[0]) - mpp_x / 2.0,
            y1=float(ys[0]) + mpp_y / 2.0,
            mpp_x=mpp_x,
            mpp_y=mpp_y,
            epsg=rec_hv.epsg,
            descripcion=f"Sentinel-2 NDVI compuesto / NISAR {escena.fecha}",
        )
        nisar.guardar_json(prefijo, meta)

    print(
        f"NDVI medio {ndvi_medio:.2f} · corr HV/NDVI {correlacion:.2f} · "
        f"cobertura {100.0 * validos_ndvi / max(1, total):.1f}%"
    )
    for nombre, hectareas in areas.items():
        print(f"  {nombre}: {hectareas:.0f} ha")
    print(f"listo: {fusion_png} | {clases_png} | {ndvi_tif}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
