import type { FeatureCollection } from "geojson";

import { leer } from "./api";

/** Caja geografica en el orden que usa ASF: oeste, sur, este, norte. */
export interface Caja {
  oeste: number;
  sur: number;
  este: number;
  norte: number;
}

export interface NivelNisar {
  value: string;
  label: string;
  detail: string;
}

export interface NisarCatalog {
  levels: NivelNisar[];
  default_bbox: number[];
  default_days: number;
  earthdata_configured: boolean;
  data_root: string;
  nisar_root: string;
}

export interface NisarImage {
  label: string;
  url: string;
}

export interface NisarGranule {
  id: string;
  level: string;
  start: string;
  stop: string;
  direction: string;
  path: number | null;
  frame: number | null;
  polarization: string[];
  collection: string;
  size_mb: number | null;
  /** Anillo lon/lat del poligono del granulo. */
  footprint: number[][];
  thumbnail: string | null;
  images: NisarImage[];
  download: string;
  asf_url: string;
  /** El .h5 ya esta en disco: renderizar no lo vuelve a bajar. */
  local: boolean;
}

export interface NisarSearch {
  bbox: number[];
  start: string;
  end: string;
  level: string;
  polarization: string | null;
  total: number;
  returned: number;
  granules: NisarGranule[];
  notes: string[];
}

export interface NisarLocalScene {
  id: string;
  date: string;
  size_mb: number;
}

export interface NisarLocalScenes {
  track: number;
  frame: number;
  collection: string;
  total: number;
  scenes: NisarLocalScene[];
}

/** Una fecha del track/frame: viene de ASF o del disco. */
export interface NisarTimelineScene {
  id: string;
  date: string;
  start: string;
  collection: string;
  size_mb: number | null;
  local: boolean;
  download: string;
}

export interface NisarTimeline {
  track: number;
  frame: number;
  level: string;
  coleccion: string;
  total: number;
  scenes: NisarTimelineScene[];
}

export interface NisarFiltros {
  start: string;
  end: string;
  level: string;
  polarization?: string;
  max?: number;
}

function bbox(caja: Caja): string {
  return `${caja.oeste},${caja.sur},${caja.este},${caja.norte}`;
}

export function getNisarCatalog(): Promise<NisarCatalog> {
  return fetch("/api/nisar/catalog").then((r) => leer<NisarCatalog>(r));
}

export function searchNisar(
  caja: Caja,
  filtros: NisarFiltros,
): Promise<NisarSearch> {
  const query = new URLSearchParams({ bbox: bbox(caja) });
  query.set("start", filtros.start);
  query.set("end", filtros.end);
  query.set("level", filtros.level);
  if (filtros.polarization) query.set("polarization", filtros.polarization);
  if (filtros.max) query.set("max", String(filtros.max));
  return fetch(`/api/nisar/search?${query}`).then((r) => leer<NisarSearch>(r));
}

export function getLocalScenes(
  track: number,
  frame: number,
  coleccion: string,
): Promise<NisarLocalScenes> {
  const query = new URLSearchParams({
    track: String(track),
    frame: String(frame),
    coleccion,
  });
  return fetch(`/api/nisar/local?${query}`).then((r) =>
    leer<NisarLocalScenes>(r),
  );
}

/** Fechas del track/frame: ASF mas lo que ya esta en disco. */
export function getNisarTimeline(
  track: number,
  frame: number,
  coleccion: string,
  level: string,
): Promise<NisarTimeline> {
  const query = new URLSearchParams({
    track: String(track),
    frame: String(frame),
    coleccion,
    level,
  });
  return fetch(`/api/nisar/timeline?${query}`).then((r) =>
    leer<NisarTimeline>(r),
  );
}

/** Resuelve una fecha suelta a su granulo del track/frame (local o en ASF). */
export function getNisarScene(
  track: number,
  frame: number,
  date: string,
  coleccion: string,
): Promise<NisarGranule> {
  const query = new URLSearchParams({
    track: String(track),
    frame: String(frame),
    date,
    coleccion,
  });
  return fetch(`/api/nisar/scene?${query}`).then((r) => leer<NisarGranule>(r));
}

export function getParaguay(): Promise<FeatureCollection> {
  return fetch("/api/nisar/paraguay").then((r) =>
    leer<FeatureCollection>(r),
  );
}
