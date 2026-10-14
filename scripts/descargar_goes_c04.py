"""Descarga GOES-18 C04 (cirrus) para un rango UTC desde NOAA S3.

Reutiliza la lógica de `lib/goes_fetch.py` (la misma que usan los notebooks).
Salta los archivos que ya existen localmente (> 1 MB).

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe scripts\\descargar_goes_c04.py
    .venv\\Scripts\\python.exe scripts\\descargar_goes_c04.py --desde 2026-10-02 --hasta 2026-10-05
    .venv\\Scripts\\python.exe scripts\\descargar_goes_c04.py --help   # no toca la red
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "lib"))
from goes_fetch import clave_de, descargar, ruta_local  # noqa: E402

SAT, BANDA = "G18", "C04"
DATOS = Path(r"D:\Users\guill\dataset era5\goes_c04_g18")

T0 = datetime(2026, 10, 2, 0, 0)   # UTC
T1 = datetime(2026, 10, 5, 0, 0)   # UTC
PASO_MIN = 10


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Descarga GOES-18 C04 (cirrus) para un rango UTC desde NOAA S3.")
    ap.add_argument("--desde", default=T0.isoformat(),
                    help=f"inicio UTC, AAAA-MM-DD[THH:MM] (por defecto {T0:%Y-%m-%d})")
    ap.add_argument("--hasta", default=T1.isoformat(),
                    help=f"fin UTC (por defecto {T1:%Y-%m-%d})")
    ap.add_argument("--paso", type=int, default=PASO_MIN,
                    help=f"minutos entre slots (por defecto {PASO_MIN})")
    args = ap.parse_args(argv)

    t0, t1 = datetime.fromisoformat(args.desde), datetime.fromisoformat(args.hasta)
    DATOS.mkdir(parents=True, exist_ok=True)
    slots = []
    t = t0
    while t < t1:
        slots.append(t)
        t += timedelta(minutes=args.paso)

    print(f"Total slots: {len(slots)} ({t0} -> {t1} UTC)")
    print(f"Destino: {DATOS}")

    descargados = existentes = errores = 0
    inicio = time.time()
    for i, t in enumerate(slots, 1):
        try:
            clave = clave_de(SAT, BANDA, t)
            destino = ruta_local(DATOS, clave)
            ya_existia = destino.exists() and destino.stat().st_size > 1_000_000
            descargar(DATOS, SAT, clave)
            if ya_existia:
                existentes += 1
            else:
                descargados += 1
            if i % 10 == 0 or i == len(slots):
                elapsed = time.time() - inicio
                print(f"[{i}/{len(slots)}] {t:%Y-%m-%d %H:%M} UTC  "
                      f"descargados={descargados} existentes={existentes} "
                      f"errores={errores}  tiempo={elapsed:.0f}s", flush=True)
        except Exception as e:                                 # hueco o fallo de red
            errores += 1
            print(f"[{i}/{len(slots)}] {t:%Y-%m-%d %H:%M} UTC  ERROR: {e}", flush=True)

    elapsed = time.time() - inicio
    print(f"\nFinalizado en {elapsed:.0f}s: descargados={descargados}, "
          f"existentes={existentes}, errores={errores}")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
