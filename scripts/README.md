# `scripts/` — ejecutables de un solo uso

Scripts sueltos con CLI. Ambos resuelven la raíz del proyecto solos, así que funcionan
desde cualquier carpeta.

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
