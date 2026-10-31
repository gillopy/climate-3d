"""Catalogo de productos: los flujos que ya existen, descritos como datos.

Es la unica pieza que sabe que hay un flujo detras de cada boton. Copia los
nombres reales de ``docs/FLUJOS.md`` para que la demo sea reconocible; no ejecuta
nada por si misma.

``command`` queda en ``None`` a proposito: conectar el script real es una linea
por producto y hay que hacerlo con los flags que cada script realmente acepta.
Inventarlos aca seria mentirle a la UI.
"""
from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path

from .schemas import ParamOption, ParamSpec, Product

# Raiz del repo (app/api/catalog.py -> app/api -> app -> raiz).
RAIZ_REPO = Path(__file__).resolve().parents[2]

_ESTILOS = [
    ParamOption(value="realista", label="Realista (poster ECMWF)"),
    ParamOption(value="gibs", label="GIBS Clean Infrared"),
    ParamOption(value="crudo", label="Crudo (sin retoque)"),
]

_RESOLUCIONES = [
    ParamOption(value="800", label="800 px"),
    ParamOption(value="1400", label="1400 px (poster)"),
    ParamOption(value="2000", label="2000 px (impresion)"),
]


def _rango(fin_dias_atras: int = 10) -> dict[str, str]:
    """Rango de fechas por defecto, relativo a hoy."""
    fin = date.today() - timedelta(days=fin_dias_atras)
    inicio = fin - timedelta(days=1)
    return {"start": inicio.isoformat(), "end": fin.isoformat()}


PRODUCTS: list[Product] = [
    Product(
        id="goes_c13",
        name="GOES - C13 infrarrojo",
        group="satelite",
        stage="cuadros/cuadros_c13_ir.py",
        summary="Globo del IR limpio (10.3 um) con el recorte de Paraguay al centro.",
        params=[
            ParamSpec(
                name="satelite",
                label="Satelite",
                kind="select",
                default="G19",
                options=[
                    ParamOption(value="G19", label="GOES-East G19 (75.2 W)"),
                    ParamOption(value="G18", label="GOES-West G18 (137 W)"),
                    ParamOption(value="G16", label="GOES-East G16 (retirado)"),
                ],
                help="GOES-East cubre Sudamerica completo.",
            ),
            ParamSpec(
                name="banda",
                label="Banda",
                kind="select",
                default="C13",
                options=[
                    ParamOption(value="C13", label="C13 - 10.3 um (IR limpio)"),
                    ParamOption(value="C02", label="C02 - 0.64 um (visible, solo de dia)"),
                    ParamOption(value="C04", label="C04 - 1.38 um (cirrus)"),
                ],
            ),
            ParamSpec(name="ventana", label="Ventana temporal", kind="date-range", default=_rango()),
            ParamSpec(name="estilo", label="Estilo", kind="select", default="realista", options=_ESTILOS),
            ParamSpec(name="resolucion", label="Resolucion", kind="select", default="1400", options=_RESOLUCIONES),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=True),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider", default=12, min=6, max=30, step=2),
        ],
    ),
    Product(
        id="mur_sst",
        name="MUR - temperatura del mar",
        group="satelite",
        stage="cuadros/cuadros_mur.py",
        summary="SST diaria de 1 km sobre globo, con paleta de contraste.",
        params=[
            ParamSpec(name="fecha", label="Fecha", kind="date-range", default=_rango(30)),
            ParamSpec(name="estilo", label="Estilo", kind="select", default="realista", options=_ESTILOS),
            ParamSpec(name="resolucion", label="Resolucion", kind="select", default="1400", options=_RESOLUCIONES),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=True),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider", default=12, min=6, max=30, step=2),
        ],
    ),
    Product(
        id="precipitacion_ecmwf",
        name="ECMWF - precipitacion",
        group="modelo",
        stage="cuadros/cuadros_precipitacion.py",
        summary="Pronostico de precipitacion acumulada por horizonte de 6 h.",
        params=[
            ParamSpec(
                name="modelo",
                label="Modelo",
                kind="select",
                default="ifs",
                options=[
                    ParamOption(value="ifs", label="IFS deterministico"),
                    ParamOption(value="aifs-ens", label="AIFS ensemble"),
                    ParamOption(value="aifs-single", label="AIFS single"),
                ],
            ),
            ParamSpec(
                name="corrida",
                label="Corrida",
                kind="select",
                default="00",
                options=[ParamOption(value=v, label=f"{v}z") for v in ("00", "06", "12", "18")],
            ),
            ParamSpec(
                name="horizonte",
                label="Horizonte (h)",
                kind="slider",
                default=144,
                min=0,
                max=240,
                step=6,
                help="A cuantas horas del analisis mirar.",
            ),
            ParamSpec(name="estilo", label="Estilo", kind="select", default="realista", options=_ESTILOS),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=True),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider", default=12, min=6, max=30, step=2),
        ],
    ),
    Product(
        id="anomalia_2t",
        name="ECMWF - anomalia de 2 m",
        group="modelo",
        stage="cuadros/cuadros_anomalia_2t.py",
        summary="Anomalia mensual de temperatura a 2 m contra la climatologia.",
        params=[
            ParamSpec(
                name="modelo",
                label="Modelo",
                kind="select",
                default="ifs",
                options=[
                    ParamOption(value="ifs", label="IFS deterministico"),
                    ParamOption(value="aifs-single", label="AIFS single"),
                ],
            ),
            ParamSpec(name="ventana", label="Meses", kind="date-range", default=_rango(60)),
            ParamSpec(name="estilo", label="Estilo", kind="select", default="realista", options=_ESTILOS),
            ParamSpec(name="resolucion", label="Resolucion", kind="select", default="1400", options=_RESOLUCIONES),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=True),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider", default=10, min=6, max=30, step=2),
        ],
    ),
    Product(
        id="follaje",
        name="PACE - follaje (LANDVI)",
        group="satelite",
        stage="cuadros/cuadros_follaje.py",
        summary="Indice de vegetacion de PACE sobre globo, con paleta de estaciones.",
        params=[
            ParamSpec(name="fecha", label="Fecha", kind="date-range", default=_rango(20)),
            ParamSpec(name="estilo", label="Estilo", kind="select", default="gibs", options=_ESTILOS),
            ParamSpec(name="resolucion", label="Resolucion", kind="select", default="1400", options=_RESOLUCIONES),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=True),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider", default=12, min=6, max=30, step=2),
        ],
    ),
]

_BY_ID = {p.id: p for p in PRODUCTS}


def get_product(product_id: str) -> Product | None:
    return _BY_ID.get(product_id)


def data_root() -> Path:
    """Misma regla que ``comun/rutas.py``: una sola variable de entorno."""
    return Path(os.environ.get("CLIMATE3D_DATOS") or r"D:\Users\guill\dataset era5")


def data_root_exists() -> bool:
    return data_root().is_dir()


def available_dates(product: Product, dias: int = 30) -> tuple[str, list[str]]:
    """Fechas que el usuario puede elegir.

    Si el disco tiene salidas reales del producto, se listan esas. Si no, se
    devuelve un calendario de demostracion y la UI lo dice explicitamente: un
    date-picker vacio es peor que uno honesto.
    """
    salidas = data_root() / "salidas"
    encontradas: set[str] = set()
    if salidas.is_dir():
        prefijo = product.id.split("_")[0]
        for path in salidas.glob(f"**/*{prefijo}*"):
            for chunk in path.stem.replace("T", "-").split("-"):
                if len(chunk) == 8 and chunk.isdigit():
                    encontradas.add(f"{chunk[:4]}-{chunk[4:6]}-{chunk[6:]}")
    if encontradas:
        return "descubierto", sorted(encontradas, reverse=True)[:90]

    hoy = date.today()
    demo = [(hoy - timedelta(days=i)).isoformat() for i in range(dias)]
    return "demo", demo
