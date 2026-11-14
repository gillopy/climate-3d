"""Contrato HTTP de la app NISAR.

La UI no conoce flags de CLI ni nombres de script: conoce estos modelos. El
pedido de analisis viaja como ``producto`` + parametros dentro de ``params`` y
el backend lo traduce a comandos reales en ``recipes.py``.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

JobStatus = Literal["queued", "running", "done", "error", "cancelled"]
RunMode = Literal["real"]


class RecipeRequest(BaseModel):
    """Pedido del visor: producto NISAR + parametros de la escena y la caja."""

    product_id: str = "nisar_render"
    params: dict[str, Any] = Field(default_factory=dict)


class Artifact(BaseModel):
    name: str
    url: str
    kind: Literal["image", "video", "file"]
    bytes: int


class LogLine(BaseModel):
    at: str
    level: Literal["info", "warn", "error"] = "info"
    text: str


class JobSnapshot(BaseModel):
    id: str
    product_id: str
    product_name: str
    params: dict[str, Any]
    mode: RunMode
    status: JobStatus
    progress: float
    stage: str
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    logs: list[LogLine] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    plan: list[str] = Field(default_factory=list)
    error: str | None = None


class JobSummary(BaseModel):
    """Fila liviana: el listado se refresca por sondeo y no arrastra logs."""

    id: str
    product_id: str
    product_name: str
    mode: RunMode
    status: JobStatus
    progress: float
    stage: str
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    ok: bool
    repo_ready: bool
    repo_python: str
    media_root: str
    earthdata_configured: bool
    nisar_root: str
    nisar_root_exists: bool
    data_root: str
