"""Descarga archivos GOES-R ABI L2 CMIP desde el bucket público de NOAA S3.

Sin flags baja las **últimas 24 horas UTC** (hasta el último slot ya publicado),
no una fecha fija. `--ultimos N` baja exactamente los N cuadros más nuevos, que
es el camino corto para "quiero lo de ahora" (y lo que usa la app).

Reutiliza `descargar/goes_descarga.py` (claves S3 y bajada),
`comun/goes_reciente.py` (qué es "lo último") y `comun/goes_lectura.py`
(ruta local). Salta los archivos que ya existen localmente (> 1 MB) y guarda en
la carpeta del satélite/banda bajo `comun.rutas.DATOS`.

Todas las horas son UTC (Paraguay es UTC-3).

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe descargar\\descargar_goes.py --ultimos 10
    .venv\\Scripts\\python.exe descargar\\descargar_goes.py        # últimas 24 h
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
from goes_reciente import ventana_ultimas, ventana_ultimos  # noqa: E402
from rutas import DATOS  # noqa: E402

SAT, BANDA = "G19", "C13"
HORAS_POR_DEFECTO = 24
PASO_MIN = 10


def carpeta_datos(sat: str, banda: str) -> Path:
    """Carpeta destino: `goes_<banda>_<sat>` (p. ej. goes_c13_g19)."""
    return DATOS / f"goes_c{banda[1:].lower()}_{sat.lower()}"


def resolver_ventana(args) -> tuple[datetime, datetime, str]:
    """Rango `[desde, hasta)` que se va a recorrer, con una etiqueta para el log.

    - `--ultimos N` gana sobre todo: los N slots ya publicados.
    - Sin fechas: las últimas 24 h que terminan en el último slot publicado.
    - Sólo `--desde` (o sólo `--hasta`): la otra punta se completa con lo último
      publicado o con 24 h, respectivamente.
    """
    if args.ultimos:
        desde, hasta = ventana_ultimos(args.ultimos, args.sat, args.banda, paso=args.paso)
        return desde, hasta, f"últimos {args.ultimos} cuadros"

    hasta = (datetime.fromisoformat(args.hasta) if args.hasta
             else ventana_ultimas(HORAS_POR_DEFECTO, args.sat, args.banda,
                                  paso=args.paso)[1])
    desde = (datetime.fromisoformat(args.desde) if args.desde
             else hasta - timedelta(hours=HORAS_POR_DEFECTO))
    etiqueta = "rango pedido" if (args.desde or args.hasta) else f"últimas {HORAS_POR_DEFECTO} h"
    return desde, hasta, etiqueta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Descarga GOES-R ABI L2 CMIP desde NOAA S3. Todas las horas son UTC.")
    ap.add_argument("--sat", default=SAT, help=f"satélite, p. ej. G19 (por defecto {SAT})")
    ap.add_argument("--banda", default=BANDA, help=f"banda, p. ej. C13 (por defecto {BANDA})")
    ap.add_argument("--desde", default=None,
                    help="inicio UTC (por defecto, 24 h antes del último slot publicado)")
    ap.add_argument("--hasta", default=None,
                    help="fin UTC exclusivo (por defecto, justo después del último publicado)")
    ap.add_argument("--ultimos", type=int, default=0, metavar="N",
                    help="baja los N cuadros más nuevos publicados (ignora --desde/--hasta)")
    ap.add_argument("--paso", type=int, default=PASO_MIN,
                    help=f"minutos entre slots (por defecto {PASO_MIN})")
    ap.add_argument("--out", help="carpeta destino (por defecto, la del satélite/banda)")
    args = ap.parse_args(argv)

    if args.ultimos < 0:
        raise SystemExit("--ultimos debe ser >= 0")
    if args.paso <= 0:
        raise SystemExit("--paso debe ser > 0")

    try:
        t0, t1, etiqueta = resolver_ventana(args)
    except LookupError as exc:
        raise SystemExit(str(exc)) from exc

    destino = Path(args.out) if args.out else carpeta_datos(args.sat, args.banda)
    destino.mkdir(parents=True, exist_ok=True)

    slots = []
    t = t0
    while t < t1:
        slots.append(t)
        t += timedelta(minutes=args.paso)

    print(f"{args.sat} {args.banda}: {len(slots)} slots ({t0} -> {t1} UTC) · {etiqueta}")
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
