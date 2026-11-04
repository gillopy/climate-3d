import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import type { RangoFechas } from "../../types";
import { Calendario, formatearFecha, formatearRango, hoyLocal } from "./Calendar";

const ISO = /^\d{4}-\d{2}-\d{2}$/;

function diasEntre(desde: string, hasta: string): number {
  const a = Date.parse(`${desde}T00:00:00Z`);
  const b = Date.parse(`${hasta}T00:00:00Z`);
  if (Number.isNaN(a) || Number.isNaN(b)) return 0;
  return Math.round((b - a) / 86_400_000) + 1;
}

/**
 * Un extremo de la ventana: el botón abre el calendario y el calendario se
 * cierra al elegir. Cada extremo tiene su propia ventana.
 */
function Extremo({
  nombre,
  fecha,
  abierto,
  alAbrir,
  children,
}: {
  nombre: string;
  fecha: string;
  abierto: boolean;
  alAbrir: () => void;
  children: (arriba: boolean) => ReactNode;
}) {
  const boton = useRef<HTMLButtonElement | null>(null);
  const [arriba, setArriba] = useState(false);

  function alternar() {
    if (!abierto) {
      // Sin lugar abajo, el calendario se abre hacia arriba.
      const caja = boton.current?.getBoundingClientRect();
      if (caja) setArriba(window.innerHeight - caja.bottom < 360);
    }
    alAbrir();
  }

  return (
    <div className="window__stop">
      <span className="window__stop-name">{nombre}</span>
      <button
        type="button"
        ref={boton}
        className={abierto ? "window__fecha window__fecha--abierta" : "window__fecha"}
        aria-haspopup="dialog"
        aria-expanded={abierto}
        aria-label={`${nombre}: ${fecha}`}
        onClick={alternar}
      >
        <span className="window__fecha-valor">{fecha}</span>
        <span className="window__icono" aria-hidden="true" />
      </button>
      {abierto ? children(arriba) : null}
    </div>
  );
}

interface VentanaProps {
  label: string;
  value: RangoFechas;
  disponibles: Set<string>;
  disabled?: boolean;
  onChange: (rango: RangoFechas) => void;
}

/**
 * Ventana temporal: dos botones, cada uno con su calendario desplegable.
 *
 * El comienzo manda: si se elige un día posterior al final, la ventana se
 * achica a ese día. El final nunca mueve el comienzo — los días anteriores
 * quedan deshabilitados en su calendario.
 */
export function VentanaTemporal({
  label,
  value,
  disponibles,
  disabled,
  onChange,
}: VentanaProps) {
  const [abierto, setAbierto] = useState<"start" | "end" | null>(null);
  const caja = useRef<HTMLDivElement | null>(null);
  const inicio = ISO.test(value.start) ? value.start : hoyLocal();
  const fin = ISO.test(value.end) && value.end >= inicio ? value.end : inicio;
  const dias = diasEntre(inicio, fin);

  useEffect(() => {
    if (!abierto) return;
    const afuera = (evento: PointerEvent) => {
      if (caja.current && !caja.current.contains(evento.target as Node)) {
        setAbierto(null);
      }
    };
    document.addEventListener("pointerdown", afuera);
    return () => document.removeEventListener("pointerdown", afuera);
  }, [abierto]);

  function elegirInicio(iso: string) {
    onChange({ start: iso, end: iso > fin ? iso : fin });
    setAbierto(null);
  }

  function elegirFin(iso: string) {
    // El final no toca el comienzo: si quedara antes, ni siquiera es clickeable.
    if (iso < inicio) return;
    onChange({ start: inicio, end: iso });
    setAbierto(null);
  }

  return (
    <div
      className={disabled ? "window window--off" : "window"}
      ref={caja}
      onKeyDown={(evento) => {
        if (evento.key === "Escape") setAbierto(null);
      }}
    >
      <div className="window__head">
        <span className="window__label">{label}</span>
        <span className="window__cuenta">
          {dias} {dias === 1 ? "día" : "días"}
        </span>
      </div>

      <div className="window__track">
        <Extremo
          nombre="Desde"
          fecha={formatearFecha(inicio)}
          abierto={abierto === "start"}
          alAbrir={() => setAbierto(abierto === "start" ? null : "start")}
        >
          {(arriba) => (
            <div
              className={arriba ? "window__pop window__pop--arriba" : "window__pop"}
              role="dialog"
              aria-label="Elegir el comienzo"
            >
              <Calendario
                modo="range"
                inicio={inicio}
                fin={fin}
                disponibles={disponibles}
                disabled={disabled}
                onElegir={elegirInicio}
              />
            </div>
          )}
        </Extremo>

        <span className="window__arrow" aria-hidden="true">
          →
        </span>

        <Extremo
          nombre="Hasta"
          fecha={formatearFecha(fin)}
          abierto={abierto === "end"}
          alAbrir={() => setAbierto(abierto === "end" ? null : "end")}
        >
          {(arriba) => (
            <div
              className={
                arriba
                  ? "window__pop window__pop--der window__pop--arriba"
                  : "window__pop window__pop--der"
              }
              role="dialog"
              aria-label="Elegir el final"
            >
              <Calendario
                modo="range"
                inicio={inicio}
                fin={fin}
                disponibles={disponibles}
                minimo={inicio}
                disabled={disabled}
                onElegir={elegirFin}
              />
            </div>
          )}
        </Extremo>
      </div>

      <p className="window__pie">
        <span className="window__paso">{formatearRango(inicio, fin)}</span>
        <span className="window__leyenda">
          <span className="window__muestra window__muestra--fuera" aria-hidden="true" />
          fuera del rango
          {disponibles.size > 0 ? (
            <>
              <span className="window__muestra" aria-hidden="true" />
              con datos en disco
            </>
          ) : null}
        </span>
      </p>
    </div>
  );
}

interface FechaProps {
  label: string;
  value: string;
  disponibles: Set<string>;
  disabled?: boolean;
  onChange: (iso: string) => void;
}

/** Fecha suelta: un botón que abre su calendario y se cierra al elegir. */
export function FechaUnica({
  label,
  value,
  disponibles,
  disabled,
  onChange,
}: FechaProps) {
  const [abierto, setAbierto] = useState(false);
  const caja = useRef<HTMLDivElement | null>(null);
  const dia = ISO.test(value) ? value : hoyLocal();

  useEffect(() => {
    if (!abierto) return;
    const afuera = (evento: PointerEvent) => {
      if (caja.current && !caja.current.contains(evento.target as Node)) {
        setAbierto(false);
      }
    };
    document.addEventListener("pointerdown", afuera);
    return () => document.removeEventListener("pointerdown", afuera);
  }, [abierto]);

  return (
    <div
      className={disabled ? "window window--sola window--off" : "window window--sola"}
      ref={caja}
      onKeyDown={(evento) => {
        if (evento.key === "Escape") setAbierto(false);
      }}
    >
      <div className="window__head">
        <span className="window__label">{label}</span>
        <span className="window__cuenta">{formatearFecha(dia)}</span>
      </div>

      <div className="window__track window__track--sola">
        <Extremo
          nombre="Día"
          fecha={formatearFecha(dia)}
          abierto={abierto}
          alAbrir={() => setAbierto(!abierto)}
        >
          {(arriba) => (
            <div
              className={arriba ? "window__pop window__pop--arriba" : "window__pop"}
              role="dialog"
              aria-label="Elegir el día"
            >
              <Calendario
                modo="single"
                inicio={dia}
                fin={dia}
                disponibles={disponibles}
                disabled={disabled}
                onElegir={(iso) => {
                  onChange(iso);
                  setAbierto(false);
                }}
              />
            </div>
          )}
        </Extremo>
      </div>

      <p className="window__pie">
        <span className="window__paso">Elegí el día</span>
        {disponibles.size > 0 ? (
          <span className="window__leyenda">
            <span className="window__muestra" aria-hidden="true" />
            con datos en disco
          </span>
        ) : null}
      </p>
    </div>
  );
}
