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
SALIDAS = Path(os.environ.get("CLIMATE3D_DATOS") or r"D:\Users\guill\dataset era5") / "salidas"
DESTINO = RAIZ / "app" / "web" / "public" / "previews"

ANCHO = 520
CALIDAD = 82

# Render de referencia por producto. `None` = no hay muestra disponible.
FUENTES: dict[str, Path | None] = {
    "goes_c13": CACHE / "625bac70faf5" / "frames" / "cuadro_001.png",
    "goes_truecolor": CACHE / "d2b759e57810" / "truecolor_2026-04-15T1700.png",
    "mur_sst": SALIDAS / "frames_mur_globo_2025-01-01T0000_94f_2711px" / "cuadro_001.png",
    "mur_realista": CACHE / "70d167e92153" / "mur_realista_1400px.png",
    "precipitacion_ecmwf": CACHE / "4af5f2bccc3b" / "poster_precip_ecmwf_2026-10-31_00z_fh012.png",
    "anomalia_2t": CACHE / "109dba2d51d7" / "poster_anom2t_ifs_2026-10-30_06z_fh144.png",
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
