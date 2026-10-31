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

export function JobPanel({ job, onCancel, onReveal }: Props) {
  const consola = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (consola.current) {
      consola.current.scrollTop = consola.current.scrollHeight;
    }
  }, [job?.logs.length]);

  if (!job) {
    return (
      <aside className="panel panel--vacio">
        <h2>Trabajo</h2>
        <p>Elegi un producto, ajusta la receta y dale a Generar.</p>
        <p className="tenue">
          La descarga y el render no bloquean la interfaz: cada pedido se encola y
          el progreso llega por SSE.
        </p>
      </aside>
    );
  }

  const activo = job.status === "queued" || job.status === "running";
  const imagenes = job.artifacts.filter((a) => a.kind === "image");
  const videos = job.artifacts.filter((a) => a.kind === "video");

  return (
    <aside className="panel">
      <div className="panel__cabecera">
        <h2>Trabajo</h2>
        <span className={`badge badge--${job.status}`}>{ETIQUETAS[job.status]}</span>
      </div>

      <p className="panel__producto">{job.product_name}</p>
      <code className="panel__id">{job.id}</code>

      {job.plan.length > 0 ? (
        <ol className="plan">
          {job.plan.map((paso, indice) => (
            <li key={indice}>{paso}</li>
          ))}
        </ol>
      ) : null}

      <div className="progreso">
        <div className="progreso__barra">
          <div
            className="progreso__relleno"
            style={{ width: `${Math.round(job.progress * 100)}%` }}
          />
        </div>
        <div className="progreso__pie">
          <span>{job.stage}</span>
          <span>{Math.round(job.progress * 100)}%</span>
        </div>
      </div>

      {job.error ? <p className="receta__error">{job.error}</p> : null}

      <div className="consola" ref={consola}>
        {job.logs.map((linea, indice) => (
          <div className={`consola__linea consola__linea--${linea.level}`} key={indice}>
            <span className="consola__hora">{linea.at.slice(11, 19)}</span>
            <span>{linea.text}</span>
          </div>
        ))}
      </div>

      {imagenes.length > 0 || videos.length > 0 ? (
        <div className="salidas">
          {imagenes.map((arte) => (
            <figure key={arte.name} className="salida">
              <img src={arte.url} alt={arte.name} loading="lazy" />
              <figcaption>
                <span>{arte.name}</span>
                <span className="tenue">{peso(arte.bytes)}</span>
              </figcaption>
            </figure>
          ))}
          {videos.map((arte) => (
            <figure key={arte.name} className="salida">
              {esVideo(arte.name) ? (
                <video src={arte.url} controls loop muted playsInline />
              ) : (
                <img src={arte.url} alt={arte.name} loading="lazy" />
              )}
              <figcaption>
                <span>{arte.name}</span>
                <span className="tenue">
                  {esGif(arte.name) ? "animo " : ""}
                  {peso(arte.bytes)}
                </span>
              </figcaption>
            </figure>
          ))}
        </div>
      ) : null}

      <div className="panel__acciones">
        <button className="boton" type="button" onClick={onReveal}>
          Abrir carpeta
        </button>
        {activo ? (
          <button className="boton boton--peligro" type="button" onClick={onCancel}>
            Cancelar
          </button>
        ) : null}
      </div>
    </aside>
  );
}
