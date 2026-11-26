import L from "leaflet";

/** Caja visible en el formato `oeste,sur,este,norte` que esperan las APIs.
 *
 * `margen` agranda la caja una fracción de su tamaño en cada lado: sirve para
 * pedir un poco más de lo que se ve y no repetir la consulta con cada paneo.
 */
export function cajaDeMapa(mapa: L.Map, margen = 0): string | null {
  const bounds = mapa.getBounds();
  let oeste = bounds.getWest();
  let este = bounds.getEast();
  if (este - oeste >= 360) {
    oeste = -180;
    este = 180;
  } else {
    oeste = Math.max(-180, oeste);
    este = Math.min(180, este);
  }
  if (este <= oeste) return null;
  let sur = bounds.getSouth();
  let norte = bounds.getNorth();
  if (margen > 0) {
    const dx = (este - oeste) * margen;
    const dy = (norte - sur) * margen;
    oeste = Math.max(-180, oeste - dx);
    este = Math.min(180, este + dx);
    sur = Math.max(-90, sur - dy);
    norte = Math.min(90, norte + dy);
  }
  return [oeste, sur, este, norte].map((valor) => valor.toFixed(4)).join(",");
}

/** Margen de tolerancia: las cajas se serializan con 4 decimales. */
const EPSILON_CAJA = 1e-4;

/** Si `caja` cae entera dentro de `contenedor` (ambas en formato `o,s,e,n`). */
export function contiene(contenedor: string, caja: string): boolean {
  const a = contenedor.split(",").map(Number);
  const b = caja.split(",").map(Number);
  if (a.length !== 4 || b.length !== 4) return false;
  if (a.some(Number.isNaN) || b.some(Number.isNaN)) return false;
  return (
    b[0] >= a[0] - EPSILON_CAJA &&
    b[1] >= a[1] - EPSILON_CAJA &&
    b[2] <= a[2] + EPSILON_CAJA &&
    b[3] <= a[3] + EPSILON_CAJA
  );
}
