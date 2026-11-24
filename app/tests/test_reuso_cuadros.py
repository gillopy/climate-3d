"""Pruebas del almacén de cuadros ya renderizados.

Fijan las reglas nuevas:

  * un cuadro se identifica por su instante UTC, no por su posición en la serie;
  * el almacén se consulta antes de renderizar y lo que ya está se enlaza (no se
    copia) en la carpeta de trabajo;
  * la carpeta es por aspecto (el sello del renderer), nunca una sola para todo;
  * la receta pasa el almacén al renderer y la carpeta del job dice qué producto es.

    .venv\\Scripts\\python.exe -m unittest discover -s app\\tests
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
for ruta in (RAIZ, RAIZ / "comun"):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))

from PIL import Image  # noqa: E402

import reuso_cuadros  # noqa: E402


def _png(ruta: Path, color: tuple[int, int, int] = (10, 20, 30)) -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), color).save(ruta)
    return ruta


class NombrePorInstante(unittest.TestCase):
    """El nombre del cuadro es su instante UTC."""

    def test_el_nombre_lleva_el_instante(self):
        self.assertEqual(
            reuso_cuadros.nombre_cuadro(datetime(2026, 11, 22, 0, 40)),
            "cuadro_20261122T0040.png",
        )

    def test_el_instante_se_puede_leer_de_vuelta(self):
        instante = datetime(2026, 11, 24, 23, 50)
        self.assertEqual(
            reuso_cuadros.instante_de(reuso_cuadros.nombre_cuadro(instante)),
            instante,
        )

    def test_un_nombre_viejo_no_es_un_instante(self):
        self.assertIsNone(reuso_cuadros.instante_de("cuadro_001.png"))
        self.assertFalse(reuso_cuadros.es_de_instante("cuadro_001.png"))

    def test_ordenar_por_nombre_es_ordenar_por_tiempo(self):
        instantes = [
            datetime(2026, 11, 22, 23, 50),
            datetime(2026, 11, 23, 0, 0),
            datetime(2026, 11, 22, 0, 0),
        ]
        nombres = sorted(reuso_cuadros.nombre_cuadro(t) for t in instantes)
        self.assertEqual(
            [reuso_cuadros.instante_de(n) for n in nombres],
            sorted(instantes),
        )


class AlmacenCompartido(unittest.TestCase):
    """Lo que ya está en el almacén no se vuelve a renderizar."""

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)
        self.almacen = self.raiz / "almacen"
        self.almacen.mkdir()

    def test_separa_lo_que_ya_esta_de_lo_que_falta(self):
        listo = datetime(2026, 11, 22, 0, 0)
        falta = datetime(2026, 11, 22, 0, 10)
        _png(self.almacen / reuso_cuadros.nombre_cuadro(listo))
        reusables, pendientes = reuso_cuadros.plan_de_reuso(
            self.almacen, [listo, falta])
        self.assertEqual(reusables, [listo])
        self.assertEqual(pendientes, [falta])

    def test_un_almacen_vacio_pide_todo(self):
        slots = [datetime(2026, 11, 22, 0, 0), datetime(2026, 11, 22, 0, 10)]
        self.assertEqual(reuso_cuadros.plan_de_reuso(self.almacen, slots),
                         ([], slots))

    def test_enlaza_sin_copiar(self):
        origen = _png(self.almacen / "cuadro_20261122T0000.png")
        destino = self.raiz / "work" / "frames" / origen.name
        reuso_cuadros.enlazar(origen, destino)
        self.assertTrue(destino.exists())
        self.assertEqual(os.stat(origen).st_ino, os.stat(destino).st_ino)

    def test_si_no_se_puede_enlazar_copia(self):
        origen = _png(self.almacen / "cuadro_20261122T0000.png")
        destino = self.raiz / "work" / "frames" / origen.name
        with mock.patch.object(reuso_cuadros.os, "link", side_effect=OSError("otro volumen")):
            reuso_cuadros.enlazar(origen, destino)
        self.assertTrue(destino.exists())
        self.assertNotEqual(os.stat(origen).st_ino, os.stat(destino).st_ino)

    def test_enlazar_dos_veces_no_falla(self):
        origen = _png(self.almacen / "cuadro_20261122T0000.png")
        destino = self.raiz / "work" / "frames" / origen.name
        reuso_cuadros.enlazar(origen, destino)
        reuso_cuadros.enlazar(origen, destino)
        self.assertTrue(destino.exists())

    def test_el_aspecto_es_la_carpeta_del_almacen(self):
        # Dos aspectos nunca comparten carpeta: el sello ya es la huella.
        self.assertNotEqual(
            reuso_cuadros.carpeta_almacen(self.raiz, "seal_a"),
            reuso_cuadros.carpeta_almacen(self.raiz, "seal_b"),
        )
        self.assertEqual(
            reuso_cuadros.carpeta_almacen(self.raiz, "seal_a").name,
            "seal_a",
        )
