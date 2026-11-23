"""Lectura de las capacidades WMTS de NASA GIBS, sin tocar la red.

GIBS publica en un XML qué capas existen y **hasta qué día** tiene dato cada una.
Los compuestos que se arman hacia atrás (por ejemplo `OCI_PACE_True_Color`) tienen
que respetar ese techo: pedir un día que la capa todavía no publicó devuelve 404 y
deja el compuesto vacío.

Este módulo sólo interpreta el XML. La descarga la hace quien lo necesita
(`prototipos/`, `descargar/`), porque `comun/` no importa nada de red.
"""
from __future__ import annotations

import re
from datetime import date

#: Capacidades WMTS (EPSG:4326) con el dominio temporal de cada capa.
CAPACIDADES = "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/1.0.0/WMTSCapabilities.xml"

#: Capa del compuesto de color real de PACE/OCI.
PACE_TRUE_COLOR = "OCI_PACE_True_Color"

# Un tramo del dominio temporal: `AAAA-MM-DD/AAAA-MM-DD/P1D` o un día suelto.
_RANGO = re.compile(r"(\d{4}-\d{2}-\d{2})(?:/(\d{4}-\d{2}-\d{2}))?(?:/P1D)?")


def ultima_fecha_de_capa(xml: str, capa: str) -> date | None:
    """Última fecha publicada de `capa`, según el dominio temporal del XML.

    Devuelve ``None`` si el XML no trae la capa o no declara fechas: el llamador
    decide si sigue sin recortar en vez de fallar.
    """
    inicio = xml.find(f"<ows:Identifier>{capa}</ows:Identifier>")
    if inicio < 0:
        return None
    fin = xml.find("</Layer>", inicio)
    bloque = xml[inicio:fin if fin >= 0 else inicio + 20000]

    fechas: list[str] = []
    for valor in re.findall(r"<Value>(.*?)</Value>", bloque, re.S):
        for tramo in valor.split(","):
            encontrado = _RANGO.fullmatch(tramo.strip())
            if encontrado:
                fechas.append(encontrado.group(2) or encontrado.group(1))

    if not fechas:
        return None
    try:
        return max(date.fromisoformat(f) for f in fechas)
    except ValueError:
        return None
