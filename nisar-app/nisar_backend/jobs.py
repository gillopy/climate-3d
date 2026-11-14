"""Cola de trabajos NISAR y stream de progreso.

Un pedido nunca bloquea: crear un job devuelve un id, el trabajo corre en
background y el resultado se sigue por SSE. Cada job ejecuta los scripts del
repo (``descargar/nisar.py`` + ``prototipos/nisar_*.py``) con el Python del
pipeline, captura el stdout linea por linea y publica los artefactos que dejan
en su carpeta de trabajo.

La carpeta de trabajo es una cache compartida por pedidos identicos: si el
render ya existe, el script lo saltea en vez de empezar de cero.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator

import psutil

from .config import RAIZ_REPO, entorno_pipeline, python_repo
from .recipes import PRODUCT_ID, PRODUCT_NAME, planear
from .schemas import Artifact, JobSnapshot, JobSummary, LogLine

TERMINALES = ("done", "error", "cancelled")

# Una linea por corrida terminada. Es lo que hace que el listado sobreviva a un
# reinicio de la API: la cache de renders ya estaba en disco, el registro no.
HISTORIAL = "historial.jsonl"

# Subir esto invalida la cache de jobs: la firma tiene que representar la receta
# entera (producto, escena, caja, resolucion).
RECETA_VERSION = 1

# Reparto del progreso entre etapas. La descarga y el render son lo que pesa.
_PESO = {"download": 0.4, "render": 0.6}

# Cuanto se espera a que cierren los pipes despues de cancelar.
_GRACIA_CANCEL = 6.0

# Codigos con los que sale un hijo cuando lo corta un Ctrl+C.
_CORTES = {130, -2, 0xC000013A, -1073741510}


def _matar_arbol(proc: subprocess.Popen[bytes]) -> None:
    """Mata el proceso y todos sus hijos.

    Los scripts lanzan hijos que heredan el stdout: si solo se mata al padre, el
    pipe sigue abierto y el job queda colgado.
    """
    try:
        padre = psutil.Process(proc.pid)
        victimas = padre.children(recursive=True) + [padre]
    except psutil.NoSuchProcess:
        return
    for proceso in victimas:
        try:
            proceso.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    try:
        padre.wait(timeout=3)
    except (psutil.TimeoutExpired, psutil.NoSuchProcess):
        pass


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _nivel_de(linea: str) -> str:
    """Nivel del log para una linea de un script.

    Los descargadores y renders avisan lo no fatal con «aviso:»; eso no puede
    entrar como ``info``, porque es justo lo que hay que mirar.
    """
    texto = linea.strip().lower()
    if texto.startswith(("aviso:", "aviso :", "warning", "warn:")):
        return "warn"
    return "info"


def _epoch(iso: str | None) -> float:
    """Marca de tiempo ISO -> segundos epoch. Sin fecha, 0 (todo cuenta)."""
    if not iso:
        return 0.0
    try:
        return datetime.fromisoformat(iso).timestamp()
    except (TypeError, ValueError):
        return 0.0


@dataclass
class Job:
    id: str
    product_id: str
    product_name: str
    params: dict[str, Any]
    mode: str
    status: str = "queued"
    progress: float = 0.0
    stage: str = "en cola"
    created_at: str = field(default_factory=_ahora)
    started_at: str | None = None
    finished_at: str | None = None
    logs: list[LogLine] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
    plan: list[str] = field(default_factory=list)
    error: str | None = None
    dir: Path | None = None
    proc: subprocess.Popen[bytes] | None = None
    cancelar: asyncio.Event = field(default_factory=asyncio.Event)
    subs: set[asyncio.Queue] = field(default_factory=set)

    @property
    def work(self) -> Path:
        assert self.dir is not None
        return self.dir

    def snapshot(self) -> JobSnapshot:
        return JobSnapshot(
            id=self.id,
            product_id=self.product_id,
            product_name=self.product_name,
            params=self.params,
            mode=self.mode,  # type: ignore[arg-type]
            status=self.status,  # type: ignore[arg-type]
            progress=round(self.progress, 4),
            stage=self.stage,
            created_at=self.created_at,
            started_at=self.started_at,
            finished_at=self.finished_at,
            logs=list(self.logs),
            artifacts=list(self.artifacts),
            plan=list(self.plan),
            error=self.error,
        )

    def resumen(self) -> JobSummary:
        return JobSummary(
            id=self.id,
            product_id=self.product_id,
            product_name=self.product_name,
            mode=self.mode,  # type: ignore[arg-type]
            status=self.status,  # type: ignore[arg-type]
            progress=round(self.progress, 4),
            stage=self.stage,
            created_at=self.created_at,
            started_at=self.started_at,
            finished_at=self.finished_at,
            error=self.error,
        )


class JobManager:
    def __init__(self, media_root: Path, max_historial: int = 40) -> None:
        self.media_root = media_root
        self.jobs: dict[str, Job] = {}
        self.max_historial = max_historial
        # Un solo worker: los pedidos se encolan en vez de pelearse la maquina.
        self._un_slot = asyncio.Semaphore(1)
        self._tareas: set[asyncio.Task] = set()
        self._cargar_historial()

    # --- API publica -----------------------------------------------------
    def crear(self, product_id: str, params: dict[str, Any]) -> Job:
        if product_id != PRODUCT_ID:
            raise ValueError(f"Producto desconocido: {product_id}")

        firma_params = {k: v for k, v in params.items() if k != "descargar"}
        firma = hashlib.sha1(
            f"v{RECETA_VERSION}|{product_id}|"
            f"{json.dumps(firma_params, sort_keys=True, default=str)}".encode("utf-8")
        ).hexdigest()[:12]
        job = Job(
            id=uuid.uuid4().hex[:12],
            product_id=PRODUCT_ID,
            product_name=PRODUCT_NAME,
            params=params,
            mode="real",
            dir=self.media_root / "cache" / firma,
        )

        if not python_repo().is_file():
            raise ValueError(
                f"Falta el Python del repo: {python_repo()}. "
                "Sin eso no se puede ejecutar el pipeline."
            )
        try:
            job.plan = [p.label for p in planear(PRODUCT_ID, params, job.work).pasos]
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        self.jobs[job.id] = job
        self._podar()

        tarea = asyncio.create_task(self._correr(job))
        self._tareas.add(tarea)
        tarea.add_done_callback(self._tareas.discard)
        return job

    def obtener(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def listar(self) -> list[Job]:
        return sorted(self.jobs.values(), key=lambda j: j.created_at, reverse=True)

    def listar_resumen(self) -> list[JobSummary]:
        return [job.resumen() for job in self.listar()]

    def cancelar(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if job is None or job.status in TERMINALES:
            return False
        job.cancelar.set()
        if job.proc is not None and job.proc.returncode is None:
            _matar_arbol(job.proc)
            try:
                job.proc.kill()
            except OSError:
                pass
        if job.status == "queued":
            job.status = "cancelled"
            job.stage = "cancelado antes de arrancar"
            job.finished_at = _ahora()
            self._guardar(job)
            self._emitir(job, {"type": "cancelled"})
        else:
            job.stage = "cancelando..."
        return True

    async def seguir(self, job_id: str) -> AsyncIterator[dict[str, Any]]:
        job = self.jobs[job_id]
        cola: asyncio.Queue = asyncio.Queue()
        job.subs.add(cola)
        try:
            yield {"type": "snapshot", "job": job.snapshot().model_dump()}
            if job.status in TERMINALES:
                yield {"type": "closed"}
                return
            while True:
                try:
                    evento = await asyncio.wait_for(cola.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield {"type": "ping"}
                    continue
                yield evento
                if evento["type"] in ("done", "error", "cancelled"):
                    return
        finally:
            job.subs.discard(cola)

    # --- historial -------------------------------------------------------
    def _cargar_historial(self) -> None:
        """Relee las corridas terminadas de la sesion anterior."""
        archivo = self.media_root / HISTORIAL
        if not archivo.is_file():
            return
        try:
            lineas = archivo.read_text(encoding="utf-8").splitlines()
        except OSError:
            return

        vistas: dict[str, Job] = {}
        for linea in lineas:
            if not linea.strip():
                continue
            try:
                job = self._desde_historial(json.loads(linea))
            except (TypeError, ValueError, KeyError):
                continue  # una linea rota no se lleva puesto el resto
            if job is not None:
                vistas[job.id] = job  # la ultima linea de un id es la mas fresca

        recientes = sorted(vistas.values(), key=lambda j: j.created_at)[-self.max_historial :]
        for job in recientes:
            self.jobs[job.id] = job
        if len(vistas) > self.max_historial:
            self._reescribir_historial()

    def _desde_historial(self, dato: Any) -> Job | None:
        if not isinstance(dato, dict):
            return None
        crudo = dato.get("job")
        relativa = dato.get("dir")
        if not isinstance(crudo, dict) or not isinstance(relativa, str):
            return None
        carpeta = (self.media_root / relativa).resolve()
        try:
            carpeta.relative_to(self.media_root.resolve())
        except ValueError:
            return None  # el archivo no puede sacarnos de media/

        snap = JobSnapshot.model_validate(crudo)
        if snap.status not in TERMINALES:
            return None
        existe = carpeta.is_dir()
        artefactos = [
            artefacto
            for artefacto in snap.artifacts
            if existe and self._archivo(artefacto.url).is_file()
        ]
        return Job(
            id=snap.id,
            product_id=snap.product_id,
            product_name=snap.product_name,
            params=snap.params,
            mode=snap.mode,
            status=snap.status,
            progress=snap.progress,
            stage=snap.stage,
            created_at=snap.created_at,
            started_at=snap.started_at,
            finished_at=snap.finished_at,
            logs=list(snap.logs),
            artifacts=artefactos,
            plan=list(snap.plan),
            error=snap.error,
            dir=carpeta,
        )

    def _archivo(self, url: str) -> Path:
        """``/media/cache/<firma>/x.png`` -> ruta real dentro de media."""
        prefijo = "/media/"
        relativa = url[len(prefijo) :] if url.startswith(prefijo) else url.lstrip("/")
        return (self.media_root / relativa).resolve()

    def _guardar(self, job: Job) -> None:
        """Anota una corrida terminada: el listado tiene que sobrevivir al reinicio."""
        if job.dir is None or job.status not in TERMINALES:
            return
        try:
            relativa = job.dir.relative_to(self.media_root).as_posix()
        except ValueError:
            return
        linea = json.dumps(
            {"job": job.snapshot().model_dump(), "dir": relativa},
            ensure_ascii=False,
        )
        try:
            with (self.media_root / HISTORIAL).open("a", encoding="utf-8") as archivo:
                archivo.write(linea + "\n")
        except OSError:
            pass  # la lista en memoria sigue viva; el disco es solo el seguro

    def _reescribir_historial(self) -> None:
        """Deja en disco solo las corridas que la lista conserva."""
        lineas: list[str] = []
        for job in sorted(self.jobs.values(), key=lambda j: j.created_at):
            if job.dir is None or job.status not in TERMINALES:
                continue
            try:
                relativa = job.dir.relative_to(self.media_root).as_posix()
            except ValueError:
                continue
            lineas.append(
                json.dumps(
                    {"job": job.snapshot().model_dump(), "dir": relativa},
                    ensure_ascii=False,
                )
            )
        try:
            (self.media_root / HISTORIAL).write_text(
                "".join(f"{linea}\n" for linea in lineas), encoding="utf-8"
            )
        except OSError:
            pass

    # --- interno ---------------------------------------------------------
    def _podar(self) -> None:
        """Olvida jobs viejos de la lista. Nunca borra la cache de renders."""
        if len(self.jobs) <= self.max_historial:
            return
        sobran = len(self.jobs) - self.max_historial
        terminados = [j for j in self.listar() if j.status in TERMINALES]
        for viejo in terminados[max(0, len(terminados) - sobran) :]:
            self.jobs.pop(viejo.id, None)

    def _emitir(self, job: Job, evento: dict[str, Any]) -> None:
        for cola in list(job.subs):
            cola.put_nowait(evento)

    def _log(self, job: Job, texto: str, level: str = "info") -> None:
        linea = LogLine(at=_ahora(), level=level, text=texto)  # type: ignore[arg-type]
        job.logs.append(linea)
        del job.logs[:-400]  # el historial de la UI no crece sin limite
        self._emitir(job, {"type": "log", "line": linea.model_dump()})

    def _progreso(self, job: Job, valor: float, etapa: str) -> None:
        job.progress = max(0.0, min(valor, 1.0))
        job.stage = etapa
        self._emitir(job, {"type": "progress", "progress": job.progress, "stage": etapa})

    def _artefacto(self, job: Job, path: Path, kind: str) -> None:
        try:
            relativa = path.relative_to(self.media_root).as_posix()
        except ValueError:
            return
        url = f"/media/{relativa}"
        if any(a.url == url for a in job.artifacts):
            return
        artefacto = Artifact(
            name=path.name,
            url=url,
            kind=kind,  # type: ignore[arg-type]
            bytes=path.stat().st_size if path.exists() else 0,
        )
        job.artifacts.append(artefacto)
        self._emitir(job, {"type": "artifact", "artifact": artefacto.model_dump()})

    def _publicar(self, job: Job) -> None:
        """Publica lo que dejo esta corrida en la raiz de su carpeta.

        Los productos NISAR escriben PNG, JSON de estadisticas y GeoTIFF en la
        raiz del work. La carpeta es cache compartida: se publica lo nuevo y, si
        el render ya estaba hecho, el resultado vigente.
        """
        posters = sorted(job.work.glob("*.png"), key=lambda p: p.stat().st_mtime)
        inicio = _epoch(job.started_at)
        nuevos = [p for p in posters if p.stat().st_mtime >= inicio - 1.0]
        for poster in (nuevos or posters[-1:]):
            self._artefacto(job, poster, "image")
        for patron in ("*.json", "*.tif", "*.tiff"):
            for archivo in sorted(job.work.glob(patron)):
                self._artefacto(job, archivo, "file")

    async def _correr(self, job: Job) -> None:
        async with self._un_slot:
            if job.status == "cancelled":
                return
            job.status = "running"
            job.started_at = _ahora()
            try:
                assert job.dir is not None
                job.dir.mkdir(parents=True, exist_ok=True)
                self._log(job, f"job {job.id} | {job.product_id} | modo={job.mode}")
                await self._real(job)

                self._publicar(job)
                if not job.artifacts:
                    raise RuntimeError(
                        "el pipeline termino pero no dejo ninguna imagen; "
                        "revisa el log de arriba"
                    )
                job.status = "done"
                job.finished_at = _ahora()
                self._progreso(job, 1.0, "listo")
                self._log(job, f"listo: {len(job.artifacts)} artefacto(s)")
                self._emitir(job, {"type": "done", "job": job.snapshot().model_dump()})
            except asyncio.CancelledError:
                job.status = "cancelled"
                job.finished_at = _ahora()
                job.stage = "cancelado"
                self._log(job, "cancelado por el usuario", "warn")
                self._emitir(job, {"type": "cancelled"})
            except Exception as exc:  # noqa: BLE001 - se reporta tal cual a la UI
                job.status = "error"
                detalle = str(exc).strip() or "sin detalle"
                job.error = (
                    detalle
                    if isinstance(exc, (RuntimeError, ValueError))
                    else f"{type(exc).__name__}: {detalle}"
                )
                job.finished_at = _ahora()
                job.stage = "error"
                self._log(job, job.error, "error")
                self._emitir(job, {"type": "error", "error": job.error})
            finally:
                job.proc = None
                self._guardar(job)

    # --- modo real -------------------------------------------------------
    async def _real(self, job: Job) -> None:
        plan = planear(job.product_id, job.params, job.work)
        pasos = list(plan.pasos)
        if not pasos:
            raise RuntimeError("la receta no genero ningun paso")

        job.plan = [p.label for p in pasos]
        self._emitir(job, {"type": "snapshot", "job": job.snapshot().model_dump()})

        total_peso = sum(_PESO.get(p.kind, 0.2) for p in pasos)
        base = 0.0

        for numero, paso in enumerate(pasos, start=1):
            span = _PESO.get(paso.kind, 0.2) / total_peso
            etiqueta = f"[{numero}/{len(pasos)}] {paso.label}"
            codigo = await self._lanzar(job, paso, list(paso.args), base, span, etiqueta)
            if codigo != 0:
                # NISAR no tiene "descarga de rescate": si el .h5 no baja, el
                # render no tiene nada que leer. Se aborta con el motivo.
                raise RuntimeError(
                    f"`{paso.script}` salio con codigo {codigo}. "
                    "Mira el log de arriba."
                )
            base += span
            self._progreso(job, base, f"{paso.label}: ok")

    async def _lanzar(
        self,
        job: Job,
        paso: Any,
        args: list[str],
        base: float,
        span: float,
        etiqueta: str,
    ) -> int:
        script = RAIZ_REPO / paso.script
        if not script.is_file():
            raise RuntimeError(f"no existe el script del repo: {paso.script}")

        cmd = [str(python_repo()), str(script), *args]
        self._log(job, etiqueta)
        self._log(job, "  " + " ".join([Path(cmd[0]).name, *cmd[1:]]))
        self._progreso(job, base, etiqueta)

        # ``subprocess.Popen`` + un hilo lector, no ``asyncio.create_subprocess_exec``:
        # en Windows el loop Selector (el que arma uvicorn con ``--reload``) no
        # sabe crear subprocesos y tira ``NotImplementedError`` sin mensaje.
        loop = asyncio.get_running_loop()
        cola: asyncio.Queue[bytes | None] = asyncio.Queue()

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(RAIZ_REPO),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=entorno_pipeline(),
            )
        except OSError as exc:
            raise RuntimeError(
                f"no se pudo ejecutar `{cmd[0]}`: {exc}. "
                "Revisa que el venv del repo exista y que el script sea ejecutable."
            ) from exc
        job.proc = proc
        assert proc.stdout is not None

        def bombear() -> None:
            # El hilo alimenta la cola para que el loop nunca se cuelgue esperando
            # un pipe que un hijo huerfano dejo abierto.
            try:
                for crudo in iter(proc.stdout.readline, b""):
                    loop.call_soon_threadsafe(cola.put_nowait, crudo)
            except (ValueError, OSError):
                pass  # el pipe se cerro mientras leiamos
            finally:
                try:
                    loop.call_soon_threadsafe(cola.put_nowait, None)
                except RuntimeError:
                    pass  # el loop ya cerro: no hay a quien avisarle
                try:
                    proc.stdout.close()  # type: ignore[union-attr]
                except (AttributeError, OSError, ValueError):
                    pass

        hilo = threading.Thread(target=bombear, name=f"job-{job.id}", daemon=True)
        hilo.start()
        vistos = 0
        limite: float | None = None

        try:
            while True:
                try:
                    crudo = await asyncio.wait_for(cola.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    if not job.cancelar.is_set():
                        continue
                    if limite is None:
                        limite = time.monotonic() + _GRACIA_CANCEL
                    _matar_arbol(proc)
                    if time.monotonic() > limite:
                        self._log(job, "corte forzado: el proceso no cerro el pipe", "warn")
                        break
                    continue

                if crudo is None:
                    break

                if job.cancelar.is_set():
                    _matar_arbol(proc)

                linea = crudo.decode("utf-8", "replace").rstrip()
                if not linea:
                    continue
                self._log(job, linea[:600], _nivel_de(linea))
                vistos += 1
                if paso.expected > 0:
                    self._progreso(job, base + span * min(0.95, vistos / paso.expected), etiqueta)

            codigo = await asyncio.wait_for(asyncio.to_thread(proc.wait), timeout=10)
        finally:
            job.proc = None

        if job.cancelar.is_set():
            raise asyncio.CancelledError
        if codigo in _CORTES:
            job.cancelar.set()
            raise asyncio.CancelledError
        return codigo
