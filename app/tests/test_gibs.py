"""Capacidades WMTS de GIBS: qué capa publica hasta qué día.

    .venv\\Scripts\\python.exe -m unittest app.tests.test_gibs
"""
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from comun.gibs import ultima_fecha_de_capa  # noqa: E402

# Recorte fiel del XML de GIBS: dos capas con dominios temporales distintos.
XML = """<Capabilities><Contents>
<Layer><ows:Title>Corrected Reflectance (True Color, OCI, PACE)</ows:Title>
<ows:Identifier>OCI_PACE_True_Color</ows:Identifier>
<Dimension><ows:Identifier>Time</ows:Identifier>
<Default>2026-11-09</Default>
<Value>2024-02-25/2024-03-12/P1D</Value>
<Value>2026-03-21/2026-11-09/P1D</Value></Dimension>
</Layer>
<Layer><ows:Title>Chlorophyll a (OCI, PACE)</ows:Title>
<ows:Identifier>OCI_PACE_Chlorophyll_a</ows:Identifier>
<Dimension><ows:Identifier>Time</ows:Identifier>
<Default>2026-11-23</Default>
<Value>2026-03-21/2026-11-23/P1D</Value></Dimension>
</Layer>
</Contents></Capabilities>"""


class UltimaFechaDeCapa(unittest.TestCase):
    def test_toma_el_fin_del_ultimo_tramo(self):
        self.assertEqual(
            ultima_fecha_de_capa(XML, "OCI_PACE_True_Color"), date(2026, 11, 9)
        )

    def test_cada_capa_tiene_su_propio_techo(self):
        self.assertEqual(
            ultima_fecha_de_capa(XML, "OCI_PACE_Chlorophyll_a"), date(2026, 11, 23)
        )

    def test_capa_inexistente_devuelve_none(self):
        self.assertIsNone(ultima_fecha_de_capa(XML, "NO_EXISTE"))

    def test_capa_sin_dominio_temporal_devuelve_none(self):
        xml = "<Layer><ows:Identifier>X</ows:Identifier></Layer>"
        self.assertIsNone(ultima_fecha_de_capa(xml, "X"))


if __name__ == "__main__":
    unittest.main()
