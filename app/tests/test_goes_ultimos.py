"""Pruebas de "últimos cuadros" de GOES y del UTC único.

Fijan las reglas nuevas:

  * el descargador resuelve "los N más nuevos publicados" caminando hacia atrás
    desde ahora (el ABI publica con ~20 min de retraso);
  * la ventana por defecto son las últimas 24 h, no una fecha hardcodeada;
  * la app planea "últimos" sin mirar la ventana de fechas y siempre anima;
  * las horas de la UI son UTC: la ventana no suma el desfase local.

    app\\.venv\\Scripts\\python.exe -m unittest discover -s app\\tests
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
for ruta in (RAIZ, RAIZ / "comun"):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))

from goes_reciente import (  # noqa: E402
    ahora_utc,
    piso_slot,
    ultimos_de,
    ultimos_slots,
    ventana_ultimas,
    ventana_ultimos,
)

from app.api import catalog, jobs as api_jobs, recipes  # noqa: E402

AHORA = datetime(2026, 11, 4, 18, 29)  # UTC, con segundos en el reloj real


def _clave(hora: str, banda: str = "C13", sat: str = "G19") -> str:
    """Clave S3 con el mismo formato que publica NOAA (día 308 de 2026)."""
    hh, mm = hora.split(":")
    # El nombre ABI trae 14 dígitos: YYYYJJJHHMMSS + décimas ("...1800211").
    inicio = f"2026308{hh}{mm}21" + "1"
    return (
        f"ABI-L2-CMIPF/2026/308/{hh}/"
        f"OR_ABI-L2-CMIPF-M6{banda}_{sat}_s{inicio}"
        f"_e2026308{hh}{mm}5931_c2026308{hh}{mm}5999.nc"
    )


def _listado(claves: list[str]):
    """Sustituto de `listar_hora`: filtra por la hora pedida, sin red."""
    return lambda sat, hora, timeout=60: [
        c for c in claves if f"/2026/308/{hora.hour:02d}/" in c
    ]


class UltimosSlots(unittest.TestCase):
    """`ultimos_slots`: los N más nuevos, del más viejo al más nuevo."""

    CLAVES = [
        _clave("17:30"), _clave("17:40"), _clave("17:50"),
        _clave("18:00"), _clave("18:10"),
        _clave("18:10", banda="C02"),          # otra banda: se ignora
        _clave("18:10", sat="G18"),            # otro satélite: se ignora
    ]

    def _slots(self, n: int, ahora: datetime = AHORA):
        with mock.patch("goes_reciente.listar_hora", side_effect=_listado(self.CLAVES)):
            return ultimos_slots("G19", "C13", n, ahora=ahora)

    def test_devuelve_los_ultimos_n_en_orden_cronologico(self):
        self.assertEqual(
            self._slots(3),
            [datetime(2026, 11, 4, 17, 50),
             datetime(2026, 11, 4, 18, 0),
             datetime(2026, 11, 4, 18, 10)],
        )

    def test_si_el_ultimo_todavia_no_salio_arranca_antes(self):
        # A las 18:29 el slot de 18:20 no está publicado: el más nuevo es 18:10.
        self.assertEqual(self._slots(1)[-1], datetime(2026, 11, 4, 18, 10))

    def test_camina_hacia_atras_hasta_completar_n(self):
        self.assertEqual(
            self._slots(4),
            [datetime(2026, 11, 4, 17, 40),
             datetime(2026, 11, 4, 17, 50),
             datetime(2026, 11, 4, 18, 0),
             datetime(2026, 11, 4, 18, 10)],
        )

    def test_sin_claves_devuelve_vacio(self):
        with mock.patch("goes_reciente.listar_hora", return_value=[]):
            self.assertEqual(ultimos_slots("G19", "C13", 5, ahora=AHORA), [])


class Ventanas(unittest.TestCase):
    """`ventana_ultimos` y `ventana_ultimas` resuelven el rango que usa la CLI."""

    CLAVES = [_clave("17:50"), _clave("18:00"), _clave("18:10")]

    def test_ventana_ultimos_termina_un_paso_despues_del_nuevo(self):
        with mock.patch("goes_reciente.listar_hora", side_effect=_listado(self.CLAVES)):
            desde, hasta = ventana_ultimos(3, "G19", "C13", ahora=AHORA)
        self.assertEqual(desde, datetime(2026, 11, 4, 17, 50))
        self.assertEqual(hasta, datetime(2026, 11, 4, 18, 20))

    def test_ventana_ultimas_cubre_24_horas(self):
        with mock.patch("goes_reciente.listar_hora", side_effect=_listado(self.CLAVES)):
            desde, hasta = ventana_ultimas(24, "G19", "C13", ahora=AHORA)
        self.assertEqual(hasta, datetime(2026, 11, 4, 18, 20))
        self.assertEqual(hasta - desde, timedelta(hours=24))
        self.assertEqual((hasta - desde) / timedelta(minutes=10), 144)


class Reloj(unittest.TestCase):
    def test_piso_slot_baja_a_multiplo_de_diez(self):
        self.assertEqual(piso_slot(datetime(2026, 11, 4, 18, 29, 45)),
                         datetime(2026, 11, 4, 18, 20))

    def test_ahora_utc_es_naive(self):
        self.assertIsNone(ahora_utc().tzinfo)

    def test_ultimos_de_recorta_la_cola(self):
        instantes = [datetime(2026, 11, 4, 18, m) for m in (0, 10, 20)]
        self.assertEqual(ultimos_de(instantes, 2), instantes[-2:])


class VentanaPorDefecto(unittest.TestCase):
    """La app ya no arranca dos días atrás."""

    def test_rango_por_defecto_termina_hoy(self):
        self.assertEqual(recipes._rango({})[1], ahora_utc().date())

    def test_catalogo_usa_hoy_en_los_goes(self):
        for producto in catalog.PRODUCTS:
            if producto.id not in ("goes_c13", "goes_banda"):
                continue
            spec = next(p for p in producto.params if p.name == "ventana")
            self.assertEqual(spec.default["end"], ahora_utc().date().isoformat())


class HorasEnUtc(unittest.TestCase):
    """Un solo UTC: 00:00 UTC es 00:00 UTC, no 21:00 del día anterior."""

    def test_ventana_de_animacion_no_desplaza_la_hora(self):
        desde, hasta = recipes._ventana_animacion(
            ahora_utc().date() - timedelta(days=1),
            ahora_utc().date() - timedelta(days=1),
            9, 12,
        )
        self.assertEqual(desde.hour, 9)
        self.assertEqual(desde.minute, 0)

    def test_cerrar_el_dia_termina_a_medianoche_utc(self):
        dia = ahora_utc().date() - timedelta(days=1)
        _, hasta = recipes._ventana_animacion(dia, dia, 0, 24)
        self.assertEqual(hasta, datetime.combine(dia + timedelta(days=1), datetime.min.time()))


class RecetaUltimos(unittest.TestCase):
    """`goes_banda` con "últimos": ignora la ventana y baja lo más nuevo."""

    INSTANTES = [
        datetime(2026, 11, 4, 16, 40) + timedelta(minutes=10 * i)
        for i in range(12)
    ]

    def _plan(self, **extra):
        params = {
            "satelite": "G19", "banda": "C13", "paleta": "clean_ir",
            "resolucion": "1400", "animar": False,
            "ultimos": True, "ultimos_n": "12",
            "ventana": {"start": "2026-10-02", "end": "2026-10-05"},
        }
        params.update(extra)
        with mock.patch.object(recipes, "_ultimos_goes", return_value=self.INSTANTES):
            return recipes._goes_banda(params, Path("C:/tmp/work"))

    def test_la_descarga_usa_el_rango_resuelto(self):
        tiempo = [p for p in self._plan().pasos if p.kind == "download"][0]
        args = tiempo.args
        self.assertEqual(args[args.index("--desde") + 1], "2026-11-04T16:40:00")
        self.assertEqual(args[args.index("--hasta") + 1], "2026-11-04T18:40:00")
        self.assertNotIn("2026-10-02", " ".join(args))

    def test_el_render_pide_los_n_cuadros(self):
        render = [p for p in self._plan().pasos if p.kind == "render"][0]
        self.assertEqual(render.args[render.args.index("--n") + 1], "12")
        self.assertEqual(render.args[render.args.index("--desde") + 1], "2026-11-04T16:40")

    def test_siempre_descarga_aunque_no_haya_datos_en_disco(self):
        kinds = [p.kind for p in self._plan().pasos]
        self.assertIn("download", kinds)

    def test_planear_anima_sin_el_switch_animar(self):
        plan = recipes.planear("goes_banda", {
            "satelite": "G19", "banda": "C13", "paleta": "clean_ir",
            "resolucion": "1400", "animar": False,
            "ultimos": True, "ultimos_n": "10",
            "ventana": {"start": "2026-10-02", "end": "2026-10-05"},
        }, Path("C:/tmp/work"))
        self.assertIn("animate", [p.kind for p in plan.pasos])

    def test_apagado_usa_la_ventana_de_siempre(self):
        with mock.patch.object(recipes, "_ultimos_goes") as resolver:
            plan = self._plan(ultimos=False)
        resolver.assert_not_called()
        tiempo = [p for p in plan.pasos if p.kind == "download"][0]
        self.assertIn("2026-10-02", " ".join(tiempo.args))


class OpcionesDelCatalogo(unittest.TestCase):
    """Los productos GOES exponen el switch y la lista exacta de cuadros."""

    EXACTOS = ["10", "12", "24", "36", "48", "60"]

    def test_goes_c13_y_goes_banda_tienen_ultimos(self):
        for pid in ("goes_c13", "goes_banda"):
            producto = catalog.get_product(pid)
            nombres = {p.name for p in producto.params}
            self.assertIn("ultimos", nombres)
            self.assertIn("ultimos_n", nombres)

    def test_la_lista_de_cuadros_es_la_pedida(self):
        producto = catalog.get_product("goes_banda")
        spec = next(p for p in producto.params if p.name == "ultimos_n")
        self.assertEqual([o.value for o in spec.options], self.EXACTOS)

    def test_ultimos_deshabilita_la_ventana(self):
        producto = catalog.get_product("goes_banda")
        ventana = next(p for p in producto.params if p.name == "ventana")
        self.assertEqual(ventana.enabled_when, {"ultimos": False})

    def test_las_horas_se_anuncian_en_utc(self):
        producto = catalog.get_product("goes_banda")
        for nombre in ("hora_desde", "hora_hasta"):
            spec = next(p for p in producto.params if p.name == nombre)
            self.assertIn("UTC", spec.label)
            self.assertNotIn("local", spec.label.lower())


class EnabledWhenCombinado(unittest.TestCase):
    """`_con_snapshot` suma su condición sin pisar la de "últimos"."""

    def test_animar_depende_de_snapshot_y_de_ultimos(self):
        producto = catalog.get_product("goes_c13")
        animar = next(p for p in producto.params if p.name == "animar")
        self.assertEqual(animar.enabled_when, {"ultimos": False, "snapshot": False})


class CuadroExacto(unittest.TestCase):
    """Snapshot de un slot exacto: 15:40 UTC y no el cenit de siempre."""

    DIA = {"start": "2026-11-03", "end": "2026-11-03"}

    def test_slot_pedido_usa_hora_y_minuto(self):
        self.assertEqual(
            recipes._slot_pedido({"hora": 15, "minuto": "40"}, date(2026, 11, 3)),
            datetime(2026, 11, 3, 15, 40),
        )

    def test_slot_pedido_redondea_al_multiplo_de_diez(self):
        slot = recipes._slot_pedido({"hora": 15, "minuto": "44"}, date(2026, 11, 3))
        self.assertEqual(slot.minute, 40)

    def test_slot_futuro_se_rechaza_con_mensaje(self):
        manana = ahora_utc().date() + timedelta(days=1)
        with self.assertRaises(ValueError):
            recipes._slot_pedido({"hora": 0, "minuto": "00"}, manana)

    def test_truecolor_snapshot_baja_y_renderiza_ese_slot(self):
        plan = recipes._goes_truecolor({
            "satelite": "G19", "ventana": self.DIA, "snapshot": True,
            "encuadre": "globo", "limbo": "completo", "nitidez": "maxima",
            "resolucion": "1400", "hora": 15, "minuto": "40",
        }, Path("C:/tmp/work"))
        descarga = [p for p in plan.pasos if p.kind == "download"][0]
        self.assertEqual(descarga.args[descarga.args.index("--desde") + 1], "2026-11-03T15:40")
        self.assertEqual(descarga.args[descarga.args.index("--n") + 1], "1")
        render = [p for p in plan.pasos if p.kind == "render"][0]
        self.assertIn("2026-11-03T15:40", " ".join(render.args))

    def test_goes_banda_snapshot_renderiza_ese_slot(self):
        plan = recipes._goes_banda({
            "satelite": "G19", "banda": "C13", "paleta": "clean_ir",
            "resolucion": "1400", "ventana": self.DIA, "snapshot": True,
            "hora": 15, "minuto": "40",
        }, Path("C:/tmp/work"))
        render = [p for p in plan.pasos if p.kind == "render"][0]
        self.assertEqual(render.args[render.args.index("--desde") + 1], "2026-11-03T15:40")
        self.assertEqual(render.args[render.args.index("--n") + 1], "1")

    def test_catalogo_expone_hora_y_minuto_del_cuadro(self):
        for pid in ("goes_truecolor", "goes_c13", "goes_banda", "geocolor", "himawari"):
            producto = catalog.get_product(pid)
            hora = next(p for p in producto.params if p.name == "hora")
            minuto = next(p for p in producto.params if p.name == "minuto")
            self.assertEqual(hora.enabled_when, {"snapshot": True}, pid)
            self.assertIn("UTC", hora.label)
            self.assertEqual(
                [o.value for o in minuto.options],
                ["00", "10", "20", "30", "40", "50"],
                pid,
            )


class RefrescoEnCadaGenerar(unittest.TestCase):
    """Cada "Generar" incluye la descarga, exista o no cache."""

    def test_planear_antepone_la_descarga_si_la_receta_la_salteaba(self):
        plan = recipes.planear("mur_sst", {
            "ventana": {"start": "2026-10-01", "end": "2026-10-10"},
            "resolucion": "1400", "animar": False,
        }, Path("C:/tmp/work"))
        self.assertEqual(plan.pasos[0].kind, "download")

    def test_snapshot_publica_solo_lo_de_esta_corrida(self):
        with tempfile.TemporaryDirectory() as temporal:
            media = Path(temporal)
            job = api_jobs.Job(
                id="snap1", product_id="snapshot_paraguay", product_name="Snapshot",
                params={}, mode="real", status="running",
                dir=media / "cache" / "uno",
            )
            job.work.mkdir(parents=True, exist_ok=True)
            viejo = job.work / "snapshot_viejo.png"
            viejo.write_bytes(b"x")
            os.utime(viejo, (time.time() - 3600, time.time() - 3600))
            nuevo = job.work / "snapshot_nuevo.png"
            nuevo.write_bytes(b"y")
            job.started_at = ahora_utc().isoformat(timespec="seconds")
            gestor = api_jobs.JobManager(media)
            gestor._publicar(job)
            self.assertEqual([a.name for a in job.artifacts], ["snapshot_nuevo.png"])


if __name__ == "__main__":
    unittest.main()
