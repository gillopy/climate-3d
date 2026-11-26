"""Baja los gránulos diarios de **PACE OCI L3M LANDVI** (índices de vegetación terrestre).

LANDVI es la suite de índices de vegetación que PACE/OCI publica sobre tierra: seis
heredados de la era MODIS (`ndvi`, `evi`, `ndwi`, `ndii`, `cci`, `ndsi`) y cuatro
habilitados por el sensor hiperespectral (`pri`, `cire`, `car`, `mari`). Es el insumo con
el que NASA Earth Observatory arma los mapas de "red leaves": el índice `mari` mide
antocianina (lo rojo) y `cire`/`cci` la clorofila (lo verde).

Fuente (OB.DAAC, no GIBS: GIBS no publica PACE sobre tierra):

    https://oceandata.sci.gsfc.nasa.gov/getfile/PACE_OCI.<YYYYMMDD>.L3m.DAY.LANDVI.V3_1.<res>.NRT.nc

El archivo pesa ~170 MB por día en 4 km (~37 MB en 0p1deg) y **exige Earthdata Login**:
`getfile` responde 302 a `urs.earthdata.nasa.gov` y sin sesión válida no entrega el NetCDF.

Hay dos formas de autenticarse, y la primera no pide navegador ni cookies:

  1. **Usuario y clave de Earthdata** (`EARTHDATA_USER`/`EARTHDATA_PASSWORD` en el
     entorno o en el `.env` del repo, o `~/.netrc`). `getfile` manda a URS, URS valida
     con Basic y vuelve con la cookie de la app. `requests` borra el header
     Authorization cuando el redirect cambia de host, que es justo lo que rompía este
     camino: `SesionEarthdata` lo vuelve a poner para los hosts de la NASA.
  2. `--cookies <archivo.json>`: lista de cookies exportada de un navegador ya logueado
     (formato de Playwright: `[{name, value, domain, path, ...}]`). Si se omite, usa
     automáticamente el archivo que guarda el botón **Conectar Earthdata** de la consola
     (`earthdata_cookies.json`, junto a `config.json`). Queda como respaldo.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe descargar\\pace_landvi.py --desde 2026-09-29 --hasta 2026-10-04
    .venv\\Scripts\\python.exe descargar\\pace_landvi.py --help   # no toca la red
"""
from __future__ import annotations

import argparse
import json
import netrc
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from urllib3.util.retry import Retry

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from rutas import DATOS, ruta_cookies_earthdata  # noqa: E402

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
# Días del compuesto móvil del renderer: con uno solo no hay cuadro posible.
VENTANA_FOLLAJE = 7


def nombre(fecha: date, res: str, tag: str = TAG) -> str:
    """Nombre canónico del gránulo L3M diario de LANDVI."""
    sufijo = f".{tag}" if tag else ""
    return f"PACE_OCI.{fecha:%Y%m%d}.L3m.DAY.{PRODUCTO}.{VERSION}.{res}{sufijo}.nc"


def candidatos(fecha: date, res: str) -> list[str]:
    """Nombres a probar, en orden: NRT (reciente) y después el procesado definitivo.

    Los días con más de ~1 mes suelen tener las dos versiones; los recientes sólo NRT.
    """
    return [nombre(fecha, res, TAG), nombre(fecha, res, "")]


def _credenciales() -> tuple[str, str] | None:
    """Usuario y clave de Earthdata: entorno, `.env` del repo y después `~/.netrc`."""
    usuario = os.environ.get("EARTHDATA_USER")
    clave = os.environ.get("EARTHDATA_PASSWORD")
    if usuario and clave:
        return usuario, clave
    env_repo = _leer_env(RAIZ / ".env")
    usuario = usuario or env_repo.get("EARTHDATA_USER")
    clave = clave or env_repo.get("EARTHDATA_PASSWORD")
    if usuario and clave:
        return usuario, clave
    try:
        _, login, password = netrc.netrc().authenticators("urs.earthdata.nasa.gov")
    except (FileNotFoundError, netrc.NetrcParseError, TypeError):
        return None
    if login and password:
        return login, password
    return None


def _leer_env(ruta: Path) -> dict[str, str]:
    """Pares clave=valor de un `.env`, sin exportarlos al proceso."""
    if not ruta.is_file():
        return {}
    datos: dict[str, str] = {}
    for linea in ruta.read_text(encoding="utf-8-sig").splitlines():
        if "=" in linea and not linea.lstrip().startswith("#"):
            clave, _, valor = linea.partition("=")
            valor = valor.strip().strip('"')
            if valor:
                datos[clave.strip()] = valor
    return datos


#: Hosts de la NASA que participan del login: el redirect OB.DAAC <-> URS.
_HOSTS_NASA = ("urs.earthdata.nasa.gov", "oceandata.sci.gsfc.nasa.gov")


class SesionEarthdata(requests.Session):
    """Sesión que conserva el Basic auth al saltar de OB.DAAC a URS.

    `requests` borra el header Authorization cuando un redirect cambia de host. El
    login de Earthdata depende justamente de ese salto: `getfile` manda a URS, URS
    valida con Basic y vuelve con la cookie de la app. Sin reenviarlo, el pedido
    termina en la página HTML de login y el `.nc` nunca baja.
    """

    def __init__(self, usuario: str, clave: str) -> None:
        super().__init__()
        self.auth = (usuario, clave)
        self._basico = HTTPBasicAuth(usuario, clave)

    def rebuild_auth(self, prepared_request, response):  # noqa: D401 - hook de requests
        super().rebuild_auth(prepared_request, response)
        host = (urlparse(prepared_request.url).hostname or "").lower()
        if host in _HOSTS_NASA and "Authorization" not in prepared_request.headers:
            self._basico(prepared_request)


def _sesion(cookies: Path | None) -> requests.Session:
    """Sesión autenticada contra OB.DAAC.

    Primero usuario y clave (no necesita navegador ni cookies); si no hay, las
    cookies del OAuth como respaldo.
    """
    s = requests.Session()
    credenciales = _credenciales()
    if credenciales:
        s = SesionEarthdata(*credenciales)
    s.headers["User-Agent"] = "climate3d/1.0"
    s.trust_env = False                  # que no se cuele un proxy del sistema

    # Reintentos para errores de conexión transitorios (timeout, DNS, reset)
    retry = Retry(
        total=3,
        connect=3,
        read=2,
        backoff_factor=2.0,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)

    if credenciales:
        print("Autenticando con EARTHDATA_USER/EARTHDATA_PASSWORD")
        return s

    if cookies:
        # `utf-8-sig` tolera el BOM que agrega PowerShell 5.1 al exportar el JSON.
        print(f"Autenticando con cookies de Earthdata: {cookies}")
        jar = json.loads(Path(cookies).read_text(encoding="utf-8-sig"))
        for c in jar:
            s.cookies.set(c["name"], c["value"],
                          domain=c.get("domain", ""), path=c.get("path", "/"))
        return s

    raise SystemExit(
        "Falta autenticación: cargá EARTHDATA_USER y EARTHDATA_PASSWORD en el .env "
        "(o en ~/.netrc). Si preferís no poner la clave, seguí usando 'Conectar "
        "Earthdata' y el archivo de cookies."
    )


def bajar(s: requests.Session, url: str, destino: Path, min_bytes: int = MIN_BYTES) -> None:
    """Descarga en streaming, reanudable por archivo temporal."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(destino.suffix + ".parcial")
    # Timeout de conexión más generoso (60s) y lectura 300s; los reintentos
    # los maneja el HTTPAdapter montado en la sesión.
    with s.get(url, stream=True, timeout=(60, 300), allow_redirects=True) as r:
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


def _presente(salida: Path, dia: date, res: str, minimo: int) -> bool:
    """True si el gránulo de ese día está completo en disco (NRT o definitivo)."""
    return any(
        (salida / n).is_file() and (salida / n).stat().st_size >= minimo
        for n in candidatos(dia, res)
    )


def ventana_completa(
    salida: Path, dias: list[date], res: str, minimo: int, ventana: int = VENTANA_FOLLAJE
) -> bool:
    """¿Queda al menos una ventana de `ventana` días consecutivos con dato?

    OB.DAAC no publica todos los días (el último suele dar 404). El renderer ya
    descarta las fechas con huecos, así que la descarga sólo debe fallar cuando
    no queda ningún compuesto armable. Se revisan las ventanas terminando en
    cada día pedido, de más reciente a más viejo.
    """
    for fin in reversed(dias):
        if all(
            _presente(salida, fin - timedelta(days=k), res, minimo)
            for k in range(ventana)
        ):
            return True
    return False


def _cookies_para_usar(explicito: str | None) -> Path | None:
    """Archivo de cookies: el que se pasó o el que guardó el login interactivo."""
    if explicito:
        return Path(explicito)
    auto = ruta_cookies_earthdata()
    return auto if auto.is_file() else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--desde", default=DESDE, help=f"primer día UTC (default {DESDE})")
    ap.add_argument("--hasta", default=HASTA, help=f"último día UTC inclusive (default {HASTA})")
    ap.add_argument("--res", default=RES, choices=("4km", "2km", "0p1deg"),
                    help=f"resolución del L3M (default {RES})")
    ap.add_argument("--destino", default=str(DESTINO), help="carpeta de salida")
    ap.add_argument("--cookies", default=None,
                    help="JSON con las cookies del navegador logueado en Earthdata. "
                         "Si no se pasa, se usa ~/.config/climate3d/earthdata_cookies.json si existe.")
    args = ap.parse_args()

    salida = Path(args.destino)
    dias = fechas(args.desde, args.hasta)
    minimo = MIN_POR_RES[args.res]
    print(f"PACE OCI L3M {PRODUCTO} {VERSION} {args.res}: {len(dias)} día(s) -> {salida}")
    bajados = 0
    faltantes = 0
    # La sesión se arma recién cuando hay algo para bajar: si todos los gránulos
    # están en disco, una cookie vencida no puede bloquear el render.
    sesion: requests.Session | None = None
    for d in dias:
        ya = [n for n in candidatos(d, args.res)
              if (salida / n).exists() and (salida / n).stat().st_size >= minimo]
        if ya:
            print(f"  = {ya[0]} (ya está)")
            continue
        if sesion is None:
            sesion = _sesion(_cookies_para_usar(args.cookies))
        for n in candidatos(d, args.res):
            destino = salida / n
            print(f"  + {n}")
            try:
                bajar(sesion, f"{BASE}/{n}", destino, minimo)
            except (requests.HTTPError, SystemExit) as exc:
                print(f"    ! {exc}")
                continue
            bajados += 1
            print(f"    {destino.stat().st_size / 1e6:.0f} MB")
            break
        else:
            print(f"  x sin datos para {d}")
            faltantes += 1
    print(f"Listo: {bajados} gránulo(s) nuevo(s) en {salida}")
    if faltantes:
        print(f"Aviso: {faltantes} día(s) sin publicar; se descarta esa fecha al renderizar.")
    if not ventana_completa(salida, dias, args.res, minimo):
        print(f"Aviso: no hay {VENTANA_FOLLAJE} días consecutivos con dato en este rango.")
    # Si quedó al menos un gránulo, la descarga cumplió su parte: el renderer es
    # quien decide qué ventanas de VENTANA_FOLLAJE días se pueden dibujar. Sólo
    # fallamos cuando no se obtuvo nada (señal de sesión vencida o fechas mal
    # pedidas), para no dejar pasar un error de autenticación como éxito.
    if not any(_presente(salida, d, args.res, minimo) for d in dias):
        print(
            "Error: no se obtuvo ningún gránulo de LANDVI; revisá la autenticación "
            "y las fechas pedidas."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
