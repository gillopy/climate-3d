# Validación · deforestación en el Este

- NISAR: 2026-06-19 21:49 UTC → 2026-10-17 21:49 UTC
- Track/frame: 82/101
- Grilla: 80 m/px · EPSG:32721
- Sentinel-2: 2026-06-01 a 2026-06-30 (previo) y 2026-10-01 a 2026-10-31 (posterior), nubes < 40%
- Referencia: NDVI previo ≥ 0.50, posterior ≤ 0.30, ΔNDVI ≤ -0.20; estable: |ΔNDVI| ≤ 0.10
- Producto: HV antes > -25 dB y ΔHV < -2 dB, mayoría 3×3
- Muestras ciegas: 500

## Métricas

| Conjunto | TP | FP | FN | TN | Precisión | Recall | F1 | IoU |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| muestra balanceada | 103 | 103 | 147 | 147 | 0.50 | 0.41 | 0.45 | 0.29 |
| muestra ponderada | 46853 | 245260 | 66867 | 350032 | 0.16 | 0.41 | 0.23 | 0.13 |
| denso (operativo) | 48597 | 420071 | 65124 | 905484 | 0.10 | 0.43 | 0.17 | 0.09 |


La fila **denso** es la operativa. La muestra balanceada (mitad pérdida, mitad estable) infla la precisión; sirve para el recall y el IC.

## IC bootstrap (95 %, muestra balanceada)

- Precisión: 0.50 [0.43, 0.57]
- Recall: 0.41 [0.35, 0.47]
- F1: 0.45 [0.39, 0.50]

## Área

- Referencia: 72781 ha
- Predicción: 299948 ha
- Sesgo: +312.1 %

## Split espacial (muestra balanceada)

- oeste (n=278): F1 0.41, precisión 0.49, recall 0.36
- este (n=222): F1 0.50, precisión 0.51, recall 0.49

## Curva de umbral (mapa denso)

| Umbral (dB) | Precisión | Recall | F1 |
|---:|---:|---:|---:|
| 1 | 0.10 | 0.60 | 0.17 |
| 1.5 | 0.10 | 0.51 | 0.17 |
| 2 | 0.10 | 0.43 | 0.17 |
| 2.5 | 0.11 | 0.37 | 0.16 |
| 3 | 0.11 | 0.32 | 0.16 |
| 4 | 0.11 | 0.26 | 0.15 |
| 5 | 0.11 | 0.21 | 0.15 |
| 6 | 0.11 | 0.18 | 0.14 |

## Límites

- La referencia es **óptica**, no verdad de campo: una cosecha, un anegamiento o un cambio de manejo también bajan el NDVI. No distingue deforestación de otras pérdidas de vegetación.
- Las ventanas de junio y octubre incluyen estacionalidad; parte del cambio óptico y del HV puede ser humedad, no cobertura.
- El bootstrap remuestrea píxeles y no corrige del todo la autocorrelación espacial; el muestreo ya adelgaza la grilla.
- NISAR tiene repetición de 12 días: la fecha de cambio no es diaria.
