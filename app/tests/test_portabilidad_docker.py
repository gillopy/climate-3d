"""Regresiones de la portabilidad a Docker: lo que no puede romperse en silencio.

Los artefactos del contenedor no se pueden ejecutar en esta máquina (no hay Docker),
así que estas pruebas fijan las invariantes que sí se pueden leer del repo: finales de
línea, orden de copia del Dockerfile, puerto en loopback y el intérprete aislado.

    .venv\\Scripts\\python.exe -m unittest discover -s app\\tests
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
# Todo lo de Docker y los lanzadores vive en despliegue/, no en la raíz del repo.
DESPLIEGUE = RAIZ / "despliegue"
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from app.api import main  # noqa: E402
from app.api.recipes import _python_repo  # noqa: E402

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover - faltan dependencias del venv de la app
    TestClient = None


def _sin_comentarios(texto: str) -> str:
    """Líneas reales de un .bat: los `rem` no ejecutan nada.

    Sin esto una aserción sobre el texto matchea la explicación en vez del
    comando (ya pasó tres veces: `pause`, `compose down` y `findstr`).
    """
    return "\n".join(
        linea.strip()
        for linea in texto.splitlines()
        if linea.strip() and not linea.strip().lower().startswith("rem")
    )


class ArtefactosDelContenedor(unittest.TestCase):
    def test_los_scripts_de_linux_van_con_lf(self) -> None:
        # Un CRLF en el shebang rompe el arranque: "bad interpreter".
        for relativo in ("despliegue/entrypoint.sh", "despliegue/setup.sh"):
            datos = (RAIZ / relativo).read_bytes()
            self.assertNotIn(b"\r\n", datos, f"{relativo} tiene CRLF")
            self.assertTrue(datos.startswith(b"#!"), f"{relativo} no tiene shebang")

    def test_el_dist_se_copia_despues_de_la_app(self) -> None:
        # Al revés, `COPY app/` pisaría el build del frontend con el dist local.
        lineas = (DESPLIEGUE / "Dockerfile").read_text(encoding="utf-8").splitlines()
        app = next(i for i, l in enumerate(lineas) if l.startswith("COPY app/ "))
        dist = next(i for i, l in enumerate(lineas) if l.startswith("COPY --from=web"))
        self.assertLess(app, dist)

    def test_el_runtime_escribe_los_artefactos_en_el_volumen(self) -> None:
        # S1: la raíz de artefactos no vive dentro de la imagen; el entrypoint la crea
        # en /data/.media, que es el volumen montado desde el host.
        texto = (DESPLIEGUE / "Dockerfile").read_text(encoding="utf-8")
        for esperado in ("CLIMATE3D_MEDIA=/data/.media", "USER appuser"):
            self.assertIn(esperado, texto)
        entrypoint = (DESPLIEGUE / "entrypoint.sh").read_text(encoding="utf-8")
        self.assertIn('mkdir -p "$MEDIA"', entrypoint)
        self.assertNotIn("/app/app/var/media", entrypoint)

    def test_cdsapi_se_instala_con_version_fija(self) -> None:
        # S1 (auditoría): `uv sync --frozen` fija todo el entorno, y esta línea era
        # la única excepción: un `uv pip install cdsapi` a secas resolvía versión y
        # dependencias desde el índice en cada build, sin hash ni entrada en el lock.
        texto = (DESPLIEGUE / "Dockerfile").read_text(encoding="utf-8")
        self.assertNotIn("python cdsapi\n", texto)
        self.assertRegex(texto, r"cdsapi==[0-9]")

    def test_el_login_no_depende_de_un_navegador_automatizado(self) -> None:
        # S1: el login de Earthdata abría Chrome/Edge con Playwright (dependencia
        # pesada e inservible en Docker). Ahora la cookie se pega a mano y se
        # verifica contra OB.DAAC, así que el proyecto no menciona Playwright.
        earthdata = (RAIZ / "app" / "api" / "earthdata.py").read_text(encoding="utf-8")
        for prohibido in ("import playwright", "sync_playwright", "PLAYWRIGHT_BROWSERS_PATH"):
            self.assertNotIn(prohibido, earthdata)
        pyproject = (RAIZ / "pyproject.toml").read_text(encoding="utf-8")
        self.assertNotIn("playwright", pyproject.lower())

    def test_compose_publica_solo_en_loopback(self) -> None:
        texto = (DESPLIEGUE / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn('"127.0.0.1:${PORT:-8080}:8000"', texto)
        self.assertIn("${DATA_DIR:?", texto)
        self.assertNotIn("0.0.0.0:${PORT", texto)


class ElLanzadorNativo(unittest.TestCase):
    """ARRANCAR.ps1 abre el navegador, pero sin romper Ctrl+C."""

    def setUp(self) -> None:
        self.texto = (DESPLIEGUE / "ARRANCAR.ps1").read_text(encoding="utf-8")

    def test_abre_el_navegador_solo_cuando_la_api_responde(self) -> None:
        # Abrirlo antes muestra una pestaña con error de conexión.
        self.assertIn("/api/health", self.texto)
        self.assertLess(self.texto.index("/api/health"), self.texto.index("Start-Process $url"))

    def test_el_navegador_se_puede_apagar(self) -> None:
        # Servidor headless: sin esta salida, un arranque automático abre pestañas.
        self.assertIn("$SinNavegador", self.texto)
        self.assertLess(self.texto.index("if (-not $SinNavegador)"), self.texto.index("Start-Process $url"))

    def test_uvicorn_sigue_en_primer_plano(self) -> None:
        # La espera va en segundo plano: si uvicorn también lo estuviera, Ctrl+C
        # dejaría de cortar la consola.
        self.assertLess(self.texto.index("Start-Job"), self.texto.index("-m uvicorn"))

    def test_el_bat_propaga_el_fallo(self) -> None:
        # `pause` pisa errorlevel: sin guardarlo antes, un fallo del lanzador
        # devuelve 0 y cualquier script que lo llame cree que salió bien.
        lineas = [
            linea.strip()
            for linea in (DESPLIEGUE / "ARRANCAR.bat").read_text(encoding="utf-8").splitlines()
            if linea.strip() and not linea.strip().lower().startswith("rem")
        ]
        cuerpo = "\n".join(lineas)
        self.assertIn('set "codigo=%errorlevel%"', cuerpo)
        self.assertIn("exit /b %codigo%", cuerpo)

    def test_es_crlf(self) -> None:
        # .gitattributes pide CRLF para *.ps1 y *.bat.
        self.assertIn(b"\r\n", (DESPLIEGUE / "ARRANCAR.ps1").read_bytes())
        self.assertIn(b"\r\n", (DESPLIEGUE / "ARRANCAR.bat").read_bytes())


class ElSelloDeCommitDeLaImagen(unittest.TestCase):
    """Docker no puede servir código viejo sin avisar."""

    def setUp(self) -> None:
        self.dockerfile = (DESPLIEGUE / "Dockerfile").read_text(encoding="utf-8")
        self.compose = (DESPLIEGUE / "docker-compose.yml").read_text(encoding="utf-8")
        self.bat = (DESPLIEGUE / "ARRANCAR-DOCKER.bat").read_text(encoding="utf-8")

    def test_la_imagen_lleva_el_commit(self) -> None:
        self.assertIn("ARG CLIMATE3D_COMMIT", self.dockerfile)
        self.assertIn("LABEL climate3d_commit=", self.dockerfile)

    def test_el_compose_pasa_el_commit_al_build(self) -> None:
        # Sin esto el ARG llega vacío y la imagen siempre dice "desconocido".
        self.assertIn("CLIMATE3D_COMMIT:", self.compose)

    def test_el_lanzador_compara_contra_head_y_ofrece_recompilar(self) -> None:
        # La imagen se queda para siempre unless alguien la vuelve a compilar:
        # comparar el sello es lo único que detecta código viejo.
        self.assertIn("climate3d_commit", self.bat)
        self.assertIn("rev-parse --short HEAD", self.bat)
        self.assertIn('if /i "%IMAGEN_COMMIT%"=="%COMMIT%"', self.bat)
        self.assertIn("docker compose build", self.bat)

    def test_una_imagen_sin_sello_no_se_confunde_con_vieja(self) -> None:
        # `docker inspect --format` imprime `<no value>` cuando la imagen no tiene
        # labels (una cargada de un .tar viejo). Sin el control, el mensaje dice
        # "se compilo con <no value>" y cmd lee el `<` como redirección: se rompe
        # con "no se puede encontrar el archivo" en vez de avisar.
        cuerpo = _sin_comentarios(self.bat)
        self.assertIn("SIN_SELLO", cuerpo)
        self.assertNotIn("findstr", cuerpo)

    @unittest.skipUnless(sys.platform == "win32", "cmd y for /f son de Windows")
    def test_el_guard_acepta_el_sello_que_escribe_docker(self) -> None:
        # docker escribe el label con LF suelto. Un `findstr /r ...$` no matchea
        # líneas LF-only, así que la versión anterior mandaba TODA imagen sellada
        # a "no se puede verificar" y la comparación quedaba muerta. Este test
        # corre cmd de verdad sobre las dos formas de salto y sobre el centinela.
        import subprocess
        import tempfile

        script = (
            "@echo off\r\n"
            "setlocal enabledelayedexpansion\r\n"
            'set "V="\r\n'
            'for /f "usebackq delims=" %%i in ("%~1") do set "V=%%i"\r\n'
            'set "NO=0"\r\n'
            "if not defined V set \"NO=1\"\r\n"
            'if defined V for /f "delims=0123456789abcdefABCDEF" %%i in ("!V!") do set "NO=1"\r\n'
            "echo !NO!\r\n"
        )
        casos = [
            (b"3fe0110\n", "0"),        # así lo escribe docker: LF suelto
            (b"3fe0110\r\n", "0"),
            (b"<no value>\n", "1"),     # imagen sin labels
            (b"desconocido\n", "1"),    # compilada sin CLIMATE3D_COMMIT
            (b"", "1"),
        ]
        with tempfile.TemporaryDirectory() as carpeta:
            guardia = Path(carpeta) / "guardia.bat"
            guardia.write_text(script, encoding="ascii", newline="")
            for crudo, esperado in casos:
                sello = Path(carpeta) / "sello.txt"
                sello.write_bytes(crudo)
                corrida = subprocess.run(
                    ["cmd", "/c", str(guardia), str(sello)],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(corrida.stdout.strip(), esperado, f"con {crudo!r}")

    def test_exporta_el_commit_antes_de_compilar(self) -> None:
        # Sin exportarlo antes, el build sella "desconocido" y el aviso nunca más
        # detecta nada.
        self.assertLess(
            self.bat.index('set "CLIMATE3D_COMMIT=%COMMIT%"'),
            self.bat.index("docker compose build"),
        )
        self.assertLess(
            self.bat.index('set "CLIMATE3D_COMMIT=%COMMIT%"'),
            self.bat.index("setup.ps1"),
        )

    def test_los_goto_apuntan_a_etiquetas_existentes(self) -> None:
        # Un goto a una etiqueta que no existe mata el .bat en silencio.
        import re

        etiquetas = {
            linea.strip()[1:]
            for linea in self.bat.splitlines()
            if linea.strip().startswith(":") and not linea.strip().startswith("::")
        }
        destinos = set(re.findall(r"goto\s+(\w+)", self.bat))
        self.assertEqual(destinos - etiquetas, set())


class InterpreteAisladoDelEntorno(unittest.TestCase):
    def test_un_mapa_vacio_no_hereda_os_environ(self) -> None:
        # `_python_repo({})` es "sin entorno", no "el entorno real".
        with mock.patch.dict(os.environ, {"CLIMATE3D_PYTHON": "/centinela/python"}):
            self.assertEqual(_python_repo(), Path("/centinela/python"))
            self.assertNotEqual(_python_repo({}), Path("/centinela/python"))
            self.assertIn(".venv", _python_repo({}).parts)


@unittest.skipIf(TestClient is None, "la API necesita las dependencias del venv de la app")
class RevealFueraDelContenedor(unittest.TestCase):
    def test_sin_la_variable_sigue_abriendo_la_carpeta(self) -> None:
        # CLIMATE3D_CONTENEDOR=0 no puede desactivar el comportamiento de siempre.
        cliente = TestClient(main.app)
        with tempfile.TemporaryDirectory() as carpeta:
            original = main.gestor.obtener
            main.gestor.obtener = lambda job_id: mock.Mock(work=Path(carpeta))  # type: ignore[assignment]
            try:
                with mock.patch.dict(os.environ, {"CLIMATE3D_CONTENEDOR": "0"}), \
                        mock.patch.object(main.subprocess, "Popen") as popen:
                    respuesta = cliente.post("/api/jobs/cualquiera/reveal")
            finally:
                main.gestor.obtener = original  # type: ignore[assignment]

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(popen.call_count, 1)


if __name__ == "__main__":
    unittest.main()
