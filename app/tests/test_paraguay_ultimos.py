"""Pruebas del encuadre "Solo Paraguay" y de "Últimos datos" en los GOES.

Fijan lo que la app promete:

  * cada producto (salvo el Snapshot, el MUR oceánico y el follaje) expone el
    toggle `paraguay` con su `margen`, y el margen cambia el encuadre;
  * cada familia de render recibe las banderas correctas (`--radio`,
    `--recorte` o `--bbox`);
  * GeoColor, color real e Himawari resuelven "últimos N" sin mirar la ventana.

    app\\.venv\\Scripts\\python.exe -m unittest discover -s app\\tests
"""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
for ruta in (RAIZ, RAIZ / "comun"):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))

from paraguay import encuadre  # noqa: E402

from app.api import catalog, recipes  # noqa: E402

CUADROS = ["10", "12", "24", "36", "48", "60"]


class Encuadre(unittest.TestCase):
    """El margen agranda el encuadre sin mover el centro."""

    def test_el_margen_agranda_el_radio(self):
        sin = encuadre(0.0)
        poco = encuadre(0.01)
        normal = encuadre(0.06)
        mucho = encuadre(0.20)
        self.assertLess(sin["radio"], poco["radio"])
        self.assertLess(poco["radio"], normal["radio"])
        self.assertLess(normal["radio"], mucho["radio"])

    def test_el_centro_no_depende_del_margen(self):
        uno, otro = encuadre(0.01), encuadre(0.20)
        self.assertAlmostEqual(uno["lon"], otro["lon"])
        self.assertAlmostEqual(uno["lat"], otro["lat"])

    def test_el_radio_cubre_la_caja(self):
        caja = encuadre(0.06)
        medio_ancho = (caja["este"] - caja["oeste"]) / 2
        medio_alto = (caja["norte"] - caja["sur"]) / 2
        self.assertAlmostEqual(caja["radio"], max(medio_ancho, medio_alto))


class Catalogo(unittest.TestCase):
    """La sección aparece en todos los productos que la pueden usar."""

    def test_excluidos_no_la_tienen(self):
        for pid in catalog.SIN_PARAGUAY:
            nombres = {s.name for s in catalog.get_product(pid).params}
            self.assertNotIn("paraguay", nombres, pid)

    def test_el_resto_la_tiene_con_margen(self):
        for producto in catalog.productos_disponibles():
            if producto.id in catalog.SIN_PARAGUAY:
                continue
            nombres = {s.name for s in producto.params}
            self.assertIn("paraguay", nombres, producto.id)
            self.assertIn("margen", nombres, producto.id)
            margen = next(s for s in producto.params if s.name == "margen")
            self.assertEqual(margen.enabled_when, {"paraguay": True}, producto.id)

    def test_el_snapshot_queda_intacto(self):
        nombres = {s.name for s in catalog.get_product("snapshot_paraguay").params}
        self.assertNotIn("paraguay", nombres)
        self.assertIn("ultima", nombres)


class RecetasParaguay(unittest.TestCase):
    """Cada familia de render recibe la bandera que entiende."""

    def _plan(self, pid: str, **extra):
        params = {s.name: s.default for s in catalog.get_product(pid).params}
        params["paraguay"] = True
        params.update(extra)
        return recipes.planear(pid, params, Path("C:/tmp/work"))

    def _render(self, pid: str, **extra):
        plan = self._plan(pid, **extra)
        return [s for s in plan.pasos if s.kind == "render"][0]

    def test_c13_usa_radio_y_contorno(self):
        render = self._render("goes_c13")
        args = render.args
        self.assertLess(float(args[args.index("--radio") + 1]), 10.0)
        self.assertTrue(args[args.index("--geojson") + 1].endswith("paraguay_gadm.json"))

    def test_banda_y_rgb_usan_recorte_y_borde(self):
        for pid in ("goes_banda", "goes_dust", "goes_airmass", "goes_firetemp"):
            args = self._render(pid).args
            recorte = float(args[args.index("--recorte") + 1])
            self.assertLess(recorte, 0.1, pid)
            self.assertTrue(args[args.index("--borde") + 1].endswith("paraguay_gadm.json"), pid)

    def test_geocolor_usa_la_caja_sin_globo(self):
        args = self._render("geocolor").args
        self.assertNotIn("--globo", args)
        oeste, sur, este, norte = (float(args[args.index("--bbox") + i]) for i in range(1, 5))
        self.assertLess(oeste, -60)
        self.assertGreater(este, -54)
        self.assertLess(sur, -27)
        self.assertGreater(norte, -19)

    def test_color_real_fuerza_el_globo(self):
        render = self._render("goes_truecolor", encuadre="disco")
        self.assertEqual(render.script, "prototipos/poster_goes_truecolor.py")
        self.assertIn("--recorte", render.args)

    def test_modelos_usan_radio(self):
        for pid in ("precipitacion_ecmwf", "anomalia_2t", "viento_250"):
            args = self._render(pid).args
            self.assertIn("--radio", args, pid)
            self.assertLess(float(args[args.index("--radio") + 1]), 10.0, pid)

    def test_himawari_no_tiene_la_seccion(self):
        nombres = {s.name for s in catalog.get_product("himawari").params}
        self.assertNotIn("paraguay", nombres)
        self.assertNotIn("margen", nombres)


class Ultimos(unittest.TestCase):
    """GeoColor, color real e Himawari ofrecen la misma lista que los demás."""

    def test_los_tres_tienen_el_switch_y_la_lista(self):
        for pid in ("geocolor", "goes_truecolor", "himawari"):
            producto = catalog.get_product(pid)
            nombres = {s.name for s in producto.params}
            self.assertIn("ultimos", nombres, pid)
            self.assertIn("ultimos_n", nombres, pid)
            spec = next(s for s in producto.params if s.name == "ultimos_n")
            self.assertEqual([o.value for o in spec.options], CUADROS, pid)

    def test_ultimos_deshabilita_la_ventana(self):
        for pid in ("geocolor", "goes_truecolor", "himawari"):
            ventana = next(s for s in catalog.get_product(pid).params if s.name == "ventana")
            self.assertEqual(ventana.enabled_when, {"ultimos": False}, pid)

    def test_geocolor_resuelve_los_ultimos_slots(self):
        instantes = [
            datetime(2026, 11, 4, 18, 0) + timedelta(minutes=10 * i)
            for i in range(12)
        ]
        with mock.patch.object(recipes, "_ultimos_geocolor", return_value=instantes):
            plan = recipes.planear("geocolor", {
                "satelite": "G19", "resolucion": "1400", "animar": False,
                "ultimos": True, "ultimos_n": "12",
                "ventana": {"start": "2026-10-02", "end": "2026-10-05"},
            }, Path("C:/tmp/work"))
        descarga = [s for s in plan.pasos if s.kind == "download"][0]
        args = descarga.args
        self.assertEqual(args[args.index("--desde") + 1], "2026-11-04T18:00")
        self.assertEqual(args[args.index("--n") + 1], "12")

    def test_truecolor_resuelve_los_ultimos_slots(self):
        instantes = [
            datetime(2026, 11, 4, 18, 0) + timedelta(minutes=10 * i)
            for i in range(10)
        ]
        with mock.patch.object(recipes, "_ultimos_goes", return_value=instantes):
            plan = recipes.planear("goes_truecolor", {
                "satelite": "G19", "resolucion": "1400", "animar": False,
                "ultimos": True, "ultimos_n": "10",
                "ventana": {"start": "2026-10-02", "end": "2026-10-05"},
            }, Path("C:/tmp/work"))
        descarga = [s for s in plan.pasos if s.kind == "download"][0]
        args = descarga.args
        self.assertEqual(args[args.index("--desde") + 1], "2026-11-04T18:00")
        self.assertEqual(args[args.index("--n") + 1], "10")

    def test_himawari_resuelve_los_ultimos_slots(self):
        instantes = [
            datetime(2026, 11, 4, 18, 0) + timedelta(minutes=10 * i)
            for i in range(10)
        ]
        with mock.patch.object(recipes, "_ultimos_himawari", return_value=instantes):
            plan = recipes.planear("himawari", {
                "resolucion": "1400", "animar": False,
                "ultimos": True, "ultimos_n": "10",
                "ventana": {"start": "2026-10-02", "end": "2026-10-05"},
            }, Path("C:/tmp/work"))
        descarga = [s for s in plan.pasos if s.kind == "download"][0]
        args = descarga.args
        self.assertEqual(args[args.index("--desde") + 1], "2026-11-04T18:00")
        self.assertEqual(args[args.index("--hasta") + 1], "2026-11-04T19:40")


if __name__ == "__main__":
    unittest.main()
