"""Descarga archivos GOES-R ABI L2 CMIP desde el bucket público de NOAA S3.

Reutiliza `descargar/goes_descarga.py` (claves S3 y bajada) y `comun/goes_lectura.py`
(ruta local). Salta los archivos que ya existen localmente (> 1 MB) y guarda en la
carpeta del satélite/banda bajo `comun.rutas.DATOS`.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe descargar\\descargar_goes.py
    .venv\\Scripts\\python.exe descargar\\descargar_goes.py --sat G19 --banda C13 --desde 2026-10-02 --hasta 2026-10-05
    .venv\\Scripts\\python.exe descargar\\descargar_goes.py --help   # no toca la red
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from goes_descarga import clave_de, descargar  # noqa: E402
from goes_lectura import ruta_local  # noqa: E402
from rutas import DATOS  # noqa: E402

SAT, BANDA = "G19", "C13"
DESDE = datetime(2026, 10, 2, 0, 0)   # UTC
HASTA = datetime(2026, 10, 5, 0, 0)   # UTC
PASO_MIN = 10


def carpeta_datos(sat: str, banda: str) -> Path:
    """Carpeta destino: `goes_<banda>_<sat>` (p. ej. goes_c13_g19)."""
    return DATOS / f"goes_c{banda[1:].lower()}_{sat.lower()}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Descarga GOES-R ABI L2 CMIP desde NOAA S3.")
    ap.add_argument("--sat", default=SAT, help=f"satélite, p. ej. G19 (por defecto {SAT})")
    ap.add_argument("--banda", default=BANDA, help=f"banda, p. ej. C13 (por defecto {BANDA})")
    ap.add_argument("--desde", default=DESDE.isoformat(),
                    help=f"inicio UTC (por defecto {DESDE:%Y-%m-%d})")
    ap.add_argument("--hasta", default=HASTA.isoformat(),
                    help=f"fin UTC (por defecto {HASTA:%Y-%m-%d})")
    ap.add_argument("--paso", type=int, default=PASO_MIN,
                    help=f"minutos entre slots (por defecto {PASO_MIN})")
    ap.add_argument("--out", help="carpeta destino (por defecto, la del satélite/banda)")
    args = ap.parse_args(argv)

    t0, t1 = datetime.fromisoformat(args.desde), datetime.fromisoformat(args.hasta)
    destino = Path(args.out) if args.out else carpeta_datos(args.sat, args.banda)
    destino.mkdir(parents=True, exist_ok=True)

    slots = []
    t = t0
    while t < t1:
        slots.append(t)
        t += timedelta(minutes=args.paso)

    print(f"{args.sat} {args.banda}: {len(slots)} slots ({t0} -> {t1} UTC)")
    print(f"Destino: {destino}")

    descargados = existentes = errores = 0
    inicio = time.time()
    for i, t in enumerate(slots, 1):
        try:
            clave = clave_de(args.sat, args.banda, t)
            ruta = ruta_local(destino, clave)
            ya_existia = ruta.exists() and ruta.stat().st_size > 1_000_000
            descargar(destino, args.sat, clave)
            if ya_existia:
                existentes += 1
            else:
                descargados += 1
            if i % 10 == 0 or i == len(slots):
                elapsed = time.time() - inicio
                print(f"[{i}/{len(slots)}] {t:%Y-%m-%d %H:%M} UTC  "
                      f"descargados={descargados} existentes={existentes} "
                      f"errores={errores}  tiempo={elapsed:.0f}s", flush=True)
        except Exception as e:                                  # hueco o fallo de red
            errores += 1
            print(f"[{i}/{len(slots)}] {t:%Y-%m-%d %H:%M} UTC  ERROR: {e}", flush=True)

    elapsed = time.time() - inicio
    print(f"\nFinalizado en {elapsed:.0f}s: descargados={descargados}, "
          f"existentes={existentes}, errores={errores}")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
