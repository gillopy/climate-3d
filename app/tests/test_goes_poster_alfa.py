"""El encuadre regional de los pósteres GOES no puede cortar en círculo.

Regresión: con "Solo Paraguay" el render pasa `--centro` + `--recorte`
(escala << 1). Los pósteres de banda, sandwich y LST aplicaban además el corte
del planeta (0.98 del marco) y las esquinas salían negras, como un globo
recortado. Sólo el modo globo (escala ~= 1) debe cortar en el círculo: con zoom
el dato válido llena el cuadro y la imagen queda cuadrada.

    .venv\\Scripts\\python.exe -m unittest app.tests.test_goes_poster_alfa
"""
from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
for ruta in (RAIZ, RAIZ / "prototipos", RAIZ / "comun"):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))


def _dependencias_de_render() -> bool:
    """El runner de `app/tests` no instala matplotlib ni xarray: sin eso, se saltea."""
    try:
        import matplotlib  # noqa: F401
        import xarray  # noqa: F401
    except ModuleNotFoundError:
        return False
    return True


HAY_RENDER = _dependencias_de_render()

if HAY_RENDER:
    import poster_goes_banda
    import poster_goes_lst
    import poster_goes_sandwich

PX = 64
H = 35786023.0
LON0 = -75.2
#: Sin zoom: el disco inscribe el cuadro y el corte del planeta sí aplica.
ESCALA_GLOBO = 0.9885
#: Encuadre Paraguay observado en la app (--recorte 0.0975462 * sin(h)).
ESCALA_PAIS = 0.0964

_ATTRS = {
    "perspective_point_height": H,
    "longitude_of_projection_origin": LON0,
}


class _Dataset:
    """Lo mínimo de `xarray.Dataset` que leen los pósteres."""

    def __enter__(self):
        return self

    def __exit__(self, *_excepcion):
        return False

    def __getitem__(self, _clave):
        return types.SimpleNamespace(attrs=_ATTRS)


def _campo():
    x = np.linspace(-0.10, 0.10, 8)
    y = np.linspace(0.10, -0.10, 8)
    return np.full((8, 8), 20.0, np.float32), x, y, None, "C", None


def _args(**extra):
    base = dict(
        tope=8, centro=[-58.4505, -23.4505], recorte=1.0, px=PX,
        interp=None, vmin=-93.0, vmax=7.0, alpha=0.5, paleta="gris",
        mapa="negro", relleno=0, compuesto=1, sat="G19",
    )
    base.update(extra)
    return types.SimpleNamespace(**base)


def _componer(modulo, escala, componer, *posicionales, args=None):
    """Corre un compositor con campo, proyección y geometría falsos."""
    parches = [
        mock.patch("xarray.open_dataset", lambda *_a, **_k: _Dataset()),
        mock.patch.object(modulo, "radio_visible",
                          lambda *_a, **_k: (escala, H, LON0)),
        mock.patch("builtins.print"),
    ]
    if hasattr(modulo, "cargar"):     # el LST arma el campo por `_campo_compuesto`
        parches.append(mock.patch.object(modulo, "cargar",
                                         lambda *_a, **_k: _campo()))
    for parche in parches:
        parche.start()
    try:
        with np.errstate(invalid="ignore"):   # el campo falso es NaN fuera de grilla
            return componer(*posicionales, args or _args())
    finally:
        for parche in reversed(parches):
            parche.stop()


def _esquinas(rgba):
    return [int(rgba[0, 0, 3]), int(rgba[0, -1, 3]),
            int(rgba[-1, 0, 3]), int(rgba[-1, -1, 3])]


@unittest.skipUnless(HAY_RENDER, "faltan matplotlib/xarray: correr con .venv")
class ZoomRegionalCuadrado(unittest.TestCase):
    """Con `--recorte` el dato llena el cuadro: nada de esquinas negras."""

    def test_banda(self):
        rgba, _escala, _ = _componer(
            poster_goes_banda, ESCALA_PAIS,
            poster_goes_banda.componer_banda, Path("nc"))
        self.assertEqual(_esquinas(rgba), [255, 255, 255, 255])

    def test_sandwich(self):
        rgba, _escala, _ = _componer(
            poster_goes_sandwich, ESCALA_PAIS,
            poster_goes_sandwich.componer_sandwich, Path("vis"), Path("ir"))
        self.assertEqual(_esquinas(rgba), [255, 255, 255, 255])

    def test_lst(self):
        modulo = poster_goes_lst
        with mock.patch.object(modulo, "_campo_compuesto",
                               lambda *_a, **_k: (*_campo()[:3], H, LON0, 1)):
            rgba, _escala, _ = _componer(
                modulo, ESCALA_PAIS, modulo.componer_lst, Path("nc"))
        self.assertEqual(_esquinas(rgba), [255, 255, 255, 255])


@unittest.skipUnless(HAY_RENDER, "faltan matplotlib/xarray: correr con .venv")
class GloboConservaElCorte(unittest.TestCase):
    """El comportamiento previo del globo no cambia: sigue cortando en círculo."""

    def test_banda(self):
        rgba, _escala, _ = _componer(
            poster_goes_banda, ESCALA_GLOBO,
            poster_goes_banda.componer_banda, Path("nc"))
        self.assertEqual(_esquinas(rgba), [0, 0, 0, 0])

    def test_sandwich(self):
        rgba, _escala, _ = _componer(
            poster_goes_sandwich, ESCALA_GLOBO,
            poster_goes_sandwich.componer_sandwich, Path("vis"), Path("ir"))
        self.assertEqual(_esquinas(rgba), [0, 0, 0, 0])

    def test_lst(self):
        modulo = poster_goes_lst
        with mock.patch.object(modulo, "_campo_compuesto",
                               lambda *_a, **_k: (*_campo()[:3], H, LON0, 1)):
            rgba, _escala, _ = _componer(
                modulo, ESCALA_GLOBO, modulo.componer_lst, Path("nc"))
        self.assertEqual(_esquinas(rgba), [0, 0, 0, 0])


if __name__ == "__main__":
    unittest.main()
