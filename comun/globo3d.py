"""Base realista y warp Orthographic para los globos del proyecto.

El truco para que el planeta no se vea plano es el de
[`../prototipos/poster_mur_realista.py`](../prototipos/poster_mur_realista.py):

  1. una **base de relieve** real (Blue Marble *Shaded Relief + Bathymetry* de NASA GIBS)
     que aporta la textura de montañas y fondos oceánicos;
  2. la capa de datos **modulada por esa luminancia**, así el color respeta el terreno en
     vez de taparlo con una mancha plana;
  3. un **sombreado de esfera** sobre el disco ya proyectado (limb darkening + una
     lambertiana muy leve), que es la señal visual de volumen.

Todo se calcula con numpy y Pillow: no hace falta scipy ni pykdtree. La base se baja una
sola vez y queda cacheada en `SALIDAS/_globo3d/`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rutas import SALIDAS  # noqa: E402

API = "https://wvs.earthdata.nasa.gov/api/v1/snapshot"
CAPA = "BlueMarble_ShadedRelief_Bathymetry"
CACHE = SALIDAS / "_globo3d"

# Luz de la esfera: arriba-izquierda, como en el póster realista del repo.
LUZ = np.array([-0.42, 0.52, 0.74]) / np.linalg.norm([-0.42, 0.52, 0.74])


def base_mundi(ancho: int = 3600) -> np.ndarray:
    """Blue Marble con relieve, remuestreada a `ancho` × `ancho/2`, en float32 0-1.

    La base es estática: se baja la primera vez y se cachea. Se pide más grande que el
    uso final (4096) para que el remuestreo no pierda el relieve.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    destino = CACHE / f"blue_marble_{ancho}.png"
    if not destino.exists():
        origen = CACHE / "blue_marble_4096.jpg"
        if not origen.exists() or origen.stat().st_size < 200_000:
            url = (f"{API}?REQUEST=GetSnapshot&TIME=2026-10-01T00:00:00Z"
                   f"&BBOX=-90,-180,90,180&CRS=EPSG:4326&LAYERS={CAPA}"
                   f"&FORMAT=image/jpeg&WIDTH=4096&HEIGHT=2048")
            r = requests.get(url, timeout=180, headers={"User-Agent": "climate3d/1.0"})
            r.raise_for_status()
            if "image" not in r.headers.get("Content-Type", ""):
                raise SystemExit("GIBS no devolvió una imagen para Blue Marble")
            origen.write_bytes(r.content)
        im = Image.open(origen).convert("RGB")
        im.resize((ancho, ancho // 2), Image.LANCZOS).save(destino)
    im = Image.open(destino).convert("RGB")
    return np.asarray(im, dtype=np.float32) / 255.0


def luminancia(rgb: np.ndarray) -> np.ndarray:
    """Luminancia perceptual 0-1 de una imagen RGB float."""
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


def warp_ortho(rgb: np.ndarray, centro: tuple[float, float], lado: int,
               bloque: int = 180):
    """Reproyecta una imagen global lon/lat (2:1) a un disco Orthographic.

    Mapeo inverso con interpolación bilineal. Se procesa **por franjas de filas**: con
    1440×1440 el cálculo completo deja una docena de matrices float64 vivas a la vez y en
    una máquina con poca RAM revienta con `ArrayMemoryError`. Con `bloque` la memoria queda
    acotada y el resultado es idéntico.

    Devuelve `(rgb, dentro)`, con `dentro` la máscara booleana del disco.
    """
    alto_o, ancho_o = rgb.shape[:2]
    lon0, lat0 = np.radians(centro[0]), np.radians(centro[1])
    sen_lat0, cos_lat0 = np.sin(lat0), np.cos(lat0)

    salida = np.zeros((lado, lado, 3), dtype=np.float32)
    dentro = np.zeros((lado, lado), dtype=bool)
    x = np.linspace(-1.0, 1.0, lado, dtype=np.float32)
    y_total = np.linspace(1.0, -1.0, lado, dtype=np.float32)

    for y0 in range(0, lado, bloque):
        y1 = min(y0 + bloque, lado)
        X, Y = np.meshgrid(x, y_total[y0:y1])
        rho = np.hypot(X, Y)
        ok = rho <= 1.0
        rho_s = np.where(ok & (rho > 1e-12), rho, 1.0)
        c = np.arcsin(np.clip(rho_s, 0.0, 1.0))
        sin_c, cos_c = np.sin(c), np.cos(c)

        lat = np.arcsin(np.clip(cos_c * sen_lat0
                                + (Y * sin_c * cos_lat0) / rho_s, -1.0, 1.0))
        lon = lon0 + np.arctan2(X * sin_c,
                                rho_s * cos_lat0 * cos_c - Y * sen_lat0 * sin_c)
        centro_px = ok & (rho <= 1e-12)
        lat = np.where(centro_px, lat0, lat)
        lon = np.where(centro_px, lon0, lon)

        lon_deg = (np.degrees(lon) + 180.0) % 360.0 - 180.0
        lat_deg = np.degrees(lat)
        col = (lon_deg + 180.0) / 360.0 * (ancho_o - 1)
        fila = (90.0 - lat_deg) / 180.0 * (alto_o - 1)
        valido = ok & (col >= 0) & (col <= ancho_o - 1) & (fila >= 0) & (fila <= alto_o - 1)

        c0 = np.clip(np.floor(col), 0, ancho_o - 2).astype(np.int32)
        f0 = np.clip(np.floor(fila), 0, alto_o - 2).astype(np.int32)
        fc = np.clip(col - c0, 0.0, 1.0)[..., None].astype(np.float32)
        ff = np.clip(fila - f0, 0.0, 1.0)[..., None].astype(np.float32)
        a = rgb[f0, c0]
        b = rgb[f0, c0 + 1]
        d = rgb[f0 + 1, c0]
        e = rgb[f0 + 1, c0 + 1]
        mezcla = (a * (1 - fc) + b * fc) * (1 - ff) + (d * (1 - fc) + e * fc) * ff
        mezcla[~valido] = 0.0
        salida[y0:y1] = mezcla
        dentro[y0:y1] = valido
    return salida, dentro


def iluminar(rgb: np.ndarray, dentro: np.ndarray) -> np.ndarray:
    """Limb darkening + lambertiana leve sobre el disco ya proyectado.

    Sin esto el disco queda plano: los colores del dato son uniformes y el ojo no recibe
    ninguna señal de esfera. El centro conserva su color y el borde se hunde.
    """
    lado = rgb.shape[0]
    y = np.linspace(1.0, -1.0, lado, dtype=np.float32)
    x = np.linspace(-1.0, 1.0, lado, dtype=np.float32)
    X, Y = np.meshgrid(x, y)
    rho2 = X * X + Y * Y
    np.clip(rho2, 0.0, 1.0, out=rho2)
    z = np.sqrt(1.0 - rho2)
    lam = X * LUZ[0] + Y * LUZ[1] + z * LUZ[2]
    np.clip(lam, 0.0, 1.0, out=lam)
    del z, X, Y
    sombra = 1.0 - 0.22 * rho2 ** 1.4
    sombra *= 0.94 + 0.06 * lam
    del rho2, lam
    salida = rgb * sombra[..., None]
    del sombra
    salida[~dentro] = 0.0
    return np.clip(salida, 0.0, 1.0)
