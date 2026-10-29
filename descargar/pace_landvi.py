"""Baja los gránulos diarios de **PACE OCI L3M LANDVI** (índices de vegetación terrestre).

LANDVI es la suite de índices de vegetación que PACE/OCI publica sobre tierra: seis
heredados de la era MODIS (`ndvi`, `evi`, `ndwi`, `ndii`, `cci`, `ndsi`) y cuatro
habilitados por el sensor hiperespectral (`pri`, `cire`, `car`, `mari`). Es el insumo con
el que NASA Earth Observatory arma los mapas de "red leaves": el índice `mari` mide
antocianina (lo rojo) y `cire`/`cci` la clorofila (lo verde).

Fuente (OB.DAAC, no GIBS: GIBS no publica PACE sobre tierra):

    https://oceandata.sci.gsfc.nasa.gov/getfile/PACE_OCI.<YYYYMMDD>.L3m.DAY.LANDVI.V3_1.<res>.NRT.nc

El archivo pesa ~170 MB por día en 4 km y **exige Earthdata Login**: `getfile` responde
302 a `urs.earthdata.nasa.gov` y sin sesión válida no entrega el NetCDF. Este script
acepta dos formas de autenticarse, y ninguna guarda la contraseña en el repo:

  * `--cookies <archivo.json>`: lista de cookies exportada de un navegador ya logueado
    (formato de Playwright: `[{name, value, domain, path, ...}]`).
  * `~/.netrc` con `machine urs.earthdata.nasa.gov login <usuario> password <clave>`
    (el método histórico de OBPG: autenticación básica preventiva).

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe descargar\\pace_landvi.py --desde 2026-09-29 --hasta 2026-10-04
    .venv\\Scripts\\python.exe descargar\\pace_landvi.py --help   # no toca la red
"""
from __future__ import annotations

import argparse
import json
import netrc
import sys
from datetime import date, timedelta
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from rutas import DATOS  # noqa: E402

BASE = "https://oceandata.sci.gsfc.nasa.gov/getfile"
PRODUCTO = "LANDVI"
VERSION = "V3_1"                        # serie 3.1 (NRT), la publicada para 2026
TAG = "NRT"
DESTINO = DATOS / "pace_landvi"

DESDE = "2026-09-29"                    # UTC, inclusive
HASTA = "2026-10-04"                    # UTC, inclusive
RES = "4km"                             # 4km | 2km | 0p1deg
BLOQUE = 4 * 1024 * 1024                # lectura en streaming, 4 MB
MIN_BYTES = 50_000_000                  # menos que esto es una página de login disfrazada
# El umbral depende de la resolución: el 0p1deg pesa ~34 MB y el 4km ~170 MB.
MIN_POR_RES = {"4km": 50_000_000, "2km": 100_000_000, "0p1deg": 5_000_000}


def nombre(fecha: date, res: str, tag: str = TAG) -> str:
    """Nombre canónico del gránulo L3M diario de LANDVI."""
    sufijo = f".{tag}" if tag else ""
    return f"PACE_OCI.{fecha:%Y%m%d}.L3m.DAY.{PRODUCTO}.{VERSION}.{res}{sufijo}.nc"


def candidatos(fecha: date, res: str) -> list[str]:
    """Nombres a probar, en orden: NRT (reciente) y después el procesado definitivo.

    Los días con más de ~1 mes suelen tener las dos versiones; los recientes sólo NRT.
    """
    return [nombre(fecha, res, TAG), nombre(fecha, res, "")]


def _sesion(cookies: Path | None) -> requests.Session:
    """Sesión autenticada contra URS: cookies de navegador o `.netrc`, en ese orden."""
    s = requests.Session()
    s.headers["User-Agent"] = "climate3d/1.0"
    s.trust_env = False                  # que no se cuele un proxy del sistema

    if cookies:
        # `utf-8-sig` tolera el BOM que agrega PowerShell 5.1 al exportar el JSON.
        jar = json.loads(Path(cookies).read_text(encoding="utf-8-sig"))
        for c in jar:
            s.cookies.set(c["name"], c["value"],
                          domain=c.get("domain", ""), path=c.get("path", "/"))
        return s

    try:
        host, login, clave = netrc.netrc().authenticators("urs.earthdata.nasa.gov")
    except (FileNotFoundError, netrc.NetrcParseError, TypeError):
        raise SystemExit(
            "Falta autenticación: exportá las cookies del navegador con --cookies, o "
            "creá ~/.netrc con la entrada de urs.earthdata.nasa.gov."
        )
    s.auth = (login, clave)              # básica preventiva, como `wget --auth-no-challenge`
    return s


def bajar(s: requests.Session, url: str, destino: Path, min_bytes: int = MIN_BYTES) -> None:
    """Descarga en streaming, reanudable por archivo temporal."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(destino.suffix + ".parcial")
    with s.get(url, stream=True, timeout=(30, 300), allow_redirects=True) as r:
        r.raise_for_status()
        tipo = r.headers.get("Content-Type", "")
        if "text/html" in tipo:
            raise SystemExit(
                f"El servidor devolvió HTML en vez de NetCDF ({url}). "
                "La sesión de Earthdata no es válida o expiró."
            )
        with tmp.open("wb") as fh:
            for bloque in r.iter_content(BLOQUE):
                fh.write(bloque)
    if tmp.stat().st_size < min_bytes:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"Archivo demasiado chico para ser un LANDVI: {destino.name}")
    tmp.replace(destino)


def fechas(desde: str, hasta: str):
    d0, d1 = date.fromisoformat(desde), date.fromisoformat(hasta)
    if d1 < d0:
        raise SystemExit("--hasta es anterior a --desde")
    return [d0 + timedelta(days=i) for i in range((d1 - d0).days + 1)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--desde", default=DESDE, help=f"primer día UTC (default {DESDE})")
    ap.add_argument("--hasta", default=HASTA, help=f"último día UTC inclusive (default {HASTA})")
    ap.add_argument("--res", default=RES, choices=("4km", "2km", "0p1deg"),
                    help=f"resolución del L3M (default {RES})")
    ap.add_argument("--destino", default=str(DESTINO), help="carpeta de salida")
    ap.add_argument("--cookies", default=None,
                    help="JSON con las cookies del navegador logueado en Earthdata")
    args = ap.parse_args()

    salida = Path(args.destino)
    s = _sesion(Path(args.cookies) if args.cookies else None)

    dias = fechas(args.desde, args.hasta)
    minimo = MIN_POR_RES[args.res]
    print(f"PACE OCI L3M {PRODUCTO} {VERSION} {args.res}: {len(dias)} día(s) -> {salida}")
    bajados = 0
    for d in dias:
        ya = [n for n in candidatos(d, args.res)
              if (salida / n).exists() and (salida / n).stat().st_size >= minimo]
        if ya:
            print(f"  = {ya[0]} (ya está)")
            continue
        for n in candidatos(d, args.res):
            destino = salida / n
            print(f"  + {n}")
            try:
                bajar(s, f"{BASE}/{n}", destino, minimo)
            except (requests.HTTPError, SystemExit) as exc:
                print(f"    ! {exc}")
                continue
            bajados += 1
            print(f"    {destino.stat().st_size / 1e6:.0f} MB")
            break
        else:
            print(f"  x sin datos para {d}")
    print(f"Listo: {bajados} gránulo(s) nuevo(s) en {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
