import type { DatesResponse, Params, Product, RangoFechas } from "../types";

interface Props {
  product: Product;
  params: Params;
  dates: DatesResponse | null;
  busy: boolean;
  error: string | null;
  repoPython: string;
  onChange: (nombre: string, valor: Params[string]) => void;
  onSubmit: () => void;
}

function Etiqueta({
  spec,
  valor,
  htmlFor,
}: {
  spec: Product["params"][number];
  valor: Params[string];
  htmlFor?: string;
}) {
  const contenido = (
    <>
      {spec.label}
      {spec.kind === "slider" ? (
        <span className="field__value">{String(valor ?? spec.default)}</span>
      ) : null}
    </>
  );
  return htmlFor ? (
    <label className="field__label" htmlFor={htmlFor}>
      {contenido}
    </label>
  ) : (
    <span className="field__label">{contenido}</span>
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
  busy,
  error,
  repoPython,
  onChange,
  onSubmit,
}: Props) {
  const pideDescarga = product.params.some((spec) => spec.name === "descargar");
  const ultimaFecha = dates?.dates.at(0) ?? "";
  const ayudaFecha =
    dates && dates.source === "descubierto"
      ? `${dates.dates.length} ${
          dates.dates.length === 1 ? "fecha" : "fechas"
        } en disco · la ultima es ${ultimaFecha}`
      : "sin datos locales: se descargan al generar";

  return (
    <form
      className="sheet"
      onSubmit={(evento) => {
        evento.preventDefault();
        onSubmit();
      }}
    >
      <div className="work__head">
        <div>
          <h2 className="work__title">{product.name}</h2>
          <div className="work__meta">
            <code className="work__script">{product.stage}</code>
          </div>
        </div>
      </div>

      {product.preview ? (
        <figure className="plate">
          <div className="plate__frame">
            <img src={product.preview} alt={`Resultado de ${product.name}`} />
          </div>
          <figcaption className="plate__cap">
            <span>salida real de este producto</span>
            <span>{product.id}</span>
          </figcaption>
        </figure>
      ) : (
        <figure className="plate plate--empty">
          <p className="plate__none">sin muestra de referencia</p>
        </figure>
      )}

      <dl className="folio">
        <div className="folio__cell">
          <dt>Grupo</dt>
          <dd>{product.group}</dd>
        </div>
        <div className="folio__cell">
          <dt>Datos en disco</dt>
          <dd>
            {dates
              ? dates.source === "descubierto"
                ? `${dates.dates.length} ${
                    dates.dates.length === 1 ? "fecha" : "fechas"
                  }`
                : "ninguno"
              : "—"}
          </dd>
        </div>
        <div className="folio__cell">
          <dt>Ultima fecha</dt>
          <dd>{dates?.dates.at(0) ?? "—"}</dd>
        </div>
        <div className="folio__cell">
          <dt>Origen</dt>
          <dd>{dates?.source === "demo" ? "calendario demo" : "descubierto"}</dd>
        </div>
      </dl>

      <div className="sheet__body">
        <div className="fields">
          {product.params.map((spec) => {
            const valor = params[spec.name];
            const id = `campo-${spec.name}`;
            const ayudaId = spec.help ? `ayuda-${spec.name}` : undefined;
            // Un control puede depender de otro: "ultima" apaga fecha/hora/minuto.
            const habilitado = spec.enabled_when
              ? Object.entries(spec.enabled_when).every(
                  ([clave, esperado]) => params[clave] === esperado,
                )
              : true;
            const clase = habilitado ? "field" : "field field--off";

            if (spec.kind === "select") {
              return (
                <div className={clase} key={spec.name}>
                  <Etiqueta spec={spec} valor={valor} htmlFor={id} />
                  <select
                    id={id}
                    value={String(valor ?? spec.default)}
                    aria-describedby={ayudaId}
                    disabled={!habilitado}
                    onChange={(e) => onChange(spec.name, e.target.value)}
                  >
                    {spec.options.map((opcion) => (
                      <option key={opcion.value} value={opcion.value}>
                        {opcion.label}
                      </option>
                    ))}
                  </select>
                  {spec.help ? (
                    <span className="field__help" id={ayudaId}>
                      {spec.help}
                    </span>
                  ) : null}
                </div>
              );
            }

            if (spec.kind === "date") {
              return (
                <div className={clase} key={spec.name}>
                  <Etiqueta spec={spec} valor={valor} htmlFor={id} />
                  <input
                    id={id}
                    type="date"
                    value={String(valor ?? spec.default)}
                    disabled={!habilitado}
                    onChange={(e) => onChange(spec.name, e.target.value)}
                  />
                  <span className="field__help">{ayudaFecha}</span>
                </div>
              );
            }

            if (spec.kind === "date-range") {
              const rango = (valor ?? spec.default) as RangoFechas;
              return (
                <div
                  className={habilitado ? "field field--wide" : "field field--wide field--off"}
                  key={spec.name}
                >
                  <Etiqueta spec={spec} valor={valor} />
                  <div className="field__range">
                    <input
                      type="date"
                      value={rango.start}
                      aria-label={`${spec.label}: desde`}
                      disabled={!habilitado}
                      onChange={(e) =>
                        onChange(spec.name, { ...rango, start: e.target.value })
                      }
                    />
                    <span>hasta</span>
                    <input
                      type="date"
                      value={rango.end}
                      aria-label={`${spec.label}: hasta`}
                      disabled={!habilitado}
                      onChange={(e) =>
                        onChange(spec.name, { ...rango, end: e.target.value })
                      }
                    />
                  </div>
                  <span className="field__help">{ayudaFecha}</span>
                </div>
              );
            }

            if (spec.kind === "toggle") {
              return (
                <div
                  className={
                    habilitado ? "field field--toggle" : "field field--toggle field--off"
                  }
                  key={spec.name}
                >
                  <span className="field__label">
                    {spec.label}
                    {spec.help ? (
                      <span className="field__help">{spec.help}</span>
                    ) : null}
                  </span>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={Boolean(valor)}
                    aria-label={spec.label}
                    className="switch"
                    disabled={!habilitado}
                    onClick={() => onChange(spec.name, !valor)}
                  >
                    <span />
                  </button>
                </div>
              );
            }

            const numero = Number(valor ?? spec.default);
            return (
              <div className={clase} key={spec.name}>
                <Etiqueta spec={spec} valor={valor} htmlFor={id} />
                <input
                  id={id}
                  type="range"
                  value={numero}
                  min={spec.min ?? 0}
                  max={spec.max ?? 100}
                  step={spec.step ?? 1}
                  aria-describedby={ayudaId}
                  disabled={!habilitado}
                  onChange={(e) => onChange(spec.name, Number(e.target.value))}
                />
                {spec.help ? (
                  <span className="field__help" id={ayudaId}>
                    {spec.help}
                  </span>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>

      <div className="sheet__foot">
        <p className="sheet__note">
          {product.command_ready ? (
            <>
              Corre con <code>{repoPython.split("\\").slice(-3).join("\\")}</code>.{" "}
              {pideDescarga
                ? "Las descargas usan la carpeta de datos compartida y quedan cacheadas."
                : "Sin descarga: usa lo que ya esta en disco, y si falta algo el job lo dice."}
            </>
          ) : (
            <>
              No se encontro el Python del repo: falta <code>{repoPython}</code>. Solo
              queda disponible el preview.
            </>
          )}
        </p>
        <button className="btn btn--primary" type="submit" disabled={busy}>
          {busy ? "Encolando…" : "Generar"}
        </button>
      </div>

      {error ? <p className="form__error">{error}</p> : null}
    </form>
  );
}
