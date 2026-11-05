"""Pruebas del ciclo de vida de un job: correr, fallar, publicar y persistir.

Todo se ejecuta con scripts de mentira en una carpeta temporal: no toca la red
ni los datos reales del repo. Lo que se fija aca es el contrato que ve la UI:
un job termina en `done` con artefactos, falla con un mensaje legible, y el
historial sobrevive al reinicio sin romperse por una linea corrupta.

    app\\.venv\\Scripts\\python.exe -m unittest discover -s app\\tests
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

try:
    from app.api import jobs
    from app.api.recipes import Plan, Step
except ImportError:  # pragma: no cover - faltan dependencias del venv de la app
    jobs = None
    Plan = Step = None


def _nuevo_job(media: Path, job_id: str = "j1", **extra) -> "jobs.Job":
    datos = {
        "id": job_id,
        "product_id": "demo",
        "product_name": "Demo",
        "params": {},
        "mode": "real",
        "dir": media / "cache" / job_id,
    }
    datos.update(extra)
    return jobs.Job(**datos)


@unittest.skipIf(jobs is None, "la API necesita las dependencias del venv de la app")
class Base(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.media = self.raiz / "media"
        self.media.mkdir()
        self.gestor = jobs.JobManager(self.media)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def escribir_script(self, nombre: str, codigo: str) -> None:
        (self.raiz / nombre).write_text(codigo, encoding="utf-8")

    def parchear_repo(self):
        """Hace que `_lanzar` use este Python y esta raiz temporal."""
        return (
            mock.patch.object(jobs, "RAIZ_REPO", self.raiz),
            mock.patch.object(jobs, "python_repo", lambda: Path(sys.executable)),
        )


class CorrerUnJob(Base):
    def _correr(self, trabajo: "jobs.Job") -> None:
        patcher_raiz, patcher_python = self.parchear_repo()
        with patcher_raiz, patcher_python:
            asyncio.run(self.gestor._correr(trabajo))

    def test_termina_bien_y_publica_el_png(self):
        self.escribir_script(
            "render.py",
            "import sys\n"
            "from pathlib import Path\n"
            "destino = Path(sys.argv[1])\n"
            "destino.mkdir(parents=True, exist_ok=True)\n"
            "(destino / 'poster.png').write_bytes(b'\\x89PNG\\r\\n\\x1a\\n')\n"
            "print('render ok')\n",
        )
        trabajo = _nuevo_job(self.media)
        plan = Plan(
            pasos=[
                Step(
                    kind="render",
                    label="demo",
                    script="render.py",
                    args=[str(trabajo.work)],
                )
            ]
        )
        with mock.patch.object(jobs, "planear", return_value=plan):
            self._correr(trabajo)

        self.assertEqual(trabajo.status, "done", trabajo.logs)
        self.assertEqual(trabajo.progress, 1.0)
        self.assertEqual(trabajo.error, None)
        self.assertEqual([a.name for a in trabajo.artifacts], ["poster.png"])
        self.assertTrue(trabajo.artifacts[0].url.startswith("/media/"))
        self.assertIn("render ok", [linea.text for linea in trabajo.logs])

    def test_informa_el_codigo_de_salida_y_lo_que_imprimio_el_script(self):
        self.escribir_script(
            "falla.py",
            "import sys\n"
            "print('arrancando')\n"
            "print('explotó la descarga', file=sys.stderr)\n"
            "sys.exit(7)\n",
        )
        trabajo = _nuevo_job(self.media)
        plan = Plan(
            pasos=[Step(kind="render", label="demo", script="falla.py", args=[])]
        )
        with mock.patch.object(jobs, "planear", return_value=plan):
            self._correr(trabajo)

        textos = [linea.text for linea in trabajo.logs]
        self.assertEqual(trabajo.status, "error")
        self.assertIn("codigo 7", trabajo.error)
        self.assertIn("arrancando", textos)
        self.assertIn("explotó la descarga", textos)
        self.assertIn(trabajo.error, textos)

    def test_avisa_cuando_el_pipeline_no_dejo_ninguna_imagen(self):
        self.escribir_script("silencio.py", "print('nada para publicar')\n")
        trabajo = _nuevo_job(self.media)
        plan = Plan(
            pasos=[Step(kind="render", label="demo", script="silencio.py", args=[])]
        )
        with mock.patch.object(jobs, "planear", return_value=plan):
            self._correr(trabajo)

        self.assertEqual(trabajo.status, "error")
        self.assertIn("no dejo ninguna imagen", trabajo.error)
        self.assertEqual(trabajo.artifacts, [])

    def test_un_error_sin_texto_igual_se_lee_en_la_ui(self):
        trabajo = _nuevo_job(self.media)

        async def real_vacia(_job):
            raise RuntimeError()

        with mock.patch.object(self.gestor, "_real", new=real_vacia):
            self._correr(trabajo)

        self.assertEqual(trabajo.status, "error")
        self.assertEqual(trabajo.error, "sin detalle")

    def test_si_no_puede_crear_la_carpeta_no_queda_colgado(self):
        trabajo = _nuevo_job(self.media)
        trabajo.work.parent.mkdir(parents=True, exist_ok=True)
        trabajo.work.write_bytes(b"un archivo donde deberia ir una carpeta")

        self._correr(trabajo)

        self.assertEqual(trabajo.status, "error")
        self.assertTrue(trabajo.error)
        self.assertIn("FileExistsError", trabajo.error)

    def test_si_el_python_del_repo_no_arranca_lo_explica(self):
        trabajo = _nuevo_job(self.media)
        paso = Step(kind="render", label="demo", script="eco.py", args=[])
        self.escribir_script("eco.py", "print('hola')\n")
        inexistente = self.raiz / "no-existe" / "python.exe"

        with mock.patch.object(jobs, "RAIZ_REPO", self.raiz), mock.patch.object(
            jobs, "python_repo", lambda: inexistente
        ):
            with self.assertRaises(RuntimeError) as error:
                asyncio.run(self.gestor._lanzar(trabajo, paso, [], 0.0, 1.0, "eco"))

        self.assertIn("no se pudo ejecutar", str(error.exception))
        self.assertIn(str(inexistente), str(error.exception))


class PublicarArtefactos(Base):
    def test_publica_primer_y_ultimo_cuadro_mas_el_video(self):
        trabajo = _nuevo_job(self.media)
        frames = trabajo.work / "frames"
        frames.mkdir(parents=True)
        for numero in (1, 2, 3):
            (frames / f"cuadro_{numero:03d}.png").write_bytes(b"png")
        (trabajo.work / "animacion.mp4").write_bytes(b"mp4")

        self.gestor._publicar(trabajo)

        nombres = [a.name for a in trabajo.artifacts]
        self.assertEqual(nombres, ["cuadro_001.png", "cuadro_003.png", "animacion.mp4"])
        self.assertEqual(trabajo.artifacts[-1].kind, "video")

    def test_publica_el_poster_suelto_de_esta_corrida(self):
        trabajo = _nuevo_job(self.media)
        trabajo.work.mkdir(parents=True)
        trabajo.started_at = jobs._ahora()
        (trabajo.work / "poster.png").write_bytes(b"png")

        self.gestor._publicar(trabajo)

        self.assertEqual([a.name for a in trabajo.artifacts], ["poster.png"])


class Historial(Base):
    def test_sobrevive_al_reinicio(self):
        trabajo = _nuevo_job(self.media)
        trabajo.work.mkdir(parents=True)
        trabajo.status = "done"
        trabajo.progress = 1.0
        poster = trabajo.work / "poster.png"
        poster.write_bytes(b"png")
        self.gestor._artefacto(trabajo, poster, "image")
        self.gestor._guardar(trabajo)

        otro = jobs.JobManager(self.media)

        recuperado = otro.obtener(trabajo.id)
        self.assertIsNotNone(recuperado, "el historial no releyó la corrida")
        self.assertEqual(recuperado.status, "done")
        self.assertEqual([a.name for a in recuperado.artifacts], ["poster.png"])

    def test_si_borraron_la_cache_no_deja_placas_rotas(self):
        trabajo = _nuevo_job(self.media)
        trabajo.work.mkdir(parents=True)
        trabajo.status = "done"
        poster = trabajo.work / "poster.png"
        poster.write_bytes(b"png")
        self.gestor._artefacto(trabajo, poster, "image")
        self.gestor._guardar(trabajo)
        poster.unlink()

        otro = jobs.JobManager(self.media)

        recuperado = otro.obtener(trabajo.id)
        self.assertIsNotNone(recuperado)
        self.assertEqual(recuperado.artifacts, [])

    def test_una_linea_corrupta_no_se_lleva_puesto_el_resto(self):
        trabajo = _nuevo_job(self.media)
        trabajo.work.mkdir(parents=True)
        trabajo.status = "done"
        self.gestor._guardar(trabajo)
        archivo = self.media / jobs.HISTORIAL
        with archivo.open("a", encoding="utf-8") as salida:
            salida.write("esto no es json\n")
            salida.write('{"job": "no es un dict"}\n')

        otro = jobs.JobManager(self.media)

        self.assertIsNotNone(otro.obtener(trabajo.id))

    def test_no_relee_corridas_que_quedaron_a_medias(self):
        trabajo = _nuevo_job(self.media, status="running")
        trabajo.work.mkdir(parents=True)
        self.gestor._guardar(trabajo)  # no escribe: solo persiste terminales

        otro = jobs.JobManager(self.media)

        self.assertIsNone(otro.obtener(trabajo.id))


class Poda(Base):
    def test_nunca_poda_un_job_que_todavia_corre(self):
        gestor = jobs.JobManager(self.media, max_historial=2)
        for numero, estado in enumerate(("done", "done", "done", "running")):
            trabajo = _nuevo_job(
                self.media, job_id=f"j{numero}", status=estado,
                created_at=f"2026-11-0{numero + 1}T00:00:00+00:00",
            )
            gestor.jobs[trabajo.id] = trabajo

        gestor._podar()

        self.assertIn("j3", gestor.jobs, "podó la corrida en curso")
        self.assertIn("j2", gestor.jobs, "podó la corrida más nueva terminada")
        self.assertNotIn("j0", gestor.jobs)
        self.assertNotIn("j1", gestor.jobs)


class CrearJob(Base):
    def test_producto_desconocido(self):
        with self.assertRaises(ValueError):
            self.gestor.crear("no-existe", {})

    def test_sin_el_python_del_repo_avisa_que_falta(self):
        with mock.patch.object(jobs, "planear", return_value=Plan()), mock.patch.object(
            jobs, "python_repo", lambda: self.raiz / "no-existe" / "python.exe"
        ):
            with self.assertRaises(ValueError) as error:
                self.gestor.crear("geocolor", {})

        self.assertIn("Falta el Python del repo", str(error.exception))


if __name__ == "__main__":
    unittest.main()
