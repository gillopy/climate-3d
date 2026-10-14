# `notebooks/` — prototipos y animaciones

Cada notebook es autocontenido: configura, descarga lo que falte, renderiza y muestra
el resultado. Todos detectan la raíz del proyecto y agregan `lib/` al `sys.path`, así
que **se pueden correr desde esta carpeta o desde la raíz**.

| Notebook | Qué genera | Dataset |
|---|---|---|
| [`animacion_globo_g19.ipynb`](./animacion_globo_g19.ipynb) | Animación del **disco completo** + cuadro fijo | GOES-East **G19 C13** (IR 10.3 µm) |
| [`animacion_paraguay_g19.ipynb`](./animacion_paraguay_g19.ipynb) | Animación con **zoom a Paraguay** (resolución completa) | GOES-East **G19 C13** |
| [`animacion_cirrus_g18.ipynb`](./animacion_cirrus_g18.ipynb) | Animación del disco completo | GOES-West **G18 C04** (cirrus 1.4 µm) |
| [`prototipo_planeta_orthographic.ipynb`](./prototipo_planeta_orthographic.ipynb) | Prototipo ERA5: rotación 360° + time-lapse | ERA5 t2m (2.7 años) |
| [`copernicus_planet_temp.ipynb`](./copernicus_planet_temp.ipynb) | Notebook original (referencia histórica) | ERA5 t2m |

## Las tres animaciones GOES

Comparten la misma estructura de 7 celdas de código:

1. **configuración** — `T0` (primer cuadro), `N_FRAMES`, `PASO_MIN`, satélite/banda,
   paleta, crédito, escala.
2. **datos y utilidades** — arma la clave S3 sola a partir del slot de 10 min, busca
   primero en local y descarga solo lo que falta.
3. **descarga** — con barra de progreso `rich`; tolera huecos del archivo NOAA.
4. **control** — imprime y valida los rótulos con `assert` (título, subtítulo,
   fuente, datos).
5. **cuadro fijo** — PNG a tamaño completo.
6. **render** — recorre los cuadros dejando un PNG por frame en disco (poca RAM).
   Si ya hay un PNG por slot en `frames_*`, **reutiliza** los existentes y saltea el
   render: volver a correr el notebook para rearmar el GIF cuesta segundos.
7. **GIF** — arma la animación con fundido entre cuadros, leyendo de a dos por vez.

### Parámetros que se suelen tocar

| Variable | Para qué |
|---|---|
| `T0`, `N_FRAMES`, `PASO_MIN` | Ventana de tiempo (10 min por slot) |
| `SAT`, `BANDA` | `"G19"`/`"C13"` (IR), `"G18"`/`"C04"` (cirrus) |
| `PALETA` | `ir_realce`, `termico`, `anomalia`, … (ver [`lib/README.md`](../lib/README.md)) |
| `VMIN`, `VMAX` | Escala fija; `None` = percentiles automáticos del primer cuadro |
| `CENTRO_LON`, `CENTRO_LAT` | Giro del globo (solo en `animacion_globo_g19`) |
| `GEOJSON` | Borde destacado a dibujar |
| `CUADRO_MS`, `FUNDIDO_PASOS` | Velocidad: más chico = más rápido, `0` = sin fundido |
| `LADO_PULG`, `DPI` | Resolución de cada cuadro (`19.3714 × 140` = 2712 px) |
| `TOPE_PX` | Submuestreo del dato antes de dibujar (2712 → grilla de 2712 px, 1:1) |
| `HACER_GIF`, `HACER_MP4` | Qué exportar. El MP4 pesa mucho menos y se ve mejor; a 2712 px el GIF pasaría 1 GB |
| `CRF_MP4`, `PRESET_MP4` | Calidad de codificación (16 y `slow` por defecto; CRF más bajo = más calidad y peso) |
| `DESCARGAR` | `False` = usar solo archivos locales y avisar si falta alguno |

### Resolución

El dato fuente de la banda 13 es de **5424×5424** (2 km en el nadir). En la práctica:

| Etapa | Resolución |
|---|---|
| Dato crudo | 5424×5424 |
| Tras `TOPE_PX=2712` (defecto) | 2712×2712 |
| **Cuadros y MP4** | **2712×2712** |
| Versión anterior | 1176×1176 |
| Primer GIF | 720×720 |

Costo de render medido (144 cuadros), crece con los píxeles:

| Salida | Tiempo por cuadro | 144 cuadros |
|---|---|---|
| 1176 px | 4.1 s | ~10 min |
| 2000 px | 9.4 s | ~22 min |
| 2712 px | 22.7 s | ~55 min |
| 5424 px (nativo) | 89.2 s | ~3.6 h |

Subir `TOPE_PX` y `LADO_PULG`/`DPI` en la misma proporción es lo que permite llegar a la
resolución nativa, a costa de tiempo.

> **Ojo con las dimensiones impares**: x264 con `yuv420p` exige lados **pares**. Si la
> figura queda en 2711 px (impar) ffmpeg falla. La celda del MP4 lo resuelve con
> `-vf "pad=ceil(iw/2)*2:ceil(ih/2)*2"`, que agrega 1 px sin remuestrear.

### Datos y salidas

- **Entrada**: `D:\Users\guill\dataset era5\goes_c13_g19` (o `...\goes_c04_g18`).
- **Salida**: `D:\Users\guill\dataset era5\salidas` — el GIF, el PNG fijo y una
  carpeta `frames_*` con los cuadros intermedios (se puede borrar al terminar).

Nada de esto se guarda en el repositorio.

## Notas

- La cadencia real de ABI en modo 6 es de **10 minutos** y el nombre del archivo
  codifica el inicio del escaneo; el `t` del dataset es el **punto medio** del barrido
  (de ahí que un archivo que arranca 22:20 y termina 22:29 reporte 22:25 UTC).
- El disco de un geoestacionario tiene un **limbo estirado**: si se reproyecta a
  Orthographic, ese anillo se ve deformado. Se disimula girando el globo para que el
  borde feo quede fuera del encuadre.
- La salida preferida es **MP4** (`HACER_MP4`): se codifica con el ffmpeg que trae
  `imageio-ffmpeg`, así que **no hace falta tener ffmpeg en el PATH**. El GIF
  (`HACER_GIF`) queda para cuando se necesita un archivo que se reproduzca en loop en
  cualquier visor; a 1176 px pesa más de 200 MB por el dithering de la paleta de 256 colores.
