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
