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

## Caja del Este (10 m, 2026-06-28 → 2026-08-27)

Misma validación con las fechas exactas de la óptica (S2 del 28-jun y del 27-ago),
track 031/165, caja `-54.688225,-24.5212,-54.600334,-24.398071`:

| Producto | Área predicha | Referencia NDVI | Precisión densa | Recall | Sesgo |
|---|---:|---:|---:|---:|---:|
| HV > −15,5 dB y ΔHV < −3 dB (defaults) | 4.764 ha | 328 ha | 0,03 | 0,38 | +1350 % |
| + bosque por NDVI > 0,55 + ΔNDVI ≤ −0,20 + MMU 0,5 ha | 138 ha | 328 ha | — | — | −58 % |

La primera fila es la que el visor pintaba como "cambio de dosel": 93 % de esos
píxeles no tienen pérdida de NDVI. La segunda es el producto con confirmación
óptica (`prototipos/nisar_cambio.py --verificar-s2 --mmu-ha 0.5`): pinta bloques
coherentes y queda del orden de la referencia. Queda conservador (menos área que
la referencia) porque exige NDVI > 0,55 antes del cambio.

El script de validación usa ahora [`comun/sentinel2.py`](../comun/sentinel2.py)
(el módulo compartido); antes importaba `nisar_fusion.STAC`, que ya no existe.

## Corrimiento del par y multilook (2026-11)

Dos pasadas del mismo track/frame **no salen al mismo nivel radiométrico**. En
estas escenas la mediana de ΔHV es −3,1 dB en la caja grande del Este y −2,6 dB
en la caja chica: la escena de agosto está más oscura que la de junio. Un umbral
fijo sin restar ese offset mide el offset, no la deforestación.

Regla nueva (`nisar_cambio.py` por defecto): multilook 5×5 en potencia (~50 m,
σ de ΔHV baja de 3,3 a 1,7 dB), se resta la mediana de ΔHV y recién ahí se
umbrala. La MMU de 0,5 ha aplica siempre.

Misma caja chica (10 m, 2026-06-28 → 2026-08-27), referencia NDVI 1.033 ha:

| Regla | Área predicha | Precisión densa | Recall | F1 | Sesgo |
|---|---:|---:|---:|---:|---:|
| HV > −15,5 dB y ΔHV < −3 dB, 1 mirada (viejo) | 4.770 ha | 0,15 | 0,70 | 0,25 | +362 % |
| ΔHV normalizado, multilook 5, umbral 2 dB (nuevo) | 4.340 ha | 0,17 | 0,70 | 0,27 | +320 % |

```powershell
.venv\Scripts\python.exe validacion\deforestacion_este.py `
  --antes ANTES.h5 --despues DESPUES.h5 `
  "--bbox=-54.688225,-24.5212,-54.600334,-24.398071" --px 2000 `
  --pre-desde 2026-06-01 --pre-hasta 2026-06-30 `
  --post-desde 2026-10-01 --post-hasta 2026-10-31 `
  --umbral 2 --out validacion\este_2026
```

**Lo que cambia y lo que no.** El F1 denso del radar solo casi no se mueve: con
este paisaje y esta resolución, ΔHV no alcanza para separar deforestación de
cosecha/estacionalidad. Lo que arregla la normalización es la *estabilidad*: el
mismo umbral significa lo mismo en cualquier par, y dos corridas con y sin
`--verificar-s2` dejan de ser incomparables (antes la verificación reemplazaba
la máscara de bosque por NDVI > 0,55, que en la estación seca es el 6 % del
área). Con confirmación óptica el producto queda en rojo = pérdida confirmada
(117 ha en la caja de 4 km del visor) y naranja = candidata (364 ha), en vez de
618 ha todas rojas.

**Índices descartados.** Se probó RFDI `(HH−HV)/(HH+HV)`, que la literatura
L-band propone para bosque amazónico denso (`1-s2.0-S0034425725005371`). Contra
la referencia NDVI de esta caja discrimina peor que el azar: AUC 0,41-0,47 para
el cambio y 0,44-0,47 para bosque/no bosque. RVI tampoco mejora a ΔHV
(AUC 0,59-0,60). Por eso el detector sigue siendo ΔHV.

**Confirmación temporal.** `--confirmar-temporal N` remide la caída contra la
misma escena base en las N fechas posteriores (mismo track/frame, ya en disco).
En la caja de 4 km del visor (2026-06-28 → 2026-08-27, control 2026-10-02):

| | pérdida confirmada | candidata | radar |
|---|---:|---:|---:|
| sin persistencia | 117 ha | 364 ha | 494 ha |
| 1 fecha posterior | 81 ha | 246 ha | 340 ha |
| 2 fechas posteriores | 14 ha | 100 ha | 128 ha |

Con dos fechas el filtro es demasiado estricto para datos PROVISIONAL: la
escena del 2026-10-14 viene +3,2 dB en HV y +2,0 dB en HH respecto de la del
2026-10-02 (no es un simple corrimiento, cambia el contraste), así que solo el
26 % de los candidatos sigue 2 dB abajo de la base. Por eso el default es **1**.

**Límites del resultado.** La referencia NDVI exige NDVI previo ≥ 0,50: en la
estación seca la mediana de la caja es 0,45, así que la referencia misma es
conservadora. Los compuestos NDVI pre/post correlacionan solo 0,26 entre sí:
parte de la "referencia" es cambio fenológico. Con dos fechas no se puede exigir
persistencia temporal, que es lo que el método NASA usa para bajar falsos
positivos.

## Baseline temporal y guard de inundación (2026-11)

`prototipos/nisar_cambio.py` ahora puede medir el cambio contra la mediana de
varias fechas (`--baseline N`, mediana por píxel en potencia, la de `--antes`
incluida, fechas ya en disco del mismo par) y apartar la firma de doble
rebote (`--guardia-hh X`), siguiendo a Flores-Anderson et al. (RSE 333, 2026).
El harness mide ambos contra la misma referencia NDVI. Par 31/165, caja chica
del visor, referencia NDVI pre 2026-08-01..26 / post 2026-10-03..31 (68 ha de
pérdida de referencia):

| Radar | Área predicha | Precisión densa | Recall | Sesgo |
|---|---:|---:|---:|---:|
| par 2026-08-27 → 10-02 | 189 ha | 0,00 | 0,01 | +177 % |
| + baseline 3 fechas (06-28, 07-10, 08-15) + CoV 0,40 | 134 ha | 0,00 | 0,00 | +96 % |
| + guardia-hh 3 dB | 134 ha | 0,00 | 0,00 | +96 % |
| par 2026-08-27 → 10-26 | 160 ha | 0,00 | 0,01 | +134 % |
| + baseline 3 fechas + CoV 0,40 | 181 ha | 0,00 | 0,00 | +165 % |

**Qué se puede afirmar.** En el par corto el baseline reduce el exceso de
detección (−29 % de área pintada); en el par largo el piso más estable hace
subir el área (+13 %): el efecto es real pero depende de la ventana. El F1
denso queda en 0,00 en todas las filas: contra esta referencia — estacional y
conservadora, NDVI pre ≥ 0,50 en agosto con mediana de caja ~0,45 — ningún
ΔHV, par o baseline, separa deforestación de humedad/estacionalidad en esta
ventana. El guard de HH no movió el área en esta caja: la firma de doble
rebote no domina los falsos positivos acá (su valor quedó probado en el
escenario sintético del test y apunta a la clase de error que el paper
admite, no a esta ventana en particular).

**Decisión de defaults.** Los números reales no justifican prender P1/P2 por
defecto: quedan opt-in (`--baseline`, `--cov-max`, `--guardia-hh`, también en
el visor), recomendados cuando el track tiene 3+ fechas en disco. Prenderlos
por defecto exige una referencia menos estacional (MapBiomas/GFW anual) —
sigue siendo el próximo paso pendiente anotado arriba.

## Guard de HH: búsqueda del pulso de inundación (2026-11)

[`buscar_doble_rebote.py`](buscar_doble_rebote.py) escanea un par buscando la
firma de doble rebote (ΔHH > +3 dB con ΔHV < −3 dB, normalizados, ~100 m/px)
y localiza la ventana más densa (la caja del centro de masa engaña con
distribuciones multimodales). Tres pares estación seca → húmeda, buscando un
evento compacto que dispare el guard a escala:

| Par | Región | Fechas | Firma en escena | Mejor ventana 30×30 km |
|---|---|---|---:|---:|
| 161/167 | chiquitano (BO) | 2026-06-13 → 11-16 | 28.497 px (0,48 %) | 761 px (0,85 %) |
| 161/167 | chiquitano (BO) | 2025-11-21 → 12-03 | — | 425 px (0,47 %) |
| 132/165 | río Paraguay | 2026-07-05 → 11-02 | 20.521 px (0,60 %) | 1.089 px (1,21 %) |

**Resultado honesto:** no hay un pulso compacto en el archivo actual (la
crecida pico es dic–mar y el archivo termina el 2026-11-16). En la mejor
ventana del río Paraguay el guard sí disparó: **50 ha con firma salieron de
los 13.732 ha** que el par julio→noviembre pinta como pérdida
(`--guardia-hh 3`); marginal pero real, y costo cero cuando la firma no está.
Dato operacional de paso: entre estación seca y húmeda el par entero se
oscurece ~1,5 dB en HH y HV (senescencia/humedad); el corrimiento del par lo
absorbe — los umbrales absolutos por fecha siguen prohibidos.

## Umbral ROC-derivado (2026-11)

`deforestacion_este.py --umbral auto` barre 0,5–4 dB con el detector completo
(P1/P2 incluidos) contra la referencia y opera en el umbral de máximo F1
denso; empates hacia el umbral más bajo (recuerdo antes que precisión: lo que
sigue confirma con óptica o persistencia). El informe aclara que es selección
contra la MISMA referencia que mide — punto de operación, no precisión
independiente.

Caja chica 08-27 → 10-02 con baseline 3 + CoV + guardia: la curva da F1 denso
≤ 0,002 en todo el barrido (ventana casi sin cambio) y `auto` elige 0,5 dB
honesto (729 ha, sesgo +967 %), anunciando que no hay señal. Con `--umbral 2`
fijo la misma corrida sigue dando 134 ha (regresión clavada). **Lectura:**
`auto` no inventa magia donde no hay cambio; su valor aparece en ventanas con
cambio real, y la curva (`curva_umbral` en `metricas.json`, `curva.png`) queda
para leerla antes de elegir a mano.

## Límites

- Referencia óptica, no campo; una cosecha o el agua también bajan el NDVI.
- Junio→octubre mezcla estacionalidad y humedad con cobertura.
- Bootstrap de píxeles: no corrige del todo la autocorrelación espacial.
- NISAR repite cada 12 días; la fecha de cambio no es diaria.
