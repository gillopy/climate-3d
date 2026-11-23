"""Tests for PACE LANDVI authentication discovery and auto cookie discovery."""
from __future__ import annotations

import importlib.util
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
    def test_sesion_usa_cookies_del_archivo(self):
        with tempfile.TemporaryDirectory() as carpeta:
            cookies = Path(carpeta) / "cookies.json"
            cookies.write_text(
                '[{"name": "GETFILE_APP", "value": "abc", "domain": "oceandata.sci.gsfc.nasa.gov", "path": "/"}]',
                encoding="utf-8",
            )
            sesion = pace._sesion(cookies)

        self.assertEqual(sesion.cookies.get("GETFILE_APP"), "abc")

    def test_sesion_informa_cookies_y_netrc_si_faltan(self):
        with patch("netrc.netrc", side_effect=FileNotFoundError):
            with self.assertRaises(SystemExit) as contexto:
                pace._sesion(None)

        self.assertIn("--cookies", str(contexto.exception))
        self.assertIn(".netrc", str(contexto.exception))

    def test_ruta_cookies_earthdata_es_independiente_del_repo(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = pace.ruta_cookies_earthdata({"LOCALAPPDATA": carpeta})

        self.assertEqual(ruta.name, "earthdata_cookies.json")


if __name__ == "__main__":
    unittest.main()
