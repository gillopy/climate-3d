# Caso de estudio · Desmonte en el Chaco con NISAR

Página estática de un solo caso. No tiene backend, no descarga nada y no depende de
internet: **abre `index.html` y funciona**.

Es independiente de la demo congelada que vive en `demo/` (esa es la consola completa de
Climate 3D en Cloudflare). Esta carpeta solo cuenta un hallazgo, con su método.

## Cómo verla

Doble clic en `index.html`.

O servila junto con el resto de `demo/`:

```powershell
.\.venv\Scripts\python.exe -m http.server 8788 --directory demo --bind 127.0.0.1
```

Y abrís `http://127.0.0.1:8788/caso-chaco/`.

## Qué cuenta

| Sección | Qué prueba |
| --- | --- |
| Hero | Slider del Chaco con la misma escala de grises y las tres cifras base |
| 01 · Área de estudio | Polígono del desmonte y de control, a 9,8 km |
| 02 · Método | La cadena completa, con parámetros y fórmula |
| 03 · Cuándo ocurrió | Los cinco pares de 12 días y el escalón de pérdida |
| 04 · Contra el control | 262,9 ha contra 2,1 ha |
| 05 · Cuánto pesa el umbral | Barrido de 2 a 5 dB, MMU y corrección por control |
| 06 · Firma polarimétrica | ΔHV contra ΔHH en desmonte, caja y control |
| 07 · Distribución | Histograma de ΔHV del Chaco |
| 08 · Por qué 12 días | 89/64 ha a 12 días contra 188/24.751 ha a 276 días |
| 09 · Segunda escena | Slider del Este, comparación y barrido propio |
| 10 · La escala | Distribución de tamaños de bloque e histograma del Este |
| 11 · Lo que no se ve | Limitaciones declaradas |

## Estructura

```
demo/caso-chaco/
  index.html      la página
  styles.css      estilos
  app.js          render de stats, slider, mapa SVG, barras, tabla, histograma
  data.js         números del caso Chaco (única fuente de verdad)
  tecnico.js      indicadores del Chaco, calculados por tools/tecnico.py
  este.js         segundo caso: Este de Paraguay, 10 m/px
  tools/tecnico.py  calcula sensibilidad, MMU, firma polarimétrica e histograma
  img/            recortes antes/después y máscaras ya renderizadas
```

`data.js` y `tecnico.js` son lo único que hay que tocar para cambiar cifras.

## Indicadores técnicos

`tools/tecnico.py` lee el mismo par de escenas que el pipeline y calcula, sobre las
mismas máscaras:

- **Barrido de umbral** de 2 a 5 dB, en el desmonte y en el control.
- **Componentes conexas** de 8 vecinos y unidad mínima de mapeo de 0,5 ha.
- **Firma polarimétrica**: ΔHV, ΔHH y Δ(HV−HH) sobre los píxeles de pérdida.
- **Distribución** de ΔHV sobre píxeles de bosque, en intervalos de 0,5 dB.
- **Corrección por control**: tasa de falsos positivos medida en bosque intacto.

Regenerarlo:

```powershell
$dir = "D:\Users\guill\dataset era5\nisar\NISAR_L2_GCOV_PROVISIONAL_V1"
& .\.venv\Scripts\python.exe demo\caso-chaco\tools\tecnico.py `
    --antes  "$dir\NISAR_..._010_..._20260120....h5" `
    --despues "$dir\NISAR_..._015_..._20260321....h5" `
    --out demo\caso-chaco\tecnico.js
```

El script no necesita scipy: si no está, etiqueta las componentes conexas con numpy puro.

## Segundo caso: Este de Paraguay

Par `2026-07-10 → 2026-08-27`, track 031 / frame 4005, 10 m/px, caja de 76.668 ha.
El objetivo es probar que el método no es un truco de una escena.

- Pérdida bruta a 3 dB: **1.069,8 ha**.
- Componentes conexas: **28.461**; sobreviven a 0,5 ha: **89** → **291,5 ha**.
- Control (1.892 ha de bosque): 707 fragmentos, **0** llegan a 0,5 ha → **0,0 ha**.
- Firma: ΔHV −4,25 dB, ΔHH −2,57 dB, Δ(HV−HH) −1,68 dB.
- Remuestreando de 10 a 20 m, la pérdida bruta cae de 1.069,8 a **639 ha**: el conteo de
  píxeles depende de la escala, los componentes coherentes no.

Regenerarlo con el mismo script:

```powershell
& .\.venv\Scripts\python.exe demo\caso-chaco\tools\tecnico.py `
    --antes  "$dir\NISAR_..._025_031_A_165_4005_..._20260710....h5" `
    --despues "$dir\NISAR_..._029_031_A_165_4005_..._20260827....h5" `
    --bbox    "-55.545502,-24.292034,-55.309296,-23.982488" `
    --control "-55.4156,-24.1527,-55.3802,-24.1063" `
    --out demo\caso-chaco\este.js
```

Los números manuales de `este.js` salen de esa corrida; el script escribe el mismo
esquema que `tecnico.js`, con `caso` y `control`.

## De dónde salen las cifras

Escena NISAR L2 GCOV, track 161 / frame 167, banda HV, 20 m/px, umbral 3 dB,
HV mínimo −15,5 dB. Colección `NISAR_L2_GCOV_PROVISIONAL_V1`.

- Desmonte: `-61.12896,-20.856085,-61.062527,-20.81036`
- Control: `-61.182518,-20.938034,-61.099777,-20.883834`

Los pares de 12 días van del 20 de enero al 21 de marzo de 2026.

## Cómo se regeneran las imágenes

```powershell
$py  = ".\.venv\Scripts\python.exe"
$bbx = "-61.12896,-20.856085,-61.062527,-20.81036"

# recortes antes/después (misma escala de grises en las dos fechas)
& $py prototipos\poster_nisar.py --h5 "$dir\...010...h5" `
    --bbox $bbx --pol HV --modo gris --db-min -17 --db-max -9 `
    --out demo\caso-chaco\img\antes_0120.png

# máscara acumulada
& $py prototipos\nisar_cambio.py --antes "$dir\...010...h5" --despues "$dir\...015...h5" `
    --bbox $bbx --px 1600 --modo mascara --umbral 3 --hv-min -15.5 `
    --out demo\caso-chaco\img\mascara_total.png
```

## Reglas que la página respeta

- **Nada inventado.** Cada hectárea y cada porcentaje salen de `data.js` o `tecnico.js`.
- **Misma escala.** Los dos recortes del slider usan el mismo rango en dB.
- **Control declarado.** Aparece en el mapa, en la sección 03 y en la corrección.
- **Umbral justificado.** No se elige un umbral: se muestra el barrido completo.
- **Limitaciones visibles.** La sección 09 no esconde el sesgo de humedad ni el estado
  provisional del producto.
- **Sin dependencias.** Sin fuentes externas, sin CDN, sin analítica.

## Pendiente

- Validación óptica con Sentinel-2 del 20-ene y del 21-mar (matriz de confusión).
- Exportar el GeoJSON de la máscara para que un tercero pueda verificarla.
- Coherencia interferométrica con GUNW (requiere otro producto, no disponible aún).
- Versión en inglés para el jurado global.
