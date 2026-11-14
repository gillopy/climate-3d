window.RESERVA = {
  "producto": "optico",
  "sensor": "Sentinel-2 L2A",
  "parametros": {
    "fecha_antes": "2025-07-03",
    "fecha_despues": "2025-10-31",
    "dias": 15,
    "nubes_max_pct": 25.0,
    "umbral_ndvi": 0.16,
    "bosque_ndvi": 0.55,
    "mmu_ha": 0.5,
    "mascara_geojson": "demo\\caso-chaco\\datos\\mbaracayu.geojson",
    "min_ndvi": 0.25
  },
  "items": {
    "antes": [
      {
        "id": "S2A_MSIL2A_20250703T135131_R024_T21KXP_20250703T201116",
        "cloud": 0.01
      },
      {
        "id": "S2B_MSIL2A_20250706T134709_R024_T21KXP_20250706T190934",
        "cloud": 7.05
      },
      {
        "id": "S2B_MSIL2A_20250716T134709_R024_T21KXP_20250716T171141",
        "cloud": 8.36
      },
      {
        "id": "S2B_MSIL2A_20250716T134709_R024_T21KXP_20250716T185720",
        "cloud": 18.85
      }
    ],
    "despues": [
      {
        "id": "S2C_MSIL2A_20251019T134721_R024_T21KXP_20251019T202715",
        "cloud": 0.0
      },
      {
        "id": "S2B_MSIL2A_20251024T134709_R024_T21KXP_20251024T172317",
        "cloud": 4.13
      },
      {
        "id": "S2A_MSIL2A_20251031T135131_R024_T21KXP_20251031T170612",
        "cloud": 9.04
      },
      {
        "id": "S2B_MSIL2A_20251103T134659_R024_T21KXP_20251103T172753",
        "cloud": 20.8
      }
    ]
  },
  "caso": {
    "area_ha": 9719.0,
    "bosque_ha": 8840.1,
    "perdida_ha": 17.7,
    "px_perdida": 2664,
    "px_bosque": 1328706,
    "ndvi_antes_medio": 0.469,
    "ndvi_despues_medio": 0.567,
    "delta_medio_db": -0.242,
    "sensibilidad": [
      {
        "ndvi": 0.08,
        "ha": 31.8,
        "px": 4773
      },
      {
        "ndvi": 0.12,
        "ha": 24.4,
        "px": 3667
      },
      {
        "ndvi": 0.16,
        "ha": 17.7,
        "px": 2664
      },
      {
        "ndvi": 0.2,
        "ha": 12.0,
        "px": 1797
      },
      {
        "ndvi": 0.25,
        "ha": 6.9,
        "px": 1044
      }
    ],
    "mmu": {
      "umbral_ha": 0.5,
      "componentes": 34,
      "componentes_validos": 14,
      "ha_sin_mmu": 17.7,
      "ha_con_mmu": 15.7,
      "componente_mayor_ha": 3.9
    }
  },
  "control": {
    "area_ha": 2808.5,
    "bosque_ha": 2808.5,
    "perdida_ha": 0.8,
    "px_perdida": 749,
    "px_bosque": 2559995,
    "ndvi_antes_medio": 0.453,
    "ndvi_despues_medio": 0.577,
    "delta_medio_db": -0.198,
    "sensibilidad": [
      {
        "ndvi": 0.08,
        "ha": 2.4,
        "px": 2197
      },
      {
        "ndvi": 0.12,
        "ha": 1.5,
        "px": 1396
      },
      {
        "ndvi": 0.16,
        "ha": 0.8,
        "px": 749
      },
      {
        "ndvi": 0.2,
        "ha": 0.2,
        "px": 206
      },
      {
        "ndvi": 0.25,
        "ha": 0.0,
        "px": 0
      }
    ],
    "mmu": {
      "umbral_ha": 0.5,
      "componentes": 12,
      "componentes_validos": 0,
      "ha_sin_mmu": 0.8,
      "ha_con_mmu": 0.0,
      "componente_mayor_ha": 0.3
    }
  },
  "bbox": [
    -55.444565,
    -24.066058,
    -55.321484,
    -23.995819
  ],
  "control_bbox": [
    -55.4,
    -24.15,
    -55.35,
    -24.1
  ]
};
