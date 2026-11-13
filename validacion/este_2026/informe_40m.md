# Validación · deforestación en el Este

- NISAR: 2026-06-19 21:49 UTC → 2026-10-17 21:49 UTC
- Track/frame: 82/101
- Grilla: 40 m/px · EPSG:32721
- Sentinel-2: 2026-06-01 a 2026-06-30 (previo) y 2026-10-01 a 2026-10-31 (posterior), nubes < 40%
- Referencia: NDVI previo ≥ 0.50, posterior ≤ 0.30, ΔNDVI ≤ -0.20; estable: |ΔNDVI| ≤ 0.10
- Producto: HV antes > -15.5 dB y ΔHV < -3 dB, mayoría 3×3
- Muestras ciegas: 500

## Métricas

| Conjunto | TP | FP | FN | TN | Precisión | Recall | F1 | IoU |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| muestra balanceada | 42 | 43 | 208 | 207 | 0.49 | 0.17 | 0.25 | 0.14 |
| muestra ponderada | 84707 | 399006 | 419506 | 1920799 | 0.18 | 0.17 | 0.17 | 0.09 |
| denso (operativo) | 95979 | 694886 | 408235 | 4558004 | 0.12 | 0.19 | 0.15 | 0.08 |


La fila **denso** es la operativa. La muestra balanceada (mitad pérdida, mitad estable) infla la precisión; sirve para el recall y el IC.

## IC bootstrap (95 %, muestra balanceada)

- Precisión: 0.49 [0.39, 0.60]
- Recall: 0.17 [0.12, 0.21]
- F1: 0.25 [0.19, 0.31]

## Área

- Referencia: 80674 ha
- Predicción: 126538 ha
- Sesgo: +56.9 %

## Split espacial (muestra balanceada)

- oeste (n=272): F1 0.18, precisión 0.40, recall 0.12
- este (n=228): F1 0.31, precisión 0.56, recall 0.21

## Curva de umbral (mapa denso)

| Umbral (dB) | Precisión | Recall | F1 |
|---:|---:|---:|---:|
| 1 | 0.11 | 0.29 | 0.16 |
| 1.5 | 0.11 | 0.25 | 0.16 |
| 2 | 0.12 | 0.22 | 0.15 |
| 2.5 | 0.12 | 0.20 | 0.15 |
| 3 | 0.12 | 0.19 | 0.15 |
| 4 | 0.12 | 0.18 | 0.14 |
| 5 | 0.12 | 0.16 | 0.14 |
| 6 | 0.13 | 0.15 | 0.14 |

## Límites

- La referencia es **óptica**, no verdad de campo: una cosecha, un anegamiento o un cambio de manejo también bajan el NDVI. No distingue deforestación de otras pérdidas de vegetación.
- Las ventanas de junio y octubre incluyen estacionalidad; parte del cambio óptico y del HV puede ser humedad, no cobertura.
- El bootstrap remuestrea píxeles y no corrige del todo la autocorrelación espacial; el muestreo ya adelgaza la grilla.
- NISAR tiene repetición de 12 días: la fecha de cambio no es diaria.
