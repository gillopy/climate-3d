# Climate 3D — demo congelada para Cloudflare

Demo de solo lectura: el frontend real de Climate 3D contra un dataset
precalculado. Corre entero en Cloudflare, **sin depender de la PC** que renderiza.

No modifica nada del pipeline ni de `app/`: todo lo nuevo vive en `demo/`.
El material de entrada son corridas reales que la app ya había hecho.

## Qué incluye

- **9 productos** con sus renders reales.
- **2 días**: 2026-11-03 y 2026-11-04.
- Imágenes en **WebP** (máx. 1600 px, calidad 82) y videos **MP4 H.264** (1280 px).
- **4 MB** de artefactos en total.
- El build del frontend tal cual, sin recompilar ni tocar `app/web`.

| Producto | Día | Artefactos |
| --- | --- | --- |
| `goes_c13` | 03–04 | 2 cuadros + MP4 |
| `geocolor` | 03–04 | 1 cuadro |
| `goes_truecolor` | 03–04 | 1 cuadro |
| `goes_banda` | 03–04 | 2 cuadros + MP4 |
| `goes_dust` | 04 | 1 cuadro |
| `goes_airmass` | 04 | 1 cuadro |
| `goes_firetemp` | 04 | 1 cuadro |
| `snapshot_paraguay` | 04 | 1 cuadro |
| `precipitacion_ecmwf` | 04 | 2 cuadros + póster + MP4 |

## Cómo funciona

```
navegador → Cloudflare Pages (climate3d.pages.dev)
          ├── /api/*  → _worker.js (misma API, resultados precalculados)
          └── resto   → assets estáticos (dist + previews + media)
```

`_worker.js` es el mismo handler de `src/index.mjs`, bundleado con esbuild.
Pages lo ejecuta en modo avanzado y le pasa el binding `ASSETS` para servir
los archivos estáticos. La URL pública no expone ningún dato de la cuenta.

`src/index.mjs` imita los mismos endpoints que `app/api/main.py`:

| Endpoint | Comportamiento |
| --- | --- |
| `GET /api/catalog` | catálogo real, recortado al dataset |
| `GET /api/catalog/:id/dates` | solo los días congelados |
| `GET /api/jobs` | las 9 corridas precalculadas |
| `POST /api/jobs` | devuelve el resultado **ya terminado** si los parámetros coinciden |
| `GET /api/jobs/:id` | snapshot real de la corrida |
| `GET /api/jobs/:id/events` | SSE: `snapshot` + `closed` |
| `POST /api/jobs/:id/cancel` | no-op (ya está terminada) |
| `POST /api/jobs/:id/reveal` | 409, no hay carpeta local |

El frontend no sabe que está congelado: usa las mismas rutas relativas y el
mismo formato de snapshot. Por eso no hubo que cambiar ni una línea de
`app/web/src`.

## Probar local

```powershell
cd demo
node scripts/dev-server.mjs
# http://127.0.0.1:8787
```

No hace falta `npm install` para probar: el servidor de desarrollo y los tests
usan solo Node.

```powershell
node --test tests/api.test.mjs
```

Los tests cubren catálogo, fechas, las 9 combinaciones, el bloqueo con 409,
el SSE, `reveal` y que todas las imágenes sean WebP livianas.

## Desplegar

Requiere una cuenta de Cloudflare y **Wrangler 4.20 o superior**:

```powershell
cd demo
npm install
npx wrangler login
npm run deploy:pages
```

Queda en **https://climate3d.pages.dev**.

`deploy:pages` compila `_worker.js` y sube `site/` como deploy directo. No
necesita Git, ni build en Cloudflare, ni un dominio propio.

### Alternativa: Workers

El mismo handler también corre como Worker con assets:

```powershell
npm run deploy:worker
```

En ese caso la URL incluye el subdominio de la cuenta
(`https://climate3d.<cuenta>.workers.dev`), por eso Pages es la opción pública.

### Proteger el acceso

Cloudflare Access (Zero Trust) es gratis hasta 50 usuarios y no requiere tocar
código: se agrega una política sobre el dominio del Worker y listo. Es la forma
recomendada para el grupo de prueba.

## Regenerar el dataset

El exportador lee el historial de la app y la carpeta de medios, y reescribe
`site/` y `src/manifest.mjs`:

```powershell
..\app\.venv\Scripts\python.exe tools\export_demo.py
```

Para cambiar los días o sumar productos, se edita la lista `SELECCION` al
principio de `tools/export_demo.py` con carpetas de `app/var/media/cache/`.
Cada entrada tiene que ser una corrida `done` del `historial.jsonl`.

## Límites de la demo

- **Solo combinaciones precalculadas.** Si alguien cambia un parámetro, la API
  responde 409 con un mensaje claro; no se ejecuta nada.
- **Sin datos nuevos.** Para sumar un día hay que exportar y volver a desplegar.
- **`reveal` deshabilitado.** No hay explorador de archivos en la nube.
- **Contenido congelado.** Los logs son los de la corrida original, con las
  rutas locales reemplazadas por `<repo>` / `<local>`.

## Costo

| Ítem | Free |
| --- | --- |
| Worker + assets | 100.000 requests/día |
| Egress | sin cargo |
| Access | hasta 50 usuarios |

$0 para el grupo de prueba. El cómputo queda en la máquina que exporta; el
sitio publicado no la necesita para nada.

## Por qué no corre el backend real en Workers

Un Worker no tiene sistema de archivos persistente, ni `subprocess`, ni ffmpeg,
ni cartopy/eccodes nativos. El pipeline no puede ejecutarse ahí. Esta demo
resuelve el problema al revés: el pipeline corre antes, y Cloudflare solo sirve
resultados. Si algún día hace falta render en vivo, va en un contenedor con
volumen (Fly.io, Render, Hetzner), no en Workers.
