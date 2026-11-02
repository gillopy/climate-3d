"""Modelos del contrato HTTP.

La UI no conoce flags de CLI ni nombres de script: conoce este contrato. Un
producto se describe como datos (``Product``) y la interfaz arma sus controles a
partir de esos datos. Agregar un producto es agregar una entrada al catalogo,
no un boton hardcodeado.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ParamKind = Literal["select", "date-range", "date", "toggle", "slider"]
JobStatus = Literal["queued", "running", "done", "error", "cancelled"]
RunMode = Literal["preview", "real"]


class ParamOption(BaseModel):
    """Una opcion de un `select`."""

    value: str
    label: str


class ParamSpec(BaseModel):
    """Un control del formulario, descrito por el backend."""

    name: str
    label: str
    kind: ParamKind
    default: Any
    options: list[ParamOption] = Field(default_factory=list)
    help: str = ""
    min: float | None = None
    max: float | None = None
    step: float | None = None


class Product(BaseModel):
    """Un flujo del repo expuesto como producto interactivo."""

    id: str
    name: str
    group: str
    stage: str
    summary: str
    params: list[ParamSpec]
    preview: str | None = Field(
        default=None,
        description="WebP de muestra generado con el pipeline real, servido en /previews.",
    )
    command_ready: bool = Field(
        default=False,
        description="True cuando el producto ya declara el comando real en catalog.py.",
    )
    command: list[str] | None = None


class CatalogResponse(BaseModel):
    products: list[Product]
    data_root: str
    data_root_exists: bool
    media_root: str
    repo_python: str
    repo_ready: bool


class DatesResponse(BaseModel):
    product_id: str
    source: Literal["descubierto", "demo"]
    dates: list[str]


class RecipeRequest(BaseModel):
    """El pedido del usuario: producto + parametros. Siempre corre el pipeline real."""

    product_id: str
    params: dict[str, Any] = Field(default_factory=dict)


class Artifact(BaseModel):
    name: str
    url: str
    kind: Literal["image", "video"]
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
    """Una fila del listado de corridas.

    El listado se refresca cada pocos segundos: no puede arrastrar el log ni los
    artefactos de cada job. El detalle completo se pide por id.
    """

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
