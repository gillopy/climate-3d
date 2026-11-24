"""Pruebas de los productos nuevos: Meteosat-12 (MTG) y CBERS-4A.

No tocan la red: fijan el contrato del catálogo, la receta y los topes de
resolución. La descarga real se prueba a mano contra EUMETView y el STAC del
INPE (ver `odd/tasks/satelites-meteosat-cbers.md`).

    .venv\\Scripts\\python.exe -m unittest discover -s app\\tests
"""
from __future__ import annotations

import math
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
for ruta in (RAIZ, RAIZ / "comun"):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))

from app.api import catalog, recipes  # noqa: E402
from comun import cbers, meteosat  # noqa: E402

PREVIOS = {
    "goes_c13", "goes_truecolor", "goes_banda", "goes_lst", "goes_sandwich",
    "geocolor", "truecolor_viirs", "pace_truecolor", "mur_sst", "mur_realista",
    "precipitacion_ecmwf", "anomalia_2t", "viento_250", "snapshot_paraguay",
    "himawari", "follaje", "nisar_render",
}


class Catalogo(unittest.TestCase):
    def test_productos_nuevos_existen(self):
        for producto_id in ("meteosat", "cbers_4a"):
            self.assertIsNotNone(catalog.get_product(producto_id), producto_id)

    def test_no_se_perdio_ningun_producto_previo(self):
        ids = {p.id for p in catalog.PRODUCTS} | {p.id for p in catalog.NISAR_PRODUCTS}
        self.assertTrue(PREVIOS - ids == set(), PREVIOS - ids)

    def test_recetas_registradas(self):
        self.assertIs(recipes._CONSTRUCTORES["meteosat"], recipes._meteosat)
        self.assertIs(recipes._CONSTRUCTORES["cbers_4a"], recipes._cbers)

    def test_meteosat_tiene_variantes_y_ultimos(self):
        producto = catalog.get_product("meteosat")
        nombres = {spec.name for spec in producto.params}
        self.assertIn("variante", nombres)
        self.assertIn("ultimos", nombres)
        self.assertIn("ultimo", nombres)          # lo agrega `_con_ultimo`
        self.assertNotIn("paraguay", nombres)     # el recorte es `encuadre`, no un toggle
        variantes = {o.value for o in next(
            s for s in producto.params if s.name == "variante").options}
        self.assertEqual(variantes, set(meteosat.CAPAS))

    def test_meteosat_elige_encuadre_globo_o_paraguay(self):
        producto = catalog.get_product("meteosat")
        spec = next(s for s in producto.params if s.name == "encuadre")
        self.assertEqual(spec.default, "globo")
        self.assertEqual({o.value for o in spec.options}, {"globo", "paraguay"})

    def test_cbers_sin_snapshot_y_con_zonas(self):
        producto = catalog.get_product("cbers_4a")
        nombres = {spec.name for spec in producto.params}
        self.assertNotIn("snapshot", nombres)
        self.assertNotIn("paraguay", nombres)
        self.assertIn("zona", nombres)
        self.assertIn("detalle", nombres)
        zonas = {o.value for o in next(
            s for s in producto.params if s.name == "zona").options}
        self.assertEqual(zonas, set(cbers.ZONAS))


class Meteosat(unittest.TestCase):
    def test_plan_snapshot_arma_dos_pasos(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = recipes.planear("meteosat", {
                "variante": "geocolour",
                "snapshot": True,
                "ultimo": False,
                "fecha": "2026-11-20",
                "hora": 12,
                "minuto": "30",
                "resolucion": "800",
            }, Path(tmp))
        self.assertEqual([p.kind for p in plan.pasos], ["download", "render"])
        descarga, render = plan.pasos
        self.assertEqual(descarga.script, "descargar/meteosat.py")
        self.assertEqual(descarga.args[descarga.args.index("--encuadre") + 1], "globo")
        self.assertEqual(descarga.args[descarga.args.index("--capa") + 1], "geocolour")
        self.assertEqual(descarga.args[descarga.args.index("--desde") + 1],
                         "2026-11-20T12:30")
        self.assertEqual(render.script, "cuadros/cuadros_meteosat.py")
        self.assertEqual(render.args[render.args.index("--centro") + 1:][:2],
                         ["0", "0"])

    def test_encuadre_paraguay_cambia_los_dos_pasos(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = recipes.planear("meteosat", {
                "variante": "truecolour",
                "encuadre": "paraguay",
                "snapshot": True,
                "ultimo": False,
                "fecha": "2026-11-23",
                "hora": 15,
                "minuto": "00",
                "resolucion": "1400",
            }, Path(tmp))
        descarga, render = plan.pasos
        for paso in (descarga, render):
            self.assertEqual(paso.args[paso.args.index("--encuadre") + 1], "paraguay")
            self.assertNotIn("--globo", paso.args)
        # Sin globo no hay centro que reproyectar.
        self.assertNotIn("--centro", render.args)

    def test_encuadre_desconocido_cae_a_globo(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = recipes.planear("meteosat", {
                "variante": "ir", "encuadre": "inventado", "snapshot": True,
                "ultimo": False, "fecha": "2026-11-23", "hora": 9, "minuto": "00",
            }, Path(tmp))
        self.assertEqual(plan.pasos[0].args[plan.pasos[0].args.index("--encuadre") + 1],
                         "globo")

    def test_placas_por_variante_y_encuadre(self):
        producto = catalog.get_product("meteosat")
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            for nombre in ("meteosat--truecolour--paraguay.webp",
                           "meteosat--truecolour.webp"):
                (carpeta / nombre).write_bytes(b"")
            variantes = catalog._muestras(producto, carpeta)
        self.assertEqual(len(variantes), 2)
        self.assertEqual(variantes[0].when,
                         {"variante": "truecolour", "encuadre": "paraguay"})
        self.assertEqual(variantes[1].when, {"variante": "truecolour"})

    def test_caja_paraguay_es_cuadrada_en_km(self):
        o, s, e, n = meteosat.caja("paraguay")
        lat = (s + n) / 2
        km_lon = (e - o) * 111.32 * math.cos(math.radians(lat))
        km_lat = (n - s) * 110.57
        self.assertAlmostEqual(km_lon, km_lat, delta=km_lat * 0.01)
        # Cubre el país entero con margen.
        self.assertLess(o, -62.6)
        self.assertGreater(e, -54.3)
        self.assertLess(s, -27.5)
        self.assertGreater(n, -19.3)

    def test_caja_desconocida_cae_al_disco(self):
        self.assertEqual(meteosat.caja("inventado"), meteosat.BBOX)
        self.assertEqual(meteosat.caja(), meteosat.BBOX)

    def test_globo_sigue_aceptando_el_flag_viejo(self):
        # El flag `--globo` de los comandos viejos tiene que seguir funcionando.
        self.assertEqual(meteosat.normaliza_encuadre(None, globo=True), "globo")
        self.assertEqual(meteosat.normaliza_encuadre("", globo=True), "globo")
        self.assertEqual(meteosat.normaliza_encuadre("paraguay", globo=False), "paraguay")
        self.assertEqual(meteosat.normaliza_encuadre("paraguay", globo=True), "paraguay")
        self.assertEqual(meteosat.normaliza_encuadre("inventado", globo=False), "globo")

    def test_la_carpeta_de_frames_lleva_el_encuadre(self):
        from cuadros import cuadros_meteosat as render
        from descargar import meteosat as baja
        t = datetime(2026, 11, 23, 15, 0)
        etiqueta = baja._etiqueta("paraguay", t, 1, 1400)
        self.assertEqual(etiqueta, "frames_meteosat_paraguay_2026-11-23T1500_1f_1400px")
        self.assertEqual(render.ts_de_frames(etiqueta), t)

    def test_variante_desconocida_cae_a_geocolour(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = recipes.planear("meteosat", {
                "variante": "inventada", "snapshot": True, "ultimo": False,
                "fecha": "2026-11-20", "hora": 9, "minuto": "00",
            }, Path(tmp))
        self.assertEqual(plan.pasos[0].args[plan.pasos[0].args.index("--capa") + 1],
                         "geocolour")

    def test_url_wms(self):
        url = meteosat.url_cuadro(datetime(2026, 11, 20, 12, 0), "geocolour", 800)
        self.assertIn("request=GetMap", url)
        self.assertIn("layers=mtg_fd%3Argb_geocolour", url)
        self.assertIn("crs=CRS%3A84", url)
        self.assertIn("time=2026-11-20T12%3A00%3A00Z", url)
        self.assertIn("width=800", url)

    def test_url_wms_paraguay_pide_la_caja_del_pais(self):
        o, s, e, n = meteosat.caja("paraguay")
        url = meteosat.url_cuadro(datetime(2026, 11, 20, 15, 0), "truecolour",
                                  ancho=900, alto=900, bbox=(o, s, e, n))
        self.assertIn("layers=mtg_fd%3Argb_truecolour", url)
        self.assertIn(f"bbox={o:g}%2C{s:g}%2C{e:g}%2C{n:g}", url)
        self.assertIn("width=900", url)
        self.assertIn("height=900", url)

    def test_piso_slot(self):
        self.assertEqual(meteosat.piso_slot(datetime(2026, 11, 20, 12, 37)),
                         datetime(2026, 11, 20, 12, 30))


class Cbers(unittest.TestCase):
    def test_recorte_2m_tope_4000(self):
        corte = cbers.recorte("cdeleste", 20, "2")
        self.assertEqual(corte["km"], 8.0)
        self.assertEqual(corte["px"], 4000)
        self.assertAlmostEqual(corte["mpp"], 2.0)

    def test_recorte_8m_y_16m(self):
        ocho = cbers.recorte("asuncion", 20, "8")
        self.assertEqual(ocho["px"], 2500)
        self.assertAlmostEqual(ocho["mpp"], 8.0)
        diesciseis = cbers.recorte("asuncion", 20, "16")
        self.assertEqual(diesciseis["px"], 1250)
        self.assertAlmostEqual(diesciseis["mpp"], 16.0)

    def test_bbox_ordenada(self):
        o, s, e, n = cbers.bbox_zona("asuncion", 16)
        self.assertLess(o, e)
        self.assertLess(s, n)

    def test_zonas_2m_son_subconjunto(self):
        self.assertTrue(set(cbers.ZONAS_2M) <= set(cbers.ZONAS))

    def test_plan_con_fecha_fija(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = recipes.planear("cbers_4a", {
                "zona": "encarnacion",
                "km": 8,
                "detalle": "2",
                "ultima": False,
                "fecha": "2026-11-20",
            }, Path(tmp))
        self.assertEqual([p.kind for p in plan.pasos], ["download", "render"])
        descarga, render = plan.pasos
        self.assertEqual(descarga.script, "descargar/cbers.py")
        self.assertEqual(descarga.args[descarga.args.index("--zona") + 1], "encarnacion")
        self.assertEqual(descarga.args[descarga.args.index("--detalle") + 1], "2")
        self.assertEqual(descarga.args[descarga.args.index("--desde") + 1], "2026-11-20")
        self.assertEqual(descarga.args[descarga.args.index("--hasta") + 1], "2026-11-20")
        self.assertEqual(render.script, "cuadros/cuadros_cbers.py")

    def test_2m_fuera_de_zona_cae_a_8m(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = recipes.planear("cbers_4a", {
                "zona": "asuncion", "km": 8, "detalle": "2",
                "ultima": False, "fecha": "2026-11-20",
            }, Path(tmp))
        self.assertEqual(plan.pasos[0].args[plan.pasos[0].args.index("--detalle") + 1],
                         "8")


if __name__ == "__main__":
    unittest.main()
