"""Traduccion de una receta a comandos reales del repo.

Los flags salen de leer cada script (`--help` y el `main()` de cada uno); no hay
adivinanzas. Si un producto no expone un control —por ejemplo una paleta— el
catalogo no lo muestra, en vez de inventar un boton que no hace nada.

Cualquier fecha es valida: si no hay datos locales para la ventana, la receta
incluye la descarga. Y si el render falla por datos faltantes, el job reintenta
con la descarga que queda guardada en ``Plan.descarga``.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

RAIZ_REPO = Path(__file__).resolve().parents[2]
PYTHON_REPO = RAIZ_REPO / ".venv" / "Scripts" / "python.exe"


@dataclass(frozen=True)
class Step:
    """Un comando del repo, listo para ejecutar."""

    kind: str  # download | render | animate
    label: str
    script: str  # ruta relativa al repo
    args: list[str]
    expected: int = 0  # lineas de progreso esperadas; 0 = indeterminado


@dataclass
class Plan:
    """Que correr ahora y que descarga queda de rescate."""

    pasos: list[Step] = field(default_factory=list)
    descarga: Step | None = None


def _a_fecha(valor: Any, por_defecto: date) -> date:
    try:
        return date.fromisoformat(str(valor)[:10])
    except (TypeError, ValueError):
        return por_defecto


def _rango(params: dict[str, Any]) -> tuple[date, date]:
    """Rango elegido por el usuario, ordenado y acotado a 60 dias."""
    hoy = date.today()
    bruto = params.get("ventana") or params.get("fecha") or {}
    if isinstance(bruto, str):
        unico = _a_fecha(bruto, hoy)
        return unico, unico
    inicio = _a_fecha(bruto.get("start"), hoy)
    fin = _a_fecha(bruto.get("end"), inicio)
    if fin < inicio:
        inicio, fin = fin, inicio
    if (fin - inicio).days > 60:
        fin = date.fromordinal(inicio.toordinal() + 60)
    return inicio, fin


def _cuadros_goes(inicio: date, fin: date) -> tuple[int, int]:
    """Cuantos cuadros y cada cuantos minutos, sobre la ventana elegida.

    Los slots de GOES caen en multiplos de 10 minutos, asi que el paso se
    redondea a 10 para que cada cuadro encuentre (o descargue) su `.nc`.
    """
    dias = max(1, (fin - inicio).days + 1)
    n = max(4, min(dias * 8 + 4, 48))
    total_min = dias * 1440
    paso = max(10, int(round(total_min / max(1, n - 1) / 10.0)) * 10)
    return n, paso


def _px(params: dict[str, Any], por_defecto: int = 1400) -> int:
    try:
        return max(400, min(int(params.get("resolucion", por_defecto)), 2712))
    except (TypeError, ValueError):
        return por_defecto


def _fps(params: dict[str, Any]) -> str:
    try:
        return str(max(2, min(int(params.get("fps", 12)), 30)))
    except (TypeError, ValueError):
        return "12"


def _bool(params: dict[str, Any], clave: str) -> bool:
    return bool(params.get(clave, False))


def planear(product_id: str, params: dict[str, Any], work: Path) -> Plan:
    """Devuelve los comandos a correr, en orden, para esta receta."""
    constructor = _CONSTRUCTORES.get(product_id)
    if constructor is None:
        raise ValueError(f"Producto sin receta real: {product_id}")
    plan = constructor(params, work)
    if _bool(params, "animar") and not any(p.kind == "animate" for p in plan.pasos):
        plan.pasos.append(_animar(params, work))
    return plan


# --- animacion (comun a todos) ------------------------------------------
def _animar(params: dict[str, Any], work: Path) -> Step:
    return Step(
        kind="animate",
        label="armando la animacion",
        script="animar/armar.py",
        args=[
            "--frames",
            "{frames}",
            "--fps",
            _fps(params),
            "--formato",
            "mp4",
            "--salida",
            str(work / "animacion.mp4"),
        ],
    )


# --- GOES: satelite + banda + paleta ------------------------------------
_SLOT_GOES = re.compile(r"_s(\d{4})(\d{3})(\d{2})(\d{2})")

# Punto subsatelite: el centro real de lo que capta cada GOES. Es el centroide
# correcto para reproyectar, en vez de un recorte regional cualquiera.
_LON_SUBSAT = {"G16": -75.2, "G19": -75.2, "G18": -137.2}


def _slots_goes(sat: str, banda: str) -> list[datetime]:
    """Marcas de tiempo con `.nc` real en disco, leidas del nombre del archivo."""
    from .catalog import data_root  # import local: evita el ciclo catalogo<->recetas

    carpeta = data_root() / f"goes_{banda.lower()}_{sat.lower()}"
    if not carpeta.is_dir():
        return []
    slots: list[datetime] = []
    for archivo in carpeta.glob("*.nc"):
        match = _SLOT_GOES.search(archivo.name)
        if not match:
            continue
        anio, dia, hora, minuto = (int(g) for g in match.groups())
        try:
            slots.append(
                datetime(anio, 1, 1).replace(day=1)
                + timedelta(days=dia - 1, hours=hora, minutes=minuto)
            )
        except ValueError:
            continue
    return sorted(set(slots))


def _goes(params: dict[str, Any], work: Path) -> Plan:
    inicio, fin = _rango(params)
    sat = str(params.get("satelite", "G19"))
    banda = str(params.get("banda", "C13"))
    px = _px(params)
    forzar = _bool(params, "descargar")

    disponibles = [s for s in _slots_goes(sat, banda) if inicio <= s.date() <= fin]

    if disponibles and not forzar:
        # Ya hay datos: se arranca en el primer slot real y se avanza solo
        # mientras el siguiente exista. `cuadros_goes.py` asume una grilla
        # contigua de 10 minutos y revienta con KeyError si falta uno.
        desde = disponibles[0]
        paso = 10
        conocidos = set(disponibles)
        n = 1
        while n < 48 and (desde + timedelta(minutes=paso * n)) in conocidos:
            n += 1
    else:
        # Sin datos, o con descarga forzada: la receta manda y la descarga
        # trae exactamente los slots que el render va a pedir.
        desde = datetime.combine(inicio, time.min)
        n, paso = _cuadros_goes(inicio, fin)

    # `descargar_goes.py` recorre [desde, hasta) en pasos de `paso` minutos.
    descarga = Step(
        kind="download",
        label=f"bajando {banda} de {sat} ({n} slot(s))",
        script="descargar/descargar_goes.py",
        args=[
            "--sat", sat,
            "--banda", banda,
            "--desde", desde.isoformat(),
            "--hasta", (desde + timedelta(minutes=paso * n)).isoformat(),
            "--paso", str(paso),
        ],
        expected=max(1, math.ceil(n / 10)),
    )

    args = [
        "--sat", sat,
        "--banda", banda,
        "--desde", desde.strftime("%Y-%m-%dT%H:%M"),
        "--n", str(n),
        "--paso", str(paso),
        "--px", str(px),
        "--paleta", str(params.get("paleta", "clean_ir")),
        "--out", str(work),
        "--lote", "1",
    ]
    if _bool(params, "globo"):
        # Globo centrado en el punto subsatelite (lat 0): la reproyeccion
        # natural del disco, no un recorte sobre Paraguay.
        lon_sub = _LON_SUBSAT.get(sat.upper(), -75.2)
        args += ["--globo", "--centro", f"{lon_sub:g}", "0"]

    render_step = Step(
        kind="render",
        label=f"renderizando {n} cuadro(s) de {banda}",
        script="cuadros/cuadros_goes.py",
        args=args,
        expected=n,
    )

    # Sin datos locales la descarga no es opcional: no hay nada que renderizar.
    pasos = [descarga, render_step] if (forzar or not disponibles) else [render_step]
    return Plan(pasos=pasos, descarga=descarga)


# --- MUR: SST descargada ya renderizada por GIBS ------------------------
def _mur(params: dict[str, Any], work: Path) -> Plan:
    inicio, fin = _rango(params)
    dias = max(1, (fin - inicio).days + 1)
    paso = max(1, int(math.ceil(dias / 8)))
    px = _px(params, 1200)
    n = max(1, dias // paso)

    comunes = [
        "--desde", inicio.isoformat(),
        "--hasta", fin.isoformat(),
        "--paso", str(paso),
        "--px", str(px),
    ]
    descarga = Step(
        kind="download",
        label="bajando cuadros de SST",
        script="descargar/mur_sst.py",
        args=[*comunes, "--out", str(work)],
        expected=n,
    )
    render_step = Step(
        kind="render",
        label="componiendo el globo",
        script="cuadros/cuadros_mur.py",
        args=[*comunes, "--out", str(work)],
        expected=n,
    )
    pasos = [descarga, render_step] if _bool(params, "descargar") else [render_step]
    return Plan(pasos=pasos, descarga=descarga)


# --- ECMWF: precipitacion y anomalia ------------------------------------
def _ecmwf_producto(producto: str, params: dict[str, Any], work: Path) -> Plan:
    inicio, _ = _rango(params)
    modelo = str(params.get("modelo", "ifs"))
    corrida = str(params.get("corrida", "00"))
    horizonte = int(params.get("horizonte", 144) or 144)
    px = _px(params, 1400)
    fondo = str(params.get("fondo", "oscuro"))
    n = max(2, min(horizonte // 6 + 2, 42))

    comunes = [
        "--modelo", modelo,
        "--fecha", inicio.isoformat(),
        "--ciclo", corrida,
        "--hasta-hora", str(horizonte),
        "--paso", "6",
    ]
    descarga_script, render_script = (
        ("descargar/precipitacion_ecmwf.py", "cuadros/cuadros_precipitacion.py")
        if producto == "precipitacion"
        else ("descargar/anomalia_2t_ecmwf.py", "cuadros/cuadros_anomalia_2t.py")
    )

    descarga = Step(
        kind="download",
        label=f"bajando {producto} de {modelo}",
        script=descarga_script,
        args=comunes,
        expected=n,
    )
    render_step = Step(
        kind="render",
        label=f"renderizando {n} cuadros",
        script=render_script,
        args=[
            *comunes,
            "--px", str(px),
            "--fondo-globo", fondo,
            "--salidas", str(work),
        ],
        expected=n,
    )
    pasos = [descarga, render_step] if _bool(params, "descargar") else [render_step]
    return Plan(pasos=pasos, descarga=descarga)


def _precipitacion(params: dict[str, Any], work: Path) -> Plan:
    return _ecmwf_producto("precipitacion", params, work)


def _anomalia(params: dict[str, Any], work: Path) -> Plan:
    return _ecmwf_producto("anomalia_2t", params, work)


# --- FOLLAJE: PACE LANDVI ----------------------------------------------
def _follaje(params: dict[str, Any], work: Path) -> Plan:
    inicio, fin = _rango(params)
    px = _px(params, 1400)
    n = max(1, (fin - inicio).days + 1)

    descarga = Step(
        kind="download",
        label="bajando LANDVI de PACE",
        script="descargar/pace_landvi.py",
        args=["--desde", inicio.isoformat(), "--hasta", fin.isoformat()],
        expected=n,
    )
    render_step = Step(
        kind="render",
        label="renderizando el follaje",
        script="cuadros/cuadros_follaje.py",
        args=[
            "--desde", inicio.isoformat(),
            "--hasta", fin.isoformat(),
            "--px", str(px),
            # aca --out es la carpeta de cuadros, no la raiz de salidas.
            "--out", str(work / "frames"),
        ],
        expected=n,
    )
    pasos = [descarga, render_step] if _bool(params, "descargar") else [render_step]
    return Plan(pasos=pasos, descarga=descarga)


_CONSTRUCTORES = {
    "goes_c13": _goes,
    "mur_sst": _mur,
    "precipitacion_ecmwf": _precipitacion,
    "anomalia_2t": _anomalia,
    "follaje": _follaje,
}


def python_repo() -> Path:
    return PYTHON_REPO


def repo_listo() -> bool:
    return PYTHON_REPO.is_file()
