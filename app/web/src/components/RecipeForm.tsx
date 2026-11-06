import type { CSSProperties } from "react";
import type {
  DatesResponse,
  Params,
  ParamSpec,
  Product,
  RangoFechas,
} from "../types";
import { Select } from "./controls/Select";
import { FechaUnica, VentanaTemporal } from "./controls/Window";
import { formatearFecha, formatearRango } from "./controls/Calendar";

// La fecha y la hora van siempre al final del formulario y en este orden, sea
// cual sea el producto: primero se eligen las opciones, después el momento.
const ORDEN_TIEMPO = [
  "ultima",
  "ultimos",
  "ultimos_n",
  "ventana",
  "fecha",
  "hora",
  "minuto",
  "hora_desde",
  "hora_hasta",
  "corrida",
  "horizonte",
];

// Secciones del inspector: agrupan el esquema que manda el backend sin que este
// archivo tenga que conocer ningún producto en particular.
const SECCIONES: {
  id: string;
  titulo: string;
  descripcion: string;
  nombres: string[];
}[] = [
  {
    id: "fuente",
    titulo: "Fuente de datos",
    descripcion: "Sensor orbital, encuadre y filtrado.",
    nombres: [
      "satelite",
      "banda",
      "capa",
      "modelo",
      "paleta",
      "encuadre",
      "limbo",
      "nitidez",
      "proyeccion",
      "detalle",
    ],
  },
  {
    id: "salida",
    titulo: "Salida & geometría",
    descripcion: "Dimensiones, aspecto 1:1 y filtros espaciales.",
    nombres: ["resolucion", "fondo", "margen", "borde", "paraguay", "snapshot", "trend"],
  },
  {
    id: "tiempo",
    titulo: "Tiempo (UTC)",
    descripcion: "Ventana, cadencia orbital y filtros por hora.",
    nombres: ORDEN_TIEMPO,
  },
  {
    id: "movimiento",
    titulo: "Movimiento & animación",
    descripcion: "Video MP4 e interpolación temporal.",
    nombres: ["animar", "fps"],
  },
];

// Clave corta para el resumen de la receta: el nombre completo no entra en un chip.
const CLAVES: Record<string, string> = {
  satelite: "sat",
  banda: "banda",
  capa: "capa",
  modelo: "modelo",
  paleta: "paleta",
  encuadre: "encuadre",
  limbo: "limbo",
  nitidez: "nitidez",
  proyeccion: "proy",
  resolucion: "px",
  fondo: "fondo",
  margen: "margen",
  detalle: "m/px",
  fps: "fps",
  ultimos_n: "cuadros",
  corrida: "ciclo",
  horizonte: "horizonte",
};

const UNIDADES: Record<string, string> = {
  fps: "fps",
  horizonte: "h",
  margen: "%",
};

interface Props {
  product: Product;
  params: Params;
  dates: DatesResponse | null;
  busy: boolean;
  error: string | null;
  onChange: (nombre: string, valor: Params[string]) => void;
  onSubmit: () => void;
}

/** Las horas del rango, como desplegable: se elige de una lista, no se arrastra. */
function opcionesHora(spec: ParamSpec) {
  const desde = Math.ceil(spec.min ?? 0);
  const hasta = Math.floor(spec.max ?? 23);
  const paso = Math.max(1, Math.floor(spec.step ?? 1));
  const salida = [];
  for (let hora = desde; hora <= hasta; hora += paso) {
    salida.push({
      value: String(hora),
      label: `${String(hora).padStart(2, "0")}:00`,
    });
  }
  return salida;
}

function numeroDe(valor: Params[string], porDefecto: unknown): number {
  const numero = Number(valor ?? porDefecto);
  return Number.isFinite(numero) ? numero : 0;
}

function igual(a: unknown, b: unknown): boolean {
  return JSON.stringify(a ?? null) === JSON.stringify(b ?? null);
}

function valorCorto(spec: ParamSpec, valor: Params[string]): string {
  if (spec.kind === "select") {
    const opcion = spec.options.find((op) => op.value === String(valor));
    const texto = opcion?.label ?? String(valor ?? spec.default ?? "—");
    const corto = texto.includes(" - ")
      ? (texto.split(" - ")[0] as string)
      : texto.replace(/\s*\([^)]*\)/g, "").trim();
    return corto.length > 24 ? `${corto.slice(0, 23)}...` : corto;
  }
  if (typeof valor === "boolean") return valor ? "sí" : "no";
  return String(valor ?? spec.default ?? "—");
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
  onChange,
  onSubmit,
}: Props) {
  const ultimaFecha = dates?.dates.at(0) ?? "";
  // Solo cuando el disco tiene las fechas: con el calendario demo no se marca.
  const disponibles = new Set(
    dates?.source === "descubierto" ? dates.dates : [],
  );
  // La placa muestra el render de la opcion elegida: satelite, paleta, modelo...
  // Los toggles se comparan serializados ("true"/"false") porque el contrato
  // de variantes viaja en el nombre del archivo.
  const textoParam = (valor: Params[string]) =>
    typeof valor === "boolean" ? String(valor) : String(valor ?? "");
  const variante = product.previews.find((muestra) =>
    Object.entries(muestra.when).every(
      ([clave, esperado]) => textoParam(params[clave]) === esperado,
    ),
  );
  const muestra = variante?.url ?? product.preview;
  const textoMuestra = (valor: unknown) =>
    valor === "true" ? "Paraguay" : valor === "false" ? "globo" : String(valor ?? "");
  const detalleMuestra = variante
    ? Object.values(variante.when).map(textoMuestra).join(" · ")
    : "";
  const ayudaFecha =
    dates && dates.source === "descubierto"
      ? `${dates.dates.length} ${
          dates.dates.length === 1 ? "fecha" : "fechas"
        } en disco · la última es ${ultimaFecha}`
      : "sin datos locales: se descargan al generar";

  // Cada spec cae en la primera sección que la nombra; lo que no figura queda
  // en "Otras opciones" para que ningún control se pierda.
  const porNombre = new Map(product.params.map((spec) => [spec.name, spec]));
  const usados = new Set<string>();
  const grupos = SECCIONES.map((seccion) => {
    const specs = seccion.nombres
      .map((nombre) => porNombre.get(nombre))
      .filter((spec): spec is ParamSpec => Boolean(spec));
    for (const spec of specs) usados.add(spec.name);
    if (seccion.id === "tiempo") {
      specs.sort(
        (uno, otro) =>
          ORDEN_TIEMPO.indexOf(uno.name) - ORDEN_TIEMPO.indexOf(otro.name),
      );
    }
    return { ...seccion, specs };
  }).filter((grupo) => grupo.specs.length > 0);

  const otros = product.params.filter((spec) => !usados.has(spec.name));
  if (otros.length > 0) {
    grupos.push({
      id: "otros",
      titulo: "Otras opciones",
      descripcion: "Parámetros que no entran en las secciones anteriores.",
      nombres: [],
      specs: otros,
    });
  }

  const hayCambios = product.params.some(
    (spec) => !igual(params[spec.name], spec.default),
  );

  function restablecerTodo() {
    for (const spec of product.params) onChange(spec.name, spec.default as Params[string]);
  }

  // Resumen de la receta: las opciones visibles + el momento elegido.
  const resumen: { clave: string; valor: string }[] = [];
  for (const spec of product.params) {
    if (ORDEN_TIEMPO.includes(spec.name)) continue;
    if (spec.kind === "select") {
      resumen.push({
        clave: CLAVES[spec.name] ?? spec.label.toLowerCase(),
        valor: valorCorto(spec, params[spec.name]),
      });
    } else if (spec.kind === "toggle" && params[spec.name] === true) {
      resumen.push({ clave: spec.label.toLowerCase(), valor: "sí" });
    }
  }

  const ventana = porNombre.get("ventana");
  const fechaSuelta = porNombre.get("fecha");
  if (ventana) {
    const rango = (params[ventana.name] ?? ventana.default) as RangoFechas;
    resumen.push({
      clave: "fecha",
      valor: formatearRango(rango.start, rango.end),
    });
  } else if (fechaSuelta) {
    resumen.push({
      clave: "fecha",
      valor: formatearFecha(String(params[fechaSuelta.name] ?? fechaSuelta.default)),
    });
  }

  const visibles = resumen.slice(0, 6);
  const restantes = resumen.length - visibles.length;

  const campo = (spec: ParamSpec) => {
    const valor = params[spec.name];
    const id = `campo-${spec.name}`;
    const ayudaId = spec.help ? `ayuda-${spec.name}` : undefined;
    // Un control puede depender de otro: "ultima" apaga fecha/hora/minuto.
    const habilitado = spec.enabled_when
      ? Object.entries(spec.enabled_when).every(
          ([clave, esperado]) => params[clave] === esperado,
        )
      : true;
    const modificado = !igual(valor, spec.default);
    const clase = habilitado ? "field" : "field field--off";

    // El punto marca "cambiaste el valor": siempre ocupa su lugar para que la
    // etiqueta no salte, y solo se pinta cuando el valor difiere del default.
    const marca = (
      <span
        className={modificado ? "field__dot" : "field__dot field__dot--off"}
        aria-hidden="true"
      />
    );

    const top = (etiqueta: string, htmlFor?: string) => (
      <div className="field__top">
        {htmlFor ? (
          <label className="field__label" htmlFor={htmlFor}>
            {marca}
            {etiqueta}
          </label>
        ) : (
          <span className="field__label">
            {marca}
            {etiqueta}
          </span>
        )}
        {modificado ? (
          <button
            type="button"
            className="field__reset"
            title={`Volver a ${String(spec.default ?? "—")}`}
            onClick={() => onChange(spec.name, spec.default as Params[string])}
          >
            restablecer
          </button>
        ) : null}
      </div>
    );

    if (spec.kind === "select") {
      return (
        <div className={clase} key={spec.name}>
          {top(spec.label, id)}
          <Select
            id={id}
            value={String(valor ?? spec.default)}
            options={spec.options}
            disabled={!habilitado}
            describedBy={ayudaId}
            onChange={(elegido) => onChange(spec.name, elegido)}
          />
          {spec.help ? (
            <span className="field__help" id={ayudaId}>
              {spec.help}
            </span>
          ) : null}
        </div>
      );
    }

    if (spec.kind === "hour") {
      return (
        <div className={clase} key={spec.name}>
          {top(spec.label, id)}
          <Select
            id={id}
            value={String(numeroDe(valor, spec.default))}
            options={opcionesHora(spec)}
            disabled={!habilitado}
            describedBy={ayudaId}
            onChange={(elegido) => onChange(spec.name, Number(elegido))}
          />
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
        <div
          className={`${clase} field--wide`}
          key={`${product.id}-${spec.name}`}
        >
          {top(spec.label)}
          <FechaUnica
            value={String(valor ?? spec.default)}
            disponibles={disponibles}
            disabled={!habilitado}
            onChange={(iso) => onChange(spec.name, iso)}
          />
          <span className="field__help">{ayudaFecha}</span>
        </div>
      );
    }

    if (spec.kind === "date-range") {
      const rango = (valor ?? spec.default) as RangoFechas;
      return (
        <div
          className={`${clase} field--wide`}
          key={`${product.id}-${spec.name}`}
        >
          {top(spec.label)}
          <VentanaTemporal
            value={rango}
            disponibles={disponibles}
            disabled={!habilitado}
            onChange={(siguiente) => onChange(spec.name, siguiente)}
          />
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
          <div className="field__top">
            <span className="field__label">
              {marca}
              {spec.label}
            </span>
            {spec.help ? <span className="field__help">{spec.help}</span> : null}
            {modificado ? (
              <button
                type="button"
                className="field__reset field__reset--start"
                onClick={() => onChange(spec.name, spec.default as Params[string])}
              >
                restablecer
              </button>
            ) : null}
          </div>
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
    const minimo = spec.min ?? 0;
    const maximo = spec.max ?? 100;
    const relleno =
      maximo > minimo ? ((numero - minimo) / (maximo - minimo)) * 100 : 0;
    const unidad = UNIDADES[spec.name];

    return (
      <div className={clase} key={spec.name}>
        <div className="field__top">
          <label className="field__label" htmlFor={id}>
            {marca}
            {spec.label}
          </label>
          <span className="field__value">
            {numero}
            {unidad ? ` ${unidad}` : ""}
          </span>
        </div>
        <div className="field__slider">
          <span className="field__bound" aria-hidden="true">
            {`${minimo}${unidad ? ` ${unidad}` : ""}`}
          </span>
          <input
            id={id}
            type="range"
            value={numero}
            min={minimo}
            max={maximo}
            step={spec.step ?? 1}
            aria-describedby={ayudaId}
            aria-valuetext={`${numero}${unidad ? ` ${unidad}` : ""}`}
            disabled={!habilitado}
            style={{ "--fill": `${relleno}%` } as CSSProperties}
            onChange={(e) => onChange(spec.name, Number(e.target.value))}
          />
          <span className="field__bound" aria-hidden="true">
            {`${maximo}${unidad ? ` ${unidad}` : ""}`}
          </span>
        </div>
        {spec.help ? (
          <span className="field__help" id={ayudaId}>
            {spec.help}
          </span>
        ) : null}
      </div>
    );
  };

  return (
    <form
      className="sheet"
      onSubmit={(evento) => {
        evento.preventDefault();
        if (busy) return;
        onSubmit();
      }}
      onKeyDown={(evento) => {
        if ((evento.ctrlKey || evento.metaKey) && evento.key === "Enter") {
          evento.preventDefault();
          if (!busy) onSubmit();
        }
      }}
    >
      <div className="work__head">
        <div>
          <h2 className="work__title">{product.name}</h2>
          <p className="work__summary">{product.summary}</p>
        </div>
        <button
          type="button"
          className="btn btn--ghost"
          disabled={!hayCambios || busy}
          onClick={restablecerTodo}
        >
          Restablecer
        </button>
      </div>

      {muestra ? (
        <figure className="plate">
          <div className="plate__frame">
            <img src={muestra} alt={`Resultado de ${product.name}`} />
          </div>
          <figcaption className="plate__cap">
            <span>salida real de este producto</span>
            <span>{detalleMuestra ? `${product.id} · ${detalleMuestra}` : product.id}</span>
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
          <dt>Última fecha</dt>
          <dd>{dates?.dates.at(0) ?? "—"}</dd>
        </div>
        <div className="folio__cell">
          <dt>Origen</dt>
          <dd>{dates?.source === "demo" ? "calendario demo" : "descubierto"}</dd>
        </div>
      </dl>

      <div className="sheet__body">
        <div className="fields">
          {grupos.map((grupo) => (
            <section key={grupo.id} className="fields__grupo">
              <header className="fields__sec">
                <h3 className="fields__title">{grupo.titulo}</h3>
                <span className="fields__sec-count">
                  {grupo.specs.length}{" "}
                  {grupo.specs.length === 1 ? "parámetro" : "parámetros"}
                </span>
                <span className="fields__desc">{grupo.descripcion}</span>
              </header>
              <div className="fields__grid">{grupo.specs.map(campo)}</div>
            </section>
          ))}
        </div>

        {!product.command_ready ? (
          <p className="sheet__note">
            No se encontró el Python del repo: solo queda disponible el preview.
          </p>
        ) : null}
      </div>

      <div className="sheet__foot">
        <div className="sheet__summary" aria-label="Resumen de la receta">
          {visibles.map((item, indice) => (
            <span className="chip" key={`${item.clave}-${indice}`}>
              <span className="chip__k">{item.clave}</span>
              <span className="chip__v">{item.valor}</span>
            </span>
          ))}
          {restantes > 0 ? (
            <span className="chip">
              <span className="chip__v">+{restantes}</span>
            </span>
          ) : null}
        </div>
        <div className="sheet__actions">
          <button className="btn btn--primary" type="submit" disabled={busy}>
            {busy ? "Encolando…" : "Generar"}
            {!busy ? <span className="btn__hint">Ctrl ↵</span> : null}
          </button>
        </div>
      </div>

      {error ? <p className="form__error">{error}</p> : null}
    </form>
  );
}
