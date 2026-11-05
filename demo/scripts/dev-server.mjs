// Servidor local que imita el runtime de Cloudflare: assets estaticos + Worker.
// Sirve para probar la demo sin desplegar nada.

import { createServer } from "node:http";
import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { extname, join, normalize, resolve, sep } from "node:path";
import { Readable } from "node:stream";
import { fileURLToPath } from "node:url";

import worker from "../src/index.mjs";

const ROOT = resolve(fileURLToPath(new URL("../site", import.meta.url)));
const PUERTO = Number(process.env.PORT ?? 8787);

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".webp": "image/webp",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
  ".mp4": "video/mp4",
  ".txt": "text/plain; charset=utf-8",
};

async function cuerpo(req) {
  const partes = [];
  for await (const parte of req) partes.push(parte);
  return Buffer.concat(partes);
}

async function api(req, res) {
  const cuerpoCrudo = await cuerpo(req);
  const sinCuerpo = req.method === "GET" || req.method === "HEAD";
  const request = new Request(`http://127.0.0.1:${PUERTO}${req.url}`, {
    method: req.method,
    headers: req.headers,
    body: sinCuerpo ? undefined : cuerpoCrudo,
  });
  const response = await worker.fetch(request, {});
  const headers = Object.fromEntries(response.headers.entries());
  res.writeHead(response.status, headers);
  if (!response.body) {
    res.end();
    return;
  }
  Readable.fromWeb(response.body).pipe(res);
}

function rangoDe(valor, tamano) {
  const match = /^bytes=(\d*)-(\d*)$/.exec(valor.trim());
  if (!match) return null;
  let inicio = match[1] === "" ? null : Number(match[1]);
  let fin = match[2] === "" ? null : Number(match[2]);
  if (inicio === null && fin === null) return null;
  if (inicio === null) {
    inicio = Math.max(0, tamano - fin);
    fin = tamano - 1;
  } else {
    fin = fin === null ? tamano - 1 : Math.min(fin, tamano - 1);
  }
  if (inicio > fin || inicio >= tamano) return null;
  return { inicio, fin };
}

async function estatico(req, res, forzada) {
  const url = new URL(req.url, `http://127.0.0.1:${PUERTO}`);
  let relativa = forzada ?? decodeURIComponent(url.pathname);
  if (relativa.endsWith("/")) relativa += "index.html";
  const destino = normalize(join(ROOT, relativa));
  if (!destino.startsWith(ROOT + sep) && destino !== ROOT) {
    res.writeHead(403).end("Prohibido");
    return;
  }

  let info;
  try {
    info = await stat(destino);
  } catch {
    // SPA: una ruta sin extension cae en index.html
    if (!extname(relativa)) {
      return estatico(req, res, "/index.html");
    }
    res.writeHead(404).end("No encontrado");
    return;
  }
  if (info.isDirectory()) {
    return estatico(req, res, join(relativa, "index.html"));
  }

  const tipo = MIME[extname(destino).toLowerCase()] ?? "application/octet-stream";
  const esMedia = relativa.startsWith("/media/") || relativa.startsWith("/assets/");
  const headers = {
    "content-type": tipo,
    "cache-control": esMedia ? "public, max-age=31536000, immutable" : "no-cache",
    "accept-ranges": "bytes",
  };

  const rango = req.headers.range ? rangoDe(req.headers.range, info.size) : null;
  if (req.headers.range && !rango) {
    res.writeHead(416, { "content-range": `bytes */${info.size}` }).end();
    return;
  }
  if (rango) {
    headers["content-range"] = `bytes ${rango.inicio}-${rango.fin}/${info.size}`;
    headers["content-length"] = String(rango.fin - rango.inicio + 1);
    res.writeHead(206, headers);
    createReadStream(destino, { start: rango.inicio, end: rango.fin }).pipe(res);
    return;
  }

  headers["content-length"] = String(info.size);
  res.writeHead(200, headers);
  if (req.method === "HEAD") {
    res.end();
    return;
  }
  createReadStream(destino).pipe(res);
}

const servidor = createServer(async (req, res) => {
  try {
    if (req.url?.startsWith("/api/")) {
      await api(req, res);
      return;
    }
    await estatico(req, res);
  } catch (error) {
    console.error(error);
    if (!res.headersSent) res.writeHead(500, { "content-type": "text/plain" });
    res.end("error");
  }
});

servidor.listen(PUERTO, () => {
  console.log(`demo: http://127.0.0.1:${PUERTO}`);
});
