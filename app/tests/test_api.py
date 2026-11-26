"""Pruebas de la API: contrato de lectura y errores delgados y legibles.

No crea jobs reales: toca los endpoints que no escriben ni lanzan scripts, y
los errores de pedido inválido. Asi la suite corre en segundos y sin red.

    .venv\\Scripts\\python.exe -m unittest discover -s app\\tests
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

try:
    from fastapi.testclient import TestClient

    from app.api import main
    from app.api.main import app
except ImportError:  # pragma: no cover - faltan dependencias del venv de la app
    TestClient = None
    app = None
    main = None


@unittest.skipIf(TestClient is None, "la API necesita las dependencias del venv de la app")
class ContratoDeLaApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cliente = TestClient(app)

    def test_health_dice_si_el_pipeline_esta_listo(self):
        cuerpo = self.cliente.get("/api/health").json()

        self.assertTrue(cuerpo["ok"])
        self.assertIn("repo_ready", cuerpo)
        self.assertIn("repo_python", cuerpo)
        self.assertIn("data_root", cuerpo)
        self.assertGreater(cuerpo["productos"], 0)

    def test_un_error_no_controlado_no_filtra_el_detalle(self):
        # S1 (auditoría): el handler global devolvía `Tipo: mensaje` al cliente, con
        # rutas absolutas y detalles de librerías. Ahora el cliente recibe un id de
        # incidente y el detalle queda sólo en el log del servidor.
        from unittest import mock

        cliente = TestClient(app, raise_server_exceptions=False)
        with mock.patch.object(main, "productos_disponibles", side_effect=RuntimeError("ruta /secreta/x")):
            respuesta = cliente.get("/api/catalog")

        self.assertEqual(respuesta.status_code, 500)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo["detail"], "Error interno.")
        self.assertRegex(cuerpo["incidente"], r"^[0-9a-f]{12}$")
        self.assertNotIn("secreta", respuesta.text)
        self.assertNotIn("RuntimeError", respuesta.text)

    def test_catalogo_trae_productos_y_rutas(self):
        respuesta = self.cliente.get("/api/catalog")

        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        self.assertGreater(len(cuerpo["products"]), 0)
        for clave in ("data_root", "media_root", "repo_python", "repo_ready"):
            self.assertIn(clave, cuerpo)
        self.assertTrue(all("id" in p and "params" in p for p in cuerpo["products"]))

    def test_fechas_de_un_producto_desconocido_es_404_con_motivo(self):
        respuesta = self.cliente.get("/api/catalog/no-existe/dates")

        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(respuesta.json()["detail"], "Producto desconocido")

    def test_pedir_un_producto_desconocido_es_400_con_motivo(self):
        respuesta = self.cliente.post(
            "/api/jobs", json={"product_id": "no-existe", "params": {}}
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("desconocido", respuesta.json()["detail"].lower())

    def test_un_job_desconocido_es_404(self):
        self.assertEqual(self.cliente.get("/api/jobs/no-existe").status_code, 404)
        self.assertEqual(
            self.cliente.post("/api/jobs/no-existe/cancel").status_code, 404
        )
        self.assertEqual(
            self.cliente.post("/api/jobs/no-existe/reveal").status_code, 404
        )
        self.assertEqual(
            self.cliente.get("/api/jobs/no-existe/events").status_code, 404
        )

    def test_available_dates_descubre_datos_locales_en_todos_los_productos_goes_y_gibs(self):
        import tempfile
        from unittest.mock import patch
        from app.api import catalog

        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            (raiz / "goes_c13_g19").mkdir()
            (raiz / "goes_c13_g19" / "OR_ABI-L1b-RadF-M6C13_G19_s20261101200000.nc").write_bytes(b"ok")
            (raiz / "goes_c02_g19").mkdir()
            (raiz / "goes_c02_g19" / "OR_ABI-L1b-RadF-M6C02_G19_s20261101200000.nc").write_bytes(b"ok")
            (raiz / "salidas" / "frames_geocolor_globo_G19_2026-04-20T1700_1f_2712px").mkdir(parents=True)
            (raiz / "salidas" / "frames_truecolor_viirs_noaa20_globo_2026-04-20T0000_1f_2000px").mkdir(parents=True)
            (raiz / "salidas" / "PACE_truecolor_2026-04-20.png").write_bytes(b"ok")

            por_id = {p.id: p for p in catalog.PRODUCTS}
            with patch.object(catalog, "data_root", return_value=raiz):
                for pid in ("goes_banda", "goes_sandwich", "geocolor", "truecolor_viirs", "pace_truecolor"):
                    fuente, fechas = catalog.available_dates(por_id[pid], {"satelite": "G19", "banda": "C13"})
                    self.assertEqual(fuente, "descubierto", f"{pid} no descubrio sus fechas en disco")
                    self.assertIn("2026-04-20", fechas, f"{pid} no devolvio 2026-04-20")

    def test_parametros_de_productos_estan_cubiertos_por_etapas_canonicas_sin_huerfanos(self):
        from app.api import catalog

        conocidos = set(catalog.ORDEN_PARAMETROS)
        for producto in catalog.PRODUCTS:
            nombres = [spec.name for spec in producto.params]
            desconocidos = [n for n in nombres if n not in conocidos]
            self.assertEqual(
                desconocidos,
                [],
                f"{producto.id} tiene parametros fuera de ORDEN_PARAMETROS: {desconocidos}",
            )


if __name__ == "__main__":
    unittest.main()
