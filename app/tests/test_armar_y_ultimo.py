"""Pruebas de la animación tolerante a huecos y del "último cuadro disponible".

Fijan lo que la app promete:

  * una serie con huecos (GIBS publica con retraso) **no** aborta: se arman los
    cuadros que sí existen y ffmpeg recibe una secuencia contigua;
  * el check "último cuadro disponible" usa el mismo camino que "últimos datos"
    con N=1, para todos los productos que ya saben resolver los últimos;
  * el Snapshot de Paraguay conserva su propio switch (`ultima`).

    app\\.venv\\Scripts\\python.exe -m unittest discover -s app\\tests
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import types
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
for ruta in (RAIZ, RAIZ / "comun", RAIZ / "cuadros"):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))

from PIL import Image  # noqa: E402

from app.api import catalog, recipes  # noqa: E402


def _armar():
    """`animar/armar.py` como módulo.

    El `app/.venv` de la API no trae `imageio_ffmpeg` (lo usa el `.venv` de la raíz
    para codificar): acá no se codifica nada, así que se reemplaza por un doble.
    """
    sys.modules.setdefault("imageio_ffmpeg",
                           types.SimpleNamespace(get_ffmpeg_exe=lambda: "ffmpeg"))
    spec = importlib.util.spec_from_file_location("armar", RAIZ / "animar" / "armar.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class Huecos(unittest.TestCase):
    """Un hueco es un aviso, no un error."""

    def test_detecta_los_que_faltan(self):
        modulo = _armar()
        self.assertEqual(modulo.huecos([1, 2, 4, 5]), [3])
        self.assertEqual(modulo.huecos([1, 2, 3]), [])
        self.assertEqual(modulo.huecos([2, 3]), [1])

    def test_la_secuencia_contigua_no_copia_nada(self):
        modulo = _armar()
        carpeta = Path(tempfile.mkdtemp(prefix="armar-"))
        try:
            for numero in (1, 2, 3):
                Image.new("RGB", (8, 8)).save(carpeta / f"cuadro_{numero:03d}.png")
            with modulo.secuencia_contigua(carpeta, [1, 2, 3]) as efectiva:
                self.assertEqual(efectiva, carpeta)
        finally:
            shutil.rmtree(carpeta, ignore_errors=True)

    def test_renumera_y_limpia_cuando_hay_huecos(self):
        modulo = _armar()
        carpeta = Path(tempfile.mkdtemp(prefix="armar-"))
        try:
            for numero, color in ((1, (255, 0, 0)), (2, (0, 255, 0)), (4, (0, 0, 255))):
                Image.new("RGB", (8, 8), color).save(
                    carpeta / f"cuadro_{numero:03d}.png")
            with modulo.secuencia_contigua(carpeta, [1, 2, 4]) as efectiva:
                self.assertNotEqual(efectiva, carpeta)
                self.assertEqual(sorted(p.name for p in efectiva.glob("cuadro_*.png")),
                                 ["cuadro_001.png", "cuadro_002.png",
                                  "cuadro_003.png"])
                # El contenido sigue el orden de los números originales.
                with Image.open(efectiva / "cuadro_003.png") as tercera:
                    self.assertEqual(tercera.convert("RGB").getpixel((0, 0)),
                                     (0, 0, 255))
            self.assertFalse(efectiva.exists())
        finally:
            shutil.rmtree(carpeta, ignore_errors=True)


class UltimoDisponible(unittest.TestCase):
    """El check del snapshot es "últimos datos" con N=1."""

    def test_en_snapshot_pide_un_solo_slot(self):
        self.assertEqual(recipes._ultimos({"snapshot": True, "ultimo": True,
                                           "ultimos_n": "24"}), 1)

    def test_sin_el_check_el_snapshot_usa_la_hora_elegida(self):
        self.assertEqual(recipes._ultimos({"snapshot": True, "ultimo": False,
                                           "ultimos_n": "24"}), 0)

    def test_los_ultimos_de_una_serie_no_cambian(self):
        self.assertEqual(recipes._ultimos({"snapshot": False, "ultimos": True,
                                           "ultimos_n": "12"}), 12)

    def test_lo_ofrecen_los_productos_que_ya_resuelven_los_ultimos(self):
        for pid in ("geocolor", "goes_c13", "goes_banda", "goes_sandwich",
                    "goes_firetemp", "goes_truecolor", "himawari"):
            nombres = {spec.name: spec for spec in catalog.get_product(pid).params}
            self.assertIn("ultimo", nombres, pid)
            self.assertEqual(nombres["ultimo"].enabled_when, {"snapshot": True}, pid)
            self.assertFalse(nombres["ultimo"].default, pid)

    def test_el_snapshot_de_paraguay_conserva_su_switch(self):
        nombres = {spec.name for spec in catalog.get_product("snapshot_paraguay").params}
        self.assertIn("ultima", nombres)
        self.assertNotIn("ultimo", nombres)

    def test_la_receta_usa_el_slot_mas_nuevo(self):
        cuando = datetime(2026, 11, 10, 13, 20)
        params = {spec.name: spec.default
                  for spec in catalog.get_product("geocolor").params}
        params.update({"snapshot": True, "ultimo": True, "paraguay": True,
                       "animar": False, "firms": False})
        with mock.patch.object(recipes, "_ultimos_geocolor", return_value=[cuando]):
            plan = recipes.planear("geocolor", params, Path("C:/tmp/work"))
        render = [paso for paso in plan.pasos if paso.kind == "render"][0]
        self.assertEqual(render.args[render.args.index("--desde") + 1],
                         "2026-11-10T13:20")
        self.assertEqual(render.args[render.args.index("--n") + 1], "1")
        # Un snapshot nunca arma video, aunque el slot salga de "los últimos".
        self.assertFalse([paso for paso in plan.pasos if paso.kind == "animate"])


if __name__ == "__main__":
    unittest.main()
