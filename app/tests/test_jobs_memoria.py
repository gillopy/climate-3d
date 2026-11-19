"""Regresion: un paso que muere por falta de memoria no puede culpar a la fecha.

La maquina del usuario tiene 8 GB de RAM y el archivo de paginacion en ``C:``,
que esta lleno: Windows no lo puede agrandar, el commit se agota y cualquier paso
muere. ``eccodes`` lo muestra como ``cannot open '/MEMFS/definitions/boot.def'``
(no puede montar sus definiciones) y el job lo reportaba como "puede que esa
fecha no exista en la fuente". El job tiene que decir la verdad y, antes de
largar un paso, darle a la maquina la chance de liberar memoria.

    .venv\\Scripts\\python.exe -m unittest app.tests.test_jobs_memoria
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

try:
    from app.api import jobs
    from app.api.schemas import LogLine
except ImportError:  # pragma: no cover - faltan dependencias del venv de la app
    jobs = None


def _trabajo(media: Path, lineas: list[str] | None = None) -> "jobs.Job":
    trabajo = jobs.Job(
        id="prueba",
        product_id="precipitacion_ecmwf",
        product_name="Precipitacion",
        params={},
        mode="real",
        dir=media / "work",
    )
    for texto in lineas or []:
        trabajo.logs.append(LogLine(at="2026-11-19T14:55:24", level="info", text=texto))
    return trabajo


# El log real del job d462c6a69aa0: el paso de consolidacion de la descarga.
SALIDA_ECCODES = [
    "49 pasos listos en 11s (0 reutilizados). Consolidando...",
    "ECCODES ERROR   :  Parser include: cannot open: "
    "'/MEMFS/definitions/boot.def' (No such file or directory)",
    "ECCODES ERROR   :  grib_handle_create: Cannot create handle, no definitions found",
    "gribapi.errors.DecodingError: Decoding invalid",
]

# Lo que tira numpy cuando el commit ya no da ni para 8 MB.
SALIDA_NUMPY = [
    "  File \"descargar/precipitacion_ecmwf.py\", line 397, in _decodificar_gid",
    "numpy._core._exceptions._ArrayMemoryError: Unable to allocate 7.92 MiB for an "
    "array with shape (1038240,) and data type float64",
]

# Un fallo de datos de verdad: no tiene ninguna firma de memoria.
SALIDA_DATOS = [
    "paso 120h  ERROR: 404 Client Error: Not Found",
    "Faltan 4 pasos: 120h, 123h, 126h, 129h",
]


@unittest.skipIf(jobs is None, "la API necesita las dependencias del venv de la app")
class SenalesDeMemoria(unittest.TestCase):
    def test_reconoce_el_error_de_eccodes_por_memfs(self):
        self.assertTrue(jobs._sin_memoria(SALIDA_ECCODES))

    def test_reconoce_el_error_de_numpy(self):
        self.assertTrue(jobs._sin_memoria(SALIDA_NUMPY))

    def test_reconoce_la_paginacion_llena(self):
        salida = [
            "DLL load failed while importing _eccodes: El archivo de paginación "
            "es demasiado pequeño para completar la operación."
        ]
        self.assertTrue(jobs._sin_memoria(salida))

    def test_no_marca_un_fallo_de_datos(self):
        self.assertFalse(jobs._sin_memoria(SALIDA_DATOS))


@unittest.skipIf(jobs is None, "la API necesita las dependencias del venv de la app")
class MensajeDeFallo(unittest.TestCase):
    def setUp(self):
        self._temporal = tempfile.TemporaryDirectory()
        self.media = Path(self._temporal.name)
        self.paso = SimpleNamespace(script="cuadros/cuadros_precipitacion.py")

    def tearDown(self):
        self._temporal.cleanup()

    def test_por_memoria_lo_dice_y_no_culpa_a_la_fecha(self):
        trabajo = _trabajo(self.media, SALIDA_ECCODES)
        with mock.patch.object(jobs, "_commit_libre_mb", return_value=540), mock.patch.object(
            jobs, "_disco_sistema_libre_gb", return_value=0.3
        ):
            texto = jobs._mensaje_de_fallo(trabajo, self.paso, 1, descargado=True)

        self.assertIn("falta de memoria", texto)
        self.assertIn("540 MB", texto)
        self.assertIn("archivo de paginacion", texto)
        self.assertNotIn("esa fecha no exista", texto)

    def test_sin_firma_conserva_la_pista_de_la_fecha(self):
        trabajo = _trabajo(self.media, SALIDA_DATOS)
        texto = jobs._mensaje_de_fallo(trabajo, self.paso, 1, descargado=True)
        self.assertIn("esa fecha no exista", texto)

    def test_sin_descarga_previa_no_habla_de_fechas(self):
        trabajo = _trabajo(self.media, SALIDA_DATOS)
        texto = jobs._mensaje_de_fallo(trabajo, self.paso, 1, descargado=False)
        self.assertNotIn("esa fecha no exista", texto)


@unittest.skipIf(jobs is None, "la API necesita las dependencias del venv de la app")
class DiagnosticoDeMemoria(unittest.TestCase):
    def test_suma_el_disco_del_sistema_cuando_esta_lleno(self):
        with mock.patch.object(jobs, "_commit_libre_mb", return_value=312), mock.patch.object(
            jobs, "_disco_sistema_libre_gb", return_value=0.3
        ):
            texto = jobs._diagnostico_memoria()

        self.assertIn("312 MB", texto)
        self.assertIn("0.3 GB", texto)
        self.assertIn("paginacion", texto)
        self.assertIn("se reusan", texto)

    def test_con_disco_sano_no_habla_del_disco(self):
        with mock.patch.object(jobs, "_commit_libre_mb", return_value=900), mock.patch.object(
            jobs, "_disco_sistema_libre_gb", return_value=120.0
        ):
            texto = jobs._diagnostico_memoria()

        self.assertIn("900 MB", texto)
        self.assertNotIn("disco del sistema", texto)


@unittest.skipIf(jobs is None, "la API necesita las dependencias del venv de la app")
class EsperaDeMemoria(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._temporal = tempfile.TemporaryDirectory()
        self.media = Path(self._temporal.name)
        self.gestor = jobs.JobManager(self.media)
        self.trabajo = _trabajo(self.media)

    def tearDown(self):
        self._temporal.cleanup()

    async def test_sin_apuro_no_espera(self):
        with mock.patch.object(jobs, "_commit_libre_mb", return_value=2000):
            await self.gestor._esperar_memoria(self.trabajo, "[1/3] descarga")

        self.assertEqual([linea.text for linea in self.trabajo.logs], [])

    async def test_espera_y_sigue_cuando_se_libera(self):
        with mock.patch.object(
            jobs, "_commit_libre_mb", side_effect=[100, 900]
        ), mock.patch.object(jobs, "_SONDEO_MEMORIA_S", 0.0), mock.patch.object(
            jobs, "_ESPERA_MEMORIA_S", 30.0
        ):
            await self.gestor._esperar_memoria(self.trabajo, "[2/3] renderizado")

        textos = [linea.text for linea in self.trabajo.logs]
        self.assertTrue(any("queda poca memoria (100 MB" in t for t in textos), textos)
        self.assertTrue(
            any("hay 900 MB otra vez: sigo con [2/3] renderizado" in t for t in textos),
            textos,
        )

    async def test_si_nunca_se_libera_larga_igual(self):
        with mock.patch.object(jobs, "_commit_libre_mb", return_value=100), mock.patch.object(
            jobs, "_ESPERA_MEMORIA_S", 0.0
        ):
            await self.gestor._esperar_memoria(self.trabajo, "[3/3] animacion")

        textos = [linea.text for linea in self.trabajo.logs]
        self.assertTrue(
            any("sigue con 100 MB: largo [3/3] animacion igual" in t for t in textos),
            textos,
        )


if __name__ == "__main__":
    unittest.main()
