"""Sesión de Earthdata: un corte de red no es una sesión vencida.

La prueba contra OB.DAAC distingue tres estados: válida, vencida y "no se pudo
comprobar". Sólo la vencida descarta el archivo de cookies.

    .venv\\Scripts\\python.exe -m unittest app.tests.test_earthdata_login
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from app.api import earthdata  # noqa: E402

COOKIES = [{
    "name": "GETFILE_APP",
    "value": "sesion-de-prueba",
    "domain": earthdata.HOST_OBDAAC,
    "path": "/",
}]


class _Respuesta:
    """Lo mínimo de `requests.Response` que mira `_estado_sesion`."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.headers: dict[str, str] = {}

    def close(self) -> None:
        pass


class EstadoDeSesion(unittest.TestCase):
    def test_host_oceandata_es_sesion_valida(self):
        with mock.patch.object(
            earthdata, "_pedir_prueba",
            return_value=_Respuesta(f"https://{earthdata.HOST_OBDAAC}/getfile/x.nc"),
        ):
            self.assertIs(earthdata._estado_sesion(COOKIES), True)

    def test_un_404_de_oceandata_sigue_siendo_sesion_valida(self):
        # El gránulo de prueba puede desaparecer: lo que importa es el host final.
        with mock.patch.object(
            earthdata, "_pedir_prueba",
            return_value=_Respuesta(f"https://{earthdata.HOST_OBDAAC}/getfile/falta.nc"),
        ):
            self.assertIs(earthdata._estado_sesion(COOKIES), True)

    def test_redirect_a_urs_es_sesion_vencida(self):
        with mock.patch.object(
            earthdata, "_pedir_prueba",
            return_value=_Respuesta(
                "https://urs.earthdata.nasa.gov//oauth/authorize?client_id=x"
            ),
        ):
            self.assertIs(earthdata._estado_sesion(COOKIES), False)

    def test_error_de_red_no_es_veredicto(self):
        with mock.patch.object(
            earthdata, "_pedir_prueba",
            side_effect=earthdata.requests.ConnectTimeout("sin red"),
        ):
            self.assertIsNone(earthdata._estado_sesion(COOKIES))


class LoginEnContenedor(unittest.TestCase):
    def test_en_docker_avisa_sin_intentar_abrir_navegador(self):
        with mock.patch.dict(earthdata.os.environ, {"CLIMATE3D_CONTENEDOR": "1"}):
            with self.assertRaises(earthdata.HTTPException) as ctx:
                earthdata.login_earthdata_interactive()

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("Docker", ctx.exception.detail)


class CookiesStatus(unittest.TestCase):
    def _archivo(self, carpeta: str) -> Path:
        ruta = Path(carpeta) / "earthdata_cookies.json"
        ruta.write_text(json.dumps(COOKIES), encoding="utf-8")
        return ruta

    def test_un_corte_de_red_conserva_las_cookies(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = self._archivo(carpeta)
            with mock.patch.object(earthdata, "ruta_cookies_earthdata", return_value=ruta), \
                 mock.patch.object(earthdata, "_estado_sesion", return_value=None):
                estado = earthdata.cookies_status()

            self.assertTrue(ruta.is_file())
            self.assertTrue(estado["configured"])
            self.assertFalse(estado["verified"])

    def test_sesion_vencida_descarta_el_archivo(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = self._archivo(carpeta)
            with mock.patch.object(earthdata, "ruta_cookies_earthdata", return_value=ruta), \
                 mock.patch.object(earthdata, "_estado_sesion", return_value=False):
                estado = earthdata.cookies_status()

            self.assertFalse(ruta.exists())
            self.assertFalse(estado["configured"])
            self.assertTrue(estado["verified"])

    def test_sesion_valida_conserva_el_archivo(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = self._archivo(carpeta)
            with mock.patch.object(earthdata, "ruta_cookies_earthdata", return_value=ruta), \
                 mock.patch.object(earthdata, "_estado_sesion", return_value=True):
                estado = earthdata.cookies_status()

            self.assertTrue(ruta.is_file())
            self.assertTrue(estado["configured"])
            self.assertTrue(estado["verified"])
            self.assertEqual(estado["cookies_count"], len(COOKIES))


if __name__ == "__main__":
    unittest.main()
