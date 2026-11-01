"""Pruebas de la cadencia de pasos de ECMWF y del producto de viento en 250 mb.

ECMWF Open Data no publica una grilla uniforme de pasos (verificado contra el
portal el 2026-11-01):

    IFS 00/12z    0-144 h cada 3 h, 150-360 h cada 6 h   (147 h no existe)
    IFS 06/18z    0-144 h cada 3 h
    AIFS          0-360 h cada 6 h                        (3 h no existe)

Pedir pasos de 3 h por encima de 144 h (147, 153, ...) devuelve 404 y el job
muere con "faltan los pasos". Estas pruebas fijan la regla sin tocar la red.

    app\\.venv\\Scripts\\python.exe -m unittest discover -s app\\tests
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from app.api import catalog, recipes  # noqa: E402

DIA = date(2026, 10, 20)


class CadenciaDePasos(unittest.TestCase):
    """`_paso_horas_ecmwf`: horas entre pasos que la corrida publica de verdad."""

    def test_ifs_hasta_144_usa_pasos_de_3_horas(self):
        self.assertEqual(recipes._paso_horas_ecmwf("ifs", 144), 3)
        self.assertEqual(recipes._paso_horas_ecmwf("ifs", 96), 3)

    def test_ifs_mas_alla_de_144_usa_pasos_de_6_horas(self):
        self.assertEqual(recipes._paso_horas_ecmwf("ifs", 150), 6)
        self.assertEqual(recipes._paso_horas_ecmwf("ifs", 240), 6)

    def test_aifs_usa_6_horas_siempre(self):
        for modelo in ("aifs-single", "aifs-ens"):
            self.assertEqual(recipes._paso_horas_ecmwf(modelo, 24), 6)
            self.assertEqual(recipes._paso_horas_ecmwf(modelo, 144), 6)
            self.assertEqual(recipes._paso_horas_ecmwf(modelo, 360), 6)


class HorizontePublicado(unittest.TestCase):
    """`_horizonte_disponible` alinea el horizonte a la grilla de pasos real."""

    def _falso_publicado(self, publicados: set[int]):
        return lambda modelo, dia, ciclo, hora: hora in publicados

    def test_encuentra_el_horizonte_pedido_si_esta_publicado(self):
        with mock.patch.object(recipes, "_publicado",
                               side_effect=self._falso_publicado({0, 144, 240})):
            self.assertEqual(recipes._horizonte_disponible("ifs", DIA, "00", 240, 6), 240)

    def test_baja_al_ultimo_paso_publicado_de_la_misma_grilla(self):
        # 18z publica hasta 144 h; se pide 240 -> se recorta a 144.
        publicados = set(range(0, 145, 6))
        with mock.patch.object(recipes, "_publicado",
                               side_effect=self._falso_publicado(publicados)):
            self.assertEqual(recipes._horizonte_disponible("ifs", DIA, "18", 240, 6), 144)

    def test_horizonte_no_alineado_no_pierde_la_corrida(self):
        # Un 145 pedido a mano no existe en la grilla; 144 sí.
        publicados = set(range(0, 145, 3))
        with mock.patch.object(recipes, "_publicado",
                               side_effect=self._falso_publicado(publicados)):
            self.assertEqual(recipes._horizonte_disponible("ifs", DIA, "00", 145, 3), 144)

    def test_sin_ningun_paso_publicado_devuelve_cero(self):
        with mock.patch.object(recipes, "_publicado",
                               side_effect=self._falso_publicado(set())):
            self.assertEqual(recipes._horizonte_disponible("ifs", DIA, "00", 144, 3), 0)


class UrlDelIndice(unittest.TestCase):
    """El sufijo del `.index` no debe confundirse con la grilla de pasos."""

    def test_la_url_usa_el_sufijo_del_paso(self):
        url = recipes._url_indice("ifs", DIA, "00", 144)
        self.assertTrue(url.endswith("/20261020000000-144h-oper-fc.index"), url)


class PlanPrecipitacion(unittest.TestCase):
    """El plan real no debe volver a pedir pasos de 3 h más allá de 144 h."""

    def _plan(self, horizonte: int, modelo: str = "ifs") -> recipes.Plan:
        with tempfile.TemporaryDirectory() as tmp:
            return recipes._ecmwf_producto(
                "precipitacion",
                {"fecha": DIA.isoformat(), "corrida": "00", "modelo": modelo,
                 "horizonte": horizonte},
                Path(tmp),
            )

    def test_horizonte_144_conserva_los_3_h(self):
        plan = self._plan(144)
        descarga = plan.descarga
        assert descarga is not None
        self.assertEqual(descarga.args[descarga.args.index("--paso") + 1], "3")

    def test_horizonte_240_usa_6_h(self):
        plan = self._plan(240)
        descarga = plan.descarga
        assert descarga is not None
        self.assertEqual(descarga.args[descarga.args.index("--paso") + 1], "6")

    def test_ningun_paso_pedido_cae_fuera_de_la_grilla_publicada(self):
        plan = self._plan(240)
        descarga = plan.descarga
        assert descarga is not None
        paso = int(descarga.args[descarga.args.index("--paso") + 1])
        hasta = int(descarga.args[descarga.args.index("--hasta-hora") + 1])
        pedidos = range(0, hasta + 1, paso)
        fuera = [h for h in pedidos if h > 144 and h % 6 != 0]
        self.assertEqual(fuera, [])

    def test_aifs_no_pide_pasos_de_3_h(self):
        plan = self._plan(144, modelo="aifs-single")
        descarga = plan.descarga
        assert descarga is not None
        self.assertEqual(descarga.args[descarga.args.index("--paso") + 1], "6")


class ProductoViento(unittest.TestCase):
    """El flujo de viento en 250 mb ya existe en el repo: se expone en la app."""

    def test_esta_en_el_catalogo(self):
        producto = catalog.get_product("viento_250")
        self.assertIsNotNone(producto)
        assert producto is not None
        horizonte = next(p for p in producto.params if p.name == "horizonte")
        self.assertEqual(horizonte.max, 144)
        self.assertEqual(horizonte.default, 144)

    def test_plan_usa_los_scripts_del_repo(self):
        params = {
            "fecha": DIA.isoformat(),
            "corrida": "18",
            "horizonte": 144,
            "fondo": "oscuro",
            "resolucion": "2712",
        }
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            with mock.patch.object(catalog, "data_root", return_value=work):
                plan = recipes.planear("viento_250", params, work)

        scripts = [paso.script for paso in plan.pasos]
        self.assertEqual(scripts, ["descargar/viento_250_mslp.py",
                                   "cuadros/cuadros_viento_250.py"])

        descarga, render = plan.pasos
        self.assertEqual(descarga.args[descarga.args.index("--paso") + 1], "3")
        self.assertEqual(descarga.args[descarga.args.index("--hasta-hora") + 1], "144")
        self.assertEqual(render.args[render.args.index("--fondo-globo") + 1], "oscuro")
        self.assertEqual(render.args[render.args.index("--px") + 1], "2712")
        self.assertEqual(render.args[render.args.index("--salidas") + 1], str(work))

    def test_sin_crudos_el_plan_descarga(self):
        params = {"fecha": DIA.isoformat(), "corrida": "18", "horizonte": 144}
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            with mock.patch.object(catalog, "data_root", return_value=work):
                plan = recipes.planear("viento_250", params, work)
        self.assertEqual(len(plan.pasos), 2)

    def test_con_crudos_el_plan_solo_renderiza(self):
        params = {"fecha": DIA.isoformat(), "corrida": "18", "horizonte": 144}
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            crudos = work / "crudos_viento250_2026-10-20_18z"
            crudos.mkdir(parents=True)
            # 0..144 h cada 3 h: el último paso es el 49 de la grilla.
            (crudos / "crudo_049_fh144_u.grib2").write_bytes(b"x")
            with mock.patch.object(catalog, "data_root", return_value=work):
                plan = recipes.planear("viento_250", params, work)
        self.assertEqual([paso.script for paso in plan.pasos],
                         ["cuadros/cuadros_viento_250.py"])

    def test_un_horizonte_nuevo_vuelve_a_descargar(self):
        # En disco sólo hay crudos hasta 96 h; pedir 144 h no puede saltarse la
        # descarga (antes bastaba con que la carpeta tuviera algo).
        params = {"fecha": DIA.isoformat(), "corrida": "18", "horizonte": 144}
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            crudos = work / "crudos_viento250_2026-10-20_18z"
            crudos.mkdir(parents=True)
            (crudos / "crudo_001_fh000_u.grib2").write_bytes(b"x")
            with mock.patch.object(catalog, "data_root", return_value=work):
                plan = recipes.planear("viento_250", params, work)
        self.assertEqual(len(plan.pasos), 2)

    def test_animar_agrega_el_paso_de_animacion(self):
        params = {"fecha": DIA.isoformat(), "corrida": "18", "horizonte": 144,
                  "animar": True, "fps": 12}
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            with mock.patch.object(catalog, "data_root", return_value=work):
                plan = recipes.planear("viento_250", params, work)
        self.assertEqual(plan.pasos[-1].script, "animar/armar.py")


class CatalogoDeLaApp(unittest.TestCase):
    """S1, S2, S3, S5, S6 y S7: el esquema que ve la interfaz."""

    def _spec(self, product_id: str, nombre: str):
        producto = catalog.get_product(product_id)
        assert producto is not None, product_id
        return next(p for p in producto.params if p.name == nombre)

    def test_precipitacion_y_anomalia_no_pasan_de_144_h(self):
        for product_id in ("precipitacion_ecmwf", "anomalia_2t", "viento_250"):
            horizonte = self._spec(product_id, "horizonte")
            self.assertEqual(horizonte.max, 144, product_id)
            self.assertEqual(horizonte.default, 144, product_id)

    def test_ciclo_por_defecto_en_00(self):
        for product_id in ("precipitacion_ecmwf", "anomalia_2t", "viento_250"):
            self.assertEqual(self._spec(product_id, "corrida").default, "00", product_id)

    def test_resoluciones_estandar_en_todos(self):
        esperadas = ["1400", "1800", "2000", "2400", "2712"]
        for producto in catalog.PRODUCTS:
            specs = [p for p in producto.params if p.name == "resolucion"]
            if not specs:
                continue
            opciones = specs[0].options
            self.assertEqual([o.value for o in opciones], esperadas, producto.id)
            # S5: el rótulo es el número solo, sin "poster" ni "nativo".
            self.assertEqual([o.label for o in opciones], esperadas, producto.id)

    def test_animar_y_descargar_arrancan_activos(self):
        for product_id in ("precipitacion_ecmwf", "anomalia_2t", "viento_250"):
            self.assertIs(self._spec(product_id, "animar").default, True, product_id)
            self.assertIs(self._spec(product_id, "descargar").default, True, product_id)

    def test_viento_ofrece_ifs_y_gfs(self):
        modelos = {o.value for o in self._spec("viento_250", "modelo").options}
        self.assertEqual(modelos, {"ifs", "gfs"})


class ModeloGfs(unittest.TestCase):
    """S8: GFS como fuente del viento en 250 mb."""

    def test_gfs_usa_pasos_de_3_horas(self):
        self.assertEqual(recipes._paso_horas_ecmwf("gfs", 144), 3)

    def test_la_url_del_indice_apunta_al_bucket_de_gfs(self):
        url = recipes._url_indice("gfs", DIA, "00", 144)
        self.assertEqual(
            url,
            "https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.20261020/00/atmos/"
            "gfs.t00z.pgrb2.0p25.f144.idx",
        )

    def test_el_plan_pasa_el_modelo_y_la_carpeta(self):
        params = {"modelo": "gfs", "fecha": DIA.isoformat(), "corrida": "00",
                  "horizonte": 144}
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            with mock.patch.object(catalog, "data_root", return_value=work):
                plan = recipes.planear("viento_250", params, work)
        descarga = plan.descarga
        assert descarga is not None
        self.assertEqual(descarga.args[descarga.args.index("--modelo") + 1], "gfs")
        self.assertEqual(descarga.args[descarga.args.index("--paso") + 1], "3")

    def test_los_crudos_de_gfs_viven_en_su_propia_carpeta(self):
        params = {"modelo": "gfs", "fecha": DIA.isoformat(), "corrida": "00",
                  "horizonte": 144}
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            crudos = work / "crudos_viento250_gfs_2026-10-20_00z"
            crudos.mkdir(parents=True)
            (crudos / "crudo_049_fh144_u.grib2").write_bytes(b"x")
            with mock.patch.object(catalog, "data_root", return_value=work):
                plan = recipes.planear("viento_250", params, work)
        self.assertEqual([paso.script for paso in plan.pasos],
                         ["cuadros/cuadros_viento_250.py"])


class SnapshotParaguay(unittest.TestCase):
    """La captura: cobertura desde el GeoJSON, un solo cuadro y sin rótulos."""

    def test_la_caja_sale_del_geojson_y_agranda_con_margen(self):
        from comun.paraguay import caja_geojson

        ruta = RAIZ / "datos" / "paraguay_gadm.json"
        o, s, e, n = caja_geojson(ruta, 0.0)
        # Los extremos reales del país (GADM), sin margen.
        self.assertAlmostEqual(o, -62.642, places=2)
        self.assertAlmostEqual(e, -54.259, places=2)
        self.assertAlmostEqual(s, -27.606, places=2)
        self.assertAlmostEqual(n, -19.295, places=2)

        om, sm, em, nm = caja_geojson(ruta, 0.06)
        self.assertLess(om, o)
        self.assertLess(sm, s)
        self.assertGreater(em, e)
        self.assertGreater(nm, n)

    def test_el_nombre_del_crudo_y_de_la_captura_es_estable(self):
        from comun.paraguay import nombre_captura, nombre_crudo
        from datetime import datetime

        t = datetime(2026, 11, 1, 15, 0)
        self.assertEqual(nombre_crudo(t, 2000), "crudo_snapshot_20261101T1500_2000px.png")
        self.assertEqual(nombre_captura(t, 2000),
                         "snapshot_paraguay_2026-11-01T1500_2000px.png")

    def test_esta_en_el_catalogo_con_un_solo_cuadro(self):
        producto = catalog.get_product("snapshot_paraguay")
        self.assertIsNotNone(producto)
        assert producto is not None
        nombres = [p.name for p in producto.params]
        self.assertIn("hora", nombres)
        self.assertIn("margen", nombres)
        self.assertIn("borde", nombres)
        # No es una animación: no ofrece "animar" ni "fps".
        self.assertNotIn("animar", nombres)
        self.assertNotIn("fps", nombres)

    def test_el_plan_descarga_y_compone(self):
        params = {"fecha": DIA.isoformat(), "hora": 15, "minuto": "30",
                  "margen": 8, "resolucion": "2000", "borde": True}
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            plan = recipes.planear("snapshot_paraguay", params, work)

        self.assertEqual([paso.script for paso in plan.pasos],
                         ["descargar/snapshot_paraguay.py",
                          "cuadros/snapshot_paraguay.py"])
        descarga, render = plan.pasos
        self.assertEqual(descarga.args[descarga.args.index("--hora") + 1], "15")
        self.assertEqual(descarga.args[descarga.args.index("--minuto") + 1], "30")
        self.assertEqual(descarga.args[descarga.args.index("--margen") + 1], "0.08")
        self.assertEqual(descarga.args[descarga.args.index("--px") + 1], "2000")
        self.assertEqual(descarga.args[descarga.args.index("--out") + 1],
                         str(work / "crudos"))
        self.assertEqual(render.args[render.args.index("--entrada") + 1],
                         str(work / "crudos"))
        self.assertEqual(render.args[render.args.index("--salidas") + 1], str(work))
        self.assertNotIn("--sin-borde", render.args)

    def test_sin_borde_lo_pide_al_render(self):
        params = {"fecha": DIA.isoformat(), "hora": 3, "borde": False}
        with tempfile.TemporaryDirectory() as tmp:
            plan = recipes.planear("snapshot_paraguay", params, Path(tmp))
        render = plan.pasos[-1]
        self.assertIn("--sin-borde", render.args)


if __name__ == "__main__":
    unittest.main()
