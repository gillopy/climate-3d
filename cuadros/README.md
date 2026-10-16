# `cuadros/` — render cuadro por cuadro

Convierte datos ya descargados en los PNG de una animación. **No descarga ni arma el video**:
deja `cuadro_NNN.png` en `SALIDAS/frames_<etiqueta>/` y termina diciéndote qué correr en
`animar/`.

| Archivo | Entrada | Vista |
|---|---|---|
| `cuadros_goes.py` | `.nc` de GOES-R ABI (`DATOS/goes_<banda>_<sat>/`) | Disco, globo o zona |
| `cuadros_geocolor.py` | `crudo_NNN.jpg` de `descargar/geocolor.py` | Globo o plano |

Los dos renderizan **por lotes en procesos separados**: con cientos de cuadros, un solo
proceso agota la RAM de una máquina chica. Y los dos **reutilizan** los PNG que ya existen, así
que si se corta se retoma donde quedó.

---

## `cuadros_goes.py`

```powershell
# Globo centrado en Paraguay, 432 cuadros a 720 px
.venv\Scripts\python.exe cuadros\cuadros_goes.py --sat G19 --banda C13 --desde 2026-10-02 `
    --n 432 --px 720 --globo --centro -73 -18 --paleta ir_realce

# Disco completo
.venv\Scripts\python.exe cuadros\cuadros_goes.py --sat G18 --banda C04 --desde 2026-10-03 --n 144 --px 1200
```

| Opción | Qué hace |
|---|---|
| `--sat`, `--banda`, `--desde`, `--paso` | Igual que en la descarga |
| `--n` | Cantidad de cuadros a animar |
| `--px` | Lado de cada cuadro en píxeles |
| `--globo` | Reprojecta a Orthographic (aspecto "planeta") |
| `--centro LON LAT` / `--zona` | Dónde centrar el globo |
| `--geojson` | Borde destacado |
| `--paleta` | `ir_realce`, `termico`, `anomalia`, `gris`, `magma`, … |
| `--vmin` / `--vmax` | Escala fija (por defecto, percentiles del primer cuadro) |
| `--lote` | Cuadros por proceso (bajalo si te falta RAM) |
| `--datos` | Carpeta de los `.nc` |

---

## `cuadros_geocolor.py`

```powershell
.venv\Scripts\python.exe cuadros\cuadros_geocolor.py --globo --desde 2026-10-15T20:00 --n 24 --px 600
```

| Opción | Qué hace |
|---|---|
| `--desde`, `--n`, `--paso` | Qué ventana renderizar |
| `--globo` / `--centro` | Globo Orthographic o vista plana |
| `--px` | Lado de cada cuadro en píxeles |
| `--dpi` | dpi del render del globo |
| `--geojson`, `--borde-color`, `--borde-ancho` | Borde destacado |
| `--credito` | Crédito y marca de agua |
| `--sin-fecha` | No estampar la fecha/hora |

Es **offline por construcción**: sólo lee los `crudo_NNN.jpg` que dejó `descargar/geocolor.py`.
Si falta alguno, aborta nombrándote el comando exacto de descarga.

Dos cosas que costó dejar bien y conviene no romper:

- **El warp Orthographic es a mano** (mapeo inverso con numpy). Cartopy no se puede usar para
  reproyectar imágenes en este venv: su `imshow` con otra proyección importa `img_transform`,
  que exige `pykdtree` o `scipy`, y no están instalados.
- **Los rótulos escalan sub-lineal** (`esc = 0.8 · (px/720)^0.45`): lineal hacía que a 2048 px
  el título dominara el cuadro.

Además el render está **sellado**: si cambiás un parámetro de aspecto (texto, borde, escala),
los PNG viejos se descartan solos en vez de reutilizarse con el rótulo anterior.

---

## Nota sobre huecos

Si un slot se cae (por ejemplo, un cuadro sin dato), la numeración queda con un hueco y
`animar/armar.py` lo va a rechazar — **y está bien**, porque `ffmpeg` cortaría el video ahí sin
avisar. Renumerá los posteriores o volvé a renderizar.

## Next step

[`../animar/`](../animar): convertir esa carpeta de cuadros en un MP4 o un GIF.
