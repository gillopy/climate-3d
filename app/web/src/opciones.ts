import type { ParamOption, ParamSpec, Params } from "./types";

function coincide(
  condicion: Record<string, unknown> | null | undefined,
  params: Params,
): boolean {
  if (!condicion) return true;
  // El valor esperado puede ser uno solo o una lista (una paleta compartida
  // por varias bandas, como la de reflectancia de C01-C06).
  return Object.entries(condicion).every(([clave, esperado]) =>
    Array.isArray(esperado)
      ? esperado.includes(params[clave])
      : params[clave] === esperado,
  );
}

/** Opciones que el estado actual del formulario permite elegir. */
export function opcionesVisibles(
  spec: ParamSpec,
  params: Params,
): ParamOption[] {
  return spec.options.filter((opcion) => coincide(opcion.only_when, params));
}

/**
 * Valor al que hay que mover un select cuando otro control lo invalida.
 *
 * Devuelve `null` si la opcion elegida sigue visible. Si no, prefiere el
 * default del control y, si tampoco esta disponible, la primera opcion.
 */
export function valorAjustado(spec: ParamSpec, params: Params): string | null {
  if (spec.kind !== "select") return null;
  const opciones = opcionesVisibles(spec, params);
  if (opciones.length === 0) return null;
  const actual = String(params[spec.name] ?? spec.default ?? "");
  if (opciones.some((opcion) => opcion.value === actual)) return null;
  const porDefecto = String(spec.default ?? "");
  return (
    opciones.find((opcion) => opcion.value === porDefecto) ?? opciones[0]
  ).value;
}

// Arranque de datos por satélite: GOES-16 voló hasta 2025, GOES-18 arrancó en
// 2022 y GOES-19 en 2024. Lo comparten el calendario (hasta dónde se navega) y
// el ajuste automático de la fecha elegida.
export const PISO_SATELITE: Record<string, string> = {
  G16: "2017-01-01",
  G18: "2022-01-01",
  G19: "2024-01-01",
};

export function pisoDeSatelite(params: Params): string | undefined {
  return PISO_SATELITE[String(params.satelite ?? "")];
}

/**
 * Acomoda la fecha elegida al arranque de datos del satélite.
 *
 * Cambiar de G16 a G19 con una fecha de 2017 dejaría un pedido imposible: la
 * ventana (y la fecha suelta) se corren al primer día que tiene datos.
 */
export function ajustarFechas(params: Params): Params {
  const piso = pisoDeSatelite(params);
  if (!piso) return params;
  const siguiente: Params = { ...params };

  const ventana = siguiente.ventana as { start?: string; end?: string } | undefined;
  if (ventana && typeof ventana === "object") {
    const inicio = String(ventana.start ?? "");
    const fin = String(ventana.end ?? "");
    const nuevoInicio = inicio && inicio < piso ? piso : inicio;
    const nuevoFin = fin && fin < piso ? piso : fin;
    if (nuevoInicio !== inicio || nuevoFin !== fin) {
      siguiente.ventana = {
        ...ventana,
        start: nuevoInicio,
        end: nuevoFin < nuevoInicio ? nuevoInicio : nuevoFin,
      };
    }
  }

  const fecha = siguiente.fecha;
  if (typeof fecha === "string" && fecha && fecha < piso) {
    siguiente.fecha = piso;
  }
  return siguiente;
}
