import type { DatesResponse, Params, Product, RangoFechas, RunMode } from "../types";

interface Props {
  product: Product;
  params: Params;
  dates: DatesResponse | null;
  mode: RunMode;
  busy: boolean;
  error: string | null;
  onChange: (nombre: string, valor: Params[string]) => void;
  onMode: (modo: RunMode) => void;
  onSubmit: () => void;
}

function Etiqueta({ texto, ayuda }: { texto: string; ayuda?: string }) {
  return (
    <div className="campo__etiqueta">
      <span>{texto}</span>
      {ayuda ? <span className="campo__ayuda">{ayuda}</span> : null}
    </div>
  );
}

/**
 * El formulario no sabe que producto esta mostrando: recorre el esquema que
 * manda el backend. Un producto nuevo aparece solo, sin tocar este archivo.
 */
export function RecipeForm({
  product,
  params,
  dates,
  mode,
  busy,
  error,
  onChange,
  onMode,
  onSubmit,
}: Props) {
  const primeraFecha = dates?.dates.at(-1) ?? "";
  const ultimaFecha = dates?.dates.at(0) ?? "";

  return (
    <form
      className="receta"
      onSubmit={(evento) => {
        evento.preventDefault();
        onSubmit();
      }}
    >
      <div className="receta__cabecera">
        <h2>{product.name}</h2>
        <p className="receta__resumen">{product.summary}</p>
        <code className="receta__script">{product.stage}</code>
      </div>

      {product.params.map((spec) => {
        const valor = params[spec.name];

        if (spec.kind === "select") {
          return (
            <div className="campo" key={spec.name}>
              <Etiqueta texto={spec.label} ayuda={spec.help || undefined} />
              <select
                value={String(valor ?? spec.default)}
                onChange={(e) => onChange(spec.name, e.target.value)}
              >
                {spec.options.map((opcion) => (
                  <option key={opcion.value} value={opcion.value}>
                    {opcion.label}
                  </option>
                ))}
              </select>
            </div>
          );
        }

        if (spec.kind === "date-range") {
          const rango = (valor ?? spec.default) as RangoFechas;
          return (
            <div className="campo" key={spec.name}>
              <Etiqueta
                texto={spec.label}
                ayuda={
                  dates?.source === "demo"
                    ? "calendario de demostracion: no hay salidas de este producto en disco"
                    : "fechas con datos en disco"
                }
              />
              <div className="campo__rango">
                <input
                  type="date"
                  value={rango.start}
                  min={primeraFecha}
                  max={ultimaFecha}
                  onChange={(e) => onChange(spec.name, { ...rango, start: e.target.value })}
                />
                <span className="campo__hasta">hasta</span>
                <input
                  type="date"
                  value={rango.end}
                  min={primeraFecha}
                  max={ultimaFecha}
                  onChange={(e) => onChange(spec.name, { ...rango, end: e.target.value })}
                />
              </div>
            </div>
          );
        }

        if (spec.kind === "toggle") {
          return (
            <div className="campo campo--fila" key={spec.name}>
              <Etiqueta texto={spec.label} />
              <button
                type="button"
                role="switch"
                aria-checked={Boolean(valor)}
                className={`switch${valor ? " switch--on" : ""}`}
                onClick={() => onChange(spec.name, !valor)}
              >
                <span />
              </button>
            </div>
          );
        }

        const numero = Number(valor ?? spec.default);
        return (
          <div className="campo" key={spec.name}>
            <Etiqueta texto={`${spec.label}: ${numero}`} ayuda={spec.help || undefined} />
            <input
              type="range"
              value={numero}
              min={spec.min ?? 0}
              max={spec.max ?? 100}
              step={spec.step ?? 1}
              onChange={(e) => onChange(spec.name, Number(e.target.value))}
            />
          </div>
        );
      })}

      <div className="receta__modo">
        <label className={product.command_ready ? "" : "receta__modo--off"}>
          <input
            type="radio"
            name="modo"
            checked={mode === "preview"}
            onChange={() => onMode("preview")}
          />
          Preview sintetico (funciona sin datos)
        </label>
        <label className={product.command_ready ? "" : "receta__modo--off"}>
          <input
            type="radio"
            name="modo"
            checked={mode === "real"}
            disabled={!product.command_ready}
            onChange={() => onMode("real")}
          />
          Script real del repo
        </label>
      </div>

      {product.command_ready ? null : (
        <p className="receta__aviso">
          El comando real todavia no esta conectado: falta una linea en{" "}
          <code>catalog.py</code> con los flags que acepta el script.
        </p>
      )}

      {error ? <p className="receta__error">{error}</p> : null}

      <button className="boton boton--primario" type="submit" disabled={busy}>
        {busy ? "Encolando..." : "Generar"}
      </button>
    </form>
  );
}
