"""Pruebas de la API: contrato de lectura y errores delgados y legibles.

No crea jobs reales: toca los endpoints que no escriben ni lanzan scripts, y
los errores de pedido inválido. Asi la suite corre en segundos y sin red.

    app\\.venv\\Scripts\\python.exe -m unittest discover -s app\\tests
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

try:
    from fastapi.testclient import TestClient

    from app.api.main import app
except ImportError:  # pragma: no cover - faltan dependencias del venv de la app
    TestClient = None
    app = None


@unittest.skipIf(TestClient is None, "la API necesita las dependencias del venv de la app")
class ContratoDeLaApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cliente = TestClient(app)

    def test_health_dice_si_el_pipeline_esta_listo(self):
        cuerpo = self.cliente.get("/api/health").json()

        self.assertTrue(cuerpo["ok"])
        self.assertIn("repo_ready", cuerpo)
        self.assertIn("repo_python", cuerpo)
        self.assertIn("data_root", cuerpo)
        self.assertGreater(cuerpo["productos"], 0)

    def test_catalogo_trae_productos_y_rutas(self):
        respuesta = self.cliente.get("/api/catalog")

        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        self.assertGreater(len(cuerpo["products"]), 0)
        for clave in ("data_root", "media_root", "repo_python", "repo_ready"):
            self.assertIn(clave, cuerpo)
        self.assertTrue(all("id" in p and "params" in p for p in cuerpo["products"]))

    def test_fechas_de_un_producto_desconocido_es_404_con_motivo(self):
        respuesta = self.cliente.get("/api/catalog/no-existe/dates")

        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(respuesta.json()["detail"], "Producto desconocido")

    def test_pedir_un_producto_desconocido_es_400_con_motivo(self):
        respuesta = self.cliente.post(
            "/api/jobs", json={"product_id": "no-existe", "params": {}}
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("desconocido", respuesta.json()["detail"].lower())

    def test_un_job_desconocido_es_404(self):
        self.assertEqual(self.cliente.get("/api/jobs/no-existe").status_code, 404)
        self.assertEqual(
            self.cliente.post("/api/jobs/no-existe/cancel").status_code, 404
        )
        self.assertEqual(
            self.cliente.post("/api/jobs/no-existe/reveal").status_code, 404
        )
        self.assertEqual(
            self.cliente.get("/api/jobs/no-existe/events").status_code, 404
        )


if __name__ == "__main__":
    unittest.main()
