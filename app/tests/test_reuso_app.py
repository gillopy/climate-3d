"""Pruebas del cableado del reuso en la app: receta y carpeta del job.

Fijan dos cosas:

  * la receta de GOES C13 le pasa al renderer el almacén compartido de cuadros
    (`--reusar`), que el renderer completa con el sello de aspecto;
  * la carpeta del job dice qué producto la generó (`goes_c13_<firma>`) y no un
    sha1 pelado.

    .venv\\Scripts\\python.exe -m unittest discover -s app\\tests
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
for ruta in (RAIZ, RAIZ / "comun"):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))

from app.api import jobs, recipes  # noqa: E402


class PlanDeLaReceta(unittest.TestCase):
    """La receta le pasa al renderer el almacén compartido."""

    def test_el_render_apunta_al_almacen(self):
        with mock.patch.object(recipes, "_slots_goes", return_value=[]):
            plan = recipes._goes({
                "satelite": "G19", "paleta": "clean_ir", "resolucion": "1400",
                "animar": True, "hora_desde": 0, "hora_hasta": 24,
                "ventana": {"start": "2026-11-01", "end": "2026-11-02"},
            }, Path("C:/tmp/work"))
        render = [p for p in plan.pasos if p.kind == "render"][0]
        destino = render.args[render.args.index("--reusar") + 1]
        self.assertIn("cuadros_render", destino)
        self.assertTrue(destino.replace("\\", "/").endswith("goes_c13/g19"))


class CarpetaDelJob(unittest.TestCase):
    """La carpeta del job se lee sin abrirla."""

    def test_el_nombre_dice_el_producto(self):
        self.assertEqual(
            jobs.nombre_cache("goes_c13", "68bb7f6df9c7"),
            "goes_c13_68bb7f6df9c7",
        )

    def test_un_producto_raro_no_rompe_la_ruta(self):
        self.assertEqual(
            jobs.nombre_cache("nisar/analisis", "abc123"),
            "nisar_analisis_abc123",
        )
