import type { FeatureCollection, Geometry } from "geojson";

import { leer } from "./api";

/** Una capa ambiental del mapa NISAR, tal como la publica el backend. */
export interface CapaInfo {
  id: string;
  nombre: string;
  descripcion: string;
  fuente: string;
  fuente_url: string;
  atribucion: string;
  color: string;
  min_zoom: number;
}

export interface CapasCatalogo {
  capas: CapaInfo[];
  fuentes: string[];
}

/** Atributos normalizados por `app/api/capas.py`, no los crudos de ArcGIS. */
export interface CapaPropiedades {
  nombre?: string;
  categoria?: string;
  designacion?: string;
  tipo?: string;
  iucn?: string;
  anio?: number | null;
  area_ha?: number | null;
  pais?: string;
  sitio?: number | null;
  situacion?: string;
  nota?: string;
  origen?: string;
  iso?: string;
  color?: string;
}

export type CapaGeoJSON = FeatureCollection<Geometry, CapaPropiedades> & {
  capa: string;
  nombre: string;
  bbox: number[];
  zoom: number;
  min_zoom: number;
  fuente: { nombre: string; url: string };
  atribucion: string;
  total: number;
  excedido: boolean;
  requiere_zoom: boolean;
  avisos: string[];
};

export function getCapas(): Promise<CapasCatalogo> {
  return fetch("/api/capas").then((r) => leer<CapasCatalogo>(r));
}

/** GeoJSON de una capa recortado a la caja visible y al zoom actual. */
export function getCapa(
  capaId: string,
  bbox: string,
  zoom: number,
  signal?: AbortSignal,
): Promise<CapaGeoJSON> {
  const query = new URLSearchParams({ bbox, zoom: String(zoom) });
  return fetch(`/api/capas/${encodeURIComponent(capaId)}?${query}`, { signal }).then(
    (r) => leer<CapaGeoJSON>(r),
  );
}
