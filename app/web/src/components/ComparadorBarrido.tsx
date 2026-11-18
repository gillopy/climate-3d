import { useEffect, useRef, useState } from "react";
import type {
  KeyboardEvent as ReactKeyboardEvent,
  PointerEvent as ReactPointerEvent,
} from "react";

/** Una capa del comparador: la imagen y su etiqueta corta (fecha o nombre). */
export interface CapaBarrido {
  url: string;
  etiqueta: string;
}

interface Props {
  antes: CapaBarrido;
  despues: CapaBarrido;
  /** Línea de contexto: producto y fecha de la corrida. */
  titulo: string;
  alCerrar: () => void;
}

/** Porcentaje que mueve cada flecha; con Shift, cinco veces más. */
const PASO_TECLADO = 2;

/**
 * Rótulo de una capa: "Antes · 2026-06-28" con fecha, "Antes" sin fecha. El
 * respaldo de la etiqueta ya dice "Antes", así que no se repite.
 */
function rotulo(prefijo: string, etiqueta: string): string {
  return etiqueta && etiqueta.toLowerCase() !== prefijo.toLowerCase()
    ? `${prefijo} · ${etiqueta}`
    : prefijo;
}

/**
 * Comparador de barrido: las dos capas apiladas y una línea que se arrastra.
 *
 * A la izquierda se ve el antes; a la derecha, el después (con la máscara del
 * cambio encima). Se monta solo mientras está abierto, así el `showModal`
 * nativo atrapa el foco, oscurece el resto y se lleva Escape sin código extra.
 */
export function ComparadorBarrido({ antes, despues, titulo, alCerrar }: Props) {
  const dialogo = useRef<HTMLDialogElement | null>(null);
  const lienzo = useRef<HTMLDivElement | null>(null);
  const capa = useRef<HTMLImageElement | null>(null);
  const [posicion, setPosicion] = useState(50);
  // Aspecto real de la capa: el lienzo lo copia para que las dos imágenes
  // coincidan píxel a píxel y el barrido no se corra.
  const [aspecto, setAspecto] = useState<number | null>(null);
  const [arrastrando, setArrastrando] = useState(false);

  const medir = (imagen: HTMLImageElement | null) => {
    if (imagen && imagen.naturalWidth > 0 && imagen.naturalHeight > 0) {
      setAspecto(imagen.naturalWidth / imagen.naturalHeight);
    }
  };

  // El modal nativo se abre al montar y devuelve foco y scroll al cerrar.
  useEffect(() => {
    const nodo = dialogo.current;
    if (!nodo) return;
    const focoPrevio = document.activeElement;
    const overflowPrevio = document.body.style.overflow;
    nodo.showModal();
    document.body.style.overflow = "hidden";
    // Con la imagen ya en caché el `onLoad` puede no volver a dispararse.
    medir(capa.current);
    return () => {
      document.body.style.overflow = overflowPrevio;
      if (nodo.open) nodo.close();
      if (focoPrevio instanceof HTMLElement) focoPrevio.focus();
    };
  }, []);

  function moverHasta(clientX: number) {
    const caja = lienzo.current?.getBoundingClientRect();
    if (!caja || caja.width === 0) return;
    const pct = ((clientX - caja.left) / caja.width) * 100;
    setPosicion(Math.min(100, Math.max(0, pct)));
  }

  function alBajar(evento: ReactPointerEvent<HTMLDivElement>) {
    evento.currentTarget.setPointerCapture(evento.pointerId);
    setArrastrando(true);
    moverHasta(evento.clientX);
  }

  function alMover(evento: ReactPointerEvent<HTMLDivElement>) {
    if (arrastrando) moverHasta(evento.clientX);
  }

  function alSoltar(evento: ReactPointerEvent<HTMLDivElement>) {
    setArrastrando(false);
    if (evento.currentTarget.hasPointerCapture(evento.pointerId)) {
      evento.currentTarget.releasePointerCapture(evento.pointerId);
    }
  }

  function alTeclear(evento: ReactKeyboardEvent<HTMLDivElement>) {
    const salto = evento.shiftKey ? PASO_TECLADO * 5 : PASO_TECLADO;
    if (evento.key === "ArrowLeft") {
      setPosicion((previa) => Math.max(0, previa - salto));
    } else if (evento.key === "ArrowRight") {
      setPosicion((previa) => Math.min(100, previa + salto));
    } else if (evento.key === "Home") {
      setPosicion(0);
    } else if (evento.key === "End") {
      setPosicion(100);
    } else {
      return;
    }
    evento.preventDefault();
  }

  return (
    <dialog
      ref={dialogo}
      className="barrido"
      aria-labelledby="barrido-titulo"
      onCancel={(evento) => {
        evento.preventDefault();
        alCerrar();
      }}
      onClick={(evento) => {
        // El backdrop también es el propio dialog: un clic afuera cierra.
        if (evento.target === evento.currentTarget) alCerrar();
      }}
    >
      <div className="barrido__cuerpo">
        <header className="barrido__head">
          <div>
            <h2 className="barrido__title" id="barrido-titulo">
              Comparador de barrido
            </h2>
            <p className="barrido__sub">{titulo} · arrastrá la línea, o movela con ← →</p>
          </div>
          <button type="button" className="btn" onClick={alCerrar} autoFocus>
            Cerrar
          </button>
        </header>

        <div
          className="barrido__marco"
          style={aspecto ? { maxWidth: `calc(74vh * ${aspecto})` } : undefined}
        >
          <div
            ref={lienzo}
            className={`barrido__lienzo${
              arrastrando ? " barrido__lienzo--arrastrando" : ""
            }`}
            style={aspecto ? { aspectRatio: String(aspecto) } : undefined}
            role="slider"
            tabIndex={0}
            aria-label="Posición del barrido entre el antes y el después"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(posicion)}
            aria-valuetext={`${Math.round(posicion)} % del antes`}
            onPointerDown={alBajar}
            onPointerMove={alMover}
            onPointerUp={alSoltar}
            onPointerCancel={alSoltar}
            onLostPointerCapture={() => setArrastrando(false)}
            onKeyDown={alTeclear}
          >
            <img
              ref={capa}
              className="barrido__capa"
              src={despues.url}
              alt={rotulo("Después", despues.etiqueta)}
              draggable={false}
              onLoad={() => medir(capa.current)}
            />
            <div
              className="barrido__capa barrido__capa--antes"
              style={{ clipPath: `inset(0 ${100 - posicion}% 0 0)` }}
            >
              <img
                className="barrido__imagen"
                src={antes.url}
                alt={rotulo("Antes", antes.etiqueta)}
                draggable={false}
              />
            </div>
            <span className="barrido__sello barrido__sello--antes">
              {rotulo("Antes", antes.etiqueta)}
            </span>
            <span className="barrido__sello barrido__sello--despues">
              {rotulo("Después", despues.etiqueta)}
            </span>
            <div
              className="barrido__linea"
              style={{ left: `${posicion}%` }}
              aria-hidden="true"
            >
              <span className="barrido__asa">
                <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
                  <path
                    d="M6 4 2.5 8 6 12M10 4l3.5 4L10 12"
                    stroke="currentColor"
                    strokeWidth="1.4"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </span>
            </div>
          </div>
        </div>

        <footer className="barrido__pie">
          <span>Izquierda: antes · derecha: después con la máscara del cambio.</span>
          <span className="barrido__pos">{Math.round(posicion)} %</span>
        </footer>
      </div>
    </dialog>
  );
}
