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
        name="GOES - IR en globo (C13)",
        group="satelite",
        stage="descargar/descargar_goes.py + cuadros/cuadros_c13_ir.py",
        summary="Disco completo en globo, centrado en el punto subsatelital: entra el globo "
        "entero, sin recorte regional y sin perder el limbo.",
        params=[
            ParamSpec(
                name="satelite",
                label="Satelite",
                kind="select",
                default="G19",
                options=[
                    ParamOption(value="G19", label="GOES-East G19 (75.2 W)"),
                    ParamOption(value="G18", label="GOES-West G18 (137.2 W)"),
                    ParamOption(value="G16", label="GOES-East G16 (hasta 2025)"),
                ],
                help="define la carpeta de datos goes_c13_<sat>",
            ),
            ParamSpec(name="ventana", label="Ventana temporal", kind="date-range", default=_rango()),
            ParamSpec(
                name="paleta",
                label="Paleta",
                kind="select",
                default="clean_ir",
                options=_PALETAS,
                help="clean_ir es la del modulo comun/paleta_gibs.py",
            ),
            ParamSpec(name="resolucion", label="Resolucion", kind="select", default="1400", options=_RESOLUCIONES),
            ParamSpec(
                name="descargar",
                label="Forzar descarga",
                kind="toggle",
                default=False,
                help="si la fecha no tiene datos en disco se descarga igual; esto baja los .nc aunque ya existan",
            ),
            ParamSpec(
                name="hora_desde",
                label="Desde (hora local UTC-3)",
                kind="slider",
                default=0,
                min=0,
                max=23,
                step=1,
                help="solo al animar: 0 a 24 son los 144 cuadros del dia, cada 10 min",
            ),
            ParamSpec(
                name="hora_hasta",
                label="Hasta (hora local UTC-3)",
                kind="slider",
                default=24,
                min=1,
                max=24,
                step=1,
                help="fin exclusivo: 24 cierra el dia completo",
            ),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=False),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider", default=12, min=4, max=30, step=2),
        ],
    ),
    Product(
        id="goes_truecolor",
        name="GOES - color real (3 bandas)",
        group="satelite",
        stage="descargar/truecolor_goes.py + prototipos/poster_goes_truecolor.py",
        summary="C01 + C02 + C03 sintetizadas con la receta CIMSS: color real de dia. "
        "Globo orthographic o disco nativo sin reproyectar.",
        params=[
            ParamSpec(
                name="satelite",
                label="Satelite",
                kind="select",
                default="G19",
                options=[
                    ParamOption(value="G19", label="GOES-East G19 (75.2 W)"),
                    ParamOption(value="G18", label="GOES-West G18 (137.2 W)"),
                    ParamOption(value="G16", label="GOES-East G16 (hasta 2025)"),
                ],
            ),
            ParamSpec(
                name="encuadre",
                label="Encuadre",
                kind="select",
                default="globo",
                options=[
                    ParamOption(value="globo", label="Globo orthographic"),
                    ParamOption(value="disco", label="Disco nativo (sin reproyectar)"),
                ],
                help="el disco nativo es la perspectiva geoestacionaria real, sin perder el limbo",
            ),
            ParamSpec(
                name="limbo",
                label="Limbo",
                kind="select",
                default="completo",
                options=[
                    ParamOption(value="completo", label="Completo: todo el disco captado"),
                    ParamOption(value="recortado", label="Recortado: sin la franja estirada"),
                ],
                help="el script recorta por defecto hasta 73.3 grados; el limite real del satelite es 81.3",
            ),
            ParamSpec(
                name="nitidez",
                label="Nitidez",
                kind="select",
                default="maxima",
                options=[
                    ParamOption(value="maxima", label="Maxima: sin mediana ni desenfoque"),
                    ParamOption(value="suave", label="Suave: mediana 3x3 y desenfoque 0.8 px"),
                ],
                help="el suavizado limpia el moteado del limbo pero borronea las nubes",
            ),
            ParamSpec(name="ventana", label="Ventana temporal", kind="date-range", default=_rango()),
            ParamSpec(
                name="resolucion",
                label="Resolucion",
                kind="select",
                default="2712",
                options=_RESOLUCIONES,
                help="2712 px es la resolucion del disco nativo: por debajo se pierde detalle",
            ),
            ParamSpec(
                name="descargar",
                label="Forzar descarga",
                kind="toggle",
                default=False,
                help="cada slot son tres bandas (~500 MB); sin forzar usa lo que ya esta en disco",
            ),
            ParamSpec(
                name="hora_desde",
                label="Desde (hora local UTC-3)",
                kind="slider",
                default=0,
                min=0,
                max=23,
                step=1,
                help="solo al animar: 0 a 24 son los 144 cuadros del dia, cada 10 min",
            ),
            ParamSpec(
                name="hora_hasta",
                label="Hasta (hora local UTC-3)",
                kind="slider",
                default=24,
                min=1,
                max=24,
                step=1,
                help="fin exclusivo: 24 cierra el dia completo",
            ),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=False),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider", default=8, min=4, max=30, step=2),
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
            ParamSpec(name="animar", label="Animar", kind="toggle", default=False),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider", default=12, min=4, max=30, step=2),
        ],
    ),
    Product(
        id="mur_realista",
        name="MUR - SST poster realista",
        group="satelite",
        stage="descargar/mur_sst.py + prototipos/poster_mur_realista.py",
        summary="Fondo blanco, globo inscripto y campana de distribucion: el diseno de "
        "poster del repo, no el globo oscuro.",
        params=[
            ParamSpec(name="ventana", label="Ventana temporal", kind="date-range", default=_rango(30)),
            ParamSpec(
                name="resolucion",
                label="Resolucion",
                kind="select",
                default="2000",
                options=[
                    ParamOption(value="1400", label="1400 px"),
                    ParamOption(value="2000", label="2000 px"),
                    ParamOption(value="2711", label="2711 px (poster)"),
                ],
            ),
            ParamSpec(
                name="paleta",
                label="Paleta",
                kind="select",
                default="realista",
                options=[
                    ParamOption(value="realista", label="realista (Earth Observatory)"),
                    ParamOption(value="gibs", label="gibs (SST oficial)"),
                ],
            ),
            ParamSpec(name="trend", label="Mostrar tendencia", kind="toggle", default=False),
            ParamSpec(
                name="descargar",
                label="Forzar descarga",
                kind="toggle",
                default=False,
                help="baja la serie semanal de GIBS si no esta en cache",
            ),
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
            ParamSpec(name="fondo", label="Fondo del globo", kind="select", default="claro", options=_FONDO),
            ParamSpec(name="resolucion", label="Resolucion", kind="select", default="1400", options=_RESOLUCIONES),
            ParamSpec(name="descargar", label="Bajar los crudos de ECMWF", kind="toggle", default=False),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=False),
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
            ParamSpec(name="fondo", label="Fondo del globo", kind="select", default="claro", options=_FONDO),
            ParamSpec(name="resolucion", label="Resolucion", kind="select", default="1400", options=_RESOLUCIONES),
            ParamSpec(name="descargar", label="Bajar los crudos de ECMWF", kind="toggle", default=False),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=False),
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
            ParamSpec(name="animar", label="Animar", kind="toggle", default=False),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider", default=12, min=4, max=30, step=2),
        ],
    ),
]

_BY_ID = {p.id: p for p in PRODUCTS}


def get_product(product_id: str) -> Product | None:
    return _BY_ID.get(product_id)


def productos_disponibles() -> list[Product]:
    """Marca cada producto segun si el entorno real esta listo y si hay muestra."""
    listo = repo_listo()
    muestras = RAIZ_REPO / "app" / "web" / "public" / "previews"
    salida: list[Product] = []
    for producto in PRODUCTS:
        webp = muestras / f"{producto.id}.webp"
        salida.append(
            producto.model_copy(
                update={
                    "command_ready": listo,
                    "preview": f"/previews/{producto.id}.webp" if webp.is_file() else None,
                }
            )
        )
    return salida


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

    if product.id in ("goes_c13", "goes_truecolor"):
        banda = "C02" if product.id == "goes_truecolor" else str(params.get("banda", "C13"))
        carpeta = _CARPETAS_GOES.get(
            (str(params.get("satelite", "G19")), banda),
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
            "goes_truecolor": "poster_G19_truecolor",
            "mur_sst": "frames_mur",
            "mur_realista": "frames_mur",
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

