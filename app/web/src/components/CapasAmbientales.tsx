import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import type { Feature } from "geojson";

import { getCapa, getCapas } from "../capas";
import type { CapaGeoJSON, CapaInfo, CapaPropiedades } from "../capas";
import { cajaDeMapa } from "../mapa";

const STORAGE = "climate3d:nisar:capas";
const PANE = "capasAmbientales";
const OPACIDAD_MIN = 0.12;
const OPACIDAD_MAX = 0.8;

const NUMERO = new Intl.NumberFormat("es-PY");

interface CapaGuardada {
  activas?: string[];
  opacidad?: number;
}

/** Estado de carga de una capa, para el renglón de la lista. */
interface EstadoCapa {
  cargando: boolean;
  total: number;
  excedido: boolean;
  avisos: string[];
  requiereZoom: boolean;
  error: string | null;
}

const ESTADO_VACIO: EstadoCapa = {
  cargando: false,
  total: 0,
  excedido: false,
  avisos: [],
  requiereZoom: false,
  error: null,
};

function leerGuardado(): CapaGuardada {
  try {
    const crudo = window.localStorage.getItem(STORAGE);
    if (!crudo) return {};
    const parsed = JSON.parse(crudo) as CapaGuardada;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function acotar(valor: number, minimo: number, maximo: number): number {
  return Math.min(maximo, Math.max(minimo, valor));
}

function areaLegible(hectareas: number): string {
  if (hectareas >= 1_000_000) {
    return `${NUMERO.format(Math.round(hectareas / 100))} km²`;
  }
  return `${NUMERO.format(Math.round(hectareas))} ha`;
}

function estiloCapa(
  capa: CapaInfo,
  props: CapaPropiedades,
  opacidad: number,
): L.PathOptions {
  if (capa.id === "ecorregiones") {
    const color = props.color ?? capa.color;
    return {
      color,
      weight: 0.8,
      opacity: 0.7,
      fillColor: color,
      fillOpacity: acotar(opacidad * 0.6, 0.04, 0.4),
    };
  }
  if (capa.id === "territorios-indigenas") {
    return {
      color: capa.color,
      weight: 1.3,
      opacity: 0.92,
      dashArray: "6 3",
      fillColor: capa.color,
      fillOpacity: acotar(opacidad * 0.65, 0.05, 0.6),
    };
  }
  if (capa.id === "ramsar") {
    return {
      color: capa.color,
      weight: 1.3,
      opacity: 0.95,
      dashArray: "3 2",
      fillColor: capa.color,
      fillOpacity: opacidad,
    };
  }
  if (capa.id === "biosfera") {
    return {
      color: capa.color,
      weight: 1.6,
      opacity: 0.95,
      dashArray: "9 3",
      fillColor: capa.color,
      fillOpacity: opacidad,
    };
  }
  if (capa.id === "otras-conservacion") {
    return {
      color: capa.color,
      weight: 1.1,
      opacity: 0.9,
      dashArray: "2 2",
      fillColor: capa.color,
      fillOpacity: opacidad,
    };
  }
  return {
    color: capa.color,
    weight: 1.1,
    opacity: 0.9,
    fillColor: capa.color,
    fillOpacity: opacidad,
  };
}

/** Tooltip con `textContent`: los nombres vienen de servicios externos. */
function nodoTooltip(props: CapaPropiedades): HTMLElement {
  const nodo = document.createElement("div");
  nodo.className = "capas-tip";
  const nombre = document.createElement("strong");
  nombre.className = "capas-tip__nombre";
  nombre.textContent = props.nombre ?? "Sin nombre";
  nodo.appendChild(nombre);
  const detalle = [props.categoria, props.situacion].filter(Boolean).join(" · ");
  if (detalle) {
    const linea = document.createElement("span");
    linea.className = "capas-tip__meta";
    linea.textContent = detalle;
    nodo.appendChild(linea);
  }
  return nodo;
}

function nodoPopup(capa: CapaInfo, props: CapaPropiedades): HTMLElement {
  const nodo = document.createElement("div");
  nodo.className = "capas-pop";

  const titulo = document.createElement("p");
  titulo.className = "capas-pop__titulo";
  titulo.textContent = props.nombre ?? "Sin nombre";
  nodo.appendChild(titulo);

  const candidatas: Array<[string, string]> = [
    ["Categoría", props.categoria ?? ""],
    ["Designación", props.designacion ?? ""],
    ["Situación", props.situacion ?? ""],
    ["Origen", props.origen ?? ""],
    ["Año", props.anio ? String(props.anio) : ""],
    ["Superficie", props.area_ha ? areaLegible(props.area_ha) : ""],
    ["País", props.pais ?? props.iso ?? ""],
    ["UICN", props.iucn && props.iucn !== "Not Applicable" ? props.iucn : ""],
    ["Nota", props.nota ?? ""],
  ];
  const filas = candidatas.filter(([, valor]) => valor && valor !== "Not Reported");

  if (filas.length) {
    const lista = document.createElement("dl");
    lista.className = "capas-pop__datos";
    for (const [etiqueta, valor] of filas) {
      const dt = document.createElement("dt");
      dt.textContent = etiqueta;
      const dd = document.createElement("dd");
      dd.textContent = valor;
      lista.append(dt, dd);
    }
    nodo.appendChild(lista);
  }

  const fuente = document.createElement("p");
  fuente.className = "capas-pop__fuente";
  fuente.textContent = capa.fuente;
  nodo.appendChild(fuente);

  if (capa.fuente_url) {
    const enlace = document.createElement("a");
    enlace.className = "capas-pop__enlace";
    enlace.href = capa.fuente_url;
    enlace.target = "_blank";
    enlace.rel = "noreferrer noopener";
    enlace.textContent = "Ver en la fuente";
    nodo.appendChild(enlace);
  }
  return nodo;
}

function crearGrupo(
  datos: CapaGeoJSON,
  capa: CapaInfo,
  opacidad: number,
): L.GeoJSON | null {
  if (!datos.features.length) return null;
  return L.geoJSON(datos, {
    pane: PANE,
    style: (elemento) =>
      estiloCapa(
        capa,
        ((elemento as Feature | undefined)?.properties ?? {}) as CapaPropiedades,
        opacidad,
      ),
    onEachFeature: (elemento, capaLeaflet) => {
      if (!(capaLeaflet instanceof L.Path)) return;
      const props = (elemento.properties ?? {}) as CapaPropiedades;
      capaLeaflet.bindTooltip(nodoTooltip(props), {
        sticky: true,
        direction: "top",
        className: "capas-tooltip",
        opacity: 1,
      });
      capaLeaflet.bindPopup(nodoPopup(capa, props), {
        className: "capas-popup",
        maxWidth: 330,
        minWidth: 250,
      });
    },
  });
}

export function CapasAmbientales({ mapa }: { mapa: L.Map | null }) {
  const raizRef = useRef<HTMLDivElement | null>(null);
  const grupos = useRef(new Map<string, L.GeoJSON>());
  const abortos = useRef(new Map<string, AbortController>());
  const turnos = useRef(new Map<string, number>());
  const ultimaCaja = useRef(new Map<string, string>());
  const mapaRef = useRef<L.Map | null>(mapa);
  mapaRef.current = mapa;

  const inicialRef = useRef<CapaGuardada | null>(null);
  if (inicialRef.current === null) inicialRef.current = leerGuardado();
  const inicial = inicialRef.current;

  const [catalogo, setCatalogo] = useState<CapaInfo[] | null>(null);
  const [errorCatalogo, setErrorCatalogo] = useState<string | null>(null);
  const [intento, setIntento] = useState(0);
  const [activas, setActivas] = useState<string[]>(() =>
    Array.isArray(inicial.activas) ? inicial.activas : [],
  );
  const [opacidad, setOpacidad] = useState(() =>
    acotar(
      typeof inicial.opacidad === "number" ? inicial.opacidad : 0.35,
      OPACIDAD_MIN,
      OPACIDAD_MAX,
    ),
  );
  const [abierto, setAbierto] = useState(false);
  const [estados, setEstados] = useState<Record<string, EstadoCapa>>({});

  const activasRef = useRef(activas);
  activasRef.current = activas;
  const opacidadRef = useRef(opacidad);
  opacidadRef.current = opacidad;
  const catalogoRef = useRef<CapaInfo[] | null>(catalogo);
  catalogoRef.current = catalogo;

  const porId = useMemo(() => {
    const mapaCapas = new Map<string, CapaInfo>();
    for (const capa of catalogo ?? []) mapaCapas.set(capa.id, capa);
    return mapaCapas;
  }, [catalogo]);

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE, JSON.stringify({ activas, opacidad }));
    } catch {
      // localStorage puede estar bloqueado: la capa sigue funcionando.
    }
  }, [activas, opacidad]);

  useEffect(() => {
    let vivo = true;
    setErrorCatalogo(null);
    getCapas()
      .then((datos) => {
        if (!vivo) return;
        setCatalogo(datos.capas);
      })
      .catch((exc: unknown) => {
        if (!vivo) return;
        setErrorCatalogo(
          exc instanceof Error ? exc.message : "No se pudo leer el catálogo.",
        );
      });
    return () => {
      vivo = false;
    };
  }, [intento]);

  const quitar = useCallback((id: string) => {
    const grupo = grupos.current.get(id);
    if (grupo) {
      grupo.remove();
      grupos.current.delete(id);
    }
  }, []);

  const cargar = useCallback(
    async (capa: CapaInfo) => {
      const mapaActual = mapaRef.current;
      if (!mapaActual) return;
      if (!activasRef.current.includes(capa.id)) return;
      const zoom = Math.round(mapaActual.getZoom());
      const turno = (turnos.current.get(capa.id) ?? 0) + 1;
      turnos.current.set(capa.id, turno);
      abortos.current.get(capa.id)?.abort();

      if (zoom < capa.min_zoom) {
        quitar(capa.id);
        ultimaCaja.current.delete(capa.id);
        setEstados((previo) => ({
          ...previo,
          [capa.id]: { ...ESTADO_VACIO, requiereZoom: true },
        }));
        return;
      }

      const caja = cajaDeMapa(mapaActual);
      if (!caja) {
        quitar(capa.id);
        ultimaCaja.current.delete(capa.id);
        setEstados((previo) => ({
          ...previo,
          [capa.id]: { ...ESTADO_VACIO, error: "La vista cruzó el antimeridiano." },
        }));
        return;
      }

      const clave = `${zoom}|${caja}`;
      if (ultimaCaja.current.get(capa.id) === clave) return;
      ultimaCaja.current.set(capa.id, clave);

      const control = new AbortController();
      abortos.current.set(capa.id, control);
      setEstados((previo) => ({
        ...previo,
        [capa.id]: { ...ESTADO_VACIO, cargando: true },
      }));

      try {
        const datos = await getCapa(capa.id, caja, zoom, control.signal);
        if (
          control.signal.aborted ||
          turnos.current.get(capa.id) !== turno ||
          !activasRef.current.includes(capa.id)
        ) {
          return;
        }
        quitar(capa.id);
        const grupo = crearGrupo(datos, capa, opacidadRef.current);
        if (grupo) {
          grupo.addTo(mapaActual);
          grupos.current.set(capa.id, grupo);
        }
        setEstados((previo) => ({
          ...previo,
          [capa.id]: {
            cargando: false,
            total: datos.total,
            excedido: datos.excedido,
            avisos: datos.avisos,
            requiereZoom: datos.requiere_zoom,
            error: null,
          },
        }));
      } catch (exc: unknown) {
        if (turnos.current.get(capa.id) !== turno) return;
        ultimaCaja.current.delete(capa.id);
        quitar(capa.id);
        setEstados((previo) => ({
          ...previo,
          [capa.id]: {
            ...ESTADO_VACIO,
            error: control.signal.aborted
              ? null
              : exc instanceof Error
                ? exc.message
                : "No se pudo cargar la capa.",
          },
        }));
      }
    },
    [quitar],
  );

  const refrescar = useCallback(() => {
    const mapaActual = mapaRef.current;
    if (!mapaActual) return;
    for (const id of activasRef.current) {
      const capa = catalogoRef.current?.find((item) => item.id === id);
      if (capa) void cargar(capa);
    }
  }, [cargar]);

  // Pane propio por debajo de las huellas NISAR (overlayPane = 400).
  useEffect(() => {
    if (!mapa) return;
    if (!mapa.getPane(PANE)) {
      const pane = mapa.createPane(PANE);
      pane.style.zIndex = "380";
    }
    let temporizador: number | null = null;
    const alMoverVista = () => {
      if (temporizador !== null) window.clearTimeout(temporizador);
      temporizador = window.setTimeout(() => {
        temporizador = null;
        refrescar();
      }, 320);
    };
    mapa.on("moveend", alMoverVista);
    mapa.on("zoomend", alMoverVista);
    return () => {
      mapa.off("moveend", alMoverVista);
      mapa.off("zoomend", alMoverVista);
      if (temporizador !== null) window.clearTimeout(temporizador);
      abortos.current.forEach((control) => control.abort());
      abortos.current.clear();
      grupos.current.forEach((grupo) => grupo.remove());
      grupos.current.clear();
      ultimaCaja.current.clear();
    };
  }, [mapa, refrescar]);

  // Alta y baja de capas según los toggles, sin repetir la consulta de una capa ya dibujada.
  useEffect(() => {
    if (!mapa || !catalogo) return;
    const vigentes = new Set(activas);
    abortos.current.forEach((control, id) => {
      if (!vigentes.has(id)) control.abort();
    });
    grupos.current.forEach((_, id) => {
      if (!vigentes.has(id)) quitar(id);
    });
    ultimaCaja.current.forEach((_, id) => {
      if (!vigentes.has(id)) ultimaCaja.current.delete(id);
    });
    setEstados((previo) => {
      const siguiente: Record<string, EstadoCapa> = {};
      for (const [id, estado] of Object.entries(previo)) {
        if (vigentes.has(id)) siguiente[id] = estado;
      }
      return siguiente;
    });
    for (const id of activas) {
      if (grupos.current.has(id)) continue;
      const capa = catalogo.find((item) => item.id === id);
      if (capa) void cargar(capa);
    }
  }, [activas, catalogo, mapa, cargar, quitar]);

  // La opacidad se aplica sobre lo ya dibujado, sin volver a consultar.
  useEffect(() => {
    for (const [id, grupo] of grupos.current) {
      const capa = porId.get(id);
      if (!capa) continue;
      grupo.setStyle((elemento) =>
        estiloCapa(
          capa,
          ((elemento as Feature | undefined)?.properties ?? {}) as CapaPropiedades,
          opacidad,
        ),
      );
    }
  }, [opacidad, porId]);

  // Atribución de las fuentes activas en el control de Leaflet.
  useEffect(() => {
    if (!mapa?.attributionControl) return;
    const textos = new Set<string>();
    for (const id of activas) {
      const capa = porId.get(id);
      if (capa) textos.add(capa.atribucion);
    }
    textos.forEach((texto) => mapa.attributionControl.addAttribution(texto));
    return () => {
      textos.forEach((texto) => mapa.attributionControl.removeAttribution(texto));
    };
  }, [mapa, activas, porId]);

  useEffect(() => {
    if (!abierto) return;
    const alBajar = (evento: PointerEvent) => {
      const raiz = raizRef.current;
      if (raiz && evento.target instanceof Node && !raiz.contains(evento.target)) {
        setAbierto(false);
      }
    };
    document.addEventListener("pointerdown", alBajar);
    return () => document.removeEventListener("pointerdown", alBajar);
  }, [abierto]);

  useEffect(() => {
    if (!abierto) return;
    const alTeclear = (evento: KeyboardEvent) => {
      if (evento.key === "Escape") setAbierto(false);
    };
    window.addEventListener("keydown", alTeclear);
    return () => window.removeEventListener("keydown", alTeclear);
  }, [abierto]);

  const alternar = (id: string) => {
    setActivas((previo) =>
      previo.includes(id) ? previo.filter((item) => item !== id) : [...previo, id],
    );
  };

  const fuentes = useMemo(() => {
    const vistas = new Map<string, string>();
    for (const capa of catalogo ?? []) {
      if (!vistas.has(capa.fuente_url)) {
        try {
          vistas.set(capa.fuente_url, new URL(capa.fuente_url).hostname.replace(/^www\./, ""));
        } catch {
          vistas.set(capa.fuente_url, capa.fuente);
        }
      }
    }
    return [...vistas.entries()];
  }, [catalogo]);

  return (
    <div className="capas-amb__wrap" ref={raizRef}>
      <button
        type="button"
        className={`nisar__capa-btn capas-amb__trigger${abierto ? " nisar__capa-btn--on" : ""}`}
        aria-expanded={abierto}
        aria-haspopup="dialog"
        title="Áreas protegidas, Ramsar, biosfera, territorios indígenas y ecorregiones"
        onClick={() => setAbierto((previo) => !previo)}
      >
        Ambientales
        {activas.length ? (
          <span className="capas-amb__badge" aria-hidden="true">
            {activas.length}
          </span>
        ) : null}
        <span className="sr-only">
          {activas.length
            ? `${activas.length} capas ambientales activas`
            : "sin capas ambientales activas"}
        </span>
      </button>

      {abierto ? (
        <div className="capas-amb" role="dialog" aria-label="Capas ambientales">
          <header className="capas-amb__head">
            <div>
              <span className="capas-amb__eyebrow">Mapa</span>
              <h3 className="capas-amb__titulo">Capas ambientales</h3>
            </div>
            <button
              type="button"
              className="capas-amb__cerrar"
              aria-label="Cerrar capas ambientales"
              onClick={() => setAbierto(false)}
            >
              ×
            </button>
          </header>

          <p className="capas-amb__intro">
            Datos globales de conservación. Se consultan para el área visible al mover
            el mapa y se cachean en el servidor.
          </p>

          {errorCatalogo ? (
            <div className="capas-amb__fallo">
              <p>{errorCatalogo}</p>
              <button
                type="button"
                className="nisar__box-btn"
                onClick={() => setIntento((previo) => previo + 1)}
              >
                Reintentar
              </button>
            </div>
          ) : null}

          {!catalogo && !errorCatalogo ? (
            <p className="capas-amb__vacio">Cargando capas…</p>
          ) : null}

          {catalogo ? (
            <ul className="capas-amb__lista">
              {catalogo.map((capa) => {
                const activa = activas.includes(capa.id);
                const estado = estados[capa.id];
                return (
                  <li
                    key={capa.id}
                    className={`capas-amb__item${activa ? " capas-amb__item--on" : ""}`}
                  >
                    <label className="capas-amb__label">
                      <input
                        type="checkbox"
                        checked={activa}
                        onChange={() => alternar(capa.id)}
                      />
                      <span
                        className="capas-amb__swatch"
                        style={{ background: capa.color }}
                        aria-hidden="true"
                      />
                      <span className="capas-amb__texto">
                        <span className="capas-amb__nombre">{capa.nombre}</span>
                        <span className="capas-amb__desc">{capa.descripcion}</span>
                        <span className="capas-amb__fuente">{capa.fuente}</span>
                        {activa ? (
                          <span className="capas-amb__estado" aria-live="polite">
                            {estado?.cargando ? (
                              "Consultando…"
                            ) : estado?.error ? (
                              <span className="capas-amb__error" title={estado.error}>
                                {estado.error}
                              </span>
                            ) : estado?.requiereZoom ? (
                              `Acercate a zoom ${capa.min_zoom}`
                            ) : estado && estado.total > 0 ? (
                              <>
                                {NUMERO.format(estado.total)}{" "}
                                {estado.total === 1 ? "sitio" : "sitios"}
                                {estado.excedido ? " · recortado" : ""}
                                {estado.avisos.length ? (
                                  <span
                                    className="capas-amb__aviso"
                                    title={estado.avisos.join(" ")}
                                  >
                                    {" "}
                                    · parcial
                                  </span>
                                ) : null}
                              </>
                            ) : (
                              "Sin sitios en esta vista"
                            )}
                          </span>
                        ) : null}
                      </span>
                    </label>
                  </li>
                );
              })}
            </ul>
          ) : null}

          <div className="capas-amb__opacidad">
            <label htmlFor="capas-amb-opacidad">Opacidad</label>
            <input
              id="capas-amb-opacidad"
              type="range"
              min={OPACIDAD_MIN * 100}
              max={OPACIDAD_MAX * 100}
              step={5}
              value={Math.round(opacidad * 100)}
              onChange={(evento) =>
                setOpacidad(
                  acotar(Number(evento.target.value) / 100, OPACIDAD_MIN, OPACIDAD_MAX),
                )
              }
            />
            <span>{Math.round(opacidad * 100)}%</span>
          </div>

          {fuentes.length ? (
            <footer className="capas-amb__pie">
              <span className="capas-amb__eyebrow">Fuentes</span>
              <div className="capas-amb__links">
                {fuentes.map(([url, etiqueta]) => (
                  <a key={url} href={url} target="_blank" rel="noreferrer noopener">
                    {etiqueta}
                  </a>
                ))}
              </div>
            </footer>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
