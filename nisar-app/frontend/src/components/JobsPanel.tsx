import { useCallback, useEffect, useState } from "react";

import { cancelJob, getJob, getJobs, revealJob, subscribeJob } from "../api";
import { pesoArchivo, resumenStats } from "../formato";
import type { StatsRow } from "../formato";
import type { Job, JobSummary } from "../types";

const ETIQUETA: Record<Job["status"], string> = {
  queued: "en cola",
  running: "corriendo",
  done: "listo",
  error: "error",
  cancelled: "cancelado",
};

function fechaHora(iso: string): string {
  if (!iso) return "-";
  const limpia = iso.replace("T", " ");
  return limpia.length >= 16 ? limpia.slice(0, 16) : limpia;
}

function horaDe(iso: string): string {
  if (!iso) return "--:--";
  const instante = iso.includes("T") ? iso : "";
  return instante ? instante.slice(11, 19) : iso;
}

function enMarcha(job: JobSummary | Job | null): boolean {
  return job?.status === "queued" || job?.status === "running";
}

interface Props {
  abierto: boolean;
  onCerrar: () => void;
  /** Id del trabajo recién creado: se selecciona al abrir el panel. */
  jobInicial: string | null;
  /** Total de corridas, para el contador del botón que abre el panel. */
  onTotal: (total: number) => void;
}

/**
 * Panel de trabajos: historial de corridas con logs y resultados.
 *
 * El backend ya persiste el historial (`/api/jobs`) y el detalle de cada job
 * (`/api/jobs/{id}`), ademas del stream SSE. Este panel los muestra juntos para
 * poder volver a una corrida anterior sin perder la vista del mapa.
 */
export function JobsPanel({ abierto, onCerrar, jobInicial, onTotal }: Props) {
  const [corridas, setCorridas] = useState<JobSummary[]>([]);
  const [seleccionId, setSeleccionId] = useState<string | null>(null);
  const [detalle, setDetalle] = useState<Job | null>(null);
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refrescarLista = useCallback(async () => {
    try {
      const lista = await getJobs();
      setCorridas(lista);
      onTotal(lista.length);
    } catch {
      // El sondeo no discute: si falla, se reintenta en el proximo tic.
    }
  }, [onTotal]);

  // Una corrida nueva se selecciona sola.
  useEffect(() => {
    if (jobInicial) setSeleccionId(jobInicial);
  }, [jobInicial]);

  // Sin seleccion (o si la corrida se podó), abre la mas nueva.
  useEffect(() => {
    if (seleccionId && corridas.some((corrida) => corrida.id === seleccionId)) {
      return;
    }
    if (corridas.length > 0) setSeleccionId(corridas[0].id);
  }, [corridas, seleccionId]);

  // Lista: se refresca siempre, aunque el panel este cerrado, para el contador.
  useEffect(() => {
    void refrescarLista();
    const tic = window.setInterval(() => void refrescarLista(), 4000);
    return () => window.clearInterval(tic);
  }, [refrescarLista]);

  const actualizarFila = useCallback((job: Job) => {
    setCorridas((previo) =>
      previo.map((corrida) =>
        corrida.id === job.id
          ? {
              ...corrida,
              status: job.status,
              progress: job.progress,
              stage: job.stage,
              error: job.error,
              finished_at: job.finished_at,
            }
          : corrida,
      ),
    );
  }, []);

  // Detalle + stream en vivo del trabajo elegido.
  useEffect(() => {
    if (!abierto || !seleccionId) return;
    let vigente = true;
    setError(null);

    getJob(seleccionId)
      .then((job) => {
        if (vigente) setDetalle(job);
      })
      .catch((exc: unknown) => {
        if (vigente) {
          setError(exc instanceof Error ? exc.message : "no se pudo leer la corrida");
        }
      });

    const corte = subscribeJob(seleccionId, {
      onSnapshot: (job) => {
        if (!vigente) return;
        setDetalle(job);
        actualizarFila(job);
      },
      onLog: (linea) =>
        setDetalle((previo) =>
          previo && previo.id === seleccionId
            ? { ...previo, logs: [...previo.logs, linea].slice(-400) }
            : previo,
        ),
      onProgress: (progress, stage) => {
        setDetalle((previo) =>
          previo && previo.id === seleccionId ? { ...previo, progress, stage } : previo,
        );
        setCorridas((previo) =>
          previo.map((corrida) =>
            corrida.id === seleccionId ? { ...corrida, progress, stage } : corrida,
          ),
        );
      },
      onArtifact: (artefacto) =>
        setDetalle((previo) => {
          if (!previo || previo.id !== seleccionId) return previo;
          if (previo.artifacts.some((arte) => arte.url === artefacto.url)) return previo;
          return { ...previo, artifacts: [...previo.artifacts, artefacto] };
        }),
      onFinal: () => void refrescarLista(),
      onFallo: (mensaje) => {
        if (vigente) setError(mensaje);
      },
    });

    return () => {
      vigente = false;
      corte();
    };
  }, [abierto, seleccionId, actualizarFila, refrescarLista]);

  // El JSON de estadisticas que deja el producto.
  const statsArtifact =
    detalle?.artifacts.find(
      (arte) => arte.kind === "file" && arte.name.endsWith(".json"),
    ) ?? null;
  useEffect(() => {
    if (!statsArtifact) {
      setStats(null);
      return;
    }
    let vigente = true;
    fetch(statsArtifact.url)
      .then((respuesta) => (respuesta.ok ? respuesta.json() : null))
      .then((datos) => {
        if (vigente) setStats(datos as Record<string, unknown> | null);
      })
      .catch(() => {
        if (vigente) setStats(null);
      });
    return () => {
      vigente = false;
    };
  }, [statsArtifact?.url]);

  const resumen: StatsRow[] = stats ? resumenStats(stats) : [];
  const imagenes = detalle?.artifacts.filter((arte) => arte.kind === "image") ?? [];
  const archivos = detalle?.artifacts.filter((arte) => arte.kind === "file") ?? [];

  async function cancelar() {
    if (!detalle) return;
    try {
      const actualizado = await cancelJob(detalle.id);
      setDetalle(actualizado);
      actualizarFila(actualizado);
      void refrescarLista();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "no se pudo cancelar");
    }
  }

  async function revelar() {
    if (!detalle) return;
    try {
      await revealJob(detalle.id);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "no se pudo abrir la carpeta");
    }
  }

  if (!abierto) return null;

  return (
    <section className="trabajos" aria-label="Trabajos NISAR">
      <header className="trabajos__head">
        <h2 className="trabajos__title">Trabajos</h2>
        <span className="trabajos__count" aria-live="polite">
          {String(corridas.length).padStart(2, "0")}
        </span>
        <button type="button" className="btn trabajos__cerrar" onClick={onCerrar}>
          Cerrar
        </button>
      </header>

      <div className="trabajos__cuerpo">
        <ul className="trabajos__lista" aria-label="Corridas">
          {corridas.length === 0 ? (
            <li className="trabajos__vacio">
              Todavía no corriste ningún trabajo. Generá un análisis y aparece acá.
            </li>
          ) : (
            corridas.map((corrida) => (
              <li key={corrida.id}>
                <button
                  type="button"
                  className="trabajos__fila"
                  aria-current={seleccionId === corrida.id ? "true" : undefined}
                  onClick={() => setSeleccionId(corrida.id)}
                >
                  <span
                    className={`trabajos__punto trabajos__punto--${corrida.status}`}
                    aria-hidden="true"
                  />
                  <span className="trabajos__fila-txt">
                    <span className="trabajos__fila-top">
                      <span className="trabajos__estado">
                        {ETIQUETA[corrida.status]}
                      </span>
                      <span className="trabajos__hora">
                        {fechaHora(corrida.created_at)}
                      </span>
                    </span>
                    <span className="trabajos__fila-stage">
                      {corrida.stage || "en cola"}
                    </span>
                    <span className="trabajos__mini" aria-hidden="true">
                      <i style={{ width: `${Math.round(corrida.progress * 100)}%` }} />
                    </span>
                  </span>
                </button>
              </li>
            ))
          )}
        </ul>

        <div className="trabajos__detalle">
          {detalle ? (
            <>
              <div className="trabajos__detalle-head">
                <div>
                  <h3 className="trabajos__detalle-title">
                    {ETIQUETA[detalle.status]} · {Math.round(detalle.progress * 100)} %
                  </h3>
                  <p className="trabajos__detalle-sub">
                    {detalle.product_name} · {fechaHora(detalle.created_at)}
                  </p>
                </div>
                <div className="trabajos__acciones">
                  {enMarcha(detalle) ? (
                    <button type="button" className="btn" onClick={() => void cancelar()}>
                      Cancelar
                    </button>
                  ) : null}
                  {detalle.status !== "queued" ? (
                    <button type="button" className="btn" onClick={() => void revelar()}>
                      Abrir carpeta
                    </button>
                  ) : null}
                </div>
              </div>

              {detalle.error ? (
                <p className="trabajos__aviso" role="alert">
                  {detalle.error}
                </p>
              ) : null}
              {error ? (
                <p className="trabajos__aviso" role="alert">
                  {error}
                </p>
              ) : null}

              <div className="trabajos__meta">
                <span>producto: {String(detalle.params.producto ?? "-")}</span>
                <span>px: {String(detalle.params.px ?? "-")}</span>
                <span className="trabajos__meta-bbox">
                  caja: {String(detalle.params.bbox ?? "-")}
                </span>
              </div>

              {detalle.plan.length > 0 ? (
                <ol className="trabajos__plan">
                  {detalle.plan.map((paso, indice) => (
                    <li key={`${indice}-${paso}`}>{paso}</li>
                  ))}
                </ol>
              ) : null}

              <div className="trabajos__barra">
                <i style={{ width: `${Math.round(detalle.progress * 100)}%` }} />
              </div>

              {imagenes.length > 0 ? (
                <div className="trabajos__seccion">
                  <h4>Resultados</h4>
                  <div className="trabajos__imagenes">
                    {imagenes.map((arte) => (
                      <a key={arte.url} href={arte.url} target="_blank" rel="noreferrer">
                        <img src={arte.url} alt={arte.name} loading="lazy" />
                      </a>
                    ))}
                  </div>
                </div>
              ) : null}

              {archivos.length > 0 ? (
                <div className="trabajos__seccion">
                  <h4>Archivos</h4>
                  {archivos.map((arte) => (
                    <a
                      key={arte.url}
                      className="trabajos__archivo"
                      href={arte.url}
                      download={arte.name}
                    >
                      {arte.name} · {pesoArchivo(arte.bytes)}
                    </a>
                  ))}
                </div>
              ) : null}

              {resumen.length > 0 ? (
                <div className="trabajos__seccion">
                  <h4>Estadísticas</h4>
                  <dl className="trabajos__stats">
                    {resumen.map((fila) => (
                      <div key={`${fila.label}-${fila.value}`} className="trabajos__stat">
                        <dt>{fila.label}</dt>
                        <dd>{fila.value}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              ) : null}

              <div className="trabajos__seccion">
                <h4>Log</h4>
                {detalle.logs.length === 0 ? (
                  <p className="trabajos__vacio">Sin líneas todavía.</p>
                ) : (
                  <ol className="trabajos__logs">
                    {detalle.logs.map((linea, indice) => (
                      <li
                        key={`${linea.at}-${indice}`}
                        className={`trabajos__log trabajos__log--${linea.level}`}
                      >
                        <time>{horaDe(linea.at)}</time>
                        <span>{linea.text}</span>
                      </li>
                    ))}
                  </ol>
                )}
              </div>
            </>
          ) : (
            <p className="trabajos__vacio">Elegí una corrida de la lista.</p>
          )}
        </div>
      </div>
    </section>
  );
}
