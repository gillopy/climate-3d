import { useEffect, useRef } from "react";
import type { Job } from "../types";

const ETIQUETAS: Record<Job["status"], string> = {
  queued: "en cola",
  running: "corriendo",
  done: "listo",
  error: "error",
  cancelled: "cancelado",
};

function peso(bytes: number): string {
  if (bytes > 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

const esGif = (nombre: string) => nombre.toLowerCase().endsWith(".gif");
const esVideo = (nombre: string) => nombre.toLowerCase().endsWith(".mp4");

interface Props {
  job: Job | null;
  onCancel: () => void;
  onReveal: () => void;
}

function Clave() {
  return (
    <div className="key">
      <p className="key__title">Estados</p>
      <div className="key__row">
        <span className="key__mark key__mark--queued" aria-hidden="true" />
        en cola: espera su turno
      </div>
      <div className="key__row">
        <span className="key__mark key__mark--running" aria-hidden="true" />
        corriendo: el frente avanza
      </div>
      <div className="key__row">
        <span className="key__mark key__mark--done" aria-hidden="true" />
        listo: el render quedo en disco
      </div>
      <div className="key__row">
        <span className="key__mark key__mark--error" aria-hidden="true" />
        error: mira el log de arriba
      </div>
    </div>
  );
}

export function JobPanel({ job, onCancel, onReveal }: Props) {
  const consola = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (consola.current) {
      consola.current.scrollTop = consola.current.scrollHeight;
    }
  }, [job?.logs.length]);

  if (!job) {
    return (
      <aside className="job" aria-label="Corrida">
        <div className="job__inner">
          <div className="job__head">
            <h2 className="job__title">Corrida</h2>
          </div>
          <div className="empty">
            <p>
              Elegi un producto, ajusta la receta y dale a Generar. La descarga y el
              render no bloquean la interfaz: cada pedido se encola y el progreso
              llega por SSE.
            </p>
            <div className="flow">
              <p className="flow__title">Como corre</p>
              <ol className="flow__list">
                <li>Elegis el producto y ajustas la receta.</li>
                <li>El job se encola y ejecuta el script real del repo.</li>
                <li>El render queda en disco y se abre desde aca.</li>
              </ol>
            </div>
            <Clave />
          </div>
        </div>
      </aside>
    );
  }

  const activo = job.status === "queued" || job.status === "running";
  const imagenes = job.artifacts.filter((a) => a.kind === "image");
  const videos = job.artifacts.filter((a) => a.kind === "video");
  const porcentaje = Math.round(job.progress * 100);
  const traza =
    job.status === "done"
      ? "trace--done"
      : job.status === "error"
        ? "trace--error"
        : "";

  return (
    <aside className="job" aria-label="Corrida">
      <div className="job__inner">
        <div className="job__head">
          <h2 className="job__title">Corrida</h2>
          <span className={`stamp stamp--${job.status}`}>{ETIQUETAS[job.status]}</span>
        </div>

        <div>
          <p className="job__product">{job.product_name}</p>
          <code className="job__id">{job.id}</code>
        </div>

        <div className={`trace ${traza}`}>
          <div
            className="trace__track"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={porcentaje}
            aria-label="Progreso de la corrida"
          >
            <div className="trace__fill" style={{ width: `${porcentaje}%` }} />
          </div>
          <div className="trace__meta">
            <span className="trace__stage">{job.stage}</span>
            <span className="trace__pct">{porcentaje}%</span>
          </div>
        </div>

        {job.plan.length > 0 ? (
          <ol className="plan">
            {job.plan.map((paso, indice) => (
              <li key={indice}>{paso}</li>
            ))}
          </ol>
        ) : null}

        {job.error ? <p className="job__error">{job.error}</p> : null}

        <div className="console" ref={consola} aria-label="Registro de la corrida">
          {job.logs.map((linea, indice) => (
            <div className={`console__line console__line--${linea.level}`} key={indice}>
              <span className="console__time">{linea.at.slice(11, 19)}</span>
              <span>{linea.text}</span>
            </div>
          ))}
        </div>

        {imagenes.length > 0 || videos.length > 0 ? (
          <div className="artifacts">
            {imagenes.map((arte) => (
              <figure key={arte.name} className="artifact">
                <img src={arte.url} alt={arte.name} loading="lazy" />
                <figcaption>
                  <span>{arte.name}</span>
                  <span className="artifact__size">{peso(arte.bytes)}</span>
                </figcaption>
              </figure>
            ))}
            {videos.map((arte) => (
              <figure key={arte.name} className="artifact">
                {esVideo(arte.name) ? (
                  <video src={arte.url} controls loop muted playsInline />
                ) : (
                  <img src={arte.url} alt={arte.name} loading="lazy" />
                )}
                <figcaption>
                  <span>{arte.name}</span>
                  <span className="artifact__size">
                    {esGif(arte.name) ? "animo " : ""}
                    {peso(arte.bytes)}
                  </span>
                </figcaption>
              </figure>
            ))}
          </div>
        ) : null}

        <div className="job__actions">
          <button className="btn" type="button" onClick={onReveal}>
            Abrir carpeta
          </button>
          {activo ? (
            <button className="btn btn--warm" type="button" onClick={onCancel}>
              Cancelar
            </button>
          ) : null}
        </div>
      </div>
    </aside>
  );
}
