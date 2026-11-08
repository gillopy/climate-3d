import type { ParamOption, ParamSpec, Params } from "./types";

function coincide(
  condicion: Record<string, unknown> | null | undefined,
  params: Params,
): boolean {
  if (!condicion) return true;
  return Object.entries(condicion).every(
    ([clave, esperado]) => params[clave] === esperado,
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
