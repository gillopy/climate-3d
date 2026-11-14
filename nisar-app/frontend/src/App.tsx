import { useEffect, useState } from "react";

import { getHealth } from "./api";
import { NisarView } from "./components/NisarView";
import type { HealthResponse } from "./types";

/**
 * App NISAR: una sola vista. La barra superior muestra si el pipeline, el login
 * de Earthdata y la raiz de datos estan listos; el resto lo maneja el visor.
 */
export default function App() {
  const [salud, setSalud] = useState<HealthResponse | null>(null);

  useEffect(() => {
    let vigente = true;
    getHealth()
      .then((datos) => {
        if (vigente) setSalud(datos);
      })
      .catch(() => {
        if (vigente) setSalud(null);
      });
    return () => {
      vigente = false;
    };
  }, []);

  const estado = (listo: boolean) =>
    `health__item ${listo ? "health__item--ok" : "health__item--warn"}`;

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand__mark" aria-hidden="true">
            <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="5.6" stroke="currentColor" strokeWidth="1.2" />
              <circle cx="8" cy="8" r="2.6" stroke="currentColor" strokeWidth="1.2" />
              <path d="M8 8 13 3" stroke="currentColor" strokeWidth="1.2" />
              <circle cx="8" cy="8" r="0.9" fill="currentColor" />
            </svg>
          </span>
          <span className="brand__txt">
            <h1>NISAR</h1>
            <span className="brand__sub">radar viewer</span>
          </span>
        </div>
        <div className="health">
          {salud ? (
            <>
              <span className={estado(salud.repo_ready)} title={salud.repo_python}>
                <span className="health__swatch" aria-hidden="true" />
                {salud.repo_ready ? "pipeline listo" : "sin .venv del repo"}
              </span>
              <span className={estado(salud.earthdata_configured)}>
                <span className="health__swatch" aria-hidden="true" />
                {salud.earthdata_configured ? "Earthdata listo" : "falta Earthdata"}
              </span>
              <span className={estado(salud.nisar_root_exists)} title={salud.nisar_root}>
                <span className="health__swatch" aria-hidden="true" />
                {salud.nisar_root_exists ? "datos NISAR" : "sin .h5 en disco"}
              </span>
            </>
          ) : (
            <span className="health__item health__item--count">
              leyendo el entorno
            </span>
          )}
        </div>
      </header>

      <NisarView />
    </div>
  );
}
