# `animar/` — de cuadros a video

El último paso: agarra una carpeta con cuadros (`cuadro_NNN.png` o
`cuadro_AAAAMMDDTHHMM.png`) y la convierte en MP4 o GIF. **No renderiza ni descarga nada.**

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
| `--frames` | Carpeta con los cuadros: `cuadro_NNN.png` (viejos) o `cuadro_AAAAMMDDTHHMM.png` (por instante) |
| `--fps` | Cuadros por segundo (por defecto 12,5) |
| `--formato` | `mp4`, `gif` o `ambos` (por defecto `mp4`) |
| `--salida` | Archivo de salida; si no, se deriva del nombre de la carpeta |
| `--forzar` | Rehace el video aunque ya esté al día |

## Details

| Tema | Decisión |
|---|---|
| Nombre de salida | `frames_<etiqueta>` → `animacion_<etiqueta>`, **con la cantidad real de cuadros** encontrados, no la que declara la carpeta |
| Orden | Por número si los nombres son `cuadro_NNN.png`; por nombre si son instantes (el orden alfabético ya es el del tiempo) |
| MP4 | H.264 con el ffmpeg que trae `imageio-ffmpeg`; no hace falta tenerlo en el PATH |
| GIF | Una **paleta común** a todos los cuadros: con paleta por cuadro los colores parpadean |
| Huecos | Se avisan con fecha (serie por instante) o por número (serie numerada) y los cuadros se renumeran en una carpeta temporal: `ffmpeg -i cuadro_%03d.png` corta en el primer hueco y devolvería un video truncado sin avisar |
| Video al día | Junto a cada salida queda `<salida>.armado.json` (fps, cantidad, primero, último). Si nada cambió, `armar.py` sale sin llamar a ffmpeg; `--forzar` lo rehace |
| MP4 vs GIF | El MP4 pesa ~7× menos y se ve mejor; el GIF sólo conviene para animaciones cortas y chicas |

## Checklist

- [ ] La carpeta tiene los cuadros (`cuadro_NNN.png` contiguos o `cuadro_<instante>.png`).
- [ ] `--fps` acorde a la cadencia: 10 min entre cuadros a 12,5 fps se ve fluido.
- [ ] Si vas a publicar, el MP4 antes que el GIF.

## Next step

Volvé al [README](../README.md) del proyecto o a [`../GUIA.md`](../GUIA.md) para el flujo
completo.
