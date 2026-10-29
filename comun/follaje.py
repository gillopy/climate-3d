"""Índice de rojez del follaje (PACE/OCI LANDVI), compartido por póster y animación.

`rojez = mari ÷ cire`, es decir **antocianina sobre clorofila**. `mari` (Modified
Anthocyanin Reflectance Index) responde a las antocianinas —lo rojo— y `cire` (Chlorophyll
Index Red Edge) al contenido de clorofila de la copa —lo verde—. El cociente vale ~1 en
vegetación verde sin cambio y sube por encima de 2 donde el rojo domina: es la semántica y
la escala (`1.00-3.00`) de la leyenda "Relative Anthocyanin / Chlorophyll" de GLOBE / NASA
Earth Observatory.

Acá viven la paleta, las máscaras y la lectura de los gránulos, para que
`prototipos/poster_follaje.py` (imagen fija) y `cuadros/cuadros_follaje.py` (cuadros de la
animación) no puedan divergir. Sólo necesita `h5py` y numpy: no toca la red.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import h5py
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rutas import DATOS, SALIDAS  # noqa: E402

CRUDOS = DATOS / "pace_landvi"
CACHE = SALIDAS / "follaje_pace"

VERSION = "V3_1"                        # serie 3.1 de LANDVI
FILL = -32767.0

# --- máscaras y escala
NDVI_MIN = 0.25                         # debajo de esto no es dosel vegetal
CIRE_MIN = 0.2                          # evita cocientes inestables
VMIN, VMAX = 1.0, 3.0                   # escala de la leyenda de referencia

# --- vestuario
ROJEZ = LinearSegmentedColormap.from_list("rojez", [
    (0.00, "#0b6623"), (0.18, "#1f8a3b"), (0.38, "#7cc35a"),
    (0.52, "#d9e87a"), (0.64, "#f5e05a"), (0.76, "#f2b13c"),
    (0.86, "#e06a2a"), (0.94, "#b81f1f"), (1.00, "#7a0d12"),
])
ROJEZ.set_bad((0, 0, 0, 0))             # sin dato: deja ver el gris del continente

OCEANO = "#dbe8ef"
TIERRA = "#e8e6de"
COSTA = "#9aa3a8"
BORDE = "#c2c2bb"
TINTA = "#1c2227"
TINTA_SUAVE = "#5d666d"

MESES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def ruta_dia(dia: date, res: str = "4km") -> Path | None:
    """Gránulo del día, priorizando el procesado definitivo sobre el NRT."""
    for sufijo in ("", ".NRT"):
        p = CRUDOS / (f"PACE_OCI.{dia:%Y%m%d}.L3m.DAY.LANDVI.{VERSION}.{res}"
                      f"{sufijo}.nc")
        if p.exists():
            return p
    return None


def leer_dia(ruta: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """mARI, CIRE y NDVI del día, con el relleno pasado a NaN."""
    with h5py.File(ruta, "r") as f:
        mari = f["mari"][:].astype(np.float32)
        cire = f["cire"][:].astype(np.float32)
        ndvi = f["ndvi"][:].astype(np.float32)
    for a in (mari, cire, ndvi):
        a[a == FILL] = np.nan
    return mari, cire, ndvi


def eje(ruta: Path) -> tuple[np.ndarray, np.ndarray]:
    with h5py.File(ruta, "r") as f:
        return f["lat"][:].astype(np.float32), f["lon"][:].astype(np.float32)


def desde_sumas(suma: list[np.ndarray], cuenta: np.ndarray):
    """Convierte las sumas del compuesto en el cociente, aplicando las máscaras."""
    mari_m, cire_m, ndvi_m = (a / np.maximum(cuenta, 1) for a in suma)
    valido = (cuenta > 0) & (cire_m > CIRE_MIN) & (ndvi_m > NDVI_MIN)
    rojez = np.full(mari_m.shape, np.nan, dtype=np.float32)
    np.divide(mari_m, cire_m, out=rojez, where=valido)
    return rojez


def compuesto(desde: str, hasta: str, res: str = "4km", forzar: bool = False):
    """Compuesto de la ventana: promedio de los índices y después el cociente.

    Promediar los índices antes de dividir (en vez de promediar cocientes diarios)
    estabiliza el resultado y rellena mucho mejor los huecos de nubes de la ventana.
    Cachea en `SALIDAS/follaje_pace/rojez_<res>_<desde>_<hasta>.npz`.
    """
    d0, d1 = date.fromisoformat(desde), date.fromisoformat(hasta)
    dias = [d0 + timedelta(days=i) for i in range((d1 - d0).days + 1)]
    CACHE.mkdir(parents=True, exist_ok=True)
    npz = CACHE / f"rojez_{res}_{desde}_{hasta}.npz"
    # Los compuestos viejos se guardaban sin la resolución en el nombre: se migran.
    legado = CACHE / f"rojez_{desde}_{hasta}.npz"
    if res == "4km" and not npz.exists() and legado.exists():
        legado.replace(npz)
    if npz.exists() and not forzar:
        z = np.load(npz)
        return z["rojez"], z["lat"], z["lon"]

    suma = None
    cuenta = None
    lat = lon = None
    for d in dias:
        ruta = ruta_dia(d, res)
        if ruta is None:
            print(f"  ! falta el gránulo {d}")
            continue
        print(f"  + {ruta.name}")
        mari, cire, ndvi = leer_dia(ruta)
        if suma is None:
            suma = [np.zeros(mari.shape, np.float32) for _ in range(3)]
            cuenta = np.zeros(mari.shape, np.int16)
            lat, lon = eje(ruta)
        ok = np.isfinite(mari) & np.isfinite(cire) & np.isfinite(ndvi)
        for acumulado, capa in zip(suma, (mari, cire, ndvi)):
            acumulado[ok] += capa[ok]
        cuenta[ok] += 1
        del mari, cire, ndvi

    if suma is None:
        raise SystemExit(f"No hay gránulos para {desde} -> {hasta} ({res})")
    rojez = desde_sumas(suma, cuenta)
    del suma
    np.savez_compressed(npz, rojez=rojez, lat=lat, lon=lon)
    print(f"  = compuesto en {npz}")
    return rojez, lat, lon


def _sumar(suma: list[np.ndarray], cuenta: np.ndarray, ruta: Path, signo: int) -> None:
    """Suma (o resta) un día al compuesto, sólo donde hay dato en los tres índices."""
    mari, cire, ndvi = leer_dia(ruta)
    ok = np.isfinite(mari) & np.isfinite(cire) & np.isfinite(ndvi)
    for acumulado, capa in zip(suma, (mari, cire, ndvi)):
        acumulado[ok] += signo * capa[ok]
    cuenta[ok] += signo
    del mari, cire, ndvi


def dias_moviles(desde: date, hasta: date, ventana: int = 7, res: str = "0p1deg") -> list[date]:
    """Fechas de cuadro con la ventana completa: recorta el arranque si falta dato.

    La descarga puede empezar en `desde`, pero el primer cuadro necesita `ventana - 1`
    días **anteriores**; sin este recorte el primer compuesto saldría incompleto (o
    directo con un `None`).
    """
    dias = [desde + timedelta(days=i) for i in range((hasta - desde).days + 1)]
    for i, dia in enumerate(dias):
        if all(ruta_dia(dia - timedelta(days=k), res) is not None for k in range(ventana)):
            return dias[i:]
    raise SystemExit(f"No hay {ventana} días consecutivos con dato entre {desde} y {hasta}")


def movil(dias: list[date], ventana: int = 7, res: str = "0p1deg"):
    """Generador de compuestos móviles: `(fecha_fin, rojez, lat, lon)`.

    Cada cuadro es el compuesto de los `ventana` días que terminan en `fecha_fin`. Un día
    suelto de LANDVI tiene demasiados huecos de nubes; el compuesto móvil los rellena y
    deja ver la onda de rojo avanzando. La ventana se mantiene con sumas incrementales
    —entra el día nuevo, sale el que quedó afuera—, así que cada cuadro cuesta dos
    lecturas de gránulo y no `ventana`.
    """
    suma = cuenta = lat = lon = None
    for dia in dias:
        if suma is None:
            primer = dia - timedelta(days=ventana - 1)
            lat, lon = eje(ruta_dia(primer, res))
            mari, cire, ndvi = leer_dia(ruta_dia(primer, res))
            suma = [np.zeros(mari.shape, np.float32) for _ in range(3)]
            cuenta = np.zeros(mari.shape, np.int16)
            del mari, cire, ndvi
            for d in [primer + timedelta(days=k) for k in range(ventana)]:
                _sumar(suma, cuenta, ruta_dia(d, res), +1)
        else:
            _sumar(suma, cuenta, ruta_dia(dia, res), +1)
            viejo = ruta_dia(dia - timedelta(days=ventana), res)
            if viejo is not None:
                _sumar(suma, cuenta, viejo, -1)
        yield dia, desde_sumas(suma, cuenta), lat, lon


def fecha_larga(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{MESES[d.month - 1]} {d.day}, {d.year}"


def rango_corto(desde: str, hasta: str) -> str:
    """'Sep 29 - Oct 4, 2026', con el mes repetido sólo si cambia."""
    d0, d1 = date.fromisoformat(desde), date.fromisoformat(hasta)
    ini = f"{MESES[d0.month - 1]} {d0.day}"
    if d0.month == d1.month:
        return f"{ini} - {d1.day}, {d1.year}"
    return f"{ini} - {MESES[d1.month - 1]} {d1.day}, {d1.year}"
