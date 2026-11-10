"""Focos de calor de NASA FIRMS: caja, CSV y ventana de tiempo.

Lo comparten el descargador y el compositor. El primero pide el CSV a la API `area`
y lo guarda; el segundo lo lee y decide qué focos entran en la captura. La ventana y
el nombre del archivo viven acá para que los dos lados calculen lo mismo.

La API pide un MAP_KEY gratuito (https://firms.modaps.eosdis.nasa.gov/api/map_key/):
va en `datos/firms_map_key.txt` o en la variable `FIRMS_MAP_KEY`. Sin clave el
servicio responde `400 Invalid MAP_KEY.` — no hay forma de saltearlo.

Sólo se usan fuentes NRT: las de procesamiento estándar (`*_SP`) llegan con días de
atraso y un snapshot es, por definición, lo más reciente que hay.
"""
from __future__ import annotations

import csv
import io
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

#: Dónde se busca la clave si no está en el entorno (gitignoreado).
CLAVE_ARCHIVO = RAIZ / "datos" / "firms_map_key.txt"

API = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

#: Fuentes NRT agrupadas por sensor. S-NPP publica de forma intermitente (medido:
#: 200 focos el 2026-11-01 y 0 el 06 y el 10), así que no es el default; S-NPP y
#: MODIS quedan como opción explícita.
FUENTES = {
    "viirs": ("VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT"),
    "snpp": ("VIIRS_SNPP_NRT",),
    "modis": ("MODIS_NRT",),
    "todos": ("VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT", "VIIRS_SNPP_NRT", "MODIS_NRT"),
}
FUENTE = "viirs"

#: Ventanas ofrecidas por la UI. `dia` es el día UTC completo de la captura y es el
#: default porque los True Color son compuestos diarios; las demás son horas a cada
#: lado del slot, para GeoColor.
VENTANAS = ("dia", "3h", "6h", "12h")
VENTANA = "dia"

#: Días que FIRMS deja pedir de una sola vez.
MAX_DIAS = 5

#: Cómo se lee `confidence`: VIIRS manda `l/n/h`, MODIS un 0-100.
_CONFIANZA = {"l": "baja", "n": "nominal", "h": "alta"}
_LETRA = {"baja": "l", "nominal": "n", "alta": "h"}

#: Paleta única para todos los renders: el compositor la usa en RGB y los pósters
#: en hex, así un foco no cambia de color según el producto.
COLORES_FOCO = {
    "baja": (255, 209, 64),
    "nominal": (255, 138, 26),
    "alta": (255, 61, 0),
}


def color_foco(confianza: str) -> tuple[int, int, int]:
    """Color RGB del foco según la confianza (nominal si viene raro)."""
    return COLORES_FOCO.get(confianza, COLORES_FOCO["nominal"])


def color_hex(confianza: str) -> str:
    """El mismo color, en hex, para matplotlib."""
    return "#%02x%02x%02x" % color_foco(confianza)

#: Columnas que se conservan al normalizar el CSV (las mismas que lee `leer_texto`).
COLUMNAS = ("latitude", "longitude", "frp", "confidence", "acq_date", "acq_time",
            "satellite", "instrument", "daynight")


@dataclass(frozen=True)
class Foco:
    """Un punto de calor detectado por un satélite."""

    lat: float
    lon: float
    frp: float            # potencia radiativa (MW): el tamaño del fuego
    confianza: str        # baja | nominal | alta
    cuando: datetime      # UTC, del propio `acq_date` + `acq_time`
    satelite: str
    instrumento: str
    dia_noche: str        # D | N


def clave_mapa() -> str:
    """MAP_KEY de FIRMS: variable de entorno o `datos/firms_map_key.txt`."""
    valor = (os.environ.get("FIRMS_MAP_KEY") or "").strip()
    if valor:
        return valor
    try:
        valor = CLAVE_ARCHIVO.read_text(encoding="utf-8").strip()
    except OSError:
        valor = ""
    if not valor:
        raise SystemExit(
            "Falta el MAP_KEY de FIRMS.\n"
            "Pedilo gratis en https://firms.modaps.eosdis.nasa.gov/api/map_key/ y guardalo en\n"
            f"  {CLAVE_ARCHIVO}\n"
            "o en la variable de entorno FIRMS_MAP_KEY."
        )
    return valor


def caja_texto(caja) -> str:
    """`oeste,sur,este,norte` como lo pide la API (5 decimales, sin espacios).

    Acepta `"world"` tal cual: un póster de disco completo no tiene recorte regional
    y la API tiene ese atajo documentado.
    """
    if isinstance(caja, str):
        return caja
    o, s, e, n = (float(v) for v in caja)
    return f"{o:.5f},{s:.5f},{e:.5f},{n:.5f}"


def url_focos(clave: str, fuente: str, caja, dia: date, dias: int = 1) -> str:
    """URL del CSV para una fuente, una caja y una ventana de días."""
    dias = max(1, min(MAX_DIAS, int(dias)))
    return f"{API}/{clave}/{fuente}/{caja_texto(caja)}/{dias}/{dia:%Y-%m-%d}"


def ventana(cuando: datetime, modo: str = VENTANA) -> tuple[datetime, datetime]:
    """Intervalo `[desde, hasta)` de focos que corresponde a la captura.

    `dia` es el día UTC completo: los True Color de GIBS son un compuesto diario, así
    que media hora de fuegos no representa la imagen. Las ventanas en horas son para
    GeoColor, que sí es un slot de 10 minutos.
    """
    if modo not in VENTANAS:
        modo = VENTANA
    base = cuando.replace(second=0, microsecond=0)
    if modo == "dia":
        inicio = base.replace(hour=0, minute=0)
        return inicio, inicio + timedelta(days=1)
    horas = int(modo.removesuffix("h"))
    return base - timedelta(hours=horas), base + timedelta(hours=horas)


def nombre_csv_rango(desde: datetime, hasta: datetime) -> str:
    """Nombre del CSV de un rango (`[desde, hasta)`) ya resuelto."""
    return f"focos_{desde:%Y%m%dT%H%M}_{hasta:%Y%m%dT%H%M}.csv"


def nombre_csv(cuando: datetime, modo: str = VENTANA) -> str:
    """Nombre del CSV de focos de esa ventana (igual en los dos scripts)."""
    return nombre_csv_rango(*ventana(cuando, modo))


def etiqueta(cuando: datetime, modo: str = VENTANA) -> str:
    """Rótulo corto de la ventana, para la leyenda de la captura."""
    desde, hasta = ventana(cuando, modo)
    if modo == "dia":
        return f"{desde:%Y-%m-%d}"
    if hasta.date() == desde.date():
        return f"{desde:%Y-%m-%d %H:%M}-{hasta:%H:%M}"
    return f"{desde:%Y-%m-%d %H:%M}-{hasta:%Y-%m-%d %H:%M}"


def _leer_confianza(texto: str) -> str:
    """Confianza normalizada, venga como letra (VIIRS) o como número (MODIS)."""
    valor = (texto or "").strip().lower()
    if valor in _CONFIANZA:
        return _CONFIANZA[valor]
    try:
        numero = float(valor)
    except ValueError:
        return "nominal"
    if numero >= 80:
        return "alta"
    if numero >= 30:
        return "nominal"
    return "baja"


def _cuando(dia: str, hora: str) -> datetime | None:
    """`acq_date` + `acq_time` -> datetime UTC. `acq_time` viene sin cero a la izquierda."""
    try:
        fecha = date.fromisoformat((dia or "").strip())
        minutos = int((hora or "").strip() or 0)
    except (TypeError, ValueError):
        return None
    horas, resto = divmod(minutos, 100)
    if not (0 <= horas <= 23 and 0 <= resto <= 59):
        return None
    return datetime(fecha.year, fecha.month, fecha.day, horas, resto)


def _numero(valor: str, por_defecto: float = 0.0) -> float:
    try:
        return float((valor or "").strip())
    except (TypeError, ValueError):
        return por_defecto


def leer_texto(texto: str) -> list[Foco]:
    """Focos de un CSV de FIRMS (o del CSV normalizado que escribe el descargador).

    Tolera filas rotas: una línea rara no se lleva puesto el resto del archivo.
    """
    focos: list[Foco] = []
    for fila in csv.DictReader(io.StringIO(texto)):
        cuando = _cuando(fila.get("acq_date", ""), fila.get("acq_time", ""))
        if cuando is None:
            continue
        lat = _numero(fila.get("latitude"), 999.0)
        lon = _numero(fila.get("longitude"), 999.0)
        if abs(lat) > 90 or abs(lon) > 180:
            continue
        focos.append(Foco(
            lat=lat,
            lon=lon,
            frp=_numero(fila.get("frp")),
            confianza=_leer_confianza(fila.get("confidence", "")),
            cuando=cuando,
            satelite=(fila.get("satellite") or "").strip(),
            instrumento=(fila.get("instrument") or "").strip(),
            dia_noche=(fila.get("daynight") or "").strip().upper()[:1],
        ))
    return focos


def leer(ruta: Path) -> list[Foco]:
    """Focos de un CSV ya guardado en disco."""
    return leer_texto(Path(ruta).read_text(encoding="utf-8", errors="replace"))


def leer_carpeta(carpeta) -> list[Foco]:
    """Todos los focos de la carpeta, uniendo los `focos_*.csv` que haya.

    Es lo que usan los renders de serie: el descargador deja un CSV por rango y el
    render no necesita saber cómo se llaman ni cuántos días cubren.
    """
    focos: list[Foco] = []
    for ruta in sorted(Path(carpeta).glob("focos_*.csv")):
        try:
            focos.extend(leer(ruta))
        except OSError:
            continue
    return focos


def fila(foco: Foco) -> dict[str, str]:
    """El foco como fila del CSV normalizado (mismas columnas que FIRMS)."""
    return {
        "latitude": f"{foco.lat:.5f}",
        "longitude": f"{foco.lon:.5f}",
        "frp": f"{foco.frp:.2f}",
        "confidence": _LETRA.get(foco.confianza, "n"),
        "acq_date": foco.cuando.date().isoformat(),
        "acq_time": foco.cuando.strftime("%H%M"),
        "satellite": foco.satelite,
        "instrument": foco.instrumento,
        "daynight": foco.dia_noche,
    }


def escribir(ruta: Path, focos: list[Foco]) -> Path:
    """Guarda los focos en el CSV normalizado, con el orden de `COLUMNAS`."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(ruta.suffix + ".parcial")
    with tmp.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(COLUMNAS),
                                  extrasaction="ignore")
        escritor.writeheader()
        for foco in focos:
            escritor.writerow(fila(foco))
    tmp.replace(ruta)
    return ruta


def filtrar(focos: list[Foco], desde: datetime, hasta: datetime) -> list[Foco]:
    """Los focos dentro de `[desde, hasta)`."""
    return [foco for foco in focos if desde <= foco.cuando < hasta]
