"""Guarda de fuentes: todo el repo compila y está en UTF-8 limpio.

Pasó de verdad: un `Set-Content` por consola convirtió un acento en un byte Latin-1
y `prototipos/poster_goes_truecolor.py` dejó de importarse (`SyntaxError: Non-UTF-8
code`). Ningún test lo vio porque nada importaba ese póster: la suite corre los
módulos de la app, no los prototipos.

    app\\.venv\\Scripts\\python.exe -m unittest discover -s app\\tests
"""
from __future__ import annotations

import compileall
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

#: Todo lo que corre con el Python del repo, incluidos los prototipos.
CARPETAS = ("app/api", "app/tests", "comun", "cuadros", "descargar",
            "prototipos", "animar")


class Fuentes(unittest.TestCase):
    """Ningún archivo puede quedar ilegible para el intérprete."""

    def test_todo_compila(self):
        for carpeta in CARPETAS:
            self.assertTrue(
                compileall.compile_dir(str(RAIZ / carpeta), quiet=2, force=True),
                f"{carpeta} no compila")

    def test_todo_es_utf8_limpio(self):
        for carpeta in CARPETAS:
            for archivo in sorted((RAIZ / carpeta).rglob("*.py")):
                with self.subTest(archivo=str(archivo.relative_to(RAIZ))):
                    texto = archivo.read_text(encoding="utf-8")
                    # El carácter de reemplazo es la huella de una conversión rota.
                    self.assertNotIn("\ufffd", texto)


if __name__ == "__main__":
    unittest.main()
