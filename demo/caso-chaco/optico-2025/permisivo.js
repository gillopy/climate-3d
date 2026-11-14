window.PERMISIVO = {
  "producto": "optico",
  "sensor": "Sentinel-2 L2A",
  "parametros": {
    "fecha_antes": "2025-07-03",
    "fecha_despues": "2025-10-31",
    "dias": 15,
    "nubes_max_pct": 25.0,
    "umbral_ndvi": 0.16,
    "bosque_ndvi": 0.25,
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
    "area_ha": 46764.3,
    "bosque_ha": 41668.1,
    "perdida_ha": 646.5,
    "px_perdida": 21787,
    "px_bosque": 1404253,
    "ndvi_antes_medio": 0.438,
    "ndvi_despues_medio": 0.532,
    "delta_medio_db": -0.258,
    "sensibilidad": [
      {
        "ndvi": 0.08,
        "ha": 1247.3,
        "px": 42036
      },
      {
        "ndvi": 0.12,
        "ha": 909.1,
        "px": 30638
      },
      {
        "ndvi": 0.16,
        "ha": 646.5,
        "px": 21787
      },
      {
        "ndvi": 0.2,
        "ha": 455.5,
        "px": 15351
      },
      {
        "ndvi": 0.25,
        "ha": 295.6,
        "px": 9961
      }
    ],
    "mmu": {
      "umbral_ha": 0.5,
      "componentes": 241,
      "componentes_validos": 112,
      "ha_sin_mmu": 646.5,
      "ha_con_mmu": 622.6,
      "componente_mayor_ha": 89.6
    }
  },
  "control": {
    "area_ha": 2022.8,
    "bosque_ha": 1862.0,
    "perdida_ha": 53.4,
    "px_perdida": 60014,
    "px_bosque": 2094362,
    "ndvi_antes_medio": 0.447,
    "ndvi_despues_medio": 0.525,
    "delta_medio_db": -0.282,
    "sensibilidad": [
      {
        "ndvi": 0.08,
        "ha": 93.7,
        "px": 105445
      },
      {
        "ndvi": 0.12,
        "ha": 67.9,
        "px": 76397
      },
      {
        "ndvi": 0.16,
        "ha": 53.4,
        "px": 60014
      },
      {
        "ndvi": 0.2,
        "ha": 43.5,
        "px": 48971
      },
      {
        "ndvi": 0.25,
        "ha": 34.9,
        "px": 39295
      }
    ],
    "mmu": {
      "umbral_ha": 0.5,
      "componentes": 72,
      "componentes_validos": 13,
      "ha_sin_mmu": 53.4,
      "ha_con_mmu": 47.9,
      "componente_mayor_ha": 12.5
    }
  },
  "bbox": [
    -55.56,
    -24.12,
    -55.3,
    -23.96
  ],
  "control_bbox": [
    -55.545,
    -24.1,
    -55.5,
    -24.06
  ]
};
