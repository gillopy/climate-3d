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

# MMU: un desmonte es un bloque, no pixeles sueltos.
m = np.zeros((40, 40), dtype=bool)
m[2:6, 2:6] = True      # 16 px
m[20:22, 20:22] = True  # 4 px
filtrada = nisar.filtrar_mmu(m, 10)
assert filtrada.sum() == 16, filtrada.sum()
assert filtrada[3, 3] and not filtrada[20, 20], "no descarto el parche chico"
assert nisar.filtrar_mmu(m, 1).sum() == 20, "con minimo 1 cambio la mascara"

# Baseline temporal: las fechas anteriores al par, del mismo track/frame y carpeta.
GRANULO_SIN = (
    "NISAR_L2_PR_GCOV_{}_082_D_101_2005_DHDH_A_{}T120000_{}T120034_"
    "P05036_N_F_J_001"
)
with tempfile.TemporaryDirectory() as carpeta:
    base = Path(carpeta)
    for ciclo, dia in (("027", "20260524"), ("028", "20260605"), ("029", "20260617"),
                       ("030", "20260629"), ("031", "20260711")):
        (base / (GRANULO_SIN.format(ciclo, dia, dia) + ".h5")).touch()
    # Otro frame en la misma carpeta: nunca entra al baseline del par.
    (base / (GRANULO_SIN.replace("_101_", "_102_").format("031", "20260711", "20260711") + ".h5")).touch()
    antes = base / (GRANULO_SIN.format("029", "20260617", "20260617") + ".h5")
    nombres = [p.name for p in nisar.escenas_anteriores(antes, 2)]
    assert nombres == [
        GRANULO_SIN.format("028", "20260605", "20260605") + ".h5",
        GRANULO_SIN.format("027", "20260524", "20260524") + ".h5",
    ], nombres  # mas recientes primero y nada del otro frame
    assert nisar.escenas_anteriores(antes, 0) == [], "maximo 0 no dio lista vacia"
    primera = base / (GRANULO_SIN.format("027", "20260524", "20260524") + ".h5")
    assert nisar.escenas_anteriores(primera, 2) == [], "sin fechas previas no dio vacia"

# Pila: mediana y CoV por pixel, NaN-aware, siempre en potencia.
plana = np.stack([np.full((4, 4), 0.10), np.full((4, 4), 0.20), np.full((4, 4), 0.30)])
assert np.allclose(nisar.pila_mediana(plana), 0.20), "la mediana no dio la del medio"
con_nan = plana.copy()
con_nan[0, 0, 0] = np.nan
con_nan[1, 0, 0] = np.nan
assert np.isclose(nisar.pila_mediana(con_nan)[0, 0], 0.30), "no ignoro el NaN de una fecha"
todo_nan = plana.copy()
todo_nan[:, 1, 1] = np.nan
assert np.isnan(nisar.pila_mediana(todo_nan)[1, 1]), "pixel sin datos no quedo NaN"

estable = np.stack([np.full((3, 3), 0.05), np.full((3, 3), 0.05)])
assert np.allclose(nisar.pila_cov(estable), 0.0), "pila constante no dio CoV 0"
variada = np.stack([np.full((3, 3), 0.05), np.full((3, 3), 0.15)])
assert np.allclose(nisar.pila_cov(variada), 0.5), "CoV de 0.05/0.15 no dio 0.5"
una_nan = variada.copy()
una_nan[0, 2, 2] = np.nan
assert np.isclose(nisar.pila_cov(una_nan)[2, 2], 0.0), "CoV no ignoro el NaN de una fecha"
ceros = np.stack([np.zeros((2, 2)), np.zeros((2, 2))])
assert np.isnan(nisar.pila_cov(ceros)).all(), "CoV con media 0 no quedo NaN"
soltera = np.stack([np.full((2, 2), 0.07)])
assert np.isnan(nisar.pila_cov(soltera)).all(), "CoV de una sola fecha no quedo NaN"
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
