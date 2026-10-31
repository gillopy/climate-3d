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
| GOES color real (C01+C02+C03) | `truecolor_goes.py --desde --n --paso --sat` | `poster_goes_truecolor.py --centro LON 0 --px --out` o `poster_goes_disco.py --px --out` | `armar.py` sobre la serie |
| MUR SST (globo oscuro) | `mur_sst.py --desde --hasta --paso --px --out` | `cuadros_mur.py --desde --hasta --paso --px --out` | `armar.py` |
| MUR SST poster realista | `mur_sst.py ...` | `poster_mur_realista.py --crudo --px --paleta [--trend] --out` | — |
| Precipitación ECMWF | `precipitacion_ecmwf.py --modelo --fecha --ciclo --hasta-hora --paso 3` | `cuadros_precipitacion.py ... --px --fondo-globo --salidas` | `armar.py` |
| Anomalía 2 m ECMWF | `anomalia_2t_ecmwf.py ... --paso 3` | `cuadros_anomalia_2t.py ...` | `armar.py` |
| Follaje PACE | `pace_landvi.py --desde --hasta` | `cuadros_follaje.py --desde --hasta --px --out` | `armar.py` |

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
app\.venv\Scripts\python.exe app\tools\previews.py
```

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

### Animación: rango horario y cadencia

Al animar, la serie cubre el **rango horario elegido** con la cadencia real del
ABI: **cada 10 minutos**. Las horas se eligen en hora local (UTC-3), que es como
se leen los pósters.

| Desde | Hasta | Cuadros |
| --- | --- | --- |
| 0 | 24 | **144** (el día completo) |
| 6 | 18 | 72 |
| 13 | 15 | 12 |

- El rango se convierte a UTC sumando 3 h: `00–24` local = `03:00` a `03:00` del
  día siguiente en UTC.
- El tope duro es 288 cuadros (2 días) para no disparar una descarga de decenas
  de GB sin querer.
- Con `animar` apagado, el rango no se usa: se renderiza un solo cuadro en el
  cenit.

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

Los cuadros van **cada 3 h**, igual que el `PASO_HORA = 3` de los scripts del
repo. Con horizonte 144 h son 49 cuadros, no 25.

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
| `cuadros/cuadros_c13_ir.py` | `--paleta`, `--geojson` | `ir_realce`, Paraguay |
| `prototipos/poster_goes_truecolor.py` | `--fondo`, `--lineas` | `claro`, líneas activas |
| `prototipos/poster_mur_realista.py` | `--rios` | sin ríos |

La firma de caché incluye `RECETA_VERSION` en `api/jobs.py`: cuando cambia cómo
se dibuja (paleta, fondo, capas) hay que subirla, si no los artefactos viejos se
reusan aunque la receta ya no sea la misma.

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
hash de producto + parámetros (sin `descargar`, que no cambia el render).

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
