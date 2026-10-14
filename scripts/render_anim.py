"""Renderiza una animación GOES-R ABI por lotes y arma el MP4.

Pensado para ventanas largas (cientos de cuadros): renderizar todo en un solo proceso
agota la memoria en máquinas chicas. Acá cada lote de `--lote` cuadros corre en su
propio proceso (memoria limpia) y al final se arma el MP4 con el ffmpeg que trae
`imageio-ffmpeg` (no hace falta tener ffmpeg en el PATH).

Los cuadros se guardan como PNG en una carpeta y se reutilizan si ya están (para
rearmar el MP4 sin volver a renderizar).

Uso (desde la raíz del proyecto):

    # Globo centrado en Paraguay, 432 cuadros a 720 px (dataset G19 C13 completo)
    .venv\\Scripts\\python.exe scripts\\render_anim.py --sat G19 --banda C13 ^
        --desde 2026-10-02 --n 432 --px 720 --globo --centro -73 -18 ^
        --geojson datos\\paraguay_gadm.json --paleta ir_realce

    # Disco completo
    .venv\\Scripts\\python.exe scripts\\render_anim.py --sat G18 --banda C04 --desde 2026-10-03 --n 144 --px 1200

    # Prueba rápida (pocos cuadros, chico)
    .venv\\Scripts\\python.exe scripts\\render_anim.py --sat G19 --banda C13 --desde 2026-10-02 --n 4 --px 480 --globo
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "lib"))
import imageio_ffmpeg  # noqa: E402
from goes_fetch import cargar  # noqa: E402
from poster_goes import BG, PALETTES, ZONES, draw_goes_poster  # noqa: E402

RAIZ_DATOS = Path(r"D:\Users\guill\dataset era5")
SALIDAS = RAIZ_DATOS / "salidas"
PATRON = re.compile(r"_s(\d{14})_")


def carpeta_datos(sat: str, banda: str) -> Path:
    return RAIZ_DATOS / f"goes_c{banda[1:].lower()}_{sat.lower()}"


def slot_map(datos: Path) -> dict:
    """Índice (fecha, hora, minuto) -> ruta del .nc (según el inicio de escaneo)."""
    m = {}
    for f in datos.glob("*.nc"):
        mm = PATRON.search(f.name)
        if not mm:
            continue
        s = mm.group(1)
        dt = (datetime(int(s[:4]), 1, 1)
              + timedelta(days=int(s[4:7]) - 1, hours=int(s[7:9]), minutes=int(s[9:11])))
        m[(dt.date(), dt.hour, dt.minute)] = f
    return m


def render(cfg, sl_map, start, end, vmin, vmax):
    for i in range(start, end + 1):
        t = cfg["t0"] + timedelta(minutes=cfg["paso"] * (i - 1))
        ruta = sl_map[(t.date(), t.hour, t.minute)]
        campo, x, y, proj, unidad, rot = cargar(ruta, tope_px=cfg["tope"], escena=cfg["escena"])
        fig, _, _ = draw_goes_poster(
            campo, x=x, y=y, proj=proj, title=rot[0], subtitle=rot[1], unit_label=unidad,
            src_line=rot[2], data_line=rot[3], credit=cfg["credito"],
            cmap=PALETTES[cfg["paleta"]], vmin=vmin, vmax=vmax,
            size=cfg["lado"], dpi=cfg["dpi"], globe_center=cfg["globo_center"],
            highlight_geojson=cfg["geojson"], highlight_width=cfg["hl_width"])
        fig.savefig(cfg["frames_dir"] / f"cuadro_{i:03d}.png", format="png", facecolor=BG)
        plt.close(fig)
        if i % 8 == 0 or i == end:
            print(f"    {i}/{end}", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Animación GOES-R ABI por lotes + MP4.")
    ap.add_argument("--sat", default="G19", help="satélite, p. ej. G19")
    ap.add_argument("--banda", default="C13", help="banda, p. ej. C13")
    ap.add_argument("--desde", default="2026-10-02", help="primer cuadro, UTC")
    ap.add_argument("--n", type=int, default=144, help="cantidad de cuadros")
    ap.add_argument("--paso", type=int, default=10, help="minutos entre cuadros")
    ap.add_argument("--px", type=int, default=720, help="lado de cada cuadro en píxeles")
    ap.add_argument("--dpi", type=int, default=140, help="dpi del render")
    ap.add_argument("--paleta", default="ir_realce", choices=sorted(PALETTES),
                    help="paleta de color")
    ap.add_argument("--globo", action="store_true", help="reproyectar a Orthographic")
    ap.add_argument("--centro", nargs=2, type=float, metavar=("LON", "LAT"),
                    help="centro del globo (default: -58 -23)")
    ap.add_argument("--zona", choices=sorted(ZONES), help="centro del globo a partir de una zona")
    ap.add_argument("--geojson", help="borde a destacar (GeoJSON Polygon/MultiPolygon)")
    ap.add_argument("--hl-width", type=float, default=1.2, help="grosor del borde")
    ap.add_argument("--credito", default="Graphic by @tu_usuario")
    ap.add_argument("--vmin", type=float, help="mínimo de la escala (default: percentiles)")
    ap.add_argument("--vmax", type=float, help="máximo de la escala (default: percentiles)")
    ap.add_argument("--fps", type=float, default=12.5, help="cuadros por segundo del MP4")
    ap.add_argument("--lote", type=int, default=24, help="cuadros por proceso")
    ap.add_argument("--datos", help="carpeta de los .nc (default: la del satélite/banda)")
    ap.add_argument("--out", help="carpeta de salida (default: D:\\...\\salidas)")
    # uso interno: renderiza un rango con escala fija
    ap.add_argument("--rango", nargs=4, metavar=("S", "E", "VMIN", "VMAX"),
                    help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    datos = Path(args.datos) if args.datos else carpeta_datos(args.sat, args.banda)
    t0 = datetime.fromisoformat(args.desde)
    lado = args.px / args.dpi
    vista = "globo" if args.globo else "disco"
    globo_center = None
    if args.globo:
        if args.centro:
            globo_center = tuple(args.centro)
        elif args.zona:
            w, e, s, n = ZONES[args.zona]
            globo_center = ((w + e) / 2, (s + n) / 2)
        else:
            globo_center = (-58.0, -23.0)
    salida = Path(args.out) if args.out else SALIDAS
    cfg = {
        "t0": t0, "paso": args.paso, "tope": args.px, "lado": lado, "dpi": args.dpi,
        "paleta": args.paleta, "geojson": args.geojson, "hl_width": args.hl_width,
        "credito": args.credito, "globo_center": globo_center, "escena": "FULL DISK",
        "frames_dir": salida / f"frames_{args.sat}_{t0:%Y-%m-%dT%H%M}_{args.n}f_{args.px}px",
    }
    cfg["frames_dir"].mkdir(parents=True, exist_ok=True)
    mp4 = salida / f"animacion_{vista}_{args.sat}_{t0:%Y-%m-%dT%H%M}_{args.n}f_{args.px}px.mp4"

    sl_map = slot_map(datos)
    if not sl_map:
        raise SystemExit(f"No hay .nc en {datos} (descargalos con scripts/descargar_goes.py).")

    # Modo lote: renderiza el rango y sale.
    if args.rango:
        s, e, vmin, vmax = (int(args.rango[0]), int(args.rango[1]),
                            float(args.rango[2]), float(args.rango[3]))
        render(cfg, sl_map, s, e, vmin, vmax)
        return

    print(f"{vista} | {args.sat} {args.banda} | {args.n} cuadros desde {t0} | {args.px} px")
    ya = sorted(cfg["frames_dir"].glob("cuadro_*.png"))
    if len(ya) == args.n:
        print(f"{len(ya)} cuadros ya renderizados -> se saltea el render")
    else:
        if args.vmin is None or args.vmax is None:
            campo, *_ = cargar(sl_map[(t0.date(), t0.hour, t0.minute)],
                               tope_px=cfg["tope"], escena=cfg["escena"])
            lo, hi = np.nanpercentile(campo, [0.5, 99.5])
            vmin = args.vmin if args.vmin is not None else float(lo)
            vmax = args.vmax if args.vmax is not None else float(hi)
        else:
            vmin, vmax = args.vmin, args.vmax
        print(f"escala: {vmin:.1f} a {vmax:.1f} | frames en {cfg['frames_dir']}")
        t_inicio = time.time()
        for s in range(1, args.n + 1, args.lote):
            e = min(s + args.lote - 1, args.n)
            print(f"lote {s}-{e} ...", flush=True)
            subprocess.run([sys.executable, str(Path(__file__).resolve()),
                            *sys.argv[1:], "--rango", str(s), str(e), str(vmin), str(vmax)],
                           check=True)
            print(f"  ok ({time.time() - t_inicio:.0f}s)", flush=True)

    proc = subprocess.run([
        imageio_ffmpeg.get_ffmpeg_exe(), "-y",
        "-framerate", f"{args.fps:.6f}", "-start_number", "1",
        "-i", str(cfg["frames_dir"] / "cuadro_%03d.png"),
        "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        "-c:v", "libx264", "-preset", "slow", "-pix_fmt", "yuv420p", "-crf", "16",
        "-movflags", "+faststart", str(mp4)], capture_output=True, text=True,
        encoding="utf-8", errors="replace")
    if proc.returncode:
        print(proc.stderr[-1200:])
        raise SystemExit(f"ffmpeg falló con código {proc.returncode}")
    print(f"MP4: {mp4} ({mp4.stat().st_size / 1e6:.1f} MB, {args.px}x{args.px})")


if __name__ == "__main__":
    main()
