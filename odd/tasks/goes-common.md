# refactor/goes-common — acceso GOES compartido

Rama: `refactor/goes-common`
Base: `main` @ `f6262de`

## Objetivo
Sacar la lógica duplicada (claves S3, descarga, lectura y fundido del GIF) de los tres
notebooks y del script a un único `lib/goes_fetch.py`, sin cambiar el formato visual
ni la salida.

## Tareas
- [x] WU1 — `lib/goes_fetch.py`: `claves_de_la_hora`, `clave_de`, `ruta_local`,
      `descargar`, `cargar` (disco completo o recorte) y `cuadros_con_fundido` /
      `fundido_desde_imagenes`.
- [x] WU2 — los 3 notebooks importan de `goes_fetch`; wrapper `cargar_cuadro` por vista;
      a `cirrus` se le agrega `DESCARGAR` (antes era el único sin él).
- [x] WU3 — `scripts/descargar_goes_c04.py` usa `goes_fetch` y tiene CLI real
      (`--desde/--hasta/--paso`); `--help` ya no toca la red (T4 del plan anterior).
- [x] WU4 — smoke test de los 3 notebooks.

## Resultado
Salidas idénticas a antes del refactor (3 frames a 300 px):
`animacion_paraguay_*.gif` 0.5 MB · `animacion_cirrus_*.gif` 0.4 MB ·
`animacion_globo_*_300px.mp4` 0.1 MB. Se eliminaron ~60 líneas duplicadas por notebook.
