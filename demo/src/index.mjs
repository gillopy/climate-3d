// API de solo lectura para la demo congelada de Climate 3D.
//
// Imita el contrato HTTP de `app/api/main.py` para que el frontend real
// funcione sin cambios. No ejecuta el pipeline: devuelve resultados ya
// precalculados por `tools/export_demo.py`.

import manifest from "./manifest.mjs";

const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
};

const CACHE_CATALOGO = "public, max-age=300";
const CACHE_LISTA = "public, max-age=10";

const COMBOS = manifest.combos;
const BY_ID = new Map(COMBOS.map((combo) => [combo.id, combo]));
const CATALOG = manifest.catalog;
const DATES = manifest.dates;

function json(data, status = 200, cache = "no-store") {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...JSON_HEADERS, "cache-control": cache },
  });
}

function same(a, b) {
  if (a === b) return true;
  if (typeof a !== typeof b || a === null || b === null) return false;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  if (Array.isArray(a)) {
    return a.length === b.length && a.every((valor, i) => same(valor, b[i]));
  }
  if (typeof a === "object") {
    const claves = Object.keys(a);
    if (claves.length !== Object.keys(b).length) return false;
    return claves.every(
      (clave) => Object.prototype.hasOwnProperty.call(b, clave) && same(a[clave], b[clave]),
    );
  }
  return false;
}

function resumen(snapshot) {
  return {
    id: snapshot.id,
    product_id: snapshot.product_id,
    product_name: snapshot.product_name,
    mode: snapshot.mode,
    status: snapshot.status,
    progress: snapshot.progress,
    stage: snapshot.stage,
    created_at: snapshot.created_at,
    started_at: snapshot.started_at,
    finished_at: snapshot.finished_at,
    error: snapshot.error,
  };
}

function eventos(snapshot) {
  const cuerpo =
    `event: snapshot\ndata: ${JSON.stringify({ job: snapshot })}\n\n` +
    `event: closed\ndata: {}\n\n`;
  return new Response(cuerpo, {
    headers: {
      "content-type": "text/event-stream; charset=utf-8",
      "cache-control": "no-store",
      "x-accel-buffering": "no",
    },
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const ruta = url.pathname.replace(/\/+$/, "") || "/";
    const metodo = request.method.toUpperCase();

    if (ruta === "/api/health") {
      return json({
        ok: true,
        demo: true,
        productos: CATALOG.products.length,
        combos: COMBOS.length,
        dias: manifest.days,
        generado: manifest.generated_at,
      });
    }

    if (ruta === "/api/catalog" && metodo === "GET") {
      return json(CATALOG, 200, CACHE_CATALOGO);
    }

    const fechas = ruta.match(/^\/api\/catalog\/([^/]+)\/dates$/);
    if (fechas && metodo === "GET") {
      const id = decodeURIComponent(fechas[1]);
      if (!DATES[id]) return json({ detail: "Producto desconocido" }, 404);
      // El backend real las devuelve de la mas nueva a la mas vieja.
      return json(
        { product_id: id, source: "descubierto", dates: [...DATES[id]].reverse() },
        200,
        CACHE_CATALOGO,
      );
    }

    if (ruta === "/api/jobs" && metodo === "GET") {
      const lista = COMBOS.map((combo) => resumen(combo.snapshot)).sort((a, b) =>
        String(b.created_at).localeCompare(String(a.created_at)),
      );
      return json(lista, 200, CACHE_LISTA);
    }

    if (ruta === "/api/jobs" && metodo === "POST") {
      let cuerpo;
      try {
        cuerpo = await request.json();
      } catch {
        return json({ detail: "Cuerpo JSON invalido" }, 400);
      }
      const productId = cuerpo?.product_id;
      const params = cuerpo?.params ?? {};
      if (typeof productId !== "string") {
        return json({ detail: "Falta product_id" }, 400);
      }
      if (!CATALOG.products.some((producto) => producto.id === productId)) {
        return json({ detail: `Producto desconocido: ${productId}` }, 404);
      }
      const combo = COMBOS.find(
        (candidato) => candidato.product_id === productId && same(candidato.params, params),
      );
      if (!combo) {
        return json(
          {
            detail:
              "Esta demo solo tiene resultados precalculados. Volve a los valores " +
              "por defecto del formulario para generar el render.",
          },
          409,
        );
      }
      return json(combo.snapshot, 201);
    }

    const detalle = ruta.match(/^\/api\/jobs\/([^/]+)$/);
    if (detalle && metodo === "GET") {
      const combo = BY_ID.get(decodeURIComponent(detalle[1]));
      if (!combo) return json({ detail: "Job desconocido" }, 404);
      return json(combo.snapshot, 200, CACHE_CATALOGO);
    }

    const accion = ruta.match(/^\/api\/jobs\/([^/]+)\/(cancel|reveal|events)$/);
    if (accion) {
      const combo = BY_ID.get(decodeURIComponent(accion[1]));
      if (!combo) return json({ detail: "Job desconocido" }, 404);
      if (accion[2] === "cancel" && metodo === "POST") {
        return json(combo.snapshot);
      }
      if (accion[2] === "reveal" && metodo === "POST") {
        return json(
          { detail: "La demo es de solo lectura: no hay carpeta local para abrir." },
          409,
        );
      }
      if (accion[2] === "events" && metodo === "GET") {
        return eventos(combo.snapshot);
      }
      return json({ detail: "Metodo no permitido" }, 405);
    }

    if (ruta.startsWith("/api/")) {
      return json({ detail: `Ruta desconocida: ${ruta}` }, 404);
    }

    if (env?.ASSETS) {
      const respuesta = await env.ASSETS.fetch(request);
      // Pages no trae el fallback SPA de Workers: una navegacion desconocida
      // tiene que terminar en index.html.
      if (
        respuesta.status === 404 &&
        metodo === "GET" &&
        (request.headers.get("accept") ?? "").includes("text/html")
      ) {
        return env.ASSETS.fetch(
          new Request(new URL("/index.html", request.url), { headers: request.headers }),
        );
      }
      return respuesta;
    }
    return new Response("No encontrado", { status: 404 });
  },
};
