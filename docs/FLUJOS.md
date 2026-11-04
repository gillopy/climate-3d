# Flujos: qué hay, cómo se corre y cómo se replica

Este documento es el **catálogo de flujos** del repo. Para cada producto dice:
de dónde sale el dato, qué script lo baja, qué script lo dibuja, cómo se anima y
qué archivos deja. Es la referencia para repetir un resultado sin adivinar
comandos.

> La guía paso a paso de las cuatro etapas está en [`../GUIA.md`](../GUIA.md). Este
> archivo es el mapa completo: todos los flujos que existen hoy, incluidos los que
> no están en la guía.

---

## Cómo está armado

| Etapa | Carpeta | Qué hace | ¿Red? |
| --- | --- | --- | --- |
| 1 | `descargar/` | Baja el dataset | **Sí** |
| 2 | `prototipos/` | Imagen fija / póster | No |
| 3 | `cuadros/` | Render cuadro por cuadro | No |
| 4 | `animar/` | Junta los cuadros en MP4/GIF | No |

`comun/` guarda lo compartido (rutas, estilo, lectura de GOES, paleta GIBS,
follaje y globo 3D). No descarga nada.

**La regla del repo**: cada producto tiene su par `descarga + render`. Nada se
pisa entre productos porque el nombre de salida incluye modelo, sensor,
ventana y resolución.

---

## Requisitos

```powershell
.venv\Scripts\python.exe -c "import cartopy, matplotlib, requests, PIL, eccodes, h5py; print('ok')"
```

- Python 3.14 y el `.venv` de la raíz; dependencias en [`../requirements.txt`](../requirements.txt).
- `eccodes` para los GRIB2 de ECMWF; `h5py` para el NetCDF de ERA5; `pykdtree`
  para el `imshow(transform=...)` de cartopy en los mapas planos.
- `cdsapi` **sólo** para `descargar/descargar_era5.py` (no está instalado por
  defecto: el flujo de anomalía mensual ya tiene el `.nc` bajado).

### Dónde viven los datos

La raíz la define un solo archivo, [`../comun/rutas.py`](../comun/rutas.py), y se
cambia sin tocar código:

```powershell
$env:CLIMATE3D_DATOS = "D:\mi\carpeta\datos"
```

Por defecto apunta a `D:\Users\guill\dataset era5`. Ahí viven los `.nc`/`.npz`
de entrada y `salidas/` con los PNG, frames y videos.

---

## Tabla maestra

| Flujo | Descarga | Imagen fija | Cuadros | Salida típica |
| --- | --- | --- | --- | --- |
| GOES ABI C13 (disco/globo) | `descargar_goes.py` | `poster_goes.py` | `cuadros_goes.py` | `poster_goes_*`, `frames_G19_*` |
| GOES C13 con diseño nuevo | — | `poster_goes_realista.py` | el mismo `--frames` | `frames_G19_C13_realista_*` |
| GOES C13 formato ECMWF | — | `cuadros_c13_ir.py --solo-poster` | `cuadros_c13_ir.py` | `frames_G19_C13_*` |
| GOES color real (3 bandas) | `truecolor_goes.py` | `poster_goes_truecolor.py` | el mismo `--frames` | `frames_G19_truecolor` |
| GOES color real nativo | `truecolor_goes.py` | `poster_goes_disco.py` | — | `poster_G19_truecolor_nativo_*` |
| GeoColor | `geocolor.py` | — | `cuadros_geocolor.py` | `frames_geocolor_*` |
| Sandwich RGB | `sandwich.py` | — | `cuadros_sandwich.py` | `frames_sandwich_*` |
| Dust / Air Mass / Fire RGB | `descargar_goes_rgb.py` | `poster_goes_rgb.py` | el mismo `--frames` | `poster_G19_<producto>_*` |
| Himawari-9 AHI B13 | `descargar_himawari.py` | `cuadros_himawari_ir.py --solo-poster` | `cuadros_himawari_ir.py` | `frames_H09_B13_*` |
| MUR SST | `mur_sst.py` | `poster_mur_realista.py` | `cuadros_mur.py`, `animar_mur_realista.py` | `frames_mur_globo_*` |
| True Color GIBS | `truecolor.py` | — | `cuadros_truecolor.py` | `frames_truecolor_*` |
| PACE LANDVI (follaje) | `pace_landvi.py` | `poster_follaje.py` | `cuadros_follaje.py`, `cuadros_follaje_globo.py` | `frames_follaje_*` |
| PACE color real | manual (SFREFL) / `poster_pace_gibs.py` | `poster_pace.py`, `poster_pace_gibs.py` | — | `poster_PACE_*` |
| ECMWF precipitación | `precipitacion_ecmwf.py` | `cuadros_precipitacion.py --solo-poster` | `cuadros_precipitacion.py` | `frames_precipitacion_*` |
| ECMWF anomalía 2 m | `anomalia_2t_ecmwf.py` | `cuadros_anomalia_2t.py --solo-poster` | `cuadros_anomalia_2t.py` | `frames_anomalia_2t_*` |
| ECMWF viento 250 mb | `viento_250_mslp.py` | `cuadros_viento_250.py --solo-poster` | `cuadros_viento_250.py` | `frames_viento_250_*` |
| ERA5 anomalía mensual | `descargar_era5.py` | `poster_anomalia.py` | — | `planeta_anomalia_<mes>.png` |

---

## Flujos satelitales GOES

### 1. ABI C13: disco, globo o zona

El infrarrojo limpio (10.3 µm) del GOES-East. Es el flujo base del repo.

```powershell
# 1) Bajar 3 días de C13 (~10 GB, reanudable)
.venv\Scripts\python.exe descargar\descargar_goes.py --sat G19 --banda C13 --desde 2026-10-02 --hasta 2026-10-05

# 2) Un cuadro fijo para revisar
.venv\Scripts\python.exe prototipos\poster_goes.py --paleta clean_ir

# 3) La animación (globo centrado en Paraguay)
.venv\Scripts\python.exe cuadros\cuadros_goes.py --sat G19 --banda C13 --desde 2026-10-02 `
    --n 432 --px 720 --globo --centro -73 -18 --paleta clean_ir

# 4) El MP4
.venv\Scripts\python.exe animar\armar.py --frames "D:\Users\guill\dataset era5\salidas\frames_G19_2026-10-02T0000_432f_720px" --fps 12.5
```

- `--tope` en `cuadros_goes.py` baja la resolución del **campo leído** (no del
  lienzo): sirve para ahorrar RAM y tiempo cuando el `--px` final es grande.
- La escala sale del primer cuadro (percentiles). Para que no salte entre
  corridas, fijala con `--vmin`/`--vmax`.
- Los slots son cada 10 min y la hora sale del nombre del archivo. Un archivo que
  arranca 04:40 se rotula 04:45 (el `t` del producto cae unos minutos después).

### 2. C13 con el diseño "realista"

El mismo dato, con el vestuario del póster MUR: fondo blanco, globo inscripto,
sombra exterior, tarjeta de leyenda y rampa `clean_ir` de NASA Worldview.

```powershell
# Póster
.venv\Scripts\python.exe prototipos\poster_goes_realista.py --px 2400 --out D:\...\poster_G19_C13_realista.png

# Serie numerada para animar
.venv\Scripts\python.exe prototipos\poster_goes_realista.py --frames "D:\...\frames_G19_C13_realista" --n 144
```

- La escala por defecto es la **física de la rampa** (`-92.1` a `56.9 °C`), no
  percentiles: los cuadros de una animación no cambian de color entre sí.
- `--recorte` se deduce del `--centro` para que el borde del disco caiga dentro
  de la zona con dato y no se vea la escalera del limbo.

### 3. C13 en el formato de los productos ECMWF

`cuadros_c13_ir.py` deja el globo recortado a un círculo, con barra sobre
pastilla oscura, halo en los textos y marca de agua al medio.

```powershell
# Póster del último cuadro de la serie
.venv\Scripts\python.exe cuadros\cuadros_c13_ir.py --solo-poster --desde 2026-10-23T19:40 --px 2712

# Serie completa
.venv\Scripts\python.exe cuadros\cuadros_c13_ir.py --desde 2026-10-19T00:00 --n 388 --px 2712
```

- Renderiza **por lotes en procesos separados** (`--lote`): la RAM de un cuadro
  no se acumula con el siguiente.
- Los PNG existentes se saltan salvo `--forzar`.

### 4. Color real de GOES: tres bandas y dos encuadres

El ABI no tiene banda verde. El color real se compone con `C01` (0.47 µm, azul),
`C02` (0.64 µm, rojo) y `C03` (0.86 µm, "veggie"), sintetizando el verde con la
receta de CIMSS.

```powershell
# Bajar las tres bandas de un slot (C02 pesa ~410 MB)
.venv\Scripts\python.exe descargar\truecolor_goes.py --desde 2026-10-24T16:40 --n 1

# Globo Orthographic
.venv\Scripts\python.exe prototipos\poster_goes_truecolor.py --desde 2026-10-24T16:40 --px 2400

# Mismo slot, sin reproyectar: la grilla nativa del satélite
.venv\Scripts\python.exe prototipos\poster_goes_disco.py --desde 2026-10-24T16:40 --px 5424
```

- `poster_goes_truecolor.py` usa el **mismo** `--frames` que el realista para
  armar una serie (`--n 24`, `--paso 10`).
- `poster_goes_disco.py` no rota ni reproyecta: usa la perspectiva
  geoestacionaria real (limbo a ~81°). Es el encuadre del disco completo.
- Si pedís un slot que no existe en las tres bandas, ambos eligen el **primer
  slot completo disponible** a partir de `--desde`.

### 5. GeoColor: día, noche y luces de ciudad

Producto RGB ya mezclado de NASA GIBS. De día se ve color real; de noche, IR más
luces de ciudad.

```powershell
.venv\Scripts\python.exe descargar\geocolor.py --globo --desde 2026-10-15T20:00 --n 24 --px 600
.venv\Scripts\python.exe cuadros\cuadros_geocolor.py --globo --desde 2026-10-15T20:00 --n 24 --px 600
.venv\Scripts\python.exe animar\armar.py --frames "D:\...\frames_geocolor_globo_2026-10-15T2000_24f_600px" --fps 8
```

- El warp a Orthographic va **por franjas de filas**: a 2712 px el pico de memoria
  baja de ~1.5 GB a ~250 MB. Es el mismo resultado, pixel a pixel.
- `--vista`/`--globo` define el encuadre y el nombre de la carpeta (`plano` vs
  `globo`), así que una corrida no pisa la otra.

### 6. Sandwich RGB: visible + IR realzado

Dos capas por cuadro: `crudo_NNN_vis.jpg` + `crudo_NNN_ir.jpg`. El color dice la
temperatura del tope; el gris del visible, su forma.

```powershell
.venv\Scripts\python.exe descargar\sandwich.py --desde 2026-10-04 --hasta 2026-10-05 --hora-desde 10 --hora-hasta 22 --paso 10 --px 2048
.venv\Scripts\python.exe cuadros\cuadros_sandwich.py --desde 2026-10-04 --hasta 2026-10-05 --hora-desde 10 --hora-hasta 22 --paso 10 --px 2048
```

- **Sólo de día**: fuera del tramo diurno el visible de GIBS viene negro.
- `--alpha` (0.5 por defecto) es la mezcla clásica.
- GIBS rate-limitea: el descargador manda `User-Agent` y usa `--hilos 8`.

### 6b. Dust, Air Mass y Fire Temperature: los RGB oficiales

Tres canales por producto, con los rangos y gammas del quick guide de NOAA. **No hay
paleta aparte**: la receta ES el color.

| Producto | R | G | B |
| --- | --- | --- | --- |
| Dust | C15−C13 (−6.7…2.6 K) | C14−C11 (−0.5…20 K, γ2.5) | C13 (−11.95…15.55 °C) |
| Air Mass | C08−C10 (−26.2…0.6 K) | C12−C13 (−43.2…6.7 K) | C08 invertida (−64.65…−29.25 °C) |
| Fire Temperature | C07 (0…60 °C, γ0.4) | C06 (0…100 %) | C05 (0…75 %) |

```powershell
.venv\Scripts\python.exe descargar\descargar_goes_rgb.py --producto dust --ultimos 10
.venv\Scripts\python.exe prototipos\poster_goes_rgb.py --producto dust --ultimos 1 --px 1400
```

- Las tres recetas están en [`comun/rgb_goes.py`](../comun/rgb_goes.py).
- Fire Temperature usa el visible/near-IR: de día se ven las nubes, de noche vienen negras.
- `--ultimos` sólo elige slots donde están **todas** las bandas; si falta una, no renderiza.

## Himawari-9 (AHI)

### 7. Banda 13 (IR 10.4 µm)

El gemelo asiático de la serie GOES, pero el dato viene en **HSD** (binario de
JMA): el descargador también lo decodifica y lo deja como `.npz` por slot.

```powershell
.venv\Scripts\python.exe descargar\descargar_himawari.py --desde 2026-10-20T04:00 --hasta 2026-10-22T04:00
.venv\Scripts\python.exe cuadros\cuadros_himawari_ir.py --desde 2026-10-20T04:00 --n 288 --px 2712
```

- Disco guardado a **4 km** (promedio 2×2 de los 2 km nativos): ~21 MB por slot.
- Rótulos en **hora de Paraguay**.
- Rampa y escala fijas de GIBS (`-92.1` a `56.9 °C`).
- Hay slots que no están en el bucket (404): se cuentan como error y la serie
  puede quedar con huecos.

## Productos globales de SST y vegetación

### 8. MUR SST: anomalía semanal en globo

```powershell
# Crudos semanales (94 muestras para dos años)
.venv\Scripts\python.exe descargar\mur_sst.py --desde 2025-01-01 --hasta 2026-10-17 --paso 7 --px 2048

# Animación clásica
.venv\Scripts\python.exe cuadros\cuadros_mur.py --desde 2025-01-01 --hasta 2026-10-17 --paso 7 --px 2048

# Póster realista con campana de distribución
.venv\Scripts\python.exe prototipos\poster_mur_realista.py --px 2711 --centro -125 0

# Animación del póster realista (la leyenda se actualiza cuadro a cuadro)
.venv\Scripts\python.exe prototipos\animar_mur_realista.py --px 1200
```

- `poster_mur_realista.py` lee el primer `crudo_001.jpg` de la serie
  `frames_mur_globo_*`; `--crudo` fuerza otro.
- `animar_mur_realista.py` recorre toda la serie semanal y recalcula media,
  desvío e histograma por cuadro. Con `--armar` arma el MP4 al final.

### 9. True Color de GIBS: el humo de 2024

```powershell
.venv\Scripts\python.exe descargar\truecolor.py --desde 2024-07-11 --hasta 2024-10-30 --paso 1 --px 2711
.venv\Scripts\python.exe cuadros\cuadros_truecolor.py --desde 2024-07-11 --hasta 2024-10-30 --paso 1 --px 2711
```

- Usá **NOAA-20 (VIIRS)**: Terra y Aqua dejan cuñas negras de barrido en el
  ecuador. `VIIRS_SNPP_...` tiene un hueco de archivo en julio de 2024.
- `--paso` va en **días**.

### 10. PACE LANDVI: el follaje de otoño

Es la única rama que **exige Earthdata Login**. El índice es
`rojez = mari ÷ cire` (antocianina sobre clorofila), escala 1.00–3.00.

```powershell
# 1) Gránulos diarios (necesita --cookies o ~/.netrc)
.venv\Scripts\python.exe descargar\pace_landvi.py --desde 2026-09-29 --hasta 2026-10-04 --res 0p1deg

# 2) Póster (una semana, o dos con --doble)
.venv\Scripts\python.exe prototipos\poster_follaje.py --res 0p1deg --px 2712
.venv\Scripts\python.exe prototipos\poster_follaje.py --doble --res 0p1deg

# 3) Animación plana (compuesto móvil de 7 días)
.venv\Scripts\python.exe cuadros\cuadros_follaje.py --desde 2026-08-07 --hasta 2026-10-11 --res 0p1deg

# 4) Animación en globo realista que rota
.venv\Scripts\python.exe cuadros\cuadros_follaje_globo.py --res 0p1deg
```

- Sin autenticación, `pace_landvi.py` corta con un mensaje explícito y **no**
  guarda credenciales.
- `--res 0p1deg` (34 MB/día) alcanza para 1920 px; `4km` (170 MB/día) es el
  insumo nativo del póster.
- El globo usa la base de relieve de `comun/globo3d.py` (cacheada en
  `salidas/_globo3d/`), modula el color por luminancia y agrega sombreado de
  esfera. `--giro 0` lo deja fijo; `--max-cuadros` permite renderizar por tandas.

### 11. PACE color real: dos caminos

```powershell
# Camino A: compuesto oficial de GIBS (sin autenticación)
.venv\Scripts\python.exe prototipos\poster_pace_gibs.py --hasta 2026-10-24 --dias 8 --px 3000

# Camino B: L3M SFREFL en NetCDF (archivo manual de OB.DAAC)
.venv\Scripts\python.exe prototipos\poster_pace.py --nc "...\PACE_OCI.<fecha>.L3m.DAY.SFREFL.<res>.nc"
```

- **No hay descargador de SFREFL en el repo**: ese `.nc` se baja a mano desde
  OB.DAAC con Earthdata Login. `poster_pace_gibs.py` es el camino reproducible
  sin cuenta.
- SFREFL es reflectancia **de superficie**: las nubes vienen enmascaradas. El
  compuesto de GIBS sí trae nubes, aerosoles y sombras.
- PACE es polar: un día suelto deja huecos. `--dias 8` rellena por prioridad
  temporal.

## Campos de modelo ECMWF y ERA5

### 12. Precipitación acumulada (`tp`)

Un solo par de scripts para tres modelos (`ifs`, `aifs-ens`, `aifs-single`).

```powershell
# 1) Bajar sólo el rango de bytes de tp/sfc (HTTP Range, ~20 MB)
.venv\Scripts\python.exe descargar\precipitacion_ecmwf.py --modelo aifs-ens --fecha 2026-10-20 --ciclo 12 --hasta-hora 360 --paso 6

# 2) Cuadros + póster de cierre
.venv\Scripts\python.exe cuadros\cuadros_precipitacion.py --modelo aifs-ens --fecha 2026-10-20 --ciclo 12 --hasta-hora 360 --paso 6

# 3) MP4
.venv\Scripts\python.exe animar\armar.py --frames "D:\...\frames_precipitacion_aifs_ens_globo_2026-10-20T1200_61f_2712px" --fps 12.5
```

- **Ventana de 4 días**: ECMWF Open Data sólo conserva corridas recientes.
- `tp` es **acumulado desde el inicio** de la corrida; el paso 0 h debe dar 0 mm.
- El IFS publica en metros y el AIFS en `kg m⁻²`; el descargador lee `units` y
  escala.
- La escala es fija (30 niveles, 0.2 a 500+ mm) para que la animación se lea de
  corrido.
- **Ojo**: `--out` es alias de `--salidas`. `cuadros_viento_250.py` sólo acepta
  `--salidas`.

### 13. Anomalía de temperatura a 2 m

```powershell
.venv\Scripts\python.exe descargar\anomalia_2t_ecmwf.py --fecha 2026-10-20 --ciclo 12 --hasta-hora 360 --paso 6
.venv\Scripts\python.exe cuadros\cuadros_anomalia_2t.py --fecha 2026-10-20 --ciclo 12 --hasta-hora 360 --paso 6
```

- La climatología se construye **una vez** (~7 min) y se cachea en
  `DATOS/climatologia_era5_t2m_mes_hora.npz`; `--forzar-climatologia` la rehace.
- `era5_t2m_2024-2026.nc` se busca en `DATOS`, `D:\Users\guill\Desktop` y la raíz
  del repo (`ERA5_EXTRA_DIRS`).
- La banda neutra `[-0.5, +0.5] °C` es transparente: se ve la base del globo.

### 14. Viento en 250 mb y extremos de MSLP

```powershell
.venv\Scripts\python.exe descargar\viento_250_mslp.py --fecha 2026-10-20 --ciclo 18 --hasta-hora 144 --paso 6
.venv\Scripts\python.exe cuadros\cuadros_viento_250.py --fecha 2026-10-20 --ciclo 18 --hasta-hora 144 --paso 6
```

- En el `.index`, `levelist` viene como string (`"250"`): hay que filtrar por
  `levtype` **y** `levelist` o se agarra otro nivel.
- Escala fija de 10 kt (20 a 250 kt) con streamlines y puntas de flecha.
- `L`/`H` sólo para extremos significativos (`< 1002` / `> 1016 hPa`).

### 15. ERA5: anomalía mensual de temperatura

```powershell
# Requiere cdsapi + ~/.cdsapirc (no instalado por defecto)
.venv\Scripts\python.exe descargar\descargar_era5.py

.venv\Scripts\python.exe prototipos\poster_anomalia.py --mes 2026-08
```

- El descargador pide 1464 pasos (~2.2 GB) y **no** re-baja si el `.nc` existe
  (salvo `--force`).
- La climatología excluye el año objetivo para no diluir la anomalía.
- Salida: `planeta_anomalia_<AAAA-MM>.png` en `SALIDAS`.

---

## Reglas de oro

1. **No pises una corrida**: el nombre de frames incluye inicio, cantidad y px;
   los pósteres incluyen modelo, sensor y fecha. Si cambiás el `--px`, es otra
   carpeta.
2. **Todo es reanudable**: un `.nc`, un `crudo_NNN.jpg` o un `cuadro_NNN.png`
   existente se saltea. Un corte se retoma volviendo a correr el mismo comando.
3. **Para probar sin ensuciar**, mandá la salida a una carpeta temporal:
   `--out`, `--salidas`, `--frames` o `--salida` según el script. Los pósteres
   sin `--out` escriben en `SALIDAS`.
4. **`animar/armar.py`**: si `--salida` termina en `.gif` genera sólo GIF y si
   termina en `.mp4` genera sólo MP4, aunque pases `--formato ambos`. Para los
   dos, pasá un **directorio** como `--salida`.
5. **Numeración contigua**: `armar.py` aborta si falta un `cuadro_NNN.png`.
   Un hueco es un cuadro sin dato, no un cuadro a inventar.
6. **Cartopy** baja shapefiles de Natural Earth la primera vez; después quedan
   cacheados y todo funciona offline.

---

## Verificación ejecutada (2026-10-29)

Se corrió cada flujo con salida a un directorio temporal, sin tocar `SALIDAS`:

| Flujo | Comando probado | Resultado |
| --- | --- | --- |
| C13 formato ECMWF | `cuadros_c13_ir.py --solo-poster --desde 2026-10-23T19:40 --px 640` | PNG 499 KB |
| C13 clásico | `cuadros_goes.py --desde 2026-10-23T19:40 --n 1 --px 300` | PNG 121 KB |
| Himawari B13 | `cuadros_himawari_ir.py --solo-poster --px 640` | PNG 435 KB |
| C13 realista | `poster_goes_realista.py --px 600` | PNG 586 KB |
| GOES color real | `poster_goes_truecolor.py --px 600` | PNG 618 KB |
| GOES disco nativo | `poster_goes_disco.py --px 600` | PNG 684 KB |
| MUR realista | `poster_mur_realista.py --px 700` | PNG 897 KB |
| MUR animación | `animar_mur_realista.py --limite 1 --px 500` | 1 cuadro |
| Follaje póster | `poster_follaje.py --res 0p1deg --px 800` | PNG 197 KB |
| Follaje plano | `cuadros_follaje.py --desde 2026-10-05 --hasta 2026-10-07 --px 600` | 3 cuadros |
| Follaje globo | `cuadros_follaje_globo.py --desde 2026-10-05 --hasta 2026-10-06 --sub 1 --max-cuadros 1` | 1 cuadro |
| Precipitación IFS | `cuadros_precipitacion.py --solo-poster` | PNG 1.74 MB (idéntico al de `SALIDAS`) |
| Anomalía 2 m | `cuadros_anomalia_2t.py --solo-poster` | PNG 1.22 MB (idéntico) |
| Viento 250 mb | `cuadros_viento_250.py --solo-poster --salidas <temp>` | PNG 1.18 MB (idéntico) |
| GeoColor | descarga 1 crudo + `cuadros_geocolor.py --globo --n 1` | PNG 549 KB |
| Sandwich | descarga 1 par + `cuadros_sandwich.py --n 1` | PNG 5.5 MB |
| True Color GIBS | descarga 1 día + `cuadros_truecolor.py --n 1` | PNG 9.2 MB |
| MUR crudos | `mur_sst.py --desde 2025-01-01 --hasta 2025-01-01` | 1 JPEG 4.2 MB |
| GOES S3 | `descargar_goes.py` 1 slot | 1 `.nc` 24.8 MB |
| Himawari S3 | `descargar_himawari.py` 1 slot | 1 `.npz` 22.0 MB |
| ECMWF | `precipitacion_ecmwf.py` 1 paso | `serie_tp_mm.npz` (1, 721, 1440) |
| PACE GIBS | `poster_pace_gibs.py --dias 1 --px 600` | PNG 786 KB |
| PACE LANDVI | `pace_landvi.py` sin cookies | corta con error de autenticación (esperado) |
| Animar MP4/GIF | `armar.py` 1 cuadro, ambos formatos | MP4 0.08 MB, GIF 0.23 MB |
| ERA5 mensual | `poster_anomalia.py --mes 2026-07` | PNG 823 KB |

Los tres pósteres ECMWF salieron **byte por byte** con el mismo tamaño que los ya
publicados en `SALIDAS`, así que el render es determinista.

## Limitaciones conocidas

- **`descargar_era5.py`** necesita `cdsapi` y `~/.cdsapirc`; no se instaló por
  defecto. El `.nc` de ERA5 ya está bajado, así que el póster funciona igual.
- **`poster_pace.py`** necesita un L3M SFREFL que no tiene descargador propio.
- **`pace_landvi.py`** exige Earthdata Login (cookies o `~/.netrc`).
- **ECMWF** sólo publica las últimas ~4 días de corridas.
- **Windows**: `--help` de scripts con `μ` griega (U+03BC) puede fallar en consola
  cp1252. Está corregido en `poster_mur_realista.py`.
