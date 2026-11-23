import type { CSSProperties } from "react";
import { useEffect, useState } from "react";
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
import { coincideParams, opcionesVisibles, pisoDeSatelite } from "../opciones";
import { earthdataLogin, earthdataCookiesStatus } from "../api";

// El momento de captura y sus banderas ("snapshot", "ultimo", "ultimos") van
// juntos en el mismo bloque temporal para que los controles dependientes se
// vean lado a lado.
const ORDEN_TIEMPO = [
  "snapshot",
  "ultimo",
  "ultima",
  "ultimos",
  "ultimos_n",
  "ventana_preset",
  "ventana",
  "fecha",
  "hora",
  "minuto",
  "hora_desde",
  "hora_hasta",
  "corrida",
  "horizonte",
  "trend",
];

// Secciones del pipeline científico: agrupan el esquema que manda el backend
// en 5 etapas limpias sin dejar parámetros huérfanos en "Otras opciones".
const SECCIONES: {
  id: string;
  titulo: string;
  descripcion: string;
  nombres: string[];
}[] = [
  {
    id: "fuente",
    titulo: "Fuente & sensor",
    descripcion: "Sensor orbital, banda espectral, modelo y paleta.",
    nombres: [
      "satelite",
      "banda",
      "capa",
      "variante",
      "compuesto",
      "modelo",
      "paleta",
      "nitidez",
      "limbo",
      "detalle",
    ],
  },
  {
    id: "encuadre",
    titulo: "Encuadre & superposiciones",
    descripcion: "Proyección espacial, recorte Paraguay y focos FIRMS.",
    nombres: [
      "encuadre",
      "proyeccion",
      "paraguay",
      "margen",
      "firms",
      "firms_fuente",
      "firms_alcance",
      "firms_ventana",
    ],
  },
  {
    id: "salida",
    titulo: "Salida & composición",
    descripcion: "Resolución en píxeles, fondo, bordes y mezcla.",
    nombres: ["resolucion", "fondo", "borde", "alpha"],
  },
  {
    id: "tiempo",
    titulo: "Ventana temporal & captura (UTC)",
    descripcion: "Snapshot, último slot publicado, calendario y horarios.",
    nombres: ORDEN_TIEMPO,
  },
  {
    id: "movimiento",
    titulo: "Movimiento & animación",
    descripcion: "Secuencia MP4 y cadencia de cuadros por segundo.",
    nombres: ["animar", "fps"],
  },
];

// Metadatos visuales de cada familia científica del catálogo.
const FAMILIA_META: Record<
  string,
  { etiqueta: string; sensor: string }
> = {
  satelite: { etiqueta: "Observación satelital", sensor: "GOES · VIIRS · PACE · Himawari · MUR" },
  modelo: { etiqueta: "Modelo numérico", sensor: "ECMWF · IFS · AIFS" },
  vegetacion: { etiqueta: "Biósfera & vegetación", sensor: "PACE OCI · LandVI" },
  radar: { etiqueta: "Radar apertura sintética", sensor: "NISAR L-Band SAR" },
};

// Parámetros subordinados a un toggle principal: se marcan visualmente como
// sub-control acoplado para que el flujo de parametrización sea evidente.
const SUBORDINADOS: Record<string, string> = {
  margen: "paraguay",
  variante: "capa",
  firms_fuente: "firms",
  firms_alcance: "firms",
  firms_ventana: "firms",
  ultimo: "snapshot",
  ultimos_n: "ultimos",
  ventana: "ventana_preset",
  fps: "animar",
};

// Clave corta para el resumen de la receta: el nombre completo no entra en un chip.
const CLAVES: Record<string, string> = {
  satelite: "sat",
  banda: "banda",
  capa: "capa",
  variante: "variante",
  compuesto: "comp",
  modelo: "modelo",
  paleta: "paleta",
  encuadre: "encuadre",
  limbo: "limbo",
  nitidez: "nitidez",
  proyeccion: "proy",
  resolucion: "px",
  fondo: "fondo",
  borde: "borde",
  alpha: "alpha",
  margen: "margen",
  detalle: "m/px",
  firms: "FIRMS",
  firms_fuente: "sensor FIRMS",
  firms_alcance: "alcance FIRMS",
  firms_ventana: "ventana FIRMS",
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
  onReset?: () => void;
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
function limpiarAyuda(texto: string): string {
  if (!texto) return "";
  return texto
    .replace(/clean_ir es la del modulo comun\/paleta_gibs\.py/gi, "Paleta infrarroja oficial de NASA GIBS")
    .replace(/;?\s*necesita el MAP_KEY en datos\/firms_map_key\.txt/gi, "")
    .replace(/define la carpeta de datos\s+\S+/gi, "Selecciona el satélite geoestacionario")
    .replace(/\b[\w./-]+\.(?:py|txt)\b/g, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

export function RecipeForm({
  product,
  params,
  dates,
  busy,
  error,
  onChange,
  onReset,
  onSubmit,
}: Props) {
  const ultimaFecha = dates?.dates.at(0) ?? "";
  // Earthdata login interactivo para PACE LANDVI (follaje)
  const [earthdataConfigurado, setEarthdataConfigurado] = useState(false);
  const [earthdataLogueando, setEarthdataLogueando] = useState(false);
  const [earthdataError, setEarthdataError] = useState<string | null>(null);

  useEffect(() => {
    if (product.id === "follaje") {
      earthdataCookiesStatus()
        .then((estado) => setEarthdataConfigurado(estado.configured))
        .catch(() => setEarthdataConfigurado(false));
    }
  }, [product.id]);

  async function loginEarthdata() {
    if (product.id !== "follaje") return;
    setEarthdataLogueando(true);
    setEarthdataError(null);
    try {
      const resp = await earthdataLogin();
      if (resp.ok) {
        setEarthdataConfigurado(true);
      } else {
        setEarthdataError(resp.message);
      }
    } catch (exc) {
      setEarthdataError(exc instanceof Error ? exc.message : "Error de login");
    } finally {
      setEarthdataLogueando(false);
    }
  }
  // Solo cuando el disco tiene las fechas: con el calendario demo no se marca.
  const disponibles = new Set(
    dates?.source === "descubierto" ? dates.dates : [],
  );
  // Hasta dónde puede irse atrás el calendario si no hay datos en disco.
  const pisoFecha = pisoDeSatelite(params);
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

  // Cada spec cae en la sección que la nombra y conserva el orden canónico de
  // `seccion.nombres`. Los controles con `visible_when` no se dibujan hasta que
  // el control padre toma el valor esperado.
  const porNombre = new Map(product.params.map((spec) => [spec.name, spec]));
  const visible = (spec: ParamSpec) =>
    coincideParams(spec.visible_when, params);
  const usados = new Set<string>();
  const grupos = SECCIONES.map((seccion) => {
    const specs = seccion.nombres
      .map((nombre) => porNombre.get(nombre))
      .filter((spec): spec is ParamSpec => Boolean(spec));
    for (const spec of specs) usados.add(spec.name);
    return { ...seccion, specs: specs.filter(visible) };
  }).filter((grupo) => grupo.specs.length > 0);

  const otros = product.params.filter(
    (spec) => !usados.has(spec.name) && visible(spec),
  );
  if (otros.length > 0) {
    grupos.push({
      id: "otros",
      titulo: "Parámetros adicionales",
      descripcion: "Opciones específicas del producto.",
      nombres: [],
      specs: otros,
    });
  }

  const familia = FAMILIA_META[product.group] ?? {
    etiqueta: product.group,
    sensor: "Observación satelital",
  };

  const hayCambios = product.params.some(
    (spec) => visible(spec) && !igual(params[spec.name], spec.default),
  );

  function restablecerTodo() {
    if (onReset) {
      onReset();
      return;
    }
    for (const spec of product.params) onChange(spec.name, spec.default as Params[string]);
  }

  // Resumen de la receta: las opciones visibles + el momento elegido.
  const resumen: { clave: string; valor: string }[] = [];
  for (const spec of product.params) {
    if (!visible(spec)) continue;
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
  const presetVentana = String(params.ventana_preset ?? "");
  if (ventana && /^\d+$/.test(presetVentana)) {
    resumen.push({ clave: "ventana", valor: `${presetVentana} cuadros` });
  } else if (ventana) {
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

  // Coherencia lógica entre hiperparámetros además del `enabled_when` básico:
  // - Si `snapshot` y `ultimo` están activos, la ventana de fechas, la fecha,
  //   la hora y el minuto se ignoran (usa el último slot publicado).
  // - Si `ultima` está activo, la fecha/hora/minuto tampoco aplican.
  // - Si `ultimos` está activo, ignora la ventana de fechas, horarios y `animar`
  //   (ya anima los últimos N cuadros).
  // - `fps` sólo tiene sentido cuando se va a generar animación (`animar` o `ultimos` sin `snapshot`).
  const estaHabilitado = (spec: ParamSpec): boolean => {
    const base = coincideParams(spec.enabled_when, params);
    if (!base) return false;

    const esSnapshot = params.snapshot === true;
    const esUltimo = params.ultimo === true;
    const esUltima = params.ultima === true;
    const esUltimos = params.ultimos === true && !esSnapshot;
    const esAnimar = params.animar === true;

    if (
      (spec.name === "ventana" ||
        spec.name === "fecha" ||
        spec.name === "hora" ||
        spec.name === "minuto") &&
      ((esSnapshot && esUltimo) || esUltima || esUltimos)
    ) {
      return false;
    }

    if (
      (spec.name === "hora_desde" || spec.name === "hora_hasta") &&
      (esSnapshot || esUltimos)
    ) {
      return false;
    }

    if (spec.name === "fps" && !esAnimar && !esUltimos) {
      return false;
    }

    return true;
  };

  const campo = (spec: ParamSpec) => {
    const valor = params[spec.name];
    const id = `campo-${spec.name}`;
    const ayudaLimpia = limpiarAyuda(spec.help);
    const ayudaId = ayudaLimpia ? `ayuda-${spec.name}` : undefined;
    const habilitado = estaHabilitado(spec);
    const modificado = !igual(valor, spec.default);
    const padre = SUBORDINADOS[spec.name];
    const claseBase = habilitado ? "field" : "field field--off";
    const clase = [
      claseBase,
      modificado ? "field--modified" : "",
      padre ? "field--sub" : "",
    ]
      .filter(Boolean)
      .join(" ");

    // El punto marca "cambiaste el valor": siempre ocupa su lugar para que la
    // etiqueta no salte, y solo se pinta cuando el valor difiere del default.
    const marca = (
      <span
        className={modificado ? "field__dot" : "field__dot field__dot--off"}
        aria-hidden="true"
      />
    );

    const top = (etiqueta: string, htmlFor?: string, tooltip?: string) => {
      const textoAyuda = tooltip ?? spec.tooltip;
      return (
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
          {textoAyuda ? (
            <span
              className="field__hint"
              tabIndex={0}
              role="note"
              aria-label={textoAyuda}
            >
              ?
              <span className="field__tooltip" aria-hidden="true">
                {textoAyuda}
              </span>
            </span>
          ) : null}
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
    };

    if (spec.kind === "select") {
      // Una opcion puede depender de otro control: la paleta oficial de la
      // banda 16 solo se ofrece cuando esa banda esta elegida.
      const opciones = opcionesVisibles(spec, params);
      const elegida = opciones.find(
        (opcion) => opcion.value === String(valor ?? spec.default),
      );
      // El "?" muestra los horarios de la capa y que resalta la composicion.
      const tooltip = [spec.tooltip, elegida?.description]
        .filter(Boolean)
        .join("\n\n");
      return (
        <div className={clase} key={spec.name}>
          {top(spec.label, id, tooltip)}
          <Select
            id={id}
            value={String(valor ?? spec.default)}
            options={opciones}
            disabled={!habilitado}
            describedBy={ayudaId}
            onChange={(elegido) => onChange(spec.name, elegido)}
          />
          {ayudaLimpia ? (
            <span className="field__help" id={ayudaId}>
              {ayudaLimpia}
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
          {ayudaLimpia ? (
            <span className="field__help" id={ayudaId}>
              {ayudaLimpia}
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
            piso={pisoFecha}
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
            piso={pisoFecha}
            disabled={!habilitado}
            onChange={(siguiente) => onChange(spec.name, siguiente)}
          />
          <span className="field__help">{ayudaFecha}</span>
        </div>
      );
    }

    if (spec.kind === "toggle") {
      const activo = Boolean(valor);
      const claseToggle = [
        "field",
        "field--toggle",
        !habilitado ? "field--off" : "",
        activo ? "field--active" : "",
        modificado ? "field--modified" : "",
        padre ? "field--sub" : "",
      ]
        .filter(Boolean)
        .join(" ");
      return (
        <div className={claseToggle} key={spec.name}>
          <div className="field__top">
            <div className="field__title-row">
              <span className="field__label">
                {marca}
                {spec.label}
              </span>
              {modificado ? (
                <button
                  type="button"
                  className="field__reset"
                  onClick={() => onChange(spec.name, spec.default as Params[string])}
                >
                  restablecer
                </button>
              ) : null}
            </div>
            {ayudaLimpia ? <span className="field__help">{ayudaLimpia}</span> : null}
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={activo}
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
        {ayudaLimpia ? (
          <span className="field__help" id={ayudaId}>
            {ayudaLimpia}
          </span>
        ) : null}
      </div>
    );
  };

  return (
    <form
      className="sheet"
      data-group={product.group}
      aria-labelledby="work-product-title"
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
        <div className="work__head-main">
          <div className="work__eyebrow">
            <span className="dataset-badge" data-group={product.group}>
              <span className="dataset-badge__dot" aria-hidden="true" />
              {familia.etiqueta}
            </span>
            <span className="dataset-sensor">{familia.sensor}</span>
          </div>
          <h2 className="work__title" id="work-product-title">
            {product.name}
          </h2>
          <p className="work__summary">{product.summary}</p>
        </div>
        <div className="work__head-actions">
          {product.id === "follaje" && (
            <div className="earthdata-login">
              {earthdataConfigurado ? (
                <span className="earthdata-ok" title="Cookies de Earthdata configuradas">
                  ✓ Earthdata conectado
                </span>
              ) : (
                <button
                  type="button"
                  className="btn btn--secondary"
                  disabled={earthdataLogueando || busy}
                  onClick={loginEarthdata}
                >
                  {earthdataLogueando ? "Abriendo navegador…" : "Login Earthdata"}
                </button>
              )}
              {earthdataError && (
                <span className="earthdata-error" role="alert">
                  {earthdataError}
                </span>
              )}
            </div>
          )}
          <button
            type="button"
            className="btn btn--ghost"
            disabled={!hayCambios || busy}
            onClick={restablecerTodo}
          >
            Restablecer
          </button>
        </div>
      </div>

      {muestra ? (
        <figure className="plate">
          <div className="plate__frame">
            <img src={muestra} alt={`Resultado de ${product.name}`} />
          </div>
          <figcaption className="plate__cap">
            <span>Vista previa de referencia</span>
            <span>{detalleMuestra || product.name}</span>
          </figcaption>
        </figure>
      ) : (
        <figure className="plate plate--empty">
          <p className="plate__none">sin muestra de referencia</p>
        </figure>
      )}

      <div className="sheet__body">
        <div className="fields">
          {grupos.map((grupo) => (
            <section
              key={grupo.id}
              id={`sec-${grupo.id}`}
              className="fields__grupo"
            >
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
            El motor de procesamiento no está disponible: solo se muestra la vista previa.
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
