"""Kit de render NISAR: tamano de salida y barra de escala.

El visor sirve el PNG como overlay; agrandarlo por encima del recorte nativo no
agrega detalle y desalinea la barra de escala respecto de los metros por pixel
del recorte. Estas pruebas corren con el Python del repo (el de los scripts),
igual que ``test_nisar_render``, porque ``comun.nisar`` necesita h5py.
"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

try:
    from app.api.recipes import python_repo
except ImportError:  # pragma: no cover
    python_repo = None

CODIGO = r'''
import tempfile
from pathlib import Path

import numpy as np

from comun import nisar

# 1213x1755 es el recorte real de una caja de 24x35 km a 20 m.
assert nisar.dimensiones(1213, 1755, 2400) == (1213, 1755), "agrando un recorte chico"
assert nisar.dimensiones(4000, 3000, 1000) == (1000, 750), "no redujo al pedido"
assert nisar.dimensiones(1, 1000, 2400) == (1, 1000), "rompio el aspecto"
assert nisar.dimensiones(1, 1, 2400) == (1, 1), "devolvio cero"

with tempfile.TemporaryDirectory() as carpeta:
    salida = Path(carpeta) / "caja.png"
    rgb = np.full((100, 80, 3), 128, dtype=np.uint8)
    ancho, alto = nisar.guardar(rgb, salida, ["uno", "dos", "tres"], 20.0, 2400)
    assert ancho == 80, f"ancho {ancho}"
    assert 100 <= alto < 200, f"alto {alto}"
    assert salida.is_file(), "no escribio el PNG"

# Multilook: promedia potencia y baja el speckle sin tocar la media.
rng = np.random.default_rng(7)
plano = np.full((60, 60), 0.02)
assert np.allclose(nisar.multilook(plano, 5), plano), "el campo constante cambio"
assert np.isnan(nisar.multilook(np.where(np.ones((20, 20)) > 0, np.nan, 1.0), 3)).all(), "NaN no se propago"

speckle = rng.gamma(shape=1.0, scale=0.02, size=(120, 120))
suave = nisar.multilook(speckle, 9)
assert np.nanstd(suave) < np.nanstd(speckle) * 0.35, "el multilook no redujo el ruido"
assert abs(np.nanmean(suave) - np.nanmean(speckle)) < 0.002, "el multilook cambio la media"

assert nisar.ventana_para(10.0) == 9, nisar.ventana_para(10.0)
assert nisar.ventana_para(20.0) == 5, nisar.ventana_para(20.0)
for mpp in (1.0, 3.7, 6.0, 10.0, 20.0, 40.0):
    assert nisar.ventana_para(mpp) % 2 == 1, f"ventana par para {mpp}"
    assert 1 <= nisar.ventana_para(mpp) <= 9
'''


@unittest.skipIf(
    python_repo is None or not python_repo().is_file(),
    "hace falta el Python del repo para el kit de render",
)
class KitNisar(unittest.TestCase):
    def test_dimensiones_y_guardar_no_agrandan(self):
        corrida = subprocess.run(
            [str(python_repo()), "-c", CODIGO],
            capture_output=True,
            text=True,
            cwd=str(RAIZ),
        )
        self.assertEqual(corrida.returncode, 0, corrida.stderr + corrida.stdout)


if __name__ == "__main__":
    unittest.main()
