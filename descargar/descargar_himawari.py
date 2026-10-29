"""Descarga la banda 13 del AHI de Himawari-9 y la deja como campo de temperatura.

Flujo del proyecto: este es el único script que toca la red. Baja los archivos
**Himawari Standard Data (HSD)** de JMA desde el bucket publico de NOAA en AWS,
los decodifica, los calibra a temperatura de brillo y los guarda como un `.npz`
por slot de 10 min, para que `cuadros/cuadros_himawari_ir.py` pueda renderizar
**offline**.

Fuente: `https://noaa-himawari9.s3.amazonaws.com/AHI-L1b-FLDK/<AAA>/<MM>/<DD>/<HHMM>/`
Cada slot son 10 segmentos (`S0110` .. `S1010`), franjas horizontales de 550 lineas
cada una; entre los 10 se arma el disco completo de 5500 x 5500 pixeles a 2 km.

El HSD es un formato binario propio de JMA (11 bloques de cabecera + datos crudos
en little-endian uint16). La calibracion a temperatura de brillo es la estandar:
radiancia -> inversion de Planck a la longitud de onda central -> correccion
polinomial de JMA.

Uso (desde la raiz del proyecto):

    .venv\\Scripts\\python.exe descargar\\descargar_himawari.py
    .venv\\Scripts\\python.exe descargar\\descargar_himawari.py --desde 2026-10-20T04:00 --hasta 2026-10-22T04:00
    .venv\\Scripts\\python.exe descargar\\descargar_himawari.py --help   # no toca la red
"""
from __future__ import annotations

import argparse
import bz2
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from rutas import DATOS  # noqa: E402

SAT = "H09"                      # Himawari-9
BANDA = 13                       # AHI band 13 = 10.4 um (infrarrojo ventana)
RESOLUCION = "R20"               # 2 km
BUCKET = "https://noaa-himawari9.s3.amazonaws.com"
PREFIJO = "AHI-L1b-FLDK"

DESDE = datetime(2026, 10, 20, 4, 0)     # UTC
HASTA = datetime(2026, 10, 22, 4, 0)     # UTC
PASO_MIN = 10
SEGMENTOS = 10                    # franjas horizontales del disco completo
#: Cada franja tiene 550 lineas; el disco completo es 5500 x 5500 pixeles a 2 km.
FILAS_FRANJA = 550
COLS_DISCO = 5500
#: Se promedia cada bloque 2x2 -> disco de 2750 x 2750 (4 km), que es el mismo
#: detalle efectivo que la serie GOES C13 a 2712 px (su fuente tambien se
#: submuestrea a la mitad) y mucho mas liviano de guardar y reproyectar.
FACTOR = 2

#: Patron del nombre de archivo HSD: HS_H09_20261022_0030_B13_FLDK_R20_S0510.DAT.bz2
PATRON = re.compile(
    r"HS_(?P<sat>H\d{2})_(?P<fecha>\d{8})_(?P<hora>\d{4})_B(?P<banda>\d{2})_"
    r"(?P<area>[A-Z]{4})_(?P<res>R\d{2})_S(?P<seg>\d{2})(?P<sub>\d{2})\.DAT\.bz2")

# --------------------------------------------------------------------------- HSD
# Cabecera: 11 bloques. Cada uno arranca con `hblock_number` (u1) + `blocklength`
# (u2 LE); el 5 (calibracion) trae los coeficientes de los canales IR adentro.
BASIC = np.dtype([
    ("n", "u1"), ("l", "<u2"), ("nb", "<u2"), ("bo", "u1"), ("sat", "S16"), ("pc", "S16"),
    ("area", "S4"), ("oot", "S2"), ("timeline", "<u2"), ("t0", "f8"), ("t1", "f8"),
    ("tfc", "f8"), ("hlen", "<u4"), ("dlen", "<u4"), ("q1", "u1"), ("q2", "u1"),
    ("q3", "u1"), ("q4", "u1"), ("ver", "S32"), ("fn", "S128"), ("spare", "S40")])
DATA = np.dtype([
    ("n", "u1"), ("l", "<u2"), ("bits", "<u2"), ("ncols", "<u2"), ("nlines", "<u2"),
    ("comp", "u1"), ("spare", "S40")])
PROJ = np.dtype([
    ("n", "u1"), ("l", "<u2"), ("sub_lon", "f8"), ("CFAC", "<u4"), ("LFAC", "<u4"),
    ("COFF", "f4"), ("LOFF", "f4"), ("dec", "f8"), ("a", "f8"), ("b", "f8"),
    ("r1", "f8"), ("r2", "f8"), ("r3", "f8"), ("csd", "f8"), ("rt", "<i2"),
    ("rs", "<i2"), ("spare", "S40")])
CAL = np.dtype([
    ("n", "u1"), ("l", "<u2"), ("band", "<u2"), ("cwl", "f8"), ("bits", "<u2"),
    ("err", "<u2"), ("out", "<u2"), ("gain", "f8"), ("off", "f8")])
IRCAL = np.dtype([
    ("c0", "f8"), ("c1", "f8"), ("c2", "f8"), ("c0b", "f8"), ("c1b", "f8"), ("c2b", "f8"),
    ("c", "f8"), ("h", "f8"), ("k", "f8"), ("spare", "S40")])
SEG = np.dtype([
    ("n", "u1"), ("l", "<u2"), ("total_segments", "u1"), ("seq", "u1"),
    ("first_line", "<u2"), ("spare", "S40")])
BLOQUE = np.dtype([("n", "u1"), ("l", "<u2")])


def leer_cabecera(raw: bytes) -> dict:
    """Lee los 11 bloques de la cabecera HSD y devuelve lo que hace falta.

    `raw` son los bytes YA descomprimidos del archivo `.DAT`.
    """
    buf = memoryview(raw)
    info: dict = {}
    off = 0
    for i in range(1, 12):
        bloque = np.frombuffer(buf, dtype=BLOQUE, count=1, offset=off)[0]
        if i == 1:
            info["basic"] = np.frombuffer(buf, dtype=BASIC, count=1, offset=off)[0]
        elif i == 2:
            info["data"] = np.frombuffer(buf, dtype=DATA, count=1, offset=off)[0]
        elif i == 3:
            info["proj"] = np.frombuffer(buf, dtype=PROJ, count=1, offset=off)[0]
        elif i == 5:
            info["cal5"] = np.frombuffer(buf, dtype=CAL, count=1, offset=off)[0]
            # Los coeficientes IR van adentro del bloque 5, despues de sus campos.
            info["ircal"] = np.frombuffer(buf, dtype=IRCAL, count=1,
                                          offset=off + CAL.itemsize)[0]
        elif i == 7:
            info["seg"] = np.frombuffer(buf, dtype=SEG, count=1, offset=off)[0]
        off += int(bloque["l"])
    return info


def a_temperatura(dn: np.ndarray, cal5, ircal) -> np.ndarray:
    """Cuenta crudos -> temperatura de brillo en Kelvin (NaN donde no hay dato)."""
    gain = float(cal5["gain"])
    offset = float(cal5["off"])
    cwl = float(cal5["cwl"]) * 1e-6
    c = float(ircal["c"])
    h = float(ircal["h"])
    k = float(ircal["k"])

    rad = dn.astype(np.float64) * gain + offset            # W/m2/sr/um
    a = (h * c) / (k * cwl)
    b = (2 * h * c ** 2) / (rad * 1e6 * cwl ** 5) + 1
    with np.errstate(invalid="ignore", divide="ignore"):
        te = a / np.log(b)                                  # T equivalente (Planck)
    tb = float(ircal["c0"]) + float(ircal["c1"]) * te + float(ircal["c2"]) * te ** 2
    tb = np.clip(tb, 0, None)
    malo = (dn == 0) | (dn == int(cal5["err"])) | (dn == int(cal5["out"])) | (rad <= 0)
    tb[malo] = np.nan
    return tb


def geometria(proj) -> dict:
    """Parametros de la proyeccion geostacionaria y de la grilla del disco.

    Convencion CGMS (LRIT/HRIT): el angulo de barrido en grados es
    `x = (columna - COFF) / (CFAC / 2^16)` y `y = (LOFF - linea) / (LFAC / 2^16)`,
    con la linea 1 al NORTE. La distancia en el plano es `radianes(angulo) * h`.
    """
    a = float(proj["a"]) * 1000.0
    b = float(proj["b"]) * 1000.0
    h = (float(proj["dec"]) - float(proj["a"])) * 1000.0
    cfac = float(proj["CFAC"])
    lfac = float(proj["LFAC"])
    coff = float(proj["COFF"])
    loff = float(proj["LOFF"])
    # Centro del bloque 2x2 (columna/linea 1-based del centro del bloque).
    x0 = np.deg2rad((1.5 - coff) / (cfac / 2 ** 16)) * h
    y0 = np.deg2rad((loff - 1.5) / (lfac / 2 ** 16)) * h
    dx = np.deg2rad(FACTOR / (cfac / 2 ** 16)) * h
    dy = np.deg2rad(-FACTOR / (lfac / 2 ** 16)) * h
    return {
        "sub_lon": float(proj["sub_lon"]), "a": a, "b": b, "h": h,
        "x0": float(x0), "y0": float(y0), "dx": float(dx), "dy": float(dy),
    }


# --------------------------------------------------------------------------- red
def clave_de(t: datetime, banda: int = BANDA) -> list[str]:
    """Claves S3 de los 10 segmentos del slot `t`."""
    base = (f"{PREFIJO}/{t:%Y/%m/%d}/{t:%H%M}/"
            f"HS_{SAT}_{t:%Y%m%d}_{t:%H%M}_B{banda:02d}_FLDK_{RESOLUCION}")
    return [f"{base}_S{s:02d}10.DAT.bz2" for s in range(1, SEGMENTOS + 1)]


def bajar(clave: str, destino: Path, timeout: int = 300) -> bytes:
    """Descarga un `.DAT.bz2` y devuelve los bytes descomprimidos."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(destino.suffix + ".parcial")
    with urllib.request.urlopen(f"{BUCKET}/{clave}", timeout=timeout) as r:
        with open(tmp, "wb") as fh:
            while True:
                trozo = r.read(1 << 20)
                if not trozo:
                    break
                fh.write(trozo)
    crudo = bz2.decompress(tmp.read_bytes())
    tmp.unlink()
    return crudo


def _franja(clave: str, cache: Path | None):
    """Descarga y decodifica una franja; devuelve `(first_line, campo_K)`."""
    m = PATRON.search(Path(clave).name)
    if not m:
        raise SystemExit(f"Nombre de archivo HSD inesperado: {clave}")
    destino = (cache / Path(clave).name) if cache is not None else Path(f"{clave}.tmp")
    crudo = bajar(clave, destino)
    info = leer_cabecera(crudo)
    nlines = int(info["data"]["nlines"])
    ncols = int(info["data"]["ncols"])
    dn = np.frombuffer(crudo, dtype="<u2", count=nlines * ncols,
                       offset=int(info["basic"]["hlen"])).reshape(nlines, ncols)
    tb = a_temperatura(dn, info["cal5"], info["ircal"])
    # Promedio 2x2 (el disco nativo es de 2 km; guardamos a 4 km).
    tb = tb.reshape(nlines // FACTOR, FACTOR, ncols // FACTOR, FACTOR).mean(axis=(1, 3))
    return int(info["seg"]["first_line"]), tb, geometria(info["proj"])


def slot_a_campo(t: datetime, banda: int = BANDA, cache: Path | None = None,
                 verbose: bool = True, hilos: int = 6) -> tuple[np.ndarray, dict]:
    """Arma el disco completo de un slot y devuelve `(campo_K, geometria)`.

    `campo_K` tiene forma `(2750, 2750)` (4 km) con la temperatura de brillo en
    Kelvin; la fila 0 es el norte. Las franjas se ordenan por `first_line`, que
    es el numero de linea global de la primera linea de cada una.
    """
    from concurrent.futures import ThreadPoolExecutor

    claves = clave_de(t, banda)
    with ThreadPoolExecutor(max_workers=hilos) as pool:
        resultados = list(pool.map(lambda c: _franja(c, cache), claves))
    franjas = {r[0]: r[1] for r in resultados}
    geo = resultados[0][2]
    orden = sorted(franjas)
    if len(orden) != SEGMENTOS:
        raise SystemExit(f"Faltan franjas del slot {t:%Y-%m-%d %H:%M}: hay {len(orden)}")
    campo = np.vstack([franjas[f] for f in orden])
    if verbose:
        valido = np.isfinite(campo)
        print(f"    {t:%H:%M} UTC  {campo.shape}  "
              f"TB {np.nanmin(campo[valido]) - 273.15:6.1f} .. "
              f"{np.nanmax(campo[valido]) - 273.15:6.1f} C  "
              f"validos {valido.mean() * 100:5.1f}%", flush=True)
    return campo, geo


def guardar_slot(t: datetime, campo: np.ndarray, geo: dict, destino: Path) -> Path:
    """Guarda el slot como `.npz` (temperatura en C + geometria de la grilla)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    # numpy agrega ".npz" si el nombre no termina asi: el parcial tambien lo lleva.
    parcial = destino.with_name(destino.name + ".parcial.npz")
    np.savez_compressed(
        parcial,
        tb=(campo - 273.15).astype(np.float32),
        x0=geo["x0"], y0=geo["y0"], dx=geo["dx"], dy=geo["dy"],
        sub_lon=geo["sub_lon"], a=geo["a"], b=geo["b"], h=geo["h"],
        tiempo=np.datetime64(f"{t:%Y-%m-%dT%H:%M}"),
    )
    parcial.replace(destino)
    return destino


def carpeta_datos(sat: str = SAT, banda: int = BANDA) -> Path:
    """Carpeta destino: `himawari_b13_h09`."""
    return DATOS / f"himawari_b{banda:02d}_{sat.lower()}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Descarga Himawari-9 AHI L1b (HSD) desde NOAA S3 y arma un .npz "
                    "por slot con la temperatura de brillo.")
    ap.add_argument("--sat", default=SAT, help=f"satelite (por defecto {SAT})")
    ap.add_argument("--banda", type=int, default=BANDA, help=f"banda AHI (por defecto {BANDA})")
    ap.add_argument("--desde", default=DESDE.isoformat(),
                    help=f"inicio UTC (por defecto {DESDE:%Y-%m-%dT%H:%M})")
    ap.add_argument("--hasta", default=HASTA.isoformat(),
                    help=f"fin UTC (por defecto {HASTA:%Y-%m-%dT%H:%M})")
    ap.add_argument("--paso", type=int, default=PASO_MIN,
                    help=f"minutos entre slots (por defecto {PASO_MIN})")
    ap.add_argument("--out", help="carpeta destino (por defecto, la del satelite/banda)")
    ap.add_argument("--cache", help="carpeta para guardar los .DAT.bz2 (por defecto no se guardan)")
    args = ap.parse_args(argv)

    t0 = datetime.fromisoformat(args.desde)
    t1 = datetime.fromisoformat(args.hasta)
    destino = Path(args.out) if args.out else carpeta_datos(args.sat, args.banda)
    destino.mkdir(parents=True, exist_ok=True)
    cache = Path(args.cache) if args.cache else None

    slots = []
    t = t0
    while t < t1:
        slots.append(t)
        t += timedelta(minutes=args.paso)

    print(f"Himawari-{args.sat[1:]} AHI B{args.banda:02d} ({RESOLUCION}) | "
          f"{len(slots)} slots ({t0} -> {t1} UTC)")
    print(f"Destino: {destino}")

    hechos = omitidos = errores = 0
    inicio = time.time()
    for i, t in enumerate(slots, 1):
        salida = destino / f"{t:%Y%m%d_%H%M}.npz"
        if salida.exists():
            omitidos += 1
            continue
        try:
            campo, geo = slot_a_campo(t, args.banda, cache=cache)
            guardar_slot(t, campo, geo, salida)
            hechos += 1
        except Exception as exc:                       # hueco de red o archivo faltante
            errores += 1
            print(f"[{i}/{len(slots)}] {t:%Y-%m-%d %H:%M} UTC  ERROR: {exc}", flush=True)
        if i % 10 == 0 or i == len(slots):
            print(f"[{i}/{len(slots)}] {t:%Y-%m-%d %H:%M} UTC  hechos={hechos} "
                  f"omitidos={omitidos} errores={errores}  "
                  f"tiempo={time.time() - inicio:.0f}s", flush=True)

    print(f"\nFinalizado en {time.time() - inicio:.0f}s: hechos={hechos}, "
          f"omitidos={omitidos}, errores={errores}")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
