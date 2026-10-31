"""Cola de trabajos y stream de progreso.

Dos modos:

- ``real``: corre los scripts del repo con el Python del repo (``.venv``), les
  sigue el stdout linea por linea y publica los archivos que dejan.
- ``preview``: dibuja un campo sintetico, para probar la app sin datos.

Un pedido nunca bloquea: crear un job devuelve un id; el trabajo corre en
background y el resultado se sigue por SSE.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator

import psutil

from .catalog import get_product
from .recipes import (
    PRODUCTOS_ECMWF,
    RAIZ_REPO,
    SinRed,
    planear,
    python_repo,
    resolver_corrida,
)
from .schemas import Artifact, JobSnapshot, LogLine

TERMINALES = ("done", "error", "cancelled")

# Subir esto invalida la cache: la firma tiene que representar la receta entera,
# incluido como se dibuja (paleta, fondo, capas), no solo los parametros.
RECETA_VERSION = 14

# Reparto del progreso entre etapas. La descarga y el render son lo que pesa.
_PESO = {"download": 0.4, "render": 0.5, "animate": 0.1}

# Cuanto se espera a que cierren los pipes despues de cancelar.
_GRACIA_CANCEL = 6.0


def _matar_arbol(proc: asyncio.subprocess.Process) -> None:
    """Mata el proceso y todos sus hijos.

    Los scripts de render lanzan un hijo por lote y ese hijo hereda el stdout:
    si solo se mata al padre, el pipe sigue abierto y el job queda colgado.
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
    proc: asyncio.subprocess.Process | None = None
    cancelar: asyncio.Event = field(default_factory=asyncio.Event)
    subs: set[asyncio.Queue] = field(default_factory=set)

    @property
    def work(self) -> Path:
        """Carpeta de trabajo, compartida por recetas identicas.

        Los scripts del repo ya saben retomar: si el PNG existe y el sello de
        render no cambio, lo saltean. Reusar la carpeta es lo que hace que un
        render de horas se pueda continuar en vez de empezar de cero.
        """
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


class JobManager:
    def __init__(self, media_root: Path, max_historial: int = 40) -> None:
        self.media_root = media_root
        self.jobs: dict[str, Job] = {}
        self.max_historial = max_historial
        # Un solo worker: los pedidos se encolan en vez de pelearse la maquina.
        self._un_slot = asyncio.Semaphore(1)
        self._tareas: set[asyncio.Task] = set()

    # --- API publica -----------------------------------------------------
    def crear(self, product_id: str, params: dict[str, Any]) -> Job:
        producto = get_product(product_id)
        if producto is None:
            raise ValueError(f"Producto desconocido: {product_id}")

        job_id = uuid.uuid4().hex[:12]
        # `descargar` no cambia el resultado del render: se excluye de la firma
        # para que activar la descarga no invalide cuadros ya hechos.
        firma_params = {k: v for k, v in params.items() if k != "descargar"}
        firma = hashlib.sha1(
            f"v{RECETA_VERSION}|{product_id}|"
            f"{json.dumps(firma_params, sort_keys=True, default=str)}".encode("utf-8")
        ).hexdigest()[:12]
        job = Job(
            id=job_id,
            product_id=producto.id,
            product_name=producto.name,
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
            job.plan = [p.label for p in planear(product_id, params, job.work).pasos]
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        self.jobs[job_id] = job
        self._podar()

        tarea = asyncio.create_task(self._correr(job))
        self._tareas.add(tarea)
        tarea.add_done_callback(self._tareas.discard)
        return job

    def obtener(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def listar(self) -> list[Job]:
        return sorted(self.jobs.values(), key=lambda j: j.created_at, reverse=True)

    def cancelar(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if job is None or job.status in TERMINALES:
            return False
        job.cancelar.set()
        if job.proc is not None and job.proc.returncode is None:
            _matar_arbol(job.proc)
            try:
                job.proc.kill()
            except ProcessLookupError:
                pass
        if job.status == "queued":
            job.status = "cancelled"
            job.stage = "cancelado antes de arrancar"
            job.finished_at = _ahora()
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

    # --- interno ---------------------------------------------------------
    def _podar(self) -> None:
        """Olvida jobs viejos de la lista. Nunca borra la cache de renders."""
        if len(self.jobs) <= self.max_historial:
            return
        terminados = [j for j in self.listar() if j.status in TERMINALES]
        for viejo in terminados[: max(0, len(self.jobs) - self.max_historial)]:
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

    def _frames_dir(self, job: Job) -> Path | None:
        """Carpeta de cuadros: la primera con `cuadro_*.png` dentro del work."""
        candidatas = [
            carpeta
            for carpeta in job.work.rglob("*")
            if carpeta.is_dir() and next(carpeta.glob("cuadro_*.png"), None) is not None
        ]
        if not candidatas:
            return None
        return max(
            candidatas,
            key=lambda c: max(f.stat().st_mtime for f in c.glob("cuadro_*.png")),
        )

    def _publicar(self, job: Job) -> None:
        frames = self._frames_dir(job)
        if frames is not None:
            cuadros = sorted(frames.glob("cuadro_*.png"))
            if cuadros:
                self._artefacto(job, cuadros[0], "image")
                if len(cuadros) > 1:
                    self._artefacto(job, cuadros[-1], "image")
        for patron, kind in (("*.mp4", "video"), ("*.gif", "video")):
            for archivo in sorted(job.work.rglob(patron)):
                self._artefacto(job, archivo, kind)
        # Posters sueltos (true color, MUR realista): PNG en la raiz del work.
        posters = sorted(
            job.work.glob("*.png"),
            key=lambda p: p.stat().st_mtime,
        )
        for poster in posters[-3:]:
            self._artefacto(job, poster, "image")

    async def _correr(self, job: Job) -> None:
        async with self._un_slot:
            if job.status == "cancelled":
                return
            job.status = "running"
            job.started_at = _ahora()
            assert job.dir is not None
            job.dir.mkdir(parents=True, exist_ok=True)
            try:
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
                job.error = (
                    str(exc)
                    if isinstance(exc, (RuntimeError, ValueError, SinRed))
                    else f"{type(exc).__name__}: {exc}"
                )
                job.finished_at = _ahora()
                job.stage = "error"
                self._log(job, job.error, "error")
                self._emitir(job, {"type": "error", "error": job.error})
            finally:
                job.proc = None

    # --- modo real -------------------------------------------------------
    async def _resolver_corrida(self, job: Job) -> None:
        """Ubica la corrida ECMWF realmente publicada antes de planear."""
        self._progreso(job, 0.01, "verificando la corrida publicada")
        try:
            ajustado, aviso = await asyncio.to_thread(resolver_corrida, job.params)
        except SinRed as exc:
            self._log(
                job,
                f"no pude verificar la corrida publicada ({exc}); sigo con la pedida",
                "warn",
            )
            return
        if aviso:
            self._log(job, aviso, "warn")
        if ajustado != job.params:
            job.params = ajustado
            self._emitir(job, {"type": "snapshot", "job": job.snapshot().model_dump()})

    async def _real(self, job: Job) -> None:
        if job.product_id in PRODUCTOS_ECMWF:
            await self._resolver_corrida(job)

        plan = planear(job.product_id, job.params, job.work)
        pasos = list(plan.pasos)
        if not pasos:
            raise RuntimeError("la receta no genero ningun paso")

        job.plan = [p.label for p in pasos]
        self._emitir(job, {"type": "snapshot", "job": job.snapshot().model_dump()})

        total_peso = sum(_PESO.get(p.kind, 0.2) for p in pasos)
        base = 0.0
        descargado = any(p.kind == "download" for p in pasos)

        for numero, paso in enumerate(pasos, start=1):
            span = _PESO.get(paso.kind, 0.2) / total_peso
            etiqueta = f"[{numero}/{len(pasos)}] {paso.label}"

            if paso.kind == "animate":
                frames = self._frames_dir(job)
                if frames is None:
                    self._log(job, "no hay cuadros para animar; se omite el video", "warn")
                    base += span
                    continue
                if len(list(frames.glob("cuadro_*.png"))) < 2:
                    self._log(job, "un solo cuadro: no hay animacion que armar", "warn")
                    base += span
                    continue
                args = [str(frames) if a == "{frames}" else a for a in paso.args]
            else:
                args = list(paso.args)
                if "{crudo}" in args:
                    crudos = sorted(job.work.rglob("crudo_*.jpg"))
                    if not crudos:
                        raise RuntimeError(
                            "no hay crudos de SST para el poster realista; "
                            "activa 'Forzar descarga' para bajarlos"
                        )
                    args = [str(crudos[0]) if a == "{crudo}" else a for a in args]

            codigo = await self._lanzar(job, paso, args, base, span, etiqueta)

            if codigo != 0 and paso.kind == "download":
                # El descargador devuelve 1 si algun slot no existe (huecos de la
                # grilla o horas que todavia no se publicaron). No es fatal: el
                # render trabaja con lo que si bajo.
                self._log(
                    job,
                    f"la descarga cerro con codigo {codigo}: sigo con lo que hay",
                    "warn",
                )
                codigo = 0
            elif codigo != 0:
                if plan.descarga is not None and not descargado:
                    # Faltaban datos: se baja lo que pida la receta y se
                    # reintenta el render una sola vez.
                    self._log(job, "faltan datos para renderizar: descargo y reintento", "warn")
                    rescate = await self._lanzar(
                        job,
                        plan.descarga,
                        list(plan.descarga.args),
                        base,
                        span * 0.5,
                        "descarga de rescate",
                    )
                    descargado = True
                    if rescate != 0:
                        self._log(
                            job,
                            f"la descarga de rescate cerro con codigo {rescate}",
                            "warn",
                        )
                    codigo = await self._lanzar(job, paso, args, base, span, etiqueta)

                if codigo != 0:
                    pista = (
                        " Puede que esa fecha no exista en el archivo de la fuente."
                        if descargado
                        else ""
                    )
                    raise RuntimeError(
                        f"`{paso.script}` salio con codigo {codigo}. "
                        f"Mira el log de arriba.{pista}"
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

        entorno = os.environ.copy()
        entorno.update(
            PYTHONUTF8="1",
            PYTHONIOENCODING="utf-8",
            PYTHONUNBUFFERED="1",
        )

        cmd = [str(python_repo()), str(script), *args]
        self._log(job, etiqueta)
        self._log(job, "  " + " ".join([Path(cmd[0]).name, *cmd[1:]]))
        self._progreso(job, base, etiqueta)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(RAIZ_REPO),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=entorno,
        )
        job.proc = proc
        assert proc.stdout is not None

        # Un hilo lector alimenta la cola: asi el loop principal nunca se cuelga
        # esperando un pipe que un hijo huerfano dejo abierto.
        cola: asyncio.Queue[bytes | None] = asyncio.Queue()

        async def bombear() -> None:
            assert proc.stdout is not None
            async for crudo in proc.stdout:
                cola.put_nowait(crudo)
            cola.put_nowait(None)

        bomba = asyncio.create_task(bombear())
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
                self._log(job, linea[:600])
                vistos += 1
                if paso.expected > 0:
                    self._progreso(job, base + span * min(0.95, vistos / paso.expected), etiqueta)

            codigo = await asyncio.wait_for(proc.wait(), timeout=10)
        finally:
            bomba.cancel()
            job.proc = None

        if job.cancelar.is_set():
            raise asyncio.CancelledError
        return codigo










