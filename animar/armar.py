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
import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import imageio_ffmpeg
from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ / "comun") not in sys.path:
    sys.path.insert(0, str(RAIZ / "comun"))

from reuso_cuadros import es_de_instante, instante_de  # noqa: E402

PATRON = "cuadro_%03d.png"
_RE_NUM = re.compile(r"cuadro_(\d+)\.png$")
_RE_TOTAL = re.compile(r"_(\d+)f(?:_|$)")


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


def cuadros_ordenados(frames_dir: Path) -> list[Path]:
    """Cuadros en orden cronológico, con nombre viejo (`001`) o por instante.

    El nombre por instante (`cuadro_20261122T0040.png`) ordena solo: es
    `YYYYMMDDTHHMM`, así que el orden alfabético es el del tiempo. Las carpetas
    viejas numeradas se ordenan por número, como siempre.
    """
    instantes = [p for p in frames_dir.glob("cuadro_*.png")
                 if es_de_instante(p.name)]
    if instantes:
        return sorted(instantes, key=lambda p: p.name)
    return [frames_dir / (PATRON % numero) for numero in cuadros_numerados(frames_dir)]


def huecos_temporales(rutas: list[Path]) -> list[datetime]:
    """Instantes que faltan entre el primero y el último de una serie por instante.

    El paso se deduce del salto más chico presente (la cadencia real del producto:
    10 min en el ABI). No es un error: la fuente deja huecos, y un tramo que no
    existe no puede pasar como si el tiempo hubiera seguido de largo.
    """
    instantes = [i for i in (instante_de(p.name) for p in rutas) if i is not None]
    if len(instantes) < 3:
        return []
    saltos = [(b - a) for a, b in zip(instantes, instantes[1:]) if b > a]
    if not saltos:
        return []
    paso = min(saltos)
    presentes = set(instantes)
    faltan = []
    actual = instantes[0]
    while actual < instantes[-1]:
        actual += paso
        if actual < instantes[-1] and actual not in presentes:
            faltan.append(actual)
    return faltan


def cuadros_esperados(nombre: str) -> int | None:
    """Cuántos cuadros declara el nombre de la carpeta (`..._80f_2712px`).

    Hace falta para saber si faltan cuadros del final: sin eso, un hueco después del
    último presente es invisible.
    """
    match = _RE_TOTAL.search(nombre)
    return int(match.group(1)) if match else None


def huecos(nums: list[int], total: int | None = None) -> list[int]:
    """Números que faltan entre 1 y `total` (por defecto, el último presente).

    No es un error: GIBS y NOAA dejan huecos (gránulos que todavía no publicaron o que
    esa pasada no tiene). La animación se arma con lo que hay, pero **avisando**: un
    tramo que no existe no puede pasar como si el tiempo hubiera seguido de largo.
    """
    presentes = set(nums)
    ultimo = total or (nums[-1] if nums else 0)
    return [i for i in range(1, ultimo + 1) if i not in presentes]


def _aviso_de_huecos(faltan: list[int], presentes: int, total: int | None) -> str:
    """Mensaje único y explícito: qué falta y cuánto se acorta la animación."""
    muestra = ", ".join(str(numero) for numero in faltan[:12])
    if len(faltan) > 12:
        muestra += ", ..."
    esperados = total if total else (presentes + len(faltan))
    return (f"aviso: faltan {len(faltan)} cuadro(s) de {esperados} ({muestra}): "
            f"la animación tiene {presentes} y esos tramos no se ven")


@contextlib.contextmanager
def secuencia_ordenada(rutas: list[Path]):
    """Carpeta con los cuadros renumerados 1..N, o la misma si ya es contigua.

    ffmpeg lee `cuadro_%03d.png` y corta en el primer índice faltante, así que una
    serie con nombres de instante (o con huecos) hay que renumerarla. Se arma una
    carpeta al lado (mismo volumen, enlaces duros; copia si el enlace no se puede)
    y se borra al salir.
    """
    contigua = all(ruta.name == PATRON % i for i, ruta in enumerate(rutas, start=1))
    if contigua:
        yield rutas[0].parent
        return
    base = rutas[0].parent
    temporal = base / f".{base.name}_contiguos"
    shutil.rmtree(temporal, ignore_errors=True)
    temporal.mkdir(parents=True, exist_ok=True)
    try:
        for destino, origen in enumerate(rutas, start=1):
            objetivo = temporal / (PATRON % destino)
            try:
                os.link(origen, objetivo)
            except OSError:
                shutil.copy2(origen, objetivo)
        yield temporal
    finally:
        shutil.rmtree(temporal, ignore_errors=True)


@contextlib.contextmanager
def secuencia_contigua(frames_dir: Path, nums: list[int]):
    """Carpeta con los cuadros numerados, sin huecos (envoltorio de `secuencia_ordenada`)."""
    with secuencia_ordenada([frames_dir / (PATRON % numero) for numero in nums]) as carpeta:
        yield carpeta


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
        "-c:v", "libx264", "-preset", "slow", "-threads", "2",
        "-pix_fmt", "yuv420p", "-crf", "18",
        "-movflags", "+faststart", str(destino)], capture_output=True, text=True,
        encoding="utf-8", errors="replace")
    if proc.returncode:
        print(proc.stderr[-1500:])
        raise SystemExit(f"ffmpeg falló con código {proc.returncode}")
    return destino


def _archivo_huella(destino: Path) -> Path:
    """Dónde queda la huella del video armado (hermana del archivo)."""
    return destino.with_suffix(destino.suffix + ".armado.json")


def huella_video(fps: float, rutas: list[Path]) -> dict:
    """Qué video corresponde a esta lista de cuadros y a este fps."""
    return {
        "fps": round(float(fps), 6),
        "n": len(rutas),
        "primero": rutas[0].name,
        "ultimo": rutas[-1].name,
    }


def al_dia(destino: Path, huella: dict, rutas: list[Path]) -> bool:
    """True si el video ya se armó con estos cuadros y este fps.

    Evita los ~10 min de ffmpeg de una animación de 200 MB cuando la corrida no
    aportó ningún cuadro nuevo. La huella se escribe recién cuando ffmpeg terminó
    bien: si se cortó a la mitad, el archivo existe pero la huella no, y se rehace.
    """
    if not destino.is_file():
        return False
    archivo = _archivo_huella(destino)
    if not archivo.is_file():
        return False
    try:
        previo = json.loads(archivo.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if previo != huella:
        return False
    return destino.stat().st_mtime >= max(p.stat().st_mtime for p in rutas)


def _anotar(destino: Path, huella: dict) -> None:
    _archivo_huella(destino).write_text(
        json.dumps(huella, indent=2) + "\n", encoding="utf-8")


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
    ap.add_argument("--forzar", action="store_true",
                    help="rehace el video aunque ya esté al día")
    args = ap.parse_args(argv)

    frames_dir = Path(args.frames)
    if not frames_dir.is_dir():
        raise SystemExit(f"No existe la carpeta {frames_dir}.")
    rutas = cuadros_ordenados(frames_dir)
    if not rutas:
        raise SystemExit(f"No hay cuadro_*.png en {frames_dir}.")
    if es_de_instante(rutas[0].name):
        # Serie por instante: el paso se deduce de la propia serie y los huecos se
        # avisan con fecha, que es lo que se ve en el video.
        faltan_instantes = huecos_temporales(rutas)
        if faltan_instantes:
            muestra = ", ".join(f"{t:%d/%m %H:%M}" for t in faltan_instantes[:8])
            print(f"  aviso: faltan {len(faltan_instantes)} cuadro(s) en la serie "
                  f"({muestra}): esos tramos no se ven", flush=True)
    else:
        nums = cuadros_numerados(frames_dir)
        total = cuadros_esperados(frames_dir.name)
        faltan = huecos(nums, total)
        if faltan:
            print(f"  {_aviso_de_huecos(faltan, len(nums), total)}", flush=True)
    n_real = len(rutas)
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
        destino = destinos["mp4"]
        huella = huella_video(args.fps, rutas)
        if not args.forzar and al_dia(destino, huella, rutas):
            print(f"MP4 al día: {destino} ({n_real} cuadros, {args.fps:g} fps)")
        else:
            with secuencia_ordenada(rutas) as carpeta:
                mp4 = armar_mp4(carpeta, destino, args.fps)
            _anotar(destino, huella)
            print(f"MP4: {mp4} ({mp4.stat().st_size / 1e6:.2f} MB)")
    if "gif" in destinos:
        destino = destinos["gif"]
        huella = huella_video(args.fps, rutas)
        if not args.forzar and al_dia(destino, huella, rutas):
            print(f"GIF al día: {destino} ({n_real} cuadros, {args.fps:g} fps)")
        else:
            gif = armar_gif(rutas, destino, args.fps)
            _anotar(destino, huella)
            print(f"GIF: {gif} ({gif.stat().st_size / 1e6:.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
