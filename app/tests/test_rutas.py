"""Rutas e intérprete del pipeline: la configuración vive en un solo lugar.

Estas pruebas fijan el contrato del que depende el contenedor: `CLIMATE3D_DATOS` manda,
el default de Windows no cambia y el intérprete se puede apuntar con `CLIMATE3D_PYTHON`.

    app\\.venv\\Scripts\\python.exe -m unittest discover -s app\\tests
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
for candidato in (RAIZ, RAIZ / "comun"):
    if str(candidato) not in sys.path:
        sys.path.insert(0, str(candidato))

import rutas  # noqa: E402
from app.api.recipes import _python_repo  # noqa: E402


class RaizDeDatos(unittest.TestCase):
    def test_la_variable_de_entorno_manda(self) -> None:
        for plataforma in ("nt", "posix"):
            self.assertEqual(
                rutas.raiz_datos({"CLIMATE3D_DATOS": "/mi/datos"}, plataforma),
                Path("/mi/datos"),
            )

    def test_una_variable_vacia_no_pisa_el_default(self) -> None:
        self.assertEqual(
            rutas.raiz_datos({"CLIMATE3D_DATOS": "   "}, "nt"), Path(rutas.RUTA_LEGADA)
        )

    def test_windows_conserva_la_ruta_historica(self) -> None:
        # S8: el flujo que ya funcionaba en Windows no cambia.
        self.assertEqual(
            rutas.raiz_datos({}, "nt"), Path(r"D:\Users\guill\dataset era5")
        )

    def test_fuera_de_windows_apunta_al_volumen_del_contenedor(self) -> None:
        # S5: dentro del contenedor la ruta es siempre /data.
        self.assertEqual(rutas.raiz_datos({}, "posix"), Path("/data"))

    def test_la_variable_real_del_proceso_se_respeta(self) -> None:
        original = os.environ.get("CLIMATE3D_DATOS")
        os.environ["CLIMATE3D_DATOS"] = "/desde/el/proceso"
        try:
            self.assertEqual(rutas.raiz_datos(), Path("/desde/el/proceso"))
        finally:
            if original is None:
                del os.environ["CLIMATE3D_DATOS"]
            else:
                os.environ["CLIMATE3D_DATOS"] = original


class CarpetasExtra(unittest.TestCase):
    def test_las_extra_del_entorno_van_primero(self) -> None:
        crudo = os.pathsep.join(["/uno", "/dos"])
        extra = rutas.carpetas_extra({"CLIMATE3D_EXTRA_DIRS": crudo}, "posix")
        self.assertEqual(extra[0], Path("/uno"))
        self.assertEqual(extra[1], Path("/dos"))

    def test_la_raiz_del_repo_siempre_esta_una_sola_vez(self) -> None:
        extra = rutas.carpetas_extra({}, "posix")
        self.assertIn(rutas.RAIZ, extra)
        self.assertEqual(sum(1 for p in extra if p == rutas.RAIZ), 1)

    def test_windows_conserva_el_escritorio_historico(self) -> None:
        self.assertIn(Path(r"D:\Users\guill\Desktop"), rutas.carpetas_extra({}, "nt"))
        self.assertNotIn(Path(r"D:\Users\guill\Desktop"), rutas.carpetas_extra({}, "posix"))


class InterpreteDelPipeline(unittest.TestCase):
    def test_la_variable_de_entorno_manda(self) -> None:
        self.assertEqual(
            _python_repo({"CLIMATE3D_PYTHON": "/app/.venv/bin/python"}),
            Path("/app/.venv/bin/python"),
        )

    def test_sin_variable_usa_el_venv_del_repo(self) -> None:
        self.assertIn(".venv", _python_repo({}).parts)


if __name__ == "__main__":
    unittest.main()
