# Consistencia del pipeline: datos y rutas de salida

Rama: `chore/consistency-fixes`
Base: `main` @ `3235d9f`

## Objetivo
Eliminar las inconsistencias detectadas en el análisis, sin rediseñar el formato
visual de los pósteres/animaciones. Foco: que cada entrypoint lea los datos correctos
y escriba sus salidas siempre en `D:\Users\guill\dataset era5\salidas`.

## Tareas
- [x] T1 — `find_data_file` de ERA5: busca en la raíz documentada (recursiva) y en
      ubicaciones alternativas; reporta la ruta usada y avisa claramente antes de caer
      en sintéticos. — commit `ef2a132`
- [x] T2 — Notebooks paraguay/cirrus: PNG/GIF ahora van a `SALIDAS` (antes caían en el
      CWD, dentro del repo). Comentarios de ffmpeg actualizados + nota del README. — commit `7fc9d7f`
- [x] T3 — Prototipo: kernel metadata a `Python 3` / 3.12.12. — commit `7fc9d7f`
- [ ] T4 — `descargar_goes_c04.py`: **diferido** a `refactor/goes-common`; su lógica S3
      se va a compartir en `lib/` ahí, no tiene sentido tocarla dos veces.
- [x] T5 — `.gitignore`: ignora `poster_*.png`, `animacion_*.png`, `vista_*.png`, `frames_*/`. — commit `cf4d4ac`
- [x] T6 — Smoke test limitado de cada entrypoint; resultados abajo.

## Verificación — smoke test (2026-10-14)
Todas las salidas fueron a `D:\Users\guill\dataset era5\salidas`; **nada quedó en el repo**.
Notebooks corridos con las celdas reales y parámetros reducidos (3 cuadros, 300 px).

| Entrypoint | Generó (en `...\salidas`) |
|---|---|
| `lib/poster_goes.py --size 3 --dpi 100` | `poster_goes_G19_C13_ir_realce.png` |
| `scripts/vista_paraguay.py` | `vista_paraguay_2026-10-03T2225.png` |
| `lib/poster_anomalia.py` (ERA5 real, 1464 pasos) | `planeta_anomalia_2026-08.png` |
| `animacion_paraguay_g19.ipynb` (3 frames) | `poster_paraguay_*.png` + `animacion_paraguay_*.gif` |
| `animacion_cirrus_g18.ipynb` (3 frames) | `poster_cirrus_*.png` + `animacion_cirrus_*.gif` |
| `animacion_globo_g19.ipynb` (3 frames) | `poster_globo_*.png` + `frames_*_300px/` + `animacion_globo_*_300px.mp4` |
| `scripts/descargar_era5.py --help` | (no toca red) |
| `scripts/descargar_goes_c04.py` | `py_compile` OK; **no se corre** (bajaría 432 archivos) |

## Pendiente (rama aparte)
- `refactor/goes-common`: deduplicar la lógica S3/loader de los 3 notebooks y del script;
  unificar la implementación del fundido GIF en `lib/`.
