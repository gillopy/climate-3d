"""Color real de Sentinel-2 sobre una caja y una fecha: la guia visual.

El radar detecta cambio estructural; el color real dice que cambio es. Este
producto baja B02/B03/B04 (mas la mascara SCL) alrededor de una fecha, compone
la mediana en reflectancia y estira 2-98% DESPUES de la mediana, para que la
misma caja en dos fechas salga comparable. Es la guia para ubicar desmontes
antes de ajustar el detector NISAR.

    .venv\\Scripts\\python.exe prototipos\\nisar_color_optico.py \\
        --bbox -55.53,-24.25,-55.42,-24.14 --fecha 2026-11-07 --out guia.png
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
from affine import Affine  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bbox", required=True)
    ap.add_argument("--fecha", required=True, help="YYYY-MM-DD, centro de la ventana")
    ap.add_argument("--dias", type=int, default=5, help="ventana en dias alrededor")
    ap.add_argument("--nubes", type=float, default=40.0)
    ap.add_argument(
        "--px", type=int, default=1300, help="lado mayor del PNG; sale a ~10 m/px"
    )
    ap.add_argument("--out", required=True)
    args = ap.parse_args(nisar.argv_bbox(sys.argv[1:]))

    if not sentinel2.DISPONIBLE:
        raise SystemExit("faltan rasterio/pystac-client/planetary-computer")

    oeste, sur, este, norte = nisar.caja(args.bbox)
    # Grilla destino en lat/lon a ~10 m: para una guia visual no hace falta la
    # UTM del radar, y el PNG queda georreferenciable en cualquier visor.
    lat_med = np.radians((sur + norte) / 2.0)
    ancho_km = (este - oeste) * 111.32 * np.cos(lat_med)
    alto_km = (norte - sur) * 110.57
    escala_km = max(ancho_km, alto_km) / max(200.0, float(args.px))
    columnas = max(10, int(round(ancho_km / escala_km)))
    filas = max(10, int(round(alto_km / escala_km)))
    transform = Affine.translation(oeste, norte) * Affine.scale(
        (este - oeste) / columnas, -(norte - sur) / filas
    )
    mpp = escala_km * 1000.0

    fecha = datetime.strptime(args.fecha[:10], "%Y-%m-%d").date()
    items = sentinel2.buscar_items(
        (oeste, sur, este, norte), fecha, int(args.dias), float(args.nubes), 6
    )
    if not items:
        raise SystemExit(f"sin Sentinel-2 cerca de {args.fecha} con nubes < {args.nubes:g}%")

    rgb, usados = sentinel2.componer_color(
        items,
        (oeste, sur, este, norte),
        (filas, columnas),
        transform,
        "EPSG:4326",
        int(args.px),
    )
    if rgb is None or not np.isfinite(rgb).any():
        raise SystemExit("ningun item dejo color valido tras la mascara SCL")

    salida = Path(args.out)
    nubes_txt = ", ".join(f"{u['id'][:34]} ({u['cloud']:.0f}%)" for u in usados)
    lineas = [
        f"Sentinel-2 L2A · color real · {args.fecha[:10]} ± {args.dias} dias",
        f"{len(usados)} item(s): {nubes_txt}",
        f"mediana de reflectancia · estirado 2-98% · {mpp:.0f} m/px",
    ]
    ancho, alto = nisar.guardar(rgb, salida, lineas, mpp, int(args.px))
    print(f"listo: {salida} ({ancho}x{alto} px)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
