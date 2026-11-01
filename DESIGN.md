# Sistema de diseño: Climate 3D — consola de render

**Mundo:** la carta de tiempo significativo (SIGWX) impresa y la mesa de análisis.
**Superficie:** Operate (la persona completa una tarea; la expresión no puede tapar el trabajo).

## 1. Tema visual y atmósfera

Dos superficies y una sola idea: una **mesa de tinta azul-noche** donde vive el trabajo, y una
**hoja de carta clara** donde vive el dato. El catálogo y la corrida son mesa; el producto, su
muestra y su receta son hoja. No hay tarjetas flotando: hay columnas separadas por líneas de
1 px, como el reticulado de una carta.

La densidad es alta y el ruido bajo: rótulos en versalitas condensadas, filetes finos, y una
sola pieza con movimiento — la **traza**, una línea de frente que avanza sobre un tramo rayado
a medida que corre el trabajo. Lo demás es quieto.

La luz es nocturna porque la escena lo es: alguien mirando discos que brillan en una pantalla
apagada. El papel de la hoja no es decorativo: es donde se leen los números.

## 2. Paleta y oficios

| Nombre | Hex | Oficio |
| --- | --- | --- |
| Tinta de carta | `#0b1420` | Fondo de la mesa (barra, catálogo, corrida). |
| Tinta elevada | `#101c2b` | Fila de catálogo en hover. |
| Tinta activa | `#16263a` | Fila de catálogo seleccionada. |
| Filete de mesa | `#25384d` | Separadores y bordes sobre tinta. |
| Filete tenue | `#1b2b3d` | Separadores internos de listas. |
| Papel de carta | `#f1f3f0` | Hoja de trabajo: formulario y ficha. |
| Papel hundido | `#eceee9` | Ficha y pie de la hoja. |
| Filete de papel | `#c8cfc6` | Bordes y reglas sobre la hoja. |
| Tinta de imprenta | `#0b1420` | Texto y títulos sobre la hoja. |
| Tinta de papel media | `#4b5761` | Rótulos y texto secundario sobre la hoja. |
| Tinta de papel tenue | `#66727c` | Ayudas de campo sobre la hoja. |
| Texto de mesa | `#e8eef4` | Texto principal sobre tinta. |
| Texto de mesa medio | `#93a5b4` | Descripciones y metadatos sobre tinta. |
| Texto de mesa tenue | `#7b8fa3` | Rótulos de grupo y numeración. |
| **Frente frío** | `#1f5fd0` | Acción primaria, foco, progreso en curso, selección viva. |
| Frente profundo | `#17489e` | Hover de la acción primaria. |
| Lavado de frente | `#dde6f6` | Interruptor encendido sobre la hoja. |
| **Frente cálido** | `#c2382e` | Error, cancelar, aviso. |
| Lavado cálido | `#f6e0dd` | Fondo de avisos y del botón cancelar en hover. |
| Calma | `#2f7a55` | Trabajo listo. |
| Retenido | `#b47f22` | En cola, advertencia. |

Reglas: **el color hace oficio, nunca ambienta**. Violeta y rosa no entran: el dato ya los usa.
Sobre la mesa, el verde y el ámbar aparecen con brillo propio (`#6fbe95`, `#e0796f`) para
alcanzar contraste AA sobre tinta.

Los estados se dibujan con el vocabulario de la carta: **rayado a 45°** para lo que espera,
**tramo azul con punta de frente** para lo que corre, **verde pleno** para lo terminado y
**rojo** para el error. El mismo rayado se repite en la clave de estados y en la traza.

## 3. Tipografía

Dos voces, ninguna de sistema:

- **Archivo** (variable, 400–700): lectura y controles. Títulos a `-0.025em`; cuerpo `13.5px/1.5`.
- **Archivo Narrow** (variable, 400–700): rótulos, nombres de producto, cifras y sellos.
  Versalitas con `letter-spacing` de `0.10em` a `0.18em`.
- **Mono del sistema** sólo para lo que es dato técnico: rutas de script, id del job, log.
  `font-variant-numeric: tabular-nums` en todo número que cambie.

Escala: `29px` título de la hoja (24px en pantallas angostas) · `17px` nombre de producto en la
corrida · `14.5px` ítem del catálogo · `13.5px` control · `12.5px` cuerpo secundario · `11px`
rótulo en versalitas · `9.5px` rótulo de la ficha.

No hay eyebrow sobre los títulos: el título carga solo. Los rótulos existen para los campos,
no para decorar encabezados.

## 4. Componentes

- **Catálogo**: lista continua sin tarjetas. Fila = miniatura de 46 px, nombre, dos líneas de
  resumen, marca de 8 px. Agrupado por `grupo` con un rótulo en versalitas. Selección: fila más
  clara + miniatura y marca en azul. Hover: un escalón de tinta. En ≤1080 px se convierte en
  cinta horizontal de 196 px por ficha.
- **Hoja**: cabecera con título y la receta técnica en mono; **placa** de borde a borde con
  marco de 16:9 y marcas de registro en las esquinas; **ficha** de cuatro celdas con filetes
  verticales (grupo, datos en disco, última fecha, origen); campos; pie con la acción.
- **Campos**: rótulo en versalitas + control nativo. Sin cajas envolventes. Selects y fechas
  sobre papel blanco con borde de 1 px y radio de 6 px; foco con anillo azul de 2 px.
- **Interruptor**: cuadrado de 46×24 con perilla cuadrada; encendido = lavado azul + perilla
  azul. No es una píldora: la píldora está reservada a etiquetas pequeñas.
- **Acción primaria**: azul pleno, versalitas de Archivo Narrow, radio de 12 px, ancho mínimo
  190 px. En el pie pegajoso, siempre a la vista mientras se recorre la hoja.
- **Traza**: la firma. Riel de 12 px con rayado de espera; el tramo recorrido es un lavado azul
  con borde derecho de 2 px y una fila de puntas de frente en su base. Termina en verde o rojo
  según el estado final. Transición de 400 ms `cubic-bezier(.16,.84,.28,1)`.
- **Sello de estado**: etiqueta con doble borde, versalitas muy espaciadas y rotación de
  `-2.5°`. Aparece con un golpe de 220 ms (`scale 1.18 → 1`) sólo en estados terminales.
- **Consola**: bloque sobre tinta más oscura, mono de 11 px, `white-space: pre` con scroll
  propio; hora en gris azulado, advertencia en ámbar, error en rojo.
- **Placas de salida**: imágenes y videos con pie en mono y peso en bytes.

## 5. Retícula y ritmo

Tres columnas: `296px · 1fr · 412px` a 1440 px; `264 · 1fr · 372` a 1280; una sola columna por
debajo de 1080 (catálogo en cinta, hoja, corrida). Cada columna scrollea sola; el alto total es
la ventana menos la barra de 62 px. Aire: `26px` de margen lateral en la mesa y la hoja, `18px`
entre campos, `22px` antes de un bloque nuevo, `14px` después.

Radios: 12 px en botones y contenedores, 6–8 px en controles y miniaturas, 3 px en sellos.

Elevación: **una**. La hoja no flota sobre la mesa (son columnas, no tarjetas). La única sombra
es la del pie pegajoso cuando la hoja scrollea (`0 -14px 20px -14px`), y existe para decir
"debajo hay más".

## 6. Movimiento

Dos momentos, ninguno decorativo:

1. La traza avanza 400 ms con ease-out exponencial al cambiar de progreso.
2. El sello aterriza 220 ms al terminar la corrida.

Todo lo demás cambia en 120–140 ms. Con `prefers-reduced-motion` los tres se apagan.

## 7. Accesibilidad

- Contraste AA: texto principal 14:1 sobre la hoja y 13:1 sobre la mesa; secundarios ≥4.8:1.
- Foco visible con anillo azul de 2 px y `outline-offset` de 2 px en todo control.
- Cada campo tiene `label` asociada por `for`/`id` y `aria-describedby` para la ayuda.
- El progreso es `role="progressbar"` con `aria-valuenow`, `aria-valuemin` y `aria-valuemax`.
- El interruptor es `role="switch"` con `aria-checked` y nombre accesible.
- Selección de texto y `caret` en azul de frente; scrollbars finas por superficie.
