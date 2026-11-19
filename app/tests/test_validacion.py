import unittest

import numpy as np

from comun import validacion


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
