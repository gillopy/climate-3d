# NISAR — app independiente

Visor y análisis de escenas **NISAR GCOV** en una app propia: se dibuja una caja
sobre el mapa, ASF devuelve las escenas, se baja el `.h5` y se corre el producto
de análisis que elijas (recorte, RVI, cambio de cobertura, serie temporal,
GeoTIFF, agua, incendio o fusión óptica).

Es el flujo NISAR de la consola general, separado en su propio backend y su
propio frontend. **No toca `app/`**: la consola general sigue igual. El pipeline
de cómputo (`descargar/`, `comun/`, `prototipos/`, `datos/`) se reutiliza tal
cual, porque es el código que realmente baja y procesa las escenas.

## Estructura

```text
nisar-app/
  nisar_backend/          # FastAPI: API NISAR + cola de jobs
    config.py             # rutas, Python del pipeline, .env, Earthdata
    nisar.py              # busqueda ASF, browse, timeline, escena, local, Paraguay
    recipes.py            # pedido -> comandos reales del repo
    jobs.py               # cola, subprocesos, SSE, artefactos
    schemas.py            # contrato HTTP
    main.py               # app FastAPI, /media y build del frontend
    tests/test_api.py     # contrato del visor + recetas (sin red)
  frontend/               # Vite + React + Leaflet
    src/components/NisarView.tsx
    src/{App.tsx,nisar.ts,api.ts,types.ts,styles.css}
  requirements.txt        # dependencias del backend (entorno propio)
  var/                    # estado local (ignorado por git)
    media/                # artefactos de los jobs
    nisar/cache/          # browse PNG cacheados
```

## Requisitos

| Cosa | Para qué |
| --- | --- |
| Python 3.11+ | backend |
| Node 20.19+ | compilar el frontend |
| `.venv` en la raíz del repo | los scripts del pipeline (h5py, pyproj, matplotlib, tifffile, rasterio…) |
| `EARTHDATA_USER` / `EARTHDATA_PASSWORD` | bajar los `.h5` desde ASF (el browse no pide credenciales) |

La app usa **dos entornos separados**: `nisar-app/.venv` para FastAPI y el
`.venv` de la raíz para el pipeline. Si arrancás el backend con el Python
equivocado vas a ver `No module named uvicorn`.

## Instalación (una sola vez)

Desde la raíz del repo:

```powershell
# backend propio de esta app
python -m venv nisar-app\.venv
nisar-app\.venv\Scripts\python.exe -m pip install --upgrade pip
nisar-app\.venv\Scripts\python.exe -m pip install -r nisar-app\requirements.txt

# frontend
cd nisar-app\frontend
npm install
cd ..\..
```

## Correr en desarrollo

Dos terminales, desde la raíz del repo.

**Backend** (puerto 8010, separado del 8000 de la consola general):

```powershell
nisar-app\.venv\Scripts\python.exe -m uvicorn nisar_backend.main:app `
  --app-dir nisar-app --port 8010 --reload
```

**Frontend** (puerto 5174, proxy a 8010):

```powershell
cd nisar-app\frontend
npm run dev
```

Abrí **http://127.0.0.1:5174**.

## Correr como app única (sin Vite)

```powershell
cd nisar-app\frontend
npm run build
cd ..\..
nisar-app\.venv\Scripts\python.exe -m uvicorn nisar_backend.main:app `
  --app-dir nisar-app --port 8010
```

Abrí **http://127.0.0.1:8010**: FastAPI sirve el `dist/` y la API en el mismo
puerto.

## Configuración

Variables de entorno (el proceso manda; lo que falte se completa con
`nisar-app/.env` y, después, con el `.env` del repo). Hay una plantilla en
`nisar-app/env.example`:

| Variable | Default | Uso |
| --- | --- | --- |
| `EARTHDATA_USER` / `EARTHDATA_PASSWORD` | — | login de Earthdata para los `.h5` |
| `CLIMATE3D_PYTHON` | `.venv` del repo | intérprete que corre el pipeline |
| `CLIMATE3D_NISAR` | `E:\nisar` (Windows) / `<datos>/nisar` | raíz de los `.h5` |
| `CLIMATE3D_DATOS` | ver `comun/rutas.py` | raíz de datos del pipeline |
| `NISAR_MEDIA` | `nisar-app/var/media` | artefactos de los jobs |
| `NISAR_BROWSE_CACHE` | `nisar-app/var/nisar/cache` | cache del browse de ASF |

## Tests

```powershell
app\.venv\Scripts\python.exe -m unittest discover -s nisar-app\nisar_backend\tests -q
```

Los tests mockean ASF: cubren el contrato de la API, la validación de la caja,
el proxy restringido de browse, la detección de `.h5` en disco, la timeline y el
plan exacto de cada producto. La búsqueda real se comprueba a mano contra la API
pública.

## Qué se reutiliza y qué es propio

- **Reutilizado** (no se duplica): `descargar/nisar.py`, `comun/nisar.py`,
  `comun/rutas.py`, `prototipos/nisar_*.py`, `prototipos/poster_nisar.py` y
  `datos/paraguay_gadm.json`.
- **Propio**: la API (`nisar_backend/`), el frontend (`frontend/`) y sus raíces
  de estado (`var/`). La consola general (`app/`) no cambia.

## Docker

Queda para la próxima etapa: la app ya está separada en backend y frontend y sus
rutas de estado son configurables, así que el Dockerfile solo tiene que copiar
`nisar-app/`, el pipeline compartido y `datos/paraguay_gadm.json`, compilar el
frontend y montar `/data` (o `CLIMATE3D_NISAR`) para los `.h5`.
