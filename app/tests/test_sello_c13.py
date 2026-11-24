"""El sello de aspecto de `cuadros_c13_ir.py` cubre TODO lo que cambia píxeles.

Si un parámetro que se dibuja queda fuera del sello, el almacén de cuadros
devuelve imágenes de otro aspecto con el mismo nombre de archivo y la animación
sale con saltos de encuadre, de escala o de estilo. El margen de Paraguay entra
por `radio` (el encuadre recalcula radio y centro), y por eso también se fija acá.

    .venv\\Scripts\\python.exe -m unittest discover -s app\\tests
"""
from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
for ruta in (RAIZ, RAIZ / "comun", RAIZ / "prototipos"):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))


def _dependencias_de_render() -> bool:
    """El runner de `app/tests` no instala matplotlib: sin eso, se saltea."""
    try:
        import matplotlib  # noqa: F401
    except ModuleNotFoundError:
        return False
    return True


HAY_RENDER = _dependencias_de_render()

if HAY_RENDER:
    _spec = importlib.util.spec_from_file_location(
        "_c13_sello", RAIZ / "cuadros" / "cuadros_c13_ir.py")
    c13 = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(c13)


def _args(**extra) -> types.SimpleNamespace:
    """Los argumentos con los que corre la app, listos para `_sello_render`."""
    base = dict(
        px=2712, dpi=140, centro=[-58.4505, -23.4505], radio=5.36563,
        credito="NOAA / CIRA", sat="G19", vmin=-92.1, vmax=56.9,
        geojson="datos/paraguay_gadm.json", paleta="clean_ir",
        limpio=False, tope=2712,
    )
    base.update(extra)
    return types.SimpleNamespace(**base)


@unittest.skipUnless(HAY_RENDER, "faltan matplotlib/xarray en este entorno")
class SelloDeAspecto(unittest.TestCase):
    def test_los_mismos_parametros_dan_el_mismo_sello(self):
        self.assertEqual(c13._sello_render(_args()), c13._sello_render(_args()))

    def test_el_margen_de_paraguay_cambia_el_sello(self):
        # El margen entra por el radio del encuadre: 6 % vs 12 % son otros grados.
        self.assertNotEqual(
            c13._sello_render(_args(radio=4.69493)),
            c13._sello_render(_args(radio=5.19796)),
        )

    def test_la_captura_limpia_cambia_el_sello(self):
        # `--limpio` saca títulos, leyenda y costas: son otros píxeles.
        self.assertNotEqual(
            c13._sello_render(_args(limpio=False)),
            c13._sello_render(_args(limpio=True)),
        )

    def test_el_tope_cambia_el_sello(self):
        # `--tope` cambia la resolución del campo leído y con eso el detalle.
        self.assertNotEqual(
            c13._sello_render(_args(tope=2712)),
            c13._sello_render(_args(tope=1400)),
        )

    def test_la_escala_cambia_el_sello(self):
        self.assertNotEqual(
            c13._sello_render(_args(vmin=-92.1)),
            c13._sello_render(_args(vmin=-64.7)),
        )

    def test_el_tamanio_y_la_paleta_cambian_el_sello(self):
        self.assertNotEqual(
            c13._sello_render(_args(px=2712)),
            c13._sello_render(_args(px=1400)),
        )
        self.assertNotEqual(
            c13._sello_render(_args(paleta="clean_ir")),
            c13._sello_render(_args(paleta="c13_ir")),
        )
