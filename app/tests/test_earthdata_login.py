"""Sesión de Earthdata sin navegador automatizado.

La cookie `GETFILE_APP` se pega a mano y se verifica contra OB.DAAC antes de
guardarla. Un corte de red no es una sesión vencida, y un GET de estado nunca
borra el archivo.

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


class GuardarCookiePegada(unittest.TestCase):
    """POST /api/earthdata/cookies: verificar antes de escribir, siempre."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.ruta = Path(self._tmp.name) / "earthdata_cookies.json"
        self.addCleanup(self._tmp.cleanup)
        parche = mock.patch.object(earthdata, "ruta_cookies_earthdata", return_value=self.ruta)
        parche.start()
        self.addCleanup(parche.stop)

    def _guardar(self, estado: bool | None, **cuerpo: object) -> earthdata.LoginResponse:
        with mock.patch.object(earthdata, "_estado_sesion", return_value=estado):
            return earthdata.guardar_cookies(earthdata.CookiesRequest(**cuerpo))

    def test_una_cookie_pegada_y_valida_se_guarda(self) -> None:
        respuesta = self._guardar(True, cookie="valor-de-la-cookie")

        self.assertTrue(respuesta.ok)
        guardadas = json.loads(self.ruta.read_text(encoding="utf-8"))
        self.assertEqual(guardadas[0]["name"], earthdata.COOKIE_SESION)
        self.assertEqual(guardadas[0]["value"], "valor-de-la-cookie")

    def test_acepta_el_formato_nombre_igual_valor(self) -> None:
        self._guardar(True, cookie="GETFILE_APP=valor-limpio")

        guardadas = json.loads(self.ruta.read_text(encoding="utf-8"))
        self.assertEqual(guardadas[0]["value"], "valor-limpio")

    def test_acepta_la_lista_de_un_json_exportado(self) -> None:
        respuesta = self._guardar(True, cookies=COOKIES)

        self.assertEqual(respuesta.cookies_count, 1)
        self.assertTrue(self.ruta.is_file())

    def test_una_lista_sin_dominio_de_earthdata_se_rechaza(self) -> None:
        ajenas = [{"name": "otra", "value": "x", "domain": "ejemplo.com", "path": "/"}]

        with self.assertRaises(earthdata.HTTPException) as ctx:
            self._guardar(True, cookies=ajenas)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertFalse(self.ruta.exists())

    def test_una_cookie_que_no_autentica_no_se_guarda(self) -> None:
        with self.assertRaises(earthdata.HTTPException) as ctx:
            self._guardar(False, cookie="vencida")

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertFalse(self.ruta.exists())

    def test_sin_red_no_se_guarda_y_se_avisa(self) -> None:
        with self.assertRaises(earthdata.HTTPException) as ctx:
            self._guardar(None, cookie="cualquiera")

        self.assertEqual(ctx.exception.status_code, 503)
        self.assertFalse(self.ruta.exists())

    def test_sin_cookie_ni_lista_es_pedido_invalido(self) -> None:
        with self.assertRaises(earthdata.HTTPException) as ctx:
            self._guardar(True)

        self.assertEqual(ctx.exception.status_code, 400)

    def test_funciona_igual_dentro_del_contenedor(self) -> None:
        # Ya no hay navegador que abrir: el flujo manual sirve en Docker.
        with mock.patch.dict(earthdata.os.environ, {"CLIMATE3D_CONTENEDOR": "1"}):
            respuesta = self._guardar(True, cookie="valor-en-docker")

        self.assertTrue(respuesta.ok)
        self.assertTrue(self.ruta.is_file())


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

    def test_sesion_vencida_no_borra_el_archivo(self):
        # Un GET no destruye credenciales: informa `stale` y el operador decide.
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = self._archivo(carpeta)
            with mock.patch.object(earthdata, "ruta_cookies_earthdata", return_value=ruta), \
                 mock.patch.object(earthdata, "_estado_sesion", return_value=False):
                estado = earthdata.cookies_status()

            self.assertTrue(ruta.is_file(), "el GET de estado no puede borrar la sesión")
            self.assertTrue(estado["configured"])
            self.assertFalse(estado["verified"])
            self.assertTrue(estado["stale"])

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
