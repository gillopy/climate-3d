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
import { CapasAmbientales } from "./CapasAmbientales";
import { CatastroPanel } from "./CatastroPanel";
import { JobsPanel } from "./JobsPanel";
import { FechaUnica, VentanaTemporal } from "./controls/Window";

const CENTRO_PARAGUAY: L.LatLngTuple = [-23.4, -58.4];
const COLOR = "#c084fc";
const COLOR_SEL = "#e9d5ff";
const COLOR_PARAGUAY = "#38bdf8";
//: La caja de selección va en ámbar: no se confunde con las huellas ASF.
const COLOR_CAJA = "#f5a524";
const STORAGE_NISAR = "climate3d:nisar:config";
const FECHAS_VACIAS = new Set<string>();
const PISO_NISAR = "2024-01-01";

interface NisarEstadoGuardado {
  capaBase?: CapaBase;
  etiquetasMapa?: boolean;
  bordes?: boolean;
  nivel?: string;
  desde?: string;
  hasta?: string;
  caja?: Caja | null;
  producto?: string;
  pol?: string;
  modo?: string;
  px?: string;
  colorReal?: boolean;
}

function leerNisarGuardado(): NisarEstadoGuardado {
  try {
    const crudo = window.localStorage.getItem(STORAGE_NISAR);
    if (!crudo) return {};
    const parsed = JSON.parse(crudo) as NisarEstadoGuardado;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

type CapaBase = "satelite" | "terreno" | "mapa";

interface LugarCientifico {
  nombre: string;
  region: string;
  lat: number;
  lon: number;
  km: number;
}

const LUGARES_PARAGUAY: LugarCientifico[] = [
  { nombre: "Asunción · Gran Asunción", region: "Capital / Central", lat: -25.286, lon: -57.635, km: 25 },
  { nombre: "Ciudad del Este · Itaipú", region: "Alto Paraná", lat: -25.509, lon: -54.611, km: 25 },
  { nombre: "Encarnación · Yacyretá", region: "Itapúa", lat: -27.33, lon: -55.866, km: 25 },
  { nombre: "Reserva Mbaracayú", region: "Canindeyú (Bosque Atlántico)", lat: -24.135, lon: -55.435, km: 15 },
  { nombre: "Filadelfia · Chaco Central", region: "Boquerón", lat: -22.34, lon: -60.031, km: 35 },
  { nombre: "Mariscal Estigarribia", region: "Boquerón", lat: -22.028, lon: -60.61, km: 35 },
  { nombre: "Fuerte Olimpo · Pantanal", region: "Alto Paraguay", lat: -21.041, lon: -57.873, km: 35 },
  { nombre: "Bahía Negra · Tres Fronteras", region: "Alto Paraguay", lat: -20.228, lon: -58.167, km: 35 },
  { nombre: "Pilar · Humedales de Ñeembucú", region: "Ñeembucú", lat: -26.868, lon: -58.296, km: 30 },
  { nombre: "Concepción · Río Paraguay", region: "Concepción", lat: -23.406, lon: -57.434, km: 25 },
  { nombre: "Pedro Juan Caballero", region: "Amambay", lat: -22.547, lon: -55.733, km: 25 },
  { nombre: "Salto del Guairá", region: "Canindeyú", lat: -24.062, lon: -54.307, km: 25 },
  { nombre: "Villarrica · Ybytyruzú", region: "Guairá", lat: -25.78, lon: -56.448, km: 20 },
  { nombre: "Coronel Oviedo", region: "Caaguazú", lat: -25.444, lon: -56.44, km: 25 },
  { nombre: "Caacupé · Lago Ypacaraí", region: "Cordillera", lat: -25.32, lon: -57.285, km: 20 },
  { nombre: "Pozo Colorado · Ruta Transchaco", region: "Presidente Hayes", lat: -23.491, lon: -58.793, km: 35 },
  { nombre: "Bañado Sur · Pilcomayo", region: "Presidente Hayes / Boquerón", lat: -23.85, lon: -60.95, km: 35 },
  { nombre: "Cerro León · Defensores del Chaco", region: "Alto Paraguay", lat: -20.42, lon: -60.32, km: 35 },
];

const ESTILO_CAJA: L.PathOptions = {
  color: COLOR_CAJA,
  weight: 2.5,
  opacity: 1,
  fillColor: COLOR_CAJA,
  fillOpacity: 0.14,
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

function cajaAlrededor(lat: number, lon: number, ladoKm: number): Caja {
  const mitadLat = ladoKm / 2 / 110.57;
  const cosLat = Math.max(0.2, Math.cos((lat * Math.PI) / 180));
  const mitadLon = ladoKm / 2 / (111.32 * cosLat);
  return {
    oeste: Number((lon - mitadLon).toFixed(4)),
    sur: Number((lat - mitadLat).toFixed(4)),
    este: Number((lon + mitadLon).toFixed(4)),
    norte: Number((lat + mitadLat).toFixed(4)),
  };
}

function dimensionesCaja(caja: Caja): {
  anchoKm: number;
  altoKm: number;
  areaKm2: number;
  latCentro: number;
  lonCentro: number;
} {
  const latCentro = (caja.sur + caja.norte) / 2;
  const lonCentro = (caja.oeste + caja.este) / 2;
  const anchoKm =
    Math.abs(caja.este - caja.oeste) *
    111.32 *
    Math.cos((latCentro * Math.PI) / 180);
  const altoKm = Math.abs(caja.norte - caja.sur) * 110.57;
  return {
    anchoKm,
    altoKm,
    areaKm2: anchoKm * altoKm,
    latCentro,
    lonCentro,
  };
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
  const capaBaseRef = useRef<L.LayerGroup | null>(null);
  const bordesRef = useRef<L.LayerGroup | null>(null);
  const huellasRef = useRef<L.LayerGroup | null>(null);
  const cajaLayerRef = useRef<L.Rectangle | null>(null);
  const esquinasRef = useRef<L.LayerGroup | null>(null);
  const borradorRef = useRef<L.Rectangle | null>(null);

  const inicialRef = useRef<NisarEstadoGuardado | null>(null);
  if (inicialRef.current === null) {
    inicialRef.current = leerNisarGuardado();
  }
  const inicial = inicialRef.current;

  const [mapaVivo, setMapaVivo] = useState<L.Map | null>(null);
  const [catalogo, setCatalogo] = useState<NisarCatalog | null>(null);
  const [capaBase, setCapaBase] = useState<CapaBase>(inicial.capaBase ?? "satelite");
  const [etiquetasMapa, setEtiquetasMapa] = useState(inicial.etiquetasMapa ?? true);
  const [bordes, setBordes] = useState(inicial.bordes ?? true);
  const [nivel, setNivel] = useState(inicial.nivel ?? "GCOV");
  const [desde, setDesde] = useState(() => inicial.desde ?? hoyISO(29));
  const [hasta, setHasta] = useState(() => inicial.hasta ?? hoyISO());
  const [caja, setCaja] = useState<Caja | null>(() => inicial.caja ?? null);
  const [dibujando, setDibujando] = useState(false);
  // Estado de la capa Catastro: el render de cambio lo usa para sumar las
  // parcelas del SNC a la imagen (NisarView no sabe nada más del catastro).
  const [catastroActivo, setCatastroActivo] = useState(false);
  const [resultado, setResultado] = useState<NisarSearch | null>(null);
  const [seleccion, setSeleccion] = useState<NisarGranule | null>(null);
  const [hoverGranuloId, setHoverGranuloId] = useState<string | null>(null);
  const [imagen, setImagen] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Buscador de ciudades y localidades
  const [ciudadQuery, setCiudadQuery] = useState("");
  const [buscandoCiudad, setBuscandoCiudad] = useState(false);
  const [sugerenciasAbiertas, setSugerenciasAbiertas] = useState(false);
  const [resultadosRemotos, setResultadosRemotos] = useState<LugarCientifico[]>([]);
  const ultimoFinComposicion = useRef<number | null>(null);

  // Render de la caja: descarga del .h5 + recorte de alta calidad.
  const [pol, setPol] = useState(inicial.pol ?? "auto");
  const [modo, setModo] = useState(inicial.modo ?? "gris");
  const [px, setPx] = useState(inicial.px ?? "2400");
  const [trabajo, setTrabajo] = useState<Job | null>(null);
  const [locales, setLocales] = useState<NisarLocalScene[]>([]);
  const [fechasSerie, setFechasSerie] = useState<string[]>([]);
  const [producto, setProducto] = useState(inicial.producto ?? "recorte");
  const [antesId, setAntesId] = useState("");
  // Fecha anterior elegida a mano: puede no venir de la ventana de busqueda.
  const [antesExterno, setAntesExterno] = useState<NisarTimelineScene | null>(null);
  const [timeline, setTimeline] = useState<NisarTimelineScene[]>([]);
  const [cargandoFechas, setCargandoFechas] = useState(false);
  const [fechaNueva, setFechaNueva] = useState(() => hoyISO(12));
  const [resolviendo, setResolviendo] = useState(false);
  const [coordTexto, setCoordTexto] = useState("");
  const [verificarS2, setVerificarS2] = useState(true);
  const [optico, setOptico] = useState("sentinel2");
  // Color real del par: dos PNG (previo/posterior) con la escena óptica más
  // cercana a cada fecha. Apagado por defecto: nadie paga la descarga sin pedirlo.
  const [colorReal, setColorReal] = useState(inicial.colorReal ?? false);
  const [persistencia, setPersistencia] = useState("0");
  const [baseline, setBaseline] = useState("0");
  const [covMax, setCovMax] = useState("0.4");
  const [guardiaHh, setGuardiaHh] = useState("0");
  const [modoCambio, setModoCambio] = useState("comparar");
  const [umbral, setUmbral] = useState("2.5");
  const [detector, setDetector] = useState("radar");
  const [hvMin, setHvMin] = useState("-15.5");
  const [modoGeo, setModoGeo] = useState("db");
  const [hhMax, setHhMax] = useState("-20");
  const [hvMax, setHvMax] = useState("-25");
  const [firms, setFirms] = useState(true);
  const [dias, setDias] = useState("15");
  const [nubes, setNubes] = useState("40");
  const [algoritmoSme2, setAlgoritmoSme2] = useState("PMI");
  const [soloCalidadSme2, setSoloCalidadSme2] = useState(false);
  const [jobNuevo, setJobNuevo] = useState<string | null>(null);
  const [copiado, setCopiado] = useState(false);

  const elegirGranulo = useCallback((granulo: NisarGranule) => {
    setSeleccion(granulo);
    setImagen(imagenInicial(granulo));
    setAntesExterno(null);
    const mapa = mapaRef.current;
    if (mapa && granulo.footprint.length >= 3) {
      const puntos = granulo.footprint.map(
        ([lon, lat]) => [lat, lon] as L.LatLngTuple,
      );
      mapa.fitBounds(L.latLngBounds(puntos), { padding: [28, 28], maxZoom: 11 });
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
            { padding: [36, 36], maxZoom: 11 },
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

  // Mapa: se crea una vez con capas satelitales realistas.
  useEffect(() => {
    const nodo = contenedor.current;
    if (!nodo || mapaRef.current) return;

    const mapa = L.map(nodo, {
      center: CENTRO_PARAGUAY,
      zoom: 6,
      minZoom: 4,
      maxZoom: 17,
      // Canvas en vez de un <path> SVG por geometría: con la capa de catastro
      // encendida hay más de mil polígonos y el árbol SVG congela el hilo.
      preferCanvas: true,
    });
    capaBaseRef.current = L.layerGroup().addTo(mapa);
    bordesRef.current = L.layerGroup();
    huellasRef.current = L.layerGroup().addTo(mapa);
    esquinasRef.current = L.layerGroup().addTo(mapa);
    mapaRef.current = mapa;
    setMapaVivo(mapa);

    getParaguay()
      .then((datos: FeatureCollection) => {
        if (!mapaRef.current || !bordesRef.current) return;
        L.geoJSON(datos, {
          interactive: false,
          style: {
            color: COLOR_PARAGUAY,
            weight: 1.6,
            opacity: 0.85,
            fill: false,
            dashArray: "4 3",
          },
        }).addTo(bordesRef.current);
      })
      .catch(() => undefined);

    return () => {
      mapa.remove();
      mapaRef.current = null;
      setMapaVivo(null);
      capaBaseRef.current = null;
      bordesRef.current = null;
      huellasRef.current = null;
      esquinasRef.current = null;
      cajaLayerRef.current = null;
      borradorRef.current = null;
    };
  }, []);

  // Conmutador de capa base realista (Satélite Esri + etiquetas híbridas, Terreno o Mapa OSM)
  useEffect(() => {
    const grupo = capaBaseRef.current;
    if (!grupo) return;
    grupo.clearLayers();

    if (capaBase === "satelite") {
      L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        {
          maxZoom: 17,
          attribution: "Tiles &copy; Esri, Maxar, Earthstar Geographics",
        },
      ).addTo(grupo);
      if (etiquetasMapa) {
        L.tileLayer(
          "https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
          {
            maxZoom: 17,
            opacity: 0.88,
          },
        ).addTo(grupo);
      }
    } else if (capaBase === "terreno") {
      L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        {
          maxZoom: 17,
          attribution: "Tiles &copy; Esri, USGS, NOAA",
        },
      ).addTo(grupo);
    } else {
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }).addTo(grupo);
    }
  }, [capaBase, etiquetasMapa]);

  // Conmutador del contorno del país: el trazo solo se ve cuando está encendido.
  useEffect(() => {
    const grupo = bordesRef.current;
    const mapa = mapaRef.current;
    if (!grupo || !mapa) return;
    if (bordes) {
      if (!mapa.hasLayer(grupo)) grupo.addTo(mapa);
    } else if (mapa.hasLayer(grupo)) {
      mapa.removeLayer(grupo);
    }
  }, [bordes, mapaVivo]);

  useEffect(() => {
    getNisarCatalog()
      .then(setCatalogo)
      .catch(() => setError("No se pudo leer el catalogo NISAR."));
  }, []);

  // Dibujo del cuadro: mouse abajo, mover, soltar (con recuperacion si suelta fuera del contenedor).
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
    let ultimoLatLng: L.LatLng | null = null;

    const alMover = (evento: L.LeafletMouseEvent) => {
      if (!inicio || !borradorRef.current) return;
      ultimoLatLng = evento.latlng;
      borradorRef.current.setBounds(L.latLngBounds(inicio, evento.latlng));
    };

    const alBajar = (evento: L.LeafletMouseEvent) => {
      inicio = evento.latlng;
      ultimoLatLng = evento.latlng;
      quitarBorrador();
      borradorRef.current = L.rectangle(
        L.latLngBounds(inicio, inicio),
        ESTILO_BORRADOR,
      ).addTo(mapa);
      mapa.on("mousemove", alMover);
    };

    const finalizarTrazo = (puntoFinal: L.LatLng | null) => {
      mapa.off("mousemove", alMover);
      if (!inicio || !puntoFinal) {
        inicio = null;
        quitarBorrador();
        setDibujando(false);
        return;
      }
      const bounds = L.latLngBounds(inicio, puntoFinal);
      inicio = null;
      ultimoLatLng = null;
      quitarBorrador();
      setDibujando(false);
      const nuevaCaja = cajaDeBounds(bounds);
      if (!nuevaCaja) {
        setError(
          "El cuadro dibujado es muy chico (< 1 km). Arrastrá un área más amplia o usá los botones de tamaño (7 km, 25 km, 50 km).",
        );
        return;
      }
      setError(null);
      setCaja(nuevaCaja);
    };

    const alSoltarMapa = (evento: L.LeafletMouseEvent) => {
      if (!inicio) return;
      finalizarTrazo(evento.latlng);
    };

    const alSoltarVentana = () => {
      if (!inicio) return;
      finalizarTrazo(ultimoLatLng);
    };

    const alTeclear = (evento: KeyboardEvent) => {
      if (evento.key === "Escape") setDibujando(false);
    };

    mapa.on("mousedown", alBajar);
    mapa.on("mouseup", alSoltarMapa);
    window.addEventListener("mouseup", alSoltarVentana);
    window.addEventListener("keydown", alTeclear);
    return () => {
      mapa.off("mousedown", alBajar);
      mapa.off("mouseup", alSoltarMapa);
      mapa.off("mousemove", alMover);
      window.removeEventListener("mouseup", alSoltarVentana);
      window.removeEventListener("keydown", alTeclear);
      quitarBorrador();
    };
  }, [dibujando]);

  // La caja vigente y sus tiradores interactivos en las 4 esquinas + centro arrastrable.
  useEffect(() => {
    const mapa = mapaRef.current;
    const capaEsquinas = esquinasRef.current;
    if (!mapa || !capaEsquinas) return;

    if (cajaLayerRef.current) {
      mapa.removeLayer(cajaLayerRef.current);
      cajaLayerRef.current = null;
    }
    capaEsquinas.clearLayers();
    if (!caja) return;

    const bounds = L.latLngBounds(
      [caja.sur, caja.oeste],
      [caja.norte, caja.este],
    );
    const rect = L.rectangle(bounds, ESTILO_CAJA).addTo(mapa);
    cajaLayerRef.current = rect;

    const iconoEsquina = L.divIcon({
      className: "nisar__handle-icon",
      iconSize: [12, 12],
      iconAnchor: [6, 6],
    });

    const esquinas: {
      pos: L.LatLngTuple;
      aplicar: (lat: number, lng: number) => Caja | null;
    }[] = [
      {
        pos: [caja.norte, caja.oeste],
        aplicar: (lat, lng) =>
          cajaDeBounds(L.latLngBounds([caja.sur, lng], [lat, caja.este])),
      },
      {
        pos: [caja.norte, caja.este],
        aplicar: (lat, lng) =>
          cajaDeBounds(L.latLngBounds([caja.sur, caja.oeste], [lat, lng])),
      },
      {
        pos: [caja.sur, caja.oeste],
        aplicar: (lat, lng) =>
          cajaDeBounds(L.latLngBounds([lat, lng], [caja.norte, caja.este])),
      },
      {
        pos: [caja.sur, caja.este],
        aplicar: (lat, lng) =>
          cajaDeBounds(L.latLngBounds([lat, caja.oeste], [caja.norte, lng])),
      },
    ];

    for (const esquina of esquinas) {
      const marcador = L.marker(esquina.pos, {
        icon: iconoEsquina,
        draggable: true,
        title: "Arrastrá la esquina para ajustar la caja ROI",
      });
      marcador.on("drag", (evento) => {
        const pos = (evento.target as L.Marker).getLatLng();
        const tentativa = esquina.aplicar(pos.lat, pos.lng);
        if (tentativa && cajaLayerRef.current) {
          cajaLayerRef.current.setBounds([
            [tentativa.sur, tentativa.oeste],
            [tentativa.norte, tentativa.este],
          ]);
        }
      });
      marcador.on("dragend", (evento) => {
        const pos = (evento.target as L.Marker).getLatLng();
        const nueva = esquina.aplicar(pos.lat, pos.lng);
        if (nueva) {
          setCaja({
            oeste: Number(nueva.oeste.toFixed(4)),
            sur: Number(nueva.sur.toFixed(4)),
            este: Number(nueva.este.toFixed(4)),
            norte: Number(nueva.norte.toFixed(4)),
          });
        }
      });
      marcador.addTo(capaEsquinas);
    }
  }, [caja]);

  useEffect(() => {
    try {
      const estado: NisarEstadoGuardado = {
        capaBase,
        etiquetasMapa,
        bordes,
        nivel,
        desde,
        hasta,
        caja,
        producto,
        pol,
        modo,
        px,
        colorReal,
      };
      window.localStorage.setItem(STORAGE_NISAR, JSON.stringify(estado));
    } catch {
      // Ignorado si localStorage no está disponible.
    }
  }, [capaBase, etiquetasMapa, bordes, nivel, desde, hasta, caja, producto, pol, modo, px, colorReal]);

  // Sincroniza el campo de texto cuando la caja cambia desde el mapa, buscador o presets.
  useEffect(() => {
    if (!caja) return;
    setCoordTexto(
      `${caja.oeste.toFixed(4)},${caja.sur.toFixed(4)},${caja.este.toFixed(4)},${caja.norte.toFixed(4)}`,
    );
  }, [caja]);

  async function copiarCoordenadas() {
    if (!caja) return;
    const texto = `${caja.oeste.toFixed(4)},${caja.sur.toFixed(4)},${caja.este.toFixed(4)},${caja.norte.toFixed(4)}`;
    try {
      await navigator.clipboard.writeText(texto);
      setCopiado(true);
      window.setTimeout(() => setCopiado(false), 1800);
    } catch {
      setCoordTexto(texto);
      setCopiado(true);
      window.setTimeout(() => setCopiado(false), 1800);
    }
  }

  // Toda caja nueva (o cambio de filtros) vuelve a consultar ASF.
  useEffect(() => {
    if (caja) void buscar(caja);
  }, [caja, buscar]);

  // Huellas de los granulos encontrados (interactivas salvo mientras se dibuja una caja).
  useEffect(() => {
    const capa = huellasRef.current;
    if (!capa) return;
    capa.clearLayers();
    if (!resultado) return;

    for (const granulo of resultado.granules) {
      if (granulo.footprint.length < 3) continue;
      const activo = seleccion?.id === granulo.id;
      const resaltado = hoverGranuloId === granulo.id;
      const puntos = granulo.footprint.map(
        ([lon, lat]) => [lat, lon] as L.LatLngTuple,
      );
      const poligono = L.polygon(puntos, {
        interactive: !dibujando,
        color: activo ? COLOR_SEL : resaltado ? "#f0abfc" : COLOR,
        weight: activo ? 2.6 : resaltado ? 2 : 1.3,
        opacity: activo || resaltado ? 1 : 0.85,
        fillColor: activo ? COLOR_SEL : COLOR,
        fillOpacity: activo ? 0.22 : resaltado ? 0.14 : 0.06,
      });
      if (!dibujando) {
        poligono.on("click", () => elegirGranulo(granulo));
      }
      const trackTxt =
        granulo.path !== null && granulo.frame !== null
          ? `T${granulo.path}/F${granulo.frame}`
          : "SAR";
      poligono.bindTooltip(
        `${granulo.level} · ${trackTxt} · ${fechaCorta(granulo.start)}${
          granulo.local ? " · EN DISCO" : ""
        }`,
        { sticky: true },
      );
      poligono.addTo(capa);
    }
  }, [resultado, seleccion, hoverGranuloId, dibujando, elegirGranulo]);

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
  const candidatosBase = fechasDelTrack
    .filter(
      (escena) => escena.id !== seleccion?.id && escena.start < (seleccion?.start ?? ""),
    )
    .sort((a, b) => b.start.localeCompare(a.start));
  // Si se resolvió una fecha externa que no estaba en `candidatosBase`, se incluye
  // en la lista para que el `<select>` siempre tenga su `<option>` sincronizado.
  const candidatos =
    antesExterno && !candidatosBase.some((c) => c.id === antesExterno.id)
      ? [antesExterno, ...candidatosBase]
      : candidatosBase;
  const antes =
    antesExterno ?? candidatos.find((escena) => escena.id === antesId) ?? null;

  const infoCaja = caja ? dimensionesCaja(caja) : null;
  const mppEfectivo = (() => {
    if (!infoCaja) return null;
    const pedido = (Math.max(infoCaja.anchoKm, infoCaja.altoKm) * 1000) / Number(px);
    return seleccion?.mpp != null ? Math.max(pedido, seleccion.mpp) : pedido;
  })();
  const mppNativo =
    mppEfectivo !== null &&
    seleccion?.mpp != null &&
    mppEfectivo <= seleccion.mpp;
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
    const lista = candidatosBase;
    if (lista.length === 0) {
      setAntesId("");
      return;
    }
    if (lista.some((escena) => escena.id === antesId)) return;
    setAntesId(lista[0].id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seleccion, antesId, antesExterno, timeline.length, locales.length, resultado]);

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
    getNisarTimeline(track, frame, "", "GCOV")
      .then((datos) => {
        if (vigente) setTimeline(datos.scenes);
      })
      .catch(() => {
        if (vigente) setTimeline([]);
      })
      .finally(() => {
        if (vigente) setCargandoFechas(false);
      });
    return () => {
      vigente = false;
    };
  }, [necesitaFechas, track, frame, coleccion]);

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

  const lugaresCoincidentes = LUGARES_PARAGUAY.filter((lugar) => {
    const q = ciudadQuery.trim().toLowerCase();
    if (!q) return true;
    return `${lugar.nombre} ${lugar.region}`.toLowerCase().includes(q);
  }).slice(0, 7);

  function irALugar(lugar: LugarCientifico, armarCaja = true) {
    setCiudadQuery(lugar.nombre);
    setSugerenciasAbiertas(false);
    setResultadosRemotos([]);
    setError(null);
    const nueva = cajaAlrededor(lugar.lat, lugar.lon, lugar.km);
    if (armarCaja) {
      setDibujando(false);
      setCaja(nueva);
    } else if (mapaRef.current) {
      mapaRef.current.flyTo([lugar.lat, lugar.lon], 10, { duration: 0.7 });
    }
  }

  async function buscarCiudadRemota() {
    const consulta = ciudadQuery.trim();
    if (!consulta) return;
    // Si coincide exacto o como único resultado local, salta directo.
    const local = LUGARES_PARAGUAY.find((l) =>
      `${l.nombre} ${l.region}`.toLowerCase().includes(consulta.toLowerCase()),
    );
    if (local && lugaresCoincidentes.length === 1) {
      irALugar(local, true);
      return;
    }
    setBuscandoCiudad(true);
    setError(null);
    try {
      const url = new URL("https://nominatim.openstreetmap.org/search");
      url.searchParams.set("q", consulta);
      url.searchParams.set("format", "jsonv2");
      url.searchParams.set("limit", "5");
      url.searchParams.set("accept-language", "es");
      const res = await fetch(url.toString());
      if (!res.ok) throw new Error("No se pudo consultar el geocodificador.");
      const items = (await res.json()) as {
        display_name: string;
        lat: string;
        lon: string;
      }[];
      const mapeados: LugarCientifico[] = items
        .map((it) => {
          const partes = it.display_name.split(",").map((s) => s.trim());
          return {
            nombre: partes.slice(0, 2).join(" · ") || it.display_name,
            region: partes.slice(2, 4).join(", ") || "Geocodificador",
            lat: Number(it.lat),
            lon: Number(it.lon),
            km: 25,
          };
        })
        .filter((it) => Number.isFinite(it.lat) && Number.isFinite(it.lon));

      if (mapeados.length === 0) {
        if (local) {
          irALugar(local, true);
        } else {
          setError(`No encontramos la localidad «${consulta}».`);
        }
        return;
      }
      setResultadosRemotos(mapeados);
      setSugerenciasAbiertas(true);
      irALugar(mapeados[0], true);
    } catch {
      if (local) {
        irALugar(local, true);
      } else {
        setError("Sin conexión al buscador remoto; elegí una localidad de la lista.");
      }
    } finally {
      setBuscandoCiudad(false);
    }
  }

  function redimensionarCajaKm(ladoKm: number) {
    const mapa = mapaRef.current;
    const centroLat = infoCaja
      ? infoCaja.latCentro
      : (mapa?.getCenter().lat ?? CENTRO_PARAGUAY[0]);
    const centroLon = infoCaja
      ? infoCaja.lonCentro
      : (mapa?.getCenter().lng ?? CENTRO_PARAGUAY[1]);
    setDibujando(false);
    setError(null);
    setCaja(cajaAlrededor(centroLat, centroLon, ladoKm));
  }

  async function renderizar() {
    if (!seleccion || !caja) return;
    const nivelEscena = seleccion.level;
    if (nivelEscena !== "GCOV" && nivelEscena !== "SME2" && nivelEscena !== "GUNW") {
      setError(
        `La escena es ${nivelEscena}. Los productos disponibles usan GCOV, SME2 o GUNW; ` +
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
        nivelEscena === "SME2" ? "sme2" : nivelEscena === "GUNW" ? "gunw" : producto,
      nivel: nivelEscena,
      granulo: seleccion.id,
      url: seleccion.download,
      coleccion: seleccion.collection,
      bbox: `${caja.oeste},${caja.sur},${caja.este},${caja.norte}`,
      px: Number(px),
    };
    if (nivelEscena === "SME2") {
      params.algoritmo = algoritmoSme2;
      params.solo_calidad = soloCalidadSme2;
    } else if (nivelEscena === "GUNW") {
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
      if (antes.download) params.antes_url = antes.download;
      params.umbral = Number(umbral);
      params.hv_min = Number(hvMin);
      if (producto === "cambio") {
        params.modo_cambio = modoCambio;
        params.verificar_s2 = verificarS2;
        params.optico = optico;
        // Check independiente del NDVI: pide dos PNG de color real
        // (escena más cercana a cada fecha), sin delta.
        if (colorReal) params.color_real = true;
        params.confirmar_temporal = Number(persistencia);
        params.baseline = Number(baseline);
        if (Number(baseline) >= 2) params.cov_max = Number(covMax);
        params.guardia_hh = Number(guardiaHh);
        params.detector = detector;
        params.mmu_ha = detector === "ndvi" ? 0.1 : 0.5;
        // La capa de catastro del mapa manda sobre el render: si está activa, el
        // producto suma los límites y el número de cada parcela a la imagen.
        if (catastroActivo) params.catastro = true;
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
        setAntesId(entrada.id);
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
    setHoverGranuloId(null);
    setImagen(null);
    setDibujando(false);
    setError(null);
    setTrabajo(null);
    setProducto("recorte");
    setPol("auto");
    setModo("gris");
    setAntesId("");
    setAntesExterno(null);
    setTimeline([]);
    setLocales([]);
    setFechasSerie([]);
    setFechaNueva(hoyISO(12));
    setCoordTexto("");
    try {
      window.localStorage.removeItem(STORAGE_NISAR);
    } catch {
      // Ignorado.
    }
  }

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
    <section className="nisar" data-group="radar" aria-label="Visor NISAR">
      <div className="nisar__mapa">
        <div ref={contenedor} className="nisar__leaflet" />

        {/* Buscador de ciudades y barra de capa base realista */}
        <div className="nisar__topbar-mapa">
          <search className="nisar__buscador" aria-label="Buscar ciudad o reserva">
            <div className="nisar__buscador-box">
              <svg
                width="13"
                height="13"
                viewBox="0 0 16 16"
                fill="none"
                aria-hidden="true"
              >
                <circle cx="7" cy="7" r="4.4" stroke="currentColor" strokeWidth="1.3" />
                <path d="m10.4 10.4 3 3" stroke="currentColor" strokeWidth="1.3" />
              </svg>
              <input
                type="search"
                value={ciudadQuery}
                placeholder="Buscar ciudad, Chaco, Mbaracayú, Itaipú…"
                aria-label="Buscar ciudad o sitio en el mapa"
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="none"
                spellCheck={false}
                onFocus={() => setSugerenciasAbiertas(true)}
                onChange={(evento) => {
                  setCiudadQuery(evento.target.value);
                  setSugerenciasAbiertas(true);
                }}
                onCompositionEnd={(evento) => {
                  ultimoFinComposicion.current = evento.timeStamp;
                }}
                onKeyDown={(evento) => {
                  if (evento.key === "Enter") {
                    evento.preventDefault();
                    if (
                      evento.nativeEvent.isComposing ||
                      (ultimoFinComposicion.current !== null &&
                        Math.abs(evento.timeStamp - ultimoFinComposicion.current) < 50)
                    ) {
                      return;
                    }
                    void buscarCiudadRemota();
                  } else if (evento.key === "Escape") {
                    setSugerenciasAbiertas(false);
                  }
                }}
              />
              {ciudadQuery ? (
                <button
                  type="button"
                  className="nisar__buscador-clear"
                  aria-label="Limpiar búsqueda de ciudad"
                  onClick={() => {
                    setCiudadQuery("");
                    setResultadosRemotos([]);
                  }}
                >
                  ×
                </button>
              ) : null}
              <button
                type="button"
                className="btn nisar__buscador-ir"
                disabled={buscandoCiudad || !ciudadQuery.trim()}
                onClick={() => void buscarCiudadRemota()}
              >
                {buscandoCiudad ? "…" : "Ir + ROI"}
              </button>
            </div>

            {sugerenciasAbiertas &&
            (lugaresCoincidentes.length > 0 || resultadosRemotos.length > 0) ? (
              <ul className="nisar__sugerencias" role="listbox" aria-label="Sitios sugeridos">
                {resultadosRemotos.map((lugar, i) => (
                  <li key={`rem-${i}`}>
                    <button
                      type="button"
                      className="nisar__sugerencia"
                      onClick={() => irALugar(lugar, true)}
                    >
                      <span className="nisar__sugerencia-nombre">{lugar.nombre}</span>
                      <span className="nisar__sugerencia-meta">
                        {lugar.region} · caja {lugar.km} km
                      </span>
                    </button>
                  </li>
                ))}
                {lugaresCoincidentes.map((lugar) => (
                  <li key={lugar.nombre}>
                    <button
                      type="button"
                      className="nisar__sugerencia"
                      onClick={() => irALugar(lugar, true)}
                    >
                      <span className="nisar__sugerencia-nombre">{lugar.nombre}</span>
                      <span className="nisar__sugerencia-meta">
                        {lugar.region} · ROI {lugar.km} km
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
          </search>

          <div className="nisar__capas" role="group" aria-label="Mapa base">
            <button
              type="button"
              className={`nisar__capa-btn${capaBase === "satelite" ? " nisar__capa-btn--on" : ""}`}
              aria-pressed={capaBase === "satelite"}
              onClick={() => setCapaBase("satelite")}
            >
              Satélite
            </button>
            <button
              type="button"
              className={`nisar__capa-btn${capaBase === "terreno" ? " nisar__capa-btn--on" : ""}`}
              aria-pressed={capaBase === "terreno"}
              onClick={() => setCapaBase("terreno")}
            >
              Terreno
            </button>
            <button
              type="button"
              className={`nisar__capa-btn${capaBase === "mapa" ? " nisar__capa-btn--on" : ""}`}
              aria-pressed={capaBase === "mapa"}
              onClick={() => setCapaBase("mapa")}
            >
              OSM
            </button>
            {capaBase === "satelite" ? (
              <button
                type="button"
                className={`nisar__capa-btn${etiquetasMapa ? " nisar__capa-btn--on" : ""}`}
                aria-pressed={etiquetasMapa}
                title="Mostrar u ocultar nombres de ciudades y límites sobre el satélite"
                onClick={() => setEtiquetasMapa((v) => !v)}
              >
                Nombres
              </button>
            ) : null}
            <CapasAmbientales mapa={mapaVivo} />
            <CatastroPanel
              mapa={mapaVivo}
              caja={caja}
              alCambiarActivo={setCatastroActivo}
            />
          </div>
        </div>

        {/* Herramientas interactivas de la caja ROI */}
        <div className="nisar__herramientas">
          <div className="nisar__roi-group">
            <button
              type="button"
              className={`nisar__tool${dibujando ? " nisar__tool--on" : ""}`}
              aria-pressed={dibujando}
              title="Cuadro: arrastrá sobre el mapa para dibujar un rectángulo"
              onClick={() => {
                setSugerenciasAbiertas(false);
                setDibujando((previo) => !previo);
              }}
            >
              <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <rect
                  x="2.5"
                  y="4"
                  width="11"
                  height="8"
                  rx="1"
                  stroke="currentColor"
                  strokeWidth="1.4"
                />
              </svg>
              {dibujando ? "Trazando…" : "Trazar cuadro"}
            </button>

            <div className="nisar__presets" role="group" aria-label="Tamaños rápidos de caja ROI">
              <span className="nisar__presets-lbl">Escala</span>
              {[7, 15, 25, 50].map((km) => (
                <button
                  key={km}
                  type="button"
                  className="nisar__preset-btn"
                  title={`Crear o ajustar caja de ${km} × ${km} km en el centro actual`}
                  onClick={() => redimensionarCajaKm(km)}
                >
                  {km} km
                </button>
              ))}
            </div>

            <button
              type="button"
              className={`nisar__tool${bordes ? " nisar__tool--on" : ""}`}
              aria-pressed={bordes}
              title="Mostrar u ocultar el contorno del país"
              onClick={() => setBordes((previo) => !previo)}
            >
              <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <path
                  d="M2.6 8.2 5.5 3.4l3.6.9 3.1-1.3 1.2 3.4-1.9 2.6.5 3.3-3 .8-2.4-2.1-3.9-.8Z"
                  stroke="currentColor"
                  strokeWidth="1.3"
                  strokeLinejoin="round"
                  strokeDasharray="2.4 1.6"
                />
              </svg>
              {bordes ? "Bordes" : "Sin bordes"}
            </button>
          </div>

          <div className="nisar__coords">
            <span className="nisar__coords-label">BBOX</span>
            <input
              type="text"
              value={coordTexto}
              aria-label="Caja por coordenadas: oeste, sur, este, norte"
              placeholder="-61.1600,-21.0700,-60.8300,-20.7400"
              title="Formato: oeste,sur,este,norte (grados). Podés pegar o editar y presionar Enter."
              onChange={(evento) => setCoordTexto(evento.target.value)}
              onKeyDown={(evento) => {
                if (evento.key === "Enter") aplicarCoordenadas();
              }}
            />
            <button
              type="button"
              className="nisar__box-btn"
              disabled={!coordTexto.trim()}
              onClick={aplicarCoordenadas}
            >
              Aplicar
            </button>
            <button
              type="button"
              className={`nisar__box-btn${copiado ? " nisar__box-btn--copied" : ""}`}
              disabled={!caja}
              title="Copiar coordenadas oeste,sur,este,norte al portapapeles"
              onClick={() => void copiarCoordenadas()}
            >
              {copiado ? "Copiado" : "Copiar"}
            </button>
          </div>

          <div className="nisar__roi-status">
            <span
              className="nisar__coord"
              title="Dimensiones del cuadro ROI seleccionado"
            >
              <i className="nisar__coord-dot" aria-hidden="true" />
              {caja && infoCaja
                ? `${infoCaja.anchoKm.toFixed(1)} × ${infoCaja.altoKm.toFixed(1)} km`
                : "Sin cuadro"}
            </span>
            <button
              type="button"
              className="nisar__box-btn nisar__box-btn--ghost"
              onClick={limpiar}
            >
              Limpiar
            </button>
          </div>
        </div>
      </div>

      <aside className="nisar__panel" aria-label="Escenas NISAR">
        <header className="nisar__head">
          <h2 className="nisar__title">NISAR · radar de apertura sintética</h2>
          <p className="nisar__sub">
            Elegí una caja sobre Paraguay y ASF devuelve las escenas. Las imágenes
            browse son públicas; los .h5 se descargan con Earthdata.
          </p>
        </header>

        <div className="nisar__filtros">
          <label className="nisar__ancho">
            Nivel del producto SAR
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
          <div className="nisar__ancho nisar__ventana-fecha">
            <span className="nisar__lbl">Ventana temporal (UTC)</span>
            <VentanaTemporal
              value={{ start: desde, end: hasta }}
              disponibles={FECHAS_VACIAS}
              piso={PISO_NISAR}
              onChange={(rango) => {
                setDesde(rango.start);
                setHasta(rango.end);
              }}
            />
          </div>
          <button
            type="button"
            className={`btn btn--primary nisar__ancho${
              caja ? "" : " nisar__btn-espera"
            }`}
            disabled={!caja || cargando}
            onClick={() => caja && void buscar(caja)}
          >
            {cargando ? "Consultando ASF…" : caja ? "Buscar escenas SAR" : "Elegí o buscá una caja ROI"}
          </button>
        </div>

        {error ? (
          <p className="nisar__aviso" role="alert">
            {error}
          </p>
        ) : null}

        <p className="nisar__estado" aria-live="polite">
          {cargando
            ? "Consultando catálogo ASF…"
            : resultado
              ? `${resultado.total} escena(s) encontradas · mostrando ${resultado.returned}`
              : dibujando
                ? "Arrastrá sobre el mapa satelital para trazar la caja ROI."
                : "Buscá una ciudad arriba o dibujá una caja sobre el mapa."}
        </p>

        <ul className="nisar__lista">
          {(resultado?.granules ?? []).map((granulo) => (
            <li key={granulo.id}>
              <button
                type="button"
                className="nisar__item"
                aria-current={seleccion?.id === granulo.id ? "true" : undefined}
                onMouseEnter={() => setHoverGranuloId(granulo.id)}
                onMouseLeave={() => setHoverGranuloId(null)}
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
                    {granulo.direction === "ASCENDING" ? "▲ ascendente" : "▼ descendente"}
                    {granulo.path !== null ? ` · T${granulo.path}` : ""}
                    {granulo.frame !== null ? `/F${granulo.frame}` : ""}
                    {granulo.mpp !== null ? ` · ${granulo.mpp} m/px` : ""}
                    {granulo.size_mb !== null ? ` · ${granulo.size_mb} MB` : ""}
                  </span>
                  <span className="nisar__chips">
                    {granulo.local ? (
                      <span className="nisar__chip nisar__chip--local">en disco</span>
                    ) : null}
                    <span className="nisar__chip nisar__chip--level">{granulo.level}</span>
                    {granulo.polarization.map((polItem) => (
                      <span className="nisar__chip" key={polItem}>
                        {polItem}
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
            <div className="nisar__detalle-head">
              <h3>Escena activa</h3>
              <span className="dataset-badge" data-group="radar">
                <span className="dataset-badge__dot" aria-hidden="true" />
                {seleccion.level} · T{seleccion.path ?? "–"}/F{seleccion.frame ?? "–"}
              </span>
            </div>
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
                  : "Descargar a almacenamiento local"}
              </button>
            </div>

            <div className="nisar__render">
              <h3>Flujo de parametrización SAR</h3>
              {esGcov ? (
                <>
                  <p className="nisar__sub">
                    {producto === "cambio"
                      ? "Compara HV entre esta fecha y otra del mismo track/frame. Con Sentinel-2 activo, el rojo es solo bosque cuyo NDVI también cayó (parches ≥ 0.5 ha). Con Catastro activo, el mapa dibuja los límites de las parcelas del SNC y la pérdida de cada una."
                      : producto === "rvi"
                        ? "Índice de vegetación radar (HH/HV) de esta fecha."
                        : producto === "serie"
                          ? "Usa todas las fechas locales del mismo track/frame/colección (mínimo 2). Genera serie, mediana y CUSUM."
                          : producto === "geotiff"
                            ? "Exporta la caja como GeoTIFF en el EPSG de la escena."
                            : producto === "agua"
                              ? "Máscara de agua abierta: HH y HV bajos. Reporta hectáreas y porcentaje."
                              : producto === "incendio"
                                ? "Cicatriz por caída de HV entre dos fechas, con focos FIRMS opcionales."
                                : producto === "fusion"
                                  ? "Compone Sentinel-2 L2A (NDVI sin nubes) sobre la caja y la cruza con HV. Clasificación rule-based, no un modelo entrenado."
                                  : "Descarga la escena .h5 al almacenamiento local y recorta esta caja."}
                    {seleccion.size_mb !== null
                      ? ` Pesa ~${seleccion.size_mb} MB.`
                      : ""}
                  </p>

                  {/* Producto y Escala de Salida */}
                  <div className="nisar__stage">
                    <div className="nisar__stage-head">
                      <span className="nisar__stage-title">Producto & resolución</span>
                    </div>
                    <div className="nisar__render-ctrl">
                      <label className="nisar__ancho">
                        Producto analítico
                        <select
                          value={producto}
                          disabled={!esGcov}
                          onChange={(evento) => setProducto(evento.target.value)}
                        >
                          <optgroup label="Visualización & GIS">
                            <option value="recorte">Recorte (dB / color)</option>
                            <option value="rvi">RVI (índice de vegetación)</option>
                            <option value="geotiff">GeoTIFF (exportación GIS)</option>
                          </optgroup>
                          <optgroup label="Detección de cambio">
                            <option value="cambio">Cambio de cobertura (deforestación)</option>
                            <option value="serie">Serie temporal + CUSUM</option>
                            <option value="incendio">Incendio (cicatriz + FIRMS)</option>
                          </optgroup>
                          <optgroup label="Hidrología & Fusión">
                            <option value="agua">Agua / inundación</option>
                            <option value="fusion">Fusión óptica (Sentinel-2)</option>
                          </optgroup>
                        </select>
                      </label>

                      <label className="nisar__ancho">
                        Tamaño máx. de salida
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
                        {mppEfectivo !== null ? (
                          <small>
                            ≈ {Math.round(mppEfectivo)} m/px efectivos
                            {mppNativo ? " · resolución nativa" : ""}
                          </small>
                        ) : null}
                      </label>
                    </div>
                  </div>

                  {/* Polarización / Umbrales radiométricos */}
                  {producto === "recorte" ||
                  producto === "geotiff" ||
                  producto === "agua" ||
                  producto === "fusion" ||
                  producto === "cambio" ||
                  producto === "incendio" ||
                  producto === "serie" ? (
                    <div className="nisar__stage">
                      <div className="nisar__stage-head">
                        <span className="nisar__stage-title">
                          {producto === "recorte" || producto === "geotiff"
                            ? "Polarización & radiometría"
                            : producto === "fusion"
                              ? "Ventana óptica Sentinel-2"
                              : "Umbrales backscatter (dB)"}
                        </span>
                      </div>
                      <div className="nisar__render-ctrl">
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
                              Escala
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

                        {producto === "cambio" ||
                        producto === "incendio" ||
                        producto === "serie" ? (
                          <>
                            <label>
                              Umbral caída (dB)
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
                              HV mín. bosque (dB)
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
                    </div>
                  ) : null}

                  {/* Referencia temporal & Corroboración óptica */}
                  {producto === "cambio" || producto === "incendio" ? (
                    <div className="nisar__stage">
                      <div className="nisar__stage-head">
                        <span className="nisar__stage-title">
                          Par temporal & verificación
                        </span>
                      </div>
                      <div className="nisar__render-ctrl">
                        <label className="nisar__ancho">
                          Fecha anterior (mismo track/frame)
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
                                {escena.mpp !== null ? ` · ${escena.mpp} m/px` : ""}
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
                              Detector primario
                              <select
                                value={detector}
                                onChange={(evento) => {
                                  setDetector(evento.target.value);
                                  if (evento.target.value === "ndvi") {
                                    setVerificarS2(true);
                                    setUmbral("4");
                                  } else {
                                    setUmbral("2.5");
                                  }
                                }}
                              >
                                <option value="radar">
                                  Radar · la caída de HV detecta (bosque seco,
                                  desmontes grandes o rebrotados)
                                </option>
                                <option value="ndvi">
                                  NDVI · la caída óptica detecta, el radar corrobora
                                  (desmonte fresco sub-hectárea en dosel denso)
                                </option>
                              </select>
                            </label>
                            <label className="nisar__ancho">
                              Modo de salida
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
                              Confirmar con óptico (NDVI)
                              <select
                                value={verificarS2 ? "si" : "no"}
                                onChange={(evento) =>
                                  setVerificarS2(evento.target.value === "si")
                                }
                              >
                                <option value="si">
                                  Sí · pérdida en rojo, candidata en naranja, parches ≥{" "}
                                  {detector === "ndvi" ? "0.1" : "0.5"} ha
                                </option>
                                <option value="no">No · solo radar (cambio candidato, sin red)</option>
                              </select>
                            </label>
                            <label className="nisar__ancho">
                              Fuente óptica
                              <select
                                value={optico}
                                onChange={(evento) => setOptico(evento.target.value)}
                                disabled={!verificarS2 && !colorReal}
                              >
                                <option value="sentinel2">Sentinel-2 L2A</option>
                                <option value="hls">HLS L30/S30 (Landsat 8/9 + Sentinel-2)</option>
                                <option value="auto">Auto: HLS y fallback Sentinel-2</option>
                              </select>
                            </label>
                            <label className="nisar__ancho nisar__check">
                              <input
                                type="checkbox"
                                checked={colorReal}
                                onChange={(evento) => setColorReal(evento.target.checked)}
                              />
                              <span>
                                Color real (antes/después) · escena más cercana a
                                cada fecha, dos imágenes y ninguna delta
                              </span>
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
                            <label className="nisar__ancho">
                              Baseline temporal
                              <select
                                value={baseline}
                                onChange={(evento) => setBaseline(evento.target.value)}
                              >
                                <option value="0">No · medir contra la fecha anterior sola</option>
                                <option value="3">Sí · mediana de 3 fechas (más estable)</option>
                                <option value="4">Sí · mediana de 4 fechas</option>
                                <option value="5">Sí · mediana de 5 fechas</option>
                              </select>
                            </label>
                            <label>
                              CoV máx.
                              <input
                                type="number"
                                min="0"
                                max="2"
                                step="0.05"
                                value={covMax}
                                onChange={(evento) => setCovMax(evento.target.value)}
                                disabled={Number(baseline) < 2}
                              />
                            </label>
                            <label>
                              Guardia HH (dB)
                              <input
                                type="number"
                                min="0"
                                max="10"
                                step="0.5"
                                value={guardiaHh}
                                onChange={(evento) => setGuardiaHh(evento.target.value)}
                              />
                            </label>
                          </>
                        ) : null}

                        {producto === "incendio" ? (
                          <label className="nisar__ancho">
                            Focos térmicos FIRMS
                            <select
                              value={firms ? "si" : "no"}
                              onChange={(evento) => setFirms(evento.target.value === "si")}
                            >
                              <option value="si">Sí · superponer focos VIIRS/MODIS</option>
                              <option value="no">No · solo cicatriz radar</option>
                            </select>
                          </label>
                        ) : null}
                      </div>
                    </div>
                  ) : null}

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
                      <div className="nisar__fechas-add">
                        <FechaUnica
                          value={fechaNueva}
                          disponibles={FECHAS_VACIAS}
                          piso={PISO_NISAR}
                          disabled={resolviendo}
                          onChange={(iso) => setFechaNueva(iso)}
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
                    <div className="nisar__fechas">
                      <p className="nisar__estado">
                        {cargandoFechas
                          ? "Consultando las fechas del track/frame en ASF…"
                          : "No aparecen otras fechas para este track/frame. Elegí una con el calendario: si existe en ASF se descarga al comparar."}
                      </p>
                      <div className="nisar__fechas-add">
                        <FechaUnica
                          value={fechaNueva}
                          disponibles={FECHAS_VACIAS}
                          piso={PISO_NISAR}
                          disabled={resolviendo}
                          onChange={(iso) => setFechaNueva(iso)}
                        />
                        <button
                          type="button"
                          className="btn"
                          disabled={!fechaNueva || resolviendo}
                          onClick={() => void agregarFecha()}
                        >
                          {resolviendo ? "Buscando…" : "Resolver fecha en ASF"}
                        </button>
                      </div>
                    </div>
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
                  <div className="nisar__stage">
                    <div className="nisar__stage-head">
                      <span className="nisar__stage-title">Algoritmo & control de calidad</span>
                    </div>
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
                  <div className="nisar__stage">
                    <div className="nisar__stage-head">
                      <span className="nisar__stage-title">Escala interferométrica</span>
                    </div>
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
