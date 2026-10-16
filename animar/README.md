# `animar/` — de cuadros a video

El último paso: agarra una carpeta `frames_*` con `cuadro_NNN.png` y la convierte en MP4 o
GIF. **No renderiza ni descarga nada.**

| Archivo | Qué hace |
|---|---|
| `armar.py` | Arma el MP4 (o el GIF) desde los cuadros de una carpeta |

---

## Quick path

```powershell
# MP4 a 8 fps
.venv\Scripts\python.exe animar\armar.py --frames "D:\Users\guill\dataset era5\salidas\frames_geocolor_globo_2026-10-04T0000_432f_2048px" --fps 8

# GIF, y a una ruta explícita
.venv\Scripts\python.exe animar\armar.py --frames <carpeta> --formato gif --salida C:\ruta\salida.gif
```

| Opción | Qué hace |
|---|---|
| `--frames` | Carpeta con los `cuadro_NNN.png` (obligatorio) |
| `--fps` | Cuadros por segundo (por defecto 12,5) |
| `--formato` | `mp4`, `gif` o `ambos` (por defecto `mp4`) |
| `--salida` | Archivo de salida; si no, se deriva del nombre de la carpeta |

## Details

| Tema | Decisión |
|---|---|
| Nombre de salida | `frames_<etiqueta>` → `animacion_<etiqueta>`, **con la cantidad real de cuadros** encontrados, no la que declara la carpeta |
| MP4 | H.264 con el ffmpeg que trae `imageio-ffmpeg`; no hace falta tenerlo en el PATH |
| GIF | Una **paleta común** a todos los cuadros: con paleta por cuadro los colores parpadean |
| Huecos | Si la numeración no es 1..N, **aborta**. `ffmpeg` con `-i cuadro_%03d.png` corta en el primer hueco y devolvería un video truncado sin avisar |
| MP4 vs GIF | El MP4 pesa ~7× menos y se ve mejor; el GIF sólo conviene para animaciones cortas y chicas |

## Checklist

- [ ] La carpeta tiene los `cuadro_NNN.png` contiguos desde 1.
- [ ] `--fps` acorde a la cadencia: 10 min entre cuadros a 12,5 fps se ve fluido.
- [ ] Si vas a publicar, el MP4 antes que el GIF.

## Next step

Volvé al [README](../README.md) del proyecto o a [`../GUIA.md`](../GUIA.md) para el flujo
completo.
