import { useCallback, useEffect, useRef, useState } from "react";
import L from "leaflet";
import type { FeatureCollection } from "geojson";

import { cancelJob, createJob, subscribeJob } from "../api";
import { getNisarCatalog, getParaguay, searchNisar } from "../nisar";
import type { Caja, NisarCatalog, NisarGranule, NisarSearch } from "../nisar";
import type { Job } from "../types";

const CENTRO_PARAGUAY: L.LatLngTuple = [-23.4, -58.4];
const COLOR = "#5e6ad2";
const COLOR_SEL = "#828fff";

function hoyISO(diasAtras = 0): string {
  return new Date(Date.now() - diasAtras * 86_400_000).toISOString().slice(0, 10);
}

function cajaDeBounds(bounds: L.LatLngBounds): Caja | null {
  const so = bounds.getSouthWest();
  const ne = bounds.getNorthEast();
  if (ne.lat - so.lat < 0.01 || ne.lng - so.lng < 0.01) return null;
  return { oeste: so.lng, sur: so.lat, este: ne.lng, norte: ne.lat };
}

function bboxTexto(caja: Caja): string {
  return `${caja.oeste.toFixed(3)}, ${caja.sur.toFixed(3)}, ${caja.este.toFixed(3)}, ${caja.norte.toFixed(3)}`;
}

function fechaCorta(iso: string): string {
  if (!iso) return "-";
  return iso.replace("T", " ").replace("Z", " UTC");
}

function imagenInicial(granulo: NisarGranule | null): string | null {
  if (!granulo) return null;
  const mapa = granulo.images.find((imagen) => imagen.label.startsWith("Mapa"));
  return mapa?.url ?? granulo.images[0]?.url ?? granulo.thumbnail;
}

export function NisarView() {
  const contenedor = useRef<HTMLDivElement | null>(null);
  const mapaRef = useRef<L.Map | null>(null);
  const huellasRef = useRef<L.LayerGroup | null>(null);
  const cajaLayerRef = useRef<L.Rectangle | null>(null);

  const [catalogo, setCatalogo] = useState<NisarCatalog | null>(null);
  const [nivel, setNivel] = useState("GCOV");
  const [desde, setDesde] = useState(() => hoyISO(29));
  const [hasta, setHasta] = useState(() => hoyISO());
  const [caja, setCaja] = useState<Caja | null>(null);
  const [dibujando, setDibujando] = useState(false);
  const [resultado, setResultado] = useState<NisarSearch | null>(null);
  const [seleccion, setSeleccion] = useState<NisarGranule | null>(null);
  const [imagen, setImagen] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Render de la caja: descarga del .h5 + recorte de alta calidad.
  const [pol, setPol] = useState("auto");
  const [modo, setModo] = useState("gris");
  const [px, setPx] = useState("2400");
  const [trabajo, setTrabajo] = useState<Job | null>(null);

  const elegirGranulo = useCallback((granulo: NisarGranule) => {
    setSeleccion(granulo);
    setImagen(imagenInicial(granulo));
    const mapa = mapaRef.current;
    if (mapa && granulo.footprint.length >= 3) {
      const puntos = granulo.footprint.map(
        ([lon, lat]) => [lat, lon] as L.LatLngTuple,
      );
      mapa.fitBounds(L.latLngBounds(puntos), { padding: [24, 24], maxZoom: 11 });
    }
  }, []);

  const buscar = useCallback(
    async (objetivo: Caja) => {
      setCargando(true);
      setError(null);
      try {
        const datos = await searchNisar(objetivo, {
          start: desde,
          end: hasta,
          level: nivel,
        });
        setResultado(datos);
        const primero = datos.granules[0] ?? null;
        setSeleccion(primero);
        setImagen(imagenInicial(primero));
        const mapa = mapaRef.current;
        if (mapa) {
          mapa.fitBounds(
            [
              [objetivo.sur, objetivo.oeste],
              [objetivo.norte, objetivo.este],
            ],
            { padding: [24, 24] },
          );
        }
      } catch (exc) {
        setError(exc instanceof Error ? exc.message : "No se pudo buscar en ASF.");
      } finally {
        setCargando(false);
      }
    },
    [desde, hasta, nivel],
  );

  // Mapa: se crea una vez. StrictMode lo monta, desmonta y vuelve a montar.
  useEffect(() => {
    const nodo = contenedor.current;
    if (!nodo || mapaRef.current) return;

    const mapa = L.map(nodo, {
      center: CENTRO_PARAGUAY,
      zoom: 6,
      minZoom: 4,
      maxZoom: 12,
    });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(mapa);
    huellasRef.current = L.layerGroup().addTo(mapa);
    mapaRef.current = mapa;

    getParaguay()
      .then((datos: FeatureCollection) => {
        if (!mapaRef.current) return;
        L.geoJSON(datos, {
          style: {
            color: COLOR,
            weight: 1.4,
            opacity: 0.9,
            fillColor: COLOR,
            fillOpacity: 0.04,
          },
        }).addTo(mapaRef.current);
      })
      .catch(() => setError("No se pudo cargar el contorno de Paraguay."));

    return () => {
      mapa.remove();
      mapaRef.current = null;
      huellasRef.current = null;
      cajaLayerRef.current = null;
    };
  }, []);

  useEffect(() => {
    getNisarCatalog()
      .then(setCatalogo)
      .catch(() => setError("No se pudo leer el catalogo NISAR."));
  }, []);

  // Dibujo de la caja: mouse abajo, mover, soltar.
  useEffect(() => {
    const mapa = mapaRef.current;
    if (!mapa) return;
    if (!dibujando) {
      mapa.dragging.enable();
      mapa.getContainer().style.cursor = "";
      return;
    }

    mapa.dragging.disable();
    mapa.getContainer().style.cursor = "crosshair";
    let inicio: L.LatLng | null = null;

    const alMover = (evento: L.LeafletMouseEvent) => {
      if (!inicio || !cajaLayerRef.current) return;
      cajaLayerRef.current.setBounds(L.latLngBounds(inicio, evento.latlng));
    };

    const alBajar = (evento: L.LeafletMouseEvent) => {
      inicio = evento.latlng;
      if (cajaLayerRef.current) mapa.removeLayer(cajaLayerRef.current);
      cajaLayerRef.current = L.rectangle(L.latLngBounds(inicio, inicio), {
        color: COLOR_SEL,
        weight: 1.5,
        fillColor: COLOR_SEL,
        fillOpacity: 0.08,
        dashArray: "4 4",
      }).addTo(mapa);
      mapa.on("mousemove", alMover);
    };

    const alSoltar = (evento: L.LeafletMouseEvent) => {
      mapa.off("mousemove", alMover);
      if (!inicio) return;
      const bounds = L.latLngBounds(inicio, evento.latlng);
      inicio = null;
      setDibujando(false);
      const nueva = cajaDeBounds(bounds);
      if (nueva) {
        setCaja(nueva);
      } else if (cajaLayerRef.current) {
        mapa.removeLayer(cajaLayerRef.current);
        cajaLayerRef.current = null;
      }
    };

    mapa.on("mousedown", alBajar);
    mapa.on("mouseup", alSoltar);
    return () => {
      mapa.off("mousedown", alBajar);
      mapa.off("mouseup", alSoltar);
      mapa.off("mousemove", alMover);
    };
  }, [dibujando]);

  // La caja vigente se dibuja aunque no se este dibujando.
  useEffect(() => {
    const mapa = mapaRef.current;
    if (!mapa) return;
    if (!caja) {
      if (cajaLayerRef.current) {
        mapa.removeLayer(cajaLayerRef.current);
        cajaLayerRef.current = null;
      }
      return;
    }
    const bounds = L.latLngBounds(
      [caja.sur, caja.oeste],
      [caja.norte, caja.este],
    );
    if (cajaLayerRef.current) {
      cajaLayerRef.current.setBounds(bounds);
    } else {
      cajaLayerRef.current = L.rectangle(bounds, {
        color: COLOR_SEL,
        weight: 1.5,
        fillColor: COLOR_SEL,
        fillOpacity: 0.08,
        dashArray: "4 4",
      }).addTo(mapa);
    }
  }, [caja]);

  // Toda caja nueva (o cambio de filtros) vuelve a consultar ASF.
  useEffect(() => {
    if (caja) void buscar(caja);
  }, [caja, buscar]);

  // Huellas de los granulos encontrados.
  useEffect(() => {
    const capa = huellasRef.current;
    if (!capa) return;
    capa.clearLayers();
    if (!resultado) return;

    for (const granulo of resultado.granules) {
      if (granulo.footprint.length < 3) continue;
      const activo = seleccion?.id === granulo.id;
      const puntos = granulo.footprint.map(
        ([lon, lat]) => [lat, lon] as L.LatLngTuple,
      );
      const poligono = L.polygon(puntos, {
        color: activo ? COLOR_SEL : COLOR,
        weight: activo ? 2 : 1,
        opacity: 0.9,
        fillColor: activo ? COLOR_SEL : COLOR,
        fillOpacity: activo ? 0.16 : 0.06,
      });
      poligono.on("click", () => elegirGranulo(granulo));
      poligono.bindTooltip(`${granulo.level} · ${fechaCorta(granulo.start)}`, {
        sticky: true,
      });
      poligono.addTo(capa);
    }
  }, [resultado, seleccion, elegirGranulo]);

  // El job de descarga+render se sigue por SSE, igual que la consola.
  const trabajoId = trabajo?.id ?? null;
  useEffect(() => {
    if (!trabajoId) return;
    let vigente = true;
    const corte = subscribeJob(trabajoId, {
      onSnapshot: (job) => {
        if (vigente) setTrabajo(job);
      },
      onLog: (linea) =>
        setTrabajo((previo) =>
          previo && previo.id === trabajoId
            ? { ...previo, logs: [...previo.logs, linea].slice(-400) }
            : previo,
        ),
      onProgress: (progress, stage) =>
        setTrabajo((previo) =>
          previo && previo.id === trabajoId ? { ...previo, progress, stage } : previo,
        ),
      onArtifact: (artefacto) =>
        setTrabajo((previo) => {
          if (!previo || previo.id !== trabajoId) return previo;
          if (previo.artifacts.some((arte) => arte.url === artefacto.url)) return previo;
          return { ...previo, artifacts: [...previo.artifacts, artefacto] };
        }),
      onFallo: (mensaje) => {
        if (vigente) setError(mensaje);
      },
    });
    return () => {
      vigente = false;
      corte();
    };
  }, [trabajoId]);

  const enMarcha = trabajo?.status === "queued" || trabajo?.status === "running";

  async function renderizar() {
    if (!seleccion || !caja) return;
    setError(null);
    const polFinal =
      pol !== "auto" && !seleccion.polarization.includes(pol.toUpperCase())
        ? "auto"
        : pol;
    const modoFinal =
      modo === "color" && seleccion.polarization.length < 2 ? "gris" : modo;
    try {
      const job = await createJob("nisar_render", {
        granulo: seleccion.id,
        url: seleccion.download,
        coleccion: seleccion.collection,
        bbox: `${caja.oeste},${caja.sur},${caja.este},${caja.norte}`,
        pol: polFinal,
        modo: modoFinal,
        px: Number(px),
      });
      setTrabajo(job);
    } catch (exc) {
      setError(
        exc instanceof Error ? exc.message : "No se pudo crear el trabajo NISAR.",
      );
    }
  }

  async function cancelarRender() {
    if (!trabajo) return;
    try {
      setTrabajo(await cancelJob(trabajo.id));
    } catch (exc) {
      setError(
        exc instanceof Error ? exc.message : "No se pudo cancelar el trabajo.",
      );
    }
  }

  function limpiar() {
    setCaja(null);
    setResultado(null);
    setSeleccion(null);
    setImagen(null);
    setDibujando(false);
    setError(null);
  }

  function alternarCaja() {
    setDibujando((previo) => !previo);
  }

  return (
    <section className="nisar" aria-label="Visor NISAR">
      <div className="nisar__mapa">
        <div ref={contenedor} className="nisar__leaflet" />
        <div className="nisar__herramientas">
          <button
            type="button"
            className={dibujando ? "btn btn--primary" : "btn"}
            aria-pressed={dibujando}
            onClick={alternarCaja}
          >
            {dibujando ? "Soltar cierra la caja" : "Dibujar caja"}
          </button>
          <button type="button" className="btn" onClick={limpiar}>
            Limpiar
          </button>
          <span className="nisar__coord">
            {caja ? bboxTexto(caja) : "Sin caja"}
          </span>
        </div>
      </div>

      <aside className="nisar__panel" aria-label="Escenas NISAR">
        <header className="nisar__head">
          <h2 className="nisar__title">NISAR · radar de apertura sintetica</h2>
          <p className="nisar__sub">
            Elegí una caja sobre Paraguay y ASF devuelve las escenas. Las imagenes
            browse son publicas; los .h5 quedan para la Fase 2.
          </p>
        </header>

        <div className="nisar__filtros">
          <label>
            Nivel
            <select value={nivel} onChange={(evento) => setNivel(evento.target.value)}>
              {(catalogo?.levels ?? [{ value: "GCOV", label: "GCOV", detail: "" }]).map(
                (opcion) => (
                  <option key={opcion.value} value={opcion.value}>
                    {opcion.label}
                  </option>
                ),
              )}
            </select>
          </label>
          <label>
            Desde (UTC)
            <input type="date" value={desde} onChange={(evento) => setDesde(evento.target.value)} />
          </label>
          <label className="nisar__ancho">
            Hasta (UTC)
            <input type="date" value={hasta} onChange={(evento) => setHasta(evento.target.value)} />
          </label>
          <button
            type="button"
            className={`btn btn--primary nisar__ancho${
              caja ? "" : " nisar__btn-espera"
            }`}
            disabled={!caja || cargando}
            onClick={() => caja && void buscar(caja)}
          >
            {cargando ? "Consultando ASF…" : caja ? "Buscar escenas" : "Elegí una caja"}
          </button>
        </div>

        {error ? (
          <p className="nisar__aviso" role="alert">
            {error}
          </p>
        ) : null}

        <p className="nisar__estado" aria-live="polite">
          {cargando
            ? "Consultando ASF…"
            : resultado
              ? `${resultado.total} escena(s) · mostrando ${resultado.returned}`
              : "Dibujá una caja sobre el mapa para empezar."}
        </p>

        <ul className="nisar__lista">
          {(resultado?.granules ?? []).map((granulo) => (
            <li key={granulo.id}>
              <button
                type="button"
                className="nisar__item"
                aria-current={seleccion?.id === granulo.id ? "true" : undefined}
                onClick={() => elegirGranulo(granulo)}
              >
                {granulo.thumbnail ? (
                  <img className="nisar__thumb" src={granulo.thumbnail} alt="" loading="lazy" />
                ) : (
                  <span className="nisar__thumb" aria-hidden="true" />
                )}
                <span className="nisar__item-txt">
                  <span className="nisar__item-fecha">{fechaCorta(granulo.start)}</span>
                  <span className="nisar__item-meta">
                    {granulo.direction === "ASCENDING" ? "ascendente" : "descendente"}
                    {granulo.path !== null ? ` · orbita ${granulo.path}` : ""}
                    {granulo.size_mb !== null ? ` · ${granulo.size_mb} MB` : ""}
                  </span>
                  <span className="nisar__chips">
                    {granulo.polarization.map((pol) => (
                      <span className="nisar__chip" key={pol}>
                        {pol}
                      </span>
                    ))}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>

        {resultado && resultado.notes.length > 0 ? (
          <ul className="nisar__notas">
            {resultado.notes.map((nota) => (
              <li key={nota}>{nota}</li>
            ))}
          </ul>
        ) : null}

        {seleccion ? (
          <div className="nisar__detalle">
            <h3>Escena seleccionada</h3>
            {imagen ? (
              <img className="nisar__imagen" src={imagen} alt={`Browse de ${seleccion.id}`} />
            ) : (
              <p className="nisar__vacio">Sin imagen browse para esta escena.</p>
            )}

            {seleccion.images.length > 0 ? (
              <div className="nisar__tabs" role="group" aria-label="Capas de la escena">
                {seleccion.images.map((capa) => (
                  <button
                    type="button"
                    key={capa.url}
                    className={
                      imagen === capa.url ? "nisar__tab nisar__tab--on" : "nisar__tab"
                    }
                    aria-pressed={imagen === capa.url}
                    onClick={() => setImagen(capa.url)}
                  >
                    {capa.label}
                  </button>
                ))}
              </div>
            ) : null}

            <dl className="nisar__dl">
              <dt>Escena</dt>
              <dd>{seleccion.id}</dd>
              <dt>Nivel</dt>
              <dd>{seleccion.level}</dd>
              <dt>Inicio</dt>
              <dd>{fechaCorta(seleccion.start)}</dd>
              <dt>Fin</dt>
              <dd>{fechaCorta(seleccion.stop)}</dd>
              <dt>Coleccion</dt>
              <dd>{seleccion.collection}</dd>
              <dt>Polarizacion</dt>
              <dd>{seleccion.polarization.join(" · ") || "-"}</dd>
              <dt>Track / frame</dt>
              <dd>
                {seleccion.path ?? "-"} / {seleccion.frame ?? "-"}
              </dd>
            </dl>

            <div className="nisar__acciones">
              <a className="btn" href={seleccion.asf_url} target="_blank" rel="noreferrer">
                Abrir en ASF Vertex
              </a>
              <a className="btn" href={seleccion.download} target="_blank" rel="noreferrer">
                Descargar .h5 (Earthdata)
              </a>
            </div>

            <div className="nisar__render">
              <h3>Render de la caja</h3>
              <p className="nisar__sub">
                Baja el .h5 a {catalogo?.data_root ?? "la carpeta de datos"} y recorta
                esta caja en la grilla de la escena.
                {seleccion.size_mb !== null
                  ? ` Pesa ~${seleccion.size_mb} MB.`
                  : ""}
              </p>
              <div className="nisar__render-ctrl">
                <label>
                  Polarización
                  <select value={pol} onChange={(evento) => setPol(evento.target.value)}>
                    <option value="auto">Auto</option>
                    {seleccion.polarization.map((valor) => (
                      <option key={valor} value={valor.toLowerCase()}>
                        {valor}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Modo
                  <select value={modo} onChange={(evento) => setModo(evento.target.value)}>
                    <option value="gris">Gris (dB)</option>
                    <option value="color" disabled={seleccion.polarization.length < 2}>
                      Color HH/HV
                    </option>
                  </select>
                </label>
                <label>
                  Tamaño
                  <select value={px} onChange={(evento) => setPx(evento.target.value)}>
                    <option value="1600">1600 px</option>
                    <option value="2400">2400 px</option>
                    <option value="3200">3200 px</option>
                    <option value="4096">4096 px</option>
                  </select>
                </label>
              </div>

              {!catalogo?.earthdata_configured ? (
                <p className="nisar__aviso">
                  Falta EARTHDATA_USER y EARTHDATA_PASSWORD en .env para bajar el .h5.
                </p>
              ) : null}

              <div className="nisar__acciones">
                <button
                  type="button"
                  className="btn btn--primary"
                  disabled={!caja || enMarcha || !catalogo?.earthdata_configured}
                  onClick={() => void renderizar()}
                >
                  Descargar y renderizar
                </button>
                {enMarcha ? (
                  <button type="button" className="btn" onClick={() => void cancelarRender()}>
                    Cancelar
                  </button>
                ) : null}
              </div>

              {trabajo ? (
                <div className="nisar__job">
                  <div className="nisar__job-head">
                    <span>{trabajo.stage}</span>
                    <span>{Math.round(trabajo.progress * 100)} %</span>
                  </div>
                  <div className="nisar__bar">
                    <i style={{ width: `${Math.round(trabajo.progress * 100)}%` }} />
                  </div>
                  {trabajo.logs.length > 0 ? (
                    <ul className="nisar__logs">
                      {trabajo.logs.slice(-6).map((linea, indice) => (
                        <li key={`${linea.at}-${indice}`}>{linea.text}</li>
                      ))}
                    </ul>
                  ) : null}
                  {trabajo.error ? (
                    <p className="nisar__aviso">{trabajo.error}</p>
                  ) : null}
                  {trabajo.artifacts
                    .filter((arte) => arte.kind === "image")
                    .map((arte) => (
                      <img
                        key={arte.url}
                        className="nisar__imagen"
                        src={arte.url}
                        alt="Recorte NISAR renderizado"
                      />
                    ))}
                </div>
              ) : null}
            </div>
          </div>
        ) : null}
      </aside>
    </section>
  );
}
