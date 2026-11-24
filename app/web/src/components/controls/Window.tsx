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
  accion,
  children,
}: {
  nombre: string;
  fecha: string;
  abierto: boolean;
  alAbrir: () => void;
  accion?: ReactNode;
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
      {accion}
      {abierto ? children(arriba) : null}
    </div>
  );
}

interface VentanaProps {
  value: RangoFechas;
  disponibles: Set<string>;
  /** Arranque de datos de la selección (el satélite): hasta dónde irse atrás. */
  piso?: string;
  /**
   * El extremo "hasta" se puede dejar vacío: significa "hasta el último cuadro
   * publicado". Sólo lo declara el producto que sabe resolverlo.
   */
  abierto?: boolean;
  disabled?: boolean;
  onChange: (rango: RangoFechas) => void;
}

/**
 * Ventana temporal: dos extremos, cada uno con su calendario desplegable.
 *
 * El comienzo manda: si se elige un día posterior al final, la ventana se
 * achica a ese día. El final nunca mueve el comienzo — los días anteriores
 * quedan deshabilitados en su calendario.
 *
 * Con `abierto`, el final se puede vaciar ("hasta el último cuadro"): el
 * extremo queda sin calendario y se vuelve a fijar abriéndolo de nuevo.
 */
export function VentanaTemporal({
  value,
  disponibles,
  piso,
  abierto = false,
  disabled,
  onChange,
}: VentanaProps) {
  const [cual, setCual] = useState<"start" | "end" | null>(null);
  const caja = useRef<HTMLDivElement | null>(null);
  const inicio = ISO.test(value.start) ? value.start : hoyUTC();
  // `end` vacío = sin fecha final, no "un día suelto".
  const sinFin = abierto && !ISO.test(value.end);
  const fin = sinFin
    ? inicio
    : ISO.test(value.end) && value.end >= inicio
      ? value.end
      : inicio;
  const dias = diasEntre(inicio, fin);

  useEffect(() => {
    if (!cual) return;
    const afuera = (evento: PointerEvent) => {
      if (caja.current && !caja.current.contains(evento.target as Node)) {
        setCual(null);
      }
    };
    document.addEventListener("pointerdown", afuera);
    return () => document.removeEventListener("pointerdown", afuera);
  }, [cual]);

  function elegirInicio(iso: string) {
    onChange({ start: iso, end: sinFin ? "" : iso > fin ? iso : fin });
    setCual(null);
  }

  function elegirFin(iso: string) {
    // El final no toca el comienzo: si quedara antes, ni siquiera es clickeable.
    if (iso < inicio) return;
    onChange({ start: inicio, end: iso });
    setCual(null);
  }

  function hastaElUltimo() {
    onChange({ start: inicio, end: "" });
    setCual(null);
  }

  return (
    <div
      className={disabled ? "datepick datepick--off" : "datepick"}
      ref={caja}
      onKeyDown={(evento) => {
        if (evento.key === "Escape") setCual(null);
      }}
    >
      <Extremo
        nombre="Desde"
        fecha={formatearFecha(inicio)}
        abierto={cual === "start"}
        alAbrir={() => setCual(cual === "start" ? null : "start")}
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
        fecha={sinFin ? "último cuadro" : formatearFecha(fin)}
        abierto={cual === "end"}
        alAbrir={() => setCual(cual === "end" ? null : "end")}
        accion={
          abierto && !sinFin ? (
            <button
              type="button"
              className="datepick__accion"
              title="Sin fecha final: hasta el último cuadro publicado"
              aria-label="Hasta el último cuadro publicado"
              disabled={disabled}
              onClick={hastaElUltimo}
            >
              ×
            </button>
          ) : undefined
        }
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
        title={
          sinFin
            ? "sin fecha final: hasta el último cuadro publicado"
            : formatearRango(inicio, fin)
        }
        aria-label={sinFin ? "sin fecha final" : `${dias} ${dias === 1 ? "día" : "días"}`}
      >
        {sinFin ? "último" : `${dias} d`}
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
