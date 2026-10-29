"""Renderiza la banda 13 (infrarrojo 10.4 µm) del AHI de Himawari-9 en globo Orthographic.

Es el gemelo de `cuadros/cuadros_c13_ir.py` (GOES-19 ABI C13) pero con el
satelite de Asia: mismo formato de poster, misma parafernalia, y la **misma rampa
de color de NASA Worldview / GIBS** (`Clean_Longwave_Infrared_Window_Band`), que es
la que usan las capas `GOES-East_ABI_Band13_Clean_Infrared` y
`Himawari_AHI_Band13_Clean_Infrared`.

El foco por defecto es el **mar Filipino** (el ciclon de Taiwan entra en cuadro).

No toca la red: lee los `.npz` que deja `descargar/descargar_himawari.py`. Cada
lote de cuadros corre en su propio proceso, asi la RAM de un cuadro no se acumula
con el siguiente.

Uso (desde la raiz del proyecto):

    .venv\\Scripts\\python.exe cuadros\\cuadros_himawari_ir.py --desde 2026-10-20T04:00 --n 288
    .venv\\Scripts\\python.exe cuadros\\cuadros_himawari_ir.py --solo-poster --desde 2026-10-22T00:30
    .venv\\Scripts\\python.exe cuadros\\cuadros_himawari_ir.py --help   # no toca la red
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
sys.path.insert(0, str(RAIZ / "descargar"))
from paleta_gibs import CMAP_GIBS_CLEAN_IR, VMAX as VMAX_GIBS, VMIN as VMIN_GIBS  # noqa: E402
from rutas import DATOS, SALIDAS  # noqa: E402
from estilo import BG, TXT, TXT_DIM  # noqa: E402

SAT, BANDA = "H09", 13
TITULO = "H09 HIMAWARI-9 · BRIGHTNESS TEMPERATURE · BAND 13 (10.4 µm)"
FUENTE = "Source: JMA Himawari Standard Data (HSD) via NOAA Open Data"
DATOS_ROT = "AHI L1b FLDK R20 (2 km) · 10 min"

#: Paraguay es UTC-4 todo el ano (no cambia el horario de verano).
ZONA = timedelta(hours=-4)
ZONA_NOMBRE = "UTC-4"

DESDE = "2026-10-20T04:00"
N = 288
PASO_MIN = 10
PX = 2712
DPI = 140
CENTRO = [133.0, 17.0]          # mar Filipino: el ciclon de Taiwan entra en cuadro
RADIO = 90.0                    # 90 = el disco completo entra en el circulo
CREDITO = "Graphic by @Gillo97"
VMIN, VMAX = VMIN_GIBS, VMAX_GIBS   # -92.1 .. 56.9 C (rango de la rampa GIBS)
#: Radio del limbo de la Tierra en el plano geostacionario (km). La grilla del
#: disco completo del AHI es un cuadrado de 11.000 km, mas grande que el disco
#: visible: fuera del limbo no hay observacion y hay que cortar.
RADIO_LIMBO_KM = 5400.0


def carpeta_datos(sat: str = SAT, banda: int = BANDA) -> Path:
    return DATOS / f"himawari_b{banda:02d}_{sat.lower()}"


def listar_slots(datos: Path) -> list[tuple[datetime, Path]]:
    """Slots disponibles en la carpeta, en orden cronologico."""
    salida = []
    for f in sorted(datos.glob("*.npz")):
        m = f.stem
        if len(m) != 13 or not (m[:8].isdigit() and m[9:].isdigit()):
            continue
        t = datetime(int(m[:4]), int(m[4:6]), int(m[6:8]), int(m[9:11]), int(m[11:13]))
        salida.append((t, f))
    return salida


def _mask_limbo(campo: np.ndarray, x: np.ndarray, y: np.ndarray,
               radio_km: float = RADIO_LIMBO_KM) -> np.ndarray:
    """Borra el anillo que queda fuera del limbo de la Tierra.

    La grilla del disco completo del AHI es un cuadrado de 11.000 km de lado, pero
    la Tierra visible desde el satelite solo ocupa un disco de radio ~5.416 km en
    el plano geostacionario (el limbo). Fuera de ese disco no hay observacion:
    JMA deja los pixeles saturados (cuenta ~4050), y al invertirlos aparecen valores
    de -150 C que en el render se ven como un peine de picos de color en el borde.
    Con esta mascara el disco queda limpio y con el borde real de la Tierra.

    Se hace por broadcasting (sin `meshgrid`): dos matrices completas de 2750 x
    2750 en float64 son 120 MB que esta maquina no tiene.
    """
    lim2 = np.float32(radio_km * 1000.0) ** 2
    fuera = (x[:, None] ** 2 + y[None, :] ** 2) > lim2
    campo[fuera] = np.nan
    return campo


def cargar(npz: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """Carga un slot: `(campo_C, x_m, y_m, meta)`."""
    with np.load(npz) as d:
        campo = np.asarray(d["tb"], dtype=np.float32)
        n = campo.shape[0]
        x = (d["x0"] + d["dx"] * np.arange(n)).astype(np.float32)
        y = (d["y0"] + d["dy"] * np.arange(n)).astype(np.float32)
        meta = {k: float(d[k]) for k in ("x0", "y0", "dx", "dy", "sub_lon", "a", "b", "h")}
    return _mask_limbo(campo, x, y), x, y, meta


def render_globo(campo, x, y, meta, rot, args, destino: Path,
                 tope: int | None = None) -> Path:
    """Dibuja un cuadro completo (globo + vestuario) y lo guarda en `destino`.

    `tope` limita la resolucion del campo que se reproyecta: el `pcolormesh` de
    cartopy reproyecta un vertice por punto de la malla, y a 2750 x 2750 son
    7,6 millones de vertices (cientos de MB). Si la RAM no alcanza, se prueba
    con una malla mas fina (el PNG de salida no cambia de tamano).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import matplotlib.patheffects as patheffects
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    if tope and tope < campo.shape[0]:
        paso = int(np.ceil(campo.shape[0] / tope))
        campo = campo[::paso, ::paso]
        x = x[::paso]
        y = y[::paso]

    lon0, lat0 = args.centro
    lado_fig = args.px / args.dpi
    fig = plt.figure(figsize=(lado_fig, lado_fig), dpi=args.dpi)
    fig.patch.set_facecolor(BG)

    ax = fig.add_axes([0.014, 0.014, 0.972, 0.972],
                      projection=ccrs.Orthographic(central_longitude=lon0,
                                                   central_latitude=lat0))
    ax.set_facecolor(BG)
    ax.spines["geo"].set_visible(False)

    if args.radio >= 90.0:
        ax.set_global()
    else:
        R = float(ax.projection.x_limits[1])
        r_m = R * math.sin(math.radians(args.radio))
        ax.set_xlim(-r_m, r_m)
        ax.set_ylim(-r_m, r_m)

    # El campo viene en proyeccion geostacionaria (JMA/CGMS): `pcolormesh` lo
    # reproyecta al Orthographic del eje (no hace falta warp previo ni scipy).
    fuente = ccrs.Geostationary(
        central_longitude=meta["sub_lon"],
        satellite_height=meta["h"],
        false_easting=0, false_northing=0,
        globe=ccrs.Globe(ellipse="WGS84"),
    )
    mesh = ax.pcolormesh(x, y, campo, transform=fuente, cmap=CMAP_GIBS_CLEAN_IR,
                         vmin=args.vmin, vmax=args.vmax, shading="auto", zorder=2)

    try:
        ax.add_feature(cfeature.COASTLINE.with_scale("110m"), linewidth=0.5,
                       edgecolor="#0b0b0b", zorder=4)
        ax.add_feature(cfeature.BORDERS.with_scale("110m"), linewidth=0.35,
                       edgecolor="#0b0b0b", linestyle=":", zorder=4)
    except Exception as exc:
        print(f"AVISO: costas/fronteras omitidas ({exc})")

    # --------------------------------------------------------------- vestuario
    # Estructura de tres lineas como los ECMWF: titulo, fecha/hora del cuadro y
    # rotulo del producto. El halo detras de cada linea es lo que permite
    # leerlas sobre el globo sin que se pisen entre si.
    esc = 0.8 * (args.px / 720.0) ** 0.45
    halo = [patheffects.withStroke(linewidth=3.2 * esc, foreground=BG)]
    titulo, subtitulo, fuente_txt, datos_txt, tiempo = rot
    fig.text(0.026, 0.985, titulo, color=TXT,
             fontsize=19 * esc, fontweight="bold", ha="left", va="top",
             path_effects=halo, zorder=11)
    fig.text(0.026, 0.946, tiempo.upper(), color=TXT,
             fontsize=13.5 * esc, fontweight="bold", ha="left", va="top",
             path_effects=halo, zorder=11)
    fig.text(0.026, 0.912, subtitulo, color=TXT_DIM, fontsize=11.5 * esc,
             fontweight="bold", ha="left", va="top", linespacing=1.15,
             path_effects=halo, zorder=11)
    fig.text(0.983, 0.983, args.credito, color=TXT_DIM, fontsize=12 * esc,
             ha="right", va="top", path_effects=halo, zorder=11)

    # Barra de color horizontal sobre una pastilla oscura traslucida, para que los
    # ticks se lean limpios sobre el borde del globo.
    fondo_cbar = mpatches.FancyBboxPatch(
        (0.050, 0.030), 0.900, 0.055,
        boxstyle="round,pad=0.006,rounding_size=0.010",
        transform=fig.transFigure, facecolor=(0.047, 0.063, 0.078, 0.86),
        edgecolor="#2a3442", linewidth=0.8, zorder=9,
    )
    fig.add_artist(fondo_cbar)
    cax = fig.add_axes([0.066, 0.055, 0.822, 0.017], zorder=10)
    cbar = fig.colorbar(mesh, cax=cax, orientation="horizontal")
    cbar.outline.set_visible(False)
    ticks = list(range(math.ceil(args.vmin / 20) * 20, int(args.vmax), 20))
    cbar.set_ticks(ticks)
    cbar.ax.tick_params(colors=TXT, length=3, width=0.8,
                        labelsize=max(6.5, 8.8 * esc), pad=2)
    fig.text(0.916, 0.0635, "°C", color=TXT,
             fontsize=max(7.0, 9.8 * esc), fontweight="bold",
             ha="left", va="center", zorder=11)

    # Marca de agua en el medio del disco, como en el poster de referencia: gris
    # apagado, delgada y espaciada. Sin borde ni trazo (que la volvian un sello) y sin
    # negrita: tiene que insinuar la firma, no tapar el mapa.
    if args.credito:
        fig.text(0.5, 0.150, " ".join(args.credito.upper()), color="#7c8698",
                 fontsize=8.5 * esc, ha="center", va="bottom", zorder=11)

    fig.text(0.026, 0.012, fuente_txt, color=TXT_DIM, fontsize=7.4 * esc,
             ha="left", va="bottom")
    fig.text(0.980, 0.012, datos_txt, color=TXT_DIM, fontsize=7.4 * esc,
             ha="right", va="bottom")
    # Guardado atomico: nunca queda un PNG truncado que despues se reutilice.
    parcial = destino.with_name(destino.name + ".parcial.png")
    fig.savefig(parcial, format="png", facecolor=BG)
    ax.cla()
    plt.close(fig)
    del fig, ax, mesh
    gc.collect()
    parcial.replace(destino)
    return destino


def _ram_libre_mb() -> int:
    """Memoria fisica libre del sistema, en MB (Windows)."""
    try:
        import ctypes

        class _Estado(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_uint32),
                        ("dwMemoryLoad", ctypes.c_uint32),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

        estado = _Estado()
        estado.dwLength = ctypes.sizeof(_Estado)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(estado))
        return int(estado.ullAvailPhys / (1 << 20))
    except Exception:
        return 999999


def _esperar_ram(mb: int = 1200, intentos: int = 8) -> None:
    """Espera a que se libere RAM antes de reproyectar un cuadro.

    El `pcolormesh` de cartopy necesita del orden de 700 MB para reproyectar la
    malla completa (2750 x 2750 -> 7,6 M vertices). Con la maquina llena el
    render se cae por `MemoryError`; esperando un poco la otra app suelta y el
    cuadro sale con la resolucion completa.
    """
    for _ in range(intentos):
        libre = _ram_libre_mb()
        if libre >= mb:
            return
        print(f"  RAM libre {libre} MB (< {mb} MB): se espera 30 s", flush=True)
        time.sleep(30)


def _render_cuadro(npz: Path, destino: Path, args, rot) -> None:
    """Renderiza un cuadro, degradando la resolucion del campo si no hay RAM.

    El `pcolormesh` de cartopy reproyecta un vertice por vertice de la malla: a
    2750 x 2750 son 7,6 M puntos y el transform necesita cientos de MB. Se
    insiste con la misma resolucion (la RAM libre oscila: cuando otra app la
    suelta, entra) y solo si no hay forma se pasa a una malla mas fina. El
    `--tope` solo cambia cuantas filas del campo se leen, no el tamano del PNG.
    """
    topes = [args.tope]
    for t in (1375, 900):
        if t < args.tope:
            topes.append(t)
    for intento, tope in enumerate(topes):
        for reintento in range(3):
            try:
                _esperar_ram()
                campo, x, y, meta = cargar(npz)
                render_globo(campo, x, y, meta, rot, args, destino, tope=tope)
                del campo
                gc.collect()
                return
            except MemoryError:
                gc.collect()
                if reintento < 2:
                    print(f"  {npz.name}: sin RAM para tope {tope}, "
                          f"se reintenta en 40 s", flush=True)
                    time.sleep(40)
                    continue
                siguiente = topes[min(intento + 1, len(topes) - 1)]
                print(f"  {npz.name}: sin RAM para tope {tope}, se prueba con "
                      f"{siguiente}", flush=True)
                break
    raise SystemExit(f"No se pudo renderizar {npz.name} con {args.tope} px de campo.")


def _sello_render(args) -> str:
    """Huella de los parametros que cambian el aspecto; invalida cuadros viejos."""
    import hashlib
    datos = {
        "px": args.px, "dpi": args.dpi, "centro": list(args.centro),
        "radio": args.radio, "credito": args.credito, "titulo": TITULO,
        "vmin": args.vmin, "vmax": args.vmax, "paleta": "gibs_clean_ir",
    }
    return hashlib.sha256(json.dumps(datos, sort_keys=True).encode()).hexdigest()[:16]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Globo Orthographic de la banda 13 (IR 10.4 µm) de Himawari-9, "
                    "con el formato de poster de los productos ECMWF y la rampa "
                    "Clean Infrared de NASA Worldview/GIBS.")
    ap.add_argument("--desde", default=DESDE, help="primer cuadro, UTC")
    ap.add_argument("--n", type=int, default=N, help="cantidad de cuadros")
    ap.add_argument("--paso", type=int, default=PASO_MIN, help="minutos entre cuadros")
    ap.add_argument("--px", type=int, default=PX, help="lado del cuadro en pixeles")
    ap.add_argument("--dpi", type=int, default=DPI, help="dpi del render")
    ap.add_argument("--centro", nargs=2, type=float, metavar=("LON", "LAT"),
                    default=list(CENTRO), help="centro del globo")
    ap.add_argument("--radio", type=float, default=RADIO,
                    help="grados al borde del disco; 90 = el disco completo en el circulo")
    ap.add_argument("--credito", default=CREDITO, help="credito de la esquina")
    ap.add_argument("--vmin", type=float, default=VMIN, help="minimo de la escala (°C)")
    ap.add_argument("--vmax", type=float, default=VMAX, help="maximo de la escala (°C)")
    ap.add_argument("--datos", help="carpeta de los .npz (default: la del satelite/banda)")
    ap.add_argument("--out", help="carpeta de salida (default: comun.rutas.SALIDAS)")
    ap.add_argument("--frames", help="carpeta de cuadros (default: frames_<etiqueta>)")
    ap.add_argument("--lote", type=int, default=8,
                    help="cuadros por proceso (cada lote corre en su propio proceso)")
    ap.add_argument("--tope", type=int, default=2750,
                    help="resolucion del campo reproyectado (default: igual al campo)")
    ap.add_argument("--solo-poster", action="store_true",
                    help="renderiza solo el poster del ultimo cuadro")
    ap.add_argument("--forzar", action="store_true",
                    help="vuelve a renderizar aunque los PNG ya existan")
    ap.add_argument("--rango", nargs=2, type=int, metavar=("S", "E"),
                    help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    if not (0.0 < args.radio <= 90.0):
        raise SystemExit(f"--radio debe estar en (0, 90] (recibi {args.radio}).")

    datos = Path(args.datos) if args.datos else carpeta_datos()
    if not datos.exists():
        raise SystemExit(f"No existe {datos}. Bajá los datos con "
                         "descargar/descargar_himawari.py.")
    disponibles = dict(listar_slots(datos))
    if not disponibles:
        raise SystemExit(f"No hay .npz en {datos}.")

    t0 = datetime.fromisoformat(args.desde)
    slots = []
    t = t0
    for _ in range(args.n):
        if t in disponibles:
            slots.append(t)
        t += timedelta(minutes=args.paso)
    if not slots:
        raise SystemExit("Ninguno de los slots pedidos tiene datos locales.")

    salida = Path(args.out) if args.out else SALIDAS
    salida.mkdir(parents=True, exist_ok=True)
    etiqueta = f"H09_B13_{slots[0]:%Y-%m-%dT%H%M}_{len(slots)}f_{args.px}px"
    frames_dir = Path(args.frames) if args.frames else salida / f"frames_{etiqueta}"
    frames_dir.mkdir(parents=True, exist_ok=True)

    def rotulo_de(t: datetime):
        local = t + ZONA
        mes = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY",
               "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"][local.month - 1]
        return (TITULO,
                f"{mes} {local:%Y} · HIMAWARI-9 AHI · CLEAN INFRARED",
                FUENTE,
                DATOS_ROT,
                f"{local:%Y-%m-%d %H:%M} {ZONA_NOMBRE}")

    # Modo lote (interno): renderiza el rango y sale. Cada proceso es independiente,
    # asi la RAM de un cuadro no se acumula con el siguiente.
    if args.rango:
        s, e = args.rango
        for i in range(s, e + 1):
            t = slots[i - 1]
            destino = frames_dir / f"cuadro_{i:03d}.png"
            if destino.exists() and not args.forzar:
                continue
            _render_cuadro(disponibles[t], destino, args, rotulo_de(t))
        return 0

    if args.solo_poster:
        t = slots[-1]
        campo, x, y, meta = cargar(disponibles[t])
        poster = salida / f"poster_H09_B13_{t:%Y-%m-%dT%H%M}.png"
        render_globo(campo, x, y, meta, rotulo_de(t), args, poster)
        print(f"Poster: {poster}")
        return 0

    # El sello invalida los cuadros viejos si cambio el aspecto.
    sello = _sello_render(args)
    archivo_sello = frames_dir / ".sello_render"
    previo = (archivo_sello.read_text(encoding="utf-8").strip()
              if archivo_sello.exists() else None)
    if previo is not None and previo != sello and not args.forzar:
        print("Cambiaron los parametros de render -> se rehacen los cuadros")
        args.forzar = True
    archivo_sello.write_text(sello, encoding="utf-8")

    print(f"H09 B13 | {len(slots)} cuadros desde {slots[0]:%Y-%m-%d %H:%M} UTC | "
          f"{args.px}x{args.px} px | radio {args.radio:g}° | frames en {frames_dir}",
          flush=True)

    # Cada lote corre en su propio proceso: la RAM de un cuadro (el campo leido y
    # la malla reproyectada) no se acumula entre cuadros.
    import subprocess
    t_inicio = time.time()
    for s in range(1, len(slots) + 1, args.lote):
        e = min(s + args.lote - 1, len(slots))
        cmd = [sys.executable, str(Path(__file__).resolve()),
               *sys.argv[1:], "--rango", str(s), str(e)]
        subprocess.run(cmd, check=True)
        print(f"  lote {s}-{e} ok ({time.time() - t_inicio:.0f}s)", flush=True)

    print(f"Cuadros en {frames_dir}")
    print(f"Arma el video con: .venv\\Scripts\\python.exe animar\\armar.py "
          f"--frames \"{frames_dir}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
