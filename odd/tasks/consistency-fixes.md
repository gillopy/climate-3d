# Consistencia del pipeline: datos y rutas de salida

Rama: `chore/consistency-fixes`
Base: `main` @ `3235d9f`

## Objetivo
Eliminar las inconsistencias detectadas en el análisis, sin rediseñar el formato
visual de los pósteres/animaciones. Foco: que cada entrypoint lea los datos correctos
y escriba sus salidas siempre en `D:\Users\guill\dataset era5\salidas`.

## Alcance
- `lib/poster_anomalia.py` — búsqueda del NetCDF de ERA5.
- `notebooks/animacion_paraguay_g19.ipynb`, `notebooks/animacion_cirrus_g18.ipynb` — rutas de salida y comentarios obsoletos.
- `notebooks/prototipo_planeta_orthographic.ipynb` — metadata de kernel.
- `scripts/descargar_goes_c04.py` — consistencia con el resto (guard de red).
- `.gitignore` — imágenes generadas fuera del repo.

## Fuera de alcance (rama aparte)
- Deduplicación de la lógica S3/loader (`refactor/goes-common`).
- Unificación del fundido GIF en `lib/`.

## Tareas
- [ ] T1 — `find_data_file` de ERA5: buscar en la raíz documentada (recursiva) y en
      ubicaciones alternativas; reportar la ruta usada y un aviso claro si cae en sintéticos.
- [ ] T2 — Notebooks paraguay/cirrus: escribir PNG/GIF en `SALIDAS` (hoy caen en el CWD
      dentro del repo). Actualizar comentarios que dicen "no hay ffmpeg".
- [ ] T3 — Prototipo: kernel metadata (`python3`) en lugar de `.venv-1 (3.14.2)`.
- [ ] T4 — `descargar_goes_c04.py`: docstring/guard alineados con los notebooks.
- [ ] T5 — `.gitignore`: ignorar PNG de salida generados por los notebooks.
- [ ] T6 — Smoke test limitado de cada entrypoint; registrar qué genera y dónde.

## Verificación
Cada tarea se cierra con una corrida reducida que confirme salida y destino.
Commits por unidad de trabajo (Conventional Commits).
