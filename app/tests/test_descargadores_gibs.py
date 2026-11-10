"""Pruebas de los descargadores de GIBS (snapshot y GeoColor).

Necesitan `requests`, `numpy` y `Pillow`, que viven en el venv del repo y no en
el de la app: si faltan, las pruebas se saltean.

    .venv\\Scripts\\python.exe -m unittest app.tests.test_descargadores_gibs
"""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

try:
    from comun import dia_reciente  # noqa: E402
    from descargar import geocolor, snapshot_paraguay  # noqa: E402
except ImportError:  # pragma: no cover - falta requests/numpy en este venv
    dia_reciente = None
    geocolor = None
    snapshot_paraguay = None


def _respuesta(status: int, cuerpo: bytes = b"") -> "object":
    """Una `requests.Response` falsa, sin salir a la red."""
    r = snapshot_paraguay.requests.Response()
    r.status_code = status
    r.url = "https://wvs.earthdata.nasa.gov/api/v1/snapshot"
    r._content = cuerpo
    return r


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

    def test_un_corte_de_red_aborta_la_sonda_sin_recorrer_dias(self):
        caja = (-63.0, -28.0, -53.0, -19.0)
        with mock.patch.object(
            snapshot_paraguay, "_pedir",
            side_effect=snapshot_paraguay.requests.ConnectTimeout("sin respuesta"),
        ) as pedir:
            with self.assertRaises(SystemExit) as ctx:
                snapshot_paraguay.ultima_disponible(
                    "truecolor", caja, 320,
                    desde=datetime(2026, 11, 1, 15), verbose=False,
                )

        self.assertIn("GIBS", str(ctx.exception))
        self.assertEqual(pedir.call_count, 1)


class SondaContraUnServicioCaido(unittest.TestCase):
    """Un 503 de GIBS no es 'falta de gránulo': no se retrocede ni se miente."""

    CAJA = (-63.0, -28.0, -53.0, -19.0)
    DESDE = datetime(2026, 11, 1, 15)

    def test_un_503_transitorio_se_reintenta_y_devuelve_el_techo(self):
        respuestas = [_respuesta(503), _respuesta(200, b"png" * 2000)]
        with mock.patch.object(
                 snapshot_paraguay.requests, "get", side_effect=respuestas
             ) as get, \
             mock.patch.object(snapshot_paraguay.time, "sleep"), \
             mock.patch.object(snapshot_paraguay, "valida", return_value=True):
            t = snapshot_paraguay.ultima_disponible(
                "truecolor", self.CAJA, 320, desde=self.DESDE, verbose=False)

        self.assertEqual(t, datetime(2026, 11, 1, 0))
        self.assertEqual(get.call_count, 2)

    def test_un_503_persistente_aborta_sin_retroceder_el_dia(self):
        salida = io.StringIO()
        with mock.patch.object(
                 snapshot_paraguay.requests, "get",
                 side_effect=lambda *a, **k: _respuesta(503)
             ), \
             mock.patch.object(snapshot_paraguay.time, "sleep"), \
             mock.patch("sys.stdout", salida):
            with self.assertRaises(SystemExit) as ctx:
                snapshot_paraguay.ultima_disponible(
                    "truecolor", self.CAJA, 320, desde=self.DESDE)

        self.assertIn("GIBS", str(ctx.exception))
        self.assertNotIn("sin gránulo", salida.getvalue())
        self.assertNotIn("pruebo", salida.getvalue())


@unittest.skipIf(dia_reciente is None, "el sondeo necesita requests del venv del repo")
class UltimoDiaContraUnServicioCaido(unittest.TestCase):
    """El sondeo de los compuestos diarios distingue la caída de la falta de dato."""

    LAYER = "MODIS_Terra_CorrectedReflectance_TrueColor"
    CAJA = (-63.0, -28.0, -53.0, -19.0)
    DESDE = datetime(2026, 11, 1, 15)

    def test_un_503_transitorio_no_retrocede_el_dia(self):
        respuestas = [_respuesta(503), _respuesta(200, b"png" * 2000)]
        with mock.patch.object(
                 dia_reciente.requests, "get", side_effect=respuestas
             ) as get, \
             mock.patch.object(dia_reciente.time, "sleep"), \
             mock.patch.object(dia_reciente, "_sirve", return_value=True):
            dia = dia_reciente.ultimo_dia(
                self.LAYER, self.CAJA, desde=self.DESDE, verbose=False)

        self.assertEqual(dia, date(2026, 11, 1))
        self.assertEqual(get.call_count, 2)

    def test_un_503_persistente_aborta_sin_recorrer_los_diez_dias(self):
        with mock.patch.object(
                 dia_reciente.requests, "get",
                 side_effect=lambda *a, **k: _respuesta(503)
             ) as get, \
             mock.patch.object(dia_reciente.time, "sleep"):
            with self.assertRaises(SystemExit) as ctx:
                dia_reciente.ultimo_dia(
                    self.LAYER, self.CAJA, desde=self.DESDE, verbose=False)

        self.assertIn("GIBS", str(ctx.exception))
        self.assertEqual(get.call_count, dia_reciente.FALLOS_DE_RED)


