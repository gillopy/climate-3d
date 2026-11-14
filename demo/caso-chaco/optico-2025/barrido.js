window.BARRIDO = {
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
    "area_ha": 46764.3,
    "bosque_ha": 674.8,
    "perdida_ha": 61.3,
    "px_perdida": 2065,
    "px_bosque": 22740,
    "ndvi_antes_medio": 0.569,
    "ndvi_despues_medio": 0.555,
    "delta_medio_db": -0.337,
    "sensibilidad": [
      {
        "ndvi": 0.08,
        "ha": 79.0,
        "px": 2664
      },
      {
        "ndvi": 0.12,
        "ha": 66.5,
        "px": 2241
      },
      {
        "ndvi": 0.16,
        "ha": 61.3,
        "px": 2065
      },
      {
        "ndvi": 0.2,
        "ha": 49.2,
        "px": 1659
      },
      {
        "ndvi": 0.25,
        "ha": 41.6,
        "px": 1401
      }
    ],
    "mmu": {
      "umbral_ha": 0.5,
      "componentes": 55,
      "componentes_validos": 15,
      "ha_sin_mmu": 61.3,
      "ha_con_mmu": 53.8,
      "componente_mayor_ha": 11.2
    }
  },
  "control": {
    "area_ha": 112.5,
    "bosque_ha": 0.1,
    "perdida_ha": 0.0,
    "px_perdida": 0,
    "px_bosque": 1817,
    "ndvi_antes_medio": 0.556,
    "ndvi_despues_medio": 0.562,
    "delta_medio_db": 0.0,
    "sensibilidad": [
      {
        "ndvi": 0.08,
        "ha": 0.0,
        "px": 0
      },
      {
        "ndvi": 0.12,
        "ha": 0.0,
        "px": 0
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
    -55.56,
    -24.12,
    -55.3,
    -23.96
  ],
  "control_bbox": [
    -55.31,
    -23.97,
    -55.3,
    -23.96
  ]
};
