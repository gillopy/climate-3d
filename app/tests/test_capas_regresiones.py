"""Regresiones del proxy de capas ambientales detectadas en verificación.

Fijan los dos bloqueos: una caja mundial con zoom alto no puede pedir detalle
máximo (tolerancia acoplada al tamaño de la caja) y la caché no puede crecer ni
retener errores. No tocan la red.

    .venv\\Scripts\\python.exe -m unittest app.tests.test_capas_regresiones -q
"""
from __future__ import annotations

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


@unittest.skipIf(TestClient is None, "la API necesita las dependencias del venv de la app")
class RegresionesCapas(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cliente = TestClient(app)

    def setUp(self) -> None:
        capas.limpiar_cache()

    def test_bbox_rechaza_nan_inf_y_fuera_de_rango(self):
        casos = ("nan,nan,nan,nan", "inf,-1,inf,1", "1e400,0,2,1", "0,0,0,1")
        for caja in casos:
            with self.subTest(caja=caja):
                respuesta = self.cliente.get(
                    f"/api/capas/areas-protegidas?bbox={caja}&zoom=6"
                )
                self.assertEqual(respuesta.status_code, 400)

    def test_la_simplificacion_acompana_al_tamano_de_la_caja(self):
        capturado: dict[str, str] = {}

        def falso(url: str, params: dict, timeout: float = 45.0) -> dict:
            capturado.update(params)
            return {"features": []}

        with patch.object(capas, "_pedir", side_effect=falso):
            respuesta = self.cliente.get(
                "/api/capas/areas-protegidas?bbox=-180,-90,180,90&zoom=22"
            )

        self.assertEqual(respuesta.status_code, 200)
        self.assertGreaterEqual(float(capturado["maxAllowableOffset"]), 0.05)

    def test_la_cache_expira_a_las_seis_horas(self):
        reloj = {"t": 1000.0}
        with patch.object(capas.time, "monotonic", lambda: reloj["t"]):
            with patch.object(capas, "_pedir", return_value={"features": []}) as pedir:
                for _ in range(2):
                    self.cliente.get("/api/capas/ramsar?bbox=0,0,1,1&zoom=6")
                self.assertEqual(pedir.call_count, 1)
                reloj["t"] = 1000.0 + capas.CACHE_TTL + 1
                self.cliente.get("/api/capas/ramsar?bbox=0,0,1,1&zoom=6")
                self.assertEqual(pedir.call_count, 2)

    def test_la_cache_no_supera_el_maximo(self):
        with patch.object(capas, "_pedir", return_value={"features": []}):
            for i in range(capas.CACHE_MAX + 10):
                self.cliente.get(f"/api/capas/ramsar?bbox=0,0,{1 + i / 100},1&zoom=6")

        self.assertLessEqual(len(capas._CACHE), capas.CACHE_MAX)

    def test_un_502_no_queda_cacheado(self):
        with patch.object(
            capas, "_pedir", side_effect=capas.ErrorFuente("sin red")
        ) as pedir:
            for _ in range(2):
                respuesta = self.cliente.get(
                    "/api/capas/ramsar?bbox=0,0,1,1&zoom=6"
                )
                self.assertEqual(respuesta.status_code, 502)

        self.assertEqual(pedir.call_count, 2)
        self.assertEqual(len(capas._CACHE), 0)


if __name__ == "__main__":
    unittest.main()
