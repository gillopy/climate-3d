export type ParamKind = "select" | "date-range" | "date" | "toggle" | "slider";
export type JobStatus = "queued" | "running" | "done" | "error" | "cancelled";
export type RunMode = "preview" | "real";

export interface ParamOption {
  value: string;
  label: string;
}

export interface ParamSpec {
  name: string;
  label: string;
  kind: ParamKind;
  default: unknown;
  options: ParamOption[];
  help: string;
  min: number | null;
  max: number | null;
  step: number | null;
  /** Se habilita solo cuando otro parametro tiene este valor. */
  enabled_when: Record<string, unknown> | null;
}

export interface PreviewVariant {
  url: string;
  when: Record<string, unknown>;
}

export interface Product {
  id: string;
  name: string;
  group: string;
  stage: string;
  summary: string;
  params: ParamSpec[];
  preview: string | null;
  previews: PreviewVariant[];
  command_ready: boolean;
  command: string[] | null;
}

export interface CatalogResponse {
  products: Product[];
  data_root: string;
  data_root_exists: boolean;
  media_root: string;
  repo_python: string;
  repo_ready: boolean;
}

export interface DatesResponse {
  product_id: string;
  source: "descubierto" | "demo";
  dates: string[];
}

export interface Artifact {
  name: string;
  url: string;
  kind: "image" | "video";
  bytes: number;
}

export interface LogLine {
  at: string;
  level: "info" | "warn" | "error";
  text: string;
}

/** Fila del listado de corridas: lo justo para dibujar la cola y el historial. */
export interface JobSummary {
  id: string;
  product_id: string;
  product_name: string;
  mode: RunMode;
  status: JobStatus;
  progress: number;
  stage: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
}

export interface Job {
  id: string;
  product_id: string;
  product_name: string;
  params: Record<string, unknown>;
  mode: RunMode;
  status: JobStatus;
  progress: number;
  stage: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  logs: LogLine[];
  artifacts: Artifact[];
  plan: string[];
  error: string | null;
}

export interface RangoFechas {
  start: string;
  end: string;
}

export type Params = Record<string, string | number | boolean | RangoFechas>;
