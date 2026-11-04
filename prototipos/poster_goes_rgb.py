"""Póster de un RGB oficial de GOES-R ABI: Dust, Air Mass o Fire Temperature.

Mismo encuadre y vestuario que `poster_goes_banda.py` (fondo oscuro, globo
inscripto, sin retícula ni costas), pero el disco no es una banda coloreada: son
tres canales mezclados con la receta del quick guide (ver `comun/rgb_goes.py`).

    .venv\\Scripts\\python.exe prototipos\\poster_goes_rgb.py --producto dust --ultimos 1
    .venv\\Scripts\\python.exe prototipos\\poster_goes_rgb.py --producto firetemp --desde 2026-11-04T18:00 --px 2000

Antes hay que bajar las bandas:

    .venv\\Scripts\\python.exe descargar\\descargar_goes_rgb.py --producto dust --ultimos 10
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
from poster_goes_realista import fecha_de, radio_visible, time_label_nc  # noqa: E402
from rgb_goes import PRODUCTOS, RECETAS, bandas, componer_rgb, etiqueta_canal  # noqa: E402
from rutas import SALIDAS  # noqa: E402

SAT = "G19"
PRODUCTO = "dust"
CENTRO = (-75.2, 0.0)
PX = 2712
#: Grilla de origen: 2 km, la resolución del producto. Baja las bandas de 1 km
#: (C05) a la misma grilla que C06/C07 sin compartir ejes entre bandas.
TOPE = 5424


def slots_producto(producto: str, sat: str, desde: datetime | None, n: int, paso: int,
                   ultimos: int = 0) -> list[tuple[datetime, dict[str, Path]]]:
    """Slots con `.nc` de TODAS las bandas de la receta.

    - `ultimos > 0`: los N más nuevos, terminando en el último completo.
    - `desde`: serie que arranca en ese instante.
    - sin ninguno de los dos: el último cuadro completo.
    """
    necesarias = bandas(producto)
    por_banda: dict[str, dict[datetime, Path]] = {}
    for banda in necesarias:
        encontrados: dict[datetime, Path] = {}
        for archivo in tc.carpeta(banda, sat).glob("*.nc"):
            match = PATRON.search(archivo.name)
            if not match or match["banda"] != banda or match["sat"] != sat:
                continue
            try:
                encontrados[fecha_de(archivo)] = archivo
            except Exception:  # noqa: BLE001 - nombre raro, se ignora
                continue
        por_banda[banda] = encontrados

    comunes = set.intersection(*(set(d) for d in por_banda.values()))
    if not comunes:
        raise SystemExit(
            f"No hay slots de {sat} con las bandas {', '.join(necesarias)}. "
            "Bajalos con descargar/descargar_goes_rgb.py."
        )

    if ultimos > 0:
        n = ultimos
        t0 = max(comunes) - timedelta(minutes=paso * (ultimos - 1))
    else:
        t0 = desde or max(comunes)

    lista: list[tuple[datetime, dict[str, Path]]] = []
    for i in range(n):
        instante = t0 + timedelta(minutes=paso * i)
        if instante in comunes:
            lista.append((instante, {b: por_banda[b][instante] for b in necesarias}))
    if not lista:
        raise SystemExit(f"Ninguno de los slots pedidos desde {t0:%Y-%m-%d %H:%M} está completo.")
    return lista


def _campos(paths: dict[str, Path], tope: int):
    """Bandas -> `{banda: (campo float32, x, y, lon0, h)}`.

    Cada banda trae su propia grilla: C05 es de 1 km y C06/C07 de 2 km, así que
    compartir la geometría de una sola banda desalinearía el muestreo (y el
    Fire Temperature saldría casi todo negro). `tope` baja las de 1 km a la
    grilla de 2 km, que es la resolución del producto.
    """
    import xarray as xr

    campos: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, float, float]] = {}
    for banda, nc in paths.items():
        campo, x, y, _proj, _unidad, _rot = cargar(nc, tope_px=tope)
        with xr.open_dataset(nc, engine="h5netcdf") as ds:
            gp = ds["goes_imager_projection"].attrs
            h = float(gp["perspective_point_height"])
            lon0 = float(gp["longitude_of_projection_origin"])
        campos[banda] = (np.asarray(campo, dtype=np.float32), x, y, lon0, h)
    return campos


def componer_disco(paths: dict[str, Path], args) -> tuple[np.ndarray, float, dict]:
    """Bandas -> RGBA del disco orthographic, con la geometría del color real."""
    campos = _campos(paths, args.tope)
    base = paths[bandas(args.producto)[0]]
    escala, _h, _lon0 = radio_visible(base, tuple(args.centro), args.recorte)
    px = args.px
    centro = tuple(args.centro)

    rgb = np.zeros((px, px, 3), dtype=np.uint8)
    alfa = np.zeros((px, px), dtype=np.uint8)
    validos = 0

    for f0 in range(0, px, tc.FILAS):
        f1 = min(f0 + tc.FILAS, px)
        lon, lat, rho, dentro = tc._orto_franja(px, escala, centro, f0, f1)
        franja = {
            banda: _muestrear_banda(campo, x, y, lon0, h, lon, lat)
            for banda, (campo, x, y, lon0, h) in campos.items()
        }
        bloque, valido = componer_rgb(franja, args.producto)
        a = tc._alfa(rho, px, escala) * dentro
        bloque[~valido] = 0

        rgb[f0:f1] = bloque
        alfa[f0:f1] = (a * 255.0).astype(np.uint8)
        validos += int(np.count_nonzero(a > 0))
        print(f"  franja {f1:5d}/{px}", flush=True)

    return np.dstack([rgb, alfa]), escala, {"px": px, "validos": validos}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Póster de un RGB oficial de GOES-R ABI.")
    ap.add_argument("--producto", choices=PRODUCTOS, default=PRODUCTO,
                    help=f"producto RGB (por defecto {PRODUCTO})")
    ap.add_argument("--sat", default=SAT, help=f"satélite (por defecto {SAT})")
    ap.add_argument("--desde", help="slot UTC ISO (por defecto, el último completo)")
    ap.add_argument("--n", type=int, default=1, help="cantidad de cuadros")
    ap.add_argument("--ultimos", type=int, default=0, metavar="N",
                    help="los N cuadros más nuevos completos (ignora --desde)")
    ap.add_argument("--paso", type=int, default=10, help="minutos entre cuadros")
    ap.add_argument("--px", type=int, default=PX, help=f"diámetro del globo (por defecto {PX})")
    ap.add_argument("--dpi", type=int, help="dpi; si se omite se deduce de --px")
    ap.add_argument("--tope", type=int, default=TOPE, help="grilla de origen de las bandas")
    ap.add_argument("--centro", nargs=2, type=float, metavar=("LON", "LAT"),
                    default=list(CENTRO), help="centro del globo")
    ap.add_argument("--recorte", type=float, default=1.0,
                    help="fracción del radio visible (1 = disco completo)")
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

    receta = RECETAS[args.producto]
    if args.fondo == "oscuro":
        tc.WHITE = "#000000"
        tc.INK = "#eef2f5"
        tc.INK_SOFT = "#9aa0a6"
        tc.COAST = "#cfd6dc"
        tc.BORDER = "#cfd6dc"
        tc.GRID = "#5a6672"

    canales = ", ".join(etiqueta_canal(c) for c in receta["canales"])
    args.titulo = args.titulo or f"{args.sat} · {receta['nombre'].upper()}"
    args.fuente = args.fuente or (
        f"SOURCE: NOAA/NESDIS {args.sat} ABI L2 CMIP | {canales}"
    )

    desde = datetime.fromisoformat(args.desde) if args.desde else None
    lista = slots_producto(args.producto, args.sat, desde, args.n, args.paso, args.ultimos)

    if args.frames:
        salida = Path(args.frames)
        salida.mkdir(parents=True, exist_ok=True)
        print(f"{len(lista)} cuadros -> {salida}", flush=True)
        for i, (instante, paths) in enumerate(lista, 1):
            destino = salida / f"cuadro_{i:03d}.png"
            if destino.exists() and not args.forzar:
                continue
            disco, escala, _ = componer_disco(paths, args)
            sello = time_label_nc(paths[bandas(args.producto)[0]])
            fig = tc.dibujar(disco, escala, args.titulo, sello, args.fuente, args, args.px)
            parcial = destino.with_suffix(".png.parcial")
            fig.savefig(parcial, format="png", facecolor=tc.WHITE)
            import matplotlib.pyplot as plt

            plt.close(fig)
            parcial.replace(destino)
            print(f"  [{i}/{len(lista)}] {instante:%Y-%m-%d %H:%M} UTC", flush=True)
        print(f"Cuadros en {salida}")
        return 0

    instante, paths = lista[0]
    print(f"{args.producto} | slot {instante:%Y-%m-%d %H:%M} UTC | globo {args.px} px | "
          f"centro {tuple(args.centro)}", flush=True)
    disco, escala, stats = componer_disco(paths, args)
    print(f"disco {stats['px']} px | {stats['validos']:,} px con dato")

    fig = tc.dibujar(disco, escala, args.titulo, time_label_nc(paths[bandas(args.producto)[0]]),
                     args.fuente, args, args.px)
    out = Path(args.out) if args.out else (
        SALIDAS / f"poster_{args.sat}_{args.producto}_{instante:%Y-%m-%dT%H%M}.png")
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
