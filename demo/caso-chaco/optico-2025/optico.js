window.OPTICO = {
  "producto": "optico",
  "sensor": "Sentinel-2 L2A",
  "parametros": {
    "fecha_antes": "2025-07-03",
    "fecha_despues": "2025-10-31",
    "dias": 15,
    "nubes_max_pct": 25.0,
    "umbral_ndvi": 0.16,
    "bosque_ndvi": 0.55,
    "mmu_ha": 0.5
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
    "bosque_ha": 320.7,
    "perdida_ha": 0.6,
    "px_perdida": 97,
    "px_bosque": 48209,
    "ndvi_antes_medio": 0.57,
    "ndvi_despues_medio": 0.605,
    "delta_medio_db": -0.273,
    "sensibilidad": [
      {
        "ndvi": 0.08,
        "ha": 4.6,
        "px": 686
      },
      {
        "ndvi": 0.12,
        "ha": 0.8,
        "px": 120
      },
      {
        "ndvi": 0.16,
        "ha": 0.6,
        "px": 97
      },
      {
        "ndvi": 0.2,
        "ha": 0.4,
        "px": 65
      },
      {
        "ndvi": 0.25,
        "ha": 0.3,
        "px": 44
      }
    ],
    "mmu": {
      "umbral_ha": 0.5,
      "componentes": 9,
      "componentes_validos": 0,
      "ha_sin_mmu": 0.6,
      "ha_con_mmu": 0.0,
      "componente_mayor_ha": 0.3
    }
  },
  "control": {
    "area_ha": 2697.9,
    "bosque_ha": 21.1,
    "perdida_ha": 0.0,
    "px_perdida": 0,
    "px_bosque": 13340,
    "ndvi_antes_medio": 0.56,
    "ndvi_despues_medio": 0.59,
    "delta_medio_db": 0.0,
    "sensibilidad": [
      {
        "ndvi": 0.08,
        "ha": 0.1,
        "px": 93
      },
      {
        "ndvi": 0.12,
        "ha": 0.0,
        "px": 6
      },
      {
        "ndvi": 0.16,
        "ha": 0.0,
        "px": 0
      },
      {
        "ndvi": 0.2,
        "ha": 0.0,
        "px": 0
      },
      {
        "ndvi": 0.25,
        "ha": 0.0,
        "px": 0
      }
    ],
    "mmu": {
      "umbral_ha": 0.5,
      "componentes": 0,
      "componentes_validos": 0,
      "ha_sin_mmu": 0.0,
      "ha_con_mmu": 0.0,
      "componente_mayor_ha": 0.0
    }
  },
  "bbox": [
    -55.444565,
    -24.066058,
    -55.321484,
    -23.995819
  ],
  "control_bbox": [
    -55.52,
    -24.06,
    -55.46,
    -24.02
  ]
};
