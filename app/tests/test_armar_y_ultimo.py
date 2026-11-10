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
from datetime import date, datetime, timedelta, timezone
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


class RespaldoDeSnapshot(unittest.TestCase):
    """Un slot que la fuente todavía no publicó cae al más nuevo, solo."""

    def _ahora(self):
        return datetime.now(timezone.utc).replace(tzinfo=None, second=0, microsecond=0)

    def test_un_slot_no_publicado_usa_el_ultimo(self):
        pedido = self._ahora() - timedelta(minutes=30)
        ultimo = pedido - timedelta(minutes=60)
        with mock.patch.object(recipes, "_slot_pedido", return_value=pedido):
            slot = recipes._slot_snapshot({}, pedido.date(), lambda n: [ultimo])
        self.assertEqual(slot, ultimo)

    def test_un_slot_ya_publicado_se_respeta(self):
        pedido = self._ahora() - timedelta(minutes=30)
        with mock.patch.object(recipes, "_slot_pedido", return_value=pedido):
            slot = recipes._slot_snapshot({}, pedido.date(), lambda n: [pedido])
        self.assertEqual(slot, pedido)

    def test_una_fecha_vieja_no_se_toca(self):
        viejo = datetime(2026, 1, 1, 15)
        with mock.patch.object(recipes, "_slot_pedido", return_value=viejo):
            slot = recipes._slot_snapshot({}, viejo.date(),
                                          lambda n: [datetime(2026, 11, 10, 13, 30)])
        self.assertEqual(slot, viejo)

    def test_si_el_sondeo_falla_se_intenta_el_slot_pedido(self):
        pedido = self._ahora() - timedelta(minutes=30)

        def rompe(_):
            raise OSError("sin red")

        with mock.patch.object(recipes, "_slot_pedido", return_value=pedido):
            slot = recipes._slot_snapshot({}, pedido.date(), rompe)
        self.assertEqual(slot, pedido)


class CarpetaDeCuadros(unittest.TestCase):
    """El render encuentra lo que bajó el descargador, aunque haya retrocedido."""

    def _modulo(self):
        sys.path.insert(0, str(RAIZ / "cuadros"))
        import cuadros_geocolor  # noqa: PLC0415 - importa cartopy/matplotlib
        return cuadros_geocolor

    def _crear(self, salida: Path, instante: str) -> Path:
        carpeta = salida / f"frames_geocolor_plano_G19_{instante}_1f_1400px"
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / "crudo_001.jpg").write_bytes(b"jpeg")
        return carpeta

    def test_lee_el_instante_del_nombre(self):
        modulo = self._modulo()
        self.assertEqual(
            modulo.ts_de_frames("frames_geocolor_globo_G19_2026-11-10T1330_1f_1400px"),
            datetime(2026, 11, 10, 13, 30))
        self.assertIsNone(modulo.ts_de_frames("cualquier_cosa"))

    def test_prefiere_la_carpeta_del_slot_pedido(self):
        modulo = self._modulo()
        salida = Path(tempfile.mkdtemp(prefix="frames-"))
        try:
            exacta = self._crear(salida, "2026-11-10T1400")
            self._crear(salida, "2026-11-10T1350")
            args = types.SimpleNamespace(n=1, px=1400)
            carpeta = modulo._carpeta_de_frames(salida, "plano", "G19",
                                                datetime(2026, 11, 10, 14, 0), args)
            self.assertEqual(carpeta, exacta)
        finally:
            shutil.rmtree(salida, ignore_errors=True)

    def test_si_el_slot_pedido_no_bajo_usa_el_que_si(self):
        modulo = self._modulo()
        salida = Path(tempfile.mkdtemp(prefix="frames-"))
        try:
            respaldo = self._crear(salida, "2026-11-10T1350")
            args = types.SimpleNamespace(n=1, px=1400)
            carpeta = modulo._carpeta_de_frames(salida, "plano", "G19",
                                                datetime(2026, 11, 10, 14, 0), args)
            self.assertEqual(carpeta, respaldo)
        finally:
            shutil.rmtree(salida, ignore_errors=True)


class RespaldoDeDescarga(unittest.TestCase):
    """Un snapshot que GIBS no entrega retrocede un slot en vez de morir."""

    def test_retrocede_hasta_el_primero_que_baja(self):
        spec = importlib.util.spec_from_file_location(
            "geocolor_descarga", RAIZ / "descargar" / "geocolor.py")
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        salida = Path(tempfile.mkdtemp(prefix="geocolor-"))
        intentos = []

        def descarga(t, _caja, _ancho, _alto, destino, _capa):
            intentos.append(t)
            if t.minute >= 10:
                raise ValueError("cuadro sin dato")
            Path(destino).write_bytes(b"jpeg")

        args = types.SimpleNamespace(n=1, paso=10, px=1400, respaldo=4)
        try:
            with mock.patch.object(modulo, "descargar_cuadro", descarga):
                usado = modulo._slot_con_dato(
                    datetime(2026, 11, 10, 14, 30), salida, "plano", "G19", args,
                    (-165.0, -80.0, 15.0, 80.0), 1400, 1244, "capa")
        finally:
            shutil.rmtree(salida, ignore_errors=True)
        self.assertEqual(usado, datetime(2026, 11, 10, 14, 0))
        self.assertEqual(len(intentos), 4)          # 14:30, 14:20, 14:10, 14:00


class UltimoDiaDeLosDiarios(unittest.TestCase):
    """Los productos diarios resuelven "último" con la sonda de GIBS."""

    DIARIOS = ("truecolor_viirs", "mur_sst", "mur_realista")

    def _params(self, producto, **extra):
        params = {spec.name: spec.default
                  for spec in catalog.get_product(producto).params}
        params.update({"snapshot": True, "ultimo": True, "animar": False})
        params.update(extra)
        return params

    def test_los_tres_ofrecen_el_check(self):
        for producto in self.DIARIOS:
            with self.subTest(producto=producto):
                nombres = {spec.name: spec
                           for spec in catalog.get_product(producto).params}
                self.assertIn("ultimo", nombres)
                self.assertEqual(nombres["ultimo"].enabled_when, {"snapshot": True})
                self.assertFalse(nombres["ultimo"].default)

    def test_la_receta_se_queda_con_un_solo_dia(self):
        for producto in self.DIARIOS:
            with self.subTest(producto=producto):
                with mock.patch.object(recipes, "_ultimo_dia",
                                       return_value=date(2026, 11, 8)):
                    plan = recipes.planear(producto, self._params(producto),
                                           Path("x"))
                descarga = next(p for p in plan.pasos if p.kind == "download")
                args = descarga.args
                self.assertEqual(args[args.index("--desde") + 1], "2026-11-08")
                self.assertEqual(args[args.index("--hasta") + 1], "2026-11-08")
                self.assertEqual(args[args.index("--paso") + 1], "1")

    def test_sin_el_check_se_respeta_la_ventana(self):
        params = self._params("truecolor_viirs", ultimo=False,
                              ventana={"start": "2026-10-01", "end": "2026-10-05"})
        with mock.patch.object(recipes, "_ultimo_dia") as sonda:
            plan = recipes.planear("truecolor_viirs", params, Path("x"))
        sonda.assert_not_called()
        descarga = next(p for p in plan.pasos if p.kind == "download")
        # Con snapshot el rango ya se reduce al último día pedido (no sondea la fuente).
        self.assertEqual(descarga.args[descarga.args.index("--desde") + 1],
                         "2026-10-05")
        self.assertEqual(descarga.args[descarga.args.index("--hasta") + 1],
                         "2026-10-05")


if __name__ == "__main__":
    unittest.main()
