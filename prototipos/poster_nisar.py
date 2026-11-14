"""Recorte de alta calidad de una escena NISAR GCOV sobre una caja.

El producto GCOV ya viene geocodificado y corregido por terreno: cada capa es
gamma0 en potencia lineal. Este script abre el HDF5, recorta la ventana que cae
dentro de ``--bbox`` (en la proyeccion UTM de la escena), pasa a dB y escribe un
PNG. En modo ``color`` compone R=HH, G=HV, B=HH-HV.

No reproyecta a lat/lon: dibuja el recorte en su grilla nativa, que es la que
tiene el dato. La caja y la escala quedan anotadas al pie.

    .venv\\Scripts\\python.exe prototipos\\poster_nisar.py --h5 ESCENA.h5 \
        --bbox -55.6,-24.5,-55.2,-23.9 --pol auto --modo color --px 2400 \
        --out recorte.png
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import h5py
import matplotlib
import numpy as np
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont
from pyproj import Transformer

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ / "comun") not in sys.path:
    sys.path.insert(0, str(RAIZ / "comun"))

import nisar as kit  # noqa: E402  (multilook y ventana automatica)

#: Nombres de dataset por polarizacion. El spec usa HHHH/HVHV; algunos productos
#: de ejemplo usan HH/HV. Se aceptan las dos formas.
CAPAS = {
    "HH": ("HHHH", "HH"),
    "HV": ("HVHV", "HV"),
    "VV": ("VVVV", "VV"),
    "VH": ("VHVH", "VH"),
}

FONDO = (11, 12, 13)
TINTA = (208, 214, 224)
TENUE = (124, 129, 138)
ACENTO = (130, 143, 255)


def _caja(texto: str) -> tuple[float, float, float, float]:
    try:
        oeste, sur, este, norte = [float(v) for v in texto.split(",")]
    except (AttributeError, ValueError) as exc:
        raise SystemExit("--bbox debe ser oeste,sur,este,norte") from exc
    if not (-180 <= oeste < este <= 180 and -90 <= sur < norte <= 90):
        raise SystemExit("--bbox fuera de rango o invertida")
    return oeste, sur, este, norte


def _grupo(f: h5py.File) -> tuple[h5py.Group, str]:
    base = f.get("/science/LSAR/GCOV/grids")
    if base is None:
        raise SystemExit("El HDF5 no tiene /science/LSAR/GCOV/grids; no es un GCOV.")
    bandas = [nombre for nombre in base if nombre.startswith("frequency")]
    if not bandas:
        raise SystemExit("El GCOV no declara ninguna banda frequencyA/frequencyB.")
    nombre = "frequencyA" if "frequencyA" in bandas else sorted(bandas)[0]
    return base[nombre], nombre


def _polarizaciones(grupo: h5py.Group) -> list[str]:
    if "listOfPolarizations" in grupo:
        crudo = grupo["listOfPolarizations"][()]
        salida = []
        for valor in np.ravel(crudo):
            texto = valor.decode() if isinstance(valor, bytes) else str(valor)
            texto = texto.strip().upper()
            if texto in CAPAS and texto not in salida:
                salida.append(texto)
        if salida:
            return salida
    # Respaldo: mirar que datasets existen.
    salida = []
    claves = set(grupo.keys())
    for pol, candidatos in CAPAS.items():
        if any(nombre in claves for nombre in candidatos):
            salida.append(pol)
    return salida


def _epsg(grupo: h5py.Group) -> int:
    if "projection" not in grupo:
        raise SystemExit("El GCOV no trae el dataset projection; no se puede ubicar la caja.")
    proyeccion = grupo["projection"]
    epsg = proyeccion.attrs.get("epsg_code")
    if epsg is None:
        epsg = proyeccion[()]
    if isinstance(epsg, bytes):
        epsg = epsg.decode()
    if isinstance(epsg, str):
        epsg = epsg.split(":")[-1]
    try:
        return int(np.ravel(epsg)[0])
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"No pude leer el EPSG de la escena: {epsg!r}") from exc


def _ventana(coords: np.ndarray, bajo: float, alto: float) -> tuple[int, int] | None:
    dentro = (coords >= bajo) & (coords <= alto)
    indices = np.flatnonzero(dentro)
    if indices.size == 0:
        return None
    return int(indices[0]), int(indices[-1]) + 1


def _capa(grupo: h5py.Group, pol: str) -> h5py.Dataset:
    for nombre in CAPAS[pol]:
        if nombre in grupo:
            return grupo[nombre]
    raise SystemExit(f"La escena no tiene la polarizacion {pol}.")


def _leer(
    capa: h5py.Dataset, r0: int, r1: int, c0: int, c1: int, px: int
) -> np.ndarray:
    alto, ancho = r1 - r0, c1 - c0
    tope = max(1, int(px * 1.5))
    paso = max(1, int(math.ceil(max(alto, ancho) / tope)))
    datos = capa[r0:r1:paso, c0:c1:paso]
    return np.asarray(datos, dtype=np.float32)


def _a_db(datos: np.ndarray) -> np.ndarray:
    potencia = np.asarray(datos, dtype=np.float32)
    valido = np.isfinite(potencia) & (potencia > 0)
    salida = np.full(potencia.shape, np.nan, dtype=np.float32)
    np.log10(potencia, out=salida, where=valido)
    salida *= 10.0
    return salida


def _limites(db: np.ndarray, vmin: float | None, vmax: float | None) -> tuple[float, float]:
    validos = db[np.isfinite(db)]
    if validos.size == 0:
        raise SystemExit("La ventana no tiene pixeles validos (todo enmascarado).")
    if vmin is None or vmax is None:
        muestra = validos
        if validos.size > 2_000_000:
            muestra = validos[:: validos.size // 2_000_000]
        p2, p98 = np.percentile(muestra, [2, 98])
        vmin = float(p2) if vmin is None else vmin
        vmax = float(p98) if vmax is None else vmax
    if not np.isfinite(vmin):
        vmin = -25.0
    if not np.isfinite(vmax):
        vmax = 5.0
    if vmax <= vmin:
        vmax = vmin + 1.0
    return float(vmin), float(vmax)


def _norm(db: np.ndarray, vmin: float, vmax: float) -> np.ndarray:
    return np.clip((db - vmin) / (vmax - vmin), 0.0, 1.0)


def _dimensiones(ancho: int, alto: int, px: int) -> tuple[int, int]:
    """Tamano de salida: el pedido, reduciendo o interpolando segun haga falta.

    Achicar no pierde detalle; agrandar no lo inventa, pero deja el PNG del
    tamano pedido para presentaciones (el log lo avisa).
    """
    objetivo = max(1, min(int(px), 4096))
    ancho = max(1, int(ancho))
    alto = max(1, int(alto))
    if ancho >= alto:
        return objetivo, max(1, round(objetivo * alto / ancho))
    return max(1, round(objetivo * ancho / alto)), objetivo


def _fuente(tamano: int) -> ImageFont.FreeTypeFont:
    try:
        ruta = font_manager.findfont("DejaVu Sans", fallback_to_default=True)
        return ImageFont.truetype(ruta, tamano)
    except Exception:  # noqa: BLE001 - sin fuente, PIL usa la de siempre
        return ImageFont.load_default()


def _barra_escala(metros_por_px: float, ancho: int) -> tuple[int, str]:
    objetivo = ancho * 0.16
    crudo = max(1.0, objetivo * metros_por_px)
    potencia = 10 ** math.floor(math.log10(crudo))
    for factor in (1, 2, 5, 10):
        distancia = factor * potencia
        if distancia >= crudo:
            break
    else:
        distancia = 10 * potencia
    return max(1, round(distancia / metros_por_px)), (
        f"{distancia / 1000:g} km" if distancia >= 1000 else f"{distancia:g} m"
    )


def _dibujar_escala(img: Image.Image, metros_por_px: float) -> None:
    ancho, alto = img.size
    largo, texto = _barra_escala(metros_por_px, ancho)
    fuente = _fuente(max(11, ancho // 95))
    margen = max(12, ancho // 80)
    y = alto - margen - max(16, ancho // 80)
    x = margen
    dibujo = ImageDraw.Draw(img)
    caja = dibujo.textbbox((0, 0), texto, font=fuente)
    alto_texto = caja[3] - caja[1]
    fondo = (8, 9, 10)
    dibujo.rectangle(
        [x - 6, y - 6, x + largo + 6, y + alto_texto + 14],
        fill=fondo,
    )
    dibujo.line([(x, y), (x + largo, y)], fill=(255, 255, 255), width=max(2, ancho // 700))
    dibujo.text((x, y + 4), texto, font=fuente, fill=(255, 255, 255))


def _dibujar_borde(
    img: Image.Image,
    geojson: Path,
    epsg: int,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
) -> None:
    try:
        datos = json.loads(geojson.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print(f"aviso: no pude leer {geojson}; sigo sin borde")
        return

    ancho, alto = img.size
    if x1 <= x0 or y1 <= y0:
        return
    transformador = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    dibujo = ImageDraw.Draw(img)

    for feature in datos.get("features", []):
        geometria = feature.get("geometry") or {}
        tipo = geometria.get("type")
        if tipo == "Polygon":
            poligonos = [geometria.get("coordinates") or []]
        elif tipo == "MultiPolygon":
            poligonos = geometria.get("coordinates") or []
        else:
            continue
        for poligono in poligonos:
            for anillo in poligono:
                if len(anillo) < 2:
                    continue
                lons = np.array([punto[0] for punto in anillo], dtype=np.float64)
                lats = np.array([punto[1] for punto in anillo], dtype=np.float64)
                xs, ys = transformador.transform(lons, lats)
                px = (xs - x0) / (x1 - x0) * (ancho - 1)
                py = (y1 - ys) / (y1 - y0) * (alto - 1)
                puntos = [
                    (float(a), float(b))
                    for a, b in zip(px, py)
                    if np.isfinite(a) and np.isfinite(b)
                ]
                if len(puntos) < 2:
                    continue
                grosor = max(1, ancho // 1100)
                dibujo.line(puntos, fill=(8, 9, 10), width=grosor + 2, joint="curve")
                dibujo.line(puntos, fill=(255, 255, 255), width=grosor, joint="curve")


def _pie(
    img: Image.Image,
    lineas: list[str],
) -> Image.Image:
    ancho, alto = img.size
    alto_pie = max(44, int(ancho * 0.05))
    lienzo = Image.new("RGB", (ancho, alto + alto_pie), FONDO)
    lienzo.paste(img, (0, 0))
    dibujo = ImageDraw.Draw(lienzo)
    dibujo.line([(0, alto), (ancho, alto)], fill=(42, 44, 49), width=1)
    fuente1 = _fuente(max(12, int(ancho * 0.012)))
    fuente2 = _fuente(max(10, int(ancho * 0.009)))
    margen = max(10, int(ancho * 0.014))
    y = alto + max(8, int(ancho * 0.009))
    for indice, texto in enumerate(lineas[:2]):
        dibujo.text(
            (margen, y),
            texto,
            font=fuente1 if indice == 0 else fuente2,
            fill=TINTA if indice == 0 else TENUE,
        )
        y += max(16, int(ancho * 0.016))
    return lienzo


def _fecha_granulo(nombre: str) -> str:
    """``..._20261029T214921_...`` -> ``2026-10-29 21:49 UTC``."""
    encontrado = re.search(r"(\d{8})T(\d{6})", nombre)
    if not encontrado:
        return ""
    dia, hora = encontrado.groups()
    return f"{dia[:4]}-{dia[4:6]}-{dia[6:]} {hora[:2]}:{hora[2:4]} UTC"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--h5", required=True, help="escena NISAR GCOV (.h5)")
    ap.add_argument("--bbox", required=True, help="oeste,sur,este,norte en grados")
    ap.add_argument("--pol", default="auto", choices=("auto", "HH", "HV", "VV", "VH"))
    ap.add_argument("--modo", default="gris", choices=("gris", "color"))
    ap.add_argument("--px", type=int, default=2400, help="lado mayor del PNG (800-4096)")
    ap.add_argument("--out", required=True, help="PNG de salida")
    ap.add_argument("--geojson", default=None, help="contorno para superponer (opcional)")
    ap.add_argument("--db-min", type=float, default=None)
    ap.add_argument("--db-max", type=float, default=None)
    ap.add_argument(
        "--ventana",
        type=int,
        default=0,
        help="lado del multilook (impar); 0 = automatico para ~90 m, 1 = sin filtro",
    )
    args = ap.parse_args()

    h5 = Path(args.h5)
    if not h5.is_file():
        raise SystemExit(f"No existe la escena: {h5}")
    oeste, sur, este, norte = _caja(args.bbox)
    px = max(800, min(int(args.px), 4096))
    salida = Path(args.out)
    salida.parent.mkdir(parents=True, exist_ok=True)

    print(f"abriendo {h5.name}")
    with h5py.File(h5, "r") as f:
        grupo, banda = _grupo(f)
        epsg = _epsg(grupo)
        disponibles = _polarizaciones(grupo)
        if not disponibles:
            raise SystemExit("La escena no declara polarizaciones.")

        x = np.asarray(grupo["xCoordinates"][()], dtype=np.float64).ravel()
        y = np.asarray(grupo["yCoordinates"][()], dtype=np.float64).ravel()
        if x.size < 2 or y.size < 2:
            raise SystemExit("Las coordenadas de la grilla estan vacias.")

        transformador = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
        try:
            x_min, y_min, x_max, y_max = transformador.transform_bounds(
                oeste, sur, este, norte, densify_pts=21
            )
        except Exception as exc:  # noqa: BLE001 - pyproj cambia el tipo de error
            raise SystemExit(f"No pude proyectar la caja a EPSG:{epsg}: {exc}") from exc
        ventana_x = _ventana(x, x_min, x_max)
        ventana_y = _ventana(y, y_min, y_max)
        if ventana_x is None or ventana_y is None:
            raise SystemExit(
                "La caja no intersecta esta escena. Revisa el poligono del granulo."
            )
        c0, c1 = ventana_x
        r0, r1 = ventana_y
        print(
            f"proyeccion EPSG:{epsg} | {banda} | "
            f"recorte {r1 - r0}x{c1 - c0} px nativos | pols {', '.join(disponibles)}"
        )

        # Multilook: un color SAR a resolucion nativa es casi todo speckle. Se
        # promedia la potencia (nunca el dB) a ~90 m para que se vea el terreno.
        mpp_nativo = abs(float(x[min(c0 + 1, x.size - 1)] - x[c0]))
        paso_lectura = max(
            1, int(math.ceil(max(r1 - r0, c1 - c0) / max(1, int(px * 1.5))))
        )
        if args.ventana == 1:
            ventana = 1
        elif args.ventana > 1:
            ventana = int(args.ventana)
        else:
            ventana = kit.ventana_para(mpp_nativo * paso_lectura, metros=90.0)
        if ventana % 2 == 0:
            ventana += 1
        resolucion = (
            f"multilook {ventana}x{ventana} (~{ventana * mpp_nativo * paso_lectura:.0f} m)"
            if ventana > 1
            else "sin filtro (speckle nativo)"
        )
        print(f"{resolucion} · {mpp_nativo:.0f} m/px nativos")

        if args.pol == "auto":
            elegidas = [p for p in ("HH", "HV") if p in disponibles]
            if not elegidas:
                elegidas = disponibles[:1]
        else:
            elegidas = [args.pol]
            if args.pol not in disponibles:
                raise SystemExit(f"La escena no tiene {args.pol}; tiene {', '.join(disponibles)}.")

        modo = args.modo
        if modo == "color" and len(elegidas) < 2:
            print("aviso: color necesita dos polarizaciones; cae a gris")
            modo = "gris"

        if modo == "color":
            hh = kit.multilook(_leer(_capa(grupo, elegidas[0]), r0, r1, c0, c1, px), ventana)
            hv = kit.multilook(_leer(_capa(grupo, elegidas[1]), r0, r1, c0, c1, px), ventana)
            db_hh = _a_db(hh)
            db_hv = _a_db(hv)
            print(f"leyendo {elegidas[0]} + {elegidas[1]}")
            vmin, vmax = _limites(db_hh, args.db_min, args.db_max)
            vmin2, vmax2 = _limites(db_hv, args.db_min, args.db_max)
            db_ratio = db_hh - db_hv
            vmin3, vmax3 = _limites(db_ratio, None, None)
            rojo = _norm(db_hh, vmin, vmax)
            verde = _norm(db_hv, vmin2, vmax2)
            azul = _norm(db_ratio, vmin3, vmax3)
            rgb = np.dstack([rojo, verde, azul]) * 255.0
            rgb = np.where(np.isfinite(db_hh)[..., None], rgb, 0.0)
            etiqueta = f"{elegidas[0]}+{elegidas[1]} · RGB {elegidas[0]}/{elegidas[1]}/ratio"
            rango = f"dB {vmin:.1f} a {vmax:.1f}"
        else:
            pol = elegidas[0]
            datos = kit.multilook(_leer(_capa(grupo, pol), r0, r1, c0, c1, px), ventana)
            db = _a_db(datos)
            print(f"leyendo {pol}")
            vmin, vmax = _limites(db, args.db_min, args.db_max)
            gris = _norm(db, vmin, vmax)
            rgba = matplotlib.colormaps["gray"](gris, bytes=True)
            rgb = rgba[..., :3].astype(np.float32)
            rgb = np.where(np.isfinite(db)[..., None], rgb, 0.0)
            etiqueta = pol
            rango = f"dB {vmin:.1f} a {vmax:.1f}"

        # La grilla puede venir al reves: se normaliza a oeste->este y norte->sur.
        if x[c0] > x[c1 - 1]:
            rgb = np.flip(rgb, axis=1)
        if y[r0] < y[r1 - 1]:
            rgb = np.flip(rgb, axis=0)
        alto, ancho = rgb.shape[:2]
        ancho_salida, alto_salida = _dimensiones(ancho, alto, px)
        if ancho_salida > ancho or alto_salida > alto:
            print(
                f"aviso: el recorte nativo es {ancho}x{alto} px; la salida "
                f"{ancho_salida}x{alto_salida} px se interpola (no agrega detalle)"
            )
        img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")
        img = img.resize((ancho_salida, alto_salida), Image.LANCZOS)

        x0, x1 = float(min(x[c0], x[c1 - 1])), float(max(x[c0], x[c1 - 1]))
        y0, y1 = float(min(y[r0], y[r1 - 1])), float(max(y[r0], y[r1 - 1]))
        metros_por_px = (x1 - x0) / max(1, ancho_salida - 1)
        _dibujar_escala(img, metros_por_px)
        if args.geojson:
            _dibujar_borde(img, Path(args.geojson), epsg, x0, x1, y0, y1)

        fecha = _fecha_granulo(h5.stem)
        pie1 = f"NISAR GCOV · {etiqueta} · {rango}"
        pie2 = (
            f"caja {oeste:g}, {sur:g}, {este:g}, {norte:g} · "
            f"{metros_por_px:.0f} m/px · EPSG:{epsg}"
        )
        if fecha:
            pie2 += f" · {fecha}"
        img = _pie(img, [pie1, pie2])
        img.save(salida, "PNG", optimize=True)

    meta = {
        "fuente": str(h5),
        "salida": str(salida),
        "bbox": [oeste, sur, este, norte],
        "epsg": epsg,
        "banda": banda,
        "polarizaciones": elegidas,
        "modo": modo,
        "tamano": list(img.size),
        "metros_por_px": round(metros_por_px, 3),
        "multilook": ventana,
        "multilook_m": round(ventana * mpp_nativo * paso_lectura, 1),
    }
    salida.with_suffix(".json").write_text(
        json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    print(f"listo: {salida} ({img.size[0]}x{img.size[1]} px)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
