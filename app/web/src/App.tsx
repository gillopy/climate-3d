import { useEffect, useRef, useState } from "react";
import {
  cancelJob,
  createJob,
  getCatalog,
  getDates,
  revealJob,
  subscribeJob,
} from "./api";
import { JobPanel } from "./components/JobPanel";
import { RecipeForm } from "./components/RecipeForm";
import type {
  CatalogResponse,
  DatesResponse,
  Job,
  Params,
  Product,
} from "./types";

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
  const [job, setJob] = useState<Job | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const corte = useRef<(() => void) | null>(null);

  const satelite = typeof params.satelite === "string" ? params.satelite : "";
  const banda = typeof params.banda === "string" ? params.banda : "";

  useEffect(() => {
    getCatalog()
      .then((datos) => {
        setCatalogo(datos);
        if (datos.products.length > 0) elegir(datos.products[0]);
      })
      .catch((exc: unknown) => {
        setError(exc instanceof Error ? exc.message : "no se pudo leer el catalogo");
      });

    return () => corte.current?.();
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

  function elegir(siguiente: Product) {
    setProducto(siguiente);
    setParams(valoresIniciales(siguiente));
    setError(null);
  }

  async function generar() {
    if (!producto) return;
    setEnviando(true);
    setError(null);
    try {
      const nuevo = await createJob(producto.id, params);
      setJob(nuevo);

      // Un pedido viejo no debe seguir escribiendo en el panel nuevo.
      corte.current?.();
      corte.current = subscribeJob(nuevo.id, {
        onSnapshot: (actual) => setJob(actual),
        onLog: (linea) =>
          setJob((previo) =>
            previo ? { ...previo, logs: [...previo.logs, linea] } : previo,
          ),
        onProgress: (progress, stage) =>
          setJob((previo) => (previo ? { ...previo, progress, stage } : previo)),
        onArtifact: (artefacto) =>
          setJob((previo) =>
            previo ? { ...previo, artifacts: [...previo.artifacts, artefacto] } : previo,
          ),
        onFallo: (mensaje) => setError(mensaje),
      });
    } catch (exc: unknown) {
      setError(exc instanceof Error ? exc.message : "no se pudo crear el job");
    } finally {
      setEnviando(false);
    }
  }

  async function cancelar() {
    if (!job) return;
    try {
      const actualizado = await cancelJob(job.id);
      setJob(actualizado);
    } catch (exc: unknown) {
      setError(exc instanceof Error ? exc.message : "no se pudo cancelar");
    }
  }

  async function revelar() {
    if (!job) return;
    try {
      await revealJob(job.id);
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

        <JobPanel job={job} onCancel={cancelar} onReveal={revelar} />
      </main>
    </div>
  );
}
