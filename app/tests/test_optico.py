"""Funciones ópticas puras: NDVI, SCL, compuesto mediano y clasificación.

No tocan red, rasterio ni STAC; el script `nisar_fusion.py` es el que baja las
imágenes. Así la lógica se prueba en el venv de la app, sin GDAL.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from comun import optico  # noqa: E402


class OpticoPuro(unittest.TestCase):
    def test_ndvi_y_nan(self):
        rojo = np.array([0.2, 0.4, 0.0], dtype=np.float32)
        nir = np.array([0.6, 0.2, 0.0], dtype=np.float32)

        salida = optico.ndvi(rojo, nir)

        np.testing.assert_allclose(salida[:2], [0.5, -1.0 / 3.0], rtol=1e-6)
        self.assertTrue(np.isnan(salida[2]))

    def test_mascara_scl_deja_pasar_vegetacion_y_agua(self):
        scl = np.array([0, 2, 4, 6, 8, 9, 10, 11, 3, 1])

        valida = optico.mascara_scl(scl)

        np.testing.assert_array_equal(
            valida,
            [False, True, True, True, False, False, False, False, False, False],
        )

    def test_compuesto_mediana_ignora_nan(self):
        a = np.array([[1.0, 2.0], [3.0, np.nan]])
        b = np.array([[3.0, 4.0], [1.0, 5.0]])
        c = np.array([[5.0, 0.0], [7.0, 6.0]])

        salida = optico.compuesto_mediana([a, b, c])

        np.testing.assert_allclose(salida, [[3.0, 2.0], [3.0, 5.5]])

    def test_clasificacion_rule_based(self):
        hv = np.array([[-22.0, -12.0, -18.0, -18.0, -30.0]])
        nd = np.array([[0.0, 0.7, 0.4, 0.1, np.nan]])

        clases = optico.clasificar(hv, nd)

        np.testing.assert_array_equal(clases, [[1, 2, 3, 4, 0]])

    def test_suavizado_de_clases_quita_un_pixel_aislado(self):
        clases = np.array(
            [
                [2, 2, 2, 2, 2],
                [2, 2, 2, 2, 2],
                [2, 2, 3, 2, 2],
                [2, 2, 2, 2, 2],
                [2, 2, 2, 2, 2],
            ],
            dtype=np.uint8,
        )

        salida = optico.suavizar_clases(clases)

        np.testing.assert_array_equal(salida, np.full((5, 5), 2, dtype=np.uint8))

    def test_suavizado_conserva_un_bloque_y_el_fondo(self):
        clases = np.array(
            [
                [0, 0, 0, 0, 0],
                [0, 2, 2, 2, 0],
                [0, 2, 2, 2, 0],
                [0, 2, 2, 2, 0],
                [0, 0, 0, 0, 0],
            ],
            dtype=np.uint8,
        )

        salida = optico.suavizar_clases(clases)

        np.testing.assert_array_equal(salida, clases)


if __name__ == "__main__":
    unittest.main()
