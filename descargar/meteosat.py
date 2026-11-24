"""Descarga cuadros de Meteosat-12 (MTG-I1) desde EUMETView.

El FCI del MTG publica cada 10 minutos. EUMETSAT lo sirve ya **pintado**
(GeoColour, True Colour, IR) por un WMS abierto: no hay NetCDF ni
reproyeccion de la proyeccion geoestacionaria. Cada cuadro es un `GetMap` en
``CRS:84`` (lon/lat) y se guarda como ``crudo_NNN.png``; el render vive en
``cuadros/cuadros_meteosat.py``.

``--encuadre`` elige la caja: ``globo`` (disco entero, la de siempre) o
``paraguay`` (recorte de 1000 km sobre el pais, cuadrado en kilometros).

Fuente: EUMETView (EUMETSAT), datos Core CC-BY 4.0. Atribucion obligatoria:
"[Contains modified] EUMETSAT Meteosat data".

Uso (desde la raiz del proyecto):

    .venv\\Scripts\\python.exe descargar\\meteosat.py --n 24 --px 1600
    .venv\\Scripts\\python.exe descargar\\meteosat.py --desde 2026-11-23T12:00 --n 1 --capa truecolour
    .venv\\Scripts\\python.exe descargar\\meteosat.py --desde 2026-11-23T15:00 --n 1 --capa truecolour --encuadre paraguay
    .venv\\Scripts\\python.exe descargar\\meteosat.py --help   # no toca la red
"""
from __future__ import annotations

import argparse
import io
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from meteosat import (  # noqa: E402
    BBOX, CAPAS, PASO, caja, normaliza_encuadre, piso_slot, ultimos_slots,
    url_cuadro,
)
from rutas import SALIDAS  # noqa: E402

PX = 1600
N = 24
DESDE = ""
REINTENTOS = 3


def valida(datos: bytes, capa: str) -> bool:
    """True si la respuesta trae imagen con dato.

    EUMETView contesta 200 con un XML de excepcion cuando el slot no existe; y
    GeoColour de noche sigue mostrando luces de ciudad, asi que una imagen negra
    significa "sin dato", no "sin sol". True Colour si puede ser negra de noche:
    ahi solo se exige que sea un PNG real.
    """
    if len(datos) < 5_000:
        return False
    try:
        with Image.open(io.BytesIO(datos)) as imagen:
            pixeles = np.asarray(imagen.convert("RGB"), dtype=np.uint8)
    except Exception:
        return False
    if capa == "truecolour":
        return True
    return int(pixeles.max()) > 8


def _bajar(t: datetime, capa: str, px: int, bbox=BBOX, alto: int | None = None) -> bytes:
    import urllib.request

    pedido = urllib.request.Request(
        url_cuadro(t, capa, px, alto=alto, bbox=bbox),
        headers={"User-Agent": "climate3d/1.0"},
    )
    with urllib.request.urlopen(pedido, timeout=60) as respuesta:
        datos = respuesta.read()
    if not valida(datos, capa):
        raise ValueError(f"cuadro sin dato ({len(datos)} B)")
    return datos


def descargar_cuadro(t: datetime, capa: str, px: int, destino: Path,
                     reintentos: int = REINTENTOS, bbox=BBOX,
                     alto: int | None = None) -> Path:
    """Baja el cuadro a `destino`; lo reutiliza si ya esta (reanudable)."""
    if destino.exists() and destino.stat().st_size > 5_000:
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    espera = 2.0
    for intento in range(1, reintentos + 1):
        try:
            datos = _bajar(t, capa, px, bbox=bbox, alto=alto)
            tmp = destino.with_suffix(destino.suffix + ".parcial")
            tmp.write_bytes(datos)
            tmp.replace(destino)
            return destino
        except Exception:
            if intento == reintentos:
                raise
            print(f"    reintento {intento}/{reintentos - 1}", flush=True)
            time.sleep(espera)
            espera *= 2
    return destino


def _etiqueta(vista: str, t0: datetime, n: int, px: int) -> str:
    return f"frames_meteosat_{vista}_{t0:%Y-%m-%dT%H%M}_{n}f_{px}px"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Descarga cuadros de Meteosat-12 (MTG-I1) desde EUMETView.")
    ap.add_argument("--desde", default=DESDE,
                    help="primer cuadro UTC (vacio = el ultimo publicado)")
    ap.add_argument("--n", type=int, default=N, help=f"cantidad de cuadros (por defecto {N})")
    ap.add_argument("--paso", type=int, default=PASO,
                    help=f"minutos entre cuadros (por defecto {PASO})")
    ap.add_argument("--px", type=int, default=PX,
                    help=f"ancho del PNG de origen en pixeles (por defecto {PX})")
    ap.add_argument("--capa", default="geocolour", choices=tuple(CAPAS),
                    help="producto pintado: geocolour (dia/noche), truecolour, ir")
    ap.add_argument("--encuadre", choices=("globo", "paraguay"), default=None,
                    help="globo (disco completo, por defecto) o paraguay (recorte "
                         "de 1000 km sobre el pais)")
    ap.add_argument("--globo", action="store_true",
                    help="alias viejo de --encuadre globo")
    ap.add_argument("--out", help="carpeta de salida (por defecto, comun.rutas.SALIDAS)")
    ap.add_argument("--respaldo", type=int, default=3,
                    help="con un solo cuadro, cuantos slots retroceder si el WMS no lo "
                         "tiene (por defecto 3; 0 = no retroceder)")
    ap.add_argument("--hilos", type=int, default=4,
                    help="descargas simultaneas (por defecto 4)")
    args = ap.parse_args(argv)

    if args.n < 1:
        raise SystemExit("--n tiene que ser >= 1.")
    if args.capa not in CAPAS:
        raise SystemExit(f"--capa invalida: {args.capa}")

    if args.desde:
        try:
            t0 = piso_slot(datetime.fromisoformat(args.desde), args.paso)
        except ValueError as exc:
            raise SystemExit(f"--desde invalido ({exc}). Usa AAAA-MM-DDTHH:MM.") from exc
    else:
        t0 = ultimos_slots(1, args.capa)[0]
        if args.n > 1:
            t0 = t0 - timedelta(minutes=args.paso * (args.n - 1))

    salida = Path(args.out) if args.out else SALIDAS
    # El flag `--globo` de los comandos viejos sigue valiendo como `globo`.
    encuadre = normaliza_encuadre(args.encuadre, args.globo)
    bbox = caja(encuadre)
    # El recorte de Paraguay es cuadrado en kilómetros: se pide cuadrado para no
    # deformar el póster. El disco mantiene la proporción de su caja lon/lat.
    alto = args.px if encuadre == "paraguay" else None
    vista = encuadre
    etiqueta = _etiqueta(vista, t0, args.n, args.px)
    frames_dir = salida / etiqueta
    frames_dir.mkdir(parents=True, exist_ok=True)

    tiempos = [t0 + timedelta(minutes=args.paso * i) for i in range(args.n)]
    print(f"Meteosat-12 {args.capa} | {args.n} cuadro(s) desde "
          f"{t0:%Y-%m-%d %H:%M} UTC | paso {args.paso} min | origen {args.px} px")
    print(f"caja {bbox} | frames en {frames_dir}")

    # Un solo cuadro: si el slot pedido no esta, se prueba el anterior.
    if args.n == 1:
        for salto in range(0, args.respaldo + 1):
            t = t0 - timedelta(minutes=args.paso * salto)
            etiqueta = _etiqueta(vista, t, 1, args.px)
            frames_dir = salida / etiqueta
            frames_dir.mkdir(parents=True, exist_ok=True)
            try:
                descargar_cuadro(t, args.capa, args.px, frames_dir / "crudo_001.png",
                                 bbox=bbox, alto=alto)
            except Exception as exc:
                print(f"  aviso: {t:%Y-%m-%d %H:%M} UTC sin dato ({exc})", flush=True)
                continue
            if salto:
                print(f"  aviso: uso {t:%Y-%m-%d %H:%M} UTC en vez de "
                      f"{t0:%Y-%m-%d %H:%M}", flush=True)
            t0 = t
            break
        else:
            raise SystemExit(
                f"Ningun slot de {args.capa} respondio en los ultimos "
                f"{args.respaldo * args.paso} min. Revisa la conexion o pedi una "
                "fecha explicita.")
        print(f"1 cuadro listo en {frames_dir}")
        print(f"Ahora renderiza con: .venv\\Scripts\\python.exe cuadros\\cuadros_meteosat.py "
              f"--desde {t0:%Y-%m-%dT%H:%M} --n 1 --px {args.px} --capa {args.capa} "
              f"--encuadre {encuadre}")
        return 0

    inicio = time.time()
    hechos = 0
    errores: list[tuple[int, datetime]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.hilos)) as pool:
        futuros = {
            pool.submit(descargar_cuadro, t, args.capa, args.px,
                        frames_dir / f"crudo_{i:03d}.png", bbox=bbox, alto=alto): (i, t)
            for i, t in enumerate(tiempos, 1)
        }
        for fut in as_completed(futuros):
            i, t = futuros[fut]
            try:
                fut.result()
            except Exception as exc:
                errores.append((i, t))
                print(f"[{i}/{args.n}] {t:%Y-%m-%d %H:%M} UTC  ERROR: {exc}", flush=True)
                continue
            hechos += 1
            print(f"  {hechos}/{args.n} listos (errores {len(errores)}) "
                  f"{time.time() - inicio:.0f}s", flush=True)

    if errores:
        print(f"Segunda pasada: {len(errores)} cuadro(s) sin dato", flush=True)
        time.sleep(2)
        for i, t in errores:
            try:
                descargar_cuadro(t, args.capa, args.px,
                                 frames_dir / f"crudo_{i:03d}.png",
                                 bbox=bbox, alto=alto)
                hechos += 1
            except Exception as exc:
                print(f"  [{i}] sigue sin dato: {exc}", flush=True)

    faltan = [i for i in range(1, args.n + 1)
              if not (frames_dir / f"crudo_{i:03d}.png").exists()]
    print(f"{hechos} cuadro(s) listos en {time.time() - inicio:.0f}s")
    if faltan:
        raise SystemExit(
            f"Faltan {len(faltan)} cuadro(s) que EUMETView no tiene publicados: "
            f"{faltan[:12]}. Volve a correr: los que ya estan se reutilizan.")
    print(f"Ahora renderiza con: .venv\\Scripts\\python.exe cuadros\\cuadros_meteosat.py "
          f"--desde {t0:%Y-%m-%dT%H:%M} --n {args.n} --px {args.px} --capa {args.capa} "
          f"--encuadre {encuadre}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
