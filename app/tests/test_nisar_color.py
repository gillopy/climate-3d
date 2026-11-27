"""Color real antes/después del cuadro ROI: cercanía, escala común y receta.

Fija el contrato que el visor pide con el check «Color real (antes/después)»:
la escena óptica más cercana a cada fecha, dos PNG separados y una sola escala
para que las dos fechas se puedan comparar. Sin red: los items son dobles.

    .venv\\Scripts\\python.exe -m unittest app.tests.test_nisar_color -q
"""
from __future__ import annotations

import re
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
for candidato in (RAIZ, RAIZ / "comun"):
    if str(candidato) not in sys.path:
        sys.path.insert(0, str(candidato))

import optico  # noqa: E402

try:
    import hls
    import rutas
    import sentinel2
    from app.api.recipes import planear
except ImportError:  # pragma: no cover - faltan dependencias del venv de la app
    hls = None
    sentinel2 = None
    rutas = None
    planear = None

GRANULO = "NISAR_L2_PR_GCOV_034_082_D_101_2005_DHDH_A_20261029T214921_20261029T214955_P05036_N_F_J_001"
#: El visor reconoce el barrido SAR por estos sufijos: los nuevos no pueden caer ahí.
RE_ANTES = re.compile(r"_antes\.png$", re.IGNORECASE)
RE_DESPUES = re.compile(r"_despues\.png$", re.IGNORECASE)


class _Item:
    """Doble mínimo de un item STAC: fecha, id y nubosidad."""

    def __init__(self, ident: str, momento: datetime, nubes: float):
        self.id = ident
        self.datetime = momento
        self.properties = {"eo:cloud_cover": nubes}


def _capas(base: float, paso: float) -> dict[str, np.ndarray]:
    valores = np.arange(100, dtype=np.float32) * paso + base
    capa = valores.reshape(10, 10)
    return {"R": capa, "G": capa * 0.9, "B": capa * 0.8}


class OrdenPorCercania(unittest.TestCase):
    def test_la_fecha_mas_cercana_gana_aunque_tenga_mas_nubes(self):
        centro = datetime(2026, 7, 1)
        lejano = _Item("lejano", centro - timedelta(days=12), 0.0)
        cercano = _Item("cercano", centro - timedelta(days=1), 35.0)

        ordenados = optico.ordenar_por_cercania([lejano, cercano], centro.date())

        self.assertEqual([item.id for item in ordenados], ["cercano", "lejano"])

    def test_empate_de_dia_desempata_por_nubes(self):
        centro = datetime(2026, 7, 1, 12)
        nublado = _Item("nublado", datetime(2026, 7, 1, 9), 60.0)
        limpio = _Item("limpio", datetime(2026, 7, 1, 15), 5.0)

        ordenados = optico.ordenar_por_cercania([nublado, limpio], centro)

        self.assertEqual(ordenados[0].id, "limpio")

    def test_item_sin_fecha_va_al_final(self):
        centro = datetime(2026, 7, 1)
        sin_fecha = _Item("sin-fecha", None, 0.0)
        con_fecha = _Item("con-fecha", centro + timedelta(days=3), 80.0)

        ordenados = optico.ordenar_por_cercania([sin_fecha, con_fecha], centro)

        self.assertEqual(ordenados[0].id, "con-fecha")

    def test_item_stac_en_utc_contra_fecha_naive_no_revienta(self):
        # Regresión: pystac entrega datetime con tzinfo y el render pide un date
        # naive. Restarlos directo rompe con "offset-naive and offset-aware".
        from datetime import timezone

        centro = datetime(2026, 7, 1)
        en_utc = _Item("utc", datetime(2026, 7, 2, 10, tzinfo=timezone.utc), 10.0)

        ordenados = optico.ordenar_por_cercania([en_utc], centro)

        self.assertEqual(ordenados[0].id, "utc")


class EscalaComun(unittest.TestCase):
    def test_una_sola_escala_cubre_las_dos_fechas(self):
        previo = _capas(0.10, 0.004)  # 0,10 a 0,50
        posterior = _capas(0.50, 0.005)  # 0,50 a 1,00

        escala = optico.escala_comun([previo, posterior])

        self.assertIsNotNone(escala)
        lo, hi = escala
        self.assertLess(lo, 0.20)
        self.assertGreater(hi, 0.90)

    def test_misma_reflectancia_mismo_valor_en_las_dos_fechas(self):
        previo = _capas(0.10, 0.004)
        posterior = _capas(0.10, 0.004)
        lo, hi = optico.escala_comun([previo, posterior])

        rgb_previo = optico.estirar_rgb(previo, lo, hi)
        rgb_posterior = optico.estirar_rgb(posterior, lo, hi)

        self.assertEqual(rgb_previo.shape, (10, 10, 3))
        np.testing.assert_array_equal(rgb_previo, rgb_posterior)

    def test_sin_pixeles_no_hay_escala(self):
        vacio = {"R": np.full((2, 2), np.nan), "G": np.full((2, 2), np.nan),
                 "B": np.full((2, 2), np.nan)}

        self.assertIsNone(optico.escala_comun([vacio]))


@unittest.skipIf(sentinel2 is None, "faltan dependencias del venv de la app")
class EscalaDeSentinel(unittest.TestCase):
    def _datos(self, scl: float):
        return {
            "B04": np.full((2, 2), 2000.0, dtype=np.float32),
            "B03": np.full((2, 2), 1500.0, dtype=np.float32),
            "B02": np.full((2, 2), 1000.0, dtype=np.float32),
            "SCL": np.full((2, 2), scl, dtype=np.float32),
        }

    def test_l2a_se_normaliza_a_reflectancia(self):
        # L2A publica DN x10000 y HLS viene en 0..1: sin normalizar, una fecha
        # de cada fuente compartiria una escala donde una de las dos es negra.
        capas = sentinel2._calcular_color(self._datos(4))

        self.assertAlmostEqual(float(capas["R"][0, 0]), 0.20, places=4)
        self.assertAlmostEqual(float(capas["G"][0, 0]), 0.15, places=4)
        self.assertAlmostEqual(float(capas["B"][0, 0]), 0.10, places=4)

    def test_la_mascara_scl_sigue_descartando_nubes(self):
        capas = sentinel2._calcular_color(self._datos(9))

        self.assertTrue(np.isnan(capas["R"]).all())


class ContratoDeNombres(unittest.TestCase):
    def test_los_png_de_color_no_secuestran_el_barrido_sar(self):
        for nombre in ("nisar_color_2400_previo.png", "nisar_color_2400_posterior.png"):
            self.assertIsNone(RE_ANTES.search(nombre))
            self.assertIsNone(RE_DESPUES.search(nombre))

    def test_el_barrido_sigue_reconociendo_sus_paneles(self):
        self.assertIsNotNone(RE_ANTES.search("nisar_cambio_comparar_2400_antes.png"))
        self.assertIsNotNone(RE_DESPUES.search("nisar_cambio_comparar_2400_despues.png"))


@unittest.skipIf(hls is None, "faltan dependencias del venv de la app")
class BandasDeColorHls(unittest.TestCase):
    def test_l30_y_s30_traen_azul_verde_rojo(self):
        for sensor in ("l30", "s30"):
            bandas = hls.BANDAS_COLOR[sensor]
            for banda in ("B02", "B03", "B04", "Fmask"):
                self.assertIn(banda, bandas)

    def test_los_dos_proveedores_exponen_color_en_reflectancia(self):
        # El render pide reflectancia (no RGB ya estirado): las dos fuentes
        # tienen que ofrecer la misma función o la escala común no es posible.
        self.assertTrue(hasattr(sentinel2, "componer_color_reflectancia"))
        self.assertTrue(hasattr(hls, "componer_color_reflectancia"))


@unittest.skipIf(planear is None, "faltan dependencias del venv de la app")
class RecetaColorReal(unittest.TestCase):
    def _plan(self, carpeta: Path, **extra):
        params = {
            "producto": "cambio",
            "granulo": GRANULO,
            "url": f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{GRANULO}.h5",
            "coleccion": "NISAR_L2_GCOV_V1",
            "antes_granulo": "NISAR_L2_PR_GCOV_033_082_D_101_2005_DHDH_A_20261017T214920_20261017T214955_P05023_N_F_J_001",
            "antes_url": "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_GCOV_V1/ANTES/ANTES.h5",
            "antes_coleccion": "NISAR_L2_GCOV_V1",
            "bbox": "-55.6,-24.5,-55.2,-23.9",
            "px": 2400,
            "modo_cambio": "comparar",
            "umbral": 2.5,
            "hv_min": -15.5,
            **extra,
        }
        with patch.object(rutas, "raiz_nisar", return_value=carpeta):
            return planear("nisar_render", params, carpeta)

    def test_sin_el_check_no_pide_color(self):
        with tempfile.TemporaryDirectory() as carpeta:
            plan = self._plan(Path(carpeta))

        render = [paso for paso in plan.pasos if paso.script == "prototipos/nisar_cambio.py"][0]
        self.assertNotIn("--color-out", render.args)

    def test_con_el_check_pide_dos_png_de_color(self):
        with tempfile.TemporaryDirectory() as carpeta:
            plan = self._plan(Path(carpeta), color_real=True)

        render = [paso for paso in plan.pasos if paso.script == "prototipos/nisar_cambio.py"][0]
        self.assertIn("--color-out", render.args)
        base = render.args[render.args.index("--color-out") + 1]
        self.assertTrue(base.endswith("nisar_color_2400"), base)
        self.assertNotIn("_antes", base)

    def test_el_color_no_depende_de_la_confirmacion_ndvi(self):
        with tempfile.TemporaryDirectory() as carpeta:
            plan = self._plan(Path(carpeta), color_real=True, verificar_s2=False)

        render = [paso for paso in plan.pasos if paso.script == "prototipos/nisar_cambio.py"][0]
        self.assertIn("--color-out", render.args)
        self.assertNotIn("--verificar-s2", render.args)


if __name__ == "__main__":
    unittest.main()
