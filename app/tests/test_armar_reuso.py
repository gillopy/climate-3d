"""Pruebas de `animar/armar.py`: orden por instante y videos que no se rehacen.

Fijan las reglas nuevas:

  * los cuadros con nombre de instante (`cuadro_20261122T0040.png`) se ordenan
    cronológicamente sin renumerar la carpeta;
  * los huecos de una serie de instantes se avisan con fecha;
  * un MP4/GIF que ya corresponde a esos cuadros y a ese fps no se vuelve a
    codificar (ffmpeg tarda minutos en una animación de 200 MB).

    .venv\\Scripts\\python.exe -m unittest discover -s app\\tests
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
for ruta in (RAIZ, RAIZ / "comun"):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))

from PIL import Image  # noqa: E402


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


def _png(ruta: Path, color: tuple[int, int, int] = (10, 20, 30)) -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), color).save(ruta)
    return ruta


def _cuadro(hh: int, mm: int) -> str:
    return f"cuadro_20261122T{hh:02d}{mm:02d}.png"


class ArmarConInstantes(unittest.TestCase):
    """`armar.py` entiende cuadros con nombre de instante."""

    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp(prefix="armar-inst-"))
        self.addCleanup(shutil.rmtree, self.carpeta, ignore_errors=True)

    def test_ordena_por_instante(self):
        modulo = _armar()
        for nombre in (_cuadro(0, 20), _cuadro(0, 0), _cuadro(0, 10)):
            _png(self.carpeta / nombre)
        self.assertEqual(
            [p.name for p in modulo.cuadros_ordenados(self.carpeta)],
            [_cuadro(0, 0), _cuadro(0, 10), _cuadro(0, 20)],
        )

    def test_sigue_entendiendo_los_numerados(self):
        modulo = _armar()
        for numero in (2, 1, 3):
            _png(self.carpeta / f"cuadro_{numero:03d}.png")
        self.assertEqual(
            [p.name for p in modulo.cuadros_ordenados(self.carpeta)],
            ["cuadro_001.png", "cuadro_002.png", "cuadro_003.png"],
        )

    def test_avisa_los_huecos_de_una_serie_de_instantes(self):
        modulo = _armar()
        for nombre in (_cuadro(0, 0), _cuadro(0, 10), _cuadro(0, 30)):
            _png(self.carpeta / nombre)
        self.assertEqual(
            modulo.huecos_temporales(modulo.cuadros_ordenados(self.carpeta)),
            [__import__("datetime").datetime(2026, 11, 22, 0, 20)],
        )


class VideoAlDia(unittest.TestCase):
    """`armar.py` no re-encodea lo que ya está armado."""

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)
        self.frames = self.raiz / "frames"
        for minuto in (0, 10, 20):
            _png(self.frames / _cuadro(0, minuto))
        self.salida = self.raiz / "animacion.mp4"

    def _correr(self, modulo, fps="12", extra=()):
        with mock.patch.object(modulo, "armar_mp4", side_effect=self._mp4) as llamado:
            codigo = modulo.main([
                "--frames", str(self.frames), "--salida", str(self.salida),
                "--fps", fps, *extra,
            ])
        return codigo, llamado

    def _mp4(self, carpeta, destino, fps):
        Path(destino).write_bytes(b"video")
        return Path(destino)

    def test_la_primera_vez_encodea(self):
        _, llamado = self._correr(_armar())
        self.assertEqual(llamado.call_count, 1)

    def test_la_segunda_vez_no_encodea(self):
        modulo = _armar()
        self._correr(modulo)
        _, llamado = self._correr(modulo)
        self.assertEqual(llamado.call_count, 0)

    def test_cambiar_los_fps_vuelve_a_encodear(self):
        modulo = _armar()
        self._correr(modulo)
        _, llamado = self._correr(modulo, fps="8")
        self.assertEqual(llamado.call_count, 1)

    def test_un_cuadro_nuevo_vuelve_a_encodear(self):
        modulo = _armar()
        self._correr(modulo)
        _png(self.frames / _cuadro(0, 30))
        _, llamado = self._correr(modulo)
        self.assertEqual(llamado.call_count, 1)

    def test_forzar_rehace_igual(self):
        modulo = _armar()
        self._correr(modulo)
        _, llamado = self._correr(modulo, extra=["--forzar"])
        self.assertEqual(llamado.call_count, 1)
