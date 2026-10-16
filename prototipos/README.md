# `prototipos/` — imágenes fijas y experimentos

Pósteres e imágenes sueltas: **no animan nada**. Se generan a partir de datos ya descargados,
así que funcionan sin conexión.

| Archivo | Qué produce |
|---|---|
| `poster_anomalia.py` | Póster de **anomalía mensual de temperatura** (ERA5) |
| `poster_goes.py` | Póster de **disco completo / globo / zona** (GOES-R ABI) |
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
| `--paleta` | `ir_realce`, `termico`, `anomalia`, `gris`, `magma`, `inferno`, `turbo` |
| `--globo` | Reprojecta a Orthographic |
| `--zona` | Encuadre predefinido: `py`, `br`, `sa`, `conus`, `caribe` |
| `--extent O E S N` | Caja lon/lat explícita |
| `--lat` / `--lon` / `--ancho` | Vista centrada, en grados |
| `--geojson` | Borde a destacar (por defecto, Paraguay) |
| `--vmin` / `--vmax` | Escala fija |
| `--size` / `--dpi` | Tamaño del render |

```powershell
.venv\Scripts\python.exe prototipos\poster_goes.py --paleta ir_realce
.venv\Scripts\python.exe prototipos\poster_goes.py --globo --zona sa
.venv\Scripts\python.exe prototipos\poster_goes.py --zona py --paleta anomalia
```

---

## `vista_paraguay.py`

Cuadro fijo (PNG) del globo centrado en Paraguay, con el encuadre aprobado: Orthographic
girado a `lon −73, lat −18`, paleta `ir_realce`, borde de Paraguay (GADM) y sin grilla.

```powershell
.venv\Scripts\python.exe prototipos\vista_paraguay.py
.venv\Scripts\python.exe prototipos\vista_paraguay.py --lon -70 --lat -20
```

Sin `--nc` toma el `.nc` más nuevo de `DATOS/goes_c13_g19`. Salida:
`vista_paraguay_<AAAA-MM-DDTHHMM>.png`.

---

## Detalle: ¿por qué `poster_anomalia.py` no está en `comun/`?

Porque `poster_goes.py` lo importa para reusar su vestuario, y los dos son generadores de
imágenes. Las **constantes** compartidas sí se extrajeron a
[`../comun/estilo.py`](../comun/estilo.py), así que `comun/` no depende de `prototipos/`.

## Next step

Para pasar de una imagen fija a una animación, seguí con
[`../cuadros/`](../cuadros) y después [`../animar/`](../animar).
