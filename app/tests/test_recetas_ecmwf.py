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

from app.api import catalog, jobs as api_jobs, recipes  # noqa: E402
from app.api.schemas import Artifact, LogLine  # noqa: E402

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
        esperadas = ["1400", "1800", "2000", "2400", "2712", "3200", "4000"]
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
        self.assertEqual(nombre_crudo("truecolor", t, 3200),
                         "crudo_snapshot_truecolor_20261101T1500_3200px.png")
        self.assertEqual(nombre_captura("geocolor", t, 3200),
                         "snapshot_paraguay_geocolor_2026-11-01T1500_3200px.png")

    def test_la_capa_diaria_pide_la_fecha_sola(self):
        from comun.paraguay import url_snapshot
        from datetime import datetime

        t = datetime(2026, 10, 30, 15, 0)
        caja = (-63.0, -28.0, -54.0, -19.0)
        diaria = url_snapshot(t, caja, 3200, "truecolor")
        self.assertIn("TIME=2026-10-30&", diaria)
        self.assertIn("VIIRS_NOAA20_CorrectedReflectance_TrueColor", diaria)
        geo = url_snapshot(t, caja, 3200, "geocolor")
        self.assertIn("TIME=2026-10-30T15:00:00Z", geo)
        self.assertIn("GOES-East_ABI_GeoColor", geo)

    def test_esta_en_el_catalogo_con_un_solo_cuadro(self):
        producto = catalog.get_product("snapshot_paraguay")
        self.assertIsNotNone(producto)
        assert producto is not None
        nombres = [p.name for p in producto.params]
        self.assertIn("capa", nombres)
        self.assertIn("hora", nombres)
        self.assertIn("margen", nombres)
        self.assertIn("borde", nombres)
        capa = next(p for p in producto.params if p.name == "capa")
        self.assertEqual(
            {o.value for o in capa.options},
            {"truecolor", "snpp", "aqua", "terra", "geocolor"},
        )
        detalle = next(p for p in producto.params if p.name == "detalle")
        self.assertEqual(detalle.default, "250")
        self.assertEqual({o.value for o in detalle.options},
                         {"125", "250", "500", "1000", "2000"})
        # No es una animación: no ofrece "animar" ni "fps".
        self.assertNotIn("animar", nombres)
        self.assertNotIn("fps", nombres)

    def test_el_plan_descarga_y_compone(self):
        params = {"capa": "truecolor", "ultima": False, "fecha": DIA.isoformat(),
                  "hora": 15, "minuto": "30", "margen": 8, "detalle": "250",
                  "borde": True}
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
        self.assertEqual(descarga.args[descarga.args.index("--mpp") + 1], "250")
        self.assertNotIn("--px", descarga.args)
        self.assertEqual(descarga.args[descarga.args.index("--capa") + 1], "truecolor")
        self.assertEqual(descarga.args[descarga.args.index("--out") + 1],
                         str(work / "crudos"))
        self.assertEqual(render.args[render.args.index("--entrada") + 1],
                         str(work / "crudos"))
        self.assertEqual(render.args[render.args.index("--salidas") + 1], str(work))
        self.assertNotIn("--sin-borde", render.args)
        # Sin "última disponible" se respeta la hora pedida.
        self.assertNotIn("--ultima", descarga.args)

    def test_sin_borde_lo_pide_al_render(self):
        params = {"fecha": DIA.isoformat(), "hora": 3, "borde": False}
        with tempfile.TemporaryDirectory() as tmp:
            plan = recipes.planear("snapshot_paraguay", params, Path(tmp))
        render = plan.pasos[-1]
        self.assertIn("--sin-borde", render.args)

    def test_ultima_disponible_se_pide_en_los_dos_pasos(self):
        params = {"capa": "geocolor", "ultima": True, "fecha": DIA.isoformat()}
        with tempfile.TemporaryDirectory() as tmp:
            plan = recipes.planear("snapshot_paraguay", params, Path(tmp))
        self.assertIn("--ultima", plan.pasos[0].args)
        self.assertIn("--ultima", plan.pasos[1].args)

    def test_la_ultima_es_el_default_del_producto(self):
        producto = catalog.get_product("snapshot_paraguay")
        assert producto is not None
        ultima = next(p for p in producto.params if p.name == "ultima")
        self.assertIs(ultima.default, True)

    def test_el_paso_y_el_techo_dependen_de_la_capa(self):
        from comun.paraguay import paso, techo
        from datetime import datetime, timedelta

        ahora = datetime(2026, 11, 1, 18, 47)
        self.assertEqual(techo("geocolor", ahora), datetime(2026, 11, 1, 18, 40))
        self.assertEqual(techo("truecolor", ahora), datetime(2026, 11, 1, 0, 0))
        self.assertEqual(paso("geocolor"), timedelta(minutes=10))
        self.assertEqual(paso("truecolor"), timedelta(days=1))

    def test_el_instante_se_lee_del_nombre_del_crudo(self):
        from comun.paraguay import ts_de_crudo
        from datetime import datetime

        self.assertEqual(
            ts_de_crudo("crudo_snapshot_geocolor_20261101T1740_1400px.png"),
            datetime(2026, 11, 1, 17, 40),
        )
        self.assertIsNone(ts_de_crudo("otra_cosa.png"))

    def test_metros_por_pixel_calculan_el_lado(self):
        from comun.paraguay import caja_geojson, px_para_mpp

        caja = caja_geojson(RAIZ / "datos" / "paraguay_gadm.json", 0.06)
        # ~9,4° de lado: a 250 m/px son ~4200 px; a 125 m/px, el doble.
        a250 = px_para_mpp(caja, 250)
        a125 = px_para_mpp(caja, 125)
        self.assertGreater(a250, 3500)
        self.assertLess(a250, 4500)
        self.assertAlmostEqual(a125 / a250, 2, delta=0.1)
        # El tope evita pedir un lado imposible.
        self.assertEqual(px_para_mpp(caja, 10), 8000)

    def test_avisa_cuando_el_detalle_supera_al_de_la_capa(self):
        from comun.paraguay import aviso_de_detalle

        self.assertIsNotNone(aviso_de_detalle("geocolor", 125))
        self.assertIsNone(aviso_de_detalle("geocolor", 700))
        self.assertIsNone(aviso_de_detalle("truecolor", 250))
        self.assertIsNotNone(aviso_de_detalle("truecolor", 125))


class ColaEHistorial(unittest.TestCase):
    """La lista de corridas: cola, historial y lo que sobrevive al reinicio."""

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.media = Path(self.temporal.name)

    def _job(self, ident, *, estado="done", creado="2026-11-01T10:00:00+00:00"):
        return api_jobs.Job(
            id=ident,
            product_id="demo",
            product_name="Demo",
            params={},
            mode="real",
            status=estado,
            created_at=creado,
            dir=self.media / "cache" / ident,
        )

    def test_el_listado_va_de_lo_mas_nuevo_a_lo_mas_viejo(self):
        gestor = api_jobs.JobManager(self.media)
        gestor.jobs["viejo"] = self._job("viejo", creado="2026-11-01T08:00:00+00:00")
        gestor.jobs["nuevo"] = self._job("nuevo", creado="2026-11-01T09:00:00+00:00")

        self.assertEqual([f.id for f in gestor.listar_resumen()], ["nuevo", "viejo"])

    def test_el_resumen_no_arrastra_el_log(self):
        job = self._job("a")
        job.logs.append(LogLine(at="2026-11-01T10:00:00+00:00", text="hola"))

        resumen = job.resumen()

        self.assertEqual(resumen.id, "a")
        self.assertFalse(hasattr(resumen, "logs"))
        self.assertFalse(hasattr(resumen, "artifacts"))

    def test_un_reinicio_relee_las_corridas_terminadas(self):
        gestor = api_jobs.JobManager(self.media)
        job = self._job("a")
        job.dir.mkdir(parents=True)
        gestor.jobs["a"] = job
        gestor._guardar(job)

        otro = api_jobs.JobManager(self.media)  # simula el reinicio de la API

        self.assertEqual([f.id for f in otro.listar_resumen()], ["a"])
        self.assertEqual(otro.obtener("a").status, "done")

    def test_una_corrida_que_sigue_en_cola_no_se_guarda(self):
        gestor = api_jobs.JobManager(self.media)

        gestor._guardar(self._job("a", estado="running"))

        self.assertFalse((self.media / api_jobs.HISTORIAL).exists())

    def test_al_releer_no_muestra_placas_borradas(self):
        gestor = api_jobs.JobManager(self.media)
        job = self._job("a")
        job.dir.mkdir(parents=True)
        (job.dir / "ok.png").write_bytes(b"png")
        job.artifacts = [
            Artifact(name="ok.png", url="/media/cache/a/ok.png", kind="image", bytes=3),
            Artifact(name="ido.png", url="/media/cache/a/ido.png", kind="image", bytes=3),
        ]
        gestor._guardar(job)

        otro = api_jobs.JobManager(self.media)

        detalle = otro.obtener("a")
        self.assertIsNotNone(detalle)
        self.assertEqual([a.name for a in detalle.artifacts], ["ok.png"])

    def test_una_linea_rota_no_se_lleva_el_historial(self):
        (self.media / api_jobs.HISTORIAL).write_text(
            'no es json\n{"job": 1}\n', encoding="utf-8"
        )

        gestor = api_jobs.JobManager(self.media)

        self.assertEqual(gestor.listar_resumen(), [])

    def test_podar_olvida_las_mas_viejas_y_no_las_mas_nuevas(self):
        gestor = api_jobs.JobManager(self.media, max_historial=2)
        for hora in ("08", "09", "10"):
            ident = f"j{hora}"
            gestor.jobs[ident] = self._job(
                ident, creado=f"2026-11-01T{hora}:00:00+00:00"
            )

        gestor._podar()

        self.assertEqual(set(gestor.jobs), {"j09", "j10"})


if __name__ == "__main__":
    unittest.main()
