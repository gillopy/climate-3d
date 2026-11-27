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

## Cómo correrlo

> ¿Solo querés usarla? Con Docker no hace falta nada de lo que sigue: corré
> `.\despliegue\setup.ps1` y listo. Ver [`../docs/DOCKER.md`](../docs/DOCKER.md).

Todo se corre en PowerShell **desde la raíz del repo** (`climate 3d\`), salvo
donde se aclare otra carpeta. No hace falta activar ningún entorno virtual: se
llama al `python.exe` del entorno directo, así que la política de ejecución de
PowerShell no molesta.

### 1. Qué necesitás

| Cosa | Versión | Para qué |
| --- | --- | --- |
| Python | 3.12 o superior (probado con 3.14.2) | el backend |
| Node.js + npm | Node 20.19 o superior (probado con 24.15.0) | compilar el frontend |
| `.venv` de la raíz | — | un solo entorno: pipeline y consola |
| carpeta de datos | — | los `.nc` / `.npz` ya descargados |

Comprobalo en dos segundos:

```powershell
python --version
uv --version
node --version
npm --version
Test-Path .venv\Scripts\python.exe
```

Si `uv` no existe, instalalo con `winget install astral-sh.uv` (o `pip install uv`). Si
`Test-Path` devuelve `False`, falta el entorno: `uv sync` lo crea (ver "Problemas
comunes").

### 2. Instalación (una sola vez)

```powershell
# entorno unico: pipeline y consola juntos (uv lee pyproject.toml + uv.lock)
uv sync

# frontend: se compila una vez y el backend lo sirve
cd app\web
npm install
npm run build
cd ..\..
```

Son **un solo entorno**: `pyproject.toml` declara el pipeline (`cartopy`, `xarray`, etc.) y
la consola (`fastapi`, `uvicorn`, `psutil`), y `uv sync` arma el mismo `.venv` para los dos.
No hay un segundo venv que instalar ni que elegir.

### 3. Arrancar

Doble clic en `despliegue\ARRANCAR.bat` (o `.\despliegue\ARRANCAR.ps1` desde la raíz del
repo). Pregunta **dónde guardar todo** — datos, salidas y caché —, valida la carpeta, la
recuerda para la próxima y levanta el servidor. Enter acepta la que ya está configurada.

Esa terminal queda ocupada: **es el servidor**. Dejala abierta y abrí:

**http://127.0.0.1:8000**

Un solo puerto sirve la API y la UI. Para cortarlo: `Ctrl+C` en esa terminal.

El comando largo, si preferís no usar el asistente (usa lo ya configurado):

```powershell
.venv\Scripts\python.exe -m uvicorn api.main:app --app-dir app --port 8000
```

### 4. Confirmar que arrancó bien

`http://127.0.0.1:8000/api/health` tiene que devolver algo así:

```json
{"ok": true, "productos": 21, "data_root": "D:\\Users\\guill\\dataset era5",
 "data_root_exists": true, "repo_ready": true, "repo_python": "...\\.venv\\Scripts\\python.exe"}
```

Y en la UI, arriba a la derecha, los tres indicadores:

| Indicador | Significa |
| --- | --- |
| `21 productos` | el catálogo cargó |
| `pipeline listo` | encontró el `.venv` de la raíz |
| `datos en disco` | encontró la carpeta de datos |

Si alguno falta, está en la tabla de abajo.

### 5. Tocar el frontend (modo desarrollo)

Dos terminales:

```powershell
# terminal 1 - backend
.venv\Scripts\python.exe -m uvicorn api.main:app --app-dir app --port 8000

# terminal 2 - frontend con recarga en caliente
cd app\web
npm run dev
```

Abrí **http://localhost:5173** (con `127.0.0.1:5173` no responde: Vite escucha en
`localhost`). El proxy manda `/api` y `/media` al `:8000`, así que los cambios de
React se ven al instante sin recompilar.

Cuando termines de tocar código, volvé al modo de un solo puerto:

```powershell
cd app\web
npm run build
```

### 6. Puerto y carpeta de datos

Otro puerto (la UI va con el mismo, no hay nada más que tocar):

```powershell
.\despliegue\ARRANCAR.ps1 -Port 8001
```

Otra raíz de trabajo:

```powershell
.\despliegue\ARRANCAR.ps1 -Raiz "D:\climate3d"
```

La raíz elegida queda guardada en `%LOCALAPPDATA%\climate3d\config.json` (no en el repo:
el repo se sincroniza y las rutas son de esta máquina). De ella cuelgan las descargas, las
`salidas\` y `.media\` — artefactos de los jobs, historial y cachés.

Para ver o cambiar las raíces sin levantar el server:

```powershell
.venv\Scripts\python.exe comun\rutas.py --show
```

| Variable | Qué mueve | Default |
| --- | --- | --- |
| `CLIMATE3D_DATOS` | datos crudos y `salidas\` | el del archivo, o `D:\Users\guill\dataset era5` |
| `CLIMATE3D_MEDIA` | artefactos, historial y cachés | `<datos>\.media` |
| `CLIMATE3D_NISAR` | los `.h5` de NISAR (~1.9 GB cada uno) | `<datos>\nisar` |
| `CLIMATE3D_CONFIG` | el archivo de configuración | `%LOCALAPPDATA%\climate3d\config.json` |

Las variables viven en la terminal actual: al cerrarla se pierde. Lo que se guarda con el
asistente, no.

El asistente además apunta `TEMP`/`TMP` a `<raíz>\.tmp`: los temporales de los renders
(h5py, matplotlib, PIL) pesan cientos de MB y en un disco lleno hacen fallar el job con un
`MemoryError` que no tiene nada que ver con la RAM.

### 7. Problemas comunes

| Síntoma | Causa | Solución |
| --- | --- | --- |
| `No module named uvicorn` | el `.venv` se creó sin la parte web | `uv sync` |
| `[Errno 10048] error while attempting to bind ... :8000` | el puerto ya está ocupado por otra instancia | cerrá la otra terminal o usá `--port 8001` |
| La página dice "Falta el build del frontend" | no corriste `npm run build` | `cd app\web; npm run build` |
| Indicador `pipeline listo` apagado / `repo_ready: false` | falta el `.venv` de la raíz | `python -m venv .venv` y `uv sync` (es pesado) |
| Indicador `datos en disco` apagado / `data_root_exists: false` | la carpeta de datos no está en la ruta por defecto | `$env:CLIMATE3D_DATOS = "<ruta>"` y reiniciá el server |
| `npm install` falla | Node demasiado viejo para Vite 7 | instalá Node 20.19+ |
| `npm` no se reconoce | falta Node.js | instalá Node.js LTS y abrí una terminal nueva |
| En modo dev, `127.0.0.1:5173` no abre | Vite escucha en `localhost` | usá `http://localhost:5173` |
| Un job falla con 404/403 al descargar | sin red o sin credenciales (NOAA S3, NASA Earthdata, CDS) | pedí fechas que ya estén en disco, o configurá las credenciales |
| Un job muere con `cannot open '/MEMFS/definitions/boot.def'`, `MemoryError` o `Unable to allocate` | el disco del sistema está lleno y Windows no puede agrandar el archivo de paginación: el commit se agota y hasta un `malloc` de 8 MB falla (no es la fecha ni los datos) | liberá espacio en `C:`, cerrá el navegador y reintentá; lo descargado y los cuadros hechos se reusan. La app avisa y espera hasta 45 s a que se libere memoria antes de largar cada paso |

Para ver qué proceso tiene tomado el puerto:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen | Select-Object OwningProcess
```

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
| API | `api/main.py` | `/api/catalog`, `/api/jobs`, SSE, `/media`. |
| UI | `web/src` | React + TS, formulario generado desde el esquema. |

Endpoints:

```
GET  /api/health
GET  /api/catalog
GET  /api/catalog/{producto}/dates?satelite=G19&banda=C13
POST /api/jobs                { product_id, params }
GET  /api/jobs
GET  /api/jobs/{id}
GET  /api/jobs/{id}/events    text/event-stream
POST /api/jobs/{id}/cancel
GET  /media/...
```

## Productos conectados (flags reales)

| Producto | Descarga | Render | Animación |
| --- | --- | --- | --- |
| GOES IR (C13, G19/G18/G16) | `descargar_goes.py --sat --banda C13 --desde --hasta --paso` | `cuadros_c13_ir.py --desde --n --paso --px --centro LON 0 --radio 90 --datos --out --frames --lote 1` | `armar.py --frames --fps --formato mp4 --salida` |
| GOES banda ABI (C01-C16) | `descargar_goes.py --sat --banda --desde --hasta --paso` | `poster_goes_banda.py --banda --sat --desde --n --paso --px --paleta --centro --recorte` | `armar.py` sobre `--frames` |
| GOES LST (ABI L2, 2 km) | `descargar_goes_lst.py --sat --desde --hasta --paso 60` | `poster_goes_lst.py --sat --desde --n --paso 60 --px --vmin --vmax --out` | `armar.py` sobre `--frames` |
| GOES color real (C01+C02+C03) | `truecolor_goes.py --desde --n --paso --sat` | `poster_goes_truecolor.py --centro LON 0 --px --out` o `poster_goes_disco.py --px --out` | `armar.py` sobre la serie |
| MUR SST (globo oscuro) | `mur_sst.py --desde --hasta --paso --px --out` | `cuadros_mur.py --desde --hasta --paso --px --out` | `armar.py` |
| MUR SST poster realista | `mur_sst.py ...` | `poster_mur_realista.py --crudo --px --paleta [--trend] --out` | — |
| Precipitación ECMWF | `precipitacion_ecmwf.py --modelo --fecha --ciclo --hasta-hora --paso 3` | `cuadros_precipitacion.py ... --px --fondo-globo --salidas` | `armar.py` |
| Anomalía 2 m ECMWF | `anomalia_2t_ecmwf.py ... --paso 3` | `cuadros_anomalia_2t.py ...` | `armar.py` |
| Viento 250 mb (IFS o GFS) | `viento_250_mslp.py --modelo --fecha --ciclo --hasta-hora --paso 3` | `cuadros_viento_250.py ... --modelo --px --fondo-globo --salidas` | `armar.py` |
| Snapshot Paraguay | `snapshot_paraguay.py --capa --fecha --hora --minuto --px --margen --out` | `snapshot_paraguay.py --capa --fecha --entrada --salidas [--sin-borde]` | — |
| Follaje PACE | `pace_landvi.py --desde --hasta` | `cuadros_follaje.py --desde --hasta --px --out` | `armar.py` |
| Meteosat-12 (MTG) | `meteosat.py --desde --n --paso --px --capa --encuadre` | `cuadros_meteosat.py --desde --n --paso --px --capa --encuadre [--centro 0 0]` | `armar.py` sobre `--frames` |
| CBERS-4A recorte | `cbers.py --zona --km --detalle --desde --hasta` | `cuadros_cbers.py --entrada --out` | — |

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

### Corridas ECMWF: cuál se usa

`data.ecmwf.int` **no publica la corrida del día apenas cierra el ciclo**, y borra
las viejas por retención. Pedir "hoy 00z" a primera hora da 404 en todos los
pasos — es exactamente el error que se veía antes.

Antes de planear, la app consulta qué corrida existe de verdad y ajusta la
receta:

1. Mismo ciclo hacia atrás, hasta 7 días → cubre "la de hoy todavía no salió".
2. Si no hay, hacia adelante hasta hoy → cubre una fecha que ya salió del archivo.
3. Si la corrida publica menos horizonte que el pedido, lo recorta.

Cada ajuste queda en el log con nombre y apellido:

```
la corrida 2026-10-31 00z no esta publicada; uso 2026-10-30 00z
la corrida 2026-10-30 00z publica hasta 144 h; recorto el horizonte de 240 h
la fecha 2026-10-20 ya no esta en el archivo de ECMWF; uso la mas cercana: 2026-10-28 12z
```

Si no hay red para verificar, se registra una advertencia y se sigue con la
corrida pedida: nunca se bloquea el job por no poder consultar.

Los crudos de ECMWF se detectan por carpeta
(`crudos_precip_<modelo>_<fecha>_<ciclo>z`, `crudos_anom2t_<modelo>_<fecha>_<ciclo>z`).
Si no están, la descarga entra al plan sin que haya que tocar el toggle.

### Horario de los GOES: el cenit

El color real necesita sol. El slot se elige con el **sol sobre el punto
subsatelital**: para G19 (75.2 W) son las **17:00 UTC = 14:00 UTC-3**, el
"mediodía" del disco.

- Si hay un `.nc` a menos de 30 minutos de ese horario, se usa ese (por ejemplo
  el slot de 16:50, que en hora local es 13:50).
- Si no, se descarga el slot del cenit. Nunca se renderiza un horario nocturno
  solo porque "era el dato más cercano": eso producía globos a oscuras.
- Con `anima` encendido, la serie arranca media hora antes del cenit.

### Muestras de cada producto

`app/tools/previews.py` genera un WebP por producto desde un **render real** y lo
deja en `app/web/public/previews/<producto>.webp`. La API lo expone como
`preview` y la UI lo muestra en la tarjeta y arriba del formulario. Si cambia un
estilo, se vuelve a correr:

```powershell
.venv\Scripts\python.exe app\tools\previews.py
```

### Productos de color

Hay cuatro formas distintas de ver "color" y no son intercambiables:

| Producto | Qué es | Fuente |
| --- | --- | --- |
| **Color real (3 bandas)** | compuesto C01+C02+C03 con la receta CIMSS | `.nc` del ABI |
| **Banda cruda, estilo color real** | una banda ABI coloreada, con el encuadre limpio; las 16 del ABI | `.nc` del ABI |
| **GeoColor** | RGB ya mezclado: día real, IR y luces de noche | GIBS |
| **NOAA-20 true color** | mosaico diario global de VIIRS | GIBS |

GeoColor y NOAA-20 son capas de GIBS, no capturas instantáneas: GeoColor es un
disco GOES con la mezcla día/noche ya hecha, y NOAA-20 es una **composición
diaria** (un cuadro por día, sin horarios).

### Abrir la carpeta del trabajo

Cuando un job termina, el panel muestra **Abrir carpeta**: el servidor abre el
explorador en la carpeta de la caché de ese job (`POST /api/jobs/{id}/reveal`).
Solo abre la carpeta que el servidor calculó para ese job; no acepta rutas del
cliente.

### La paleta GIBS y su escala

La rampa `clean_ir` de `comun/paleta_gibs.py` es la de Worldview y **es correcta**:
237 bins copiados del XML oficial. El problema era la **escala**.

- Himawari la usa con el rango fijo de GIBS: **-92.1 a 56.9 °C**.
- GOES la usaba con percentiles 0.5/99.5 del primer cuadro.

Con percentiles, la misma temperatura caía en otro color: a -40 °C GIBS pinta
verde y el póster de GOES pintaba rojo. Ahora, cuando la paleta es `clean_ir`,
la app pasa `--vmin -92.1 --vmax 56.9` y las dos barras quedan idénticas.

### Himawari-9

Producto propio (`descargar_himawari.py` + `cuadros_himawari_ir.py`): disco
completo en la proyección del satélite, centrado en su punto subsatelital
(**140.7 E, lat 0**) con `--radio 90`. Sin recorte regional.

- Los slots son `.npz` de ~21 MB en `himawari_b13_h09` (`YYYYMMDD_HHMM.npz`).
- La descarga decodifica HSD de JMA, así que es más lenta que un `.nc` de GOES.
- Resolución por defecto **2712 px**: es el default del script y por debajo el
  título se superpone con el crédito.

### Meteosat-12 (MTG-I1)

Producto propio (`meteosat.py` + `cuadros_meteosat.py`): disco del FCI cada 10
minutos, ya pintado por EUMETView. `variante` elige GeoColour (día, IR y luces),
True Colour o IR 10.5 µm. Se pide por WMS en `CRS:84`; en `globo` se reproyecta a
Orthographic centrado en 0,0 y en `paraguay` se pide el recorte del país y se
enmarca cuadrado. Sin clave; atribución EUMETSAT/CC-BY 4.0.

- Cobertura Europa/África/Atlántico: Paraguay queda a 58° del subpunto satelital,
  en el limbo. `encuadre: paraguay` recorta 1000 km cuadrados sobre el país, pero
  el píxel viene estirado y el Rayleigh lava el color: sirve para ver el paso de
  los sistemas, no para detalle. IR es el que mejor se lleva con el limbo.
- Es el "tercer disco" del anillo geoestacionario.

### CBERS-4A

Producto propio (`cbers.py` + `cuadros_cbers.py`): recorte de una escena del STAC
del INPE (CC-BY 4.0, sin clave). `detalle` elige 2 m (PCA, sólo zonas cubiertas),
8 m (WPM) o 16 m (MUX); `zona` y `km` fijan el cuadrado.

- El `bbox` del STAC es el sobre del swath, no el polígono con dato: el descargador
  prueba una muestra de 48×48 y elige la escena más nueva con ≥60 % de dato.
- El tope de 4000 px recorta el pedido: 2 m deja 8 km por lado; 8 m, 32 km; 16 m,
  64 km. La cabecera del póster muestra el m/px real.

### Animación: rango horario y cadencia

Al animar, la serie cubre el **rango horario elegido** con la cadencia real del
ABI: **cada 10 minutos**. Las horas se eligen en **UTC**, igual que el dataset
crudo y que la etiqueta de cada cuadro (Paraguay es UTC-3: 12 UTC = 09:00 local).

| Desde | Hasta | Cuadros |
| --- | --- | --- |
| 0 | 24 | **144** (el día completo) |
| 6 | 18 | 72 |
| 13 | 15 | 12 |

- El `hasta` es **exclusivo**: `24` cierra el día UTC completo (medianoche del
  día siguiente). Una ventana de 3 días completos son **432** cuadros.
- El tope es 288 cuadros (2 días) para no disparar una descarga de decenas de GB
  sin querer. El globo C13 es la excepción: cada `.nc` pesa ~30 MB, así que su
  tope es 1008 (7 días). Si una ventana pide más que el tope, se recorta **por el
  principio** —se pierde el arranque y se conserva el final— y la etiqueta del
  paso lo dice con el rango real en UTC.
- **Sin fecha final** (`hasta` vacío) la serie cierra en el último slot que NOAA ya
  publicó. En el calendario se vacía con la **×** del extremo "Hasta" y se vuelve a
  fijar abriéndolo de nuevo; la hora final se apaga sola. Anima sin el switch
  "Animar": pedir "desde el 22 hasta donde haya" es pedir una serie.
- Con `animar` apagado (y una fecha final puesta), el rango no se usa: se renderiza
  un solo cuadro en el cenit.

**Los cuadros también se reciclan.** Cada PNG se guarda con su instante
(`cuadro_AAAAMMDDTHHMM.png`) en `<DATOS>cuadros_render/goes_c13/<sat>/<sello>/`, donde
el sello es la huella de aspecto (px, paleta, centro, radio, escala, borde). La carpeta
del job no copia bytes: enlaza los cuadros de su ventana. Repetir la misma ventana no
renderiza nada y ampliarla (22→24 y después 22→26) renderiza sólo los días nuevos;
cambiar `px` o `paleta` abre otra carpeta y rehace todo. `.aspecto.txt` adentro de cada
sello dice qué hay. El MP4 tampoco se re-encodea si no cambió nada.

Cuidado con el peso: 144 slots de C13 son ~7 GB de `.nc`. La descarga saltea lo
que ya está en disco, así que repetir una animación no vuelve a bajarla.

**El ABI publica con retraso.** Si elegís el día de hoy, la ventana se recorta al
último múltiplo de 10 minutos ya cumplido: pedir horas futuras solo llenaba el
log de 404. Y si la descarga termina con código 1 por slots que no existen, el
job **sigue** y renderiza lo que bajó — antes abortaba.

### GOES-16: fechas anteriores a 2025

G16 fue el GOES-East operativo hasta 2025, así que las fechas viejas se piden con
`satelite = G16`. No hubo que tocar el descargador: arma el bucket desde el
código del satélite (`noaa-goes{sat[1:]}` → `noaa-goes16`), y las carpetas de
datos ya eran `goes_<banda>_<sat>`.

Lo que sí faltaba era el rótulo: `cuadros_c13_ir.py` tenía `G19` escrito a mano
en el nombre de la carpeta de cuadros, el del póster y el log. Ahora acepta
`--sat` (default `G19`, así que nada existente cambia), y los textos dentro de la
imagen ya salían del archivo (`platform_ID`), por eso dicen `G16 GOES-East` solos.

Verificado de punta a punta: `2024-04-09 17:00 UTC` bajó de `noaa-goes16` en 4 s
y renderizó con el rótulo correcto en las cuatro líneas del póster.

### Nitidez del color real

El póster salía borroso no por el dato sino por el post-proceso:

| Paso | Qué hacía | Efecto medido |
| --- | --- | --- |
| `--mediana` (3×3) | mata el píxel suelto del limbo | pierde textura fina de nube |
| `--suavizado 0.8` | desenfoque gaussiano | 0.9 px a 2712 px de salida |
| `px 1400` | disco a 1400 px | 26 % de los 5424 nativos del ABI |

Los tres juntos dejan el disco con aspecto algodonoso. Ahora `nitidez = maxima`
(default) apaga mediana y desenfoque, y la resolución por defecto es **2712 px**,
el tamaño del disco nativo. Con `nitidez = suave` vuelve el look anterior, útil
si el limbo completo aparece con moteado.

El límite físico no cambia: ABI da 0.5–1 km por píxel, mientras que un mosaico
VIIRS/MODIS tiene 250–750 m. Un compuesto de GOES nunca va a igualar ese detalle;
lo que sí se puede es no tirar el que hay.

### El limbo del color real: está recortado por diseño

`radio_visible()` en `prototipos/poster_goes_realista.py` corta el disco en
`LIMBO_DEG = 73.3°` de ángulo central, mientras que el límite visible real de un
satélite geoestacionario está en `acos(R/(R+h)) = 81.3°`. Consecuencia: se
descarta el **6.1 % del área del disco** (el anillo exterior) y el resto queda
ampliado ~3 %.

El corte existe porque esa franja es donde el remuestreo estira los píxeles. La
app lo expone como `limbo`:

| Valor | Qué hace |
| --- | --- |
| `completo` (default) | `--recorte 1.0`: todo el disco captado, hasta 81.3° |
| `recortado` | deja el default del script, sin la franja estirada |

Ninguna de las dos es la captura cruda: ambas reproyectan a Orthographic. Para
**cero reproyección** está `encuadre = disco nativo` (`poster_goes_disco.py`),
que usa la perspectiva geoestacionaria tal como sale del ABI.

### Vista y centro

| Producto | Encuadre | Centro |
| --- | --- | --- |
| GOES IR | globo completo con `--radio 90` | punto subsatelital (75.2 W / 137.2 W, lat 0) |
| GOES color real | globo o disco nativo | punto subsatelital |
| MUR, ECMWF, follaje | default del script del repo | igual |

`cuadros_goes.py --globo` no tiene `--radio` y el globo se sale del marco por
abajo, así que el IR usa `cuadros_c13_ir.py`, que sí encuadra el disco entero.
El default de `cuadros_goes.py` y de `poster_goes_truecolor.py` es `-58 -23` /
`-71 -10` (recorte sobre Sudamérica): la app siempre pasa el subsatelital.

### Paso temporal en ECMWF

La app sigue la grilla que la corrida publica **de verdad**; pedir otra cosa da
404 en los pasos que faltan y el job muere con "faltan los pasos":

| Corrida | Pasos |
| --- | --- |
| IFS `00z` / `12z` | 0–144 h cada 3 h, 150–360 h cada 6 h |
| IFS `06z` / `18z` | 0–144 h cada 3 h |
| GFS (0.25°) | 0–144 h cada 3 h |
| AIFS (`aifs-single`, `aifs-ens`) | 0–360 h cada 6 h |

Los tres productos de la app (precipitación, anomalía y viento) topean en **144 h** y
van **cada 3 h**: 49 cuadros. Por encima de 144 h ECMWF sólo publica cada 6 h, así
que no se ofrece.

### Resoluciones y valores por defecto

- Una sola escala para todos los productos: **1400, 1800, 2000, 2400 y 2712** (el
  número solo; la interfaz no agrega "poster" ni "nativo").
- Ciclo por defecto **`00z`** en los productos de modelo.
- `Animar` y `Bajar los crudos` arrancan **encendidos** en precip-itación, anomalía y
  viento: el pedido típico ya deja el MP4 y los crudos en disco. En satélite quedan
  apagados a propósito (una animación GOES son cientos de `.nc`).

### Snapshot de Paraguay (una captura, no una animación)

El producto `snapshot_paraguay` no arma serie ni globo: pide **una sola** imagen y
la entrega recortada al país, sin rótulos ni barra de color.

Capas disponibles (el **?** al lado de la capa muestra los horarios de paso y qué
resalta cada composición):

En la UI, **Satélite / producto** elige el sensor y, solo para NOAA-20/21, aparece
un segundo control **Variante** con las composiciones (color real, falsos colores,
superficie y noche). El resto de los satélites tiene una sola composición y no
muestra Variante. Los scripts siguen recibiendo una única clave combinada
(`noaa21_dnb_marble`, etc.).

| `capa` | Sensor | Compuesto | Detalle real |
| --- | --- | --- | --- |
| `truecolor` (default) | NOAA-20 / VIIRS | Color real | **250 m** |
| `noaa21` | NOAA-21 / VIIRS | Color real | **250 m** |
| `snpp` | Suomi NPP / VIIRS | Color real | **250 m** |
| `aqua` | Aqua / MODIS | Color real | **250 m** |
| `terra` | Terra / MODIS | Color real | **250 m** |
| `geocolor` | GOES-19 ABI | GeoColor día/noche | **~700 m** |

Composiciones de bandas NOAA/VIIRS (misma API, mismo flujo):

| `capa` | Bandas (R-G-B) | Para qué | Detalle |
| --- | --- | --- | --- |
| `noaa20_m11i2i1` / `noaa21_m11i2i1` | M11-I2-I1 | Cicatrices de incendio, inundaciones, nieve/hielo vs nubes | 250 m |
| `noaa20_m3i3m11` / `noaa21_m3i3m11` | M3-I3-M11 | Nieve y hielo, agua líquida vs congelada | 250 m |
| `noaa20_i1i2i1` / `noaa21_i1i2i1` | I1-I2-I1 | Vegetación, sequía, inundaciones | 250 m |
| `noaa20_m11m7m5` / `noaa21_m11m7m5` | M11-M7-M5 | Quemaduras, vegetación y suelo desnudo | 500 m |
| `noaa20_m5m4m3` / `noaa21_m5m4m3` | M5-M4-M3 | Color natural de superficie, menos velo | 500 m |

Capas nocturnas:

| `capa` | Producto | Para qué | Detalle |
| --- | --- | --- | --- |
| `noaa20_dnb` / `noaa21_dnb` | Day/Night Band | Luces de ciudad, nubes iluminadas por la luna, incendios y auroras | 1 km |
| `noaa20_dnb_marble` / `noaa21_dnb_marble` | Black Marble | Luces nocturnas en azul/amarillo; suele cubrir mejor el país | 500 m |

La DNB puede traer **cuñas negras de barrido** (swath); para una cobertura más
completa del país, usá Black Marble. Ambas son diarias: se piden por fecha y la
hora se ignora; la imagen corresponde a la **noche de ese día UTC**.

**Continuidad de MODIS**: Terra deja de colectar ciencia el **2026-12-01** y Aqua se
retira en **2027**; Suomi NPP ya cesó la entrega de datos (2026-11-02). NASA no tiene
un reemplazo en la órbita matinal de Terra: la continuidad es **VIIRS**, con **NOAA-21
como primario** y **NOAA-20 como secundario** (JPSS-4/NOAA-22 llega en 2027). Para
fechas nuevas usá `noaa21` o `truecolor`; Terra/Aqua quedan para archivo histórico.

El control no es "píxeles" sino **metros por píxel** (125, 250, 500, 1000, 2000), como
en EOSDIS: el lado se calcula solo a partir de la caja del GeoJSON. Medido sobre este
encuadre (9,4° de lado):

| Pedido | GeoColor | VIIRS 250 m |
| --- | --- | --- |
| 1400 px | nitidez 352 · 2,7 MB | 1194 · 4,8 MB |
| 3600 px | 272 · 3,3 MB | **1195** · 28,8 MB |
| 6930×6888 | 253 · 4,5 MB | 1160 · 38,7 MB |

O sea: en GeoColor **más píxeles empeoran** la imagen (se interpola); en VIIRS a 3600
px ya está el detalle nativo y de ahí para arriba sólo crece el archivo. Por eso el
default es VIIRS con **250 m/px** (~4200 px, 17-20 MB) y el script avisa cuando se
pide más detalle del que la capa tiene.

Aun así, el control llega a **125 m/px** (el mismo del diálogo de Worldview): genera
~7600 px y un PNG de 40-50 MB, con el detalle real de 250 m interpolado.

- **La cobertura sale del GeoJSON** (`datos/paraguay_gadm.json`): se calcula la caja
  que encierra al país y se agranda con el `margen` que elige el usuario. No hay
  bbox escrito a mano.
- El **contorno de Paraguay** se dibuja en negro sobre la imagen, a 2x y reducido con
  LANCZOS (si no, a 3600 px queda escalonado). El grosor es automático: ~2 px a 3200.
  Se puede apagar o cambiar con `--borde-ancho`.
- Fuente: `wvs.earthdata.nasa.gov` (`REQUEST=GetSnapshot`). Las capas diarias piden
  `TIME=AAAA-MM-DD`; GeoColor pide el instante ISO y GIBS devuelve el gránulo más
  cercano, así que no hace falta acertar el slot de 10 minutos.
- **Última disponible (default)**: el instante no se adivina. El descargador sondea
  miniaturas de 320 px hacia atrás —10 min por paso en GeoColor, 1 día en las capas
  diarias (los cuatro True Color de VIIRS/MODIS)— hasta encontrar un gránulo real. La
  cadencia y el tope de la sonda salen del tipo de capa en `comun/paraguay.py`, no de
  una tabla aparte: agregar una capa a `CAPAS` alcanza. La trampa que hay que conocer:
  cuando el `TIME` no existe, GIBS responde **200 con un PNG de 0,7 KB totalmente
  negro**, no un 404. Por eso la sonda mira los píxeles y no el código HTTP.
- Si elegís la hora a mano y no hay gránulo, el job **falla con la última disponible
  y el comando exacto**, en vez de dejar una imagen negra. `--verificar` informa la
  última sin descargar nada.
- El crudo baja a `<work>/crudos/` para que el visor no lo publique como si fuera
  el resultado; el PNG final queda en la raíz del job (con la hora real en el nombre).

### Posters sueltos

`truecolor` y `mur_realista` producen un PNG, no una serie de cuadros. El runner
publica tanto cuadros (`frames_*/cuadro_*.png`) como **PNG en la raíz del work**,
por eso el visor muestra el póster igual que una animación.

### Estética de cada producto

| Producto | Cómo se pide |
| --- | --- |
| GOES IR (C13) | paleta `clean_ir` (la de `comun/paleta_gibs.py`) y `--geojson ""`: sin el contorno de Paraguay |
| GOES color real | `--fondo oscuro --no-lineas --no-fronteras --borde ""`: imagen limpia, sin retícula, costas ni bordes |
| MUR realista | `--rios`: ríos y lagos de Natural Earth sobre el continente |
| ECMWF (precipitación y anomalía) | `--fondo-globo claro` por defecto: el globo blanco, no negro |

### Flags nuevos en los scripts del repo

Para lograr lo anterior se agregaron **flags opcionales** a tres scripts del
pipeline. Los valores por defecto son los de siempre, así que ningún flujo
existente cambia:

| Script | Flag | Default (comportamiento previo) |
| --- | --- | --- |
| `cuadros/cuadros_c13_ir.py` | `--paleta`, `--geojson` | `clean_ir`, Paraguay |
| `prototipos/poster_goes_truecolor.py` | `--fondo`, `--lineas` | `claro`, líneas activas |
| `prototipos/poster_mur_realista.py` | `--rios` | sin ríos |

La firma de caché incluye `RECETA_VERSION` en `api/jobs.py`: cuando cambia cómo
se dibuja (paleta, fondo, capas) hay que subirla, si no los artefactos viejos se
reusan aunque la receta ya no sea la misma.

Decisiones que vienen de leer los scripts, no de suponer:

- **Solo se muestran los controles que existen.** GOES expone `--paleta`; MUR no
expone paleta, así que MUR no tiene selector de paleta.
- **Un control puede depender de otro.** `enabled_when` en el `ParamSpec` apaga un campo
mientras otro no valga lo esperado: en Snapshot, encender `ultima` deja en gris `fecha`,
`hora` y `minuto`, porque la última captura los ignora. Lo mismo con el switch
`snapshot` de los demás productos: apaga `animar`, `fps` y el horario.
- **Un control puede depender de la opción elegida.** `visible_when` en el `ParamSpec`
esconde el campo hasta que otro valga lo esperado: en Snapshot, **Variante** solo
aparece con NOAA-20/21; los demás satélites tienen una sola composición.
- **La placa muestra la opci?n elegida.** El cat?logo publica muestras por variante
  (`previews/<producto>--<valores>.webp`) y el formulario elige la que coincide con los
  par?metros: cambiar el sat?lite, la paleta, el modelo o la proyecci?n cambia el render
  de la placa. Sin variante para esa combinaci?n, cae a la muestra por defecto.
- **Snapshot en cualquier producto.** El switch pide **un solo cuadro**: en GOES es el
  slot de siempre (el cenital), en los productos de GIBS el último día de la ventana y
  en los modelos sólo dos crudos (0 h y el horizonte) con `--solo-poster`. Nunca arma
  video, aunque `animar` haya quedado encendido.
- **GOES arranca en el primer slot que hay en disco** cuando no se fuerza
  descarga: `cuadros_goes.py` asume una grilla contigua de 10 minutos y revienta
  con `KeyError` si falta un slot, así que la receta avanza solo mientras el
  siguiente slot exista. Con descarga, en cambio, la receta manda (`--paso`
  propio) y baja exactamente los slots que va a renderizar.
- **Nada de 800 px.** La tipografía del póster se superpone por debajo de
  ~1400 px; el mínimo ofrecido es 1400.

## Visor NISAR

La barra superior tiene dos vistas: **Consola** (las recetas) y **NISAR**. NISAR
no entra al catálogo: es un visor de búsqueda, no una receta.

- Se dibuja una caja sobre Paraguay y se consulta ASF por `bbox`, ventana y nivel.
- Niveles: **GCOV** (backscatter RTC, el de imágenes), GSLC, GUNW y SME2.
- Cada escena trae su polígono, miniatura y las imágenes browse públicas (mapa
  lat/lon y polarizaciones HH/HV). El backend las proxya y las cachea en
  `<raíz>\.media\nisar\cache`; solo acepta URLs
  `https://nisar.asf.earthdatacloud.nasa.gov/BROWSE/…`.
- La búsqueda y el browse no piden credenciales. La descarga del `.h5` sí:
  un GCOV pesa ~1.9 GB y exige Earthdata Login.
- Endpoints: `GET /api/nisar/catalog`, `/api/nisar/search`, `/api/nisar/browse`
  y `/api/nisar/paraguay`.

### Catastro: parcelas, fincas y matrículas

El mapa puede superponer las **parcelas catastrales del SNC** (Servicio Nacional
de Catastro) y cruzarlas con el cuadro ROI que se usa para buscar y renderizar
NISAR. Es la pieza que traduce "acá hubo pérdida de bosque" a "este inmueble":

- **Capa de parcelas**: polígonos con popup de `ccatastral`, departamento,
  distrito, padrón, zona/manzana/lote, finca, matrícula, colonia, registro de
  propiedad, superficies legal y medida. Se pide por la caja visible y el zoom,
  se simplifica según el zoom y se corta en 1.200 parcelas por respuesta: si hay
  más, el panel avisa "recortado" y muestra las más grandes.
- **Escala**: desde zoom 5, así que en la vista de país ya se ven las estancias
  grandes. Una parcela se dibuja recién cuando mide ~2 px de lado: al alejarte
  quedan sólo las grandes (contornos, sin relleno) y los lotes urbanos aparecen
  al acercarte, sin amontonarse. El umbral es automático y el panel dice cuál
  está aplicando:

  | Zoom | Parcela mínima | Zoom | Parcela mínima |
  | --- | --- | --- | --- |
  | 5 | 7.988 ha | 10 | 7,8 ha |
  | 6 | 1.997 ha | 11 | 1,95 ha |
  | 7 | 499 ha | 12 | 0,49 ha |
  | 8 | 125 ha | 13 | 0,12 ha |
  | 9 | 31 ha | 14+ | todas |
- **Inmuebles afectados**: con un cuadro ROI dibujado, **Analizar cuadro ROI**
  devuelve cada parcela que cae adentro con su **área afectada** (m²/ha) y la
  **fracción del predio** que ocupa la zona. La lista se ordena por superficie
  afectada, se resalta en el mapa por gravedad y al hacer clic vuela a la parcela.
  El cuadro es el mismo del render NISAR, así que la imagen de cambio y los
  predios quedan alineados.
- **Catastro en el render**: con la capa activa, el producto de cambio dibuja las
  parcelas dentro de la imagen (`nisar_cambio.py --catastro`). El panel
  *después* —y el barrido antes/después— salen con el contorno de cada predio y,
  sobre cada mancha roja, su número y la pérdida medida adentro
  (`finca 12336 · 2,3 ha`, `padrón 823 · 924 ha`). El cruce es por pixel: se
  cuentan los centros de pixel de la máscara que caen dentro de la parcela
  (`comun/catastro.py` lee el índice en sólo lectura). La capa encendida viaja
  como parámetro del job (`catastro: true`), así que un render con y sin catastro
  son dos corridas distintas.
- **Máscara de pérdida y cruce**: toda corrida de cambio deja
  `<corrida>_perdida.geojson` (EPSG:4326, simplificado a medio pixel). El panel de
  **Trabajos** lo publica como archivo y ofrece **Cruzar con catastro**, que manda
  ese polígono —no el cuadro ROI— a `/api/catastro/afectadas` y lista los
  inmuebles con la pérdida real adentro, con mapa de parcelas y popup del SNC.
- **Sin nombre de propietario**: el export del SNC no trae dueños. `nombre_obj`
  es manzana/lote y `parc_usrin`/`parc_usrac` son códigos de usuario del sistema,
  no personas. El panel muestra los identificadores registrales, que son los que
  el SNC usa para llegar al expediente; no inventa nombres.

**Configuración (una sola vez).** El shapefile pesa ~167 MB más 1,7 GB de DBF y
tiene 1.062.544 parcelas, así que no va al repo. Se apunta con
`CLIMATE3D_CATASTRO` (el `.shp` o su carpeta) o con el asistente de rutas:

```powershell
.venv\Scripts\python.exe comun\rutas.py --catastro "C:\ruta\al\shapefile"
```

La primera vez que se abre el panel, el backend construye un **índice SQLite con
R-tree** en `<MEDIA>/catastro/catastro.sqlite3` (geometría en EPSG:4326 y área en
m²). Tarda unos minutos y muestra el progreso; después cada vista se resuelve con
una consulta espacial. Si el `.shp` cambia de tamaño o fecha, el índice se
rehace solo. Para dejarlo listo antes, o reconstruirlo a mano:

```powershell
.venv\Scripts\python.exe app\tools\catastro.py --estado
.venv\Scripts\python.exe app\tools\catastro.py --reconstruir
```

**Calidad del dato**: el export declara EPSG:32721 (UTM 21S) y `.cpg` UTF-8. Un
puñado de registros viene guardado en grados lon/lat dentro del mismo shapefile:
se detectan por rango y se reparan (el índice los cuenta). Los que caen fuera de
Paraguay se descartan y también se informan en el estado.

Endpoints: `GET /api/catastro` (estado, progreso, rutas y conteos),
`GET /api/catastro/parcelas?bbox=…&zoom=…` y
`POST /api/catastro/afectadas` (`{"bbox": [...]}` o `{"poligono": {GeoJSON}}`).

### Descarga y render (Fase 2)

Con una escena seleccionada y una caja, **Descargar y renderizar** crea un job
`nisar_render` que:

1. Baja el `.h5` desde ASF a `DATOS/nisar/<coleccion>/<granulo>.h5` con
   `descargar/nisar.py`. Es reanudable por `.parcial` y saltea el archivo si ya
   está: cambiar polarización, modo o tamaño no vuelve a bajar 1.9 GB.
2. Recorta la caja en la grilla nativa de la escena con
   `prototipos/poster_nisar.py`, pasa a dB y escribe un PNG de hasta 4096 px
   (gris o color HH/HV), con escala, pie y el contorno de Paraguay.

Las credenciales salen de `EARTHDATA_USER`/`EARTHDATA_PASSWORD` (entorno o
`.env`), de `~/.netrc`, o de cookies del navegador (`--cookies`). Sin
credenciales el visor avisa y el job falla con un mensaje claro. La descarga se
guarda en la raíz de datos del pipeline (`CLIMATE3D_DATOS`).

### Productos de análisis (Fase 3)

El job `nisar_render` despacha por `producto`:

- **Recorte** (`poster_nisar.py`): el PNG de la caja en dB, gris o color HH/HV.
- **RVI** (`nisar_rvi.py`): índice de vegetación radar
  `sqrt(HH/(HH+HV)) * 4·HV/(HH+HV)`, calculado en potencia lineal, con media,
  percentiles y hectáreas.
- **Cambio de cobertura** (`nisar_cambio.py`): ΔHV entre dos fechas del mismo
  track/frame. **Resta el corrimiento radiométrico del par** (la mediana de ΔHV:
  dos pasadas pueden venir 3-4 dB distintas) y promedia speckle con multilook en
  potencia (~50 m) antes de umbralar. Aplica mayoría 3×3 y una unidad mínima de
  mapeo de 0.5 ha. Con **Confirmar con Sentinel-2**, rojo = pérdida confirmada
  por caída de NDVI y naranja = candidata solo-radar; sin confirmar, todo el
  cambio se pinta rojo y el pie lo aclara. Con **Persistencia temporal**, la
  caída se vuelve a medir contra la misma escena base en la fecha siguiente: si
  el pixel recuperó, no era pérdida. Usa los `.h5` que ya están en disco (no
  descarga nada) y, si no hay fecha posterior, sigue sin persistencia y avisa.
  Con **Baseline temporal**, la referencia deja de ser la escena anterior
  sola y pasa a ser la mediana por píxel de varias fechas en potencia (la de
  la fecha anterior incluida) que ya están en disco del mismo track/frame: la
  anomalía de humedad de una sola pasada deja de definir el cambio y el umbral
  de bosque se mide sobre la mediana; el **CoV máx.** aparta de la pérdida
  los píxeles que ya oscilaban entre fechas. Con **Guardia HH**, la caída de
  HV con subida de HH se pinta celeste como posible inundación por doble
  rebote (el error que el paper de L-band admite) y no cuenta como
  deforestación. Ambos son opt-in y degradan con aviso cuando faltan fechas
  o HH en disco (números reales en `validacion/README.md`). Con **Detector
  NDVI**, para desmontes sub-hectárea en bosque denso (Mbaracayú): la caída
  de NDVI es la detección y el radar corrobora a ±20 m — rojo = pérdida
  óptica corroborada, naranja = pérdida solo óptica; exige los compuestos
  de Sentinel-2. La guía visual a color real sale con
  `prototipos/nisar_color_optico.py`. El visor lo expone como selector
  «Detector» — al elegir NDVI aplica el empareje verificado (ml 1 ·
  umbral 4 dB · MMU 0,1 ha, compuestos obligatorios) — y junto al tamaño
  máx. muestra los m/px efectivos del render: la calidad se decide en
  caja × px, y una caja grande con px bajo sale gruenta aunque el
  granulo sea de 10 m. El detector NDVI no ve desmontes en bosque seco
  (NDVI ~0,4, debajo del piso de bosque) ni ya rebrotados (la NDVI se
  recupera antes que la estructura): cuando el cambio estructural y la
  caída óptica no coinciden, el producto lo avisa y recomienda el
  detector radar.
  La ganancia de HV es opcional
  (`--ganancia`) porque a este nivel de ruido es casi toda speckle. Medido contra
  la referencia NDVI del Este, el radar solo queda en F1 denso ≈ 0.27: es un mapa
  de cambio/screening, no un detector operativo de deforestación (ver
  `validacion/README.md`).
  Con **Color real (antes/después)** —un check aparte, apagado por defecto— la
  corrida suma dos PNG sueltos, `<base>_previo.png` y `<base>_posterior.png`, con
  la escena óptica **más cercana** a cada fecha (la cercanía manda; las nubes
  solo desempatan) entre Sentinel-2, HLS L30 y HLS S30 según **Fuente óptica**.
  Las dos fechas comparten un único estirado 2-98 %, así que se pueden comparar
  de verdad; no hay delta ni máscara. No depende de «Confirmar con óptico»: con
  el check activo y la confirmación apagada, el render sigue siendo solo radar
  más las dos imágenes de color. Si un lado no consigue escena, el log dice el
  motivo y sale el otro lado, sin cortar la corrida.
- **Serie temporal** (`nisar_serie.py`): usa todas las fechas locales del mismo
  track/frame/colección (mínimo 2), arma la serie de HV/HH/RVI, el compuesto
  mediano y el mapa CUSUM con la fecha de cambio y hectáreas por fecha.
- **GeoTIFF** (`nisar_geotiff.py`): exporta el recorte en la UTM de la escena
  (float32, dB o potencia) con tags EPSG; deja un PNG de vista previa. El `.tif`
  queda en la carpeta del job, accesible con **Abrir carpeta**. Lo escribe
  `tifffile`, sin GDAL.
- **Agua / inundación** (`nisar_agua.py`): máscara de agua abierta por HH y HV
  bajos, con mayoría 3×3 y hectáreas. Ojo: el bosque inundado puede brillar en
  HH por doble rebote; el producto apunta a agua abierta.
- **Incendio** (`nisar_incendio.py`): cicatriz por caída de HV y, opcionalmente,
  focos FIRMS del intervalo entre las dos fechas. El radar ve la cicatriz, no el
  fuego activo. Si falta el MAP_KEY de FIRMS, el producto sigue sin focos.
- **Fusión óptica** (`nisar_fusion.py`): busca Sentinel-2 L2A en Planetary
  Computer (±días, nubes máximas), enmascara nubes con SCL, compone NDVI mediano
  y lo reproyecta a la grilla NISAR. Genera figuras de HV/NDVI/RGB/clases, un
  GeoTIFF de NDVI y JSON. La clasificación es rule-based (agua/bosque/cultivo/
  suelo), no un modelo entrenado. Suma `rasterio`, `pystac-client` y
  `planetary-computer` al `.venv` del repo.

**Niveles:** los productos actuales usan **GCOV**. GSLC, GUNW y SME2 se pueden
buscar y descargar, pero su render (coherencia, deformación, humedad) queda para
una próxima iteración; la UI y la receta los rechazan con un mensaje claro en
lugar de fallar.

El motor común vive en `comun/nisar.py` (abrir escena, recortar, máscara, dB,
RVI, normalizar, PNG con escala/pie) y `comun/optico.py` (NDVI, SCL, compuesto
mediano y clasificación). Un producto nuevo es un script chico.

**Candado de colección:** las dos fechas de un cambio tienen que ser de la misma
colección (`NISAR_L2_GCOV_V1` o `NISAR_L2_GCOV_PROVISIONAL_V1`). Mezclar
PROVISIONAL con VALIDATED puede inventar cambios por el procesamiento. La UI
filtra las fechas por track/frame/colección y el backend rechaza la mezcla. Los
scripts de cambio/incendio también exigen el mismo track/frame y una grilla
alineada a 1/4 de píxel.

### Confianza y lectura (P0)

- Al terminar un job, el panel muestra una **tarjeta de estadísticas** (hectáreas,
  porcentajes, fechas, umbrales) leída del JSON del producto.
- El JSON y los GeoTIFF se publican como **artefactos descargables** (`kind=file`).
- Los productos están agrupados por **Visualización / Cambio / Agua / Óptico**.
- La **serie temporal** deja elegir las fechas locales del track/frame/colección
  (mínimo 2) con `GET /api/nisar/local`.
- Los mapas de análisis llevan una tercera línea de leyenda (qué significa cada
  color) además del pie y la escala.

### Validación

`validacion/deforestacion_este.py` mide el cambio NISAR contra NDVI Sentinel-2
pre/post. Primer caso del Este (82/101, junio→octubre 2026): **F1 denso 0,15** y
sesgo de área **+57 %**. El producto es una herramienta de screening, no un
detector de deforestación; el detalle y los límites están en
`validacion/este_2026/`.

## Caché de renders

La carpeta de trabajo es `<raíz>\.media\cache\<firma>\`, donde la firma es un
hash de producto + parámetros (sin `descargar`, que no cambia el render).

Consecuencias:

- Reordenar la misma receta **reusa los cuadros**: los scripts ya saltean PNG
  existentes si el sello de render no cambió. Medido: 27 s → 6 s.
- Un render largo se puede retomar: matá el server, volvé a pedir lo mismo.
- La caché **no** se borra al podar el historial de jobs. Se limpia a mano:
  `Remove-Item -Recurse "$env:CLIMATE3D_MEDIA\cache"` (o `<raíz>\.media\cache`).

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

## Un solo entorno

- `.venv` (raíz) — todo: el pipeline (`cartopy`, `xarray`, `h5py`…) y la consola
  (`fastapi`, `uvicorn`, `psutil`). Lo declara `pyproject.toml` y lo fija `uv.lock`.

No hay un segundo venv: la consola y los renders comparten intérprete. Es el mismo
acuerdo que usa la imagen de Docker, que instala ese único entorno con `uv sync`.

Para correr las pruebas, el entorno trae además el grupo `dev` de `pyproject.toml`
(`requests` para los descargadores y `httpx2` para `TestClient`); `uv sync` lo instala
por defecto.

## Pruebas

Una sola vez:

```powershell
uv sync
```

Toda la suite (unos 3 s, sin red):

```powershell
.venv\Scripts\python.exe -m unittest discover -s app\tests
```

Qué cubre:

- `test_jobs.py` — ciclo de vida: un job termina en `done` con artefactos, un
  script que falla deja el código de salida y su stderr en el log, un job sin
  imágenes avisa, el historial sobrevive al reinicio y una línea corrupta no
  rompe el resto.
- `test_jobs_subprocess.py` — regresión del loop Selector de Windows
  (`uvicorn --reload`): el job tiene que correr igual.
- `test_api.py` — contrato HTTP: health, catálogo, y los 400/404 con motivo.
- `test_nisar.py` — visor NISAR con ASF mockeado: búsqueda, caja válida, proxy
  restringido a ASF, caché del browse y GeoJSON de Paraguay.
- `test_nisar_render.py` — render de un GCOV sintético con la estructura real:
  recorte, paso a dB, PNG color/gris, caja fuera de escena, RVI y cambio con un
  par sintético que tiene un parche de pérdida, serie/CUSUM de tres fechas,
  GeoTIFF con EPSG, agua y cicatriz de incendio.
- `test_optico.py` — NDVI, máscara SCL, compuesto mediano y clasificación rule-based.
- `test_recetas_ecmwf.py`, `test_goes_rgb.py`, `test_goes_ultimos.py`,
  `test_paraguay_ultimos.py`, `test_descargadores_gibs.py` — recetas, bandas,
  encuadre y descargadores.

Resultado esperado al día de hoy: **405 tests, OK**. Si ves `skipped`, falta
alguna dependencia del grupo `dev` de `pyproject.toml`; el mensaje del skip dice cuál.

## Límites conocidos

- Un solo worker. Dos personas pidiendo renders a la vez ven la cola, no
  paralelismo.
- El historial de jobs se guarda en `<raíz>\.media\historial.jsonl` (las últimas
  40 corridas terminadas) y se relee al arrancar. Si el archivo se borra, la
  lista arranca vacía; los artefactos quedan en `<raíz>\.media\cache`.
- Sin autenticación: es local.
- El repo vive en OneDrive: `node_modules` y `.venv` generan mucho tráfico de
  sincronización. La caché de renders ya **no** está ahí: vive en la raíz de trabajo.
- Progreso por líneas de log: en descargas largas la barra se queda quieta hasta
  que el script imprime. Es honesto, no inventado.
- El archivo de cada fuente tiene retención: NOAA S3 conserva GOES unas semanas.
  Una fecha demasiado vieja se descarga con errores y el job falla avisando.

## Próximo paso natural

`titiler` + PMTiles para que el visor tenga zoom/pan en vez de imágenes fijas, y
una cola externa (Redis/arq) cuando haya más de una persona usándolo.
