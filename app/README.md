# Climate 3D - consola interactiva

Aplicación web sobre el pipeline real del repo: elegís producto, fechas, banda,
paleta, resolución y si querés animación; el job corre los scripts de
`descargar/`, `cuadros/` y `animar/` con el `.venv` del repo, y el progreso llega
en vivo. No reemplaza nada: los scripts y el pipeline siguen siendo los mismos.

Dos decisiones que definen el resultado:

- **Cualquier fecha es válida.** Las fechas que ya están en disco son una pista,
  no un límite. Si la ventana no tiene datos, la receta incluye la descarga y
  trae exactamente los slots que el render va a pedir.
- **La vista es la del satélite, no un recorte.** Por defecto se renderiza el
  disco completo en la proyección nativa de ABI. Si pedís globo, se centra en el
  **punto subsatelital** (75.2 W para GOES-East, 137.2 W para GOES-West, lat 0),
  que es el centroide real de lo captado.

## Correr

```powershell
# 1) dependencias de la app, en SU propio entorno
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

Para desarrollo del frontend, en otra terminal: `cd app\web; npm run dev`
(`http://localhost:5173` con proxy a `:8000`).

## Cómo funciona

```
catálogo (api/catalog.py)
   ↓  el usuario elige parámetros
receta (api/schemas.py)
   ↓
comandos reales (api/recipes.py)      ← traduce a flags de los scripts del repo
   ↓
cola + subprocess (api/jobs.py)        ← corre con el Python del repo, sigue stdout
   ↓  SSE
UI (web/src)                           ← formulario armado desde el esquema
   ↓
artefactos (/media/...)
```

| Pieza | Archivo | Qué hace |
| --- | --- | --- |
| Catálogo | `api/catalog.py` | Productos y **solo** los controles que su script acepta. |
| Receta | `api/recipes.py` | Convierte la receta en `descargar_goes.py --sat G19 ...`, `cuadros_goes.py ...`, `animar/armar.py ...`. |
| Cola | `api/jobs.py` | Un worker, jobs encolados, stdout a streaming, cancelación por árbol de procesos. |
| Preview | `api/render.py` | Campo sintético para probar la UI sin datos ni pipeline. |
| API | `api/main.py` | `/api/catalog`, `/api/jobs`, SSE, `/media`. |
| UI | `web/src` | React + TS, formulario generado desde el esquema. |

Endpoints:

```
GET  /api/health
GET  /api/catalog
GET  /api/catalog/{producto}/dates?satelite=G19&banda=C13
POST /api/jobs                { product_id, params, mode: "real" | "preview" }
GET  /api/jobs
GET  /api/jobs/{id}
GET  /api/jobs/{id}/events    text/event-stream
POST /api/jobs/{id}/cancel
GET  /media/...
```

## Productos conectados (flags reales)

| Producto | Descarga | Render | Animación |
| --- | --- | --- | --- |
| GOES (C13/C02/C04, G19/G18/G16) | `descargar_goes.py --sat --banda --desde --hasta --paso` | `cuadros_goes.py --sat --banda --desde --n --paso --px --paleta [--globo --centro LON 0] --out --lote 1` | `armar.py --frames --fps --formato mp4 --salida` |
| MUR SST | `mur_sst.py --desde --hasta --paso --px --out` | `cuadros_mur.py --desde --hasta --paso --px --out` | idem |
| Precipitación ECMWF | `precipitacion_ecmwf.py --modelo --fecha --ciclo --hasta-hora --paso` | `cuadros_precipitacion.py ... --px --fondo-globo --salidas` | idem |
| Anomalía 2 m ECMWF | `anomalia_2t_ecmwf.py ...` | `cuadros_anomalia_2t.py ...` | idem |
| Follaje PACE | `pace_landvi.py --desde --hasta` | `cuadros_follaje.py --desde --hasta --px --out` | idem |

### Fechas y datos faltantes

```
ventana elegida
   ├── hay .nc/esquirlos locales  → render directo (sin red)
   ├── no hay nada               → descarga + render, siempre
   ├── forzar descarga (toggle)  → descarga + render, aunque haya datos
   └── render falla              → descarga de rescate + un reintento
```

El descargador de GOES devuelve 1 si algún slot no existe (huecos normales en la
grilla). Eso **no** aborta el job: se registra como advertencia y se sigue con lo
que bajó. Si aun así no hay con qué renderizar, el error dice qué pasó.

### Vista y centro

| Producto | Por defecto | Con globo 3D |
| --- | --- | --- |
| GOES | disco nativo, proyección ABI | centro en el punto subsatelital |
| MUR, precipitación, anomalía, follaje | default del script del repo | igual |

`cuadros_goes.py` centra en `-58 -23` (Paraguay) si no le pasás `--centro`. La app
siempre le pasa el subsatelital cuando se pide globo, así que el resultado no
depende de ese default.

Decisiones que vienen de leer los scripts, no de suponer:

- **Solo se muestran los controles que existen.** GOES expone `--paleta`; MUR no
  expone paleta, así que MUR no tiene selector de paleta.
- **GOES arranca en el primer slot que hay en disco** cuando no se fuerza
  descarga: `cuadros_goes.py` asume una grilla contigua de 10 minutos y revienta
  con `KeyError` si falta un slot, así que la receta avanza solo mientras el
  siguiente slot exista. Con descarga, en cambio, la receta manda (`--paso`
  propio) y baja exactamente los slots que va a renderizar.
- **Nada de 800 px.** La tipografía del póster se superpone por debajo de
  ~1400 px; el mínimo ofrecido es 1400.

## Caché de renders

La carpeta de trabajo es `app/var/media/cache/<firma>/`, donde la firma es un
hash de producto + modo + parámetros (sin `descargar`, que no cambia el render).

Consecuencias:

- Reordenar la misma receta **reusa los cuadros**: los scripts ya saltean PNG
  existentes si el sello de render no cambió. Medido: 27 s → 6 s.
- Un render largo se puede retomar: matá el server, volvé a pedir lo mismo.
- La caché **no** se borra al podar el historial de jobs. Se limpia a mano:
  `Remove-Item -Recurse app\var\media\cache`.

## Cómo se cancela

`Cancelar` mata el árbol de procesos completo (psutil). Los scripts de render
lanzan un hijo por lote y ese hijo hereda el stdout: matar solo al padre deja el
hijo renderizando y el pipe abierto. Verificado: cancelar en 79 % deja el job en
`cancelled`, sin procesos huérfanos y sin bloquear el siguiente job.

## Qué necesita cada cosa

- **Render**: el `.venv` del repo y los datos en `CLIMATE3D_DATOS`
  (por defecto `D:\Users\guill\dataset era5`).
- **Descargar** (opcional, apagado por defecto): internet y credenciales según la
  fuente — NOAA S3 para GOES/MUR, NASA Earthdata para LACE/PACE, CDS para ERA5.
  Si la descarga falla, el job muestra el error real del script.
- **Preview**: nada. Dibuja un campo sintético para probar la UI.

## Entornos separados

- `app\.venv` — la app: `fastapi`, `uvicorn`, `numpy`, `pillow`, `psutil`.
- `.venv` (raíz) — el pipeline de siempre, sin una dependencia nueva.

Nunca se mezclan: la capa web no necesita `cartopy`, y el pipeline no necesita
`fastapi`.

## Límites conocidos

- Un solo worker. Dos personas pidiendo renders a la vez ven la cola, no
  paralelismo.
- El historial de jobs vive en memoria: reiniciar el server lo borra (los
  artefactos quedan en `app/var/media/cache`).
- Sin autenticación: es local.
- El repo vive en OneDrive: `node_modules`, `.venv` y la caché de renders generan
  mucho tráfico de sincronización. Conviene moverlo fuera antes de crecer.
- Progreso por líneas de log: en descargas largas la barra se queda quieta hasta
  que el script imprime. Es honesto, no inventado.
- El archivo de cada fuente tiene retención: NOAA S3 conserva GOES unas semanas.
  Una fecha demasiado vieja se descarga con errores y el job falla avisando.

## Próximo paso natural

`titiler` + PMTiles para que el visor tenga zoom/pan en vez de imágenes fijas, y
una cola externa (Redis/arq) cuando haya más de una persona usándolo.
