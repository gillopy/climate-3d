import { useCallback, useEffect, useState } from "react";
import {
  cancelJob,
  createJob,
  getCatalog,
  getDates,
  getJob,
  getJobs,
  revealJob,
  subscribeJob,
} from "./api";
import { JobPanel } from "./components/JobPanel";
import { Reloj } from "./components/controls/Clock";
import { RecipeForm } from "./components/RecipeForm";
import type {
  CatalogResponse,
  DatesResponse,
  Job,
  JobSummary,
  Params,
  Product,
} from "./types";

const EN_MARCHA = (estado: JobSummary["status"]) =>
  estado === "queued" || estado === "running";

function valoresIniciales(producto: Product): Params {
  const salida: Params = {};
  for (const spec of producto.params) {
    salida[spec.name] = spec.default as Params[string];
  }
  return salida;
}

export default function App() {
  const [catalogo, setCatalogo] = useState<CatalogResponse | null>(null);
  const [producto, setProducto] = useState<Product | null>(null);
  const [params, setParams] = useState<Params>({});
  const [fechas, setFechas] = useState<DatesResponse | null>(null);

  // La cola y el historial viven aparte del detalle: la lista se refresca por
  // sondeo (y es liviana), el detalle se pide completo una sola vez y despues
  // lo mantiene vivo el stream.
  const [corridas, setCorridas] = useState<JobSummary[]>([]);
  const [detalle, setDetalle] = useState<Job | null>(null);
  const [activa, setActiva] = useState<string | null>(null);
  // Relanzar la misma receta reusa el id del job: esto fuerza la resuscripcion.
  const [reintento, setReintento] = useState(0);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const satelite = typeof params.satelite === "string" ? params.satelite : "";
  const banda = typeof params.banda === "string" ? params.banda : "";

  const refrescarCorridas = useCallback(async () => {
    try {
      setCorridas(await getJobs());
    } catch {
      // El sondeo no discute: si falla, se reintenta en el proximo tic.
    }
  }, []);

  useEffect(() => {
    void refrescarCorridas();
  }, [refrescarCorridas]);

  useEffect(() => {
    getCatalog()
      .then((datos) => {
        setCatalogo(datos);
        if (datos.products.length > 0) elegir(datos.products[0]);
      })
      .catch((exc: unknown) => {
        setError(exc instanceof Error ? exc.message : "no se pudo leer el catalogo");
      });
    // Un solo fetch al montar.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Las fechas dependen del producto y, en GOES, tambien del satelite y la banda.
  useEffect(() => {
    if (!producto) return;
    let vigente = true;
    const extra = satelite || banda ? { satelite, banda } : undefined;
    getDates(producto.id, extra)
      .then((datos) => {
        if (vigente) setFechas(datos);
      })
      .catch(() => {
        if (vigente) setFechas(null);
      });
    return () => {
      vigente = false;
    };
  }, [producto, satelite, banda]);

  // Con historial y sin seleccion, se abre la corrida mas nueva.
  useEffect(() => {
    if (activa && corridas.some((corrida) => corrida.id === activa)) return;
    if (corridas.length > 0) setActiva(corridas[0].id);
  }, [corridas, activa]);

  // Mientras haya algo en cola o corriendo, la lista se refresca sola.
  const enMarcha = corridas.some((corrida) => EN_MARCHA(corrida.status));
  useEffect(() => {
    if (!enMarcha) return;
    const tic = window.setInterval(() => void refrescarCorridas(), 2500);
    return () => window.clearInterval(tic);
  }, [enMarcha, refrescarCorridas]);

  // La corrida elegida: snapshot completo una vez y despues lo mantiene el stream.
  useEffect(() => {
    if (!activa) {
      setDetalle(null);
      return;
    }
    let vigente = true;
    let llegado = false;

    getJob(activa)
      .then((job) => {
        // El stream manda: si ya llego su snapshot, este no lo pisa.
        if (vigente && !llegado) setDetalle(job);
      })
      .catch((exc: unknown) => {
        if (vigente) {
          setError(exc instanceof Error ? exc.message : "no se pudo leer la corrida");
        }
      });

    const corte = subscribeJob(activa, {
      onSnapshot: (job) => {
        llegado = true;
        if (vigente) setDetalle(job);
      },
      onLog: (linea) =>
        setDetalle((previo) =>
          previo && previo.id === activa
            ? { ...previo, logs: [...previo.logs, linea] }
            : previo,
        ),
      onProgress: (progress, stage) =>
        setDetalle((previo) =>
          previo && previo.id === activa ? { ...previo, progress, stage } : previo,
        ),
      onArtifact: (artefacto) =>
        setDetalle((previo) => {
          if (!previo || previo.id !== activa) return previo;
          if (previo.artifacts.some((arte) => arte.url === artefacto.url)) {
            return previo;
          }
          return { ...previo, artifacts: [...previo.artifacts, artefacto] };
        }),
      onFinal: () => void refrescarCorridas(),
      onFallo: (mensaje) => {
        if (vigente) setError(mensaje);
      },
    });

    return () => {
      vigente = false;
      corte();
    };
  }, [activa, reintento, refrescarCorridas]);

  // Solo se muestra el detalle de la corrida elegida: mientras llega, el panel
  // no muestra la anterior como si fuera la nueva.
  const actual = detalle && detalle.id === activa ? detalle : null;

  function elegir(siguiente: Product) {
    setProducto(siguiente);
    setParams(valoresIniciales(siguiente));
    setError(null);
  }

  function elegirCorrida(id: string) {
    setActiva(id);
  }

  async function generar() {
    if (!producto) return;
    setEnviando(true);
    setError(null);
    try {
      const nuevo = await createJob(producto.id, params);
      setDetalle(nuevo);
      setActiva(nuevo.id);
      // Misma receta = mismo id de job: hay que volver a suscribirse igual.
      setReintento((numero) => numero + 1);
      void refrescarCorridas();
    } catch (exc: unknown) {
      setError(exc instanceof Error ? exc.message : "no se pudo crear el job");
    } finally {
      setEnviando(false);
    }
  }

  async function cancelar() {
    if (!actual) return;
    try {
      const actualizado = await cancelJob(actual.id);
      setDetalle(actualizado);
      void refrescarCorridas();
    } catch (exc: unknown) {
      setError(exc instanceof Error ? exc.message : "no se pudo cancelar");
    }
  }

  async function revelar() {
    if (!actual) return;
    try {
      await revealJob(actual.id);
    } catch (exc: unknown) {
      setError(exc instanceof Error ? exc.message : "no se pudo abrir la carpeta");
    }
  }

  const listo = catalogo?.repo_ready === true;
  const conDatos = catalogo?.data_root_exists === true;
  // Agrupa por nombre conservando el orden en que el catalogo los presenta.
  const grupos: { nombre: string; items: Product[] }[] = [];
  const porGrupo = new Map<string, Product[]>();
  for (const item of catalogo?.products ?? []) {
    const lista = porGrupo.get(item.group);
    if (lista) {
      lista.push(item);
    } else {
      const nueva = [item];
      porGrupo.set(item.group, nueva);
      grupos.push({ nombre: item.group, items: nueva });
    }
  }

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <h1>Climate 3D</h1>
          <span className="brand__sub">consola de render</span>
        </div>
        <div className="health">
          <span className="health__item health__item--count">
            {catalogo ? `${catalogo.products.length} productos` : "leyendo catalogo"}
          </span>
          <span
            className={`health__item ${
              listo ? "health__item--ok" : "health__item--warn"
            }`}
            title={catalogo?.repo_python ?? ""}
          >
            <span className="health__swatch" aria-hidden="true" />
            {listo ? "pipeline listo" : "sin .venv del repo"}
          </span>
          <span
            className={`health__item ${
              conDatos ? "health__item--ok" : "health__item--warn"
            }`}
            title={catalogo?.data_root ?? ""}
          >
            <span className="health__swatch" aria-hidden="true" />
            {conDatos ? "datos en disco" : "sin datos locales"}
          </span>
          <Reloj />
        </div>
      </header>

      {error ? (
        <p className="notice" role="alert">
          <strong>Aviso</strong>
          {error}
        </p>
      ) : null}

      <main className="layout">
        <section className="rail" aria-label="Productos disponibles">
          <div className="rail__head">
            <h2 className="rail__title" id="productos-titulo">
              Productos
            </h2>
            <span className="rail__count">
              {catalogo ? String(catalogo.products.length).padStart(2, "0") : "—"}
            </span>
          </div>
          <ul className="catalog" aria-labelledby="productos-titulo">
            {grupos.map((grupo) => (
              <li key={grupo.nombre} className="catalog__grupo">
                <p className="catalog__grupo-nombre" id={`grupo-${grupo.nombre}`}>
                  {grupo.nombre}
                </p>
                <ul className="catalog__lista" aria-labelledby={`grupo-${grupo.nombre}`}>
                  {grupo.items.map((item) => {
                    const activo = producto?.id === item.id;
                    return (
                      <li key={item.id}>
                        <button
                          type="button"
                          className="catalog__item"
                          aria-current={activo ? "true" : undefined}
                          onClick={() => elegir(item)}
                        >
                          {item.preview ? (
                            <img
                              className="catalog__thumb"
                              src={item.preview}
                              alt=""
                              loading="lazy"
                            />
                          ) : (
                            <span className="catalog__thumb" aria-hidden="true" />
                          )}
                          <span className="catalog__body">
                            <span className="catalog__name">{item.name}</span>
                            <span className="catalog__desc">{item.summary}</span>
                          </span>
                          <span className="catalog__mark" aria-hidden="true" />
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </li>
            ))}
          </ul>
          {catalogo === null && !error ? (
            <p className="rail__empty">Leyendo el catalogo…</p>
          ) : null}
        </section>

        <section className="work" aria-label="Receta del producto">
          {producto ? (
            <RecipeForm
              product={producto}
              params={params}
              dates={fechas}
              busy={enviando}
              error={null}
              repoPython={catalogo?.repo_python ?? ".venv\\Scripts\\python.exe"}
              onChange={(nombre, valor) =>
                setParams((previo) => ({ ...previo, [nombre]: valor }))
              }
              onSubmit={generar}
            />
          ) : (
            <p className="rail__empty">Elegi un producto para empezar.</p>
          )}
        </section>

        <JobPanel
          job={actual}
          corridas={corridas}
          onSelect={elegirCorrida}
          onCancel={cancelar}
          onReveal={revelar}
        />
      </main>
    </div>
  );
}
