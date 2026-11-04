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
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

RAIZ_REPO = Path(__file__).resolve().parents[2]
PYTHON_REPO = RAIZ_REPO / ".venv" / "Scripts" / "python.exe"

# Tabla de fuentes de pronóstico (copiada del propio descargador).
_BASE_ECMWF = "https://data.ecmwf.int/forecasts/{ymd}/{ciclo}z/{ruta}/{ymd}{ciclo}0000-{paso}.index"
# GFS 0.25° en AWS Open Data: un `.idx` de texto por paso (offsets en bytes).
_BASE_GFS = ("https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.{ymd}/{ciclo}/atmos/"
             "gfs.t{ciclo}z.pgrb2.0p25.f{hora:03d}.idx")
_RUTA_ECMWF = {
    "ifs": "ifs/0p25/oper",
    "aifs-single": "aifs-single/0p25/oper",
    "aifs-ens": "aifs-ens/0p25/enfo",
}
MODELOS = (*_RUTA_ECMWF, "gfs")
PRODUCTOS_ECMWF = ("precipitacion_ecmwf", "anomalia_2t", "viento_250")

# ECMWF Open Data no publica una grilla uniforme de pasos (verificado contra el
# portal):
#   IFS 00/12z   0-144 h cada 3 h, 150-360 h cada 6 h
#   IFS 06/18z   0-144 h cada 3 h
#   AIFS         0-360 h cada 6 h
# Pedir 3 h por encima de 144 (147, 153, ...) devuelve 404 y el job muere con
# "faltan los pasos". Igual con los AIFS, que no publican pasos de 3 h.
_PASO_3H_HASTA = 144


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
    hoy = datetime.now(timezone.utc).date()
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


def _px(params: dict[str, Any], por_defecto: int = 1400, tope: int = 2712) -> int:
    """Resoluci?n pedida, acotada al techo del producto.

    El globo no pasa de 2712 px (el disco nativo); la captura plana s? admite m?s.
    """
    try:
        return max(400, min(int(params.get("resolucion", por_defecto)), tope))
    except (TypeError, ValueError):
        return por_defecto


def _fps(params: dict[str, Any]) -> str:
    try:
        return str(max(2, min(int(params.get("fps", 12)), 30)))
    except (TypeError, ValueError):
        return "12"


def _bool(params: dict[str, Any], clave: str) -> bool:
    return bool(params.get(clave, False))


#: Cuántos cuadros ofrece "Últimos datos". Es la lista cerrada de la UI.
CUADROS_ULTIMOS = (10, 12, 24, 36, 48, 60)


def _ultimos(params: dict[str, Any]) -> int:
    """Cuántos cuadros recientes se pidieron (0 = usar la ventana de fechas)."""
    if not _bool(params, "ultimos") or _snapshot(params):
        return 0
    try:
        n = int(params.get("ultimos_n", 24))
    except (TypeError, ValueError):
        return 24
    # La UI manda un valor de la lista; igual se acota al más cercano.
    return min(CUADROS_ULTIMOS, key=lambda valor: abs(valor - n))


def _ultimos_goes(sat: str, banda: str, n: int) -> list[datetime]:
    """Los `n` slots más nuevos publicados en NOAA S3 (una consulta por hora).

    Si no hay red, se cae a los últimos `n` que ya estén en disco: el job puede
    renderizar y la descarga avisa con su error en el log. Sin red y sin disco no
    hay nada que mostrar, y el pedido falla con un mensaje claro.
    """
    comun = RAIZ_REPO / "comun"
    if str(comun) not in sys.path:
        sys.path.insert(0, str(comun))
    from goes_reciente import ultimos_slots

    try:
        slots = ultimos_slots(sat, banda, n)
    except Exception:  # noqa: BLE001 - offline: molesta más un job muerto que un fallback
        slots = []
    if slots:
        return slots

    locales = _slots_goes(sat, banda)
    if locales:
        return locales[-n:]
    raise ValueError(
        f"No hay datos de {sat} {banda}: NOAA S3 no respondió y el disco está vacío. "
        "Revisá la conexión y volvé a intentar."
    )


def _ultimos_geocolor(sat: str, n: int) -> list[datetime]:
    """Los `n` slots GeoColor más nuevos que GIBS ya publica.

    GIBS contesta 200 con una imagen negra para un instante sin gránulo, así que
    `comun/geocolor_reciente` camina hacia atrás validando miniaturas. Si la red
    falla, cae al reloj de C13 en NOAA S3 (misma cadencia de 10 min).
    """
    comun = RAIZ_REPO / "comun"
    if str(comun) not in sys.path:
        sys.path.insert(0, str(comun))
    try:
        from geocolor_reciente import ultimos_slots

        return ultimos_slots(sat, n)
    except Exception:  # noqa: BLE001 - offline: se usa el reloj de C13
        return _ultimos_goes(sat, "C13", n)


def _ultimos_himawari(n: int) -> list[datetime]:
    """Los `n` slots Himawari-9 más nuevos con los 10 segmentos publicados."""
    comun = RAIZ_REPO / "comun"
    if str(comun) not in sys.path:
        sys.path.insert(0, str(comun))
    try:
        from himawari_reciente import ultimos_slots

        slots = ultimos_slots(n)
    except Exception:  # noqa: BLE001 - offline: se usan los que ya están en disco
        slots = []
    if slots:
        return slots

    locales = _slots_himawari()
    if locales:
        return locales[-n:]
    raise ValueError(
        "No hay datos de Himawari: el bucket de NOAA no respondió y el disco está "
        "vacío. Revisá la conexión y volvé a intentar."
    )


def _snapshot(params: dict[str, Any]) -> bool:
    """True si el pedido quiere un solo cuadro: sin serie y sin animación.

    No toca los scripts: cada receta recorta el pedido a un cuadro con las
    mismas banderas que ya usa (un slot, un día, un paso).
    """
    return _bool(params, "snapshot")


def _rango_de_la_corrida(params: dict[str, Any]) -> tuple[date, date]:
    """Rango efectivo de días: con snapshot se queda con el último pedido."""
    inicio, fin = _rango(params)
    return (fin, fin) if _snapshot(params) else (inicio, fin)


# --- disponibilidad de corridas ECMWF -----------------------------------
def _paso_ecmwf(modelo: str, hora: int) -> str:
    """Sufijo del paso, igual que `_sufijo()` del descargador del repo."""
    return f"{hora}h-enfo-cf" if modelo == "aifs-ens" else f"{hora}h-oper-fc"


def _url_indice(modelo: str, dia: date, ciclo: str, hora: int) -> str:
    ymd = dia.strftime("%Y%m%d")
    if modelo == "gfs":
        return _BASE_GFS.format(ymd=ymd, ciclo=ciclo, hora=hora)
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


def _paso_horas_ecmwf(modelo: str, horizonte: int) -> int:
    """Horas entre pasos que esa corrida publica de verdad.

    Los AIFS publican cada 6 h de punta a punta. El IFS y el GFS publican cada
    3 h hasta las 144 h; el IFS pasa a 6 h de ahí en adelante.
    """
    if modelo in ("aifs-single", "aifs-ens"):
        return 6
    if modelo == "gfs":
        return 3
    return 3 if horizonte <= _PASO_3H_HASTA else 6


def _horizonte_disponible(
    modelo: str, dia: date, ciclo: str, horizonte: int, paso: int
) -> int:
    """El horizonte pedido, recortado a lo que la corrida publica de verdad.

    El recorte se mueve sobre la misma grilla de `paso` que después pide el
    descargador, así nunca devuelve un horizonte que no calce con los pasos.
    Antes bajaba de a 6 h fijo: un 145 h con pasos de 3 h probaba 139, 133...
    (ninguno múltiplo de 3) y terminaba en 0.
    """
    candidato = horizonte - horizonte % paso
    # Tope de sondas: 360 h cada 6 h son 60 pasos, el horizonte más largo.
    for _ in range(60):
        if candidato <= 0:
            break
        if _publicado(modelo, dia, ciclo, candidato):
            return candidato
        candidato -= paso
    return 0


def resolver_corrida(params: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    """Ubica la corrida publicada mas conveniente y recorta el horizonte.

    `data.ecmwf.int` no publica la corrida del dia hasta horas despues del
    ciclo, y borra las viejas por retencion. Pedir "hoy 00z" a las 03:00 UTC da
    404 en todos los pasos; esta funcion encuentra la ultima que si existe.
    """
    modelo = str(params.get("modelo", "ifs"))
    if modelo not in MODELOS:
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

    # Se sonda con la grilla que corresponde al horizonte pedido. Si el recorte
    # baja a 144 h o menos, el plan vuelve a elegir 3 h y sigue calzando.
    disponible = _horizonte_disponible(
        modelo, elegida, ciclo, horizonte, _paso_horas_ecmwf(modelo, horizonte)
    )
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
    # Cada "Generar" vuelve a consultar el origen: los descargadores son
    # reanudables (saltean lo que ya está en disco) y un fallo de red no es
    # fatal (jobs.py sigue con lo cacheado y lo avisa en el log).
    if plan.descarga is not None and not any(p.kind == "download" for p in plan.pasos):
        plan.pasos.insert(0, plan.descarga)
    # "Últimos datos" siempre es una serie: no depende del switch "Animar".
    quiere_animar = _bool(params, "animar") or _ultimos(params) > 0
    if (
        quiere_animar
        and not _snapshot(params)   # un snapshot nunca arma video
        and not any(p.kind == "animate" for p in plan.pasos)
    ):
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


# --- encuadre "Solo Paraguay" -------------------------------------------
def _margen_paraguay(params: dict[str, Any]) -> float:
    """Margen del encuadre como fracción del lado (la UI manda 0-20 %)."""
    try:
        return max(0.0, min(0.20, float(params.get("margen", 6)) / 100.0))
    except (TypeError, ValueError):
        return 0.06


def _encuadre_paraguay(params: dict[str, Any], modo: str) -> list[str]:
    """Flags del encuadre Paraguay para el render, o [] si está apagado.

    `modo` es cómo lo pide cada script:
      * `radio`   — `--centro LON LAT --radio GRADOS` (cartopy)
      * `recorte` — `--centro LON LAT --recorte FRACCIÓN` (póster orthographic)
      * `bbox`    — `--bbox O S E N` (mapa plano)
    """
    if not _bool(params, "paraguay"):
        return []
    comun = RAIZ_REPO / "comun"
    if str(comun) not in sys.path:
        sys.path.insert(0, str(comun))
    from paraguay import encuadre

    caja = encuadre(_margen_paraguay(params))
    if modo == "radio":
        return ["--centro", f"{caja['lon']:g}", f"{caja['lat']:g}",
                "--radio", f"{caja['radio']:g}"]
    if modo == "recorte":
        return ["--centro", f"{caja['lon']:g}", f"{caja['lat']:g}",
                "--recorte", f"{caja['radio'] / 90.0:g}"]
    if modo == "bbox":
        return ["--bbox", f"{caja['oeste']:g}", f"{caja['sur']:g}",
                f"{caja['este']:g}", f"{caja['norte']:g}"]
    raise ValueError(f"modo de encuadre desconocido: {modo}")


def _borde_paraguay(params: dict[str, Any]) -> str:
    """Ruta del contorno de Paraguay si el encuadre está activo, o cadena vacía."""
    if not _bool(params, "paraguay"):
        return ""
    return str(RAIZ_REPO / "datos" / "paraguay_gadm.json")


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
    """Cénit de ese día, nunca en el futuro.

    Si se pide hoy y la hora central todavía no pasó, se usa el mismo horario del
    día anterior: pedir un slot que aún no existe devuelve una imagen negra.
    """
    slot = datetime.combine(dia, _hora_cenital(lon))
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)
    while slot > ahora:
        slot -= timedelta(days=1)
    return slot


# Que tan lejos del cenit se acepta un slot que ya esta en disco. Con 10 min de
# cadencia, media hora cubre el horario sin caer en la noche.
_TOLERANCIA_CENIT = timedelta(minutes=30)

# Los horarios se eligen en **UTC**, igual que el dataset crudo y que la hora de
# los cuadros. Paraguay es UTC-3: la etiqueta de la UI muestra el equivalente.
_PASO_SLOT = 10  # minutos entre cuadros: la cadencia real del ABI
_MAX_CUADROS = 288  # 2 dias a 10 min: tope para no disparar 10 GB sin querer
# El ABI (y GIBS) publican con retraso: no se piden slots que todavía no salieron.
_MARGEN_PUBLICACION = timedelta(minutes=20)


def _piso_slot(t: datetime, paso: int = _PASO_SLOT) -> datetime:
    return t.replace(second=0, microsecond=0, minute=t.minute - t.minute % paso)


#: Hora UTC que propone el formulario para un snapshot (mediodía en Paraguay).
_HORA_SNAPSHOT = 15


def _slot_pedido(params: dict[str, Any], dia: date) -> datetime:
    """Instante exacto del snapshot: la hora y el minuto que eligió el usuario.

    Es UTC, como todo el resto. El minuto se redondea al múltiplo de 10 (la
    cadencia del ABI) y un cuadro que todavía no se publicó se rechaza con un
    mensaje claro en vez de bajar un 404.
    """
    try:
        hora = max(0, min(23, int(params.get("hora", _HORA_SNAPSHOT) or 0)))
        minuto = int(params.get("minuto", 0) or 0)
    except (TypeError, ValueError):
        hora, minuto = _HORA_SNAPSHOT, 0
    minuto = max(0, min(59, minuto)) // _PASO_SLOT * _PASO_SLOT
    slot = datetime.combine(dia, time(hora, minuto))

    tope = _piso_slot(datetime.now(timezone.utc).replace(tzinfo=None) - _MARGEN_PUBLICACION)
    if slot > tope:
        raise ValueError(
            f"El cuadro {slot:%Y-%m-%d %H:%M} UTC todavía no está publicado: el "
            f"satélite publica con ~{int(_MARGEN_PUBLICACION.total_seconds() // 60)} min "
            "de retraso. Elegí una hora anterior."
        )
    return slot


def _ventana_animacion(
    inicio: date,
    fin: date,
    hora_desde: Any,
    hora_hasta: Any,
) -> tuple[datetime, datetime]:
    """Rango UTC que cubre las horas UTC elegidas, en el primer y último día."""
    h0 = max(0, min(23, int(hora_desde)))
    h1 = max(h0 + 1, min(24, int(hora_hasta)))
    desde = datetime.combine(inicio, time(h0))
    if h1 >= 24:
        # Cerrar el día: medianoche UTC del día siguiente.
        hasta = datetime.combine(fin + timedelta(days=1), time(0))
    else:
        hasta = datetime.combine(fin, time(h1))

    # El ABI publica con retraso: pedir horas que todavía no existen sólo llena
    # el log de 404. Se recorta al último múltiplo de 10 ya publicado.
    tope = _piso_slot(datetime.now(timezone.utc).replace(tzinfo=None) - _MARGEN_PUBLICACION)
    if hasta > tope:
        hasta = max(desde, tope)

    if hasta <= desde:
        raise ValueError(
            "Esa ventana todavía no tiene datos: el satélite publica con ~20 min "
            "de retraso. Probá con una fecha anterior a hoy."
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

    from .catalog import data_root  # import local: evita el ciclo

    datos_dir = data_root() / f"goes_c13_{sat.lower()}"
    n_ultimos = _ultimos(params)

    if n_ultimos:
        # "Últimos datos": la ventana de fechas no manda. Se resuelve el tramo
        # más nuevo publicado y siempre se baja.
        disponibles_slots = _ultimos_goes(sat, banda, n_ultimos)
        desde, n, paso, falta = disponibles_slots[0], len(disponibles_slots), _PASO_SLOT, True
    elif _snapshot(params):
        # Snapshot: el cuadro exacto que eligió el usuario (hora y minuto UTC).
        desde, n, paso, falta = _slot_pedido(params, fin), 1, _PASO_SLOT, True
    else:
        disponibles = [s for s in _slots_goes(sat, banda) if inicio <= s.date() <= fin]
        lon_sub = _LON_SUBSAT.get(sat.upper(), -75.2)
        cenital = _slot_cenital(inicio, lon_sub)
        ventana = _ventana_animacion(
            inicio, fin, params.get("hora_desde", 0), params.get("hora_hasta", 24)
        )
        desde, n, paso, falta = _plan_slots(
            set(disponibles),
            cenital,
            _bool(params, "animar") and not _snapshot(params),
            ventana,
        )

    # `descargar_goes.py` recorre [desde, hasta) en pasos de `paso` minutos.
    descarga = Step(
        kind="download",
        label=(f"bajando los últimos {n} slots de {banda} ({sat})"
               if n_ultimos else f"bajando {banda} de {sat} ({n} slot(s))"),
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
    # Con "Solo Paraguay" el centro y el radio salen de la caja del país; si no,
    # el globo completo centrado en el punto subsatelital.
    marco = _encuadre_paraguay(params, "radio") or [
        "--centro", f"{lon_sub:g}", "0", "--radio", "90",
    ]
    args = [
        "--sat", sat,
        "--desde", desde.strftime("%Y-%m-%dT%H:%M"),
        "--n", str(n),
        "--paso", str(paso),
        "--px", str(px),
        "--paleta", str(params.get("paleta", "clean_ir")),
        "--geojson", _borde_paraguay(params),
        *marco,
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
    pasos = [descarga, render_step]  # el origen se consulta en cada corrida
    return Plan(pasos=pasos, descarga=descarga)


# --- MUR: SST descargada ya renderizada por GIBS ------------------------
def _mur(params: dict[str, Any], work: Path) -> Plan:
    inicio, fin = _rango_de_la_corrida(params)
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
    pasos = [descarga, render_step]  # el origen se consulta siempre
    return Plan(pasos=pasos, descarga=descarga)


# --- ECMWF: precipitacion y anomalia ------------------------------------
def _crudo_final(carpeta: Path, horizonte: int, paso: int, sufijo: str) -> Path:
    """Crudo del último paso pedido (`crudo_NNN_fhHHH.<ext>`).

    Los descargadores numeran los pasos desde 1, así que el índice sale de la
    posición del último paso en la grilla. Mirar sólo el último archivo es la
    forma barata de saber si la carpeta cubre de verdad el horizonte pedido.
    """
    return carpeta / f"crudo_{horizonte // paso + 1:03d}_fh{horizonte:03d}{sufijo}"


def _crudos_existen(
    producto: str, modelo: str, fecha: str, ciclo: str, horizonte: int, paso: int
) -> bool:
    """Si los crudos ya cubren el horizonte que el render de ECMWF va a leer.

    Antes alcanzaba con que la carpeta tuviera algo: pedir 240 h cuando en disco
    había 144 h dejaba un render condenado a fallar por pasos faltantes.
    """
    from .catalog import data_root  # import local: evita el ciclo

    nombre = "ecmwf" if modelo == "ifs" else modelo
    carpeta = (
        data_root() / f"crudos_precip_{nombre}_{fecha}_{ciclo}z"
        if producto == "precipitacion"
        else data_root() / f"crudos_anom2t_{modelo}_{fecha}_{ciclo}z"
    )
    sufijo = ".npy" if (producto == "precipitacion" and modelo == "aifs-ens") else ".grib2"
    return _crudo_final(carpeta, horizonte, paso, sufijo).is_file()


def _ecmwf_producto(producto: str, params: dict[str, Any], work: Path) -> Plan:
    inicio, _ = _rango(params)
    modelo = str(params.get("modelo", "ifs"))
    corrida = str(params.get("corrida", "00"))
    horizonte = int(params.get("horizonte", 144) or 144)
    px = _px(params, 1400)
    fondo = str(params.get("fondo", "oscuro"))
    # ECMWF publica 3 h hasta 144 h y 6 h de ahí en adelante; los AIFS, cada 6 h
    # siempre. Los dos scripts del repo piden exactamente la misma grilla.
    # Con snapshot se piden sólo dos horas (0 y el horizonte) y se renderiza el
    # póster del último: un mapa en vez de la serie entera.
    snap = _snapshot(params)
    paso_horas = max(1, horizonte) if snap else _paso_horas_ecmwf(modelo, horizonte)
    cuadros = len(range(0, horizonte + 1, paso_horas))

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
        expected=cuadros,
    )
    render_step = Step(
        kind="render",
        label=f"renderizando {cuadros} cuadros",
        script=render_script,
        args=[
            *comunes,
            "--px", str(px),
            "--fondo-globo", fondo,
            *_encuadre_paraguay(params, "radio"),
            "--salidas", str(work),
            *(["--solo-poster"] if snap else []),
        ],
        expected=cuadros + 1,  # el póster de cierre imprime una línea más
    )
    # El origen se consulta en cada corrida; el snapshot igual necesita sus
    # propios crudos (001/002 del pedido recortado).
    pasos = [descarga, render_step]
    return Plan(pasos=pasos, descarga=descarga)


def _precipitacion(params: dict[str, Any], work: Path) -> Plan:
    return _ecmwf_producto("precipitacion", params, work)


def _anomalia(params: dict[str, Any], work: Path) -> Plan:
    return _ecmwf_producto("anomalia_2t", params, work)


# --- SNAPSHOT: una captura GeoColor recortada a Paraguay ----------------
# Las capas v?lidas viven en comun/paraguay.py; si no se puede importar (raro),
# se cae a la lista literal para no romper el pedido.
try:
    from comun.paraguay import CAPAS as _CAPAS_SNAPSHOT
except Exception:  # pragma: no cover
    _CAPAS_SNAPSHOT = {k: None for k in ("truecolor", "snpp", "aqua", "terra",
                                         "geocolor")}

def _snapshot_paraguay(params: dict[str, Any], work: Path) -> Plan:
    inicio, _ = _rango(params)
    hora = max(0, min(23, int(params.get("hora", 15) or 0)))
    try:
        minuto = max(0, min(59, int(params.get("minuto", 0) or 0)))
    except (TypeError, ValueError):
        minuto = 0
    capa = str(params.get("capa", "truecolor"))
    if capa not in _CAPAS_SNAPSHOT:
        capa = "truecolor"
    px = _px(params, 3600, tope=4000)
    try:
        mpp = float(params.get("detalle")) if params.get("detalle") else 0.0
    except (TypeError, ValueError):
        mpp = 0.0
    # El margen llega como porcentaje (0-20) y los scripts lo usan como fracción.
    try:
        margen = max(0.0, min(0.20, float(params.get("margen", 6)) / 100.0))
    except (TypeError, ValueError):
        margen = 0.06

    # El tamaño se pide en metros por píxel (como EOSDIS) o, si no hay, en píxeles:
    # los dos scripts resuelven el mismo lado a partir de la caja del GeoJSON.
    tamano = ["--mpp", f"{mpp:g}"] if mpp > 0 else ["--px", str(px)]
    comun = [
        "--capa", capa,
        "--fecha", inicio.isoformat(),
        "--hora", str(hora),
        "--minuto", str(minuto),
        *tamano,
        "--margen", f"{margen:g}",
    ]
    # Con "última disponible" la fecha la resuelve GIBS: los dos scripts reciben
    # --ultima y el compositor toma el instante del nombre del crudo.
    if _bool(params, "ultima"):
        comun.append("--ultima")
    crudos = work / "crudos"
    descarga = Step(
        kind="download",
        label="bajando la captura de GIBS",
        script="descargar/snapshot_paraguay.py",
        args=[*comun, "--out", str(crudos)],
        expected=1,
    )
    args_render = [*comun, "--entrada", str(crudos), "--salidas", str(work)]
    if not _bool(params, "borde"):
        args_render.append("--sin-borde")
    render_step = Step(
        kind="render",
        label="componiendo la captura",
        script="cuadros/snapshot_paraguay.py",
        args=args_render,
        expected=1,
    )
    return Plan(pasos=[descarga, render_step], descarga=descarga)


# --- VIENTO: 250 mb + extremos de MSLP ----------------------------------
def _carpeta_viento(modelo: str, fecha: str, ciclo: str) -> str:
    """Carpeta de crudos: el IFS conserva el nombre viejo, GFS lleva el modelo."""
    if modelo == "ifs":
        return f"crudos_viento250_{fecha}_{ciclo}z"
    return f"crudos_viento250_{modelo}_{fecha}_{ciclo}z"


def _crudos_viento_existen(modelo: str, fecha: str, ciclo: str, horizonte: int,
                           paso: int) -> bool:
    """Si los crudos de viento cubren el horizonte que el render va a leer."""
    from .catalog import data_root  # import local: evita el ciclo

    carpeta = data_root() / _carpeta_viento(modelo, fecha, ciclo)
    # El viento guarda un GRIB por variable: el ?ltimo paso es el de `u`.
    return _crudo_final(carpeta, horizonte, paso, "_u.grib2").is_file()


def _viento_250(params: dict[str, Any], work: Path) -> Plan:
    inicio, _ = _rango(params)
    modelo = str(params.get("modelo", "ifs"))
    corrida = str(params.get("corrida", "00")).zfill(2)
    horizonte = int(params.get("horizonte", 144) or 144)
    px = _px(params, 1400)
    fondo = str(params.get("fondo", "oscuro"))
    # IFS y GFS publican cada 3 h hasta 144 h: la animación queda fluida.
    # Con snapshot se piden 0 y el horizonte nada más, y se renderiza el último.
    snap = _snapshot(params)
    paso_horas = max(1, horizonte) if snap else _paso_horas_ecmwf(modelo, horizonte)
    cuadros = len(range(0, horizonte + 1, paso_horas))

    comunes = [
        "--modelo", modelo,
        "--fecha", inicio.isoformat(),
        "--ciclo", corrida,
        "--hasta-hora", str(horizonte),
        "--paso", str(paso_horas),
    ]
    descarga = Step(
        kind="download",
        label=f"bajando el viento en 250 mb de {modelo}",
        script="descargar/viento_250_mslp.py",
        args=comunes,
        expected=cuadros,
    )
    render_step = Step(
        kind="render",
        label=f"renderizando {cuadros} cuadros de viento",
        script="cuadros/cuadros_viento_250.py",
        args=[
            *comunes,
            "--px", str(px),
            "--fondo-globo", fondo,
            *_encuadre_paraguay(params, "radio"),
            "--salidas", str(work),
            *(["--solo-poster"] if snap else []),
        ],
        expected=cuadros + 1,  # el póster de cierre imprime una línea más
    )
    # El origen se consulta en cada corrida; el snapshot igual necesita sus
    # propios crudos (001/002 del pedido recortado).
    pasos = [descarga, render_step]
    return Plan(pasos=pasos, descarga=descarga)


# --- FOLLAJE: PACE LANDVI ----------------------------------------------
def _follaje(params: dict[str, Any], work: Path) -> Plan:
    inicio, fin = _rango_de_la_corrida(params)
    px = _px(params, 1400)
    n = max(1, (fin - inicio).days + 1)
    # Dos vestuarios para la misma data: mapa plano (Robinson) o globo realista.
    globo = str(params.get("proyeccion", "plano")) == "globo"
    script = "cuadros/cuadros_follaje_globo.py" if globo else "cuadros/cuadros_follaje.py"

    descarga = Step(
        kind="download",
        label="bajando LANDVI de PACE",
        script="descargar/pace_landvi.py",
        args=["--desde", inicio.isoformat(), "--hasta", fin.isoformat()],
        expected=n,
    )
    render_step = Step(
        kind="render",
        label=f"renderizando el follaje ({'globo' if globo else 'plano'})",
        script=script,
        args=[
            "--desde", inicio.isoformat(),
            "--hasta", fin.isoformat(),
            "--px", str(px),
            # aca --out es la carpeta de cuadros, no la raiz de salidas.
            "--out", str(work / "frames"),
        ],
        expected=n,
    )
    pasos = [descarga, render_step]  # el origen se consulta siempre
    return Plan(pasos=pasos, descarga=descarga)


# --- GOES color real: C01 + C02 + C03 -----------------------------------
def _goes_truecolor(params: dict[str, Any], work: Path) -> Plan:
    inicio, fin = _rango(params)
    sat = str(params.get("satelite", "G19"))
    px = _px(params, 2400)
    n_ultimos = _ultimos(params)
    animar = bool(n_ultimos) or (_bool(params, "animar") and not _snapshot(params))
    # El disco nativo no se puede encuadrar en Paraguay: con el encuadre activo
    # se usa el globo, que es el que acepta centro y recorte.
    disco = (str(params.get("encuadre", "globo")) == "disco"
             and not _bool(params, "paraguay"))

    # C02 es la banda pesada (~410 MB): si esta, el slot existe.
    lon_sub = _LON_SUBSAT.get(sat.upper(), -75.2)
    if n_ultimos:
        # "Últimos datos": los slots nuevos publicados, sin mirar la ventana.
        slots_nuevos = _ultimos_goes(sat, "C02", n_ultimos)
        desde, n, paso, falta = (
            slots_nuevos[0], len(slots_nuevos), _PASO_SLOT, True,
        )
    elif _snapshot(params):
        # Snapshot: el cuadro exacto que eligió el usuario (hora y minuto UTC).
        desde, n, paso, falta = _slot_pedido(params, fin), 1, _PASO_SLOT, True
    else:
        disponibles = [s for s in _slots_goes(sat, "C02") if inicio <= s.date() <= fin]
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
        # Globo centrado en el punto subsatelital o encuadre Paraguay.
        lon_sub = _LON_SUBSAT.get(sat.upper(), -75.2)
        marco = _encuadre_paraguay(params, "recorte")
        if marco:
            centro = marco
        else:
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
                    "--no-lineas", "--no-fronteras", "--borde", _borde_paraguay(params),
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
                    "--no-lineas", "--no-fronteras", "--borde", _borde_paraguay(params),
                    *centro,
                    "--out", str(work / f"truecolor_{desde:%Y-%m-%dT%H%M}.png"),
                ],
                expected=1,
            )

    pasos = [descarga, render_step]  # el origen se consulta en cada corrida
    return Plan(pasos=pasos, descarga=descarga)


# --- MUR: poster realista ----------------------------------------------
def _mur_realista(params: dict[str, Any], work: Path) -> Plan:
    inicio, fin = _rango_de_la_corrida(params)
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
    pasos = [descarga, render_step]  # el origen se consulta siempre
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
    n_ultimos = _ultimos(params)
    animar = bool(n_ultimos) or (_bool(params, "animar") and not _snapshot(params))

    if n_ultimos:
        # "Últimos datos": el bucket del AHI, sin mirar la ventana de fechas.
        slots_nuevos = _ultimos_himawari(n_ultimos)
        desde, n, paso, falta = (
            slots_nuevos[0], len(slots_nuevos), _PASO_SLOT, True,
        )
    elif _snapshot(params):
        # Snapshot: el cuadro exacto que eligió el usuario (hora y minuto UTC).
        desde, n, paso, falta = _slot_pedido(params, fin), 1, _PASO_SLOT, True
    else:
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

    # Disco completo centrado en el punto subsatelital (Himawari no tiene la
    # sección "Solo Paraguay").
    marco = ["--centro", f"{_LON_SUBSAT['H09']:g}", "0", "--radio", "90"]
    render_step = Step(
        kind="render",
        label=f"renderizando {n} cuadro(s) de Himawari",
        script="cuadros/cuadros_himawari_ir.py",
        args=[
            "--desde", desde.strftime("%Y-%m-%dT%H:%M"),
            "--n", str(n),
            "--paso", str(paso),
            "--px", str(px),
            # Globo completo centrado en el punto subsatelital, o Paraguay.
            *marco,
            "--datos", str(_carpeta_himawari()),
            "--out", str(work),
            "--frames", str(work / "frames"),
            "--lote", "1",
        ],
        expected=n,
    )

    pasos = [descarga, render_step]  # el origen se consulta en cada corrida
    return Plan(pasos=pasos, descarga=descarga)



# --- GOES: una banda cruda con el diseno del color real ----------------
def _goes_banda(params: dict[str, Any], work: Path) -> Plan:
    inicio, fin = _rango(params)
    sat = str(params.get("satelite", "G19"))
    banda = str(params.get("banda", "C13"))
    px = _px(params, 2712)
    n_ultimos = _ultimos(params)
    animar = bool(n_ultimos) or (_bool(params, "animar") and not _snapshot(params))

    if n_ultimos:
        # "Últimos datos": la ventana de fechas no manda y siempre se baja.
        slots_nuevos = _ultimos_goes(sat, banda, n_ultimos)
        desde, n, paso, falta = slots_nuevos[0], len(slots_nuevos), _PASO_SLOT, True
    elif _snapshot(params):
        # Snapshot: el cuadro exacto que eligió el usuario (hora y minuto UTC).
        desde, n, paso, falta = _slot_pedido(params, fin), 1, _PASO_SLOT, True
    else:
        disponibles = [s for s in _slots_goes(sat, banda) if inicio <= s.date() <= fin]
        lon_sub = _LON_SUBSAT.get(sat.upper(), -75.2)
        cenital = _slot_cenital(inicio, lon_sub)
        ventana = _ventana_animacion(
            inicio, fin, params.get("hora_desde", 0), params.get("hora_hasta", 24)
        )
        desde, n, paso, falta = _plan_slots(set(disponibles), cenital, animar, ventana)

    lon_sub = _LON_SUBSAT.get(sat.upper(), -75.2)
    descarga = Step(
        kind="download",
        label=(f"bajando los últimos {n} slots de {banda} ({sat})"
               if n_ultimos else f"bajando {banda} de {sat} ({n} slot(s))"),
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

    marco = _encuadre_paraguay(params, "recorte") or [
        "--centro", f"{lon_sub:g}", "0", "--recorte", "1.0",
    ]
    comunes = [
        "--banda", banda,
        "--sat", sat,
        "--desde", desde.strftime("%Y-%m-%dT%H:%M"),
        "--n", str(n),
        "--paso", str(paso),
        "--px", str(px),
        "--paleta", str(params.get("paleta", "clean_ir")),
        # Globo completo centrado en el punto subsatelital, o Paraguay.
        *marco,
        "--borde", _borde_paraguay(params),
    ]
    if animar and n > 1:
        render_step = Step(
            kind="render",
            label=f"{n} cuadro(s) de {banda}",
            script="prototipos/poster_goes_banda.py",
            args=[*comunes, "--frames", str(work / "frames")],
            expected=n,
        )
    else:
        render_step = Step(
            kind="render",
            label=f"poster {banda} {px}px",
            script="prototipos/poster_goes_banda.py",
            args=[*comunes, "--out", str(work / f"{sat}_{banda}_{desde:%Y-%m-%dT%H%M}.png")],
            expected=1,
        )

    pasos = [descarga, render_step]  # el origen se consulta en cada corrida
    return Plan(pasos=pasos, descarga=descarga)



# --- GEOCOLOR: color real de dia + IR y luces de noche -----------------
def _geocolor(params: dict[str, Any], work: Path) -> Plan:
    inicio, fin = _rango(params)
    px = _px(params, 1400)
    n_ultimos = _ultimos(params)
    animar = bool(n_ultimos) or (_bool(params, "animar") and not _snapshot(params))
    sat = str(params.get("satelite", "G19"))
    lon_sub = _LON_SUBSAT.get(sat.upper(), -75.2)

    cenital = _slot_cenital(inicio, lon_sub)
    if n_ultimos:
        # "Últimos datos": se resuelve contra GIBS, que es quien publica GeoColor.
        slots = _ultimos_geocolor(sat, n_ultimos)
        desde, n, paso = slots[0], len(slots), _PASO_SLOT
    elif _snapshot(params):
        # Snapshot: el cuadro exacto que eligió el usuario (hora y minuto UTC).
        desde, n, paso = _slot_pedido(params, fin), 1, _PASO_SLOT
    else:
        ventana = _ventana_animacion(
            inicio, fin, params.get("hora_desde", 0), params.get("hora_hasta", 24)
        )
        # GeoColor no tiene .nc por slot: el estado se mira en la carpeta de cuadros
        # de la cache, que el descargador arma con el mismo nombre que el render.
        desde, n, paso, _ = _plan_slots(set(), cenital, animar, ventana)

    etiqueta = f"frames_geocolor_globo_{sat}_{desde:%Y-%m-%dT%H%M}_{n}f_{px}px"
    carpeta = work / etiqueta
    falta = not (carpeta.is_dir() and next(carpeta.glob("crudo_*.jpg"), None) is not None)

    # El hemisferio visible depende del satélite: la caja va centrada en él. Para
    # GOES-West cruza el antimeridiano y los dos scripts la parten en dos mitades.
    # Con "Solo Paraguay" se pide la caja del país SIN --globo: el render sale
    # como mapa plano cuadrado (el mismo encuadre del producto Snapshot).
    py = _bool(params, "paraguay")
    if py:
        comunes = [
            "--sat", sat,
            *_encuadre_paraguay(params, "bbox"),
            "--desde", desde.strftime("%Y-%m-%dT%H:%M"),
            "--n", str(n),
            "--paso", str(paso),
            "--px", str(px),
            "--out", str(work),
        ]
    else:
        caja = [lon_sub - 90.0, -80.0, lon_sub + 90.0, 80.0]
        comunes = [
            "--globo",
            "--sat", sat,
            "--bbox", *[f"{valor:g}" for valor in caja],
            "--desde", desde.strftime("%Y-%m-%dT%H:%M"),
            "--n", str(n),
            "--paso", str(paso),
            "--px", str(px),
            "--out", str(work),
        ]
    descarga = Step(
        kind="download",
        label=f"bajando GeoColor de {sat} ({n} cuadro(s))",
        script="descargar/geocolor.py",
        args=comunes,
        expected=max(1, n),
    )
    render_step = Step(
        kind="render",
        label=f"renderizando {n} cuadro(s) de GeoColor",
        script="cuadros/cuadros_geocolor.py",
        args=[
            *comunes,
            # Globo completo centrado en el punto subsatelital, o el contorno de
            # Paraguay sobre la caja recortada.
            *([] if py else ["--centro", f"{lon_sub:g}", "0"]),
            "--geojson", _borde_paraguay(params),
        ],
        expected=n,
    )

    pasos = [descarga, render_step]  # el origen se consulta siempre
    return Plan(pasos=pasos, descarga=descarga)



# --- VIIRS NOAA-20: true color diario de GIBS --------------------------
def _truecolor_viirs(params: dict[str, Any], work: Path) -> Plan:
    inicio, fin = _rango_de_la_corrida(params)
    px = _px(params, 2000)
    animar = _bool(params, "animar") and not _snapshot(params)
    capa = str(params.get("capa", "VIIRS_NOAA20_CorrectedReflectance_TrueColor"))

    # La capa es una composicion DIARIA: un cuadro por dia, sin horarios.
    dias = max(1, (fin - inicio).days + 1)
    n = min(dias, 31) if animar else 1
    hasta = fin if animar else inicio

    comunes = [
        "--desde", inicio.isoformat(),
        "--hasta", hasta.isoformat(),
        "--paso", "1",
        "--px", str(px),
        "--capa", capa,
        "--out", str(work),
    ]
    descarga = Step(
        kind="download",
        label=f"bajando true color NOAA-20 ({n} dia(s))",
        script="descargar/truecolor.py",
        args=comunes,
        expected=n,
    )
    render_step = Step(
        kind="render",
        label=f"renderizando {n} cuadro(s) de NOAA-20",
        script="cuadros/cuadros_truecolor.py",
        args=[
            *comunes,
            *_encuadre_paraguay(params, "radio"),
            "--geojson", _borde_paraguay(params),
        ],
        expected=n,
    )

    etiqueta = f"frames_truecolor_viirs_noaa20_globo_{inicio:%Y-%m-%dT}0000_{n}f_{px}px"
    carpeta = work / etiqueta
    falta = not (carpeta.is_dir() and next(carpeta.glob("crudo_*.jpg"), None) is not None)

    pasos = [descarga, render_step]  # el origen se consulta siempre
    return Plan(pasos=pasos, descarga=descarga)


# --- GOES: RGB oficial de tres canales (Dust, Air Mass, Fire Temperature) ---
def _bandas_rgb(producto: str) -> tuple[str, ...]:
    """Bandas ABI de la receta, desde la misma tabla que usa el render."""
    comun = RAIZ_REPO / "comun"
    if str(comun) not in sys.path:
        sys.path.insert(0, str(comun))
    from rgb_goes import bandas

    return tuple(bandas(producto))


def _slots_goes_rgb(sat: str, bandas: tuple[str, ...]) -> list[datetime]:
    """Slots con `.nc` de TODAS las bandas de la receta."""
    conjuntos = [set(_slots_goes(sat, banda)) for banda in bandas]
    return sorted(set.intersection(*conjuntos)) if conjuntos else []


def _ultimos_goes_rgb(sat: str, producto: str, n: int) -> list[datetime]:
    """Los `n` slots más nuevos con TODAS las bandas publicadas en NOAA S3.

    `goes_reciente` es stdlib puro: pide el listado una sola vez por hora y sirve
    para las 3-4 bandas del producto (el `.venv` de la API no tiene xarray).
    """
    comun = RAIZ_REPO / "comun"
    if str(comun) not in sys.path:
        sys.path.insert(0, str(comun))
    try:
        from goes_reciente import ultimos_slots_conjunto

        slots = ultimos_slots_conjunto(sat, _bandas_rgb(producto), n)
    except Exception:  # noqa: BLE001 - offline: molesta más un job muerto que un fallback
        slots = []
    if slots:
        return slots

    locales = _slots_goes_rgb(sat, _bandas_rgb(producto))
    if locales:
        return locales[-n:]
    raise ValueError(
        f"No hay datos de {sat} {producto}: NOAA S3 no respondió y el disco está "
        "vacío. Revisá la conexión y volvé a intentar."
    )


def _goes_rgb(params: dict[str, Any], work: Path, producto: str) -> Plan:
    """Plan de un RGB oficial: baja todas sus bandas y compone el globo."""
    inicio, fin = _rango(params)
    sat = str(params.get("satelite", "G19"))
    bandas = _bandas_rgb(producto)
    px = _px(params, 2712)
    n_ultimos = _ultimos(params)
    animar = bool(n_ultimos) or (_bool(params, "animar") and not _snapshot(params))

    if n_ultimos:
        slots_nuevos = _ultimos_goes_rgb(sat, producto, n_ultimos)
        desde, n, paso, falta = slots_nuevos[0], len(slots_nuevos), _PASO_SLOT, True
    elif _snapshot(params):
        desde, n, paso, falta = _slot_pedido(params, fin), 1, _PASO_SLOT, True
    else:
        disponibles = [
            s for s in _slots_goes_rgb(sat, bandas) if inicio <= s.date() <= fin
        ]
        lon_sub = _LON_SUBSAT.get(sat.upper(), -75.2)
        cenital = _slot_cenital(inicio, lon_sub)
        ventana = _ventana_animacion(
            inicio, fin, params.get("hora_desde", 0), params.get("hora_hasta", 24)
        )
        desde, n, paso, falta = _plan_slots(set(disponibles), cenital, animar, ventana)

    lon_sub = _LON_SUBSAT.get(sat.upper(), -75.2)
    descarga = Step(
        kind="download",
        label=(f"bajando los últimos {n} slots de {producto} ({sat})"
               if n_ultimos else f"bajando {producto} de {sat} ({n} slot(s))"),
        script="descargar/descargar_goes_rgb.py",
        args=[
            "--producto", producto,
            "--sat", sat,
            "--desde", desde.isoformat(),
            "--hasta", (desde + timedelta(minutes=paso * n)).isoformat(),
            "--paso", str(paso),
        ],
        expected=max(1, math.ceil(n / 10)),
    )

    marco = _encuadre_paraguay(params, "recorte") or [
        "--centro", f"{lon_sub:g}", "0", "--recorte", "1.0",
    ]
    comunes = [
        "--producto", producto,
        "--sat", sat,
        "--desde", desde.strftime("%Y-%m-%dT%H:%M"),
        "--n", str(n),
        "--paso", str(paso),
        "--px", str(px),
        # Globo completo centrado en el punto subsatelital, o Paraguay.
        *marco,
        "--borde", _borde_paraguay(params),
    ]
    if animar and n > 1:
        render_step = Step(
            kind="render",
            label=f"{n} cuadro(s) de {producto}",
            script="prototipos/poster_goes_rgb.py",
            args=[*comunes, "--frames", str(work / "frames")],
            expected=n,
        )
    else:
        render_step = Step(
            kind="render",
            label=f"poster {producto} {px}px",
            script="prototipos/poster_goes_rgb.py",
            args=[*comunes, "--out", str(work / f"{sat}_{producto}_{desde:%Y-%m-%dT%H%M}.png")],
            expected=1,
        )

    return Plan(pasos=[descarga, render_step], descarga=descarga)


_CONSTRUCTORES = {
    "goes_c13": _goes,
    "goes_truecolor": _goes_truecolor,
    "goes_banda": _goes_banda,
    "goes_dust": lambda p, w: _goes_rgb(p, w, "dust"),
    "goes_airmass": lambda p, w: _goes_rgb(p, w, "airmass"),
    "goes_firetemp": lambda p, w: _goes_rgb(p, w, "firetemp"),
    "geocolor": _geocolor,
    "truecolor_viirs": _truecolor_viirs,
    "mur_sst": _mur,
    "mur_realista": _mur_realista,
    "precipitacion_ecmwf": _precipitacion,
    "anomalia_2t": _anomalia,
    "viento_250": _viento_250,
    "snapshot_paraguay": _snapshot_paraguay,
    "follaje": _follaje,
    "himawari": _himawari,
}


def python_repo() -> Path:
    return PYTHON_REPO


def repo_listo() -> bool:
    return PYTHON_REPO.is_file()


