# `scripts/` — ejecutables con CLI

Scripts sueltos. Todos resuelven la raíz del proyecto solos, así que funcionan desde
cualquier carpeta. Para el flujo completo de descarga + animación, ver
[`../GUIA.md`](../GUIA.md).

---

## `vista_paraguay.py`

**Cuadro fijo (PNG)** del globo centrado en Paraguay, con el encuadre aprobado:
Orthographic girado a `lon −73, lat −18`, paleta `ir_realce`, borde de Paraguay (GADM)
y sin grilla.

```powershell
.venv\Scripts\python.exe scripts\vista_paraguay.py
.venv\Scripts\python.exe scripts\vista_paraguay.py --nc OR_ABI-L2-CMIPF-M6C13_G19_....nc
.venv\Scripts\python.exe scripts\vista_paraguay.py --lon -70 --lat -20
.venv\Scripts\python.exe scripts\vista_paraguay.py --show
```

Sin `--nc` toma el `.nc` más nuevo de `D:\Users\guill\dataset era5\goes_c13_g19`.
Salida: `vista_paraguay_<AAAA-MM-DDTHHMM>.png` a tamaño completo (1176 px).

Depende de `lib/poster_goes.py` y de `datos/paraguay_gadm.json`.

---

## `descargar_era5.py`

Descarga **ERA5 2m temperature** (2024–2026) desde Copernicus CDS.

```powershell
.venv\Scripts\python.exe scripts\descargar_era5.py
.venv\Scripts\python.exe scripts\descargar_era5.py --out D:\otra\ruta
.venv\Scripts\python.exe scripts\descargar_era5.py --force    # re-descargar
```

- Requiere `cdsapi` y la API key configurada en `~/.cdsapirc`.
- Si el archivo destino ya existe y no está vacío, **no vuelve a descargar**
  (salvo `--force`).
- Destino por defecto: `D:\Users\guill\dataset era5\era5_t2m_2024-2026.nc`.
- La cola de CDS puede tardar bastante; conviene correrlo en segundo plano y revisar
  [`logs/`](../logs).
- Ojo: la descarga **solo** ocurre al ejecutar el script; sin argumentos válidos
  (`--help`) no toca la red.

Pide un día por mes a las 00/06/12/18 UTC (≈1464 pasos de tiempo, ~2.2 GB), que es la
resolución temporal suficiente para las climatologías del póster de anomalía.

---

## `descargar_goes.py`

Descarga archivos **GOES-R ABI L2 CMIP** desde el bucket público de NOAA S3 (infrarrojo,
cirrus, visible… para cualquier satélite y banda). Saltea los que ya existen. Reutiliza
`lib/goes_fetch.py`.

```powershell
.venv\Scripts\python.exe scripts\descargar_goes.py --sat G19 --banda C13 --desde 2026-10-02 --hasta 2026-10-05
.venv\Scripts\python.exe scripts\descargar_goes.py --help   # no toca la red
```

Destino por defecto: `D:\Users\guill\dataset era5\goes_<banda>_<sat>`.

---

## `render_anim.py`

**Animación por lotes**: renderiza los cuadros en varios procesos (poca RAM) y arma el
MP4 con el ffmpeg de `imageio-ffmpeg`. Pensado para ventanas largas (cientos de cuadros),
donde un notebook agotaría la memoria. Reutiliza los PNG si ya están.

```powershell
# Globo centrado en Paraguay, 432 cuadros a 720 px
.venv\Scripts\python.exe scripts\render_anim.py --sat G19 --banda C13 --desde 2026-10-02 --n 432 --px 720 --globo --centro -73 -18 --geojson datos\paraguay_gadm.json --paleta ir_realce
```

Salida: `D:\Users\guill\dataset era5\salidas\animacion_<vista>_<SAT>_<fecha>_<N>f_<PX>px.mp4`.
