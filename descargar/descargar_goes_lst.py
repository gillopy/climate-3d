"""Download GOES-R ABI L2 Land Surface Temperature (LST 2 km full disk) from NOAA S3.

The product publishes one granule per hour, about 10 minutes after the scan.
Without flags this script fetches the last 24 h ending at the newest published
hour. `--ultimos N` fetches exactly the N newest granules, the quick path for
"what is out right now".

Reuses `descargar/goes_descarga.py` (it builds the S3 URL for any key) and
`comun/goes_lectura.py` (local path). Skips files already on disk (2 MB or more)
and writes to `comun.rutas.DATOS/goes_lst_<sat>` (e.g. `goes_lst_g19`), the
folder the app reads as `goes_lst_g19`.

All times are UTC (Paraguay is UTC-3).

Usage (from the project root):

    .venv\\Scripts\\python.exe descargar\\descargar_goes_lst.py --ultimos 6
    .venv\\Scripts\\python.exe descargar\\descargar_goes_lst.py                 # last 24 h
    .venv\\Scripts\\python.exe descargar\\descargar_goes_lst.py --sat G19 --desde 2026-11-13T00:00 --hasta 2026-11-14T00:00
    .venv\\Scripts\\python.exe descargar\\descargar_goes_lst.py --help          # no network
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from goes_descarga import descargar  # noqa: E402
from goes_lectura import ruta_local  # noqa: E402
from goes_lst import PASO, PREFIJO, clave_de, ultimos_slots, ventana_ultimas  # noqa: E402
from rutas import DATOS  # noqa: E402

SAT = "G19"
HORAS_POR_DEFECTO = 24
MINIMO_BYTES = 2_000_000


def carpeta_datos(sat: str) -> Path:
    """Default destination folder: `goes_lst_<sat>` (e.g. goes_lst_g19)."""
    return DATOS / f"goes_lst_{sat.lower()}"


def resolver_slots(args) -> list[datetime]:
    """Slots to download: the newest published queue or an explicit window.

    `--ultimos N` wins over everything. With only one end of the range given,
    the other end is filled with the newest published hour or 24 h before it.
    """
    if args.ultimos:
        return ultimos_slots(args.sat, args.ultimos)
    hasta = (datetime.fromisoformat(args.hasta) if args.hasta
             else ventana_ultimas(HORAS_POR_DEFECTO, args.sat)[1])
    desde = (datetime.fromisoformat(args.desde) if args.desde
             else hasta - timedelta(hours=HORAS_POR_DEFECTO))
    slots: list[datetime] = []
    t = desde
    while t < hasta:
        slots.append(t)
        t += timedelta(minutes=args.paso)
    return slots


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Download GOES-R ABI L2 LST 2 km full disk from NOAA S3. "
                    "All times are UTC.")
    ap.add_argument("--sat", default=SAT, help=f"satellite, e.g. G19 (default {SAT})")
    ap.add_argument("--desde", default=None,
                    help="start time UTC (default: 24 h before the newest published hour)")
    ap.add_argument("--hasta", default=None,
                    help="end time UTC, exclusive (default: just after the newest "
                         "published hour)")
    ap.add_argument("--ultimos", type=int, default=0, metavar="N",
                    help="download the N newest published granules "
                         "(ignores --desde/--hasta)")
    ap.add_argument("--paso", type=int, default=PASO,
                    help=f"minutes between slots (default {PASO}: the hourly LST cadence)")
    ap.add_argument("--out",
                    help="destination folder (default: goes_lst_<sat> under DATOS)")
    args = ap.parse_args(argv)

    if args.ultimos < 0:
        raise SystemExit("--ultimos must be >= 0")
    if args.paso <= 0:
        raise SystemExit("--paso must be > 0")

    try:
        slots = resolver_slots(args)
    except LookupError as exc:
        raise SystemExit(str(exc)) from exc
    if not slots:
        raise SystemExit(f"No {PREFIJO} slots for {args.sat} in the requested window.")

    destino = Path(args.out) if args.out else carpeta_datos(args.sat)
    destino.mkdir(parents=True, exist_ok=True)
    print(f"{args.sat} {PREFIJO}: {len(slots)} slots "
          f"({slots[0]} -> {slots[-1]} UTC)")
    print(f"Destination: {destino}")

    descargados = existentes = errores = 0
    inicio = time.time()
    for i, t in enumerate(slots, 1):
        try:
            clave = clave_de(args.sat, t)
            ruta = ruta_local(destino, clave)
            ya_existia = ruta.exists() and ruta.stat().st_size >= MINIMO_BYTES
            descargar(destino, args.sat, clave, minimo_bytes=MINIMO_BYTES)
            if ya_existia:
                existentes += 1
            else:
                descargados += 1
            if i % 10 == 0 or i == len(slots):
                elapsed = time.time() - inicio
                print(f"[{i}/{len(slots)}] {t:%Y-%m-%d %H:%M} UTC  "
                      f"downloaded={descargados} existing={existentes} "
                      f"errors={errores}  time={elapsed:.0f}s", flush=True)
        except Exception as e:                                  # gap or network failure
            errores += 1
            print(f"[{i}/{len(slots)}] {t:%Y-%m-%d %H:%M} UTC  ERROR: {e}", flush=True)

    elapsed = time.time() - inicio
    print(f"\nDone in {elapsed:.0f}s: downloaded={descargados}, "
          f"existing={existentes}, errors={errores}")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
