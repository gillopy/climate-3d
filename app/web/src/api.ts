import type {
  Artifact,
  CatalogResponse,
  DatesResponse,
  Job,
  LogLine,
  Params,
} from "./types";

async function leer<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detalle = `${res.status} ${res.statusText}`;
    try {
      const cuerpo = (await res.json()) as { detail?: string };
      if (cuerpo.detail) detalle = cuerpo.detail;
    } catch {
      // El cuerpo no era JSON: nos quedamos con el status.
    }
    throw new Error(detalle);
  }
  return (await res.json()) as T;
}

export function getCatalog(): Promise<CatalogResponse> {
  return fetch("/api/catalog").then((r) => leer<CatalogResponse>(r));
}

export function getDates(
  productId: string,
  extra?: { satelite?: string; banda?: string },
): Promise<DatesResponse> {
  const query = new URLSearchParams();
  if (extra?.satelite) query.set("satelite", extra.satelite);
  if (extra?.banda) query.set("banda", extra.banda);
  const sufijo = query.toString() ? `?${query}` : "";
  return fetch(`/api/catalog/${productId}/dates${sufijo}`).then((r) =>
    leer<DatesResponse>(r),
  );
}

export function getJobs(): Promise<Job[]> {
  return fetch("/api/jobs").then((r) => leer<Job[]>(r));
}

export function createJob(productId: string, params: Params): Promise<Job> {
  return fetch("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_id: productId, params }),
  }).then((r) => leer<Job>(r));
}

export function cancelJob(jobId: string): Promise<Job> {
  return fetch(`/api/jobs/${jobId}/cancel`, { method: "POST" }).then((r) =>
    leer<Job>(r),
  );
}

export interface JobHandlers {
  onSnapshot?: (job: Job) => void;
  onLog?: (line: LogLine) => void;
  onProgress?: (progress: number, stage: string) => void;
  onArtifact?: (artifact: Artifact) => void;
  onFinal?: (estado: Job["status"]) => void;
  onFallo?: (mensaje: string) => void;
}

/**
 * SSE: el progreso llega solo, sin polling. Devuelve la funcion para cortar.
 */
export function subscribeJob(jobId: string, h: JobHandlers): () => void {
  const fuente = new EventSource(`/api/jobs/${jobId}/events`);

  const escuchar = <T,>(nombre: string, fn: (dato: T) => void) => {
    fuente.addEventListener(nombre, (evento) => {
      const mensaje = evento as MessageEvent<string>;
      fn(JSON.parse(mensaje.data) as T);
    });
  };

  escuchar<{ job: Job }>("snapshot", (d) => h.onSnapshot?.(d.job));
  escuchar<{ line: LogLine }>("log", (d) => h.onLog?.(d.line));
  escuchar<{ progress: number; stage: string }>("progress", (d) =>
    h.onProgress?.(d.progress, d.stage),
  );
  escuchar<{ artifact: Artifact }>("artifact", (d) => h.onArtifact?.(d.artifact));

  const cerrar = (estado: Job["status"]) => {
    fuente.close();
    h.onFinal?.(estado);
  };

  escuchar<{ job: Job }>("done", (d) => {
    if (d?.job) h.onSnapshot?.(d.job);
    cerrar("done");
  });
  escuchar<{ error: string }>("error", (d) => {
    if (d?.error) h.onFallo?.(d.error);
    cerrar("error");
  });
  escuchar<Record<string, never>>("cancelled", () => cerrar("cancelled"));
  escuchar<Record<string, never>>("closed", () => fuente.close());

  fuente.onerror = () => {
    if (fuente.readyState === EventSource.CLOSED) {
      h.onFallo?.("se corto el stream de progreso");
    }
  };

  return () => fuente.close();
}
