"""Genera los WebP de muestra de cada producto.

Las muestras salen de renders reales, no de dibujos: lo que ves en la tarjeta es
lo que el producto produce. Si cambia un estilo, se vuelve a correr este script.

Cada producto tiene una placa fija (`<producto>.webp`) y, si el catálogo declara
variantes, una placa por combinación de parámetros (`<producto>--<valores>.webp`),
con los mismos campos y en el mismo orden que `_VARIANTES` de `api/catalog.py`.

    .venv\\Scripts\\python.exe app\\tools\\previews.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parents[2]
for candidato in (RAIZ, RAIZ / "comun"):
    if str(candidato) not in sys.path:
        sys.path.insert(0, str(candidato))

from rutas import CACHE, SALIDAS  # noqa: E402  (necesita la raíz del repo de arriba)

VAR = RAIZ / "app" / "var"
GALERIA = RAIZ / "docs" / "galeria"
DESTINO = RAIZ / "app" / "web" / "public" / "previews"

ANCHO = 520
CALIDAD = 82

# Renders recientes de la consola (cache de cada job). La firma del job es estable
# mientras la receta no cambie; si se purga la cache, la placa queda "sin muestra".
JOB = CACHE
GOES_G19_1700 = JOB / "ea848b0da6e6" / "frames_geocolor_globo_G19_2026-11-18T1700_1f_2712px" / "cuadro_001.png"
GOES_G18_2240 = JOB / "8142314c5025" / "frames_geocolor_globo_G18_2026-11-18T2240_1f_2712px" / "cuadro_001.png"
BANDA_C13 = {
    "G19": JOB / "9994508e6cfb" / "G19_C13_2026-11-18T2310.png",
    "G18": JOB / "e8c62a37029d" / "G18_C13_2026-11-18T2310.png",
    "G16": JOB / "94e41a6113d2" / "G16_C13_2025-02-02T1700.png",
}
RGB = {
    "airmass": {
        "G19": JOB / "cd82a76d9626" / "G19_airmass_2026-11-18T1700.png",
        "G18": JOB / "5b338664759e" / "G18_airmass_2026-11-18T2100.png",
        "G16": JOB / "9593c9893e37" / "G16_airmass_2025-02-02T1700.png",
    },
    "dust": {
        "G19": JOB / "2d2d2a8a3f66" / "G19_dust_2026-11-18T1700.png",
        "G18": JOB / "83e81657dffc" / "G18_dust_2026-11-18T2100.png",
        "G16": JOB / "eb5c33e85906" / "G16_dust_2025-02-02T1700.png",
    },
    "firetemp": {
        "G19": JOB / "b9f0881d2b35" / "G19_firetemp_2026-11-18T1700.png",
        "G18": JOB / "2b239d209488" / "G18_firetemp_2026-11-18T2100.png",
        "G16": JOB / "eb6687bceb94" / "G16_firetemp_2025-02-02T1700.png",
    },
}
SANDWICH = {
    "G19": JOB / "ec9b26111db1" / "G19_Sandwich_2026-11-18T1700.png",
    "G18": JOB / "806ac86bcc3e" / "G18_Sandwich_2026-11-18T2100.png",
    "G16": JOB / "cb7be29a3eb7" / "G16_Sandwich_2025-02-02T1700.png",
}
# Meteosat-12: el mismo cuadro del 2026-11-23 12:00 UTC en las tres capas, para
# que la placa cambie con `variante` igual que el render.
METEOSAT = {
    "geocolour": JOB / "c406ea1d966b" / "frames_meteosat_globo_2026-11-23T1200_1f_2712px" / "cuadro_001.png",
    "truecolour": JOB / "88cef0c2f038" / "frames_meteosat_globo_2026-11-23T1200_1f_2712px" / "cuadro_001.png",
    "ir": JOB / "0d48a0a0d6f3" / "frames_meteosat_globo_2026-11-23T1200_1f_2712px" / "cuadro_001.png",
}
# CBERS-4A: un recorte por zona; Ciudad del Este es el de 2 m (PCA), el resto 8 m
# (WPM). La placa fija usa el de 2 m, que es el que muestra el detalle del sensor.
CBERS = {
    "cdeleste": JOB / "5adf917ad026" / "cbers_cdeleste_20261026.png",
    "asuncion": JOB / "10bd4295fae4" / "cbers_asuncion_20261106.png",
    "filadelfia": JOB / "0b892dee9a54" / "cbers_filadelfia_20261117.png",
}

# Placa fija de cada producto. `None` = no hay muestra disponible.
# Precipitacion y anomalia de 2 m usan el poster de fondo negro.
FUENTES: dict[str, Path | None] = {
    "goes_c13": JOB / "d231dc297a0d" / "frames" / "cuadro_001.png",
    "goes_banda": BANDA_C13["G19"],
    "goes_lst": JOB / "24f9f6a06b52" / "G19_LST_2026-11-18T2300.png",
    "goes_dust": RGB["dust"]["G19"],
    "goes_airmass": RGB["airmass"]["G19"],
    "goes_firetemp": RGB["firetemp"]["G19"],
    "goes_sandwich": SANDWICH["G19"],
    "geocolor": GOES_G19_1700,
    "goes_truecolor": VAR / "truecolor_limpio.png",
    "truecolor_viirs": GALERIA / "truecolor_noaa20_globo_2024-09-28.png",
    "mur_sst": SALIDAS / "frames_mur_globo_2025-01-01T0000_94f_2711px" / "cuadro_001.png",
    "mur_realista": JOB / "ccca0828c94f" / "mur_realista_1400px.png",
    "precipitacion_ecmwf": JOB / "f17fd55f512a" / "poster_precip_ecmwf_2026-10-31_00z_fh144.png",
    "anomalia_2t": JOB / "157996c077e8" / "poster_anom2t_ifs_2026-10-31_00z_fh012.png",
    "viento_250": GALERIA / "viento_250_globo_2026-10-20_18z_fh144.png",
    "snapshot_paraguay": GALERIA / "snapshot_paraguay_2026-10-31T0000.png",
    "himawari": JOB / "9a62988526ae" / "frames" / "cuadro_001.png",
    "follaje": SALIDAS / "frames_follaje_pace_globo_ortho3d_2026-08-07T0000_66f_1440px" / "cuadro_001.png",
    "meteosat": METEOSAT["geocolour"],
    "cbers_4a": CBERS["cdeleste"],
}

#: Placas por variante: `(producto, valores)` -> render. Los campos y su orden son
#: los de `_VARIANTES` en `api/catalog.py` (`paraguay` va como "true"/"false").
VARIANTES: dict[tuple[str, tuple[str, ...]], Path] = {
    ("geocolor", ("G19", "false")): GOES_G19_1700,
    ("geocolor", ("G18", "false")): GOES_G18_2240,
    ("goes_c13", ("G18", "false")): JOB / "d231dc297a0d" / "frames" / "cuadro_001.png",
    # La banda declara dos formas: la completa gana, la corta queda como respaldo.
    ("goes_banda", ("G19", "C13", "clean_ir")): BANDA_C13["G19"],
    ("goes_banda", ("G18", "C13", "clean_ir")): BANDA_C13["G18"],
    ("goes_banda", ("G16", "C13", "clean_ir")): BANDA_C13["G16"],
    ("goes_banda", ("G19", "clean_ir")): BANDA_C13["G19"],
    ("goes_banda", ("G18", "clean_ir")): BANDA_C13["G18"],
    ("goes_banda", ("G16", "clean_ir")): BANDA_C13["G16"],
}
for _sat in ("G19", "G18", "G16"):
    VARIANTES[("goes_airmass", (_sat, "false"))] = RGB["airmass"][_sat]
    VARIANTES[("goes_dust", (_sat, "false"))] = RGB["dust"][_sat]
    VARIANTES[("goes_firetemp", (_sat, "false"))] = RGB["firetemp"][_sat]
    # Sandwich no lleva "paraguay" en el catalogo: la variante es solo el satelite.
    VARIANTES[("goes_sandwich", (_sat,))] = SANDWICH[_sat]
for _capa, _origen in METEOSAT.items():
    VARIANTES[("meteosat", (_capa,))] = _origen
for _zona, _origen in CBERS.items():
    VARIANTES[("cbers_4a", (_zona,))] = _origen


def _nombre(producto: str, valores: tuple[str, ...]) -> str:
    return f"{producto}.webp" if not valores else f"{producto}--{'--'.join(valores)}.webp"


def _guardar(origen: Path, destino: Path, etiqueta: str) -> bool:
    with Image.open(origen) as imagen:
        rgb = imagen.convert("RGB")
        alto = max(1, round(rgb.height * ANCHO / rgb.width))
        chica = rgb.resize((ANCHO, alto), Image.LANCZOS)
        chica.save(destino, format="WEBP", quality=CALIDAD, method=6)
    print(f"{etiqueta:34s} {destino.stat().st_size / 1024:7.1f} KB  {origen.name}")
    return True


def main() -> int:
    DESTINO.mkdir(parents=True, exist_ok=True)
    faltan: list[str] = []
    hechas = 0

    placas = [(producto, (), origen) for producto, origen in FUENTES.items()]
    placas += [(producto, valores, origen) for (producto, valores), origen in VARIANTES.items()]

    for producto, valores, origen in placas:
        nombre = _nombre(producto, valores)
        if origen is None or not origen.is_file():
            faltan.append(f"{nombre} -> {origen}")
            continue
        if _guardar(origen, DESTINO / nombre, nombre):
            hechas += 1

    print(f"\n{hechas} placas generadas en {DESTINO}")
    if faltan:
        print("\nSin muestra (revisar rutas):")
        for faltante in faltan:
            print(f"  {faltante}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
