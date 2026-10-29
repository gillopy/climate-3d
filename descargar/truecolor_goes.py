"""Descarga las bandas visibles de GOES-R ABI para armar el póster de color real.

El color real **no se puede hacer con una sola banda**. El ABI tiene tres canales
útiles en el visible/próximo infrarrojo y hay que bajar los tres para el mismo slot:

  * ``C01`` — 0.47 µm, azul (1 km).
  * ``C02`` — 0.64 µm, rojo (0.5 km). Es el archivo más grande del set (~410 MB).
  * ``C03`` — 0.86 µm, "veggie" (1 km), el que aporta la textura de la vegetación.

Cada banda va a su carpeta (``goes_c01_g19``, ...), igual que ``goes_c13_g19``: así
el mismo slot se puede mezclar con la C13 que ya está descargada.

No confundir con ``descargar/truecolor.py``, que baja un JPEG ya compuesto de NASA
GIBS. Acá se baja el dato crudo (L2 CMIP en netCDF) del bucket público de NOAA, que
es lo único que permite componer el color con criterio propio.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe descargar\\truecolor_goes.py --n 1
    .venv\\Scripts\\python.exe descargar\\truecolor_goes.py --desde 2026-10-27T18:00 --n 3
    .venv\\Scripts\\python.exe descargar\\truecolor_goes.py --help   # no toca la red
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
sys.path.insert(0, str(RAIZ / "descargar"))

from goes_descarga import clave_de, descargar  # noqa: E402
from goes_lectura import PATRON  # noqa: E402
from rutas import DATOS  # noqa: E402

SAT = "G19"
BANDAS = ("C01", "C02", "C03")
N, PASO = 1, 10


def carpeta(banda: str, sat: str = SAT) -> Path:
    """Carpeta de una banda: ``goes_c01_g19`` bajo ``comun.rutas.DATOS``."""
    return DATOS / f"goes_c{banda[1:].lower()}_{sat.lower()}"


def fecha_de(nc: Path) -> datetime:
    """Fecha/hora UTC del slot, leída del nombre (``_sAAAADDDHHMMSS_``)."""
    m = PATRON.search(Path(nc).name)
    if not m:
        return datetime.fromtimestamp(Path(nc).stat().st_mtime)
    s = m.group("s")
    return (datetime(int(s[:4]), 1, 1)
            + timedelta(days=int(s[4:7]) - 1, hours=int(s[7:9]), minutes=int(s[9:11])))


def slots_locales(banda: str, sat: str = SAT) -> list[datetime]:
    """Slots con ``.nc`` local de esa banda, ordenados."""
    carpeta_ = carpeta(banda, sat)
    if not carpeta_.exists():
        return []
    return sorted(fecha_de(f) for f in carpeta_.glob("OR_ABI-*.nc") if PATRON.search(f.name))


def slot_de_referencia(bandas=BANDAS, sat: str = SAT) -> datetime | None:
    """Último slot que ya está completo en todas las bandas (si hay alguna)."""
    comunes = None
    for banda in bandas:
        s = set(slots_locales(banda, sat))
        comunes = s if comunes is None else (comunes & s)
    if not comunes:
        return None
    return max(comunes)


def descargar_slot(t: datetime, sat: str = SAT, bandas=BANDAS) -> dict[str, Path]:
    """Baja el slot ``t`` de todas las bandas. Devuelve ``{banda: ruta local}``."""
    salida: dict[str, Path] = {}
    for banda in bandas:
        clave = clave_de(sat, banda, t)
        salida[banda] = descargar(carpeta(banda, sat), sat, clave)
    return salida


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Descarga C01+C02+C03 (ABI) para el póster de color real.")
    ap.add_argument("--desde", help="primer slot, UTC ISO (por defecto, el último que "
                                    "ya esté descargado en las tres bandas)")
    ap.add_argument("--n", type=int, default=N, help=f"cantidad de slots (por defecto {N})")
    ap.add_argument("--paso", type=int, default=PASO,
                    help=f"minutos entre slots (por defecto {PASO})")
    ap.add_argument("--sat", default=SAT, help=f"satélite, p. ej. G19 o G18 (por defecto {SAT})")
    ap.add_argument("--bandas", default=",".join(BANDAS),
                    help=f"bandas a bajar (por defecto {','.join(BANDAS)})")
    args = ap.parse_args(argv)

    bandas = tuple(b.strip().upper() for b in args.bandas.split(",") if b.strip())
    desconocidas = [b for b in bandas if b not in BANDAS]
    if desconocidas:
        raise SystemExit(f"Bandas no soportadas: {desconocidas}. Usá {list(BANDAS)}.")

    if args.desde:
        t0 = datetime.fromisoformat(args.desde)
    else:
        t0 = slot_de_referencia(bandas, args.sat)
        if t0 is None:
            raise SystemExit("No hay ningún slot local completo en las tres bandas. "
                             "Pasá --desde (UTC), p. ej. --desde 2026-10-27T18:00")

    tiempos = [t0 + timedelta(minutes=args.paso * i) for i in range(args.n)]
    print(f"{len(tiempos)} slot(s) desde {t0:%Y-%m-%d %H:%M} UTC | paso {args.paso} min")
    print(f"bandas {', '.join(bandas)} | satélite {args.sat} | destino {DATOS}")

    antes = {b: set(p.name for p in carpeta(b, args.sat).glob("*.nc"))
             if carpeta(b, args.sat).exists() else set() for b in bandas}
    fallidos = 0
    for i, t in enumerate(tiempos, 1):
        try:
            rutas = descargar_slot(t, args.sat, bandas)
        except LookupError as exc:
            fallidos += 1
            print(f"[{i}/{len(tiempos)}] {t:%Y-%m-%d %H:%M} UTC  SIN DATO: {exc}", flush=True)
            continue
        detalle = "  ".join(f"{b} {p.stat().st_size / 1e6:.0f} MB"
                            for b, p in rutas.items())
        print(f"[{i}/{len(tiempos)}] {t:%Y-%m-%d %H:%M} UTC  {detalle}", flush=True)

    nuevos = []
    for b in bandas:
        carpeta_ = carpeta(b, args.sat)
        if carpeta_.exists():
            nuevos += [p for p in carpeta_.glob("*.nc") if p.name not in antes[b]]
    if nuevos:
        total = sum(p.stat().st_size for p in nuevos) / 1e9
        print(f"{len(nuevos)} archivo(s) nuevos, {total:.2f} GB")

    if fallidos:
        raise SystemExit(f"Faltan {fallidos} slot(s). Volvé a correr el mismo comando: "
                         "lo que ya está se reutiliza y sólo se reintenta lo que falta.")

    print("Ahora renderizá con:")
    print(f"  .venv\\Scripts\\python.exe prototipos\\poster_goes_truecolor.py "
          f"--desde {t0:%Y-%m-%dT%H:%M}" + (f" --n {args.n}" if args.n > 1 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
