"""Cola de trabajos y stream de progreso.

La regla de oro: un pedido nunca bloquea. Crear un job devuelve un id al toque;
el trabajo corre en background y el resultado se sigue por SSE. Con un semaforo
de 1 se ve el comportamiento real: los pedidos se encolan en vez de pelearse la
maquina.
"""
from __future__ import annotations

import asyncio
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator

from . import render
from .catalog import get_product
from .schemas import Artifact, JobSnapshot, LogLine

TERMINALES = ("done", "error", "cancelled")


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
    error: str | None = None
    dir: Path | None = None
    cancelar: asyncio.Event = field(default_factory=asyncio.Event)
    subs: set[asyncio.Queue] = field(default_factory=set)

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
            error=self.error,
        )


class JobManager:
    def __init__(self, media_root: Path, max_historial: int = 40) -> None:
        self.media_root = media_root
        self.jobs: dict[str, Job] = {}
        self.max_historial = max_historial
        self._un_slot = asyncio.Semaphore(1)
        self._tareas: set[asyncio.Task] = set()

    # --- API publica -----------------------------------------------------
    def crear(self, product_id: str, params: dict[str, Any], mode: str) -> Job:
        producto = get_product(product_id)
        if producto is None:
            raise ValueError(f"Producto desconocido: {product_id}")
        if mode == "real" and not producto.command:
            raise ValueError("Este producto todavia no tiene el comando real conectado")

        job_id = uuid.uuid4().hex[:12]
        job = Job(
            id=job_id,
            product_id=producto.id,
            product_name=producto.name,
            params=params,
            mode=mode,
            dir=self.media_root / "jobs" / job_id,
        )
        self.jobs[job_id] = job
        self._podar()

        tarea = asyncio.create_task(self._correr(job, producto.stage))
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
        if job.status == "queued":
            job.status = "cancelled"
            job.stage = "cancelado antes de arrancar"
            job.finished_at = _ahora()
            self._emitir(job, {"type": "cancelled"})
        else:
            # El corte lo aplica el loop del render en el proximo cuadro.
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
        if len(self.jobs) <= self.max_historial:
            return
        terminados = [j for j in self.listar() if j.status in TERMINALES]
        for viejo in terminados[: max(0, len(self.jobs) - self.max_historial)]:
            self.jobs.pop(viejo.id, None)
            if viejo.dir and viejo.dir.exists():
                shutil.rmtree(viejo.dir, ignore_errors=True)

    def _emitir(self, job: Job, evento: dict[str, Any]) -> None:
        for cola in list(job.subs):
            cola.put_nowait(evento)

    def _log(self, job: Job, texto: str, level: str = "info") -> None:
        linea = LogLine(at=_ahora(), level=level, text=texto)  # type: ignore[arg-type]
        job.logs.append(linea)
        self._emitir(job, {"type": "log", "line": linea.model_dump()})

    def _progreso(self, job: Job, valor: float, etapa: str) -> None:
        job.progress = max(0.0, min(valor, 1.0))
        job.stage = etapa
        self._emitir(job, {"type": "progress", "progress": job.progress, "stage": etapa})

    def _artefacto(self, job: Job, path: Path, kind: str) -> None:
        relativa = path.relative_to(self.media_root).as_posix()
        artefacto = Artifact(
            name=path.name,
            url=f"/media/{relativa}",
            kind=kind,  # type: ignore[arg-type]
            bytes=path.stat().st_size if path.exists() else 0,
        )
        job.artifacts.append(artefacto)
        self._emitir(job, {"type": "artifact", "artifact": artefacto.model_dump()})

    async def _correr(self, job: Job, etapa_script: str) -> None:
        async with self._un_slot:
            if job.status == "cancelled":
                return
            job.status = "running"
            job.started_at = _ahora()
            try:
                self._progreso(job, 0.02, "preparando receta")
                self._log(job, f"job {job.id} | producto={job.product_id} | modo={job.mode}")
                self._log(job, f"script real del flujo: {etapa_script}")
                await asyncio.sleep(0)

                parametros = job.params
                total = render.frame_count(parametros)
                marcas = render.build_timeline(parametros, total)
                tamaño = int(parametros.get("resolucion", 1400))
                estilo = str(parametros.get("estilo", "realista"))

                self._log(
                    job,
                    f"plan: {total} cuadro(s) | {marcas[0]} -> {marcas[-1]} | "
                    f"estilo={estilo} | {tamaño}px",
                )

                assert job.dir is not None
                frames: list[Path] = []
                for i, marca in enumerate(marcas):
                    if job.cancelar.is_set():
                        raise asyncio.CancelledError
                    destino = job.dir / f"cuadro_{i:03d}.png"
                    await asyncio.to_thread(
                        render.render_frame,
                        destino,
                        titulo=job.product_name,
                        subtitulo=marca,
                        estilo=estilo,
                        marca=f"{job.product_id} - preview",
                        indice=i,
                        total=total,
                        tamaño=tamaño,
                    )
                    frames.append(destino)
                    self._log(job, f"[{i + 1}/{total}] {marca} -> {destino.name}")
                    self._progreso(
                        job,
                        0.05 + 0.8 * (i + 1) / total,
                        f"renderizando cuadro {i + 1}/{total}",
                    )

                if frames:
                    self._artefacto(job, frames[0], "image")

                if len(frames) > 1 and parametros.get("animar", True):
                    fps = int(parametros.get("fps", 12))
                    self._progreso(job, 0.9, "armando la animacion")
                    gif = job.dir / f"{job.product_id}_{job.id}.gif"
                    await asyncio.to_thread(render.save_gif, frames, gif, fps)
                    self._log(job, f"animacion lista: {gif.name} ({fps} fps)")
                    # Un GIF animado lo renderiza el navegador dentro de un <img>.
                    self._artefacto(job, gif, "image")

                job.status = "done"
                job.finished_at = _ahora()
                self._progreso(job, 1.0, "listo")
                self._log(job, "listo")
                self._emitir(job, {"type": "done", "job": job.snapshot().model_dump()})
            except asyncio.CancelledError:
                job.status = "cancelled"
                job.finished_at = _ahora()
                job.stage = "cancelado"
                self._log(job, "cancelado por el usuario", "warn")
                self._emitir(job, {"type": "cancelled"})
            except Exception as exc:  # noqa: BLE001 - se reporta tal cual a la UI
                job.status = "error"
                job.error = f"{type(exc).__name__}: {exc}"
                job.finished_at = _ahora()
                job.stage = "error"
                self._log(job, job.error, "error")
                self._emitir(job, {"type": "error", "error": job.error})
