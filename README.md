# Climate 3D — pósteres y animaciones satelitales

Visualizaciones de **temperatura** (reanálisis ERA5) y de **imágenes satelitales**
(GOES-R ABI) en estilo póster: globo sobre fondo oscuro, barra de color fina al pie
y rótulos (mes, variable, fuente, datos, crédito y marca de agua).

## Estructura

| Carpeta | Contenido |
|---|---|
| [`lib/`](./lib) | Módulos reutilizables: póster de anomalía ERA5 y póster GOES |
| [`notebooks/`](./notebooks) | Notebooks: prototipos y animaciones (GIF) |
| [`scripts/`](./scripts) | Scripts ejecutables: vista fija y descarga de ERA5 |
| [`datos/`](./datos) | Datos auxiliares (bordes GeoJSON) |
| [`logs/`](./logs) | Registros de descargas (descartables) |

Los **datos satelitales** (`.nc`, varios GB) y las **salidas** (PNG/GIF) no viven en
el repositorio: van a `D:\Users\guill\dataset era5` y `...\salidas` respectivamente.
Los notebooks ya apuntan ahí.

## Requisitos

- Python 3.12 con el entorno virtual `.venv` de la raíz.
- Paquetes principales: `numpy`, `xarray`, `matplotlib`, `cartopy`, `Pillow`, `rich`.
- Para el póster ERA5: `cdsapi` (descarga) — ver [`scripts/`](./scripts).

```powershell
# Verificar el entorno
.venv\Scripts\python.exe -c "import cartopy, xarray, rich; print('ok')"
```

## Inicio rápido

```powershell
# 1) Póster de disco completo desde un archivo GOES (busca el .nc en la raíz)
.venv\Scripts\python.exe lib\poster_goes.py --paleta ir_realce

# 2) Cuadro fijo centrado en Paraguay (usa el .nc más nuevo de D:)
.venv\Scripts\python.exe scripts\vista_paraguay.py

# 3) Animación: abrir notebooks\animacion_globo_g19.ipynb y correr las celdas
```

## Convenciones

- **Idioma**: docstrings, comentarios y mensajes en español; nombres de código en inglés
  cuando son términos técnicos (`draw_goes_poster`, `vmin`, `stride`).
- **Rutas de datos**: siempre absolutas a `D:\`, nunca dentro del repositorio.
- **Paletas**: la rampa del póster de anomalía se muestreó de una imagen de referencia;
  la IR con realce (`ir_realce`) pone color en los topes fríos y gris en el fondo.
- **Ventanas de tiempo**: los slots son cada 10 min (modo 6 de ABI); el nombre del
  archivo S3 codifica la hora, no hay que escribirla a mano.

## Notas

- Los `.nc` y `.gif` están en `.gitignore` por tamaño.
- Sin `ffmpeg` en el PATH, las animaciones se exportan a **GIF** (`PillowWriter`).
