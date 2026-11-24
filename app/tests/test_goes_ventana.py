"""Pruebas de la ventana de animación de GOES C13 en globo.

Fijan las reglas que antes no existían:

  * una ventana de 3 días produce 432 slots: el tope ya no recorta a 2 días en
    silencio (`_MAX_CUADROS_GOES`, sólo para el globo C13);
  * si la ventana supera el tope, el recorte se lleva el arranque y conserva el
    final (lo más nuevo), y el paso lo dice en su etiqueta;
  * "Hasta el último cuadro" cierra la ventana en el último slot publicado, sin
    mirar la fecha final del calendario.

    .venv\\Scripts\\python.exe -m unittest discover -s app\\tests
"""
from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
for ruta in (RAIZ, RAIZ / "comun"):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))

from app.api import catalog, recipes  # noqa: E402

#: Todo en el pasado: así `_ventana_animacion` no recorta al último slot publicado.
PASADO = {"start": "2026-11-01", "end": "2026-11-03"}


def _params(**extra) -> dict:
    params = {
        "satelite": "G19",
        "paleta": "clean_ir",
        "resolucion": "1400",
        "animar": True,
        "hora_desde": 0,
        "hora_hasta": 24,
        "ventana": PASADO,
    }
    params.update(extra)
    return params


def _plan(params: dict) -> recipes.Plan:
    # Sin disco: el plan es el mismo, sólo cambia si hace falta descargar.
    with mock.patch.object(recipes, "_slots_goes", return_value=[]):
        return recipes._goes(params, Path("C:/tmp/work"))


def _paso(plan: recipes.Plan, kind: str) -> recipes.Step:
    return [p for p in plan.pasos if p.kind == kind][0]


def _arg(paso: recipes.Step, nombre: str) -> str:
    return paso.args[paso.args.index(nombre) + 1]


class VentanaDeTresDias(unittest.TestCase):
    """Tres días completos son 432 cuadros, no 288."""

    def test_tres_dias_no_se_recortan_a_dos(self):
        plan = _plan(_params())
        descarga = _paso(plan, "download")
        self.assertEqual(_arg(descarga, "--desde"), "2026-11-01T00:00:00")
        self.assertEqual(_arg(descarga, "--hasta"), "2026-11-04T00:00:00")
        self.assertEqual(_arg(descarga, "--paso"), "10")

    def test_el_render_pide_los_432_cuadros(self):
        render = _paso(_plan(_params()), "render")
        self.assertEqual(_arg(render, "--n"), "432")
        self.assertEqual(_arg(render, "--desde"), "2026-11-01T00:00")

    def test_la_etiqueta_dice_el_rango_real(self):
        descarga = _paso(_plan(_params()), "download")
        self.assertIn("01/11 00:00", descarga.label)
        self.assertIn("04/11 00:00", descarga.label)


class RecortePorElFinal(unittest.TestCase):
    """Diez días no entran: se pierde el arranque, nunca el final."""

    DIEZ_DIAS = {"start": "2026-10-01", "end": "2026-10-10"}

    def _descarga(self) -> recipes.Step:
        return _paso(_plan(_params(ventana=self.DIEZ_DIAS)), "download")

    def test_conserva_el_final_de_la_ventana(self):
        descarga = self._descarga()
        self.assertEqual(_arg(descarga, "--hasta"), "2026-10-11T00:00:00")

    def test_arranca_justo_el_tope_antes_del_final(self):
        descarga = self._descarga()
        self.assertEqual(_arg(descarga, "--desde"), "2026-10-04T00:00:00")

    def test_la_etiqueta_avisa_del_tope(self):
        self.assertIn("tope", self._descarga().label)


class HastaElUltimoCuadro(unittest.TestCase):
    """El final lo pone NOAA, no el calendario."""

    ULTIMO = datetime(2026, 11, 4, 18, 10)

    def _plan(self, **extra) -> recipes.Plan:
        # La fecha final del calendario miente a propósito: tiene que ignorarla.
        params = _params(animar=False, hasta_ultimo=True,
                         ventana={"start": "2026-11-02", "end": "2026-11-09"})
        params.update(extra)
        with mock.patch.object(recipes, "_ultimos_goes", return_value=[self.ULTIMO]):
            with mock.patch.object(recipes, "_slots_goes", return_value=[]):
                return recipes._goes(params, Path("C:/tmp/work"))

    def test_termina_un_paso_despues_del_ultimo_publicado(self):
        descarga = _paso(self._plan(), "download")
        self.assertEqual(_arg(descarga, "--desde"), "2026-11-02T00:00:00")
        self.assertEqual(_arg(descarga, "--hasta"), "2026-11-04T18:20:00")

    def test_anima_aunque_el_switch_de_animar_este_apagado(self):
        render = _paso(self._plan(), "render")
        self.assertEqual(_arg(render, "--n"), "398")

    def test_la_etiqueta_dice_que_va_hasta_el_ultimo(self):
        self.assertIn("último", _paso(self._plan(), "download").label)

    def test_sin_slots_despues_del_arranque_avisa(self):
        with self.assertRaises(ValueError) as caja:
            self._plan(ventana={"start": "2026-11-05", "end": "2026-11-09"})
        self.assertIn("último", str(caja.exception))


class ControlesDelCatalogo(unittest.TestCase):
    """La UI pide el final de las dos maneras, nunca a la vez."""

    def _spec(self, nombre: str):
        producto = next(p for p in catalog.PRODUCTS if p.id == "goes_c13")
        return next(s for s in producto.params if s.name == nombre)

    def test_el_toggle_arranca_apagado(self):
        self.assertIs(self._spec("hasta_ultimo").default, False)

    def test_el_calendario_se_apaga_con_el_toggle(self):
        # `snapshot` no aparece acá: lo apaga la regla del formulario, no el spec.
        self.assertEqual(
            self._spec("ventana").enabled_when,
            {"ultimos": False, "hasta_ultimo": False},
        )

    def test_la_hora_final_se_apaga_con_el_toggle(self):
        self.assertEqual(
            self._spec("hora_hasta").enabled_when,
            {"ultimos": False, "hasta_ultimo": False, "snapshot": False},
        )

    def test_la_hora_inicial_sigue_mandando(self):
        self.assertEqual(
            self._spec("hora_desde").enabled_when,
            {"ultimos": False, "snapshot": False},
        )
