"""Arma un MP4 o un GIF a partir de los cuadros PNG de una carpeta `frames_*`.

Sólo ensambla: no renderiza ni descarga nada. Lee los `cuadro_NNN.png` de la carpeta que
le pases, verifica que la secuencia sea contigua y deriva el nombre de salida del de la
carpeta (`frames_` → `animacion_`), usando la cantidad **real** de cuadros encontrados.

El MP4 se codifica con el ffmpeg que trae `imageio-ffmpeg` (no hace falta tenerlo en el
PATH); el GIF cuantiza una paleta común a todos los cuadros para que no parpadeen.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe animar\\armar.py --frames "D:\\...\\salidas\\frames_geocolor_globo_2026-10-04T0000_432f_2048px" --fps 8
    .venv\\Scripts\\python.exe animar\\armar.py --frames <carpeta> --formato gif
    .venv\\Scripts\\python.exe animar\\armar.py --frames <carpeta> --salida C:\\ruta\\salida.mp4
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from PIL import Image

PATRON = "cuadro_%03d.png"
_RE_NUM = re.compile(r"cuadro_(\d+)\.png$")


def _formatos(formato: str) -> list[str]:
    """Formatos a generar según `--formato`."""
    return ["mp4", "gif"] if formato == "ambos" else [formato]


def cuadros_numerados(frames_dir: Path) -> list[int]:
    """Números de todos los `cuadro_NNN.png` de la carpeta, ordenados."""
    nums = []
    for p in frames_dir.glob("cuadro_*.png"):
        m = _RE_NUM.match(p.name)
        if m:
            nums.append(int(m.group(1)))
    return sorted(nums)


def verificar_contiguos(nums: list[int]) -> None:
    """Aborta si la secuencia no es 1..N: ffmpeg cortaría en el primer hueco."""
    presentes = set(nums)
    ultimo = nums[-1] if nums else 0
    faltan = [i for i in range(1, ultimo + 1) if i not in presentes]
    if faltan:
        raise SystemExit(f"La secuencia no es contigua: faltan {len(faltan)} cuadros "
                         f"({faltan[:12]}...). Volvé a renderizarlos o descargarlos.")


def etiqueta_salida(frames_dir: Path, n_real: int) -> str:
    """`frames_<etiqueta>` → `animacion_<etiqueta>`, con la cantidad REAL de cuadros."""
    base = frames_dir.name
    etiqueta = base[len("frames_"):] if base.startswith("frames_") else base
    # El nombre de la carpeta puede declarar otra cantidad (p. ej. 432f): se reemplaza
    # por la real para que el video se identifique por lo que tiene adentro.
    etiqueta = re.sub(r"_\d+f_", f"_{n_real}f_", etiqueta)
    return f"animacion_{etiqueta}"


def armar_mp4(frames_dir: Path, destino: Path, fps: float) -> Path:
    """MP4 H.264 con el ffmpeg que trae imageio-ffmpeg (no hace falta en el PATH)."""
    proc = subprocess.run([
        imageio_ffmpeg.get_ffmpeg_exe(), "-y",
        "-framerate", f"{fps:.6f}", "-start_number", "1",
        "-i", str(frames_dir / PATRON),
        "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        "-c:v", "libx264", "-preset", "slow", "-pix_fmt", "yuv420p", "-crf", "18",
        "-movflags", "+faststart", str(destino)], capture_output=True, text=True,
        encoding="utf-8", errors="replace")
    if proc.returncode:
        print(proc.stderr[-1500:])
        raise SystemExit(f"ffmpeg falló con código {proc.returncode}")
    return destino


def armar_gif(cuadros_paths, destino: Path, fps: float) -> Path:
    """GIF en bucle infinito, con una única paleta para todos los cuadros.

    Una paleta adaptativa por cuadro hace parpadear los colores entre fotogramas
    (cada uno cuantiza distinto). Muestreando todos los cuadros se arma una tabla
    común y la animación queda estable.
    """
    imgs = [Image.open(p).convert("RGB") for p in cuadros_paths]
    ancho, alto = 160, 90
    muestra = Image.new("RGB", (ancho * len(imgs), alto))
    for i, im in enumerate(imgs):
        muestra.paste(im.resize((ancho, alto)), (i * ancho, 0))
    paleta = muestra.quantize(colors=256, method=Image.MEDIANCUT)
    frames = [im.quantize(palette=paleta, dither=Image.FLOYDSTEINBERG) for im in imgs]
    frames[0].save(destino, save_all=True, append_images=frames[1:],
                   duration=int(1000 / fps), loop=0, optimize=True)
    return destino


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Arma un MP4/GIF desde los cuadros de una carpeta frames_*.")
    ap.add_argument("--frames", required=True, help="carpeta con los cuadro_NNN.png")
    ap.add_argument("--fps", type=float, default=12.5, help="cuadros por segundo")
    ap.add_argument("--formato", choices=["mp4", "gif", "ambos"], default="mp4",
                    help="qué armar (por defecto mp4)")
    ap.add_argument("--salida",
                    help="archivo de salida (por defecto, junto a la carpeta de cuadros)")
    args = ap.parse_args(argv)

    frames_dir = Path(args.frames)
    if not frames_dir.is_dir():
        raise SystemExit(f"No existe la carpeta {frames_dir}.")
    nums = cuadros_numerados(frames_dir)
    if not nums:
        raise SystemExit(f"No hay cuadro_NNN.png en {frames_dir}.")
    verificar_contiguos(nums)
    n_real = len(nums)
    etiqueta = etiqueta_salida(frames_dir, n_real)

    if args.salida:
        p = Path(args.salida)
        if p.suffix.lower() == ".gif":
            destinos = {"gif": p}
        elif p.suffix.lower() == ".mp4":
            destinos = {"mp4": p}
        else:
            destinos = {k: p / f"{etiqueta}.{k}" for k in _formatos(args.formato)}
    else:
        destinos = {k: frames_dir.parent / f"{etiqueta}.{k}"
                    for k in _formatos(args.formato)}

    print(f"{n_real} cuadros en {frames_dir} -> {etiqueta}")

    if "mp4" in destinos:
        mp4 = armar_mp4(frames_dir, destinos["mp4"], args.fps)
        print(f"MP4: {mp4} ({mp4.stat().st_size / 1e6:.2f} MB)")
    if "gif" in destinos:
        gif = armar_gif(sorted(frames_dir.glob("cuadro_*.png")), destinos["gif"], args.fps)
        print(f"GIF: {gif} ({gif.stat().st_size / 1e6:.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
