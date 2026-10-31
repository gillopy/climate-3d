"""Traduccion de una receta a comandos reales del repo.

Los flags salen de leer cada script (`--help` y el `main()` de cada uno); no hay
adivinanzas. Si un producto no expone un control —por ejemplo una paleta— el
catalogo no lo muestra, en vez de inventar un boton que no hace nada.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
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


def _a_fecha(valor: Any, por_defecto: date) -> date:
    try:
        return date.fromisoformat(str(valor))
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
        fin = inicio.fromordinal(inicio.toordinal() + 60)
    return inicio, fin


def _cuadros_goes(inicio: date, fin: date) -> tuple[int, int]:
    """Cuantos cuadros y cada cuantos minutos, sobre la ventana elegida.

    Los slots de GOES caen en multiplos de 10 minutos, asi que el paso se
    redondea a 10 para que cada cuadro encuentre su `.nc`.
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


def planear(product_id: str, params: dict[str, Any], work: Path) -> list[Step]:
    """Devuelve los comandos a correr, en orden, para esta receta."""
    constructor = _CONSTRUCTORES.get(product_id)
    if constructor is None:
        raise ValueError(f"Producto sin receta real: {product_id}")
    pasos = constructor(params, work)
    if not any(p.kind == "animate" for p in pasos) and _bool(params, "animar"):
        pasos.append(_animar(params, work))
    return pasos


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


def _goes(params: dict[str, Any], work: Path) -> list[Step]:
    inicio, fin = _rango(params)
    sat = str(params.get("satelite", "G19"))
    banda = str(params.get("banda", "C13"))
    px = _px(params)

    # Arrancar en el primer slot que exista evita pedirle al render un horario
    # que no esta en disco: la grilla de GOES es de 10 minutos, pero los .nc no.
    disponibles = [s for s in _slots_goes(sat, banda) if inicio <= s.date() <= fin]
    if not disponibles:
        if _bool(params, "descargar"):
            desde = datetime.combine(inicio, datetime.min.time())
            n, paso = _cuadros_goes(inicio, fin)
        else:
            raise ValueError(
                f"No hay .nc de {banda} de {sat} entre {inicio} y {fin}. "
                "Activa 'Bajar los .nc antes de renderizar' o elegi otra fecha."
            )
    else:
        desde = disponibles[0]
        paso = 10
        # `cuadros_goes.py` asume una grilla contigua de 10 minutos: si un slot
        # falta, revienta con KeyError. Se avanza solo mientras el siguiente
        # slot exista de verdad.
        conocidos = set(disponibles)
        n = 1
        while n < 48 and (desde + timedelta(minutes=paso * n)) in conocidos:
            n += 1

    pasos: list[Step] = []
    if _bool(params, "descargar"):
        peticion = _cuadros_goes(inicio, fin)
        pasos.append(
            Step(
                kind="download",
                label=f"bajando {banda} de {sat}",
                script="descargar/descargar_goes.py",
                args=[
                    "--sat", sat,
                    "--banda", banda,
                    "--desde", inicio.isoformat(),
                    "--hasta", fin.isoformat(),
                    "--paso", str(peticion[1]),
                ],
                expected=peticion[0],
            )
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
        args.append("--globo")
    pasos.append(
        Step(
            kind="render",
            label=f"renderizando {n} cuadro(s) de {banda}",
            script="cuadros/cuadros_goes.py",
            args=args,
            expected=n,
        )
    )
    return pasos


# --- MUR: SST descargada ya renderizada por GIBS ------------------------
def _mur(params: dict[str, Any], work: Path) -> list[Step]:
    inicio, fin = _rango(params)
    dias = max(1, (fin - inicio).days + 1)
    paso = max(1, int(math.ceil(dias / 8)))
    px = _px(params, 1200)

    comunes = [
        "--desde", inicio.isoformat(),
        "--hasta", fin.isoformat(),
        "--paso", str(paso),
        "--px", str(px),
    ]
    pasos: list[Step] = []
    if _bool(params, "descargar"):
        pasos.append(
            Step(
                kind="download",
                label="bajando cuadros de SST",
                script="descargar/mur_sst.py",
                args=[*comunes, "--out", str(work)],
                expected=max(1, dias // paso),
            )
        )
    pasos.append(
        Step(
            kind="render",
            label="componiendo el globo",
            script="cuadros/cuadros_mur.py",
            args=[*comunes, "--out", str(work)],
            expected=max(1, dias // paso),
        )
    )
    return pasos


# --- ECMWF: precipitacion y anomalia ------------------------------------
def _ecmwf_producto(producto: str, params: dict[str, Any], work: Path) -> list[Step]:
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
    descarga, render = (
        ("descargar/precipitacion_ecmwf.py", "cuadros/cuadros_precipitacion.py")
        if producto == "precipitacion"
        else ("descargar/anomalia_2t_ecmwf.py", "cuadros/cuadros_anomalia_2t.py")
    )

    pasos: list[Step] = []
    if _bool(params, "descargar"):
        pasos.append(
            Step(
                kind="download",
                label=f"bajando {producto} de {modelo}",
                script=descarga,
                args=comunes,
                expected=n,
            )
        )
    pasos.append(
        Step(
            kind="render",
            label=f"renderizando {n} cuadros",
            script=render,
            args=[
                *comunes,
                "--px", str(px),
                "--fondo-globo", fondo,
                "--salidas", str(work),
            ],
            expected=n,
        )
    )
    return pasos


def _precipitacion(params: dict[str, Any], work: Path) -> list[Step]:
    return _ecmwf_producto("precipitacion", params, work)


def _anomalia(params: dict[str, Any], work: Path) -> list[Step]:
    return _ecmwf_producto("anomalia_2t", params, work)


# --- FOLLAJE: PACE LANDVI ----------------------------------------------
def _follaje(params: dict[str, Any], work: Path) -> list[Step]:
    inicio, fin = _rango(params)
    px = _px(params, 1400)

    pasos: list[Step] = []
    if _bool(params, "descargar"):
        pasos.append(
            Step(
                kind="download",
                label="bajando LANDVI de PACE",
                script="descargar/pace_landvi.py",
                args=["--desde", inicio.isoformat(), "--hasta", fin.isoformat()],
                expected=max(1, (fin - inicio).days + 1),
            )
        )
    pasos.append(
        Step(
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
            expected=max(1, (fin - inicio).days + 1),
        )
    )
    return pasos


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
