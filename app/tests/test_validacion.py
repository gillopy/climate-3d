"""Métricas puras de validación: confusión, F1/IoU, bootstrap y muestreo."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from comun import validacion  # noqa: E402


class MetricasDeValidacion(unittest.TestCase):
    def test_matriz_de_confusion_y_metricas(self):
        referencia = np.array([True, True, False, False])
        prediccion = np.array([True, False, True, False])

        tp, fp, fn, tn = validacion.matriz_confusion(referencia, prediccion)

        self.assertEqual((tp, fp, fn, tn), (1, 1, 1, 1))
        fila = validacion.metricas(tp, fp, fn, tn)
        self.assertAlmostEqual(fila["precision"], 0.5)
        self.assertAlmostEqual(fila["recall"], 0.5)
        self.assertAlmostEqual(fila["f1"], 0.5)
        self.assertAlmostEqual(fila["iou"], 1 / 3)
        self.assertAlmostEqual(fila["accuracy"], 0.5)

    def test_metricas_ponderadas_reexpanden_la_muestra(self):
        fila = validacion.metricas_ponderadas(1, 1, 1, 1, 2.0, 3.0)

        self.assertAlmostEqual(fila["precision"], 0.4)
        self.assertAlmostEqual(fila["recall"], 0.5)
        self.assertAlmostEqual(fila["f1"], 2 * 0.4 * 0.5 / 0.9)

    def test_bootstrap_devuelve_intervalos(self):
        referencia = np.array([True, True, False, False] * 10)
        prediccion = np.array([True, False, True, False] * 10)

        intervalo = validacion.bootstrap_ic(referencia, prediccion, n=50)

        self.assertIn("f1", intervalo)
        self.assertLessEqual(intervalo["f1"]["p2_5"], intervalo["f1"]["p97_5"])
        self.assertAlmostEqual(intervalo["precision"]["mean"], 0.5, places=2)

    def test_muestreo_adelgaza_y_separa_clases(self):
        mascara_a = np.zeros((10, 10), dtype=bool)
        mascara_a[0:4, 0:4] = True
        mascara_b = np.zeros((10, 10), dtype=bool)
        mascara_b[6:10, 6:10] = True

        muestras = validacion.muestreo_estratificado(
            {"perdida": mascara_a, "estable": mascara_b}, 2, separacion=2
        )

        self.assertLessEqual(len(muestras["perdida"][0]), 2)
        self.assertLessEqual(len(muestras["estable"][0]), 2)
        for fila, columna in zip(*muestras["perdida"]):
            self.assertTrue(mascara_a[fila, columna])
        for fila, columna in zip(*muestras["estable"]):
            self.assertTrue(mascara_b[fila, columna])


class ValidacionPorBloques(unittest.TestCase):
    def test_metricas_por_bloques_agrega_mayoria_y_reporta_cantidad(self):
        referencia = np.array(
            [
                [True, True, False, False],
                [True, False, False, False],
                [False, False, True, True],
                [False, False, True, False],
            ]
        )
        prediccion = np.array(
            [
                [True, False, False, False],
                [True, True, False, False],
                [False, False, True, False],
                [False, False, False, False],
            ]
        )

        resultado = validacion.metricas_por_bloques(referencia, prediccion, bloque=2)

        self.assertEqual(resultado["bloques"], 4.0)
        self.assertEqual(resultado["tp"], 1.0)
        self.assertEqual(resultado["fp"], 0.0)
        self.assertEqual(resultado["fn"], 1.0)
        self.assertEqual(resultado["tn"], 2.0)
        self.assertEqual(resultado["tamano_bloque"], 2.0)

    def test_bootstrap_por_bloques_es_reproducible_y_no_muestrea_pixeles(self):
        referencia = np.array(
            [
                [True, True, False, False],
                [True, False, False, False],
                [False, False, True, True],
                [False, False, True, False],
            ]
        )
        prediccion = np.array(
            [
                [True, False, False, False],
                [True, True, False, False],
                [False, False, True, False],
                [False, False, False, False],
            ]
        )

        primero = validacion.bootstrap_bloques_ic(referencia, prediccion, bloque=2, n=20)
        segundo = validacion.bootstrap_bloques_ic(referencia, prediccion, bloque=2, n=20)

        self.assertEqual(primero, segundo)
        self.assertEqual(set(primero), {"precision", "recall", "f1"})
        for intervalo in primero.values():
            self.assertLessEqual(intervalo["p2_5"], intervalo["p97_5"])


if __name__ == "__main__":
    unittest.main()
