import { useCallback, useEffect, useRef, useState } from "react";
import L from "leaflet";
import type { FeatureCollection } from "geojson";

import { cancelJob, createJob, revealJob, subscribeJob } from "../api";
import { getLocalScenes, getNisarCatalog, getParaguay, searchNisar } from "../nisar";
import type {
  Caja,
  NisarCatalog,
  NisarGranule,
  NisarLocalScene,
  NisarSearch,
} from "../nisar";
import type { Job, Params } from "../types";

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

function pesoArchivo(bytes: number): string {
  return bytes >= 1_048_576
    ? `${(bytes / 1_048_576).toFixed(1)} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

interface StatsRow {
  label: string;
  value: string;
}

function _get(meta: Record<string, unknown>, ruta: string): unknown {
  let actual: unknown = meta;
  for (const parte of ruta.split(".")) {
    if (actual === null || typeof actual !== "object") return undefined;
    actual = (actual as Record<string, unknown>)[parte];
  }
  return actual;
}

function resumenStats(meta: Record<string, unknown>): StatsRow[] {
  const filas: StatsRow[] = [];
  const agregar = (
    label: string,
    ruta: string,
    formato: (valor: unknown) => string,
  ) => {
    const valor = _get(meta, ruta);
    if (valor === undefined || valor === null || valor === "") return;
    filas.push({ label, value: formato(valor) });
  };
  const texto = (valor: unknown) => String(valor);
  const num = (valor: unknown) =>
    Number(valor).toLocaleString("es-PY", { maximumFractionDigits: 2 });
  const ha = (valor: unknown) => `${num(valor)} ha`;
  const pct = (valor: unknown) => `${Number(valor).toFixed(1)} %`;
  const db = (valor: unknown) => `${Number(valor).toFixed(1)} dB`;

  agregar("Producto", "producto", texto);
  agregar("Fecha", "fecha", texto);
  agregar("Fecha", "nisar.fecha", texto);
  agregar("Antes", "fecha_antes", texto);
  agregar("Después", "fecha_despues", texto);
  agregar("Track / frame", "track", (valor) => `${valor} / ${_get(meta, "frame") ?? "?"}`);
  agregar("Track / frame", "nisar.track", (valor) => `${valor} / ${_get(meta, "nisar.frame") ?? "?"}`);
  agregar("Fechas", "fechas", (valor) =>
    `${Array.isArray(valor) ? valor.length : "?"} fecha(s)`,
  );
  agregar("Área", "area_ha", ha);
  agregar("Bosque", "bosque_ha", ha);
  agregar("Pérdida (área)", "perdida_ha", ha);
  agregar("Pérdida (%)", "perdida_pct", pct);
  agregar("Pérdida del bosque", "perdida_bosque_pct", pct);
  agregar("Ganancia", "ganancia_ha", ha);
  agregar("Cicatriz (área)", "cicatriz_ha", ha);
  agregar("Cicatriz (%)", "cicatriz_pct", pct);
  agregar("Agua (área)", "agua_ha", ha);
  agregar("Agua (%)", "agua_pct", pct);
  agregar("RVI medio", "rvi_medio", num);
  agregar("RVI p10 / p90", "rvi_p10", (valor) => `${num(valor)} / ${num(_get(meta, "rvi_p90"))}`);
  agregar("Umbral", "umbral_db", db);
  agregar("HV mínimo", "hv_min_db", db);
  agregar("HH máximo", "hh_max_db", db);
  agregar("HV máximo", "hv_max_db", db);
  agregar("NDVI medio", "ndvi.medio", num);
  agregar("Correlación HV/NDVI", "correlacion", num);
  agregar("Cambio CUSUM", "cusum.cambio_ha", ha);
  agregar("Área CUSUM", "cusum.area_ha", ha);
  agregar("Sentinel-2", "optico.items", (valor) => `${valor} ítem(s)`);
  agregar("Cobertura NDVI", "optico.cobertura_valida_pct", pct);
  agregar("Focos FIRMS", "focos", texto);
  agregar("Resolución", "mpp", (valor) => `${Number(valor).toFixed(0)} m/px`);
  agregar("Resolución", "metros_por_px", (valor) => `${Number(valor).toFixed(0)} m/px`);
  agregar("EPSG", "epsg", texto);
  agregar("Polarización", "polarizaciones", (valor) =>
    Array.isArray(valor) ? valor.join(" · ") : String(valor),
  );
  agregar("Polarización", "polarizacion", texto);
  agregar("Modo", "modo", texto);
  agregar("Colección", "coleccion", texto);

  const clases = meta.clases;
  if (clases && typeof clases === "object" && !Array.isArray(clases)) {
    for (const [nombre, valor] of Object.entries(clases as Record<string, unknown>)) {
      filas.push({ label: nombre, value: ha(valor) });
    }
  }
  return filas;
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
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [locales, setLocales] = useState<NisarLocalScene[]>([]);
  const [fechasSerie, setFechasSerie] = useState<string[]>([]);
  const [producto, setProducto] = useState("recorte");
  const [antesId, setAntesId] = useState("");
  const [modoCambio, setModoCambio] = useState("mascara");
  const [umbral, setUmbral] = useState("3");
  const [hvMin, setHvMin] = useState("-15.5");
  const [modoGeo, setModoGeo] = useState("db");
  const [hhMax, setHhMax] = useState("-20");
  const [hvMax, setHvMax] = useState("-25");
  const [firms, setFirms] = useState(true);
  const [dias, setDias] = useState("15");
  const [nubes, setNubes] = useState("40");

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

  // Fechas del mismo track/frame para comparar.
  const candidatos = (resultado?.granules ?? [])
    .filter(
      (granulo) =>
        granulo.id !== seleccion?.id &&
        granulo.path !== null &&
        granulo.path === seleccion?.path &&
        granulo.frame === seleccion?.frame &&
        granulo.collection === seleccion?.collection,
    )
    .sort((a, b) => b.start.localeCompare(a.start));
  const antes = candidatos.find((granulo) => granulo.id === antesId) ?? null;

  useEffect(() => {
    if (!seleccion) {
      setAntesId("");
      return;
    }
    const lista = (resultado?.granules ?? [])
      .filter(
        (granulo) =>
          granulo.id !== seleccion.id &&
          granulo.path !== null &&
          granulo.path === seleccion.path &&
          granulo.frame === seleccion.frame &&
          granulo.collection === seleccion.collection,
      )
      .sort((a, b) => b.start.localeCompare(a.start));
    if (lista.length === 0) {
      setAntesId("");
      return;
    }
    if (lista.some((granulo) => granulo.id === antesId)) return;
    const previas = lista.filter((granulo) => granulo.start < seleccion.start);
    setAntesId((previas[0] ?? lista[0]).id);
  }, [seleccion, resultado, antesId]);

  // La serie lee como máximo 1600 px para no apilar 11 escenas gigantes.
  useEffect(() => {
    if (producto === "serie" && px !== "1200" && px !== "1600") {
      setPx("1600");
    }
  }, [producto, px]);

  const statsArtifact =
    trabajo?.artifacts.find(
      (arte) => arte.kind === "file" && arte.name.endsWith(".json"),
    ) ?? null;

  useEffect(() => {
    if (!statsArtifact) {
      setStats(null);
      return;
    }
    let vigente = true;
    fetch(statsArtifact.url)
      .then((respuesta) => (respuesta.ok ? respuesta.json() : null))
      .then((datos) => {
        if (vigente) setStats(datos as Record<string, unknown> | null);
      })
      .catch(() => {
        if (vigente) setStats(null);
      });
    return () => {
      vigente = false;
    };
  }, [statsArtifact?.url]);

  useEffect(() => {
    if (
      !seleccion ||
      seleccion.path === null ||
      seleccion.frame === null ||
      !seleccion.collection
    ) {
      setLocales([]);
      setFechasSerie([]);
      return;
    }
    let vigente = true;
    getLocalScenes(seleccion.path, seleccion.frame, seleccion.collection)
      .then((datos) => {
        if (!vigente) return;
        setLocales(datos.scenes);
        setFechasSerie(datos.scenes.map((escena) => escena.id));
      })
      .catch(() => {
        if (vigente) {
          setLocales([]);
          setFechasSerie([]);
        }
      });
    return () => {
      vigente = false;
    };
  }, [seleccion?.id, seleccion?.path, seleccion?.frame, seleccion?.collection]);

  const resumen = stats ? resumenStats(stats) : [];
  const enMarcha = trabajo?.status === "queued" || trabajo?.status === "running";
  const esGcov = seleccion?.level === "GCOV";

  async function renderizar() {
    if (!seleccion || !caja) return;
    if (seleccion.level !== "GCOV") {
      setError(
        `La escena es ${seleccion.level}. Los productos actuales usan GCOV; ` +
          "elegí una escena GCOV para analizar.",
      );
      return;
    }
    setError(null);
    const polFinal =
      pol !== "auto" && !seleccion.polarization.includes(pol.toUpperCase())
        ? "auto"
        : pol;
    const modoFinal =
      modo === "color" && seleccion.polarization.length < 2 ? "gris" : modo;
    const params: Params = {
      producto,
      nivel: seleccion.level,
      granulo: seleccion.id,
      url: seleccion.download,
      coleccion: seleccion.collection,
      bbox: `${caja.oeste},${caja.sur},${caja.este},${caja.norte}`,
      px: Number(px),
    };
    if (producto === "recorte") {
      params.pol = polFinal;
      params.modo = modoFinal;
    } else if (producto === "cambio" || producto === "incendio") {
      if (!antes) {
        setError("Elegí una fecha anterior del mismo track/frame.");
        return;
      }
      params.antes_granulo = antes.id;
      params.antes_url = antes.download;
      params.antes_coleccion = antes.collection;
      params.umbral = Number(umbral);
      params.hv_min = Number(hvMin);
      if (producto === "cambio") {
        params.modo_cambio = modoCambio;
      } else {
        params.firms = firms;
      }
    } else if (producto === "agua") {
      params.hh_max = Number(hhMax);
      params.hv_max = Number(hvMax);
    } else if (producto === "fusion") {
      params.dias = Number(dias);
      params.nubes = Number(nubes);
    } else if (producto === "serie") {
      if (seleccion.path === null || seleccion.frame === null) {
        setError("La escena no declara track/frame; no puedo armar la serie.");
        return;
      }
      params.track = seleccion.path;
      params.frame = seleccion.frame;
      params.umbral = Number(umbral);
      params.hv_min = Number(hvMin);
      if (fechasSerie.length < 2) {
        setError("Elegí al menos 2 fechas locales para la serie.");
        return;
      }
      params.fechas = fechasSerie.join(",");
    } else if (producto === "geotiff") {
      params.pol = polFinal;
      params.modo_geo = modoGeo;
    }
    try {
      const job = await createJob("nisar_render", params);
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

  async function revelarCarpeta() {
    if (!trabajo) return;
    try {
      await revealJob(trabajo.id);
    } catch (exc) {
      setError(
        exc instanceof Error ? exc.message : "No se pudo abrir la carpeta.",
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
    setTrabajo(null);
    setProducto("recorte");
    setAntesId("");
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
            Elegí una caja sobre Paraguay y ASF devuelve las escenas. Las imágenes
            browse son públicas; los .h5 se descargan con Earthdata.
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
              <h3>Análisis de la caja</h3>
              {esGcov ? (
                <>
                  <p className="nisar__sub">
                    {producto === "cambio"
                      ? "Compara HV entre esta fecha y otra del mismo track/frame. Pérdida = caída de HV."
                      : producto === "rvi"
                        ? "Índice de vegetación radar (HH/HV) de esta fecha."
                        : producto === "serie"
                          ? "Usa todas las fechas locales del mismo track/frame/colección (mínimo 2). Genera serie, mediana y CUSUM."
                          : producto === "geotiff"
                            ? "Exporta la caja como GeoTIFF en el EPSG de la escena. El .tif queda en la carpeta del job."
                            : producto === "agua"
                              ? "Máscara de agua abierta: HH y HV bajos. Reporta hectáreas y porcentaje."
                              : producto === "incendio"
                                ? "Cicatriz por caída de HV entre dos fechas, con focos FIRMS opcionales."
                                : producto === "fusion"
                                  ? "Compone Sentinel-2 L2A (NDVI sin nubes) sobre la caja y la cruza con HV. Clasificación rule-based, no un modelo entrenado."
                                  : `Baja el .h5 a ${
                                      catalogo?.data_root
                                        ? `${catalogo.data_root}/nisar`
                                        : "la carpeta de datos"
                                    } y recorta esta caja.`}
                    {seleccion.size_mb !== null
                      ? ` Pesa ~${seleccion.size_mb} MB.`
                      : ""}
                  </p>
                  <div className="nisar__render-ctrl">
                    <label className="nisar__ancho">
                      Producto
                      <select
                        value={producto}
                        disabled={!esGcov}
                        onChange={(evento) => setProducto(evento.target.value)}
                      >
                        <optgroup label="Visualización">
                          <option value="recorte">Recorte (dB / color)</option>
                          <option value="rvi">RVI (vegetación)</option>
                          <option value="geotiff">GeoTIFF (GIS)</option>
                        </optgroup>
                        <optgroup label="Cambio">
                          <option value="cambio">Cambio de cobertura</option>
                          <option value="serie">Serie temporal + CUSUM</option>
                          <option value="incendio">Incendio (cicatriz + FIRMS)</option>
                        </optgroup>
                        <optgroup label="Agua">
                          <option value="agua">Agua / inundación</option>
                        </optgroup>
                        <optgroup label="Óptico">
                          <option value="fusion">Fusión óptica (Sentinel-2)</option>
                        </optgroup>
                      </select>
                    </label>

                    {producto === "recorte" ? (
                      <>
                        <label>
                          Polarización
                          <select
                            value={pol}
                            onChange={(evento) => setPol(evento.target.value)}
                          >
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
                          <select
                            value={modo}
                            onChange={(evento) => setModo(evento.target.value)}
                          >
                            <option value="gris">Gris (dB)</option>
                            <option value="color" disabled={seleccion.polarization.length < 2}>
                              Color HH/HV
                            </option>
                          </select>
                        </label>
                      </>
                    ) : null}

                    {producto === "geotiff" ? (
                      <>
                        <label>
                          Polarización
                          <select
                            value={pol}
                            onChange={(evento) => setPol(evento.target.value)}
                          >
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
                          <select
                            value={modoGeo}
                            onChange={(evento) => setModoGeo(evento.target.value)}
                          >
                            <option value="db">dB</option>
                            <option value="lineal">Potencia lineal</option>
                          </select>
                        </label>
                      </>
                    ) : null}

                    {producto === "agua" ? (
                      <>
                        <label>
                          HH máx. (dB)
                          <input
                            type="number"
                            min="-40"
                            max="0"
                            step="0.5"
                            value={hhMax}
                            onChange={(evento) => setHhMax(evento.target.value)}
                          />
                        </label>
                        <label>
                          HV máx. (dB)
                          <input
                            type="number"
                            min="-40"
                            max="0"
                            step="0.5"
                            value={hvMax}
                            onChange={(evento) => setHvMax(evento.target.value)}
                          />
                        </label>
                      </>
                    ) : null}

                    {producto === "fusion" ? (
                      <>
                        <label>
                          Días ópticos
                          <select value={dias} onChange={(evento) => setDias(evento.target.value)}>
                            <option value="7">±7 días</option>
                            <option value="15">±15 días</option>
                            <option value="30">±30 días</option>
                          </select>
                        </label>
                        <label>
                          Nubes máx.
                          <select value={nubes} onChange={(evento) => setNubes(evento.target.value)}>
                            <option value="20">20 %</option>
                            <option value="40">40 %</option>
                            <option value="60">60 %</option>
                          </select>
                        </label>
                      </>
                    ) : null}

                    <label>
                      Tamaño
                      {producto === "serie" ? (
                        <select value={px} onChange={(evento) => setPx(evento.target.value)}>
                          <option value="1200">1200 px</option>
                          <option value="1600">1600 px</option>
                        </select>
                      ) : (
                        <select value={px} onChange={(evento) => setPx(evento.target.value)}>
                          <option value="1600">1600 px</option>
                          <option value="2400">2400 px</option>
                          <option value="3200">3200 px</option>
                          <option value="4096">4096 px</option>
                        </select>
                      )}
                    </label>

                    {producto === "cambio" || producto === "incendio" ? (
                      <>
                        <label className="nisar__ancho">
                          Fecha anterior
                          <select
                            value={antesId}
                            onChange={(evento) => setAntesId(evento.target.value)}
                            disabled={candidatos.length === 0}
                          >
                            {candidatos.length === 0 ? (
                              <option value="">Sin otra fecha</option>
                            ) : null}
                            {candidatos.map((granulo) => (
                              <option key={granulo.id} value={granulo.id}>
                                {fechaCorta(granulo.start)}
                              </option>
                            ))}
                          </select>
                        </label>
                        {producto === "cambio" ? (
                          <label>
                            Modo
                            <select
                              value={modoCambio}
                              onChange={(evento) => setModoCambio(evento.target.value)}
                            >
                              <option value="mascara">Máscara</option>
                              <option value="delta">Delta</option>
                              <option value="rgb">RGB</option>
                            </select>
                          </label>
                        ) : null}
                        <label>
                          Umbral (dB)
                          <input
                            type="number"
                            min="0.5"
                            max="20"
                            step="0.5"
                            value={umbral}
                            onChange={(evento) => setUmbral(evento.target.value)}
                          />
                        </label>
                        <label>
                          HV mín. (dB)
                          <input
                            type="number"
                            min="-30"
                            max="0"
                            step="0.5"
                            value={hvMin}
                            onChange={(evento) => setHvMin(evento.target.value)}
                          />
                        </label>
                        {producto === "incendio" ? (
                          <label>
                            Focos FIRMS
                            <select
                              value={firms ? "si" : "no"}
                              onChange={(evento) => setFirms(evento.target.value === "si")}
                            >
                              <option value="si">Sí</option>
                              <option value="no">No</option>
                            </select>
                          </label>
                        ) : null}
                      </>
                    ) : null}

                    {producto === "serie" ? (
                      <>
                        <label>
                          Umbral (dB)
                          <input
                            type="number"
                            min="0.5"
                            max="20"
                            step="0.5"
                            value={umbral}
                            onChange={(evento) => setUmbral(evento.target.value)}
                          />
                        </label>
                        <label>
                          HV mín. (dB)
                          <input
                            type="number"
                            min="-30"
                            max="0"
                            step="0.5"
                            value={hvMin}
                            onChange={(evento) => setHvMin(evento.target.value)}
                          />
                        </label>
                      </>
                    ) : null}
                  </div>

                  {producto === "serie" ? (
                    <div className="nisar__fechas">
                      <div className="nisar__fechas-head">
                        <span>Fechas locales ({locales.length})</span>
                        <button
                          type="button"
                          className="btn"
                          onClick={() =>
                            setFechasSerie(locales.map((escena) => escena.id))
                          }
                        >
                          Todas
                        </button>
                        <button
                          type="button"
                          className="btn"
                          onClick={() => setFechasSerie([])}
                        >
                          Ninguna
                        </button>
                      </div>
                      {locales.length === 0 ? (
                        <p className="nisar__vacio">
                          No hay fechas locales de ese track/frame/colección.
                        </p>
                      ) : (
                        <ul className="nisar__fechas-lista">
                          {locales.map((escena) => (
                            <li key={escena.id}>
                              <label>
                                <input
                                  type="checkbox"
                                  checked={fechasSerie.includes(escena.id)}
                                  onChange={(evento) =>
                                    setFechasSerie((previo) =>
                                      evento.target.checked
                                        ? [...previo, escena.id]
                                        : previo.filter((id) => id !== escena.id),
                                    )
                                  }
                                />
                                <span>{escena.date}</span>
                                <span className="nisar__fechas-peso">
                                  {escena.size_mb} MB
                                </span>
                              </label>
                            </li>
                          ))}
                        </ul>
                      )}
                      {fechasSerie.length < 2 ? (
                        <p className="nisar__aviso">
                          Elegí al menos 2 fechas para la serie.
                        </p>
                      ) : null}
                    </div>
                  ) : null}

                  {(producto === "cambio" || producto === "incendio") &&
                  candidatos.length === 0 ? (
                    <p className="nisar__aviso">
                      No hay otra fecha del mismo track/frame en esta búsqueda. Ampliá la
                      ventana de fechas.
                    </p>
                  ) : null}

                  {!catalogo?.earthdata_configured ? (
                    <p className="nisar__aviso">
                      Falta EARTHDATA_USER y EARTHDATA_PASSWORD en .env para bajar el .h5.
                    </p>
                  ) : null}

                  <div className="nisar__acciones">
                    <button
                      type="button"
                      className="btn btn--primary"
                      disabled={
                        !caja ||
                        !esGcov ||
                        enMarcha ||
                        !catalogo?.earthdata_configured ||
                        ((producto === "cambio" || producto === "incendio") && !antes) ||
                        (producto === "serie" &&
                          (seleccion.path === null ||
                            seleccion.frame === null ||
                            fechasSerie.length < 2))
                      }
                      onClick={() => void renderizar()}
                    >
                      {producto === "cambio"
                        ? "Comparar fechas"
                        : producto === "rvi"
                          ? "Calcular RVI"
                          : producto === "serie"
                            ? "Generar serie"
                            : producto === "geotiff"
                              ? "Exportar GeoTIFF"
                              : producto === "agua"
                                ? "Detectar agua"
                                : producto === "incendio"
                                  ? "Detectar cicatriz"
                                  : producto === "fusion"
                                    ? "Fusionar óptico"
                                    : "Descargar y renderizar"}
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
                      {resumen.length > 0 ? (
                        <dl className="nisar__stats">
                          {resumen.map((fila) => (
                            <div key={`${fila.label}-${fila.value}`} className="nisar__stat">
                              <dt>{fila.label}</dt>
                              <dd>{fila.value}</dd>
                            </div>
                          ))}
                        </dl>
                      ) : null}
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
                            alt="Resultado NISAR"
                          />
                        ))}
                      {trabajo.artifacts
                        .filter((arte) => arte.kind === "file")
                        .map((arte) => (
                          <a
                            key={arte.url}
                            className="nisar__archivo"
                            href={arte.url}
                            download={arte.name}
                          >
                            {arte.name} · {pesoArchivo(arte.bytes)}
                          </a>
                        ))}
                      <div className="nisar__acciones">
                        <button
                          type="button"
                          className="btn"
                          onClick={() => void revelarCarpeta()}
                        >
                          Abrir carpeta
                        </button>
                      </div>
                    </div>
                  ) : null}
                </>
              ) : (
                <p className="nisar__aviso">
                  {seleccion.level} no usa la grilla GCOV. Los productos actuales
                  (RVI, cambio, agua, incendio, serie, fusión) requieren GCOV.
                  Podés descargar el .h5 o elegir una escena GCOV.
                </p>
              )}
            </div>
          </div>
        ) : null}
      </aside>
    </section>
  );
}
