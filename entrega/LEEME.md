# Climate 3D — paquete para correrlo

No necesitás el repositorio, ni Python, ni Node. Solo Docker y esta carpeta.

## 1. Requisito

Docker Desktop instalado y **abierto** (el motor tiene que estar corriendo).

## 2. Arrancar

```powershell
.\setup.ps1
```

Te va a preguntar **dónde guardar los datos** y, si querés, las claves de NASA FIRMS,
Copernicus CDS y Earthdata (todas opcionales). Después baja la imagen y levanta la app.

Al final abrí **http://127.0.0.1:8080**.

En Linux o macOS es `./setup.sh`.

## Si preferís hacerlo a mano

```bash
cp env.example .env      # editá DATA_DIR
docker compose up -d
```

`DATA_DIR` es una carpeta **tuya**, fuera de esta carpeta: ahí van los `.nc` (varios GB),
las salidas y el estado de los jobs. Tiene que estar en un disco local, no en OneDrive
ni en una ruta de red.

## Comandos

| Quiero… | Comando |
| --- | --- |
| levantarla | `docker compose up -d` |
| ver qué pasa | `docker compose logs -f app` |
| apagarla (los datos quedan) | `docker compose down` |
| actualizar a una imagen nueva | `docker compose pull` y `docker compose up -d` |

## Dos cosas que conviene saber

- La app **no tiene autenticación**: queda publicada en `127.0.0.1`, solo en tu máquina.
  No la abras a la red.
- La imagen **no trae datos**. La primera vez que pidas un producto, la app descarga lo
  que necesite. Para ERA5 y PACE hacen falta las claves del `.env`; GOES y GIBS no piden
  nada.
