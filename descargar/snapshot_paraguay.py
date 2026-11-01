"""Descarga una **captura** (snapshot) GeoColor de NASA GIBS recortada a Paraguay.

No es una serie: es **una sola imagen**. El encuadre no se escribe a mano: sale del
GeoJSON de Paraguay (`datos/paraguay_gadm.json`) más un margen, así la cobertura
queda definida por los bordes del país.

Fuente (Worldview Snapshots API — un GET):

    https://wvs.earthdata.nasa.gov/api/v1/snapshot
      ?REQUEST=GetSnapshot&TIME=<ISO8601>Z&BBOX=<o>,<s>,<e>,<n>&CRS=EPSG:4326
      &LAYERS=GOES-East_ABI_GeoColor&FORMAT=image/png&WIDTH=<px>&HEIGHT=<px>

GeoColor es el "color IR día/noche" del ABI de GOES-19: color real de día, IR
multiespectral y luces de ciudad de noche. GIBS devuelve el gránulo más cercano al
instante pedido, así que no hay que adivinar el slot exacto.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe descargar\\snapshot_paraguay.py
    .venv\\Scripts\\python.exe descargar\\snapshot_paraguay.py --fecha 2026-11-01 --hora 15 --px 2000
    .venv\\Scripts\\python.exe descargar\\snapshot_paraguay.py --help   # no toca la red
"""
from __future__ import annotations

import argparse
import io
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import requests
from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from paraguay import (CAPAS, CAPA, INTENTOS, MARGEN, aviso_de_detalle,  # noqa: E402
                     caja_geojson, nombre_crudo, paso, px_para_mpp, techo,
                     url_snapshot)

GEOJSON = RAIZ / "datos" / "paraguay_gadm.json"

FECHA = "2026-11-01"                   # UTC
HORA = 15                              # UTC (15z = mediodía en Paraguay)
MINUTO = 0
PX = 3200                              # lado de la captura en píxeles


def valida(datos: bytes) -> bool:
    """True si el PNG trae imagen de verdad.

    GIBS responde `200` con un PNG de ~0,7 KB totalmente negro cuando el instante
    pedido no tiene gránulo. Esa es la trampa que deja capturas en negro.
    """
    if len(datos) < 2_500:
        return False
    try:
        with Image.open(io.BytesIO(datos)) as imagen:
            pixeles = np.asarray(imagen.convert("RGB"), dtype=np.uint8)
    except Exception:
        return False
    return not bool((pixeles.max(axis=2) < 8).all())


def _pedir(t: datetime, caja, px: int, capa: str, timeout: int = 90) -> bytes:
    r = requests.get(url_snapshot(t, caja, px, capa), timeout=timeout,
                     headers={"User-Agent": "climate3d/1.0"})
    r.raise_for_status()
    return r.content


def ultima_disponible(capa: str, caja, px: int, desde: datetime | None = None,
                      verbose: bool = True) -> datetime:
    """El gránulo más nuevo que GIBS sí tiene, retrocediendo desde ahora.

    La sonda pide una miniatura de `px` (por defecto 320) para no bajar 27 MB por
    cada intento. GeoColor publica con ~1 h de atraso; VIIRS, el día siguiente.
    """
    ahora = desde or datetime.now(timezone.utc).replace(tzinfo=None)
    t = techo(capa, ahora)
    intervalo = paso(capa)
    for intento in range(1, INTENTOS[capa] + 1):
        try:
            datos = _pedir(t, caja, px, capa, timeout=60)
        except Exception as exc:
            if verbose:
                print(f"    sonda {t:%Y-%m-%d %H:%M}: {exc}", flush=True)
            datos = b""
        if valida(datos):
            return t
        if verbose:
            print(f"    {t:%Y-%m-%d %H:%M} sin gránulo, pruebo {intervalo} antes",
                  flush=True)
        t -= intervalo
    etiqueta = "días" if intervalo.days else "slots"
    raise SystemExit(
        f"No encontré ningún gránulo de {capa} en los últimos "
        f"{INTENTOS[capa]} {etiqueta} desde {ahora:%Y-%m-%d %H:%M} UTC."
    )


def _formato(capa: str) -> str:
    """Patr?n de strftime que corresponde a la capa."""
    return "%Y-%m-%d" if CAPAS[capa][1] else "%Y-%m-%d %H:%M"


def descargar(t: datetime, caja, px: int, destino: Path, capa: str = CAPA,
              reintentos: int = 4) -> Path:
    """Baja la captura a `destino`; si ya está, la reutiliza (reanudable)."""
    if destino.exists() and destino.stat().st_size > 5_000:
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    url = url_snapshot(t, caja, px, capa)
    espera = 2.0
    for intento in range(1, reintentos + 1):
        try:
            r = requests.get(url, timeout=120, headers={"User-Agent": "climate3d/1.0"})
            r.raise_for_status()
            if len(r.content) < 5_000:
                raise ValueError(f"respuesta demasiado chica ({len(r.content)} B)")
            if not valida(r.content):
                ultima = ultima_disponible(capa, caja, 320)
                raise SystemExit(
                    f"No hay gránulo de {capa} para {t:%Y-%m-%d %H:%M} UTC "
                    f"(GIBS devolvió una imagen negra).\n"
                    f"La última disponible es "
                    f"{ultima.strftime(_formato(capa))}.\n"
                    f"Volvé a correr con --ultima, o con "
                    f"--fecha {ultima:%Y-%m-%d}"
                    + ("" if CAPAS[capa][1] else f" --hora {ultima:%H} --minuto {ultima:%M}")
                    + "."
                )
            tmp = destino.with_suffix(destino.suffix + ".parcial")
            tmp.write_bytes(r.content)
            tmp.replace(destino)
            return destino
        except Exception as exc:                       # red o corte del servicio
            if intento == reintentos:
                raise
            print(f"    reintento {intento}/{reintentos - 1} ({exc})", flush=True)
            time.sleep(espera)
            espera *= 2
    return destino


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Descarga una captura GeoColor (GOES-19) recortada a Paraguay.")
    ap.add_argument("--fecha", default=FECHA,
                    help=f"día UTC de la captura, YYYY-MM-DD (por defecto {FECHA})")
    ap.add_argument("--hora", type=int, default=HORA,
                    help=f"hora UTC 0-23 (por defecto {HORA})")
    ap.add_argument("--minuto", type=int, default=MINUTO,
                    help=f"minuto UTC 0-59 (por defecto {MINUTO})")
    ap.add_argument("--px", type=int, default=None,
                    help=f"lado de la captura en píxeles (por defecto {PX})")
    ap.add_argument("--mpp", type=float,
                    help="metros por píxel: calcula el lado según la caja "
                         "(125, 250, 500...). Tiene prioridad sobre --px")
    ap.add_argument("--margen", type=float, default=MARGEN,
                    help=f"margen alrededor del país, fracción del lado "
                         f"(por defecto {MARGEN})")
    ap.add_argument("--geojson", default=str(GEOJSON),
                    help="GeoJSON que define la cobertura (por defecto, Paraguay GADM)")
    ap.add_argument("--capa", default=CAPA, choices=tuple(CAPAS),
                    help=f"truecolor = VIIRS 250 m sólo de día; geocolor = GOES-19 "
                         f"día/noche a ~2 km (por defecto {CAPA})")
    ap.add_argument("--ultima", action="store_true",
                    help="ignora --fecha/--hora y busca el gránulo más nuevo publicado")
    ap.add_argument("--verificar", action="store_true",
                    help="sólo informa la última captura disponible (no descarga)")
    ap.add_argument("--out", help="carpeta de salida (por defecto, la del job)")
    args = ap.parse_args(argv)

    try:
        dia = date.fromisoformat(args.fecha)
    except ValueError:
        raise SystemExit(f"--fecha inválida: {args.fecha!r} (se espera YYYY-MM-DD).")
    if not 0 <= args.hora <= 23:
        raise SystemExit(f"--hora fuera de rango: {args.hora} (0-23).")
    if not 0 <= args.minuto <= 59:
        raise SystemExit(f"--minuto fuera de rango: {args.minuto} (0-59).")
    if args.px is not None and args.px < 256:
        raise SystemExit(f"--px demasiado chico: {args.px}.")
    if args.margen < 0:
        raise SystemExit(f"--margen debe ser >= 0 (recibí {args.margen}).")

    caja = caja_geojson(Path(args.geojson), args.margen)
    if args.mpp:
        args.px = px_para_mpp(caja, args.mpp)
        aviso = aviso_de_detalle(args.capa, args.mpp)
        if aviso:
            print(f"  aviso: {aviso}")
    elif not args.px:
        args.px = PX

    if args.ultima or args.verificar:
        print(f"Buscando la última captura de {args.capa} disponible...")
        t = ultima_disponible(args.capa, caja, min(args.px, 320))
        print(f"última disponible: {t.strftime(_formato(args.capa))} UTC")
        if args.verificar:
            return 0
    else:
        t = datetime(dia.year, dia.month, dia.day, args.hora, args.minuto)
    salida = Path(args.out) if args.out else RAIZ / "app" / "var" / "media" / "cache"
    destino = salida / nombre_crudo(args.capa, t, args.px)

    o, s, e, n = caja
    print(f"Snapshot {args.capa} {t:%Y-%m-%d %H:%M} UTC | {args.px}x{args.px} px")
    print(f"caja (desde el GeoJSON + margen {args.margen:g}): "
          f"{o:.2f},{s:.2f} .. {e:.2f},{n:.2f}")
    print(f"fuente: {url_snapshot(t, caja, args.px, args.capa)}")

    inicio = time.time()
    ruta = descargar(t, caja, args.px, destino, args.capa)
    print(f"listo: {ruta} ({ruta.stat().st_size / 1024:.0f} KB, "
          f"{time.time() - inicio:.1f}s)")
    print("Ahora componé con: "
          f".venv\\Scripts\\python.exe cuadros\\snapshot_paraguay.py "
          f"--crudo \"{ruta}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
