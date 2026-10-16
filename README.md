# Climate 3D

![Póster GOES-19 · disco completo · 4 de octubre de 2026, 04:45 UTC](docs/portada.png)

Animaciones y pósteres del clima con datos reales: **ERA5** (reanálisis) y
**GOES-R ABI** (satélite). Todo se renderiza local con matplotlib + cartopy en un
estilo de afiche — fondo oscuro, barra de color fina al pie, rótulos discretos.
No hay servicios ni cuentas de por medio: bajás el dato y lo dibujás.

## Qué hay en el repo

| Carpeta | Contenido |
| --- | --- |
| [`lib/`](./lib) | Los módulos que dibujan: póster de anomalía (ERA5) y póster/vista GOES |
| [`scripts/`](./scripts) | Ejecutables: descargar datasets, vista fija y animación por lotes |
| [`notebooks/`](./notebooks) | Prototipos y animaciones, para probar y tocar |
| [`datos/`](./datos) | Auxiliares chicos que sí van al repo (el contorno de Paraguay) |
| [`docs/`](./docs) | La portada y la galería de imágenes publicadas |
| [`logs/`](./logs) | Registros de descarga, descartables |

Si es tu primera vez, andá a [`GUIA.md`](./GUIA.md): ahí está el flujo completo
(descargar → animar) explicado paso a paso.

## Cómo se ven

En [`docs/galeria/`](./docs/galeria) quedan los PNG generados. Un recorrido
rápido de lo que hay:

- **Disco completo, GOES-East C13** con la paleta `ir_realce` — la portada.
- **Globo centrado en Paraguay**, con el contorno del país marcado.
- **Zoom regional** a Paraguay, Sudamérica y el cono sur.
- **Anomalía de temperatura (ERA5)**: la media del mes contra su propia
  climatología.
- **Cirrus C04 de GOES-West (G18)**, en la rampa muestreada de la referencia.

## Requisitos

- Python 3.12 y el entorno `.venv` de la raíz.
- `numpy`, `xarray`, `matplotlib`, `cartopy`, `Pillow` y `rich`. Para ERA5, además
  `cdsapi`.

```powershell
.venv\Scripts\python.exe -c "import cartopy, xarray, rich; print('ok')"
```

## Primeros pasos

```powershell
# Póster de disco completo desde un .nc GOES
.venv\Scripts\python.exe lib\poster_goes.py --paleta ir_realce

# Globo centrado en Paraguay
.venv\Scripts\python.exe scripts\vista_paraguay.py

# Animación: abrí notebooks\animacion_globo_g19.ipynb y corré las celdas
```

## El formato

Todas las salidas comparten el mismo vestuario, así que un póster, un cuadro de
animación o una vista regional se leen igual:

- El **crédito** (`Graphic by @Gillo97`) va arriba a la derecha y repetido como
  marca de agua. Se cambia con `--credito`.
- Debajo del título va la **fecha y hora del cuadro, grande**: es lo primero que
  uno quiere leer.
- El **contorno de Paraguay** se dibuja negro y fino (0.8 pt), sutil sobre el
  mapa. Se activa con `--geojson` y se apaga con `--sin-borde`.
- **Paletas**: `ir_realce` (IR con color en los topes fríos), `termico`,
  `anomalia`, `gris`, `magma`, `inferno`, `turbo`.

## Datos y salidas

Los `.nc` pesan varios GB y los MP4/GIF también, así que no van al repo: viven en
`D:\Users\guill\dataset era5` y los scripts los buscan ahí. Las **imágenes finales
en PNG sí se publican**, en [`docs/`](./docs).

## Notas

- Los `.nc`, `.gif` y `.log` están ignorados; las imágenes de `docs/` se exceptúan
  a propósito.
- Las animaciones salen en **MP4** con el ffmpeg que trae `imageio-ffmpeg` — no
  hace falta tenerlo en el PATH. El GIF queda para el loop universal.
- Los slots GOES son cada 10 min (modo 6) y la hora sale del nombre del archivo,
  no la escribas a mano. Ojo: el `t` del producto cae unos 5 min después del inicio
  del escaneo, así que un archivo que arranca a las 04:40 se rotula 04:45.
