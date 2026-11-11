import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import type { RangoFechas } from "../../types";
import { Calendario, formatearFecha, formatearRango, hoyUTC } from "./Calendar";

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
    <div className="datepick__stop">
      <button
        type="button"
        ref={boton}
        className={abierto ? "datepick__btn datepick__btn--open" : "datepick__btn"}
        aria-haspopup="dialog"
        aria-expanded={abierto}
        aria-label={`${nombre}: ${fecha}`}
        onClick={alternar}
      >
        <span className="datepick__k">{nombre}</span>
        <span className="datepick__v">{fecha}</span>
      </button>
      {abierto ? children(arriba) : null}
    </div>
  );
}

interface VentanaProps {
  value: RangoFechas;
  disponibles: Set<string>;
  /** Arranque de datos de la selección (el satélite): hasta dónde irse atrás. */
  piso?: string;
  disabled?: boolean;
  onChange: (rango: RangoFechas) => void;
}

/**
 * Ventana temporal: dos extremos, cada uno con su calendario desplegable.
 *
 * El comienzo manda: si se elige un día posterior al final, la ventana se
 * achica a ese día. El final nunca mueve el comienzo — los días anteriores
 * quedan deshabilitados en su calendario.
 */
export function VentanaTemporal({
  value,
  disponibles,
  piso,
  disabled,
  onChange,
}: VentanaProps) {
  const [abierto, setAbierto] = useState<"start" | "end" | null>(null);
  const caja = useRef<HTMLDivElement | null>(null);
  const inicio = ISO.test(value.start) ? value.start : hoyUTC();
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
      className={disabled ? "datepick datepick--off" : "datepick"}
      ref={caja}
      onKeyDown={(evento) => {
        if (evento.key === "Escape") setAbierto(null);
      }}
    >
      <Extremo
        nombre="Desde"
        fecha={formatearFecha(inicio)}
        abierto={abierto === "start"}
        alAbrir={() => setAbierto(abierto === "start" ? null : "start")}
      >
        {(arriba) => (
          <div
            className={arriba ? "datepick__pop datepick__pop--arriba" : "datepick__pop"}
            role="dialog"
            aria-label="Elegir el comienzo"
          >
            <Calendario
              modo="range"
              inicio={inicio}
              fin={fin}
              disponibles={disponibles}
              piso={piso}
              disabled={disabled}
              onElegir={elegirInicio}
            />
          </div>
        )}
      </Extremo>

      <span className="datepick__sep" aria-hidden="true">
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
                ? "datepick__pop datepick__pop--der datepick__pop--arriba"
                : "datepick__pop datepick__pop--der"
            }
            role="dialog"
            aria-label="Elegir el final"
          >
            <Calendario
              modo="range"
              inicio={inicio}
              fin={fin}
              disponibles={disponibles}
              piso={piso}
              minimo={inicio}
              disabled={disabled}
              onElegir={elegirFin}
            />
          </div>
        )}
      </Extremo>

      <span
        className="datepick__days"
        title={formatearRango(inicio, fin)}
        aria-label={`${dias} ${dias === 1 ? "día" : "días"}`}
      >
        {dias} d
      </span>
    </div>
  );
}

interface FechaProps {
  value: string;
  disponibles: Set<string>;
  /** Arranque de datos de la selección (el satélite): hasta dónde irse atrás. */
  piso?: string;
  disabled?: boolean;
  onChange: (iso: string) => void;
}

/** Fecha suelta: un control que abre su calendario y se cierra al elegir. */
export function FechaUnica({
  value,
  disponibles,
  piso,
  disabled,
  onChange,
}: FechaProps) {
  const [abierto, setAbierto] = useState(false);
  const [arriba, setArriba] = useState(false);
  const boton = useRef<HTMLButtonElement | null>(null);
  const caja = useRef<HTMLDivElement | null>(null);
  const dia = ISO.test(value) ? value : hoyUTC();

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

  function alternar() {
    if (!abierto) {
      const cajaBoton = boton.current?.getBoundingClientRect();
      if (cajaBoton) setArriba(window.innerHeight - cajaBoton.bottom < 360);
    }
    setAbierto(!abierto);
  }

  return (
    <div
      className={disabled ? "datepick datepick--off" : "datepick"}
      ref={caja}
      onKeyDown={(evento) => {
        if (evento.key === "Escape") setAbierto(false);
      }}
    >
      <button
        type="button"
        ref={boton}
        className={
          abierto ? "datepick__btn datepick__btn--sola datepick__btn--open" : "datepick__btn datepick__btn--sola"
        }
        aria-haspopup="dialog"
        aria-expanded={abierto}
        aria-label={`Día: ${formatearFecha(dia)}`}
        onClick={alternar}
      >
        <span className="datepick__icon" aria-hidden="true" />
        <span className="datepick__k">Día</span>
        <span className="datepick__v">{formatearFecha(dia)}</span>
      </button>

      {abierto ? (
        <div
          className={arriba ? "datepick__pop datepick__pop--arriba" : "datepick__pop"}
          role="dialog"
          aria-label="Elegir el día"
        >
          <Calendario
            modo="single"
            inicio={dia}
            fin={dia}
            disponibles={disponibles}
            piso={piso}
            disabled={disabled}
            onElegir={(iso) => {
              onChange(iso);
              setAbierto(false);
            }}
          />
        </div>
      ) : null}
    </div>
  );
}
