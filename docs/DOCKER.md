# Correr Climate 3D en Docker

La consola y el pipeline entero —GOES, ERA5, ECMWF, GIBS, FIRMS— dentro de un contenedor.
Del lado de la otra persona hace falta **Docker y nada más**: no Python, no Node, no `.venv`.

El contenedor **renderiza de verdad**: descarga los datos, arma los cuadros y produce el
MP4/GIF con los mismos scripts del repo. No es una demo congelada.

## Arranque rápido

### Windows (PowerShell)

```powershell
.\setup.ps1
```

Si PowerShell bloquea el script:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

### Linux / macOS

```bash
./setup.sh
```

### Qué hace el asistente

1. Verifica que Docker esté instalado y que el daemon responda.
2. Pregunta **dónde viven los datos** y propone una carpeta.
3. Valida esa carpeta de verdad: la crea si falta, comprueba que se pueda escribir, avisa
   si quedan menos de 20 GB libres y rechaza rutas de red y carpetas de OneDrive.
4. Pregunta las **credenciales opcionales** y explica qué desbloquea cada una.
5. Escribe `.env` (UTF-8 sin BOM).
6. Valida `docker-compose.yml` con `docker compose config`.
7. Levanta el contenedor y espera a que `/api/health` responda con el pipeline listo.

Al final imprime la dirección: **http://127.0.0.1:8080**.

El primer build tarda entre 10 y 20 minutos y la imagen queda en el orden de 3 GB: trae
cartopy, PROJ, ECMWF eccodes, numpy y el frontend compilado.

## Qué hay adentro

| Ruta en el contenedor | Qué es |
| --- | --- |
| `/data` | el volumen: los `.nc`, las salidas y las carpetas de cada job |
| `/app` | el repo, de solo lectura |
| `/tmp/home` | el `HOME` del proceso: ahí caen `.cdsapirc` y `.netrc` si configuraste claves |

**Adentro del contenedor la ruta es siempre `/data`.** Lo único configurable es el lado
host, en `DATA_DIR`. Esa es toda la configuración de rutas: no se edita código.

Todo lo que genera la app queda dentro de `DATA_DIR`:

```
$DATA_DIR/
├── .media/      carpetas por job de la consola (artefactos que se descargan)
├── salidas/     lo que escriben los scripts por su cuenta
└── *.nc         los datasets que bajaste
```

## Credenciales

Todas son opcionales: la app arranca y renderiza sin ninguna. Solo habilitan productos
puntuales.

| Variable | Servicio | Qué desbloquea | Dónde se saca |
| --- | --- | --- | --- |
| `FIRMS_MAP_KEY` | NASA FIRMS | focos de calor | <https://firms.modaps.eosdis.nasa.gov/api/map_key/> |
| `CDSAPI_KEY` | Copernicus CDS | descarga de ERA5 | <https://cds.climate.copernicus.eu/> |
| `EARTHDATA_USER` + `EARTHDATA_PASSWORD` | Earthdata Login | follaje PACE | <https://urs.earthdata.nasa.gov/> |

Todas viajan por entorno: el entrypoint escribe `~/.cdsapirc` y `~/.netrc` al arrancar, así
que no hay que preparar archivos a mano. El `.env` generado incluye credenciales: está en
`.gitignore` y en `.dockerignore`, no se publica.

## Comandos del día a día

| Quiero… | Comando |
| --- | --- |
| levantarla | `docker compose up -d` |
| ver qué está pasando | `docker compose logs -f app` |
| apagarla (los datos quedan) | `docker compose down` |
| reconstruir después de cambiar código | `docker compose up -d --build` |
| chequear salud | `curl http://127.0.0.1:8080/api/health` |
| cambiar la carpeta de datos | editar `DATA_DIR` en `.env` y `docker compose up -d` |

## Por qué el puerto va en 127.0.0.1

La API **no tiene autenticación** y ejecuta subprocesos que escriben en tu disco. Por eso
`docker-compose.yml` publica `127.0.0.1:8080`, no `0.0.0.0`. No la abras a la red sin poner
algo adelante que autentique.

## Problemas comunes

| Síntoma | Causa | Arreglo |
| --- | --- | --- |
| `falta DATA_DIR` | no hay `.env` | corré `setup.ps1` / `setup.sh` |
| `repo_ready: false` en `/api/health` | el venv no quedó en `/app/.venv` | `docker compose up -d --build` y mirá el log del build |
| `data_root_exists: false` | la ruta del host no existe o está mal escrita | revisá `DATA_DIR` en `.env` |
| `la raíz de datos … no es escribible` | en Linux, el UID 1000 del contenedor no es dueño de la carpeta | `sudo chown -R 1000:1000 "$DATA_DIR"` |
| `no existe '/app/app/var/media'` | se saltó el asistente | borrá `$DATA_DIR/.media` y volvé a correrlo |
| `port is already allocated` | el 8080 está ocupado | cambiá `PORT` en `.env` |
| un render falla con `eccodes` | falta la librería del sistema | `docker compose build --no-cache` |
| el primer render tarda muchísimo | está bajando datos satelitales | es normal: mirá `docker compose logs -f app` |

## Distribuir la imagen ya compilada

Compilar 3 GB en la máquina de otra persona es el paso más molesto. Si la publicás en un
registry, el otro solo baja la imagen:

```bash
# una vez, en la máquina que la publica
docker build -t ghcr.io/USUARIO/climate3d:latest .
docker push ghcr.io/USUARIO/climate3d:latest
```

Después, en `docker-compose.yml` de la otra persona:

```yaml
    image: ghcr.io/USUARIO/climate3d:latest
    # build:
    #   context: .
```

Y `docker compose up -d` baja la imagen en vez de compilarla.

## Lo que este diseño no hace

- **No es multiusuario.** Un contenedor, un volumen, una persona. No hay cuentas ni cuotas.
- **No usa GPU.** Todo es CPU; lo pesado son los cuadros de matplotlib.
- **No persiste la cola de jobs.** Si recreás el contenedor, `.media` sobrevive pero el
  historial en memoria no.
- **Kubernetes queda afuera a propósito.** Una app, una máquina, un usuario: orquestar no
  agrega nada y sí agrega instalación. Si algún día esto es un servicio compartido con
  cuotas por usuario, ahí se discute.
