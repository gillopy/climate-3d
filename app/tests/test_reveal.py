"""`/reveal` en contenedor: no hay escritorio, así que se avisa en vez de fallar.

    app\\.venv\\Scripts\\python.exe -m unittest discover -s app\\tests
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

try:
    from fastapi.testclient import TestClient

    from app.api import main
except ImportError:  # pragma: no cover - faltan dependencias del venv de la app
    TestClient = None
    main = None


@unittest.skipIf(TestClient is None, "la API necesita las dependencias del venv de la app")
class RevealEnContenedor(unittest.TestCase):
    def setUp(self) -> None:
        self.cliente = TestClient(main.app)
        self.carpeta = tempfile.TemporaryDirectory()
        self._obtener = main.gestor.obtener
        main.gestor.obtener = lambda job_id: SimpleNamespace(  # type: ignore[assignment]
            work=Path(self.carpeta.name)
        )

    def tearDown(self) -> None:
        main.gestor.obtener = self._obtener  # type: ignore[assignment]
        self.carpeta.cleanup()

    def test_en_contenedor_no_intenta_abrir_el_escritorio(self) -> None:
        with mock.patch.dict(os.environ, {"CLIMATE3D_CONTENEDOR": "1"}):
            respuesta = self.cliente.post("/api/jobs/cualquiera/reveal")

        self.assertEqual(respuesta.status_code, 409)
        self.assertIn("contenedor", respuesta.json()["detail"].lower())

    def test_un_job_desconocido_sigue_siendo_404(self) -> None:
        main.gestor.obtener = lambda job_id: None  # type: ignore[assignment]

        respuesta = self.cliente.post("/api/jobs/no-existe/reveal")

        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(respuesta.json()["detail"], "Job desconocido")


if __name__ == "__main__":
    unittest.main()
