"""Traduccion del pedido NISAR a comandos reales del repo.

Es el mismo plan que usa la app general, recortado a lo que necesita este flujo:
descargar el ``.h5`` desde ASF y correr el prototipo del producto elegido. Los
scripts son los del repo (``descargar/nisar.py`` y ``prototipos/nisar_*.py``);
aca solo se arma la lista de argumentos, con las mismas validaciones de siempre.

Productos: ``recorte``, ``rvi``, ``cambio``, ``serie``, ``geotiff``, ``agua``,
``incendio``, ``fusion`` y ``descarga`` (solo baja el ``.h5``).
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import RAIZ_REPO

#: El visor arma un unico producto interno; el JobManager lo resuelve por id.
PRODUCT_ID = "nisar_render"
PRODUCT_NAME = "NISAR - analisis de escena"

PRODUCTOS = (
    "recorte",
    "rvi",
    "cambio",
    "serie",
    "geotiff",
    "agua",
    "incendio",
    "fusion",
    "sme2",
    "gunw",
    "descarga",
)


@dataclass(frozen=True)
class Step:
    """Un comando del repo, listo para ejecutar."""

    kind: str  # download | render
    label: str
    script: str  # ruta relativa a la raiz del repo
    args: list[str]
    expected: int = 0  # lineas de progreso esperadas; 0 = indeterminado


@dataclass
class Plan:
    """Que correr ahora y que descarga queda de rescate."""

    pasos: list[Step] = field(default_factory=list)
    descarga: Step | None = None


def _nisar_nombre(valor: str, nombre: str) -> str:
    if not valor or any(c in valor for c in '\\/:*?"<>|'):
        raise ValueError(f"Parametro NISAR invalido: {nombre}")
    return valor


def _nisar_instante(nombre: str) -> str:
    """Instante de adquisicion del granulo, como ``AAAAMMDDTHHMMSS`` (ordenable)."""
    encontrado = re.search(r"(\d{8})T(\d{6})", nombre or "")
    return f"{encontrado.group(1)}T{encontrado.group(2)}" if encontrado else ""


def _exigir_orden(antes: str, despues: str) -> None:
    """Comparar dos escenas solo tiene sentido si la anterior es mas vieja.

    Sin este control, elegir una escena posterior como "anterior" invierte el
    signo del cambio y produce hectareas que no existen.
    """
    i_antes = _nisar_instante(antes)
    i_despues = _nisar_instante(despues)
    if not i_antes or not i_despues:
        return
    if i_antes >= i_despues:
        raise ValueError(
            "La escena anterior tiene que ser mas vieja que la seleccionada: "
            f"llego antes={i_antes} y despues={i_despues}."
        )


def _nisar_coleccion(url: str, valor: str) -> str:
    """La URL de ASF manda: ``.../NISAR/<coleccion>/<granulo>/...``.

    Los granulos provisionales viven en ``NISAR_L2_GCOV_PROVISIONAL_V1`` y el
    ``collectionName`` del JSON puede venir vacio. Deducirla de la URL evita un
    404 al bajar una fecha anterior.
    """
    coleccion = (valor or "").strip()
    if not coleccion and "/NISAR/" in url:
        coleccion = url.split("/NISAR/", 1)[1].split("/", 1)[0]
    return _nisar_nombre(coleccion or "NISAR_L2_GCOV_V1", "coleccion")


def _nisar_descarga(
    granulo: str,
    url: str,
    coleccion: str,
    raiz: Path,
    etiqueta: str,
    sello: Path | None = None,
) -> Step:
    args = [
        "--url", url,
        "--granulo", granulo,
        "--destino", str(raiz),
        "--coleccion", coleccion,
    ]
    if sello is not None:
        args += ["--sello", str(sello)]
    return Step(
        kind="download",
        label=f"descargando {etiqueta} {granulo[-24:]}",
        script="descargar/nisar.py",
        args=args,
        expected=40,
    )


def _nisar_en_disco(raiz: Path, coleccion: str, granulo: str) -> bool:
    """Si el ``.h5`` ya esta, no se agrega el paso de descarga ni se pide URL."""
    return (raiz / coleccion / f"{granulo}.h5").is_file()


def _nisar_escenas(params: dict[str, Any]) -> list[dict[str, str]]:
    """Fechas extra de la serie: ``[{"id","url","coleccion"}]`` en un JSON.

    La UI manda las que no estan en disco con su URL de ASF para que la receta
    las baje antes de correr el CUSUM. Las que ya estan se pueden mandar sin URL.
    """
    crudo = params.get("escenas")
    if crudo in (None, ""):
        return []
    if isinstance(crudo, str):
        try:
            crudo = json.loads(crudo)
        except json.JSONDecodeError as exc:
            raise ValueError("La lista de escenas de la serie no es JSON valido.") from exc
    if not isinstance(crudo, list):
        raise ValueError("La lista de escenas de la serie tiene que ser un arreglo.")
    escenas: list[dict[str, str]] = []
    for indice, entrada in enumerate(crudo):
        if not isinstance(entrada, dict):
            raise ValueError(f"Escena {indice + 1} de la serie invalida.")
        granulo = _nisar_nombre(str(entrada.get("id") or "").strip(), f"escena {indice + 1}")
        url = str(entrada.get("url") or "").strip()
        coleccion = str(entrada.get("coleccion") or "").strip()
        if url and not url.startswith("https://"):
            raise ValueError(f"La escena {granulo} no trae una URL https de descarga.")
        escenas.append({"id": granulo, "url": url, "coleccion": coleccion})
    return escenas


def _nisar_render(params: dict[str, Any], work: Path) -> Plan:
    """Plan del visor: descarga la/s escena/s y corre el producto elegido.

    La descarga es reanudable y saltea el archivo si ya esta: cambiar de producto
    no vuelve a bajar 1.9 GB por escena.
    """
    producto = str(params.get("producto") or "recorte").strip().lower()
    if producto not in PRODUCTOS:
        raise ValueError(f"Producto NISAR desconocido: {producto}")

    nivel = str(params.get("nivel") or "GCOV").strip().upper()
    if producto == "sme2":
        if nivel != "SME2":
            raise ValueError(
                f"El producto sme2 usa una escena SME2; la escena elegida es "
                f"{nivel}. Elegí una escena SME2 para humedad del suelo."
            )
    elif producto == "gunw":
        if nivel != "GUNW":
            raise ValueError(
                f"El producto gunw usa una escena GUNW; la escena elegida es "
                f"{nivel}. Elegí una escena GUNW para el interferograma."
            )
    elif nivel != "GCOV" and producto != "descarga":
        raise ValueError(
            f"El producto {producto} usa GCOV; la escena elegida es {nivel}. "
            "Elegí una escena GCOV. GSLC queda como búsqueda y "
            "descarga hasta tener su producto."
        )

    granulo = _nisar_nombre(str(params.get("granulo") or "").strip(), "granulo")
    url = str(params.get("url") or "").strip()
    coleccion = _nisar_coleccion(url, str(params.get("coleccion") or ""))
    if not url.startswith("https://"):
        raise ValueError("La escena NISAR no trae una URL https de descarga.")

    comun = RAIZ_REPO / "comun"
    if str(comun) not in sys.path:
        sys.path.insert(0, str(comun))
    from rutas import raiz_nisar  # import local: igual que los otros helpers

    raiz_h5 = raiz_nisar()
    h5 = raiz_h5 / coleccion / f"{granulo}.h5"

    # Bajar una escena no necesita caja: el .h5 es el mismo para cualquier recorte.
    bbox = str(params.get("bbox") or "").strip()
    oeste = sur = este = norte = 0.0
    if bbox or producto != "descarga":
        try:
            oeste, sur, este, norte = [float(v) for v in bbox.split(",")]
        except (AttributeError, ValueError) as exc:
            raise ValueError("La caja NISAR debe ser oeste,sur,este,norte") from exc
        if not (-180 <= oeste < este <= 180 and -90 <= sur < norte <= 90):
            raise ValueError("La caja NISAR esta fuera de rango o invertida.")

    try:
        px = max(800, min(int(params.get("px", 2400)), 4096))
    except (TypeError, ValueError):
        px = 2400

    if producto == "descarga":
        sello = work / "nisar_descarga.json"
        return Plan(
            pasos=[_nisar_descarga(granulo, url, coleccion, raiz_h5, "escena", sello)]
        )

    pasos: list[Step] = [
        _nisar_descarga(granulo, url, coleccion, raiz_h5, "escena"),
    ]
    geojson = str(RAIZ_REPO / "datos" / "paraguay_gadm.json")
    bbox_final = f"{oeste:g},{sur:g},{este:g},{norte:g}"

    if producto == "rvi":
        render = Step(
            kind="render",
            label=f"calculando RVI a {px} px",
            script="prototipos/nisar_rvi.py",
            args=[
                "--h5", str(h5),
                "--bbox", bbox_final,
                "--px", str(px),
                "--out", str(work / f"nisar_rvi_{px}.png"),
                "--geojson", geojson,
            ],
            expected=5,
        )
    elif producto == "agua":
        try:
            hh_max = max(-40.0, min(float(params.get("hh_max", -20.0)), 0.0))
        except (TypeError, ValueError):
            hh_max = -20.0
        try:
            hv_max = max(-40.0, min(float(params.get("hv_max", -25.0)), 0.0))
        except (TypeError, ValueError):
            hv_max = -25.0
        render = Step(
            kind="render",
            label=f"detectando agua a {px} px",
            script="prototipos/nisar_agua.py",
            args=[
                "--h5", str(h5),
                "--bbox", bbox_final,
                "--px", str(px),
                "--hh-max", f"{hh_max:g}",
                "--hv-max", f"{hv_max:g}",
                "--out", str(work / f"nisar_agua_{px}.png"),
                "--geojson", geojson,
            ],
            expected=5,
        )
    elif producto == "sme2":
        algoritmo = str(params.get("algoritmo") or "DSG").strip().upper()
        if algoritmo not in ("DSG", "PMI", "TSR"):
            algoritmo = "DSG"
        solo_calidad = bool(params.get("solo_calidad", False))
        render = Step(
            kind="render",
            label=f"humedad del suelo {algoritmo} a {px} px",
            script="prototipos/nisar_sme2.py",
            args=[
                "--h5", str(h5),
                "--bbox", bbox_final,
                "--px", str(px),
                "--algoritmo", algoritmo,
                "--out", str(work / f"nisar_sme2_{algoritmo.lower()}_{px}.png"),
                "--geojson", geojson,
                *(["--solo-calidad"] if solo_calidad else []),
            ],
            expected=5,
        )
    elif producto == "gunw":
        render = Step(
            kind="render",
            label=f"interferograma a {px} px",
            script="prototipos/nisar_gunw.py",
            args=[
                "--h5", str(h5),
                "--bbox", bbox_final,
                "--px", str(px),
                "--out", str(work / f"nisar_gunw_{px}.png"),
                "--geojson", geojson,
            ],
            expected=5,
        )
    elif producto == "fusion":
        try:
            dias = max(1, min(int(params.get("dias", 15)), 60))
        except (TypeError, ValueError):
            dias = 15
        try:
            nubes = max(0.0, min(float(params.get("nubes", 40.0)), 100.0))
        except (TypeError, ValueError):
            nubes = 40.0
        px_fusion = max(800, min(px, 2000))
        render = Step(
            kind="render",
            label=f"fusionando Sentinel-2 (±{dias} días)",
            script="prototipos/nisar_fusion.py",
            args=[
                "--h5", str(h5),
                "--bbox", bbox_final,
                "--px", str(px_fusion),
                "--dias", str(dias),
                "--nubes", f"{nubes:g}",
                "--out", str(work / "nisar_fusion"),
                "--geojson", geojson,
            ],
            expected=15,
        )
    elif producto in ("cambio", "incendio"):
        antes_granulo = _nisar_nombre(
            str(params.get("antes_granulo") or "").strip(), "antes_granulo"
        )
        _exigir_orden(antes_granulo, granulo)
        antes_url = str(params.get("antes_url") or "").strip()
        antes_coleccion = _nisar_coleccion(
            antes_url, str(params.get("antes_coleccion") or "")
        )
        if antes_granulo == granulo:
            raise ValueError("La fecha anterior no puede ser la misma escena.")
        # Mezclar PROVISIONAL con VALIDATED cambia el procesamiento, no solo el
        # terreno: el JSON de la comparacion deja las dos colecciones a la vista.
        h5_antes = raiz_h5 / antes_coleccion / f"{antes_granulo}.h5"
        if _nisar_en_disco(raiz_h5, antes_coleccion, antes_granulo):
            # Ya esta: no se pide URL ni se agrega un paso que no baja nada.
            pass
        elif antes_url.startswith("https://"):
            pasos.append(
                _nisar_descarga(
                    antes_granulo, antes_url, antes_coleccion, raiz_h5, "anterior"
                )
            )
        else:
            raise ValueError(
                f"La escena anterior {antes_granulo} no esta en disco y no trae una "
                "URL https de descarga."
            )

        try:
            umbral = max(0.5, min(abs(float(params.get("umbral", 3.0))), 20.0))
        except (TypeError, ValueError):
            umbral = 3.0
        try:
            hv_min = max(-30.0, min(float(params.get("hv_min", -15.5)), 0.0))
        except (TypeError, ValueError):
            hv_min = -15.5
        if producto == "cambio":
            modo_cambio = str(params.get("modo_cambio") or "mascara").lower()
            if modo_cambio not in ("delta", "mascara", "rgb", "comparar"):
                modo_cambio = "mascara"
            try:
                # ΔHV se resta el corrimiento del par y se promedia el speckle:
                # 2 dB queda por encima del piso de ruido (~1,5 dB a 50 m).
                umbral = max(0.5, min(abs(float(params.get("umbral", 2.0))), 20.0))
            except (TypeError, ValueError):
                umbral = 2.0
            verificar = bool(params.get("verificar_s2"))
            try:
                # Confirmacion temporal con los .h5 que ya estan en disco: no
                # agrega descargas. 0 apaga la persistencia.
                confirmar_temporal = max(
                    0, min(int(params.get("confirmar_temporal", 1)), 3)
                )
            except (TypeError, ValueError):
                confirmar_temporal = 1
            try:
                # Un desmonte es un bloque: 0,5 ha descarta el moteado de speckle.
                mmu_ha = max(0.0, float(params.get("mmu_ha", 0.5)))
            except (TypeError, ValueError):
                mmu_ha = 0.5
            render = Step(
                kind="render",
                label=f"comparando fechas a {px} px",
                script="prototipos/nisar_cambio.py",
                args=[
                    "--antes", str(h5_antes),
                    "--despues", str(h5),
                    "--bbox", bbox_final,
                    "--px", str(px),
                    "--modo", modo_cambio,
                    "--umbral", f"{umbral:g}",
                    "--hv-min", f"{hv_min:g}",
                    *(["--verificar-s2"] if verificar else []),
                    *(["--confirmar-temporal", str(confirmar_temporal)]
                      if confirmar_temporal > 0 else []),
                    *(["--mmu-ha", f"{mmu_ha:g}"] if mmu_ha > 0 else []),
                    "--out", str(work / f"nisar_cambio_{modo_cambio}_{px}.png"),
                    "--geojson", geojson,
                ],
                expected=8,
            )
        else:
            render = Step(
                kind="render",
                label=f"detectando cicatriz a {px} px",
                script="prototipos/nisar_incendio.py",
                args=[
                    "--antes", str(h5_antes),
                    "--despues", str(h5),
                    "--bbox", bbox_final,
                    "--px", str(px),
                    "--umbral", f"{umbral:g}",
                    "--hv-min", f"{hv_min:g}",
                    "--out", str(work / f"nisar_incendio_{px}.png"),
                    "--geojson", geojson,
                    *(["--firms"] if params.get("firms", True) else []),
                ],
                expected=10,
            )
    elif producto == "serie":
        try:
            track = int(params.get("track") or 0)
            frame = int(params.get("frame") or 0)
        except (TypeError, ValueError):
            track = frame = 0
        if not track or not frame:
            raise ValueError("La serie temporal necesita track y frame.")
        try:
            umbral = max(0.5, min(abs(float(params.get("umbral", 3.0))), 20.0))
        except (TypeError, ValueError):
            umbral = 3.0
        try:
            hv_min = max(-30.0, min(float(params.get("hv_min", -15.5)), 0.0))
        except (TypeError, ValueError):
            hv_min = -15.5
        px_serie = max(800, min(px, 1600))
        fechas = str(params.get("fechas") or "").strip()
        ids_fechas: list[str] = []
        if fechas:
            ids_fechas = [parte.strip() for parte in fechas.split(",") if parte.strip()]
            for rid in ids_fechas:
                _nisar_nombre(rid, "fecha")

        # Fechas elegidas en el visor: si el .h5 ya esta se usa tal cual; si no,
        # se baja antes de apilar la serie. Asi la serie no depende de que ASF
        # haya devuelto esa fecha en la ventana de busqueda.
        colecciones = [coleccion]
        for extra in _nisar_escenas(params):
            coleccion_extra = extra["coleccion"] or coleccion
            if coleccion_extra not in colecciones:
                colecciones.append(coleccion_extra)
            if extra["id"] not in ids_fechas:
                ids_fechas.append(extra["id"])
            if _nisar_en_disco(raiz_h5, coleccion_extra, extra["id"]):
                continue
            if not extra["url"].startswith("https://"):
                raise ValueError(
                    f"La fecha {extra['id']} no esta en disco y no trae una URL https "
                    "de descarga."
                )
            pasos.append(
                _nisar_descarga(
                    extra["id"], extra["url"], coleccion_extra, raiz_h5, "fecha"
                )
            )

        args_serie = [
            "--h5", str(h5),
            *[parte for nombre in colecciones for parte in ("--coleccion-dir", str(raiz_h5 / nombre))],
            "--track", str(track),
            "--frame", str(frame),
            "--bbox", bbox_final,
            "--px", str(px_serie),
            "--umbral", f"{umbral:g}",
            "--hv-min", f"{hv_min:g}",
            "--out", str(work / "serie"),
            "--geojson", geojson,
        ]
        if ids_fechas:
            args_serie += ["--fechas", ",".join(ids_fechas)]
        render = Step(
            kind="render",
            label=f"serie temporal track {track} frame {frame}",
            script="prototipos/nisar_serie.py",
            args=args_serie,
            expected=20,
        )
    elif producto == "geotiff":
        pol = str(params.get("pol") or "auto").lower()
        if pol not in ("auto", "hh", "hv", "vv", "vh"):
            pol = "auto"
        modo_geo = str(params.get("modo_geo") or "db").lower()
        if modo_geo not in ("db", "lineal"):
            modo_geo = "db"
        render = Step(
            kind="render",
            label=f"exportando GeoTIFF {pol} ({modo_geo})",
            script="prototipos/nisar_geotiff.py",
            args=[
                "--h5", str(h5),
                "--bbox", bbox_final,
                "--pol", pol,
                "--px", str(px),
                "--modo", modo_geo,
                "--out", str(work / "nisar_geotiff.tif"),
                "--geojson", geojson,
            ],
            expected=5,
        )
    else:
        pol = str(params.get("pol") or "auto").lower()
        if pol not in ("auto", "hh", "hv", "vv", "vh"):
            pol = "auto"
        modo = str(params.get("modo") or "gris").lower()
        if modo not in ("gris", "color"):
            modo = "gris"
        render = Step(
            kind="render",
            label=f"renderizando la caja a {px} px",
            script="prototipos/poster_nisar.py",
            args=[
                "--h5", str(h5),
                "--bbox", bbox_final,
                "--pol", pol,
                "--modo", modo,
                "--px", str(px),
                "--out", str(work / f"nisar_{modo}_{pol}_{px}.png"),
                "--geojson", geojson,
            ],
            expected=6,
        )

    pasos.append(render)
    return Plan(pasos=pasos)


_CONSTRUCTORES = {PRODUCT_ID: _nisar_render}


def planear(product_id: str, params: dict[str, Any], work: Path) -> Plan:
    """Devuelve los comandos a correr, en orden, para este pedido NISAR."""
    constructor = _CONSTRUCTORES.get(product_id)
    if constructor is None:
        raise ValueError(f"Producto sin receta real: {product_id}")
    return constructor(params, work)
