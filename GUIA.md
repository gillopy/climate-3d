# Guía: de un dataset satelital a una animación

Esta guía te deja hacer el flujo completo **sin depender de nadie**: bajar un dataset de NOAA
y convertirlo en una animación.

El repo está separado en cuatro etapas, y ese es siempre el orden:

```
descargar/     ->   prototipos/        ->   cuadros/            ->   animar/
baja el dato        imagen fija             render cuadro a cuadro     MP4 / GIF
(necesita red)      (opcional, offline)     (offline)                  (offline)
```

> Todo va a `D:\Users\guill\dataset era5` salvo que exportes `CLIMATE3D_DATOS`. Los `.nc`
> (varios GB) y las salidas (PNG/MP4) **nunca** van dentro del repositorio.

**Sólo la etapa 1 necesita internet.** Las otras tres trabajan sobre lo que ya bajaste; si les
falta un dato, te dicen qué comando correr.

---

## 1. Elegir satélite y banda

**Satélite (por cobertura):**

| Satélite | Posición | Conviene para |
|---|---|---|
| **GOES-East** `G16` / `G19` | 75.2° O | **Sudamérica, Paraguay**, Brasil |
| GOES-West `G17` / `G18` | 137° O | Pacífico, EE.UU. (Paraguay cae al borde del disco) |

**Banda (por lo que querés ver):**

| Banda | Longitud | Qué muestra |
|---|---|---|
| `C13` | 10.3 µm | Infrarrojo "limpio": nubes de día y de noche (lo habitual) |
| `C02` | 0.64 µm | Visible: sólo de día |
| `C04` | 1.38 µm | Cirrus |

La clave es la carpeta destino: `goes_<banda>_<sat>` (ej. `goes_c13_g19`).

---

## 2. Descargar el dataset

`descargar/descargar_goes.py` baja los `.nc` desde el bucket público de NOAA S3 y **saltea los
que ya tenés**.

```powershell
# GOES-East C13 (infrarrojo) del 2 al 5 de octubre de 2026 (≈ 432 cuadros, ~10 GB)
.venv\Scripts\python.exe descargar\descargar_goes.py --sat G19 --banda C13 --desde 2026-10-02 --hasta 2026-10-05

# Ver la ayuda (NO toca la red)
.venv\Scripts\python.exe descargar\descargar_goes.py --help
```

| Opción | Qué hace |
|---|---|
| `--sat` | Satélite (`G19`, `G18`, …) |
| `--banda` | Banda (`C13`, `C04`, …) |
| `--desde` / `--hasta` | Rango UTC (`AAAA-MM-DD` o `AAAA-MM-DDTHH:MM`) |
| `--paso` | Minutos entre cuadros (por defecto 10; la cadencia real de ABI) |
| `--out` | Carpeta destino (por defecto, `goes_<banda>_<sat>`) |

- La cadencia real de ABI es de **10 minutos** (modo 6). 24 h = 144 cuadros; 3 días = 432.
- Es una descarga larga (~10 GB) y **reanudable**: si la cortás, volvé a correrla y sigue.

---

## 3. Una imagen fija (opcional)

Antes de animar 432 cuadros, conviene mirar uno solo. `prototipos/` tiene los generadores de
pósteres; todos funcionan sin conexión.

```powershell
# Disco completo con la rampa de IR
.venv\Scripts\python.exe prototipos\poster_goes.py --paleta ir_realce

# El globo centrado en Paraguay
.venv\Scripts\python.exe prototipos\vista_paraguay.py

# Zona Sudamérica, a globo
.venv\Scripts\python.exe prototipos\poster_goes.py --globo --zona sa
```

Para experimentar con más libertad están los notebooks de
[`prototipos/notebooks/`](./prototipos/notebooks): abrilos y corré las celdas.

---

## 4. Renderizar los cuadros

`cuadros/cuadros_goes.py` renderiza por **lotes en procesos separados**: renderizar cientos de
cuadros en un solo proceso agota la memoria de una máquina chica.

```powershell
# Globo centrado en Paraguay, 432 cuadros a 720 px (el caso de la guía)
.venv\Scripts\python.exe cuadros\cuadros_goes.py --sat G19 --banda C13 --desde 2026-10-02 `
    --n 432 --px 720 --globo --centro -73 -18 --paleta ir_realce

# Prueba rápida antes de largar en serio
.venv\Scripts\python.exe cuadros\cuadros_goes.py --sat G19 --banda C13 --desde 2026-10-02 --n 4 --px 480 --globo
```

| Opción | Qué hace |
|---|---|
| `--sat`, `--banda`, `--desde`, `--paso` | Igual que en la descarga |
| `--n` | Cantidad de cuadros a animar |
| `--px` | Lado de cada cuadro en píxeles (más px = más lento y pesado) |
| `--globo` | Reprojecta a Orthographic (aspecto "planeta") |
| `--centro LON LAT` / `--zona py` | Dónde centrar el globo |
| `--geojson` | Borde destacado (ej. `datos\paraguay_gadm.json`) |
| `--paleta` | `ir_realce`, `termico`, `anomalia`, `gris`, `magma`, … |
| `--vmin` / `--vmax` | Escala fija (por defecto, percentiles del primer cuadro) |
| `--lote` | Cuadros por proceso (bajalo si te falta RAM: `--lote 12`) |

- Los cuadros se guardan como PNG y **se reutilizan** si ya están: si sólo querés rearmar el
  MP4, salta el render y pasás directo a la etapa 5.
- Si el render se corta, volvé a correrlo: completa lo que falta.

---

## 5. Armar la animación

```powershell
.venv\Scripts\python.exe animar\armar.py --frames "D:\Users\guill\dataset era5\salidas\frames_G19_2026-10-02T0000_432f_720px" --fps 12.5
```

| Opción | Qué hace |
|---|---|
| `--frames` | Carpeta con los `cuadro_NNN.png` |
| `--fps` | Velocidad del MP4 (por defecto 12,5) |
| `--formato` | `mp4`, `gif` o `ambos` (por defecto `mp4`) |
| `--salida` | Archivo de salida; si no, se deriva del nombre de la carpeta |

El nombre sale del de la carpeta, con la **cantidad real** de cuadros:

```
frames_G19_2026-10-02T0000_432f_720px   ->   animacion_G19_2026-10-02T0000_432f_720px.mp4
```

Si la carpeta dijera `432f` pero adentro hubiera 431, el video sale como `431f`. Y si la
numeración tiene un hueco, aborta — `ffmpeg` cortaría el video ahí sin avisar.

---

## 6. Dónde quedan las salidas

En `D:\Users\guill\dataset era5\salidas`:

| Archivo | Qué es |
|---|---|
| `frames_<lo que defina el renderizador>\` | Los cuadros PNG (podés borrarlos al terminar) |
| `animacion_<lo mismo>.mp4` | La animación |
| `poster_*.png`, `vista_paraguay_*.png` | Cuadros fijos |

El nombre de la carpeta lo define quién renderiza, y `animar/armar.py` deriva el video de ahí
(`frames_` → `animacion_`):

| Renderizador | Carpeta de cuadros |
|---|---|
| `cuadros/cuadros_goes.py` | `frames_<SAT>_<AAAA-MM-DDTHHMM>_<N>f_<PX>px` |
| `cuadros/cuadros_geocolor.py` | `frames_geocolor_<vista>_<AAAA-MM-DDTHHMM>_<N>f_<PX>px` |
| `cuadros/cuadros_mur.py` | `frames_mur_globo_<AAAA-MM-DDTHHMM>_<N>f_<PX>px` |
| `cuadros/cuadros_truecolor.py` | `frames_truecolor_<sensor>_globo_<AAAA-MM-DDTHHMM>_<N>f_<PX>px` |
| `cuadros/cuadros_sandwich.py` | `frames_sandwich_globo_<AAAA-MM-DDTHHMM>_<N>f_<PX>px` |

El nombre incluye **inicio + cantidad de cuadros + px**, así que una corrida **no pisa** la de
otra ventana o resolución.

---

## 7. Chuleta

```powershell
# 1) Descargar (GOES-East C13, 3 días)
.venv\Scripts\python.exe descargar\descargar_goes.py --sat G19 --banda C13 --desde 2026-10-02 --hasta 2026-10-05

# 2) Mirar un cuadro fijo
.venv\Scripts\python.exe prototipos\poster_goes.py --paleta ir_realce

# 3) Renderizar 432 cuadros (globo Paraguay, 720 px)
.venv\Scripts\python.exe cuadros\cuadros_goes.py --sat G19 --banda C13 --desde 2026-10-02 --n 432 --px 720 --globo --centro -73 -18 --paleta ir_realce

# 4) Armar el MP4
.venv\Scripts\python.exe animar\armar.py --frames "D:\Users\guill\dataset era5\salidas\frames_G19_2026-10-02T0000_432f_720px"
```

---

## 8. Flujo extra: MUR SST (anomalía semanal en globo)

MUR es un producto **global** de anomalía de temperatura superficial del mar (GHRSST L4
v4.1). No es una banda GOES: es otro dataset, con su propio par descarga/render, pero pasa
por las mismas cuatro etapas de siempre (identificar → descargar → cuadros → animar).

**Identificar.** Producto GHRSST MUR v4.1, capa *Sea Surface Temperature Anomalies*; en GIBS
es `GHRSST_L4_MUR_Sea_Surface_Temperature_Anomalies`. Cobertura global y cadencia diaria,
pero como la animación abarca dos años se muestrea **una vez por semana**.

**Descargar.**

```powershell
.venv\Scripts\python.exe descargar\mur_sst.py --desde 2025-01-01 --hasta 2026-10-17 --paso 7 --px 2048
```

**Cuadros.** El comando exacto lo imprime la descarga al terminar:

```powershell
.venv\Scripts\python.exe cuadros\cuadros_mur.py --desde 2025-01-01 --hasta 2026-10-17 --paso 7 --px 2048
```

**Animar.**

```powershell
.venv\Scripts\python.exe animar\armar.py --frames "D:\Users\guill\dataset era5\salidas\frames_mur_globo_2025-01-01T0000_94f_2048px" --fps 6
```

- Son ~94 cuadros (`--paso 7` de días): una muestra por semana, no la cadencia diaria.
- La serie y la etiqueta de la carpeta salen de [`comun/series.py`](./comun/series.py), así
  que la descarga y el render nunca se desincronizan.
- El render es globo Orthographic (MUR siempre es global), con el mismo vestuario del póster.

---

## 9. Flujo extra: True Color (MODIS/VIIRS, el humo de 2024)

Para ver el **humo de los incendios de 2024** hace falta color real. GeoColor (GOES-East)
**no tiene archivo 2024**: su capa devuelve un placeholder. La salida es **True Color
(Corrected Reflectance)** de MODIS/VIIRS vía NASA GIBS, que sí cubre 2024, es 250 m y es lo
que muestra el humo.

Es un producto **global** (no un disco GOES) y de **cadencia diaria** (composición del día),
así que usa su propio par descarga/render, pero pasa por las mismas cuatro etapas.

**Identificar.** En GIBS es `VIIRS_NOAA20_CorrectedReflectance_TrueColor` (default); las
alternativas son `MODIS_Terra_...` y `MODIS_Aqua_...`. Ventana: `2024-07-11` a
`2024-10-30`, un cuadro por día (**112 cuadros**).

**Descargar.**

```powershell
.venv\Scripts\python.exe descargar\truecolor.py --desde 2024-07-11 --hasta 2024-10-30 --paso 1 --px 2711
```

**Cuadros.** El comando exacto lo imprime la descarga al terminar:

```powershell
.venv\Scripts\python.exe cuadros\cuadros_truecolor.py --desde 2024-07-11 --hasta 2024-10-30 --paso 1 --px 2711
```

**Animar.**

```powershell
.venv\Scripts\python.exe animar\armar.py --frames "D:\Users\guill\dataset era5\salidas\frames_truecolor_noaa20_globo_2024-07-11T0000_112f_2711px" --fps 12.5
```

- `--paso` va en **días** (acá `1`): la cadencia de la capa ya es diaria.
- **No uses `VIIRS_SNPP_...`**: tiene un hueco de archivo (2024-07-12..15 devuelve un
  placeholder); para 2024 usá Terra o NOAA-20.
- **Por eso el default es NOAA-20**: la composición diaria de **Terra y Aqua** deja huecos de
  franja (swaths) cerca del ecuador —el barrido de MODIS es más angosto que la separación de
  órbitas—, que en el globo se ven como cuñas negras diagonales y dejan el globo rayado. Por
  eso **no se recomiendan** para el globo. **NOAA-20** (VIIRS) no los tiene y es la capa por
  defecto. Es una propiedad del producto, no del render.
- El nombre corto del sensor entra en la etiqueta (`frames_truecolor_noaa20_...`), así que dos
  sensores no se pisan la carpeta.
- La serie y la etiqueta salen de [`comun/series.py`](./comun/series.py), igual que en el
  resto del repo: la descarga y el render nunca se desincronizan.

---

## 10. Flujo extra: Sandwich RGB (convección profunda, de día)

El **Sandwich RGB** sirve para monitorear **convección profunda**: combina el **visible**
(la morfología del tope nuboso) con el **IR 10.8 µm realzado en color** (la temperatura del
tope). **No es un RGB de tres bandas**: son **dos imágenes** que se mezclan, así que su par
descarga/render baja y compone dos capas. En GOES-19 (GOES-East) son las bandas ABI **C02
(0.64 µm)** para el visible y **C13 (10.3 µm)** para el IR.

Es un producto **sólo diurno** (el visible necesita sol), así que la animación son los
**tramos diurnos** de cada jornada, no las horas corridas. Pasa por las mismas cuatro etapas.

**Identificar.** En GIBS son `GOES-East_ABI_Band2_Red_Visible_1km` y
`GOES-East_ABI_Band13_Clean_Infrared`, ambas de cadencia de 10 min. Se toma el tramo
`10`–`22` UTC de cada día (≈ `07:00`–`19:00` en Paraguay), que a `--paso 10` dan 73
cuadros por día.

**Descargar.**

```powershell
.venv\Scripts\python.exe descargar\sandwich.py --desde 2026-10-04 --hasta 2026-10-05 --hora-desde 10 --hora-hasta 22 --paso 10 --px 2048
```

**Cuadros.** El comando exacto lo imprime la descarga al terminar:

```powershell
.venv\Scripts\python.exe cuadros\cuadros_sandwich.py --desde 2026-10-04 --hasta 2026-10-05 --hora-desde 10 --hora-hasta 22 --paso 10 --px 2048
```

**Animar.**

```powershell
.venv\Scripts\python.exe animar\armar.py --frames "D:\Users\guill\dataset era5\salidas\frames_sandwich_globo_2026-10-04T1000_146f_2048px" --fps 12.5
```

- **Sólo de día**: `--hora-desde`/`--hora-hasta` recortan el tramo diurno; fuera de él el
  visible de GIBS viene negro y la mezcla no aporta nada.
- **Dos capas por cuadro**: `crudo_NNN_vis.jpg` + `crudo_NNN_ir.jpg`; el render los compone
  con `--alpha` (por defecto `0.5`, la mezcla clásica).
- **GIBS rate-limitea**: el descargador manda `User-Agent` y usa `--hilos 8` por defecto;
  sin `User-Agent` el servicio devuelve un XML de error con HTTP 200.
- **Por qué GIBS y no el `.nc` de NOAA S3**: la banda visible de ABI (C02) es de 0.5 km y
  cada archivo pesa ~200 MB; para dos días serían decenas de GB. GIBS sirve las mismas
  bandas ya rasterizadas a 1 km.
- La serie y la etiqueta salen de [`comun/series.py`](./comun/series.py) (`serie_diurna`),
  así que la descarga y el render nunca se desincronizan.

---

## 11. Notas

- **RAM**: si ves errores de memoria, bajá `--px` y/o `--lote`. El render por lotes existe
  justamente por esto.
- **MP4 vs GIF**: el MP4 pesa ~7× menos y se ve mejor; el GIF sólo conviene para animaciones
  cortas y chicas.
- **Sin internet**: `prototipos/`, `cuadros/` y `animar/` funcionan offline. La excepción es
  la **primera** vez que cartopy dibuja costas: baja shapefiles de Natural Earth y después
  quedan cacheados.
- **Datos en `D:\`**: los `.nc` y las salidas no viven en el repositorio (están ignorados por
  tamaño). Si los movés, exportá `CLIMATE3D_DATOS` en vez de editar código.
- **Anomalía de temperatura (ERA5)**: es otro flujo, con `prototipos/poster_anomalia.py`; se
  descarga con `descargar/descargar_era5.py`.
- **GeoColor**: es un producto RGB, no una banda, así que tiene su propia descarga
  (`descargar/geocolor.py`) y su propio render (`cuadros/cuadros_geocolor.py`).
- **MUR SST**: dataset global de otra familia (SST, no nubes); su flujo está en la sección 8
  (`descargar/mur_sst.py` + `cuadros/cuadros_mur.py`).
- **True Color**: el color real de MODIS/VIIRS cuando GeoColor no tiene archivo; su flujo
  está en la sección 9 (`descargar/truecolor.py` + `cuadros/cuadros_truecolor.py`).
- **Sandwich RGB**: visible + IR realzado del GOES-19 para convección profunda de día; su
  flujo está en la sección 10 (`descargar/sandwich.py` + `cuadros/cuadros_sandwich.py`).
