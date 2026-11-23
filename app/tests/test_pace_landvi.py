"""Tests for PACE LANDVI authentication discovery."""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


RAIZ = Path(__file__).resolve().parents[2]
ESPEC = importlib.util.spec_from_file_location("pace_landvi", RAIZ / "descargar" / "pace_landvi.py")
assert ESPEC and ESPEC.loader
pace = importlib.util.module_from_spec(ESPEC)
sys.modules["pace_landvi"] = pace
ESPEC.loader.exec_module(pace)


class AutenticacionPACE(unittest.TestCase):
    def test_sesion_usa_credenciales_del_env_del_repo(self):
        with patch.object(pace, "RAIZ", Path(tempfile.mkdtemp())), patch.dict(
            os.environ,
            {"EARTHDATA_USER": "usuario-prueba", "EARTHDATA_PASSWORD": "secreto-prueba"},
            clear=False,
        ):
            sesion = pace._sesion(None)

        self.assertEqual(sesion.auth, ("usuario-prueba", "secreto-prueba"))

    def test_sesion_informa_todas_las_formas_de_autenticacion(self):
        with patch.object(pace, "_credenciales", return_value=None):
            with self.assertRaises(SystemExit) as contexto:
                pace._sesion(None)

        self.assertIn("EARTHDATA_USER", str(contexto.exception))
        self.assertIn("--cookies", str(contexto.exception))
        self.assertIn(".netrc", str(contexto.exception))


if __name__ == "__main__":
    unittest.main()
