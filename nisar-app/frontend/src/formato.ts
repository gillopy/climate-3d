/** Formato compartido por el visor y el panel de trabajos. */

export interface StatsRow {
  label: string;
  value: string;
}

export function fechaCorta(iso: string): string {
  if (!iso) return "-";
  return iso.replace("T", " ").replace("Z", " UTC");
}

export function pesoArchivo(bytes: number): string {
  return bytes >= 1_048_576
    ? `${(bytes / 1_048_576).toFixed(1)} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

function _get(meta: Record<string, unknown>, ruta: string): unknown {
  let actual: unknown = meta;
  for (const parte of ruta.split(".")) {
    if (actual === null || typeof actual !== "object") return undefined;
    actual = (actual as Record<string, unknown>)[parte];
  }
  return actual;
}

/** Resumen legible del JSON de estadisticas que dejan los productos NISAR. */
export function resumenStats(meta: Record<string, unknown>): StatsRow[] {
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
  agregar("Pérdida candidata", "perdida_candidata_ha", ha);
  agregar("Pérdida radar", "perdida_radar_ha", ha);
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
  agregar("Corrimiento del par", "offset_db", db);
  agregar("HV mínimo", "hv_min_db", db);
  agregar("HH máximo", "hh_max_db", db);
  agregar("HV máximo", "hv_max_db", db);
  agregar("NDVI medio", "ndvi.medio", num);
  agregar("Correlación HV/NDVI", "correlacion", num);
  agregar("Cambio CUSUM", "cusum.cambio_ha", ha);
  agregar("Área CUSUM", "cusum.area_ha", ha);
  agregar("Sentinel-2", "optico.items", (valor) => `${valor} ítem(s)`);
  agregar("NDVI confirma", "optico.verificado", (valor) =>
    valor ? "sí" : "no",
  );
  agregar("Persistencia", "temporal.disponible", (valor) =>
    valor ? "sí" : "no",
  );
  agregar("Recuperado", "temporal.recuperados_ha", ha);
  agregar("Cobertura NDVI", "optico.cobertura_valida_pct", pct);
  agregar("Focos FIRMS", "focos", texto);
  agregar("Resolución", "mpp", (valor) => `${Number(valor).toFixed(0)} m/px`);
  agregar("Resolución", "metros_por_px", (valor) => `${Number(valor).toFixed(0)} m/px`);
  agregar("Salida", "px", (valor) =>
    Array.isArray(valor) ? `${valor[0]} × ${valor[1]} px` : String(valor),
  );
  const multilook = _get(meta, "multilook");
  if (typeof multilook === "number" && multilook > 1) {
    const mpp = Number(_get(meta, "mpp"));
    filas.push({
      label: "Multilook",
      value:
        Number.isFinite(mpp) && mpp > 0
          ? `${multilook}×${multilook} (~${Math.round(multilook * mpp)} m)`
          : `${multilook}×${multilook}`,
    });
  }
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
