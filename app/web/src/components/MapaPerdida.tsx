import { useEffect, useRef } from "react";
import L from "leaflet";
import type { Feature, FeatureCollection, Geometry } from "geojson";

import type { CatastroAfectadas, ParcelaProps } from "../catastro";
import { estiloAfectada, nodoParcela } from "./CatastroPanel";

/** Panes propios: la pérdida va debajo de las parcelas para no tapar el clic. */
const PANE_PERDIDA = "perdidaMascara";
const PANE_PARCELAS = "perdidaParcelas";

/** Atribución de las dos fuentes que se ven juntas en este mapa. */
const ATRIBUCION = "Esri, Maxar, Earthstar Geographics · SNC";

interface Props {
  /** GeoJSON de la máscara de pérdida (EPSG:4326) que dejó el producto. */
  perdida: FeatureCollection<Geometry, Record<string, unknown>>;
  /** Parcelas que devolvió el cruce con el catastro. */
  parcelas: CatastroAfectadas;
  /** `ccatastral` que hay que enfocar al abrir (clic en la lista), o null. */
  foco: string | null;
  titulo: string;
  alCerrar: () => void;
}

/**
 * Mapa de la pérdida detectada contra el catastro: la mancha roja del producto
 * NISAR y, arriba, las parcelas del SNC que la contienen con sus datos.
 *
 * Se monta solo mientras el diálogo está abierto: el `showModal` nativo atrapa
 * el foco y se lleva Escape sin código extra, y el mapa se destruye al cerrar.
 */
export function MapaPerdida({ perdida, parcelas, foco, titulo, alCerrar }: Props) {
  const dialogo = useRef<HTMLDialogElement | null>(null);
  const contenedor = useRef<HTMLDivElement | null>(null);
  const mapaRef = useRef<L.Map | null>(null);
  const capasRef = useRef(new Map<string, L.Path>());
  const estilosRef = useRef(new Map<string, L.PathOptions>());

  useEffect(() => {
    const nodo = dialogo.current;
    if (!nodo) return;
    const focoPrevio = document.activeElement;
    const overflowPrevio = document.body.style.overflow;
    nodo.showModal();
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = overflowPrevio;
      if (nodo.open) nodo.close();
      if (focoPrevio instanceof HTMLElement) focoPrevio.focus();
    };
  }, []);

  useEffect(() => {
    const caja = contenedor.current;
    if (!caja) return;
    const mapa = L.map(caja, {
      zoomControl: true,
      attributionControl: true,
      preferCanvas: true,
    });
    mapaRef.current = mapa;
    mapa.createPane(PANE_PERDIDA).style.zIndex = "330";
    mapa.createPane(PANE_PARCELAS).style.zIndex = "350";

    L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      { maxZoom: 19, attribution: ATRIBUCION },
    ).addTo(mapa);

    // La pérdida es contexto: no captura clics, así el popup siempre es la parcela.
    const mascara = L.geoJSON(perdida, {
      pane: PANE_PERDIDA,
      interactive: false,
      style: () => ({
        color: "#dc2626",
        weight: 0.4,
        opacity: 0.9,
        fillColor: "#dc2626",
        fillOpacity: 0.45,
      }),
    }).addTo(mapa);

    const grupo = L.geoJSON(parcelas, {
      pane: PANE_PARCELAS,
      style: (elemento) => estiloAfectada(elemento as Feature | undefined),
      onEachFeature: (elemento, capa) => {
        if (!(capa instanceof L.Path)) return;
        const props = (elemento.properties ?? {}) as ParcelaProps;
        if (props.ccatastral) {
          capasRef.current.set(props.ccatastral, capa);
          estilosRef.current.set(
            props.ccatastral,
            estiloAfectada(elemento as Feature | undefined),
          );
        }
        capa.bindTooltip(
          props.ccatastral
            ? `${props.ccatastral}${props.padron ? ` · padrón ${props.padron}` : ""}`
            : "Parcela",
          { sticky: true, direction: "top", className: "capas-tooltip", opacity: 1 },
        );
        capa.bindPopup(nodoParcela(props, true), {
          className: "capas-popup",
          maxWidth: 340,
          minWidth: 260,
        });
      },
    }).addTo(mapa);

    const limites = mascara.getBounds();
    if (limites.isValid()) {
      mapa.fitBounds(limites, { padding: [18, 18] });
    } else if (grupo.getBounds().isValid()) {
      mapa.fitBounds(grupo.getBounds(), { padding: [18, 18] });
    }
    // El diálogo recién abierto todavía no tiene tamaño: Leaflet necesita que
    // le avisen para calcular los tiles.
    const medir = () => mapa.invalidateSize();
    const cuadro = window.requestAnimationFrame(medir);
    window.addEventListener("resize", medir);

    return () => {
      window.cancelAnimationFrame(cuadro);
      window.removeEventListener("resize", medir);
      capasRef.current.clear();
      estilosRef.current.clear();
      mapa.remove();
      mapaRef.current = null;
    };
  }, [perdida, parcelas]);

  // Cada pedido de la lista reencuadra la parcela y abre su popup.
  useEffect(() => {
    const mapa = mapaRef.current;
    if (!mapa || !foco) return;
    const capa = capasRef.current.get(foco);
    if (!capa) return;
    capasRef.current.forEach((otra, clave) => {
      const base = estilosRef.current.get(clave) ?? {};
      otra.setStyle(
        clave === foco
          ? { ...base, color: "#ffffff", weight: 3, opacity: 1, fillOpacity: 0.5 }
          : base,
      );
    });
    const conLimites = capa as L.Path & { getBounds?: () => L.LatLngBounds };
    if (conLimites.getBounds) {
      mapa.fitBounds(conLimites.getBounds(), { maxZoom: 16, padding: [28, 28] });
    }
    capa.openPopup();
  }, [foco]);

  return (
    <dialog
      ref={dialogo}
      className="barrido perdida-mapa"
      aria-labelledby="perdida-mapa-titulo"
      onCancel={(evento) => {
        evento.preventDefault();
        alCerrar();
      }}
      onClick={(evento) => {
        if (evento.target === evento.currentTarget) alCerrar();
      }}
    >
      <div className="barrido__cuerpo">
        <header className="barrido__head">
          <div>
            <h2 className="barrido__title" id="perdida-mapa-titulo">
              Pérdida y catastro
            </h2>
            <p className="barrido__sub">
              {titulo} · clic en una parcela para ver finca, padrón y matrícula
            </p>
          </div>
          <button type="button" className="btn" onClick={alCerrar} autoFocus>
            Cerrar
          </button>
        </header>

        <div className="perdida-mapa__marco">
          <div
            ref={contenedor}
            className="perdida-mapa__lienzo"
            role="application"
            aria-label="Mapa de la pérdida detectada y las parcelas afectadas"
          />
        </div>

        <footer className="barrido__pie">
          <span>
            rojo = pérdida detectada (ΔHV) · contorno = parcela del SNC · más rojo,
            mayor fracción del predio afectada
          </span>
          <span className="barrido__pos">{parcelas.total} parcela(s)</span>
        </footer>
      </div>
    </dialog>
  );
}
