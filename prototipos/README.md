# `prototipos/` — imágenes fijas y experimentos

Pósteres e imágenes sueltas: **no animan nada**. Se generan a partir de datos ya descargados,
así que funcionan sin conexión.

| Archivo | Qué produce |
|---|---|
| `poster_anomalia.py` | Póster de **anomalía mensual de temperatura** (ERA5) |
| `poster_goes.py` | Póster de **disco completo / globo / zona** (GOES-R ABI) |
| `poster_goes_realista.py` | Póster **realista** de GOES-19 C13 (globo blanco, tarjeta de leyenda) |
| `poster_goes_truecolor.py` | Póster de **color real** de GOES-19 (C01 + C02 + C03) |
| `poster_goes_disco.py` | El mismo color real, en la **grilla nativa** del satélite |
| `poster_mur_realista.py` | Póster **realista** de la anomalía de SST de MUR |
| `animar_mur_realista.py` | Serie de cuadros del póster MUR con la leyenda viva |
| `poster_pace.py` | Póster de **color real de PACE/OCI** desde un L3M SFREFL |
| `poster_pace_gibs.py` | Póster de **color real de PACE/OCI** desde el compuesto de GIBS |
| `poster_follaje.py` | Póster global de **follaje de otoño** (PACE/OCI LANDVI) |
| `vista_paraguay.py` | **Cuadro fijo** del globo centrado en Paraguay |
| `notebooks/` | Los prototipos originales: ver [`notebooks/README.md`](./notebooks/README.md) |

---

## `poster_anomalia.py`

Anomalía mensual a partir de ERA5: globo Orthographic llenando el cuadro, rampa divergente de
−6 a +6 °C y los textos del póster.

**Cálculo**: temperatura media del mes elegido menos la climatología de ese mes calculada con
los **demás años** del propio archivo (excluir el año objetivo evita diluir la anomalía
consigo misma). La lectura del NetCDF es *lazy* y por bloques (`isel`), porque sin dask la
aritmética sobre todo el array materializaría los GB en RAM.

| Opción | Qué hace |
|---|---|
| `--nc` | Archivo ERA5 explícito |
| `--mes` | Mes a mostrar (`2026-09`) |
| `--credito` | Crédito y marca de agua |
| `--gif` | Además del PNG, un GIF rotando 360° |
| `--show` | Abre la ventana al final |

Sin archivo ERA5 disponible cae a **datos sintéticos**, para que el póster siempre se pueda
generar. Salida: `planeta_anomalia_<AAAA-MM>.png`.

---

## `poster_goes.py`

Póster desde un archivo GOES-R ABI L2 CMIP. Un archivo ABI trae el disco en su **grilla
geoestacionaria**, así que se dibuja con `cartopy.crs.Geostationary` y `pcolormesh` no
reproyecta. Con `--globo` pasa a **Orthographic**, para el aspecto "planeta" centrado donde
quieras.

Detecta sola la variable y las unidades: reflectancia (`units "1"`) → **%**; temperatura de
brillo (`units "K"`) → **°C**.

| Opción | Qué hace |
|---|---|
| `--paleta` | `clean_ir`, `termico`, `anomalia`, `gris`, `magma`, `inferno`, `turbo` |
| `--globo` | Reprojecta a Orthographic |
| `--zona` | Encuadre predefinido: `py`, `br`, `sa`, `conus`, `caribe` |
| `--extent O E S N` | Caja lon/lat explícita |
| `--lat` / `--lon` / `--ancho` | Vista centrada, en grados |
| `--geojson` | Borde a destacar (por defecto, Paraguay) |
| `--vmin` / `--vmax` | Escala fija |
| `--size` / `--dpi` | Tamaño del render |

```powershell
.venv\Scripts\python.exe prototipos\poster_goes.py --paleta clean_ir
.venv\Scripts\python.exe prototipos\poster_goes.py --globo --zona sa
.venv\Scripts\python.exe prototipos\poster_goes.py --zona py --paleta anomalia
```

---

## `vista_paraguay.py`

Cuadro fijo (PNG) del globo centrado en Paraguay, con el encuadre aprobado: Orthographic
girado a `lon −73, lat −18`, paleta `clean_ir`, borde de Paraguay (GADM) y sin grilla.

```powershell
.venv\Scripts\python.exe prototipos\vista_paraguay.py
.venv\Scripts\python.exe prototipos\vista_paraguay.py --lon -70 --lat -20
```

Sin `--nc` toma el `.nc` más nuevo de `DATOS/goes_c13_g19`. Salida:
`vista_paraguay_<AAAA-MM-DDTHHMM>.png`.

---

## `poster_follaje.py`

Mapa global del **follaje de otoño** con los índices de vegetación de **PACE/OCI (LANDVI)**,
en el lenguaje visual del mapa de NASA Earth Observatory *"Hunting Red Leaves with
Satellites"*: fondo blanco, océano celeste, continentes en gris crema y la vegetación
coloreada de verde a rojo.

**Qué se dibuja**: `rojez = mari ÷ cire`, es decir **antocianina sobre clorofila**. `mari`
(Modified Anthocyanin Reflectance Index) responde a las antocianinas y `cire` (Chlorophyll
Index Red Edge) al contenido de clorofila de la copa. El cociente da ~1 en vegetación verde
sin cambio y sube por encima de 2 donde el rojo domina: es la misma semántica —y la misma
escala `1.00–3.00`— de la leyenda oficial de GLOBE. Verificado con la semana 2026-09-29 →
10-04: **mediana global 1.16**, Amazonas 0.35, Siberia y Canadá boreal 1.4–2.2.

Máscaras: `ndvi > 0.25`, `cire > 0.2` y descarte de los `_FillValue`; el L3M ya viene sin
nubes. El compuesto semanal **promedia los índices y recién después divide** (promediar
cocientes diarios deja mucho más ruido y más huecos).

| Opción | Qué hace |
|---|---|
| `--desde` / `--hasta` | Ventana del compuesto (por defecto, `2026-09-29` a `2026-10-04`) |
| `--dia` | Un solo día, sin compuesto |
| `--doble` | Dos paneles: la ventana y la semana siguiente |
| `--desde2` / `--hasta2` | Overrides del segundo panel |
| `--px` | Ancho del póster (por defecto `2712`) |
| `--rehacer` | Ignora el compuesto cacheado en `SALIDAS/follaje_pace/` |

```powershell
.venv\Scripts\python.exe prototipos\poster_follaje.py
.venv\Scripts\python.exe prototipos\poster_follaje.py --doble
.venv\Scripts\python.exe prototipos\poster_follaje.py --dia 2026-10-04
```

- Proyección **Robinson** (cartopy no trae Winkel Tripel, que es la de la referencia; a este
  tamaño la diferencia no se nota).
- **RAM**: deformar la grilla nativa entera pide ~1.5 GB porque `warp_array` materializa
  matrices temporales; el render submuestrea por 3 (1440×2880) antes del warp.
- `imshow` con `transform=PlateCarree` necesita **`pykdtree`** (o `scipy`): sin eso cartopy
  corta con `ImportError`.
- Salidas: `poster_follaje_pace_<desde>_<hasta>_<px>px.png` y, con `--doble`,
  `poster_follaje_pace_doble_<desde>_<hasta2>_<px>px.png`.

---

## `poster_goes_realista.py`

Globo Orthographic de la **banda 13 de GOES-19** con el diseño aprobado del póster MUR:
fondo blanco, disco inscripto, sombra exterior difusa, limbo sombreado, retícula tenue y
tarjeta de leyenda con la distribución. No toca el pipeline viejo (`poster_goes.py`,
`cuadros_goes.py`).

| Opción | Qué hace |
|---|---|
| `--nc` / `--datos` | Archivo ABI L2 CMIP o carpeta (por defecto, el más reciente) |
| `--px` / `--dpi` / `--tope` | Diámetro del globo (2400), dpi y resolución del campo (2712) |
| `--centro LON LAT` / `--recorte` | Centro (por defecto `-71 -10`) y fracción del radio visible |
| `--paleta` | `clean_ir` (Worldview) |
| `--vmin` / `--vmax` / `--porcentiles` | Escala física de la rampa o percentiles 0.5/99.5 |
| `--sombra-borde` | Profundidad del borde 0..0.8 (0 deja el limbo del diseño MUR) |
| `--borde` / `--fronteras` | Contorno destacado (Paraguay por defecto) y límites punteados |
| `--out` / `--frames` / `--n` / `--paso` / `--forzar` | PNG suelto o serie numerada |

La escala por defecto es la **física** (`-92.1` a `56.9 °C`), no percentiles: los cuadros de
la animación no cambian de color entre sí. `--recorte` se deduce del centro para que el borde
del disco caiga dentro de la zona con dato.

---

## `poster_goes_truecolor.py`

El color real del GOES-19 exige **tres bandas** (`C01` 0.47 µm, `C02` 0.64 µm, `C03`
0.86 µm): el ABI no tiene verde y se sintetiza con `0.45·rojo + 0.10·veggie + 0.45·azul`.
Usa el vestuario de `poster_goes_realista.py` y las bandas que baja
[`../descargar/truecolor_goes.py`](../descargar/truecolor_goes.py).

```powershell
.venv\Scripts\python.exe prototipos\poster_goes_truecolor.py --desde 2026-10-24T16:40 --px 2400
.venv\Scripts\python.exe prototipos\poster_goes_truecolor.py --frames "D:\...\frames_G19_truecolor" --n 24
```

- `--px` por defecto es 8360: la resolución nativa de 1 km.
- `--saturacion`, `--gamma`, `--pedestal`, `--pct-lo`/`--pct-hi`, `--mu-*` y `--suavizado`
  son los pasos del pipeline de color; los defaults son los aprobados.
- Si pedís un slot que no existe en las tres bandas, elige el **primer slot completo**
  a partir de `--desde`.

---

## `poster_goes_disco.py`

El mismo color real, **sin reproyectar**: usa la grilla de escaneo del ABI tal cual. El
encuadre es el que le da el satélite (limbo a ~81° del subpunto) y las deformaciones reales
de la perspectiva geoestacionaria.

```powershell
.venv\Scripts\python.exe prototipos\poster_goes_disco.py --desde 2026-10-24T16:40 --px 5424
```

- `--limbo` compensa el camino atmosférico en el borde (0 = sin compensar).
- Costas, retícula y fronteras vienen **apagadas** por defecto: sólo queda el contorno de
  Paraguay. Se prenden con `--costas`, `--reticula` y `--fronteras`.

---

## `poster_mur_realista.py` y `animar_mur_realista.py`

Póster realista de la **anomalía de SST de MUR** desde un `crudo_NNN.jpg` de GIBS: globo
Orthographic sobre fondo blanco, continentes en gris con relieve (Blue Marble + Natural
Earth), rampa divergente azul-blanco-rojo, retícula y barra al pie.

```powershell
.venv\Scripts\python.exe prototipos\poster_mur_realista.py --px 2711 --centro -125 0
.venv\Scripts\python.exe prototipos\poster_mur_realista.py --crudo "...\crudo_001.jpg"
.venv\Scripts\python.exe prototipos\animar_mur_realista.py --px 1200 --armar
```

- `poster_mur_realista.py` busca el primer `crudo_001.jpg` de las series
  `frames_mur_globo_*`; `--crudo` fuerza otro. `--trend` agrega media y p90/p95.
- `animar_mur_realista.py` recorre la serie semanal, recalcula media, desvío e histograma
  **cuadro a cuadro** y actualiza la tarjeta. `--limite` renderiza sólo los primeros N.
- La base de relieve y la leyenda de GIBS se cachean en `SALIDAS/_poster_realista/`.

---

## `poster_pace.py` y `poster_pace_gibs.py`

Dos caminos al **color real de PACE/OCI**:

- `poster_pace.py` lee un L3M **SFREFL** (`rhos`) en NetCDF. OCI **sí tiene verde real**
  (555 nm), así que el RGB es (670, 555, 443) medido, sin síntesis. SFREFL es reflectancia
  de superficie: las nubes vienen enmascaradas. **No hay descargador**: ese `.nc` se baja a
  mano desde OB.DAAC.
- `poster_pace_gibs.py` baja el compuesto **OCI_PACE_True_Color** de NASA GIBS (teselas WMTS
  EPSG:4326, `--nivel 4` = 10240×5120). Trae nubes, aerosoles y sombras, y no necesita cuenta.

```powershell
.venv\Scripts\python.exe prototipos\poster_pace.py --nc "...\PACE_OCI.<fecha>.L3m.DAY.SFREFL.<res>.nc"
.venv\Scripts\python.exe prototipos\poster_pace_gibs.py --hasta 2026-10-24 --dias 8 --px 3000
```

PACE es polar: un día suelto deja huecos. `--dias` rellena por prioridad temporal (el primer
píxel con dato gana). Los `NaN` se leen como zonas sin dato, no como error de render.

---

## Detalle: ¿por qué `poster_anomalia.py` no está en `comun/`?

Porque `poster_goes.py` lo importa para reusar su vestuario, y los dos son generadores de
imágenes. Las **constantes** compartidas sí se extrajeron a
[`../comun/estilo.py`](../comun/estilo.py), así que `comun/` no depende de `prototipos/`.

## Next step

Para pasar de una imagen fija a una animación, seguí con
[`../cuadros/`](../cuadros) y después [`../animar/`](../animar).
