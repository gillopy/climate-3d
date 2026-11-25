"""Rutas e intérprete del pipeline: la configuración vive en un solo lugar.

Estas pruebas fijan el contrato del que depende el contenedor: `CLIMATE3D_DATOS` manda,
el default de Windows no cambia y el intérprete se puede apuntar con `CLIMATE3D_PYTHON`.
El archivo de configuración sólo se lee cuando no se pasa un entorno explícito, así que
la resolución con un mapping es pura y estas pruebas no dependen de la máquina.

    .venv\\Scripts\\python.exe -m unittest discover -s app\\tests
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
for candidato in (RAIZ, RAIZ / "comun"):
    if str(candidato) not in sys.path:
        sys.path.insert(0, str(candidato))

import rutas  # noqa: E402
from app.api.recipes import _python_repo  # noqa: E402


class RaizPortable(unittest.TestCase):
    """Sin configuración, la raíz no puede ser una ruta personal del autor."""

    def test_el_default_vive_en_la_carpeta_del_usuario(self):
        from pathlib import Path

        with mock.patch("comun.rutas.Path.is_dir", return_value=False):
            raiz = rutas.raiz_datos({}, "nt")

        self.assertEqual(raiz, Path.home() / "climate3d" / "datos")
        self.assertNotIn("guill", str(raiz))

    def test_una_instalacion_vieja_conserva_su_ruta(self):
        from pathlib import Path

        with mock.patch("comun.rutas.Path.is_dir", return_value=True):
            raiz = rutas.raiz_datos({}, "nt")

        self.assertEqual(raiz, Path(rutas.RUTA_LEGADA))
        self.assertTrue((raiz / "nisar").as_posix().endswith("nisar"))


class RaizDeDatos(unittest.TestCase):
    def test_la_variable_de_entorno_manda(self) -> None:
        for plataforma in ("nt", "posix"):
            self.assertEqual(
                rutas.raiz_datos({"CLIMATE3D_DATOS": "/mi/datos"}, plataforma),
                Path("/mi/datos"),
            )

    def test_una_variable_vacia_no_pisa_el_default(self) -> None:
        self.assertEqual(
            rutas.raiz_datos({"CLIMATE3D_DATOS": "   "}, "nt"), Path(rutas.RUTA_LEGADA)
        )

    def test_windows_conserva_la_ruta_historica(self) -> None:
        # S8: el flujo que ya funcionaba en Windows no cambia.
        self.assertEqual(
            rutas.raiz_datos({}, "nt"), Path(r"D:\Users\guill\dataset era5")
        )

    def test_fuera_de_windows_apunta_al_volumen_del_contenedor(self) -> None:
        # S5: dentro del contenedor la ruta es siempre /data.
        self.assertEqual(rutas.raiz_datos({}, "posix"), Path("/data"))

    def test_la_variable_real_del_proceso_se_respeta(self) -> None:
        original = os.environ.get("CLIMATE3D_DATOS")
        os.environ["CLIMATE3D_DATOS"] = "/desde/el/proceso"
        try:
            self.assertEqual(rutas.raiz_datos(), Path("/desde/el/proceso"))
        finally:
            if original is None:
                del os.environ["CLIMATE3D_DATOS"]
            else:
                os.environ["CLIMATE3D_DATOS"] = original


class RaizDeNisar(unittest.TestCase):
    def test_sin_configuracion_cuelga_de_los_datos(self) -> None:
        # Una sola carpeta: los .h5 van adentro de la raiz de datos.
        self.assertEqual(
            rutas.raiz_nisar({}, "nt"), Path(rutas.RUTA_LEGADA) / "nisar"
        )

    def test_la_variable_de_nisar_manda(self) -> None:
        for plataforma in ("nt", "posix"):
            self.assertEqual(
                rutas.raiz_nisar({"CLIMATE3D_NISAR": "/mi/nisar"}, plataforma),
                Path("/mi/nisar"),
            )

    def test_fuera_de_windows_queda_con_los_datos(self) -> None:
        self.assertEqual(
            rutas.raiz_nisar({"CLIMATE3D_DATOS": "/data"}, "posix"),
            Path("/data/nisar"),
        )

    def test_una_variable_vacia_no_pisa_el_default(self) -> None:
        self.assertEqual(
            rutas.raiz_nisar({"CLIMATE3D_NISAR": "   "}, "nt"),
            Path(rutas.RUTA_LEGADA) / "nisar",
        )


class CarpetasExtra(unittest.TestCase):
    def test_las_extra_del_entorno_van_primero(self) -> None:
        crudo = os.pathsep.join(["/uno", "/dos"])
        extra = rutas.carpetas_extra({"CLIMATE3D_EXTRA_DIRS": crudo}, "posix")
        self.assertEqual(extra[0], Path("/uno"))
        self.assertEqual(extra[1], Path("/dos"))

    def test_la_raiz_del_repo_siempre_esta_una_sola_vez(self) -> None:
        extra = rutas.carpetas_extra({}, "posix")
        self.assertIn(rutas.RAIZ, extra)
        self.assertEqual(sum(1 for p in extra if p == rutas.RAIZ), 1)

    def test_windows_conserva_el_escritorio_historico(self) -> None:
        self.assertIn(Path(r"D:\Users\guill\Desktop"), rutas.carpetas_extra({}, "nt"))
        self.assertNotIn(Path(r"D:\Users\guill\Desktop"), rutas.carpetas_extra({}, "posix"))


class ConfigPersistida(unittest.TestCase):
    """El archivo que escribe el asistente: precedencia, media y tolerancia a basura."""

    CLAVES = ("CLIMATE3D_CONFIG", "CLIMATE3D_DATOS", "CLIMATE3D_MEDIA", "CLIMATE3D_NISAR")

    def setUp(self) -> None:
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.base = Path(temporal.name)
        self.archivo = self.base / "config.json"
        previo = {clave: os.environ.get(clave) for clave in self.CLAVES}
        for clave in self.CLAVES[1:]:
            os.environ.pop(clave, None)
        os.environ["CLIMATE3D_CONFIG"] = str(self.archivo)
        self.addCleanup(self._restaurar, previo)

    @staticmethod
    def _restaurar(previo: dict[str, str | None]) -> None:
        for clave, valor in previo.items():
            if valor is None:
                os.environ.pop(clave, None)
            else:
                os.environ[clave] = valor

    @staticmethod
    def _legado() -> Path:
        return Path(rutas.RUTA_LEGADA) if os.name == "nt" else Path(rutas.RUTA_CONTENEDOR)

    def test_sin_archivo_cae_al_default_de_la_plataforma(self) -> None:
        self.assertEqual(rutas.raiz_datos(), self._legado())

    def test_el_archivo_manda_cuando_no_hay_entorno(self) -> None:
        datos = self.base / "datos"
        rutas.guardar_config(datos=datos)
        self.assertEqual(rutas.raiz_datos(), datos)

    def test_el_entorno_le_gana_al_archivo(self) -> None:
        rutas.guardar_config(datos=self.base / "datos")
        self.assertEqual(
            rutas.raiz_datos({"CLIMATE3D_DATOS": str(self.base / "otro")}),
            self.base / "otro",
        )

    def test_media_cuelga_de_los_datos(self) -> None:
        # S1: los artefactos y la caché salen de la misma raíz que los datos.
        datos = self.base / "datos"
        rutas.guardar_config(datos=datos)
        self.assertEqual(rutas.raiz_media(), datos / ".media")

    def test_media_se_puede_mover_aparte(self) -> None:
        rutas.guardar_config(datos=self.base / "datos", media=self.base / "media")
        self.assertEqual(rutas.raiz_media(), self.base / "media")

    def test_media_del_entorno_manda(self) -> None:
        rutas.guardar_config(datos=self.base / "datos", media=self.base / "media")
        os.environ["CLIMATE3D_MEDIA"] = str(self.base / "otra")
        self.assertEqual(rutas.raiz_media(), self.base / "otra")

    def test_nisar_se_configura_sin_tocar_los_datos(self) -> None:
        # S5: los .h5 viven en otro disco y la raíz de datos no se entera.
        rutas.guardar_config(datos=self.base / "datos", nisar=self.base / "nisar")
        self.assertEqual(rutas.raiz_nisar(), self.base / "nisar")
        self.assertEqual(rutas.raiz_datos(), self.base / "datos")

    def test_un_archivo_roto_no_rompe_el_arranque(self) -> None:
        # S9: un JSON corrupto cae al default en vez de tumbar la API.
        self.archivo.write_text("{ esto no es json", encoding="utf-8")
        self.assertEqual(rutas.leer_config(), {})
        self.assertEqual(rutas.raiz_datos(), self._legado())
        self.assertEqual(rutas.raiz_media(), self._legado() / ".media")

    def test_guardar_conserva_lo_que_no_se_pregunta(self) -> None:
        rutas.guardar_config(datos=self.base / "datos", nisar=self.base / "nisar")
        rutas.guardar_config(datos=self.base / "datos2")
        leido = rutas.leer_config()
        self.assertEqual(leido["datos"], str(self.base / "datos2"))
        self.assertEqual(leido["nisar"], str(self.base / "nisar"))

    def test_el_resumen_muestra_las_raices_efectivas(self) -> None:
        rutas.guardar_config(datos=self.base / "datos")
        resumen = rutas.resumen()
        self.assertEqual(resumen["datos"], str(self.base / "datos"))
        self.assertEqual(resumen["media"], str(self.base / "datos" / ".media"))
        self.assertEqual(resumen["salidas"], str(self.base / "datos" / "salidas"))
        self.assertTrue(resumen["config"].endswith("config.json"))

    def test_lo_que_guarda_es_json_legible(self) -> None:
        rutas.guardar_config(datos=self.base / "datos")
        crudo = json.loads(self.archivo.read_text(encoding="utf-8"))
        self.assertEqual(crudo, {"datos": str(self.base / "datos")})


class InterpreteDelPipeline(unittest.TestCase):
    def test_la_variable_de_entorno_manda(self) -> None:
        self.assertEqual(
            _python_repo({"CLIMATE3D_PYTHON": "/app/.venv/bin/python"}),
            Path("/app/.venv/bin/python"),
        )

    def test_sin_variable_usa_el_venv_del_repo(self) -> None:
        self.assertIn(".venv", _python_repo({}).parts)


if __name__ == "__main__":
    unittest.main()
