"""Pruebas de los descargadores de GIBS (snapshot y GeoColor).

Necesitan `requests`, `numpy` y `Pillow`, que viven en el venv del repo y no en
el de la app: si faltan, las pruebas se saltean.

    .venv\\Scripts\\python.exe -m unittest app.tests.test_descargadores_gibs
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

try:
    from descargar import geocolor, snapshot_paraguay  # noqa: E402
except ImportError:  # pragma: no cover - falta requests/numpy en este venv
    geocolor = None
    snapshot_paraguay = None


@unittest.skipIf(geocolor is None, "los descargadores necesitan requests del venv del repo")
class FuentesDelSnapshot(unittest.TestCase):
    """GIBS: cada satélite con su capa, y qué pasa cuando el servicio no responde."""

    def test_geocolor_west_usa_la_capa_west(self):
        self.assertEqual(geocolor.CAPAS["G18"], "GOES-West_ABI_GeoColor")
        self.assertEqual(geocolor.CAPAS["G19"], "GOES-East_ABI_GeoColor")
        self.assertEqual(geocolor.CAPAS["G16"], "GOES-East_ABI_GeoColor")

    def test_si_gibs_no_responde_usa_la_ultima_captura(self):
        caja = (-63.0, -28.0, -53.0, -19.0)
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            respaldo = carpeta / "ultima_truecolor_320px.png"
            respaldo.write_bytes(b"png" * 2000)
            destino = carpeta / "crudo.png"
            with mock.patch.object(snapshot_paraguay, "RESPALDO", carpeta), \
                 mock.patch.object(
                     snapshot_paraguay.requests, "get",
                     side_effect=snapshot_paraguay.requests.ConnectTimeout("sin respuesta"),
                 ):
                ruta = snapshot_paraguay.descargar(
                    datetime(2026, 11, 1, 15), caja, 320, destino, "truecolor", reintentos=1
                )
            self.assertTrue(ruta.is_file())
            self.assertEqual(ruta.read_bytes(), respaldo.read_bytes())

    def test_la_sonda_corta_a_los_tres_fallos_de_red(self):
        caja = (-63.0, -28.0, -53.0, -19.0)
        with mock.patch.object(
            snapshot_paraguay, "_pedir",
            side_effect=snapshot_paraguay.requests.ConnectTimeout("sin respuesta"),
        ) as pedir:
            with self.assertRaises(SystemExit):
                snapshot_paraguay.ultima_disponible(
                    "truecolor", caja, 320,
                    desde=datetime(2026, 11, 1, 15), verbose=False,
                )

        self.assertEqual(pedir.call_count, snapshot_paraguay.FALLOS_DE_RED)


