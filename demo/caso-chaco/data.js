/* Datos congelados del caso de estudio. Sin fetch: la pagina funciona desde file:// */
window.DEMO = {
  caso: {
    nombre: "Desmonte en el Chaco paraguayo",
    bbox: [-61.12896, -20.856085, -61.062527, -20.81036],
    poligono: [
      [-61.12896, -20.856085],
      [-61.12896, -20.81036],
      [-61.062527, -20.81036],
      [-61.062527, -20.856085],
      [-61.12896, -20.856085]
    ],
    area_ha: 3601.7,
    bosque_ha: 2699.8,
    desde: "2026-01-20",
    hasta: "2026-03-21",
    perdida_ha: 262.9,
    ganancia_ha: 4.1,
    delta_db: -3.82
  },

  control: {
    bbox: [-61.182518, -20.938034, -61.099777, -20.883834],
    poligono: [
      [-61.182518, -20.938034],
      [-61.182518, -20.883834],
      [-61.099777, -20.883834],
      [-61.099777, -20.938034],
      [-61.182518, -20.938034]
    ],
    area_ha: 5282.6,
    bosque_ha: 4984.7,
    perdida_ha: 2.1,
    ganancia_ha: 1.0
  },

  pasos: [
    { desde: "20 ene", hasta: "01 feb", perdida: 71, ganancia: 0, control_perdida: 1, control_ganancia: 0 },
    { desde: "01 feb", hasta: "13 feb", perdida: 27, ganancia: 0, control_perdida: 0, control_ganancia: 0 },
    { desde: "13 feb", hasta: "25 feb", perdida: 7, ganancia: 102, control_perdida: 0, control_ganancia: 26.6 },
    { desde: "25 feb", hasta: "09 mar", perdida: 21, ganancia: 0, control_perdida: 1, control_ganancia: 0 },
    { desde: "09 mar", hasta: "21 mar", perdida: 0, ganancia: 32, control_perdida: 0, control_ganancia: 0 }
  ],

  ventanas: [
    {
      etiqueta: "12 días",
      detalle: "21 nov 2025 → 03 dic 2025",
      perdida: 89,
      ganancia: 64,
      estado: "valida",
      lectura: "Piso de ruido del detector: resultado pequeño y simétrico."
    },
    {
      etiqueta: "276 días",
      detalle: "08 ene 2026 → 11 oct 2026",
      perdida: 188,
      ganancia: 24751,
      estado: "invalida",
      lectura: "15,8 % de la caja aparece como ganancia. Domina la diferencia de humedad."
    },
    {
      etiqueta: "276 días",
      detalle: "11 oct 2026 → 08 ene 2026 (invertido)",
      perdida: 17204,
      ganancia: 873,
      estado: "invalida",
      lectura: "No es antisimétrico: el resultado depende del orden de las fechas."
    }
  ],

  escala: { este_20m_ha: 639 },

  landsat: {
    antes: "2026-01-22",
    despues: "2026-03-27",
    perdida_ha: 553.1,
    umbral: 0.20,
    min_ndvi: 0.5,
    sensor: "Landsat 8/9 C2 L2"
  },

  reserva: {
    antes: "2025-07-03",
    despues: "2025-10-31",
    area_ha: 9719.0,
    dentro_reserva_ha: 8840.1,
    perdida_ha: 17.7,
    mmu_ha: 15.7,
    parcelas: 14,
    mayor_ha: 3.9,
    control_ha: 0.8,
    ndvi_antes: 0.469,
    ndvi_despues: 0.567
  },

  meta: {
    sensor: "NISAR L-band GCOV",
    coleccion: "NISAR_L2_GCOV_PROVISIONAL_V1",
    track: 161,
    frame: 167,
    polarizacion: "HH + HV",
    banda: "HV",
    mpp: 20,
    epsg: 32720,
    umbral_db: 3,
    hv_min_db: -15.5
  }
};
