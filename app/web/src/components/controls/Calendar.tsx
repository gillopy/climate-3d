import { useEffect, useMemo, useState } from "react";

const MESES = [
  "ENERO",
  "FEBRERO",
  "MARZO",
  "ABRIL",
  "MAYO",
  "JUNIO",
  "JULIO",
  "AGOSTO",
  "SEPTIEMBRE",
  "OCTUBRE",
  "NOVIEMBRE",
  "DICIEMBRE",
];

const MESES_CORTOS = [
  "ENE",
  "FEB",
  "MAR",
  "ABR",
  "MAY",
  "JUN",
  "JUL",
  "AGO",
  "SEP",
  "OCT",
  "NOV",
  "DIC",
];

// Semana que empieza el lunes: las cartas se leen así.
const DIAS = ["L", "M", "M", "J", "V", "S", "D"];

const ISO = /^(\d{4})-(\d{2})-(\d{2})$/;

function dosDigitos(numero: number) {
  return String(numero).padStart(2, "0");
}

/** Fecha de hoy en el huso de la máquina, que es el que usa el input local. */
export function hoyLocal(): string {
  const ahora = new Date();
  return `${ahora.getFullYear()}-${dosDigitos(ahora.getMonth() + 1)}-${dosDigitos(
    ahora.getDate(),
  )}`;
}

/** "2026-11-03" → "3 NOV 2026". */
export function formatearFecha(iso: string): string {
  const partes = ISO.exec(iso);
  if (!partes) return iso || "—";
  const [, anio, mes, dia] = partes;
  return `${Number(dia)} ${MESES_CORTOS[Number(mes) - 1]} ${anio}`;
}

function mesDe(iso: string): string | null {
  return ISO.test(iso) ? iso.slice(0, 7) : null;
}

/** "01 NOV → 02 NOV 2026", sin repetir lo que ya se entiende. */
export function formatearRango(desde: string, hasta: string): string {
  if (!ISO.test(desde) || !ISO.test(hasta)) return "—";
  const [primero, segundo] = desde <= hasta ? [desde, hasta] : [hasta, desde];
  if (primero === segundo) return formatearFecha(primero);
  const [, mesA, diaA] = primero.split("-");
  const [anioB, mesB, diaB] = segundo.split("-");
  const anioA = primero.slice(0, 4);
  if (anioA !== anioB) {
    return `${formatearFecha(primero)} — ${formatearFecha(segundo)}`;
  }
  if (mesA !== mesB) {
    return `${Number(diaA)} ${MESES_CORTOS[Number(mesA) - 1]} — ${Number(diaB)} ${
      MESES_CORTOS[Number(mesB) - 1]
    } ${anioB}`;
  }
  return `${Number(diaA)} — ${Number(diaB)} ${MESES_CORTOS[Number(mesB) - 1]} ${anioB}`;
}

function correrMes(mes: string, paso: number): string {
  const [anio, numero] = mes.split("-").map(Number);
  const fecha = new Date(anio, numero - 1 + paso, 1);
  return `${fecha.getFullYear()}-${dosDigitos(fecha.getMonth() + 1)}`;
}

function etiquetaDia(iso: string): string {
  const partes = ISO.exec(iso);
  if (!partes) return iso;
  const [, anio, mes, dia] = partes;
  return `${Number(dia)} de ${MESES[Number(mes) - 1].toLowerCase()} de ${anio}`;
}

interface Props {
  modo: "range" | "single";
  /** Primer día del rango (o el día elegido, en modo simple). */
  inicio: string;
  /** Último día del rango. En modo simple se ignora. */
  fin: string;
  /** Fechas con datos en disco; vacío cuando el calendario es una referencia. */
  disponibles: Set<string>;
  /** Piso del calendario: los días anteriores quedan bloqueados (fin del rango). */
  minimo?: string;
  disabled?: boolean;
  onElegir: (iso: string) => void;
}

/**
 * Calendario de la hoja.
 *
 * En modo rango, lo que queda fuera de [inicio, fin] se apaga: el día elegido
 * primero marca el comienzo y el segundo cierra el rango. Los días apagados
 * siguen siendo clickeables, porque también son la forma de extender el rango.
 */
export function Calendario({
  modo,
  inicio,
  fin,
  disponibles,
  minimo,
  disabled,
  onElegir,
}: Props) {
  const hoy = hoyLocal();
  const tope = mesDe(hoy) as string;
  // Se navega entre el primer dato (o un año atrás) y el mes en curso.
  const piso = useMemo(() => {
    let minimoMes = mesDe(inicio) ?? tope;
    for (const fecha of disponibles) {
      const mes = mesDe(fecha);
      if (mes && mes < minimoMes) minimoMes = mes;
    }
    const anioAtras = correrMes(tope, -12);
    return minimoMes < anioAtras ? minimoMes : anioAtras;
  }, [inicio, disponibles, tope]);

  const [visible, setVisible] = useState(() => mesDe(inicio) ?? tope);

  // Si el rango cambia de mes desde afuera (input o nuevo producto), se sigue.
  const mesInicio = mesDe(inicio);
  useEffect(() => {
    if (mesInicio) setVisible(mesInicio);
  }, [mesInicio]);

  const celdas = useMemo(() => {
    const [anio, numero] = visible.split("-").map(Number);
    const primero = new Date(anio, numero - 1, 1);
    // getDay(): domingo = 0. Corrido a lunes = 0.
    const huecos = (primero.getDay() + 6) % 7;
    const total = new Date(anio, numero, 0).getDate();
    const dias: (string | null)[] = Array.from({ length: huecos }, () => null);
    for (let dia = 1; dia <= total; dia += 1) {
      dias.push(`${visible}-${dosDigitos(dia)}`);
    }
    return dias;
  }, [visible]);

  const [anio, numero] = visible.split("-").map(Number);
  const inicioRango = inicio <= fin ? inicio : fin;
  const finRango = inicio <= fin ? fin : inicio;

  function clase(iso: string) {
    const partes = ["cal__d"];
    const enRango = iso >= inicioRango && iso <= finRango;
    const borde = iso === inicioRango || iso === finRango;
    const bloqueado = Boolean(minimo) && iso < (minimo as string);
    if (modo === "single") {
      if (iso === inicio) partes.push("cal__d--borde");
    } else if (borde) {
      partes.push("cal__d--borde");
    } else if (enRango) {
      partes.push("cal__d--dentro");
    } else {
      partes.push("cal__d--fuera");
    }
    if (iso === hoy) partes.push("cal__d--hoy");
    if (iso > hoy) partes.push("cal__d--future");
    if (bloqueado) partes.push("cal__d--bloqueado");
    if (disponibles.has(iso)) partes.push("cal__d--dato");
    return partes.join(" ");
  }

  function inactivo(iso: string) {
    return disabled || iso > hoy || (Boolean(minimo) && iso < (minimo as string));
  }

  return (
    <div className="cal">
      <div className="cal__barra">
        <button
          type="button"
          className="cal__paso"
          aria-label="Mes anterior"
          disabled={disabled || visible <= piso}
          onClick={() => setVisible((mes) => correrMes(mes, -1))}
        >
          ‹
        </button>
        <span className="cal__mes" aria-live="polite">
          {MESES[numero - 1]} {anio}
        </span>
        <button
          type="button"
          className="cal__paso"
          aria-label="Mes siguiente"
          disabled={disabled || visible >= tope}
          onClick={() => setVisible((mes) => correrMes(mes, 1))}
        >
          ›
        </button>
      </div>

      <div className="cal__semana" aria-hidden="true">
        {DIAS.map((dia, indice) => (
          <span key={`${dia}-${indice}`}>{dia}</span>
        ))}
      </div>

      <div className="cal__grilla">
        {celdas.map((iso, indice) =>
          iso ? (
            <button
              key={iso}
              type="button"
              className={clase(iso)}
              aria-label={etiquetaDia(iso)}
              aria-pressed={
                modo === "single" ? iso === inicio : iso === inicioRango || iso === finRango
              }
              disabled={inactivo(iso)}
              onClick={() => onElegir(iso)}
            >
              {Number(iso.slice(-2))}
            </button>
          ) : (
            <span key={`hueco-${indice}`} className="cal__hueco" aria-hidden="true" />
          ),
        )}
      </div>
    </div>
  );
}
