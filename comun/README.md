# `comun/` — compartido, sin red

Módulos que usan los demás roles (descargar / prototipos / cuadros / animar). Ninguno
toca la red: la descarga vive entera en `descargar/`.

| Archivo | Qué aporta |
|---|---|
| `rutas.py` | La raíz de datos en un solo lugar: `RAIZ`, `DATOS`, `SALIDAS`, `ERA5_EXTRA_DIRS`, `find_data_file` |
| `estilo.py` | Constantes visuales de los pósteres: `BG`, `TXT`, `TXT_DIM`, `WM_COLOR`, `MONTHS_EN`, `POSTER_SIZE`, `POSTER_DPI`, `ANOM_COLORS`, `ANOM_CMAP` |
| `goes_lectura.py` | Lectura local de archivos GOES-R ABI: `PATRON`, `ruta_local`, `cargar` y los fundidos para GIF |

## Quick path

1. Importá la raíz de datos desde `rutas` en vez de escribirla a mano:

   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "comun"))
   from rutas import DATOS, SALIDAS  # noqa: E402
   ```

2. Si los datos viven en otro lado, exportá `CLIMATE3D_DATOS` y no toques código:

   ```powershell
   $env:CLIMATE3D_DATOS = "D:\mi\carpeta\era5"
   ```

3. Verificá que los módulos importan sin red:

   ```powershell
   .venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'comun'); import rutas, estilo, goes_lectura; print(rutas.DATOS)"
   ```

## Details

| Tema | Decisión |
|---|---|
| Raíz de datos | `comun/rutas.py` es la única fuente. `CLIMATE3D_DATOS` la sobreescribe; si no está definida se usa el valor histórico del proyecto |
| Rutas de repo | `RAIZ` apunta a la raíz del repositorio (`comun/` está un nivel por debajo) |
| Bootstrap de imports | Los módulos no forman un paquete: cada script agrega a `sys.path` sólo las carpetas que importa |
| Frontera de red | `comun/` no importa `requests`, `urllib` ni `cdsapi`; si falta un dato, quien lo necesite nombra el comando de `descargar/` |

## Checklist

- [ ] Nadie fuera de `comun/rutas.py` escribe una ruta absoluta de datos.
- [ ] `comun/` no importa nada de red.
- [ ] `cargar` de `goes_lectura` recibe los rótulos de `prototipos/poster_goes.py`.

## Next step

Volvé al [README](../README.md) del proyecto o seguí con `descargar/`, `prototipos/`,
`cuadros/` y `animar/`.
