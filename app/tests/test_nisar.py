"""Contrato del visor NISAR (Fase 1), sin tocar la red.

ASF se mockea a proposito: estos tests fijan la forma de la respuesta, la
validacion de la caja y el proxy restringido. La busqueda real se comprueba a
mano contra la API publica.

    app\\.venv\\Scripts\\python.exe -m unittest app.tests.test_nisar -q
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

try:
    from fastapi.testclient import TestClient

    from app.api import nisar
    from app.api.catalog import get_product, productos_disponibles
    from app.api.main import app
    from app.api.recipes import planear
except ImportError:  # pragma: no cover - faltan dependencias del venv de la app
    TestClient = None
    nisar = None
    app = None

GRANULO = "NISAR_L2_PR_GCOV_034_082_D_101_2005_DHDH_A_20261029T214921_20261029T214955_P05036_N_F_J_001"
BASE_BROWSE = f"https://nisar.asf.earthdatacloud.nasa.gov/BROWSE/NISAR_L2_GCOV_V1/{GRANULO}/{GRANULO}"

FEATURE = {
    "type": "Feature",
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [
                [-55.5, -24.4],
                [-55.2, -24.4],
                [-55.2, -23.9],
                [-55.5, -23.9],
                [-55.5, -24.4],
            ]
        ],
    },
    "properties": {
        "fileID": GRANULO,
        "processingLevel": "GCOV",
        "startTime": "2026-10-29T21:49:21Z",
        "stopTime": "2026-10-29T21:49:55Z",
        "flightDirection": "DESCENDING",
        "pathNumber": 82,
        "frameNumber": 101,
        "mainBandPolarization": ["HH", "HV"],
        "collectionName": "NISAR_L2_GCOV_V1",
        "fileName": f"{GRANULO}.h5",
        "url": f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_GCOV_V1/{GRANULO}/{GRANULO}.h5",
        "bytes": {f"{GRANULO}.h5": {"bytes": 1_874_853_888, "format": "HDF5"}},
        "browse": [
            f"{BASE_BROWSE}_LATLON.png",
            f"{BASE_BROWSE}_LATLON_thumbnail.png",
            f"{BASE_BROWSE}_NATIVE_A_HHHH.png",
            f"{BASE_BROWSE}_NATIVE_A_HVHV.png",
        ],
    },
}

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


@unittest.skipIf(TestClient is None, "la API necesita las dependencias del venv de la app")
class VisorNisar(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cliente = TestClient(app)

    def test_catalogo_declara_niveles_y_caja_de_paraguay(self):
        respuesta = self.cliente.get("/api/nisar/catalog")

        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        valores = [nivel["value"] for nivel in cuerpo["levels"]]
        self.assertIn("GCOV", valores)
        self.assertEqual(len(cuerpo["default_bbox"]), 4)
        self.assertIn("earthdata_configured", cuerpo)

    def test_busqueda_devuelve_granulos_con_huella_y_browse_proxeado(self):
        with (
            patch.object(nisar, "_contar", return_value=55),
            patch.object(
                nisar,
                "_json_asf",
                return_value={"type": "FeatureCollection", "features": [FEATURE]},
            ),
        ):
            respuesta = self.cliente.get(
                "/api/nisar/search",
                params={"bbox": "-55.6,-24.5,-55.2,-23.9", "level": "GCOV"},
            )

        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo["total"], 55)
        self.assertEqual(cuerpo["returned"], 1)
        self.assertEqual(cuerpo["level"], "GCOV")
        self.assertTrue(cuerpo["notes"])

        granulo = cuerpo["granules"][0]
        self.assertEqual(granulo["id"], GRANULO)
        self.assertEqual(granulo["polarization"], ["HH", "HV"])
        self.assertEqual(granulo["size_mb"], 1874.9)
        self.assertEqual(len(granulo["footprint"]), 5)
        self.assertTrue(granulo["thumbnail"].startswith("/api/nisar/browse?url="))
        self.assertEqual(
            [imagen["label"] for imagen in granulo["images"]],
            ["Mapa (lat/lon)", "HH", "HV"],
        )
        self.assertTrue(granulo["asf_url"].startswith("https://search.asf.alaska.edu/"))

    def test_caja_invertida_es_400(self):
        respuesta = self.cliente.get(
            "/api/nisar/search", params={"bbox": "-54,-24,-56,-23"}
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("longitudes", respuesta.json()["detail"])

    def test_caja_demasiado_grande_es_400(self):
        respuesta = self.cliente.get(
            "/api/nisar/search", params={"bbox": "-70,-30,-45,-15"}
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("maximo", respuesta.json()["detail"])

    def test_nivel_y_polarizacion_desconocidos_son_400(self):
        caja = {"bbox": "-55.6,-24.5,-55.2,-23.9"}

        nivel = self.cliente.get("/api/nisar/search", params={**caja, "level": "XYZ"})
        self.assertEqual(nivel.status_code, 400)
        self.assertIn("nivel desconocido", nivel.json()["detail"])

        pol = self.cliente.get(
            "/api/nisar/search", params={**caja, "polarization": "QQ"}
        )
        self.assertEqual(pol.status_code, 400)
        self.assertIn("polarizacion desconocida", pol.json()["detail"])

    def test_proxy_solo_acepta_el_host_de_browse_de_asf(self):
        externo = self.cliente.get(
            "/api/nisar/browse",
            params={"url": "https://evil.example/BROWSE/a.png"},
        )
        self.assertEqual(externo.status_code, 400)
        self.assertIn("no permitido", externo.json()["detail"])

        ruta = self.cliente.get(
            "/api/nisar/browse",
            params={"url": f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{GRANULO}.h5"},
        )
        self.assertEqual(ruta.status_code, 400)

        http = self.cliente.get(
            "/api/nisar/browse",
            params={"url": f"{BASE_BROWSE}_LATLON.png".replace("https", "http")},
        )
        self.assertEqual(http.status_code, 400)
        self.assertIn("https", http.json()["detail"])

    def test_redirect_de_browse_acepta_solo_el_cdn_de_nisar(self):
        cdn = (
            "https://d1mv8zhcvry6x4.cloudfront.net/s3-abc/"
            "sds-n-cumulus-prod-nisar-browse.s3.us-west-2.amazonaws.com/x.png?Signature=1"
        )
        self.assertTrue(nisar._destino_final_permitido(cdn))
        self.assertTrue(
            nisar._destino_final_permitido(f"{BASE_BROWSE}_LATLON.png")
        )
        self.assertFalse(nisar._destino_final_permitido("https://evil.example/x.png"))
        self.assertFalse(
            nisar._destino_final_permitido(
                "http://d1mv8zhcvry6x4.cloudfront.net/nisar-browse/x.png"
            )
        )

    def test_proxy_sirve_y_cachea_el_png(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with (
                patch.object(nisar, "CACHE", Path(carpeta)),
                patch.object(nisar, "_descargar_png", return_value=PNG),
            ):
                respuesta = self.cliente.get(
                    "/api/nisar/browse",
                    params={"url": f"{BASE_BROWSE}_LATLON.png"},
                )
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.headers["content-type"], "image/png")
                self.assertEqual(respuesta.content, PNG)
                self.assertEqual(len(list(Path(carpeta).glob("*.png"))), 1)

    def test_producto_nisar_es_interno_y_arma_descarga_mas_render(self):
        ids = [producto.id for producto in productos_disponibles()]
        self.assertNotIn("nisar_render", ids)
        self.assertIsNotNone(get_product("nisar_render"))

        with tempfile.TemporaryDirectory() as carpeta:
            plan = planear(
                "nisar_render",
                {
                    "granulo": GRANULO,
                    "url": f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{GRANULO}.h5",
                    "coleccion": "NISAR_L2_GCOV_V1",
                    "bbox": "-55.6,-24.5,-55.2,-23.9",
                    "pol": "auto",
                    "modo": "color",
                    "px": 2400,
                },
                Path(carpeta),
            )

        self.assertEqual(
            [paso.script for paso in plan.pasos],
            ["descargar/nisar.py", "prototipos/poster_nisar.py"],
        )
        self.assertEqual(plan.pasos[0].kind, "download")
        self.assertEqual(plan.pasos[1].kind, "render")
        self.assertIn("--bbox", plan.pasos[1].args)
        self.assertTrue(plan.pasos[1].args[-1].endswith("paraguay_gadm.json"))
        self.assertIn("nisar", plan.pasos[0].args[-3])

    def test_receta_nisar_rechaza_una_caja_invertida(self):
        with self.assertRaises(ValueError):
            planear(
                "nisar_render",
                {
                    "granulo": GRANULO,
                    "url": f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{GRANULO}.h5",
                    "coleccion": "NISAR_L2_GCOV_V1",
                    "bbox": "-55.2,-23.9,-55.6,-24.5",
                    "pol": "auto",
                    "modo": "gris",
                    "px": 2400,
                },
                Path("."),
            )

    def test_paraguay_sale_del_geojson_del_repo(self):
        respuesta = self.cliente.get("/api/nisar/paraguay")

        self.assertEqual(respuesta.status_code, 200)
        cuerpo = json.loads(respuesta.content)
        self.assertEqual(cuerpo["type"], "FeatureCollection")
        self.assertGreaterEqual(len(cuerpo["features"]), 1)


if __name__ == "__main__":
    unittest.main()
