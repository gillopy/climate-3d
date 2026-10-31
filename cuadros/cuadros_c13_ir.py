"""Renderiza la banda 13 (infrarrojo 10.3 µm) de GOES-19 en globo Orthographic.

Usa el **formato de póster de los productos ECMWF** (precipitación, anomalía y viento):
- texto con escala sublineal (`esc`) y halo, para que se lea sobre el globo sin
  superponerse (el póster viejo, de tamaño fijo, se pisaba a 2712 px);
- barra de color sobre una pastilla oscura, con la unidad a la derecha;
- aro exterior y viñeta hacia el limbo, que le dan volumen al disco;
- el globo recortado a un **círculo completo** (con las esquinas en fondo), no el disco
  desbordado del póster anterior.

Además mantiene la **marca de agua en el medio** del disco, como en el póster de
referencia.

No toca la red: lee los `.nc` locales que deja `descargar/descargar_goes.py`. Cada lote
de cuadros corre en su propio proceso, así la RAM de un cuadro no se acumula con el
siguiente.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe cuadros\\cuadros_c13_ir.py --desde 2026-10-19T00:00 --n 388
    .venv\\Scripts\\python.exe cuadros\\cuadros_c13_ir.py --solo-poster --desde 2026-10-21T16:00
    .venv\\Scripts\\python.exe cuadros\\cuadros_c13_ir.py --help   # no toca la red
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
sys.path.insert(0, str(RAIZ / "prototipos"))
from goes_lectura import PATRON, cargar  # noqa: E402
from goes_descarga import clave_de  # noqa: E402
from poster_goes import IR_REALCE_CMAP, PALETTES  # noqa: E402
from rutas import DATOS, SALIDAS  # noqa: E402
from estilo import BG, TXT, TXT_DIM  # noqa: E402

SAT, BANDA = "G19", "C13"
TITULO = "G19 GOES-EAST · BRIGHTNESS TEMPERATURE · BAND 13 (10.3 µm)"
BORDE_SA = str(RAIZ / "datos" / "paraguay_gadm.json")
ESPESOR_BORDE_PY = 0.9

DESDE = "2026-10-19T00:00"
N = 388
PASO_MIN = 10
PX = 2712
DPI = 140
CENTRO = [-73.0, -18.0]            # centro aprobado en el cuaderno del 12-10
RADIO = 90.0                    # 90 = el disco completo entra en el círculo
CREDITO = "Graphic by @Gillo97"
VMIN, VMAX = None, None            # percentiles (0.5, 99.5) del primer cuadro


def carpeta_datos(sat: str = SAT, banda: str = BANDA) -> Path:
    return DATOS / f"goes_c{banda[1:].lower()}_{sat.lower()}"


def slot_map(datos: Path) -> dict:
    """(fecha, hora, minuto) -> ruta del `.nc` (según el inicio de escaneo)."""
    m = {}
    for f in datos.glob("*.nc"):
        mm = PATRON.search(f.name)
        if not mm:
            continue
        s = mm.group("s")
        dt = (datetime(int(s[:4]), 1, 1)
              + timedelta(days=int(s[4:7]) - 1, hours=int(s[7:9]), minutes=int(s[9:11])))
        m[(dt.date(), dt.hour, dt.minute)] = f
    return m


def _borde_geojson(ax, ruta, color, ancho):
    """Contorno destacado (Paraguay) sobre el globo."""
    if not ruta:
        return None
    import json as _json
    from matplotlib.collections import LineCollection
    import cartopy.crs as ccrs
    try:
        gj = _json.load(open(ruta, encoding="utf-8"))
    except Exception as exc:
        print(f"AVISO: borde omitido ({exc})")
        return None
    feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
    segs = []
    for f in feats:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            for ring in poly:
                segs.append(np.asarray(ring, dtype=float))
    if not segs:
        return None
    return ax.add_collection(LineCollection(segs, transform=ccrs.PlateCarree(),
                                            colors=color, linewidths=ancho, zorder=5))


def render_globo(campo, x, y, proj, rot, vmin: float, vmax: float,
                 args, destino: Path) -> Path:
    """Dibuja un cuadro completo (globo + vestuario) y lo guarda en `destino`."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import matplotlib.patheffects as patheffects
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    lon0, lat0 = args.centro
    lado_fig = args.px / args.dpi
    fig = plt.figure(figsize=(lado_fig, lado_fig), dpi=args.dpi)
    fig.patch.set_facecolor(BG)

    ax = fig.add_axes([0.014, 0.014, 0.972, 0.972],
                      projection=ccrs.Orthographic(central_longitude=lon0,
                                                   central_latitude=lat0))
    ax.set_facecolor(BG)
    ax.spines["geo"].set_visible(False)

    # Encuadre: el disco completo del hemisferio, DESBORDANDO el cuadro (como en el
    # póster de referencia): no se recorta a un círculo, se muestra entero y el marco
    # lo corta por los bordes. `set_global` deja el hemisferio entero en la vista.
    if args.radio >= 90.0:
        ax.set_global()
    else:
        # Con `--radio` menor se recorta a una cúpula: `R` (radio del hemisferio) hay
        # que leerlo ANTES de achicar la vista, porque después devuelve el nuevo.
        R = float(ax.projection.x_limits[1])
        r_m = R * math.sin(math.radians(args.radio))
        ax.set_xlim(-r_m, r_m)
        ax.set_ylim(-r_m, r_m)

    # El campo viene en proyección geostacionaria: `pcolormesh` lo reproyecta al
    # Orthographic del eje (no hace falta warp previo ni scipy).
    mesh = ax.pcolormesh(x, y, campo, transform=proj,
                         cmap=PALETTES.get(args.paleta, IR_REALCE_CMAP),
                         vmin=vmin, vmax=vmax, shading="auto", zorder=2)

    try:
        ax.add_feature(cfeature.COASTLINE.with_scale("110m"), linewidth=0.5,
                       edgecolor="#0b0b0b", zorder=4)
        ax.add_feature(cfeature.BORDERS.with_scale("110m"), linewidth=0.35,
                       edgecolor="#0b0b0b", linestyle=":", zorder=4)
    except Exception as exc:
        print(f"AVISO: costas/fronteras omitidas ({exc})")
    if args.geojson:
        _borde_geojson(ax, args.geojson, "#ffffff", ESPESOR_BORDE_PY)

    # --------------------------------------------------------------- vestuario
    # Estructura de tres líneas como los ECMWF: título (mes y año), fecha/hora del
    # cuadro y rótulo del producto. El halo detrás de cada línea es lo que permite
    # leerlas sobre el globo sin que se pisen entre sí.
    esc = 0.8 * (args.px / 720.0) ** 0.45
    halo = [patheffects.withStroke(linewidth=3.2 * esc, foreground=BG)]
    titulo, subtitulo, fuente, datos, tiempo = rot
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

    # Barra de color horizontal sobre una pastilla oscura traslúcida, para que los
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
    ticks = list(range(math.ceil(vmin / 10) * 10, int(vmax), 10))
    cbar.set_ticks(ticks)
    cbar.ax.tick_params(colors=TXT, length=3, width=0.8,
                        labelsize=max(6.5, 8.8 * esc), pad=2)
    fig.text(0.916, 0.0635, "°C", color=TXT,
             fontsize=max(7.0, 9.8 * esc), fontweight="bold",
             ha="left", va="center", zorder=11)

    # Marca de agua en el medio del disco, como en el póster de referencia: gris
    # apagado, delgada y espaciada. Sin borde ni trazo (que la volvían un sello) y sin
    # negrita: tiene que insinuar la firma, no tapar el mapa.
    if args.credito:
        fig.text(0.5, 0.150, " ".join(args.credito.upper()), color="#7c8698",
                 fontsize=8.5 * esc, ha="center", va="bottom", zorder=11)

    fig.text(0.026, 0.012, fuente, color=TXT_DIM, fontsize=7.4 * esc,
             ha="left", va="bottom")
    fig.text(0.980, 0.012, datos, color=TXT_DIM, fontsize=7.4 * esc,
             ha="right", va="bottom")
    # Guardado atómico: nunca queda un PNG truncado que después se reutilice.
    parcial = destino.with_suffix(".png.parcial")
    fig.savefig(parcial, format="png", facecolor=BG)
    ax.cla()
    plt.close(fig)
    del fig, ax, mesh
    gc.collect()
    parcial.replace(destino)
    return destino


def _re_descargar(nc: Path) -> Path:
    """Vuelve a bajar de S3 un `.nc` que quedó truncado (y lo reemplaza)."""
    import shutil
    import urllib.request
    from datetime import datetime as _dt

    m = PATRON.search(nc.name)
    s = m.group("s")
    t = (_dt(int(s[:4]), 1, 1)
         + timedelta(days=int(s[4:7]) - 1, hours=int(s[7:9]), minutes=int(s[9:11])))
    clave = clave_de(SAT, BANDA, t)
    tmp = nc.with_suffix(".nc.parcial")
    with urllib.request.urlopen(f"https://noaa-goes19.s3.amazonaws.com/{clave}",
                               timeout=300) as r, open(tmp, "wb") as fh:
        shutil.copyfileobj(r, fh, 1 << 20)
    nc.unlink()
    tmp.replace(nc)
    return nc


def _render_cuadro(nc: Path, destino: Path, args) -> None:
    """Renderiza un cuadro, degradando la resolución sólo si no hay otra forma.

    El `pcolormesh` de cartopy reproyecta un punto por vértice de la malla: a
    2712 px son 7,4 M puntos y el transform necesita cientos de MB. Con poca RAM
    libre eso revienta. Primero se insiste con la misma resolución (la RAM libre
    oscila: cuando otra app la suelta, entra) y sólo si no hay forma se pasa a una
    malla más fina. El `--tope` sólo cambia cuántas filas del `.nc` se leen, no el
    tamaño del PNG de salida.
    """
    topes = [args.tope]
    for t in (2034, 1356, 900):
        if t < args.tope:
            topes.append(t)
    for intento, tope in enumerate(topes):
        for reintento in range(3):
            try:
                campo, x, y, proj, unidad, rot = cargar(nc, tope_px=tope,
                                                        escena="FULL DISK")
                render_globo(campo, x, y, proj, rot, args.vmin, args.vmax, args, destino)
                del campo
                gc.collect()
                return
            except MemoryError:
                gc.collect()
                if reintento < 2:
                    print(f"  {nc.name[-40:]}: sin RAM para tope {tope}, "
                          f"se reintenta en 25 s", flush=True)
                    time.sleep(25)
                    continue
                siguiente = topes[min(intento + 1, len(topes) - 1)]
                print(f"  {nc.name[-40:]}: sin RAM para tope {tope}, se prueba con "
                      f"{siguiente}", flush=True)
                break
            except Exception as exc:
                # `.nc` truncado o ilegible: se re-baja de S3 y se reintenta.
                print(f"  {nc.name[-40:]}: {type(exc).__name__}, se re-baja de S3",
                      flush=True)
                try:
                    _re_descargar(nc)
                except Exception as exc2:
                    raise SystemExit(f"No se pudo recuperar {nc.name}: {exc2}")
                gc.collect()
                break
    raise SystemExit(f"No se pudo renderizar {nc.name} con {args.tope} px de campo.")


def _sello_render(args) -> str:
    """Huella de los parámetros que cambian el aspecto; invalida cuadros viejos."""
    import hashlib
    datos = {
        "px": args.px, "dpi": args.dpi, "centro": list(args.centro),
        "radio": args.radio, "credito": args.credito, "sat": args.sat,
        "vmin": args.vmin, "vmax": args.vmax, "borde": args.geojson,
        "paleta": args.paleta,
    }
    return hashlib.sha256(json.dumps(datos, sort_keys=True).encode()).hexdigest()[:16]


def _slots(datos: Path, t0: datetime, n: int, paso: int) -> list[datetime]:
    """Instantes con `.nc` local, en orden (la numeración de los cuadros es corrida)."""
    sl_map = slot_map(datos)
    out = []
    t = t0
    for _ in range(n):
        if (t.date(), t.hour, t.minute) in sl_map:
            out.append(t)
        t += timedelta(minutes=paso)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Globo Orthographic de la banda 13 (IR 10.3 µm) de GOES-19, con el "
                    "formato de póster de los productos ECMWF.")
    ap.add_argument("--sat", default=SAT,
                    help=f"satélite, p. ej. G16 o G19 (por defecto {SAT})")
    ap.add_argument("--desde", default=DESDE, help="primer cuadro, UTC")
    ap.add_argument("--n", type=int, default=N, help="cantidad de cuadros")
    ap.add_argument("--paso", type=int, default=PASO_MIN, help="minutos entre cuadros")
    ap.add_argument("--px", type=int, default=PX, help="lado del cuadro en píxeles")
    ap.add_argument("--dpi", type=int, default=DPI, help="dpi del render")
    ap.add_argument("--centro", nargs=2, type=float, metavar=("LON", "LAT"),
                    default=list(CENTRO), help="centro del globo")
    ap.add_argument("--radio", type=float, default=RADIO,
                    help="grados al borde del disco; 90 = el disco completo en el círculo")
    ap.add_argument("--credito", default=CREDITO, help="crédito de la esquina")
    ap.add_argument("--vmin", type=float, default=VMIN, help="mínimo de la escala (°C)")
    ap.add_argument("--vmax", type=float, default=VMAX, help="máximo de la escala (°C)")
    ap.add_argument("--paleta", default="ir_realce", choices=sorted(PALETTES),
                    help="paleta de color (default: ir_realce, la histórica)")
    ap.add_argument("--geojson", default=BORDE_SA,
                    help="contorno destacado (GeoJSON); vacío = sin borde, p. ej. --geojson \"\"")
    ap.add_argument("--tope", type=int, default=2712,
                    help="resolución del campo leído del .nc (default: igual a --px)")
    ap.add_argument("--datos", help="carpeta de los .nc (default: la del satélite/banda)")
    ap.add_argument("--out", help="carpeta de salida (default: comun.rutas.SALIDAS)")
    ap.add_argument("--frames", help="carpeta de cuadros (default: frames_<etiqueta>)")
    ap.add_argument("--lote", type=int, default=8,
                    help="cuadros por proceso (cada lote corre en su propio proceso)")
    ap.add_argument("--solo-poster", action="store_true",
                    help="renderiza sólo el póster del último cuadro")
    ap.add_argument("--forzar", action="store_true",
                    help="vuelve a renderizar aunque los PNG ya existan")
    ap.add_argument("--rango", nargs=2, type=int, metavar=("S", "E"),
                    help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    if not (0.0 < args.radio <= 90.0):
        raise SystemExit(f"--radio debe estar en (0, 90] (recibí {args.radio}).")

    t0 = datetime.fromisoformat(args.desde)
    datos = Path(args.datos) if args.datos else carpeta_datos(args.sat)
    if not datos.exists():
        raise SystemExit(f"No existe {datos}. Bajá los .nc con "
                         "descargar/descargar_goes.py.")
    sl_map = slot_map(datos)
    if not sl_map:
        raise SystemExit(f"No hay .nc en {datos}.")

    slots = _slots(datos, t0, args.n, args.paso)
    if not slots:
        raise SystemExit("Ninguno de los slots pedidos tiene .nc local.")

    salida = Path(args.out) if args.out else SALIDAS
    salida.mkdir(parents=True, exist_ok=True)
    etiqueta = f"{args.sat}_C13_{slots[0]:%Y-%m-%dT%H%M}_{len(slots)}f_{args.px}px"
    frames_dir = Path(args.frames) if args.frames else salida / f"frames_{etiqueta}"
    frames_dir.mkdir(parents=True, exist_ok=True)

    # La escala se calcula una vez, sobre el primer cuadro (percentiles 0.5/99.5, como
    # en el cuaderno del 12-10) y se aplica a todos: así la barra no salta entre cuadros.
    if args.vmin is None or args.vmax is None:
        t = slots[0]
        campo, *_ = cargar(sl_map[(t.date(), t.hour, t.minute)], tope_px=args.tope,
                           escena="FULL DISK")
        lo, hi = np.nanpercentile(campo, [0.5, 99.5])
        args.vmin = float(lo)
        args.vmax = float(hi)
        del campo
        gc.collect()
        print(f"escala: {args.vmin:.1f} a {args.vmax:.1f} °C", flush=True)

    # Modo lote (interno): renderiza el rango y sale. Cada proceso es independiente,
    # así la RAM de un cuadro no se acumula con el siguiente.
    if args.rango:
        s, e = args.rango
        for i in range(s, e + 1):
            t = slots[i - 1]
            destino = frames_dir / f"cuadro_{i:03d}.png"
            if destino.exists() and not args.forzar:
                continue
            nc = sl_map[(t.date(), t.hour, t.minute)]
            _render_cuadro(nc, destino, args)
        return 0

    if args.solo_poster:
        t = slots[-1]
        campo, x, y, proj, unidad, rot = cargar(sl_map[(t.date(), t.hour, t.minute)],
                                                tope_px=args.tope, escena="FULL DISK")
        poster = salida / f"poster_{args.sat}_C13_{t:%Y-%m-%dT%H%M}.png"
        render_globo(campo, x, y, proj, rot, args.vmin, args.vmax, args, poster)
        print(f"Póster: {poster}")
        return 0

    # El sello invalida los cuadros viejos si cambió el aspecto.
    sello = _sello_render(args)
    archivo_sello = frames_dir / ".sello_render"
    previo = (archivo_sello.read_text(encoding="utf-8").strip()
              if archivo_sello.exists() else None)
    if previo is not None and previo != sello and not args.forzar:
        print("Cambiaron los parámetros de render -> se rehacen los cuadros")
        args.forzar = True
    archivo_sello.write_text(sello, encoding="utf-8")

    print(f"{args.sat} C13 | {len(slots)} cuadros desde {slots[0]:%Y-%m-%d %H:%M} UTC | "
          f"{args.px}x{args.px} px | radio {args.radio:g}° | frames en {frames_dir}",
          flush=True)

    # Cada lote corre en su propio proceso: la RAM de un cuadro (el .nc leído y la malla
    # reproyectada) no se acumula entre cuadros.
    import subprocess
    t_inicio = time.time()
    for s in range(1, len(slots) + 1, args.lote):
        e = min(s + args.lote - 1, len(slots))
        cmd = [sys.executable, str(Path(__file__).resolve()),
               *sys.argv[1:], "--rango", str(s), str(e),
               "--vmin", str(args.vmin), "--vmax", str(args.vmax)]
        subprocess.run(cmd, check=True)
        print(f"  lote {s}-{e} ok ({time.time() - t_inicio:.0f}s)", flush=True)

    print(f"Cuadros en {frames_dir}")
    print(f"Armá el video con: .venv\\Scripts\\python.exe animar\\armar.py "
          f"--frames \"{frames_dir}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
