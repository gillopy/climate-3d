# `descargar/` — lo único que necesita internet

Todo lo que toca la red vive acá. `prototipos/`, `cuadros/` y `animar/` funcionan **sin
conexión** a partir de lo que ya está descargado.

| Archivo | Qué baja | Fuente | Destino |
|---|---|---|---|
| `descargar_goes.py` | GOES-R ABI L2 CMIP (`.nc`) | Bucket público NOAA S3 | `DATOS/goes_<banda>_<sat>/` |
| `descargar_era5.py` | ERA5 2m temperature 2024–2026 | Copernicus CDS | `DATOS/era5_t2m_2024-2026.nc` |
| `geocolor.py` | GeoColor (GOES-East), ya rasterizado | NASA GIBS | `SALIDAS/frames_<etiqueta>/crudo_NNN.jpg` |
| `mur_sst.py` | GHRSST MUR L4 SST Anomalies (globo), ya rasterizado | NASA GIBS | `SALIDAS/frames_mur_globo_<...>/crudo_NNN.jpg` |
| `truecolor.py` | True Color (MODIS/VIIRS) diario, ya rasterizado | NASA GIBS | `SALIDAS/frames_truecolor_<sensor>_globo_<...>/crudo_NNN.jpg` |
| `goes_descarga.py` | *(módulo)* claves S3 y descarga | — | — |

`DATOS` y `SALIDAS` salen de [`../comun/rutas.py`](../comun/rutas.py): se cambian con
`CLIMATE3D_DATOS` sin tocar código.

## Quick path

```powershell
# GOES-East C13 (infrarrojo) del 2 al 5 de octubre de 2026
.venv\Scripts\python.exe descargar\descargar_goes.py --sat G19 --banda C13 --desde 2026-10-02 --hasta 2026-10-05

# GeoColor: 24 cuadros de globo a 600 px
.venv\Scripts\python.exe descargar\geocolor.py --globo --desde 2026-10-15T20:00 --n 24 --px 600
```

Cada script imprime al terminar **el comando del paso siguiente**. Ningún `--help` toca la red.

---

## `descargar_goes.py`

Baja archivos `.nc` de ABI desde el bucket público de NOAA S3, para cualquier satélite y
banda. **Saltea los que ya existen**, así que se puede cortar y retomar.

| Opción | Qué hace |
|---|---|
| `--sat` | Satélite (`G19`, `G18`, …) |
| `--banda` | Banda (`C13`, `C04`, `C02`, …) |
| `--desde` / `--hasta` | Rango UTC (`AAAA-MM-DD` o `AAAA-MM-DDTHH:MM`) |
| `--paso` | Minutos entre cuadros (por defecto 10; la cadencia real de ABI) |
| `--out` | Carpeta destino (por defecto, `goes_<banda>_<sat>`) |

La cadencia real de ABI es de 10 minutos (modo 6): 24 h = 144 cuadros, 3 días = 432.
Los `.nc` son de varios MB cada uno, así que una ventana larga pesa GB.

---

## `descargar_era5.py`

Baja **ERA5 2m temperature** (2024–2026) desde Copernicus CDS.

| Opción | Qué hace |
|---|---|
| `--out` | Carpeta destino |
| `--nc` | Nombre del archivo destino |
| `--force` | Vuelve a descargar aunque ya exista |

- Requiere el paquete `cdsapi` y la API key en `~/.cdsapirc`.
- Pide un día por mes a las 00/06/12/18 UTC (≈1464 pasos, ~2.2 GB): resolución temporal
  suficiente para las climatologías del póster de anomalía.
- La cola de CDS puede tardar; conviene correrlo en segundo plano y mirar
  [`../logs/`](../logs).

---

## `mur_sst.py`

Baja la **anomalía de SST** del análisis GHRSST Level 4 MUR (v4.1) desde la Worldview
Snapshots API de NASA GIBS. Igual que GeoColor, no es una banda cruda sino un producto ya
coloreado: se pide rasterizado, un JPEG por cuadro, sin `.nc` que leer. A diferencia de
GeoColor, **es global** (caja `-180,-90,180,90`).

Como el producto es diario pero la animación abarca dos años, se muestrea **una vez por
semana** (`--paso` en días): ~94 cuadros en vez de los ~650 diarios.

| Opción | Qué hace |
|---|---|
| `--desde` / `--hasta` | Rango UTC (por defecto, `2025-01-01` a `2026-10-17`) |
| `--paso` | Días entre cuadros (por defecto `7`: una muestra por semana) |
| `--bbox O S E N` | Caja de origen (por defecto, global) |
| `--px` | Ancho de salida (por defecto `2048`); el origen se pide `max(1200, px*2)` |
| `--src-px` / `--alto` | Tamaño del origen (overrides) |
| `--hilos` | Descargas simultáneas (por defecto 16) |
| `--out` | Carpeta de salida |

- **La serie y la etiqueta de la carpeta vienen de [`../comun/series.py`](../comun/series.py)**,
  así que la descarga y el render calculan exactamente los mismos cuadros.
- Cada cuadro pesa ~1,4 MB a 4096×2048; la tierra y los polos van enmascarados en negro.
- Ojo: GIBS a veces responde un JPEG **válido pero sin dato** (uniforme). El descargador lo
  detecta con Pillow + numpy y lo reintenta, en vez de dejar un hueco silencioso.

---

## `truecolor.py`

Baja **True Color (Corrected Reflectance)** de MODIS/VIIRS desde la misma Worldview
Snapshots API de NASA GIBS. Es la **composición de color real** del día (reflectancia
corregida de los canales visibles), servida ya rasterizada: igual que GeoColor y MUR, se
pide un JPEG por cuadro, sin `.nc` que leer. A diferencia de GeoColor —un disco GOES— estas
capas son **globales** (caja `-180,-90,180,90`), y a diferencia de MUR son de **cadencia
diaria** (`P1D`, composición del día): el `TIME` va como fecha sola `AAAA-MM-DD`.

Estas capas muestran el **humo de los incendios**, que es lo que se busca en la ventana
2024-07-11 → 2024-10-30.

| Capa GIBS | Nombre corto |
|---|---|
| `VIIRS_NOAA20_CorrectedReflectance_TrueColor` (**default**) | `noaa20` |
| `MODIS_Terra_CorrectedReflectance_TrueColor` | `terra` |
| `MODIS_Aqua_CorrectedReflectance_TrueColor` | `aqua` |

| Opción | Qué hace |
|---|---|
| `--desde` / `--hasta` | Rango UTC (por defecto, `2024-07-11` a `2024-10-30`) |
| `--capa` | Capa GIBS (por defecto, NOAA-20) |
| `--paso` | Días entre cuadros (por defecto `1`: composición diaria) |
| `--bbox O S E N` | Caja de origen (por defecto, global) |
| `--px` | Ancho de salida (por defecto `2711`); el origen se pide `8192` (`--src-px`) |
| `--hilos` | Descargas simultáneas (por defecto 16) |
| `--out` | Carpeta de salida |

- **La serie y la etiqueta de la carpeta vienen de [`../comun/series.py`](../comun/series.py)**,
  así que la descarga y el render calculan exactamente los mismos cuadros. El nombre corto
  del sensor entra en la etiqueta (`frames_truecolor_terra_globo_<...>`), para que dos
  sensores no se pisen la carpeta.
- **Ojo con `VIIRS_SNPP_CorrectedReflectance_TrueColor`**: tiene un hueco de archivo
  (2024-07-12..15 devuelve un placeholder). Por eso no se ofrece; para 2024 usá Terra o
  NOAA-20.
- **Por eso el default es VIIRS NOAA-20, no MODIS**: las composiciones diarias de **Terra y
  Aqua traen huecos de franja (swaths) cerca del ecuador** —el ancho de barrido de MODIS
  (2330 km) es menor que la separación de órbitas en el ecuador (~2800 km)—, así que cada día
  quedan cuñas negras entre pasadas que en el globo se ven como franjas diagonales rayadas
  (verificado en el globo del 2024-07-15/16). **NOAA-20 no las tiene** (el barrido de VIIRS
  es más ancho que la separación orbital), así que es la capa por defecto y la recomendada
  para el globo. Es una propiedad del producto, no del render.
- Como estas capas son **diarias**, un día puede no tener composición publicada y GIBS
  responde igual un JPEG **válido pero sin dato**. El descargador lo detecta con Pillow +
  numpy (imagen uniforme) y lo reintenta, en vez de dejar un hueco silencioso.

---

## `geocolor.py`

Baja **GeoColor** (GOES-East) desde la Worldview Snapshots API de NASA GIBS. GeoColor no es
una banda cruda sino un producto **RGB ya mezclado** (color real de día; IR + luces de ciudad
de noche), así que se pide ya rasterizado: no hay `.nc` que leer.

| Opción | Qué hace |
|---|---|
| `--desde` | Primer cuadro, UTC |
| `--n` / `--paso` | Cantidad de cuadros y minutos entre ellos |
| `--globo` | Pide la caja que cubre el hemisferio visible (para renderizar en globo) |
| `--centro LON LAT` | Centro del globo (por defecto `-58 -23`) |
| `--px` / `--alto` / `--src-px` | Tamaño de salida y del origen |
| `--hilos` | Descargas simultáneas (por defecto 16) |
| `--out` | Carpeta de salida |

- Cadencia de 10 min, ~90 días de historia rodante, ~40 min de latencia.
- **El cuello de botella es el servidor, no tu enlace**: medido en frío, 4 hilos dan
  ~0,45 MB/s y 32 hilos ~1,45 MB/s. Subir de 16 casi no cambia nada.
- Ojo: algunos slots **sin dato** vuelven como un JPEG válido pero en blanco. No son un
  hueco: hay que detectarlos comparando contra los cuadros vecinos.

---

## `goes_descarga.py`

Módulo, no tiene CLI. Expone `claves_de_la_hora` (listado S3 por hora), `clave_de` (clave del
slot de 10 min) y `descargar`. Lo usan `descargar_goes.py` y los notebooks de `prototipos/`.

La parte **local** de GOES (leer `.nc`, recortar, fundidos para GIF) está en
[`../comun/goes_lectura.py`](../comun/goes_lectura.py), justamente para que se pueda leer sin
tocar la red.

## Next step

Seguí con [`../prototipos/`](../prototipos) para imágenes fijas, o con
[`../cuadros/`](../cuadros) para animaciones.
