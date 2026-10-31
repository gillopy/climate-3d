"""Catalogo de productos: los flujos reales del repo, descritos como datos.

Cada producto declara **solo** los controles que su script realmente acepta.
Si un render no expone paleta, el catalogo no muestra un selector de paleta: un
boton que no hace nada es peor que un boton ausente.
"""
from __future__ import annotations

import os
import re
from datetime import date, timedelta
from pathlib import Path

from .recipes import repo_listo
from .schemas import ParamOption, ParamSpec, Product

RAIZ_REPO = Path(__file__).resolve().parents[2]

_PALETAS = [
    ParamOption(value="clean_ir", label="clean_ir - Clean Infrared (GIBS)"),
    ParamOption(value="ir_realce", label="ir_realce - IR con realce"),
    ParamOption(value="termico", label="termico - gris termico"),
    ParamOption(value="gris", label="gris - reflectancia"),
    ParamOption(value="anomalia", label="anomalia - paleta de anomalia"),
    ParamOption(value="magma", label="magma"),
    ParamOption(value="inferno", label="inferno"),
]

_RESOLUCIONES = [
    ParamOption(value="1400", label="1400 px (poster)"),
    ParamOption(value="2000", label="2000 px"),
    ParamOption(value="2712", label="2712 px (nativo del disco)"),
]

_FONDO = [
    ParamOption(value="oscuro", label="Fondo oscuro"),
    ParamOption(value="claro", label="Fondo claro"),
]


def _rango(dias_atras: int = 2) -> dict[str, str]:
    fin = date.today() - timedelta(days=dias_atras)
    return {"start": (fin - timedelta(days=1)).isoformat(), "end": fin.isoformat()}


PRODUCTS: list[Product] = [
    Product(
        id="goes_c13",
        name="GOES - disco ABI",
        group="satelite",
        stage="descargar/descargar_goes.py + cuadros/cuadros_goes.py",
        summary="Banda ABI. Por defecto, el disco completo en la proyeccion nativa "
        "en que lo capto el satelite; opcionalmente, globo centrado en el.",
        params=[
            ParamSpec(
                name="satelite",
                label="Satelite",
                kind="select",
                default="G19",
                options=[
                    ParamOption(value="G19", label="GOES-East G19 (75.2 W)"),
                    ParamOption(value="G18", label="GOES-West G18 (137.2 W)"),
                    ParamOption(value="G16", label="GOES-East G16 (retirado)"),
                ],
                help="define la carpeta de datos goes_<banda>_<sat>",
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
            ParamSpec(name="paleta", label="Paleta", kind="select", default="clean_ir", options=_PALETAS),
            ParamSpec(
                name="globo",
                label="Reproyectar a globo 3D",
                kind="toggle",
                default=False,
                help="apagado = disco nativo del satelite; encendido = globo centrado en su punto subsatelite",
            ),
            ParamSpec(name="ventana", label="Ventana temporal", kind="date-range", default=_rango()),
            ParamSpec(name="resolucion", label="Resolucion", kind="select", default="1400", options=_RESOLUCIONES),
            ParamSpec(
                name="descargar",
                label="Forzar descarga",
                kind="toggle",
                default=False,
                help="si la fecha no tiene datos en disco se descarga igual; esto baja los .nc aunque ya existan",
            ),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=True),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider", default=12, min=4, max=30, step=2),
        ],
    ),
    Product(
        id="mur_sst",
        name="MUR - temperatura del mar",
        group="satelite",
        stage="descargar/mur_sst.py + cuadros/cuadros_mur.py",
        summary="SST diaria de 1 km: GIBS entrega el cuadro ya coloreado y aca se compone el globo.",
        params=[
            ParamSpec(name="ventana", label="Ventana temporal", kind="date-range", default=_rango(30)),
            ParamSpec(
                name="resolucion",
                label="Resolucion",
                kind="select",
                default="1400",
                options=[
                    ParamOption(value="1200", label="1200 px"),
                    ParamOption(value="2000", label="2000 px"),
                    ParamOption(value="2712", label="2712 px"),
                ],
            ),
            ParamSpec(name="descargar", label="Bajar los cuadros de GIBS", kind="toggle", default=False),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=True),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider", default=12, min=4, max=30, step=2),
        ],
    ),
    Product(
        id="precipitacion_ecmwf",
        name="ECMWF - precipitacion",
        group="modelo",
        stage="descargar/precipitacion_ecmwf.py + cuadros/cuadros_precipitacion.py",
        summary="Precipitacion acumulada por horizonte de 6 h sobre globo.",
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
            ParamSpec(name="fecha", label="Fecha de la corrida", kind="date", default=date.today().isoformat()),
            ParamSpec(
                name="corrida",
                label="Ciclo",
                kind="select",
                default="00",
                options=[ParamOption(value=v, label=f"{v}z") for v in ("00", "06", "12", "18")],
            ),
            ParamSpec(name="horizonte", label="Horizonte (h)", kind="slider", default=144, min=6, max=240, step=6),
            ParamSpec(name="fondo", label="Fondo del globo", kind="select", default="oscuro", options=_FONDO),
            ParamSpec(name="resolucion", label="Resolucion", kind="select", default="1400", options=_RESOLUCIONES),
            ParamSpec(name="descargar", label="Bajar los crudos de ECMWF", kind="toggle", default=False),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=True),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider", default=12, min=4, max=30, step=2),
        ],
    ),
    Product(
        id="anomalia_2t",
        name="ECMWF - anomalia de 2 m",
        group="modelo",
        stage="descargar/anomalia_2t_ecmwf.py + cuadros/cuadros_anomalia_2t.py",
        summary="Anomalia de temperatura a 2 m contra la climatologia horaria de ERA5.",
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
            ParamSpec(name="fecha", label="Fecha de la corrida", kind="date", default=date.today().isoformat()),
            ParamSpec(
                name="corrida",
                label="Ciclo",
                kind="select",
                default="12",
                options=[ParamOption(value=v, label=f"{v}z") for v in ("00", "06", "12", "18")],
            ),
            ParamSpec(name="horizonte", label="Horizonte (h)", kind="slider", default=144, min=6, max=240, step=6),
            ParamSpec(name="fondo", label="Fondo del globo", kind="select", default="oscuro", options=_FONDO),
            ParamSpec(name="resolucion", label="Resolucion", kind="select", default="1400", options=_RESOLUCIONES),
            ParamSpec(name="descargar", label="Bajar los crudos de ECMWF", kind="toggle", default=False),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=True),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider", default=12, min=4, max=30, step=2),
        ],
    ),
    Product(
        id="follaje",
        name="PACE - follaje (LANDVI)",
        group="satelite",
        stage="descargar/pace_landvi.py + cuadros/cuadros_follaje.py",
        summary="Indice de vegetacion de PACE sobre fondo de poster, ventana por dias.",
        params=[
            ParamSpec(name="ventana", label="Ventana temporal", kind="date-range", default=_rango(20)),
            ParamSpec(name="resolucion", label="Resolucion", kind="select", default="1400", options=_RESOLUCIONES),
            ParamSpec(
                name="descargar",
                label="Bajar LANDVI (Earthdata)",
                kind="toggle",
                default=False,
                help="necesita credenciales de NASA Earthdata configuradas",
            ),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=True),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider", default=12, min=4, max=30, step=2),
        ],
    ),
]

_BY_ID = {p.id: p for p in PRODUCTS}


def get_product(product_id: str) -> Product | None:
    return _BY_ID.get(product_id)


def productos_disponibles() -> list[Product]:
    """Marca cada producto segun si el entorno real esta listo."""
    listo = repo_listo()
    return [p.model_copy(update={"command_ready": listo}) for p in PRODUCTS]


def data_root() -> Path:
    """Misma regla que ``comun/rutas.py``: una sola variable de entorno."""
    return Path(os.environ.get("CLIMATE3D_DATOS") or r"D:\Users\guill\dataset era5")


def data_root_exists() -> bool:
    return data_root().is_dir()


# --- fechas disponibles -------------------------------------------------
_FECHA_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_DIA_GOES = re.compile(r"_s(\d{4})(\d{3})")

_CARPETAS_GOES = {
    ("G19", "C13"): "goes_c13_g19",
    ("G19", "C02"): "goes_c02_g19",
    ("G19", "C04"): "goes_c04_g19",
    ("G18", "C13"): "goes_c13_g18",
    ("G16", "C13"): "goes_c13_g16",
}


def _fechas_de_nombres(nombres: list[str], patron: re.Pattern[str]) -> set[str]:
    encontradas: set[str] = set()
    for nombre in nombres:
        for match in patron.finditer(nombre):
            try:
                if patron is _DIA_GOES:
                    encontradas.add(date.fromordinal(
                        date(int(match.group(1)), 1, 1).toordinal() + int(match.group(2)) - 1
                    ).isoformat())
                else:
                    encontradas.add(f"{match.group(1)}-{match.group(2)}-{match.group(3)}")
            except ValueError:
                continue
    return encontradas


def available_dates(product: Product, params: dict | None = None) -> tuple[str, list[str]]:
    """Fechas que el usuario deberia poder elegir.

    Se busca, en orden: los datos crudos del producto y las salidas ya hechas.
    Si no hay nada, se devuelve un calendario de demostracion y la UI lo dice.
    """
    params = params or {}
    encontradas: set[str] = set()
    raiz = data_root()

    if product.id == "goes_c13":
        carpeta = _CARPETAS_GOES.get(
            (str(params.get("satelite", "G19")), str(params.get("banda", "C13"))),
            "goes_c13_g19",
        )
        datos = raiz / carpeta
        if datos.is_dir():
            encontradas |= _fechas_de_nombres([f.name for f in datos.glob("*.nc")], _DIA_GOES)

    if product.id == "follaje":
        datos = raiz / "pace_landvi"
        if datos.is_dir():
            encontradas |= _fechas_de_nombres([f.name for f in datos.iterdir()], _FECHA_ISO)

    salidas = raiz / "salidas"
    if salidas.is_dir():
        prefijo = {
            "goes_c13": "frames_G",
            "mur_sst": "frames_mur",
            "precipitacion_ecmwf": "frames_precipitacion",
            "anomalia_2t": "frames_anomalia",
            "follaje": "frames_follaje",
        }.get(product.id, "")
        if prefijo:
            for carpeta in salidas.glob(f"{prefijo}*"):
                encontradas |= _fechas_de_nombres([carpeta.name], _FECHA_ISO)

    if encontradas:
        return "descubierto", sorted(encontradas, reverse=True)[:180]

    hoy = date.today()
    return "demo", [(hoy - timedelta(days=i)).isoformat() for i in range(30)]
