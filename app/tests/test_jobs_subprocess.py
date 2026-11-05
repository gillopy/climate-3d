"""Regresion: un job tiene que correr en cualquier event loop.

En Windows, uvicorn arrancado con ``--reload`` usa un loop Selector, y ahi
``asyncio.create_subprocess_exec`` tira ``NotImplementedError`` sin mensaje. El
job moria al instante con progreso 0 y el log vacio. ``_lanzar`` usa
``subprocess.Popen`` + un hilo lector para no depender del loop.

    app\\.venv\\Scripts\\python.exe -m unittest app.tests.test_jobs_subprocess
"""
from __future__ import annotations

import asyncio
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
    from app.api import jobs
except ImportError:  # pragma: no cover - faltan dependencias del venv de la app
    jobs = None


@unittest.skipIf(jobs is None, "la API necesita las dependencias del venv de la app")
class LanzarEnUnLoopSelector(unittest.TestCase):
    """El caso que rompia: loop Selector, el que usa uvicorn --reload en Windows."""

    def test_captura_la_salida_del_script(self):
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal)
            (raiz / "eco.py").write_text(
                "print('hola desde el hijo')\nprint('chau')\n", encoding="utf-8"
            )
            media = raiz / "media"
            media.mkdir()
            gestor = jobs.JobManager(media)
            trabajo = jobs.Job(
                id="prueba",
                product_id="x",
                product_name="X",
                params={},
                mode="real",
                dir=media / "work",
            )
            paso = SimpleNamespace(
                kind="render", label="eco", script="eco.py", args=[], expected=0
            )

            loop = asyncio.SelectorEventLoop()
            try:
                with mock.patch.object(jobs, "RAIZ_REPO", raiz), mock.patch.object(
                    jobs, "python_repo", lambda: Path(sys.executable)
                ):
                    codigo = loop.run_until_complete(
                        gestor._lanzar(trabajo, paso, [], 0.0, 1.0, "[1/1] eco")
                    )
            finally:
                loop.close()

            textos = [linea.text for linea in trabajo.logs]
            self.assertEqual(codigo, 0, textos)
            self.assertIn("[1/1] eco", textos)
            self.assertTrue(
                any("hola desde el hijo" in texto for texto in textos), textos
            )


if __name__ == "__main__":
    unittest.main()
