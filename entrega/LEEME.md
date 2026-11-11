# Climate 3D — cómo usarlo

Cuatro pasos. No hace falta saber nada de programación.

---

## Paso 1 — Instalar Docker Desktop

Descargalo de **https://www.docker.com/products/docker-desktop/**, instalalo con las
opciones por defecto y **abrilo**.

Si te pide reiniciar la PC, reiniciá.

Cuando esté abierto, abajo a la izquierda tiene que decir **Engine running**.

> Docker es lo único que hay que instalar. La aplicación ya viene adentro de esta carpeta.

---

## Paso 2 — Poner la carpeta en el escritorio

Copiá la carpeta completa `Climate3d` al escritorio. No la abras ni muevas archivos de
adentro.

---

## Paso 3 — Doble clic en `ARRANCAR.bat`

Se abre una ventana negra que hace todo sola:

1. Verifica que Docker esté encendido (si está apagado, lo arranca y espera).
2. La **primera vez** carga la aplicación desde `climate3d-image.tar` (tarda un minuto,
   no necesita internet). Las veces siguientes se lo saltea.
3. Te pregunta **dónde guardar los datos**.
4. Pregunta si querés cargar las claves de NASA FIRMS, Copernicus CDS y Earthdata.
   Si no las tenés, apretá **Enter** y listo.
5. Levanta la aplicación y abre el navegador.

No hace falta escribir ningún comando: el lanzador se encarga de cargar la imagen.

Si Windows muestra un cartel azul de "Windows protegió tu PC", tocá **Más información**
→ **Ejecutar de todas formas**. Es normal con archivos que vienen de otra PC.

### Sobre la carpeta de datos

Cuando pregunte dónde guardar los datos, elegí una carpeta **nueva y vacía**, fuera de
esta carpeta. Por ejemplo:

```
C:\climate3d-data
```

Ahí van los datos satelitales (pesan varios GB) y las imágenes que generes. Tiene que
estar en un disco local: **no** en OneDrive ni en una carpeta de red.

---

## Paso 4 — Usar la app

El navegador se abre solo en **http://127.0.0.1:8080**.

Elegís un producto, una fecha y apretás generar. La primera vez que pidas algo, la app
baja los datos que necesite (necesita internet).

---

## Para apagarla

Doble clic en **`APAGAR.bat`**.

Tus datos y tus imágenes **no se borran**: quedan en la carpeta que elegiste.

---

## Si algo no anda

| Qué pasa | Qué hacer |
| --- | --- |
| "Docker Desktop no está instalado" | Instalalo (Paso 1) y volvé a intentar. |
| "Docker no respondió en 3 minutos" | Abrí Docker Desktop a mano, esperá a que diga **Engine running** y volvé a ejecutar `ARRANCAR.bat`. |
| La página no carga | Esperá 30 segundos. Si sigue igual, abrí Docker Desktop y volvé a ejecutar `ARRANCAR.bat`. |
| Quiero cambiar la carpeta o las claves | Volvé a ejecutar `ARRANCAR.bat` y respondé de nuevo. |

---

## Lo que hay en esta carpeta

| Archivo | Para qué |
| --- | --- |
| `ARRANCAR.bat` | **el que tenés que usar** |
| `APAGAR.bat` | para apagarla |
| `climate3d-image.tar` | la aplicación (274 MB). No lo borres: el lanzador lo carga la primera vez. |
| `docker-compose.yml`, `setup.ps1`, `env.example` | configuración; no hace falta tocarlos |
