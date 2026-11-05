# Sistema de diseño: Climate 3D — consola de render

**Mundo:** instrumento de precisión. Un canvas casi negro, una escalera de superficies y un
solo acento cromático.
**Superficie:** Operate (la persona completa una tarea; la expresión no puede tapar el
trabajo).

## 1. Tema visual y atmósfera

La consola se lee como un instrumento: fondo negro profundo, paneles apenas elevados,
filetes de 1 px y micro-etiquetas en versalitas. No hay tarjetas flotando ni gradientes
decorativos; la jerarquía la llevan la **escalera de superficies** y los filetes. El color
aparece únicamente cuando tiene oficio: acción primaria, foco, selección y estado.

La imagen del satélite es la protagonista cromática. El cromo de la interfaz se retira para
que el render respire; el formulario, en cambio, gana estructura: secciones, etiquetas,
valor actual y ayuda por campo.

## 2. Paleta y oficios

### Superficies

| Token | Hex | Oficio |
| --- | --- | --- |
| `--void` | `#08090a` | Canvas de la aplicación y columna de trabajo. |
| `--carbon` | `#0f1011` | Riel de productos, panel de corridas, ficha técnica. |
| `--obsidian` | `#161718` | Controles, filas seleccionadas, popovers. |
| `--slate` | `#1c1e21` | Hover de controles y filas. |
| `--line` | `#23252a` | Filete base. |
| `--line-strong` | `#34343a` | Filete de foco secundario y bordes de popover. |

### Tinta

| Token | Hex | Oficio |
| --- | --- | --- |
| `--paper` | `#f7f8f8` | Títulos y valores. |
| `--mist` | `#d0d6e0` | Texto principal. |
| `--fog` | `#8a8f98` | Texto secundario, ayudas y metadatos. |
| `--ash` | `#7c818a` | Micro-etiquetas; se subió desde el gris original para sostener AA. |

### Acento y semánticos

| Token | Hex | Oficio |
| --- | --- | --- |
| **`--iris`** | `#5e6ad2` | Único acento: acción primaria, foco, selección, progreso. |
| `--iris-hi` | `#828fff` | Hover y texto de acento sobre oscuro. |
| `--iris-soft` | `rgba(94,106,210,.16)` | Lavado de selección, anillo de foco, chip de valor. |
| `--success` | `#3fb950` | Trabajo listo y dato en disco. |
| `--warn` | `#d29922` | En cola, advertencia. |
| `--danger` | `#f85149` | Error y cancelar. |

Reglas: un solo acento cromático. Los semánticos no se usan como decoración. Violeta y rosa
quedan reservados al dato científico.

## 3. Tipografía

- **Archivo** (variable, 400–700): lectura, títulos y controles. Títulos a `-0.035em`.
- **Archivo Narrow** (variable): micro-etiquetas en versalitas con `letter-spacing` de
  `0.10em` a `0.16em`.
- **Mono del sistema**: ids, rutas, horas, valores numéricos y resumen. Siempre
  `font-variant-numeric: tabular-nums`.

Escala: `27px` título del producto · `16px` nombre en la corrida · `13.5px` base ·
`12.5px` etiquetas de campo y controles · `11.5px` ayuda · `10.5px` metadatos ·
`10px` micro-etiqueta · `9px` rótulo de ficha.

## 4. Componentes

- **Barra superior**: 56 px, canvas, filete inferior. Marca con glifo en lavanda, "render
  console" en versalitas, y a la derecha las píldoras de salud (punto verde para listo,
  ámbar para advertencia) más el reloj UTC / UTC-3 en mono.
- **Catálogo**: lista continua sobre `--carbon`. Fila = miniatura de 44 px con radio 6,
  nombre, dos líneas de resumen y punto de selección. Hover y selección suben un escalón a
  `--obsidian`; la selección suma un filete de 1 px en `--iris` a la izquierda. El buscador
  del riel filtra por nombre, grupo, resumen o id y muestra el conteo `visibles / total`
  con un botón de limpiar. En ≤1120 px se convierte en cinta horizontal.
- **Cabecera del producto**: título de 27 px, resumen, y en la línea de metadatos el
  `grupo · id`, el script en mono y la píldora "pipeline listo". A la derecha,
  **Restablecer** (fantasma, deshabilitado si no hay cambios).
- **Placa**: imagen real dentro de un panel con radio 14, filete y fondo `#050607`; alto
  máximo `clamp(260px, 50vh, 560px)`. El pie en mono dice "salida real de este producto" y
  la variante elegida.
- **Ficha técnica**: cuatro celdas (grupo, datos en disco, última fecha, origen) en una
  caja `--carbon` con filetes verticales y valores en mono.
- **Inspector de receta**: el formulario se agrupa en paneles por sección —**Fuente de
  datos**, **Salida & geometría**, **Tiempo (UTC)**, **Movimiento & animación** y "Otras
  opciones"—. Cada panel lleva en la cabecera el número (`01`), el título en versalitas, una
  píldora con la cuenta (`4 parámetros`) y una descripción corta alineada a la derecha;
  debajo, una grilla `auto-fit minmax(232px, 1fr)` de tarjetas.
- **Campo**: tarjeta sobre `--obsidian` con filete y radio 10; etiqueta de 12.5 px + valor
  actual + ayuda de 11.5 px. Al enfocar cualquier control, el filete de la tarjeta pasa a
  `--iris-line`. Si el valor difiere del default, aparece un punto lavanda y un enlace
  **restablecer**; el botón global restauran todos. Los controles deshabilitados por otro
  parámetro quedan al 38 % y no reciben interacción.
- **Slider**: riel de 4 px con relleno lavanda hasta el valor, perilla redonda y chip mono
  con la unidad (`144 h`, `12 fps`, `6 %`). Los extremos muestran el mínimo y el máximo
  (`0 %` / `20 %`) en mono a los costados. El relleno se calcula con `--fill`.
- **Desplegable**: control oscuro con chevron dibujado en CSS; lista flotante sobre
  `--obsidian` con filete fuerte y sombra profunda. Opción activa en `--slate`, opción
  elegida con punto lavanda. Conserva `combobox`/`listbox` y flechas, Home/End, Enter,
  Escape.
- **Fechas**: control compacto de dos extremos (`Desde 4 NOV 2026 → Hasta 5 NOV 2026`) con
  contador de días en píldora. Cada extremo abre su calendario en un popover que se
  posiciona arriba si no hay lugar. En fecha única hay un solo control con icono.
- **Calendario**: grilla de 7 columnas desde el lunes, celdas de 28–30 px, mes en
  versalitas con navegación. Dentro del rango: lavado lavanda; extremos: lavanda pleno;
  fuera del rango: apagado. Punto verde cuando la fecha ya está en disco; futuros y
  anteriores al mínimo quedan deshabilitados.
- **Interruptor**: píldora de 38×22; apagado = perilla gris sobre `--obsidian`; encendido =
  riel lavanda y perilla blanca.
- **Pie pegajoso**: resumen de la receta en chips (`clave` en versalitas + `valor` en mono)
  a la izquierda y **Generar** a la derecha con atajo `Ctrl ↵`. Fondo translúcido con
  `backdrop-filter`, filete superior y sombra suave hacia arriba.
- **Corridas**: lista con punto de estado, nombre, hora y etapa; selección con fondo
  elevado y filete lavanda de 1 px. Debajo, el detalle: nombre, id en mono, píldora de
  estado, barra de progreso de 6 px, plan numerado, consola y artefactos.
- **Estado**: píldora con punto y color semántico (`en cola` ámbar, `corriendo` lavanda,
  `listo` verde, `error` rojo, `cancelado` gris).
- **Consola**: bloque `#050607`, mono de 10.5 px, alto fijo de 224 px, scroll propio y
  rutas envueltas (`pre-wrap`). Cada línea lleva hora y etiqueta de severidad —`INF`, `WRN`,
  `ERR`— además del color: advertencias en ámbar y errores en rojo.
- **Artefactos**: miniatura o video dentro de un panel; el pie muestra nombre, peso y un
  enlace **Bajar** que descarga el archivo con su nombre real.

## 5. Retícula y ritmo

Tres columnas: `288px · 1fr · 408px` en escritorio, `264 · 1fr · 372` por debajo de 1380 px.
Por debajo de 1120 px colapsa a una columna, el catálogo pasa a cinta y el pie deja de
pegarse. Cada columna scrollea sola; el alto total es la ventana menos la barra de 56 px.

Aire: `20px` de margen lateral, `18px` entre campos, `22px` entre secciones, `16px` entre
bloques del panel. Radios: 6 px controles, 10 px fichas, 14 px placa, píldora para estados y
chips.

Elevación: casi nula. Solo los popovers y el pie pegajoso proyectan sombra, y existe para
decir "esto flota" o "debajo hay más".

## 6. Movimiento

Dos gestos, ninguno decorativo: el pulso del estado en curso (1.8 s) y el avance del
progreso (400 ms). Todo lo demás cambia en 120–160 ms. Con `prefers-reduced-motion` se
apaga.

## 7. Accesibilidad

- Contraste AA: `--mist` sobre `--void` ≈ 14:1; `--fog` ≈ 6:1; `--ash` ≈ 5:1.
- Foco visible con anillo lavanda de 2 px y `outline-offset` de 2 px.
- Cada campo tiene `label` asociada por `for`/`id` y `aria-describedby` para la ayuda.
- El desplegable expone `role="combobox"`, `aria-expanded` y `aria-activedescendant`.
- El calendario es una grilla de botones con `aria-label` completo y `aria-pressed`.
- El progreso es `role="progressbar"` con `aria-valuenow`; el interruptor es `role="switch"`
  con `aria-checked`.
- El resumen de la receta es texto, no depende del color; los estados suman etiqueta escrita.
