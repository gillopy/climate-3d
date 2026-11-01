"""Genera los WebP de muestra de cada producto.

Las muestras salen de renders reales, no de dibujos: lo que ves en la tarjeta es
lo que el producto produce. Si cambia un estilo, se vuelve a correr este script.

    app\\.venv\\Scripts\\python.exe app\\tools\\previews.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parents[2]
CACHE = RAIZ / "app" / "var" / "media" / "cache"
VAR = RAIZ / "app" / "var"
GALERIA = RAIZ / "docs" / "galeria"
SALIDAS = Path(os.environ.get("CLIMATE3D_DATOS") or r"D:\Users\guill\dataset era5") / "salidas"
DESTINO = RAIZ / "app" / "web" / "public" / "previews"

ANCHO = 520
CALIDAD = 82

# Render de referencia por producto. `None` = no hay muestra disponible.
# Precipitacion y anomalia de 2 m usan el poster de fondo negro.
FUENTES: dict[str, Path | None] = {
    "goes_c13": CACHE / "409c61c9a623" / "frames" / "cuadro_001.png",
    "goes_truecolor": VAR / "truecolor_limpio.png",
    "goes_banda": VAR / "banda3.png",
    "geocolor": GALERIA / "geocolor_globo_G19_2026-10-04T1650.png",
    "truecolor_viirs": GALERIA / "truecolor_noaa20_globo_2024-09-28.png",
    "mur_sst": SALIDAS / "frames_mur_globo_2025-01-01T0000_94f_2711px" / "cuadro_001.png",
    "mur_realista": CACHE / "ccca0828c94f" / "mur_realista_1400px.png",
    "precipitacion_ecmwf": CACHE / "f17fd55f512a" / "poster_precip_ecmwf_2026-10-31_00z_fh144.png",
    "anomalia_2t": CACHE / "157996c077e8" / "poster_anom2t_ifs_2026-10-31_00z_fh012.png",
    "viento_250": GALERIA / "viento_250_globo_2026-10-20_18z_fh144.png",
    "snapshot_paraguay": GALERIA / "snapshot_paraguay_2026-11-01T1500.png",
    "himawari": CACHE / "9a62988526ae" / "frames" / "cuadro_001.png",
    "follaje": SALIDAS / "frames_follaje_pace_globo_ortho3d_2026-08-07T0000_66f_1440px" / "cuadro_001.png",
}


def main() -> int:
    DESTINO.mkdir(parents=True, exist_ok=True)
    faltan: list[str] = []

    for producto, origen in FUENTES.items():
        if origen is None or not origen.is_file():
            faltan.append(f"{producto} -> {origen}")
            continue

        with Image.open(origen) as imagen:
            rgb = imagen.convert("RGB")
            alto = max(1, round(rgb.height * ANCHO / rgb.width))
            chica = rgb.resize((ANCHO, alto), Image.LANCZOS)
            salida = DESTINO / f"{producto}.webp"
            chica.save(salida, format="WEBP", quality=CALIDAD, method=6)
            print(f"{producto:22s} {salida.stat().st_size / 1024:7.1f} KB  {origen.name}")

    if faltan:
        print("\nSin muestra (revisar rutas):")
        for faltante in faltan:
            print(f"  {faltante}")
        return 1 if len(faltan) == len(FUENTES) else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
