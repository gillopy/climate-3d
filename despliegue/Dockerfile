# syntax=docker/dockerfile:1

# --- Web: se compila una vez y el backend la sirve desde app/web/dist -------------
FROM node:22-slim AS web

WORKDIR /build
COPY app/web/package.json app/web/package-lock.json ./
RUN npm ci
COPY app/web/ ./
RUN npm run build


# --- Runtime: un solo venv con el pipeline y con la API --------------------------
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    HOME=/tmp/home \
    CLIMATE3D_CONTENEDOR=1 \
    CLIMATE3D_DATOS=/data \
    CLIMATE3D_MEDIA=/data/.media \
    CLIMATE3D_PYTHON=/app/.venv/bin/python

# `cartopy`, `shapely`, `pyproj`, `h5py`, `pykdtree` y `eccodes` llegan como wheels
# con sus bibliotecas adentro: NO hace falta el toolchain de desarrollo. Instalar
# `libeccodes-dev` arrastra gcc-14, gfortran y cpp-14 (~200 MB) sin ninguna ganancia;
# probado que `import eccodes` funciona solo con `libeccodes0` + `libeccodes-data`.
# `libexpat1` no lo pide pip: es una dependencia de las GDAL que rasterio trae
# empaquetadas y carga en tiempo de ejecucion. Sin el, `import rasterio` falla con
# "libexpat.so.1: cannot open shared object file" y la fusion optica queda apagada.
# ffmpeg tampoco va acá: lo baja imageio-ffmpeg en build time, más abajo.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      passwd \
      libeccodes0 \
      libeccodes-data \
      libexpat1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# uv instala exactamente lo que dice `uv.lock`: sin re-resolver y sin sorpresas de
# version. El entorno queda en /app/.venv, igual que en una maquina de desarrollo.
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /uvx /bin/
COPY pyproject.toml uv.lock ./

# Dependencias primero: cambiar el c��digo no reinstala nada de esto.
# El grupo `era5` entra por el mismo lock: cdsapi con version exacta y hashes.
RUN uv sync --frozen --no-dev --no-install-project --group era5

# `cdsapi` solo hace falta para descargar el .nc de ERA5, que suele venir bajado:
# por eso vive en el grupo `era5` y no en las dependencias duras. Entra por el lock,
# con version exacta y hashes, igual que el resto del entorno.

# ffmpeg queda horneado: el primer render no depende de la red.
RUN /app/.venv/bin/python -c \
      "import imageio_ffmpeg; print('ffmpeg listo:', imageio_ffmpeg.get_ffmpeg_exe())"

# Pipeline y API. `datos/paraguay_gadm.json` es el único archivo del repo que los
# scripts leen; el resto de `datos/` son descargas que viven en el volumen /data.
COPY comun/ ./comun/
COPY descargar/ ./descargar/
COPY cuadros/ ./cuadros/
COPY animar/ ./animar/
COPY prototipos/ ./prototipos/
COPY app/ ./app/
COPY datos/README.md datos/paraguay_gadm.json ./datos/
COPY --from=web /build/dist ./app/web/dist

COPY despliegue/entrypoint.sh /usr/local/bin/entrypoint.sh
# La raiz de artefactos vive en el volumen (/data/.media): la crea el entrypoint como
# appuser, no el build. Dentro de la imagen no queda nada que escribir en /app/app/var.
RUN chmod 0755 /usr/local/bin/entrypoint.sh \
 && useradd --create-home --uid 1000 --shell /bin/bash appuser
# El HOME es /tmp/home (ENV de arriba) y los RUN anteriores corrieron como root: uv
# y el chequeo de imports dejaron /tmp/home (con su .cache) con dueño root. appuser
# no podia escribir ahi las credenciales (~/.cdsapirc, ~/.netrc) y el contenedor
# entraba en un bucle de reinicio en cuanto el .env traia claves.
RUN mkdir -p /tmp/home && chown -R 1000:1000 /tmp/home

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
    CMD curl -fsS http://127.0.0.1:8000/api/health > /dev/null || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "api.main:app", \
     "--app-dir", "app", "--host", "0.0.0.0", "--port", "8000"]

# Sello del commit con el que se construyo. ARRANCAR-DOCKER.bat lo compara con
# HEAD para no servir codigo viejo sin avisar; va al final para no invalidar la
# cache de las capas de arriba.
ARG CLIMATE3D_COMMIT=desconocido
LABEL climate3d_commit="${CLIMATE3D_COMMIT}"
