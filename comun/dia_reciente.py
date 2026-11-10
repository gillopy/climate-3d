"""Último día que GIBS ya publica para una capa diaria.

Los compuestos diarios (true color de VIIRS/MODIS) y la SST de MUR son **un cuadro por
día**. Pedir el día de hoy casi siempre devuelve una imagen negra: el compuesto se arma
cuando cierra el día. Esta sonda camina hacia atrás hasta encontrar uno con dato, con el
mismo truco que `descargar/snapshot_paraguay.py`: mirar los píxeles, no el status.

La sonda pide una miniatura de 320 px, no el cuadro completo: son ~10 KB por intento en
vez de varios MB.
"""
from __future__ import annotations

import io
import time
from datetime import date, datetime, timedelta, timezone

import numpy as np
import requests
from PIL import Image

API = "https://wvs.earthdata.nasa.gov/api/v1/snapshot"
TIMEOUT = 25
INTENTOS = 10
FALLOS_DE_RED = 3
MIN_BYTES = 2_500


def _transitorio(exc: Exception) -> bool:
    """True si el error es del servicio y no la falta del día pedido.

    Ante un `4xx` el día no existe y hay que retroceder; ante un `503`, un
    timeout o un corte, retroceder diez días no sirve de nada: hay que decir que
    el servicio está caído.
    """
    if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
        return True
    if isinstance(exc, requests.HTTPError):
        respuesta = exc.response
        return respuesta is None or respuesta.status_code >= 500 or respuesta.status_code == 429
    return False


def _sirve(datos: bytes) -> bool:
    """True si el PNG trae imagen de verdad.

    GIBS responde `200` con un PNG de ~0,7 KB totalmente negro cuando el día pedido no
    tiene dato: el status no alcanza, hay que mirar los píxeles.
    """
    if len(datos) < MIN_BYTES:
        return False
    try:
        with Image.open(io.BytesIO(datos)) as imagen:
            pixeles = np.asarray(imagen.convert("RGB"), dtype=np.uint8)
    except Exception:
        return False
    return not bool((pixeles.max(axis=2) < 8).all())


def ultimo_dia(layer: str, caja, desde: datetime | None = None,
               intentos: int = INTENTOS, verbose: bool = True) -> date:
    """El día más nuevo con dato para `layer`, retrocediendo desde `desde` (hoy)."""
    o, s, e, n = (float(valor) for valor in caja)
    alto = max(64, round(320 * (n - s) / (e - o)))
    dia = (desde or datetime.now(timezone.utc).replace(tzinfo=None)).date()
    for _ in range(intentos):
        url = (f"{API}?REQUEST=GetSnapshot&TIME={dia:%Y-%m-%d}"
               f"&BBOX={s},{o},{n},{e}&CRS=EPSG:4326&LAYERS={layer}"
               f"&FORMAT=image/png&WIDTH=320&HEIGHT={alto}")
        datos = b""
        for intento in range(1, FALLOS_DE_RED + 1):
            try:
                r = requests.get(url, timeout=TIMEOUT,
                                 headers={"User-Agent": "climate3d/1.0"})
                r.raise_for_status()
                datos = r.content
                break
            except Exception as exc:                   # red o corte del servicio
                if not _transitorio(exc):
                    datos = b""                        # el día no existe
                    break
                if verbose:
                    print(f"    sonda {dia:%Y-%m-%d}: reintento {intento}/"
                          f"{FALLOS_DE_RED} ({type(exc).__name__})", flush=True)
                if intento == FALLOS_DE_RED:
                    raise SystemExit(
                        f"GIBS no responde ({type(exc).__name__}: {exc}).\n"
                        "No es un problema de fecha: el servicio de NASA está "
                        "caído o saturado. Probá de nuevo en unos minutos."
                    ) from exc
                time.sleep(2 * intento)
        if _sirve(datos):
            return dia
        if verbose:
            print(f"    {dia:%Y-%m-%d} sin dato, pruebo el anterior", flush=True)
        dia -= timedelta(days=1)
    raise SystemExit(
        f"No encontré ningún día con dato de {layer} en los últimos {intentos} días. "
        "GIBS puede estar caído: probá más tarde."
    )
