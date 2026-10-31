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
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

RAIZ_REPO = Path(__file__).resolve().parents[2]
PYTHON_REPO = RAIZ_REPO / ".venv" / "Scripts" / "python.exe"

# Tabla de productos ECMWF en data.ecmwf.int (copiada del propio descargador).
_BASE_ECMWF = "https://data.ecmwf.int/forecasts/{ymd}/{ciclo}z/{ruta}/{ymd}{ciclo}0000-{paso}.index"
_RUTA_ECMWF = {
    "ifs": "ifs/0p25/oper",
    "aifs-single": "aifs-single/0p25/oper",
    "aifs-ens": "aifs-ens/0p25/enfo",
}
PRODUCTOS_ECMWF = ("precipitacion_ecmwf", "anomalia_2t")


class SinRed(Exception):
    """No se pudo consultar la disponibilidad (no es un 404)."""


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


# --- disponibilidad de corridas ECMWF -----------------------------------
def _paso_ecmwf(modelo: str, hora: int) -> str:
    """Sufijo del paso, igual que `_sufijo()` del descargador del repo."""
    return f"{hora}h-enfo-cf" if modelo == "aifs-ens" else f"{hora}h-oper-fc"


def _url_indice(modelo: str, dia: date, ciclo: str, hora: int) -> str:
    ymd = dia.strftime("%Y%m%d")
    return _BASE_ECMWF.format(
        ymd=ymd,
        ciclo=ciclo,
        ruta=_RUTA_ECMWF[modelo],
        paso=_paso_ecmwf(modelo, hora),
    )


def _publicado(modelo: str, dia: date, ciclo: str, hora: int) -> bool:
    """True si el `.index` de ese paso existe en data.ecmwf.int."""
    pedido = urllib.request.Request(_url_indice(modelo, dia, ciclo, hora), method="HEAD")
    try:
        with urllib.request.urlopen(pedido, timeout=6) as respuesta:
            return 200 <= respuesta.status < 300
    except urllib.error.HTTPError:
        return False  # 404/403: ese paso no esta publicado
    except Exception as exc:  # noqa: BLE001 - red caida, DNS, proxy...
        raise SinRed(str(exc)) from exc


def _horizonte_disponible(modelo: str, dia: date, ciclo: str, horizonte: int) -> int:
    """El horizonte pedido, recortado a lo que la corrida publica de verdad."""
    if _publicado(modelo, dia, ciclo, horizonte):
        return horizonte
    # Baja de a 6 h: los modelos publican de forma progresiva y los 404 en
    # cadena del descargador son justamente esto.
    for intento in range(1, 21):
        candidato = horizonte - intento * 6
        if candidato <= 0:
            break
        if _publicado(modelo, dia, ciclo, candidato):
            return candidato
    return 0


def resolver_corrida(params: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    """Ubica la corrida publicada mas conveniente y recorta el horizonte.

    `data.ecmwf.int` no publica la corrida del dia hasta horas despues del
    ciclo, y borra las viejas por retencion. Pedir "hoy 00z" a las 03:00 UTC da
    404 en todos los pasos; esta funcion encuentra la ultima que si existe.
    """
    modelo = str(params.get("modelo", "ifs"))
    if modelo not in _RUTA_ECMWF:
        return params, None

    pedida = _a_fecha(params.get("fecha"), date.today())
    ciclo = str(params.get("corrida", "00")).zfill(2)
    horizonte = int(params.get("horizonte", 144) or 144)
    hoy = date.today()

    elegida: date | None = None
    mensaje: str | None = None

    # 1) Mismo ciclo hacia atras: cubre "la de hoy todavia no salio".
    for atras in range(0, 8):
        dia = pedida - timedelta(days=atras)
        if _publicado(modelo, dia, ciclo, 0):
            elegida = dia
            if atras:
                mensaje = (
                    f"la corrida {pedida} {ciclo}z no esta publicada; "
                    f"uso {dia} {ciclo}z"
                )
            break

    # 2) Hacia adelante: la fecha pedida ya salio del archivo por retencion.
    if elegida is None:
        for adelante in range(1, 11):
            dia = pedida + timedelta(days=adelante)
            if dia > hoy:
                break
            if _publicado(modelo, dia, ciclo, 0):
                elegida = dia
                mensaje = (
                    f"la fecha {pedida} ya no esta en el archivo de ECMWF; "
                    f"uso la mas cercana: {dia} {ciclo}z"
                )
                break

    if elegida is None:
        raise ValueError(
            f"No hay ninguna corrida {ciclo}z de {modelo} cerca de {pedida}. "
            "Proba otra fecha o ciclo."
        )

    disponible = _horizonte_disponible(modelo, elegida, ciclo, horizonte)
    if disponible <= 0:
        raise ValueError(
            f"La corrida {elegida} {ciclo}z de {modelo} no publica ningun paso. "
            "Proba otra fecha o ciclo."
        )
    if disponible < horizonte:
        aviso = (
            f"la corrida {elegida} {ciclo}z publica hasta {disponible} h; "
            f"recorto el horizonte de {horizonte} h"
        )
        mensaje = f"{mensaje}. {aviso}" if mensaje else aviso
        horizonte = disponible

    ajustado = {
        **params,
        "fecha": elegida.isoformat(),
        "corrida": ciclo,
        "horizonte": horizonte,
    }
    return ajustado, mensaje


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


def _hora_cenital(lon: float) -> time:
    """Hora UTC con el sol sobre el punto subsatelital.

    Es el momento en que el centro del disco esta iluminado: el que conviene
    para un poster de color real. Para G19 (75.2 W) cae cerca de las 17:00 UTC.
    """
    horas = (12.0 - lon / 15.0) % 24.0
    h = int(horas)
    m = int(round((horas - h) * 6)) * 10
    if m >= 60:
        h, m = (h + 1) % 24, 0
    return time(h, m)


def _slot_cenital(dia: date, lon: float) -> datetime:
    return datetime.combine(dia, _hora_cenital(lon))


# Que tan lejos del cenit se acepta un slot que ya esta en disco. Con 10 min de
# cadencia, media hora cubre el horario sin caer en la noche.
_TOLERANCIA_CENIT = timedelta(minutes=30)

# Los horarios se eligen en hora local (UTC-3), que es como se leen los posters.
_DESFASE_LOCAL = timedelta(hours=3)
_PASO_SLOT = 10  # minutos entre cuadros: la cadencia real del ABI
_MAX_CUADROS = 288  # 2 dias a 10 min: tope para no disparar 10 GB sin querer


def _ventana_animacion(
    inicio: date,
    fin: date,
    hora_desde: Any,
    hora_hasta: Any,
) -> tuple[datetime, datetime]:
    """Rango UTC que cubre las horas locales elegidas, en el primer y ultimo dia."""
    h0 = max(0, min(23, int(hora_desde)))
    h1 = max(h0 + 1, min(24, int(hora_hasta)))
    desde = datetime.combine(inicio, time(h0)) + _DESFASE_LOCAL
    if h1 >= 24:
        # Cerrar el dia: medianoche local del dia siguiente.
        hasta = datetime.combine(fin + timedelta(days=1), time(0)) + _DESFASE_LOCAL
    else:
        hasta = datetime.combine(fin, time(h1)) + _DESFASE_LOCAL

    # El ABI publica con retraso: pedir horas que todavia no existen solo llena
    # el log de 404. Se recorta al ultimo multiplo de 10 ya cumplido.
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)
    if hasta > ahora:
        tope = ahora.replace(second=0, microsecond=0)
        tope += timedelta(minutes=(10 - tope.minute % 10) % 10)
        hasta = max(desde, tope)

    if hasta <= desde:
        raise ValueError(
            "Esa ventana todavia no tiene datos: el satelite publica con retraso. "
            "Proba con una fecha anterior a hoy."
        )
    return desde, hasta


def _plan_slots(
    disponibles: set[datetime],
    cenital: datetime,
    animar: bool,
    ventana: tuple[datetime, datetime],
) -> tuple[datetime, int, int, bool]:
    """Slot inicial, cuantos cuadros y si hay que descargarlos.

    - Poster: un cuadro en el cenit (disco iluminado).
    - Animacion: todo el rango horario elegido, cada 10 minutos.
    """
    paso = _PASO_SLOT

    if animar:
        desde, hasta = ventana
        n = max(1, int((hasta - desde).total_seconds() // (paso * 60)))
        n = min(n, _MAX_CUADROS)
        faltan = any(
            (desde + timedelta(minutes=paso * i)) not in disponibles
            for i in range(n)
        )
        return desde, n, paso, faltan

    if cenital in disponibles:
        return cenital, 1, paso, False

    cercanos = [
        s for s in disponibles
        if abs((s - cenital).total_seconds()) <= _TOLERANCIA_CENIT.total_seconds()
    ]
    if cercanos:
        elegido = min(cercanos, key=lambda s: abs((s - cenital).total_seconds()))
        return elegido, 1, paso, False

    return cenital, 1, paso, True


def _goes(params: dict[str, Any], work: Path) -> Plan:
    inicio, fin = _rango(params)
    sat = str(params.get("satelite", "G19"))
    banda = "C13"
    px = _px(params)
    forzar = _bool(params, "descargar")

    from .catalog import data_root  # import local: evita el ciclo

    datos_dir = data_root() / f"goes_c13_{sat.lower()}"
    disponibles = [s for s in _slots_goes(sat, banda) if inicio <= s.date() <= fin]

    lon_sub = _LON_SUBSAT.get(sat.upper(), -75.2)
    cenital = _slot_cenital(inicio, lon_sub)
    ventana = _ventana_animacion(
        inicio, fin, params.get("hora_desde", 0), params.get("hora_hasta", 24)
    )
    desde, n, paso, falta = _plan_slots(
        set(disponibles), cenital, _bool(params, "animar"), ventana
    )

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

    # `cuadros_c13_ir.py` encuadra el disco completo con margen (`--radio`) y
    # centra donde se le diga. `cuadros_goes.py --globo` no tiene radio y el
    # globo se sale del marco por abajo.
    lon_sub = _LON_SUBSAT.get(sat.upper(), -75.2)
    args = [
        "--sat", sat,
        "--desde", desde.strftime("%Y-%m-%dT%H:%M"),
        "--n", str(n),
        "--paso", str(paso),
        "--px", str(px),
        "--paleta", str(params.get("paleta", "clean_ir")),
        "--geojson", "",  # sin el contorno de Paraguay: solo el dato
        "--centro", f"{lon_sub:g}", "0",
        "--radio", "90",
        "--datos", str(datos_dir),
        "--out", str(work),
        "--frames", str(work / "frames"),
        "--lote", "1",
    ]
    if str(params.get("paleta", "clean_ir")) == "clean_ir":
        # La rampa de GIBS tiene escala fija (-92.1 a 56.9 C). Con percentiles
        # los mismos colores caen en otras temperaturas y deja de coincidir con
        # Worldview (y con el render de Himawari, que si la usa fija).
        args += ["--vmin", "-92.1", "--vmax", "56.9"]

    render_step = Step(
        kind="render",
        label=f"renderizando {n} cuadro(s) de C13",
        script="cuadros/cuadros_c13_ir.py",
        args=args,
        expected=n,
    )

    # Si el slot del cenit no esta en disco, se baja: no se renderiza la noche.
    pasos = [descarga, render_step] if (forzar or falta) else [render_step]
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
def _crudos_existen(producto: str, modelo: str, fecha: str, ciclo: str) -> bool:
    """Si ya estan los crudos que el render de ECMWF va a leer."""
    from .catalog import data_root  # import local: evita el ciclo

    nombre = "ecmwf" if modelo == "ifs" else modelo
    carpeta = (
        data_root() / f"crudos_precip_{nombre}_{fecha}_{ciclo}z"
        if producto == "precipitacion"
        else data_root() / f"crudos_anom2t_{modelo}_{fecha}_{ciclo}z"
    )
    return carpeta.is_dir() and any(carpeta.iterdir())


def _ecmwf_producto(producto: str, params: dict[str, Any], work: Path) -> Plan:
    inicio, _ = _rango(params)
    modelo = str(params.get("modelo", "ifs"))
    corrida = str(params.get("corrida", "00"))
    horizonte = int(params.get("horizonte", 144) or 144)
    px = _px(params, 1400)
    fondo = str(params.get("fondo", "oscuro"))
    # El descargador y los cuadros del repo trabajan cada 3 h (PASO_HORA = 3).
    paso_horas = 3
    n = max(2, min(horizonte // paso_horas + 2, 81))

    comunes = [
        "--modelo", modelo,
        "--fecha", inicio.isoformat(),
        "--ciclo", corrida,
        "--hasta-hora", str(horizonte),
        "--paso", str(paso_horas),
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
    pasos = [descarga, render_step] if (
        _bool(params, "descargar")
        or not _crudos_existen(producto, modelo, inicio.isoformat(), corrida)
    ) else [render_step]
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


# --- GOES color real: C01 + C02 + C03 -----------------------------------
def _goes_truecolor(params: dict[str, Any], work: Path) -> Plan:
    inicio, fin = _rango(params)
    sat = str(params.get("satelite", "G19"))
    px = _px(params, 2400)
    forzar = _bool(params, "descargar")
    animar = _bool(params, "animar")
    disco = str(params.get("encuadre", "globo")) == "disco"

    # C02 es la banda pesada (~410 MB): si esta, el slot existe.
    disponibles = [s for s in _slots_goes(sat, "C02") if inicio <= s.date() <= fin]

    lon_sub = _LON_SUBSAT.get(sat.upper(), -75.2)
    cenital = _slot_cenital(inicio, lon_sub)
    ventana = _ventana_animacion(
        inicio, fin, params.get("hora_desde", 0), params.get("hora_hasta", 24)
    )
    desde, n, paso, falta = _plan_slots(set(disponibles), cenital, animar, ventana)

    slot = desde.strftime("%Y-%m-%dT%H:%M")
    descarga = Step(
        kind="download",
        label=f"bajando C01+C02+C03 de {sat} ({n} slot(s))",
        script="descargar/truecolor_goes.py",
        args=[
            "--desde", slot,
            "--n", str(n),
            "--paso", str(paso),
            "--sat", sat,
        ],
        expected=max(1, n),
    )

    if disco:
        render_step = Step(
            kind="render",
            label=f"disco nativo {px}px",
            script="prototipos/poster_goes_disco.py",
            args=[
                "--desde", slot,
                "--sat", sat,
                "--px", str(px),
                "--out", str(work / f"truecolor_nativo_{desde:%Y-%m-%dT%H%M}.png"),
            ],
            expected=1,
        )
    else:
        # Globo centrado en el punto subsatelital: disco completo, sin recorte
        # regional. El default del script es (-71, -10), que corta los bordes.
        lon_sub = _LON_SUBSAT.get(sat.upper(), -75.2)
        centro = ["--centro", f"{lon_sub:g}", "0"]
        if str(params.get("limbo", "completo")) == "completo":
            # Sin esto el script corta en 73.3 grados y deja afuera el 6 %
            # del disco: el limite visible real del satelite esta en 81.3.
            centro += ["--recorte", "1.0"]
        if str(params.get("nitidez", "maxima")) == "maxima":
            # La mediana 3x3 y el desenfoque de 0.8 px borronean las nubes:
            # a 2712 px se nota. Se apagan salvo que se pida el look suave.
            centro += ["--no-mediana", "--suavizado", "0"]
        if animar and n > 1:
            render_step = Step(
                kind="render",
                label=f"globo color real {n} cuadro(s)",
                script="prototipos/poster_goes_truecolor.py",
                args=[
                    "--desde", slot,
                    "--sat", sat,
                    "--px", str(px),
                    "--fondo", "oscuro",
                    "--no-lineas", "--no-fronteras", "--borde", "",
                    *centro,
                    "--n", str(n),
                    "--paso", str(paso),
                    "--frames", str(work / "frames"),
                ],
                expected=n,
            )
        else:
            render_step = Step(
                kind="render",
                label=f"poster color real {px}px",
                script="prototipos/poster_goes_truecolor.py",
                args=[
                    "--desde", slot,
                    "--sat", sat,
                    "--px", str(px),
                    "--fondo", "oscuro",
                    "--no-lineas", "--no-fronteras", "--borde", "",
                    *centro,
                    "--out", str(work / f"truecolor_{desde:%Y-%m-%dT%H%M}.png"),
                ],
                expected=1,
            )

    pasos = [descarga, render_step] if (forzar or falta) else [render_step]
    return Plan(pasos=pasos, descarga=descarga)


# --- MUR: poster realista ----------------------------------------------
def _mur_realista(params: dict[str, Any], work: Path) -> Plan:
    inicio, fin = _rango(params)
    dias = max(1, (fin - inicio).days + 1)
    paso = max(1, int(math.ceil(dias / 12)))
    px = _px(params, 2000)
    n = max(1, dias // paso)

    descarga = Step(
        kind="download",
        label="bajando la serie semanal de SST",
        script="descargar/mur_sst.py",
        args=[
            "--desde", inicio.isoformat(),
            "--hasta", fin.isoformat(),
            "--paso", str(paso),
            "--px", "2048",
            "--out", str(work),
        ],
        expected=n,
    )

    args = [
        "--crudo", "{crudo}",
        "--px", str(px),
        "--paleta", str(params.get("paleta", "realista")),
        "--rios",
        "--out", str(work / f"mur_realista_{px}px.png"),
    ]
    if _bool(params, "trend"):
        args.append("--trend")

    render_step = Step(
        kind="render",
        label=f"poster realista {px}px",
        script="prototipos/poster_mur_realista.py",
        args=args,
        expected=1,
    )
    # Sin crudos en la cache no hay poster: la descarga no es opcional.
    hay_crudos = any(work.rglob("crudo_*.jpg"))
    pasos = [descarga, render_step] if (_bool(params, "descargar") or not hay_crudos) else [render_step]
    return Plan(pasos=pasos, descarga=descarga)



# --- HIMAWARI-9: disco completo en la proyeccion del satelite -----------
_LON_SUBSAT["H09"] = 140.7  # Himawari-9 esta en 140.7 E

_SLOT_HIMAWARI = re.compile(r"(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})")


def _carpeta_himawari() -> Path:
    from .catalog import data_root  # import local: evita el ciclo

    return data_root() / "himawari_b13_h09"


def _slots_himawari() -> list[datetime]:
    """Marcas con `.npz` en disco, leidas del nombre (`YYYYMMDD_HHMM.npz`)."""
    carpeta = _carpeta_himawari()
    if not carpeta.is_dir():
        return []
    slots: list[datetime] = []
    for archivo in carpeta.glob("*.npz"):
        match = _SLOT_HIMAWARI.search(archivo.name)
        if not match:
            continue
        anio, mes, dia, hora, minuto = (int(g) for g in match.groups())
        try:
            slots.append(datetime(anio, mes, dia, hora, minuto))
        except ValueError:
            continue
    return sorted(set(slots))


def _himawari(params: dict[str, Any], work: Path) -> Plan:
    inicio, fin = _rango(params)
    px = _px(params, 1400)
    forzar = _bool(params, "descargar")
    animar = _bool(params, "animar")

    disponibles = [s for s in _slots_himawari() if inicio <= s.date() <= fin]
    cenital = _slot_cenital(inicio, _LON_SUBSAT["H09"])
    ventana = _ventana_animacion(
        inicio, fin, params.get("hora_desde", 0), params.get("hora_hasta", 24)
    )
    desde, n, paso, falta = _plan_slots(set(disponibles), cenital, animar, ventana)

    descarga = Step(
        kind="download",
        label=f"bajando B13 de Himawari-9 ({n} slot(s))",
        script="descargar/descargar_himawari.py",
        args=[
            "--sat", "H09",
            "--banda", "13",
            "--desde", desde.strftime("%Y-%m-%dT%H:%M"),
            "--hasta", (desde + timedelta(minutes=paso * n)).strftime("%Y-%m-%dT%H:%M"),
            "--paso", str(paso),
        ],
        expected=max(1, math.ceil(n / 10)),
    )

    render_step = Step(
        kind="render",
        label=f"renderizando {n} cuadro(s) de Himawari",
        script="cuadros/cuadros_himawari_ir.py",
        args=[
            "--desde", desde.strftime("%Y-%m-%dT%H:%M"),
            "--n", str(n),
            "--paso", str(paso),
            "--px", str(px),
            # Centro en el punto subsatelital y radio 90: el disco completo,
            # sin recorte regional.
            "--centro", f"{_LON_SUBSAT['H09']:g}", "0",
            "--radio", "90",
            "--datos", str(_carpeta_himawari()),
            "--out", str(work),
            "--frames", str(work / "frames"),
            "--lote", "1",
        ],
        expected=n,
    )

    pasos = [descarga, render_step] if (forzar or falta) else [render_step]
    return Plan(pasos=pasos, descarga=descarga)


_CONSTRUCTORES = {
    "goes_c13": _goes,
    "goes_truecolor": _goes_truecolor,
    "mur_sst": _mur,
    "mur_realista": _mur_realista,
    "precipitacion_ecmwf": _precipitacion,
    "anomalia_2t": _anomalia,
    "follaje": _follaje,
    "himawari": _himawari,
}


def python_repo() -> Path:
    return PYTHON_REPO


def repo_listo() -> bool:
    return PYTHON_REPO.is_file()


