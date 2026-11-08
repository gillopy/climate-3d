"""Congela el dataset de la demo a partir de corridas reales de la app.

No modifica nada del pipeline ni de la app: lee el historial que la propia app
escribio, convierte los artefactos a WebP, arma un manifiesto y copia el build
del frontend. Todo lo generado cae en `demo/`.

Uso:
    python demo/tools/export_demo.py            # con el .venv de la app
    python demo/tools/export_demo.py --probe    # solo valida, no escribe
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# --- seleccion curada -----------------------------------------------------
# Una corrida real por producto. Los directorios salen del historial de la app
# (`app/var/media/historial.jsonl`); con `--historial` se puede pasar uno
# combinado (la app poda el suyo a 40 corridas).
SELECCION = [
    # GOES banda cruda: barrido completo del 2026-11-08 15:00 UTC, una corrida
    # por canal. C13 va primero porque es el default del formulario.
    "cache/592cf601145e",  # goes_banda C13 clean_ir
    "cache/ed08695cf02c",  # goes_banda C01 reflectancia
    "cache/b83dc623bb82",  # goes_banda C02 reflectancia
    "cache/1e8202a76eb3",  # goes_banda C03 reflectancia
    "cache/cc74c4e0d149",  # goes_banda C04 reflectancia
    "cache/b0fc16945680",  # goes_banda C05 reflectancia
    "cache/9bbdd4d9f85d",  # goes_banda C06 reflectancia
    "cache/63782456c295",  # goes_banda C08 c08_ir
    "cache/b7051eb198ba",  # goes_banda C09 c09_ir
    "cache/d4a07c0400a3",  # goes_banda C10 c10_ir
    "cache/bb69b8e3f84e",  # goes_banda C11 c11_ir
    "cache/68453ef2dc6e",  # goes_banda C12 c12_ir
    "cache/20cb2f6efc8f",  # goes_banda C14 c14_ir
    "cache/071cadf65216",  # goes_banda C15 c15_ir
    "cache/d0d1cec062bd",  # goes_banda C16 c16_ir
    "cache/1c68639dc983",  # goes_c13          03..04
    "cache/5e119fd99e80",  # geocolor          03..04
    "cache/d8fa7a21aea2",  # goes_truecolor    03..04
    "cache/63d06b4cfae3",  # goes_dust         04
    "cache/146799ea59cf",  # goes_airmass      04
    "cache/298727bb5a29",  # goes_firetemp     04
    "cache/1068c325336e",  # goes_sandwich     08
    "cache/86214db86a85",  # snapshot_paraguay 04
    "cache/b4bce5063c8f",  # anomalia_2t       05 (encuadre Paraguay limpio)
    "cache/157a64c714e6",  # viento_250        04 (encuadre Paraguay limpio)
    "cache/0a4f59e85579",  # mur_sst           04
    "cache/e05b5761e386",  # mur_realista      04
    "cache/422e427360ed",  # precipitacion_ecmwf 06 (encuadre Paraguay limpio)
    "cache/98b1ea7a7872",  # follaje           10-10
    "cache/50ecae621392",  # truecolor_viirs   04
]

MAX_ANCHO = 1600
WEBP_CALIDAD = 82
VIDEO_ANCHO = 1280
VIDEO_CRF = 30

RAIZ = Path(__file__).resolve().parents[2]


def _scrub(texto: str, repo: Path) -> str:
    """Saca rutas locales de logs y catalogos antes de publicarlos."""
    texto = texto.replace(str(repo), "<repo>")
    texto = re.sub(r"[A-Za-z]:\\[^\s\"']*", "<local>", texto)
    return texto


def _scrub_profundo(dato: Any, repo: Path) -> Any:
    if isinstance(dato, str):
        return _scrub(dato, repo)
    if isinstance(dato, list):
        return [_scrub_profundo(x, repo) for x in dato]
    if isinstance(dato, dict):
        return {k: _scrub_profundo(v, repo) for k, v in dato.items()}
    return dato


def _ffmpeg() -> str | None:
    try:  # el .venv de la app no lo trae; el de la raiz si
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    for ruta in (RAIZ / ".venv").glob("Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg*.exe"):
        return str(ruta)
    return None


def _webp(origen: Path, destino: Path) -> int:
    from PIL import Image

    destino.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(origen) as img:
        img = img.convert("RGB")
        if img.width > MAX_ANCHO:
            alto = round(img.height * MAX_ANCHO / img.width)
            img = img.resize((MAX_ANCHO, alto), Image.LANCZOS)
        img.save(destino, "WEBP", quality=WEBP_CALIDAD, method=6)
    return destino.stat().st_size


def _video(origen: Path, destino: Path, ffmpeg: str | None) -> tuple[Path, int]:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if ffmpeg:
        cmd = [
            ffmpeg, "-y", "-loglevel", "error", "-i", str(origen),
            "-vf", f"scale={VIDEO_ANCHO}:-2:force_original_aspect_ratio=decrease",
            "-c:v", "libx264", "-crf", str(VIDEO_CRF), "-preset", "veryfast",
            "-movflags", "+faststart", "-an", str(destino),
        ]
        hecho = subprocess.run(cmd, capture_output=True, text=True)
        if hecho.returncode == 0 and destino.is_file():
            return destino, destino.stat().st_size
    shutil.copy2(origen, destino)
    return destino, destino.stat().st_size


def _fechas(params: dict[str, Any]) -> list[str]:
    salida: set[str] = set()
    ventana = params.get("ventana")
    if isinstance(ventana, dict) and isinstance(ventana.get("start"), str):
        inicio = date.fromisoformat(ventana["start"])
        fin = date.fromisoformat(str(ventana.get("end") or ventana["start"]))
        while inicio <= fin:
            salida.add(inicio.isoformat())
            inicio += timedelta(days=1)
    fecha = params.get("fecha")
    if isinstance(fecha, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha):
        salida.add(fecha)
    return sorted(salida)


def _leer_historial(media: Path) -> dict[str, dict[str, Any]]:
    archivo = media / "historial.jsonl"
    filas: dict[str, dict[str, Any]] = {}
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        fila = json.loads(linea)
        filas[fila["dir"]] = fila
    return filas


def _catalogo(repo: Path) -> dict[str, Any]:
    sys.path.insert(0, str(repo))
    sys.path.insert(0, str(repo / "comun"))
    from app.api.catalog import productos_disponibles  # noqa: E402

    return {p.id: p.model_dump() for p in productos_disponibles()}


def _parametros_alineados(producto: dict[str, Any], params: dict[str, Any]) -> list[dict[str, Any]]:
    """Deja solo los controles que la corrida congelada realmente uso.

    Asi el formulario arranca con exactamente los parametros del manifiesto y
    el primer click siempre encuentra su resultado.
    """
    alineados = []
    for spec in producto.get("params", []):
        nombre = spec["name"]
        if nombre not in params:
            continue
        spec = dict(spec)
        spec["default"] = params[nombre]
        alineados.append(spec)
    return alineados


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=str(RAIZ))
    parser.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "site"))
    parser.add_argument("--historial",
                        help="historial.jsonl a congelar (por defecto, el de la app)")
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    salida = Path(args.out).resolve()
    media = repo / "app" / "var" / "media"

    if args.historial:
        filas = {}
        for linea in Path(args.historial).read_text(encoding="utf-8").splitlines():
            if not linea.strip():
                continue
            fila = json.loads(linea)
            filas[fila["dir"]] = fila
        historial = filas
    else:
        historial = _leer_historial(media)
    catalogo = _catalogo(repo)
    ffmpeg = _ffmpeg()

    combos: list[dict[str, Any]] = []
    dias: set[str] = set()
    avisos: list[str] = []

    for carpeta in SELECCION:
        fila = historial.get(carpeta)
        if fila is None:
            avisos.append(f"falta la corrida {carpeta}")
            continue
        job = fila["job"]
        producto = catalogo.get(job["product_id"])
        if producto is None:
            avisos.append(f"producto desconocido en la corrida {carpeta}")
            continue
        params = dict(job["params"])
        fechas = _fechas(params)
        if not fechas:
            avisos.append(f"sin fecha deducible en {carpeta}")
            continue
        dias.update(fechas)

        for spec in _parametros_alineados(producto, params):
            if spec["kind"] == "select" and spec["options"]:
                validos = {o["value"] for o in spec["options"]}
                if str(spec["default"]) not in validos:
                    avisos.append(
                        f"{producto['id']}: default {spec['default']!r} no esta entre las opciones de {spec['name']}"
                    )

        combos.append(
            {
                "id": job["id"],
                "product_id": job["product_id"],
                "params": params,
                "dates": fechas,
                "dir": carpeta,
                "job": job,
            }
        )

    print(f"corridas seleccionadas: {len(combos)}  dias: {sorted(dias)}")
    for aviso in avisos:
        print(f"  aviso: {aviso}")
    if args.probe:
        return 0 if combos else 1

    if salida.exists():
        shutil.rmtree(salida)
    salida.mkdir(parents=True)

    # --- frontend ya construido ------------------------------------------
    shutil.copytree(repo / "app" / "web" / "dist", salida, dirs_exist_ok=True)
    previews = repo / "app" / "web" / "public" / "previews"
    if previews.is_dir():
        shutil.copytree(previews, salida / "previews", dirs_exist_ok=True)

    # --- artefactos ------------------------------------------------------
    manifest_combos: list[dict[str, Any]] = []
    total = 0
    for combo in combos:
        job = combo["job"]
        destino_base = salida / "media" / job["id"]
        artefactos = []
        for artefacto in job["artifacts"]:
            origen = media / artefacto["url"].removeprefix("/media/")
            if not origen.is_file():
                avisos.append(f"artefacto ausente: {origen}")
                continue
            if artefacto["kind"] == "video":
                destino, peso = _video(origen, destino_base / artefacto["name"], ffmpeg)
            else:
                nombre = Path(artefacto["name"]).stem + ".webp"
                destino, peso = (destino_base / nombre), _webp(origen, destino_base / nombre)
            total += peso
            artefactos.append(
                {
                    "name": destino.name,
                    "url": f"/media/{job['id']}/{destino.name}",
                    "kind": artefacto["kind"],
                    "bytes": peso,
                }
            )

        log = [
            {
                "at": linea.get("at", ""),
                "level": linea.get("level", "info"),
                "text": _scrub(str(linea.get("text", "")), repo),
            }
            for linea in job.get("logs", [])[-40:]
        ]
        snapshot = {
            "id": job["id"],
            "product_id": job["product_id"],
            "product_name": job["product_name"],
            "params": combo["params"],
            "mode": "real",
            "status": "done",
            "progress": 1.0,
            "stage": "resultado precalculado",
            "created_at": job.get("created_at"),
            "started_at": job.get("started_at"),
            "finished_at": job.get("finished_at"),
            "logs": log,
            "artifacts": artefactos,
            "plan": job.get("plan", []),
            "error": None,
        }
        manifest_combos.append(
            {
                "id": job["id"],
                "product_id": job["product_id"],
                "params": combo["params"],
                "dates": combo["dates"],
                "snapshot": snapshot,
            }
        )
        print(f"  {job['product_id']:<22} {len(artefactos)} artefactos  {destino_base.name}")

    # --- catalogo recortado ----------------------------------------------
    productos = []
    dates: dict[str, list[str]] = {}
    for combo in manifest_combos:
        producto = catalogo[combo["product_id"]]
        if not any(p["id"] == producto["id"] for p in productos):
            recortado = dict(producto)
            recortado["params"] = _parametros_alineados(producto, combo["params"])
            recortado["command"] = None
            productos.append(recortado)
        previas = dates.setdefault(combo["product_id"], [])
        dates[combo["product_id"]] = sorted(set(previas) | set(combo["dates"]))

    catálogo_final = {
        "products": productos,
        "data_root": "dataset congelado de la demo",
        "data_root_exists": True,
        "media_root": "/media",
        "repo_python": "cloudflare/workers",
        "repo_ready": True,
    }
    catálogo_final = _scrub_profundo(catálogo_final, repo)

    manifiesto = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "days": sorted(dias),
        "dates": {k: v for k, v in sorted(dates.items())},
        "combos": manifest_combos,
        "catalog": catálogo_final,
    }

    src = Path(__file__).resolve().parents[1] / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "manifest.mjs").write_text(
        "// Generado por demo/tools/export_demo.py. No editar a mano.\n"
        "export default " + json.dumps(manifiesto, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )

    # Las portadas de productos que salieron del dataset no se publican.
    incluidos = {c["product_id"] for c in manifest_combos}
    carpeta_previews = salida / "previews"
    if carpeta_previews.is_dir():
        for portada in carpeta_previews.glob("*.webp"):
            if portada.stem.split("--")[0] not in incluidos:
                portada.unlink()

    (salida / "_headers").write_text(
        "/*\n  x-robots-tag: noindex\n"
        "/assets/*\n  cache-control: public, max-age=31536000, immutable\n"
        "/previews/*\n  cache-control: public, max-age=604800\n"
        "/media/*\n  cache-control: public, max-age=31536000, immutable\n"
        "/api/*\n  cache-control: no-store\n",
        encoding="utf-8",
    )
    (salida / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")

    print(f"\nlisto: {len(manifest_combos)} combos, {total / 1024 / 1024:.1f} MB de artefactos")
    print(f"manifiesto: {src / 'manifest.mjs'}")
    print(f"sitio:      {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
