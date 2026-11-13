# Validación · deforestación en el Este

- NISAR: 2026-06-19 21:49 UTC → 2026-10-17 21:49 UTC
- Track/frame: 82/101
- Grilla: 80 m/px · EPSG:32721
- Sentinel-2: 2026-06-01 a 2026-06-30 (previo) y 2026-10-01 a 2026-10-31 (posterior), nubes < 40%
- Referencia: NDVI previo ≥ 0.50, posterior ≤ 0.30, ΔNDVI ≤ -0.20; estable: |ΔNDVI| ≤ 0.10
- Producto: HV antes > -15.5 dB y ΔHV < -3 dB, mayoría 3×3
- Muestras ciegas: 500

## Métricas

| Conjunto | TP | FP | FN | TN | Precisión | Recall | F1 | IoU |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| muestra balanceada | 50 | 51 | 200 | 199 | 0.50 | 0.20 | 0.28 | 0.17 |
| muestra ponderada | 22744 | 121439 | 90976 | 473853 | 0.16 | 0.20 | 0.18 | 0.10 |
| denso (operativo) | 20801 | 166056 | 92920 | 1159499 | 0.11 | 0.18 | 0.14 | 0.07 |


La fila **denso** es la operativa. La muestra balanceada (mitad pérdida, mitad estable) infla la precisión; sirve para el recall y el IC.

## IC bootstrap (95 %, muestra balanceada)

- Precisión: 0.49 [0.39, 0.59]
- Recall: 0.20 [0.15, 0.25]
- F1: 0.28 [0.22, 0.34]

## Área

- Referencia: 72781 ha
- Predicción: 119588 ha
- Sesgo: +64.3 %

## Split espacial (muestra balanceada)

- oeste (n=278): F1 0.22, precisión 0.51, recall 0.14
- este (n=222): F1 0.36, precisión 0.48, recall 0.28

## Curva de umbral (mapa denso)

| Umbral (dB) | Precisión | Recall | F1 |
|---:|---:|---:|---:|
| 1 | 0.10 | 0.29 | 0.15 |
| 1.5 | 0.10 | 0.24 | 0.15 |
| 2 | 0.11 | 0.21 | 0.14 |
| 2.5 | 0.11 | 0.19 | 0.14 |
| 3 | 0.11 | 0.18 | 0.14 |
| 4 | 0.11 | 0.17 | 0.13 |
| 5 | 0.11 | 0.16 | 0.13 |
| 6 | 0.11 | 0.15 | 0.13 |

## Límites

- La referencia es **óptica**, no verdad de campo: una cosecha, un anegamiento o un cambio de manejo también bajan el NDVI. No distingue deforestación de otras pérdidas de vegetación.
- Las ventanas de junio y octubre incluyen estacionalidad; parte del cambio óptico y del HV puede ser humedad, no cobertura.
- El bootstrap remuestrea píxeles y no corrige del todo la autocorrelación espacial; el muestreo ya adelgaza la grilla.
- NISAR tiene repetición de 12 días: la fecha de cambio no es diaria.
