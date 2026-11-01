"""Descarga una **captura** (snapshot) GeoColor de NASA GIBS recortada a Paraguay.

No es una serie: es **una sola imagen**. El encuadre no se escribe a mano: sale del
GeoJSON de Paraguay (`datos/paraguay_gadm.json`) más un margen, así la cobertura
queda definida por los bordes del país.

Fuente (Worldview Snapshots API — un GET):

    https://wvs.earthdata.nasa.gov/api/v1/snapshot
      ?REQUEST=GetSnapshot&TIME=<ISO8601>Z&BBOX=<o>,<s>,<e>,<n>&CRS=EPSG:4326
      &LAYERS=GOES-East_ABI_GeoColor&FORMAT=image/png&WIDTH=<px>&HEIGHT=<px>

GeoColor es el "color IR día/noche" del ABI de GOES-19: color real de día, IR
multiespectral y luces de ciudad de noche. GIBS devuelve el gránulo más cercano al
instante pedido, así que no hay que adivinar el slot exacto.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe descargar\\snapshot_paraguay.py
    .venv\\Scripts\\python.exe descargar\\snapshot_paraguay.py --fecha 2026-11-01 --hora 15 --px 2000
    .venv\\Scripts\\python.exe descargar\\snapshot_paraguay.py --help   # no toca la red
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, datetime
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from paraguay import MARGEN, caja_geojson, nombre_crudo  # noqa: E402

API = "https://wvs.earthdata.nasa.gov/api/v1/snapshot"
CAPA = "GOES-East_ABI_GeoColor"
GEOJSON = RAIZ / "datos" / "paraguay_gadm.json"

FECHA = "2026-11-01"                   # UTC
HORA = 15                              # UTC (15z = mediodía en Paraguay)
MINUTO = 0
PX = 2000                              # lado de la captura en píxeles


def url_snapshot(t: datetime, caja, px: int, capa: str = CAPA) -> str:
    """URL del snapshot para el instante `t` (en PNG: la composición va sin pérdida)."""
    o, s, e, n = caja
    momento = t.strftime("%Y-%m-%dT%H:%M:%SZ")
    return (f"{API}?REQUEST=GetSnapshot&TIME={momento}"
            f"&BBOX={s},{o},{n},{e}&CRS=EPSG:4326"
            f"&LAYERS={capa}&FORMAT=image/png&WIDTH={px}&HEIGHT={px}")


def descargar(t: datetime, caja, px: int, destino: Path, capa: str = CAPA,
              reintentos: int = 4) -> Path:
    """Baja la captura a `destino`; si ya está, la reutiliza (reanudable)."""
    if destino.exists() and destino.stat().st_size > 5_000:
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    url = url_snapshot(t, caja, px, capa)
    espera = 2.0
    for intento in range(1, reintentos + 1):
        try:
            r = requests.get(url, timeout=120, headers={"User-Agent": "climate3d/1.0"})
            r.raise_for_status()
            if len(r.content) < 5_000:
                raise ValueError(f"respuesta demasiado chica ({len(r.content)} B)")
            tmp = destino.with_suffix(destino.suffix + ".parcial")
            tmp.write_bytes(r.content)
            tmp.replace(destino)
            return destino
        except Exception as exc:                       # red o corte del servicio
            if intento == reintentos:
                raise
            print(f"    reintento {intento}/{reintentos - 1} ({exc})", flush=True)
            time.sleep(espera)
            espera *= 2
    return destino


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Descarga una captura GeoColor (GOES-19) recortada a Paraguay.")
    ap.add_argument("--fecha", default=FECHA,
                    help=f"día UTC de la captura, YYYY-MM-DD (por defecto {FECHA})")
    ap.add_argument("--hora", type=int, default=HORA,
                    help=f"hora UTC 0-23 (por defecto {HORA})")
    ap.add_argument("--minuto", type=int, default=MINUTO,
                    help=f"minuto UTC 0-59 (por defecto {MINUTO})")
    ap.add_argument("--px", type=int, default=PX,
                    help=f"lado de la captura en píxeles (por defecto {PX})")
    ap.add_argument("--margen", type=float, default=MARGEN,
                    help=f"margen alrededor del país, fracción del lado "
                         f"(por defecto {MARGEN})")
    ap.add_argument("--geojson", default=str(GEOJSON),
                    help="GeoJSON que define la cobertura (por defecto, Paraguay GADM)")
    ap.add_argument("--capa", default=CAPA, help=f"capa GIBS (por defecto {CAPA})")
    ap.add_argument("--out", help="carpeta de salida (por defecto, la del job)")
    args = ap.parse_args(argv)

    try:
        dia = date.fromisoformat(args.fecha)
    except ValueError:
        raise SystemExit(f"--fecha inválida: {args.fecha!r} (se espera YYYY-MM-DD).")
    if not 0 <= args.hora <= 23:
        raise SystemExit(f"--hora fuera de rango: {args.hora} (0-23).")
    if not 0 <= args.minuto <= 59:
        raise SystemExit(f"--minuto fuera de rango: {args.minuto} (0-59).")
    if args.px < 256:
        raise SystemExit(f"--px demasiado chico: {args.px}.")
    if args.margen < 0:
        raise SystemExit(f"--margen debe ser >= 0 (recibí {args.margen}).")

    t = datetime(dia.year, dia.month, dia.day, args.hora, args.minuto)
    caja = caja_geojson(Path(args.geojson), args.margen)
    salida = Path(args.out) if args.out else RAIZ / "app" / "var" / "media" / "cache"
    destino = salida / nombre_crudo(t, args.px)

    o, s, e, n = caja
    print(f"Snapshot GeoColor {t:%Y-%m-%d %H:%M} UTC | {args.px}x{args.px} px")
    print(f"caja (desde el GeoJSON + margen {args.margen:g}): "
          f"{o:.2f},{s:.2f} .. {e:.2f},{n:.2f}")
    print(f"fuente: {url_snapshot(t, caja, args.px, args.capa)}")

    inicio = time.time()
    ruta = descargar(t, caja, args.px, destino, args.capa)
    print(f"listo: {ruta} ({ruta.stat().st_size / 1024:.0f} KB, "
          f"{time.time() - inicio:.1f}s)")
    print("Ahora componé con: "
          f".venv\\Scripts\\python.exe cuadros\\snapshot_paraguay.py "
          f"--crudo \"{ruta}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
