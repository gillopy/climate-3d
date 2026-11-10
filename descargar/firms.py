"""Baja los focos de calor de NASA FIRMS para la caja de la captura de Paraguay.

No genera imagen: deja un CSV **normalizado** en la carpeta de crudos, y el
compositor (`cuadros/snapshot_paraguay.py`) lo dibuja encima. Un GET por fuente, con
reintentos y backoff; la API es la misma que usa la web de FIRMS.

La caja es la del GeoJSON + margen, la misma de la captura: no se escribe a mano,
así los focos caen exactamente donde están.

La ventana (`--ventana`) decide qué focos se guardan:
  * `dia` — el día UTC completo de la captura (default: los True Color son compuestos
    diarios y la imagen ES ese día);
  * `3h` / `6h` / `12h` — horas a cada lado del slot, para GeoColor.

Un fallo de red o una fuente vacía **no** es un error del job: se avisa y el CSV queda
con lo que haya (posiblemente vacío) para que la captura salga sin overlay.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe descargar\\firms.py --fecha 2026-11-08 --hora 15
    .venv\\Scripts\\python.exe descargar\\firms.py --ultima --entrada app\\var\\media\\cache
    .venv\\Scripts\\python.exe descargar\\firms.py --help   # no toca la red
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from firms import (FUENTE, FUENTES, MAX_DIAS, VENTANA, VENTANAS,  # noqa: E402
                   clave_mapa, escribir, etiqueta, filtrar, leer_texto,
                   nombre_csv, url_focos, ventana)
from paraguay import GEOJSON, MARGEN, caja_geojson, crudo_mas_nuevo, ts_de_crudo  # noqa: E402

TIMEOUT = 60
REINTENTOS = 3
FECHA = datetime.now(timezone.utc).date()


def _aviso(texto: str) -> None:
    print(f"  aviso: {texto}", flush=True)


def _sin_clave(texto: str, clave: str) -> str:
    """Borra la MAP_KEY de un mensaje antes de imprimirlo.

    `requests` mete la URL entera en sus excepciones y la clave viaja en la URL: sin
    esto, un corte de red dejaría la credencial escrita en el log del job.
    """
    return texto.replace(clave, "***") if clave else texto


def _pedir(url: str, reintentos: int = REINTENTOS, clave: str = "") -> str:
    """GET con backoff. Devuelve el texto o lanza la última excepción."""
    espera = 2.0
    for intento in range(1, reintentos + 1):
        try:
            r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "climate3d/1.0"})
            if r.status_code == 400 and "Invalid MAP_KEY" in r.text:
                raise SystemExit(
                    "FIRMS rechazó el MAP_KEY (400 Invalid MAP_KEY).\n"
                    f"Revisá {RAIZ / 'datos' / 'firms_map_key.txt'} o la variable "
                    "FIRMS_MAP_KEY."
                )
            r.raise_for_status()
            return r.text
        except SystemExit:
            raise
        except Exception as exc:                       # red, rate-limit o corte
            if intento == reintentos:
                raise
            print(f"    reintento {intento}/{reintentos - 1} "
                  f"({type(exc).__name__}: {_sin_clave(str(exc), clave)})", flush=True)
            time.sleep(espera)
            espera *= 2
    raise AssertionError("bucle de reintentos sin retorno")


def _instante(args, entrada: Path) -> datetime:
    """El momento de la captura: el pedido a mano o el que resolvió GIBS."""
    if args.ultima:
        crudo = crudo_mas_nuevo(entrada, args.capa)
        if crudo is None:
            raise SystemExit(
                f"No hay crudos de {args.capa} en {entrada}. Sin la captura no se "
                "sabe qué día pedirle a FIRMS.\n"
                "Corré primero descargar\\snapshot_paraguay.py o quitá --ultima."
            )
        resuelto = ts_de_crudo(crudo.name)
        if resuelto is None:
            raise SystemExit(f"No pude leer el instante de {crudo.name}.")
        return resuelto
    return datetime(args.fecha.year, args.fecha.month, args.fecha.day,
                    args.hora, args.minuto)


def _dias(desde: datetime, hasta: datetime) -> int:
    """Días de calendario que hay que pedirle a FIRMS para cubrir la ventana."""
    ultimo = hasta - timedelta(seconds=1)
    return max(1, min(MAX_DIAS, (ultimo.date() - desde.date()).days + 1))


def descargar(caja, instante: datetime, destino: Path, fuente: str = FUENTE,
              modo: str = VENTANA, clave: str | None = None,
              reintentos: int = REINTENTOS) -> tuple[Path, list]:
    """Baja los focos de la ventana y los deja en `destino`. Devuelve `(ruta, focos)`."""
    desde, hasta = ventana(instante, modo)
    dias = _dias(desde, hasta)
    clave = clave or clave_mapa()
    focos = []
    for nombre in FUENTES.get(fuente, FUENTES[FUENTE]):
        url = url_focos(clave, nombre, caja, desde.date(), dias)
        try:
            texto = _pedir(url, reintentos, clave)
        except SystemExit:
            raise
        except Exception as exc:
            _aviso(f"{nombre}: {type(exc).__name__}: {_sin_clave(str(exc), clave)}")
            continue
        encontrados = leer_texto(texto)
        en_ventana = filtrar(encontrados, desde, hasta)
        if encontrados and not en_ventana:
            _aviso(f"{nombre}: {len(encontrados)} focos en el día, 0 en la ventana "
                   f"{etiqueta(instante, modo)}")
        print(f"  {nombre}: {len(en_ventana)} focos", flush=True)
        focos.extend(en_ventana)
    focos.sort(key=lambda foco: foco.cuando)
    return escribir(destino, focos), focos


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Baja los focos de calor de FIRMS para la caja de Paraguay.")
    ap.add_argument("--fecha", default=FECHA.isoformat(),
                    help=f"día UTC de la captura (por defecto {FECHA})")
    ap.add_argument("--hora", type=int, default=15,
                    help="hora UTC 0-23 de la captura (por defecto 15)")
    ap.add_argument("--minuto", type=int, default=0,
                    help="minuto UTC 0-59 de la captura (por defecto 0)")
    ap.add_argument("--ultima", action="store_true",
                    help="toma el instante del crudo más nuevo de --entrada")
    ap.add_argument("--capa", default="truecolor",
                    help="capa del crudo, para encontrar el instante con --ultima")
    ap.add_argument("--fuente", default=FUENTE, choices=tuple(FUENTES),
                    help=f"{FUENTE} = NOAA-20 + NOAA-21 (375 m), el default")
    ap.add_argument("--ventana", default=VENTANA, choices=VENTANAS,
                    help=f"{VENTANA} = día UTC completo (compuesto diario)")
    ap.add_argument("--margen", type=float, default=MARGEN,
                    help=f"margen alrededor del país, fracción del lado "
                         f"(por defecto {MARGEN})")
    ap.add_argument("--geojson", default=str(GEOJSON),
                    help="GeoJSON que define la cobertura")
    ap.add_argument("--entrada", help="carpeta de crudos (para --ultima)")
    ap.add_argument("--out", help="carpeta donde dejar el CSV (por defecto --entrada)")
    ap.add_argument("--clave", help="MAP_KEY (por defecto, entorno o datos/firms_map_key.txt)")
    ap.add_argument("--reintentos", type=int, default=REINTENTOS,
                    help=f"intentos por fuente (por defecto {REINTENTOS})")
    args = ap.parse_args(argv)

    try:
        args.fecha = date.fromisoformat(args.fecha)
    except ValueError:
        raise SystemExit(f"--fecha inválida: {args.fecha!r} (se espera YYYY-MM-DD).")
    if not 0 <= args.hora <= 23:
        raise SystemExit(f"--hora fuera de rango: {args.hora} (0-23).")
    if not 0 <= args.minuto <= 59:
        raise SystemExit(f"--minuto fuera de rango: {args.minuto} (0-59).")
    if args.margen < 0:
        raise SystemExit(f"--margen debe ser >= 0 (recibí {args.margen}).")
    if args.ventana not in VENTANAS:
        raise SystemExit(f"--ventana desconocida: {args.ventana!r}.")

    caja = caja_geojson(Path(args.geojson), args.margen)
    entrada = Path(args.entrada) if args.entrada else Path(args.out or ".")
    salida = Path(args.out) if args.out else entrada
    instante = _instante(args, entrada)
    desde, hasta = ventana(instante, args.ventana)

    print(f"FIRMS {args.fuente} | captura {instante:%Y-%m-%d %H:%M} UTC | "
          f"ventana {etiqueta(instante, args.ventana)}")
    print(f"caja: {caja}")
    ruta, focos = descargar(
        caja, instante, salida / nombre_csv(instante, args.ventana),
        fuente=args.fuente, modo=args.ventana, clave=args.clave,
        reintentos=args.reintentos)
    if not focos:
        _aviso("sin focos en la ventana: la captura sale sin overlay")
    print(f"listo: {ruta} ({len(focos)} focos, {ruta.stat().st_size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
