"""Render de demostracion.

Este archivo es el unico que dibuja. Hoy produce un cuadro sintetico para que la
demo funcione en cualquier maquina, sin depender de que los `.nc` esten en disco.
El camino real (los scripts de `cuadros/`) se conecta reemplazando el cuerpo de
`render_frame` por la llamada al producto, sin tocar la API ni la UI.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Paletas equivalentes a los estilos del catalogo: mismo nombre, distinto tono.
_PALETAS: dict[str, list[tuple[int, int, int]]] = {
    "realista": [
        (8, 8, 24),
        (40, 20, 90),
        (140, 30, 110),
        (230, 80, 60),
        (250, 180, 70),
        (255, 246, 210),
    ],
    "gibs": [
        (10, 10, 10),
        (70, 70, 70),
        (140, 140, 140),
        (200, 200, 200),
        (245, 245, 245),
    ],
    "crudo": [
        (10, 20, 60),
        (20, 120, 150),
        (60, 200, 120),
        (230, 220, 90),
        (240, 120, 60),
    ],
}

_FONDO = (11, 15, 20)
_TEXTO = (232, 238, 245)
_TENUE = (110, 125, 140)


def _fuente(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for nombre in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nombre, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _paleta(nombre: str) -> np.ndarray:
    paradas = np.array(_PALETAS.get(nombre, _PALETAS["realista"]), dtype=np.float32)
    # Rampa de 256 colores interpolando las paradas a mano.
    posiciones = np.linspace(0, 1, len(paradas))
    destino = np.linspace(0, 1, 256)
    return np.stack(
        [np.interp(destino, posiciones, paradas[:, canal]) for canal in range(3)],
        axis=1,
    ).astype(np.uint8)


def _campo(lado: int, t: float) -> tuple[np.ndarray, np.ndarray]:
    """Campo sintetico con estructura: sirve para probar el flujo, no el clima."""
    eje = np.linspace(-1.0, 1.0, lado, dtype=np.float32)
    x, y = np.meshgrid(eje, eje)
    r = np.hypot(x, y)
    theta = np.arctan2(y, x)

    bandas = 0.55 * np.sin(3.0 * theta + t * 0.9) * np.exp(-((r - 0.55) ** 2) / 0.06)
    remolino = 0.35 * np.cos(6.0 * theta - t * 1.5 + r * 5.0) * np.clip(1.0 - r, 0, 1)
    brillo = 0.85 * np.exp(-(r**2) / 0.22)
    z = bandas + remolino + brillo

    z = (z - z.min()) / (z.max() - z.min() + 1e-6)
    return z, r


def _graticula(draw: ImageDraw.ImageDraw, centro: tuple[float, float], radio: float) -> None:
    for fraccion in (0.33, 0.66):
        r = radio * fraccion
        draw.ellipse(
            [centro[0] - r, centro[1] - r, centro[0] + r, centro[1] + r],
            outline=(*_TENUE, 90),
            width=1,
        )
    for angulo in range(0, 180, 30):
        dx = radio * np.cos(np.radians(angulo))
        dy = radio * np.sin(np.radians(angulo))
        draw.line(
            [centro[0] - dx, centro[1] - dy, centro[0] + dx, centro[1] + dy],
            fill=(*_TENUE, 70),
            width=1,
        )


def render_frame(
    out_path: Path,
    *,
    titulo: str,
    subtitulo: str,
    estilo: str,
    marca: str,
    indice: int,
    total: int,
    tamaño: int,
) -> None:
    """Dibuja un cuadro y lo guarda como PNG."""
    lado = max(320, min(tamaño, 2000))
    t = indice * 0.55

    valores, r = _campo(lado, t)
    rgb = _paleta(estilo)[(valores * 255).astype(np.int32)]
    rgb[r > 1.0] = _FONDO

    imagen = Image.fromarray(rgb, mode="RGB")
    dibujo = ImageDraw.Draw(imagen, "RGBA")

    centro = (lado / 2, lado / 2)
    radio = lado * 0.46
    _graticula(dibujo, centro, radio)
    dibujo.ellipse(
        [centro[0] - radio, centro[1] - radio, centro[0] + radio, centro[1] + radio],
        outline=(*_TEXTO, 120),
        width=max(2, lado // 500),
    )

    # Rotulos: arriba el producto, al pie el cuadro. Formato de poster.
    titulo_font = _fuente(max(14, lado // 34))
    chico = _fuente(max(11, lado // 62))
    margen = lado * 0.05

    dibujo.text((margen, margen * 0.7), titulo, font=titulo_font, fill=_TEXTO)
    dibujo.text((margen, margen * 0.7 + lado // 26), subtitulo, font=chico, fill=_TENUE)

    pie = marca
    ancho = dibujo.textlength(pie, font=chico)
    dibujo.text((lado - margen - ancho, margen * 0.7), pie, font=chico, fill=_TENUE)

    contador = f"cuadro {indice + 1}/{total}"
    ancho = dibujo.textlength(contador, font=chico)
    dibujo.text(
        (lado - margen - ancho, lado - margen * 1.5),
        contador,
        font=chico,
        fill=_TENUE,
    )

    # Barra de color fina al pie, como en los posters del repo.
    alto_barra = max(4, lado // 200)
    ancho_barra = int(lado * 0.42)
    x0 = int(margen)
    y0 = int(lado - margen * 1.5 + alto_barra * 3)
    rampa = _paleta(estilo)[np.linspace(0, 255, ancho_barra).astype(int)]
    for i in range(ancho_barra):
        dibujo.line(
            [(x0 + i, y0), (x0 + i, y0 + alto_barra)],
            fill=tuple(int(c) for c in rampa[i]),
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    imagen.save(out_path, format="PNG", optimize=True)


def build_timeline(params: dict, total: int) -> list[str]:
    """Deriva las marcas de tiempo de los parametros, sin inventar fechas."""
    ventana = params.get("ventana") or params.get("fecha") or {}
    inicio = ventana.get("start")
    fin = ventana.get("end")

    if inicio and fin:
        try:
            d0 = datetime.fromisoformat(f"{inicio}T00:00:00")
            d1 = datetime.fromisoformat(f"{fin}T00:00:00")
        except ValueError:
            d0 = d1 = datetime.now()
        if total == 1 or d1 <= d0:
            base = [d0]
        else:
            paso = (d1 - d0) / (total - 1)
            base = [d0 + paso * i for i in range(total)]
        return [m.strftime("%Y-%m-%d %HZ") for m in base]

    horizonte = params.get("horizonte")
    if horizonte is not None:
        corrida = int(str(params.get("corrida", "00")))
        arranque = datetime.now().replace(hour=corrida, minute=0, second=0, microsecond=0)
        return [
            (arranque + timedelta(hours=6 * i)).strftime("%Y-%m-%d %HZ")
            for i in range(total)
        ]

    ahora = datetime.now().replace(minute=0, second=0, microsecond=0)
    return [(ahora - timedelta(hours=total - 1 - i)).strftime("%Y-%m-%d %HZ") for i in range(total)]


def frame_count(params: dict) -> int:
    """Cuantos cuadros: suficiente para que la animacion se lea, corto para probar."""
    ventana = params.get("ventana") or params.get("fecha") or {}
    if ventana.get("start") and ventana.get("end"):
        try:
            dias = (datetime.fromisoformat(ventana["end"]) - datetime.fromisoformat(ventana["start"])).days
            return max(2, min(dias * 2 + 1, 12))
        except ValueError:
            return 8
    if params.get("horizonte") is not None:
        return max(2, min(int(params["horizonte"]) // 24 + 2, 12))
    return 8


def save_gif(frames: Iterable[Path], destino: Path, fps: int) -> None:
    """Arma el GIF animado. El MP4 real lo sigue haciendo `animar/armar.py`."""
    lista = [Image.open(f).convert("RGB") for f in frames]
    if not lista:
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    lista[0].save(
        destino,
        format="GIF",
        save_all=True,
        append_images=lista[1:],
        duration=int(1000 / max(1, fps)),
        loop=0,
        optimize=True,
    )
