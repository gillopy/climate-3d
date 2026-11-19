# Climate 3D — cómo se usa

Todo lo de despliegue vive acá, en `despliegue/`. No hay que editar código: la
carpeta de descargas y las claves se configuran desde el asistente.

| Archivo | Para qué |
| --- | --- |
| `ARRANCAR.bat` | **el que usás todos los días**: arranca la consola con Python |
| `ARRANCAR-DOCKER.bat` | la misma app dentro de Docker (no necesita Python ni Node) |
| `APAGAR.bat` | baja el contenedor de Docker (los datos quedan) |
| `setup.ps1` / `setup.sh` | el asistente de Docker: carpeta, claves y `docker compose up` |
| `env.example` | contrato de variables, por si armás el `.env` a mano |
| `Dockerfile`, `docker-compose.yml`, `entrypoint.sh` | la imagen |

---

## Opción 1 — directo (Python)

Doble clic en **`ARRANCAR.bat`**. Pregunta cuatro cosas y arranca en
**http://127.0.0.1:8000**:

1. **Dónde descargar**: la carpeta donde van los datos crudos, los productos, las
   salidas y la caché. Enter conserva la que ya está.
2. **Claves** (opcionales): NASA FIRMS (focos de calor), Copernicus CDS (ERA5) y
   Earthdata (NISAR y PACE). Enter en cada una conserva la que ya estaba.
3. Si quedó trabajo viejo dentro del repo, ofrece moverlo.
4. Levanta la consola.

Las claves quedan en `%LOCALAPPDATA%\climate3d\credenciales.json`, **fuera del
repo**, y se exportan al proceso: los scripts del pipeline las heredan.

## Opción 2 — Docker

Doble clic en **`ARRANCAR-DOCKER.bat`**. Verifica Docker, carga
`climate3d-image.tar` si está, y si no compila la imagen (10-20 minutos la primera
vez). Después abre **http://127.0.0.1:8080**.

El asistente (`setup.ps1`) pregunta la carpeta y las claves y escribe
`despliegue\.env`. Para apagarla: `APAGAR.bat` o `docker compose down`.

---

## Problemas comunes

| Síntoma | Causa | Arreglo |
| --- | --- | --- |
| `falta .venv` | no está el entorno de Python | `uv sync` en la raíz del repo |
| `al .venv le faltan las dependencias` | entorno a medio instalar | `uv sync` |
| `esa carpeta está dentro de OneDrive` | OneDrive sincronizaría varios GB | elegí un disco local (D:, E:) |
| `Docker no respondió en 3 minutos` | el daemon no arrancó | abrí Docker Desktop y esperá "Engine running" |
| La app de Docker no carga | todavía está arrancando | esperá 30 s; si sigue, `docker compose logs -f app` |
| `falta DATA_DIR` | no hay `despliegue\.env` | corré `setup.ps1` |
| Un render falla por memoria | el disco de trabajo está lleno | liberá espacio en la carpeta de descargas |

## Dónde queda cada cosa

```
<carpeta elegida>/
  goes_c13_g19/ …     datos crudos descargados
  salidas/            productos y animaciones
  .media/             artefactos de los jobs, historial y cachés
  .tmp/               temporales de los renders
  nisar/              escenas .h5 de NISAR (opcional, 1.9 GB cada una)
```

Los `.h5` de NISAR van en `nisar\` adentro de la misma carpeta (pesan ~1.9 GB cada uno). Si querés tenerlos en otro disco, el asistente te deja cambiar esa subcarpeta.
