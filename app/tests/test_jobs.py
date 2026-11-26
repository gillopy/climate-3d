"""Pruebas del ciclo de vida de un job: correr, fallar, publicar y persistir.

Todo se ejecuta con scripts de mentira en una carpeta temporal: no toca la red
ni los datos reales del repo. Lo que se fija aca es el contrato que ve la UI:
un job termina en `done` con artefactos, falla con un mensaje legible, y el
historial sobrevive al reinicio sin romperse por una linea corrupta.

    .venv\\Scripts\\python.exe -m unittest discover -s app\\tests
"""
from __future__ import annotations

import asyncio
import os
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

try:
    from fastapi.testclient import TestClient

    from app.api import main
except ImportError:  # pragma: no cover - faltan dependencias del venv de la app
    TestClient = None
    main = None


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

    def test_un_corte_por_ctrl_c_termina_cancelado_y_no_como_error(self):
        # Los scripts salen con 130 cuando los corta un Ctrl+C (el snapshot lo hace
        # desde que atrapa KeyboardInterrupt). Un corte del usuario no es una falla
        # del pipeline: la UI tiene que ver `cancelled`, no `error` con un codigo.
        self.escribir_script(
            "cortado.py",
            "import sys\nprint('a medias')\nsys.exit(130)\n",
        )
        trabajo = _nuevo_job(self.media)
        plan = Plan(
            pasos=[Step(kind="render", label="demo", script="cortado.py", args=[])]
        )
        with mock.patch.object(jobs, "planear", return_value=plan):
            self._correr(trabajo)

        textos = [linea.text for linea in trabajo.logs]
        self.assertEqual(trabajo.status, "cancelled", trabajo.logs)
        self.assertIsNone(trabajo.error)
        self.assertIn("cancelado por el usuario", textos)

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

    def test_un_paso_de_descarga_requerido_no_deja_arrancar_el_render(self):
        self.escribir_script("falla_descarga.py", "import sys\nprint('sin autenticacion')\nsys.exit(1)\n")
        self.escribir_script(
            "render.py",
            "from pathlib import Path\n"
            "Path('render-arranco.txt').write_text('no deberia')\n",
        )
        trabajo = _nuevo_job(self.media)
        plan = Plan(
            pasos=[
                Step(kind="download", label="datos", script="falla_descarga.py", args=[], required=True),
                Step(kind="render", label="render", script="render.py", args=[]),
            ],
        )
        with mock.patch.object(jobs, "planear", return_value=plan):
            self._correr(trabajo)

        self.assertEqual(trabajo.status, "error")
        self.assertIn("faltan los datos de entrada", trabajo.error)
        self.assertFalse((self.raiz / "render-arranco.txt").exists())

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

    def test_real_reusa_el_plan_de_crear_si_los_parametros_no_cambiaron(self):
        plan = Plan(
            pasos=[
                Step(
                    kind="render",
                    label="demo",
                    script="render.py",
                    args=[],
                )
            ]
        )
        trabajo = self.gestor._preparar_job("geocolor", {})
        trabajo._plan = plan
        with mock.patch.object(
            jobs,
            "planear",
            side_effect=AssertionError("no debe replanear si _plan ya está armado"),
        ), mock.patch.object(
            self.gestor, "_lanzar", new=mock.AsyncMock(return_value=0)
        ), mock.patch.object(self.gestor, "_publicar"):
            asyncio.run(self.gestor._real(trabajo))

        self.assertEqual(trabajo.progress, 1.0)


class Admision(Base):
    """Tope de admision: la cola no crece con pedidos que nunca van a arrancar.

    La ejecucion ya se serializa con un solo slot, asi que aceptar pedidos sin
    limite no acelera nada: solo deja trabajos esperando para siempre. El tope
    mira unicamente los jobs no terminales.
    """

    def test_un_pedido_sin_parametros_usa_los_defaults_del_catalogo(self):
        # La UI arma el formulario con los defaults del catálogo; la API tiene que
        # comportarse igual. Antes, `params: {}` planeaba otra cosa (y podía fallar el
        # render por falta de la fecha que la UI sí manda).
        gestor = jobs.JobManager(self.media)

        trabajo = gestor._preparar_job("snapshot_paraguay", {})

        self.assertEqual(trabajo.params["capa"], "truecolor")
        self.assertIn("fecha", trabajo.params)
        self.assertIn("margen", trabajo.params)

    def test_un_parametro_explicito_gana_sobre_el_default(self):
        gestor = jobs.JobManager(self.media)

        trabajo = gestor._preparar_job("snapshot_paraguay", {"capa": "falsecolor"})

        self.assertEqual(trabajo.params["capa"], "falsecolor")

    def _gestor_con(self, cuantos: int, **kwargs) -> "jobs.JobManager":
        gestor = jobs.JobManager(self.media, **kwargs)
        for numero in range(cuantos):
            trabajo = _nuevo_job(
                self.media,
                job_id=f"v{numero}",
                status="queued",
                created_at=f"2026-11-0{numero + 1}T00:00:00+00:00",
            )
            gestor.jobs[trabajo.id] = trabajo
        return gestor

    def _crear(self, gestor: "jobs.JobManager") -> "jobs.Job":
        """Crea un pedido sin planear de verdad ni agendar la tarea real."""
        with mock.patch.object(jobs, "python_repo", lambda: Path(sys.executable)), mock.patch.object(
            jobs, "planear", return_value=Plan()
        ), mock.patch.object(gestor, "_agendar_job", side_effect=lambda job, _plan: job):
            return gestor.crear("geocolor", {})

    def test_rechaza_el_pedido_cuando_la_admision_esta_llena(self):
        gestor = self._gestor_con(2, max_admision=2)

        with mock.patch.object(
            jobs, "python_repo", lambda: Path(sys.executable)
        ), mock.patch.object(
            jobs, "planear", side_effect=AssertionError("no se planea un pedido que no entra")
        ):
            with self.assertRaises(jobs.SinCupo) as error:
                gestor.crear("geocolor", {})

        texto = str(error.exception)
        self.assertIn("2 pedidos", texto)
        self.assertIn("limite es 2", texto)
        self.assertIn("cancel", texto)  # dice que hacer, no solo que fallo
        self.assertEqual(gestor.en_curso(), 2, "el pedido rechazado quedo en la lista")

    def test_los_jobs_terminados_no_ocupan_lugar(self):
        gestor = self._gestor_con(0, max_admision=1)
        for numero, estado in enumerate(("done", "error", "cancelled")):
            terminado = _nuevo_job(self.media, job_id=f"t{numero}", status=estado)
            gestor.jobs[terminado.id] = terminado

        self.assertEqual(gestor.en_curso(), 0)
        trabajo = self._crear(gestor)

        self.assertEqual(trabajo.status, "queued")

    def test_el_tope_por_defecto_deja_lanzar_de_a_uno(self):
        # Sin ``CLIMATE3D_MAX_JOBS`` manda el default de la spec.
        limpio = {k: v for k, v in os.environ.items() if k != jobs.MAX_ADMISION_ENV}
        with mock.patch.dict(os.environ, limpio, clear=True):
            self.assertEqual(jobs.JobManager(self.media).max_admision, 4)
        # Un operador con tres pedidos vivos todavia entra con el cuarto.
        lleno = self._gestor_con(3, max_admision=jobs.MAX_ADMISION)
        self.assertEqual(self._crear(lleno).status, "queued")

    def test_cancelar_un_pedido_libera_el_lugar(self):
        # El camino de salida del tope tiene que servir: cancelar desde la lista
        # de corridas devuelve el cupo sin reiniciar la API.
        gestor = self._gestor_con(1, max_admision=1)
        with mock.patch.object(
            jobs, "python_repo", lambda: Path(sys.executable)
        ), mock.patch.object(jobs, "planear", return_value=Plan()):
            with self.assertRaises(jobs.SinCupo):
                gestor.crear("geocolor", {})

            self.assertTrue(gestor.cancelar("v0"))
            trabajo = self._crear(gestor)

        self.assertEqual(trabajo.status, "queued")
        self.assertNotIn("v0", [j.id for j in gestor.listar() if j.status not in jobs.TERMINALES])

    def test_el_tope_se_configura_por_entorno(self):
        with mock.patch.dict(os.environ, {"CLIMATE3D_MAX_JOBS": "2"}):
            self.assertEqual(jobs.JobManager(self.media).max_admision, 2)

    def test_un_valor_de_entorno_invalido_no_bloquea_la_cola(self):
        for crudo in ("", "0", "-3", "muchos"):
            with mock.patch.dict(os.environ, {"CLIMATE3D_MAX_JOBS": crudo}):
                self.assertEqual(
                    jobs.JobManager(self.media).max_admision,
                    jobs.MAX_ADMISION,
                    f"{crudo!r} no deberia dejar la cola cerrada",
                )


@unittest.skipIf(jobs is None, "la API necesita las dependencias del venv de la app")
class RespuestaHttpDeLaAdmision(unittest.TestCase):
    @unittest.skipIf(TestClient is None, "la API necesita las dependencias del venv de la app")
    def test_un_pedido_sin_cupo_es_429_y_no_400_ni_500(self):
        cliente = TestClient(main.app, raise_server_exceptions=False)
        lleno = jobs.SinCupo(
            "Ya hay 4 pedidos en curso o en cola y el limite es 4. "
            "Espera a que termine uno o cancela alguno desde la lista de corridas."
        )

        with mock.patch.object(
            main.gestor, "crear_async", new=mock.AsyncMock(side_effect=lleno)
        ):
            respuesta = cliente.post(
                "/api/jobs", json={"product_id": "geocolor", "params": {}}
            )

        self.assertEqual(respuesta.status_code, 429, respuesta.text)
        self.assertIn("limite es 4", respuesta.json()["detail"])
        self.assertIn("Retry-After", respuesta.headers)


@unittest.skipIf(jobs is None, "la API necesita las dependencias del venv de la app")
class StreamDeProgreso(unittest.IsolatedAsyncioTestCase):
    """Cotas del stream SSE: un cliente que deja de leer no retiene todo."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.media = Path(self._tmp.name)
        self.media.mkdir(exist_ok=True)
        self.gestor = jobs.JobManager(self.media)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _job_vivo(self, job_id: str = "sse") -> "jobs.Job":
        trabajo = _nuevo_job(self.media, job_id=job_id, status="running")
        self.gestor.jobs[trabajo.id] = trabajo
        return trabajo

    async def _drenar(self, flujo, cuantos: int) -> list[dict]:
        """Lee `cuantos` eventos con un solo tope de espera (no uno por evento)."""

        async def leer():
            return [await flujo.__anext__() for _ in range(cuantos)]

        return await asyncio.wait_for(leer(), 5)

    async def test_al_dia_entrega_todos_los_eventos_en_orden(self):
        # El contrato de los eventos que si se entregan no cambia: snapshot
        # primero y despues todo lo emitido, en orden.
        trabajo = self._job_vivo()
        flujo = self.gestor.seguir(trabajo.id)

        primero = await asyncio.wait_for(flujo.__anext__(), 1)
        self.assertEqual(primero["type"], "snapshot")
        for numero in range(3):
            self.gestor._emitir(trabajo, {"type": "log", "line": {"n": numero}})

        recibidos = await self._drenar(flujo, 3)

        self.assertEqual([e["line"]["n"] for e in recibidos], [0, 1, 2])
        await flujo.aclose()

    async def test_el_buffer_de_una_conexion_tiene_cota_y_deja_lo_mas_nuevo(self):
        trabajo = self._job_vivo()
        flujo = self.gestor.seguir(trabajo.id)
        self.assertEqual((await asyncio.wait_for(flujo.__anext__(), 1))["type"], "snapshot")

        total = jobs.SSE_MAXSIZE + 10
        for numero in range(total):
            self.gestor._emitir(trabajo, {"type": "log", "line": {"n": numero}})

        cola = next(iter(trabajo.subs))
        self.assertEqual(cola.qsize(), jobs.SSE_MAXSIZE)
        recibidos = await self._drenar(flujo, jobs.SSE_MAXSIZE)
        # Se descarta el evento mas viejo de esa conexion, no el mas nuevo.
        self.assertEqual(
            [e["line"]["n"] for e in recibidos],
            list(range(total - jobs.SSE_MAXSIZE, total)),
        )
        await flujo.aclose()

    async def test_no_abre_mas_conexiones_que_el_tope_por_job(self):
        trabajo = self._job_vivo()
        abiertas = []
        for _ in range(jobs.SSE_MAX_SUBS):
            flujo = self.gestor.seguir(trabajo.id)
            self.assertEqual(
                (await asyncio.wait_for(flujo.__anext__(), 1))["type"], "snapshot"
            )
            abiertas.append(flujo)
        self.assertFalse(self.gestor.admite_suscriptor(trabajo))

        # El corte por cupo lo decide el endpoint (`main.eventos`) ANTES de abrir la
        # respuesta: si se re-chequeara aca, la conexion ya estaria abierta y solo
        # podria abortarse a mitad de stream en vez de devolver un 429 limpio.
        for flujo in abiertas:
            await flujo.aclose()
        self.assertEqual(trabajo.subs, set(), "el cupo no se libera al cerrar la conexion")
        self.assertTrue(self.gestor.admite_suscriptor(trabajo))

    def test_el_cupo_de_sse_se_reserva_sin_pasarse_del_tope(self):
        # Control y registro en la misma llamada: dos aperturas simultáneas no
        # pueden ver el mismo conteo y abrir una conexión de más.
        trabajo = self._job_vivo()
        reservadas = [self.gestor.reservar_suscriptor(trabajo) for _ in range(jobs.SSE_MAX_SUBS)]

        self.assertTrue(all(cola is not None for cola in reservadas))
        self.assertIsNone(self.gestor.reservar_suscriptor(trabajo))
        self.assertEqual(len(trabajo.subs), jobs.SSE_MAX_SUBS)

        for cola in reservadas:
            trabajo.subs.discard(cola)
        self.assertIsNotNone(self.gestor.reservar_suscriptor(trabajo))

    async def test_una_conexion_lenta_no_le_saca_eventos_a_la_que_lee(self):
        # El descarte es por conexion: el que lee al dia no pierde nada porque
        # otra pestaña dejada abierta se este llenando.
        with mock.patch.object(jobs, "SSE_MAXSIZE", 8):
            trabajo = self._job_vivo()
            lenta = self.gestor.seguir(trabajo.id)
            rapida = self.gestor.seguir(trabajo.id)
            await asyncio.wait_for(lenta.__anext__(), 1)
            await asyncio.wait_for(rapida.__anext__(), 1)

            total = 18
            for numero in range(total):
                self.gestor._emitir(trabajo, {"type": "log", "line": {"n": numero}})
                leido = await asyncio.wait_for(rapida.__anext__(), 1)
                self.assertEqual(leido["line"]["n"], numero)

            # La conexion que no leyo guardo los ultimos eventos y conto los perdidos.
            cola_lenta = [c for c in trabajo.subs if c.qsize() == 8]
            self.assertTrue(cola_lenta, "la conexion lenta no quedo acotada")
            self.assertEqual(cola_lenta[0].descartados, total - 8)
            await lenta.aclose()
            await rapida.aclose()


if __name__ == "__main__":
    unittest.main()
