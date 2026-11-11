#!/usr/bin/env bash
# Asistente de instalación de Climate 3D en Docker (Linux/macOS).
#
# Verifica Docker, pregunta la carpeta de datos, valida que se pueda escribir, pide
# las credenciales opcionales, escribe `.env` y levanta el contenedor.
# No edita código: lo único configurable es el lado host.
#
#   ./setup.sh
#   DATA_DIR=~/clima PORT=8080 ./setup.sh
#   ./setup.sh --solo-configurar

set -euo pipefail

cd "$(dirname "$0")"

DATA_DIR_IN="${DATA_DIR:-}"
PORT_IN="${PORT:-8080}"
SOLO_CONFIGURAR=0

for arg in "$@"; do
    case "$arg" in
        --solo-configurar) SOLO_CONFIGURAR=1 ;;
        -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
        *) printf 'argumento desconocido: %s\n' "$arg" >&2; exit 2 ;;
    esac
done

fallar() { printf '\n  x  %s\n' "$1" >&2; exit 1; }
ok()     { printf '  ok  %s\n' "$1"; }
paso()   { printf '\n%s\n' "$1"; }

# Compose corta el valor en un `#` y se come los espacios de los bordes.
valor_env() {
    case "$1" in
        *[[:space:]#]*) printf '"%s"' "$1" ;;
        *) printf '%s' "$1" ;;
    esac
}

paso '[1/6] Docker'
command -v docker >/dev/null 2>&1 \
    || fallar "no encontré 'docker'. Instalá Docker Engine o Docker Desktop y volvé a correr esto."
docker info --format '{{.ServerVersion}}' >/dev/null 2>&1 \
    || fallar 'Docker está instalado pero el daemon no responde. Arrancalo y reintentá.'
docker compose version >/dev/null 2>&1 \
    || fallar "falta el plugin 'docker compose'."
ok 'Docker responde.'

paso '[2/6] Carpeta de datos (los .nc y las salidas)'
sugerida="$HOME/climate3d-data"
DATA_DIR="$DATA_DIR_IN"
if [ -z "$DATA_DIR" ]; then
    printf '  ¿Dónde guardamos los datos? [%s] ' "$sugerida"
    read -r entrada || true
    DATA_DIR="${entrada:-$sugerida}"
fi
DATA_DIR="$(printf '%s' "$DATA_DIR" | tr -d "\"'")"
# Adentro del contenedor la ruta es fija (/data): lo que configuramos es el lado host.
DATA_DIR="$(printf '%s' "$DATA_DIR" | sed 's:/*$::')"
[ -n "$DATA_DIR" ] || fallar 'la carpeta de datos quedó vacía.'

case "$DATA_DIR" in
    '~') DATA_DIR="$HOME" ;;
    '~/'*) DATA_DIR="$HOME/${DATA_DIR#~/}" ;;
esac

case "$DATA_DIR" in
    //*) fallar "no puedo montar una ruta de red como volumen ('$DATA_DIR'). Usá un disco local." ;;
esac
# Un segmento exacto del camino: /mnt/onedrive-archive no es OneDrive, /home/x/OneDrive sí.
if printf '%s' "$DATA_DIR" | grep -qiE '/(onedrive[^/]*)(/|$)'; then
    fallar 'esa carpeta está dentro de OneDrive. Elegí una carpeta fuera de la nube: son varios GB.'
fi

if [ -d "$DATA_DIR" ]; then
    ok "usa $DATA_DIR (ya existía)"
else
    mkdir -p "$DATA_DIR" 2>/dev/null || fallar "no pude crear '$DATA_DIR'. Revisá los permisos."
    ok "creé $DATA_DIR"
fi

[ -w "$DATA_DIR" ] || fallar "'$DATA_DIR' no es escribible. Elegí otra carpeta o dale permiso."

prueba="$DATA_DIR/.escritura-$$"
( : > "$prueba" ) 2>/dev/null || fallar "no puedo escribir en '$DATA_DIR'."
rm -f "$prueba"
ok 'la carpeta es escribible.'

mkdir -p "$DATA_DIR/.media" 2>/dev/null || fallar "no pude crear '$DATA_DIR/.media'."

if libre_kb=$(df -Pk "$DATA_DIR" 2>/dev/null | awk 'NR==2 {print $4}'); then
    libre_kb="${libre_kb:-0}"
    libres=$(( libre_kb / 1024 / 1024 ))
    if [ "$libres" -lt 20 ]; then
        printf '  !  quedan %s GB libres: un render largo genera muchos cuadros.\n' "$libres"
    else
        ok "espacio libre: ${libres} GB"
    fi
fi

paso '[3/6] Credenciales (opcionales: Enter para saltear)'
printf '  FIRMS      -> focos de calor  (gratis: https://firms.modaps.eosdis.nasa.gov/api/map_key/)\n'
printf '  CDS        -> descarga ERA5   (gratis: https://cds.climate.copernicus.eu/)\n'
printf '  Earthdata  -> follaje PACE    (gratis: https://urs.earthdata.nasa.gov/)\n'

FIRMS_MAP_KEY="${FIRMS_MAP_KEY:-}"
CDSAPI_KEY="${CDSAPI_KEY:-}"
EARTHDATA_USER="${EARTHDATA_USER:-}"
EARTHDATA_PASSWORD="${EARTHDATA_PASSWORD:-}"

if [ -z "$FIRMS_MAP_KEY$CDSAPI_KEY$EARTHDATA_USER" ]; then
    printf '  ¿Configuramos credenciales ahora? (s/N) '
    read -r quiere || true
    case "$quiere" in
        s|S|si|sí|y|Y|yes)
            printf '  FIRMS MAP_KEY: ';       read -r FIRMS_MAP_KEY || true
            printf '  Copernicus CDS key: ';  read -r CDSAPI_KEY || true
            printf '  Earthdata usuario: ';   read -r EARTHDATA_USER || true
            printf '  Earthdata clave: ';     read -r -s EARTHDATA_PASSWORD || true; printf '\n'
            ;;
    esac
fi

paso '[4/6] Configuración (.env)'
{
    printf '# Generado por setup.sh. Ver env.example para el detalle de cada variable.\n'
    printf '\n# --- host ---\n'
    printf 'DATA_DIR=%s\n' "$(valor_env "$DATA_DIR")"
    printf 'PORT=%s\n' "$PORT_IN"
    printf '\n# --- credenciales (opcionales) ---\n'
    printf 'FIRMS_MAP_KEY=%s\n' "$(valor_env "$FIRMS_MAP_KEY")"
    printf 'CDSAPI_KEY=%s\n' "$(valor_env "$CDSAPI_KEY")"
    printf 'EARTHDATA_USER=%s\n' "$(valor_env "$EARTHDATA_USER")"
    printf 'EARTHDATA_PASSWORD=%s\n' "$(valor_env "$EARTHDATA_PASSWORD")"
} > .env
chmod 600 .env 2>/dev/null || true
ok "escribí $(pwd)/.env"

paso '[5/6] Validación de docker-compose.yml'
docker compose config --quiet || fallar 'docker-compose.yml no valida con el .env generado. Corré "docker compose config" para ver el detalle.'
ok 'la configuración es válida.'

if [ "$SOLO_CONFIGURAR" -eq 1 ]; then
    printf '\nListo: configuré .env. Para levantar la app: docker compose up -d\n'
    exit 0
fi

paso '[6/6] Levantando la app (si la imagen no está, se compila o se baja)'
docker compose up -d || fallar 'el build o el arranque falló: mirá la salida de arriba.'

url="http://127.0.0.1:$PORT_IN"

if ! command -v curl >/dev/null 2>&1; then
    printf '  !  no hay curl en este host, así que no puedo esperar a la API.\n'
    printf '     Abrí %s cuando "docker compose logs app" muestre que arrancó.\n' "$url"
    exit 0
fi

printf '  esperando a que la API responda...\n'
salud=''
limite=$(( $(date +%s) + 360 ))
while [ "$(date +%s)" -lt "$limite" ]; do
    salud=$(curl -fsS --max-time 4 "$url/api/health" 2>/dev/null || true)
    case "$salud" in
        *'"ok":true'*) break ;;
    esac
    sleep 3
done

case "$salud" in
    *'"ok":true'*) ok 'la API responde.' ;;
    *) salud='' ;;
esac
[ -n "$salud" ] || fallar 'la app no respondió en 6 minutos. Mirá los logs con: docker compose logs --tail 50 app'

printf '\n  Listo. Abrí esta dirección en el navegador:\n'
printf '    %s\n\n' "$url"

case "$salud" in
    *'"repo_ready":false'*)         printf '  !  El pipeline no quedó listo (repo_ready=false). Mirá "docker compose logs app".\n' ;;
esac
case "$salud" in
    *'"data_root_exists":false'*)   printf '  !  La carpeta de datos no se ve desde el contenedor. Revisá DATA_DIR en .env.\n' ;;
esac

printf '  Para apagarla: docker compose down\n'
