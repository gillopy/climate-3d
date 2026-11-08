"""Póster de UNA banda ABI con el diseño del color real.

Mismo encuadre, mismo fondo y mismos rótulos que `poster_goes_truecolor.py`
(fondo negro, globo inscripto, sin retícula ni costas), pero el disco no es un
compuesto RGB: es una banda cruda del ABI coloreada con una paleta.

    .venv\\Scripts\\python.exe prototipos\\poster_goes_banda.py --banda C13 --desde 2026-10-24T16:50
    .venv\\Scripts\\python.exe prototipos\\poster_goes_banda.py --banda C02 --paleta gris --px 2000
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from matplotlib import colormaps

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
sys.path.insert(0, str(RAIZ / "prototipos"))

import poster_goes_truecolor as tc  # noqa: E402
from goes_lectura import PATRON, cargar  # noqa: E402
from poster_goes import PALETTES  # noqa: E402
from poster_goes_realista import (  # noqa: E402
    _geo_scan,
    fecha_de,
    radio_visible,
    time_label_nc,
)
from rutas import SALIDAS  # noqa: E402

SAT = "G19"
BANDA = "C13"
CENTRO = (-75.2, 0.0)
PX = 2712
TOPE = 10848
#: Corte del planeta: fracción del radio del encuadre donde termina el disco
#: (igual que en los RGB). Todo lo de afuera no se muestra.
CORTE_PLANETA = 0.98
PALETA = "clean_ir"
VMIN, VMAX = -92.1, 56.9

#: Escala fija de las paletas oficiales (grados C). El color no se mueve con
#: los percentiles de cada cuadro: es la barra que publica la pagina de GOES.
ESCALAS_OFICIALES = {
    # Vapor de agua: una sola barra para las bandas 8 a 10.
    "c08_ir": (-93.0, 7.0),
    "c09_ir": (-93.0, 7.0),
    "c10_ir": (-93.0, 7.0),
    # Ventana IR: una sola barra para las bandas 11 a 15 (misma escala fija).
    "c11_ir": (-110.0, 57.0),
    "c12_ir": (-110.0, 57.0),
    "c13_ir": (-110.0, 57.0),
    "c14_ir": (-110.0, 57.0),
    "c15_ir": (-110.0, 57.0),
    # CO2: barra propia, mas ancha.
    "c16_ir": (-128.0, 128.0),
}

#: Bandas termicas (temperatura de brillo en C) frente a reflectancia (0..1).
TERMICAS = {"C07", "C08", "C09", "C10", "C11", "C12", "C13", "C14", "C15", "C16"}


def _lut(paleta: str) -> np.ndarray:
    """Colores de la paleta, para indexar sin alocar float por píxel.

    `PALETTES` mezcla colormaps armadas (clean_ir, anomalia, c16_ir) con
    nombres de matplotlib (gris, magma...): acá se resuelven los dos casos.
    Se muestrean `cmap.N` entradas (c16_ir trae 2048: 0.125 C por bin en
    su escala; las demás, 256): con 256 el degradado cálido de C16 entraba
    en 4 escalones.
    """
    cmap = PALETTES[paleta]
    if isinstance(cmap, str):
        cmap = colormaps[cmap]
    n = int(getattr(cmap, "N", 256))
    return (np.asarray(cmap(np.linspace(0.0, 1.0, n)))[:, :3] * 255.0).astype(np.uint8)


def slots(banda: str, sat: str, desde: datetime | None, n: int, paso: int,
          ultimos: int = 0):
    """Slots con `.nc` en disco.

    - `ultimos > 0`: los N más nuevos, terminando en el último que haya.
    - `desde`: serie que arranca en ese instante.
    - sin ninguno de los dos: el último cuadro.
    """
    encontrados: dict[datetime, Path] = {}
    for archivo in tc.carpeta(banda, sat).glob("*.nc"):
        match = PATRON.search(archivo.name)
        if not match or match["banda"] != banda or match["sat"] != sat:
            continue
        try:
            encontrados[fecha_de(archivo)] = archivo
        except Exception:  # noqa: BLE001 - nombre raro, se ignora
            continue
    if not encontrados:
        raise SystemExit(
            f"No hay .nc de {banda} de {sat} en {tc.carpeta(banda, sat)}. "
            "Bajalos con descargar/descargar_goes.py."
        )
    if ultimos > 0:
        n = ultimos
        t0 = max(encontrados) - timedelta(minutes=paso * (ultimos - 1))
    else:
        t0 = desde or max(encontrados)
    lista = []
    for i in range(n):
        instante = t0 + timedelta(minutes=paso * i)
        if instante in encontrados:
            lista.append((instante, encontrados[instante]))
    if not lista:
        raise SystemExit(f"Ninguno de los slots pedidos desde {t0:%Y-%m-%d %H:%M} tiene .nc.")
    return lista


def _muestrear_banda(campo, x, y, lon0: float, h: float, lon, lat):
    """Bilineal del campo (C o reflectancia) en el disco; NaN fuera del dato.

    `_muestrear` del true color no sirve aca: asume el plano cuantizado a uint16
    y descarta todo valor <= 0, lo que borraria las temperaturas bajo cero.
    """
    xs, ys = _geo_scan(lon, lat, lon0, h)
    dx = float(x[1] - x[0])
    dy = float(y[1] - y[0])
    col = (xs - float(x[0])) / dx
    fila = (ys - float(y[0])) / dy
    del xs, ys

    alto, ancho = campo.shape
    ok = (col >= 0) & (col <= ancho - 1) & (fila >= 0) & (fila <= alto - 1)
    c0 = np.clip(np.floor(col), 0, ancho - 2).astype(np.intp)
    f0 = np.clip(np.floor(fila), 0, alto - 2).astype(np.intp)
    fc = np.clip(col - c0, 0.0, 1.0).astype(np.float32)
    ff = np.clip(fila - f0, 0.0, 1.0).astype(np.float32)
    del col, fila

    v00, v01 = campo[f0, c0], campo[f0, c0 + 1]
    v10, v11 = campo[f0 + 1, c0], campo[f0 + 1, c0 + 1]
    valores = ((v00 * (1 - fc) + v01 * fc) * (1 - ff)
               + (v10 * (1 - fc) + v11 * fc) * ff)
    valido = (np.isfinite(v00) & np.isfinite(v01)
              & np.isfinite(v10) & np.isfinite(v11))
    return np.where(ok & valido, valores, np.nan).astype(np.float32)


def componer_banda(nc: Path, args) -> tuple[np.ndarray, float, dict]:
    """Banda -> RGBA del disco orthographic, con la misma geometría del true color."""
    # `cargar` devuelve el campo en unidades de display: C para las bandas
    # termicas, reflectancia 0..1 para las visibles. `_plano` del true color
    # devuelve reflectancia normalizada y no sirve para una banda cruda.
    import xarray as xr

    campo, x, y, _proj, _unidad, _rot = cargar(nc, tope_px=args.tope)
    with xr.open_dataset(nc, engine="h5netcdf") as ds:
        gp = ds["goes_imager_projection"].attrs
        h = float(gp["perspective_point_height"])
        lon0 = float(gp["longitude_of_projection_origin"])

    escala, _h, _lon0 = radio_visible(nc, tuple(args.centro), args.recorte)
    lut = _lut(args.paleta)
    px = args.px
    centro = tuple(args.centro)

    rgb = np.zeros((px, px, 3), dtype=np.uint8)
    alfa = np.zeros((px, px), dtype=np.uint8)
    validos = 0

    for f0 in range(0, px, tc.FILAS):
        f1 = min(f0 + tc.FILAS, px)
        lon, lat, rho, dentro = tc._orto_franja(px, escala, centro, f0, f1)
        valores = _muestrear_banda(campo, x, y, lon0, h, lon, lat)
        a = tc._alfa(rho, px, escala) * dentro
        # El corte va en el planeta, no en el marco: rampa analítica de
        # 1.5 px sobre el círculo de corte, sin dientes ni banda.
        a = a * tc._alfa(rho, px, 1.0 / CORTE_PLANETA)

        normalizado = np.clip((valores - args.vmin) / (args.vmax - args.vmin), 0.0, 1.0)
        n = len(lut)
        indice = (normalizado * (n - 1)).astype(np.uint16 if n > 256 else np.uint8)
        bloque = lut[indice]
        bloque[~np.isfinite(valores)] = 0

        rgb[f0:f1] = bloque
        alfa[f0:f1] = (a * 255.0).astype(np.uint8)
        validos += int(np.count_nonzero(a > 0))
        print(f"  franja {f1:5d}/{px}", flush=True)

    # Sin filo brillante: display bilineal en vez de lanczos (sin overshoot).
    args.interp = "bilinear"

    return np.dstack([rgb, alfa]), escala, {"px": px, "validos": validos}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Póster de una banda ABI con el diseño del color real.")
    ap.add_argument("--banda", default=BANDA, help=f"banda ABI (por defecto {BANDA})")
    ap.add_argument("--sat", default=SAT, help=f"satélite (por defecto {SAT})")
    ap.add_argument("--desde", help="slot UTC ISO (por defecto, el último con .nc)")
    ap.add_argument("--n", type=int, default=1, help="cantidad de cuadros")
    ap.add_argument("--ultimos", type=int, default=0, metavar="N",
                    help="los N cuadros más nuevos con .nc en disco (ignora --desde)")
    ap.add_argument("--paso", type=int, default=10, help="minutos entre cuadros")
    ap.add_argument("--px", type=int, default=PX, help=f"diámetro del globo (por defecto {PX})")
    ap.add_argument("--dpi", type=int, help="dpi; si se omite se deduce de --px")
    ap.add_argument("--tope", type=int, default=TOPE, help="grilla de origen de la banda")
    ap.add_argument("--centro", nargs=2, type=float, metavar=("LON", "LAT"),
                    default=list(CENTRO), help="centro del globo")
    ap.add_argument("--recorte", type=float, default=1.0,
                    help="fracción del radio visible (1 = disco completo)")
    ap.add_argument("--paleta", choices=sorted(PALETTES), default=PALETA)
    ap.add_argument("--vmin", type=float, default=VMIN, help="mínimo de la escala (°C)")
    ap.add_argument("--vmax", type=float, default=VMAX, help="máximo de la escala (°C)")
    ap.add_argument("--titulo", default=None, help="título del póster")
    ap.add_argument("--fuente", default=None, help="línea de fuente al pie")
    ap.add_argument("--credito", default="Graphic by @Gillo97")
    ap.add_argument("--limpio", action="store_true",
                    help="captura limpia: sin títulos, créditos, halo ni sombreado de borde")
    ap.add_argument("--fondo", choices=["claro", "oscuro"], default="oscuro")
    ap.add_argument("--lineas", action=argparse.BooleanOptionalAction, default=False,
                    help="retícula y costas (por defecto, no)")
    ap.add_argument("--fronteras", action=argparse.BooleanOptionalAction, default=False)
    ap.add_argument("--borde", nargs="?", const="", default="")
    ap.add_argument("--sombra-borde", type=float, default=0.18)
    ap.add_argument("--out", help="PNG de salida")
    ap.add_argument("--frames", help="carpeta de cuadros")
    ap.add_argument("--forzar", action="store_true")
    args = ap.parse_args(argv)

    if args.banda.upper() not in TERMICAS:
        # Reflectancia: las rampas termicas (GIBS y las oficiales) no aplican,
        # va en gris 0..1.
        if args.paleta == PALETA or args.paleta in ESCALAS_OFICIALES:
            args.paleta = "gris"
        if args.vmin == VMIN and args.vmax == VMAX:
            args.vmin, args.vmax = 0.0, 1.0

    if args.paleta in ESCALAS_OFICIALES and args.vmin == VMIN and args.vmax == VMAX:
        # Las barras oficiales tienen escala fija: sin esto, los mismos colores
        # caerian en otras temperaturas y no coincidirian con la pagina de GOES.
        args.vmin, args.vmax = ESCALAS_OFICIALES[args.paleta]

    if args.fondo == "oscuro":
        tc.WHITE = "#000000"
        tc.INK = "#eef2f5"
        tc.INK_SOFT = "#9aa0a6"
        tc.COAST = "#cfd6dc"
        tc.BORDER = "#cfd6dc"
        tc.GRID = "#5a6672"

    args.titulo = args.titulo or f"{args.sat} · {args.banda} · BRILLO"
    args.fuente = args.fuente or (
        f"SOURCE: NOAA/NESDIS {args.sat} ABI L2 CMIP | {args.banda}"
    )

    desde = datetime.fromisoformat(args.desde) if args.desde else None
    lista = slots(args.banda, args.sat, desde, args.n, args.paso, args.ultimos)

    if args.frames:
        salida = Path(args.frames)
        salida.mkdir(parents=True, exist_ok=True)
        print(f"{len(lista)} cuadros -> {salida}", flush=True)
        for i, (instante, nc) in enumerate(lista, 1):
            destino = salida / f"cuadro_{i:03d}.png"
            if destino.exists() and not args.forzar:
                continue
            disco, escala, _ = componer_banda(nc, args)
            fig = tc.dibujar(disco, escala, args.titulo, time_label_nc(nc),
                             args.fuente, args, args.px)
            parcial = destino.with_suffix(".png.parcial")
            fig.savefig(parcial, format="png", facecolor=tc.WHITE)
            import matplotlib.pyplot as plt
            plt.close(fig)
            parcial.replace(destino)
            print(f"  [{i}/{len(lista)}] {instante:%Y-%m-%d %H:%M} UTC", flush=True)
        print(f"Cuadros en {salida}")
        return 0

    instante, nc = lista[0]
    print(f"{nc.name}\nslot: {instante:%Y-%m-%d %H:%M} UTC | globo {args.px} px | "
          f"centro {tuple(args.centro)} | paleta {args.paleta}", flush=True)
    disco, escala, stats = componer_banda(nc, args)
    print(f"disco {stats['px']} px | {stats['validos']:,} px con dato")

    fig = tc.dibujar(disco, escala, args.titulo, time_label_nc(nc), args.fuente,
                     args, args.px)
    out = Path(args.out) if args.out else (
        SALIDAS / f"poster_{args.sat}_{args.banda}_{instante:%Y-%m-%dT%H%M}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    parcial = out.with_suffix(".png.parcial")
    fig.savefig(parcial, format="png", facecolor=tc.WHITE)
    import matplotlib.pyplot as plt
    plt.close(fig)
    parcial.replace(out)
    print(f"PNG: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
