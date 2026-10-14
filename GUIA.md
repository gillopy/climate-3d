# Guía: descargar datasets GOES y animarlos

Esta guía te deja hacer el flujo completo **sin depender de nadie**: bajar un dataset
satelital de NOAA y convertirlo en una animación.

El flujo es siempre el mismo:

```
descargar el dataset  ->  renderizar los cuadros  ->  armar el MP4
   (scripts/descargar_goes.py)   (scripts/render_anim.py)   (automático)
```

> Todo va a `D:\Users\guill\dataset era5`. Los `.nc` (varios GB) y las salidas
> (PNG/MP4) **nunca** van dentro del repositorio.

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

`scripts/descargar_goes.py` baja los `.nc` desde el bucket público de NOAA S3 y
**saltea los que ya tenés**.

```powershell
# GOES-East C13 (infrarrojo) del 2 al 5 de octubre de 2026 (≈ 432 cuadros, ~10 GB)
.venv\Scripts\python.exe scripts\descargar_goes.py --sat G19 --banda C13 --desde 2026-10-02 --hasta 2026-10-05

# Otro rango
.venv\Scripts\python.exe scripts\descargar_goes.py --sat G18 --banda C04 --desde 2026-10-03 --hasta 2026-10-05

# Ver la ayuda (NO toca la red)
.venv\Scripts\python.exe scripts\descargar_goes.py --help
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

## 3. Animar

Tenés dos caminos. Usá el que te convenga según cuántos cuadros quieras.

### Opción A — Notebook (para experimentar o pocos cuadros)

Abrí el notebook que corresponda en `notebooks/`, ajustá la **celda de configuración** y
corré las celdas:

| Notebook | Qué hace |
|---|---|
| `animacion_globo_g19.ipynb` | **Globo centrado en Paraguay** (Orthographic + borde), todo el disco submuestreado |
| `animacion_paraguay_g19.ipynb` | Zoom regional a Paraguay a resolución completa |
| `animacion_cirrus_g18.ipynb` | Disco completo (sin globo) en otras bandas |

Parámetros que se tocan: `SAT`, `BANDA`, `PALETA`, `T0`, `N_FRAMES`, `LADO_PULG`/`DPI`,
`TOPE_PX`, `HACER_GIF`/`HACER_MP4`.

### Opción B — Script por lotes (para ventanas largas, poca RAM)

Con **cientos de cuadros**, un notebook que renderiza todo en un proceso **agota la
memoria** de una máquina chica. `scripts/render_anim.py` resuelve eso: renderiza por
**lotes en procesos separados** y arma el MP4 solo.

```powershell
# Globo centrado en Paraguay, 432 cuadros a 720 px (el caso de la guía)
.venv\Scripts\python.exe scripts\render_anim.py --sat G19 --banda C13 --desde 2026-10-02 --n 432 --px 720 --globo --centro -73 -18 --geojson datos\paraguay_gadm.json --paleta ir_realce

# Disco completo (sin --globo)
.venv\Scripts\python.exe scripts\render_anim.py --sat G18 --banda C04 --desde 2026-10-03 --n 144 --px 1200 --paleta anomalia

# Prueba rápida antes de largar en serio
.venv\Scripts\python.exe scripts\render_anim.py --sat G19 --banda C13 --desde 2026-10-02 --n 4 --px 480 --globo
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
| `--fps` | Velocidad del MP4 (por defecto 12.5) |

- Los cuadros se guardan como PNG y **se reutilizan** si ya están: si sólo querés
  rearmar el MP4, volvé a correr el mismo comando y salta el render.
- Si el render se corta, volvé a correrlo: completa lo que falta.

---

## 4. Dónde quedan las salidas

En `D:\Users\guill\dataset era5\salidas`:

| Archivo | Qué es |
|---|---|
| `animacion_<vista>_<SAT>_<AAAA-MM-DDTHHMM>_<N>f_<PX>px.mp4` | La animación |
| `frames_<SAT>_<AAAA-MM-DDTHHMM>_<N>f_<PX>px\` | Los cuadros PNG (podés borrarlos al terminar) |
| `poster_*.png` | Cuadros fijos |

El nombre incluye **inicio + cantidad de cuadros + px**, así que una corrida **no pisa**
la de otra ventana o resolución.

---

## 5. Chuleta

```powershell
# 1) Descargar (GOES-East C13, 3 días)
.venv\Scripts\python.exe scripts\descargar_goes.py --sat G19 --banda C13 --desde 2026-10-02 --hasta 2026-10-05

# 2) Animar (globo Paraguay, 432 cuadros, 720 px)
.venv\Scripts\python.exe scripts\render_anim.py --sat G19 --banda C13 --desde 2026-10-02 --n 432 --px 720 --globo --centro -73 -18 --geojson datos\paraguay_gadm.json --paleta ir_realce
```

---

## 6. Notas

- **RAM**: si ves errores de memoria, bajá `--px` y/o `--lote`, o subí `N_FRAMES` en
  pasos. El render por lotes existe justamente por esto.
- **MP4 vs GIF**: el MP4 pesa ~7× menos y se ve mejor; el GIF sólo conviene para
  animaciones cortas y chicas.
- **Datos en `D:\`**: los `.nc` y las salidas no viven en el repositorio (están
  ignorados por tamaño).
- **Anomalía de temperatura (ERA5)**: es otro flujo, con `lib/poster_anomalia.py`;
  se descarga con `scripts/descargar_era5.py`.
