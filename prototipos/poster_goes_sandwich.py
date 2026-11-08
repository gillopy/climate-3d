"""Póster del producto **Sandwich** de GOES (visible + IR realzado).

El Sandwich no es un RGB de tres bandas: son **dos imágenes mezcladas**. El fondo
es el visible (C02, 0.64 µm) y encima va el IR ventana (C13, 10.3 µm) pasado por
una rampa de color (frío -> rojo/naranja/amarillo/verde/cian -> gris cálido). La
mezcla es `alpha * visible + (1 - alpha) * IR_realzado`, la misma receta validada
en `cuadros/cuadros_sandwich.py`, pero acá se lee el `.nc` del ABI y se dibuja el
disco como el resto de los posters.

Es un producto **sólo diurno** (el visible necesita sol).

    .venv\\Scripts\\python.exe prototipos\\poster_goes_sandwich.py --desde 2026-11-08T16:10
    .venv\\Scripts\\python.exe prototipos\\poster_goes_sandwich.py --alpha 0.4 --px 2000
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "comun"))
sys.path.insert(0, str(RAIZ / "prototipos"))

import poster_goes_truecolor as tc  # noqa: E402
from goes_lectura import PATRON, cargar  # noqa: E402
from poster_goes_banda import _muestrear_banda  # noqa: E402
from poster_goes_realista import (  # noqa: E402
    fecha_de,
    radio_visible,
    time_label_nc,
)
from rutas import SALIDAS  # noqa: E402

SAT = "G19"
VIS, IR = "C02", "C13"
CENTRO = (-75.2, 0.0)
PX = 2712
#: La banda visible es de 0.5 km (21696 px): con 5424 sobra para un disco de 2712
#: y no hay que tener dos campos enormes en memoria a la vez.
TOPE = 5424
CORTE_PLANETA = 0.98
#: Mezcla: 1 = sólo visible, 0 = sólo IR realzado. 0.5 es el clásico.
ALPHA = 0.5
#: Escala del IR (la misma de `clean_ir`, o sea la rampa de GIBS/Worldview).
VMIN, VMAX = -92.1, 56.9

#: Rampa del IR realzado: posición 0 = lo más frío, 1 = lo más cálido. Es la
#: misma de `cuadros/cuadros_sandwich.py` (validada contra el producto oficial).
RAMPA_IR = [
    (0.00, (255, 32, 32)), (0.08, (224, 0, 0)), (0.14, (255, 128, 0)),
    (0.20, (240, 240, 0)), (0.26, (0, 224, 0)), (0.32, (0, 200, 255)),
    (0.38, (0, 80, 255)), (0.45, (10, 42, 143)),
    (0.55, (176, 176, 176)), (0.70, (140, 140, 140)), (1.00, (90, 90, 90)),
]
_POS = np.array([p for p, _ in RAMPA_IR], dtype=np.float32)
_COL = np.array([c for _, c in RAMPA_IR], dtype=np.float32)
_T = np.linspace(0.0, 1.0, 256, dtype=np.float32)
#: Tabla `(256, 3)` lista para indexar con la posición normalizada del IR.
LUT_IR = np.stack(
    [np.interp(_T, _POS, _COL[:, canal]) for canal in range(3)], axis=1
)


def _mapa(banda: str, sat: str) -> dict[datetime, Path]:
    """`{instante: .nc}` de una banda en disco."""
    encontrados: dict[datetime, Path] = {}
    for archivo in tc.carpeta(banda, sat).glob("*.nc"):
        match = PATRON.search(archivo.name)
        if not match or match["banda"] != banda or match["sat"] != sat:
            continue
        try:
            encontrados[fecha_de(archivo)] = archivo
        except Exception:  # noqa: BLE001 - nombre raro, se ignora
            continue
    return encontrados


def slots(sat: str, desde: datetime | None, n: int, paso: int,
          ultimos: int = 0) -> list[tuple[datetime, Path, Path]]:
    """Pares `(instante, visible, IR)` con los dos `.nc` en disco.

    Igual que en `poster_goes_banda`: `ultimos > 0` toma los N más nuevos que
    tengan las DOS bandas, `desde` arranca la serie y sin ninguno va el último.
    """
    vis = _mapa(VIS, sat)
    ir = _mapa(IR, sat)
    comunes = vis.keys() & ir.keys()
    if not comunes:
        raise SystemExit(
            f"No hay .nc de {VIS} y {IR} de {sat} en la misma carpeta "
            f"({tc.carpeta(VIS, sat)} y {tc.carpeta(IR, sat)}). "
            "Bajalos con descargar/descargar_goes.py."
        )
    if ultimos > 0:
        n = ultimos
        t0 = max(comunes) - timedelta(minutes=paso * (ultimos - 1))
    else:
        t0 = desde or max(comunes)
    lista = []
    for i in range(n):
        instante = t0 + timedelta(minutes=paso * i)
        if instante in comunes:
            lista.append((instante, vis[instante], ir[instante]))
    if not lista:
        raise SystemExit(
            f"Ninguno de los slots pedidos desde {t0:%Y-%m-%d %H:%M} tiene "
            f"las dos bandas."
        )
    return lista


def componer_sandwich(vis_nc: Path, ir_nc: Path, args) -> tuple[np.ndarray, float, dict]:
    """Mezcla visible + IR realzado -> RGBA del disco orthographic."""
    import xarray as xr

    vis, xv, yv, _pv, _uv, _rv = cargar(vis_nc, tope_px=args.tope)
    ir, xi, yi, _pi, _ui, _ri = cargar(ir_nc, tope_px=args.tope)
    with xr.open_dataset(vis_nc, engine="h5netcdf") as ds:
        gp = ds["goes_imager_projection"].attrs
        h = float(gp["perspective_point_height"])
        lon0 = float(gp["longitude_of_projection_origin"])

    escala, _h, _lon0 = radio_visible(vis_nc, tuple(args.centro), args.recorte)
    px = args.px
    centro = tuple(args.centro)
    alpha = float(args.alpha)

    rgb = np.zeros((px, px, 3), dtype=np.uint8)
    alfa = np.zeros((px, px), dtype=np.uint8)
    validos = 0

    for f0 in range(0, px, tc.FILAS):
        f1 = min(f0 + tc.FILAS, px)
        lon, lat, rho, dentro = tc._orto_franja(px, escala, centro, f0, f1)
        # `cargar` ya devuelve % (0..100) para el visible y C para el IR.
        v = _muestrear_banda(vis, xv, yv, lon0, h, lon, lat)
        t_campo = _muestrear_banda(ir, xi, yi, lon0, h, lon, lat)
        a = tc._alfa(rho, px, escala) * dentro
        a = a * tc._alfa(rho, px, 1.0 / CORTE_PLANETA)

        vis_n = np.clip(v / 100.0, 0.0, 1.0)
        t = np.clip((t_campo - args.vmin) / (args.vmax - args.vmin), 0.0, 1.0)
        t = np.where(np.isfinite(t), t, 0.0)
        ir_rgb = LUT_IR[(t * 255.0).astype(np.uint8)]
        gris = (vis_n * 255.0)[..., None]
        bloque = alpha * gris + (1.0 - alpha) * ir_rgb
        bloque[~np.isfinite(v) | ~np.isfinite(t_campo)] = 0.0

        rgb[f0:f1] = np.clip(bloque, 0.0, 255.0).astype(np.uint8)
        alfa[f0:f1] = (a * 255.0).astype(np.uint8)
        validos += int(np.count_nonzero(a > 0))
        print(f"  franja {f1:5d}/{px}", flush=True)

    # Sin filo brillante: display bilineal en vez de lanczos (sin overshoot).
    args.interp = "bilinear"

    return np.dstack([rgb, alfa]), escala, {"px": px, "validos": validos}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Póster Sandwich (visible + IR realzado) de GOES.")
    ap.add_argument("--sat", default=SAT, help=f"satélite (por defecto {SAT})")
    ap.add_argument("--desde", help="slot UTC ISO (por defecto, el último con .nc)")
    ap.add_argument("--n", type=int, default=1, help="cantidad de cuadros")
    ap.add_argument("--ultimos", type=int, default=0, metavar="N",
                    help="los N cuadros más nuevos con las dos bandas (ignora --desde)")
    ap.add_argument("--paso", type=int, default=10, help="minutos entre cuadros")
    ap.add_argument("--px", type=int, default=PX, help=f"diámetro del globo (por defecto {PX})")
    ap.add_argument("--dpi", type=int, help="dpi; si se omite se deduce de --px")
    ap.add_argument("--tope", type=int, default=TOPE, help="grilla de origen")
    ap.add_argument("--centro", nargs=2, type=float, metavar=("LON", "LAT"),
                    default=list(CENTRO), help="centro del globo")
    ap.add_argument("--recorte", type=float, default=1.0,
                    help="fracción del radio visible (1 = disco completo)")
    ap.add_argument("--alpha", type=float, default=ALPHA,
                    help=f"mezcla: 1 = sólo visible, 0 = sólo IR realzado "
                         f"(por defecto {ALPHA})")
    ap.add_argument("--vmin", type=float, default=VMIN,
                    help="mínimo IR de la rampa (°C)")
    ap.add_argument("--vmax", type=float, default=VMAX,
                    help="máximo IR de la rampa (°C)")
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

    if not (0.0 <= args.alpha <= 1.0):
        raise SystemExit(f"--alpha fuera de [0, 1]: {args.alpha}")
    if args.vmax <= args.vmin:
        raise SystemExit(f"escala IR inválida: {args.vmin}..{args.vmax}")

    if args.fondo == "oscuro":
        tc.WHITE = "#000000"
        tc.INK = "#eef2f5"
        tc.INK_SOFT = "#9aa0a6"
        tc.COAST = "#cfd6dc"
        tc.BORDER = "#cfd6dc"
        tc.GRID = "#5a6672"

    args.titulo = args.titulo or f"{args.sat} · SANDWICH · VIS + IR"
    args.fuente = args.fuente or (
        f"SOURCE: NOAA/NESDIS {args.sat} ABI L2 CMIP | {VIS} + {IR}"
    )

    desde = datetime.fromisoformat(args.desde) if args.desde else None
    lista = slots(args.sat, desde, args.n, args.paso, args.ultimos)

    if args.frames:
        salida = Path(args.frames)
        salida.mkdir(parents=True, exist_ok=True)
        print(f"{len(lista)} cuadros -> {salida}", flush=True)
        for i, (instante, vis_nc, ir_nc) in enumerate(lista, 1):
            destino = salida / f"cuadro_{i:03d}.png"
            if destino.exists() and not args.forzar:
                continue
            disco, escala, _ = componer_sandwich(vis_nc, ir_nc, args)
            fig = tc.dibujar(disco, escala, args.titulo, time_label_nc(vis_nc),
                             args.fuente, args, args.px)
            parcial = destino.with_suffix(".png.parcial")
            fig.savefig(parcial, format="png", facecolor=tc.WHITE)
            import matplotlib.pyplot as plt
            plt.close(fig)
            parcial.replace(destino)
            print(f"  [{i}/{len(lista)}] {instante:%Y-%m-%d %H:%M} UTC", flush=True)
        print(f"Cuadros en {salida}")
        return 0

    instante, vis_nc, ir_nc = lista[0]
    print(f"{vis_nc.name} + {ir_nc.name}\nslot: {instante:%Y-%m-%d %H:%M} UTC | "
          f"globo {args.px} px | alpha {args.alpha}", flush=True)
    disco, escala, stats = componer_sandwich(vis_nc, ir_nc, args)
    print(f"disco {stats['px']} px | {stats['validos']:,} px con dato")

    fig = tc.dibujar(disco, escala, args.titulo, time_label_nc(vis_nc), args.fuente,
                     args, args.px)
    out = Path(args.out) if args.out else (
        SALIDAS / f"poster_{args.sat}_sandwich_{instante:%Y-%m-%dT%H%M}.png")
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
