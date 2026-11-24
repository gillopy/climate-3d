"""Contrato de las capas ambientales del visor NISAR, sin tocar la red.

Los servicios de WDPA, LandMark y RESOLVE se mockean: estos tests fijan la
normalizacion, el recorte por zoom, la union de fuentes, el dedupe de biosfera,
la paginacion y la cache. La consulta real se comprueba a mano.

    .venv\\Scripts\\python.exe -m unittest app.tests.test_capas -q
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

try:
    from fastapi.testclient import TestClient

    from app.api import capas
    from app.api.main import app
except ImportError:  # pragma: no cover - faltan dependencias del venv de la app
    TestClient = None
    capas = None
    app = None

CAJA = "-62.7,-27.7,-54.2,-19.2"


def feature(props: dict, x: float = 0.0) -> dict:
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [x, -25.0],
                    [x + 0.1, -25.0],
                    [x + 0.1, -24.9],
                    [x, -24.9],
                    [x, -25.0],
                ]
            ],
        },
        "properties": props,
    }


WDPA = {
    "name_eng": "Parque Nacional Defensores del Chaco",
    "name": "Parque Nacional Defensores del Chaco",
    "desig_eng": "National Park",
    "desig": "Parque Nacional",
    "desig_type": "National",
    "iucn_cat": "II",
    "status_yr": 1975,
    "gis_area": 7800.5,
    "iso3": "PRY",
    "site_id": 1234,
}


@unittest.skipIf(TestClient is None, "la API necesita las dependencias del venv de la app")
class CapasAmbientales(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cliente = TestClient(app)

    def setUp(self) -> None:
        capas.limpiar_cache()

    def _pedir(self, capa: str, zoom: int = 6, caja: str = CAJA):
        return self.cliente.get(f"/api/capas/{capa}?bbox={caja}&zoom={zoom}")

    def test_catalogo_lista_las_seis_capas_en_orden(self):
        cuerpo = self.cliente.get("/api/capas").json()

        ids = [c["id"] for c in cuerpo["capas"]]
        self.assertEqual(
            ids,
            [
                "areas-protegidas",
                "ramsar",
                "biosfera",
                "territorios-indigenas",
                "ecorregiones",
                "otras-conservacion",
            ],
        )
        for capa in cuerpo["capas"]:
            for clave in ("nombre", "descripcion", "fuente", "fuente_url", "color", "min_zoom"):
                self.assertIn(clave, capa)
            self.assertRegex(capa["color"], r"^#[0-9a-f]{6}$")
        fuentes = " ".join(cuerpo["fuentes"])
        self.assertIn("WDPA", fuentes)
        self.assertIn("LandMark", fuentes)
        self.assertIn("RESOLVE", fuentes)

    def test_capa_desconocida_es_404_con_opciones(self):
        respuesta = self._pedir("no-existe")

        self.assertEqual(respuesta.status_code, 404)
        detalle = respuesta.json()["detail"]
        self.assertIn("Capa desconocida", detalle)
        self.assertIn("areas-protegidas", detalle)

    def test_bbox_invalida_es_400_con_motivo(self):
        casos = {
            "1,2,3": "4 numeros",
            "a,b,c,d": "oeste,sur,este,norte",
            "-50,-30,-60,-20": "longitudes",
            "-50,-20,-40,-30": "latitudes",
        }
        for caja, esperado in casos.items():
            with self.subTest(caja=caja):
                respuesta = self._pedir("areas-protegidas", caja=caja)
                self.assertEqual(respuesta.status_code, 400)
                self.assertIn(esperado, respuesta.json()["detail"])

    def test_zoom_insuficiente_no_consulta_la_fuente(self):
        with patch.object(capas, "_pedir") as pedir:
            respuesta = self._pedir("areas-protegidas", zoom=4)

        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        self.assertTrue(cuerpo["requiere_zoom"])
        self.assertEqual(cuerpo["total"], 0)
        self.assertEqual(cuerpo["min_zoom"], 5)
        self.assertEqual(cuerpo["features"], [])
        pedir.assert_not_called()

    def test_areas_protegidas_normaliza_y_pide_la_caja_visible(self):
        with patch.object(
            capas,
            "_pedir",
            return_value={"features": [feature(WDPA)], "exceededTransferLimit": False},
        ) as pedir:
            respuesta = self._pedir("areas-protegidas", zoom=7)

        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo["type"], "FeatureCollection")
        self.assertEqual(cuerpo["capa"], "areas-protegidas")
        self.assertEqual(cuerpo["total"], 1)
        self.assertFalse(cuerpo["excedido"])
        self.assertEqual(cuerpo["bbox"], [-62.7, -27.7, -54.2, -19.2])
        props = cuerpo["features"][0]["properties"]
        self.assertEqual(props["nombre"], "Parque Nacional Defensores del Chaco")
        self.assertEqual(props["categoria"], "National Park")
        self.assertEqual(props["iucn"], "II")
        self.assertEqual(props["anio"], 1975)
        self.assertEqual(props["area_ha"], 780050)
        self.assertEqual(props["pais"], "PRY")
        self.assertEqual(props["sitio"], 1234)

        pedido = pedir.call_args.args[1]
        self.assertIn("desig_type='National'", pedido["where"])
        self.assertIn("Biosphere", pedido["where"])
        self.assertIn("Ramsar", pedido["where"])
        self.assertEqual(pedido["outSR"], "4326")
        self.assertEqual(pedido["f"], "geojson")
        self.assertEqual(pedido["resultRecordCount"], "2000")
        self.assertEqual(pedido["geometryType"], "esriGeometryEnvelope")
        self.assertEqual(pedido["inSR"], "4326")
        envoltura = json.loads(pedido["geometry"])
        self.assertEqual(envoltura["xmin"], -62.7)
        self.assertEqual(envoltura["ymax"], -19.2)

    def test_ramsar_y_otras_usan_su_designacion(self):
        with patch.object(
            capas,
            "_pedir",
            return_value={"features": [feature(WDPA)]},
        ) as pedir:
            self._pedir("ramsar")
            self.assertEqual(pedir.call_count, 1)
            self.assertIn("Ramsar", pedir.call_args.args[1]["where"])

        capas.limpiar_cache()
        with patch.object(
            capas,
            "_pedir",
            return_value={"features": [feature(WDPA)]},
        ) as pedir:
            self._pedir("otras-conservacion")
            self.assertEqual(pedir.call_count, 1)
            where = pedir.call_args.args[1]["where"]
            self.assertIn("Privada", where)
            self.assertIn("Otras Categor", where)
            self.assertIn("Binacional", where)

    def test_biosfera_dedupe_prefiere_el_registro_unesco(self):
        nacional = feature({**WDPA, "desig_type": "National", "desig_eng": "Biosphere Reserve-National"}, x=0.0)
        unesco = feature(
            {**WDPA, "desig_type": "International", "desig_eng": "UNESCO-MAB Biosphere Reserve"},
            x=1.0,
        )
        with patch.object(
            capas,
            "_pedir",
            return_value={"features": [nacional, unesco]},
        ):
            cuerpo = self._pedir("biosfera", zoom=6).json()

        self.assertEqual(cuerpo["total"], 1)
        self.assertEqual(cuerpo["features"][0]["properties"]["tipo"], "International")
        self.assertEqual(cuerpo["features"][0]["geometry"]["coordinates"][0][0][0], 1.0)

    def test_territorios_indigenas_une_las_fuentes_de_landmark(self):
        def falso(url: str, params: dict, timeout: float = 45.0) -> dict:
            if "comm_ind_Documented" in url:
                return {
                    "features": [
                        feature(
                            {
                                "Name": "Tierra Comunitaria de Origen",
                                "Category": "TCO",
                                "Doc_Status": "Documented",
                                "Country": "Bolivia",
                                "ISO_Code": "BOL",
                                "Area_GIS": 7176.2,
                            }
                        )
                    ]
                }
            if "comm_ind_NotDocumented" in url:
                return {
                    "features": [
                        feature(
                            {
                                "Name": "Terra Indígena",
                                "Category": "Terra Indígena",
                                "Doc_Status": "Not documented",
                                "Country": "Brazil",
                                "ISO_Code": "BRA",
                                "Area_GIS": 500.0,
                            }
                        )
                    ]
                }
            return {"features": []}

        with patch.object(capas, "_pedir", side_effect=falso) as pedir:
            cuerpo = self._pedir("territorios-indigenas", zoom=6).json()

        self.assertEqual(pedir.call_count, 4)
        self.assertEqual(cuerpo["total"], 2)
        origenes = {f["properties"]["origen"] for f in cuerpo["features"]}
        self.assertEqual(origenes, {"Documentado", "No documentado"})
        primera = cuerpo["features"][0]["properties"]
        self.assertEqual(primera["area_ha"], 7176)
        self.assertEqual(primera["situacion"], "Documented")

    def test_fuente_parcial_avisa_pero_devuelve_lo_que_hay(self):
        def falso(url: str, params: dict, timeout: float = 45.0) -> dict:
            if "comm_ind_Documented" in url:
                return {"features": [feature({"Name": "X", "Category": "Tierra Indígena"})]}
            raise capas.ErrorFuente("TimeoutError: se corto")

        with patch.object(capas, "_pedir", side_effect=falso):
            respuesta = self._pedir("territorios-indigenas")

        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo["total"], 1)
        self.assertTrue(cuerpo["avisos"])
        self.assertIn("Fuente parcial", cuerpo["avisos"][0])

    def test_si_todas_las_fuentes_fallan_es_502(self):
        with patch.object(capas, "_pedir", side_effect=capas.ErrorFuente("sin red")):
            respuesta = self._pedir("areas-protegidas")

        self.assertEqual(respuesta.status_code, 502)
        self.assertIn("no respondió", respuesta.json()["detail"])

    def test_paginacion_de_landmark_pide_el_siguiente_bloque(self):
        consulta = capas.Consulta(
            "https://ejemplo/query", "1=1", "Name", pagina=2, paginar=True
        )
        lote1 = {"features": [feature({}), feature({})]}
        lote2 = {"features": [feature({})]}
        with patch.object(capas, "_pedir", side_effect=[lote1, lote2]) as pedir:
            crudas, excedido = capas._pedir_consulta(
                consulta, (-62.7, -27.7, -54.2, -19.2), 6, capas.CAPAS[0]
            )

        self.assertEqual(len(crudas), 3)
        self.assertFalse(excedido)
        offsets = [llamada.args[1]["resultOffset"] for llamada in pedir.call_args_list]
        self.assertEqual(offsets, ["0", "2"])

    def test_exceeded_transfer_limit_marca_la_capa(self):
        with patch.object(
            capas,
            "_pedir",
            return_value={"features": [feature(WDPA)], "exceededTransferLimit": True},
        ):
            cuerpo = self._pedir("areas-protegidas").json()

        self.assertTrue(cuerpo["excedido"])

    def test_la_cache_evita_repetir_la_consulta(self):
        with patch.object(
            capas,
            "_pedir",
            return_value={"features": [feature(WDPA)]},
        ) as pedir:
            primero = self._pedir("areas-protegidas").json()
            segundo = self._pedir("areas-protegidas").json()

        self.assertEqual(pedir.call_count, 1)
        self.assertEqual(primero, segundo)

    def test_ecorregiones_usa_el_color_del_dataset_y_lo_valida(self):
        valido = feature({"ECO_NAME": "Dry Chaco", "BIOME_NAME": "Chaco", "COLOR": "#D4D20E"})
        invalido = feature({"ECO_NAME": "Cerrado", "BIOME_NAME": "Cerrado", "COLOR": "rojo"})
        with patch.object(
            capas,
            "_pedir",
            return_value={"features": [valido, invalido]},
        ):
            cuerpo = self._pedir("ecorregiones", zoom=6).json()

        self.assertEqual(cuerpo["total"], 2)
        self.assertEqual(cuerpo["features"][0]["properties"]["color"], "#d4d20e")
        self.assertEqual(cuerpo["features"][1]["properties"]["color"], "#94a3b8")


@unittest.skipIf(TestClient is None, "la API necesita las dependencias del venv de la app")
class DetallesDelPedido(unittest.TestCase):
    def test_la_simplificacion_se_afina_con_el_zoom(self):
        areas = capas.POR_ID["areas-protegidas"]

        self.assertEqual(capas._offset(5, areas), 0.02)
        self.assertEqual(capas._offset(8, areas), 0.005)
        self.assertLess(capas._offset(13, areas), capas._offset(9, areas))

    def test_la_precision_es_mas_fina_a_partir_del_zoom_7(self):
        eco = capas.POR_ID["ecorregiones"]

        self.assertEqual(capas._precision(eco, 6), 3)
        self.assertEqual(capas._precision(eco, 7), 4)


if __name__ == "__main__":
    unittest.main()
