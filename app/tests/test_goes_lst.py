"""Offline tests for the GOES-19 ABI L2 LST 2 km full disk slot resolver.

Every test injects the S3 listing, so none touches the network:

  * `instante` parses the real granule name (14 digits = YYYYJJJHHMMSS + tenths);
  * `prefijo` builds the hourly bucket prefix;
  * `clave_de` finds the granule of an hour and rejects a missing one;
  * `ultimos_slots` walks back hour by hour and returns the newest N in order;
  * `ventana_ultimos` / `ventana_ultimas` build the `[desde, hasta)` range.

    .venv\\Scripts\\python.exe -m unittest app.tests.test_goes_lst -v
"""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
for ruta in (RAIZ, RAIZ / "comun"):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))

from goes_lst import (  # noqa: E402
    PASO,
    PREFIJO,
    clave_de,
    instante,
    prefijo,
    ultimos_slots,
    ventana_ultimas,
    ventana_ultimos,
)

# Key verified against the live bucket on 2026-11-13.
REAL = ("ABI-L2-LST2KMF/2026/317/22/"
        "OR_ABI-L2-LST2KMF-M6_G19_s20263172200207_e20263172209515_c20263172214319.nc")


def _clave(hora: datetime, sat: str = "G19") -> str:
    """S3 key with NOAA's real LST granule format for the given hour."""
    inicio = f"{hora:%Y%j%H}00207"
    cuerpo = f"{hora:%Y%j%H}"
    return (f"ABI-L2-LST2KMF/{hora.year}/{int(hora.strftime('%j')):03d}/{hora.hour:02d}/"
            f"OR_ABI-L2-LST2KMF-M6_{sat}_s{inicio}"
            f"_e{cuerpo}09515_c{cuerpo}214319.nc")


def _listado(claves: list[str]):
    """Stand-in for `listar_hora`: filters by hour prefix, never the network."""
    return lambda sat, hora, timeout=60: [
        c for c in claves if f"/{hora.year}/{int(hora.strftime('%j')):03d}/{hora.hour:02d}/" in c
    ]


class Parseo(unittest.TestCase):
    """Constants and the real granule name."""

    def test_constantes(self):
        self.assertEqual(PREFIJO, "ABI-L2-LST2KMF")
        self.assertEqual(PASO, 60)

    def test_nombre_real(self):
        # s20263172200207 -> day 317 of 2026, 22:00:20.7 UTC; the slot is 22:00.
        self.assertEqual(instante(REAL), datetime(2026, 11, 13, 22, 0))

    def test_acepta_solo_el_nombre_sin_prefijo(self):
        self.assertEqual(instante(REAL.rsplit("/", 1)[-1]),
                         datetime(2026, 11, 13, 22, 0))

    def test_nombre_ajeno_devuelve_none(self):
        cmip = ("ABI-L2-CMIPF/2026/317/22/"
                "OR_ABI-L2-CMIPF-M6C13_G19_s20263172200207_"
                "e20263172209515_c20263172214319.nc")
        self.assertIsNone(instante(cmip))
        self.assertIsNone(instante("no-es-un-granulo.nc"))


class Prefijo(unittest.TestCase):
    """The hourly bucket prefix, day of year included."""

    def test_prefijo_de_la_hora(self):
        self.assertEqual(prefijo(datetime(2026, 11, 13, 22)),
                         "ABI-L2-LST2KMF/2026/317/22/")

    def test_prefijo_ignora_los_minutos(self):
        self.assertEqual(prefijo(datetime(2026, 11, 13, 22, 37, 45)),
                         "ABI-L2-LST2KMF/2026/317/22/")

    def test_prefijo_del_primer_dia_del_anio(self):
        self.assertEqual(prefijo(datetime(2026, 1, 1, 5)),
                         "ABI-L2-LST2KMF/2026/001/05/")


class ClaveDe(unittest.TestCase):
    """`clave_de` picks the granule of one hour and satellite."""

    CLAVES = [
        _clave(datetime(2026, 11, 13, 21)),
        _clave(datetime(2026, 11, 13, 22)),
        _clave(datetime(2026, 11, 13, 22), sat="G18"),
    ]

    def _clave_de(self, sat: str, t: datetime) -> str:
        with mock.patch("goes_lst._listar_s3", side_effect=_listado(self.CLAVES)):
            return clave_de(sat, t)

    def test_encuentra_el_granulo_de_la_hora(self):
        self.assertEqual(self._clave_de("G19", datetime(2026, 11, 13, 22)),
                         self.CLAVES[1])

    def test_ignora_el_mismo_slot_de_otro_satelite(self):
        self.assertEqual(self._clave_de("G18", datetime(2026, 11, 13, 22)),
                         self.CLAVES[2])

    def test_cualquier_minuto_cae_en_la_hora(self):
        self.assertEqual(self._clave_de("G19", datetime(2026, 11, 13, 22, 37)),
                         self.CLAVES[1])

    def test_hora_sin_archivo_levanta_lookuperror(self):
        with mock.patch("goes_lst._listar_s3", side_effect=_listado(self.CLAVES)):
            with self.assertRaises(LookupError):
                clave_de("G19", datetime(2026, 11, 13, 23))


class UltimosSlots(unittest.TestCase):
    """`ultimos_slots` returns the newest published hours, oldest first."""

    CLAVES = [
        _clave(datetime(2026, 11, 13, 17)),
        _clave(datetime(2026, 11, 13, 18)),
        _clave(datetime(2026, 11, 13, 19)),
        _clave(datetime(2026, 11, 13, 20)),
        _clave(datetime(2026, 11, 13, 21)),
        _clave(datetime(2026, 11, 13, 22)),
        _clave(datetime(2026, 11, 13, 22), sat="G18"),  # another satellite
        REAL,                                          # duplicate of 22:00
    ]
    AHORA = datetime(2026, 11, 13, 22, 41)

    def _slots(self, n: int, claves=None, ahora: datetime = AHORA) -> list[datetime]:
        return ultimos_slots("G19", n, ahora=ahora,
                             listar=_listado(self.CLAVES if claves is None else claves))

    def test_devuelve_los_ultimos_n_en_orden_cronologico(self):
        self.assertEqual(
            self._slots(3),
            [datetime(2026, 11, 13, 20),
             datetime(2026, 11, 13, 21),
             datetime(2026, 11, 13, 22)],
        )

    def test_si_la_hora_actual_no_salio_arranca_antes(self):
        # At 22:41 the 23:00 granule does not exist yet: the newest is 22:00.
        self.assertEqual(self._slots(1)[-1], datetime(2026, 11, 13, 22))

    def test_salta_las_horas_sin_archivo(self):
        claves = [_clave(datetime(2026, 11, 13, 19)),
                  _clave(datetime(2026, 11, 13, 21))]
        self.assertEqual(self._slots(2, claves=claves),
                         [datetime(2026, 11, 13, 19),
                          datetime(2026, 11, 13, 21)])

    def test_sin_archivos_devuelve_vacio(self):
        self.assertEqual(self._slots(5, claves=[]), [])

    def test_n_cero_devuelve_vacio(self):
        self.assertEqual(self._slots(0), [])

    def test_filtra_por_satelite(self):
        claves = [_clave(datetime(2026, 11, 13, 21)),
                  _clave(datetime(2026, 11, 13, 22), sat="G18")]
        self.assertEqual(self._slots(1, claves=claves),
                         [datetime(2026, 11, 13, 21)])

    def test_el_listado_inyectado_evita_la_red(self):
        llamadas: list[datetime] = []

        def listar(_sat, hora, timeout=60):
            llamadas.append(hora)
            return []

        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            self.assertEqual(ultimos_slots("G19", 1, ahora=self.AHORA, listar=listar), [])
        self.assertEqual(llamadas[0], datetime(2026, 11, 13, 22))


class Ventanas(unittest.TestCase):
    """`ventana_ultimos` / `ventana_ultimas` build the CLI range."""

    CLAVES = [_clave(datetime(2026, 11, 13, 20)),
              _clave(datetime(2026, 11, 13, 21)),
              _clave(datetime(2026, 11, 13, 22))]
    AHORA = datetime(2026, 11, 13, 22, 41)

    def test_ventana_ultimos_termina_un_paso_despues_del_nuevo(self):
        desde, hasta = ventana_ultimos(3, "G19", ahora=self.AHORA,
                                       listar=_listado(self.CLAVES))
        self.assertEqual(desde, datetime(2026, 11, 13, 20))
        self.assertEqual(hasta, datetime(2026, 11, 13, 23))

    def test_ventana_ultimas_cubre_24_horas(self):
        desde, hasta = ventana_ultimas(24, "G19", ahora=self.AHORA,
                                       listar=_listado(self.CLAVES))
        self.assertEqual(hasta, datetime(2026, 11, 13, 23))
        self.assertEqual(hasta - desde, timedelta(hours=24))
        self.assertEqual((hasta - desde) / timedelta(minutes=PASO), 24)

    def test_ventana_sin_datos_levanta_lookuperror(self):
        with self.assertRaises(LookupError):
            ventana_ultimos(1, "G19", ahora=self.AHORA, listar=lambda *a, **k: [])


if __name__ == "__main__":
    unittest.main()
