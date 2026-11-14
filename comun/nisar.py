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


def compatibles(a: Recorte, b: Recorte) -> bool:
    """True si dos recortes comparten forma y extensión (misma grilla)."""
    if a.datos.shape != b.datos.shape:
        return False
    # Mismo track/frame = misma grilla exacta; 1/4 de píxel es margen de sobra.
    tolerancia = max(a.metros_por_px, b.metros_por_px, 1.0) * 0.25
    return all(
        abs(uno - otro) <= tolerancia
        for uno, otro in ((a.x0, b.x0), (a.x1, b.x1), (a.y0, b.y0), (a.y1, b.y1))
    )


def hectareas(pixeles: int, mpp_x: float, mpp_y: float) -> float:
    return pixeles * mpp_x * mpp_y / 10000.0


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


def mayoria3(mascara: np.ndarray) -> np.ndarray:
    """True si al menos 5 de los 9 pixeles del entorno son True.

    Sirve para no contar pixeles aislados de cambio como pérdida.
    """
    m = np.asarray(mascara).astype(np.uint8)
    if m.size == 0:
        return np.asarray(mascara, dtype=bool)
    relleno = np.pad(m, 1)
    suma = np.zeros_like(m, dtype=np.uint8)
    for dy in range(3):
        for dx in range(3):
            suma += relleno[dy : dy + m.shape[0], dx : dx + m.shape[1]]
    return suma >= 5


def filtrar_mmu(mascara: np.ndarray, minimo: int) -> np.ndarray:
    """Deja solo las componentes conexas (8 vecinos) de al menos ``minimo`` px.

    Es la unidad minima de mapeo: un desmonte real es un bloque, no pixeles
    sueltos. Sin scipy: recorrido en profundidad iterativo sobre el array plano.
    """
    m = np.asarray(mascara, dtype=bool)
    if minimo <= 1 or not m.any():
        return m
    alto, ancho = m.shape
    plano = m.ravel()
    vistos = np.zeros(plano.shape, dtype=bool)
    salida = np.zeros(plano.shape, dtype=bool)
    for inicio in np.flatnonzero(plano):
        origen = int(inicio)
        if vistos[origen]:
            continue
        vistos[origen] = True
        pila = [origen]
        componentes: list[int] = []
        while pila:
            indice = pila.pop()
            componentes.append(indice)
            fila, columna = divmod(indice, ancho)
            for df in (-1, 0, 1):
                nueva_fila = fila + df
                if nueva_fila < 0 or nueva_fila >= alto:
                    continue
                base = nueva_fila * ancho
                for dc in (-1, 0, 1):
                    nueva_columna = columna + dc
                    if nueva_columna < 0 or nueva_columna >= ancho:
                        continue
                    vecino = base + nueva_columna
                    if plano[vecino] and not vistos[vecino]:
                        vistos[vecino] = True
                        pila.append(vecino)
        if len(componentes) >= minimo:
            salida[componentes] = True
    return salida.reshape(alto, ancho)


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


def _boxcar_eje(datos: np.ndarray, ventana: int, eje: int) -> np.ndarray:
    """Suma movil de ``ventana`` muestras a lo largo de ``eje`` (borde replicado)."""
    if ventana <= 1:
        return datos
    mitad = ventana // 2
    relleno = [(0, 0), (0, 0)]
    relleno[eje] = (mitad, ventana - 1 - mitad)
    ampliado = np.pad(datos, relleno, mode="edge")
    acumulado = np.cumsum(ampliado, axis=eje, dtype=np.float64)
    largo = acumulado.shape[eje]
    ceros = np.zeros_like(np.take(acumulado, [0], axis=eje))
    previo = np.concatenate(
        [ceros, np.take(acumulado, np.arange(largo - ventana), axis=eje)], axis=eje
    )
    return np.take(acumulado, np.arange(ventana - 1, largo), axis=eje) - previo


def multilook(potencia: np.ndarray, ventana: int) -> np.ndarray:
    """Promedio ``ventana``x``ventana`` sobre potencia lineal, ignorando NaN.

    Un indice por pixel calculado sobre dos canales con speckle es ruido puro:
    promediar la potencia (nunca el dB) antes de dividir deja ver la estructura
    del terreno a costa de resolucion (``ventana`` x metros por pixel).
    """
    if ventana <= 1:
        return np.asarray(potencia, dtype=np.float32)
    datos = np.asarray(potencia, dtype=np.float64)
    valido = np.isfinite(datos)
    numerador = np.where(valido, datos, 0.0)
    cuenta = valido.astype(np.float64)
    for eje in (0, 1):
        numerador = _boxcar_eje(numerador, ventana, eje)
        cuenta = _boxcar_eje(cuenta, ventana, eje)
    with np.errstate(invalid="ignore", divide="ignore"):
        salida = numerador / cuenta
    salida[cuenta <= 0] = np.nan
    return salida.astype(np.float32)


def ventana_para(mpp: float, metros: float = 90.0, tope: int = 9) -> int:
    """Ventana impar para que el multilook llegue a ~``metros`` de resolucion.

    Un indice de razon (RVI) calculado pixel a pixel es casi todo speckle: con
    ~90 m se ve la estructura del terreno y sigue siendo util para vegetacion.
    """
    if not np.isfinite(mpp) or mpp <= 0:
        return 1
    ventana = int(round(float(metros) / float(mpp)))
    ventana = max(1, min(tope, ventana))
    if ventana % 2 == 0:
        ventana = ventana + 1 if ventana < tope else ventana - 1
    return max(1, ventana)


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
    """Tamano de salida: el pedido, pero nunca mayor que el recorte nativo.

    Agrandar por encima del nativo no agrega detalle (y el speckle se estira):
    el detalle real es el pixel de la escena. El visor ya escala el PNG al mapa.
    """
    objetivo = max(1, min(int(px), 4096))
    ancho = max(1, int(ancho))
    alto = max(1, int(alto))
    lado = min(objetivo, max(ancho, alto))
    if ancho >= alto:
        return lado, max(1, round(lado * alto / ancho))
    return max(1, round(lado * ancho / alto)), lado


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


def _pie(img: Image.Image, lineas: list[str]) -> Image.Image:
    ancho, alto = img.size
    alto_pie = max(56, int(ancho * 0.068)) if len(lineas) >= 3 else max(44, int(ancho * 0.05))
    lienzo = Image.new("RGB", (ancho, alto + alto_pie), FONDO)
    lienzo.paste(img, (0, 0))
    dibujo = ImageDraw.Draw(lienzo)
    dibujo.line([(0, alto), (ancho, alto)], fill=(42, 44, 49), width=1)
    fuente1 = _fuente(max(12, int(ancho * 0.012)))
    fuente2 = _fuente(max(10, int(ancho * 0.009)))
    margen = max(10, int(ancho * 0.014))
    y = alto + max(8, int(ancho * 0.009))
    for indice, texto in enumerate(lineas[:3]):
        dibujo.text(
            (margen, y),
            texto,
            font=fuente1 if indice == 0 else fuente2,
            fill=TINTA if indice == 0 else TENUE,
        )
        y += max(16, int(ancho * 0.016))
    return lienzo


def _dibujar_focos(
    img: Image.Image,
    focos: list[tuple[float, float, tuple[int, int, int]]],
    epsg: int,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
) -> None:
    """Puntos FIRMS (lon, lat, color) sobre el mapa, con halo oscuro."""
    ancho, alto = img.size
    if x1 <= x0 or y1 <= y0:
        return
    transformador = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    dibujo = ImageDraw.Draw(img)
    radio = max(4, ancho // 220)
    for lon, lat, color in focos:
        x, y = transformador.transform(lon, lat)
        if not (np.isfinite(x) and np.isfinite(y)):
            continue
        px = (x - x0) / (x1 - x0) * (ancho - 1)
        py = (y1 - y) / (y1 - y0) * (alto - 1)
        if px < -radio or px > ancho + radio or py < -radio or py > alto + radio:
            continue
        dibujo.ellipse(
            [px - radio - 2, py - radio - 2, px + radio + 2, py + radio + 2],
            fill=(8, 9, 10),
        )
        dibujo.ellipse(
            [px - radio, py - radio, px + radio, py + radio],
            fill=tuple(int(c) for c in color),
        )


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
    focos: list[tuple[float, float, tuple[int, int, int]]] | None = None,
) -> tuple[int, int]:
    """Guarda un RGB (h,w,3) con escala, borde opcional y pie. Devuelve (W,H)."""
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    alto, ancho = rgb.shape[:2]
    ancho_salida, alto_salida = dimensiones(ancho, alto, px)
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")
    img = img.resize((ancho_salida, alto_salida), Image.LANCZOS)
    # La escala se dibuja sobre el PNG final: si hubo resize, los metros por
    # pixel de salida no son los del recorte nativo.
    mpp_salida = metros_por_px * ancho / max(1, ancho_salida)
    if metros_por_px > 0:
        _dibujar_escala(img, mpp_salida)
    if geojson and epsg is not None and None not in (x0, x1, y0, y1):
        _dibujar_borde(img, Path(geojson), epsg, float(x0), float(x1), float(y0), float(y1))
    if focos and epsg is not None and None not in (x0, x1, y0, y1):
        _dibujar_focos(
            img, focos, epsg, float(x0), float(x1), float(y0), float(y1)
        )
    img = _pie(img, lineas)
    img.save(salida, "PNG", optimize=True)
    return img.size


def guardar_json(salida: str | Path, meta: dict) -> None:
    ruta = Path(salida).with_suffix(".json")
    ruta.write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")


def guardar_geotiff(
    salida: str | Path,
    datos: np.ndarray,
    *,
    x0: float,
    y1: float,
    mpp_x: float,
    mpp_y: float,
    epsg: int,
    descripcion: str = "",
) -> None:
    """GeoTIFF de una banda float32 (norte arriba) con tags EPSG.

    Sin GDAL: `tifffile` escribe el raster y los tres tags que necesitan QGIS,
    ArcGIS y rasterio (pixel scale, tiepoint y GeoKeyDirectory). El tiepoint es
    la esquina superior izquierda del pixel (PixelIsArea).
    """
    import tifffile

    datos = np.asarray(datos, dtype=np.float32)
    claves = (
        1, 1, 0, 3,          # version, revision, minor, numero de claves
        1024, 0, 1, 1,       # GTModelTypeGeoKey = projected
        1025, 0, 1, 1,       # GTRasterTypeGeoKey = PixelIsArea
        3072, 0, 1, int(epsg),  # ProjectedCSTypeGeoKey
        3076, 0, 1, 9001,    # ProjLinearUnitsGeoKey = metro
    )
    extratags = [
        (33550, "d", 3, (float(mpp_x), float(mpp_y), 0.0), False),
        (33922, "d", 6, (0.0, 0.0, 0.0, float(x0), float(y1), 0.0), False),
        (34735, "H", len(claves), claves, False),
    ]
    ruta = Path(salida)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    # El tag TIFF solo acepta ASCII de 7 bits.
    descripcion = str(descripcion).encode("ascii", "replace").decode("ascii")
    tifffile.imwrite(
        ruta,
        datos,
        photometric="minisblack",
        compression="zlib",
        extratags=extratags,
        metadata=None,
        description=descripcion,
    )
