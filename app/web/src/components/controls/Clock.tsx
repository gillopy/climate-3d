import { useEffect, useState } from "react";

function dosDigitos(numero: number): string {
  return String(numero).padStart(2, "0");
}

/** "21:42:07" de un instante, leído en el huso que resulte de sumar el desfase. */
function horaEn(instante: Date, desfaseHoras: number): string {
  const corrido = new Date(instante.getTime() + desfaseHoras * 3_600_000);
  return [
    dosDigitos(corrido.getUTCHours()),
    dosDigitos(corrido.getUTCMinutes()),
    dosDigitos(corrido.getUTCSeconds()),
  ].join(":");
}

/**
 * Reloj del header: el mismo instante en UTC y en Paraguay (UTC-3).
 *
 * Todo el pipeline trabaja en UTC; el segundo renglón existe para no tener que
 * hacer la cuenta mental al elegir una hora o un slot.
 */
export function Reloj() {
  const [ahora, setAhora] = useState(() => new Date());

  useEffect(() => {
    const tic = window.setInterval(() => setAhora(new Date()), 1000);
    return () => window.clearInterval(tic);
  }, []);

  const utc = horaEn(ahora, 0);
  const local = horaEn(ahora, -3);
  const titulo = `${ahora.toISOString().slice(0, 10)} · ${utc} UTC = ${local} UTC-3`;

  return (
    <span className="clock" role="group" aria-label="Hora actual" title={titulo}>
      <span className="clock__linea">
        <span className="clock__zona">UTC</span>
        <time dateTime={ahora.toISOString()}>{utc}</time>
      </span>
      <span className="clock__linea">
        <span className="clock__zona">UTC-3</span>
        <time>{local}</time>
      </span>
    </span>
  );
}
