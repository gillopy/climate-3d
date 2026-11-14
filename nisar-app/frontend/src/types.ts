export type JobStatus = "queued" | "running" | "done" | "error" | "cancelled";
export type RunMode = "real";

export interface RangoFechas {
  start: string;
  end: string;
}

export type Params = Record<string, string | number | boolean | RangoFechas>;

export interface HealthResponse {
  ok: boolean;
  repo_ready: boolean;
  repo_python: string;
  media_root: string;
  earthdata_configured: boolean;
  nisar_root: string;
  nisar_root_exists: boolean;
  data_root: string;
}

export interface Artifact {
  name: string;
  url: string;
  kind: "image" | "video" | "file";
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
