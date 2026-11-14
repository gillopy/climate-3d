"""Contrato del visor NISAR (Fase 1), sin tocar la red.

ASF se mockea a proposito: estos tests fijan la forma de la respuesta, la
validacion de la caja y el proxy restringido. La busqueda real se comprueba a
mano contra la API publica.

    app\\.venv\\Scripts\\python.exe -m unittest app.tests.test_nisar -q
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[2]
for candidato in (RAIZ, RAIZ / "comun"):
    if str(candidato) not in sys.path:
        sys.path.insert(0, str(candidato))

try:
    from fastapi.testclient import TestClient

    from app.api import nisar
    from app.api.catalog import get_product, productos_disponibles
    from app.api.main import app
    from app.api.recipes import planear
    import rutas
except ImportError:  # pragma: no cover - faltan dependencias del venv de la app
    TestClient = None
    nisar = None
    app = None
    rutas = None

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

    def test_receta_rvi_descarga_y_calcula_el_indice(self):
        with tempfile.TemporaryDirectory() as carpeta:
            plan = planear(
                "nisar_render",
                {
                    "producto": "rvi",
                    "granulo": GRANULO,
                    "url": f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{GRANULO}.h5",
                    "coleccion": "NISAR_L2_GCOV_V1",
                    "bbox": "-55.6,-24.5,-55.2,-23.9",
                    "px": 2400,
                },
                Path(carpeta),
            )

        self.assertEqual(
            [paso.script for paso in plan.pasos],
            ["descargar/nisar.py", "prototipos/nisar_rvi.py"],
        )
        self.assertEqual(plan.pasos[1].kind, "render")

    def test_receta_serie_usa_la_carpeta_de_la_coleccion(self):
        with tempfile.TemporaryDirectory() as carpeta:
            plan = planear(
                "nisar_render",
                {
                    "producto": "serie",
                    "granulo": GRANULO,
                    "url": (
                        "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/"
                        f"NISAR_L2_GCOV_V1/{GRANULO}/{GRANULO}.h5"
                    ),
                    "coleccion": "NISAR_L2_GCOV_V1",
                    "bbox": "-55.6,-24.5,-55.2,-23.9",
                    "px": 1200,
                    "track": 82,
                    "frame": 101,
                    "umbral": 3,
                    "hv_min": -15.5,
                    "fechas": "A,B",
                },
                Path(carpeta),
            )

        self.assertEqual(
            [paso.script for paso in plan.pasos],
            ["descargar/nisar.py", "prototipos/nisar_serie.py"],
        )
        self.assertIn("--coleccion-dir", plan.pasos[1].args)
        self.assertIn("--track", plan.pasos[1].args)
        self.assertIn("82", plan.pasos[1].args)
        self.assertIn("--fechas", plan.pasos[1].args)

    def test_receta_geotiff(self):
        with tempfile.TemporaryDirectory() as carpeta:
            plan = planear(
                "nisar_render",
                {
                    "producto": "geotiff",
                    "granulo": GRANULO,
                    "url": (
                        "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/"
                        f"NISAR_L2_GCOV_V1/{GRANULO}/{GRANULO}.h5"
                    ),
                    "coleccion": "NISAR_L2_GCOV_V1",
                    "bbox": "-55.6,-24.5,-55.2,-23.9",
                    "px": 1200,
                    "pol": "hv",
                    "modo_geo": "db",
                },
                Path(carpeta),
            )

        self.assertEqual(
            [paso.script for paso in plan.pasos],
            ["descargar/nisar.py", "prototipos/nisar_geotiff.py"],
        )
        self.assertIn("--modo", plan.pasos[1].args)

    def test_receta_fusion_optica(self):
        with tempfile.TemporaryDirectory() as carpeta:
            plan = planear(
                "nisar_render",
                {
                    "producto": "fusion",
                    "granulo": GRANULO,
                    "url": (
                        "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/"
                        f"NISAR_L2_GCOV_V1/{GRANULO}/{GRANULO}.h5"
                    ),
                    "coleccion": "NISAR_L2_GCOV_V1",
                    "bbox": "-55.6,-24.5,-55.2,-23.9",
                    "px": 1200,
                    "dias": 15,
                    "nubes": 40,
                },
                Path(carpeta),
            )

        self.assertEqual(
            [paso.script for paso in plan.pasos],
            ["descargar/nisar.py", "prototipos/nisar_fusion.py"],
        )
        self.assertIn("--dias", plan.pasos[1].args)
        self.assertIn("--nubes", plan.pasos[1].args)

    def test_receta_rechaza_nivel_no_gcov(self):
        with self.assertRaises(ValueError) as contexto:
            planear(
                "nisar_render",
                {
                    "producto": "agua",
                    "nivel": "SME2",
                    "granulo": "NISAR_L3_PR_SME2_033_132_A_165_2005_DHDH_A_20261021T094010_20261021T094045_P05023_N_F_J_001",
                    "url": (
                        "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/"
                        "NISAR_L3_SME2_PROVISIONAL_V1/GRAN/GRAN.h5"
                    ),
                    "coleccion": "NISAR_L3_SME2_PROVISIONAL_V1",
                    "bbox": "-55.6,-24.5,-55.2,-23.9",
                    "px": 1200,
                },
                Path("."),
            )

        self.assertIn("GCOV", str(contexto.exception))
        self.assertIn("SME2", str(contexto.exception))

    def test_receta_agua(self):
        with tempfile.TemporaryDirectory() as carpeta:
            plan = planear(
                "nisar_render",
                {
                    "producto": "agua",
                    "granulo": GRANULO,
                    "url": (
                        "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/"
                        f"NISAR_L2_GCOV_V1/{GRANULO}/{GRANULO}.h5"
                    ),
                    "coleccion": "NISAR_L2_GCOV_V1",
                    "bbox": "-55.6,-24.5,-55.2,-23.9",
                    "px": 1400,
                    "hh_max": -20,
                    "hv_max": -25,
                },
                Path(carpeta),
            )

        self.assertEqual(
            [paso.script for paso in plan.pasos],
            ["descargar/nisar.py", "prototipos/nisar_agua.py"],
        )
        self.assertIn("--hh-max", plan.pasos[1].args)

    def test_receta_incendio_con_dos_fechas_y_firms(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with patch.object(rutas, "raiz_nisar", return_value=Path(carpeta)):
                plan = planear(
                    "nisar_render",
                    {
                        "producto": "incendio",
                        "granulo": GRANULO,
                        "url": (
                            "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/"
                            f"NISAR_L2_GCOV_V1/{GRANULO}/{GRANULO}.h5"
                        ),
                        "coleccion": "NISAR_L2_GCOV_V1",
                        "antes_granulo": "ANTES",
                        "antes_url": (
                            "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/"
                            "NISAR_L2_GCOV_V1/ANTES/ANTES.h5"
                        ),
                        "antes_coleccion": "NISAR_L2_GCOV_V1",
                        "bbox": "-55.6,-24.5,-55.2,-23.9",
                        "px": 1400,
                        "umbral": 3,
                        "hv_min": -15.5,
                        "firms": True,
                    },
                    Path(carpeta),
                )

        self.assertEqual(
            [paso.script for paso in plan.pasos],
            ["descargar/nisar.py", "descargar/nisar.py", "prototipos/nisar_incendio.py"],
        )
        self.assertIn("--firms", plan.pasos[2].args)

    def test_receta_cambio_descarga_dos_fechas_y_compara(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with patch.object(rutas, "raiz_nisar", return_value=Path(carpeta)):
                plan = planear(
                    "nisar_render",
                    {
                        "producto": "cambio",
                        "granulo": GRANULO,
                        "url": f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{GRANULO}.h5",
                        "coleccion": "NISAR_L2_GCOV_V1",
                        "antes_granulo": "NISAR_L2_PR_GCOV_033_082_D_101_2005_DHDH_A_20261017T214920_20261017T214955_P05023_N_F_J_001",
                        "antes_url": "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_GCOV_V1/ANTES/ANTES.h5",
                        "antes_coleccion": "NISAR_L2_GCOV_V1",
                        "bbox": "-55.6,-24.5,-55.2,-23.9",
                        "px": 2400,
                        "modo_cambio": "mascara",
                        "umbral": 3,
                        "hv_min": -15.5,
                    },
                    Path(carpeta),
                )

        self.assertEqual(
            [paso.script for paso in plan.pasos],
            ["descargar/nisar.py", "descargar/nisar.py", "prototipos/nisar_cambio.py"],
        )
        self.assertIn("--antes", plan.pasos[2].args)
        self.assertIn("--despues", plan.pasos[2].args)

    def test_receta_deriva_la_coleccion_provisional_de_la_url(self):
        url = (
            "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/"
            "NISAR_L2_GCOV_PROVISIONAL_V1/GRAN/GRAN.h5"
        )
        with tempfile.TemporaryDirectory() as carpeta:
            plan = planear(
                "nisar_render",
                {
                    "producto": "rvi",
                    "granulo": "GRAN",
                    "url": url,
                    "coleccion": "",
                    "bbox": "-55.6,-24.5,-55.2,-23.9",
                    "px": 1200,
                },
                Path(carpeta),
            )

        self.assertEqual(plan.pasos[0].args[-1], "NISAR_L2_GCOV_PROVISIONAL_V1")

    def test_receta_cambio_confirma_con_sentinel_y_descarta_parches_chicos(self):
        base = {
            "producto": "cambio",
            "granulo": GRANULO,
            "url": f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{GRANULO}.h5",
            "coleccion": "NISAR_L2_GCOV_V1",
            "antes_granulo": "NISAR_L2_PR_GCOV_033_082_D_101_2005_DHDH_A_20261017T214920_20261017T214955_P05023_N_F_J_001",
            "antes_url": "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_GCOV_V1/ANTES/ANTES.h5",
            "antes_coleccion": "NISAR_L2_GCOV_V1",
            "bbox": "-55.6,-24.5,-55.2,-23.9",
            "px": 1600,
            "modo_cambio": "comparar",
            "umbral": 3,
            "hv_min": -15.5,
        }
        with tempfile.TemporaryDirectory() as carpeta:
            with patch.object(rutas, "raiz_nisar", return_value=Path(carpeta)):
                con = planear("nisar_render", {**base, "verificar_s2": True}, Path(carpeta))
                sin = planear("nisar_render", base, Path(carpeta))

        args_con = con.pasos[-1].args
        self.assertIn("--verificar-s2", args_con)
        self.assertEqual(args_con[args_con.index("--modo") + 1], "comparar")
        self.assertIn("--mmu-ha", args_con)
        self.assertEqual(args_con[args_con.index("--mmu-ha") + 1], "0.5")

        args_sin = sin.pasos[-1].args
        self.assertNotIn("--verificar-s2", args_sin)
        # La MMU es del producto radar, no de la confirmacion optica: sin NDVI
        # tambien se descartan los bloques menores a 0,5 ha.
        self.assertIn("--mmu-ha", args_sin)
        self.assertEqual(args_sin[args_sin.index("--mmu-ha") + 1], "0.5")
        self.assertEqual(args_sin[args_sin.index("--umbral") + 1], "3")

    def test_receta_cambio_rechaza_la_misma_fecha(self):
        with self.assertRaises(ValueError):
            planear(
                "nisar_render",
                {
                    "producto": "cambio",
                    "granulo": GRANULO,
                    "url": f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{GRANULO}.h5",
                    "coleccion": "NISAR_L2_GCOV_V1",
                    "antes_granulo": GRANULO,
                    "antes_url": "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_GCOV_V1/ANTES/ANTES.h5",
                    "antes_coleccion": "NISAR_L2_GCOV_V1",
                    "bbox": "-55.6,-24.5,-55.2,-23.9",
                    "px": 2400,
                },
                Path("."),
            )

    def test_granulo_deriva_la_coleccion_desde_la_url(self):
        copia = copy.deepcopy(FEATURE)
        copia["properties"]["collectionName"] = ""
        copia["properties"]["url"] = (
            "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/"
            "NISAR_L2_GCOV_PROVISIONAL_V1/GRAN/GRAN.h5"
        )

        granulo = nisar._granulo(copia)

        self.assertEqual(granulo.collection, "NISAR_L2_GCOV_PROVISIONAL_V1")

    def test_receta_cambio_permite_mezclar_colecciones_con_aviso_en_el_json(self):
        # El archivo real publica las fechas viejas solo como PROVISIONAL: bloquear
        # la mezcla dejaria la comparacion sin segundas fechas.
        with tempfile.TemporaryDirectory() as carpeta:
            with patch.object(rutas, "raiz_nisar", return_value=Path(carpeta)):
                plan = planear(
                    "nisar_render",
                    {
                        "producto": "cambio",
                        "granulo": GRANULO,
                        "url": (
                            "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/"
                            f"NISAR_L2_GCOV_V1/{GRANULO}/{GRANULO}.h5"
                        ),
                        "coleccion": "NISAR_L2_GCOV_V1",
                        "antes_granulo": "ANTES",
                        "antes_url": (
                            "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/"
                            "NISAR_L2_GCOV_PROVISIONAL_V1/ANTES/ANTES.h5"
                        ),
                        "antes_coleccion": "NISAR_L2_GCOV_PROVISIONAL_V1",
                        "bbox": "-55.6,-24.5,-55.2,-23.9",
                        "px": 1200,
                    },
                    Path(carpeta),
                )

        self.assertEqual(
            [paso.script for paso in plan.pasos],
            ["descargar/nisar.py", "descargar/nisar.py", "prototipos/nisar_cambio.py"],
        )
        self.assertEqual(
            plan.pasos[1].args[plan.pasos[1].args.index("--coleccion") + 1],
            "NISAR_L2_GCOV_PROVISIONAL_V1",
        )

    def test_locales_lista_solo_track_frame_y_coleccion(self):
        with tempfile.TemporaryDirectory() as carpeta:
            base = Path(carpeta) / "COL"
            base.mkdir(parents=True)
            nombres = [
                "NISAR_L2_PR_GCOV_032_082_D_101_2005_DHDH_A_"
                "20261005T214920_20261005T214955_P05023_N_F_J_001.h5",
                "NISAR_L2_PR_GCOV_033_082_D_101_2005_DHDH_A_"
                "20261017T214920_20261017T214955_P05023_N_F_J_001.h5",
                "NISAR_L2_PR_GCOV_033_082_D_100_2005_DHDH_A_"
                "20261017T214847_20261017T214921_P05023_N_F_J_001.h5",
            ]
            for nombre in nombres:
                (base / nombre).write_bytes(b"x")
            with patch.object(nisar, "_raiz_nisar", return_value=Path(carpeta)):
                respuesta = self.cliente.get(
                    "/api/nisar/local",
                    params={"track": 82, "frame": 101, "coleccion": "COL"},
                )

        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo["total"], 2)
        self.assertEqual(
            [escena["date"][:10] for escena in cuerpo["scenes"]],
            ["2026-10-05", "2026-10-17"],
        )

    # --- fechas del track/frame y descarga bajo demanda -------------------
    def _feature(self, sufijo: str, coleccion: str = "NISAR_L2_GCOV_V1") -> dict:
        """FEATURE con otra fecha/coleccion, para armar un track con historia."""
        copia = copy.deepcopy(FEATURE)
        granulo = (
            "NISAR_L2_PR_GCOV_033_082_D_101_2005_DHDH_A_"
            f"{sufijo}T214920_{sufijo}T214955_P05023_N_F_J_001"
        )
        props = copia["properties"]
        props["fileID"] = granulo
        props["sceneName"] = granulo
        props["startTime"] = f"{sufijo[:4]}-{sufijo[4:6]}-{sufijo[6:]}T21:49:20Z"
        props["stopTime"] = f"{sufijo[:4]}-{sufijo[4:6]}-{sufijo[6:]}T21:49:55Z"
        props["collectionName"] = coleccion
        props["fileName"] = f"{granulo}.h5"
        props["url"] = (
            "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/"
            f"{coleccion}/{granulo}/{granulo}.h5"
        )
        props["bytes"] = {f"{granulo}.h5": {"bytes": 1_874_853_888, "format": "HDF5"}}
        props["browse"] = []
        return copia

    def test_el_catalogo_declara_la_raiz_de_nisar(self):
        with patch.object(nisar, "_raiz_nisar", return_value=Path(r"E:\nisar")):
            cuerpo = self.cliente.get("/api/nisar/catalog").json()

        self.assertEqual(cuerpo["nisar_root"], r"E:\nisar")
        self.assertIn("data_root", cuerpo)

    def test_la_busqueda_marca_los_granulos_que_ya_estan_en_disco(self):
        with tempfile.TemporaryDirectory() as carpeta:
            base = Path(carpeta) / "NISAR_L2_GCOV_V1"
            base.mkdir(parents=True)
            (base / f"{GRANULO}.h5").write_bytes(b"x")
            with (
                patch.object(nisar, "_raiz_nisar", return_value=Path(carpeta)),
                patch.object(nisar, "_contar", return_value=1),
                patch.object(
                    nisar,
                    "_json_asf",
                    return_value={"type": "FeatureCollection", "features": [FEATURE]},
                ),
            ):
                cuerpo = self.cliente.get(
                    "/api/nisar/search",
                    params={"bbox": "-55.6,-24.5,-55.2,-23.9", "level": "GCOV"},
                ).json()

        self.assertTrue(cuerpo["granules"][0]["local"])

    def test_timeline_mezcla_asf_con_lo_que_esta_en_disco(self):
        local_solo = (
            "NISAR_L2_PR_GCOV_032_082_D_101_2005_DHDH_A_"
            "20261005T214920_20261005T214955_P05023_N_F_J_001"
        )
        with tempfile.TemporaryDirectory() as carpeta:
            base = Path(carpeta) / "NISAR_L2_GCOV_V1"
            base.mkdir(parents=True)
            (base / f"{GRANULO}.h5").write_bytes(b"x" * 20)
            (base / f"{local_solo}.h5").write_bytes(b"x" * 20)
            with (
                patch.object(nisar, "_raiz_nisar", return_value=Path(carpeta)),
                patch.object(
                    nisar,
                    "_json_asf",
                    return_value={
                        "type": "FeatureCollection",
                        "features": [FEATURE, self._feature("20261001", "OTRA")],
                    },
                ),
            ):
                respuesta = self.cliente.get(
                    "/api/nisar/timeline",
                    params={
                        "track": 82,
                        "frame": 101,
                        "coleccion": "NISAR_L2_GCOV_V1",
                    },
                )

        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo["total"], 2)
        self.assertEqual(
            [escena["date"] for escena in cuerpo["scenes"]],
            ["2026-10-05", "2026-10-29"],
        )
        self.assertTrue(all(escena["local"] for escena in cuerpo["scenes"]))
        # La fecha que ASF lista trae URL; la que solo esta en disco, no.
        self.assertEqual(cuerpo["scenes"][1]["download"], FEATURE["properties"]["url"])
        self.assertEqual(cuerpo["scenes"][0]["download"], "")

    def test_escena_por_fecha_usa_el_disco_sin_consultar_asf(self):
        local = (
            "NISAR_L2_PR_GCOV_033_082_D_101_2005_DHDH_A_"
            "20261017T214920_20261017T214955_P05023_N_F_J_001"
        )
        with tempfile.TemporaryDirectory() as carpeta:
            base = Path(carpeta) / "NISAR_L2_GCOV_V1"
            base.mkdir(parents=True)
            (base / f"{local}.h5").write_bytes(b"x" * 20)
            with (
                patch.object(nisar, "_raiz_nisar", return_value=Path(carpeta)),
                patch.object(
                    nisar, "_json_asf", side_effect=AssertionError("no debe consultar ASF")
                ),
            ):
                respuesta = self.cliente.get(
                    "/api/nisar/scene",
                    params={"track": 82, "frame": 101, "date": "2026-10-17"},
                )

        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo["id"], local)
        self.assertTrue(cuerpo["local"])
        self.assertEqual(cuerpo["collection"], "NISAR_L2_GCOV_V1")
        self.assertEqual(cuerpo["start"], "2026-10-17T21:49:20Z")

    def test_escena_por_fecha_sin_datos_es_404(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with (
                patch.object(nisar, "_raiz_nisar", return_value=Path(carpeta)),
                patch.object(
                    nisar,
                    "_json_asf",
                    return_value={"type": "FeatureCollection", "features": []},
                ),
            ):
                respuesta = self.cliente.get(
                    "/api/nisar/scene",
                    params={"track": 82, "frame": 101, "date": "2026-09-20"},
                )

        self.assertEqual(respuesta.status_code, 404)
        self.assertIn("No hay escena NISAR GCOV para track 82 frame 101", respuesta.json()["detail"])

    def test_receta_cambio_usa_la_anterior_local_sin_url(self):
        anterior = (
            "NISAR_L2_PR_GCOV_033_082_D_101_2005_DHDH_A_"
            "20261017T214920_20261017T214955_P05023_N_F_J_001"
        )
        with tempfile.TemporaryDirectory() as carpeta:
            base = Path(carpeta) / "NISAR_L2_GCOV_V1"
            base.mkdir(parents=True)
            (base / f"{anterior}.h5").write_bytes(b"x")
            with patch.object(rutas, "raiz_nisar", return_value=Path(carpeta)):
                plan = planear(
                    "nisar_render",
                    {
                        "producto": "cambio",
                        "granulo": GRANULO,
                        "url": f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{GRANULO}.h5",
                        "coleccion": "NISAR_L2_GCOV_V1",
                        "antes_granulo": anterior,
                        "antes_coleccion": "NISAR_L2_GCOV_V1",
                        "bbox": "-55.6,-24.5,-55.2,-23.9",
                        "px": 1200,
                    },
                    Path(carpeta),
                )

        self.assertEqual(
            [paso.script for paso in plan.pasos],
            ["descargar/nisar.py", "prototipos/nisar_cambio.py"],
        )

    def test_receta_cambio_exige_url_si_la_anterior_no_esta_en_disco(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with patch.object(rutas, "raiz_nisar", return_value=Path(carpeta)):
                with self.assertRaises(ValueError) as contexto:
                    planear(
                        "nisar_render",
                        {
                            "producto": "cambio",
                            "granulo": GRANULO,
                            "url": f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{GRANULO}.h5",
                            "coleccion": "NISAR_L2_GCOV_V1",
                            "antes_granulo": "NISAR_L2_PR_GCOV_033_082_D_101_2005_DHDH_A_20261017T214920_20261017T214955_P05023_N_F_J_001",
                            "antes_coleccion": "NISAR_L2_GCOV_V1",
                            "bbox": "-55.6,-24.5,-55.2,-23.9",
                            "px": 1200,
                        },
                        Path(carpeta),
                    )

        self.assertIn("no esta en disco", str(contexto.exception))

    def test_receta_serie_baja_las_fechas_que_faltan(self):
        faltan = [
            {
                "id": "NISAR_L2_PR_GCOV_032_082_D_101_2005_DHDH_A_20261005T214920_20261005T214955_P05023_N_F_J_001",
                "url": "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_GCOV_V1/A/A.h5",
                "coleccion": "NISAR_L2_GCOV_V1",
            },
            {
                "id": "NISAR_L2_PR_GCOV_033_082_D_101_2005_DHDH_A_20261017T214920_20261017T214955_P05023_N_F_J_001",
                "url": "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_GCOV_V1/B/B.h5",
                "coleccion": "NISAR_L2_GCOV_V1",
            },
        ]
        with tempfile.TemporaryDirectory() as carpeta:
            with patch.object(rutas, "raiz_nisar", return_value=Path(carpeta)):
                plan = planear(
                    "nisar_render",
                    {
                        "producto": "serie",
                        "granulo": GRANULO,
                        "url": f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{GRANULO}.h5",
                        "coleccion": "NISAR_L2_GCOV_V1",
                        "bbox": "-55.6,-24.5,-55.2,-23.9",
                        "px": 1200,
                        "track": 82,
                        "frame": 101,
                        "escenas": json.dumps(faltan),
                    },
                    Path(carpeta),
                )

        self.assertEqual(
            [paso.script for paso in plan.pasos],
            [
                "descargar/nisar.py",
                "descargar/nisar.py",
                "descargar/nisar.py",
                "prototipos/nisar_serie.py",
            ],
        )
        indice = plan.pasos[-1].args.index("--fechas")
        fechas = plan.pasos[-1].args[indice + 1].split(",")
        self.assertEqual(fechas, [escena["id"] for escena in faltan])

    def test_receta_serie_no_baja_lo_que_ya_esta_en_disco(self):
        ya_esta = {
            "id": "NISAR_L2_PR_GCOV_032_082_D_101_2005_DHDH_A_20261005T214920_20261005T214955_P05023_N_F_J_001",
            "url": "",
            "coleccion": "NISAR_L2_GCOV_V1",
        }
        with tempfile.TemporaryDirectory() as carpeta:
            base = Path(carpeta) / "NISAR_L2_GCOV_V1"
            base.mkdir(parents=True)
            (base / f"{ya_esta['id']}.h5").write_bytes(b"x")
            with patch.object(rutas, "raiz_nisar", return_value=Path(carpeta)):
                plan = planear(
                    "nisar_render",
                    {
                        "producto": "serie",
                        "granulo": GRANULO,
                        "url": f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{GRANULO}.h5",
                        "coleccion": "NISAR_L2_GCOV_V1",
                        "bbox": "-55.6,-24.5,-55.2,-23.9",
                        "px": 1200,
                        "track": 82,
                        "frame": 101,
                        "escenas": json.dumps([ya_esta]),
                    },
                    Path(carpeta),
                )

        self.assertEqual(
            [paso.script for paso in plan.pasos],
            ["descargar/nisar.py", "prototipos/nisar_serie.py"],
        )

    def test_receta_serie_acepta_fechas_de_otra_coleccion(self):
        extra = {
            "id": "NISAR_L2_PR_GCOV_032_082_D_101_2005_DHDH_A_20261005T214920_20261005T214955_P05023_N_F_J_001",
            "url": "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_GCOV_V1/X/X.h5",
            "coleccion": "NISAR_L2_GCOV_PROVISIONAL_V1",
        }
        with tempfile.TemporaryDirectory() as carpeta:
            with patch.object(rutas, "raiz_nisar", return_value=Path(carpeta)):
                plan = planear(
                    "nisar_render",
                    {
                        "producto": "serie",
                        "granulo": GRANULO,
                        "url": f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{GRANULO}.h5",
                        "coleccion": "NISAR_L2_GCOV_V1",
                        "bbox": "-55.6,-24.5,-55.2,-23.9",
                        "px": 1200,
                        "track": 82,
                        "frame": 101,
                        "escenas": json.dumps([extra]),
                    },
                    Path(carpeta),
                )

        args = plan.pasos[-1].args
        carpetas = [args[i + 1] for i, valor in enumerate(args) if valor == "--coleccion-dir"]
        self.assertEqual(len(carpetas), 2)
        self.assertTrue(carpetas[1].endswith("NISAR_L2_GCOV_PROVISIONAL_V1"))
        # La descarga extra va a su propia carpeta de coleccion.
        self.assertEqual(
            plan.pasos[1].args[plan.pasos[1].args.index("--coleccion") + 1],
            "NISAR_L2_GCOV_PROVISIONAL_V1",
        )

    def test_receta_descarga_solo_baja_el_h5(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with patch.object(rutas, "raiz_nisar", return_value=Path(carpeta)):
                plan = planear(
                    "nisar_render",
                    {
                        "producto": "descarga",
                        "nivel": "GSLC",
                        "granulo": GRANULO,
                        "url": f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{GRANULO}.h5",
                        "coleccion": "NISAR_L2_GCOV_V1",
                    },
                    Path(carpeta),
                )

        self.assertEqual([paso.script for paso in plan.pasos], ["descargar/nisar.py"])
        self.assertEqual(plan.pasos[0].kind, "download")
        self.assertIn("--sello", plan.pasos[0].args)
        self.assertIn("--destino", plan.pasos[0].args)
        self.assertEqual(plan.pasos[0].args[plan.pasos[0].args.index("--destino") + 1], str(carpeta))

    def test_la_busqueda_reporta_la_coleccion_del_archivo_en_disco(self):
        # El id del granulo no incluye la coleccion: si el .h5 esta en otra
        # carpeta hay que analizar ESA copia, no la que lista ASF.
        with tempfile.TemporaryDirectory() as carpeta:
            base = Path(carpeta) / "NISAR_L2_GCOV_PROVISIONAL_V1"
            base.mkdir(parents=True)
            (base / f"{GRANULO}.h5").write_bytes(b"x")
            with (
                patch.object(nisar, "_raiz_nisar", return_value=Path(carpeta)),
                patch.object(nisar, "_contar", return_value=1),
                patch.object(
                    nisar,
                    "_json_asf",
                    return_value={"type": "FeatureCollection", "features": [FEATURE]},
                ),
            ):
                cuerpo = self.cliente.get(
                    "/api/nisar/search",
                    params={"bbox": "-55.6,-24.5,-55.2,-23.9", "level": "GCOV"},
                ).json()

        granulo = cuerpo["granules"][0]
        self.assertTrue(granulo["local"])
        self.assertEqual(granulo["collection"], "NISAR_L2_GCOV_PROVISIONAL_V1")

    def test_timeline_omite_la_coleccion_beta_si_no_esta_en_disco(self):
        beta = self._feature("20261001", "NISAR_L2_GCOV_BETA_V1")
        with tempfile.TemporaryDirectory() as carpeta:
            with (
                patch.object(nisar, "_raiz_nisar", return_value=Path(carpeta)),
                patch.object(
                    nisar,
                    "_json_asf",
                    return_value={
                        "type": "FeatureCollection",
                        "features": [FEATURE, beta],
                    },
                ),
            ):
                cuerpo = self.cliente.get(
                    "/api/nisar/timeline",
                    params={"track": 82, "frame": 101},
                ).json()

        self.assertEqual([escena["date"] for escena in cuerpo["scenes"]], ["2026-10-29"])

    def test_escena_por_fecha_omite_beta(self):
        beta = self._feature("20261001", "NISAR_L2_GCOV_BETA_V1")
        with tempfile.TemporaryDirectory() as carpeta:
            with (
                patch.object(nisar, "_raiz_nisar", return_value=Path(carpeta)),
                patch.object(
                    nisar,
                    "_json_asf",
                    return_value={"type": "FeatureCollection", "features": [beta]},
                ),
            ):
                respuesta = self.cliente.get(
                    "/api/nisar/scene",
                    params={"track": 82, "frame": 101, "date": "2026-10-01"},
                )

        self.assertEqual(respuesta.status_code, 404)

    def test_el_nombre_del_granulo_dice_el_tamano_del_pixel(self):
        # No depende del track: el mismo track alterna modos de 10 y 20 m.
        self.assertEqual(
            nisar._mpp_de_granulo(
                "NISAR_L2_PR_GCOV_034_031_A_165_4005_DHDH_A_20261026T093148_20261026T093229_P05036_N_F_J_001"
            ),
            10.0,
        )
        self.assertEqual(
            nisar._mpp_de_granulo(
                "NISAR_L2_PR_GCOV_034_082_D_101_2005_DHDH_A_20261029T214921_20261029T214955_P05036_N_F_J_001"
            ),
            20.0,
        )
        self.assertIsNone(nisar._mpp_de_granulo("NISAR_L2_PR_GCOV_SIN_MODO"))
        self.assertEqual(nisar._granulo(FEATURE).mpp, 20.0)

    def test_paraguay_sale_del_geojson_del_repo(self):
        respuesta = self.cliente.get("/api/nisar/paraguay")

        self.assertEqual(respuesta.status_code, 200)
        cuerpo = json.loads(respuesta.content)
        self.assertEqual(cuerpo["type"], "FeatureCollection")
        self.assertGreaterEqual(len(cuerpo["features"]), 1)


if __name__ == "__main__":
    unittest.main()
