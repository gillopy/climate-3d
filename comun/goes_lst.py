"""Slot resolution for the GOES-R ABI L2 LST 2 km full disk product.

Standard library only on purpose: the app API (`app\\.venv`, no xarray) imports
this module, while the download scripts run with the project `.venv`.

The bucket is the public NOAA S3 one (`noaa-goes19`, no credentials):
`ABI-L2-LST2KMF/{YYYY}/{DDD}/{HH}/` with one granule per hour, published with a
delay. "Newest" is therefore never derived from the clock alone: the listing of
each hour is consulted while walking backwards.

  * `instante` — scan start (UTC hour) parsed from a granule name.
  * `prefijo` — hourly bucket prefix.
  * `listar_hora` — S3 keys of an hour (one HTTP request unless `listar` is injected).
  * `clave_de` — S3 key of the granule scanned in a given hour.
  * `ultimos_slots` — the `n` newest published hours, oldest first.
  * `ventana_ultimos` / `ventana_ultimas` — `[desde, hasta)` ranges for the CLI.
"""
from __future__ import annotations

import re
import urllib.request
from datetime import datetime, timedelta, timezone

PREFIJO = "ABI-L2-LST2KMF"
PASO = 60                    # minutes between slots: the LST product is hourly

_CLAVE = re.compile(r"<Key>([^<]+)</Key>")
# NOAA's LST granule name: the 14 digits are YYYYJJJHHMMSS plus one tenth of a second.
PATRON = re.compile(r"OR_ABI-L2-LST2KMF-M6_(?P<sat>G\d+)_s(?P<s>\d{14})_")


def _ahora_utc() -> datetime:
    """Current UTC time without `tzinfo`, like the rest of the scripts."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _piso_hora(t: datetime) -> datetime:
    """Drop `t` to the start of its UTC hour."""
    return t.replace(minute=0, second=0, microsecond=0)


def instante(nombre: str) -> datetime | None:
    """Scan hour (UTC) of an LST granule name, or None if it is not one.

    The real name starts with `s20263172200207`: 2026, day 317, 22:00:20.7 UTC.
    The slot is the hour, so the seconds and tenths are discarded.
    """
    match = PATRON.search(str(nombre))
    if not match:
        return None
    return datetime.strptime(match["s"][:13], "%Y%j%H%M%S").replace(
        minute=0, second=0, microsecond=0)


def prefijo(hora: datetime) -> str:
    """Hourly S3 prefix (`ABI-L2-LST2KMF/2026/317/22/`); minutes are ignored."""
    return f"{PREFIJO}/{hora.year}/{int(hora.strftime('%j')):03d}/{hora.hour:02d}/"


def listar_hora(sat: str, hora: datetime, timeout: int = 60,
                listar=None) -> list[str]:
    """S3 keys published under the LST prefix of one hour.

    `listar` is an optional callable `(sat, hora, timeout=...) -> list[str]` used
    by the tests to inject a listing and keep them offline.
    """
    traer = listar or _listar_s3
    return traer(sat, hora, timeout=timeout)


def _listar_s3(sat: str, hora: datetime, timeout: int = 60) -> list[str]:
    """Keys of the public NOAA bucket for one hour (a single HTTP request)."""
    url = (f"https://noaa-goes{sat[1:]}.s3.amazonaws.com/"
           f"?list-type=2&prefix={prefijo(hora)}")
    with urllib.request.urlopen(url, timeout=timeout) as respuesta:
        xml = respuesta.read().decode()
    return _CLAVE.findall(xml)


def _por_instante(sat: str, hora: datetime, listar=None) -> dict[datetime, str]:
    """`{scan hour: key}` of this hour, only for that satellite."""
    salida: dict[datetime, str] = {}
    for clave in listar_hora(sat, hora, listar=listar):
        match = PATRON.search(clave)
        if not match or match["sat"] != sat:
            continue
        momento = instante(clave)
        if momento is not None:
            salida[momento] = clave
    return salida


def clave_de(sat: str, t: datetime) -> str:
    """S3 key of the granule whose scan starts in the hour of `t`.

    Raises `LookupError` when that hour has no granule for `sat` (the product is
    hourly, so any minute inside the hour resolves to the same file).
    """
    hora = _piso_hora(t)
    clave = _por_instante(sat, hora).get(hora)
    if clave is None:
        raise LookupError(
            f"No {PREFIJO} granule for {sat} at {hora:%Y-%m-%d %H:%M} UTC")
    return clave


def ultimos_slots(sat: str, n: int, ahora: datetime | None = None,
                  intentos_horas: int = 48, listar=None) -> list[datetime]:
    """The `n` newest published hours, oldest first.

    Walks backwards from `ahora`, one hour at a time, consulting each hour's
    listing once. Returns whatever it found if `n` is not reached within
    `intentos_horas` (it never invents slots). `listar` injects the listing.
    """
    if n <= 0:
        return []
    t = _piso_hora(ahora or _ahora_utc())
    por_hora: dict[datetime, dict[datetime, str]] = {}
    encontrados: list[datetime] = []
    for _ in range(intentos_horas):
        if t not in por_hora:
            por_hora[t] = _por_instante(sat, t, listar=listar)
        if t in por_hora[t]:
            encontrados.append(t)
            if len(encontrados) == n:
                break
        t -= timedelta(hours=1)
    return sorted(encontrados)


def ventana_ultimos(n: int, sat: str, ahora: datetime | None = None,
                    listar=None) -> tuple[datetime, datetime]:
    """`[desde, hasta)` covering the `n` newest published hours."""
    slots = ultimos_slots(sat, n, ahora=ahora, listar=listar)
    if not slots:
        raise LookupError(
            f"No new {PREFIJO} granules for {sat} in NOAA S3. "
            "Check the connection or request an explicit date.")
    return slots[0], slots[-1] + timedelta(minutes=PASO)


def ventana_ultimas(horas: int, sat: str, ahora: datetime | None = None,
                    listar=None) -> tuple[datetime, datetime]:
    """`[desde, hasta)` of the last `horas`, ending at the newest published hour."""
    _, hasta = ventana_ultimos(1, sat, ahora=ahora, listar=listar)
    return hasta - timedelta(hours=horas), hasta
