import assert from "node:assert/strict";
import { existsSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import test from "node:test";

import worker from "../src/index.mjs";
import manifest from "../src/manifest.mjs";

const SITE = resolve(fileURLToPath(new URL("../site", import.meta.url)));

function pedir(ruta, init = {}) {
  return worker.fetch(new Request(`https://demo.local${ruta}`, init), {});
}

async function json(ruta, init) {
  const respuesta = await pedir(ruta, init);
  return { estado: respuesta.status, cuerpo: await respuesta.json() };
}

test("el catalogo es el real, recortado y sin rutas locales", async () => {
  const { estado, cuerpo } = await json("/api/catalog");
  assert.equal(estado, 200);
  const ids = cuerpo.products.map((producto) => producto.id);
  assert.equal(new Set(ids).size, ids.length, "hay productos duplicados");
  const conCombos = [...new Set(manifest.combos.map((combo) => combo.product_id))];
  assert.deepEqual([...ids].sort(), conCombos.sort());
  assert.equal(cuerpo.repo_ready, true);
  assert.ok(!JSON.stringify(cuerpo).includes(":\\"), "no debe filtrar rutas de Windows");
  assert.ok(!cuerpo.media_root.includes("var"));
  for (const producto of cuerpo.products) {
    assert.ok(producto.params.length > 0, `${producto.id} sin controles`);
    assert.equal(producto.command, null);
  }
});

test("cada producto ofrece solo los dos dias congelados", async () => {
  const { cuerpo: catalogo } = await json("/api/catalog");
  for (const producto of catalogo.products) {
    const { estado, cuerpo } = await json(`/api/catalog/${producto.id}/dates`);
    assert.equal(estado, 200, producto.id);
    assert.ok(cuerpo.dates.length >= 1, producto.id);
    for (const dia of cuerpo.dates) {
      assert.ok(manifest.days.includes(dia), `${producto.id} ofrece ${dia} fuera del dataset`);
    }
  }
});

test("los parametros por defecto del formulario generan sin tocar nada", async () => {
  const { cuerpo: catalogo } = await json("/api/catalog");
  for (const producto of catalogo.products) {
    const params = Object.fromEntries(producto.params.map((spec) => [spec.name, spec.default]));
    const { estado, cuerpo } = await json("/api/jobs", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ product_id: producto.id, params }),
    });
    assert.equal(estado, 201, `${producto.id}: ${JSON.stringify(cuerpo)}`);
    assert.equal(cuerpo.status, "done");
    assert.ok(cuerpo.artifacts.length > 0, producto.id);
    for (const artefacto of cuerpo.artifacts) {
      assert.ok(artefacto.url.startsWith("/media/"), artefacto.url);
      assert.ok(existsSync(resolve(SITE, `.${artefacto.url}`)), `falta ${artefacto.url}`);
      assert.equal(statSync(resolve(SITE, `.${artefacto.url}`)).size, artefacto.bytes);
    }
  }
});

test("una combinacion fuera del dataset se bloquea con un mensaje claro", async () => {
  const producto = manifest.catalog.products[0];
  const params = Object.fromEntries(producto.params.map((spec) => [spec.name, spec.default]));
  const { estado, cuerpo } = await json("/api/jobs", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ product_id: producto.id, params: { ...params, fps: 999 } }),
  });
  assert.equal(estado, 409);
  assert.match(cuerpo.detail, /precalculad/i);
});

test("el historial y el detalle devuelven corridas terminadas", async () => {
  const { estado, cuerpo } = await json("/api/jobs");
  assert.equal(estado, 200);
  assert.equal(cuerpo.length, manifest.combos.length);
  for (const fila of cuerpo) {
    assert.equal(fila.status, "done");
  }
  const uno = await json(`/api/jobs/${cuerpo[0].id}`);
  assert.equal(uno.estado, 200);
  assert.equal(uno.cuerpo.id, cuerpo[0].id);
  assert.ok(Array.isArray(uno.cuerpo.plan));
});

test("el SSE entrega snapshot y cierra, como el backend real con un job terminado", async () => {
  const id = manifest.combos[0].id;
  const respuesta = await pedir(`/api/jobs/${id}/events`);
  assert.equal(respuesta.status, 200);
  assert.match(respuesta.headers.get("content-type"), /text\/event-stream/);
  const texto = await respuesta.text();
  assert.match(texto, /event: snapshot/);
  assert.match(texto, /event: closed/);
  const datos = JSON.parse(texto.split("data: ")[1].split("\n")[0]);
  assert.equal(datos.job.id, id);
});

test("reveal no abre nada y las rutas desconocidas no inventan datos", async () => {
  const reveal = await pedir(`/api/jobs/${manifest.combos[0].id}/reveal`, { method: "POST" });
  assert.equal(reveal.status, 409);
  assert.equal((await json("/api/jobs/nope")).estado, 404);
  assert.equal((await json("/api/nada")).estado, 404);
});

test("las imagenes publicadas son WebP y pesan poco", async () => {
  const imagenes = manifest.combos.flatMap((combo) =>
    combo.snapshot.artifacts.filter((artefacto) => artefacto.kind === "image"),
  );
  assert.ok(imagenes.length > 0);
  for (const imagen of imagenes) {
    assert.match(imagen.url, /\.webp$/);
    assert.ok(imagen.bytes < 1_200_000, `${imagen.url} pesa ${imagen.bytes}`);
  }
});
