"""Pruebas de los focos de calor de FIRMS sobre la captura de Paraguay.

Fijan lo que la app promete:

  * el CSV de FIRMS se lee con las dos formas de `confidence` (VIIRS `l/n/h` y
    MODIS 0-100) y con `acq_time` sin cero a la izquierda;
  * la ventana es el día UTC completo por defecto y horas a cada lado para GeoColor;
  * el foco cae en el píxel que le corresponde (misma proyección que el contorno);
  * sin MAP_KEY el error dice qué falta y dónde ponerlo;
  * sin focos la captura sale **idéntica** a la de sin `--firms`;
  * la receta mete el paso de FIRMS entre GIBS y el render.

    app\\.venv\\Scripts\\python.exe -m unittest discover -s app\\tests
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
for ruta in (RAIZ, RAIZ / "comun", RAIZ / "cuadros"):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))

import firms  # noqa: E402
import snapshot_paraguay as snapshot  # noqa: E402
from PIL import Image  # noqa: E402

from app.api import catalog, recipes  # noqa: E402

CABECERA = ("latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,"
            "satellite,instrument,confidence,version,bright_ti5,frp,daynight")

FILA_VIIRS = "-23.40,-58.20,310.1,0.39,0.36,2026-11-08,522,N20,VIIRS,n,2.0NRT,285.1,3.40,N"
FILA_MODIS = "-24.10,-57.30,318.7,1.79,1.31,2026-11-08,1236,Terra,MODIS,77,6.1NRT,293.5,30.25,D"
FILA_MAL = "-24.10,-57.30,318.7,1.79,1.31,2026-13-45,1236,Terra,MODIS,77,6.1NRT,293.5,30.25,D"


class Parser(unittest.TestCase):
    """El CSV de FIRMS se lee sin importar de qué sensor venga."""

    def test_lee_viirs_con_confianza_en_letras(self):
        focos = firms.leer_texto(f"{CABECERA}\n{FILA_VIIRS}\n")
        self.assertEqual(len(focos), 1)
        foco = focos[0]
        self.assertAlmostEqual(foco.lat, -23.40)
        self.assertAlmostEqual(foco.lon, -58.20)
        self.assertAlmostEqual(foco.frp, 3.40)
        self.assertEqual(foco.confianza, "nominal")
        self.assertEqual(foco.satelite, "N20")
        self.assertEqual(foco.dia_noche, "N")

    def test_lee_acq_time_sin_cero_a_la_izquierda(self):
        foco = firms.leer_texto(f"{CABECERA}\n{FILA_VIIRS}\n")[0]
        self.assertEqual(foco.cuando, datetime(2026, 11, 8, 5, 22))

    def test_lee_modis_con_confianza_numerica(self):
        foco = firms.leer_texto(f"{CABECERA}\n{FILA_MODIS}\n")[0]
        self.assertEqual(foco.confianza, "nominal")
        self.assertAlmostEqual(foco.frp, 30.25)

    def test_la_confianza_numerica_ordena_baja_nominal_alta(self):
        filas = "\n".join(
            FILA_MODIS.replace(",77,", f",{valor},") for valor in ("10", "55", "95"))
        valores = [f.confianza for f in firms.leer_texto(f"{CABECERA}\n{filas}\n")]
        self.assertEqual(valores, ["baja", "nominal", "alta"])

    def test_una_fila_rota_no_se_lleva_puesto_el_resto(self):
        focos = firms.leer_texto(f"{CABECERA}\n{FILA_MAL}\n{FILA_VIIRS}\n")
        self.assertEqual(len(focos), 1)

    def test_una_respuesta_que_no_es_csv_devuelve_vacio(self):
        self.assertEqual(firms.leer_texto("Invalid MAP_KEY."), [])

    def test_el_csv_normalizado_ida_y_vuelta(self):
        original = firms.leer_texto(f"{CABECERA}\n{FILA_VIIRS}\n{FILA_MODIS}\n")
        carpeta = Path(tempfile.mkdtemp(prefix="firms-"))
        try:
            ruta = firms.escribir(carpeta / "focos.csv", original)
            leidos = firms.leer(ruta)
        finally:
            shutil.rmtree(carpeta, ignore_errors=True)
        self.assertEqual(len(leidos), 2)
        self.assertEqual([f.confianza for f in leidos], ["nominal", "nominal"])
        self.assertEqual([f.cuando for f in leidos], [f.cuando for f in original])


class Ventana(unittest.TestCase):
    """El día completo por defecto; horas a cada lado para GeoColor."""

    def test_el_dia_va_de_medianoche_a_medianoche(self):
        desde, hasta = firms.ventana(datetime(2026, 11, 8, 15, 40), "dia")
        self.assertEqual(desde, datetime(2026, 11, 8))
        self.assertEqual(hasta, datetime(2026, 11, 9))

    def test_las_horas_son_a_cada_lado_del_slot(self):
        desde, hasta = firms.ventana(datetime(2026, 11, 8, 15, 40), "3h")
        self.assertEqual(desde, datetime(2026, 11, 8, 12, 40))
        self.assertEqual(hasta, datetime(2026, 11, 8, 18, 40))

    def test_una_ventana_desconocida_cae_al_dia(self):
        self.assertEqual(firms.ventana(datetime(2026, 11, 8, 9), "9d"),
                         firms.ventana(datetime(2026, 11, 8, 9), "dia"))

    def test_el_nombre_del_csv_cambia_con_la_ventana(self):
        cuando = datetime(2026, 11, 8, 15)
        dia = firms.nombre_csv(cuando, "dia")
        tres = firms.nombre_csv(cuando, "3h")
        self.assertEqual(dia, "focos_20261108T0000_20261109T0000.csv")
        self.assertNotEqual(dia, tres)
        self.assertEqual(firms.nombre_csv(cuando, "3h"), tres)

    def test_la_etiqueta_del_dia_es_la_fecha(self):
        self.assertEqual(firms.etiqueta(datetime(2026, 11, 8, 15), "dia"),
                         "2026-11-08")


class Filtro(unittest.TestCase):
    """`[desde, hasta)`: el borde de entrada entra, el de salida no."""

    def _focos(self):
        texto = "\n".join(
            FILA_VIIRS.replace(",522,", f",{hora}00,") for hora in (0, 5, 12, 17, 23))
        return firms.leer_texto(f"{CABECERA}\n{texto}\n")

    def test_el_dia_toma_las_cinco_horas(self):
        focos = firms.filtrar(self._focos(), *firms.ventana(
            datetime(2026, 11, 8, 15), "dia"))
        self.assertEqual(len(focos), 5)

    def test_tres_horas_solo_toma_los_pasos_cercanos(self):
        # VIIRS pasa ~05 y ~17 UTC: a las 15:00 sólo entra el paso de la tarde.
        focos = firms.filtrar(self._focos(), *firms.ventana(
            datetime(2026, 11, 8, 15), "3h"))
        self.assertEqual([f.cuando.hour for f in focos], [12, 17])

    def test_tres_horas_a_media_manana_no_trae_ningun_paso(self):
        focos = firms.filtrar(self._focos(), *firms.ventana(
            datetime(2026, 11, 8, 9), "3h"))
        self.assertEqual(focos, [])


class Clave(unittest.TestCase):
    """Sin MAP_KEY el mensaje dice qué falta y dónde ponerlo."""

    def test_la_variable_de_entorno_gana(self):
        with mock.patch.dict(os.environ, {"FIRMS_MAP_KEY": "abc123"}):
            self.assertEqual(firms.clave_mapa(), "abc123")

    def test_sin_clave_el_error_lo_explica(self):
        with mock.patch.dict(os.environ, {"FIRMS_MAP_KEY": ""}), \
                mock.patch.object(firms, "CLAVE_ARCHIVO",
                                  Path("C:/no/existe/firms_map_key.txt")):
            with self.assertRaises(SystemExit) as contexto:
                firms.clave_mapa()
        self.assertIn("MAP_KEY", str(contexto.exception))

    def test_la_url_arma_la_caja_como_la_espera_firms(self):
        url = firms.url_focos("K", "VIIRS_NOAA20_NRT",
                              (-63.145428, -28.10433, -53.755572, -18.79657),
                              date(2026, 11, 8), 1)
        self.assertTrue(url.endswith(
            "/K/VIIRS_NOAA20_NRT/-63.14543,-28.10433,-53.75557,-18.79657/1/2026-11-08"))

    def test_los_dias_se_acotan_a_lo_que_deja_la_api(self):
        url = firms.url_focos("K", "MODIS_NRT", (-63, -28, -53, -18),
                              date(2026, 11, 8), 99)
        self.assertIn("/5/2026-11-08", url)


class Dibujo(unittest.TestCase):
    """El foco cae en su píxel y sin focos la captura no cambia."""

    CAJA = (-63.0, -28.0, -53.0, -18.0)
    LADO = 400

    def test_el_centro_de_la_caja_es_el_centro_de_la_imagen(self):
        x, y = snapshot._a_pixel(-58.0, -23.0, self.CAJA, self.LADO, 1)
        self.assertAlmostEqual(x, 200.0)
        self.assertAlmostEqual(y, 200.0)

    def test_un_foco_pinta_su_pixel_y_no_el_resto(self):
        lienzo = Image.new("RGB", (self.LADO, self.LADO), (0, 0, 0))
        foco = firms.Foco(lat=-23.0, lon=-58.0, frp=5.0, confianza="alta",
                          cuando=datetime(2026, 11, 8, 17), satelite="N20",
                          instrumento="VIIRS", dia_noche="D")
        fuera = snapshot.dibujar_focos(lienzo, self.CAJA, [foco], self.LADO)
        self.assertNotEqual(fuera.getpixel((200, 200)), (0, 0, 0))
        self.assertEqual(fuera.getpixel((10, 10)), (0, 0, 0))

    def test_sin_focos_no_toca_un_pixel(self):
        carpeta = Path(tempfile.mkdtemp(prefix="firms-"))
        try:
            crudo = carpeta / "crudo.png"
            Image.new("RGB", (self.LADO, self.LADO), (40, 80, 120)).save(crudo)
            geojson = RAIZ / "datos" / "paraguay_gadm.json"
            sin = snapshot.componer(crudo, self.CAJA, geojson, self.LADO,
                                    borde=False)
            vacio = snapshot.componer(crudo, self.CAJA, geojson, self.LADO,
                                      borde=False, focos=[])
            self.assertEqual(sin.tobytes(), vacio.tobytes())
        finally:
            shutil.rmtree(carpeta, ignore_errors=True)


class CatalogoYReceta(unittest.TestCase):
    """El toggle existe y la receta ordena GIBS -> FIRMS -> render."""

    def _params(self, **extra):
        params = {s.name: s.default for s in catalog.get_product("snapshot_paraguay").params}
        params.update(extra)
        return params

    def test_el_producto_expone_el_toggle_y_sus_opciones(self):
        producto = catalog.get_product("snapshot_paraguay")
        nombres = {s.name: s for s in producto.params}
        self.assertIn("firms", nombres)
        self.assertFalse(nombres["firms"].default)
        for nombre in ("firms_fuente", "firms_ventana"):
            self.assertEqual(nombres[nombre].enabled_when, {"firms": True}, nombre)
        self.assertEqual([o.value for o in nombres["firms_fuente"].options],
                         ["viirs", "modis", "snpp", "todos"])
        self.assertEqual([o.value for o in nombres["firms_ventana"].options],
                         list(firms.VENTANAS))

    def test_prendido_mete_el_paso_entre_la_descarga_y_el_render(self):
        plan = recipes.planear("snapshot_paraguay",
                               self._params(firms=True, firms_fuente="modis",
                                            firms_ventana="3h"),
                               Path("C:/tmp/work"))
        self.assertEqual([p.script for p in plan.pasos],
                         ["descargar/snapshot_paraguay.py", "descargar/firms.py",
                          "cuadros/snapshot_paraguay.py"])
        args = plan.pasos[1].args
        self.assertIn("--ultima", args)          # el default del producto
        self.assertEqual(args[args.index("--fuente") + 1], "modis")
        self.assertEqual(args[args.index("--ventana") + 1], "3h")
        render = plan.pasos[2].args
        self.assertIn("--firms", render)
        self.assertEqual(render[render.index("--firms-ventana") + 1], "3h")

    def test_apagado_no_cambia_la_receta_de_antes(self):
        plan = recipes.planear("snapshot_paraguay", self._params(), Path("C:/tmp/work"))
        self.assertEqual([p.script for p in plan.pasos],
                         ["descargar/snapshot_paraguay.py",
                          "cuadros/snapshot_paraguay.py"])
        self.assertNotIn("--firms", plan.pasos[1].args)

    def test_una_fuente_desconocida_cae_a_viirs(self):
        plan = recipes.planear("snapshot_paraguay",
                               self._params(firms=True, firms_fuente="landsat"),
                               Path("C:/tmp/work"))
        args = plan.pasos[1].args
        self.assertEqual(args[args.index("--fuente") + 1], "viirs")


if __name__ == "__main__":
    unittest.main()
