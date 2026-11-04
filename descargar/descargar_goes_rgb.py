"""Descarga las bandas crudas que forman un RGB oficial de GOES-R ABI.

Un producto RGB (Dust, Air Mass, Fire Temperature) no es una banda: son 3-4
bandas del mismo slot. Este script reutiliza `descargar/goes_descarga.py` y baja
todas las bandas de la receta para cada slot pedido, en la carpeta de siempre
(`goes_<banda>_<sat>`, p. ej. `goes_c15_g19`).

  * `--ultimos N` — los N slots más nuevos donde están TODAS las bandas.
  * `--desde/--hasta` — rango UTC explícito (se saltea lo que ya está en disco).

Todas las horas son UTC (Paraguay es UTC-3).

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe descargar\\descargar_goes_rgb.py --producto dust --ultimos 10
    .venv\\Scripts\\python.exe descargar\\descargar_goes_rgb.py --producto airmass --desde 2026-11-04T12:00 --hasta 2026-11-04T13:00
    .venv\\Scripts\\python.exe descargar\\descargar_goes_rgb.py --help   # no toca la red
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
from goes_reciente import PASO, ahora_utc, piso_slot, ultimos_slots_conjunto  # noqa: E402
from rgb_goes import PRODUCTOS, bandas  # noqa: E402
from rutas import DATOS  # noqa: E402

SAT = "G19"
PRODUCTO = "dust"
INTENTOS_HORAS = 24


def carpeta_datos(sat: str, banda: str) -> Path:
    """Carpeta destino: `goes_<banda>_<sat>` (la misma que usa el render)."""
    return DATOS / f"goes_{banda.lower()}_{sat.lower()}"


def slots_completos(sat: str, producto: str, n: int, ahora: datetime | None = None,
                    paso: int = PASO, intentos_horas: int = INTENTOS_HORAS) -> list[datetime]:
    """Los `n` instantes más nuevos donde están publicadas TODAS las bandas."""
    return ultimos_slots_conjunto(
        sat, bandas(producto), n, ahora=ahora, paso=paso, intentos_horas=intentos_horas
    )


def resolver_slots(args) -> list[datetime]:
    """Slots a bajar: la cola publicada o el rango explícito."""
    if args.ultimos:
        return slots_completos(args.sat, args.producto, args.ultimos, paso=args.paso)
    hasta = datetime.fromisoformat(args.hasta) if args.hasta else piso_slot(
        ahora_utc(), args.paso)
    desde = datetime.fromisoformat(args.desde) if args.desde else hasta - timedelta(hours=24)
    slots: list[datetime] = []
    t = desde
    while t < hasta:
        slots.append(t)
        t += timedelta(minutes=args.paso)
    return slots


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Descarga las bandas de un RGB oficial de GOES-R ABI (UTC).")
    ap.add_argument("--producto", choices=PRODUCTOS, default=PRODUCTO,
                    help=f"producto RGB (por defecto {PRODUCTO})")
    ap.add_argument("--sat", default=SAT, help=f"satélite, p. ej. G19 (por defecto {SAT})")
    ap.add_argument("--desde", default=None, help="inicio UTC (por defecto, 24 h antes)")
    ap.add_argument("--hasta", default=None, help="fin UTC exclusivo (por defecto, ahora)")
    ap.add_argument("--ultimos", type=int, default=0, metavar="N",
                    help="baja los N slots más nuevos con TODAS las bandas")
    ap.add_argument("--paso", type=int, default=PASO,
                    help=f"minutos entre slots (por defecto {PASO})")
    args = ap.parse_args(argv)

    if args.ultimos < 0:
        raise SystemExit("--ultimos debe ser >= 0")
    if args.paso <= 0:
        raise SystemExit("--paso debe ser > 0")

    necesarias = bandas(args.producto)
    try:
        slots = resolver_slots(args)
    except LookupError as exc:
        raise SystemExit(str(exc)) from exc
    if not slots:
        raise SystemExit(
            f"No hay slots de {args.sat} con las bandas {', '.join(necesarias)} "
            f"para {args.producto}.")

    print(f"{args.sat} {args.producto}: {len(slots)} slots "
          f"({slots[0]} -> {slots[-1]} UTC) · bandas {', '.join(necesarias)}")
    for banda in necesarias:
        print(f"  {banda}: {carpeta_datos(args.sat, banda)}")

    descargados = existentes = errores = 0
    inicio = time.time()
    for i, t in enumerate(slots, 1):
        for banda in necesarias:
            try:
                clave = clave_de(args.sat, banda, t)
                ruta = ruta_local(carpeta_datos(args.sat, banda), clave)
                ya_existia = ruta.exists() and ruta.stat().st_size > 1_000_000
                descargar(carpeta_datos(args.sat, banda), args.sat, clave)
                if ya_existia:
                    existentes += 1
                else:
                    descargados += 1
            except Exception as e:  # hueco o fallo de red: se sigue con el resto
                errores += 1
                print(f"[{i}/{len(slots)}] {t:%Y-%m-%d %H:%M} UTC {banda} ERROR: {e}",
                      flush=True)
        if i % 10 == 0 or i == len(slots):
            elapsed = time.time() - inicio
            print(f"[{i}/{len(slots)}] {t:%Y-%m-%d %H:%M} UTC  "
                  f"descargados={descargados} existentes={existentes} "
                  f"errores={errores}  tiempo={elapsed:.0f}s", flush=True)

    elapsed = time.time() - inicio
    print(f"\nFinalizado en {elapsed:.0f}s: descargados={descargados}, "
          f"existentes={existentes}, errores={errores}")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
