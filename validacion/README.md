# Validación NISAR

Scripts reproducibles para medir los productos NISAR contra una referencia
independiente. No hay verdad de campo: la referencia es **Sentinel-2 L2A**
(NDVI pre/post, enmascarado con SCL), que es otro sensor y otra física.

## Deforestación en el Este

```powershell
.venv\Scripts\python.exe validacion\deforestacion_este.py `
  --antes  ANTES.h5 `
  --despues DESPUES.h5 `
  --bbox "-55.8,-24.8,-55.0,-23.8" `
  --px 2000 `
  --pre-desde 2026-06-01 --pre-hasta 2026-06-30 `
  --post-desde 2026-10-01 --post-hasta 2026-10-31 `
  --nubes 40 --hv-min -15.5 --umbral 3 --muestras 250 `
  --out validacion\este_2026
```

- `--antes` / `--despues`: dos GCOV del mismo track/frame y misma colección.
- Referencia: NDVI previo ≥ 0.50, posterior ≤ 0.30, ΔNDVI ≤ -0.20; estable
  |ΔNDVI| ≤ 0.10. Los bordes se limpian con mayoría 3×3.
- Producto: HV antes > `--hv-min` y ΔHV < `-umbral`, mayoría 3×3.
- La primera corrida baja Sentinel-2 y deja `ndvi_pre.npy` / `ndvi_post.npy`
  como caché; las siguientes son rápidas. `--refrescar` las ignora.

Salidas: `informe.md`, `metricas.json`, `muestras.csv` (con lon/lat),
`comparacion.png`, `errores.png`, `curva.png`, `dispersion.png`.

## Primer resultado (82/101, 2026-06-19 → 2026-10-17)

| Grilla | Precisión densa | Recall denso | F1 denso | Área ref | Área pred | Sesgo |
|---|---:|---:|---:|---:|---:|---:|
| 40 m | 0.12 | 0.19 | 0.15 | 80.674 ha | 126.538 ha | +56,9 % |
| 80 m | 0.11 | 0.18 | 0.14 | 72.781 ha | 119.588 ha | +64,3 % |

La muestra balanceada da precisión ~0,49, pero **no es operativa**: sobrerrepresenta
la pérdida. La fila densa es la que manda. Con `hv_min -25` y umbral 2 el recall
sube a 0,43, pero el área predicha se va a +312 %.

**Conclusión:** con estos defaults el cambio NISAR **no es un detector de
deforestación**; es un mapa de cambio/screening. La referencia óptica también
incluye cosechas, anegamientos y estacionalidad, así que no es verdad de campo.
El próximo paso es serie/CUSUM, máscara de bosque, misma estación y una
referencia anual (MapBiomas/GFW) o interpretación visual de polígonos.

## Límites

- Referencia óptica, no campo; una cosecha o el agua también bajan el NDVI.
- Junio→octubre mezcla estacionalidad y humedad con cobertura.
- Bootstrap de píxeles: no corrige del todo la autocorrelación espacial.
- NISAR repite cada 12 días; la fecha de cambio no es diaria.
