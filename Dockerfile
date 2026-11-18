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
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/tmp/home \
    CLIMATE3D_CONTENEDOR=1 \
    CLIMATE3D_DATOS=/data \
    CLIMATE3D_MEDIA=/data/.media \
    CLIMATE3D_PYTHON=/app/.venv/bin/python

# `cartopy`, `shapely`, `pyproj`, `h5py`, `pykdtree` y `eccodes` llegan como wheels
# con sus bibliotecas adentro: NO hace falta el toolchain de desarrollo. Instalar
# `libeccodes-dev` arrastra gcc-14, gfortran y cpp-14 (~200 MB) sin ninguna ganancia;
# probado que `import eccodes` funciona solo con `libeccodes0` + `libeccodes-data`.
# ffmpeg tampoco va acá: lo baja imageio-ffmpeg en build time, más abajo.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      passwd \
      libeccodes0 \
      libeccodes-data \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencias primero: cambiar el código no reinstala nada de esto.
COPY requirements.txt ./
COPY app/requirements.txt ./app/requirements.txt
RUN python -m venv /app/.venv \
 && /app/.venv/bin/pip install --upgrade pip \
 && /app/.venv/bin/pip install -r requirements.txt -r app/requirements.txt

# `cdsapi` queda solo en la imagen. El repo lo deja fuera a propósito porque el .nc de
# ERA5 ya suele estar bajado; acá quien llega puede no tenerlo, y el asistente ofrece
# la clave del CDS. Sin esto, `descargar_era5.py` muere con ModuleNotFoundError.
RUN /app/.venv/bin/pip install cdsapi

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

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
# La raiz de artefactos vive en el volumen (/data/.media): la crea el entrypoint como
# appuser, no el build. Dentro de la imagen no queda nada que escribir en /app/app/var.
RUN chmod 0755 /usr/local/bin/entrypoint.sh \
 && useradd --create-home --uid 1000 --shell /bin/bash appuser

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
    CMD curl -fsS http://127.0.0.1:8000/api/health > /dev/null || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "api.main:app", \
     "--app-dir", "app", "--host", "0.0.0.0", "--port", "8000"]
