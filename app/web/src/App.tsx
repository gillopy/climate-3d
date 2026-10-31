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

  return (
    <div className="shell">
      <header className="cabecera">
        <div className="marca">
          <span className="marca__punto" />
          <div>
            <h1>Climate 3D</h1>
            <p>consola interactiva</p>
          </div>
        </div>
        <div className="pills">
          <span className="pill">
            {catalogo ? `${catalogo.products.length} productos` : "cargando..."}
          </span>
          <span
            className={`pill ${catalogo?.repo_ready ? "pill--ok" : "pill--warn"}`}
            title={catalogo?.repo_python ?? ""}
          >
            {catalogo?.repo_ready ? "pipeline listo" : "sin .venv del repo"}
          </span>
          <span
            className={`pill ${catalogo?.data_root_exists ? "pill--ok" : "pill--warn"}`}
            title={catalogo?.data_root ?? ""}
          >
            {catalogo?.data_root_exists ? "datos en disco" : "sin datos locales"}
          </span>
        </div>
      </header>

      {error ? <div className="banner">{error}</div> : null}

      <main className="grilla">
        <nav className="productos">
          <h2>Productos</h2>
          {(catalogo?.products ?? []).map((item) => (
            <button
              key={item.id}
              type="button"
              className={`producto${producto?.id === item.id ? " producto--activo" : ""}`}
              onClick={() => elegir(item)}
            >
              {item.preview ? (
                <img
                  className="producto__preview"
                  src={item.preview}
                  alt=""
                  loading="lazy"
                />
              ) : null}
              <span className="producto__grupo">{item.group}</span>
              <span className="producto__nombre">{item.name}</span>
              <span className="producto__resumen">{item.summary}</span>
            </button>
          ))}
          {catalogo === null && !error ? (
            <p className="tenue">Leyendo el catalogo...</p>
          ) : null}
        </nav>

        <section className="centro">
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
            <p className="tenue">Elegi un producto para empezar.</p>
          )}
        </section>

        <JobPanel job={job} onCancel={cancelar} onReveal={revelar} />
      </main>
    </div>
  );
}
