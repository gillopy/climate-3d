#!/usr/bin/env bash
# Arranque del contenedor: prepara un HOME escribible, materializa las credenciales
# que llegan por entorno y verifica las rutas de escritura antes de levantar la API.
#
# La idea es que un volumen mal montado falle acá, con un mensaje que se entienda,
# y no en medio del primer render con un traceback de matplotlib.
set -euo pipefail

DATOS="${CLIMATE3D_DATOS:-/data}"
MEDIA="${CLIMATE3D_MEDIA:-$DATOS/.media}"

fallar() {
    printf 'climate3d: %s\n' "$1" >&2
    exit 1
}

# El HOME vive en /tmp para no depender del UID con el que se monte el volumen.
mkdir -p "$HOME" || fallar "no se pudo crear el HOME '$HOME'."

if [ ! -d "$DATOS" ]; then
    fallar "no existe la raíz de datos '$DATOS'. Revisá el volumen /data (DATA_DIR en .env)."
fi
[ -w "$DATOS" ] || fallar "la raíz de datos '$DATOS' no es escribible. En Linux, el UID 1000 del contenedor necesita permiso sobre DATA_DIR."

mkdir -p "$MEDIA" || fallar "no se pudo crear '$MEDIA'. Revisá el volumen /data (DATA_DIR en .env)."
[ -w "$MEDIA" ] || fallar "'$MEDIA' no es escribible. Borrá esa carpeta y volvé a correr el asistente."

# Copernicus CDS: ~/.cdsapirc. El archivo nunca viaja en la imagen.
if [ -n "${CDSAPI_KEY:-}" ]; then
    {
        printf 'url: %s\n' "${CDSAPI_URL:-https://cds.climate.copernicus.eu/api}"
        printf 'key: %s\n' "$CDSAPI_KEY"
    } > "$HOME/.cdsapirc"
    chmod 600 "$HOME/.cdsapirc"
fi

# Earthdata Login (NISAR/ASF): ~/.netrc. PACE/LANDVI no lo usa: necesita la cookie
# GETFILE_APP del OAuth, que se copia como earthdata_cookies.json.
if [ -n "${EARTHDATA_USER:-}" ] && [ -n "${EARTHDATA_PASSWORD:-}" ]; then
    printf 'machine urs.earthdata.nasa.gov login %s password %s\n' \
        "$EARTHDATA_USER" "$EARTHDATA_PASSWORD" > "$HOME/.netrc"
    chmod 600 "$HOME/.netrc"
fi

# La MAP_KEY de FIRMS va por entorno (FIRMS_MAP_KEY): el archivo histórico
# datos/firms_map_key.txt no es escribible dentro de la imagen, y no hace falta.

printf 'climate3d: datos=%s media=%s\n' "$DATOS" "$MEDIA"

exec "$@"
