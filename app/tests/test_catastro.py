"""Contrato del catastro en el visor NISAR, sin tocar el shapefile real.

Se arma un shapefile sintético de cinco parcelas en UTM 21S (tres normales, una
guardada en grados y una fuera de Paraguay) y se fija: construcción del índice,
atributos, gate por zoom, recorte por caja, reparación de geometrías, cruce con
el cuadro ROI y validación de los endpoints.

    .venv\\Scripts\\python.exe -m unittest app.tests.test_catastro -q
"""
from __future__ import annotations

import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

try:
    from pyproj import Transformer
    from fastapi.testclient import TestClient

    from app.api import catastro
    from app.api.main import app
except ImportError:  # pragma: no cover - faltan dependencias del venv de la app
    TestClient = None
    catastro = None
    app = None

_A_4326 = Transformer.from_crs(32721, 4326, always_xy=True) if TestClient else None

CAMPOS = (
    ("ccatastral", "C", 20),
    ("dpto", "C", 1),
    ("dist", "N", 10),
    ("padron", "N", 10),
    ("zona", "N", 10),
    ("mz", "N", 10),
    ("lote", "N", 10),
    ("finca", "C", 10),
    ("matricula", "C", 10),
    ("colonia", "C", 42),
    ("reg_prof", "C", 30),
    ("nombre_obj", "C", 110),
    ("tipo", "N", 10),
    ("zona_urban", "N", 10),
    ("sup_legal", "N", 24),
    ("sup_sig_m2", "N", 42),
)


def _cuadrado(x0: float, y0: float, lado: float) -> list[tuple[float, float]]:
    return [
        (x0, y0),
        (x0 + lado, y0),
        (x0 + lado, y0 + lado),
        (x0, y0 + lado),
        (x0, y0),
    ]


def _en_grados(anillo: list[tuple[float, float]]) -> list[tuple[float, float]]:
    xs = [p[0] for p in anillo]
    ys = [p[1] for p in anillo]
    lon, lat = _A_4326.transform(xs, ys)
    return list(zip(lon, lat))


def _fila(ccatastral: str, **extra):
    base = {
        "ccatastral": ccatastral,
        "dpto": "B",
        "dist": 1,
        "padron": 0,
        "zona": 17,
        "mz": 1346,
        "lote": 22,
        "finca": "9033",
        "matricula": "B01/9033",
        "colonia": "CONCEPCION",
        "reg_prof": "1685",
        "nombre_obj": "MZ 03, LOTE 02",
        "tipo": 1,
        "zona_urban": 0,
        "sup_legal": 10000.0,
        "sup_sig_m2": 10000.0,
    }
    base.update(extra)
    return base


def crear_shapefile(carpeta: Path) -> Path:
    """Cinco parcelas: tres válidas, una en grados y una fuera de rango.

    Se escriben .shp/.shx/.dbf a mano (formato ESRI) para no arrastrar el Writer
    de pyshp al armado del fixture: el Reader es el mismo que usa la API.
    """
    registros = [
        (_cuadrado(456000, 7410000, 100), _fila("B01171346022")),
        (_cuadrado(456200, 7410000, 100), _fila("B01171346023", lote=23)),
        (
            _cuadrado(456400, 7410000, 200),
            _fila("B01171346024", lote=24, sup_legal=40000.0),
        ),
        # Registro guardado en grados dentro de un shapefile declarado en UTM.
        (_en_grados(_cuadrado(457000, 7410000, 100)), _fila("B01171346025", lote=25)),
        # Registro basura: easting y northing imposibles para Paraguay.
        (_cuadrado(9000000, 9000000, 100), _fila("B01171346026", lote=26)),
    ]
    base = carpeta / "parcelas"
    _escribir_shp(base, registros)
    _escribir_dbf(base, [fila for _, fila in registros])
    return base.with_suffix(".shp")


def _escribir_shp(base: Path, registros: list) -> None:
    from shapely.geometry import Polygon  # mismo polígono que arma el índice

    contenidos: list[bytes] = []
    for anillo, _ in registros:
        pol = Polygon(anillo)
        minx, miny, maxx, maxy = pol.bounds
        cuerpo = struct.pack("<i", 5)
        cuerpo += struct.pack("<4d", minx, miny, maxx, maxy)
        cuerpo += struct.pack("<2i", 1, len(anillo))
        cuerpo += struct.pack("<i", 0)
        cuerpo += b"".join(struct.pack("<2d", float(x), float(y)) for x, y in anillo)
        contenidos.append(cuerpo)

    total = 100 + sum(8 + len(cuerpo) for cuerpo in contenidos)
    caja = (
        min(min(p[0] for p in anillo) for anillo, _ in registros),
        min(min(p[1] for p in anillo) for anillo, _ in registros),
        max(max(p[0] for p in anillo) for anillo, _ in registros),
        max(max(p[1] for p in anillo) for anillo, _ in registros),
    )

    def cabecera(largo_bytes: int) -> bytes:
        datos = struct.pack(">i", 9994) + b"\x00" * 20
        datos += struct.pack(">i", largo_bytes // 2)
        datos += struct.pack("<2i", 1000, 5)
        datos += struct.pack("<4d", *caja) + struct.pack("<4d", 0.0, 0.0, 0.0, 0.0)
        return datos

    with base.with_suffix(".shp").open("wb") as shp:
        shp.write(cabecera(total))
        for numero, cuerpo in enumerate(contenidos, start=1):
            shp.write(struct.pack(">2i", numero, len(cuerpo) // 2))
            shp.write(cuerpo)
    with base.with_suffix(".shx").open("wb") as shx:
        shx.write(cabecera(100 + 8 * len(contenidos)))
        offset = 50
        for cuerpo in contenidos:
            shx.write(struct.pack(">2i", offset, len(cuerpo) // 2))
            offset += (8 + len(cuerpo)) // 2


def _escribir_dbf(base: Path, filas: list[dict]) -> None:
    cabecera_len = 32 + 32 * len(CAMPOS) + 1
    registro_len = 1 + sum(largo for _, _, largo in CAMPOS)
    cabecera = struct.pack(
        "<4BIHH", 0x03, 126, 1, 1, len(filas), cabecera_len, registro_len
    )
    cabecera += b"\x00" * 11 + b"\x03" + b"\x00" * 8
    for nombre, tipo, largo in CAMPOS:
        cabecera += nombre.encode("ascii").ljust(11, b"\x00")
        cabecera += tipo.encode("ascii") + b"\x00" * 4
        cabecera += bytes([largo, 0]) + b"\x00" * 14
    cabecera += b"\x0d"

    cuerpo = bytearray()
    for fila in filas:
        cuerpo += b" "
        for nombre, tipo, largo in CAMPOS:
            valor = fila[nombre]
            if tipo == "N":
                decimales = 2 if nombre == "sup_legal" else 0
                texto = f"{float(valor):.{decimales}f}".rjust(largo)
            else:
                texto = str(valor).ljust(largo)
            cuerpo += texto.encode("utf-8")[:largo].ljust(largo, b" ")
    with base.with_suffix(".dbf").open("wb") as dbf:
        dbf.write(cabecera)
        dbf.write(cuerpo)
        dbf.write(b"\x1a")


@unittest.skipIf(TestClient is None, "la API necesita las dependencias del venv de la app")
class Catastro(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cliente = TestClient(app)

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.shp = crear_shapefile(self.base)
        self.media = self.base / "media"
        self.parches = [
            patch.object(catastro, "raiz_catastro", return_value=self.shp.parent),
            patch.object(catastro, "raiz_media", return_value=self.media),
        ]
        for parche in self.parches:
            parche.start()
        catastro._ESTADO.update(  # noqa: SLF001 - se reinicia el estado del módulo
            construyendo=False, progreso=0.0, mensaje="", error=None, inicio=None
        )
        self.meta = catastro.construir_indice(self.shp, catastro.ruta_indice())

    def tearDown(self) -> None:
        for parche in self.parches:
            parche.stop()
        self._tmp.cleanup()

    # --- índice ----------------------------------------------------------
    def test_el_indice_cuenta_y_separa_geometrias_rotas(self):
        self.assertEqual(self.meta["total"], "5")
        self.assertEqual(self.meta["usadas"], "4")
        self.assertEqual(self.meta["invalidas"], "1")
        self.assertEqual(self.meta["reparadas"], "1")
        self.assertEqual(self.meta["epsg_origen"], "32721")
        self.assertTrue(catastro.ruta_indice().is_file())
        self.assertAlmostEqual(float(self.meta["segundos"]), 0.0, delta=60.0)

    def test_los_lectores_coinciden_con_pyshp(self):
        try:
            import shapefile
        except ImportError:  # pragma: no cover - pyshp viene con Cartopy
            self.skipTest("pyshp no está en el entorno")
        lector = shapefile.Reader(str(self.shp), encoding="utf-8")
        try:
            total, registros = catastro._leer_dbf(self.shp.with_suffix(".dbf"))  # noqa: SLF001
            formas = list(catastro._leer_shapes(self.shp))  # noqa: SLF001
            self.assertEqual(total, len(lector))
            self.assertEqual(len(formas), len(lector))
            for indice, (forma, registro) in enumerate(zip(formas, registros)):
                referencia = lector.shape(indice)
                self.assertEqual(len(forma[1]) // 2, len(referencia.points))
                self.assertAlmostEqual(forma[1][0], referencia.points[0][0], places=6)
                self.assertAlmostEqual(forma[1][1], referencia.points[0][1], places=6)
                self.assertEqual(
                    registro["ccatastral"],
                    str(lector.record(indice)["ccatastral"]).strip(),
                )
        finally:
            lector.close()

    def test_el_indice_solo_esta_vigente_con_la_misma_firma(self):
        meta = catastro._leer_meta(catastro.ruta_indice())  # noqa: SLF001
        self.assertTrue(catastro._vigente(meta, catastro._firma(self.shp)))  # noqa: SLF001
        self.assertFalse(catastro._vigente(meta, "otra-firma"))  # noqa: SLF001
        self.assertFalse(catastro._vigente({}, catastro._firma(self.shp)))  # noqa: SLF001

    def test_el_estado_cuenta_el_dataset_y_la_atribucion(self):
        datos = catastro.estado()

        self.assertTrue(datos["disponible"])
        self.assertFalse(datos["indexando"])
        self.assertEqual(datos["parcelas"], 4)
        self.assertEqual(datos["invalidas"], 1)
        self.assertIn("SNC", datos["atribucion"])
        self.assertEqual(datos["departamentos"]["B"], "Concepción")
        self.assertEqual(datos["zoom_min"], 5)

    def test_sin_dataset_el_estado_lo_explica(self):
        with patch.object(catastro, "raiz_catastro", return_value=self.base / "vacio"):
            datos = catastro.estado()

        self.assertFalse(datos["disponible"])
        self.assertEqual(datos["parcelas"], 0)
        self.assertIn("CLIMATE3D_CATASTRO", datos["mensaje"])

    # --- parcelas --------------------------------------------------------
    def test_parcelas_devuelve_los_atributos_catastrales(self):
        cuerpo = catastro.parcelas(self._caja(455900, 7409900, 456700, 7410300), 15)

        self.assertEqual(cuerpo["type"], "FeatureCollection")
        self.assertEqual(cuerpo["capa"], "catastro")
        self.assertEqual(cuerpo["total"], 3)
        self.assertFalse(cuerpo["excedido"])
        self.assertFalse(cuerpo["requiere_zoom"])
        props = cuerpo["features"][0]["properties"]
        self.assertEqual(props["ccatastral"], "B01171346024")
        self.assertEqual(props["departamento"], "Concepción")
        self.assertEqual(props["matricula"], "B01/9033")
        self.assertEqual(props["area_ha"], 4.0)
        self.assertEqual(props["finca"], "9033")
        self.assertEqual(props["nombre_obj"], "MZ 03, LOTE 02")
        geometry = cuerpo["features"][0]["geometry"]
        lon = geometry["coordinates"][0][0][0]
        self.assertTrue(-63 < lon < -54, f"se esperaba longitud de Paraguay, vino {lon}")

    def test_la_geometria_en_grados_se_repara_a_metros(self):
        cuerpo = catastro.parcelas(self._caja(456900, 7409900, 457200, 7410300), 16)

        self.assertEqual(cuerpo["total"], 1)
        props = cuerpo["features"][0]["properties"]
        self.assertEqual(props["lote"], "25")
        self.assertAlmostEqual(props["area_ha"], 1.0, delta=0.05)

    def test_el_recorte_por_caja_no_devuelve_vecinas(self):
        cuerpo = catastro.parcelas(self._caja(455950, 7409950, 456150, 7410150), 15)

        self.assertEqual(cuerpo["total"], 1)
        self.assertEqual(cuerpo["features"][0]["properties"]["lote"], "22")

    def test_zoom_insuficiente_no_consulta_el_indice(self):
        cuerpo = catastro.parcelas(self._caja(455900, 7409900, 456700, 7410300), 4)

        self.assertTrue(cuerpo["requiere_zoom"])
        self.assertEqual(cuerpo["total"], 0)
        self.assertEqual(cuerpo["min_zoom"], 5)

    def test_al_alejar_solo_quedan_las_parcelas_grandes(self):
        caja = self._caja(455900, 7409900, 456700, 7410300)

        grande = catastro.parcelas(caja, 11)
        self.assertEqual(grande["total"], 1)
        self.assertEqual(grande["features"][0]["properties"]["lote"], "24")
        self.assertAlmostEqual(grande["area_min_ha"], 1.95, delta=0.2)

        mediano = catastro.parcelas(caja, 12)
        self.assertEqual(mediano["total"], 3)
        self.assertLess(mediano["area_min_ha"], grande["area_min_ha"])

        nada = catastro.parcelas(caja, 10)
        self.assertEqual(nada["total"], 0)
        self.assertGreater(nada["area_min_ha"], grande["area_min_ha"])

        todas = catastro.parcelas(caja, 14)
        self.assertEqual(todas["total"], 3)
        self.assertEqual(todas["area_min_ha"], 0)

    def test_una_vista_mucho_mas_ancha_que_el_zoom_devuelve_las_mas_grandes(self):
        # Pedir zoom 15 con una caja de ~3° no debe ordenar un millón de filas:
        # se responde con las más grandes de la vista, como en vista de país.
        cuerpo = catastro.parcelas(self._caja(300000, 7250000, 611000, 7560000), 15)

        self.assertEqual(cuerpo["total"], 4)
        self.assertEqual(cuerpo["area_min_ha"], 0)
        areas = [f["properties"]["area_ha"] for f in cuerpo["features"]]
        self.assertEqual(areas, sorted(areas, reverse=True))
        self.assertEqual(cuerpo["features"][0]["properties"]["lote"], "24")

    def test_sin_indice_avisa_que_esta_indexando(self):
        with patch.object(catastro, "asegurar_indice", return_value={}):
            with patch.object(catastro, "_leer_meta", return_value={}):
                cuerpo = catastro.parcelas(
                    self._caja(455900, 7409900, 456700, 7410300), 15
                )

        self.assertTrue(cuerpo["requiere_indice"])
        self.assertEqual(cuerpo["total"], 0)

    # --- velocidad --------------------------------------------------------
    def test_la_vista_de_trabajo_la_maneja_el_rtree(self):
        # El bug era manejar por el índice de área global: en una vista con menos
        # parcelas grandes que el límite, SQLite recorría el país entero.
        con = catastro._conectar()  # noqa: SLF001 - se mira el plan real
        try:
            plan = con.execute(
                "EXPLAIN QUERY PLAN " + catastro._SQL_VISTA_RTREE.format(filtro=""),
                (455900.0, 456700.0, 7409900.0, 7410300.0, 1201),
            ).fetchall()
        finally:
            con.close()
        detalle = " ".join(str(fila[-1]) for fila in plan)
        # `g` es el alias de parcelas_geo: la vista maneja por el R-tree y busca la
        # fila de atributos por rowid, en vez de recorrer el índice de área.
        self.assertIn("SCAN g VIRTUAL TABLE", detalle)
        self.assertNotIn("parcelas_area", detalle)

    def test_la_vista_ancha_sigue_recorriendo_el_indice_de_area(self):
        con = catastro._conectar()  # noqa: SLF001 - se mira el plan real
        try:
            plan = con.execute(
                "EXPLAIN QUERY PLAN " + catastro._SQL_VISTA_ANCHA,
                (0.0, -180.0, 180.0, -90.0, 90.0, 1201),
            ).fetchall()
        finally:
            con.close()
        detalle = " ".join(str(fila[-1]) for fila in plan)
        self.assertIn("parcelas_area", detalle)

    def test_la_misma_vista_se_responde_desde_la_cache(self):
        caja = self._caja(455900, 7409900, 456700, 7410300)

        primera = catastro.parcelas(caja, 15)
        segunda = catastro.parcelas(caja, 15)

        self.assertIs(primera, segunda)

    def test_reconstruir_el_indice_tira_la_cache(self):
        caja = self._caja(455900, 7409900, 456700, 7410300)
        primera = catastro.parcelas(caja, 15)

        catastro.construir_indice(self.shp, catastro.ruta_indice())
        segunda = catastro.parcelas(caja, 15)

        self.assertIsNot(primera, segunda)
        self.assertEqual(primera["total"], segunda["total"])

    # --- afectadas -------------------------------------------------------
    def test_afectadas_mide_la_mitad_exacta_de_una_parcela(self):
        poly = catastro.PedidoAfectadas(
            poligono={
                "type": "Polygon",
                "coordinates": [
                    [
                        list(_A_4326.transform(456000, 7410000)),
                        list(_A_4326.transform(456050, 7410000)),
                        list(_A_4326.transform(456050, 7410100)),
                        list(_A_4326.transform(456000, 7410100)),
                        list(_A_4326.transform(456000, 7410000)),
                    ]
                ],
            }
        )
        cuerpo = catastro.afectadas(poly)

        self.assertEqual(cuerpo["total"], 1)
        props = cuerpo["features"][0]["properties"]
        self.assertEqual(props["lote"], "22")
        self.assertAlmostEqual(props["afectado_m2"], 5000.0, delta=60.0)
        self.assertAlmostEqual(props["fraccion"], 0.5, delta=0.02)
        self.assertAlmostEqual(cuerpo["area_ha"], 0.5, delta=0.01)
        self.assertAlmostEqual(cuerpo["cubierto_ha"], 0.5, delta=0.01)
        self.assertAlmostEqual(cuerpo["cubierto_pct"], 100.0, delta=2.0)

    def test_afectadas_ordena_por_superficie_afectada(self):
        cuerpo = catastro.afectadas(
            catastro.PedidoAfectadas(bbox=self._grados(455900, 7409990, 456700, 7410500))
        )

        lotes = [f["properties"]["lote"] for f in cuerpo["features"]]
        self.assertEqual(lotes[:2], ["24", "22"])
        self.assertGreater(
            cuerpo["features"][0]["properties"]["afectado_m2"],
            cuerpo["features"][1]["properties"]["afectado_m2"],
        )

    def test_afectadas_respeta_el_limite_y_avisa(self):
        cuerpo = catastro.afectadas(
            catastro.PedidoAfectadas(
                bbox=self._grados(455900, 7409900, 456700, 7410300), limite=1
            )
        )

        self.assertEqual(cuerpo["total"], 1)
        self.assertTrue(cuerpo["excedido"])
        self.assertTrue(cuerpo["avisos"])

    # --- endpoints -------------------------------------------------------
    def test_endpoint_de_parcelas_responde_geojson(self):
        caja = ",".join(str(valor) for valor in self._grados(455900, 7409900, 456700, 7410300))
        respuesta = self.cliente.get(f"/api/catastro/parcelas?bbox={caja}&zoom=15")

        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo["total"], 3)
        self.assertEqual(cuerpo["fuente"]["nombre"], catastro.FUENTE)

    def test_endpoint_de_parcelas_valida_la_caja(self):
        respuesta = self.cliente.get("/api/catastro/parcelas?bbox=1,2,3&zoom=15")

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("4 numeros", respuesta.json()["detail"])

    def test_endpoint_de_afectadas_acepta_caja_y_poligono(self):
        caja = self.cliente.post(
            "/api/catastro/afectadas",
            json={"bbox": self._grados(455950, 7409950, 456150, 7410150)},
        )
        self.assertEqual(caja.status_code, 200)
        self.assertEqual(caja.json()["total"], 1)

        valores = _A_4326.transform(
            [456000, 456250, 456250, 456000, 456000],
            [7410000, 7410000, 7410100, 7410100, 7410000],
        )
        poligono = [[lon, lat] for lon, lat in zip(*valores)]
        otra = self.cliente.post(
            "/api/catastro/afectadas",
            json={"poligono": {"type": "Polygon", "coordinates": [poligono]}},
        )
        self.assertEqual(otra.status_code, 200)
        self.assertEqual(otra.json()["total"], 2)

    def test_endpoint_de_afectadas_sin_geometria_es_400(self):
        respuesta = self.cliente.post("/api/catastro/afectadas", json={})

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("bbox", respuesta.json()["detail"])

    def test_endpoint_de_afectadas_con_poligono_invalido_es_400(self):
        respuesta = self.cliente.post(
            "/api/catastro/afectadas",
            json={"poligono": {"type": "Point", "coordinates": [-57.4, -23.4]}},
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("Polygon", respuesta.json()["detail"])

    # --- utilidades ------------------------------------------------------
    def _grados(self, x0: float, y0: float, x1: float, y1: float) -> list[float]:
        """Caja en UTM 21S -> oeste,sur,este,norte en grados (para la API)."""
        oeste, sur = _A_4326.transform(x0, y0)
        este, norte = _A_4326.transform(x1, y1)
        return [round(valor, 6) for valor in (oeste, sur, este, norte)]

    def _caja(self, x0: float, y0: float, x1: float, y1: float) -> tuple[float, ...]:
        return catastro._caja(",".join(str(v) for v in self._grados(x0, y0, x1, y1)))  # noqa: SLF001


@unittest.skipIf(TestClient is None, "la API necesita las dependencias del venv de la app")
class DetallesDelCatastro(unittest.TestCase):
    def test_la_simplificacion_se_afina_con_el_zoom(self):
        for zoom in range(5, 17):
            self.assertGreaterEqual(
                catastro.SIMPLIFICACION[zoom], catastro.SIMPLIFICACION[zoom + 1]
            )

    def test_el_area_minima_baja_con_el_zoom_y_desaparece_a_14(self):
        areas = [catastro.area_minima(zoom) for zoom in range(5, 15)]
        self.assertEqual(areas, sorted(areas, reverse=True))
        self.assertAlmostEqual(catastro.area_minima(6) / 10_000, 1997, delta=60)
        self.assertAlmostEqual(catastro.area_minima(11) / 10_000, 1.95, delta=0.2)
        self.assertEqual(catastro.area_minima(14), 0.0)

    def test_caja_invalida_es_400_con_motivo(self):
        casos = {
            "1,2,3": "4 numeros",
            "a,b,c,d": "oeste,sur,este,norte",
            "-50,-30,-60,-20": "longitudes",
            "-50,-20,-40,-30": "latitudes",
        }
        for caja, esperado in casos.items():
            with self.subTest(caja=caja):
                with self.assertRaises(Exception) as contexto:
                    catastro._caja(caja)  # noqa: SLF001
                self.assertIn(esperado, str(contexto.exception))

    def test_los_departamentos_del_snc_tienen_nombre(self):
        self.assertEqual(len(catastro.DEPARTAMENTOS), 18)
        self.assertEqual(catastro.DEPARTAMENTOS["A"], "Asunción")
        self.assertEqual(catastro.DEPARTAMENTOS["K"], "Alto Paraná")
        self.assertEqual(catastro.DEPARTAMENTOS["S"], "Canindeyú")
        self.assertNotIn("O", catastro.DEPARTAMENTOS)


if __name__ == "__main__":
    unittest.main()
