import { useCallback, useEffect, useRef, useState } from "react";
import type { FeatureCollection, Geometry } from "geojson";

import { analizarPerdida, getMascaraPerdida } from "../catastro";
import type { CatastroAfectadas } from "../catastro";
import { areaTexto } from "./CatastroPanel";
import { MapaPerdida } from "./MapaPerdida";

const NUMERO = new Intl.NumberFormat("es-PY");

interface Props {
  /** URL del GeoJSON que dejó el producto (`<corrida>_perdida.geojson`). */
  url: string;
  /** Pérdida total de la corrida, para contrastar con lo catastrado. */
  perdidaHa?: number;
  /** Fechas del par, para el título del mapa. */
  fechas?: string;
}

function textoParcela(props: {
  colonia?: string;
  padron?: string;
  finca?: string;
  matricula?: string;
}): string {
  const limpio = (valor: string | undefined) =>
    valor && valor !== "0" ? valor : "";
  const partes = [
    limpio(props.colonia),
    limpio(props.padron) ? `padrón ${props.padron}` : "",
    limpio(props.finca) ? `finca ${props.finca}` : "",
    limpio(props.matricula),
  ].filter(Boolean);
  return partes.join(" · ") || "Sin datos registrales";
}

/**
 * Cruce de la pérdida detectada por NISAR con el catastro del SNC.
 *
 * La consulta es la máscara real de la corrida (el rojo del producto), no el
 * cuadro ROI: cada parcela muestra la pérdida que cae adentro del predio. El
 * GeoJSON se baja recién al apretar el botón: una corrida de 2400 px pesa ~1,5 MB.
 */
export function PerdidaCatastro({ url, perdidaHa, fechas }: Props) {
  const [mascara, setMascara] = useState<FeatureCollection<
    Geometry,
    Record<string, unknown>
  > | null>(null);
  const [cruce, setCruce] = useState<CatastroAfectadas | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [abierto, setAbierto] = useState(false);
  const [foco, setFoco] = useState<string | null>(null);
  const aborto = useRef<AbortController | null>(null);

  // Cambió la corrida: el cruce anterior ya no corresponde.
  useEffect(() => {
    aborto.current?.abort();
    setMascara(null);
    setCruce(null);
    setError(null);
    setCargando(false);
    setAbierto(false);
    setFoco(null);
  }, [url]);

  useEffect(() => () => aborto.current?.abort(), []);

  const cruzar = useCallback(async () => {
    aborto.current?.abort();
    const control = new AbortController();
    aborto.current = control;
    setCargando(true);
    setError(null);
    try {
      let datos = mascara;
      if (!datos) {
        datos = await getMascaraPerdida(url, control.signal);
        if (control.signal.aborted) return;
        setMascara(datos);
      }
      const feature = datos.features[0];
      if (!feature?.geometry) {
        setError("La máscara de pérdida vino vacía.");
        return;
      }
      const resultado = await analizarPerdida(feature.geometry, control.signal);
      if (control.signal.aborted) return;
      setCruce(resultado);
    } catch (exc: unknown) {
      if (control.signal.aborted) return;
      setError(
        exc instanceof Error
          ? exc.message
          : "No se pudo cruzar la pérdida con el catastro.",
      );
    } finally {
      if (!control.signal.aborted) setCargando(false);
    }
  }, [mascara, url]);

  const enfocar = useCallback((ccatastral: string) => {
    setFoco(ccatastral);
    setAbierto(true);
  }, []);

  return (
    <div className="trabajos__seccion perdida-catastro">
      <h4>Inmuebles afectados</h4>
      <p className="perdida-catastro__intro">
        Cruza la pérdida detectada con el catastro del SNC: dice a qué inmueble
        pertenece cada zona roja, con padrón, finca y matrícula.
      </p>

      <div className="catastro__acciones">
        <button
          type="button"
          className="btn btn--primary"
          onClick={() => void cruzar()}
          disabled={cargando}
        >
          {cargando ? "Cruzando…" : cruce ? "Volver a cruzar" : "Cruzar con catastro"}
        </button>
        {cruce && mascara ? (
          <button type="button" className="btn" onClick={() => setAbierto(true)}>
            Ver en el mapa
          </button>
        ) : null}
      </div>

      {error ? (
        <p className="trabajos__aviso" role="alert">
          {error}
        </p>
      ) : null}

      {cruce?.requiere_indice ? (
        <p className="perdida-catastro__nota">
          El índice de catastro todavía se está construyendo
          {cruce.indexando ? ` (${Math.round(cruce.progreso * 100)} %)` : ""}: probá
          de nuevo en unos minutos.
        </p>
      ) : null}

      {cruce && !cruce.requiere_indice ? (
        <>
          <p className="perdida-catastro__resumen">
            <strong>{NUMERO.format(cruce.total)}</strong>{" "}
            {cruce.total === 1 ? "inmueble" : "inmuebles"} con pérdida adentro ·{" "}
            <strong>{areaTexto(cruce.cubierto_ha)}</strong> de pérdida catastrada
            sobre {areaTexto(cruce.area_ha)} detectadas ({cruce.cubierto_pct} %)
            {perdidaHa ? ` · ${areaTexto(perdidaHa)} en total` : ""}
          </p>
          {cruce.avisos.length ? (
            <p className="perdida-catastro__nota">{cruce.avisos.join(" ")}</p>
          ) : null}
          {cruce.total === 0 ? (
            <p className="perdida-catastro__nota">
              La pérdida no cae dentro de parcelas del catastro: puede ser tierra
              fiscal, reserva o un área sin mensura.
            </p>
          ) : (
            <ul className="catastro__lista">
              {cruce.features.map((feature, indice) => {
                const props = feature.properties;
                const clave = props.ccatastral || `parcela-${indice}`;
                return (
                  <li key={clave}>
                    <button
                      type="button"
                      className="catastro__item"
                      onClick={() => enfocar(props.ccatastral)}
                      title="Ver la parcela en el mapa"
                    >
                      <span className="catastro__item-id">
                        {props.ccatastral || "Sin código"}
                      </span>
                      <span className="catastro__item-meta">
                        {textoParcela(props)}
                      </span>
                      <span className="catastro__item-area">
                        {areaTexto(props.afectado_ha)}
                        {props.fraccion !== null && props.fraccion !== undefined
                          ? ` · ${Math.round(props.fraccion * 100)} % del predio`
                          : ""}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </>
      ) : null}

      {abierto && mascara && cruce ? (
        <MapaPerdida
          perdida={mascara}
          parcelas={cruce}
          foco={foco}
          titulo={fechas ?? "Cambio NISAR"}
          alCerrar={() => {
            setAbierto(false);
            setFoco(null);
          }}
        />
      ) : null}
    </div>
  );
}
