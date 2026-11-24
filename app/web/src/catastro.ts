import type { FeatureCollection, Geometry } from "geojson";
import { leer } from "./api";
import type { Caja } from "./nisar";

/** Estado del dataset y del índice de catastro en el servidor. */
export interface CatastroEstado {
  disponible: boolean;
  indexando: boolean;
  progreso: number;
  mensaje: string;
  error: string | null;
  ruta_origen: string;
  ruta_configurada: string;
  ruta_indice: string;
  parcelas: number;
  total_origen: number;
  invalidas: number;
  reparadas: number;
  construido: string | null;
  segundos: number;
  bytes_indice: number;
  zoom_min: number;
  fuente: string;
  atribucion: string;
  departamentos: Record<string, string>;
}

/** Atributos tal como los publica el backend (nombres del DBF del SNC). */
export interface ParcelaProps {
  ccatastral: string;
  departamento: string;
  dpto: string;
  dist: string;
  padron: string;
  zona: string;
  mz: string;
  lote: string;
  finca: string;
  matricula: string;
  colonia: string;
  reg_prof: string;
  nombre_obj: string;
  tipo: string;
  zona_urban: string;
  sup_legal: number | null;
  sup_sig_m2: number | null;
  area_ha: number | null;
  afectado_m2?: number;
  afectado_ha?: number;
  fraccion?: number | null;
}

export type CatastroCapa = FeatureCollection<Geometry, ParcelaProps> & {
  capa: string;
  bbox: number[];
  zoom: number;
  min_zoom: number;
  area_min_m2: number;
  area_min_ha: number;
  total: number;
  excedido: boolean;
  requiere_zoom: boolean;
  requiere_indice: boolean;
  indexando: boolean;
  progreso: number;
  mensaje: string;
  avisos: string[];
  simplificado_grados?: number;
};

export type CatastroAfectadas = FeatureCollection<Geometry, ParcelaProps> & {
  caja: number[];
  area_ha: number;
  total: number;
  excedido: boolean;
  cubierto_ha: number;
  cubierto_pct: number;
  requiere_indice: boolean;
  indexando: boolean;
  progreso: number;
  mensaje: string;
  atribucion: string;
  avisos: string[];
};

export function getCatastro(signal?: AbortSignal): Promise<CatastroEstado> {
  return fetch("/api/catastro", { signal }).then((r) => leer<CatastroEstado>(r));
}

/** Parcelas de la caja visible, simplificadas para el zoom actual. */
export function getParcelas(
  bbox: string,
  zoom: number,
  signal?: AbortSignal,
): Promise<CatastroCapa> {
  const query = new URLSearchParams({ bbox, zoom: String(zoom) });
  return fetch(`/api/catastro/parcelas?${query}`, { signal }).then((r) =>
    leer<CatastroCapa>(r),
  );
}

/** Cruza el cuadro ROI con el catastro y devuelve el área afectada por parcela. */
export function analizarAfectadas(
  caja: Caja,
  signal?: AbortSignal,
): Promise<CatastroAfectadas> {
  return fetch("/api/catastro/afectadas", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      bbox: [caja.oeste, caja.sur, caja.este, caja.norte],
    }),
    signal,
  }).then((r) => leer<CatastroAfectadas>(r));
}
