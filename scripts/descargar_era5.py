"""Descarga ERA5 2m temperature (2024-2026) desde Copernicus CDS.

Pide un día por mes a las 00/06/12/18 UTC (≈1464 pasos de tiempo, ~2.2 GB), que es
la resolución temporal suficiente para las climatologías del póster de anomalía.

Uso (desde la raíz del proyecto):

    .venv\\Scripts\\python.exe scripts\\descargar_era5.py
    .venv\\Scripts\\python.exe scripts\\descargar_era5.py --out D:\\otra\\ruta
    .venv\\Scripts\\python.exe scripts\\descargar_era5.py --force   # re-descargar

Requiere `cdsapi` y la API key configurada en `~/.cdsapirc`.
La cola de CDS puede tardar bastante: conviene correrlo en segundo plano y mirar
`logs/`. Si el archivo destino ya existe y no está vacío, no vuelve a descargar.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cdsapi

DATASET = "reanalysis-era5-single-levels"
REQUEST = {
    "product_type": ["reanalysis"],
    "variable": ["2m_temperature"],
    "year": ["2024", "2025", "2026"],
    "month": ["01", "02", "03", "04", "05", "06",
              "07", "08", "09", "10", "11", "12"],
    "day": ["01", "04", "07", "09", "12", "15",
            "17", "20", "23", "25", "28", "31"],
    "time": ["00:00", "06:00", "12:00", "18:00"],
    "data_format": "netcdf",
    "download_format": "unarchived",
}

DESTINO_D = Path(r"D:\Users\guill\dataset era5")
NOMBRE = "era5_t2m_2024-2026.nc"


def descargar(destino: Path, forzar: bool = False) -> Path:
    """Baja el dataset a `destino` salvo que ya exista (y no se fuerce)."""
    if destino.exists() and destino.stat().st_size > 0 and not forzar:
        print(f"El archivo ya existe, no se vuelve a descargar: {destino}")
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    client = cdsapi.Client()
    print("Solicitud enviada a CDS; esperando en la cola...")
    client.retrieve(DATASET, REQUEST).download(str(destino))
    print(f"Descarga completa: {destino} ({destino.stat().st_size / 1e9:.2f} GB)")
    return destino


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Descarga ERA5 2m temperature (2024-2026) desde Copernicus CDS.")
    ap.add_argument("--out", help="carpeta destino (por defecto, D:\\Users\\guill\\dataset era5)")
    ap.add_argument("--nc", help=f"nombre del archivo a escribir (por defecto, {NOMBRE})")
    ap.add_argument("--force", action="store_true",
                    help="volver a descargar aunque el archivo ya exista")
    args = ap.parse_args(argv)

    carpeta = Path(args.out) if args.out else DESTINO_D
    descargar(carpeta / (args.nc or NOMBRE), forzar=args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
