"""Catalogo de productos: los flujos reales del repo, descritos como datos.

Cada producto declara **solo** los controles que su script realmente acepta.
Si un render no expone paleta, el catalogo no muestra un selector de paleta: un
boton que no hace nada es peor que un boton ausente.
"""
from __future__ import annotations

import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .recipes import repo_listo
from .schemas import ParamOption, ParamSpec, PreviewVariant, Product

RAIZ_REPO = Path(__file__).resolve().parents[2]

def _paleta(
    value: str, label: str, banda: str | list[str] | None = None
) -> ParamOption:
    """Paleta del catalogo; con `banda`, solo se ofrece con ese canal (o canales)."""
    if isinstance(banda, list):
        condicion: dict[str, object] | None = {"banda": list(banda)}
    elif banda:
        condicion = {"banda": banda}
    else:
        condicion = None
    return ParamOption(value=value, label=label, only_when=condicion)


# Paletas que no dependen del canal elegido: valen en cualquier banda.
_PALETAS_GENERICAS = [
    _paleta("termico", "termico - gris termico"),
    _paleta("gris", "gris - reflectancia"),
    _paleta("anomalia", "anomalia - paleta de anomalia"),
    _paleta("magma", "magma"),
    _paleta("inferno", "inferno"),
    _paleta("turbo", "turbo"),
]

# `goes_c13` siempre es C13: la rampa de GIBS no necesita condicion.
_PALETAS = [
    _paleta("clean_ir", "clean_ir - Clean Infrared (GIBS)"),
    *_PALETAS_GENERICAS,
]

# `goes_banda` cambia de canal: cada rampa oficial va atada a su banda y el
# resto sigue disponible siempre. El orden importa: al cambiar de banda la UI
# cae en la primera opcion visible, asi que primero van las de la banda y
# despues `gris`, que es la unica rampa que se lee bien en reflectancia (las
# visibles C01-C06 usan 0..1).
_PALETAS_BANDA = [
    _paleta(
        "reflectancia",
        "reflectancia - visible e infrarrojo cercano, negro a blanco (0 a 100 %)",
        ["C01", "C02", "C03", "C04", "C05", "C06"],
    ),
    _paleta("clean_ir", "clean_ir - Clean Infrared (GIBS), banda 13", "C13"),
    _paleta("c07_ir", "c07_ir - IR oficial GOES, banda 7 (3.9 um, -83 a 127 C)", "C07"),
    _paleta("c08_ir", "c08_ir - vapor de agua oficial GOES, banda 8 (6.2 um, -93 a 7 C)", "C08"),
    _paleta("c09_ir", "c09_ir - vapor de agua oficial GOES, banda 9 (6.9 um, -93 a 7 C)", "C09"),
    _paleta("c10_ir", "c10_ir - vapor de agua oficial GOES, banda 10 (7.3 um, -93 a 7 C)", "C10"),
    _paleta("c11_ir", "c11_ir - IR oficial GOES, banda 11 (8.5 um, -110 a 57 C)", "C11"),
    _paleta("c12_ir", "c12_ir - IR oficial GOES, banda 12 (9.6 um, -110 a 57 C)", "C12"),
    _paleta("c13_ir", "c13_ir - IR oficial GOES, banda 13 (10.3 um, -110 a 57 C)", "C13"),
    _paleta("c14_ir", "c14_ir - IR oficial GOES, banda 14 (11.2 um, -110 a 57 C)", "C14"),
    _paleta("c15_ir", "c15_ir - IR oficial GOES, banda 15 (12.3 um, -110 a 57 C)", "C15"),
    _paleta("c16_ir", "c16_ir - IR oficial GOES, banda 16 (13.3 um, -128 a 128 C)", "C16"),
    _paleta("gris", "gris - reflectancia"),
    *[opcion for opcion in _PALETAS_GENERICAS if opcion.value != "gris"],
]

# Las 16 bandas del ABI, con la lectura que les da NOAA STAR. Sirve para armar
# un producto por banda sin inventar escalas: la longitud de onda manda el tipo
# de dato (reflectancia en C01-C06, temperatura de brillo en C07-C16).
_BANDAS_ABI = [
    ParamOption(value="C01", label="C01 - 0.47 um (visible azul)"),
    ParamOption(value="C02", label="C02 - 0.64 um (visible rojo)"),
    ParamOption(value="C03", label="C03 - 0.86 um (veggie)"),
    ParamOption(value="C04", label="C04 - 1.37 um (cirrus)"),
    ParamOption(value="C05", label="C05 - 1.61 um (nieve y hielo)"),
    ParamOption(value="C06", label="C06 - 2.25 um (particula de nube)"),
    ParamOption(value="C07", label="C07 - 3.90 um (IR onda corta)"),
    ParamOption(value="C08", label="C08 - 6.19 um (vapor de agua alto)"),
    ParamOption(value="C09", label="C09 - 6.95 um (vapor de agua medio)"),
    ParamOption(value="C10", label="C10 - 7.34 um (vapor de agua bajo)"),
    ParamOption(value="C11", label="C11 - 8.50 um (fase de tope de nube)"),
    ParamOption(value="C12", label="C12 - 9.61 um (ozono)"),
    ParamOption(value="C13", label="C13 - 10.35 um (IR ventana limpia)"),
    ParamOption(value="C14", label="C14 - 11.20 um (IR onda larga)"),
    ParamOption(value="C15", label="C15 - 12.30 um (IR onda larga sucia)"),
    ParamOption(value="C16", label="C16 - 13.30 um (CO2 onda larga)"),
]

# Una sola escala de resoluciones para todos los productos: el numero solo.
# 2712 es el nativo del disco de GOES y el techo que aceptan los scripts.
_RESOLUCIONES = [
    ParamOption(value=v, label=v)
    for v in ("1400", "1800", "2000", "2400", "2712", "3200", "4000")
]

_FONDO = [
    ParamOption(value="oscuro", label="Fondo oscuro"),
    ParamOption(value="claro", label="Fondo claro"),
]


def _rango(dias_atras: int = 0) -> dict[str, str]:
    """Ventana por defecto: ayer y hoy en UTC (el dataset crudo viene en UTC)."""
    fin = datetime.now(timezone.utc).date() - timedelta(days=dias_atras)
    return {"start": (fin - timedelta(days=1)).isoformat(), "end": fin.isoformat()}


#: Lista cerrada de "últimos N cuadros": la UI no inventa otros valores.
CUADROS_ULTIMOS = (10, 12, 24, 36, 48, 60)

_AYUDA_HORA_UTC = ("hora UTC, igual que el dataset crudo; Paraguay es UTC-3 "
                   "(12 UTC = 09:00 local)")


def _params_cuadro() -> list[ParamSpec]:
    """Hora y minuto UTC del cuadro exacto: sólo tienen sentido con Snapshot.

    "Snapshot" ya no es "el cuadro de siempre": con estos dos controles se elige
    cualquier slot de 10 minutos (15:40 UTC, por ejemplo) y se renderiza ése.
    """
    return [
        ParamSpec(
            name="hora",
            label="Hora del cuadro (UTC)",
            kind="hour",
            default=15,          # mediodía en Paraguay; igual que el snapshot de GIBS
            min=0,
            max=23,
            step=1,
            help=_AYUDA_HORA_UTC,
            enabled_when={"snapshot": True},
        ),
        ParamSpec(
            name="minuto",
            label="Minuto",
            kind="select",
            default="00",
            options=[
                ParamOption(value=f"{m:02d}", label=f"{m:02d}")
                for m in range(0, 60, 10)
            ],
            help="los slots del ABI caen cada 10 minutos",
            enabled_when={"snapshot": True},
        ),
    ]


def _params_ultimos() -> list[ParamSpec]:
    """Switch "Últimos datos" + selector de cuántos cuadros.

    Se arma por producto (no se comparte el objeto) porque `_con_snapshot`
    ajusta `enabled_when` en cada instancia.
    """
    return [
        ParamSpec(
            name="ultimos",
            label="Últimos datos",
            kind="toggle",
            default=False,
            help="ignora la ventana de fechas: baja y anima los cuadros más nuevos publicados",
        ),
        ParamSpec(
            name="ultimos_n",
            label="Cuántos cuadros",
            kind="select",
            default="24",
            options=[
                ParamOption(value=str(n), label=f"{n} cuadros")
                for n in CUADROS_ULTIMOS
            ],
            enabled_when={"ultimos": True},
        ),
    ]


def _params_firms(por_defecto: str = "dia") -> list[ParamSpec]:
    """Toggle de focos de FIRMS + sus dos selectores.

    `por_defecto` es la ventana que propone la UI: `dia` para una captura suelta
    (el compuesto diario ES ese día) y `3h` para una animación, donde los focos
    aparecen cuando pasa el satélite en vez de quedar fijos todo el día.

    Se arma por producto (no se comparte el objeto) por la misma razón que
    `_params_ultimos`: `_con_snapshot` ajusta `enabled_when` en cada instancia.
    """
    return [
        ParamSpec(
            name="firms",
            label="Focos de calor (FIRMS)",
            kind="toggle",
            default=False,
            help="superpone los focos de NASA FIRMS; necesita el MAP_KEY en "
                 "datos/firms_map_key.txt",
        ),
        ParamSpec(
            name="firms_fuente",
            label="Sensor FIRMS",
            kind="select",
            default="viirs",
            options=[
                ParamOption(value="viirs", label="VIIRS NOAA-20 + NOAA-21 (375 m)"),
                ParamOption(value="modis", label="MODIS Aqua + Terra (1 km)"),
                ParamOption(value="snpp", label="Suomi NPP (publica intermitente)"),
                ParamOption(value="landsat", label="Landsat (sólo EE.UU. y Canadá)"),
                ParamOption(value="todos", label="Todos los sensores"),
            ],
            help="VIIRS es el que tiene sentido a 250 m/px; MODIS detecta menos y "
                 "Landsat no cubre Sudamérica",
            enabled_when={"firms": True},
        ),
        ParamSpec(
            name="firms_alcance",
            label="Focos a mostrar",
            kind="select",
            default="completo",
            options=[
                ParamOption(value="completo", label="Todos los del área"),
                ParamOption(value="paraguay", label="Sólo los de Paraguay"),
            ],
            help="en el globo, «sólo Paraguay» evita que miles de focos del hemisferio "
                 "tapen el disco (y baja mucho menos)",
            enabled_when={"firms": True},
        ),
        ParamSpec(
            name="firms_ventana",
            label="Ventana de focos",
            kind="select",
            default=por_defecto,
            options=[
                ParamOption(value="dia", label="Día UTC completo"),
                ParamOption(value="3h", label="± 3 horas"),
                ParamOption(value="6h", label="± 6 horas"),
                ParamOption(value="12h", label="± 12 horas"),
                ParamOption(value="24h", label="Últimas 24 horas"),
                ParamOption(value="48h", label="Últimos 2 días"),
                ParamOption(value="72h", label="Últimos 3 días"),
                ParamOption(value="5d", label="Últimos 5 días"),
            ],
            help="el día completo acompaña a los compuestos diarios; ±3 h sigue el paso "
                 "del satélite; 24 h en adelante es el «time based» de FIRMS",
            enabled_when={"firms": True},
        ),
    ]


def _receta_rgb(producto: str) -> dict:
    """Receta RGB oficial (bandas, rangos y guía) desde `comun/rgb_goes.py`.

    La app no reimplementa la receta: la misma tabla que usa el render manda en
    el catálogo, así no se puede desincronizar la ayuda de lo que se dibuja.
    """
    comun = RAIZ_REPO / "comun"
    if str(comun) not in sys.path:
        sys.path.insert(0, str(comun))
    from rgb_goes import RECETAS  # import local: evita depender del sys.path global

    return RECETAS[producto]


def _producto_rgb(pid: str, nombre: str, producto: str, extras=()) -> Product:
    """Un producto RGB: mismos controles que `goes_banda`, sin banda ni paleta."""
    receta = _receta_rgb(producto)
    from rgb_goes import etiqueta_canal  # noqa: PLC0415 - ver `_receta_rgb`

    canales = " · ".join(etiqueta_canal(c) for c in receta["canales"])
    return Product(
        id=pid,
        name=nombre,
        group="satelite",
        stage="descargar/descargar_goes_rgb.py + prototipos/poster_goes_rgb.py",
        summary=f"RGB oficial de tres canales ({canales}). {receta['resumen']}",
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
                help="define la carpeta de datos goes_<banda>_<sat>",
            ),
            ParamSpec(name="ventana", label="Ventana temporal", kind="date-range",
                      default=_rango(), enabled_when={"ultimos": False}),
            *_params_ultimos(),
            *_params_cuadro(),
            ParamSpec(name="resolucion", label="Resolucion", kind="select",
                      default="2712", options=_RESOLUCIONES),
            ParamSpec(
                name="hora_desde",
                label="Desde (UTC)",
                kind="hour",
                default=0,
                min=0,
                max=23,
                step=1,
                help=_AYUDA_HORA_UTC,
                enabled_when={"ultimos": False},
            ),
            ParamSpec(
                name="hora_hasta",
                label="Hasta (UTC)",
                kind="hour",
                default=24,
                min=1,
                max=24,
                step=1,
                help="fin exclusivo: 24 cierra el día UTC completo",
                enabled_when={"ultimos": False},
            ),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=False,
                      enabled_when={"ultimos": False}),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider",
                      default=12, min=4, max=30, step=2),
            *extras,
        ],
    )


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
            ParamSpec(name="ventana", label="Ventana temporal", kind="date-range",
                      default=_rango(), enabled_when={"ultimos": False}),
            *_params_ultimos(),
            *_params_cuadro(),
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
                name="hora_desde",
                label="Desde (UTC)",
                kind="hour",
                default=0,
                min=0,
                max=23,
                step=1,
                help=_AYUDA_HORA_UTC,
                enabled_when={"ultimos": False},
            ),
            ParamSpec(
                name="hora_hasta",
                label="Hasta (UTC)",
                kind="hour",
                default=24,
                min=1,
                max=24,
                step=1,
                help="fin exclusivo: 24 cierra el día UTC completo",
                enabled_when={"ultimos": False},
            ),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=False,
                      enabled_when={"ultimos": False}),
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
            ParamSpec(name="ventana", label="Ventana temporal", kind="date-range",
                      default=_rango(), enabled_when={"ultimos": False}),
            *_params_ultimos(),
            *_params_cuadro(),
            ParamSpec(
                name="resolucion",
                label="Resolucion",
                kind="select",
                default="2712",
                options=_RESOLUCIONES,
                help="2712 px es la resolucion del disco nativo: por debajo se pierde detalle",
            ),
            ParamSpec(
                name="hora_desde",
                label="Desde (UTC)",
                kind="hour",
                default=0,
                min=0,
                max=23,
                step=1,
                help=_AYUDA_HORA_UTC,
                enabled_when={"ultimos": False},
            ),
            ParamSpec(
                name="hora_hasta",
                label="Hasta (UTC)",
                kind="hour",
                default=24,
                min=1,
                max=24,
                step=1,
                help="fin exclusivo: 24 cierra el día UTC completo",
                enabled_when={"ultimos": False},
            ),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=False,
                      enabled_when={"ultimos": False}),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider", default=8, min=4, max=30, step=2),
            *_params_firms(por_defecto="3h"),
        ],
    ),
    Product(
        id="goes_banda",
        name="GOES - banda cruda, estilo color real",
        group="satelite",
        stage="descargar/descargar_goes.py + prototipos/poster_goes_banda.py",
        summary="Una banda ABI real, no el compuesto de tres. Mismo encuadre y fondo "
        "del color real: globo completo, sin reticula, costas ni barra de color.",
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
                name="banda",
                label="Banda",
                kind="select",
                default="C13",
                options=_BANDAS_ABI,
                help="C01-C06 son reflectancia (visible e infrarrojo cercano); C07-C16, temperatura de brillo",
            ),
            ParamSpec(
                name="paleta",
                label="Paleta",
                kind="select",
                default="clean_ir",
                options=_PALETAS_BANDA,
                help="cada banda termica tiene su paleta oficial y solo se ofrece con ella: reflectancia es la de C01-C06 (negro a blanco, 0 a 100 %); clean_ir es la de GIBS (-92.1 a 56.9 C, C13), c07_ir la de la banda 7 (-83 a 127 C), c08_ir..c10_ir la de vapor de agua (-93 a 7 C), c11_ir..c15_ir la de la ventana IR (-110 a 57 C) y c16_ir va de -128 a 128 C",
            ),
            ParamSpec(name="ventana", label="Ventana temporal", kind="date-range",
                      default=_rango(), enabled_when={"ultimos": False}),
            *_params_ultimos(),
            *_params_cuadro(),
            ParamSpec(name="resolucion", label="Resolucion", kind="select",
                      default="2712", options=_RESOLUCIONES),
            ParamSpec(
                name="hora_desde",
                label="Desde (UTC)",
                kind="hour",
                default=0,
                min=0,
                max=23,
                step=1,
                help=_AYUDA_HORA_UTC,
                enabled_when={"ultimos": False},
            ),
            ParamSpec(
                name="hora_hasta",
                label="Hasta (UTC)",
                kind="hour",
                default=24,
                min=1,
                max=24,
                step=1,
                help="fin exclusivo: 24 cierra el día UTC completo",
                enabled_when={"ultimos": False},
            ),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=False,
                      enabled_when={"ultimos": False}),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider", default=12, min=4, max=30, step=2),
        ],
    ),
    Product(
        id="goes_lst",
        name="GOES - temperatura de superficie (LST)",
        group="satelite",
        stage="descargar/descargar_goes_lst.py + prototipos/poster_goes_lst.py",
        summary="ABI L2 LST a 2 km, disco completo: temperatura de la superficie solo "
        "en tierra despejada, con cadencia horaria. La escala va en C y muestra F "
        "como escala secundaria.",
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
            ParamSpec(name="ventana", label="Ventana temporal", kind="date-range",
                      default=_rango(), enabled_when={"ultimos": False}),
            *_params_ultimos(),
            ParamSpec(
                name="hora",
                label="Hora del cuadro (UTC)",
                kind="hour",
                default=15,
                min=0,
                max=23,
                step=1,
                help=_AYUDA_HORA_UTC,
                enabled_when={"snapshot": True},
            ),
            ParamSpec(name="resolucion", label="Resolucion", kind="select",
                      default="2712", options=_RESOLUCIONES),
            ParamSpec(
                name="compuesto",
                label="Compuesto temporal (h)",
                kind="select",
                default="1",
                options=[
                    ParamOption(value="1", label="1 h (cuadro instantaneo)"),
                    ParamOption(value="3", label="3 h (menos huecos)"),
                    ParamOption(value="6", label="6 h (poster, mas suave)"),
                ],
                help="promedia las horas anteriores para tapar nubes; con mas de una "
                     "hora el cuadro deja de ser una instantanea",
            ),
            ParamSpec(
                name="hora_desde",
                label="Desde (UTC)",
                kind="hour",
                default=0,
                min=0,
                max=23,
                step=1,
                help=_AYUDA_HORA_UTC,
                enabled_when={"ultimos": False},
            ),
            ParamSpec(
                name="hora_hasta",
                label="Hasta (UTC)",
                kind="hour",
                default=24,
                min=1,
                max=24,
                step=1,
                help="fin exclusivo: 24 cierra el dia UTC completo",
                enabled_when={"ultimos": False},
            ),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=False,
                      enabled_when={"ultimos": False}),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider",
                      default=8, min=4, max=30, step=2),
        ],
    ),
    _producto_rgb("goes_dust", "GOES - Dust RGB", "dust"),
    _producto_rgb("goes_airmass", "GOES - Air Mass RGB", "airmass"),
    _producto_rgb("goes_firetemp", "GOES - Fire Temperature RGB", "firetemp",
                  extras=_params_firms(por_defecto="3h")),
    Product(
        id="goes_sandwich",
        name="GOES - Sandwich (visible + IR realzado)",
        group="satelite",
        stage="descargar/descargar_goes.py + prototipos/poster_goes_sandwich.py",
        summary="Mezcla el visible (C02, 0.64 um) con el IR ventana (C13, 10.3 um) "
        "realzado en color: morfologia y temperatura del tope nuboso en una imagen. "
        "Producto de dia.",
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
                name="alpha",
                label="Mezcla visible / IR",
                kind="slider",
                default=0.5,
                min=0.0,
                max=1.0,
                step=0.05,
                help="1 = solo visible; 0 = solo IR realzado; 0.5 es el clasico",
            ),
            ParamSpec(name="ventana", label="Ventana temporal", kind="date-range",
                      default=_rango(), enabled_when={"ultimos": False}),
            *_params_ultimos(),
            *_params_cuadro(),
            ParamSpec(name="resolucion", label="Resolucion", kind="select", default="2712",
                      options=_RESOLUCIONES),
            ParamSpec(
                name="hora_desde",
                label="Desde (UTC)",
                kind="hour",
                default=0,
                min=0,
                max=23,
                step=1,
                help=_AYUDA_HORA_UTC,
                enabled_when={"ultimos": False},
            ),
            ParamSpec(
                name="hora_hasta",
                label="Hasta (UTC)",
                kind="hour",
                default=24,
                min=1,
                max=24,
                step=1,
                help="fin exclusivo: 24 cierra el dia UTC completo",
                enabled_when={"ultimos": False},
            ),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=False,
                      enabled_when={"ultimos": False}),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider", default=8,
                      min=4, max=30, step=2),
        ],
    ),
    Product(
        id="geocolor",
        name="GOES - GeoColor (dia real, IR y luces)",
        group="satelite",
        stage="descargar/geocolor.py + cuadros/cuadros_geocolor.py",
        summary="Producto RGB ya mezclado de NASA GIBS: color real de dia, IR de noche "
        "y luces de ciudad. No es el compuesto de tres bandas.",
        params=[
            ParamSpec(
                name="satelite",
                label="Satelite",
                kind="select",
                default="G19",
                options=[
                    ParamOption(value="G19", label="GOES-East G19 (75.2 W)"),
                    ParamOption(value="G18", label="GOES-West G18 (137.2 W)"),
                ],
            ),
            ParamSpec(name="ventana", label="Ventana temporal", kind="date-range",
                      default=_rango(), enabled_when={"ultimos": False}),
            *_params_ultimos(),
            *_params_cuadro(),
            ParamSpec(
                name="resolucion",
                label="Resolucion",
                kind="select",
                default="1400",
                options=_RESOLUCIONES,
            ),
            ParamSpec(
                name="hora_desde",
                label="Desde (UTC)",
                kind="hour",
                default=0,
                min=0,
                max=23,
                step=1,
                help=_AYUDA_HORA_UTC,
                enabled_when={"ultimos": False},
            ),
            ParamSpec(
                name="hora_hasta",
                label="Hasta (UTC)",
                kind="hour",
                default=24,
                min=1,
                max=24,
                step=1,
                help="fin exclusivo: 24 cierra el día UTC completo",
                enabled_when={"ultimos": False},
            ),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=False,
                      enabled_when={"ultimos": False}),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider", default=8, min=4, max=30, step=2),
            *_params_firms(por_defecto="3h"),
        ],
    ),
    Product(
        id="truecolor_viirs",
        name="NOAA-20 - true color (VIIRS)",
        group="satelite",
        stage="descargar/truecolor.py + cuadros/cuadros_truecolor.py",
        summary="Composicion diaria global de VIIRS en color real corregido. "
        "Un cuadro por dia: es un mosaico, no una captura instantanea.",
        params=[
            ParamSpec(name="ventana", label="Dias", kind="date-range", default=_rango(30)),
            ParamSpec(
                name="resolucion",
                label="Resolucion",
                kind="select",
                default="2000",
                options=_RESOLUCIONES,
            ),
            ParamSpec(
                name="animar",
                label="Animar los dias",
                kind="toggle",
                default=False,
                help="un cuadro por dia; la animacion muestra la evolucion entre fechas",
            ),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider", default=6, min=2, max=30, step=1),
        ],
    ),
    Product(
        id="pace_truecolor",
        name="PACE - color real (OCI)",
        group="satelite",
        stage="prototipos/poster_pace_gibs.py (NASA GIBS)",
        summary="Compuesto de color real del OCI (670/555/443 nm) desde NASA GIBS. "
        "PACE es polar y su swath no cubre el planeta de una vez: se combinan varios "
        "dias para llenar la grilla. Un solo cuadro, globo completo.",
        params=[
            ParamSpec(
                name="ventana",
                label="Dias del compuesto",
                kind="date-range",
                default=_rango(8),
                help="el compuesto se arma hacia atras desde el ultimo dia",
            ),
            ParamSpec(
                name="resolucion",
                label="Resolucion",
                kind="select",
                default="2000",
                options=_RESOLUCIONES,
            ),
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
                options=_RESOLUCIONES,
            ),
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
                options=_RESOLUCIONES,
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
            ParamSpec(
                name="horizonte",
                label="Horizonte (h)",
                kind="slider",
                default=144,
                min=6,
                max=144,
                step=6,
                help="los pasos de 3 h llegan hasta 144 h",
            ),
            ParamSpec(name="fondo", label="Fondo del globo", kind="select", default="claro", options=_FONDO),
            ParamSpec(name="resolucion", label="Resolucion", kind="select", default="1400", options=_RESOLUCIONES),
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
                default="00",
                options=[ParamOption(value=v, label=f"{v}z") for v in ("00", "06", "12", "18")],
            ),
            ParamSpec(
                name="horizonte",
                label="Horizonte (h)",
                kind="slider",
                default=144,
                min=6,
                max=144,
                step=6,
                help="los pasos de 3 h llegan hasta 144 h",
            ),
            ParamSpec(name="fondo", label="Fondo del globo", kind="select", default="claro", options=_FONDO),
            ParamSpec(name="resolucion", label="Resolucion", kind="select", default="1400", options=_RESOLUCIONES),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=True),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider", default=12, min=4, max=30, step=2),
        ],
    ),
    Product(
        id="viento_250",
        name="Viento en 250 mb",
        group="modelo",
        stage="descargar/viento_250_mslp.py + cuadros/cuadros_viento_250.py",
        summary="Velocidad del viento en 250 mb (kt) con streamlines y extremos "
        "de presion a nivel del mar sobre globo.",
        params=[
            ParamSpec(
                name="modelo",
                label="Modelo",
                kind="select",
                default="ifs",
                options=[
                    ParamOption(value="ifs", label="ECMWF IFS 0.25"),
                    ParamOption(value="gfs", label="GFS 0.25 (NOAA)"),
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
            ParamSpec(
                name="horizonte",
                label="Horizonte (h)",
                kind="slider",
                default=144,
                min=6,
                max=144,
                step=6,
                help="los pasos de 3 h llegan hasta 144 h",
            ),
            ParamSpec(name="fondo", label="Fondo del globo", kind="select", default="claro", options=_FONDO),
            ParamSpec(name="resolucion", label="Resolucion", kind="select", default="1400", options=_RESOLUCIONES),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=True),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider", default=12, min=4, max=30, step=2),
        ],
    ),
    Product(
        id="snapshot_paraguay",
        name="Snapshot - Paraguay",
        group="satelite",
        stage="descargar/snapshot_paraguay.py + cuadros/snapshot_paraguay.py",
        summary="Una sola captura recortada a los bordes de Paraguay, sin rotulos. "
        "VIIRS a 250 m de dia, o GeoColor de dia y noche.",
        params=[
            ParamSpec(
                name="capa",
                label="Capa",
                kind="select",
                default="truecolor",
                options=[
                    ParamOption(value="truecolor", label="NOAA-20 / VIIRS (250 m)"),
                    ParamOption(value="snpp", label="Suomi NPP / VIIRS (250 m)"),
                    ParamOption(value="aqua", label="Aqua / MODIS (250 m)"),
                    ParamOption(value="terra", label="Terra / MODIS (250 m)"),
                    ParamOption(value="geocolor", label="GOES-19 GeoColor (dia y noche, ~2 km)"),
                ],
                help="los cuatro True Color son diarios y de 250 m; GeoColor llega a 2 km",
            ),
            ParamSpec(
                name="ultima",
                label="Ultima disponible",
                kind="toggle",
                default=True,
                help="resuelve el granulo mas nuevo; ignora fecha, hora y minuto",
            ),
            ParamSpec(
                name="fecha",
                label="Fecha de la captura",
                kind="date",
                default=date.today().isoformat(),
                enabled_when={"ultima": False},
            ),
            ParamSpec(
                name="hora",
                label="Hora UTC",
                kind="hour",
                default=15,
                min=0,
                max=23,
                step=1,
                help="15z es el mediodia en Paraguay; de noche se ve el IR",
                enabled_when={"ultima": False},
            ),
            ParamSpec(
                name="minuto",
                label="Minuto",
                kind="select",
                default="00",
                options=[ParamOption(value=f"{m:02d}", label=f"{m:02d}") for m in range(0, 60, 10)],
                enabled_when={"ultima": False},
            ),
            ParamSpec(
                name="margen",
                label="Margen (%)",
                kind="slider",
                default=6,
                min=0,
                max=20,
                step=1,
                help="aire alrededor del pais dentro del encuadre",
            ),
            ParamSpec(
                name="detalle",
                label="Detalle (m/px)",
                kind="select",
                default="250",
                options=[
                    ParamOption(value=v, label=f"{v} m/px")
                    for v in ("125", "250", "500", "1000", "2000")
                ],
                help="250 m/px es el detalle real de VIIRS; por debajo solo interpola",
            ),
            ParamSpec(name="borde", label="Dibujar el contorno", kind="toggle", default=True),
            *_params_firms(),
        ],
    ),
    Product(
        id="himawari",
        name="Himawari-9 - disco completo (B13)",
        group="satelite",
        stage="descargar/descargar_himawari.py + cuadros/cuadros_himawari_ir.py",
        summary="AHI banda 13 (10.4 um). El disco entero, centrado en el punto "
        "subsatelital (140.7 E): la vista del satelite, sin recorte regional.",
        params=[
            ParamSpec(name="ventana", label="Ventana temporal", kind="date-range",
                      default=_rango(), enabled_when={"ultimos": False}),
            *_params_ultimos(),
            *_params_cuadro(),
            ParamSpec(
                name="resolucion",
                label="Resolucion",
                kind="select",
                default="2712",
                options=_RESOLUCIONES,
                help="2712 px es el default del script; por debajo el titulo se superpone",
            ),
            ParamSpec(
                name="hora_desde",
                label="Desde (UTC)",
                kind="hour",
                default=0,
                min=0,
                max=23,
                step=1,
                help=_AYUDA_HORA_UTC,
                enabled_when={"ultimos": False},
            ),
            ParamSpec(
                name="hora_hasta",
                label="Hasta (UTC)",
                kind="hour",
                default=24,
                min=1,
                max=24,
                step=1,
                help="fin exclusivo: 24 cierra el día UTC completo",
                enabled_when={"ultimos": False},
            ),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=False,
                      enabled_when={"ultimos": False}),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider", default=12, min=4, max=30, step=2),
        ],
    ),
    Product(
        id="follaje",
        name="PACE - follaje (LANDVI)",
        # Grupo propio: el rail lo deja despues de los modelos (ver _ORDEN).
        group="vegetacion",
        stage="descargar/pace_landvi.py + cuadros/cuadros_follaje.py",
        summary="Indice de vegetacion de PACE sobre fondo de poster, ventana por dias.",
        params=[
            ParamSpec(name="ventana", label="Ventana temporal", kind="date-range", default=_rango(20)),
            ParamSpec(
                name="proyeccion",
                label="Proyeccion",
                kind="select",
                default="plano",
                options=[
                    ParamOption(value="plano", label="Plano (Robinson)"),
                    ParamOption(value="globo", label="Globo (Orthographic)"),
                ],
            ),
            ParamSpec(name="resolucion", label="Resolucion", kind="select", default="1400", options=_RESOLUCIONES),
            ParamSpec(name="animar", label="Animar", kind="toggle", default=False),
            ParamSpec(name="fps", label="Cuadros por segundo", kind="slider", default=12, min=4, max=30, step=2),
        ],
    ),
]

#: Productos que no llevan el switch "Snapshot": el de Snapshot ya es una sola
#: captura y PACE/OCI ya es un compuesto de varios dias.
SIN_SNAPSHOT = {"snapshot_paraguay", "pace_truecolor"}


def _con_snapshot(producto: Product) -> Product:
    """Suma el switch de snapshot y apaga lo que no aplica cuando está prendido.

    Se aplica al final: cada producto declara sus controles y acá se agrega el
    corte transversal, sin repetir la misma regla trece veces. El producto de
    Snapshot ya es una sola captura, así que no lo lleva.
    """
    if producto.id in SIN_SNAPSHOT:
        return producto
    for spec in producto.params:
        if spec.name in ("animar", "fps", "hora_desde", "hora_hasta",
                         "ultimos", "ultimos_n"):
            # Se suma la condición, no se pisa: "últimos" ya trae la suya.
            spec.enabled_when = {**(spec.enabled_when or {}), "snapshot": False}
    producto.params.insert(
        0,
        ParamSpec(
            name="snapshot",
            label="Snapshot",
            kind="toggle",
            default=False,
            help="un solo cuadro: no arma serie ni animación, y usa el cuadro de siempre",
        ),
    )
    return producto


#: Productos sin encuadre Paraguay: el Snapshot ya ES el encuadre (y no se toca);
#: el MUR es SST oceánica (Paraguay es mediterráneo, no hay mar que mostrar); el
#: follaje usa un globo Robinson/3D con otro diseño y el Himawari no lo necesita.
SIN_PARAGUAY = {"snapshot_paraguay", "mur_sst", "mur_realista", "follaje", "himawari",
                "pace_truecolor"}  # PACE no tiene encuadre Paraguay: es un compuesto global


def _con_paraguay(producto: Product) -> Product:
    """Suma el encuadre "Solo Paraguay" con su margen.

    El margen se expresa en porcentaje (0-20), igual que en el producto Snapshot;
    el motor lo traduce a una fracción del lado de la caja del país. El producto
    Snapshot queda intacto: ya es una captura de Paraguay.
    """
    if producto.id in SIN_PARAGUAY:
        return producto
    producto.params.insert(
        0,
        ParamSpec(
            name="paraguay",
            label="Solo Paraguay",
            kind="toggle",
            default=False,
            help="encuadra la captura o la animación en las coordenadas de Paraguay",
        ),
    )
    producto.params.insert(
        1,
        ParamSpec(
            name="margen",
            label="Margen Paraguay (%)",
            kind="slider",
            default=6,
            min=0,
            max=20,
            step=1,
            help="aire alrededor del país dentro del encuadre",
            enabled_when={"paraguay": True},
        ),
    )
    return producto


#: Productos diarios sin "últimos datos" que resuelven el último día con la sonda de
#: GIBS (`comun/dia_reciente.py`). Los modelos ECMWF no van acá: su "último" es la
#: corrida, que ya se ajusta por otro camino.
_ULTIMO_DIARIO = {"truecolor_viirs", "mur_sst", "mur_realista"}


def _con_ultimo(producto: Product) -> Product:
    """Suma "último cuadro disponible" a los productos que saben resolverlo.

    Es la misma maquinaria de `ultimos` (un solo cuadro, el más nuevo publicado) y,
    para los productos diarios, la sonda de GIBS. Sin esto, elegir un día u hora que
    la fuente todavía no tiene hace fallar el job, y no hay forma de saberlo antes.
    """
    nombres = {spec.name for spec in producto.params}
    if "snapshot" not in nombres:
        return producto
    if "ultimos" not in nombres and producto.id not in _ULTIMO_DIARIO:
        return producto
    indices = [i for i, spec in enumerate(producto.params)
               if spec.name in ("ultimos", "ultimos_n")]
    indice = (max(indices) + 1) if indices else 1
    producto.params.insert(
        indice,
        ParamSpec(
            name="ultimo",
            label="Último cuadro disponible",
            kind="toggle",
            default=False,
            help="en snapshot, ignora fecha, hora y minuto y usa el slot más nuevo "
                 "que la fuente ya publicó",
            enabled_when={"snapshot": True},
        ),
    )
    return producto


PRODUCTS = [_con_ultimo(_con_snapshot(_con_paraguay(p))) for p in PRODUCTS]

#: Orden del rail. Los productos se definen en bloques de codigo por familia,
#: pero la UI los muestra en este orden; lo que no figure aca va al final.
#: El rail agrupa por `group` respetando el orden de aparicion, asi que este
#: orden tambien fija el de los grupos (satelite, modelo, vegetacion).
_ORDEN = (
    "goes_banda",
    "geocolor",
    "goes_c13",
    "goes_lst",
    "goes_truecolor",
    "goes_airmass",
    "goes_dust",
    "goes_firetemp",
    "goes_sandwich",
    "snapshot_paraguay",
    "truecolor_viirs",   # NOAA-20
    "pace_truecolor",    # PACE / OCI
    "himawari",
    "mur_sst",
    "mur_realista",
    "precipitacion_ecmwf",
    "anomalia_2t",
    "viento_250",
    "follaje",           # PACE, ultimo
)
_POSICION = {producto_id: posicion for posicion, producto_id in enumerate(_ORDEN)}
PRODUCTS.sort(key=lambda producto: _POSICION.get(producto.id, len(_ORDEN)))

_BY_ID = {p.id: p for p in PRODUCTS}


def get_product(product_id: str) -> Product | None:
    return _BY_ID.get(product_id)


# Muestras por variante: el nombre del archivo es el contrato.
#   previews/<producto>--<valor1>--<valor2>.webp
# Los valores siguen el orden de esta tabla y se comparan con los parametros que
# manda el formulario. Los toggles van como true/false en minúscula (tal cual
# los serializa el frontend). Sin variante para la seleccion actual, se cae al
# sample.
_VARIANTES = {
    "goes_c13": ("satelite", "paraguay"),
    # Dos formas: la de la banda (la placa cambia al cambiar de canal) y la
    # vieja por paleta, que queda como respaldo.
    "goes_banda": (("satelite", "banda", "paleta"), ("satelite", "paleta")),
    "goes_dust": ("satelite", "paraguay"),
    "goes_airmass": ("satelite", "paraguay"),
    "goes_firetemp": ("satelite", "paraguay"),
    "goes_truecolor": ("satelite", "encuadre", "limbo"),
    "geocolor": ("satelite", "paraguay"),
    "precipitacion_ecmwf": ("modelo", "paraguay"),
    "anomalia_2t": ("modelo", "paraguay"),
    "viento_250": ("modelo", "paraguay"),
    "follaje": ("proyeccion",),
    "snapshot_paraguay": ("capa",),
}


def _formas(especificacion) -> tuple[tuple[str, ...], ...]:
    """Normaliza la declaracion de `_VARIANTES` a una tupla de formas.

    Un producto puede aceptar nombres de archivo con distinta cantidad de
    campos: `goes_banda--G19--C06--reflectancia` (banda) y el viejo
    `goes_banda--G19--clean_ir` (solo paleta).
    """
    if not especificacion:
        return ()
    if isinstance(especificacion[0], str):
        return (tuple(especificacion),)
    return tuple(tuple(forma) for forma in especificacion)


def _muestras(producto: Product, carpeta: Path) -> list[PreviewVariant]:
    """Variantes que existen en disco para este producto."""
    formas = _formas(_VARIANTES.get(producto.id))
    if not formas:
        return []
    variantes: list[PreviewVariant] = []
    for archivo in carpeta.glob(f"{producto.id}--*.webp"):
        valores = archivo.stem.split("--")[1:]
        for campos in formas:
            if len(valores) != len(campos):
                continue
            variantes.append(
                PreviewVariant(
                    url=f"/previews/{archivo.name}",
                    when=dict(zip(campos, valores)),
                )
            )
            break
    # La más específica primero: {satélite, banda, paleta} gana sobre
    # {satélite, paleta} y sobre la placa fija del producto.
    variantes.sort(key=lambda v: (-len(v.when), v.url))
    return variantes


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
                    "previews": _muestras(producto, muestras),
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

    if product.id in ("goes_dust", "goes_airmass", "goes_firetemp"):
        banda = "C07" if product.id == "goes_firetemp" else "C13"
        datos = raiz / f"goes_{banda.lower()}_{str(params.get('satelite', 'G19')).lower()}"
        if datos.is_dir():
            encontradas |= _fechas_de_nombres([f.name for f in datos.glob("*.nc")], _DIA_GOES)

    if product.id == "goes_lst":
        datos = raiz / f"goes_lst_{str(params.get('satelite', 'G19')).lower()}"
        if datos.is_dir():
            encontradas |= _fechas_de_nombres([f.name for f in datos.glob("*.nc")], _DIA_GOES)

    if product.id == "himawari":
        datos = raiz / "himawari_b13_h09"
        if datos.is_dir():
            encontradas |= _fechas_de_nombres([f.name for f in datos.glob("*.npz")], _FECHA_ISO)

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
            "viento_250": "frames_viento_250",
            "snapshot_paraguay": "snapshot_paraguay",
            "follaje": "frames_follaje",
        }.get(product.id, "")
        if prefijo:
            for carpeta in salidas.glob(f"{prefijo}*"):
                encontradas |= _fechas_de_nombres([carpeta.name], _FECHA_ISO)

    if encontradas:
        return "descubierto", sorted(encontradas, reverse=True)[:180]

    hoy = date.today()
    return "demo", [(hoy - timedelta(days=i)).isoformat() for i in range(30)]

