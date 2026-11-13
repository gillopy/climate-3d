"""Render NISAR con un GCOV sintetico de estructura real.

El dataset real pesa ~1.9 GB y exige Earthdata, asi que la suite arma un HDF5
chico con los mismos grupos, coordenadas, proyeccion y polarizaciones. Asi se
prueba el recorte, la conversion a dB y el PNG sin red ni credenciales.

    app\\.venv\\Scripts\\python.exe -m unittest app.tests.test_nisar_render -q
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

try:
    from app.api.recipes import python_repo
except ImportError:  # pragma: no cover
    python_repo = None

FIXTURE = r'''
from __future__ import annotations

import sys
from pathlib import Path

import h5py
import numpy as np
from pyproj import Transformer

salida = Path(sys.argv[1])
modo = sys.argv[2] if len(sys.argv) > 2 else "base"
epsg = 32721  # UTM 21S, Paraguay
tr = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
cx, cy = tr.transform(-58.4, -23.4)

alto, ancho = 400, 600
paso = 20.0
x = cx + (np.arange(ancho) - ancho / 2) * paso
y = cy + (alto / 2 - np.arange(alto)) * paso
yy, xx = np.meshgrid(np.arange(alto), np.arange(ancho), indexing="ij")
hh = (10 ** (-1.2 + 0.35 * np.sin(xx / 37.0) * np.cos(yy / 29.0))).astype("float32")
hv = (hh * (0.28 + 0.08 * np.cos(xx / 19.0))).astype("float32")
hh[10:20, 30:50] = 0.0
if modo == "perdida":
    # Parche de perdida de dosel: HV cae ~7 dB en el centro de la caja.
    hv[150:250, 250:350] *= 0.2
if modo == "agua":
    # Parche de agua abierta: HH y HV muy bajos en el centro de la caja.
    hh[150:230, 250:330] = 1e-5
    hv[150:230, 250:330] = 1e-6

salida.parent.mkdir(parents=True, exist_ok=True)
with h5py.File(salida, "w") as f:
    g = f.create_group("/science/LSAR/GCOV/grids/frequencyA")
    g.create_dataset("HHHH", data=hh, compression="gzip")
    g.create_dataset("HVHV", data=hv, compression="gzip")
    g.create_dataset("xCoordinates", data=x)
    g.create_dataset("yCoordinates", data=y)
    g.create_dataset("xCoordinateSpacing", data=paso)
    g.create_dataset("yCoordinateSpacing", data=paso)
    proj = g.create_dataset("projection", data=np.int32(epsg))
    proj.attrs["epsg_code"] = np.int32(epsg)
    proj.attrs["grid_mapping_name"] = "universal_transverse_mercator"
    dt = h5py.special_dtype(vlen=str)
    pols = g.create_dataset("listOfPolarizations", (2,), dtype=dt)
    pols[:] = ["HH", "HV"]

inverso = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
oeste, sur = inverso.transform(cx - 2000, cy - 1500)
este, norte = inverso.transform(cx + 2000, cy + 1500)
print(f"{oeste:.6f},{sur:.6f},{este:.6f},{norte:.6f}")
'''


@unittest.skipIf(
    python_repo is None or not python_repo().is_file(),
    "hace falta el Python del repo para el render",
)
class RenderNisar(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        chequeo = subprocess.run(
            [str(python_repo()), "-c", "import h5py, pyproj, matplotlib, PIL, tifffile"],
            capture_output=True,
        )
        if chequeo.returncode != 0:
            raise unittest.SkipTest("al Python del repo le faltan h5py/pyproj/matplotlib")

    def test_render_color_y_gris_recortan_la_caja(self):
        with tempfile.TemporaryDirectory() as carpeta:
            tmp = Path(carpeta)
            fixture = tmp / "fixture.py"
            fixture.write_text(FIXTURE, encoding="utf-8")
            h5 = tmp / "NISAR_L2_PR_GCOV_034_082_D_101_2005_DHDH_A_20261029T214921_20261029T214955_P05036_N_F_J_001.h5"

            creado = subprocess.run(
                [str(python_repo()), str(fixture), str(h5), "base"],
                capture_output=True,
                text=True,
                cwd=str(RAIZ),
            )
            self.assertEqual(creado.returncode, 0, creado.stderr)
            bbox = creado.stdout.strip().splitlines()[-1]

            for modo in ("color", "gris"):
                png = tmp / f"{modo}.png"
                corrida = subprocess.run(
                    [
                        str(python_repo()),
                        "prototipos/poster_nisar.py",
                        "--h5",
                        str(h5),
                        "--bbox",
                        bbox,
                        "--pol",
                        "auto",
                        "--modo",
                        modo,
                        "--px",
                        "1000",
                        "--out",
                        str(png),
                        "--geojson",
                        "datos/paraguay_gadm.json",
                    ],
                    capture_output=True,
                    text=True,
                    cwd=str(RAIZ),
                )
                self.assertEqual(corrida.returncode, 0, corrida.stdout + corrida.stderr)
                self.assertTrue(png.is_file(), corrida.stdout)
                self.assertGreater(png.stat().st_size, 10_000)
                with Image.open(png) as imagen:
                    self.assertEqual(imagen.mode, "RGB")
                    self.assertLessEqual(max(imagen.size), 1000)
                self.assertTrue(png.with_suffix(".json").is_file())

            # Una caja fuera de la escena tiene que fallar claro, no renderizar vacio.
            fuera = subprocess.run(
                [
                    str(python_repo()),
                    "prototipos/poster_nisar.py",
                    "--h5",
                    str(h5),
                    "--bbox",
                    "-10,-10,-9,-9",
                    "--out",
                    str(tmp / "fuera.png"),
                ],
                capture_output=True,
                text=True,
                cwd=str(RAIZ),
            )
            self.assertNotEqual(fuera.returncode, 0)
            self.assertIn("no intersecta", fuera.stderr + fuera.stdout)

    def test_rvi_y_cambio_con_par_sintetico(self):
        with tempfile.TemporaryDirectory() as carpeta:
            tmp = Path(carpeta)
            fixture = tmp / "fixture.py"
            fixture.write_text(FIXTURE, encoding="utf-8")
            antes = tmp / (
                "NISAR_L2_PR_GCOV_033_082_D_101_2005_DHDH_A_"
                "20261017T214920_20261017T214955_P05023_N_F_J_001.h5"
            )
            despues = tmp / (
                "NISAR_L2_PR_GCOV_034_082_D_101_2005_DHDH_A_"
                "20261029T214921_20261029T214955_P05036_N_F_J_001.h5"
            )
            for ruta, modo in ((antes, "base"), (despues, "perdida")):
                creado = subprocess.run(
                    [str(python_repo()), str(fixture), str(ruta), modo],
                    capture_output=True,
                    text=True,
                    cwd=str(RAIZ),
                )
                self.assertEqual(creado.returncode, 0, creado.stderr)
                bbox = creado.stdout.strip().splitlines()[-1]

            rvi = tmp / "rvi.png"
            corrida = subprocess.run(
                [
                    str(python_repo()),
                    "prototipos/nisar_rvi.py",
                    "--h5",
                    str(antes),
                    "--bbox",
                    bbox,
                    "--px",
                    "900",
                    "--out",
                    str(rvi),
                ],
                capture_output=True,
                text=True,
                cwd=str(RAIZ),
            )
            self.assertEqual(corrida.returncode, 0, corrida.stdout + corrida.stderr)
            self.assertTrue(rvi.is_file())
            meta_rvi = json.loads(rvi.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(meta_rvi["producto"], "rvi")
            self.assertGreater(meta_rvi["rvi_medio"], 0.0)
            self.assertLessEqual(meta_rvi["rvi_medio"], 1.5)

            cambio = tmp / "cambio.png"
            corrida = subprocess.run(
                [
                    str(python_repo()),
                    "prototipos/nisar_cambio.py",
                    "--antes",
                    str(antes),
                    "--despues",
                    str(despues),
                    "--bbox",
                    bbox,
                    "--px",
                    "900",
                    "--modo",
                    "mascara",
                    "--umbral",
                    "3",
                    "--hv-min",
                    "-30",
                    "--out",
                    str(cambio),
                    "--geojson",
                    "datos/paraguay_gadm.json",
                ],
                capture_output=True,
                text=True,
                cwd=str(RAIZ),
            )
            self.assertEqual(corrida.returncode, 0, corrida.stdout + corrida.stderr)
            self.assertTrue(cambio.is_file())
            meta = json.loads(cambio.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(meta["producto"], "cambio")
            self.assertGreater(meta["perdida_ha"], 0.0)
            self.assertGreater(meta["area_ha"], meta["perdida_ha"])
            with Image.open(cambio) as imagen:
                self.assertEqual(imagen.mode, "RGB")

    def test_serie_temporal_y_geotiff(self):
        with tempfile.TemporaryDirectory() as carpeta:
            tmp = Path(carpeta)
            coleccion = tmp / "NISAR_L2_GCOV_V1"
            coleccion.mkdir()
            fixture = tmp / "fixture.py"
            fixture.write_text(FIXTURE, encoding="utf-8")
            nombres = [
                (
                    "NISAR_L2_PR_GCOV_032_082_D_101_2005_DHDH_A_"
                    "20261005T214920_20261005T214955_P05023_N_F_J_001",
                    "base",
                ),
                (
                    "NISAR_L2_PR_GCOV_033_082_D_101_2005_DHDH_A_"
                    "20261017T214920_20261017T214955_P05023_N_F_J_001",
                    "base",
                ),
                (
                    "NISAR_L2_PR_GCOV_034_082_D_101_2005_DHDH_A_"
                    "20261029T214921_20261029T214955_P05036_N_F_J_001",
                    "perdida",
                ),
            ]
            rutas = []
            for nombre, modo in nombres:
                ruta = coleccion / f"{nombre}.h5"
                creado = subprocess.run(
                    [str(python_repo()), str(fixture), str(ruta), modo],
                    capture_output=True,
                    text=True,
                    cwd=str(RAIZ),
                )
                self.assertEqual(creado.returncode, 0, creado.stderr)
                bbox = creado.stdout.strip().splitlines()[-1]
                rutas.append(ruta)

            prefijo = tmp / "serie"
            corrida = subprocess.run(
                [
                    str(python_repo()),
                    "prototipos/nisar_serie.py",
                    "--h5",
                    str(rutas[-1]),
                    "--coleccion-dir",
                    str(coleccion),
                    "--track",
                    "82",
                    "--frame",
                    "101",
                    "--bbox",
                    bbox,
                    "--px",
                    "900",
                    "--umbral",
                    "3",
                    "--hv-min",
                    "-30",
                    "--out",
                    str(prefijo),
                    "--geojson",
                    "datos/paraguay_gadm.json",
                ],
                capture_output=True,
                text=True,
                cwd=str(RAIZ),
            )
            self.assertEqual(corrida.returncode, 0, corrida.stdout + corrida.stderr)
            for sufijo in ("_serie.png", "_mediana.png", "_cusum.png"):
                self.assertTrue(prefijo.with_name(f"serie{sufijo}").is_file())
            meta = json.loads((tmp / "serie.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["producto"], "serie")
            self.assertEqual(len(meta["fechas"]), 3)
            self.assertGreater(meta["cusum"]["cambio_ha"], 0)
            self.assertTrue(
                any(fecha.startswith("2026-10-29") for fecha in meta["cusum"]["por_fecha"])
            )

            tif = tmp / "corte.tif"
            corrida = subprocess.run(
                [
                    str(python_repo()),
                    "prototipos/nisar_geotiff.py",
                    "--h5",
                    str(rutas[0]),
                    "--bbox",
                    bbox,
                    "--pol",
                    "hv",
                    "--px",
                    "900",
                    "--out",
                    str(tif),
                    "--geojson",
                    "datos/paraguay_gadm.json",
                ],
                capture_output=True,
                text=True,
                cwd=str(RAIZ),
            )
            self.assertEqual(corrida.returncode, 0, corrida.stdout + corrida.stderr)
            self.assertTrue(tif.is_file())
            self.assertTrue(tif.with_name("corte_preview.png").is_file())

            codigo = (
                "import tifffile; "
                f"t=tifffile.TiffFile({str(tif)!r}); p=t.pages[0]; "
                "print(p.shape); print(p.tags['GeoKeyDirectoryTag'].value)"
            )
            chequeo = subprocess.run(
                [str(python_repo()), "-c", codigo],
                capture_output=True,
                text=True,
                cwd=str(RAIZ),
            )
            self.assertEqual(chequeo.returncode, 0, chequeo.stderr)
            self.assertIn("32721", chequeo.stdout)

    def test_agua_e_incendio(self):
        with tempfile.TemporaryDirectory() as carpeta:
            tmp = Path(carpeta)
            fixture = tmp / "fixture.py"
            fixture.write_text(FIXTURE, encoding="utf-8")
            base = tmp / (
                "NISAR_L2_PR_GCOV_032_082_D_101_2005_DHDH_A_"
                "20261005T214920_20261005T214955_P05023_N_F_J_001.h5"
            )
            perdida = tmp / (
                "NISAR_L2_PR_GCOV_034_082_D_101_2005_DHDH_A_"
                "20261029T214921_20261029T214955_P05036_N_F_J_001.h5"
            )
            agua = tmp / (
                "NISAR_L2_PR_GCOV_033_082_D_101_2005_DHDH_A_"
                "20261017T214920_20261017T214955_P05023_N_F_J_001.h5"
            )
            for ruta, modo in ((base, "base"), (perdida, "perdida"), (agua, "agua")):
                creado = subprocess.run(
                    [str(python_repo()), str(fixture), str(ruta), modo],
                    capture_output=True,
                    text=True,
                    cwd=str(RAIZ),
                )
                self.assertEqual(creado.returncode, 0, creado.stderr)
                bbox = creado.stdout.strip().splitlines()[-1]

            png_agua = tmp / "agua.png"
            corrida = subprocess.run(
                [
                    str(python_repo()),
                    "prototipos/nisar_agua.py",
                    "--h5",
                    str(agua),
                    "--bbox",
                    bbox,
                    "--px",
                    "900",
                    "--out",
                    str(png_agua),
                    "--geojson",
                    "datos/paraguay_gadm.json",
                ],
                capture_output=True,
                text=True,
                cwd=str(RAIZ),
            )
            self.assertEqual(corrida.returncode, 0, corrida.stdout + corrida.stderr)
            self.assertTrue(png_agua.is_file())
            meta_agua = json.loads(png_agua.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertGreater(meta_agua["agua_ha"], 0.0)

            png_fuego = tmp / "incendio.png"
            corrida = subprocess.run(
                [
                    str(python_repo()),
                    "prototipos/nisar_incendio.py",
                    "--antes",
                    str(base),
                    "--despues",
                    str(perdida),
                    "--bbox",
                    bbox,
                    "--px",
                    "900",
                    "--umbral",
                    "3",
                    "--hv-min",
                    "-30",
                    "--out",
                    str(png_fuego),
                    "--geojson",
                    "datos/paraguay_gadm.json",
                ],
                capture_output=True,
                text=True,
                cwd=str(RAIZ),
            )
            self.assertEqual(corrida.returncode, 0, corrida.stdout + corrida.stderr)
            self.assertTrue(png_fuego.is_file())
            meta_fuego = json.loads(png_fuego.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertGreater(meta_fuego["cicatriz_ha"], 0.0)
            self.assertFalse(meta_fuego["firms"])
            self.assertEqual(meta_fuego["focos"], 0)


if __name__ == "__main__":
    unittest.main()
