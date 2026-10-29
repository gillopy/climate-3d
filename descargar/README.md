# `descargar/` — lo único que necesita internet

Todo lo que toca la red vive acá. `prototipos/`, `cuadros/` y `animar/` funcionan **sin
conexión** a partir de lo que ya está descargado.

| Archivo | Qué baja | Fuente | Destino |
|---|---|---|---|
| `descargar_goes.py` | GOES-R ABI L2 CMIP (`.nc`) | Bucket público NOAA S3 | `DATOS/goes_<banda>_<sat>/` |
| `descargar_era5.py` | ERA5 2m temperature 2024–2026 (requiere `cdsapi`) | Copernicus CDS | `DATOS/era5_t2m_2024-2026.nc` |
| `descargar_himawari.py` | Himawari-9 AHI banda 13 en HSD, decodificada a `.npz` | Bucket público NOAA S3 | `DATOS/himawari_b13_h09/` |
| `truecolor_goes.py` | Bandas visibles C01 / C02 / C03 del GOES-R ABI | Bucket público NOAA S3 | `DATOS/goes_c0{1,2,3}_<sat>/` |
| `pace_landvi.py` | PACE OCI L3M LANDVI diario (`.nc`) | OB.DAAC (**Earthdata Login**) | `DATOS/pace_landvi/` |
| `geocolor.py` | GeoColor (GOES-East), ya rasterizado | NASA GIBS | `SALIDAS/frames_<etiqueta>/crudo_NNN.jpg` |
| `mur_sst.py` | GHRSST MUR L4 SST Anomalies (globo), ya rasterizado | NASA GIBS | `SALIDAS/frames_mur_globo_<...>/crudo_NNN.jpg` |
| `truecolor.py` | True Color (MODIS/VIIRS) diario, ya rasterizado | NASA GIBS | `SALIDAS/frames_truecolor_<sensor>_globo_<...>/crudo_NNN.jpg` |
| `sandwich.py` | Sandwich RGB (GOES-19): visible + IR realzado, dos JPEG por cuadro | NASA GIBS | `SALIDAS/frames_sandwich_globo_<...>/crudo_NNN_{vis,ir}.jpg` |
| `precipitacion_ecmwf.py` | Precipitación total acumulada (`tp`) de IFS 0.25° / AIFS, por HTTP Range | ECMWF Open Data | `DATOS/crudos_precip_<modelo>_<fecha>_<ciclo>z/` (GRIB2 o `.npy` + `serie_tp_mm.npz`) |
| `anomalia_2t_ecmwf.py` | Temperatura a 2 m (`2t`) del IFS 0.25° y su anomalía vs la climatología ERA5, por HTTP Range | ECMWF Open Data | `DATOS/crudos_anom2t_<modelo>_<fecha>_<ciclo>z/` (GRIB2 + `serie_anom_2t_c.npz`) |
| `viento_250_mslp.py` | Viento en 250 mb (`u`, `v`) y presión a nivel del mar (`msl`) del IFS 0.25°, por HTTP Range | ECMWF Open Data | `DATOS/crudos_viento250_<fecha>_<ciclo>z/` (GRIB2 + `serie_viento_250.npz`) |
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

## `sandwich.py`

Baja los **dos crudos** del producto **Sandwich RGB** de **GOES-19 (GOES-East)** desde la
misma Worldview Snapshots API de NASA GIBS. El Sandwich **no es un RGB de tres bandas**:
combina **dos imágenes** que después se mezclan en el render. Por eso baja **dos JPEG por
cuadro**: el fondo **visible** (`crudo_NNN_vis.jpg`, banda ABI C02 0.64 µm) y el **IR
10.8 µm** (`crudo_NNN_ir.jpg`, banda C13 10.3 µm) que se realza en color.

| Capa GIBS | Rol | Archivo |
|---|---|---|
| `GOES-East_ABI_Band2_Red_Visible_1km` | fondo visible (gris) | `crudo_NNN_vis.jpg` |
| `GOES-East_ABI_Band13_Clean_Infrared` | IR realzado en color | `crudo_NNN_ir.jpg` |

| Opción | Qué hace |
|---|---|
| `--desde` / `--hasta` | Rango de días UTC (por defecto, `2026-10-04` a `2026-10-05`) |
| `--hora-desde` / `--hora-hasta` | Tramo diurno de cada día, horas UTC (por defecto `10` a `22`) |
| `--paso` | Minutos entre cuadros (por defecto `10`: la cadencia nativa de ABI) |
| `--bbox O S E N` | Caja de origen (por defecto, el globo `-160 -80 15 80`) |
| `--px` | Ancho de salida (por defecto `2048`); el origen se pide `max(1200, px*2)` |
| `--src-px` / `--alto` | Tamaño del origen (overrides) |
| `--hilos` | Descargas simultáneas (por defecto `8`: GIBS rate-limitea) |
| `--out` | Carpeta de salida |

- **Es sólo diurno**: el visible necesita sol, así que la serie son los **tramos diurnos**
  de cada jornada (`--hora-desde/--hora-hasta`), no las horas corridas. `--hora-desde 10`
  / `--hora-hasta 22` UTC ≈ `07:00–19:00` en Paraguay (UTC-3 en octubre) → 73 cuadros por
  día.
- **La serie y la etiqueta de la carpeta vienen de [`../comun/series.py`](../comun/series.py)**
  (`serie_diurna` + `etiqueta_frames`), así que la descarga y el render calculan exactamente
  los mismos cuadros.
- **Ojo con el rate-limit de GIBS**: se manda `User-Agent` y se usan pocos hilos. Sin
  `User-Agent` el servicio devuelve un XML `ServiceExceptionReport` **con HTTP 200** en vez
  de la imagen; el descargador chequea el `Content-Type` (y la guarda de imagen uniforme) y
  reintenta con backoff.
- **Por qué GIBS y no el `.nc` de NOAA S3**: la banda visible de ABI (C02) es de 0.5 km y
  cada `OR_ABI-L2-CMIPF-M6C02_*.nc` pesa ~200–228 MB. Para 2 días a 10 min serían ~57 GB:
  inviable. GIBS sirve las mismas bandas ya rasterizadas a 1 km (~90–200 KB por cuadro).

---

## `pace_landvi.py`

Baja los gránulos diarios de **PACE OCI L3M LANDVI**: la suite de **índices de vegetación
terrestre** del satélite PACE. Es la primera fuente del repo que **no** sale de GIBS ni de
ECMWF, y la única que **exige cuenta**: `getfile` de OB.DAAC redirige a *Earthdata Login* y
sin sesión válida no entrega nada.

El producto es una grilla global de **4320×8640** (1/24°, ~4,6 km) en NetCDF-4, con diez
índices por día: los heredados de la era MODIS (`ndvi`, `evi`, `ndwi`, `ndii`, `cci`, `ndsi`)
y los cuatro que sólo un sensor hiperespectral puede calcular (`pri`, `cire`, `car`, `mari`).
Pesa **~170 MB por día** y **ya viene enmascarado para nubes**.

```
https://oceandata.sci.gsfc.nasa.gov/getfile/
  PACE_OCI.<AAAA-MM-DD>.L3m.DAY.LANDVI.V3_1.<res>.NRT.nc
```

| Opción | Qué hace |
|---|---|
| `--desde` / `--hasta` | Rango UTC inclusive (por defecto, `2026-09-29` a `2026-10-04`) |
| `--res` | `4km` (por defecto), `2km` u `0p1deg` |
| `--destino` | Carpeta de salida (por defecto, `DATOS/pace_landvi`) |
| `--cookies` | JSON con las cookies de un navegador ya logueado en Earthdata |

- **Autenticación, dos caminos**: `--cookies navegador.json` (formato de Playwright:
  `[{name, value, domain, path}]`) o `~/.netrc` con `machine urs.earthdata.nasa.gov`. Sin
  ninguno de los dos, el script corta con un mensaje explícito; nunca guarda la contraseña.
- **Las cookies de URS solas no alcanzan**: hay que completar el OAuth visitando una URL
  `getfile` en el navegador para que quede la cookie `GETFILE_APP` del dominio de oceandata.
- El `.nc` va a `*.parcial` y se renombra al final, así que un corte deja el archivo
  incompleto marcado y no un gránulo corrupto con nombre definitivo.
- **Por qué no GIBS**: GIBS publica PACE sólo para océano y atmósfera; los índices de
  vegetación terrestre no están ahí.

---

## `precipitacion_ecmwf.py`

Baja la **precipitación total acumulada (`tp`)** de **ECMWF Open Data** a 0.25°. No es una
imagen: es un campo del modelo, y `tp` viene acumulado desde el inicio de la corrida, así que
el descargador lo convierte a **mm**. Con `--modelo` se elige cuál de los tres modelos se
baja:

| `--modelo` | Ruta en el servidor | Qué es |
|---|---|---|
| `ifs` (por defecto) | `ifs/0p25/oper` | IFS HRES determinístico (`oper-fc`) |
| `aifs-single` | `aifs-single/0p25/oper` | AIFS determinístico (`oper-fc`) |
| `aifs-ens` | `aifs-ens/0p25/enfo` | AIFS ensamble (`enfo-cf` + `enfo-pf`) |

La fuente publica, por cada paso, un `.index` (JSON Lines) y un `.grib2` con todos los campos.
Bajar el `.grib2` completo son ~98 MB por paso (~4,8 GB para 49 pasos). Como el `.index`
publica `_offset` y `_length`, el script pide **sólo el rango de bytes** de
`"param": "tp", "levtype": "sfc"`: ~20 MB en total. Cada mensaje se decodifica con
**eccodes** (el GRIB2 de ECMWF usa empaquetado CCSDS/AEC, que otras herramientas no leen) y la
serie consolidada queda en **mm** en `serie_tp_mm.npz`, con la rejilla `721 x 1440` en el orden
que espera el render (lat 90→-90, lon -180→179.75).

**El ensamble AIFS-ENS.** ECMWF publica el AIFS-ENS partido en **dos archivos por paso**:
`enfo-cf` (el control) y `enfo-pf` (los 50 miembros perturbados, con `number` de 1 a 50 en el
`.index`). El script lee el `.index` de cada tipo, pide el rango de `tp`/`sfc` de `cf` y de los
miembros `pf` elegidos, los promedia y guarda **un `.npy` por paso** con la media del
ensamble en mm (no se guardan los 11 GRIB). `--miembros` decide cuántos `pf` entran:

| `--miembros` | Qué se promedia |
|---|---|
| `1` | Sólo el control `cf` (no pide ningún `pf`) |
| `11` (por defecto) | `cf` + los 10 `pf` equiespaciados (`5, 10, …, 50`): media suave y barata |
| `51` | `cf` + los 50 `pf` |

Los crudos quedan como `crudo_NNN_fhHHH.grib2` (en `aifs-ens`, como `crudo_NNN_fhHHH.npy` con
la media ya calculada) y el paso `0h` se valida en **0 mm**: si el recorte por bytes o la
orientación de la rejilla están mal, el script aborta en vez de dejar una serie corrida.

**Unidades.** El **IFS publica `tp` en metros (`m`)** y el **AIFS en `kg m**-2`** (numéricamente
igual a mm). El lector consulta el `units` de cada mensaje y aplica el factor 1000 sólo cuando
corresponde, así que los tres modelos quedan en la misma escala sin tocar nada.

| Opción | Qué hace |
|---|---|
| `--modelo` | Modelo de ECMWF Open Data: `ifs`, `aifs-ens` o `aifs-single` (por defecto `ifs`) |
| `--fecha` | Día UTC de la corrida, `AAAA-MM-DD` (por defecto `2026-10-20`) |
| `--ciclo` | Ciclo UTC de la corrida: `00`, `06`, `12` o `18` (por defecto `06`) |
| `--hasta-hora` | Último paso de pronóstico en horas (por defecto `144`) |
| `--paso` | Horas entre pasos (por defecto `3`) |
| `--hilos` | Descargas simultáneas (por defecto `12` para `aifs-ens` y `6` para el resto) |
| `--miembros` | Miembros del ensamble en `aifs-ens`: `1` = sólo `cf`, `11` = `cf` + 10 `pf`, `51` = `cf` + los 50 `pf` (por defecto `11`) |
| `--forzar` | Vuelve a bajar los pasos aunque ya estén completos |
| `--out` | Carpeta de salida (por defecto, `DATOS/crudos_precip_ecmwf_<fecha>_<ciclo>z` para `ifs` o `DATOS/crudos_precip_<modelo>_<fecha>_<ciclo>z` para los AIFS) |

- **Base de ECMWF Open Data**: `https://data.ecmwf.int/forecasts/{yyyymmdd}/{ciclo}z/<ruta>/`.
  Ojo: la fecha va **sin guiones** (`20261020`, no `2026-10-20`) y el ciclo con la `z` pegada
  (`12z`). Cada paso publica `<yyyymmdd><ciclo>0000-<paso>h-<sufijo>.index` y `.grib2`, donde
  el sufijo es `oper-fc` en los determinísticos y `enfo-cf` / `enfo-pf` en el ensamble.
- **Ventana rodante de 4 días**: el ECMWF Open Data sólo conserva las corridas recientes (unas
  cuatro jornadas). Una corrida más vieja ya no está publicada, así que hay que descargarla
  dentro de esa ventana; no es un archivo histórico.
- **Reanudable**: si un `crudo_NNN_fhHHH.grib2` ya existe con el tamaño exacto que publica el
  `.index` y el marco GRIB (`GRIB`…`7777`) está completo, no se vuelve a pedir.
- Si cambias `--miembros` con la serie ya cacheada, el script **descarta la media anterior y
  la rehace**: la media cacheada no representa lo pedido.
- La serie y la etiqueta de la carpeta salen de [`../comun/series.py`](../comun/series.py),
  igual que en el resto del repo.

---

## `anomalia_2t_ecmwf.py`

Baja la **temperatura a 2 m (`2t`)** del **ECMWF Open Data** a 0.25° y calcula su **anomalía
contra una climatología diurna de ERA5**. Soporta los dos determinísticos: `ifs` (por
defecto) y `aifs-single`.

| Variable | Índice | Notas |
|---|---|---|
| `2t` | `levtype="sfc"` | Temperatura a 2 m en kelvin |

Como en el resto de los productos ECMWF, se pide **sólo el rango de bytes** de `2t`/`sfc` de
cada paso (el `.index` publica `_offset` y `_length`), así que no baja el `.grib2` completo.
Los mensajes se decodifican con **eccodes** y salen en kelvin; el script los pasa a **°C**
(`- 273.15`) y de ahí a la anomalía.

**La climatología.** Se construye una **climatología diurna por mes y hora UTC** —12 meses ×
las 4 horas `00`, `06`, `12` y `18`— a partir del NetCDF local **`era5_t2m_2024-2026.nc`**
(1464 instantes cada 6 h). Ese archivo es HDF5/NetCDF4 y se lee **directamente con `h5py`**,
sin `xarray`: por mes, para no cargar los ~6 GB de una vez. De cada mes se promedia `t2m` por
hora UTC, se pasa a °C, se rota la longitud de `0..359.75` a `-180..179.75` (para calzar 1:1
con ECMWF Open Data) y se suaviza con un **Gaussiano separable de σ = 1 celda** (`0.25°`): los
Andes tienen celdas de orografía muy distintas entre ERA5 e IFS HRES y el suavizado evita
picos aislados sin borrar estructura sinóptica.

El resultado se cachea en **`DATOS/climatologia_era5_t2m_mes_hora.npz`** y **se reutiliza
entre corridas**: la primera vez tarda ~7 minutos, después se lee de la caché al instante.
`--forzar-climatologia` la reconstruye.

Al calcular la anomalía, la climatología se **interpola en hora** (entre los dos slots UTC que
rodean, con vuelta `18 → 0`) y **en mes** (entre los centros `15 → 16` de los meses
vecinos), así que el paso del 31 de octubre al 1 de noviembre **no tiene salto**.

| Opción | Qué hace |
|---|---|
| `--modelo` | Modelo de ECMWF Open Data: `ifs` o `aifs-single` (por defecto `ifs`) |
| `--fecha` | Día UTC de la corrida, `AAAA-MM-DD` (por defecto `2026-10-20`) |
| `--ciclo` | Ciclo UTC de la corrida: `00`, `06`, `12` o `18` (por defecto `12`) |
| `--hasta-hora` | Último paso de pronóstico en horas (por defecto `360`: 15 días) |
| `--paso` | Horas entre pasos (por defecto `6`) |
| `--hilos` | Descargas simultáneas (por defecto `8`) |
| `--era5-nc` | NetCDF/HDF5 de ERA5 con `t2m` (por defecto se busca con `comun.rutas.find_data_file`) |
| `--forzar-climatologia` | Reconstruye la climatología aunque el `.npz` ya exista |
| `--forzar` | Vuelve a bajar los pasos aunque ya estén completos |
| `--out` | Carpeta de salida (por defecto, `DATOS/crudos_anom2t_<modelo>_<fecha>_<ciclo>z`) |

- Los crudos quedan como `crudo_NNN_fhHHH.grib2` y la serie consolidada en
  `serie_anom_2t_c.npz`, con la anomalía en **°C** en `(pasos, 721, 1440)` float32, más `lat`,
  `lon`, `horas`, `fecha_init` y `modelo`.
- Es **reanudable**: un crudo con el tamaño exacto que publica el `.index` y el marco GRIB
  sano no se vuelve a pedir.
- La **base** es la misma de los demás productos ECMWF:
  `https://data.ecmwf.int/forecasts/{yyyymmdd}/{ciclo}z/ifs/0p25/oper/` (fecha **sin guiones**,
  ciclo con la `z` pegada).
- **Ventana rodante de 4 días**: como todo el ECMWF Open Data, sólo conserva las corridas
  recientes.

---

## `viento_250_mslp.py`

Baja el **viento en 250 mb** (`u` y `v`) y la **presión a nivel del mar** (`msl`) del **ECMWF
IFS 0.25°** (`oper`). Los tres campos se piden **por HTTP Range** con los offsets del `.index`,
igual que el resto de los productos ECMWF.

| Variable | Índice | Unidades | Uso |
|---|---|---|---|
| `u` | `levtype="pl"`, `levelist=250` | m s**-1 | viento zonal a 250 mb |
| `v` | `levtype="pl"`, `levelist=250` | m s**-1 | viento meridional a 250 mb |
| `msl` | `levtype="sfc"` | Pa | presión a nivel del mar |

**Ojo con el `.index`**: `levelist` viene como **string** (`"250"`), así que hay que castear
antes de comparar. Además `u`/`v` aparecen en muchos niveles de presión: sin filtrar por
`levtype` **y** `levelist` se agarra el nivel equivocado.

Las unidades de salida son `u`/`v` en **m/s** (el render multiplica por `1.9438445` para
obtener nudos) y `msl` en **hPa** (`Pa / 100`).

| Opción | Qué hace |
|---|---|
| `--fecha` | Día UTC de la corrida, `AAAA-MM-DD` (por defecto `2026-10-20`) |
| `--ciclo` | Ciclo UTC de la corrida: `00`, `06`, `12` o `18` (por defecto `18`) |
| `--hasta-hora` | Último paso de pronóstico en horas (por defecto `144`) |
| `--paso` | Horas entre pasos (por defecto `6`) |
| `--hilos` | Descargas simultáneas (por defecto `8`) |
| `--forzar` | Vuelve a bajar los pasos aunque ya estén completos |
| `--out` | Carpeta de salida (por defecto, `DATOS/crudos_viento250_<fecha>_<ciclo>z`) |

- Los crudos quedan como `crudo_NNN_fhHHH_u.grib2`, `crudo_NNN_fhHHH_v.grib2` y
  `crudo_NNN_fhHHH_msl.grib2` (uno por variable y paso), y la serie consolidada en
  `serie_viento_250.npz`, con `u_ms`, `v_ms` y `msl_hpa` en `(pasos, 721, 1440)` float32, más
  `lat`, `lon`, `horas` y `fecha_init`.
- Es **reanudable**: un crudo con el tamaño exacto que publica el `.index` y el marco GRIB
  sano no se vuelve a pedir.
- La **base** es `https://data.ecmwf.int/forecasts/{yyyymmdd}/{ciclo}z/ifs/0p25/oper/`
  (fecha **sin guiones**, ciclo con la `z` pegada).
- **Ventana rodante de 4 días**: el ECMWF Open Data sólo conserva las corridas recientes.
- Los pasos `12z` y `18z` publican hasta `144 h`.

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

## `descargar_himawari.py`

Baja la **banda 13 (infrarrojo ventana 10.4 µm) del AHI de Himawari-9** y la deja como
un `.npz` por slot de 10 min. Es el gemelo identico de `descargar_goes.py`, pero el dato no
viene en NetCDF: viene en **HSD** (Himawari Standard Data), un formato binario propio de
JMA, así que este script también lo decodifica.

Fuente: el bucket público de NOAA en AWS,
`https://noaa-himawari9.s3.amazonaws.com/AHI-L1b-FLDK/<AAA>/<MM>/<DD>/<HHMM>/`.

| Opción | Qué hace |
|---|---|
| `--desde` / `--hasta` | Ventana de slots, UTC |
| `--paso` | Minutos entre slots (por defecto 10) |
| `--banda` | Banda del AHI (por defecto 13) |
| `--sat` | Satélite (por defecto `H09`) |
| `--out` | Carpeta destino (por defecto `himawari_b13_h09`) |
| `--cache` | Si se pasa, guarda los `.DAT.bz2` crudos ahí (por defecto no) |

- Salida: `himawari_b13_h09/<AAAAMMDD_HHMM>.npz` con `tb` (2750×2750, °C), la geometría
  de la grilla (`x0`, `y0`, `dx`, `dy`, `sub_lon`, `a`, `b`, `h`) y la hora del slot.
- **El disco se guarda a 4 km** (promedio 2×2 de los 2 km nativos): mismo detalle
  efectivo que la serie GOES C13 a 2712 px, y 21 MB por slot en vez de 80.
- **El HSD no es trivial de leer**: la cabecera va en *little-endian*, son 11 bloques y
  el `blocklength` de cada uno dice dónde termina; los coeficientes de los canales IR
  van *dentro* del bloque 5; y el bloque 7 trae `first_line_number_of_image_segment`, que
  es lo que ordena las 10 franjas del disco. Todo está documentado en el código.
- Hay **slots que no están en el bucket** (404): el script los cuenta como error y
  sigue, así que la serie puede quedar con huecos.

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
