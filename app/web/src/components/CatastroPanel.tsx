import { useCallback, useEffect, useRef, useState } from "react";
import L from "leaflet";
import type { Feature } from "geojson";

import {
  analizarAfectadas,
  getCatastro,
  getParcelas,
} from "../catastro";
import type {
  CatastroAfectadas,
  CatastroEstado,
  ParcelaProps,
} from "../catastro";
import { cajaDeMapa, contiene } from "../mapa";
import type { Caja } from "../nisar";

const STORAGE = "climate3d:nisar:catastro";
const PANE = "catastro";
const PANE_AFECTADAS = "catastroAfectadas";
const OPACIDAD_MIN = 0.05;
const OPACIDAD_MAX = 0.7;
const COLOR = "#f8fafc";

/** Cuánto se agranda la vista al pedirla (fracción por lado).
 *
 * Un paneo menor a este margen ya está dibujado: no hay que consultar de nuevo.
 */
const MARGEN_VISTA = 0.25;

/** Espera tras el último movimiento antes de consultar. Corta, porque cada
 * movimiento nuevo aborta el pedido anterior de todos modos. */
const ESPERA_MOVIMIENTO = 180;

const NUMERO = new Intl.NumberFormat("es-PY");

interface Guardado {
  activo?: boolean;
  opacidad?: number;
}

interface Vista {
  cargando: boolean;
  total: number;
  excedido: boolean;
  requiereZoom: boolean;
  requiereIndice: boolean;
  indexando: boolean;
  progreso: number;
  areaMinHa: number;
  avisos: string[];
  error: string | null;
}

const VISTA_VACIA: Vista = {
  cargando: false,
  total: 0,
  excedido: false,
  requiereZoom: false,
  requiereIndice: false,
  indexando: false,
  progreso: 0,
  areaMinHa: 0,
  avisos: [],
  error: null,
};

function leerGuardado(): Guardado {
  try {
    const crudo = window.localStorage.getItem(STORAGE);
    if (!crudo) return {};
    const parsed = JSON.parse(crudo) as Guardado;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function acotar(valor: number, minimo: number, maximo: number): number {
  return Math.min(maximo, Math.max(minimo, valor));
}

function areaTexto(hectareas: number | null | undefined): string {
  if (hectareas === null || hectareas === undefined) return "";
  if (hectareas >= 1000) return `${NUMERO.format(Math.round(hectareas))} ha`;
  if (hectareas >= 1) return `${NUMERO.format(Number(hectareas.toFixed(1)))} ha`;
  return `${NUMERO.format(Math.round(hectareas * 10_000))} m²`;
}

function metrosTexto(valor: number | null | undefined): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) return "";
  return `${NUMERO.format(Math.round(valor))} m²`;
}

function estiloParcela(opacidad: number, zoom: number): L.PathOptions {
  // En vista de país manda el contorno: rellenar cientos de estancias tapa el mapa.
  const relleno = zoom <= 8 ? 0 : zoom <= 10 ? 0.16 : 0.42;
  return {
    color: COLOR,
    weight: zoom <= 8 ? 0.55 : 0.75,
    opacity: 0.9,
    fillColor: COLOR,
    fillOpacity: acotar(opacidad * relleno, 0, 0.42),
  };
}

/** Más rojo cuanto más superficie del predio cae dentro del cuadro. */
function estiloAfectada(elemento?: Feature): L.PathOptions {
  const props = (elemento?.properties ?? {}) as ParcelaProps;
  const fraccion = props.fraccion ?? 0;
  const color = fraccion >= 0.6 ? "#ef4444" : fraccion >= 0.25 ? "#fb923c" : "#facc15";
  return {
    color,
    weight: 1.7,
    opacity: 0.95,
    fillColor: color,
    fillOpacity: 0.36,
  };
}

/** Popup con `textContent`: los valores vienen del DBF del SNC. */
function nodoParcela(props: ParcelaProps, conCopia: boolean): HTMLElement {
  const nodo = document.createElement("div");
  nodo.className = "capas-pop catastro-pop";

  const titulo = document.createElement("p");
  titulo.className = "capas-pop__titulo";
  titulo.textContent = props.ccatastral || "Parcela sin código";
  nodo.appendChild(titulo);

  const filas: Array<[string, string]> = [
    ["Departamento", props.departamento ?? ""],
    ["Distrito", props.dist ?? ""],
    ["Padrón", props.padron && props.padron !== "0" ? props.padron : ""],
    [
      "Zona · Mz · Lote",
      [props.zona, props.mz, props.lote].filter((valor) => valor && valor !== "0").join(" · "),
    ],
    ["Finca", props.finca ?? ""],
    ["Matrícula", props.matricula ?? ""],
    ["Colonia", props.colonia ?? ""],
    ["Reg. propiedad", props.reg_prof ?? ""],
    ["Objeto", props.nombre_obj ?? ""],
    ["Tipo", props.tipo ?? ""],
    ["Sup. legal", metrosTexto(props.sup_legal)],
    ["Sup. medida", metrosTexto(props.sup_sig_m2)],
    ["Área", areaTexto(props.area_ha)],
    ["Afectado", areaTexto(props.afectado_ha)],
    [
      "Fracción afectada",
      props.fraccion !== null && props.fraccion !== undefined
        ? `${Math.round(props.fraccion * 100)} % del predio`
        : "",
    ],
  ];
  const visibles = filas.filter(([, valor]) => valor && valor !== "0");

  if (visibles.length) {
    const lista = document.createElement("dl");
    lista.className = "capas-pop__datos";
    for (const [etiqueta, valor] of visibles) {
      const dt = document.createElement("dt");
      dt.textContent = etiqueta;
      const dd = document.createElement("dd");
      dd.textContent = valor;
      lista.append(dt, dd);
    }
    nodo.appendChild(lista);
  }

  if (conCopia && props.ccatastral) {
    const boton = document.createElement("button");
    boton.type = "button";
    boton.className = "capas-pop__enlace catastro-pop__copiar";
    boton.textContent = "Copiar código";
    boton.addEventListener("click", () => {
      void navigator.clipboard?.writeText(props.ccatastral).then(() => {
        boton.textContent = "Copiado";
        window.setTimeout(() => {
          boton.textContent = "Copiar código";
        }, 1600);
      });
    });
    nodo.appendChild(boton);
  }

  const fuente = document.createElement("p");
  fuente.className = "capas-pop__fuente";
  fuente.textContent = "SNC · Servicio Nacional de Catastro";
  nodo.appendChild(fuente);
  return nodo;
}

export function CatastroPanel({
  mapa,
  caja,
}: {
  mapa: L.Map | null;
  caja: Caja | null;
}) {
  const raizRef = useRef<HTMLDivElement | null>(null);
  const grupoRef = useRef<L.GeoJSON | null>(null);
  const analisisRef = useRef<L.GeoJSON | null>(null);
  const capasAnalisis = useRef(new Map<string, L.Path>());
  const estilosBase = useRef(new Map<string, L.PathOptions>());
  const abortoDibujo = useRef<AbortController | null>(null);
  const abortoAnalisis = useRef<AbortController | null>(null);
  /** Última caja pedida (ya con margen) y el zoom al que se pidió. */
  const pedidoRef = useRef<{ zoom: number; caja: string } | null>(null);
  const zoomRef = useRef(8);
  const mapaRef = useRef<L.Map | null>(mapa);
  mapaRef.current = mapa;

  const inicialRef = useRef<Guardado | null>(null);
  if (inicialRef.current === null) inicialRef.current = leerGuardado();
  const inicial = inicialRef.current;

  const [abierto, setAbierto] = useState(false);
  const [activo, setActivo] = useState(Boolean(inicial.activo));
  const [opacidad, setOpacidad] = useState(() =>
    acotar(
      typeof inicial.opacidad === "number" ? inicial.opacidad : 0.35,
      OPACIDAD_MIN,
      OPACIDAD_MAX,
    ),
  );
  const [estado, setEstado] = useState<CatastroEstado | null>(null);
  const [errorEstado, setErrorEstado] = useState<string | null>(null);
  const [vista, setVista] = useState<Vista>(VISTA_VACIA);
  const [analisis, setAnalisis] = useState<CatastroAfectadas | null>(null);
  const [analizando, setAnalizando] = useState(false);
  const [errorAnalisis, setErrorAnalisis] = useState<string | null>(null);
  const [seleccion, setSeleccion] = useState<string | null>(null);

  const activoRef = useRef(activo);
  activoRef.current = activo;
  const opacidadRef = useRef(opacidad);
  opacidadRef.current = opacidad;
  const estadoRef = useRef<CatastroEstado | null>(estado);
  estadoRef.current = estado;
  const pidiendoRef = useRef(false);

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE, JSON.stringify({ activo, opacidad }));
    } catch {
      // localStorage puede estar bloqueado: la capa sigue funcionando.
    }
  }, [activo, opacidad]);

  const refrescarEstado = useCallback(async () => {
    if (pidiendoRef.current) return;
    pidiendoRef.current = true;
    try {
      const datos = await getCatastro();
      setEstado(datos);
      setErrorEstado(null);
    } catch (exc: unknown) {
      setErrorEstado(
        exc instanceof Error ? exc.message : "No se pudo leer el estado del catastro.",
      );
    } finally {
      pidiendoRef.current = false;
    }
  }, []);

  // El índice se pide recién cuando hace falta: abrir el panel o tener la capa activa.
  useEffect(() => {
    if ((abierto || activo) && !estado) void refrescarEstado();
  }, [abierto, activo, estado, refrescarEstado]);

  // Mientras se construye el índice (minutos la primera vez) se refresca el progreso.
  useEffect(() => {
    if (!estado?.indexando) return;
    const timer = window.setInterval(() => void refrescarEstado(), 2500);
    return () => window.clearInterval(timer);
  }, [estado?.indexando, refrescarEstado]);

  const quitarParcelas = useCallback(() => {
    grupoRef.current?.remove();
    grupoRef.current = null;
  }, []);

  const cargar = useCallback(async () => {
    const mapaActual = mapaRef.current;
    const datos = estadoRef.current;
    if (!mapaActual || !activoRef.current) return;
    const zoom = Math.round(mapaActual.getZoom());
    const zoomMin = datos?.zoom_min ?? 5;
    zoomRef.current = zoom;
    if (!datos?.disponible || zoom < zoomMin) {
      quitarParcelas();
      pedidoRef.current = null;
      setVista({
        ...VISTA_VACIA,
        requiereZoom: zoom < zoomMin,
        requiereIndice: !datos?.disponible,
        indexando: Boolean(datos?.indexando),
        progreso: datos?.progreso ?? 0,
        total: 0,
      });
      return;
    }
    const cajaTexto = cajaDeMapa(mapaActual);
    if (!cajaTexto) return;
    // Si la vista nueva sigue adentro de lo ya pedido y sin cambiar de zoom, lo que
    // está dibujado alcanza: pedir de nuevo solo repite la consulta.
    const pedido = pedidoRef.current;
    if (pedido && pedido.zoom === zoom && contiene(pedido.caja, cajaTexto)) return;
    const cajaPedido = cajaDeMapa(mapaActual, MARGEN_VISTA) ?? cajaTexto;
    pedidoRef.current = { zoom, caja: cajaPedido };

    abortoDibujo.current?.abort();
    const control = new AbortController();
    abortoDibujo.current = control;
    setVista((previo) => ({ ...previo, cargando: true, error: null }));
    try {
      const resultado = await getParcelas(cajaPedido, zoom, control.signal);
      if (control.signal.aborted || !activoRef.current) return;
      quitarParcelas();
      if (resultado.features.length) {
        const grupo = L.geoJSON(resultado, {
          pane: PANE,
          style: () => estiloParcela(opacidadRef.current, zoomRef.current),
          onEachFeature: (elemento, capa) => {
            if (!(capa instanceof L.Path)) return;
            const props = (elemento.properties ?? {}) as ParcelaProps;
            capa.bindTooltip(
              props.ccatastral
                ? `${props.ccatastral}${props.colonia ? ` · ${props.colonia}` : ""}`
                : "Parcela",
              { sticky: true, direction: "top", className: "capas-tooltip", opacity: 1 },
            );
            capa.bindPopup(nodoParcela(props, true), {
              className: "capas-popup",
              maxWidth: 340,
              minWidth: 260,
            });
          },
        });
        grupo.addTo(mapaActual);
        grupoRef.current = grupo;
      }
      setVista({
        cargando: false,
        total: resultado.total,
        excedido: resultado.excedido,
        requiereZoom: resultado.requiere_zoom,
        requiereIndice: resultado.requiere_indice,
        indexando: resultado.indexando,
        progreso: resultado.progreso,
        areaMinHa: resultado.area_min_ha ?? 0,
        avisos: resultado.avisos,
        error: null,
      });
    } catch (exc: unknown) {
      if (control.signal.aborted) return;
      pedidoRef.current = null;
      setVista({
        ...VISTA_VACIA,
        error: exc instanceof Error ? exc.message : "No se pudieron cargar las parcelas.",
      });
    }
  }, [quitarParcelas]);

  // Panes propios: parcelas debajo de las capas ambientales y de las huellas NISAR.
  useEffect(() => {
    if (!mapa) return;
    if (!mapa.getPane(PANE)) {
      mapa.createPane(PANE).style.zIndex = "360";
    }
    if (!mapa.getPane(PANE_AFECTADAS)) {
      mapa.createPane(PANE_AFECTADAS).style.zIndex = "370";
    }
    let temporizador: number | null = null;
    const alMover = () => {
      if (temporizador !== null) window.clearTimeout(temporizador);
      temporizador = window.setTimeout(() => {
        temporizador = null;
        void cargar();
      }, ESPERA_MOVIMIENTO);
    };
    mapa.on("moveend", alMover);
    mapa.on("zoomend", alMover);
    return () => {
      mapa.off("moveend", alMover);
      mapa.off("zoomend", alMover);
      if (temporizador !== null) window.clearTimeout(temporizador);
      abortoDibujo.current?.abort();
      quitarParcelas();
      pedidoRef.current = null;
    };
  }, [mapa, cargar, quitarParcelas]);

  // Alta/baja de la capa y primer dibujo cuando el índice queda listo.
  useEffect(() => {
    if (!mapa) return;
    if (!activo) {
      abortoDibujo.current?.abort();
      quitarParcelas();
      pedidoRef.current = null;
      setVista(VISTA_VACIA);
      return;
    }
    void cargar();
  }, [activo, estado?.disponible, mapa, cargar, quitarParcelas]);

  // La opacidad se aplica sobre lo ya dibujado, sin volver a consultar.
  useEffect(() => {
    grupoRef.current?.setStyle(() => estiloParcela(opacidad, zoomRef.current));
  }, [opacidad]);

  // El cuadro ROI cambia: el análisis anterior ya no corresponde.
  useEffect(() => {
    abortoAnalisis.current?.abort();
    setAnalizando(false);
    setAnalisis(null);
    setErrorAnalisis(null);
    setSeleccion(null);
  }, [caja]);

  useEffect(() => {
    const mapaActual = mapaRef.current;
    if (!mapaActual) return;
    analisisRef.current?.remove();
    analisisRef.current = null;
    capasAnalisis.current.clear();
    estilosBase.current.clear();
    setSeleccion(null);
    if (!analisis || !analisis.features.length) return;
    const grupo = L.geoJSON(analisis, {
      pane: PANE_AFECTADAS,
      style: (elemento) => estiloAfectada(elemento as Feature | undefined),
      onEachFeature: (elemento, capa) => {
        if (!(capa instanceof L.Path)) return;
        const props = (elemento.properties ?? {}) as ParcelaProps;
        if (props.ccatastral) capasAnalisis.current.set(props.ccatastral, capa);
        estilosBase.current.set(
          props.ccatastral,
          estiloAfectada(elemento as Feature | undefined),
        );
        capa.bindPopup(nodoParcela(props, true), {
          className: "capas-popup",
          maxWidth: 340,
          minWidth: 260,
        });
      },
    });
    grupo.addTo(mapaActual);
    analisisRef.current = grupo;
    return () => {
      grupo.remove();
      if (analisisRef.current === grupo) analisisRef.current = null;
      capasAnalisis.current.clear();
      estilosBase.current.clear();
    };
  }, [analisis, mapa]);

  // Atribución de las fuentes activas en el control de Leaflet.
  useEffect(() => {
    if (!mapa?.attributionControl) return;
    const textos = new Set<string>();
    if ((activo || analisis) && estado?.disponible) textos.add(estado.atribucion);
    if (analisis) textos.add(analisis.atribucion);
    textos.forEach((texto) => mapa.attributionControl.addAttribution(texto));
    return () => {
      textos.forEach((texto) => mapa.attributionControl.removeAttribution(texto));
    };
  }, [mapa, estado?.disponible, estado?.atribucion, analisis]);

  useEffect(() => {
    if (!abierto) return;
    const alBajar = (evento: PointerEvent) => {
      const raiz = raizRef.current;
      if (raiz && evento.target instanceof Node && !raiz.contains(evento.target)) {
        setAbierto(false);
      }
    };
    const alTeclear = (evento: KeyboardEvent) => {
      if (evento.key === "Escape") setAbierto(false);
    };
    document.addEventListener("pointerdown", alBajar);
    window.addEventListener("keydown", alTeclear);
    return () => {
      document.removeEventListener("pointerdown", alBajar);
      window.removeEventListener("keydown", alTeclear);
    };
  }, [abierto]);

  const analizar = useCallback(async () => {
    if (!caja) return;
    setAnalizando(true);
    setErrorAnalisis(null);
    abortoAnalisis.current?.abort();
    const control = new AbortController();
    abortoAnalisis.current = control;
    try {
      const datos = await analizarAfectadas(caja, control.signal);
      if (control.signal.aborted) return;
      setAnalisis(datos);
    } catch (exc: unknown) {
      if (control.signal.aborted) return;
      setErrorAnalisis(
        exc instanceof Error ? exc.message : "No se pudo cruzar el cuadro con el catastro.",
      );
    } finally {
      if (!control.signal.aborted) setAnalizando(false);
    }
  }, [caja]);

  const limpiarAnalisis = useCallback(() => {
    abortoAnalisis.current?.abort();
    setAnalizando(false);
    setAnalisis(null);
    setErrorAnalisis(null);
    setSeleccion(null);
  }, []);

  const enfocar = useCallback((ccatastral: string) => {
    const mapaActual = mapaRef.current;
    const capa = capasAnalisis.current.get(ccatastral);
    if (!mapaActual || !capa) return;
    setSeleccion(ccatastral);
    capasAnalisis.current.forEach((otra, clave) => {
      const base = estilosBase.current.get(clave) ?? {};
      otra.setStyle(
        clave === ccatastral
          ? { ...base, color: "#ffffff", weight: 3, opacity: 1, fillOpacity: 0.45 }
          : base,
      );
    });
    const capaActual = capa as L.Path & { getBounds?: () => L.LatLngBounds };
    if (capaActual.getBounds) {
      mapaActual.fitBounds(capaActual.getBounds(), { maxZoom: 17, padding: [24, 24] });
    }
    capa.openPopup();
  }, []);

  const indiceListo = estado?.disponible ?? false;
  const zoomMin = estado?.zoom_min ?? 14;
  const progreso = Math.round((estado?.indexando ? estado.progreso : vista.progreso) * 100);

  return (
    <div className="capas-amb__wrap" ref={raizRef}>
      <button
        type="button"
        className={`nisar__capa-btn capas-amb__trigger${activo ? " nisar__capa-btn--on" : ""}`}
        aria-expanded={abierto}
        aria-haspopup="dialog"
        title="Parcelas catastrales del SNC y análisis del cuadro ROI"
        onClick={() => setAbierto((previo) => !previo)}
      >
        Catastro
        {activo ? (
          <span className="capas-amb__badge" aria-hidden="true">
            on
          </span>
        ) : null}
        <span className="sr-only">
          {activo ? "capa de catastro activa" : "capa de catastro apagada"}
        </span>
      </button>

      {abierto ? (
        <div className="capas-amb catastro" role="dialog" aria-label="Catastro">
          <header className="capas-amb__head">
            <div>
              <span className="capas-amb__eyebrow">Mapa</span>
              <h3 className="capas-amb__titulo">Catastro · parcelas</h3>
            </div>
            <button
              type="button"
              className="capas-amb__cerrar"
              aria-label="Cerrar catastro"
              onClick={() => setAbierto(false)}
            >
              ×
            </button>
          </header>

          <p className="capas-amb__intro">
            Parcelas del Servicio Nacional de Catastro sobre el mapa. El dataset no
            publica nombre de propietario: el inmueble se identifica por código
            catastral, finca y matrícula.
          </p>

          {errorEstado ? (
            <div className="capas-amb__fallo">
              <p>{errorEstado}</p>
              <button
                type="button"
                className="nisar__box-btn"
                onClick={() => void refrescarEstado()}
              >
                Reintentar
              </button>
            </div>
          ) : null}

          {!estado && !errorEstado ? (
            <p className="capas-amb__vacio">Consultando el catastro…</p>
          ) : null}

          {estado && !estado.disponible && !estado.indexando ? (
            <div className="catastro__aviso">
              <p>{estado.mensaje}</p>
              <code className="catastro__ruta">{estado.ruta_configurada}</code>
              {estado.error ? <p className="capas-amb__error">{estado.error}</p> : null}
            </div>
          ) : null}

          {estado?.indexando ? (
            <div className="catastro__progreso">
              <div className="catastro__barra" role="progressbar" aria-valuenow={progreso}>
                <span style={{ width: `${Math.max(2, progreso)}%` }} />
              </div>
              <p>
                {estado.mensaje} · {progreso} %
              </p>
              <p className="catastro__nota">
                La primera vez se indexa el shapefile completo del SNC
                {estado.total_origen
                  ? ` (${NUMERO.format(estado.total_origen)} parcelas)`
                  : ""}
                . Tarda unos minutos y queda guardado.
              </p>
            </div>
          ) : null}

          {indiceListo ? (
            <>
              <div className="catastro__bloque">
                <label className="capas-amb__label catastro__toggle">
                  <input
                    type="checkbox"
                    checked={activo}
                    onChange={() => setActivo((previo) => !previo)}
                  />
                  <span className="capas-amb__texto">
                    <span className="capas-amb__nombre">Mostrar parcelas</span>
                    <span className="capas-amb__estado" aria-live="polite">
                      {vista.cargando ? (
                        "Consultando…"
                      ) : vista.error ? (
                        <span className="capas-amb__error">{vista.error}</span>
                      ) : vista.requiereZoom ? (
                        `Acercate a zoom ${zoomMin}`
                      ) : vista.total > 0 ? (
                        <>
                          {NUMERO.format(vista.total)}{" "}
                          {vista.total === 1 ? "parcela" : "parcelas"}
                          {vista.excedido ? " · recortado" : ""}
                        </>
                      ) : activo ? (
                        vista.areaMinHa >= 1
                          ? `Sin parcelas de ${NUMERO.format(
                              Number(vista.areaMinHa.toFixed(1)),
                            )} ha o más en esta vista`
                          : "Sin parcelas en esta vista"
                      ) : (
                        "Apagada"
                      )}
                    </span>
                  </span>
                </label>

                {activo && !vista.requiereZoom && vista.areaMinHa >= 1 ? (
                  <p className="catastro__nota">
                    A este zoom se muestran las parcelas de{" "}
                    {NUMERO.format(Number(vista.areaMinHa.toFixed(1)))} ha o más.
                  </p>
                ) : null}

                <div className="capas-amb__opacidad">
                  <label htmlFor="catastro-opacidad">Opacidad</label>
                  <input
                    id="catastro-opacidad"
                    type="range"
                    min={OPACIDAD_MIN * 100}
                    max={OPACIDAD_MAX * 100}
                    step={5}
                    value={Math.round(opacidad * 100)}
                    onChange={(evento) =>
                      setOpacidad(
                        acotar(
                          Number(evento.target.value) / 100,
                          OPACIDAD_MIN,
                          OPACIDAD_MAX,
                        ),
                      )
                    }
                  />
                  <span>{Math.round(opacidad * 100)}%</span>
                </div>
              </div>

              <div className="catastro__bloque catastro__analisis">
                <span className="capas-amb__eyebrow">Inmuebles afectados</span>
                {caja ? (
                  <p className="catastro__nota">
                    Cruza el cuadro ROI dibujado con las parcelas y mide cuánta
                    superficie de cada inmueble cae adentro.
                  </p>
                ) : (
                  <p className="catastro__nota">
                    Dibujá un cuadro en el mapa (Trazar cuadro) para saber a qué
                    inmuebles pertenece la zona analizada con NISAR.
                  </p>
                )}
                <div className="catastro__acciones">
                  <button
                    type="button"
                    className="nisar__box-btn"
                    disabled={!caja || analizando || !indiceListo}
                    onClick={() => void analizar()}
                  >
                    {analizando ? "Cruzando…" : "Analizar cuadro ROI"}
                  </button>
                  {analisis ? (
                    <button
                      type="button"
                      className="nisar__box-btn"
                      onClick={limpiarAnalisis}
                    >
                      Limpiar
                    </button>
                  ) : null}
                </div>

                {errorAnalisis ? (
                  <p className="capas-amb__error">{errorAnalisis}</p>
                ) : null}

                {analisis ? (
                  <>
                    <p className="catastro__resumen">
                      <strong>{NUMERO.format(analisis.total)}</strong>{" "}
                      {analisis.total === 1 ? "parcela" : "parcelas"} dentro del cuadro ·{" "}
                      <strong>{areaTexto(analisis.cubierto_ha)}</strong> catastradas de{" "}
                      {areaTexto(analisis.area_ha)} ({analisis.cubierto_pct} %)
                    </p>
                    {analisis.excedido ? (
                      <p className="catastro__nota">{analisis.avisos.join(" ")}</p>
                    ) : null}
                    <ul className="catastro__lista">
                      {analisis.features.map((feature, indice) => {
                        const props = feature.properties;
                        const clave = props.ccatastral || `parcela-${indice}`;
                        return (
                          <li key={clave}>
                            <button
                              type="button"
                              className={`catastro__item${
                                seleccion === props.ccatastral
                                  ? " catastro__item--sel"
                                  : ""
                              }`}
                              onClick={() => enfocar(props.ccatastral)}
                            >
                              <span className="catastro__item-id">
                                {props.ccatastral || "Sin código"}
                              </span>
                              <span className="catastro__item-meta">
                                {[
                                  props.colonia,
                                  props.finca ? `finca ${props.finca}` : "",
                                  props.matricula,
                                ]
                                  .filter(Boolean)
                                  .join(" · ") || "Sin datos registrales"}
                              </span>
                              <span className="catastro__item-area">
                                {areaTexto(props.afectado_ha)}
                                {props.fraccion !== null && props.fraccion !== undefined
                                  ? ` · ${Math.round(props.fraccion * 100)} %`
                                  : ""}
                              </span>
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  </>
                ) : null}
              </div>
            </>
          ) : null}

          {estado?.disponible ? (
            <footer className="capas-amb__pie catastro__pie">
              <span className="capas-amb__eyebrow">Fuente</span>
              <div className="capas-amb__links">
                <span>
                  {NUMERO.format(estado.parcelas)} parcelas
                  {estado.invalidas
                    ? ` · ${NUMERO.format(estado.invalidas)} sin geometría válida`
                    : ""}
                  {estado.reparadas
                    ? ` · ${NUMERO.format(estado.reparadas)} reparadas`
                    : ""}
                </span>
                <a href="https://www.snc.gov.py/" target="_blank" rel="noreferrer noopener">
                  snc.gov.py
                </a>
              </div>
            </footer>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
