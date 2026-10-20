# Climate 3D

![Póster GOES-19 · disco completo · 4 de octubre de 2026, 04:45 UTC](docs/portada.png)

Animaciones y pósteres del clima con datos reales: **ERA5** (reanálisis) y
**GOES-R ABI** (satélite). Todo se renderiza local con matplotlib + cartopy en un
estilo de afiche — fondo oscuro, barra de color fina al pie, rótulos discretos.
No hay servicios ni cuentas de por medio: bajás el dato y lo dibujás.

## Las cuatro etapas

El repo está separado por **rol**, y se lee en el orden en que se usa:

| Carpeta | Qué hace | ¿Internet? |
| --- | --- | --- |
| [`descargar/`](./descargar) | Baja los datasets (NOAA S3, Copernicus CDS, NASA GIBS) | **Sí** |
| [`prototipos/`](./prototipos) | Pósteres e imágenes fijas, y los notebooks originales | No |
| [`cuadros/`](./cuadros) | Renderiza una animación cuadro por cuadro | No |
| [`animar/`](./animar) | Junta los cuadros en un MP4 o un GIF | No |

### Scripts por etapa

| Etapa | Scripts |
| --- | --- |
| `descargar/` | `descargar_goes.py`, `descargar_era5.py`, `geocolor.py`, `mur_sst.py`, `truecolor.py`, `sandwich.py`, `precipitacion_ecmwf.py` |
| `prototipos/` | `poster_goes.py`, `poster_anomalia.py`, `vista_paraguay.py` |
| `cuadros/` | `cuadros_goes.py`, `cuadros_geocolor.py`, `cuadros_mur.py`, `cuadros_truecolor.py`, `cuadros_sandwich.py`, `cuadros_precipitacion.py` |
| `animar/` | `armar.py` |

Aparte, [`comun/`](./comun) guarda lo compartido (rutas y constantes de estilo), también sin
red.

**Sólo `descargar/` necesita conexión.** Todo lo demás trabaja sobre lo ya bajado, así que
podés renderizar y animar sin internet.

Si es tu primera vez, andá a [`GUIA.md`](./GUIA.md): ahí está el flujo completo explicado paso
a paso.

## Dónde viven los datos

Los `.nc` pesan varios GB y las salidas también, así que **no van al repo**. La raíz de datos
la define un solo archivo, [`comun/rutas.py`](./comun/rutas.py), y por defecto apunta a
`D:\Users\guill\dataset era5`.

Si tus datos están en otro lado, no toques código:

```powershell
$env:CLIMATE3D_DATOS = "D:\mi\carpeta\datos"
```

## Qué se puede lograr

Ocho salidas del mismo pipeline, todas con datos reales. En
[`docs/galeria/`](./docs/galeria) están las demás.

### GeoColor (GOES-East): color real de día, IR y luces de ciudad de noche

El mismo globo, el mismo día, a las 16:50 y a las 04:00 UTC:

| Día · 16:50 UTC | Noche · 04:00 UTC |
| --- | --- |
| ![GeoColor de día — 4 de octubre de 2026, 16:50 UTC](docs/galeria/geocolor_globo_G19_2026-10-04T1650.png) | ![GeoColor de noche — 4 de octubre de 2026, 04:00 UTC](docs/galeria/geocolor_globo_G19_2026-10-04T0400.png) |

GeoColor no es una banda: es un producto RGB ya mezclado. **De día** se ve color real —la
Amazonía en verde, los Andes en ocre, el océano y las nubes tal como los vería el ojo—.
**De noche** el terreno da paso al infrarrojo, que separa las nubes bajas de agua líquida
(azul claro) de las altas de hielo (gris y blanco), y por encima van las **luces de ciudad**:
esas motas anaranjadas sobre la costa de Brasil y los Andes. Se baja de NASA GIBS, así que no
hay `.nc` que leer.

### Anomalía de temperatura (ERA5): el mes contra su propia climatología

![Anomalía de temperatura de agosto de 2026](docs/galeria/planeta_anomalia_2026-08.png)

Cada mes se compara contra la climatología de ese mismo mes calculada con **los otros años**
del archivo. El rojo es más calor que lo normal, el azul menos.

### Cirrus C04 (GOES-West): reflectancia en 1.4 µm

![Cirrus C04 de GOES-West, 3 de octubre de 2026](docs/galeria/poster_cirrus_G18_2026-10-03T2220.png)

La banda de cirrus aísla las nubes altas de hielo y las despega del resto de la escena: los
topes convectivos aparecen en rojo sobre un fondo casi negro.

### Anomalía de SST (MUR): el Pacífico ecuatorial, semana a semana

![Anomalía de SST del 1 de enero de 2025](docs/galeria/mur_sst_globo_2025-01-01.png)

El producto **GHRSST MUR (v4.1) Sea Surface Temperature Anomalies** es global y diario. Acá
se anima **una muestra por semana**: del 2025-01-01 al 2026-10-17 son **94 cuadros**. El globo
es Orthographic y está centrado en la **región Niño 3.4 corrida al este** (`-125 0`), así
Sudamérica entra por el borde derecho. Las anomalías cálidas van en naranja y rojo, las frías
en cian y azul, y la tierra y los polos quedan enmascarados en negro. Se baja de **NASA GIBS**
(Worldview Snapshots API), igual que GeoColor: no hay `.nc` que leer. Los scripts son
[`descargar/mur_sst.py`](./descargar/mur_sst.py) y [`cuadros/cuadros_mur.py`](./cuadros/cuadros_mur.py).

### True Color (VIIRS): el humo de los incendios de 2024

![True Color del 28 de setiembre de 2024](docs/galeria/truecolor_noaa20_globo_2024-09-28.png)

Es la **Corrected Reflectance (True Color)** de **VIIRS NOAA-20** vía NASA GIBS, a **250 m** y
con composición **diaria**. El remate va del 2024-07-11 al 2024-10-30: **112 cuadros** en globo
Orthographic sobre Paraguay. **Por qué no GeoColor**: esa capa en GIBS sólo tiene ventana
reciente (arranca el 2026-08-10), no hay archivo 2024. Y GOES-16 no publica ningún producto de
color real: habría que componer bandas a mano. **Por qué NOAA-20 y no MODIS**: los MODIS
(Terra y Aqua) dejan **cuñas negras de barrido** sobre el ecuador porque su ancho de barrido es
menor que la separación orbital; VIIRS NOAA-20 no. Los scripts son
[`descargar/truecolor.py`](./descargar/truecolor.py) y [`cuadros/cuadros_truecolor.py`](./cuadros/cuadros_truecolor.py).

### Sandwich RGB (GOES-19): la textura de las nubes sobre su temperatura

![Sandwich RGB del 4 de octubre de 2026, 18:00 UTC](docs/galeria/sandwich_globo_G19_2026-10-04T1800.png)

El Sandwich **no es un RGB de tres bandas**: junta **dos imágenes**. El **visible (0.64 µm)**
pone la *morfología* del tope nuboso —las sombras que delatan un *overshooting top*, ondas de
gravedad, plumas de hielo— y el **IR de 10.3 µm realzado en color** pone la *temperatura* de
ese tope. Se mezclan 50/50 y queda una sola imagen: el color dice cuán frío (y alto) está el
tope, el gris del visible dice qué forma tiene. Es **de día**: sin sol el visible es negro, así
que se animan los **tramos diurnos del 4 y 5 de octubre de 2026** (10:00 a 22:00 UTC, paso 10
min) → **146 cuadros** en globo Orthographic sobre Paraguay. Se compone a partir de dos capas de
**NASA GIBS** (`GOES-East_ABI_Band2_Red_Visible_1km` y `GOES-East_ABI_Band13_Clean_Infrared`),
no de los `.nc`: el ABI **C02 a 0.5 km pesa ~200 MB por archivo**, inviable para cientos de
cuadros. Como GOES-East no ve el hemisferio centrado en Paraguay entero, el disco se dibuja con
`--radio` (~53°) para que el borde entre dentro de lo que ve el satélite y no quede un gajo sin
dato. Los scripts son [`descargar/sandwich.py`](./descargar/sandwich.py) y
[`cuadros/cuadros_sandwich.py`](./cuadros/cuadros_sandwich.py).

### Precipitación total acumulada (ECMWF): 144 h de lluvia sobre Sudamérica

![Precipitación total acumulada de ECMWF, FH +144 h](docs/galeria/precip_globo_ecmwf_2026-10-20_06z_fh144.png)

El **acumulado total de precipitación (`tp`)** de **ECMWF IFS 0.25°** (`oper`) no es una
imagen satelital: es un campo del modelo. La corrida `06z` del 20 de octubre de 2026 cubre
**0 a 144 h** (hasta el 26 de octubre, 06z) en pasos de **3 h**: **49 cuadros** en globo
Orthographic centrado en Paraguay. `tp` viene acumulado desde el inicio de la corrida en
metros de agua equivalente, así que se convierte a **mm** y se pinta con la **paleta discreta
de 30 niveles** de Tropical Tidbits (`0.2` a `500+ mm`), con sombreado esférico 3D, costas,
fronteras y el contorno de Paraguay. El póster de cierre (`FH +144 h`) muestra el máximo sobre
Paraguay y el sur de Brasil. En vez de bajar los ~4,8 GB de GRIB2 de los 49 pasos, el
descargador lee el `.index` de cada paso y pide **sólo el rango de bytes** de `tp`/`sfc`:
~20 MB en total. Los scripts son
[`descargar/precipitacion_ecmwf.py`](./descargar/precipitacion_ecmwf.py) y
[`cuadros/cuadros_precipitacion.py`](./cuadros/cuadros_precipitacion.py).

## Requisitos

- Python 3.14 y el entorno `.venv` de la raíz.
- Las dependencias están fijadas en [`requirements.txt`](./requirements.txt).

```powershell
.venv\Scripts\python.exe -c "import cartopy, matplotlib, requests, PIL, eccodes; print('ok')"
```

## Primeros pasos

```powershell
# 1) Bajar un dataset (GOES-East C13, 3 días)
.venv\Scripts\python.exe descargar\descargar_goes.py --sat G19 --banda C13 --desde 2026-10-02 --hasta 2026-10-05

# 2) Un póster fijo de disco completo
.venv\Scripts\python.exe prototipos\poster_goes.py --paleta ir_realce

# 3) Renderizar los cuadros de la animación (globo centrado en Paraguay, 432 a 720 px)
.venv\Scripts\python.exe cuadros\cuadros_goes.py --sat G19 --banda C13 --desde 2026-10-02 `
    --n 432 --px 720 --globo --centro -73 -18 --paleta ir_realce

# 4) Armar el MP4
.venv\Scripts\python.exe animar\armar.py --frames "D:\Users\guill\dataset era5\salidas\frames_G19_2026-10-02T0000_432f_720px" --fps 12.5
```

Cada etapa imprime al terminar **el comando de la siguiente**, así que en la práctica alcanza
con arrancar por la 1.

## Ruta rápida: precipitación ECMWF en 3 pasos

El flujo completo del globo de **precipitación total acumulada** (49 cuadros de `2712x2712 px`):

```powershell
# 1) Descargar tp de la corrida 06z del 20 de octubre de 2026 (0h a 144h, paso 3h)
.venv\Scripts\python.exe descargar\precipitacion_ecmwf.py --fecha 2026-10-20 --ciclo 06 --hasta-hora 144 --paso 3

# 2) Renderizar los 49 cuadros y el póster de cierre FH +144 h (2712 px)
.venv\Scripts\python.exe cuadros\cuadros_precipitacion.py --fecha 2026-10-20 --ciclo 06 --hasta-hora 144 --paso 3

# Sólo el póster, sin la secuencia
.venv\Scripts\python.exe cuadros\cuadros_precipitacion.py --fecha 2026-10-20 --ciclo 06 --hasta-hora 144 --paso 3 --solo-poster

# 3) Armar el MP4
.venv\Scripts\python.exe animar\armar.py --frames "D:\Users\guill\dataset era5\salidas\frames_precipitacion_globo_2026-10-20T0600_49f_2712px" --fps 12.5
```

El póster queda en `SALIDAS/poster_precip_ecmwf_2026-10-20_06z_fh144.png` y los cuadros en la
carpeta `frames_precipitacion_globo_...` que imprime el paso 2.

## El formato

Todas las salidas comparten el mismo vestuario, así que un póster, un cuadro de animación o
una vista regional se leen igual:

- El **crédito** (`Graphic by @Gillo97`) va arriba a la derecha y repetido como marca de agua.
  Se cambia con `--credito`.
- Debajo del título va la **fecha y hora del cuadro, grande**: es lo primero que uno quiere
  leer.
- El **contorno de Paraguay** se dibuja negro y fino (0.8 pt), sutil sobre el mapa. Se activa
  con `--geojson` y se apaga con `--sin-borde`.
- **Paletas**: `ir_realce` (IR con color en los topes fríos), `termico`, `anomalia`, `gris`,
  `magma`, `inferno`, `turbo`.

En las animaciones los rótulos escalan **sub-linealmente** con la resolución: si escalaran
linealmente, a 2048 px el título se comería el cuadro.

## Notas

- Los `.nc`, `.gif` y `.log` están ignorados; las imágenes de `docs/` se exceptúan a
  propósito.
- Las animaciones salen en **MP4** con el ffmpeg que trae `imageio-ffmpeg` — no hace falta
  tenerlo en el PATH. El GIF queda para el loop universal, pero a alta resolución y muchos
  cuadros pesa cientos de MB.
- Los slots GOES son cada 10 min (modo 6) y la hora sale del nombre del archivo, no la
  escribas a mano. Ojo: el `t` del producto cae unos 5 min después del inicio del escaneo,
  así que un archivo que arranca a las 04:40 se rotula 04:45.
- **cartopy baja shapefiles de Natural Earth la primera vez** que dibuja costas. Ese primer
  render necesita internet aunque el resto del paso no; después quedan cacheados.
