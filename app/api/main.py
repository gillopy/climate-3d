"""App interactiva de Climate 3D.

Capas: catalogo -> receta -> comandos reales del repo -> artefactos. La UI nunca
habla con un script: habla con esta API, y la API corre el pipeline con el Python
del repo.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .catalog import (
    available_dates,
    data_root,
    data_root_exists,
    get_product,
    productos_disponibles,
)
from .jobs import JobManager
from .recipes import python_repo, repo_listo
from .schemas import CatalogResponse, DatesResponse, JobSnapshot, RecipeRequest

RAIZ_APP = Path(__file__).resolve().parents[1]
MEDIA = RAIZ_APP / "var" / "media"
MEDIA.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Climate 3D - consola interactiva",
    version="0.2.0",
    description="Receta -> comandos reales del repo -> progreso en vivo -> artefacto.",
)

# Vite corre en otro puerto durante el desarrollo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

gestor = JobManager(MEDIA)

app.mount("/media", StaticFiles(directory=MEDIA), name="media")


@app.get("/api/health")
def health() -> dict[str, object]:
    return {
        "ok": True,
        "productos": len(productos_disponibles()),
        "data_root": str(data_root()),
        "data_root_exists": data_root_exists(),
        "repo_ready": repo_listo(),
        "repo_python": str(python_repo()),
    }


@app.get("/api/catalog", response_model=CatalogResponse)
def catalogo() -> CatalogResponse:
    return CatalogResponse(
        products=productos_disponibles(),
        data_root=str(data_root()),
        data_root_exists=data_root_exists(),
        media_root=str(MEDIA),
        repo_python=str(python_repo()),
        repo_ready=repo_listo(),
    )


@app.get("/api/catalog/{product_id}/dates", response_model=DatesResponse)
def fechas(
    product_id: str,
    satelite: str | None = None,
    banda: str | None = None,
) -> DatesResponse:
    producto = get_product(product_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto desconocido")
    params: dict[str, Any] = {}
    if satelite:
        params["satelite"] = satelite
    if banda:
        params["banda"] = banda
    source, dates = available_dates(producto, params)
    return DatesResponse(product_id=product_id, source=source, dates=dates)  # type: ignore[arg-type]


@app.post("/api/jobs", response_model=JobSnapshot, status_code=201)
async def crear_job(receta: RecipeRequest) -> JobSnapshot:
    # async a proposito: `crear` agenda la tarea en el event loop que corre la API.
    try:
        job = gestor.crear(receta.product_id, receta.params)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return job.snapshot()


@app.get("/api/jobs", response_model=list[JobSnapshot])
def listar_jobs() -> list[JobSnapshot]:
    return [job.snapshot() for job in gestor.listar()]


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


@app.get("/api/jobs/{job_id}/events")
async def eventos(job_id: str, request: Request) -> StreamingResponse:
    if gestor.obtener(job_id) is None:
        raise HTTPException(status_code=404, detail="Job desconocido")

    async def flujo():
        import json

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
DIST = RAIZ_APP / "web" / "dist"
if DIST.is_dir():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="web")
else:

    @app.get("/")
    def sin_build() -> dict[str, str]:
        return {
            "mensaje": "Falta el build del frontend.",
            "paso_1": "cd app/web && npm install",
            "paso_2": "npm run build",
            "alternativa": "o correr `npm run dev` en app/web (proxy a :8000)",
        }
