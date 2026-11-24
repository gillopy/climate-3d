"""Construye el índice SQLite del catastro sin abrir la app.

La API lo arma sola la primera vez que alguien abre el panel de catastro, pero
para dejarlo listo antes (o reconstruirlo a mano) está este comando:

    .venv\\Scripts\\python.exe app\\tools\\catastro.py --estado
    .venv\\Scripts\\python.exe app\\tools\\catastro.py
    .venv\\Scripts\\python.exe app\\tools\\catastro.py --reconstruir

El origen sale de ``CLIMATE3D_CATASTRO`` (o ``comun/rutas.py --catastro ...``):

    .venv\\Scripts\\python.exe comun\\rutas.py --catastro "C:\\ruta\\al\\shapefile"
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from app.api import catastro  # noqa: E402


def _barra(fraccion: float, mensaje: str) -> None:
    ancho = 28
    llenos = int(round(ancho * max(0.0, min(1.0, fraccion))))
    barra = "#" * llenos + "." * (ancho - llenos)
    print(f"\r[{barra}] {fraccion * 100:5.1f} %  {mensaje[:60]:<60}", end="", flush=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Índice de catastro para el visor NISAR")
    ap.add_argument("--estado", action="store_true", help="sólo muestra el estado")
    ap.add_argument(
        "--reconstruir",
        action="store_true",
        help="rehace el índice aunque el shapefile no haya cambiado",
    )
    args = ap.parse_args(argv)

    shp = catastro.origen()
    if shp is None:
        print(
            "No hay shapefile de catastro. Configurá CLIMATE3D_CATASTRO o "
            f"`comun/rutas.py --catastro <ruta>` (hoy: {catastro.raiz_catastro()})",
            file=sys.stderr,
        )
        return 2

    db = catastro.ruta_indice()
    estado = catastro._estado_actual()  # noqa: SLF001 - herramienta interna
    print(f"origen  {shp}")
    print(f"índice  {db}")
    if args.estado:
        print(f"listo   {estado['disponible']} · parcelas {estado['parcelas']:,}")
        return 0
    if estado["disponible"] and not args.reconstruir:
        print(f"al día  {estado['parcelas']:,} parcelas · {estado['bytes_indice'] / 1e6:.0f} MB")
        return 0

    momento = time.time()
    meta = catastro.construir_indice(shp, db, avisar=_barra)
    print()
    print(
        f"listo en {meta['segundos']} s · {int(meta['usadas']):,} parcelas "
        f"({int(meta['invalidas'])} sin geometría válida, "
        f"{int(meta['reparadas'])} con coordenadas en grados) · "
        f"{db.stat().st_size / 1e6:.0f} MB"
    )
    print(f"total del comando: {time.time() - momento:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
