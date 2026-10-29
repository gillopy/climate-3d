"""Animación del póster realista de MUR: un cuadro por semana, con la campana viva.

Reutiliza el render de `prototipos/poster_mur_realista.py` sin tocar el pipeline
existente. La diferencia con un póster fijo es que acá se recorre la serie semanal
de crudos, se recalcula la distribución (media, desvío e histograma) de cada cuadro
y la tarjeta de leyenda se actualiza cuadro a cuadro. Después se puede armar el MP4
con `animar/armar.py`.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe prototipos\\animar_mur_realista.py --limite 6 --px 700
    .venv\\Scripts\\python.exe prototipos\\animar_mur_realista.py --px 1200 --armar
    .venv\\Scripts\\python.exe prototipos\\animar_mur_realista.py --help
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "prototipos"))
sys.path.insert(0, str(RAIZ / "comun"))

import poster_mur_realista as P  # noqa: E402
from rutas import SALIDAS  # noqa: E402

RE_FRAMES = re.compile(
    r"frames_mur_globo_(\d{4}-\d{2}-\d{2})T(\d{2})(\d{2})_(\d+)f_(\d+)px")


def elegir_frames(explicito: str | None) -> Path:
    """Carpeta de crudos MUR: la indicada o la serie semanal más reciente."""
    if explicito:
        p = Path(explicito)
        if not p.is_dir():
            raise SystemExit(f"No existe la carpeta de frames: {p}")
        return p
    carpetas = sorted(SALIDAS.glob("frames_mur_globo_*"),
                      key=lambda d: d.stat().st_mtime)
    if not carpetas:
        raise SystemExit(f"No hay frames MUR bajo {SALIDAS}.")
    return carpetas[-1]


def fechas_de_serie(frames_dir: Path, crudos: list[Path],
                    paso_dias: int) -> tuple[datetime, list[datetime]]:
    """Fecha del primer cuadro y una fecha por crudo.

    El nombre de la carpeta codifica `t0`; la cadencia no, así que se toma de
    `--paso-dias` (7 por defecto, la serie semanal de MUR). Si el nombre no matchea,
    se usa el mtime del primer crudo y se avanza con el mismo paso.
    """
    m = RE_FRAMES.search(frames_dir.name)
    if m:
        t0 = datetime.strptime(f"{m.group(1)} {m.group(2)}:{m.group(3)}",
                               "%Y-%m-%d %H:%M")
    else:
        t0 = datetime.fromtimestamp(crudos[0].stat().st_mtime)
    return t0, [t0 + timedelta(days=paso_dias * i) for i in range(len(crudos))]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Anima el póster realista de MUR (globo + campana por cuadro).")
    ap.add_argument("--frames", help="carpeta de frames_mur_globo_* de origen")
    ap.add_argument("--out", help="carpeta de cuadros de salida")
    ap.add_argument("--px", type=int, default=1200,
                    help="diámetro del globo en píxeles (por defecto 1200)")
    ap.add_argument("--dpi", type=int, help="dpi; si se omite se deduce de --px")
    ap.add_argument("--base-px", type=int, default=2048,
                    help="ancho del raster de trabajo (por defecto 2048)")
    ap.add_argument("--centro", nargs=2, type=float, metavar=("LON", "LAT"),
                    default=[-125.0, 0.0], help="centro del globo")
    ap.add_argument("--paleta", choices=("realista", "gibs"), default="realista")
    ap.add_argument("--paso-dias", type=int, default=7,
                    help="días entre cuadros (por defecto 7: serie semanal)")
    ap.add_argument("--limite", type=int,
                    help="renderizar sólo los primeros N cuadros (prueba)")
    ap.add_argument("--forzar", action="store_true",
                    help="re-renderizar aunque el cuadro ya exista")
    ap.add_argument("--credito", default="Graphic by @Gillo97")
    ap.add_argument("--trend", action="store_true",
                    help="agregar marca de la media y mini trend de mu/p95")
    ap.add_argument("--fps", type=float, default=10.0,
                    help="fps para el MP4 si se usa --armar")
    ap.add_argument("--armar", action="store_true",
                    help="armar el MP4 al terminar (usa animar/armar.py)")
    args = ap.parse_args(argv)

    frames_dir = elegir_frames(args.frames)
    crudos = sorted(frames_dir.glob("crudo_*.jpg"))
    if not crudos:
        raise SystemExit(f"No hay crudo_*.jpg en {frames_dir}.")
    if args.limite:
        crudos = crudos[:args.limite]
    t0, fechas = fechas_de_serie(frames_dir, crudos, args.paso_dias)

    if args.base_px % 2:
        args.base_px += 1
    ancho_trabajo = min(args.base_px, 8192)

    etiqueta = "trend_" if args.trend else ""
    out_dir = Path(args.out) if args.out else (
        SALIDAS / f"frames_poster_mur_realista_{etiqueta}{t0:%Y-%m-%dT%H%M}_"
                  f"{len(crudos)}f_{args.px}px")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Insumos estáticos: se cargan una sola vez para toda la serie.
    P.CACHE.mkdir(parents=True, exist_ok=True)
    base_path = P.CACHE / f"base_{ancho_trabajo}.jpg"
    legend_path = P.CACHE / "legend_mur.png"
    P._bajar(P._url_base(t0, ancho_trabajo), base_path)
    P._bajar(P.LEGEND_URL, legend_path, min_bytes=1000)

    base = P.cargar_rgb(base_path, ancho_trabajo)
    tierra = P.mascara_tierra(base.shape[:2])
    cols, vals = P.paleta_gibs(legend_path)
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("sst_anomaly", P.COOL_WARM)
    ns = SimpleNamespace(dpi=args.dpi, px=args.px, credito=args.credito)

    serie = None
    if args.trend:
        print(f"Calculando trend de {len(crudos)} cuadros...", flush=True)
        serie = P.estadisticas_serie(crudos, tierra, cols, vals, ancho_trabajo)

    print(f"Serie: {frames_dir.name}")
    print(f"{len(crudos)} cuadros | inicio {t0:%Y-%m-%d %H:%M} UTC | "
          f"paso {args.paso_dias} d | globo {args.px} px")
    print(f"Salida: {out_dir}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    for i, (crudo, fecha) in enumerate(zip(crudos, fechas), 1):
        destino = out_dir / f"cuadro_{i:03d}.png"
        if (destino.exists() and not args.forzar
                and destino.stat().st_mtime >= crudo.stat().st_mtime):
            print(f"  {i}/{len(crudos)} ya existe", flush=True)
            continue
        data = P.cargar_rgb(crudo, ancho_trabajo)
        comp, cmap_usada, stats = P.componer(
            data, base, tierra, args.paleta == "realista", cols, vals, cmap)
        disco = P.warp_ortho(comp, tuple(args.centro), args.px)
        fig, _ = P.dibujar(disco, tuple(args.centro), fecha, cmap_usada,
                           stats, ns, serie=serie, idx=i - 1)
        parcial = destino.with_name(destino.stem + ".parcial.png")
        fig.savefig(parcial, format="png", facecolor=P.WHITE)
        plt.close(fig)
        parcial.replace(destino)
        print(f"  {i}/{len(crudos)} listo | {fecha:%Y-%m-%d} | "
              f"media {stats['mu']:+.2f} C", flush=True)

    print(f"{len(crudos)} cuadros en {out_dir}")
    if args.armar:
        cmd = [sys.executable, str(RAIZ / "animar" / "armar.py"),
               "--frames", str(out_dir), "--fps", str(args.fps)]
        print("Armando MP4...")
        subprocess.run(cmd, check=True)
    else:
        print("Armá el MP4 con: "
              f".venv\\Scripts\\python.exe animar\\armar.py --frames \"{out_dir}\" "
              f"--fps {args.fps:g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
