"""Offline tests for the GOES ABI L2 LST product in the app catalog and recipes.

These fix the public contract of the product, never the network:

  * the catalog entry, its identity and the exact controls it exposes;
  * the rail order and the recipe registration;
  * a plan built from an explicit date window (local disk only) that runs the
    download script and the render script with the hourly `--paso 60`;
  * snapshot uses a whole UTC hour (the LST cadence has no minutes).

    app\\.venv\\Scripts\\python.exe -m unittest app.tests.test_goes_lst_catalogo -v
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
for ruta in (RAIZ, RAIZ / "comun"):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))

from app.api import catalog, recipes  # noqa: E402

TRABAJO = Path("C:/tmp/work")
DIA = {"start": "2026-11-12", "end": "2026-11-12"}


class ProductoEnElCatalogo(unittest.TestCase):
    """The product exists with the identity the spec fixes."""

    def test_identidad(self):
        producto = catalog.get_product("goes_lst")
        self.assertIsNotNone(producto)
        self.assertEqual(producto.id, "goes_lst")
        self.assertEqual(producto.name, "GOES - temperatura de superficie (LST)")
        self.assertEqual(producto.group, "satelite")
        self.assertEqual(
            producto.stage,
            "descargar/descargar_goes_lst.py + prototipos/poster_goes_lst.py",
        )

    def test_el_resumen_describe_el_producto(self):
        resumen = catalog.get_product("goes_lst").summary
        for fragmento in ("ABI L2 LST", "2 km", "tierra despejada", "horaria",
                          "C", "F"):
            self.assertIn(fragmento, resumen, fragmento)

    def test_va_inmediatamente_despues_de_goes_c13(self):
        self.assertEqual(
            catalog._ORDEN.index("goes_lst"),
            catalog._ORDEN.index("goes_c13") + 1,
        )


class Controles(unittest.TestCase):
    """Only the controls the renderer accepts, and no `minuto`."""

    def setUp(self):
        self.producto = catalog.get_product("goes_lst")
        self.params = {spec.name: spec for spec in self.producto.params}

    def test_conjunto_exacto_de_controles(self):
        self.assertEqual(
            set(self.params),
            {
                "snapshot", "paraguay", "margen",
                "satelite", "ventana", "ultimos", "ultimos_n", "ultimo",
                "hora", "resolucion", "compuesto",
                "hora_desde", "hora_hasta", "animar", "fps",
            },
        )
        self.assertNotIn("minuto", self.params)

    def test_satelite(self):
        satelite = self.params["satelite"]
        self.assertEqual(satelite.default, "G19")
        self.assertEqual([o.value for o in satelite.options], ["G19", "G18", "G16"])

    def test_ventana(self):
        ventana = self.params["ventana"]
        self.assertEqual(ventana.kind, "date-range")
        self.assertEqual(ventana.enabled_when, {"ultimos": False})
        self.assertIn("start", ventana.default)
        self.assertIn("end", ventana.default)

    def test_hora_es_entera_y_solo_en_snapshot(self):
        hora = self.params["hora"]
        self.assertEqual(hora.kind, "hour")
        self.assertEqual(hora.default, 15)
        self.assertEqual((hora.min, hora.max, hora.step), (0, 23, 1))
        self.assertEqual(hora.enabled_when, {"snapshot": True})
        self.assertIn("UTC", hora.help)

    def test_resolucion(self):
        resolucion = self.params["resolucion"]
        self.assertEqual(resolucion.default, "2712")
        self.assertEqual(
            [o.value for o in resolucion.options],
            ["1400", "1800", "2000", "2400", "2712", "3200", "4000"],
        )

    def test_compuesto_temporal(self):
        compuesto = self.params["compuesto"]
        self.assertEqual(compuesto.kind, "select")
        self.assertEqual(compuesto.default, "1")
        self.assertEqual([o.value for o in compuesto.options], ["1", "3", "6"])
        self.assertIn("instantanea", compuesto.help)

    def test_animacion(self):
        self.assertEqual(self.params["animar"].kind, "toggle")
        self.assertEqual(self.params["fps"].kind, "slider")
        self.assertEqual(self.params["ultimos"].kind, "toggle")
        self.assertEqual(
            [o.value for o in self.params["ultimos_n"].options],
            ["10", "12", "24", "36", "48", "60"],
        )


class Registro(unittest.TestCase):
    """The recipe is reachable through `planear`."""

    def test_constructores(self):
        self.assertIn("goes_lst", recipes._CONSTRUCTORES)
        self.assertIs(recipes._CONSTRUCTORES["goes_lst"], recipes._goes_lst)

    def test_constantes_de_cadencia(self):
        self.assertEqual(recipes._PASO_LST, 60)
        self.assertEqual(recipes._MAX_CUADROS_LST, 72)


class Plan(unittest.TestCase):
    """An explicit window reads only the local disk (no S3 listing)."""

    def _plan(self, **extra):
        params = {
            "satelite": "G19",
            "ventana": DIA,
            "resolucion": "1400",
            "animar": False,
            "snapshot": False,
            "ultimos": False,
        }
        params.update(extra)
        return recipes._goes_lst(params, TRABAJO)

    def test_ventana_explicita_arma_descarga_y_render(self):
        plan = self._plan()

        descargas = [p for p in plan.pasos if p.kind == "download"]
        self.assertEqual(len(descargas), 1)
        descarga = descargas[0]
        self.assertEqual(descarga.script, "descargar/descargar_goes_lst.py")
        self.assertEqual(descarga.args[descarga.args.index("--sat") + 1], "G19")
        self.assertEqual(descarga.args[descarga.args.index("--paso") + 1], "60")
        self.assertEqual(descarga.args[descarga.args.index("--desde") + 1],
                         "2026-11-12T17:00:00")
        self.assertEqual(descarga.args[descarga.args.index("--hasta") + 1],
                         "2026-11-12T18:00:00")

        renders = [p for p in plan.pasos if p.kind == "render"]
        self.assertEqual(len(renders), 1)
        render = renders[0]
        self.assertEqual(render.script, "prototipos/poster_goes_lst.py")
        self.assertEqual(render.args[render.args.index("--sat") + 1], "G19")
        self.assertEqual(render.args[render.args.index("--n") + 1], "1")
        self.assertEqual(render.args[render.args.index("--paso") + 1], "60")
        self.assertEqual(render.args[render.args.index("--px") + 1], "1400")
        self.assertIn("--out", render.args)
        self.assertNotIn("--frames", render.args)
        self.assertNotIn("animate", [p.kind for p in plan.pasos])

    def test_el_render_pide_fondo_y_relleno(self):
        render = [p for p in self._plan().pasos if p.kind == "render"][0]
        self.assertEqual(render.args[render.args.index("--mapa") + 1], "base")
        self.assertEqual(render.args[render.args.index("--fondo") + 1], "oscuro")
        self.assertEqual(render.args[render.args.index("--relleno") + 1], "2")
        self.assertEqual(render.args[render.args.index("--compuesto") + 1], "1")

    def test_paraguay_pide_mapa_plano_cuadrado(self):
        render = [p for p in self._plan(paraguay=True).pasos if p.kind == "render"][0]
        self.assertIn("--bbox", render.args)
        self.assertIn("--limpio", render.args)
        self.assertNotIn("--centro", render.args)
        self.assertNotIn("--recorte", render.args)

    def test_sin_paraguay_pide_el_globo(self):
        render = [p for p in self._plan().pasos if p.kind == "render"][0]
        self.assertIn("--centro", render.args)
        self.assertIn("--recorte", render.args)
        self.assertNotIn("--bbox", render.args)

    def test_el_compuesto_adelanta_la_descarga(self):
        plan = self._plan(compuesto="3")

        descarga = [p for p in plan.pasos if p.kind == "download"][0]
        self.assertEqual(descarga.args[descarga.args.index("--desde") + 1],
                         "2026-11-12T15:00:00")
        render = [p for p in plan.pasos if p.kind == "render"][0]
        self.assertEqual(render.args[render.args.index("--compuesto") + 1], "3")

    def test_el_compuesto_se_acota_a_la_lista(self):
        self.assertEqual(recipes._compuesto_lst({"compuesto": "5"}), 6)
        self.assertEqual(recipes._compuesto_lst({"compuesto": "abc"}), 1)
        self.assertEqual(recipes._compuesto_lst({}), 1)

    def test_animacion_horaria_usa_frames(self):
        with mock.patch.object(
            recipes,
            "_ventana_animacion",
            return_value=(datetime(2026, 11, 12, 0), datetime(2026, 11, 13, 0)),
        ):
            plan = self._plan(animar=True)

        descarga = [p for p in plan.pasos if p.kind == "download"][0]
        self.assertEqual(descarga.args[descarga.args.index("--hasta") + 1],
                         "2026-11-13T00:00:00")
        render = [p for p in plan.pasos if p.kind == "render"][0]
        self.assertEqual(render.args[render.args.index("--n") + 1], "24")
        self.assertEqual(render.args[render.args.index("--paso") + 1], "60")
        self.assertIn("--frames", render.args)

    def test_la_animacion_topea_en_72_cuadros(self):
        with mock.patch.object(
            recipes,
            "_ventana_animacion",
            return_value=(datetime(2026, 11, 10, 0), datetime(2026, 11, 14, 0)),
        ):
            plan = self._plan(animar=True)

        render = [p for p in plan.pasos if p.kind == "render"][0]
        self.assertEqual(render.args[render.args.index("--n") + 1], "72")

    def test_snapshot_usa_la_hora_entera(self):
        plan = self._plan(snapshot=True, hora=15)

        render = [p for p in plan.pasos if p.kind == "render"][0]
        self.assertEqual(render.args[render.args.index("--desde") + 1],
                         "2026-11-12T15:00")
        self.assertEqual(render.args[render.args.index("--n") + 1], "1")


class FechasDisponibles(unittest.TestCase):
    """The calendar reads the granules already on disk, never the network."""

    def test_lee_los_granulos_de_lst(self):
        nombre = ("OR_ABI-L2-LST2KMF-M6_G19_s20263172200207"
                  "_e20263172209515_c20263172214319.nc")
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp) / "goes_lst_g19"
            carpeta.mkdir()
            (carpeta / nombre).write_bytes(b"x")
            with mock.patch.dict("os.environ", {"CLIMATE3D_DATOS": tmp}):
                origen, fechas = catalog.available_dates(
                    catalog.get_product("goes_lst"), {"satelite": "G19"},
                )
        self.assertEqual(origen, "descubierto")
        self.assertIn("2026-11-13", fechas)


if __name__ == "__main__":
    unittest.main()
