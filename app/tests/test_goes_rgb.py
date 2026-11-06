"""Pruebas de los RGB oficiales de GOES: Dust, Air Mass y Fire Temperature.

Fijan lo que el quick guide manda y lo que la app promete:

  * las bandas, rangos, gammas e inversiones de cada receta;
  * la mezcla de canales (incluida la inversión del azul de Air Mass);
  * que el catálogo no ofrezca `paleta` en estos productos;
  * que la receta baje TODAS las bandas y renderice el slot pedido.

    app\\.venv\\Scripts\\python.exe -m unittest discover -s app\\tests
"""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
for ruta in (RAIZ, RAIZ / "comun"):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))

from rgb_goes import RECETAS, bandas, componer_rgb, etiqueta_canal  # noqa: E402

from app.api import catalog, recipes  # noqa: E402


class RecetasOficiales(unittest.TestCase):
    """Bandas, rangos y gammas copiados de los quick guides."""

    def test_dust(self):
        receta = RECETAS["dust"]
        self.assertEqual(bandas("dust"), ("C11", "C13", "C14", "C15"))
        rojo, verde, azul = receta["canales"]
        self.assertEqual(etiqueta_canal(rojo), "C15-C13")
        self.assertEqual((rojo["vmin"], rojo["vmax"], rojo["gamma"]), (-6.7, 2.6, 1.0))
        self.assertEqual(etiqueta_canal(verde), "C14-C11")
        self.assertEqual((verde["vmin"], verde["vmax"], verde["gamma"]), (-0.5, 20.0, 2.5))
        self.assertEqual(etiqueta_canal(azul), "C13")
        self.assertEqual((azul["vmin"], azul["vmax"], azul["gamma"]), (-11.95, 15.55, 1.0))

    def test_airmass(self):
        receta = RECETAS["airmass"]
        self.assertEqual(bandas("airmass"), ("C08", "C10", "C12", "C13"))
        rojo, verde, azul = receta["canales"]
        self.assertEqual(etiqueta_canal(rojo), "C08-C10")
        self.assertEqual((rojo["vmin"], rojo["vmax"]), (-26.2, 0.6))
        self.assertEqual(etiqueta_canal(verde), "C12-C13")
        self.assertEqual((verde["vmin"], verde["vmax"]), (-43.2, 6.7))
        self.assertEqual(etiqueta_canal(azul), "C08")
        self.assertTrue(azul["invertir"])
        self.assertEqual((azul["vmin"], azul["vmax"]), (-64.65, -29.25))

    def test_firetemp(self):
        receta = RECETAS["firetemp"]
        self.assertEqual(bandas("firetemp"), ("C05", "C06", "C07"))
        rojo, verde, azul = receta["canales"]
        self.assertEqual((rojo["banda"], rojo["vmin"], rojo["vmax"], rojo["gamma"]),
                         ("C07", 0.0, 60.0, 0.4))
        self.assertEqual((verde["banda"], verde["vmin"], verde["vmax"]),
                         ("C06", 0.0, 100.0))
        self.assertEqual((azul["banda"], azul["vmin"], azul["vmax"]),
                         ("C05", 0.0, 75.0))


class Composicion(unittest.TestCase):
    """La mezcla de canales, con los valores del quick guide."""

    def _uno(self, producto: str, **valores) -> np.ndarray:
        campos = {
            banda: np.full((1, 1), valores[banda], dtype=np.float32)
            for banda in bandas(producto)
        }
        rgb, valido = componer_rgb(campos, producto)
        self.assertTrue(bool(valido[0, 0]))
        return rgb[0, 0]

    def test_dust_mezcla_diferencias_y_gamma(self):
        rgb = self._uno("dust", C15=5.0, C13=0.0, C14=10.0, C11=0.0)
        # R = (5 - (-6.7)) / 9.3 satura; G = 10.5/20.5 con gamma 2.5; B = 11.95/27.5.
        self.assertEqual(tuple(int(v) for v in rgb), (255, 195, 111))

    def test_airmass_invierte_el_azul(self):
        frio = self._uno("airmass", C08=-70.0, C10=-70.0, C12=-70.0, C13=-70.0)
        calido = self._uno("airmass", C08=-20.0, C10=-20.0, C12=-20.0, C13=-20.0)
        self.assertEqual(int(frio[2]), 255)   # tope frío: azul brillante
        self.assertEqual(int(calido[2]), 0)   # aire cálido: sin azul

    def test_firetemp_gamma_oscurece_los_medios(self):
        rgb = self._uno("firetemp", C07=30.0, C06=0.0, C05=0.0)
        # 0.5 ** (1/0.4) = 0.1768 -> 45. El fuego "tibio" queda rojo, no blanco.
        self.assertEqual(int(rgb[0]), 45)

    def test_pixel_sin_dato_queda_negro(self):
        campos = {
            "C11": np.full((1, 1), np.nan, dtype=np.float32),
            "C13": np.full((1, 1), 0.0, dtype=np.float32),
            "C14": np.full((1, 1), 0.0, dtype=np.float32),
            "C15": np.full((1, 1), 0.0, dtype=np.float32),
        }
        rgb, valido = componer_rgb(campos, "dust")
        self.assertFalse(bool(valido[0, 0]))
        self.assertEqual(tuple(int(v) for v in rgb[0, 0]), (0, 0, 0))


class UltimosConjunto(unittest.TestCase):
    """`ultimos_slots_conjunto`: sólo slots con TODAS las bandas del RGB."""

    def _clave(self, hora: str, banda: str) -> str:
        hh, mm = hora.split(":")
        inicio = f"2026308{hh}{mm}21" + "1"
        return (f"ABI-L2-CMIPF/2026/308/{hh}/"
                f"OR_ABI-L2-CMIPF-M6{banda}_G19_s{inicio}"
                f"_e2026308{hh}{mm}5931_c2026308{hh}{mm}5999.nc")

    def test_saltea_el_slot_al_que_le_falta_una_banda(self):
        bandas_rgb = ("C11", "C13", "C14", "C15")
        claves = [
            *[self._clave("18:00", b) for b in bandas_rgb],
            *[self._clave("18:10", b) for b in bandas_rgb[:3]],  # falta C15
        ]

        def listado(_sat, hora, timeout=60):
            return [c for c in claves if f"/2026/308/{hora.hour:02d}/" in c]

        from goes_reciente import ultimos_slots_conjunto

        with mock.patch("goes_reciente.listar_hora", side_effect=listado):
            slots = ultimos_slots_conjunto(
                "G19", bandas_rgb, 2, ahora=datetime(2026, 11, 4, 18, 29))
        self.assertEqual(slots, [datetime(2026, 11, 4, 18, 0)])


class Catalogo(unittest.TestCase):
    """Los tres productos existen y no ofrecen una paleta que no existe."""

    IDS = ("goes_dust", "goes_airmass", "goes_firetemp")

    def test_estan_en_el_catalogo(self):
        ids = {p.id for p in catalog.productos_disponibles()}
        for pid in self.IDS:
            self.assertIn(pid, ids)

    def test_no_ofrecen_paleta(self):
        for pid in self.IDS:
            nombres = {p.name for p in catalog.get_product(pid).params}
            self.assertNotIn("paleta", nombres, pid)

    def test_tienen_los_controles_de_goes(self):
        for pid in self.IDS:
            nombres = {p.name for p in catalog.get_product(pid).params}
            for esperado in ("snapshot", "satelite", "ventana", "ultimos", "ultimos_n",
                             "hora", "minuto", "resolucion", "animar", "fps"):
                self.assertIn(esperado, nombres, f"{pid}: {esperado}")

    def test_el_resumen_nombra_las_bandas(self):
        self.assertIn("C15-C13", catalog.get_product("goes_dust").summary)
        self.assertIn("C08-C10", catalog.get_product("goes_airmass").summary)
        self.assertIn("C07", catalog.get_product("goes_firetemp").summary)


class RecetaApp(unittest.TestCase):
    """La receta baja todas las bandas y renderiza el slot pedido."""

    DIA = {"start": "2026-11-03", "end": "2026-11-03"}

    def test_snapshot_baja_y_renderiza_ese_slot(self):
        plan = recipes._goes_rgb({
            "satelite": "G19", "ventana": self.DIA, "snapshot": True,
            "hora": 15, "minuto": "40", "resolucion": "1400",
        }, Path("C:/tmp/work"), "dust")
        descarga = [p for p in plan.pasos if p.kind == "download"][0]
        self.assertEqual(descarga.script, "descargar/descargar_goes_rgb.py")
        self.assertEqual(descarga.args[descarga.args.index("--producto") + 1], "dust")
        self.assertEqual(descarga.args[descarga.args.index("--desde") + 1],
                         "2026-11-03T15:40:00")
        render = [p for p in plan.pasos if p.kind == "render"][0]
        self.assertEqual(render.script, "prototipos/poster_goes_rgb.py")
        self.assertEqual(render.args[render.args.index("--producto") + 1], "dust")
        self.assertEqual(render.args[render.args.index("--n") + 1], "1")

    def test_ultimos_usa_el_rango_resuelto_y_anima(self):
        instantes = [
            datetime(2026, 11, 4, 16, 40) + timedelta(minutes=10 * i)
            for i in range(12)
        ]
        with mock.patch.object(recipes, "_ultimos_goes_rgb", return_value=instantes):
            plan = recipes.planear("goes_airmass", {
                "satelite": "G19", "resolucion": "1400", "animar": False,
                "ultimos": True, "ultimos_n": "12",
                "ventana": {"start": "2026-10-02", "end": "2026-10-05"},
            }, Path("C:/tmp/work"))
        descarga = [p for p in plan.pasos if p.kind == "download"][0]
        self.assertEqual(descarga.args[descarga.args.index("--desde") + 1],
                         "2026-11-04T16:40:00")
        self.assertEqual(descarga.args[descarga.args.index("--hasta") + 1],
                         "2026-11-04T18:40:00")
        render = [p for p in plan.pasos if p.kind == "render"][0]
        self.assertEqual(render.args[render.args.index("--n") + 1], "12")
        self.assertIn("animate", [p.kind for p in plan.pasos])

    def test_los_slots_piden_todas_las_bandas(self):
        def por_banda(_sat, banda):
            completo = [datetime(2026, 11, 4, 18, 0), datetime(2026, 11, 4, 18, 10)]
            if banda == "C07":
                return completo[:1]          # al slot de 18:10 le falta C07
            return completo

        with mock.patch.object(recipes, "_slots_goes", side_effect=por_banda):
            slots = recipes._slots_goes_rgb("G19", bandas("firetemp"))
        self.assertEqual(slots, [datetime(2026, 11, 4, 18, 0)])

    def test_snapshot_paraguay_pide_encuadre_limpio(self):
        # Solo Paraguay + snapshot: captura limpia rectangular (como el C13),
        # nunca el globo con su círculo. Vale para los tres RGB.
        for producto in ("dust", "airmass", "firetemp"):
            plan = recipes._goes_rgb({
                "satelite": "G19", "ventana": self.DIA, "snapshot": True,
                "paraguay": True, "margen": 6,
                "hora": 15, "minuto": "00", "resolucion": "1400",
            }, Path("C:/tmp/work"), producto)
            render = [p for p in plan.pasos if p.kind == "render"][0]
            self.assertIn("--limpio", render.args, producto)
            self.assertNotEqual(
                render.args[render.args.index("--recorte") + 1], "1.0", producto)


if __name__ == "__main__":
    unittest.main()
