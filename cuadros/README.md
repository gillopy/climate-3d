# `cuadros/` — render cuadro por cuadro

Convierte datos ya descargados en los PNG de una animación. **No descarga ni arma el video**:
deja `cuadro_NNN.png` en `SALIDAS/frames_<etiqueta>/` y termina diciéndote qué correr en
`animar/`.

| Archivo | Entrada | Vista |
|---|---|---|
| `cuadros_goes.py` | `.nc` de GOES-R ABI (`DATOS/goes_<banda>_<sat>/`) | Disco, globo o zona |
| `cuadros_geocolor.py` | `crudo_NNN.jpg` de `descargar/geocolor.py` | Globo o plano |
| `cuadros_mur.py` | `crudo_NNN.jpg` de `descargar/mur_sst.py` | Globo |
| `cuadros_truecolor.py` | `crudo_NNN.jpg` de `descargar/truecolor.py` | Globo |
| `cuadros_sandwich.py` | `crudo_NNN_vis.jpg` + `crudo_NNN_ir.jpg` de `descargar/sandwich.py` | Globo |
| `cuadros_precipitacion.py` | `serie_tp_mm.npz` (o los `.grib2` / `--nc`) de `descargar/precipitacion_ecmwf.py` | Globo |
| `cuadros_anomalia_2t.py` | `serie_anom_2t_c.npz` de `descargar/anomalia_2t_ecmwf.py` | Globo |
| `cuadros_viento_250.py` | `serie_viento_250.npz` de `descargar/viento_250_mslp.py` | Globo |

Todos **reutilizan** los PNG que ya existen, así que si se corta se retoma donde quedó.
`cuadros_goes.py` además renderiza **por lotes en procesos separados**: con cientos de
cuadros, un solo proceso agota la RAM de una máquina chica.

---

## `cuadros_goes.py`

```powershell
# Globo centrado en Paraguay, 432 cuadros a 720 px
.venv\Scripts\python.exe cuadros\cuadros_goes.py --sat G19 --banda C13 --desde 2026-10-02 `
    --n 432 --px 720 --globo --centro -73 -18 --paleta ir_realce

# Disco completo
.venv\Scripts\python.exe cuadros\cuadros_goes.py --sat G18 --banda C04 --desde 2026-10-03 --n 144 --px 1200
```

| Opción | Qué hace |
|---|---|
| `--sat`, `--banda`, `--desde`, `--paso` | Igual que en la descarga |
| `--n` | Cantidad de cuadros a animar |
| `--px` | Lado de cada cuadro en píxeles |
| `--globo` | Reprojecta a Orthographic (aspecto "planeta") |
| `--centro LON LAT` / `--zona` | Dónde centrar el globo |
| `--geojson` | Borde destacado |
| `--paleta` | `ir_realce`, `termico`, `anomalia`, `gris`, `magma`, … |
| `--vmin` / `--vmax` | Escala fija (por defecto, percentiles del primer cuadro) |
| `--lote` | Cuadros por proceso (bajalo si te falta RAM) |
| `--datos` | Carpeta de los `.nc` |

---

## `cuadros_geocolor.py`

```powershell
.venv\Scripts\python.exe cuadros\cuadros_geocolor.py --globo --desde 2026-10-15T20:00 --n 24 --px 600
```

| Opción | Qué hace |
|---|---|
| `--desde`, `--n`, `--paso` | Qué ventana renderizar |
| `--globo` / `--centro` | Globo Orthographic o vista plana |
| `--px` | Lado de cada cuadro en píxeles |
| `--dpi` | dpi del render del globo |
| `--geojson`, `--borde-color`, `--borde-ancho` | Borde destacado |
| `--credito` | Crédito y marca de agua |
| `--sin-fecha` | No estampar la fecha/hora |

Es **offline por construcción**: sólo lee los `crudo_NNN.jpg` que dejó `descargar/geocolor.py`.
Si falta alguno, aborta nombrándote el comando exacto de descarga.

Dos cosas que costó dejar bien y conviene no romper:

- **El warp Orthographic es a mano** (mapeo inverso con numpy). Cartopy no se puede usar para
  reproyectar imágenes en este venv: su `imshow` con otra proyección importa `img_transform`,
  que exige `pykdtree` o `scipy`, y no están instalados.
- **Los rótulos escalan sub-lineal** (`esc = 0.8 · (px/720)^0.45`): lineal hacía que a 2048 px
  el título dominara el cuadro.

Además el render está **sellado**: si cambiás un parámetro de aspecto (texto, borde, escala),
los PNG viejos se descartan solos en vez de reutilizarse con el rótulo anterior.

---

## `cuadros_mur.py`

```powershell
# Semanal, dos años, globo a 2048 px
.venv\Scripts\python.exe cuadros\cuadros_mur.py --desde 2025-01-01 --hasta 2026-10-17 --paso 7 --px 2048
```

| Opción | Qué hace |
|---|---|
| `--desde` / `--hasta` / `--paso` | Qué ventana renderizar (paso en días) |
| `--px` | Lado del globo en píxeles (por defecto `2048`) |
| `--dpi` | dpi del render del globo |
| `--centro LON LAT` | Centro del globo (por defecto `-58 -23`) |
| `--geojson`, `--borde-color`, `--borde-ancho` | Borde destacado |
| `--credito` | Crédito y marca de agua |
| `--sin-fecha` | No estampar la fecha/hora |

MUR siempre es **global**: no hay modo plano ni `--globo`; todo se reproyecta a Orthographic
centrado en `--centro`, con el mismo vestuario y el mismo warp a mano que
`cuadros_geocolor.py`. Es **offline por construcción**: sólo lee los `crudo_NNN.jpg` que dejó
`descargar/mur_sst.py`; si falta alguno, aborta nombrándote el comando exacto de descarga.

---

## `cuadros_truecolor.py`

```powershell
# Diario, ventana de los incendios de 2024, globo a 2711 px
.venv\Scripts\python.exe cuadros\cuadros_truecolor.py --desde 2024-07-11 --hasta 2024-10-30 --paso 1 --px 2711
```

| Opción | Qué hace |
|---|---|
| `--desde` / `--hasta` / `--paso` | Qué ventana renderizar (paso en días) |
| `--capa` | Capa GIBS (mismo default que la descarga: NOAA-20) |
| `--px` | Lado del globo en píxeles (por defecto `2711`) |
| `--dpi` | dpi del render del globo |
| `--centro LON LAT` | Centro del globo (por defecto `-58 -23`) |
| `--geojson`, `--borde-color`, `--borde-ancho` | Borde destacado |
| `--credito` | Crédito y marca de agua |
| `--sin-fecha` | No estampar la fecha |

True Color siempre es **global**: no hay modo plano ni `--globo`; todo se reproyecta a
Orthographic centrado en `--centro`, con el mismo vestuario y el mismo warp a mano que
`cuadros_mur.py`. El nombre del sensor en los rótulos (`MODIS TERRA` / `MODIS AQUA` /
`VIIRS NOAA-20`) sale de `--capa`, y el sello de render incluye la capa: cambiar de sensor
no reutiliza los PNG del anterior. Es **offline por construcción**: sólo lee los
`crudo_NNN.jpg` que dejó `descargar/truecolor.py`; si falta alguno, aborta nombrándote el
comando exacto de descarga.

El default de `--capa` es **VIIRS NOAA-20**, el mismo que la descarga. Las composiciones
diarias de **Terra y Aqua (MODIS) dejan cuñas de barrido (swaths) cerca del ecuador**, que en
el globo se ven como franjas negras diagonales; por eso **no se recomiendan** para el globo y
NOAA-20 (cuyo barrido cubre la separación orbital) es la capa limpia.

---

## `cuadros_sandwich.py`

```powershell
# Convección de día, dos jornadas, globo a 2048 px
.venv\Scripts\python.exe cuadros\cuadros_sandwich.py --desde 2026-10-04 --hasta 2026-10-05 --hora-desde 10 --hora-hasta 22 --paso 10 --px 2048
```

| Opción | Qué hace |
|---|---|
| `--desde` / `--hasta` | Rango de días UTC a renderizar |
| `--hora-desde` / `--hora-hasta` / `--paso` | Tramo diurno y minutos entre cuadros (mismos que la descarga) |
| `--px` | Lado del globo en píxeles (por defecto `2048`) |
| `--dpi` | dpi del render del globo |
| `--centro LON LAT` | Centro del globo (por defecto `-58 -23`) |
| `--alpha` | Mezcla del Sandwich: `1` = sólo visible, `0` = sólo IR realzado (por defecto `0.5`) |
| `--bbox O S E N` | Caja de origen (mismo default que la descarga) |
| `--geojson`, `--borde-color`, `--borde-ancho` | Borde destacado |
| `--credito` | Crédito y marca de agua |
| `--sin-fecha` | No estampar la fecha/hora |

El **Sandwich RGB** mezcla **dos imágenes** en vez de combinar tres bandas: el fondo visible
aporta la morfología del tope nuboso y el IR realzado su temperatura. La composición es
`alpha · visible + (1 - alpha) · IR_realzado`, con el IR pasado por una rampa de color
(frío → rojo/naranja/amarillo/verde/cian) de la misma familia que
`poster_goes.IR_REALCE_COLORS`. `componer` arma la mezcla y recién después se reproyecta al
globo con el mismo warp a mano que el resto.

Es siempre **globo** (no hay modo plano) y **sub-diario**: la línea de tiempo lleva hora,
como GeoColor. El sello de render incluye el `alpha`: cambiar la mezcla descarta los PNG
viejos en vez de reutilizarlos. Es **offline por construcción**: sólo lee los
`crudo_NNN_vis.jpg` / `crudo_NNN_ir.jpg` que dejó `descargar/sandwich.py`; si falta alguno,
aborta nombrándote el comando exacto de descarga.

---

## `cuadros_precipitacion.py`

```powershell
# Póster de cierre FH +144 h, sin secuencia
.venv\Scripts\python.exe cuadros\cuadros_precipitacion.py --fecha 2026-10-20 --ciclo 06 --hasta-hora 144 --paso 3 --solo-poster

# Secuencia completa: 49 cuadros + póster a 2712 px
.venv\Scripts\python.exe cuadros\cuadros_precipitacion.py --fecha 2026-10-20 --ciclo 06 --hasta-hora 144 --paso 3

# Media del ensamble AIFS-ENS: 61 cuadros a 2712 px
.venv\Scripts\python.exe cuadros\cuadros_precipitacion.py --modelo aifs-ens --fecha 2026-10-20 --ciclo 12 --hasta-hora 360 --paso 6
```

| Opción | Qué hace |
|---|---|
| `--modelo` | Modelo de ECMWF Open Data: `ifs`, `aifs-ens` o `aifs-single` (por defecto `ifs`) |
| `--fecha` | Día UTC de la corrida, `AAAA-MM-DD` (por defecto `2026-10-20`) |
| `--ciclo` | Ciclo UTC de la corrida: `00`, `06`, `12` o `18` (por defecto `06`) |
| `--hasta-hora` / `--paso` | Último paso y horas entre pasos (por defecto `144` y `3`) |
| `--px` | Lado del rectángulo donde se warpea el disco (por defecto `2712`) |
| `--centro LON LAT` | Centro del globo (por defecto `-58 -23`: Paraguay) |
| `--radio` | Grados al borde del disco; `90` = hemisferio (por defecto `58`) |
| `--fondo-globo` | `claro` u `oscuro` (por defecto `claro`) |
| `--solo-poster` | Renderiza sólo el póster estático del último paso |
| `--forzar` | Vuelve a renderizar los cuadros aunque los PNG ya existan |
| `--nc` | Archivo ERA5 (`.nc`/`.npz`) alternativo a los crudos |
| `--crudos` | Carpeta de entrada (por defecto, la que deja el descargador) |

Lee `serie_tp_mm.npz`, que ya viene en **mm**; si no existe, decodifica al vuelo los
`crudo_*_fh*.grib2` de la corrida, y con `--nc` puede leer un acumulado de ERA5 (`.nc` o
`.npz`) para el mismo diseño. La geometría del **warp Orthographic** —índices bilineales,
pesos y factor de luz esférico— se **precomputa una sola vez**, así que cada cuadro cuesta
sólo cuatro lecturas por píxel y una mezcla.

El campo se interpola a resolución de píxel y recién después se mapea a la **paleta discreta
de 30 niveles** de Tropical Tidbits (`0.2` a `500+ mm`): verdes, azules, violetas, bordó/rojos
y naranjas/amarillos. Donde llueve menos de `0.2 mm` el alfa queda en 0 y se ve la superficie
base del globo (océano y tierra) con el sombreado esférico 3D hacia el limbo. Encima van
costas, fronteras y el contorno de **Paraguay** (`datos/paraguay_gadm.json`), más el aro del
disco y la barra de colores al pie.

Las salidas son dos:

- `poster_precip_ecmwf_<fecha>_<ciclo>z_fh<hora>.png` — el póster estático del último paso.
- `frames_precipitacion_globo_<AAAA-MM-DDTHHMM>_<N>f_<PX>px/cuadro_NNN.png` — la secuencia
  (49 cuadros de `2712x2712 px` con `--hasta-hora 144 --paso 3`), lista para `animar/armar.py`.

**Con `--modelo` cambian el nombre del póster y la carpeta de cuadros**, para que una corrida
no pise a la de otro modelo:

| `--modelo` | Póster | Carpeta de cuadros |
|---|---|---|
| `ifs` | `poster_precip_ecmwf_<fecha>_<ciclo>z_fh<hora>.png` | `frames_precipitacion_globo_<...>` |
| `aifs-ens` | `poster_precip_aifs-ens_<fecha>_<ciclo>z_fh<hora>.png` | `frames_precipitacion_aifs_ens_globo_<...>` |
| `aifs-single` | `poster_precip_aifs-single_<fecha>_<ciclo>z_fh<hora>.png` | `frames_precipitacion_aifs_single_globo_<...>` |

El **título** y el **pie de fuente** cambian con el modelo, y el modelo forma parte de la
huella del render: un PNG de un modelo no se reutiliza para otro.

El guardado es **atómico** y el render está **sellado**: si cambiás `--px`, `--dpi`,
`--centro`, `--radio`, el fondo, el crédito o la paleta, los PNG viejos se descartan solos en
vez de reutilizarse con otro aspecto. Es **offline por construcción**: sólo lee los crudos que
dejó `descargar/precipitacion_ecmwf.py`; si no hay datos, aborta nombrándote el comando exacto
de descarga.

---

## `cuadros_anomalia_2t.py`

```powershell
# Póster de cierre FH +360 h, sin secuencia
.venv\Scripts\python.exe cuadros\cuadros_anomalia_2t.py --fecha 2026-10-20 --ciclo 12 --hasta-hora 360 --paso 6 --solo-poster

# Secuencia completa: 61 cuadros + póster a 2712 px
.venv\Scripts\python.exe cuadros\cuadros_anomalia_2t.py --fecha 2026-10-20 --ciclo 12 --hasta-hora 360 --paso 6
```

| Opción | Qué hace |
|---|---|
| `--modelo` | Modelo de ECMWF Open Data: `ifs` o `aifs-single` (por defecto `ifs`) |
| `--fecha` | Día UTC de la corrida, `AAAA-MM-DD` (por defecto `2026-10-20`) |
| `--ciclo` | Ciclo UTC de la corrida: `00`, `06`, `12` o `18` (por defecto `12`) |
| `--hasta-hora` / `--paso` | Último paso y horas entre pasos (por defecto `360` y `6`) |
| `--px` | Lado del rectángulo donde se warpea el disco (por defecto `2712`) |
| `--dpi` | dpi del render (por defecto `140`) |
| `--centro LON LAT` | Centro del globo (por defecto `-58 -23`: Paraguay) |
| `--radio` | Grados al borde del disco; `90` = hemisferio (por defecto `58`) |
| `--fondo-globo` | `claro` u `oscuro` (por defecto `claro`) |
| `--credito` | Crédito de la esquina superior |
| `--solo-poster` | Renderiza sólo el póster estático del último paso |
| `--forzar` | Vuelve a renderizar los cuadros aunque los PNG ya existan |
| `--crudos` / `--out-crudos` | Carpeta de entrada (por defecto, la que deja el descargador) |
| `--salidas` / `--out` | Carpeta de salida (por defecto `comun.rutas.SALIDAS`) |

Lee `serie_anom_2t_c.npz`, que ya viene con la **anomalía en °C** (la calcula
`descargar/anomalia_2t_ecmwf.py` contra la climatología diurna de ERA5). La geometría del
**warp Orthographic** —índices bilineales, pesos y factor de luz esférico— se **precomputa una
sola vez**, así que cada cuadro cuesta sólo cuatro lecturas por píxel y una mezcla.

El campo se interpola a resolución de píxel y recién después se mapea a la **paleta divergente
discreta de 37 colores** de Tropical Tidbits (35 intervalos entre `-28` y `+28 °C`, más las
extensiones `under` y `over`): violetas y rosas para el frío extremo, azules y cianes en el
frío, amarillos, naranjas y rojos en el cálido. La **banda neutra `[-0.5, +0.5] °C` queda
transparente**, así que ahí se ve la **superficie base del globo** (océano, tierra y el
sombreado esférico hacia el limbo) en vez de un parche blanco. Encima van costas, fronteras
y el contorno de **Paraguay** (`datos/paraguay_gadm.json`), más el aro del disco y la barra
de colores al pie.

**Memoria plana a 2712 px**: el blend bilineal va **por bloques de filas** (`512`) en
**float32**, y el color se busca con una **consulta directa a la tabla RGBA** (sin máscaras
booleanas 1D). A resolución completa, un blend entero en float64 dispararía el consumo de RAM
y el OOM por los temporales; así el pico se mantiene plano.

Las salidas son dos:

- `poster_anom2t_<modelo>_<fecha>_<ciclo>z_fh<hora>.png` — el póster estático del último paso.
- `frames_anomalia_2t_<modelo>_globo_<AAAA-MM-DDTHHMM>_<N>f_<PX>px/cuadro_NNN.png` — la
  secuencia (61 cuadros de `2712x2712 px` con `--hasta-hora 360 --paso 6`), lista para
  `animar/armar.py`.

El guardado es **atómico** y el render está **sellado**: si cambiás `--px`, `--dpi`,
`--centro`, `--radio`, el fondo, el crédito o el modelo, los PNG viejos se descartan solos.
Es **offline por construcción**: sólo lee la serie que dejó
`descargar/anomalia_2t_ecmwf.py`; si no hay datos, aborta nombrándote el comando exacto de
descarga.

---

## `cuadros_viento_250.py`

```powershell
# Póster de cierre FH +144 h, sin secuencia
.venv\Scripts\python.exe cuadros\cuadros_viento_250.py --fecha 2026-10-20 --ciclo 18 --hasta-hora 144 --paso 6 --solo-poster

# Secuencia completa: 25 cuadros + póster a 2712 px
.venv\Scripts\python.exe cuadros\cuadros_viento_250.py --fecha 2026-10-20 --ciclo 18 --hasta-hora 144 --paso 6
```

| Opción | Qué hace |
|---|---|
| `--fecha` | Día UTC de la corrida, `AAAA-MM-DD` (por defecto `2026-10-20`) |
| `--ciclo` | Ciclo UTC de la corrida: `00`, `06`, `12` o `18` (por defecto `18`) |
| `--hasta-hora` / `--paso` | Último paso y horas entre pasos (por defecto `144` y `6`) |
| `--px` | Lado del rectángulo donde se warpea el disco (por defecto `2712`) |
| `--dpi` | dpi del render (por defecto `140`) |
| `--centro LON LAT` | Centro del globo (por defecto `-58 -23`: Paraguay) |
| `--radio` | Grados al borde del disco; `90` = hemisferio (por defecto `58`) |
| `--fondo-globo` | `claro` u `oscuro` (por defecto `claro`) |
| `--credito` | Crédito de la esquina superior |
| `--solo-poster` | Renderiza sólo el póster estático del último paso |
| `--forzar` | Vuelve a renderizar los cuadros aunque los PNG ya existan |
| `--crudos` | Carpeta de entrada (por defecto, la que deja el descargador) |
| `--salidas` | Carpeta de salida (por defecto `comun.rutas.SALIDAS`) |

Lee `serie_viento_250.npz`, que trae `u_ms`, `v_ms` y `msl_hpa` en la rejilla `721 x 1440`. La
velocidad del viento sale de `hypot(u, v) × 1.9438445` (m/s → nudos) y se pinta con la
**escala discreta de 10 kt de 20 a 250** (cian → verde → amarillo → naranja → rojo → bordó →
violeta → magenta → rosa → marrón), con extensión `under` (< 20 kt) y `over` (> 250 kt). A
diferencia de la anomalía, **todo el disco es opaco**: las zonas de viento débil toman el color
`under`.

Encima van dos capas extra:

- **Streamlines**: las líneas de corriente se calculan con `streamplot` sobre una rejilla
  regular de ~1° y se dibujan como un único `LineCollection` de trazos finos y oscuros
  (`0.35 pt`), con las **puntas de flecha triangulares dibujadas a mano** (matplotlib
  dibuja las suyas con `arrowsize=0`).
- **Extremos de MSLP**: marcadores `L` en **rojo** y `H` en **azul**, con el valor en **hPa**
  arriba. Sólo cuentan los más significativos (`L` por debajo de `1002 hPa`, `H` por encima de
  `1016 hPa`), con un máximo de 6 de cada tipo, separados al menos 4° entre sí y dentro del
  disco.

La geometría del **warp Orthographic** se **precomputa una sola vez** y el blend va **por
bloques de filas** en **float32**, con la **consulta directa a la tabla RGBA**: a
`2712x2712 px` el consumo de RAM se mantiene plano.

Las salidas son dos:

- `poster_viento250_<fecha>_<ciclo>z_fh<hora>.png` — el póster estático del último paso.
- `frames_viento_250_globo_<AAAA-MM-DDTHHMM>_<N>f_<PX>px/cuadro_NNN.png` — la secuencia
  (25 cuadros de `2712x2712 px` con `--hasta-hora 144 --paso 6`), lista para `animar/armar.py`.

El guardado es **atómico** y el render está **sellado**: si cambiás `--px`, `--dpi`,
`--centro`, `--radio`, el fondo, el crédito, la escala de colores o los umbrales de MSLP, los
PNG viejos se descartan solos. Es **offline por construcción**: sólo lee la serie que dejó
`descargar/viento_250_mslp.py`; si no hay datos, aborta nombrándote el comando exacto de
descarga.

---

## Nota sobre huecos

Si un slot se cae (por ejemplo, un cuadro sin dato), la numeración queda con un hueco y
`animar/armar.py` lo va a rechazar — **y está bien**, porque `ffmpeg` cortaría el video ahí sin
avisar. Renumerá los posteriores o volvé a renderizar.

## Next step

[`../animar/`](../animar): convertir esa carpeta de cuadros en un MP4 o un GIF.
