"""Compone el póster de un recorte CBERS-4A.

La descarga deja ``crudo_cbers.png`` + ``crudo_cbers.json`` en
``descargar/cbers.py``. Acá se arma el póster: imagen, título, zona, detalle
real y barra de escala. Sin proyecciones ni cartopy: el recorte ya viene en su
grilla y la escala sale de los metros por píxel del JSON.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe cuadros\\cuadros_cbers.py --entrada datos\\cbers
    .venv\\Scripts\\python.exe cuadros\\cuadros_cbers.py --help
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
from estilo import BG, TXT, TXT_DIM, ruta_fuente  # noqa: E402
from rutas import SALIDAS  # noqa: E402

CREDITO = "Graphic by @Gillo97"
FUENTE = "INPE · CBERS-4A · CC-BY 4.0"
ESCALA_TEXTO = 0.9


def _fuente(px: int, negrita: bool = False) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype(ruta_fuente(negrita), max(8, int(px)))
    except OSError:
        return ImageFont.load_default()


def _rgb(hexa: str) -> tuple[int, int, int]:
    hexa = hexa.lstrip("#")
    return tuple(int(hexa[i:i + 2], 16) for i in (0, 2, 4))


def _texto(d: ImageDraw.ImageDraw, xy, texto: str, px: int, color,
           negrita: bool = False, sombra: bool = False) -> None:
    f = _fuente(px, negrita)
    if sombra:
        d.text((xy[0] + 2, xy[1] + 2), texto, font=f, fill=(0, 0, 0, 220))
    d.text(xy, texto, font=f, fill=color)


def _barra_escala(d: ImageDraw.ImageDraw, ancho_img: int, alto_img: int,
                  mpp: float, margen: int) -> None:
    """Barra de ~1/5 del ancho con una longitud redonda en km."""
    if mpp <= 0:
        return
    objetivo_m = ancho_img * 0.22 * mpp
    candidatos = (0.5, 1, 2, 5, 10, 20, 25, 50, 100)
    km = min(candidatos, key=lambda v: abs(v * 1000 - objetivo_m))
    largo = km * 1000.0 / mpp
    if largo < 30 or largo > ancho_img * 0.6:
        return
    x1 = margen
    y = alto_img - margen
    x2 = x1 + largo
    alto = max(6, int(alto_img * 0.008))
    tam = max(12, int(alto_img * 0.019))
    f = _fuente(tam)
    caja_texto = d.textbbox((0, 0), f"{km:g} km", font=f)
    alto_texto = caja_texto[3] - caja_texto[1]
    y_texto = y - alto - 12 - alto_texto
    d.rectangle([x1 - 12, y_texto - 10, x2 + 12, y + 8], fill=(0, 0, 0, 115))
    d.rectangle([x1, y - alto, x2, y], fill=(255, 255, 255, 235))
    d.rectangle([x1, y - alto - 6, x1 + 3, y + 6], fill=(255, 255, 255, 235))
    d.rectangle([x2 - 3, y - alto - 6, x2, y + 6], fill=(255, 255, 255, 235))
    _texto(d, (x1, y_texto), f"{km:g} km", tam, "#ffffff",
           negrita=True, sombra=True)


def componer(img: Image.Image, meta: dict, salida: Path, credito: str,
             sin_fecha: bool = False) -> Path:
    px = img.width
    margen = max(20, px // 40)
    cabecera = max(96, px // 7)
    pie = max(60, px // 12)
    ancho = px + 2 * margen
    alto = px + cabecera + pie

    fondo = _rgb(BG)
    lienzo = Image.new("RGBA", (ancho, alto), (*fondo, 255))
    d = ImageDraw.Draw(lienzo, "RGBA")

    x0, y0 = margen, cabecera
    d.rectangle([x0 - 1, y0 - 1, x0 + px, y0 + px], fill=(255, 255, 255, 40))
    lienzo.paste(img, (x0, y0))

    detalle = str(meta.get("detalle", "8"))
    sensor = "WPM" if detalle in ("2", "8") else "MUX"
    zona = str(meta.get("zona_label") or meta.get("zona") or "")
    mpp = float(meta.get("mpp") or 0)
    km = float(meta.get("km") or 0)
    fecha = str(meta.get("datetime") or "")[:10]
    if fecha:
        try:
            fecha = datetime.strptime(fecha, "%Y-%m-%d").strftime("%d %b %Y").upper()
        except ValueError:
            pass

    esc = ESCALA_TEXTO * (px / 1200.0) ** 0.35
    _texto(d, (margen, max(16, px // 48)), f"CBERS-4A · {sensor}",
           int(36 * esc), TXT, negrita=True)
    linea = f"{zona.upper()} · {km:.0f} KM · {mpp:.1f} M/PX"
    if fecha and not sin_fecha:
        linea += f" · {fecha}"
    _texto(d, (margen, max(16, px // 48) + int(46 * esc)), linea,
           int(18 * esc), TXT_DIM)

    y_pie = cabecera + px + max(12, px // 60)
    _texto(d, (margen, y_pie), FUENTE, int(15 * esc), TXT_DIM)
    if credito:
        f = _fuente(int(15 * esc))
        caja = d.textbbox((0, 0), credito, font=f)
        _texto(d, (margen + px - (caja[2] - caja[0]), y_pie), credito,
               int(15 * esc), TXT_DIM)

    zona_id = str(meta.get("zona") or "cbers")
    fecha_id = str(meta.get("datetime") or "")[:10].replace("-", "")
    destino = salida / f"cbers_{zona_id}_{fecha_id or 'sinfecha'}.png"
    temporal = destino.with_suffix(".png.parcial")
    lienzo.convert("RGB").save(temporal, format="PNG")
    temporal.replace(destino)
    return destino


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Compone el póster de un recorte CBERS-4A.")
    ap.add_argument("--entrada", required=True,
                    help="carpeta con crudo_cbers.png y crudo_cbers.json")
    ap.add_argument("--out", help="carpeta del PNG final (por defecto, SALIDAS)")
    ap.add_argument("--credito", default=CREDITO, help="crédito del pie")
    ap.add_argument("--sin-fecha", action="store_true",
                    help="no incluir la fecha en el subtítulo")
    args = ap.parse_args(argv)

    entrada = Path(args.entrada)
    png = entrada / "crudo_cbers.png"
    meta_path = entrada / "crudo_cbers.json"
    if not png.is_file() or not meta_path.is_file():
        raise SystemExit(
            f"Faltan {png.name} o {meta_path.name} en {entrada}. "
            "Descargá primero con descargar\\cbers.py.")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    salida = Path(args.out) if args.out else SALIDAS
    salida.mkdir(parents=True, exist_ok=True)

    img = Image.open(png).convert("RGB")
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    cd = ImageDraw.Draw(capa, "RGBA")
    _barra_escala(cd, img.width, img.height, float(meta.get("mpp") or 1),
                  max(16, img.width // 40))
    img = Image.alpha_composite(img.convert("RGBA"), capa).convert("RGB")
    destino = componer(img, meta, salida, args.credito, args.sin_fecha)
    print(f"Póster CBERS-4A: {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
