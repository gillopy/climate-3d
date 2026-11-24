import L from "leaflet";

/** Caja visible en el formato `oeste,sur,este,norte` que esperan las APIs. */
export function cajaDeMapa(mapa: L.Map): string | null {
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
  return [oeste, bounds.getSouth(), este, bounds.getNorth()]
    .map((valor) => valor.toFixed(4))
    .join(",");
}
