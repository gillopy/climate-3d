"""Kit compartido para escenas NISAR GCOV.

Abre el HDF5, recorta una caja en la grilla nativa de la escena, aplica la mascara
de la escena y deja los datos en potencia lineal (que es como vienen). Los
productos (`nisar_rvi.py`, `nisar_cambio.py`, `poster_nisar.py`) solo eligen la
cuenta y la paleta: leer, recortar, orientar y guardar vive aca.

Nada de esto reproyecta a lat/lon: el recorte se queda en la UTM de la escena,
que es la grilla que tiene el dato y la que mantiene el pixel cuadrado.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import h5py
import matplotlib
import numpy as np
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont
from pyproj import Transformer

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


@dataclass
class Recorte:
    """Una ventana de una capa, ya recortada, en potencia lineal."""

    datos: np.ndarray
    xs: np.ndarray
    ys: np.ndarray
    epsg: int
    escena: str
    paso: int
    filas: int
    columnas: int

    @property
    def x0(self) -> float:
        return float(min(self.xs[0], self.xs[-1]))

    @property
    def x1(self) -> float:
        return float(max(self.xs[0], self.xs[-1]))

    @property
    def y0(self) -> float:
        return float(min(self.ys[0], self.ys[-1]))

    @property
    def y1(self) -> float:
        return float(max(self.ys[0], self.ys[-1]))

    @property
    def metros_por_px(self) -> float:
        return abs(self.x1 - self.x0) / max(1, self.columnas - 1)


def caja(texto: str) -> tuple[float, float, float, float]:
    try:
        oeste, sur, este, norte = [float(v) for v in str(texto).split(",")]
    except (AttributeError, ValueError) as exc:
        raise SystemExit("La caja debe ser oeste,sur,este,norte") from exc
    if not (-180 <= oeste < este <= 180 and -90 <= sur < norte <= 90):
        raise SystemExit("La caja esta fuera de rango o invertida")
    return oeste, sur, este, norte


def fecha_granulo(nombre: str) -> str:
    """``..._20261029T214921_...`` -> ``2026-10-29 21:49 UTC``."""
    encontrado = re.search(r"(\d{8})T(\d{6})", nombre)
    if not encontrado:
        return ""
    dia, hora = encontrado.groups()
    return f"{dia[:4]}-{dia[4:6]}-{dia[6:]} {hora[:2]}:{hora[2:4]} UTC"


def _epsg(grupo: h5py.Group) -> int:
    if "projection" not in grupo:
        raise SystemExit("El GCOV no trae el dataset projection.")
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


def _polarizaciones(grupo: h5py.Group) -> list[str]:
    salida: list[str] = []
    if "listOfPolarizations" in grupo:
        crudo = grupo["listOfPolarizations"][()]
        for valor in np.ravel(crudo):
            texto = valor.decode() if isinstance(valor, bytes) else str(valor)
            texto = texto.strip().upper()
            if texto in CAPAS and texto not in salida:
                salida.append(texto)
        if salida:
            return salida
    claves = set(grupo.keys())
    for pol, candidatos in CAPAS.items():
        if any(nombre in claves for nombre in candidatos):
            salida.append(pol)
    return salida


def _ventana(coords: np.ndarray, bajo: float, alto: float) -> tuple[int, int] | None:
    dentro = (coords >= bajo) & (coords <= alto)
    indices = np.flatnonzero(dentro)
    if indices.size == 0:
        return None
    return int(indices[0]), int(indices[-1]) + 1


class Escena:
    """Una escena GCOV abierta. Usar como context manager."""

    def __init__(self, ruta: str | Path) -> None:
        self.ruta = Path(ruta)
        if not self.ruta.is_file():
            raise SystemExit(f"No existe la escena: {self.ruta}")
        self._f = h5py.File(self.ruta, "r")
        base = self._f.get("/science/LSAR/GCOV/grids")
        if base is None:
            self._f.close()
            raise SystemExit("El HDF5 no tiene /science/LSAR/GCOV/grids; no es un GCOV.")
        bandas = [nombre for nombre in base if nombre.startswith("frequency")]
        if not bandas:
            self._f.close()
            raise SystemExit("El GCOV no declara frequencyA/frequencyB.")
        self.banda = "frequencyA" if "frequencyA" in bandas else sorted(bandas)[0]
        self.grupo = base[self.banda]
        self.epsg = _epsg(self.grupo)
        self.pols = _polarizaciones(self.grupo)
        self.x = np.asarray(self.grupo["xCoordinates"][()], dtype=np.float64).ravel()
        self.y = np.asarray(self.grupo["yCoordinates"][()], dtype=np.float64).ravel()
        if self.x.size < 2 or self.y.size < 2:
            self._f.close()
            raise SystemExit("Las coordenadas de la grilla estan vacias.")
        self.fecha = fecha_granulo(self.ruta.stem)
        self.track = self._ident("trackNumber")
        self.frame = self._ident("frameNumber")

    def _ident(self, clave: str) -> int | None:
        ruta = f"/science/LSAR/identification/{clave}"
        if ruta not in self._f:
            return None
        valor = self._f[ruta][()]
        if isinstance(valor, bytes):
            valor = valor.decode()
        try:
            return int(valor)
        except (TypeError, ValueError):
            return None

    def __enter__(self) -> "Escena":
        return self

    def __exit__(self, *_) -> None:
        self._f.close()

    def capa(self, pol: str) -> h5py.Dataset:
        for nombre in CAPAS.get(pol, ()):
            if nombre in self.grupo:
                return self.grupo[nombre]
        raise SystemExit(
            f"La escena no tiene {pol}; tiene {', '.join(self.pols) or 'ninguna'}."
        )

    def recortar(self, pol: str, bbox: str, px: int = 2400) -> Recorte:
        """Recorta `bbox` (lon/lat) en la grilla de la escena, con mascara."""
        oeste, sur, este, norte = caja(bbox)
        transformador = Transformer.from_crs("EPSG:4326", f"EPSG:{self.epsg}", always_xy=True)
        try:
            x_min, y_min, x_max, y_max = transformador.transform_bounds(
                oeste, sur, este, norte, densify_pts=21
            )
        except Exception as exc:  # noqa: BLE001 - pyproj cambia el tipo
            raise SystemExit(f"No pude proyectar la caja a EPSG:{self.epsg}: {exc}") from exc

        ventana_x = _ventana(self.x, x_min, x_max)
        ventana_y = _ventana(self.y, y_min, y_max)
        if ventana_x is None or ventana_y is None:
            raise SystemExit("La caja no intersecta esta escena.")
        c0, c1 = ventana_x
        r0, r1 = ventana_y

        alto, ancho = r1 - r0, c1 - c0
        tope = max(1, int(px * 1.5))
        paso = max(1, int(math.ceil(max(alto, ancho) / tope)))
        datos = np.asarray(self.capa(pol)[r0:r1:paso, c0:c1:paso], dtype=np.float32)

        if "mask" in self.grupo:
            mascara = np.asarray(self.grupo["mask"][r0:r1:paso, c0:c1:paso])
            datos = np.where((mascara > 0) & (mascara < 255), datos, np.nan)

        xs = self.x[c0:c1:paso]
        ys = self.y[r0:r1:paso]
        return Recorte(
            datos=datos,
            xs=xs,
            ys=ys,
            epsg=self.epsg,
            escena=self.ruta.stem,
            paso=paso,
            filas=int(datos.shape[0]),
            columnas=int(datos.shape[1]),
        )


def orientar(recorte: Recorte) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Devuelve (datos, xs, ys) con oeste->este y norte->sur."""
    datos = recorte.datos
    xs = recorte.xs
    ys = recorte.ys
    if xs[0] > xs[-1]:
        datos = np.flip(datos, axis=1)
        xs = xs[::-1]
    if ys[0] < ys[-1]:
        datos = np.flip(datos, axis=0)
        ys = ys[::-1]
    return datos, xs, ys


def a_db(potencia: np.ndarray) -> np.ndarray:
    datos = np.asarray(potencia, dtype=np.float32)
    valido = np.isfinite(datos) & (datos > 0)
    salida = np.full(datos.shape, np.nan, dtype=np.float32)
    np.log10(datos, out=salida, where=valido)
    salida *= 10.0
    return salida


def rvi(hh: np.ndarray, hv: np.ndarray) -> np.ndarray:
    """RVI dual-pol (notebook de Sentinel-1) adaptado a HH/HV en potencia."""
    hh = np.asarray(hh, dtype=np.float32)
    hv = np.asarray(hv, dtype=np.float32)
    valido = np.isfinite(hh) & np.isfinite(hv) & (hh > 0) & (hv > 0)
    suma = np.where(valido, hh + hv, np.nan)
    dop = np.where(valido, hh / suma, np.nan)
    salida = np.sqrt(dop) * (4.0 * hv / suma)
    salida = np.where(valido, np.clip(salida, 0.0, 1.5), np.nan)
    return salida.astype(np.float32)


def limites(datos: np.ndarray, vmin: float | None = None, vmax: float | None = None) -> tuple[float, float]:
    validos = datos[np.isfinite(datos)]
    if validos.size == 0:
        raise SystemExit("La ventana no tiene pixeles validos.")
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


def normalizar(datos: np.ndarray, vmin: float, vmax: float) -> np.ndarray:
    return np.clip((datos - vmin) / (vmax - vmin), 0.0, 1.0)


def paleta(nombre: str, valores: np.ndarray) -> np.ndarray:
    rgba = matplotlib.colormaps[nombre](valores, bytes=True)
    return rgba[..., :3]


def dimensiones(ancho: int, alto: int, px: int) -> tuple[int, int]:
    px = max(800, min(int(px), 4096))
    if ancho >= alto:
        return px, max(1, round(px * alto / ancho))
    return max(1, round(px * ancho / alto)), px


def _fuente(tamano: int) -> ImageFont.FreeTypeFont:
    try:
        ruta = font_manager.findfont("DejaVu Sans", fallback_to_default=True)
        return ImageFont.truetype(ruta, tamano)
    except Exception:  # noqa: BLE001
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
    caja_texto = dibujo.textbbox((0, 0), texto, font=fuente)
    alto_texto = caja_texto[3] - caja_texto[1]
    dibujo.rectangle([x - 6, y - 6, x + largo + 6, y + alto_texto + 14], fill=(8, 9, 10))
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
                lons = np.array([p[0] for p in anillo], dtype=np.float64)
                lats = np.array([p[1] for p in anillo], dtype=np.float64)
                xs, ys = transformador.transform(lons, lats)
                px = (xs - x0) / (x1 - x0) * (ancho - 1)
                py = (y1 - ys) / (y1 - y0) * (alto - 1)
                puntos = [(float(a), float(b)) for a, b in zip(px, py) if np.isfinite(a) and np.isfinite(b)]
                if len(puntos) < 2:
                    continue
                grosor = max(1, ancho // 1100)
                dibujo.line(puntos, fill=(8, 9, 10), width=grosor + 2, joint="curve")
                dibujo.line(puntos, fill=(255, 255, 255), width=grosor, joint="curve")


def _pie(img: Image.Image, lineas: list[str], px: int) -> Image.Image:
    ancho, alto = img.size
    alto_pie = max(58, int(px * 0.05))
    lienzo = Image.new("RGB", (ancho, alto + alto_pie), FONDO)
    lienzo.paste(img, (0, 0))
    dibujo = ImageDraw.Draw(lienzo)
    dibujo.line([(0, alto), (ancho, alto)], fill=(42, 44, 49), width=1)
    fuente1 = _fuente(max(14, int(px * 0.012)))
    fuente2 = _fuente(max(11, int(px * 0.009)))
    margen = max(14, int(px * 0.014))
    y = alto + max(10, int(px * 0.009))
    for indice, texto in enumerate(lineas[:2]):
        dibujo.text(
            (margen, y),
            texto,
            font=fuente1 if indice == 0 else fuente2,
            fill=TINTA if indice == 0 else TENUE,
        )
        y += max(18, int(px * 0.016))
    return lienzo


def guardar(
    rgb: np.ndarray,
    salida: str | Path,
    lineas: list[str],
    metros_por_px: float,
    px: int,
    geojson: str | Path | None = None,
    epsg: int | None = None,
    x0: float | None = None,
    x1: float | None = None,
    y0: float | None = None,
    y1: float | None = None,
) -> tuple[int, int]:
    """Guarda un RGB (h,w,3) con escala, borde opcional y pie. Devuelve (W,H)."""
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    alto, ancho = rgb.shape[:2]
    ancho_salida, alto_salida = dimensiones(ancho, alto, px)
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")
    img = img.resize((ancho_salida, alto_salida), Image.LANCZOS)
    if metros_por_px > 0:
        _dibujar_escala(img, metros_por_px)
    if geojson and epsg is not None and None not in (x0, x1, y0, y1):
        _dibujar_borde(img, Path(geojson), epsg, float(x0), float(x1), float(y0), float(y1))
    img = _pie(img, lineas, px)
    img.save(salida, "PNG", optimize=True)
    return img.size


def guardar_json(salida: str | Path, meta: dict) -> None:
    ruta = Path(salida).with_suffix(".json")
    ruta.write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
