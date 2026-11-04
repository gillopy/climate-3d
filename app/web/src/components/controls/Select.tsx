import { useEffect, useId, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import type { ParamOption } from "../../types";

interface Props {
  id?: string;
  value: string;
  options: ParamOption[];
  disabled?: boolean;
  describedBy?: string;
  onChange: (value: string) => void;
}

/**
 * Desplegable de la hoja: botón cerrado + lista propia.
 *
 * El `<select>` nativo no se puede vestir: la lista la dibuja el sistema. Este
 * control mantiene el mismo teclado (flechas, Home/End, Enter, Escape) y el
 * mismo contrato de `combobox`/`listbox`, pero usa la tipografía y los filetes
 * del papel.
 */
export function Select({
  id,
  value,
  options,
  disabled,
  describedBy,
  onChange,
}: Props) {
  const [abierto, setAbierto] = useState(false);
  const [activo, setActivo] = useState(0);
  const caja = useRef<HTMLDivElement | null>(null);
  const base = useId();
  const idLista = `${base}-lista`;
  const elegido = options.findIndex((opcion) => opcion.value === value);

  // La lista se abre parada en la opción vigente.
  useEffect(() => {
    if (abierto) setActivo(elegido >= 0 ? elegido : 0);
  }, [abierto, elegido]);

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

  useEffect(() => {
    if (!abierto) return;
    document
      .getElementById(`${base}-op-${activo}`)
      ?.scrollIntoView({ block: "nearest" });
  }, [abierto, activo, base]);

  function elegir(indice: number) {
    const opcion = options[indice];
    if (!opcion) return;
    onChange(opcion.value);
    setAbierto(false);
  }

  function tecla(evento: KeyboardEvent<HTMLButtonElement>) {
    if (disabled) return;
    if (evento.key === "ArrowDown" || evento.key === "ArrowUp") {
      evento.preventDefault();
      if (!abierto) {
        setAbierto(true);
        return;
      }
      const paso = evento.key === "ArrowDown" ? 1 : -1;
      setActivo((indice) => (indice + paso + options.length) % options.length);
      return;
    }
    if (evento.key === "Home" || evento.key === "End") {
      if (!abierto) return;
      evento.preventDefault();
      setActivo(evento.key === "Home" ? 0 : options.length - 1);
      return;
    }
    if (evento.key === "Enter" || evento.key === " ") {
      evento.preventDefault();
      if (abierto) elegir(activo);
      else setAbierto(true);
      return;
    }
    if (evento.key === "Escape") {
      setAbierto(false);
      return;
    }
    if (evento.key === "Tab") setAbierto(false);
  }

  return (
    <div className="pick" ref={caja}>
      <button
        type="button"
        id={id}
        role="combobox"
        aria-haspopup="listbox"
        aria-expanded={abierto}
        aria-controls={abierto ? idLista : undefined}
        aria-describedby={describedBy}
        aria-activedescendant={
          abierto ? `${base}-op-${activo}` : undefined
        }
        className={abierto ? "pick__control pick__control--open" : "pick__control"}
        disabled={disabled}
        onClick={() => setAbierto((estado) => !estado)}
        onKeyDown={tecla}
      >
        <span className="pick__valor">
          {options[elegido]?.label ?? String(value)}
        </span>
        <span className="pick__chevron" aria-hidden="true" />
      </button>
      {abierto ? (
        <ul className="pick__lista" id={idLista} role="listbox">
          {options.map((opcion, indice) => (
            <li
              key={opcion.value}
              id={`${base}-op-${indice}`}
              role="option"
              aria-selected={opcion.value === value}
              className={
                indice === activo ? "pick__op pick__op--activa" : "pick__op"
              }
              onPointerDown={(evento) => evento.preventDefault()}
              onMouseEnter={() => setActivo(indice)}
              onClick={() => elegir(indice)}
            >
              <span>{opcion.label}</span>
              {opcion.value === value ? (
                <span className="pick__marca" aria-hidden="true" />
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
