import { useCallback, useEffect, useRef, useState } from "react";

import { cancelJob, getJob, getJobs, revealJob, subscribeJob } from "../api";
import { pesoArchivo, resumenStats } from "../formato";
import type { StatsRow } from "../formato";
import type { Job, JobSummary } from "../types";
import { ComparadorBarrido } from "./ComparadorBarrido";
import type { CapaBarrido } from "./ComparadorBarrido";

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

/**
 * Fecha corta de una capa del comparador. El JSON de la corrida guarda la
 * marca completa; en la etiqueta alcanza el día.
 */
function fechaDeCapa(valor: unknown, respaldo: string): string {
  const texto = typeof valor === "string" ? valor.trim() : "";
  return texto ? texto.slice(0, 10) : respaldo;
}

interface Props {
  /** Id del trabajo recién creado: se selecciona y se trae a la vista. */
  jobInicial: string | null;
}

/**
 * Panel de trabajos: historial de corridas con logs y resultados.
 *
 * Vive en la misma columna que los hiperparámetros. El backend ya persiste el
 * historial (`/api/jobs`) y el detalle de cada job (`/api/jobs/{id}`), ademas
 * del stream SSE: aca se muestran juntos para volver a una corrida anterior.
 */
export function JobsPanel({ jobInicial }: Props) {
  const raiz = useRef<HTMLElement | null>(null);
  const logRef = useRef<HTMLOListElement | null>(null);
  /** false cuando el usuario subio a leer una linea vieja: ahi no se autoscrollea. */
  const seguirLog = useRef(true);
  const [corridas, setCorridas] = useState<JobSummary[]>([]);
  const [seleccionId, setSeleccionId] = useState<string | null>(null);
  const [detalle, setDetalle] = useState<Job | null>(null);
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Comparador de barrido: lo que muestra la ventana flotante, o null cerrada.
  const [comparador, setComparador] = useState<{
    antes: CapaBarrido;
    despues: CapaBarrido;
    titulo: string;
  } | null>(null);

  const refrescarLista = useCallback(async () => {
    try {
      const lista = await getJobs();
      setCorridas(lista);
    } catch {
      // El sondeo no discute: si falla, se reintenta en el proximo tic.
    }
  }, []);

  // Una corrida nueva se selecciona sola y se trae a la vista.
  useEffect(() => {
    if (!jobInicial) return;
    setSeleccionId(jobInicial);
    raiz.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [jobInicial]);

  // Al cambiar de corrida se vuelve a seguir el final del log.
  useEffect(() => {
    seguirLog.current = true;
  }, [seleccionId]);

  // Cada linea nueva baja el log, salvo que el usuario haya subido a leer.
  // La dependencia es el array (identidad nueva por linea): con el largo, al
  // llegar al tope de 400 lineas dejaria de seguir.
  useEffect(() => {
    const lista = logRef.current;
    if (!lista || !seguirLog.current) return;
    lista.scrollTop = lista.scrollHeight;
  }, [detalle?.id, detalle?.logs]);

  function alDesplazarLog() {
    const lista = logRef.current;
    if (!lista) return;
    seguirLog.current = lista.scrollHeight - lista.scrollTop - lista.clientHeight < 32;
  }

  // Sin seleccion (o si la corrida se podó), abre la mas nueva.
  useEffect(() => {
    if (seleccionId && corridas.some((corrida) => corrida.id === seleccionId)) {
      return;
    }
    if (corridas.length > 0) setSeleccionId(corridas[0].id);
  }, [corridas, seleccionId]);

  // Lista: se refresca siempre, sin depender de un boton que abra el panel.
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
    if (!seleccionId) return;
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
  }, [seleccionId, actualizarFila, refrescarLista]);

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
  // El producto de cambio deja el par como `*_antes.png` / `*_despues.png`:
  // ese sufijo es el contrato con el pipeline y lo unico que pide el barrido.
  const capaAntes = imagenes.find((arte) => /_antes\.png$/i.test(arte.name)) ?? null;
  const capaDespues =
    imagenes.find((arte) => /_despues\.png$/i.test(arte.name)) ?? null;

  function abrirComparador() {
    if (!capaAntes || !capaDespues) return;
    setComparador({
      antes: {
        url: capaAntes.url,
        etiqueta: fechaDeCapa(stats?.fecha_antes, "Antes"),
      },
      despues: {
        url: capaDespues.url,
        etiqueta: fechaDeCapa(stats?.fecha_despues, "Después"),
      },
      titulo: `${String(detalle?.params.producto ?? "cambio")} · ${
        detalle ? fechaHora(detalle.created_at) : "corrida"
      }`,
    });
  }

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

  return (
    <section className="trabajos" aria-label="Trabajos NISAR" ref={raiz}>
      <header className="trabajos__head">
        <h2 className="trabajos__title">Trabajos</h2>
        <span className="trabajos__count" aria-live="polite">
          {String(corridas.length).padStart(2, "0")}
        </span>
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
                  {capaAntes && capaDespues ? (
                    <div className="trabajos__barrido">
                      <button
                        type="button"
                        className="btn btn--primary"
                        title="Abre una ventana flotante con el antes y el después en el mismo mapa: arrastrás la línea"
                        onClick={abrirComparador}
                      >
                        <svg
                          width="14"
                          height="14"
                          viewBox="0 0 16 16"
                          fill="none"
                          aria-hidden="true"
                        >
                          <rect
                            x="1.5"
                            y="4"
                            width="13"
                            height="8"
                            rx="1.2"
                            stroke="currentColor"
                            strokeWidth="1.3"
                          />
                          <path d="M8 2.5v11" stroke="currentColor" strokeWidth="1.3" />
                          <path
                            d="M5.6 6.2 3.6 8l2 1.8M10.4 6.2l2 1.8-2 1.8"
                            stroke="currentColor"
                            strokeWidth="1.2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                        Comparar antes/después
                      </button>
                      <span className="trabajos__barrido-hint">
                        Ventana flotante con barrido: arrastrás la línea y ves el antes y el
                        después en el mismo mapa.
                      </span>
                    </div>
                  ) : null}
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
                  <ol
                    className="trabajos__logs"
                    ref={logRef}
                    onScroll={alDesplazarLog}
                  >
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

      {/* `dialog` va en la capa superior del navegador: no lo recorta el panel. */}
      {comparador ? (
        <ComparadorBarrido
          antes={comparador.antes}
          despues={comparador.despues}
          titulo={comparador.titulo}
          alCerrar={() => setComparador(null)}
        />
      ) : null}
    </section>
  );
}
