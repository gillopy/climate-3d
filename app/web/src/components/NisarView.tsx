import { useCallback, useEffect, useRef, useState } from "react";
import L from "leaflet";
import type { FeatureCollection } from "geojson";

import { cancelJob, createJob, subscribeJob } from "../api";
import {
  getLocalScenes,
  getNisarCatalog,
  getNisarScene,
  getNisarTimeline,
  getParaguay,
  searchNisar,
} from "../nisar";
import type {
  Caja,
  NisarCatalog,
  NisarGranule,
  NisarLocalScene,
  NisarSearch,
  NisarTimelineScene,
} from "../nisar";
import { fechaCorta } from "../formato";
import type { Job, Params } from "../types";
import { JobsPanel } from "./JobsPanel";

const CENTRO_PARAGUAY: L.LatLngTuple = [-23.4, -58.4];
const COLOR = "#5e6ad2";
const COLOR_SEL = "#828fff";
//: La caja de selección va en ámbar: no se confunde con las huellas ASF (iris).
const COLOR_CAJA = "#f5a524";

const ESTILO_CAJA: L.PathOptions = {
  color: COLOR_CAJA,
  weight: 2.5,
  opacity: 1,
  fillColor: COLOR_CAJA,
  fillOpacity: 0.12,
  className: "nisar__caja",
  interactive: false,
};

const ESTILO_BORRADOR: L.PathOptions = {
  color: COLOR_CAJA,
  weight: 2,
  opacity: 0.9,
  fillColor: COLOR_CAJA,
  fillOpacity: 0.08,
  dashArray: "5 4",
  interactive: false,
};

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

/** `NISAR_..._20261017T214920_...` -> `2026-10-17T21:49:20Z` (ordenable). */
function instanteDeId(id: string): string {
  const partes = /(\d{8})T(\d{6})/.exec(id);
  if (!partes) return "";
  const [, dia, hora] = partes;
  return `${dia.slice(0, 4)}-${dia.slice(4, 6)}-${dia.slice(6)}T${hora.slice(0, 2)}:${hora.slice(2, 4)}:${hora.slice(4, 6)}Z`;
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
  const borradorRef = useRef<L.Rectangle | null>(null);

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
  const [locales, setLocales] = useState<NisarLocalScene[]>([]);
  const [fechasSerie, setFechasSerie] = useState<string[]>([]);
  const [producto, setProducto] = useState("recorte");
  const [antesId, setAntesId] = useState("");
  // Fecha anterior elegida a mano: puede no venir de la ventana de busqueda.
  const [antesExterno, setAntesExterno] = useState<NisarTimelineScene | null>(null);
  const [timeline, setTimeline] = useState<NisarTimelineScene[]>([]);
  const [cargandoFechas, setCargandoFechas] = useState(false);
  const [fechaNueva, setFechaNueva] = useState("");
  const [resolviendo, setResolviendo] = useState(false);
  const [coordTexto, setCoordTexto] = useState("");
  // Confirmar la caida de HV con NDVI de Sentinel-2 y descartar parches chicos:
  // sin esto el "rojo" incluye cosechas, anegamientos y estacionalidad.
  const [verificarS2, setVerificarS2] = useState(true);
  // Persistencia: un cambio tiene que seguir ahi en la fecha siguiente. Usa los
  // .h5 que ya estan en disco; si no hay fecha posterior, el producto avisa.
  // Por defecto no se exige persistencia: la corrida compara solo el par.
  const [persistencia, setPersistencia] = useState("0");
  const [modoCambio, setModoCambio] = useState("comparar");
  const [umbral, setUmbral] = useState("2.5");
  const [hvMin, setHvMin] = useState("-15.5");
  const [modoGeo, setModoGeo] = useState("db");
  const [hhMax, setHhMax] = useState("-20");
  const [hvMax, setHvMax] = useState("-25");
  const [firms, setFirms] = useState(true);
  const [dias, setDias] = useState("15");
  const [nubes, setNubes] = useState("40");
  const [algoritmoSme2, setAlgoritmoSme2] = useState("PMI");
  const [soloCalidadSme2, setSoloCalidadSme2] = useState(false);
  // Panel de trabajos: historial de corridas con logs y resultados.
  const [jobNuevo, setJobNuevo] = useState<string | null>(null);

  const elegirGranulo = useCallback((granulo: NisarGranule) => {
    setSeleccion(granulo);
    setImagen(imagenInicial(granulo));
    // Otra escena principal invalida la fecha anterior elegida a mano.
    setAntesExterno(null);
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
        setAntesExterno(null);
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

    // El contorno del pais es opcional: `datos/paraguay_gadm.json` no se versiona
    // (licencia GADM) y la imagen Docker no lo trae. Sin el archivo el mapa, las
    // huellas y las cajas funcionan igual, asi que un 404 no se muestra como error.
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
      .catch(() => undefined);

    return () => {
      mapa.remove();
      mapaRef.current = null;
      huellasRef.current = null;
      cajaLayerRef.current = null;
      borradorRef.current = null;
    };
  }, []);

  useEffect(() => {
    getNisarCatalog()
      .then(setCatalogo)
      .catch(() => setError("No se pudo leer el catalogo NISAR."));
  }, []);

  // Dibujo del cuadro: mouse abajo, mover, soltar.
  useEffect(() => {
    const mapa = mapaRef.current;
    if (!mapa) return;

    const quitarBorrador = () => {
      if (borradorRef.current) {
        mapa.removeLayer(borradorRef.current);
        borradorRef.current = null;
      }
    };

    if (!dibujando) {
      mapa.dragging.enable();
      mapa.getContainer().style.cursor = "";
      quitarBorrador();
      return;
    }

    mapa.dragging.disable();
    mapa.getContainer().style.cursor = "crosshair";
    let inicio: L.LatLng | null = null;

    const alMover = (evento: L.LeafletMouseEvent) => {
      if (!inicio || !borradorRef.current) return;
      borradorRef.current.setBounds(L.latLngBounds(inicio, evento.latlng));
    };

    const alBajar = (evento: L.LeafletMouseEvent) => {
      inicio = evento.latlng;
      quitarBorrador();
      borradorRef.current = L.rectangle(
        L.latLngBounds(inicio, inicio),
        ESTILO_BORRADOR,
      ).addTo(mapa);
      mapa.on("mousemove", alMover);
    };

    const alSoltar = (evento: L.LeafletMouseEvent) => {
      mapa.off("mousemove", alMover);
      if (!inicio) return;
      const bounds = L.latLngBounds(inicio, evento.latlng);
      inicio = null;
      quitarBorrador();
      setDibujando(false);
      setCaja(cajaDeBounds(bounds));
    };

    const alTeclear = (evento: KeyboardEvent) => {
      if (evento.key === "Escape") setDibujando(false);
    };

    mapa.on("mousedown", alBajar);
    mapa.on("mouseup", alSoltar);
    window.addEventListener("keydown", alTeclear);
    return () => {
      mapa.off("mousedown", alBajar);
      mapa.off("mouseup", alSoltar);
      mapa.off("mousemove", alMover);
      window.removeEventListener("keydown", alTeclear);
      quitarBorrador();
    };
  }, [dibujando]);

  // La caja vigente se dibuja aunque no se este dibujando.
  useEffect(() => {
    const mapa = mapaRef.current;
    if (!mapa) return;

    if (cajaLayerRef.current) {
      mapa.removeLayer(cajaLayerRef.current);
      cajaLayerRef.current = null;
    }
    if (!caja) return;

    const bounds = L.latLngBounds(
      [caja.sur, caja.oeste],
      [caja.norte, caja.este],
    );
    cajaLayerRef.current = L.rectangle(bounds, ESTILO_CAJA).addTo(mapa);
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
  //
  // Tres fuentes, una sola lista: el timeline de ASF (que ya trae las fechas
  // fuera de la ventana de busqueda), los .h5 que estan en disco y, como red de
  // seguridad, lo que devolvio la busqueda actual.
  const localesComoEscenas: NisarTimelineScene[] = locales.map((escena) => ({
    id: escena.id,
    date: instanteDeId(escena.id),
    start: instanteDeId(escena.id),
    collection: seleccion?.collection ?? "",
    size_mb: escena.size_mb,
    local: true,
    download: "",
    mpp: null,
  }));
  const fechasDelTrack: NisarTimelineScene[] = (() => {
    const mapa = new Map<string, NisarTimelineScene>();
    for (const escena of timeline) mapa.set(escena.id, escena);
    for (const granulo of resultado?.granules ?? []) {
      if (
        granulo.path !== seleccion?.path ||
        granulo.frame !== seleccion?.frame ||
        granulo.collection !== seleccion?.collection ||
        mapa.has(granulo.id)
      ) {
        continue;
      }
      mapa.set(granulo.id, {
        id: granulo.id,
        date: granulo.start.slice(0, 10),
        start: granulo.start,
        collection: granulo.collection,
        size_mb: granulo.size_mb,
        local: granulo.local,
        download: granulo.download,
        mpp: granulo.mpp,
      });
    }
    for (const escena of localesComoEscenas) {
      if (!mapa.has(escena.id)) mapa.set(escena.id, escena);
    }
    return [...mapa.values()].sort((a, b) => a.start.localeCompare(b.start));
  })();
  const candidatos = fechasDelTrack
    .filter(
      (escena) => escena.id !== seleccion?.id && escena.start < (seleccion?.start ?? ""),
    )
    .sort((a, b) => b.start.localeCompare(a.start));
  const antes =
    antesExterno ?? candidatos.find((escena) => escena.id === antesId) ?? null;
  const coleccionesSerie = [
    ...new Set(
      fechasDelTrack
        .filter((escena) => fechasSerie.includes(escena.id))
        .map((escena) => escena.collection),
    ),
  ];

  useEffect(() => {
    if (!seleccion) {
      setAntesId("");
      return;
    }
    if (antesExterno) return;
    const lista = candidatos;
    if (lista.length === 0) {
      setAntesId("");
      return;
    }
    if (lista.some((escena) => escena.id === antesId)) return;
    // Solo escenas anteriores: comparar hacia adelante invierte el signo del cambio.
    setAntesId(lista[0].id);
    // `fechasDelTrack` se rearma en cada render; los disparadores reales son estos.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seleccion, antesId, antesExterno, timeline.length, locales.length, resultado]);

  // El timeline se pide solo para los productos que comparan fechas.
  const necesitaFechas =
    producto === "cambio" || producto === "incendio" || producto === "serie";
  const track = seleccion?.path ?? null;
  const frame = seleccion?.frame ?? null;
  const coleccion = seleccion?.collection ?? "";
  useEffect(() => {
    if (!necesitaFechas || track === null || frame === null || !coleccion) {
      setTimeline([]);
      return;
    }
    let vigente = true;
    setCargandoFechas(true);
    // Sin filtro de coleccion: NISAR publica las fechas viejas solo como
    // PROVISIONAL y las nuevas como VALIDATED. Filtrar dejaria una sola fecha.
    getNisarTimeline(track, frame, "", "GCOV")
      .then((datos) => {
        if (vigente) setTimeline(datos.scenes);
      })
      .catch(() => {
        // Sin timeline queda la busqueda y el disco: no se bloquea nada.
        if (vigente) setTimeline([]);
      })
      .finally(() => {
        if (vigente) setCargandoFechas(false);
      });
    return () => {
      vigente = false;
    };
  }, [necesitaFechas, track, frame, coleccion]);

  // La serie lee como máximo 1600 px para no apilar 11 escenas gigantes.
  useEffect(() => {
    if (producto === "serie" && px !== "1200" && px !== "1600") {
      setPx("1600");
    }
  }, [producto, px]);

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

  const enMarcha = trabajo?.status === "queued" || trabajo?.status === "running";
  const esGcov = seleccion?.level === "GCOV";
  const esSme2 = seleccion?.level === "SME2";
  const esGunw = seleccion?.level === "GUNW";

  async function renderizar() {
    if (!seleccion || !caja) return;
    const nivel = seleccion.level;
    if (nivel !== "GCOV" && nivel !== "SME2" && nivel !== "GUNW") {
      setError(
        `La escena es ${nivel}. Los productos disponibles usan GCOV, SME2 o GUNW; ` +
          "elegí una escena de esos niveles para analizar.",
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
      producto:
        nivel === "SME2" ? "sme2" : nivel === "GUNW" ? "gunw" : producto,
      nivel,
      granulo: seleccion.id,
      url: seleccion.download,
      coleccion: seleccion.collection,
      bbox: `${caja.oeste},${caja.sur},${caja.este},${caja.norte}`,
      px: Number(px),
    };
    if (nivel === "SME2") {
      params.algoritmo = algoritmoSme2;
      params.solo_calidad = soloCalidadSme2;
    } else if (nivel === "GUNW") {
      // GUNW no necesita parametros extra: el renderer muestra coherencia y fase.
    } else if (producto === "recorte") {
      params.pol = polFinal;
      params.modo = modoFinal;
    } else if (producto === "cambio" || producto === "incendio") {
      if (!antes) {
        setError(
          "Elegí una fecha anterior del mismo track/frame, o agregá una con el calendario.",
        );
        return;
      }
      params.antes_granulo = antes.id;
      params.antes_coleccion = antes.collection;
      // Si no esta en disco hace falta la URL; el backend la exige solo si falta.
      if (antes.download) params.antes_url = antes.download;
      params.umbral = Number(umbral);
      params.hv_min = Number(hvMin);
      if (producto === "cambio") {
        params.modo_cambio = modoCambio;
        params.verificar_s2 = verificarS2;
        params.confirmar_temporal = Number(persistencia);
        // La MMU no depende de la confirmacion: un desmonte es un bloque.
        params.mmu_ha = 0.5;
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
        setError("Elegí al menos 2 fechas para la serie.");
        return;
      }
      params.fechas = fechasSerie.join(",");
      // Todas las fechas elegidas viajan con su coleccion: si el .h5 no esta se
      // baja, y si esta en otra carpeta de coleccion la serie la incluye igual.
      const elegidas = fechasDelTrack
        .filter((escena) => fechasSerie.includes(escena.id))
        .map((escena) => ({
          id: escena.id,
          url: escena.download,
          coleccion: escena.collection,
        }));
      if (elegidas.length > 0) params.escenas = JSON.stringify(elegidas);
    } else if (producto === "geotiff") {
      params.pol = polFinal;
      params.modo_geo = modoGeo;
    }
    try {
      const job = await createJob("nisar_render", params);
      setTrabajo(job);
      setJobNuevo(job.id);
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

  async function agregarFecha() {
    if (!seleccion || seleccion.path === null || seleccion.frame === null) {
      setError("Elegí una escena GCOV con track/frame para agregar fechas.");
      return;
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(fechaNueva)) {
      setError("Elegí una fecha (AAAA-MM-DD) para buscarla.");
      return;
    }
    setResolviendo(true);
    setError(null);
    try {
      const escena = await getNisarScene(
        seleccion.path,
        seleccion.frame,
        fechaNueva,
        "",
      );
      const entrada: NisarTimelineScene = {
        id: escena.id,
        date: escena.start.slice(0, 10),
        start: escena.start,
        collection: escena.collection,
        size_mb: escena.size_mb,
        local: escena.local,
        download: escena.download,
        mpp: escena.mpp,
      };
      setTimeline((previo) =>
        [...previo.filter((vieja) => vieja.id !== entrada.id), entrada].sort(
          (a, b) => a.start.localeCompare(b.start),
        ),
      );
      if (producto === "serie") {
        setFechasSerie((previo) =>
          previo.includes(entrada.id) ? previo : [...previo, entrada.id],
        );
      } else if (entrada.start >= seleccion.start) {
        setError(
          "Para comparar, la fecha anterior tiene que ser más vieja que la escena elegida.",
        );
      } else {
        setAntesExterno(entrada);
      }
      setFechaNueva("");
    } catch (exc) {
      setError(
        exc instanceof Error ? exc.message : "No pude resolver esa fecha en ASF.",
      );
    } finally {
      setResolviendo(false);
    }
  }

  async function descargarEscena(escena: {
    id: string;
    download: string;
    collection: string;
    level?: string;
  }) {
    if (!escena.download) {
      setError(
        "Esa fecha no trae URL de ASF: ya está en disco o hay que buscarla de nuevo.",
      );
      return;
    }
    setError(null);
    try {
      const job = await createJob("nisar_render", {
        producto: "descarga",
        nivel: escena.level ?? "GCOV",
        granulo: escena.id,
        url: escena.download,
        coleccion: escena.collection,
      });
      setTrabajo(job);
      setJobNuevo(job.id);
    } catch (exc) {
      setError(
        exc instanceof Error ? exc.message : "No se pudo crear la descarga.",
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
    setAntesExterno(null);
    setTimeline([]);
    setFechaNueva("");
  }

  // Permite pegar la caja exacta (oeste,sur,este,norte) en vez de dibujarla:
  // una caja de 7 km a mano en el mapa es casi imposible de acertar.
  function aplicarCoordenadas() {
    const partes = coordTexto
      .split(/[,\s;]+/)
      .map((parte) => Number(parte.replace(",", ".")))
      .filter((valor) => Number.isFinite(valor));
    if (partes.length !== 4) {
      setError("Las coordenadas van como oeste,sur,este,norte.");
      return;
    }
    const [oeste, sur, este, norte] = partes;
    if (
      !(
        -180 <= oeste &&
        oeste < este &&
        este <= 180 &&
        -90 <= sur &&
        sur < norte &&
        norte <= 90
      )
    ) {
      setError("Coordenadas fuera de rango o invertidas: van oeste,sur,este,norte.");
      return;
    }
    setError(null);
    setDibujando(false);
    setCaja({ oeste, sur, este, norte });
  }

  return (
    <section className="nisar" aria-label="Visor NISAR">
      <div className="nisar__mapa">
        <div ref={contenedor} className="nisar__leaflet" />
        <div className="nisar__herramientas">
          <div className="nisar__tools" role="group" aria-label="Herramienta de dibujo">
            <button
              type="button"
              className={`nisar__tool${dibujando ? " nisar__tool--on" : ""}`}
              aria-pressed={dibujando}
              title="Cuadro: arrastrá sobre el mapa para dibujar un rectángulo"
              onClick={() => setDibujando((previo) => !previo)}
            >
              <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <rect
                  x="2.5"
                  y="4"
                  width="11"
                  height="8"
                  rx="1.2"
                  stroke="currentColor"
                  strokeWidth="1.4"
                />
              </svg>
              Cuadro
            </button>
          </div>
          <button type="button" className="btn" onClick={limpiar}>
            Limpiar
          </button>
          <div className="nisar__coords">
            <div className="nisar__coords-field">
              <input
                type="text"
                value={coordTexto}
                aria-label="Caja por coordenadas: oeste, sur, este, norte"
                placeholder="-61.16,-21.07,-60.83,-20.74"
                title="Formato: oeste,sur,este,norte (grados). Ejemplo: -61.16,-21.07,-60.83,-20.74"
                onChange={(evento) => setCoordTexto(evento.target.value)}
                onKeyDown={(evento) => {
                  if (evento.key === "Enter") aplicarCoordenadas();
                }}
              />
              <span className="nisar__coords-hint">
                oeste,sur,este,norte · ej. -61.16,-21.07,-60.83,-20.74
              </span>
            </div>
            <button
              type="button"
              className="btn"
              disabled={!coordTexto.trim()}
              onClick={aplicarCoordenadas}
            >
              Usar caja
            </button>
          </div>
          <span
            className="nisar__coord"
            title="Caja de selección (oeste, sur, este, norte)"
          >
            <i className="nisar__coord-dot" aria-hidden="true" />
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
          <label className="nisar__ancho">
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
          <label>
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
              : dibujando
                ? "Arrastrá sobre el mapa para dibujar el cuadro."
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
                    {granulo.mpp !== null ? ` · ${granulo.mpp} m/px` : ""}
                    {granulo.size_mb !== null ? ` · ${granulo.size_mb} MB` : ""}
                  </span>
                  <span className="nisar__chips">
                    {granulo.local ? (
                      <span className="nisar__chip nisar__chip--local">local</span>
                    ) : null}
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
              <button
                type="button"
                className="btn"
                disabled={enMarcha || seleccion.local}
                onClick={() =>
                  void descargarEscena({
                    id: seleccion.id,
                    download: seleccion.download,
                    collection: seleccion.collection,
                    level: seleccion.level,
                  })
                }
              >
                {seleccion.local
                  ? "Ya está en disco"
                  : `Descargar a ${catalogo?.nisar_root ?? "E:\\nisar"}`}
              </button>
            </div>

            <div className="nisar__render">
              <h3>Análisis de la caja</h3>
              {esGcov ? (
                <>
                  <p className="nisar__sub">
                    {producto === "cambio"
                      ? "Compara HV entre esta fecha y otra del mismo track/frame. Con Sentinel-2 activo, el rojo es solo bosque cuyo NDVI también cayó (parches ≥ 0.5 ha)."
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
                                      catalogo?.nisar_root
                                        ? catalogo.nisar_root
                                        : "la carpeta de datos NISAR"
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
                      Tamaño máx.
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
                            value={antes?.id ?? ""}
                            onChange={(evento) => {
                              setAntesExterno(null);
                              setAntesId(evento.target.value);
                            }}
                            disabled={candidatos.length === 0}
                          >
                            {candidatos.length === 0 ? (
                              <option value="">Sin otra fecha en el track/frame</option>
                            ) : null}
                            {candidatos.map((escena) => (
                              <option key={escena.id} value={escena.id}>
                                {fechaCorta(escena.start)}
                                {escena.local ? " · local" : " · se descarga"}
                              </option>
                            ))}
                          </select>
                        </label>
                        {antes ? (
                          <dl className="nisar__dl nisar__ancho">
                            <dt>Fecha anterior</dt>
                            <dd>{fechaCorta(antes.start)}</dd>
                            <dt>Origen</dt>
                            <dd>
                              {antes.local
                                ? "ya está en disco"
                                : antes.size_mb !== null
                                  ? `se descarga (${antes.size_mb} MB)`
                                  : "se descarga al comparar"}
                            </dd>
                            <dt>Colección</dt>
                            <dd>
                              {antes.collection}
                              {antes.collection !== seleccion.collection
                                ? " · distinta a la escena actual"
                                : ""}
                            </dd>
                          </dl>
                        ) : null}
                        {producto === "cambio" ? (
                          <>
                            <label className="nisar__ancho">
                              Modo
                              <select
                                value={modoCambio}
                                onChange={(evento) => setModoCambio(evento.target.value)}
                              >
                                <option value="comparar">Antes | después + máscara</option>
                                <option value="mascara">Máscara sola</option>
                                <option value="delta">Delta</option>
                                <option value="rgb">RGB</option>
                              </select>
                            </label>
                            <label className="nisar__ancho">
                              Confirmar con Sentinel-2 (NDVI)
                              <select
                                value={verificarS2 ? "si" : "no"}
                                onChange={(evento) =>
                                  setVerificarS2(evento.target.value === "si")
                                }
                              >
                                <option value="si">
                                  Sí · pérdida en rojo, candidata en naranja, parches ≥ 0.5 ha
                                </option>
                                <option value="no">No · solo radar (cambio candidato, sin red)</option>
                              </select>
                            </label>
                            <label className="nisar__ancho">
                              Persistencia temporal
                              <select
                                value={persistencia}
                                onChange={(evento) =>
                                  setPersistencia(evento.target.value)
                                }
                              >
                                <option value="0">No · solo el par de fechas</option>
                                <option value="1">
                                  Sí · tiene que seguir en la fecha siguiente (local)
                                </option>
                                <option value="2">
                                  Sí · dos fechas siguientes (más estricto)
                                </option>
                              </select>
                            </label>
                          </>
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
                        <span>
                          Fechas del track/frame ({fechasDelTrack.length})
                          {cargandoFechas ? " · consultando ASF…" : ""}
                        </span>
                        <button
                          type="button"
                          className="btn"
                          onClick={() =>
                            setFechasSerie(fechasDelTrack.map((escena) => escena.id))
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
                      <div className="nisar__fechas-head">
                        <input
                          type="date"
                          value={fechaNueva}
                          onChange={(evento) => setFechaNueva(evento.target.value)}
                        />
                        <button
                          type="button"
                          className="btn"
                          disabled={!fechaNueva || resolviendo}
                          onClick={() => void agregarFecha()}
                        >
                          {resolviendo ? "Buscando…" : "Buscar y agregar fecha"}
                        </button>
                      </div>
                      {fechasDelTrack.length === 0 ? (
                        <p className="nisar__vacio">
                          No hay fechas para ese track/frame. Agregá una con el
                          calendario: si existe, se descarga al generar la serie.
                        </p>
                      ) : (
                        <ul className="nisar__fechas-lista">
                          {fechasDelTrack.map((escena) => (
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
                                <span>{fechaCorta(escena.start)}</span>
                                <span className="nisar__fechas-peso">
                                  {escena.mpp !== null ? `${escena.mpp} m/px · ` : ""}
                                  {escena.local
                                    ? "local"
                                    : escena.size_mb !== null
                                      ? `${escena.size_mb} MB`
                                      : "por bajar"}
                                </span>
                              </label>
                              {!escena.local && escena.download ? (
                                <button
                                  type="button"
                                  className="btn"
                                  disabled={enMarcha}
                                  onClick={() => void descargarEscena(escena)}
                                >
                                  Descargar
                                </button>
                              ) : null}
                            </li>
                          ))}
                        </ul>
                      )}
                      {fechasSerie.length < 2 ? (
                        <p className="nisar__estado">
                          Marcá al menos 2 fechas: las que no estén en disco se bajan al
                          generar la serie.
                        </p>
                      ) : null}
                      {coleccionesSerie.length > 1 ? (
                        <p className="nisar__estado">
                          Mezclás {coleccionesSerie.slice().sort().join(" con ")}: parte
                          del cambio puede venir del procesamiento, no del terreno.
                        </p>
                      ) : null}
                    </div>
                  ) : null}

                  {(producto === "cambio" || producto === "incendio") &&
                  candidatos.length === 0 ? (
                    <p className="nisar__estado">
                      {cargandoFechas
                        ? "Consultando las fechas del track/frame en ASF…"
                        : "No aparecen otras fechas para este track/frame. Elegí una con el calendario: si existe en ASF se descarga al comparar."}
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
                </>
              ) : esSme2 ? (
                <>
                  <p className="nisar__sub">
                    Humedad del suelo a 200 m (EASE-Grid 2.0). El producto es
                    PROVISIONAL: la calibración sigue en curso. El análisis usa la
                    caja dibujada.
                  </p>
                  <div className="nisar__render-ctrl">
                    <label>
                      Algoritmo
                      <select
                        value={algoritmoSme2}
                        onChange={(evento) => setAlgoritmoSme2(evento.target.value)}
                      >
                        <option value="PMI">PMI - modelo físico (recomendado)</option>
                        <option value="DSG">DSG - desagregación</option>
                        <option value="TSR">TSR - serie temporal</option>
                        <option value="COMPARAR">Comparar (validación)</option>
                      </select>
                    </label>
                    <label>
                      Calidad
                      <select
                        value={soloCalidadSme2 ? "si" : "no"}
                        disabled={algoritmoSme2 === "COMPARAR"}
                        onChange={(evento) =>
                          setSoloCalidadSme2(evento.target.value === "si")
                        }
                      >
                        <option value="no">Todos los píxeles válidos</option>
                        <option value="si">Solo quality flag = 0</option>
                      </select>
                    </label>
                    <label>
                      Tamaño máx.
                      <select value={px} onChange={(evento) => setPx(evento.target.value)}>
                        <option value="1600">1600 px</option>
                        <option value="2400">2400 px</option>
                        <option value="3200">3200 px</option>
                        <option value="4096">4096 px</option>
                      </select>
                    </label>
                  </div>
                  <p className="nisar__estado">
                    SME2 se publica cada ~12 días y no reemplaza al GCOV: es
                    humedad del suelo, no cambio de cobertura.
                  </p>
                  {algoritmoSme2 === "COMPARAR" ? (
                    <p className="nisar__estado">
                      Compara DSG, PMI y TSR en la caja y escribe un informe de
                      validación (cobertura, calidad, bias/RMSE/correlación). No
                      produce una capa calibrada única.
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
                      disabled={!caja || enMarcha || !catalogo?.earthdata_configured}
                      onClick={() => void renderizar()}
                    >
                      {algoritmoSme2 === "COMPARAR"
                        ? "Comparar algoritmos"
                        : "Descargar y renderizar"}
                    </button>
                    {enMarcha ? (
                      <button type="button" className="btn" onClick={() => void cancelarRender()}>
                        Cancelar
                      </button>
                    ) : null}
                  </div>
                </>
              ) : esGunw ? (
                <>
                  <p className="nisar__sub">
                    Interferograma del par: coherencia (0–1), fase envuelta a 20 m
                    y fase desenvuelta a 80 m. La fase es la del producto: no trae
                    correcciones atmosféricas ni ionosféricas.
                  </p>
                  <div className="nisar__render-ctrl">
                    <label>
                      Tamaño máx.
                      <select value={px} onChange={(evento) => setPx(evento.target.value)}>
                        <option value="1600">1600 px</option>
                        <option value="2400">2400 px</option>
                        <option value="3200">3200 px</option>
                        <option value="4096">4096 px</option>
                      </select>
                    </label>
                  </div>
                  <p className="nisar__estado">
                    Par de 12 días, co-pol (HH o VV). El desplazamiento es relativo:
                    para deslizamientos hay que corregir atmósfera/ionósfera y tomar
                    una referencia. 1 franja (2π) ≈ 12.2 cm LOS.
                  </p>
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
                </>
              ) : (
                <p className="nisar__aviso">
                  {seleccion.level} todavía no tiene un producto de análisis en esta
                  app. Podés descargar el .h5 o elegir una escena GCOV/SME2/GUNW.
                </p>
              )}
            </div>
          </div>
        ) : null}
      </aside>
      <aside className="nisar__resultados" aria-label="Resultados de los trabajos">
        <JobsPanel jobInicial={jobNuevo} />
      </aside>
    </section>
  );
}
