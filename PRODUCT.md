# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

**Inferido del repositorio, sin confirmar en entrevista.** Un autor individual (usuario-herramienta) que
produce pósters e animaciones de satélite y de modelos meteorológicos desde su máquina Windows. Trabaja
sobre datos que ya están en un disco compartido, con un entorno virtual de Python por delante, y conoce
los productos por nombre (GOES, MUR, ECMWF, PACE, Himawari). Usa la consola en tandas cortas: elige un
producto, ajusta la receta, lanza el trabajo y vuelve a mirar cuando termina. Posibles colaboradores
ocasionales reciben la misma máquina o sus resultados, no una cuenta.

## Product Purpose

La app es la consola interactiva de un pipeline que ya existe. Convierte un pedido en lenguaje humano
(producto + parámetros) en los comandos reales de `descargar/`, `cuadros/` y `animar/`, los ejecuta con
el `.venv` del repo y devuelve los PNG/MP4 en la misma pantalla. Existe para no tener que recordar flags,
rutas ni nombres de archivo, y para que un trabajo largo se pueda lanzar y seguir sin bloquearse.
Éxito = el render correcto aparece sin abrir una terminal.

## Positioning

El catálogo es un contrato de datos, no una colección de botones: cada producto declara **sólo** los
parámetros que su script acepta, la interfaz arma el formulario a partir de ese esquema y un producto
nuevo aparece sin tocar el formulario. El trabajo corre el comando real del repo (no una reimplementación),
transmite progreso y log por SSE, y cachea renders por firma de producto + parámetros. Una herramienta
de vecino no podría copiar el catálogo sin copiar el pipeline.

## Operating Context

- Windows, PowerShell, un `.venv` en la raíz del repo para el pipeline y otro en `app/.venv` para la app.
- Una carpeta de datos externa (`CLIMATE3D_DATOS`) con crudos y salidas; su ausencia es un estado normal.
- Los jobs se encolan de a uno: descargas y renders de varios minutos, con log como superficie principal
  de diagnóstico.
- El trabajo se lee de reojo mientras corre; el resultado final se abre y se compara con otros productos.
- El idioma de la interfaz es español rioplatense; los nombres de producto y los logs vienen del pipeline.

## Capabilities and Constraints

- 12 productos en cuatro grupos: satélite, modelo, color y vegetación.
- Controles soportados: `select`, fecha, rango de fechas, toggle y slider; los tipos y límites vienen del
  backend y no se inventan en el cliente.
- Estados de trabajo: `queued`, `running`, `done`, `error`, `cancelled`; un solo job activo a la vez.
- Salidas: PNG sueltos, series de cuadros y video (`mp4`/`gif`), servidas desde `/media`.
- El pipeline y el catálogo funcionan y **no se tocan** en un rediseño visual; el contrato HTTP y la
  lógica de jobs son restricciones duras.
- Sin framework de estilos ni librería de componentes: React + CSS propio.

## Brand Commitments

- Nombre: **Climate 3D**. Se conserva.
- Interfaz en español; los identificadores técnicos (scripts, ids, logs) se copian tal cual.
- El producto son imágenes científicas reales; la interfaz no debe competir con ellas ni decorarlas.

## Evidence on Hand

- `app/web/public/previews/*.webp`: una muestra real por producto (12), generadas desde renders.
- `docs/galeria/`: renders reales a resolución completa (GOES, MUR, PACE, ECMWF, viento, Himawari).
- `app/README.md` y `GUIA.md`: flujos, flags y comportamiento real de cada script.

## Product Principles

1. **El dato es el protagonista.** El cromo de la interfaz se retira: la imagen generada y sus parámetros
   mandan, la herramienta no.
2. **Nada inventado.** Si el script no acepta un flag, la interfaz no muestra ese control.
3. **El trabajo largo se vigila, no se espera.** Estado, etapa y log siempre visibles sin tapar el render.
4. **Idioma del oficio.** Nombres técnicos exactos, sin traducciones ni adornos que confundan.
5. **Densidad con calma.** Mucha información (12 productos, muchos parámetros) sin ruido ni scroll infinito.

## Accessibility & Inclusion

**Inferido.** Uso local con teclado y mouse; controles nativos (select, date, range, botón) ya accesibles.
Un rediseño debe conservar foco visible, etiquetas asociadas y contraste AA sobre el fondo elegido.
