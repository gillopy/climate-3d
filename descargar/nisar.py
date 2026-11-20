"""Descarga una escena NISAR (.h5) desde ASF a la carpeta de datos.

Los productos NISAR exigen Earthdata Login: el .h5 responde 303 a URS sin sesion
valida. Este script arma la sesion con usuario y clave (o cookies del navegador),
baja en streaming y reanuda por archivo ``.parcial``, porque un GCOV pesa ~1.9 GB.

Credenciales, en este orden:

1. ``--usuario`` / ``--clave``.
2. Variables ``EARTHDATA_USER`` / ``EARTHDATA_PASSWORD``.
3. El ``.env`` del repo.
4. ``~/.netrc`` con la entrada de ``urs.earthdata.nasa.gov``.
5. ``--cookies``: JSON exportado del navegador ya logueado.

Nunca imprime las credenciales. Si falta autenticacion, sale con un error que
dice exactamente que configurar.

    .venv\\Scripts\\python.exe descargar\\nisar.py --url URL --granulo ID
"""
from __future__ import annotations

import argparse
import json
import netrc
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from rutas import raiz_nisar  # noqa: E402

BLOQUE = 8 * 1024 * 1024
MIN_BYTES = 10_000_000  # un H5 real pesa cientos de MB; menos que esto es un error
EDL = "https://urs.earthdata.nasa.gov"
EDL_CLIENT_ID = "BO_n7nTIlMljdvU6kRRB3g"
ASF_AUTH = "https://cumulus.asf.alaska.edu/login"
DOMINIOS_AUTH = ("asf.alaska.edu", "earthdatacloud.nasa.gov", "earthdata.nasa.gov")


class SesionASF(requests.Session):
    """Mantiene el Bearer token en los redirects dentro de ASF/Earthdata."""

    def rebuild_auth(self, prepared_request, response):  # type: ignore[override]
        headers = prepared_request.headers
        if "Authorization" not in headers:
            return
        origen = urlparse(response.request.url).hostname or ""
        destino = urlparse(prepared_request.url).hostname or ""
        permitido = any(
            origen == dominio or origen.endswith("." + dominio) for dominio in DOMINIOS_AUTH
        ) and any(
            destino == dominio or destino.endswith("." + dominio) for dominio in DOMINIOS_AUTH
        )
        if not permitido:
            headers.pop("Authorization", None)


def _env_repo() -> dict[str, str]:
    """Lee el .env del repo sin imprimir valores."""
    env: dict[str, str] = {}
    archivo = RAIZ / ".env"
    try:
        for linea in archivo.read_text(encoding="utf-8-sig").splitlines():
            limpia = linea.strip()
            if not limpia or limpia.startswith("#") or "=" not in limpia:
                continue
            clave, valor = limpia.split("=", 1)
            env[clave.strip()] = valor.strip().strip('"').strip("'")
    except OSError:
        pass
    return env


def _credenciales(usuario: str | None, clave: str | None) -> tuple[str, str] | None:
    if usuario and clave:
        return usuario, clave
    env = os.environ
    env_repo = _env_repo()
    usuario = usuario or env.get("EARTHDATA_USER") or env_repo.get("EARTHDATA_USER")
    clave = clave or env.get("EARTHDATA_PASSWORD") or env_repo.get("EARTHDATA_PASSWORD")
    if usuario and clave:
        return usuario, clave
    try:
        host, login, password = netrc.netrc().authenticators("urs.earthdata.nasa.gov")
    except (FileNotFoundError, netrc.NetrcParseError, TypeError):
        return None
    if host and login and password:
        return login, password
    return None


def _sesion_cookies(ruta: Path) -> SesionASF:
    s = SesionASF()
    s.trust_env = False
    jar = json.loads(ruta.read_text(encoding="utf-8-sig"))
    for cookie in jar:
        s.cookies.set(
            cookie["name"],
            cookie["value"],
            domain=cookie.get("domain", ""),
            path=cookie.get("path", "/"),
        )
    token = s.cookies.get_dict().get("urs-access-token")
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
    return s


def _sesion(usuario: str | None, clave: str | None, cookies: Path | None) -> SesionASF:
    if cookies is not None:
        return _sesion_cookies(cookies)

    credenciales = _credenciales(usuario, clave)
    if credenciales is None:
        raise SystemExit(
            "Falta autenticacion de Earthdata. Carga EARTHDATA_USER y "
            "EARTHDATA_PASSWORD en .env (o en el entorno), o pasa --cookies con "
            "el JSON del navegador logueado."
        )
    usuario, clave = credenciales

    s = SesionASF()
    s.trust_env = False
    s.headers["User-Agent"] = "climate3d/1.0"
    s.auth = (usuario, clave)

    respuesta = s.post(f"{EDL}/api/users/find_or_create_token", timeout=(30, 60))
    if respuesta.status_code != 200:
        raise SystemExit(
            "Earthdata rechazo las credenciales "
            f"(HTTP {respuesta.status_code}). Revisa usuario y clave."
        )
    token = (respuesta.json() or {}).get("access_token")
    if not token:
        raise SystemExit("Earthdata no devolvio un access_token; revisa la cuenta.")

    # El `asf-urs` cookie autoriza los productos que lo piden; el token cubre el resto.
    # El redirect cae en ASF, que hoy sirve un certificado vencido en ~90% de los
    # nodos: se reintenta solo el handshake vencido y, si no hay suerte, se sigue
    # con el Bearer token en vez de abortar la descarga.
    for intento in range(12):
        try:
            s.get(
                f"{EDL}/oauth/authorize",
                params={
                    "splash": "false",
                    "client_id": EDL_CLIENT_ID,
                    "response_type": "code",
                    "redirect_uri": ASF_AUTH,
                },
                timeout=(30, 60),
            )
            break
        except requests.exceptions.SSLError as exc:
            if "certificate has expired" not in str(exc):
                raise
            time.sleep(min(0.3 * 2**intento, 2.0))
    s.auth = None
    s.headers["Authorization"] = f"Bearer {token}"
    return s


def _total_de(respuesta: requests.Response, ya: int) -> int | None:
    rango = respuesta.headers.get("Content-Range", "")
    if "/" in rango:
        try:
            return int(rango.rsplit("/", 1)[1])
        except ValueError:
            pass
    largo = respuesta.headers.get("Content-Length")
    if largo is not None:
        try:
            return ya + int(largo)
        except ValueError:
            pass
    return None


def bajar(s: requests.Session, url: str, destino: Path) -> None:
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SystemExit(
            f"No se pudo crear la carpeta de descarga {destino.parent}: {exc}. "
            "Revisa que la unidad/ruta exista (por ejemplo, D:\\nisar) o cambia "
            "CLIMATE3D_NISAR a otra carpeta."
        ) from exc
    if destino.is_file() and destino.stat().st_size >= MIN_BYTES:
        print(f"= {destino.name} ya esta ({destino.stat().st_size / 1e6:.0f} MB)")
        return

    parcial = destino.with_suffix(destino.suffix + ".parcial")
    ya = parcial.stat().st_size if parcial.is_file() else 0
    cabeceras = {"Range": f"bytes={ya}-"} if ya else {}

    with s.get(url, headers=cabeceras, stream=True, timeout=(30, 600), allow_redirects=True) as r:
        if r.status_code in (401, 403):
            raise SystemExit(
                f"ASF nego el acceso (HTTP {r.status_code}). La sesion de Earthdata "
                "no es valida o la cuenta no acepto la licencia de ASF."
            )
        if r.status_code not in (200, 206):
            raise SystemExit(f"ASF respondio HTTP {r.status_code} al pedir el .h5")
        tipo = r.headers.get("Content-Type", "")
        if "text/html" in tipo:
            raise SystemExit(
                "ASF devolvio HTML en vez del .h5: la sesion de Earthdata no es valida."
            )

        if r.status_code == 200 and ya:
            ya = 0  # el servidor ignoro el Range: se reescribe entero
        total = _total_de(r, ya)
        modo = "ab" if ya else "wb"
        print(f"+ {destino.name} ({'reanudo en ' + str(ya // 1_000_000) + ' MB' if ya else 'desde cero'})")
        with parcial.open(modo) as fh:
            ultimo = -1
            for bloque in r.iter_content(BLOQUE):
                if not bloque:
                    continue
                fh.write(bloque)
                ya += len(bloque)
                if total:
                    pct = int(ya * 100 / total)
                    if pct >= ultimo + 2:
                        ultimo = pct
                        print(f"  descarga: {ya / 1e6:.0f}/{total / 1e6:.0f} MB ({pct} %)")
                elif ya // (256 * 1024 * 1024) != ultimo:
                    ultimo = ya // (256 * 1024 * 1024)
                    print(f"  descarga: {ya / 1e6:.0f} MB")

    tamano = parcial.stat().st_size
    if tamano < MIN_BYTES:
        parcial.unlink(missing_ok=True)
        raise SystemExit(f"El archivo quedo demasiado chico ({tamano} bytes); se descarta.")
    if total and tamano < total:
        raise SystemExit(
            f"Descarga incompleta: {tamano / 1e6:.0f} de {total / 1e6:.0f} MB. "
            "El .parcial queda para reanudar."
        )
    parcial.replace(destino)
    print(f"listo: {destino} ({destino.stat().st_size / 1e6:.0f} MB)")


def _sello(
    ruta: Path, granulo: str, coleccion: str, destino: Path, ya_estaba: bool
) -> None:
    """Deja un JSON con lo que quedo en disco (el visor lo muestra como artefacto)."""
    datos = {
        "producto": "descarga",
        "granulo": granulo,
        "coleccion": coleccion,
        "ruta": str(destino),
        "bytes": destino.stat().st_size if destino.is_file() else 0,
        "ya_estaba": ya_estaba,
    }
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        parcial = ruta.with_suffix(ruta.suffix + ".part")
        parcial.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
        parcial.replace(ruta)
    except OSError as exc:
        print(f"aviso: no se pudo escribir el sello {ruta}: {exc}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", required=True, help="URL del .h5 en ASF")
    ap.add_argument("--granulo", required=True, help="id de la escena (nombre del archivo)")
    ap.add_argument(
        "--destino", default=str(raiz_nisar()), help="carpeta raiz de datos NISAR"
    )
    ap.add_argument("--coleccion", default="NISAR_L2_GCOV_V1", help="subcarpeta por coleccion")
    ap.add_argument("--usuario", default=None)
    ap.add_argument("--clave", default=None)
    ap.add_argument("--cookies", default=None, help="JSON de cookies del navegador logueado")
    ap.add_argument(
        "--sello",
        default=None,
        help="JSON de resumen de la descarga (lo usa el visor para mostrarla)",
    )
    args = ap.parse_args()

    granulo = args.granulo.strip()
    if not granulo or any(c in granulo for c in '\\/:*?"<>|'):
        raise SystemExit("--granulo tiene caracteres invalidos")
    coleccion = args.coleccion.strip() or "NISAR_L2_GCOV_V1"
    if any(c in coleccion for c in '\\/:*?"<>|'):
        raise SystemExit("--coleccion tiene caracteres invalidos")

    destino = Path(args.destino) / coleccion / f"{granulo}.h5"
    print(f"destino: {destino}")
    # Re-renderizar no puede exigir credenciales si el .h5 ya esta en disco.
    if destino.is_file() and destino.stat().st_size >= MIN_BYTES:
        print(f"= {destino.name} ya esta ({destino.stat().st_size / 1e6:.0f} MB)")
        if args.sello:
            _sello(Path(args.sello), granulo, coleccion, destino, True)
        return 0
    sesion = _sesion(args.usuario, args.clave, Path(args.cookies) if args.cookies else None)
    bajar(sesion, args.url, destino)
    if args.sello:
        _sello(Path(args.sello), granulo, coleccion, destino, False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
