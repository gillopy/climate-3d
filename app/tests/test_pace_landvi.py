"""Tests for PACE LANDVI authentication discovery and auto cookie discovery."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests


RAIZ = Path(__file__).resolve().parents[2]
ESPEC = importlib.util.spec_from_file_location("pace_landvi", RAIZ / "descargar" / "pace_landvi.py")
assert ESPEC and ESPEC.loader
pace = importlib.util.module_from_spec(ESPEC)
sys.modules["pace_landvi"] = pace
ESPEC.loader.exec_module(pace)


class AutenticacionPACE(unittest.TestCase):
    """La sesión prefiere usuario/clave: sin navegador ni cookie manual."""

    def test_sesion_usa_credenciales_antes_que_cookies(self):
        with patch.object(pace, "_credenciales", return_value=("usuario", "clave")):
            sesion = pace._sesion(Path("cookies-que-no-existen.json"))

        self.assertIsInstance(sesion, pace.SesionEarthdata)
        self.assertEqual(sesion.auth, ("usuario", "clave"))

    def test_sesion_usa_cookies_del_archivo_si_no_hay_credenciales(self):
        with tempfile.TemporaryDirectory() as carpeta, patch.object(
            pace, "_credenciales", return_value=None
        ):
            cookies = Path(carpeta) / "cookies.json"
            cookies.write_text(
                '[{"name": "GETFILE_APP", "value": "abc", "domain": "oceandata.sci.gsfc.nasa.gov", "path": "/"}]',
                encoding="utf-8",
            )
            sesion = pace._sesion(cookies)

        self.assertEqual(sesion.cookies.get("GETFILE_APP"), "abc")

    def test_sesion_pide_credenciales_o_cookies_si_no_hay_nada(self):
        with patch.object(pace, "_credenciales", return_value=None):
            with self.assertRaises(SystemExit) as contexto:
                pace._sesion(None)

        mensaje = str(contexto.exception)
        self.assertIn("EARTHDATA_USER", mensaje)
        self.assertIn("Conectar Earthdata", mensaje)

    def test_el_auth_sobrevive_al_redirect_a_urs(self):
        # `requests` borra el header cuando el redirect cambia de host, y el login
        # de Earthdata depende de ese salto: OB.DAAC -> URS -> OB.DAAC.
        sesion = pace.SesionEarthdata("usuario", "clave")

        class Respuesta:
            class request:  # noqa: N801 - imita la forma que espera requests
                url = "https://oceandata.sci.gsfc.nasa.gov/getfile/x.nc"

        pedido = requests.Request(
            "GET", "https://urs.earthdata.nasa.gov/oauth/authorize"
        ).prepare()
        pedido.headers["Authorization"] = "Basic algo-viejo"
        sesion.rebuild_auth(pedido, Respuesta())

        self.assertTrue(pedido.headers["Authorization"].startswith("Basic "))

    def test_el_auth_no_se_manda_a_un_host_ajeno(self):
        sesion = pace.SesionEarthdata("usuario", "clave")

        class Respuesta:
            class request:  # noqa: N801 - imita la forma que espera requests
                url = "https://oceandata.sci.gsfc.nasa.gov/getfile/x.nc"

        pedido = requests.Request("GET", "https://ejemplo.com/ruta").prepare()
        pedido.headers["Authorization"] = "Basic algo-viejo"
        sesion.rebuild_auth(pedido, Respuesta())

        self.assertNotIn("Authorization", pedido.headers)

    def test_ruta_cookies_earthdata_es_independiente_del_repo(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = pace.ruta_cookies_earthdata({"LOCALAPPDATA": carpeta})

        self.assertEqual(ruta.name, "earthdata_cookies.json")


class DescargaTolerante(unittest.TestCase):
    """Un día no publicado (404) no puede cortar una ventana con datos válidos."""

    @staticmethod
    def _grano(salida, dia, res="0p1deg"):
        (salida / pace.nombre(dia, res)).write_bytes(b"x" * 6_000_000)

    def test_main_tolera_un_dia_faltante_si_queda_ventana_completa(self):
        import requests
        from datetime import date, timedelta

        with tempfile.TemporaryDirectory() as carpeta:
            salida = Path(carpeta)
            (salida / "cookies.json").write_text("[]", encoding="utf-8")
            dias = [date(2026, 11, 17) + timedelta(days=k) for k in range(7)]
            # Ventana completa terminando en el 22 (16..22); el 23 falla 404.
            self._grano(salida, date(2026, 11, 16))
            for dia in dias[:-1]:
                self._grano(salida, dia)

            def bajar_falso(sesion, url, destino, minimo):
                if "20261123" in url:
                    raise requests.HTTPError("404 Client Error: Not Found")
                destino.write_bytes(b"x" * 6_000_000)

            argv = [
                "pace_landvi.py", "--desde", "2026-11-17", "--hasta", "2026-11-23",
                "--res", "0p1deg", "--destino", str(salida),
                "--cookies", str(salida / "cookies.json"),
            ]
            with patch("sys.argv", argv), patch.object(pace, "_sesion", return_value=object()), \
                    patch.object(pace, "bajar", side_effect=bajar_falso):
                codigo = pace.main()

        self.assertEqual(codigo, 0)

    def test_main_no_falla_si_solo_hay_un_granulo(self):
        from datetime import date

        with tempfile.TemporaryDirectory() as carpeta:
            salida = Path(carpeta)
            (salida / "cookies.json").write_text("[]", encoding="utf-8")
            # Un solo día no da ventana, pero la descarga sí cumplió: el que decide
            # si se puede renderizar es `dias_moviles`, no este script.
            self._grano(salida, date(2026, 11, 22))
            argv = [
                "pace_landvi.py", "--desde", "2026-11-22", "--hasta", "2026-11-22",
                "--res", "0p1deg", "--destino", str(salida),
                "--cookies", str(salida / "cookies.json"),
            ]
            # `bajar` se parchea: el gránulo de este caso ya está en disco, pero si
            # el script decidiera bajarlo la prueba saldría a la red. La suite tiene
            # que correr sin red (S1).
            def bajar_falso(sesion, url, destino, minimo):
                destino.write_bytes(b"x" * 6_000_000)

            with patch("sys.argv", argv), patch.object(pace, "_sesion", return_value=object()),                     patch.object(pace, "bajar", side_effect=bajar_falso):
                codigo = pace.main()

        self.assertEqual(codigo, 0)

    def test_main_no_pide_autenticacion_si_ya_estan_los_granulos(self):
        from datetime import date

        with tempfile.TemporaryDirectory() as carpeta:
            salida = Path(carpeta)
            self._grano(salida, date(2026, 11, 22))
            argv = [
                "pace_landvi.py", "--desde", "2026-11-22", "--hasta", "2026-11-22",
                "--res", "0p1deg", "--destino", str(salida),
            ]
            with patch("sys.argv", argv), \
                    patch.object(
                        pace, "_sesion",
                        side_effect=AssertionError("no debe pedir autenticación"),
                    ):
                codigo = pace.main()

        self.assertEqual(codigo, 0)

    def test_main_falla_si_no_se_obtuvo_ningun_granulo(self):
        import requests
        from datetime import date

        with tempfile.TemporaryDirectory() as carpeta:
            salida = Path(carpeta)
            (salida / "cookies.json").write_text("[]", encoding="utf-8")
            argv = [
                "pace_landvi.py", "--desde", "2026-11-22", "--hasta", "2026-11-22",
                "--res", "0p1deg", "--destino", str(salida),
                "--cookies", str(salida / "cookies.json"),
            ]
            with patch("sys.argv", argv), patch.object(pace, "_sesion", return_value=object()), \
                    patch.object(pace, "bajar", side_effect=requests.HTTPError("404")):
                codigo = pace.main()

        self.assertEqual(codigo, 1)


if __name__ == "__main__":
    unittest.main()
