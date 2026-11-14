"""App NISAR: visor + analisis de escenas sobre el radar.

Capas: ASF (busqueda/browse) -> escena GCOV -> recorte de la caja -> artefacto.
La UI nunca habla con un script: habla con esta API, y la API corre el pipeline
del repo con el Python del pipeline.

Solo NISAR: no hay catalogo de recetas ni productos de otras familias.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .config import MEDIA, RAIZ_APP, earthdata_configurada, python_repo, repo_listo
from .jobs import JobManager
from .nisar import _datos, _raiz_nisar
from .nisar import router as nisar_router
from .schemas import HealthResponse, JobSnapshot, JobSummary, RecipeRequest

MEDIA.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="NISAR - visor de radar",
    version="1.0.0",
    description="Caja -> escenas ASF -> descarga .h5 -> producto de analisis.",
)

# Vite corre en otro puerto durante el desarrollo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)

gestor = JobManager(MEDIA)

app.include_router(nisar_router, prefix="/api/nisar", tags=["nisar"])
app.mount("/media", StaticFiles(directory=MEDIA), name="media")


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    raiz_nisar = _raiz_nisar()
    return HealthResponse(
        ok=True,
        repo_ready=repo_listo(),
        repo_python=str(python_repo()),
        media_root=str(MEDIA),
        earthdata_configured=earthdata_configurada(),
        nisar_root=str(raiz_nisar),
        nisar_root_exists=raiz_nisar.is_dir(),
        data_root=str(_datos()),
    )


@app.post("/api/jobs", response_model=JobSnapshot, status_code=201)
async def crear_job(receta: RecipeRequest) -> JobSnapshot:
    # async a proposito: `crear` agenda la tarea en el event loop que corre la API.
    try:
        job = gestor.crear(receta.product_id, receta.params)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return job.snapshot()


@app.get("/api/jobs", response_model=list[JobSummary])
def listar_jobs() -> list[JobSummary]:
    """Cola + historial. Liviano a proposito: la UI lo refresca cada pocos segundos."""
    return gestor.listar_resumen()


@app.get("/api/jobs/{job_id}", response_model=JobSnapshot)
def ver_job(job_id: str) -> JobSnapshot:
    job = gestor.obtener(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job desconocido")
    return job.snapshot()


@app.post("/api/jobs/{job_id}/cancel", response_model=JobSnapshot)
def cancelar_job(job_id: str) -> JobSnapshot:
    job = gestor.obtener(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job desconocido")
    gestor.cancelar(job_id)
    return job.snapshot()


@app.post("/api/jobs/{job_id}/reveal")
def revelar_carpeta(job_id: str) -> dict[str, str]:
    """Abre el explorador en la carpeta del job.

    Solo abre la carpeta que el servidor calculo para ese job: no acepta rutas
    del cliente, asi que no sirve para abrir cualquier cosa del disco.

    En el contenedor no hay escritorio: se explica como bajar el artefacto en vez
    de fallar con el error de un ``explorer``/``xdg-open`` que no existe.
    """
    job = gestor.obtener(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job desconocido")

    if os.environ.get("CLIMATE3D_CONTENEDOR") == "1":
        raise HTTPException(
            status_code=409,
            detail=(
                "En modo contenedor no hay escritorio que abrir: "
                "descargá el artefacto desde el panel."
            ),
        )

    destino = job.work
    if not destino.is_dir():
        raise HTTPException(status_code=409, detail="La carpeta todavia no existe")

    if sys.platform == "win32":
        subprocess.Popen(["explorer", str(destino)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(destino)])
    else:
        subprocess.Popen(["xdg-open", str(destino)])
    return {"abierto": str(destino)}


@app.get("/api/jobs/{job_id}/events")
async def eventos(job_id: str, request: Request) -> StreamingResponse:
    if gestor.obtener(job_id) is None:
        raise HTTPException(status_code=404, detail="Job desconocido")

    async def flujo():
        async for evento in gestor.seguir(job_id):
            if await request.is_disconnected():
                break
            if evento.get("type") == "ping":
                yield ": ping\n\n"
                continue
            yield f"event: {evento['type']}\ndata: {json.dumps(evento, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        flujo(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Sin esto, un proxy intermedio bufferiza el stream y no se ve nada.
            "X-Accel-Buffering": "no",
        },
    )


@app.exception_handler(Exception)
async def error_no_controlado(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": f"{type(exc).__name__}: {exc}"})


# Build del frontend: un solo puerto para toda la app.
DIST = RAIZ_APP / "frontend" / "dist"
if DIST.is_dir():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="web")
else:

    @app.get("/")
    def sin_build() -> dict[str, str]:
        return {
            "mensaje": "Falta el build del frontend.",
            "paso_1": "cd nisar-app/frontend && npm install",
            "paso_2": "npm run build",
            "alternativa": "o correr `npm run dev` en nisar-app/frontend (proxy a :8010)",
        }
