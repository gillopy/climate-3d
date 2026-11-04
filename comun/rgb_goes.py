"""Recetas RGB oficiales de GOES-R ABI: Dust, Air Mass y Fire Temperature.

Los rangos, gammas e inversiones están copiados de los quick guides oficiales:

  * Dust RGB      — https://www.star.nesdis.noaa.gov/goes/documents/QuickGuide_Dust_RGB.pdf
  * Air Mass RGB  — https://rammb.cira.colostate.edu/training/visit/quick_guides/
                    QuickGuide_GOESR_AirMassRGB_final.pdf
  * Fire Temp RGB — https://www.star.nesdis.noaa.gov/goes/documents/
                    QuickGuide_Fire_Temperature_RGB.pdf

Un producto RGB **no** es una banda con paleta: son tres canales que se mezclan.
La receta ES la paleta del producto, así que no hay LUT que ofrecer aparte.

Unidades: `comun/goes_lectura.cargar` entrega °C en las bandas térmicas (C07-C16) y
% en las reflectivas (C01-C06). Una diferencia de temperatura en °C es la misma
diferencia en K, así que los rangos de los quick guides entran tal cual.
"""
from __future__ import annotations

import numpy as np

#: Canales en el orden en que se mezclan.
CANALES = ("R", "G", "B")

#: Cada canal: `banda` (o `banda` menos `resta`), rango físico, gamma e inversión.
#: `gamma > 1` aclara los medios (norm ** 1/gamma); `gamma < 1` los oscurece.
RECETAS: dict[str, dict] = {
    "dust": {
        "nombre": "Dust RGB",
        "bandas": ("C11", "C13", "C14", "C15"),
        "canales": [
            {"banda": "C15", "resta": "C13", "vmin": -6.7, "vmax": 2.6,
             "gamma": 1.0, "invertir": False},
            {"banda": "C14", "resta": "C11", "vmin": -0.5, "vmax": 20.0,
             "gamma": 2.5, "invertir": False},
            {"banda": "C13", "resta": None, "vmin": -11.95, "vmax": 15.55,
             "gamma": 1.0, "invertir": False},
        ],
        "resumen": "Polvo en magenta/rosa (de noche, violeta bajo 3 km); nubes de agua "
                   "violeta claro; desierto de día celeste; nubes medias gruesas tan; "
                   "finas verdes; frías gruesas rojas; cirrus finos negros.",
    },
    "airmass": {
        "nombre": "Air Mass RGB",
        "bandas": ("C08", "C10", "C12", "C13"),
        "canales": [
            {"banda": "C08", "resta": "C10", "vmin": -26.2, "vmax": 0.6,
             "gamma": 1.0, "invertir": False},
            {"banda": "C12", "resta": "C13", "vmin": -43.2, "vmax": 6.7,
             "gamma": 1.0, "invertir": False},
            # 6.2 µm invertida: tope frío -> azul brillante; aire seco cálido -> oscuro.
            {"banda": "C08", "resta": None, "vmin": -64.65, "vmax": -29.25,
             "gamma": 1.0, "invertir": True},
        ],
        "resumen": "Aire polar azul/violeta oscuro; tropical verde; seco y cálido "
                   "oliva/naranja; nubes altas gruesas blancas; medias tan/salmón; "
                   "bajas verdes/azul oscuro.",
    },
    "firetemp": {
        "nombre": "Fire Temperature RGB",
        "bandas": ("C05", "C06", "C07"),
        "canales": [
            {"banda": "C07", "resta": None, "vmin": 0.0, "vmax": 60.0,
             "gamma": 0.4, "invertir": False},
            {"banda": "C06", "resta": None, "vmin": 0.0, "vmax": 100.0,
             "gamma": 1.0, "invertir": False},
            {"banda": "C05", "resta": None, "vmin": 0.0, "vmax": 75.0,
             "gamma": 1.0, "invertir": False},
        ],
        "resumen": "Fuego tibio rojo; muy tibio naranja; caliente amarillo; muy caliente "
                   "casi blanco; cicatrices de quema marrón; cielo claro púrpura/rosa; "
                   "agua/nieve/noche casi negro; nubes de agua azules; de hielo verdes.",
    },
}

PRODUCTOS = tuple(RECETAS)


def etiqueta_canal(canal: dict) -> str:
    """Texto corto del canal: `C15-C13` o `C07`."""
    if canal.get("resta"):
        return f"{canal['banda']}-{canal['resta']}"
    return str(canal["banda"])


def bandas(producto: str) -> tuple[str, ...]:
    """Bandas ABI que hay que descargar para el producto."""
    return tuple(RECETAS[producto]["bandas"])


def normalizar(valores: np.ndarray, canal: dict) -> np.ndarray:
    """Rango físico -> 0..1, con gamma e inversión del quick guide."""
    span = float(canal["vmax"]) - float(canal["vmin"])
    norma = np.clip((valores - float(canal["vmin"])) / span, 0.0, 1.0)
    if canal.get("invertir"):
        norma = 1.0 - norma
    gamma = float(canal.get("gamma", 1.0))
    if gamma != 1.0:
        norma = np.power(norma, 1.0 / gamma)
    return norma


def componer_rgb(campos: dict[str, np.ndarray], producto: str) -> tuple[np.ndarray, np.ndarray]:
    """Mezcla los canales de la receta.

    `campos` es `{banda: array}` con las bandas de `bandas(producto)`.
    Devuelve `(rgb uint8 (h, w, 3), valido bool (h, w))`: un píxel es válido sólo
    si TODOS los canales tienen dato; fuera de ahí el RGB queda en negro.
    """
    receta = RECETAS[producto]
    canales: list[np.ndarray] = []
    valido: np.ndarray | None = None
    for canal in receta["canales"]:
        base = campos[canal["banda"]]
        resta = canal.get("resta")
        valores = base - campos[resta] if resta else base
        ok = np.isfinite(valores)
        valido = ok if valido is None else (valido & ok)
        # Donde no hay dato se normaliza el mínimo (0) y después se enmascara.
        canales.append(normalizar(np.where(ok, valores, canal["vmin"]), canal))

    mezcla = np.stack(canales, axis=-1)
    mezcla = np.where(valido[..., None], mezcla, 0.0)
    rgb = np.clip(np.rint(mezcla * 255.0), 0, 255).astype(np.uint8)
    return rgb, valido  # type: ignore[return-value]
