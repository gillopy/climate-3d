"""Lectura del indice de catastro del SNC para dibujarlo en los renders NISAR.

El indice SQLite lo construye la app (``app/api/catastro.py``, con
``app/tools/catastro.py`` para dejarlo listo a mano). Aca solo se lee, para que
los prototipos de render no tengan que importar FastAPI ni duplicar la capa web.

    from pathlib import Path
    import catastro

    indice = catastro.ruta_indice()
    for parcela in catastro.parcelas(indice, (-61.75, -23.51, -61.09, -23.12)):
        print(parcela.props["padron"], parcela.geometry.bounds)

El esquema del indice es parte del contrato: si cambia, esto avisa en vez de
devolver parcelas sin datos.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shapely import wkb
from shapely.geometry.base import BaseGeometry

#: Version del esquema que entiende este lector (la misma de app/api/catastro.py).
ESQUEMA = 3

#: Columnas que se dibujan: el codigo catastral y lo registral que hay en el DBF.
_COLUMNAS = (
    "p.ccatastral, p.padron, p.finca, p.matricula, p.colonia, p.dpto, p.dist, "
    "p.area_m2, p.geometria"
)


@dataclass
class Parcela:
    """Una parcela del SNC: atributos del DBF y su geometria en EPSG:4326."""

    props: dict[str, Any]
    geometry: BaseGeometry

    @property
    def area_m2(self) -> float:
        return float(self.props.get("area_m2") or 0.0)


def ruta_indice(media: Path | None = None) -> Path:
    """Indice del catastro dentro de la raiz de medios."""
    if media is not None:
        return Path(media) / "catastro" / "catastro.sqlite3"
    import rutas

    return rutas.raiz_media() / "catastro" / "catastro.sqlite3"


def _conectar(ruta: Path) -> sqlite3.Connection:
    ruta = Path(ruta)
    if not ruta.is_file():
        raise FileNotFoundError(
            f"no hay indice de catastro en {ruta} "
            "(se construye abriendo el panel Catastro o con app/tools/catastro.py)"
        )
    # Solo lectura: el render nunca toca el indice. `as_uri` escapa espacios y
    # caracteres raros de la ruta, que en Windows aparecen seguido.
    con = sqlite3.connect(f"{ruta.resolve().as_uri()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only = ON")
    return con


def _esquema(con: sqlite3.Connection) -> int:
    fila = con.execute("SELECT valor FROM meta WHERE clave = 'esquema'").fetchone()
    if fila is None:
        return 0
    try:
        return int(fila[0])
    except (TypeError, ValueError):
        return 0


def parcelas(
    ruta: Path | str,
    caja: tuple[float, float, float, float],
    limite: int = 4000,
) -> list[Parcela]:
    """Parcelas cuya caja toca ``caja`` (oeste, sur, este, norte en grados).

    El filtro va por el R-tree (``parcelas_geo``), que es lo que hace usable un
    indice de un millon de filas. Devuelve las de mayor superficie primero: si
    la caja tiene mas parcelas que ``limite``, quedan las que se ven.
    """
    oeste, sur, este, norte = (float(valor) for valor in caja)
    con = _conectar(Path(ruta))
    try:
        esquema = _esquema(con)
        if esquema != ESQUEMA:
            raise ValueError(
                f"el indice de catastro es de esquema {esquema or '?'}; este lector "
                f"espera {ESQUEMA} (reconstruilo con app/tools/catastro.py --reconstruir)"
            )
        filas = con.execute(
            f"SELECT {_COLUMNAS} FROM parcelas_geo AS g "
            "JOIN parcelas AS p ON p.id = g.id "
            "WHERE g.maxx >= ? AND g.minx <= ? AND g.maxy >= ? AND g.miny <= ? "
            "ORDER BY p.area_m2 DESC LIMIT ?",
            (oeste, este, sur, norte, max(1, int(limite))),
        ).fetchall()
    finally:
        con.close()

    salida: list[Parcela] = []
    for fila in filas:
        try:
            geometry = wkb.loads(fila["geometria"])
        except Exception:  # noqa: BLE001 - una fila rota no se lleva el resto
            continue
        if geometry.is_empty:
            continue
        props = {
            clave: fila[clave]
            for clave in (
                "ccatastral",
                "padron",
                "finca",
                "matricula",
                "colonia",
                "dpto",
                "dist",
                "area_m2",
            )
        }
        salida.append(Parcela(props=props, geometry=geometry))
    return salida
