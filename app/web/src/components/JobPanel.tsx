import { useEffect, useRef } from "react";
import type { Job, JobSummary, LogLine } from "../types";

const ETIQUETAS: Record<Job["status"], string> = {
  queued: "en cola",
  running: "corriendo",
  done: "listo",
  error: "error",
  cancelled: "cancelado",
};

// Marca de severidad: la consola se escanea por color y por etiqueta, no solo
// por el tinte de la linea.
const NIVEL: Record<LogLine["level"], string> = {
  info: "INF",
  warn: "WRN",
  error: "ERR",
};

function peso(bytes: number): string {
  if (bytes > 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

/** "2026-11-02T03:04:05+00:00" -> "02/11 03:04" (UTC, igual que la consola). */
function cuando(iso: string): string {
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)} ${iso.slice(11, 16)}`;
}

const esGif = (nombre: string) => nombre.toLowerCase().endsWith(".gif");
const esVideo = (nombre: string) => nombre.toLowerCase().endsWith(".mp4");
const enMarcha = (estado: Job["status"]) =>
  estado === "queued" || estado === "running";

interface Props {
  job: Job | null;
  corridas: JobSummary[];
  onSelect: (jobId: string) => void;
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
      <div className="key__row">
        <span className="key__mark key__mark--cancelled" aria-hidden="true" />
        cancelado: no llego al disco
      </div>
    </div>
  );
}

export function JobPanel({ job, corridas, onSelect, onCancel, onReveal }: Props) {
  const consola = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (consola.current) {
      consola.current.scrollTop = consola.current.scrollHeight;
    }
  }, [job?.logs.length]);

  if (corridas.length === 0) {
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

  const activas = corridas.filter((corrida) => enMarcha(corrida.status)).length;
  const imagenes = job?.artifacts.filter((a) => a.kind === "image") ?? [];
  const videos = job?.artifacts.filter((a) => a.kind === "video") ?? [];
  const porcentaje = Math.round((job?.progress ?? 0) * 100);
  const relleno =
    job?.status === "done"
      ? "progress__fill progress__fill--done"
      : job?.status === "error"
        ? "progress__fill progress__fill--error"
        : "progress__fill";

  return (
    <aside className="job" aria-label="Corridas">
      <section className="runbook" aria-labelledby="corridas-titulo">
        <div className="runbook__head">
          <h2 className="rail__title" id="corridas-titulo">
            Corridas
          </h2>
          <span className="runbook__facts">
            {activas > 0 ? (
              <span className="runbook__live">{activas} en curso</span>
            ) : null}
            <span className="rail__count">
              {String(corridas.length).padStart(2, "0")}
            </span>
          </span>
        </div>
        <ul className="runbook__list">
          {corridas.map((corrida) => {
            const activa = job?.id === corrida.id;
            return (
              <li key={corrida.id}>
                <button
                  type="button"
                  className="run"
                  aria-current={activa ? "true" : undefined}
                  title={`${corrida.product_name} · ${corrida.stage}`}
                  onClick={() => onSelect(corrida.id)}
                >
                  <span
                    className={`run__dot run__dot--${corrida.status}`}
                    aria-hidden="true"
                  />
                  <span className="run__body">
                    <span className="run__name">{corrida.product_name}</span>
                    <span className="run__meta">
                      <span className="run__when">
                        {cuando(corrida.created_at)}
                      </span>
                      <span className="run__stage">{corrida.stage}</span>
                    </span>
                  </span>
                  {enMarcha(corrida.status) ? (
                    <span className="run__pct">
                      {Math.round(corrida.progress * 100)}%
                    </span>
                  ) : null}
                </button>
              </li>
            );
          })}
        </ul>
      </section>

      <div className="job__inner">
        {job ? (
          <>
            <div className="job__head">
              <h2 className="job__title">Corrida</h2>
              <span className={`status status--${job.status}`}>
                {ETIQUETAS[job.status]}
              </span>
            </div>

            <div>
              <p className="job__product">{job.product_name}</p>
              <code className="job__id">
                {job.id} · {cuando(job.created_at)}
              </code>
            </div>

            <div className="progress">
              <div
                className="progress__track"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={porcentaje}
                aria-label="Progreso de la corrida"
              >
                <div className={relleno} style={{ width: `${porcentaje}%` }} />
              </div>
              <div className="progress__meta">
                <span className="progress__stage">{job.stage}</span>
                <span className="progress__pct">{porcentaje}%</span>
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
                <div
                  className={`console__line console__line--${linea.level}`}
                  key={indice}
                >
                  <span className="console__time">{linea.at.slice(11, 19)}</span>
                  <span
                    className={`console__tag console__tag--${linea.level}`}
                    aria-hidden="true"
                  >
                    {NIVEL[linea.level]}
                  </span>
                  <span className="sr-only">{`[${linea.level}] `}</span>
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
                      <span className="artifact__name">{arte.name}</span>
                      <span className="artifact__meta">
                        <span className="artifact__size">{peso(arte.bytes)}</span>
                        <a
                          className="artifact__dl"
                          href={arte.url}
                          download={arte.name}
                        >
                          Bajar
                        </a>
                      </span>
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
                      <span className="artifact__name">{arte.name}</span>
                      <span className="artifact__meta">
                        <span className="artifact__size">
                          {esGif(arte.name) ? "animo " : ""}
                          {peso(arte.bytes)}
                        </span>
                        <a
                          className="artifact__dl"
                          href={arte.url}
                          download={arte.name}
                        >
                          Bajar
                        </a>
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
              {enMarcha(job.status) ? (
                <button className="btn btn--warm" type="button" onClick={onCancel}>
                  Cancelar
                </button>
              ) : null}
            </div>
          </>
        ) : (
          <p className="runbook__wait">Leyendo la corrida…</p>
        )}
      </div>
    </aside>
  );
}
