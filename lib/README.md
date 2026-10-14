# `lib/` — módulos reutilizables

Dos módulos que arman los pósteres. `poster_goes.py` **importa** de
`poster_anomalia.py` (constantes y paleta compartidas), así que deben quedar juntos
en esta carpeta.

---

## `poster_anomalia.py`

Póster de **anomalía mensual de temperatura** a partir de ERA5: globo Orthographic
llenando el cuadro, rampa divergente de −6 a +6 °C y textos del póster.

Es además el **módulo de constantes compartidas** del proyecto:

| Constante | Qué es |
|---|---|
| `BG` | Fondo del póster (`#0c1014`) |
| `TXT`, `TXT_DIM`, `WM_COLOR` | Colores de texto y marca de agua |
| `MONTHS_EN` | Nombres de meses en inglés (para los rótulos) |
| `POSTER_SIZE`, `POSTER_DPI` | Tamaño por defecto (8.4 in, 140 dpi → 1176 px) |
| `ANOM_CMAP` | Rampa divergente muestreada de la imagen de referencia |

**Cálculo de la anomalía**: temperatura media del mes elegido menos la climatología
de ese mes calculada con los **demás años** del propio archivo (excluir el año
objetivo evita diluir la anomalía consigo misma). La lectura del NetCDF es **lazy** y
por bloques (`isel`), porque sin dask la aritmética sobre todo el array materializaría
los GB en RAM.

Funciones principales: `load_field`, `month_climatology`, `mean_steps`,
`resolve_target`, `draw_poster`, `caption_lines`.

```powershell
.venv\Scripts\python.exe lib\poster_anomalia.py                 # PNG del mes por defecto
.venv\Scripts\python.exe lib\poster_anomalia.py --mes 2026-09   # otro mes
.venv\Scripts\python.exe lib\poster_anomalia.py --gif           # PNG + GIF rotando 360°
.venv\Scripts\python.exe lib\poster_anomalia.py --show          # abrir la ventana
```

Salida (en `D:\Users\guill\dataset era5\salidas`): `planeta_anomalia_<AAAA-MM>.png` y,
con `--gif`, `planeta_anomalia_rotando.gif`. Sin archivo ERA5 en `DATOS_D`, cae a
datos sintéticos para que el póster siempre se pueda generar.

---

## `poster_goes.py`

Póster de **disco completo** desde un archivo GOES-R ABI L2 CMIP. A diferencia del
póster ERA5 (grilla global lat/lon), un archivo ABI trae el disco en su **grilla
geoestacionaria**: se dibuja con `cartopy.crs.Geostationary`, así `pcolormesh` no
necesita reproyectar. Opcionalmente se reproyecta a **Orthographic** (`globe_center`)
para el aspecto "planeta" centrado donde uno quiera.

Detecta sola la variable y las unidades: reflectancia (`units "1"`) → **%**;
temperatura de brillo (`units "K"`) → **°C**.

### Paletas disponibles

| Nombre | Uso |
|---|---|
| `gris` | Reflectancia: 0 = negro (mar/espacio), 1 = blanco (nubes) |
| `termico` | IR clásico: frío (nube alta) = blanco, cálido = negro |
| `ir_realce` | IR **con realce**: color en los topes fríos, gris en el fondo |
| `anomalia` | La rampa del póster de anomalía |
| `magma`, `inferno`, `turbo` | Paletas de matplotlib para explorar |

Para `termico` el colorbar lleva **escala invertida** (frío a la izquierda); para el
resto se calcula automáticamente según el tipo de variable.

### Zonas predefinidas (`--zona`)

`py` (Paraguay), `br` (Brasil), `sa` (Sudamérica), `conus` (EE.UU.), `caribe`.

### API

```python
from poster_goes import PALETTES, draw_goes_poster, caption_lines, to_display

campo, unidad, tipo = to_display(crudo, cmi)          # K→°C o →%
titulo, subtitulo, fuente, datos = caption_lines(ds, cmi, tipo, "FULL DISK")
draw_goes_poster(
    campo, x=x, y=y, proj=proj, title=titulo, subtitle=subtitulo,
    unit_label=unidad, src_line=fuente, data_line=datos,
    cmap=PALETTES["ir_realce"], vmin=-65, vmax=25,
    globe_center=(-73.0, -18.0),        # Orthographic girado
    highlight_geojson="datos/paraguay_gadm.json",   # borde destacado
)
```

Parámetros útiles de `draw_goes_poster`: `globe_center`, `highlight_geojson`,
`highlight_color`, `highlight_width`, `grid`, `xlim`/`ylim`, `size`/`dpi`.

### CLI

```powershell
.venv\Scripts\python.exe lib\poster_goes.py                          # disco completo, gris
.venv\Scripts\python.exe lib\poster_goes.py --paleta ir_realce
.venv\Scripts\python.exe lib\poster_goes.py --globo --zona sa       # globo, Sudamérica
.venv\Scripts\python.exe lib\poster_goes.py --zona py               # encuadre regional
.venv\Scripts\python.exe lib\poster_goes.py --lat -25.3 --lon -57.6 --ancho 20
.venv\Scripts\python.exe lib\poster_goes.py --nc OR_ABI-...nc --out salida.png
```

**Ojo**: un archivo de GOES-West (G18, satélite en −137°) apenas alcanza Paraguay,
que cae al borde del disco. Para Paraguay y Sudamérica conviene **GOES-East**
(G16/G19, satélite en −75.2°).

### Entrada y salida

- **Entrada**: el `.nc` de `--nc`, o el **más reciente** que encuentre bajo
  `D:\Users\guill\dataset era5` (busca recursivamente en `goes_c13_g19`,
  `goes_c04_g18`, etc.).
- **Salida**: `D:\Users\guill\dataset era5\salidas\poster_goes_<PLATAFORMA>_C<banda>.png`,
  o lo que diga `--out`. Nada se escribe dentro del repositorio.
