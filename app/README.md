# Climate 3D - consola interactiva (demo)

Ejemplo funcional del salto de CLI a aplicación: **receta → job → progreso en vivo → artefacto**.
No reemplaza nada del repo: `descargar/`, `cuadros/`, `animar/` y `comun/` quedan intactos.

## Correr

```powershell
# 1) dependencias del backend, en SU propio entorno
python -m venv app\.venv
app\.venv\Scripts\python.exe -m pip install -r app\requirements.txt

# 2) frontend (una vez)
cd app\web
npm install
npm run build

# 3) servidor: un solo puerto para API + UI
cd app
.venv\Scripts\python.exe -m uvicorn api.main:app --port 8000
```

Abrí `http://127.0.0.1:8000`.

Para desarrollo del frontend, en otra terminal:

```powershell
cd app\web
npm run dev      # http://localhost:5173 con proxy a :8000
```

## Qué hace

| Pieza | Archivo | Rol |
| --- | --- | --- |
| Catálogo | `api/catalog.py` | Los flujos del repo descritos **como datos**: parámetros, opciones, defaults. |
| Contrato | `api/schemas.py` | Lo único que la UI conoce. Ningún flag de CLI cruza esta frontera. |
| Cola | `api/jobs.py` | Un pedido devuelve un id al toque. Un semáforo de 1 los encola de verdad. |
| Render | `api/render.py` | Dibuja. Hoy sintético; mañana llama al producto real. |
| API | `api/main.py` | `/api/catalog`, `/api/jobs`, SSE de progreso, artefactos en `/media`. |
| UI | `web/src` | React + TS. El formulario se arma **desde el esquema**, no hardcodeado. |

Endpoints:

```
GET  /api/health
GET  /api/catalog
GET  /api/catalog/{producto}/dates
POST /api/jobs                { product_id, params, mode }
GET  /api/jobs
GET  /api/jobs/{id}
GET  /api/jobs/{id}/events    text/event-stream
POST /api/jobs/{id}/cancel
GET  /media/...               PNG y GIF generados
```

## Qué es real y qué es demo

**Real**: la arquitectura. Catálogo desde el backend, cola con estado, progreso por SSE,
cancelación, artefactos servidos, formulario generado por esquema, layout de tres columnas.

**Demo**: el dibujo. `api/render.py` produce un campo sintético para que la app funcione en
cualquier máquina sin depender de que los `.nc` estén en disco. También el calendario: si el
disco no tiene salidas del producto, la UI muestra un calendario de demostración **y lo dice**.

## Conectar un script de verdad

Una línea por producto en `catalog.py`:

```python
Product(
    id="goes_c13",
    ...
    command=["cuadros/cuadros_c13_ir.py", "--satelite", "{satelite}", "--banda", "{banda}"],
)
```

Con `command` presente, el modo "Script real del repo" se habilita en la UI. El runner debe
ejecutarlo con el `.venv` del repo (donde viven `cartopy`, `eccodes`, `h5py`), no con el de la app:
son entornos distintos a propósito.

## Entornos separados

- `app\.venv` - solo la app (`fastapi`, `uvicorn`, `numpy`, `pillow`). Ver `app/requirements.txt`.
- `.venv` (raíz) - el pipeline de siempre, sin una dependencia nueva.

No se mezclan: la capa web no necesita `cartopy`, y el pipeline no necesita `fastapi`.

## Límites conocidos

- Una sola instancia y un solo worker. Suficiente para local; para varias personas hace falta
  cola externa (Redis/arq) y almacenamiento de objetos.
- El historial vive en memoria: reiniciar el server lo borra (los artefactos quedan en `app/var/media`).
- El render es bloqueante dentro de un hilo: la UI sigue viva, pero dos renders no corren en paralelo.
- El repo vive en OneDrive: `node_modules`, `.venv` y `var/media` generan mucho tráfico de sync.
  Conviene mover el proyecto fuera de OneDrive antes de crecer.

## Próximo paso natural

Cambiar `render.py` por el llamado al script real, y agregar `titiler` + PMTiles para que el visor
sea un mapa con zoom/pan en vez de imágenes fijas.
