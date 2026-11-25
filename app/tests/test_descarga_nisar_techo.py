"""La descarga de un gránulo NISAR no puede escribir sin techo.

S1 (auditoría): `bajar()` volcaba `iter_content` al `.parcial` sin máximo; el único
número era un piso de 10 MB. Un servidor que responde con un cuerpo enorme llenaba
el volumen de datos del operador.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from descargar import nisar  # noqa: E402


class _Respuesta:
    """Respuesta mínima: alcanza para el bucle de escritura, sin red."""

    def __init__(self, bloques: list[bytes], status: int = 200) -> None:
        self.status_code = status
        self.headers = {"Content-Type": "application/octet-stream"}
        self._bloques = bloques

    def __enter__(self) -> "_Respuesta":
        return self

    def __exit__(self, *_excepcion: object) -> bool:
        return False

    def iter_content(self, tamano: int):
        for bloque in self._bloques:
            yield bloque


class _Sesion:
    def __init__(self, respuesta: _Respuesta) -> None:
        self._respuesta = respuesta

    def get(self, *_args: object, **_kwargs: object) -> _Respuesta:
        return self._respuesta


class TechoDeDescarga(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.carpeta = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _bajar(self, bloques: list[bytes], *, max_bytes: int, min_bytes: int) -> Path:
        destino = self.carpeta / "coleccion" / "granulo.h5"
        with mock.patch.object(nisar, "MAX_BYTES", max_bytes), \
                mock.patch.object(nisar, "MIN_BYTES", min_bytes):
            nisar.bajar(_Sesion(_Respuesta(bloques)), "https://x/g.h5", destino)
        return destino

    def test_corta_y_borra_el_parcial_al_pasarse_del_techo(self) -> None:
        bloques = [b"x" * 8, b"x" * 8, b"x" * 8]

        with self.assertRaises(SystemExit) as caso:
            self._bajar(bloques, max_bytes=10, min_bytes=1)

        self.assertIn("techo", str(caso.exception))
        parcial = self.carpeta / "coleccion" / "granulo.h5.parcial"
        self.assertFalse(parcial.exists(), "el .parcial tiene que borrarse al cancelar")
        self.assertFalse((self.carpeta / "coleccion" / "granulo.h5").exists())

    def test_una_descarga_dentro_del_techo_se_publica(self) -> None:
        destino = self._bajar([b"x" * 8, b"x" * 8], max_bytes=10_000, min_bytes=1)

        self.assertTrue(destino.is_file())
        self.assertEqual(destino.stat().st_size, 16)


if __name__ == "__main__":
    unittest.main()
