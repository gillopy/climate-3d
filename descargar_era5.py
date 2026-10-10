"""Descarga ERA5 2m temperature (2024-2026) desde Copernicus CDS.

Ejecutar con el venv del proyecto:  .venv\\Scripts\\python.exe descargar_era5.py
Salida: era5_t2m_2024-2026.nc (~2-4 GB, la cola de CDS puede tardar).
"""
from pathlib import Path

import cdsapi

TARGET = Path(__file__).parent / "era5_t2m_2024-2026.nc"

dataset = "reanalysis-era5-single-levels"
request = {
    "product_type": ["reanalysis"],
    "variable": ["2m_temperature"],
    "year": ["2024", "2025", "2026"],
    "month": [
        "01", "02", "03",
        "04", "05", "06",
        "07", "08", "09",
        "10", "11", "12",
    ],
    "day": [
        "01", "04", "07",
        "09", "12", "15",
        "17", "20", "23",
        "25", "28", "31",
    ],
    "time": [
        "00:00", "06:00", "12:00",
        "18:00",
    ],
    "data_format": "netcdf",
    "download_format": "unarchived",
}

if TARGET.exists() and TARGET.stat().st_size > 0:
    print(f"El archivo ya existe, no se vuelve a descargar: {TARGET}")
else:
    client = cdsapi.Client()
    print("Solicitud enviada a CDS; esperando en la cola...")
    client.retrieve(dataset, request).download(str(TARGET))
    print(f"Descarga completa: {TARGET} ({TARGET.stat().st_size / 1e9:.2f} GB)")
