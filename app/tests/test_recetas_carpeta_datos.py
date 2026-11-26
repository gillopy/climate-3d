"""La carpeta de datos de una receta no puede salirse de la raíz configurada.

S1 (auditoría): `satelite` y `banda` llegan del cuerpo del pedido sin validar y se
interpolaban en el nombre de carpeta bajo la raíz de datos. El hijo del pipeline
hacía `mkdir(parents=True)` sobre esa ruta antes de validar nada, así que un valor
con `..` creaba directorios fuera de `CLIMATE3D_DATOS`.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from app.api import recipes  # noqa: E402


def _params(**extra: object) -> dict[str, object]:
    base: dict[str, object] = {"desde": "2020-01-01", "hasta": "2020-01-02"}
    base.update(extra)
    return base


class CarpetaDeDatosConfinada(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        parche = mock.patch("app.api.catalog.data_root", return_value=self.raiz)
        parche.start()
        self.addCleanup(parche.stop)
        self.addCleanup(self._tmp.cleanup)

    def test_una_carpeta_normal_queda_adentro(self) -> None:
        carpeta = recipes._carpeta_datos("goes_c13_g19")

        self.assertEqual(carpeta, (self.raiz / "goes_c13_g19").resolve())

    def test_una_carpeta_con_puntos_puntos_es_rechazada(self) -> None:
        with self.assertRaises(ValueError):
            recipes._carpeta_datos("goes_c13_/../../../../tmp/poc")

    def test_una_carpeta_absoluta_es_rechazada(self) -> None:
        with self.assertRaises(ValueError):
            recipes._carpeta_datos("/tmp/poc")

    def test_el_plan_de_goes_rechaza_un_satelite_que_escapa(self) -> None:
        with tempfile.TemporaryDirectory() as work:
            with self.assertRaises(ValueError):
                recipes.planear(
                    "goes_c13",
                    _params(satelite="x/../../../../tmp/poc"),
                    Path(work),
                )

    def test_el_plan_de_goes_sigue_armandose_con_un_satelite_valido(self) -> None:
        with tempfile.TemporaryDirectory() as work:
            plan = recipes.planear("goes_c13", _params(satelite="G19"), Path(work))

        self.assertTrue(plan.pasos)


if __name__ == "__main__":
    unittest.main()
