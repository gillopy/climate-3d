"""Compone la captura de Paraguay: la imagen de GIBS + el contorno del país.

Sin globo, sin rótulos, sin barra de color: la captura es la imagen. El contorno
sale del mismo GeoJSON que define la cobertura, así el borde cae exactamente donde
está el país en el recorte.

La línea se dibuja a 2x y se reduce con LANCZOS: a 2000 px una línea de 1 px queda
escalonada si se dibuja directo.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe cuadros\\snapshot_paraguay.py --fecha 2026-11-01 --hora 15
    .venv\\Scripts\\python.exe cuadros\\snapshot_paraguay.py --fecha 2026-11-01 --hora 15 --sin-borde
    .venv\\Scripts\\python.exe cuadros\\snapshot_paraguay.py --help   # no toca la red

Salida: `snapshot_paraguay_<AAAA-MM-DDTHHMM>_<PX>px.png`.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from paraguay import (MARGEN, caja_geojson, nombre_captura,  # noqa: E402
                     px_para_mpp, ts_de_crudo)
from rutas import SALIDAS  # noqa: E402

GEOJSON = RAIZ / "datos" / "paraguay_gadm.json"

FECHA = "2026-11-01"
HORA = 15
MINUTO = 0
PX = 3600
CAPA = "truecolor"
# El contorno va en negro; el grosor automático crece con el lado de la captura.
BORDE_COLOR = "#000000"
BORDE_ANCHO = 0.0                      # 0 = automático (1,6 px por cada 1600 px de lado)
SOMBRA_ANCHO = 2.4
SOMBRA_ALFA = 55

# Fuentes candidatas para el crédito opcional (si no hay ninguna, no se dibuja).
FUENTES = (
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)


def _anillos(geometria) -> list[list[tuple[float, float]]]:
    """Anillos exteriores e interiores de un Polygon o MultiPolygon."""
    tipo = geometria.get("type")
    coordenadas = geometria.get("coordinates", [])
    poligonos = [coordenadas] if tipo == "Polygon" else coordenadas
    anillos: list[list[tuple[float, float]]] = []
    for poligono in poligonos:
        for anillo in poligono:
            anillos.append([(float(p[0]), float(p[1])) for p in anillo])
    return anillos


def _a_pixel(lon: float, lat: float, caja, lado: int, escala: int) -> tuple[float, float]:
    """Proyección lineal lon/lat -> píxel (la imagen de GIBS es EPSG:4326)."""
    o, s, e, n = caja
    x = (lon - o) / (e - o) * lado * escala
    y = (n - lat) / (n - s) * lado * escala
    return x, y


def dibujar_borde(imagen: Image.Image, caja, geojson: Path, lado: int,
                  color: str = BORDE_COLOR, ancho: float = BORDE_ANCHO,
                  sombra: bool = False) -> Image.Image:
    """Dibuja el contorno de Paraguay sobre la captura, con antialias."""
    # A 2x un lado de 7600 px pide ~1 GB; arriba de 4000 se dibuja 1:1.
    escala = 2 if lado <= 4000 else 1
    capa = Image.new("RGBA", (lado * escala, lado * escala), (0, 0, 0, 0))
    lapiz = ImageDraw.Draw(capa)

    datos = json.loads(Path(geojson).read_text(encoding="utf-8"))
    anillos = []
    for feature in datos.get("features", []):
        anillos.extend(_anillos(feature.get("geometry", {})))

    grosor = ancho if ancho > 0 else max(1.6, lado / 1400)
    trazo = max(1, round(grosor * escala))
    for anillo in anillos:
        puntos = [_a_pixel(lon, lat, caja, lado, escala) for lon, lat in anillo]
        if len(puntos) < 3:
            continue
        if sombra:
            # Un filo oscuro debajo del blanco: la línea se lee sobre la nube.
            lapiz.line(puntos, fill=(0, 0, 0, SOMBRA_ALFA),
                       width=trazo + round(SOMBRA_ANCHO * escala), joint="curve")
        lapiz.line(puntos, fill=color, width=trazo, joint="curve")

    capa = capa.resize((lado, lado), Image.LANCZOS)
    salida = imagen.convert("RGBA").copy()
    salida.alpha_composite(capa)
    return salida.convert("RGB")


def _credito(imagen: Image.Image, texto: str, lado: int) -> Image.Image:
    """Crédito discreto abajo a la derecha (opcional)."""
    fuente = None
    for ruta in FUENTES:
        if Path(ruta).is_file():
            fuente = ImageFont.truetype(ruta, max(12, round(lado * 0.011)))
            break
    if fuente is None:
        return imagen
    dibujo = ImageDraw.Draw(imagen)
    margen = round(lado * 0.012)
    caja = dibujo.textbbox((0, 0), texto, font=fuente)
    x = lado - margen - (caja[2] - caja[0])
    y = lado - margen - (caja[3] - caja[1])
    dibujo.text((x + 2, y + 2), texto, font=fuente, fill=(0, 0, 0, 170))
    dibujo.text((x, y), texto, font=fuente, fill=(255, 255, 255, 235))
    return imagen


def componer(crudo: Path, caja, geojson: Path, lado: int, borde: bool = True,
             color: str = BORDE_COLOR, ancho: float = BORDE_ANCHO,
             sombra: bool = False, credito: str = "") -> Image.Image:
    with Image.open(crudo) as origen:
        imagen = origen.convert("RGB")
    if imagen.size != (lado, lado):
        raise SystemExit(f"{crudo.name}: {imagen.size[0]}x{imagen.size[1]}, "
                         f"se esperaba {lado}x{lado}. Revisá --px/margen.")
    if borde:
        imagen = dibujar_borde(imagen, caja, geojson, lado, color, ancho, sombra)
    if credito:
        imagen = _credito(imagen, credito, lado)
    return imagen


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Compone la captura de Paraguay (GIBS + contorno del país).")
    ap.add_argument("--fecha", default=FECHA,
                    help=f"día UTC de la captura (por defecto {FECHA})")
    ap.add_argument("--hora", type=int, default=HORA,
                    help=f"hora UTC 0-23 (por defecto {HORA})")
    ap.add_argument("--minuto", type=int, default=MINUTO,
                    help=f"minuto UTC 0-59 (por defecto {MINUTO})")
    ap.add_argument("--capa", default=CAPA,
                    help=f"capa del crudo: truecolor o geocolor (por defecto {CAPA})")
    ap.add_argument("--px", type=int, default=None,
                    help=f"lado de la captura en píxeles (por defecto {PX})")
    ap.add_argument("--mpp", type=float,
                    help="metros por píxel (el mismo que usó la descarga)")
    ap.add_argument("--margen", type=float, default=MARGEN,
                    help=f"margen alrededor del país (por defecto {MARGEN})")
    ap.add_argument("--geojson", default=str(GEOJSON),
                    help="GeoJSON usado para la cobertura y el contorno")
    ap.add_argument("--entrada", help="carpeta donde buscar el crudo "
                                       "(por defecto, la de salida)")
    ap.add_argument("--crudo", help="PNG crudo de GIBS (por defecto, el que deja "
                                    "descargar/snapshot_paraguay.py)")
    ap.add_argument("--ultima", action="store_true",
                    help="el instante sale del nombre del crudo (última disponible)")
    ap.add_argument("--sin-borde", action="store_true",
                    help="no dibujar el contorno del país")
    ap.add_argument("--borde-color", default=BORDE_COLOR,
                    help=f"color del contorno (por defecto {BORDE_COLOR})")
    ap.add_argument("--borde-ancho", type=float, default=BORDE_ANCHO,
                    help="grosor del contorno en px; 0 = automático según el lado")
    ap.add_argument("--sombra", action="store_true",
                    help="filo oscuro debajo del contorno (para líneas claras)")
    ap.add_argument("--credito", default="", help="texto de crédito (opcional)")
    ap.add_argument("--salidas", help="carpeta de salida (por defecto comun.rutas.SALIDAS)")
    ap.add_argument("--out", help="alias de --salidas")
    args = ap.parse_args(argv)

    try:
        dia = date.fromisoformat(args.fecha)
    except ValueError:
        raise SystemExit(f"--fecha inválida: {args.fecha!r} (se espera YYYY-MM-DD).")
    t = datetime(dia.year, dia.month, dia.day, args.hora, args.minuto)
    caja = caja_geojson(Path(args.geojson), args.margen)
    if args.mpp:
        args.px = px_para_mpp(caja, args.mpp)
    elif not args.px:
        args.px = PX
    salidas = Path(args.salidas or args.out or SALIDAS)
    salidas.mkdir(parents=True, exist_ok=True)

    if args.crudo:
        crudo = Path(args.crudo)
    else:
        entrada = Path(args.entrada) if args.entrada else salidas
        candidatos = sorted(
            entrada.glob(f"crudo_snapshot_{args.capa}_*_{args.px}px.png"))
        if not candidatos:
            raise SystemExit(
                f"No hay crudos en {entrada}. Corré primero:\n"
                f"  .venv\\Scripts\\python.exe descargar\\snapshot_paraguay.py "
                f"--fecha {args.fecha} --hora {args.hora} --px {args.px} "
                f"--out \"{entrada}\"")
        crudo = candidatos[-1]

    if getattr(args, "ultima", False):
        # Sin --ultima el instante es el que pidió el usuario; con --ultima manda
        # el nombre del crudo, que es el gránulo que GIBS realmente tenía.
        del_crudo = ts_de_crudo(crudo.name)
        if del_crudo is not None:
            t = del_crudo

    imagen = componer(crudo, caja, Path(args.geojson), args.px,
                      borde=not args.sin_borde, color=args.borde_color,
                      ancho=args.borde_ancho, sombra=args.sombra,
                      credito=args.credito)

    destino = salidas / nombre_captura(args.capa, t, args.px)
    tmp = destino.with_suffix(".png.parcial")
    imagen.save(tmp, format="PNG")
    tmp.replace(destino)
    print(f"Captura: {destino} ({imagen.size[0]}x{imagen.size[1]} px, "
          f"{destino.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
