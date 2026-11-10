// Generado por demo/tools/export_demo.py. No editar a mano.
export default {
  "version": 1,
  "generated_at": "2026-11-08T18:12:58+00:00",
  "days": [
    "2026-10-10",
    "2026-11-03",
    "2026-11-04",
    "2026-11-05",
    "2026-11-06",
    "2026-11-07",
    "2026-11-08"
  ],
  "dates": {
    "anomalia_2t": [
      "2026-11-05"
    ],
    "follaje": [
      "2026-10-10"
    ],
    "geocolor": [
      "2026-11-03",
      "2026-11-04"
    ],
    "goes_airmass": [
      "2026-11-04"
    ],
    "goes_banda": [
      "2026-11-07",
      "2026-11-08"
    ],
    "goes_c13": [
      "2026-11-03",
      "2026-11-04"
    ],
    "goes_dust": [
      "2026-11-03",
      "2026-11-04"
    ],
    "goes_firetemp": [
      "2026-11-04"
    ],
    "goes_sandwich": [
      "2026-11-07",
      "2026-11-08"
    ],
    "goes_truecolor": [
      "2026-11-03",
      "2026-11-04"
    ],
    "mur_realista": [
      "2026-11-04"
    ],
    "mur_sst": [
      "2026-11-04"
    ],
    "precipitacion_ecmwf": [
      "2026-11-06"
    ],
    "snapshot_paraguay": [
      "2026-11-04"
    ],
    "truecolor_viirs": [
      "2026-11-04"
    ],
    "viento_250": [
      "2026-11-04"
    ]
  },
  "combos": [
    {
      "id": "a86bb24c3588",
      "product_id": "goes_banda",
      "params": {
        "snapshot": true,
        "paraguay": false,
        "margen": 6,
        "satelite": "G19",
        "banda": "C13",
        "paleta": "clean_ir",
        "ventana": {
          "start": "2026-11-07",
          "end": "2026-11-08"
        },
        "ultimos": false,
        "ultimos_n": "24",
        "hora": 15,
        "minuto": "00",
        "resolucion": "2712",
        "hora_desde": 0,
        "hora_hasta": 24,
        "animar": false,
        "fps": 12
      },
      "dates": [
        "2026-11-07",
        "2026-11-08"
      ],
      "snapshot": {
        "id": "a86bb24c3588",
        "product_id": "goes_banda",
        "product_name": "GOES - banda cruda, estilo color real",
        "params": {
          "snapshot": true,
          "paraguay": false,
          "margen": 6,
          "satelite": "G19",
          "banda": "C13",
          "paleta": "clean_ir",
          "ventana": {
            "start": "2026-11-07",
            "end": "2026-11-08"
          },
          "ultimos": false,
          "ultimos_n": "24",
          "hora": 15,
          "minuto": "00",
          "resolucion": "2712",
          "hora_desde": 0,
          "hora_hasta": 24,
          "animar": false,
          "fps": 12
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-08T17:09:11+00:00",
        "started_at": "2026-11-08T17:09:37+00:00",
        "finished_at": "2026-11-08T17:09:57+00:00",
        "logs": [
          {
            "at": "2026-11-08T17:09:37+00:00",
            "level": "info",
            "text": "job a86bb24c3588 | goes_banda | modo=real"
          },
          {
            "at": "2026-11-08T17:09:37+00:00",
            "level": "info",
            "text": "[1/2] bajando C13 de G19 (1 slot(s))"
          },
          {
            "at": "2026-11-08T17:09:37+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\descargar_goes.py --sat G19 --banda C13 --desde 2026-11-08T15:00:00 --hasta 2026-11-08T15:10:00 --paso 10"
          },
          {
            "at": "2026-11-08T17:09:40+00:00",
            "level": "info",
            "text": "G19 C13: 1 slots (2026-11-08 15:00:00 -> 2026-11-08 15:10:00 UTC) · rango pedido"
          },
          {
            "at": "2026-11-08T17:09:40+00:00",
            "level": "info",
            "text": "Destino: <local> era5\\goes_c13_g19"
          },
          {
            "at": "2026-11-08T17:09:44+00:00",
            "level": "info",
            "text": "[1/1] 2026-11-08 15:00 UTC  descargados=1 existentes=0 errores=0  tiempo=4s"
          },
          {
            "at": "2026-11-08T17:09:44+00:00",
            "level": "info",
            "text": "Finalizado en 4s: descargados=1, existentes=0, errores=0"
          },
          {
            "at": "2026-11-08T17:09:44+00:00",
            "level": "info",
            "text": "[2/2] poster C13 2712px"
          },
          {
            "at": "2026-11-08T17:09:44+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\prototipos\\poster_goes_banda.py --banda C13 --sat G19 --desde 2026-11-08T15:00 --n 1 --paso 10 --px 2712 --paleta clean_ir --sombra-borde 0 --centro -75.2 0 --recorte 1.0 --borde  --out <repo>\\app\\var\\media\\cache\\592cf601145e\\G19_C13_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T17:09:47+00:00",
            "level": "info",
            "text": "OR_ABI-L2-CMIPF-M6C13_G19_s20263121500218_e20263121509538_c20263121510014.nc"
          },
          {
            "at": "2026-11-08T17:09:47+00:00",
            "level": "info",
            "text": "slot: 2026-11-08 15:00 UTC | globo 2712 px | centro (-75.2, 0.0) | paleta clean_ir"
          },
          {
            "at": "2026-11-08T17:09:48+00:00",
            "level": "info",
            "text": "<repo>\\prototipos\\poster_goes_banda.py:185: RuntimeWarning: invalid value encountered in cast"
          },
          {
            "at": "2026-11-08T17:09:48+00:00",
            "level": "info",
            "text": "  indice = (normalizado * (n - 1)).astype(np.uint16 if n > 256 else np.uint8)"
          },
          {
            "at": "2026-11-08T17:09:48+00:00",
            "level": "info",
            "text": "  franja   256/2712"
          },
          {
            "at": "2026-11-08T17:09:49+00:00",
            "level": "info",
            "text": "  franja   512/2712"
          },
          {
            "at": "2026-11-08T17:09:49+00:00",
            "level": "info",
            "text": "  franja   768/2712"
          },
          {
            "at": "2026-11-08T17:09:49+00:00",
            "level": "info",
            "text": "  franja  1024/2712"
          },
          {
            "at": "2026-11-08T17:09:50+00:00",
            "level": "info",
            "text": "  franja  1280/2712"
          },
          {
            "at": "2026-11-08T17:09:50+00:00",
            "level": "info",
            "text": "  franja  1536/2712"
          },
          {
            "at": "2026-11-08T17:09:50+00:00",
            "level": "info",
            "text": "  franja  1792/2712"
          },
          {
            "at": "2026-11-08T17:09:51+00:00",
            "level": "info",
            "text": "  franja  2048/2712"
          },
          {
            "at": "2026-11-08T17:09:51+00:00",
            "level": "info",
            "text": "  franja  2304/2712"
          },
          {
            "at": "2026-11-08T17:09:51+00:00",
            "level": "info",
            "text": "  franja  2560/2712"
          },
          {
            "at": "2026-11-08T17:09:52+00:00",
            "level": "info",
            "text": "  franja  2712/2712"
          },
          {
            "at": "2026-11-08T17:09:52+00:00",
            "level": "info",
            "text": "disco 2712 px | 5,543,676 px con dato"
          },
          {
            "at": "2026-11-08T17:09:57+00:00",
            "level": "info",
            "text": "PNG: <repo>\\app\\var\\media\\cache\\592cf601145e\\G19_C13_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T17:09:57+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "G19_C13_2026-11-08T1500.webp",
            "url": "/media/a86bb24c3588/G19_C13_2026-11-08T1500.webp",
            "kind": "image",
            "bytes": 375614
          }
        ],
        "plan": [
          "bajando C13 de G19 (1 slot(s))",
          "poster C13 2712px"
        ],
        "error": null
      }
    },
    {
      "id": "32cce7cb8efc",
      "product_id": "goes_banda",
      "params": {
        "snapshot": true,
        "paraguay": false,
        "margen": 6,
        "satelite": "G19",
        "banda": "C01",
        "paleta": "reflectancia",
        "ventana": {
          "start": "2026-11-07",
          "end": "2026-11-08"
        },
        "ultimos": false,
        "ultimos_n": "24",
        "hora": 15,
        "minuto": "00",
        "resolucion": "2712",
        "hora_desde": 0,
        "hora_hasta": 24,
        "animar": false,
        "fps": 12
      },
      "dates": [
        "2026-11-07",
        "2026-11-08"
      ],
      "snapshot": {
        "id": "32cce7cb8efc",
        "product_id": "goes_banda",
        "product_name": "GOES - banda cruda, estilo color real",
        "params": {
          "snapshot": true,
          "paraguay": false,
          "margen": 6,
          "satelite": "G19",
          "banda": "C01",
          "paleta": "reflectancia",
          "ventana": {
            "start": "2026-11-07",
            "end": "2026-11-08"
          },
          "ultimos": false,
          "ultimos_n": "24",
          "hora": 15,
          "minuto": "00",
          "resolucion": "2712",
          "hora_desde": 0,
          "hora_hasta": 24,
          "animar": false,
          "fps": 12
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-08T16:50:25+00:00",
        "started_at": "2026-11-08T16:50:25+00:00",
        "finished_at": "2026-11-08T16:57:51+00:00",
        "logs": [
          {
            "at": "2026-11-08T16:50:25+00:00",
            "level": "info",
            "text": "job 32cce7cb8efc | goes_banda | modo=real"
          },
          {
            "at": "2026-11-08T16:50:25+00:00",
            "level": "info",
            "text": "[1/2] bajando C01 de G19 (1 slot(s))"
          },
          {
            "at": "2026-11-08T16:50:25+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\descargar_goes.py --sat G19 --banda C01 --desde 2026-11-08T15:00:00 --hasta 2026-11-08T15:10:00 --paso 10"
          },
          {
            "at": "2026-11-08T16:50:29+00:00",
            "level": "info",
            "text": "G19 C01: 1 slots (2026-11-08 15:00:00 -> 2026-11-08 15:10:00 UTC) · rango pedido"
          },
          {
            "at": "2026-11-08T16:50:29+00:00",
            "level": "info",
            "text": "Destino: <local> era5\\goes_c01_g19"
          },
          {
            "at": "2026-11-08T16:50:44+00:00",
            "level": "info",
            "text": "[1/1] 2026-11-08 15:00 UTC  descargados=1 existentes=0 errores=0  tiempo=15s"
          },
          {
            "at": "2026-11-08T16:50:44+00:00",
            "level": "info",
            "text": "Finalizado en 15s: descargados=1, existentes=0, errores=0"
          },
          {
            "at": "2026-11-08T16:50:44+00:00",
            "level": "info",
            "text": "[2/2] poster C01 2712px"
          },
          {
            "at": "2026-11-08T16:50:44+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\prototipos\\poster_goes_banda.py --banda C01 --sat G19 --desde 2026-11-08T15:00 --n 1 --paso 10 --px 2712 --paleta reflectancia --sombra-borde 0 --centro -75.2 0 --recorte 1.0 --borde  --out <repo>\\app\\var\\media\\cache\\ed08695cf02c\\G19_C01_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T16:50:48+00:00",
            "level": "info",
            "text": "OR_ABI-L2-CMIPF-M6C01_G19_s20263121500218_e20263121509526_c20263121509573.nc"
          },
          {
            "at": "2026-11-08T16:50:48+00:00",
            "level": "info",
            "text": "slot: 2026-11-08 15:00 UTC | globo 2712 px | centro (-75.2, 0.0) | paleta reflectancia"
          },
          {
            "at": "2026-11-08T16:50:57+00:00",
            "level": "info",
            "text": "<repo>\\prototipos\\poster_goes_banda.py:185: RuntimeWarning: invalid value encountered in cast"
          },
          {
            "at": "2026-11-08T16:50:57+00:00",
            "level": "info",
            "text": "  indice = (normalizado * (n - 1)).astype(np.uint16 if n > 256 else np.uint8)"
          },
          {
            "at": "2026-11-08T16:50:57+00:00",
            "level": "info",
            "text": "  franja   256/2712"
          },
          {
            "at": "2026-11-08T16:50:58+00:00",
            "level": "info",
            "text": "  franja   512/2712"
          },
          {
            "at": "2026-11-08T16:50:59+00:00",
            "level": "info",
            "text": "  franja   768/2712"
          },
          {
            "at": "2026-11-08T16:51:00+00:00",
            "level": "info",
            "text": "  franja  1024/2712"
          },
          {
            "at": "2026-11-08T16:51:00+00:00",
            "level": "info",
            "text": "  franja  1280/2712"
          },
          {
            "at": "2026-11-08T16:51:00+00:00",
            "level": "info",
            "text": "  franja  1536/2712"
          },
          {
            "at": "2026-11-08T16:51:01+00:00",
            "level": "info",
            "text": "  franja  1792/2712"
          },
          {
            "at": "2026-11-08T16:51:02+00:00",
            "level": "info",
            "text": "  franja  2048/2712"
          },
          {
            "at": "2026-11-08T16:51:03+00:00",
            "level": "info",
            "text": "  franja  2304/2712"
          },
          {
            "at": "2026-11-08T16:51:03+00:00",
            "level": "info",
            "text": "  franja  2560/2712"
          },
          {
            "at": "2026-11-08T16:51:03+00:00",
            "level": "info",
            "text": "  franja  2712/2712"
          },
          {
            "at": "2026-11-08T16:51:03+00:00",
            "level": "info",
            "text": "disco 2712 px | 5,543,676 px con dato"
          },
          {
            "at": "2026-11-08T16:54:32+00:00",
            "level": "info",
            "text": "PNG: <repo>\\app\\var\\media\\cache\\ed08695cf02c\\G19_C01_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T16:57:51+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "G19_C01_2026-11-08T1500.webp",
            "url": "/media/32cce7cb8efc/G19_C01_2026-11-08T1500.webp",
            "kind": "image",
            "bytes": 239092
          }
        ],
        "plan": [
          "bajando C01 de G19 (1 slot(s))",
          "poster C01 2712px"
        ],
        "error": null
      }
    },
    {
      "id": "03734847ca95",
      "product_id": "goes_banda",
      "params": {
        "snapshot": true,
        "paraguay": false,
        "margen": 6,
        "satelite": "G19",
        "banda": "C02",
        "paleta": "reflectancia",
        "ventana": {
          "start": "2026-11-07",
          "end": "2026-11-08"
        },
        "ultimos": false,
        "ultimos_n": "24",
        "hora": 15,
        "minuto": "00",
        "resolucion": "2712",
        "hora_desde": 0,
        "hora_hasta": 24,
        "animar": false,
        "fps": 12
      },
      "dates": [
        "2026-11-07",
        "2026-11-08"
      ],
      "snapshot": {
        "id": "03734847ca95",
        "product_id": "goes_banda",
        "product_name": "GOES - banda cruda, estilo color real",
        "params": {
          "snapshot": true,
          "paraguay": false,
          "margen": 6,
          "satelite": "G19",
          "banda": "C02",
          "paleta": "reflectancia",
          "ventana": {
            "start": "2026-11-07",
            "end": "2026-11-08"
          },
          "ultimos": false,
          "ultimos_n": "24",
          "hora": 15,
          "minuto": "00",
          "resolucion": "2712",
          "hora_desde": 0,
          "hora_hasta": 24,
          "animar": false,
          "fps": 12
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-08T17:05:05+00:00",
        "started_at": "2026-11-08T17:05:05+00:00",
        "finished_at": "2026-11-08T17:05:54+00:00",
        "logs": [
          {
            "at": "2026-11-08T17:05:05+00:00",
            "level": "info",
            "text": "job 03734847ca95 | goes_banda | modo=real"
          },
          {
            "at": "2026-11-08T17:05:05+00:00",
            "level": "info",
            "text": "[1/2] bajando C02 de G19 (1 slot(s))"
          },
          {
            "at": "2026-11-08T17:05:05+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\descargar_goes.py --sat G19 --banda C02 --desde 2026-11-08T15:00:00 --hasta 2026-11-08T15:10:00 --paso 10"
          },
          {
            "at": "2026-11-08T17:05:08+00:00",
            "level": "info",
            "text": "G19 C02: 1 slots (2026-11-08 15:00:00 -> 2026-11-08 15:10:00 UTC) · rango pedido"
          },
          {
            "at": "2026-11-08T17:05:08+00:00",
            "level": "info",
            "text": "Destino: <local> era5\\goes_c02_g19"
          },
          {
            "at": "2026-11-08T17:05:09+00:00",
            "level": "info",
            "text": "[1/1] 2026-11-08 15:00 UTC  descargados=0 existentes=1 errores=0  tiempo=1s"
          },
          {
            "at": "2026-11-08T17:05:09+00:00",
            "level": "info",
            "text": "Finalizado en 1s: descargados=0, existentes=1, errores=0"
          },
          {
            "at": "2026-11-08T17:05:09+00:00",
            "level": "info",
            "text": "[2/2] poster C02 2712px"
          },
          {
            "at": "2026-11-08T17:05:09+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\prototipos\\poster_goes_banda.py --banda C02 --sat G19 --desde 2026-11-08T15:00 --n 1 --paso 10 --px 2712 --paleta reflectancia --sombra-borde 0 --centro -75.2 0 --recorte 1.0 --borde  --out <repo>\\app\\var\\media\\cache\\b83dc623bb82\\G19_C02_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T17:05:13+00:00",
            "level": "info",
            "text": "OR_ABI-L2-CMIPF-M6C02_G19_s20263121500218_e20263121509526_c20263121509583.nc"
          },
          {
            "at": "2026-11-08T17:05:13+00:00",
            "level": "info",
            "text": "slot: 2026-11-08 15:00 UTC | globo 2712 px | centro (-75.2, 0.0) | paleta reflectancia"
          },
          {
            "at": "2026-11-08T17:05:40+00:00",
            "level": "info",
            "text": "<repo>\\prototipos\\poster_goes_banda.py:185: RuntimeWarning: invalid value encountered in cast"
          },
          {
            "at": "2026-11-08T17:05:40+00:00",
            "level": "info",
            "text": "  indice = (normalizado * (n - 1)).astype(np.uint16 if n > 256 else np.uint8)"
          },
          {
            "at": "2026-11-08T17:05:40+00:00",
            "level": "info",
            "text": "  franja   256/2712"
          },
          {
            "at": "2026-11-08T17:05:40+00:00",
            "level": "info",
            "text": "  franja   512/2712"
          },
          {
            "at": "2026-11-08T17:05:41+00:00",
            "level": "info",
            "text": "  franja   768/2712"
          },
          {
            "at": "2026-11-08T17:05:41+00:00",
            "level": "info",
            "text": "  franja  1024/2712"
          },
          {
            "at": "2026-11-08T17:05:42+00:00",
            "level": "info",
            "text": "  franja  1280/2712"
          },
          {
            "at": "2026-11-08T17:05:42+00:00",
            "level": "info",
            "text": "  franja  1536/2712"
          },
          {
            "at": "2026-11-08T17:05:42+00:00",
            "level": "info",
            "text": "  franja  1792/2712"
          },
          {
            "at": "2026-11-08T17:05:43+00:00",
            "level": "info",
            "text": "  franja  2048/2712"
          },
          {
            "at": "2026-11-08T17:05:44+00:00",
            "level": "info",
            "text": "  franja  2304/2712"
          },
          {
            "at": "2026-11-08T17:05:44+00:00",
            "level": "info",
            "text": "  franja  2560/2712"
          },
          {
            "at": "2026-11-08T17:05:44+00:00",
            "level": "info",
            "text": "  franja  2712/2712"
          },
          {
            "at": "2026-11-08T17:05:45+00:00",
            "level": "info",
            "text": "disco 2712 px | 5,543,676 px con dato"
          },
          {
            "at": "2026-11-08T17:05:53+00:00",
            "level": "info",
            "text": "PNG: <repo>\\app\\var\\media\\cache\\b83dc623bb82\\G19_C02_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T17:05:54+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "G19_C02_2026-11-08T1500.webp",
            "url": "/media/03734847ca95/G19_C02_2026-11-08T1500.webp",
            "kind": "image",
            "bytes": 307794
          }
        ],
        "plan": [
          "bajando C02 de G19 (1 slot(s))",
          "poster C02 2712px"
        ],
        "error": null
      }
    },
    {
      "id": "82849f98af9b",
      "product_id": "goes_banda",
      "params": {
        "snapshot": true,
        "paraguay": false,
        "margen": 6,
        "satelite": "G19",
        "banda": "C03",
        "paleta": "reflectancia",
        "ventana": {
          "start": "2026-11-07",
          "end": "2026-11-08"
        },
        "ultimos": false,
        "ultimos_n": "24",
        "hora": 15,
        "minuto": "00",
        "resolucion": "2712",
        "hora_desde": 0,
        "hora_hasta": 24,
        "animar": false,
        "fps": 12
      },
      "dates": [
        "2026-11-07",
        "2026-11-08"
      ],
      "snapshot": {
        "id": "82849f98af9b",
        "product_id": "goes_banda",
        "product_name": "GOES - banda cruda, estilo color real",
        "params": {
          "snapshot": true,
          "paraguay": false,
          "margen": 6,
          "satelite": "G19",
          "banda": "C03",
          "paleta": "reflectancia",
          "ventana": {
            "start": "2026-11-07",
            "end": "2026-11-08"
          },
          "ultimos": false,
          "ultimos_n": "24",
          "hora": 15,
          "minuto": "00",
          "resolucion": "2712",
          "hora_desde": 0,
          "hora_hasta": 24,
          "animar": false,
          "fps": 12
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-08T16:50:31+00:00",
        "started_at": "2026-11-08T17:00:16+00:00",
        "finished_at": "2026-11-08T17:00:58+00:00",
        "logs": [
          {
            "at": "2026-11-08T17:00:16+00:00",
            "level": "info",
            "text": "job 82849f98af9b | goes_banda | modo=real"
          },
          {
            "at": "2026-11-08T17:00:16+00:00",
            "level": "info",
            "text": "[1/2] bajando C03 de G19 (1 slot(s))"
          },
          {
            "at": "2026-11-08T17:00:16+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\descargar_goes.py --sat G19 --banda C03 --desde 2026-11-08T15:00:00 --hasta 2026-11-08T15:10:00 --paso 10"
          },
          {
            "at": "2026-11-08T17:00:28+00:00",
            "level": "info",
            "text": "G19 C03: 1 slots (2026-11-08 15:00:00 -> 2026-11-08 15:10:00 UTC) · rango pedido"
          },
          {
            "at": "2026-11-08T17:00:28+00:00",
            "level": "info",
            "text": "Destino: <local> era5\\goes_c03_g19"
          },
          {
            "at": "2026-11-08T17:00:39+00:00",
            "level": "info",
            "text": "[1/1] 2026-11-08 15:00 UTC  descargados=1 existentes=0 errores=0  tiempo=11s"
          },
          {
            "at": "2026-11-08T17:00:39+00:00",
            "level": "info",
            "text": "Finalizado en 11s: descargados=1, existentes=0, errores=0"
          },
          {
            "at": "2026-11-08T17:00:39+00:00",
            "level": "info",
            "text": "[2/2] poster C03 2712px"
          },
          {
            "at": "2026-11-08T17:00:39+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\prototipos\\poster_goes_banda.py --banda C03 --sat G19 --desde 2026-11-08T15:00 --n 1 --paso 10 --px 2712 --paleta reflectancia --sombra-borde 0 --centro -75.2 0 --recorte 1.0 --borde  --out <repo>\\app\\var\\media\\cache\\1e8202a76eb3\\G19_C03_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T17:00:44+00:00",
            "level": "info",
            "text": "OR_ABI-L2-CMIPF-M6C03_G19_s20263121500218_e20263121509526_c20263121509584.nc"
          },
          {
            "at": "2026-11-08T17:00:44+00:00",
            "level": "info",
            "text": "slot: 2026-11-08 15:00 UTC | globo 2712 px | centro (-75.2, 0.0) | paleta reflectancia"
          },
          {
            "at": "2026-11-08T17:00:49+00:00",
            "level": "info",
            "text": "<repo>\\prototipos\\poster_goes_banda.py:185: RuntimeWarning: invalid value encountered in cast"
          },
          {
            "at": "2026-11-08T17:00:49+00:00",
            "level": "info",
            "text": "  indice = (normalizado * (n - 1)).astype(np.uint16 if n > 256 else np.uint8)"
          },
          {
            "at": "2026-11-08T17:00:49+00:00",
            "level": "info",
            "text": "  franja   256/2712"
          },
          {
            "at": "2026-11-08T17:00:49+00:00",
            "level": "info",
            "text": "  franja   512/2712"
          },
          {
            "at": "2026-11-08T17:00:49+00:00",
            "level": "info",
            "text": "  franja   768/2712"
          },
          {
            "at": "2026-11-08T17:00:50+00:00",
            "level": "info",
            "text": "  franja  1024/2712"
          },
          {
            "at": "2026-11-08T17:00:50+00:00",
            "level": "info",
            "text": "  franja  1280/2712"
          },
          {
            "at": "2026-11-08T17:00:50+00:00",
            "level": "info",
            "text": "  franja  1536/2712"
          },
          {
            "at": "2026-11-08T17:00:51+00:00",
            "level": "info",
            "text": "  franja  1792/2712"
          },
          {
            "at": "2026-11-08T17:00:51+00:00",
            "level": "info",
            "text": "  franja  2048/2712"
          },
          {
            "at": "2026-11-08T17:00:51+00:00",
            "level": "info",
            "text": "  franja  2304/2712"
          },
          {
            "at": "2026-11-08T17:00:52+00:00",
            "level": "info",
            "text": "  franja  2560/2712"
          },
          {
            "at": "2026-11-08T17:00:52+00:00",
            "level": "info",
            "text": "  franja  2712/2712"
          },
          {
            "at": "2026-11-08T17:00:52+00:00",
            "level": "info",
            "text": "disco 2712 px | 5,543,676 px con dato"
          },
          {
            "at": "2026-11-08T17:00:57+00:00",
            "level": "info",
            "text": "PNG: <repo>\\app\\var\\media\\cache\\1e8202a76eb3\\G19_C03_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T17:00:58+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "G19_C03_2026-11-08T1500.webp",
            "url": "/media/82849f98af9b/G19_C03_2026-11-08T1500.webp",
            "kind": "image",
            "bytes": 332152
          }
        ],
        "plan": [
          "bajando C03 de G19 (1 slot(s))",
          "poster C03 2712px"
        ],
        "error": null
      }
    },
    {
      "id": "c504339febb6",
      "product_id": "goes_banda",
      "params": {
        "snapshot": true,
        "paraguay": false,
        "margen": 6,
        "satelite": "G19",
        "banda": "C04",
        "paleta": "reflectancia",
        "ventana": {
          "start": "2026-11-07",
          "end": "2026-11-08"
        },
        "ultimos": false,
        "ultimos_n": "24",
        "hora": 15,
        "minuto": "00",
        "resolucion": "2712",
        "hora_desde": 0,
        "hora_hasta": 24,
        "animar": false,
        "fps": 12
      },
      "dates": [
        "2026-11-07",
        "2026-11-08"
      ],
      "snapshot": {
        "id": "c504339febb6",
        "product_id": "goes_banda",
        "product_name": "GOES - banda cruda, estilo color real",
        "params": {
          "snapshot": true,
          "paraguay": false,
          "margen": 6,
          "satelite": "G19",
          "banda": "C04",
          "paleta": "reflectancia",
          "ventana": {
            "start": "2026-11-07",
            "end": "2026-11-08"
          },
          "ultimos": false,
          "ultimos_n": "24",
          "hora": 15,
          "minuto": "00",
          "resolucion": "2712",
          "hora_desde": 0,
          "hora_hasta": 24,
          "animar": false,
          "fps": 12
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-08T16:50:35+00:00",
        "started_at": "2026-11-08T17:00:58+00:00",
        "finished_at": "2026-11-08T17:01:16+00:00",
        "logs": [
          {
            "at": "2026-11-08T17:00:58+00:00",
            "level": "info",
            "text": "job c504339febb6 | goes_banda | modo=real"
          },
          {
            "at": "2026-11-08T17:00:58+00:00",
            "level": "info",
            "text": "[1/2] bajando C04 de G19 (1 slot(s))"
          },
          {
            "at": "2026-11-08T17:00:58+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\descargar_goes.py --sat G19 --banda C04 --desde 2026-11-08T15:00:00 --hasta 2026-11-08T15:10:00 --paso 10"
          },
          {
            "at": "2026-11-08T17:01:01+00:00",
            "level": "info",
            "text": "G19 C04: 1 slots (2026-11-08 15:00:00 -> 2026-11-08 15:10:00 UTC) · rango pedido"
          },
          {
            "at": "2026-11-08T17:01:01+00:00",
            "level": "info",
            "text": "Destino: <local> era5\\goes_c04_g19"
          },
          {
            "at": "2026-11-08T17:01:04+00:00",
            "level": "info",
            "text": "[1/1] 2026-11-08 15:00 UTC  descargados=1 existentes=0 errores=0  tiempo=4s"
          },
          {
            "at": "2026-11-08T17:01:04+00:00",
            "level": "info",
            "text": "Finalizado en 4s: descargados=1, existentes=0, errores=0"
          },
          {
            "at": "2026-11-08T17:01:05+00:00",
            "level": "info",
            "text": "[2/2] poster C04 2712px"
          },
          {
            "at": "2026-11-08T17:01:05+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\prototipos\\poster_goes_banda.py --banda C04 --sat G19 --desde 2026-11-08T15:00 --n 1 --paso 10 --px 2712 --paleta reflectancia --sombra-borde 0 --centro -75.2 0 --recorte 1.0 --borde  --out <repo>\\app\\var\\media\\cache\\cc74c4e0d149\\G19_C04_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T17:01:07+00:00",
            "level": "info",
            "text": "OR_ABI-L2-CMIPF-M6C04_G19_s20263121500218_e20263121509526_c20263121509563.nc"
          },
          {
            "at": "2026-11-08T17:01:07+00:00",
            "level": "info",
            "text": "slot: 2026-11-08 15:00 UTC | globo 2712 px | centro (-75.2, 0.0) | paleta reflectancia"
          },
          {
            "at": "2026-11-08T17:01:08+00:00",
            "level": "info",
            "text": "<repo>\\prototipos\\poster_goes_banda.py:185: RuntimeWarning: invalid value encountered in cast"
          },
          {
            "at": "2026-11-08T17:01:08+00:00",
            "level": "info",
            "text": "  indice = (normalizado * (n - 1)).astype(np.uint16 if n > 256 else np.uint8)"
          },
          {
            "at": "2026-11-08T17:01:08+00:00",
            "level": "info",
            "text": "  franja   256/2712"
          },
          {
            "at": "2026-11-08T17:01:09+00:00",
            "level": "info",
            "text": "  franja   512/2712"
          },
          {
            "at": "2026-11-08T17:01:09+00:00",
            "level": "info",
            "text": "  franja   768/2712"
          },
          {
            "at": "2026-11-08T17:01:09+00:00",
            "level": "info",
            "text": "  franja  1024/2712"
          },
          {
            "at": "2026-11-08T17:01:10+00:00",
            "level": "info",
            "text": "  franja  1280/2712"
          },
          {
            "at": "2026-11-08T17:01:10+00:00",
            "level": "info",
            "text": "  franja  1536/2712"
          },
          {
            "at": "2026-11-08T17:01:10+00:00",
            "level": "info",
            "text": "  franja  1792/2712"
          },
          {
            "at": "2026-11-08T17:01:10+00:00",
            "level": "info",
            "text": "  franja  2048/2712"
          },
          {
            "at": "2026-11-08T17:01:11+00:00",
            "level": "info",
            "text": "  franja  2304/2712"
          },
          {
            "at": "2026-11-08T17:01:11+00:00",
            "level": "info",
            "text": "  franja  2560/2712"
          },
          {
            "at": "2026-11-08T17:01:11+00:00",
            "level": "info",
            "text": "  franja  2712/2712"
          },
          {
            "at": "2026-11-08T17:01:11+00:00",
            "level": "info",
            "text": "disco 2712 px | 5,543,676 px con dato"
          },
          {
            "at": "2026-11-08T17:01:16+00:00",
            "level": "info",
            "text": "PNG: <repo>\\app\\var\\media\\cache\\cc74c4e0d149\\G19_C04_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T17:01:16+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "G19_C04_2026-11-08T1500.webp",
            "url": "/media/c504339febb6/G19_C04_2026-11-08T1500.webp",
            "kind": "image",
            "bytes": 104638
          }
        ],
        "plan": [
          "bajando C04 de G19 (1 slot(s))",
          "poster C04 2712px"
        ],
        "error": null
      }
    },
    {
      "id": "6bc7f9f005dd",
      "product_id": "goes_banda",
      "params": {
        "snapshot": true,
        "paraguay": false,
        "margen": 6,
        "satelite": "G19",
        "banda": "C05",
        "paleta": "reflectancia",
        "ventana": {
          "start": "2026-11-07",
          "end": "2026-11-08"
        },
        "ultimos": false,
        "ultimos_n": "24",
        "hora": 15,
        "minuto": "00",
        "resolucion": "2712",
        "hora_desde": 0,
        "hora_hasta": 24,
        "animar": false,
        "fps": 12
      },
      "dates": [
        "2026-11-07",
        "2026-11-08"
      ],
      "snapshot": {
        "id": "6bc7f9f005dd",
        "product_id": "goes_banda",
        "product_name": "GOES - banda cruda, estilo color real",
        "params": {
          "snapshot": true,
          "paraguay": false,
          "margen": 6,
          "satelite": "G19",
          "banda": "C05",
          "paleta": "reflectancia",
          "ventana": {
            "start": "2026-11-07",
            "end": "2026-11-08"
          },
          "ultimos": false,
          "ultimos_n": "24",
          "hora": 15,
          "minuto": "00",
          "resolucion": "2712",
          "hora_desde": 0,
          "hora_hasta": 24,
          "animar": false,
          "fps": 12
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-08T16:50:40+00:00",
        "started_at": "2026-11-08T17:01:16+00:00",
        "finished_at": "2026-11-08T17:01:44+00:00",
        "logs": [
          {
            "at": "2026-11-08T17:01:16+00:00",
            "level": "info",
            "text": "job 6bc7f9f005dd | goes_banda | modo=real"
          },
          {
            "at": "2026-11-08T17:01:16+00:00",
            "level": "info",
            "text": "[1/2] bajando C05 de G19 (1 slot(s))"
          },
          {
            "at": "2026-11-08T17:01:16+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\descargar_goes.py --sat G19 --banda C05 --desde 2026-11-08T15:00:00 --hasta 2026-11-08T15:10:00 --paso 10"
          },
          {
            "at": "2026-11-08T17:01:18+00:00",
            "level": "info",
            "text": "G19 C05: 1 slots (2026-11-08 15:00:00 -> 2026-11-08 15:10:00 UTC) · rango pedido"
          },
          {
            "at": "2026-11-08T17:01:18+00:00",
            "level": "info",
            "text": "Destino: <local> era5\\goes_c05_g19"
          },
          {
            "at": "2026-11-08T17:01:28+00:00",
            "level": "info",
            "text": "[1/1] 2026-11-08 15:00 UTC  descargados=1 existentes=0 errores=0  tiempo=10s"
          },
          {
            "at": "2026-11-08T17:01:28+00:00",
            "level": "info",
            "text": "Finalizado en 10s: descargados=1, existentes=0, errores=0"
          },
          {
            "at": "2026-11-08T17:01:28+00:00",
            "level": "info",
            "text": "[2/2] poster C05 2712px"
          },
          {
            "at": "2026-11-08T17:01:28+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\prototipos\\poster_goes_banda.py --banda C05 --sat G19 --desde 2026-11-08T15:00 --n 1 --paso 10 --px 2712 --paleta reflectancia --sombra-borde 0 --centro -75.2 0 --recorte 1.0 --borde  --out <repo>\\app\\var\\media\\cache\\b0fc16945680\\G19_C05_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T17:01:31+00:00",
            "level": "info",
            "text": "OR_ABI-L2-CMIPF-M6C05_G19_s20263121500218_e20263121509526_c20263121509594.nc"
          },
          {
            "at": "2026-11-08T17:01:31+00:00",
            "level": "info",
            "text": "slot: 2026-11-08 15:00 UTC | globo 2712 px | centro (-75.2, 0.0) | paleta reflectancia"
          },
          {
            "at": "2026-11-08T17:01:35+00:00",
            "level": "info",
            "text": "<repo>\\prototipos\\poster_goes_banda.py:185: RuntimeWarning: invalid value encountered in cast"
          },
          {
            "at": "2026-11-08T17:01:35+00:00",
            "level": "info",
            "text": "  indice = (normalizado * (n - 1)).astype(np.uint16 if n > 256 else np.uint8)"
          },
          {
            "at": "2026-11-08T17:01:35+00:00",
            "level": "info",
            "text": "  franja   256/2712"
          },
          {
            "at": "2026-11-08T17:01:36+00:00",
            "level": "info",
            "text": "  franja   512/2712"
          },
          {
            "at": "2026-11-08T17:01:36+00:00",
            "level": "info",
            "text": "  franja   768/2712"
          },
          {
            "at": "2026-11-08T17:01:36+00:00",
            "level": "info",
            "text": "  franja  1024/2712"
          },
          {
            "at": "2026-11-08T17:01:37+00:00",
            "level": "info",
            "text": "  franja  1280/2712"
          },
          {
            "at": "2026-11-08T17:01:37+00:00",
            "level": "info",
            "text": "  franja  1536/2712"
          },
          {
            "at": "2026-11-08T17:01:37+00:00",
            "level": "info",
            "text": "  franja  1792/2712"
          },
          {
            "at": "2026-11-08T17:01:37+00:00",
            "level": "info",
            "text": "  franja  2048/2712"
          },
          {
            "at": "2026-11-08T17:01:38+00:00",
            "level": "info",
            "text": "  franja  2304/2712"
          },
          {
            "at": "2026-11-08T17:01:38+00:00",
            "level": "info",
            "text": "  franja  2560/2712"
          },
          {
            "at": "2026-11-08T17:01:38+00:00",
            "level": "info",
            "text": "  franja  2712/2712"
          },
          {
            "at": "2026-11-08T17:01:38+00:00",
            "level": "info",
            "text": "disco 2712 px | 5,543,676 px con dato"
          },
          {
            "at": "2026-11-08T17:01:44+00:00",
            "level": "info",
            "text": "PNG: <repo>\\app\\var\\media\\cache\\b0fc16945680\\G19_C05_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T17:01:44+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "G19_C05_2026-11-08T1500.webp",
            "url": "/media/6bc7f9f005dd/G19_C05_2026-11-08T1500.webp",
            "kind": "image",
            "bytes": 297930
          }
        ],
        "plan": [
          "bajando C05 de G19 (1 slot(s))",
          "poster C05 2712px"
        ],
        "error": null
      }
    },
    {
      "id": "67f374de1b03",
      "product_id": "goes_banda",
      "params": {
        "snapshot": true,
        "paraguay": false,
        "margen": 6,
        "satelite": "G19",
        "banda": "C06",
        "paleta": "reflectancia",
        "ventana": {
          "start": "2026-11-07",
          "end": "2026-11-08"
        },
        "ultimos": false,
        "ultimos_n": "24",
        "hora": 15,
        "minuto": "00",
        "resolucion": "2712",
        "hora_desde": 0,
        "hora_hasta": 24,
        "animar": false,
        "fps": 12
      },
      "dates": [
        "2026-11-07",
        "2026-11-08"
      ],
      "snapshot": {
        "id": "67f374de1b03",
        "product_id": "goes_banda",
        "product_name": "GOES - banda cruda, estilo color real",
        "params": {
          "snapshot": true,
          "paraguay": false,
          "margen": 6,
          "satelite": "G19",
          "banda": "C06",
          "paleta": "reflectancia",
          "ventana": {
            "start": "2026-11-07",
            "end": "2026-11-08"
          },
          "ultimos": false,
          "ultimos_n": "24",
          "hora": 15,
          "minuto": "00",
          "resolucion": "2712",
          "hora_desde": 0,
          "hora_hasta": 24,
          "animar": false,
          "fps": 12
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-08T16:50:42+00:00",
        "started_at": "2026-11-08T17:01:44+00:00",
        "finished_at": "2026-11-08T17:02:07+00:00",
        "logs": [
          {
            "at": "2026-11-08T17:01:44+00:00",
            "level": "info",
            "text": "job 67f374de1b03 | goes_banda | modo=real"
          },
          {
            "at": "2026-11-08T17:01:45+00:00",
            "level": "info",
            "text": "[1/2] bajando C06 de G19 (1 slot(s))"
          },
          {
            "at": "2026-11-08T17:01:45+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\descargar_goes.py --sat G19 --banda C06 --desde 2026-11-08T15:00:00 --hasta 2026-11-08T15:10:00 --paso 10"
          },
          {
            "at": "2026-11-08T17:01:48+00:00",
            "level": "info",
            "text": "G19 C06: 1 slots (2026-11-08 15:00:00 -> 2026-11-08 15:10:00 UTC) · rango pedido"
          },
          {
            "at": "2026-11-08T17:01:48+00:00",
            "level": "info",
            "text": "Destino: <local> era5\\goes_c06_g19"
          },
          {
            "at": "2026-11-08T17:01:51+00:00",
            "level": "info",
            "text": "[1/1] 2026-11-08 15:00 UTC  descargados=1 existentes=0 errores=0  tiempo=4s"
          },
          {
            "at": "2026-11-08T17:01:51+00:00",
            "level": "info",
            "text": "Finalizado en 4s: descargados=1, existentes=0, errores=0"
          },
          {
            "at": "2026-11-08T17:01:52+00:00",
            "level": "info",
            "text": "[2/2] poster C06 2712px"
          },
          {
            "at": "2026-11-08T17:01:52+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\prototipos\\poster_goes_banda.py --banda C06 --sat G19 --desde 2026-11-08T15:00 --n 1 --paso 10 --px 2712 --paleta reflectancia --sombra-borde 0 --centro -75.2 0 --recorte 1.0 --borde  --out <repo>\\app\\var\\media\\cache\\9bbdd4d9f85d\\G19_C06_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T17:01:55+00:00",
            "level": "info",
            "text": "OR_ABI-L2-CMIPF-M6C06_G19_s20263121500218_e20263121509532_c20263121509584.nc"
          },
          {
            "at": "2026-11-08T17:01:55+00:00",
            "level": "info",
            "text": "slot: 2026-11-08 15:00 UTC | globo 2712 px | centro (-75.2, 0.0) | paleta reflectancia"
          },
          {
            "at": "2026-11-08T17:01:57+00:00",
            "level": "info",
            "text": "<repo>\\prototipos\\poster_goes_banda.py:185: RuntimeWarning: invalid value encountered in cast"
          },
          {
            "at": "2026-11-08T17:01:57+00:00",
            "level": "info",
            "text": "  indice = (normalizado * (n - 1)).astype(np.uint16 if n > 256 else np.uint8)"
          },
          {
            "at": "2026-11-08T17:01:57+00:00",
            "level": "info",
            "text": "  franja   256/2712"
          },
          {
            "at": "2026-11-08T17:01:57+00:00",
            "level": "info",
            "text": "  franja   512/2712"
          },
          {
            "at": "2026-11-08T17:01:57+00:00",
            "level": "info",
            "text": "  franja   768/2712"
          },
          {
            "at": "2026-11-08T17:01:58+00:00",
            "level": "info",
            "text": "  franja  1024/2712"
          },
          {
            "at": "2026-11-08T17:01:58+00:00",
            "level": "info",
            "text": "  franja  1280/2712"
          },
          {
            "at": "2026-11-08T17:01:59+00:00",
            "level": "info",
            "text": "  franja  1536/2712"
          },
          {
            "at": "2026-11-08T17:01:59+00:00",
            "level": "info",
            "text": "  franja  1792/2712"
          },
          {
            "at": "2026-11-08T17:02:00+00:00",
            "level": "info",
            "text": "  franja  2048/2712"
          },
          {
            "at": "2026-11-08T17:02:00+00:00",
            "level": "info",
            "text": "  franja  2304/2712"
          },
          {
            "at": "2026-11-08T17:02:01+00:00",
            "level": "info",
            "text": "  franja  2560/2712"
          },
          {
            "at": "2026-11-08T17:02:01+00:00",
            "level": "info",
            "text": "  franja  2712/2712"
          },
          {
            "at": "2026-11-08T17:02:01+00:00",
            "level": "info",
            "text": "disco 2712 px | 5,543,676 px con dato"
          },
          {
            "at": "2026-11-08T17:02:06+00:00",
            "level": "info",
            "text": "PNG: <repo>\\app\\var\\media\\cache\\9bbdd4d9f85d\\G19_C06_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T17:02:07+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "G19_C06_2026-11-08T1500.webp",
            "url": "/media/67f374de1b03/G19_C06_2026-11-08T1500.webp",
            "kind": "image",
            "bytes": 238476
          }
        ],
        "plan": [
          "bajando C06 de G19 (1 slot(s))",
          "poster C06 2712px"
        ],
        "error": null
      }
    },
    {
      "id": "1f1b6b58491a",
      "product_id": "goes_banda",
      "params": {
        "snapshot": true,
        "paraguay": false,
        "margen": 6,
        "satelite": "G19",
        "banda": "C08",
        "paleta": "c08_ir",
        "ventana": {
          "start": "2026-11-07",
          "end": "2026-11-08"
        },
        "ultimos": false,
        "ultimos_n": "24",
        "hora": 15,
        "minuto": "00",
        "resolucion": "2712",
        "hora_desde": 0,
        "hora_hasta": 24,
        "animar": false,
        "fps": 12
      },
      "dates": [
        "2026-11-07",
        "2026-11-08"
      ],
      "snapshot": {
        "id": "1f1b6b58491a",
        "product_id": "goes_banda",
        "product_name": "GOES - banda cruda, estilo color real",
        "params": {
          "snapshot": true,
          "paraguay": false,
          "margen": 6,
          "satelite": "G19",
          "banda": "C08",
          "paleta": "c08_ir",
          "ventana": {
            "start": "2026-11-07",
            "end": "2026-11-08"
          },
          "ultimos": false,
          "ultimos_n": "24",
          "hora": 15,
          "minuto": "00",
          "resolucion": "2712",
          "hora_desde": 0,
          "hora_hasta": 24,
          "animar": false,
          "fps": 12
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-08T16:14:58+00:00",
        "started_at": "2026-11-08T16:14:58+00:00",
        "finished_at": "2026-11-08T16:15:21+00:00",
        "logs": [
          {
            "at": "2026-11-08T16:14:58+00:00",
            "level": "info",
            "text": "job 1f1b6b58491a | goes_banda | modo=real"
          },
          {
            "at": "2026-11-08T16:14:58+00:00",
            "level": "info",
            "text": "[1/2] bajando C08 de G19 (1 slot(s))"
          },
          {
            "at": "2026-11-08T16:14:58+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\descargar_goes.py --sat G19 --banda C08 --desde 2026-11-08T15:00:00 --hasta 2026-11-08T15:10:00 --paso 10"
          },
          {
            "at": "2026-11-08T16:15:03+00:00",
            "level": "info",
            "text": "G19 C08: 1 slots (2026-11-08 15:00:00 -> 2026-11-08 15:10:00 UTC) · rango pedido"
          },
          {
            "at": "2026-11-08T16:15:03+00:00",
            "level": "info",
            "text": "Destino: <local> era5\\goes_c08_g19"
          },
          {
            "at": "2026-11-08T16:15:06+00:00",
            "level": "info",
            "text": "[1/1] 2026-11-08 15:00 UTC  descargados=1 existentes=0 errores=0  tiempo=3s"
          },
          {
            "at": "2026-11-08T16:15:06+00:00",
            "level": "info",
            "text": "Finalizado en 3s: descargados=1, existentes=0, errores=0"
          },
          {
            "at": "2026-11-08T16:15:07+00:00",
            "level": "info",
            "text": "[2/2] poster C08 2712px"
          },
          {
            "at": "2026-11-08T16:15:07+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\prototipos\\poster_goes_banda.py --banda C08 --sat G19 --desde 2026-11-08T15:00 --n 1 --paso 10 --px 2712 --paleta c08_ir --sombra-borde 0 --centro -75.2 0 --recorte 1.0 --borde  --out <repo>\\app\\var\\media\\cache\\63782456c295\\G19_C08_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T16:15:10+00:00",
            "level": "info",
            "text": "OR_ABI-L2-CMIPF-M6C08_G19_s20263121500218_e20263121509526_c20263121510003.nc"
          },
          {
            "at": "2026-11-08T16:15:10+00:00",
            "level": "info",
            "text": "slot: 2026-11-08 15:00 UTC | globo 2712 px | centro (-75.2, 0.0) | paleta c08_ir"
          },
          {
            "at": "2026-11-08T16:15:12+00:00",
            "level": "info",
            "text": "<repo>\\prototipos\\poster_goes_banda.py:183: RuntimeWarning: invalid value encountered in cast"
          },
          {
            "at": "2026-11-08T16:15:12+00:00",
            "level": "info",
            "text": "  indice = (normalizado * (n - 1)).astype(np.uint16 if n > 256 else np.uint8)"
          },
          {
            "at": "2026-11-08T16:15:12+00:00",
            "level": "info",
            "text": "  franja   256/2712"
          },
          {
            "at": "2026-11-08T16:15:12+00:00",
            "level": "info",
            "text": "  franja   512/2712"
          },
          {
            "at": "2026-11-08T16:15:12+00:00",
            "level": "info",
            "text": "  franja   768/2712"
          },
          {
            "at": "2026-11-08T16:15:13+00:00",
            "level": "info",
            "text": "  franja  1024/2712"
          },
          {
            "at": "2026-11-08T16:15:13+00:00",
            "level": "info",
            "text": "  franja  1280/2712"
          },
          {
            "at": "2026-11-08T16:15:13+00:00",
            "level": "info",
            "text": "  franja  1536/2712"
          },
          {
            "at": "2026-11-08T16:15:14+00:00",
            "level": "info",
            "text": "  franja  1792/2712"
          },
          {
            "at": "2026-11-08T16:15:14+00:00",
            "level": "info",
            "text": "  franja  2048/2712"
          },
          {
            "at": "2026-11-08T16:15:14+00:00",
            "level": "info",
            "text": "  franja  2304/2712"
          },
          {
            "at": "2026-11-08T16:15:15+00:00",
            "level": "info",
            "text": "  franja  2560/2712"
          },
          {
            "at": "2026-11-08T16:15:15+00:00",
            "level": "info",
            "text": "  franja  2712/2712"
          },
          {
            "at": "2026-11-08T16:15:15+00:00",
            "level": "info",
            "text": "disco 2712 px | 5,543,676 px con dato"
          },
          {
            "at": "2026-11-08T16:15:21+00:00",
            "level": "info",
            "text": "PNG: <repo>\\app\\var\\media\\cache\\63782456c295\\G19_C08_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T16:15:21+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "G19_C08_2026-11-08T1500.webp",
            "url": "/media/1f1b6b58491a/G19_C08_2026-11-08T1500.webp",
            "kind": "image",
            "bytes": 183282
          }
        ],
        "plan": [
          "bajando C08 de G19 (1 slot(s))",
          "poster C08 2712px"
        ],
        "error": null
      }
    },
    {
      "id": "168268224bc9",
      "product_id": "goes_banda",
      "params": {
        "snapshot": true,
        "paraguay": false,
        "margen": 6,
        "satelite": "G19",
        "banda": "C09",
        "paleta": "c09_ir",
        "ventana": {
          "start": "2026-11-07",
          "end": "2026-11-08"
        },
        "ultimos": false,
        "ultimos_n": "24",
        "hora": 15,
        "minuto": "00",
        "resolucion": "2712",
        "hora_desde": 0,
        "hora_hasta": 24,
        "animar": false,
        "fps": 12
      },
      "dates": [
        "2026-11-07",
        "2026-11-08"
      ],
      "snapshot": {
        "id": "168268224bc9",
        "product_id": "goes_banda",
        "product_name": "GOES - banda cruda, estilo color real",
        "params": {
          "snapshot": true,
          "paraguay": false,
          "margen": 6,
          "satelite": "G19",
          "banda": "C09",
          "paleta": "c09_ir",
          "ventana": {
            "start": "2026-11-07",
            "end": "2026-11-08"
          },
          "ultimos": false,
          "ultimos_n": "24",
          "hora": 15,
          "minuto": "00",
          "resolucion": "2712",
          "hora_desde": 0,
          "hora_hasta": 24,
          "animar": false,
          "fps": 12
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-08T16:07:46+00:00",
        "started_at": "2026-11-08T16:07:46+00:00",
        "finished_at": "2026-11-08T16:08:04+00:00",
        "logs": [
          {
            "at": "2026-11-08T16:07:46+00:00",
            "level": "info",
            "text": "job 168268224bc9 | goes_banda | modo=real"
          },
          {
            "at": "2026-11-08T16:07:46+00:00",
            "level": "info",
            "text": "[1/2] bajando C09 de G19 (1 slot(s))"
          },
          {
            "at": "2026-11-08T16:07:46+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\descargar_goes.py --sat G19 --banda C09 --desde 2026-11-08T15:00:00 --hasta 2026-11-08T15:10:00 --paso 10"
          },
          {
            "at": "2026-11-08T16:07:48+00:00",
            "level": "info",
            "text": "G19 C09: 1 slots (2026-11-08 15:00:00 -> 2026-11-08 15:10:00 UTC) · rango pedido"
          },
          {
            "at": "2026-11-08T16:07:48+00:00",
            "level": "info",
            "text": "Destino: <local> era5\\goes_c09_g19"
          },
          {
            "at": "2026-11-08T16:07:52+00:00",
            "level": "info",
            "text": "[1/1] 2026-11-08 15:00 UTC  descargados=1 existentes=0 errores=0  tiempo=4s"
          },
          {
            "at": "2026-11-08T16:07:52+00:00",
            "level": "info",
            "text": "Finalizado en 4s: descargados=1, existentes=0, errores=0"
          },
          {
            "at": "2026-11-08T16:07:52+00:00",
            "level": "info",
            "text": "[2/2] poster C09 2712px"
          },
          {
            "at": "2026-11-08T16:07:52+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\prototipos\\poster_goes_banda.py --banda C09 --sat G19 --desde 2026-11-08T15:00 --n 1 --paso 10 --px 2712 --paleta c09_ir --sombra-borde 0 --centro -75.2 0 --recorte 1.0 --borde  --out <repo>\\app\\var\\media\\cache\\b7051eb198ba\\G19_C09_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T16:07:54+00:00",
            "level": "info",
            "text": "OR_ABI-L2-CMIPF-M6C09_G19_s20263121500218_e20263121509532_c20263121510004.nc"
          },
          {
            "at": "2026-11-08T16:07:54+00:00",
            "level": "info",
            "text": "slot: 2026-11-08 15:00 UTC | globo 2712 px | centro (-75.2, 0.0) | paleta c09_ir"
          },
          {
            "at": "2026-11-08T16:07:56+00:00",
            "level": "info",
            "text": "<repo>\\prototipos\\poster_goes_banda.py:182: RuntimeWarning: invalid value encountered in cast"
          },
          {
            "at": "2026-11-08T16:07:56+00:00",
            "level": "info",
            "text": "  indice = (normalizado * (n - 1)).astype(np.uint16 if n > 256 else np.uint8)"
          },
          {
            "at": "2026-11-08T16:07:56+00:00",
            "level": "info",
            "text": "  franja   256/2712"
          },
          {
            "at": "2026-11-08T16:07:56+00:00",
            "level": "info",
            "text": "  franja   512/2712"
          },
          {
            "at": "2026-11-08T16:07:57+00:00",
            "level": "info",
            "text": "  franja   768/2712"
          },
          {
            "at": "2026-11-08T16:07:57+00:00",
            "level": "info",
            "text": "  franja  1024/2712"
          },
          {
            "at": "2026-11-08T16:07:57+00:00",
            "level": "info",
            "text": "  franja  1280/2712"
          },
          {
            "at": "2026-11-08T16:07:57+00:00",
            "level": "info",
            "text": "  franja  1536/2712"
          },
          {
            "at": "2026-11-08T16:07:58+00:00",
            "level": "info",
            "text": "  franja  1792/2712"
          },
          {
            "at": "2026-11-08T16:07:58+00:00",
            "level": "info",
            "text": "  franja  2048/2712"
          },
          {
            "at": "2026-11-08T16:07:58+00:00",
            "level": "info",
            "text": "  franja  2304/2712"
          },
          {
            "at": "2026-11-08T16:07:59+00:00",
            "level": "info",
            "text": "  franja  2560/2712"
          },
          {
            "at": "2026-11-08T16:07:59+00:00",
            "level": "info",
            "text": "  franja  2712/2712"
          },
          {
            "at": "2026-11-08T16:07:59+00:00",
            "level": "info",
            "text": "disco 2712 px | 5,543,676 px con dato"
          },
          {
            "at": "2026-11-08T16:08:03+00:00",
            "level": "info",
            "text": "PNG: <repo>\\app\\var\\media\\cache\\b7051eb198ba\\G19_C09_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T16:08:04+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "G19_C09_2026-11-08T1500.webp",
            "url": "/media/168268224bc9/G19_C09_2026-11-08T1500.webp",
            "kind": "image",
            "bytes": 307270
          }
        ],
        "plan": [
          "bajando C09 de G19 (1 slot(s))",
          "poster C09 2712px"
        ],
        "error": null
      }
    },
    {
      "id": "44c3251e997b",
      "product_id": "goes_banda",
      "params": {
        "snapshot": true,
        "paraguay": false,
        "margen": 6,
        "satelite": "G19",
        "banda": "C10",
        "paleta": "c10_ir",
        "ventana": {
          "start": "2026-11-07",
          "end": "2026-11-08"
        },
        "ultimos": false,
        "ultimos_n": "24",
        "hora": 15,
        "minuto": "00",
        "resolucion": "2712",
        "hora_desde": 0,
        "hora_hasta": 24,
        "animar": false,
        "fps": 12
      },
      "dates": [
        "2026-11-07",
        "2026-11-08"
      ],
      "snapshot": {
        "id": "44c3251e997b",
        "product_id": "goes_banda",
        "product_name": "GOES - banda cruda, estilo color real",
        "params": {
          "snapshot": true,
          "paraguay": false,
          "margen": 6,
          "satelite": "G19",
          "banda": "C10",
          "paleta": "c10_ir",
          "ventana": {
            "start": "2026-11-07",
            "end": "2026-11-08"
          },
          "ultimos": false,
          "ultimos_n": "24",
          "hora": 15,
          "minuto": "00",
          "resolucion": "2712",
          "hora_desde": 0,
          "hora_hasta": 24,
          "animar": false,
          "fps": 12
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-08T15:56:08+00:00",
        "started_at": "2026-11-08T15:56:08+00:00",
        "finished_at": "2026-11-08T15:56:40+00:00",
        "logs": [
          {
            "at": "2026-11-08T15:56:08+00:00",
            "level": "info",
            "text": "job 44c3251e997b | goes_banda | modo=real"
          },
          {
            "at": "2026-11-08T15:56:08+00:00",
            "level": "info",
            "text": "[1/2] bajando C10 de G19 (1 slot(s))"
          },
          {
            "at": "2026-11-08T15:56:08+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\descargar_goes.py --sat G19 --banda C10 --desde 2026-11-08T15:00:00 --hasta 2026-11-08T15:10:00 --paso 10"
          },
          {
            "at": "2026-11-08T15:56:15+00:00",
            "level": "info",
            "text": "G19 C10: 1 slots (2026-11-08 15:00:00 -> 2026-11-08 15:10:00 UTC) · rango pedido"
          },
          {
            "at": "2026-11-08T15:56:15+00:00",
            "level": "info",
            "text": "Destino: <local> era5\\goes_c10_g19"
          },
          {
            "at": "2026-11-08T15:56:19+00:00",
            "level": "info",
            "text": "[1/1] 2026-11-08 15:00 UTC  descargados=1 existentes=0 errores=0  tiempo=4s"
          },
          {
            "at": "2026-11-08T15:56:19+00:00",
            "level": "info",
            "text": "Finalizado en 4s: descargados=1, existentes=0, errores=0"
          },
          {
            "at": "2026-11-08T15:56:19+00:00",
            "level": "info",
            "text": "[2/2] poster C10 2712px"
          },
          {
            "at": "2026-11-08T15:56:19+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\prototipos\\poster_goes_banda.py --banda C10 --sat G19 --desde 2026-11-08T15:00 --n 1 --paso 10 --px 2712 --paleta c10_ir --sombra-borde 0 --centro -75.2 0 --recorte 1.0 --borde  --out <repo>\\app\\var\\media\\cache\\d4a07c0400a3\\G19_C10_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T15:56:22+00:00",
            "level": "info",
            "text": "OR_ABI-L2-CMIPF-M6C10_G19_s20263121500218_e20263121509538_c20263121509593.nc"
          },
          {
            "at": "2026-11-08T15:56:22+00:00",
            "level": "info",
            "text": "slot: 2026-11-08 15:00 UTC | globo 2712 px | centro (-75.2, 0.0) | paleta c10_ir"
          },
          {
            "at": "2026-11-08T15:56:24+00:00",
            "level": "info",
            "text": "<repo>\\prototipos\\poster_goes_banda.py:181: RuntimeWarning: invalid value encountered in cast"
          },
          {
            "at": "2026-11-08T15:56:24+00:00",
            "level": "info",
            "text": "  indice = (normalizado * (n - 1)).astype(np.uint16 if n > 256 else np.uint8)"
          },
          {
            "at": "2026-11-08T15:56:24+00:00",
            "level": "info",
            "text": "  franja   256/2712"
          },
          {
            "at": "2026-11-08T15:56:25+00:00",
            "level": "info",
            "text": "  franja   512/2712"
          },
          {
            "at": "2026-11-08T15:56:25+00:00",
            "level": "info",
            "text": "  franja   768/2712"
          },
          {
            "at": "2026-11-08T15:56:26+00:00",
            "level": "info",
            "text": "  franja  1024/2712"
          },
          {
            "at": "2026-11-08T15:56:26+00:00",
            "level": "info",
            "text": "  franja  1280/2712"
          },
          {
            "at": "2026-11-08T15:56:27+00:00",
            "level": "info",
            "text": "  franja  1536/2712"
          },
          {
            "at": "2026-11-08T15:56:27+00:00",
            "level": "info",
            "text": "  franja  1792/2712"
          },
          {
            "at": "2026-11-08T15:56:27+00:00",
            "level": "info",
            "text": "  franja  2048/2712"
          },
          {
            "at": "2026-11-08T15:56:28+00:00",
            "level": "info",
            "text": "  franja  2304/2712"
          },
          {
            "at": "2026-11-08T15:56:28+00:00",
            "level": "info",
            "text": "  franja  2560/2712"
          },
          {
            "at": "2026-11-08T15:56:28+00:00",
            "level": "info",
            "text": "  franja  2712/2712"
          },
          {
            "at": "2026-11-08T15:56:28+00:00",
            "level": "info",
            "text": "disco 2712 px | 5,543,676 px con dato"
          },
          {
            "at": "2026-11-08T15:56:37+00:00",
            "level": "info",
            "text": "PNG: <repo>\\app\\var\\media\\cache\\d4a07c0400a3\\G19_C10_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T15:56:40+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "G19_C10_2026-11-08T1500.webp",
            "url": "/media/44c3251e997b/G19_C10_2026-11-08T1500.webp",
            "kind": "image",
            "bytes": 384986
          }
        ],
        "plan": [
          "bajando C10 de G19 (1 slot(s))",
          "poster C10 2712px"
        ],
        "error": null
      }
    },
    {
      "id": "5f7264c5d1a6",
      "product_id": "goes_banda",
      "params": {
        "snapshot": true,
        "paraguay": false,
        "margen": 6,
        "satelite": "G19",
        "banda": "C11",
        "paleta": "c11_ir",
        "ventana": {
          "start": "2026-11-07",
          "end": "2026-11-08"
        },
        "ultimos": false,
        "ultimos_n": "24",
        "hora": 15,
        "minuto": "00",
        "resolucion": "2712",
        "hora_desde": 0,
        "hora_hasta": 24,
        "animar": false,
        "fps": 12
      },
      "dates": [
        "2026-11-07",
        "2026-11-08"
      ],
      "snapshot": {
        "id": "5f7264c5d1a6",
        "product_id": "goes_banda",
        "product_name": "GOES - banda cruda, estilo color real",
        "params": {
          "snapshot": true,
          "paraguay": false,
          "margen": 6,
          "satelite": "G19",
          "banda": "C11",
          "paleta": "c11_ir",
          "ventana": {
            "start": "2026-11-07",
            "end": "2026-11-08"
          },
          "ultimos": false,
          "ultimos_n": "24",
          "hora": 15,
          "minuto": "00",
          "resolucion": "2712",
          "hora_desde": 0,
          "hora_hasta": 24,
          "animar": false,
          "fps": 12
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-08T17:08:56+00:00",
        "started_at": "2026-11-08T17:08:56+00:00",
        "finished_at": "2026-11-08T17:09:19+00:00",
        "logs": [
          {
            "at": "2026-11-08T17:08:57+00:00",
            "level": "info",
            "text": "job 5f7264c5d1a6 | goes_banda | modo=real"
          },
          {
            "at": "2026-11-08T17:08:57+00:00",
            "level": "info",
            "text": "[1/2] bajando C11 de G19 (1 slot(s))"
          },
          {
            "at": "2026-11-08T17:08:57+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\descargar_goes.py --sat G19 --banda C11 --desde 2026-11-08T15:00:00 --hasta 2026-11-08T15:10:00 --paso 10"
          },
          {
            "at": "2026-11-08T17:09:02+00:00",
            "level": "info",
            "text": "G19 C11: 1 slots (2026-11-08 15:00:00 -> 2026-11-08 15:10:00 UTC) · rango pedido"
          },
          {
            "at": "2026-11-08T17:09:02+00:00",
            "level": "info",
            "text": "Destino: <local> era5\\goes_c11_g19"
          },
          {
            "at": "2026-11-08T17:09:06+00:00",
            "level": "info",
            "text": "[1/1] 2026-11-08 15:00 UTC  descargados=1 existentes=0 errores=0  tiempo=5s"
          },
          {
            "at": "2026-11-08T17:09:06+00:00",
            "level": "info",
            "text": "Finalizado en 5s: descargados=1, existentes=0, errores=0"
          },
          {
            "at": "2026-11-08T17:09:06+00:00",
            "level": "info",
            "text": "[2/2] poster C11 2712px"
          },
          {
            "at": "2026-11-08T17:09:06+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\prototipos\\poster_goes_banda.py --banda C11 --sat G19 --desde 2026-11-08T15:00 --n 1 --paso 10 --px 2712 --paleta c11_ir --sombra-borde 0 --centro -75.2 0 --recorte 1.0 --borde  --out <repo>\\app\\var\\media\\cache\\bb69b8e3f84e\\G19_C11_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T17:09:09+00:00",
            "level": "info",
            "text": "OR_ABI-L2-CMIPF-M6C11_G19_s20263121500218_e20263121509526_c20263121509584.nc"
          },
          {
            "at": "2026-11-08T17:09:09+00:00",
            "level": "info",
            "text": "slot: 2026-11-08 15:00 UTC | globo 2712 px | centro (-75.2, 0.0) | paleta c11_ir"
          },
          {
            "at": "2026-11-08T17:09:10+00:00",
            "level": "info",
            "text": "<repo>\\prototipos\\poster_goes_banda.py:185: RuntimeWarning: invalid value encountered in cast"
          },
          {
            "at": "2026-11-08T17:09:10+00:00",
            "level": "info",
            "text": "  indice = (normalizado * (n - 1)).astype(np.uint16 if n > 256 else np.uint8)"
          },
          {
            "at": "2026-11-08T17:09:10+00:00",
            "level": "info",
            "text": "  franja   256/2712"
          },
          {
            "at": "2026-11-08T17:09:10+00:00",
            "level": "info",
            "text": "  franja   512/2712"
          },
          {
            "at": "2026-11-08T17:09:11+00:00",
            "level": "info",
            "text": "  franja   768/2712"
          },
          {
            "at": "2026-11-08T17:09:11+00:00",
            "level": "info",
            "text": "  franja  1024/2712"
          },
          {
            "at": "2026-11-08T17:09:11+00:00",
            "level": "info",
            "text": "  franja  1280/2712"
          },
          {
            "at": "2026-11-08T17:09:12+00:00",
            "level": "info",
            "text": "  franja  1536/2712"
          },
          {
            "at": "2026-11-08T17:09:12+00:00",
            "level": "info",
            "text": "  franja  1792/2712"
          },
          {
            "at": "2026-11-08T17:09:12+00:00",
            "level": "info",
            "text": "  franja  2048/2712"
          },
          {
            "at": "2026-11-08T17:09:13+00:00",
            "level": "info",
            "text": "  franja  2304/2712"
          },
          {
            "at": "2026-11-08T17:09:13+00:00",
            "level": "info",
            "text": "  franja  2560/2712"
          },
          {
            "at": "2026-11-08T17:09:13+00:00",
            "level": "info",
            "text": "  franja  2712/2712"
          },
          {
            "at": "2026-11-08T17:09:13+00:00",
            "level": "info",
            "text": "disco 2712 px | 5,543,676 px con dato"
          },
          {
            "at": "2026-11-08T17:09:19+00:00",
            "level": "info",
            "text": "PNG: <repo>\\app\\var\\media\\cache\\bb69b8e3f84e\\G19_C11_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T17:09:19+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "G19_C11_2026-11-08T1500.webp",
            "url": "/media/5f7264c5d1a6/G19_C11_2026-11-08T1500.webp",
            "kind": "image",
            "bytes": 285680
          }
        ],
        "plan": [
          "bajando C11 de G19 (1 slot(s))",
          "poster C11 2712px"
        ],
        "error": null
      }
    },
    {
      "id": "6b71d5e4f233",
      "product_id": "goes_banda",
      "params": {
        "snapshot": true,
        "paraguay": false,
        "margen": 6,
        "satelite": "G19",
        "banda": "C12",
        "paleta": "c12_ir",
        "ventana": {
          "start": "2026-11-07",
          "end": "2026-11-08"
        },
        "ultimos": false,
        "ultimos_n": "24",
        "hora": 15,
        "minuto": "00",
        "resolucion": "2712",
        "hora_desde": 0,
        "hora_hasta": 24,
        "animar": false,
        "fps": 12
      },
      "dates": [
        "2026-11-07",
        "2026-11-08"
      ],
      "snapshot": {
        "id": "6b71d5e4f233",
        "product_id": "goes_banda",
        "product_name": "GOES - banda cruda, estilo color real",
        "params": {
          "snapshot": true,
          "paraguay": false,
          "margen": 6,
          "satelite": "G19",
          "banda": "C12",
          "paleta": "c12_ir",
          "ventana": {
            "start": "2026-11-07",
            "end": "2026-11-08"
          },
          "ultimos": false,
          "ultimos_n": "24",
          "hora": 15,
          "minuto": "00",
          "resolucion": "2712",
          "hora_desde": 0,
          "hora_hasta": 24,
          "animar": false,
          "fps": 12
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-08T17:09:00+00:00",
        "started_at": "2026-11-08T17:09:19+00:00",
        "finished_at": "2026-11-08T17:09:37+00:00",
        "logs": [
          {
            "at": "2026-11-08T17:09:19+00:00",
            "level": "info",
            "text": "job 6b71d5e4f233 | goes_banda | modo=real"
          },
          {
            "at": "2026-11-08T17:09:19+00:00",
            "level": "info",
            "text": "[1/2] bajando C12 de G19 (1 slot(s))"
          },
          {
            "at": "2026-11-08T17:09:19+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\descargar_goes.py --sat G19 --banda C12 --desde 2026-11-08T15:00:00 --hasta 2026-11-08T15:10:00 --paso 10"
          },
          {
            "at": "2026-11-08T17:09:21+00:00",
            "level": "info",
            "text": "G19 C12: 1 slots (2026-11-08 15:00:00 -> 2026-11-08 15:10:00 UTC) · rango pedido"
          },
          {
            "at": "2026-11-08T17:09:21+00:00",
            "level": "info",
            "text": "Destino: <local> era5\\goes_c12_g19"
          },
          {
            "at": "2026-11-08T17:09:25+00:00",
            "level": "info",
            "text": "[1/1] 2026-11-08 15:00 UTC  descargados=1 existentes=0 errores=0  tiempo=4s"
          },
          {
            "at": "2026-11-08T17:09:25+00:00",
            "level": "info",
            "text": "Finalizado en 4s: descargados=1, existentes=0, errores=0"
          },
          {
            "at": "2026-11-08T17:09:25+00:00",
            "level": "info",
            "text": "[2/2] poster C12 2712px"
          },
          {
            "at": "2026-11-08T17:09:25+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\prototipos\\poster_goes_banda.py --banda C12 --sat G19 --desde 2026-11-08T15:00 --n 1 --paso 10 --px 2712 --paleta c12_ir --sombra-borde 0 --centro -75.2 0 --recorte 1.0 --borde  --out <repo>\\app\\var\\media\\cache\\68453ef2dc6e\\G19_C12_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T17:09:27+00:00",
            "level": "info",
            "text": "OR_ABI-L2-CMIPF-M6C12_G19_s20263121500218_e20263121509532_c20263121509584.nc"
          },
          {
            "at": "2026-11-08T17:09:27+00:00",
            "level": "info",
            "text": "slot: 2026-11-08 15:00 UTC | globo 2712 px | centro (-75.2, 0.0) | paleta c12_ir"
          },
          {
            "at": "2026-11-08T17:09:29+00:00",
            "level": "info",
            "text": "<repo>\\prototipos\\poster_goes_banda.py:185: RuntimeWarning: invalid value encountered in cast"
          },
          {
            "at": "2026-11-08T17:09:29+00:00",
            "level": "info",
            "text": "  indice = (normalizado * (n - 1)).astype(np.uint16 if n > 256 else np.uint8)"
          },
          {
            "at": "2026-11-08T17:09:29+00:00",
            "level": "info",
            "text": "  franja   256/2712"
          },
          {
            "at": "2026-11-08T17:09:29+00:00",
            "level": "info",
            "text": "  franja   512/2712"
          },
          {
            "at": "2026-11-08T17:09:29+00:00",
            "level": "info",
            "text": "  franja   768/2712"
          },
          {
            "at": "2026-11-08T17:09:30+00:00",
            "level": "info",
            "text": "  franja  1024/2712"
          },
          {
            "at": "2026-11-08T17:09:30+00:00",
            "level": "info",
            "text": "  franja  1280/2712"
          },
          {
            "at": "2026-11-08T17:09:30+00:00",
            "level": "info",
            "text": "  franja  1536/2712"
          },
          {
            "at": "2026-11-08T17:09:31+00:00",
            "level": "info",
            "text": "  franja  1792/2712"
          },
          {
            "at": "2026-11-08T17:09:31+00:00",
            "level": "info",
            "text": "  franja  2048/2712"
          },
          {
            "at": "2026-11-08T17:09:31+00:00",
            "level": "info",
            "text": "  franja  2304/2712"
          },
          {
            "at": "2026-11-08T17:09:31+00:00",
            "level": "info",
            "text": "  franja  2560/2712"
          },
          {
            "at": "2026-11-08T17:09:32+00:00",
            "level": "info",
            "text": "  franja  2712/2712"
          },
          {
            "at": "2026-11-08T17:09:32+00:00",
            "level": "info",
            "text": "disco 2712 px | 5,543,676 px con dato"
          },
          {
            "at": "2026-11-08T17:09:36+00:00",
            "level": "info",
            "text": "PNG: <repo>\\app\\var\\media\\cache\\68453ef2dc6e\\G19_C12_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T17:09:37+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "G19_C12_2026-11-08T1500.webp",
            "url": "/media/6b71d5e4f233/G19_C12_2026-11-08T1500.webp",
            "kind": "image",
            "bytes": 261806
          }
        ],
        "plan": [
          "bajando C12 de G19 (1 slot(s))",
          "poster C12 2712px"
        ],
        "error": null
      }
    },
    {
      "id": "3d9883550fbf",
      "product_id": "goes_banda",
      "params": {
        "snapshot": true,
        "paraguay": false,
        "margen": 6,
        "satelite": "G19",
        "banda": "C14",
        "paleta": "c14_ir",
        "ventana": {
          "start": "2026-11-07",
          "end": "2026-11-08"
        },
        "ultimos": false,
        "ultimos_n": "24",
        "hora": 15,
        "minuto": "00",
        "resolucion": "2712",
        "hora_desde": 0,
        "hora_hasta": 24,
        "animar": false,
        "fps": 12
      },
      "dates": [
        "2026-11-07",
        "2026-11-08"
      ],
      "snapshot": {
        "id": "3d9883550fbf",
        "product_id": "goes_banda",
        "product_name": "GOES - banda cruda, estilo color real",
        "params": {
          "snapshot": true,
          "paraguay": false,
          "margen": 6,
          "satelite": "G19",
          "banda": "C14",
          "paleta": "c14_ir",
          "ventana": {
            "start": "2026-11-07",
            "end": "2026-11-08"
          },
          "ultimos": false,
          "ultimos_n": "24",
          "hora": 15,
          "minuto": "00",
          "resolucion": "2712",
          "hora_desde": 0,
          "hora_hasta": 24,
          "animar": false,
          "fps": 12
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-08T17:09:15+00:00",
        "started_at": "2026-11-08T17:09:57+00:00",
        "finished_at": "2026-11-08T17:10:16+00:00",
        "logs": [
          {
            "at": "2026-11-08T17:09:57+00:00",
            "level": "info",
            "text": "job 3d9883550fbf | goes_banda | modo=real"
          },
          {
            "at": "2026-11-08T17:09:57+00:00",
            "level": "info",
            "text": "[1/2] bajando C14 de G19 (1 slot(s))"
          },
          {
            "at": "2026-11-08T17:09:57+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\descargar_goes.py --sat G19 --banda C14 --desde 2026-11-08T15:00:00 --hasta 2026-11-08T15:10:00 --paso 10"
          },
          {
            "at": "2026-11-08T17:10:00+00:00",
            "level": "info",
            "text": "G19 C14: 1 slots (2026-11-08 15:00:00 -> 2026-11-08 15:10:00 UTC) · rango pedido"
          },
          {
            "at": "2026-11-08T17:10:00+00:00",
            "level": "info",
            "text": "Destino: <local> era5\\goes_c14_g19"
          },
          {
            "at": "2026-11-08T17:10:04+00:00",
            "level": "info",
            "text": "[1/1] 2026-11-08 15:00 UTC  descargados=1 existentes=0 errores=0  tiempo=4s"
          },
          {
            "at": "2026-11-08T17:10:04+00:00",
            "level": "info",
            "text": "Finalizado en 4s: descargados=1, existentes=0, errores=0"
          },
          {
            "at": "2026-11-08T17:10:04+00:00",
            "level": "info",
            "text": "[2/2] poster C14 2712px"
          },
          {
            "at": "2026-11-08T17:10:04+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\prototipos\\poster_goes_banda.py --banda C14 --sat G19 --desde 2026-11-08T15:00 --n 1 --paso 10 --px 2712 --paleta c14_ir --sombra-borde 0 --centro -75.2 0 --recorte 1.0 --borde  --out <repo>\\app\\var\\media\\cache\\20cb2f6efc8f\\G19_C14_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T17:10:06+00:00",
            "level": "info",
            "text": "OR_ABI-L2-CMIPF-M6C14_G19_s20263121500218_e20263121509526_c20263121509593.nc"
          },
          {
            "at": "2026-11-08T17:10:06+00:00",
            "level": "info",
            "text": "slot: 2026-11-08 15:00 UTC | globo 2712 px | centro (-75.2, 0.0) | paleta c14_ir"
          },
          {
            "at": "2026-11-08T17:10:08+00:00",
            "level": "info",
            "text": "<repo>\\prototipos\\poster_goes_banda.py:185: RuntimeWarning: invalid value encountered in cast"
          },
          {
            "at": "2026-11-08T17:10:08+00:00",
            "level": "info",
            "text": "  indice = (normalizado * (n - 1)).astype(np.uint16 if n > 256 else np.uint8)"
          },
          {
            "at": "2026-11-08T17:10:08+00:00",
            "level": "info",
            "text": "  franja   256/2712"
          },
          {
            "at": "2026-11-08T17:10:08+00:00",
            "level": "info",
            "text": "  franja   512/2712"
          },
          {
            "at": "2026-11-08T17:10:08+00:00",
            "level": "info",
            "text": "  franja   768/2712"
          },
          {
            "at": "2026-11-08T17:10:09+00:00",
            "level": "info",
            "text": "  franja  1024/2712"
          },
          {
            "at": "2026-11-08T17:10:09+00:00",
            "level": "info",
            "text": "  franja  1280/2712"
          },
          {
            "at": "2026-11-08T17:10:09+00:00",
            "level": "info",
            "text": "  franja  1536/2712"
          },
          {
            "at": "2026-11-08T17:10:10+00:00",
            "level": "info",
            "text": "  franja  1792/2712"
          },
          {
            "at": "2026-11-08T17:10:10+00:00",
            "level": "info",
            "text": "  franja  2048/2712"
          },
          {
            "at": "2026-11-08T17:10:10+00:00",
            "level": "info",
            "text": "  franja  2304/2712"
          },
          {
            "at": "2026-11-08T17:10:11+00:00",
            "level": "info",
            "text": "  franja  2560/2712"
          },
          {
            "at": "2026-11-08T17:10:11+00:00",
            "level": "info",
            "text": "  franja  2712/2712"
          },
          {
            "at": "2026-11-08T17:10:11+00:00",
            "level": "info",
            "text": "disco 2712 px | 5,543,676 px con dato"
          },
          {
            "at": "2026-11-08T17:10:16+00:00",
            "level": "info",
            "text": "PNG: <repo>\\app\\var\\media\\cache\\20cb2f6efc8f\\G19_C14_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T17:10:16+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "G19_C14_2026-11-08T1500.webp",
            "url": "/media/3d9883550fbf/G19_C14_2026-11-08T1500.webp",
            "kind": "image",
            "bytes": 295098
          }
        ],
        "plan": [
          "bajando C14 de G19 (1 slot(s))",
          "poster C14 2712px"
        ],
        "error": null
      }
    },
    {
      "id": "a8bd1b5daff4",
      "product_id": "goes_banda",
      "params": {
        "snapshot": true,
        "paraguay": false,
        "margen": 6,
        "satelite": "G19",
        "banda": "C15",
        "paleta": "c15_ir",
        "ventana": {
          "start": "2026-11-07",
          "end": "2026-11-08"
        },
        "ultimos": false,
        "ultimos_n": "24",
        "hora": 15,
        "minuto": "00",
        "resolucion": "2712",
        "hora_desde": 0,
        "hora_hasta": 24,
        "animar": false,
        "fps": 12
      },
      "dates": [
        "2026-11-07",
        "2026-11-08"
      ],
      "snapshot": {
        "id": "a8bd1b5daff4",
        "product_id": "goes_banda",
        "product_name": "GOES - banda cruda, estilo color real",
        "params": {
          "snapshot": true,
          "paraguay": false,
          "margen": 6,
          "satelite": "G19",
          "banda": "C15",
          "paleta": "c15_ir",
          "ventana": {
            "start": "2026-11-07",
            "end": "2026-11-08"
          },
          "ultimos": false,
          "ultimos_n": "24",
          "hora": 15,
          "minuto": "00",
          "resolucion": "2712",
          "hora_desde": 0,
          "hora_hasta": 24,
          "animar": false,
          "fps": 12
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-08T17:09:19+00:00",
        "started_at": "2026-11-08T17:10:16+00:00",
        "finished_at": "2026-11-08T17:10:37+00:00",
        "logs": [
          {
            "at": "2026-11-08T17:10:17+00:00",
            "level": "info",
            "text": "job a8bd1b5daff4 | goes_banda | modo=real"
          },
          {
            "at": "2026-11-08T17:10:17+00:00",
            "level": "info",
            "text": "[1/2] bajando C15 de G19 (1 slot(s))"
          },
          {
            "at": "2026-11-08T17:10:17+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\descargar_goes.py --sat G19 --banda C15 --desde 2026-11-08T15:00:00 --hasta 2026-11-08T15:10:00 --paso 10"
          },
          {
            "at": "2026-11-08T17:10:19+00:00",
            "level": "info",
            "text": "G19 C15: 1 slots (2026-11-08 15:00:00 -> 2026-11-08 15:10:00 UTC) · rango pedido"
          },
          {
            "at": "2026-11-08T17:10:19+00:00",
            "level": "info",
            "text": "Destino: <local> era5\\goes_c15_g19"
          },
          {
            "at": "2026-11-08T17:10:23+00:00",
            "level": "info",
            "text": "[1/1] 2026-11-08 15:00 UTC  descargados=1 existentes=0 errores=0  tiempo=4s"
          },
          {
            "at": "2026-11-08T17:10:23+00:00",
            "level": "info",
            "text": "Finalizado en 4s: descargados=1, existentes=0, errores=0"
          },
          {
            "at": "2026-11-08T17:10:23+00:00",
            "level": "info",
            "text": "[2/2] poster C15 2712px"
          },
          {
            "at": "2026-11-08T17:10:23+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\prototipos\\poster_goes_banda.py --banda C15 --sat G19 --desde 2026-11-08T15:00 --n 1 --paso 10 --px 2712 --paleta c15_ir --sombra-borde 0 --centro -75.2 0 --recorte 1.0 --borde  --out <repo>\\app\\var\\media\\cache\\071cadf65216\\G19_C15_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T17:10:26+00:00",
            "level": "info",
            "text": "OR_ABI-L2-CMIPF-M6C15_G19_s20263121500218_e20263121509532_c20263121510003.nc"
          },
          {
            "at": "2026-11-08T17:10:26+00:00",
            "level": "info",
            "text": "slot: 2026-11-08 15:00 UTC | globo 2712 px | centro (-75.2, 0.0) | paleta c15_ir"
          },
          {
            "at": "2026-11-08T17:10:27+00:00",
            "level": "info",
            "text": "<repo>\\prototipos\\poster_goes_banda.py:185: RuntimeWarning: invalid value encountered in cast"
          },
          {
            "at": "2026-11-08T17:10:27+00:00",
            "level": "info",
            "text": "  indice = (normalizado * (n - 1)).astype(np.uint16 if n > 256 else np.uint8)"
          },
          {
            "at": "2026-11-08T17:10:27+00:00",
            "level": "info",
            "text": "  franja   256/2712"
          },
          {
            "at": "2026-11-08T17:10:27+00:00",
            "level": "info",
            "text": "  franja   512/2712"
          },
          {
            "at": "2026-11-08T17:10:28+00:00",
            "level": "info",
            "text": "  franja   768/2712"
          },
          {
            "at": "2026-11-08T17:10:28+00:00",
            "level": "info",
            "text": "  franja  1024/2712"
          },
          {
            "at": "2026-11-08T17:10:29+00:00",
            "level": "info",
            "text": "  franja  1280/2712"
          },
          {
            "at": "2026-11-08T17:10:29+00:00",
            "level": "info",
            "text": "  franja  1536/2712"
          },
          {
            "at": "2026-11-08T17:10:29+00:00",
            "level": "info",
            "text": "  franja  1792/2712"
          },
          {
            "at": "2026-11-08T17:10:30+00:00",
            "level": "info",
            "text": "  franja  2048/2712"
          },
          {
            "at": "2026-11-08T17:10:30+00:00",
            "level": "info",
            "text": "  franja  2304/2712"
          },
          {
            "at": "2026-11-08T17:10:31+00:00",
            "level": "info",
            "text": "  franja  2560/2712"
          },
          {
            "at": "2026-11-08T17:10:31+00:00",
            "level": "info",
            "text": "  franja  2712/2712"
          },
          {
            "at": "2026-11-08T17:10:31+00:00",
            "level": "info",
            "text": "disco 2712 px | 5,543,676 px con dato"
          },
          {
            "at": "2026-11-08T17:10:36+00:00",
            "level": "info",
            "text": "PNG: <repo>\\app\\var\\media\\cache\\071cadf65216\\G19_C15_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T17:10:37+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "G19_C15_2026-11-08T1500.webp",
            "url": "/media/a8bd1b5daff4/G19_C15_2026-11-08T1500.webp",
            "kind": "image",
            "bytes": 291364
          }
        ],
        "plan": [
          "bajando C15 de G19 (1 slot(s))",
          "poster C15 2712px"
        ],
        "error": null
      }
    },
    {
      "id": "86d7997f00ff",
      "product_id": "goes_banda",
      "params": {
        "snapshot": true,
        "paraguay": false,
        "margen": 6,
        "satelite": "G19",
        "banda": "C16",
        "paleta": "c16_ir",
        "ventana": {
          "start": "2026-11-07",
          "end": "2026-11-08"
        },
        "ultimos": false,
        "ultimos_n": "24",
        "hora": 15,
        "minuto": "00",
        "resolucion": "2712",
        "hora_desde": 0,
        "hora_hasta": 24,
        "animar": false,
        "fps": 12
      },
      "dates": [
        "2026-11-07",
        "2026-11-08"
      ],
      "snapshot": {
        "id": "86d7997f00ff",
        "product_id": "goes_banda",
        "product_name": "GOES - banda cruda, estilo color real",
        "params": {
          "snapshot": true,
          "paraguay": false,
          "margen": 6,
          "satelite": "G19",
          "banda": "C16",
          "paleta": "c16_ir",
          "ventana": {
            "start": "2026-11-07",
            "end": "2026-11-08"
          },
          "ultimos": false,
          "ultimos_n": "24",
          "hora": 15,
          "minuto": "00",
          "resolucion": "2712",
          "hora_desde": 0,
          "hora_hasta": 24,
          "animar": false,
          "fps": 12
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-08T17:09:22+00:00",
        "started_at": "2026-11-08T17:10:37+00:00",
        "finished_at": "2026-11-08T17:10:55+00:00",
        "logs": [
          {
            "at": "2026-11-08T17:10:37+00:00",
            "level": "info",
            "text": "job 86d7997f00ff | goes_banda | modo=real"
          },
          {
            "at": "2026-11-08T17:10:37+00:00",
            "level": "info",
            "text": "[1/2] bajando C16 de G19 (1 slot(s))"
          },
          {
            "at": "2026-11-08T17:10:37+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\descargar_goes.py --sat G19 --banda C16 --desde 2026-11-08T15:00:00 --hasta 2026-11-08T15:10:00 --paso 10"
          },
          {
            "at": "2026-11-08T17:10:39+00:00",
            "level": "info",
            "text": "G19 C16: 1 slots (2026-11-08 15:00:00 -> 2026-11-08 15:10:00 UTC) · rango pedido"
          },
          {
            "at": "2026-11-08T17:10:39+00:00",
            "level": "info",
            "text": "Destino: <local> era5\\goes_c16_g19"
          },
          {
            "at": "2026-11-08T17:10:43+00:00",
            "level": "info",
            "text": "[1/1] 2026-11-08 15:00 UTC  descargados=1 existentes=0 errores=0  tiempo=4s"
          },
          {
            "at": "2026-11-08T17:10:43+00:00",
            "level": "info",
            "text": "Finalizado en 4s: descargados=1, existentes=0, errores=0"
          },
          {
            "at": "2026-11-08T17:10:43+00:00",
            "level": "info",
            "text": "[2/2] poster C16 2712px"
          },
          {
            "at": "2026-11-08T17:10:43+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\prototipos\\poster_goes_banda.py --banda C16 --sat G19 --desde 2026-11-08T15:00 --n 1 --paso 10 --px 2712 --paleta c16_ir --sombra-borde 0 --centro -75.2 0 --recorte 1.0 --borde  --out <repo>\\app\\var\\media\\cache\\d0d1cec062bd\\G19_C16_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T17:10:46+00:00",
            "level": "info",
            "text": "OR_ABI-L2-CMIPF-M6C16_G19_s20263121500218_e20263121509538_c20263121509593.nc"
          },
          {
            "at": "2026-11-08T17:10:46+00:00",
            "level": "info",
            "text": "slot: 2026-11-08 15:00 UTC | globo 2712 px | centro (-75.2, 0.0) | paleta c16_ir"
          },
          {
            "at": "2026-11-08T17:10:47+00:00",
            "level": "info",
            "text": "<repo>\\prototipos\\poster_goes_banda.py:185: RuntimeWarning: invalid value encountered in cast"
          },
          {
            "at": "2026-11-08T17:10:47+00:00",
            "level": "info",
            "text": "  indice = (normalizado * (n - 1)).astype(np.uint16 if n > 256 else np.uint8)"
          },
          {
            "at": "2026-11-08T17:10:47+00:00",
            "level": "info",
            "text": "  franja   256/2712"
          },
          {
            "at": "2026-11-08T17:10:48+00:00",
            "level": "info",
            "text": "  franja   512/2712"
          },
          {
            "at": "2026-11-08T17:10:48+00:00",
            "level": "info",
            "text": "  franja   768/2712"
          },
          {
            "at": "2026-11-08T17:10:48+00:00",
            "level": "info",
            "text": "  franja  1024/2712"
          },
          {
            "at": "2026-11-08T17:10:49+00:00",
            "level": "info",
            "text": "  franja  1280/2712"
          },
          {
            "at": "2026-11-08T17:10:49+00:00",
            "level": "info",
            "text": "  franja  1536/2712"
          },
          {
            "at": "2026-11-08T17:10:49+00:00",
            "level": "info",
            "text": "  franja  1792/2712"
          },
          {
            "at": "2026-11-08T17:10:50+00:00",
            "level": "info",
            "text": "  franja  2048/2712"
          },
          {
            "at": "2026-11-08T17:10:50+00:00",
            "level": "info",
            "text": "  franja  2304/2712"
          },
          {
            "at": "2026-11-08T17:10:50+00:00",
            "level": "info",
            "text": "  franja  2560/2712"
          },
          {
            "at": "2026-11-08T17:10:51+00:00",
            "level": "info",
            "text": "  franja  2712/2712"
          },
          {
            "at": "2026-11-08T17:10:51+00:00",
            "level": "info",
            "text": "disco 2712 px | 5,543,676 px con dato"
          },
          {
            "at": "2026-11-08T17:10:55+00:00",
            "level": "info",
            "text": "PNG: <repo>\\app\\var\\media\\cache\\d0d1cec062bd\\G19_C16_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T17:10:55+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "G19_C16_2026-11-08T1500.webp",
            "url": "/media/86d7997f00ff/G19_C16_2026-11-08T1500.webp",
            "kind": "image",
            "bytes": 321266
          }
        ],
        "plan": [
          "bajando C16 de G19 (1 slot(s))",
          "poster C16 2712px"
        ],
        "error": null
      }
    },
    {
      "id": "e9d1c9f6004d",
      "product_id": "goes_c13",
      "params": {
        "snapshot": false,
        "satelite": "G19",
        "ventana": {
          "start": "2026-11-03",
          "end": "2026-11-04"
        },
        "ultimos": true,
        "ultimos_n": "12",
        "hora": 15,
        "minuto": "00",
        "paleta": "clean_ir",
        "resolucion": "1400",
        "hora_desde": 0,
        "hora_hasta": 24,
        "animar": false,
        "fps": 6
      },
      "dates": [
        "2026-11-03",
        "2026-11-04"
      ],
      "snapshot": {
        "id": "e9d1c9f6004d",
        "product_id": "goes_c13",
        "product_name": "GOES - IR en globo (C13)",
        "params": {
          "snapshot": false,
          "satelite": "G19",
          "ventana": {
            "start": "2026-11-03",
            "end": "2026-11-04"
          },
          "ultimos": true,
          "ultimos_n": "12",
          "hora": 15,
          "minuto": "00",
          "paleta": "clean_ir",
          "resolucion": "1400",
          "hora_desde": 0,
          "hora_hasta": 24,
          "animar": false,
          "fps": 6
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-04T19:16:58+00:00",
        "started_at": "2026-11-04T19:17:00+00:00",
        "finished_at": "2026-11-04T19:21:18+00:00",
        "logs": [
          {
            "at": "2026-11-04T19:17:00+00:00",
            "level": "info",
            "text": "job e9d1c9f6004d | goes_c13 | modo=real"
          },
          {
            "at": "2026-11-04T19:17:02+00:00",
            "level": "info",
            "text": "[1/3] bajando los últimos 12 slots de C13 (G19)"
          },
          {
            "at": "2026-11-04T19:17:02+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\descargar_goes.py --sat G19 --banda C13 --desde 2026-11-04T17:10:00 --hasta 2026-11-04T19:10:00 --paso 10"
          },
          {
            "at": "2026-11-04T19:17:05+00:00",
            "level": "info",
            "text": "G19 C13: 12 slots (2026-11-04 17:10:00 -> 2026-11-04 19:10:00 UTC) · rango pedido"
          },
          {
            "at": "2026-11-04T19:17:05+00:00",
            "level": "info",
            "text": "Destino: <local> era5\\goes_c13_g19"
          },
          {
            "at": "2026-11-04T19:17:16+00:00",
            "level": "info",
            "text": "[10/12] 2026-11-04 18:40 UTC  descargados=3 existentes=7 errores=0  tiempo=11s"
          },
          {
            "at": "2026-11-04T19:17:23+00:00",
            "level": "info",
            "text": "[12/12] 2026-11-04 19:00 UTC  descargados=5 existentes=7 errores=0  tiempo=18s"
          },
          {
            "at": "2026-11-04T19:17:23+00:00",
            "level": "info",
            "text": "Finalizado en 18s: descargados=5, existentes=7, errores=0"
          },
          {
            "at": "2026-11-04T19:17:23+00:00",
            "level": "info",
            "text": "[2/3] renderizando 12 cuadro(s) de C13"
          },
          {
            "at": "2026-11-04T19:17:23+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\cuadros\\cuadros_c13_ir.py --sat G19 --desde 2026-11-04T17:10 --n 12 --paso 10 --px 1400 --paleta clean_ir --geojson  --centro -75.2 0 --radio 90 --datos <local> era5\\goes_c13_g19 --out <repo>\\app\\var\\media\\cache\\1c68639dc983 --frames <repo>\\app\\var\\media\\cache\\1c68639dc983\\frames --lote 1 --vmin -92.1 --vmax 56.9"
          },
          {
            "at": "2026-11-04T19:17:25+00:00",
            "level": "info",
            "text": "G19 C13 | 12 cuadros desde 2026-11-04 17:10 UTC | 1400x1400 px | radio 90° | frames en <repo>\\app\\var\\media\\cache\\1c68639dc983\\frames"
          },
          {
            "at": "2026-11-04T19:17:46+00:00",
            "level": "info",
            "text": "  lote 1-1 ok (20s)"
          },
          {
            "at": "2026-11-04T19:18:07+00:00",
            "level": "info",
            "text": "  lote 2-2 ok (42s)"
          },
          {
            "at": "2026-11-04T19:18:25+00:00",
            "level": "info",
            "text": "  lote 3-3 ok (60s)"
          },
          {
            "at": "2026-11-04T19:18:43+00:00",
            "level": "info",
            "text": "  lote 4-4 ok (77s)"
          },
          {
            "at": "2026-11-04T19:19:02+00:00",
            "level": "info",
            "text": "  lote 5-5 ok (96s)"
          },
          {
            "at": "2026-11-04T19:19:20+00:00",
            "level": "info",
            "text": "  lote 6-6 ok (115s)"
          },
          {
            "at": "2026-11-04T19:19:40+00:00",
            "level": "info",
            "text": "  lote 7-7 ok (134s)"
          },
          {
            "at": "2026-11-04T19:19:58+00:00",
            "level": "info",
            "text": "  lote 8-8 ok (153s)"
          },
          {
            "at": "2026-11-04T19:20:16+00:00",
            "level": "info",
            "text": "  lote 9-9 ok (171s)"
          },
          {
            "at": "2026-11-04T19:20:35+00:00",
            "level": "info",
            "text": "  lote 10-10 ok (190s)"
          },
          {
            "at": "2026-11-04T19:20:53+00:00",
            "level": "info",
            "text": "  lote 11-11 ok (207s)"
          },
          {
            "at": "2026-11-04T19:21:11+00:00",
            "level": "info",
            "text": "  lote 12-12 ok (226s)"
          },
          {
            "at": "2026-11-04T19:21:11+00:00",
            "level": "info",
            "text": "Cuadros en <repo>\\app\\var\\media\\cache\\1c68639dc983\\frames"
          },
          {
            "at": "2026-11-04T19:21:11+00:00",
            "level": "info",
            "text": "Armá el video con: .venv\\Scripts\\python.exe animar\\armar.py --frames \"<repo>\\app\\var\\media\\cache\\1c68639dc983\\frames\""
          },
          {
            "at": "2026-11-04T19:21:11+00:00",
            "level": "info",
            "text": "[3/3] armando la animacion"
          },
          {
            "at": "2026-11-04T19:21:11+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\animar\\armar.py --frames <repo>\\app\\var\\media\\cache\\1c68639dc983\\frames --fps 6 --formato mp4 --salida <repo>\\app\\var\\media\\cache\\1c68639dc983\\animacion.mp4"
          },
          {
            "at": "2026-11-04T19:21:11+00:00",
            "level": "info",
            "text": "12 cuadros en <repo>\\app\\var\\media\\cache\\1c68639dc983\\frames -> animacion_frames"
          },
          {
            "at": "2026-11-04T19:21:18+00:00",
            "level": "info",
            "text": "MP4: <repo>\\app\\var\\media\\cache\\1c68639dc983\\animacion.mp4 (5.50 MB)"
          },
          {
            "at": "2026-11-04T19:21:18+00:00",
            "level": "info",
            "text": "listo: 3 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "cuadro_001.webp",
            "url": "/media/e9d1c9f6004d/cuadro_001.webp",
            "kind": "image",
            "bytes": 438200
          },
          {
            "name": "cuadro_012.webp",
            "url": "/media/e9d1c9f6004d/cuadro_012.webp",
            "kind": "image",
            "bytes": 446626
          },
          {
            "name": "animacion.mp4",
            "url": "/media/e9d1c9f6004d/animacion.mp4",
            "kind": "video",
            "bytes": 997192
          }
        ],
        "plan": [],
        "error": null
      }
    },
    {
      "id": "2910edd68cef",
      "product_id": "geocolor",
      "params": {
        "snapshot": true,
        "paraguay": true,
        "margen": 10,
        "satelite": "G19",
        "ventana": {
          "start": "2026-11-03",
          "end": "2026-11-04"
        },
        "ultimos": false,
        "ultimos_n": "24",
        "hora": 21,
        "minuto": "00",
        "resolucion": "1400",
        "hora_desde": 0,
        "hora_hasta": 24,
        "animar": false,
        "fps": 8
      },
      "dates": [
        "2026-11-03",
        "2026-11-04"
      ],
      "snapshot": {
        "id": "2910edd68cef",
        "product_id": "geocolor",
        "product_name": "GOES - GeoColor (dia real, IR y luces)",
        "params": {
          "snapshot": true,
          "paraguay": true,
          "margen": 10,
          "satelite": "G19",
          "ventana": {
            "start": "2026-11-03",
            "end": "2026-11-04"
          },
          "ultimos": false,
          "ultimos_n": "24",
          "hora": 21,
          "minuto": "00",
          "resolucion": "1400",
          "hora_desde": 0,
          "hora_hasta": 24,
          "animar": false,
          "fps": 8
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-04T21:52:39+00:00",
        "started_at": "2026-11-04T21:52:39+00:00",
        "finished_at": "2026-11-04T21:52:45+00:00",
        "logs": [
          {
            "at": "2026-11-04T21:52:39+00:00",
            "level": "info",
            "text": "job 2910edd68cef | geocolor | modo=real"
          },
          {
            "at": "2026-11-04T21:52:39+00:00",
            "level": "info",
            "text": "[1/2] bajando GeoColor de G19 (1 cuadro(s))"
          },
          {
            "at": "2026-11-04T21:52:39+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\geocolor.py --sat G19 --bbox -63.4808 -28.4367 -53.4202 -18.4642 --desde 2026-11-04T21:00 --n 1 --paso 10 --px 1400 --out <repo>\\app\\var\\media\\cache\\5e119fd99e80"
          },
          {
            "at": "2026-11-04T21:52:40+00:00",
            "level": "info",
            "text": "GeoColor plano | G19 (GOES-East_ABI_GeoColor) | 1 cuadros desde 2026-11-04 21:00 UTC | paso 10 min | origen 1400x1388 px"
          },
          {
            "at": "2026-11-04T21:52:40+00:00",
            "level": "info",
            "text": "caja -63.4808,-28.4367,-53.4202,-18.4642 | frames en <repo>\\app\\var\\media\\cache\\5e119fd99e80\\frames_geocolor_plano_G19_2026-11-04T2100_1f_1400px"
          },
          {
            "at": "2026-11-04T21:52:43+00:00",
            "level": "info",
            "text": "  1/1 listos (errores 0) 3s"
          },
          {
            "at": "2026-11-04T21:52:43+00:00",
            "level": "info",
            "text": "1 cuadros listos en 3s"
          },
          {
            "at": "2026-11-04T21:52:43+00:00",
            "level": "info",
            "text": "Ahora renderizá con: .venv\\Scripts\\python.exe cuadros\\cuadros_geocolor.py --desde 2026-11-04T21:00 --n 1 --px 1400"
          },
          {
            "at": "2026-11-04T21:52:44+00:00",
            "level": "info",
            "text": "[2/2] renderizando 1 cuadro(s) de GeoColor"
          },
          {
            "at": "2026-11-04T21:52:44+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\cuadros\\cuadros_geocolor.py --sat G19 --bbox -63.4808 -28.4367 -53.4202 -18.4642 --desde 2026-11-04T21:00 --n 1 --paso 10 --px 1400 --out <repo>\\app\\var\\media\\cache\\5e119fd99e80 --geojson <repo>\\datos\\paraguay_gadm.json"
          },
          {
            "at": "2026-11-04T21:52:44+00:00",
            "level": "info",
            "text": "GeoColor plano | 1 cuadros desde 2026-11-04 21:00 UTC | salida 1400x1388 px | frames en <repo>\\app\\var\\media\\cache\\5e119fd99e80\\frames_geocolor_plano_G19_2026-11-04T2100_1f_1400px"
          },
          {
            "at": "2026-11-04T21:52:45+00:00",
            "level": "info",
            "text": "  1/1 listos (1s)"
          },
          {
            "at": "2026-11-04T21:52:45+00:00",
            "level": "info",
            "text": "1 cuadros en <repo>\\app\\var\\media\\cache\\5e119fd99e80\\frames_geocolor_plano_G19_2026-11-04T2100_1f_1400px"
          },
          {
            "at": "2026-11-04T21:52:45+00:00",
            "level": "info",
            "text": "Armá el video con: .venv\\Scripts\\python.exe animar\\armar.py --frames \"<repo>\\app\\var\\media\\cache\\5e119fd99e80\\frames_geocolor_plano_G19_2026-11-04T2100_1f_1400px\""
          },
          {
            "at": "2026-11-04T21:52:45+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "cuadro_001.webp",
            "url": "/media/2910edd68cef/cuadro_001.webp",
            "kind": "image",
            "bytes": 230364
          }
        ],
        "plan": [
          "bajando GeoColor de G19 (1 cuadro(s))",
          "renderizando 1 cuadro(s) de GeoColor"
        ],
        "error": null
      }
    },
    {
      "id": "8f11d2eae2af",
      "product_id": "goes_truecolor",
      "params": {
        "snapshot": true,
        "satelite": "G19",
        "encuadre": "globo",
        "limbo": "completo",
        "nitidez": "maxima",
        "ventana": {
          "start": "2026-11-03",
          "end": "2026-11-04"
        },
        "hora": 19,
        "minuto": "00",
        "resolucion": "1400",
        "hora_desde": 0,
        "hora_hasta": 24,
        "animar": false,
        "fps": 8
      },
      "dates": [
        "2026-11-03",
        "2026-11-04"
      ],
      "snapshot": {
        "id": "8f11d2eae2af",
        "product_id": "goes_truecolor",
        "product_name": "GOES - color real (3 bandas)",
        "params": {
          "snapshot": true,
          "satelite": "G19",
          "encuadre": "globo",
          "limbo": "completo",
          "nitidez": "maxima",
          "ventana": {
            "start": "2026-11-03",
            "end": "2026-11-04"
          },
          "hora": 19,
          "minuto": "00",
          "resolucion": "1400",
          "hora_desde": 0,
          "hora_hasta": 24,
          "animar": false,
          "fps": 8
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-04T19:23:54+00:00",
        "started_at": "2026-11-04T19:23:54+00:00",
        "finished_at": "2026-11-04T19:25:21+00:00",
        "logs": [
          {
            "at": "2026-11-04T19:23:54+00:00",
            "level": "info",
            "text": "job 8f11d2eae2af | goes_truecolor | modo=real"
          },
          {
            "at": "2026-11-04T19:23:54+00:00",
            "level": "info",
            "text": "[1/2] bajando C01+C02+C03 de G19 (1 slot(s))"
          },
          {
            "at": "2026-11-04T19:23:54+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\truecolor_goes.py --desde 2026-11-04T19:00 --n 1 --paso 10 --sat G19"
          },
          {
            "at": "2026-11-04T19:23:57+00:00",
            "level": "info",
            "text": "1 slot(s) desde 2026-11-04 19:00 UTC | paso 10 min"
          },
          {
            "at": "2026-11-04T19:23:57+00:00",
            "level": "info",
            "text": "bandas C01, C02, C03 | satélite G19 | destino <local> era5"
          },
          {
            "at": "2026-11-04T19:24:34+00:00",
            "level": "info",
            "text": "[1/1] 2026-11-04 19:00 UTC  C01 85 MB  C02 413 MB  C03 91 MB"
          },
          {
            "at": "2026-11-04T19:24:34+00:00",
            "level": "info",
            "text": "3 archivo(s) nuevos, 0.59 GB"
          },
          {
            "at": "2026-11-04T19:24:34+00:00",
            "level": "info",
            "text": "Ahora renderizá con:"
          },
          {
            "at": "2026-11-04T19:24:34+00:00",
            "level": "info",
            "text": "  .venv\\Scripts\\python.exe prototipos\\poster_goes_truecolor.py --desde 2026-11-04T19:00"
          },
          {
            "at": "2026-11-04T19:24:35+00:00",
            "level": "info",
            "text": "[2/2] poster color real 1400px"
          },
          {
            "at": "2026-11-04T19:24:35+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\prototipos\\poster_goes_truecolor.py --desde 2026-11-04T19:00 --sat G19 --px 1400 --fondo oscuro --no-lineas --no-fronteras --borde  --centro -75.2 0 --recorte 1.0 --no-mediana --suavizado 0 --out <repo>\\app\\var\\media\\cache\\d8fa7a21aea2\\truecolor_2026-11-04T1900.png"
          },
          {
            "at": "2026-11-04T19:24:37+00:00",
            "level": "info",
            "text": "OR_ABI-L2-CMIPF-M6C01_G19_s20263081900212_e20263081909520_c20263081909563.nc"
          },
          {
            "at": "2026-11-04T19:24:37+00:00",
            "level": "info",
            "text": "slot: 2026-11-04 19:00 UTC | globo 1400 px | centro (-75.2, 0.0) | saturaciÃ³n 1.1 | gamma 0.85"
          },
          {
            "at": "2026-11-04T19:24:38+00:00",
            "level": "info",
            "text": "  leyendo C01..."
          },
          {
            "at": "2026-11-04T19:24:46+00:00",
            "level": "info",
            "text": "  leyendo C02..."
          },
          {
            "at": "2026-11-04T19:25:06+00:00",
            "level": "info",
            "text": "  leyendo C03..."
          },
          {
            "at": "2026-11-04T19:25:13+00:00",
            "level": "info",
            "text": "  franja   256/1400"
          },
          {
            "at": "2026-11-04T19:25:14+00:00",
            "level": "info",
            "text": "  franja   512/1400"
          },
          {
            "at": "2026-11-04T19:25:14+00:00",
            "level": "info",
            "text": "  franja   768/1400"
          },
          {
            "at": "2026-11-04T19:25:15+00:00",
            "level": "info",
            "text": "  franja  1024/1400"
          },
          {
            "at": "2026-11-04T19:25:16+00:00",
            "level": "info",
            "text": "  franja  1280/1400"
          },
          {
            "at": "2026-11-04T19:25:16+00:00",
            "level": "info",
            "text": "  franja  1400/1400"
          },
          {
            "at": "2026-11-04T19:25:18+00:00",
            "level": "info",
            "text": "disco 1400 px | 1,537,076 px con dato"
          },
          {
            "at": "2026-11-04T19:25:19+00:00",
            "level": "info",
            "text": "PNG: <repo>\\app\\var\\media\\cache\\d8fa7a21aea2\\truecolor_2026-11-04T1900.png"
          },
          {
            "at": "2026-11-04T19:25:19+00:00",
            "level": "info",
            "text": "Serie de cuadros: .venv\\Scripts\\python.exe prototipos\\poster_goes_truecolor.py --frames \"<local> era5\\salidas\\frames_G19_truecolor\" --n 24"
          },
          {
            "at": "2026-11-04T19:25:21+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "truecolor_2026-11-04T1900.webp",
            "url": "/media/8f11d2eae2af/truecolor_2026-11-04T1900.webp",
            "kind": "image",
            "bytes": 396996
          }
        ],
        "plan": [],
        "error": null
      }
    },
    {
      "id": "44e8be56f11d",
      "product_id": "goes_dust",
      "params": {
        "snapshot": true,
        "satelite": "G19",
        "ventana": {
          "start": "2026-11-03",
          "end": "2026-11-04"
        },
        "ultimos": false,
        "ultimos_n": "24",
        "hora": 20,
        "minuto": "10",
        "resolucion": "2712",
        "hora_desde": 0,
        "hora_hasta": 24,
        "animar": false,
        "fps": 12
      },
      "dates": [
        "2026-11-03",
        "2026-11-04"
      ],
      "snapshot": {
        "id": "44e8be56f11d",
        "product_id": "goes_dust",
        "product_name": "GOES - Dust RGB",
        "params": {
          "snapshot": true,
          "satelite": "G19",
          "ventana": {
            "start": "2026-11-03",
            "end": "2026-11-04"
          },
          "ultimos": false,
          "ultimos_n": "24",
          "hora": 20,
          "minuto": "10",
          "resolucion": "2712",
          "hora_desde": 0,
          "hora_hasta": 24,
          "animar": false,
          "fps": 12
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-04T20:46:58+00:00",
        "started_at": "2026-11-04T20:46:58+00:00",
        "finished_at": "2026-11-04T20:47:48+00:00",
        "logs": [
          {
            "at": "2026-11-04T20:46:58+00:00",
            "level": "info",
            "text": "job 44e8be56f11d | goes_dust | modo=real"
          },
          {
            "at": "2026-11-04T20:46:58+00:00",
            "level": "info",
            "text": "[1/2] bajando dust de G19 (1 slot(s))"
          },
          {
            "at": "2026-11-04T20:46:58+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\descargar_goes_rgb.py --producto dust --sat G19 --desde 2026-11-04T20:10:00 --hasta 2026-11-04T20:20:00 --paso 10"
          },
          {
            "at": "2026-11-04T20:47:04+00:00",
            "level": "info",
            "text": "G19 dust: 1 slots (2026-11-04 20:10:00 -> 2026-11-04 20:10:00 UTC) · bandas C11, C13, C14, C15"
          },
          {
            "at": "2026-11-04T20:47:04+00:00",
            "level": "info",
            "text": "  C11: <local> era5\\goes_c11_g19"
          },
          {
            "at": "2026-11-04T20:47:04+00:00",
            "level": "info",
            "text": "  C13: <local> era5\\goes_c13_g19"
          },
          {
            "at": "2026-11-04T20:47:04+00:00",
            "level": "info",
            "text": "  C14: <local> era5\\goes_c14_g19"
          },
          {
            "at": "2026-11-04T20:47:04+00:00",
            "level": "info",
            "text": "  C15: <local> era5\\goes_c15_g19"
          },
          {
            "at": "2026-11-04T20:47:19+00:00",
            "level": "info",
            "text": "[1/1] 2026-11-04 20:10 UTC  descargados=4 existentes=0 errores=0  tiempo=16s"
          },
          {
            "at": "2026-11-04T20:47:19+00:00",
            "level": "info",
            "text": "Finalizado en 16s: descargados=4, existentes=0, errores=0"
          },
          {
            "at": "2026-11-04T20:47:20+00:00",
            "level": "info",
            "text": "[2/2] poster dust 2712px"
          },
          {
            "at": "2026-11-04T20:47:20+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\prototipos\\poster_goes_rgb.py --producto dust --sat G19 --desde 2026-11-04T20:10 --n 1 --paso 10 --px 2712 --centro -75.2 0 --recorte 1.0 --out <repo>\\app\\var\\media\\cache\\63d06b4cfae3\\G19_dust_2026-11-04T2010.png"
          },
          {
            "at": "2026-11-04T20:47:22+00:00",
            "level": "info",
            "text": "dust | slot 2026-11-04 20:10 UTC | globo 2712 px | centro (-75.2, 0.0)"
          },
          {
            "at": "2026-11-04T20:47:32+00:00",
            "level": "info",
            "text": "  franja   256/2712"
          },
          {
            "at": "2026-11-04T20:47:33+00:00",
            "level": "info",
            "text": "  franja   512/2712"
          },
          {
            "at": "2026-11-04T20:47:34+00:00",
            "level": "info",
            "text": "  franja   768/2712"
          },
          {
            "at": "2026-11-04T20:47:35+00:00",
            "level": "info",
            "text": "  franja  1024/2712"
          },
          {
            "at": "2026-11-04T20:47:35+00:00",
            "level": "info",
            "text": "  franja  1280/2712"
          },
          {
            "at": "2026-11-04T20:47:36+00:00",
            "level": "info",
            "text": "  franja  1536/2712"
          },
          {
            "at": "2026-11-04T20:47:37+00:00",
            "level": "info",
            "text": "  franja  1792/2712"
          },
          {
            "at": "2026-11-04T20:47:38+00:00",
            "level": "info",
            "text": "  franja  2048/2712"
          },
          {
            "at": "2026-11-04T20:47:38+00:00",
            "level": "info",
            "text": "  franja  2304/2712"
          },
          {
            "at": "2026-11-04T20:47:39+00:00",
            "level": "info",
            "text": "  franja  2560/2712"
          },
          {
            "at": "2026-11-04T20:47:40+00:00",
            "level": "info",
            "text": "  franja  2712/2712"
          },
          {
            "at": "2026-11-04T20:47:40+00:00",
            "level": "info",
            "text": "disco 2712 px | 5,772,176 px con dato"
          },
          {
            "at": "2026-11-04T20:47:48+00:00",
            "level": "info",
            "text": "PNG: <repo>\\app\\var\\media\\cache\\63d06b4cfae3\\G19_dust_2026-11-04T2010.png"
          },
          {
            "at": "2026-11-04T20:47:48+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "G19_dust_2026-11-04T2010.webp",
            "url": "/media/44e8be56f11d/G19_dust_2026-11-04T2010.webp",
            "kind": "image",
            "bytes": 352864
          }
        ],
        "plan": [],
        "error": null
      }
    },
    {
      "id": "0901921feae3",
      "product_id": "goes_airmass",
      "params": {
        "snapshot": true,
        "satelite": "G19",
        "ventana": {
          "start": "2026-11-04",
          "end": "2026-11-04"
        },
        "ultimos": false,
        "ultimos_n": "24",
        "hora": 19,
        "minuto": "20",
        "resolucion": "2712",
        "hora_desde": 0,
        "hora_hasta": 24,
        "animar": false,
        "fps": 12
      },
      "dates": [
        "2026-11-04"
      ],
      "snapshot": {
        "id": "0901921feae3",
        "product_id": "goes_airmass",
        "product_name": "GOES - Air Mass RGB",
        "params": {
          "snapshot": true,
          "satelite": "G19",
          "ventana": {
            "start": "2026-11-04",
            "end": "2026-11-04"
          },
          "ultimos": false,
          "ultimos_n": "24",
          "hora": 19,
          "minuto": "20",
          "resolucion": "2712",
          "hora_desde": 0,
          "hora_hasta": 24,
          "animar": false,
          "fps": 12
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-04T20:48:29+00:00",
        "started_at": "2026-11-04T20:48:29+00:00",
        "finished_at": "2026-11-04T20:49:10+00:00",
        "logs": [
          {
            "at": "2026-11-04T20:48:29+00:00",
            "level": "info",
            "text": "job 0901921feae3 | goes_airmass | modo=real"
          },
          {
            "at": "2026-11-04T20:48:29+00:00",
            "level": "info",
            "text": "[1/2] bajando airmass de G19 (1 slot(s))"
          },
          {
            "at": "2026-11-04T20:48:29+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\descargar_goes_rgb.py --producto airmass --sat G19 --desde 2026-11-04T19:20:00 --hasta 2026-11-04T19:30:00 --paso 10"
          },
          {
            "at": "2026-11-04T20:48:32+00:00",
            "level": "info",
            "text": "G19 airmass: 1 slots (2026-11-04 19:20:00 -> 2026-11-04 19:20:00 UTC) · bandas C08, C10, C12, C13"
          },
          {
            "at": "2026-11-04T20:48:32+00:00",
            "level": "info",
            "text": "  C08: <local> era5\\goes_c08_g19"
          },
          {
            "at": "2026-11-04T20:48:32+00:00",
            "level": "info",
            "text": "  C10: <local> era5\\goes_c10_g19"
          },
          {
            "at": "2026-11-04T20:48:32+00:00",
            "level": "info",
            "text": "  C12: <local> era5\\goes_c12_g19"
          },
          {
            "at": "2026-11-04T20:48:32+00:00",
            "level": "info",
            "text": "  C13: <local> era5\\goes_c13_g19"
          },
          {
            "at": "2026-11-04T20:48:42+00:00",
            "level": "info",
            "text": "[1/1] 2026-11-04 19:20 UTC  descargados=3 existentes=1 errores=0  tiempo=10s"
          },
          {
            "at": "2026-11-04T20:48:42+00:00",
            "level": "info",
            "text": "Finalizado en 10s: descargados=3, existentes=1, errores=0"
          },
          {
            "at": "2026-11-04T20:48:42+00:00",
            "level": "info",
            "text": "[2/2] poster airmass 2712px"
          },
          {
            "at": "2026-11-04T20:48:42+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\prototipos\\poster_goes_rgb.py --producto airmass --sat G19 --desde 2026-11-04T19:20 --n 1 --paso 10 --px 2712 --centro -75.2 0 --recorte 1.0 --out <repo>\\app\\var\\media\\cache\\146799ea59cf\\G19_airmass_2026-11-04T1920.png"
          },
          {
            "at": "2026-11-04T20:48:45+00:00",
            "level": "info",
            "text": "airmass | slot 2026-11-04 19:20 UTC | globo 2712 px | centro (-75.2, 0.0)"
          },
          {
            "at": "2026-11-04T20:48:50+00:00",
            "level": "info",
            "text": "  franja   256/2712"
          },
          {
            "at": "2026-11-04T20:48:51+00:00",
            "level": "info",
            "text": "  franja   512/2712"
          },
          {
            "at": "2026-11-04T20:48:52+00:00",
            "level": "info",
            "text": "  franja   768/2712"
          },
          {
            "at": "2026-11-04T20:48:53+00:00",
            "level": "info",
            "text": "  franja  1024/2712"
          },
          {
            "at": "2026-11-04T20:48:53+00:00",
            "level": "info",
            "text": "  franja  1280/2712"
          },
          {
            "at": "2026-11-04T20:48:54+00:00",
            "level": "info",
            "text": "  franja  1536/2712"
          },
          {
            "at": "2026-11-04T20:48:55+00:00",
            "level": "info",
            "text": "  franja  1792/2712"
          },
          {
            "at": "2026-11-04T20:48:56+00:00",
            "level": "info",
            "text": "  franja  2048/2712"
          },
          {
            "at": "2026-11-04T20:48:58+00:00",
            "level": "info",
            "text": "  franja  2304/2712"
          },
          {
            "at": "2026-11-04T20:48:59+00:00",
            "level": "info",
            "text": "  franja  2560/2712"
          },
          {
            "at": "2026-11-04T20:48:59+00:00",
            "level": "info",
            "text": "  franja  2712/2712"
          },
          {
            "at": "2026-11-04T20:48:59+00:00",
            "level": "info",
            "text": "disco 2712 px | 5,772,176 px con dato"
          },
          {
            "at": "2026-11-04T20:49:10+00:00",
            "level": "info",
            "text": "PNG: <repo>\\app\\var\\media\\cache\\146799ea59cf\\G19_airmass_2026-11-04T1920.png"
          },
          {
            "at": "2026-11-04T20:49:10+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "G19_airmass_2026-11-04T1920.webp",
            "url": "/media/0901921feae3/G19_airmass_2026-11-04T1920.webp",
            "kind": "image",
            "bytes": 251160
          }
        ],
        "plan": [],
        "error": null
      }
    },
    {
      "id": "a9c4c8630e1b",
      "product_id": "goes_firetemp",
      "params": {
        "snapshot": true,
        "satelite": "G19",
        "ventana": {
          "start": "2026-11-04",
          "end": "2026-11-04"
        },
        "ultimos": false,
        "ultimos_n": "24",
        "hora": 19,
        "minuto": "00",
        "resolucion": "2712",
        "hora_desde": 0,
        "hora_hasta": 24,
        "animar": false,
        "fps": 12
      },
      "dates": [
        "2026-11-04"
      ],
      "snapshot": {
        "id": "a9c4c8630e1b",
        "product_id": "goes_firetemp",
        "product_name": "GOES - Fire Temperature RGB",
        "params": {
          "snapshot": true,
          "satelite": "G19",
          "ventana": {
            "start": "2026-11-04",
            "end": "2026-11-04"
          },
          "ultimos": false,
          "ultimos_n": "24",
          "hora": 19,
          "minuto": "00",
          "resolucion": "2712",
          "hora_desde": 0,
          "hora_hasta": 24,
          "animar": false,
          "fps": 12
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-04T20:49:51+00:00",
        "started_at": "2026-11-04T20:49:51+00:00",
        "finished_at": "2026-11-04T20:50:38+00:00",
        "logs": [
          {
            "at": "2026-11-04T20:49:51+00:00",
            "level": "info",
            "text": "job a9c4c8630e1b | goes_firetemp | modo=real"
          },
          {
            "at": "2026-11-04T20:49:51+00:00",
            "level": "info",
            "text": "[1/2] bajando firetemp de G19 (1 slot(s))"
          },
          {
            "at": "2026-11-04T20:49:51+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\descargar_goes_rgb.py --producto firetemp --sat G19 --desde 2026-11-04T19:00:00 --hasta 2026-11-04T19:10:00 --paso 10"
          },
          {
            "at": "2026-11-04T20:49:54+00:00",
            "level": "info",
            "text": "G19 firetemp: 1 slots (2026-11-04 19:00:00 -> 2026-11-04 19:00:00 UTC) · bandas C05, C06, C07"
          },
          {
            "at": "2026-11-04T20:49:54+00:00",
            "level": "info",
            "text": "  C05: <local> era5\\goes_c05_g19"
          },
          {
            "at": "2026-11-04T20:49:54+00:00",
            "level": "info",
            "text": "  C06: <local> era5\\goes_c06_g19"
          },
          {
            "at": "2026-11-04T20:49:54+00:00",
            "level": "info",
            "text": "  C07: <local> era5\\goes_c07_g19"
          },
          {
            "at": "2026-11-04T20:50:08+00:00",
            "level": "info",
            "text": "[1/1] 2026-11-04 19:00 UTC  descargados=3 existentes=0 errores=0  tiempo=15s"
          },
          {
            "at": "2026-11-04T20:50:08+00:00",
            "level": "info",
            "text": "Finalizado en 15s: descargados=3, existentes=0, errores=0"
          },
          {
            "at": "2026-11-04T20:50:09+00:00",
            "level": "info",
            "text": "[2/2] poster firetemp 2712px"
          },
          {
            "at": "2026-11-04T20:50:09+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\prototipos\\poster_goes_rgb.py --producto firetemp --sat G19 --desde 2026-11-04T19:00 --n 1 --paso 10 --px 2712 --centro -75.2 0 --recorte 1.0 --out <repo>\\app\\var\\media\\cache\\298727bb5a29\\G19_firetemp_2026-11-04T1900.png"
          },
          {
            "at": "2026-11-04T20:50:11+00:00",
            "level": "info",
            "text": "firetemp | slot 2026-11-04 19:00 UTC | globo 2712 px | centro (-75.2, 0.0)"
          },
          {
            "at": "2026-11-04T20:50:20+00:00",
            "level": "info",
            "text": "  franja   256/2712"
          },
          {
            "at": "2026-11-04T20:50:21+00:00",
            "level": "info",
            "text": "  franja   512/2712"
          },
          {
            "at": "2026-11-04T20:50:22+00:00",
            "level": "info",
            "text": "  franja   768/2712"
          },
          {
            "at": "2026-11-04T20:50:23+00:00",
            "level": "info",
            "text": "  franja  1024/2712"
          },
          {
            "at": "2026-11-04T20:50:24+00:00",
            "level": "info",
            "text": "  franja  1280/2712"
          },
          {
            "at": "2026-11-04T20:50:24+00:00",
            "level": "info",
            "text": "  franja  1536/2712"
          },
          {
            "at": "2026-11-04T20:50:25+00:00",
            "level": "info",
            "text": "  franja  1792/2712"
          },
          {
            "at": "2026-11-04T20:50:26+00:00",
            "level": "info",
            "text": "  franja  2048/2712"
          },
          {
            "at": "2026-11-04T20:50:26+00:00",
            "level": "info",
            "text": "  franja  2304/2712"
          },
          {
            "at": "2026-11-04T20:50:27+00:00",
            "level": "info",
            "text": "  franja  2560/2712"
          },
          {
            "at": "2026-11-04T20:50:28+00:00",
            "level": "info",
            "text": "  franja  2712/2712"
          },
          {
            "at": "2026-11-04T20:50:28+00:00",
            "level": "info",
            "text": "disco 2712 px | 5,772,176 px con dato"
          },
          {
            "at": "2026-11-04T20:50:37+00:00",
            "level": "info",
            "text": "PNG: <repo>\\app\\var\\media\\cache\\298727bb5a29\\G19_firetemp_2026-11-04T1900.png"
          },
          {
            "at": "2026-11-04T20:50:38+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "G19_firetemp_2026-11-04T1900.webp",
            "url": "/media/a9c4c8630e1b/G19_firetemp_2026-11-04T1900.webp",
            "kind": "image",
            "bytes": 178184
          }
        ],
        "plan": [
          "bajando firetemp de G19 (1 slot(s))",
          "poster firetemp 2712px"
        ],
        "error": null
      }
    },
    {
      "id": "c343e709328f",
      "product_id": "goes_sandwich",
      "params": {
        "snapshot": true,
        "paraguay": false,
        "margen": 6,
        "satelite": "G19",
        "alpha": 0.5,
        "ventana": {
          "start": "2026-11-07",
          "end": "2026-11-08"
        },
        "ultimos": false,
        "ultimos_n": "24",
        "hora": 15,
        "minuto": "00",
        "resolucion": "2712",
        "hora_desde": 0,
        "hora_hasta": 24,
        "animar": false,
        "fps": 8
      },
      "dates": [
        "2026-11-07",
        "2026-11-08"
      ],
      "snapshot": {
        "id": "c343e709328f",
        "product_id": "goes_sandwich",
        "product_name": "GOES - Sandwich (visible + IR realzado)",
        "params": {
          "snapshot": true,
          "paraguay": false,
          "margen": 6,
          "satelite": "G19",
          "alpha": 0.5,
          "ventana": {
            "start": "2026-11-07",
            "end": "2026-11-08"
          },
          "ultimos": false,
          "ultimos_n": "24",
          "hora": 15,
          "minuto": "00",
          "resolucion": "2712",
          "hora_desde": 0,
          "hora_hasta": 24,
          "animar": false,
          "fps": 8
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-08T18:04:10+00:00",
        "started_at": "2026-11-08T18:04:10+00:00",
        "finished_at": "2026-11-08T18:04:46+00:00",
        "logs": [
          {
            "at": "2026-11-08T18:04:10+00:00",
            "level": "info",
            "text": "job c343e709328f | goes_sandwich | modo=real"
          },
          {
            "at": "2026-11-08T18:04:10+00:00",
            "level": "info",
            "text": "[1/3] bajando C02 de G19 (1 slot(s))"
          },
          {
            "at": "2026-11-08T18:04:10+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\descargar_goes.py --sat G19 --banda C02 --desde 2026-11-08T15:00:00 --hasta 2026-11-08T15:10:00 --paso 10"
          },
          {
            "at": "2026-11-08T18:04:15+00:00",
            "level": "info",
            "text": "G19 C02: 1 slots (2026-11-08 15:00:00 -> 2026-11-08 15:10:00 UTC) · rango pedido"
          },
          {
            "at": "2026-11-08T18:04:15+00:00",
            "level": "info",
            "text": "Destino: <local> era5\\goes_c02_g19"
          },
          {
            "at": "2026-11-08T18:04:15+00:00",
            "level": "info",
            "text": "[1/1] 2026-11-08 15:00 UTC  descargados=0 existentes=1 errores=0  tiempo=1s"
          },
          {
            "at": "2026-11-08T18:04:15+00:00",
            "level": "info",
            "text": "Finalizado en 1s: descargados=0, existentes=1, errores=0"
          },
          {
            "at": "2026-11-08T18:04:16+00:00",
            "level": "info",
            "text": "[2/3] bajando C13 de G19 (1 slot(s))"
          },
          {
            "at": "2026-11-08T18:04:16+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\descargar_goes.py --sat G19 --banda C13 --desde 2026-11-08T15:00:00 --hasta 2026-11-08T15:10:00 --paso 10"
          },
          {
            "at": "2026-11-08T18:04:18+00:00",
            "level": "info",
            "text": "G19 C13: 1 slots (2026-11-08 15:00:00 -> 2026-11-08 15:10:00 UTC) · rango pedido"
          },
          {
            "at": "2026-11-08T18:04:18+00:00",
            "level": "info",
            "text": "Destino: <local> era5\\goes_c13_g19"
          },
          {
            "at": "2026-11-08T18:04:19+00:00",
            "level": "info",
            "text": "[1/1] 2026-11-08 15:00 UTC  descargados=0 existentes=1 errores=0  tiempo=1s"
          },
          {
            "at": "2026-11-08T18:04:19+00:00",
            "level": "info",
            "text": "Finalizado en 1s: descargados=0, existentes=1, errores=0"
          },
          {
            "at": "2026-11-08T18:04:19+00:00",
            "level": "info",
            "text": "[3/3] poster Sandwich 2712px"
          },
          {
            "at": "2026-11-08T18:04:19+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\prototipos\\poster_goes_sandwich.py --sat G19 --desde 2026-11-08T15:00 --n 1 --paso 10 --px 2712 --alpha 0.5 --sombra-borde 0 --centro -75.2 0 --recorte 1.0 --borde  --out <repo>\\app\\var\\media\\cache\\1068c325336e\\G19_Sandwich_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T18:04:21+00:00",
            "level": "info",
            "text": "OR_ABI-L2-CMIPF-M6C02_G19_s20263121500218_e20263121509526_c20263121509583.nc + OR_ABI-L2-CMIPF-M6C13_G19_s20263121500218_e20263121509538_c20263121510014.nc"
          },
          {
            "at": "2026-11-08T18:04:21+00:00",
            "level": "info",
            "text": "slot: 2026-11-08 15:00 UTC | globo 2712 px | alpha 0.5"
          },
          {
            "at": "2026-11-08T18:04:32+00:00",
            "level": "info",
            "text": "  franja   256/2712"
          },
          {
            "at": "2026-11-08T18:04:33+00:00",
            "level": "info",
            "text": "  franja   512/2712"
          },
          {
            "at": "2026-11-08T18:04:33+00:00",
            "level": "info",
            "text": "  franja   768/2712"
          },
          {
            "at": "2026-11-08T18:04:34+00:00",
            "level": "info",
            "text": "  franja  1024/2712"
          },
          {
            "at": "2026-11-08T18:04:35+00:00",
            "level": "info",
            "text": "  franja  1280/2712"
          },
          {
            "at": "2026-11-08T18:04:35+00:00",
            "level": "info",
            "text": "  franja  1536/2712"
          },
          {
            "at": "2026-11-08T18:04:36+00:00",
            "level": "info",
            "text": "  franja  1792/2712"
          },
          {
            "at": "2026-11-08T18:04:36+00:00",
            "level": "info",
            "text": "  franja  2048/2712"
          },
          {
            "at": "2026-11-08T18:04:37+00:00",
            "level": "info",
            "text": "  franja  2304/2712"
          },
          {
            "at": "2026-11-08T18:04:38+00:00",
            "level": "info",
            "text": "  franja  2560/2712"
          },
          {
            "at": "2026-11-08T18:04:38+00:00",
            "level": "info",
            "text": "  franja  2712/2712"
          },
          {
            "at": "2026-11-08T18:04:38+00:00",
            "level": "info",
            "text": "disco 2712 px | 5,543,676 px con dato"
          },
          {
            "at": "2026-11-08T18:04:45+00:00",
            "level": "info",
            "text": "PNG: <repo>\\app\\var\\media\\cache\\1068c325336e\\G19_Sandwich_2026-11-08T1500.png"
          },
          {
            "at": "2026-11-08T18:04:46+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "G19_Sandwich_2026-11-08T1500.webp",
            "url": "/media/c343e709328f/G19_Sandwich_2026-11-08T1500.webp",
            "kind": "image",
            "bytes": 280828
          }
        ],
        "plan": [
          "bajando C02 de G19 (1 slot(s))",
          "bajando C13 de G19 (1 slot(s))",
          "poster Sandwich 2712px"
        ],
        "error": null
      }
    },
    {
      "id": "8183969cab6e",
      "product_id": "snapshot_paraguay",
      "params": {
        "capa": "geocolor",
        "ultima": true,
        "fecha": "2026-11-04",
        "hora": 15,
        "minuto": "00",
        "margen": 0,
        "detalle": "250",
        "borde": false
      },
      "dates": [
        "2026-11-04"
      ],
      "snapshot": {
        "id": "8183969cab6e",
        "product_id": "snapshot_paraguay",
        "product_name": "Snapshot - Paraguay",
        "params": {
          "capa": "geocolor",
          "ultima": true,
          "fecha": "2026-11-04",
          "hora": 15,
          "minuto": "00",
          "margen": 0,
          "detalle": "250",
          "borde": false
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-04T20:57:13+00:00",
        "started_at": "2026-11-04T20:57:13+00:00",
        "finished_at": "2026-11-04T20:57:29+00:00",
        "logs": [
          {
            "at": "2026-11-04T20:57:13+00:00",
            "level": "info",
            "text": "job 8183969cab6e | snapshot_paraguay | modo=real"
          },
          {
            "at": "2026-11-04T20:57:13+00:00",
            "level": "info",
            "text": "[1/2] bajando la captura de GIBS"
          },
          {
            "at": "2026-11-04T20:57:13+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\snapshot_paraguay.py --capa geocolor --fecha 2026-11-04 --hora 15 --minuto 0 --mpp 250 --margen 0 --ultima --out <repo>\\app\\var\\media\\cache\\86214db86a85\\crudos"
          },
          {
            "at": "2026-11-04T20:57:14+00:00",
            "level": "info",
            "text": "  aviso: geocolor tiene ~700 m/px: pedir 250 m/px sólo interpola (el archivo pesa más y no agrega detalle)"
          },
          {
            "at": "2026-11-04T20:57:14+00:00",
            "level": "info",
            "text": "Buscando la última captura de geocolor disponible..."
          },
          {
            "at": "2026-11-04T20:57:15+00:00",
            "level": "info",
            "text": "    2026-11-04 20:50 sin gránulo, pruebo 0:10:00 antes"
          },
          {
            "at": "2026-11-04T20:57:16+00:00",
            "level": "info",
            "text": "    2026-11-04 20:40 sin gránulo, pruebo 0:10:00 antes"
          },
          {
            "at": "2026-11-04T20:57:18+00:00",
            "level": "info",
            "text": "    2026-11-04 20:30 sin gránulo, pruebo 0:10:00 antes"
          },
          {
            "at": "2026-11-04T20:57:19+00:00",
            "level": "info",
            "text": "    2026-11-04 20:20 sin gránulo, pruebo 0:10:00 antes"
          },
          {
            "at": "2026-11-04T20:57:21+00:00",
            "level": "info",
            "text": "    2026-11-04 20:10 sin gránulo, pruebo 0:10:00 antes"
          },
          {
            "at": "2026-11-04T20:57:23+00:00",
            "level": "info",
            "text": "última disponible: 2026-11-04 20:00 UTC"
          },
          {
            "at": "2026-11-04T20:57:23+00:00",
            "level": "info",
            "text": "Snapshot geocolor 2026-11-04 20:00 UTC | 3733x3733 px"
          },
          {
            "at": "2026-11-04T20:57:23+00:00",
            "level": "info",
            "text": "caja (desde el GeoJSON + margen 0): -62.64,-27.61 .. -54.26,-19.30"
          },
          {
            "at": "2026-11-04T20:57:23+00:00",
            "level": "info",
            "text": "fuente: https://wvs.earthdata.nasa.gov/api/v1/snapshot?REQUEST=GetSnapshot&TIME=2026-11-04T20:00:00Z&BBOX=-27.6057,-62.6424,-19.2952,-54.2586&CRS=EPSG:4326&LAYERS=GOES-East_ABI_GeoColor&FORMAT=image/png&WIDTH=3733&HEIGHT=3733"
          },
          {
            "at": "2026-11-04T20:57:28+00:00",
            "level": "info",
            "text": "listo: <repo>\\app\\var\\media\\cache\\86214db86a85\\crudos\\crudo_snapshot_geocolor_20261104T2000_3733px.png (3036 KB, 5.2s)"
          },
          {
            "at": "2026-11-04T20:57:28+00:00",
            "level": "info",
            "text": "Ahora componé con: .venv\\Scripts\\python.exe cuadros\\snapshot_paraguay.py --crudo \"<repo>\\app\\var\\media\\cache\\86214db86a85\\crudos\\crudo_snapshot_geocolor_20261104T2000_3733px.png\""
          },
          {
            "at": "2026-11-04T20:57:28+00:00",
            "level": "info",
            "text": "[2/2] componiendo la captura"
          },
          {
            "at": "2026-11-04T20:57:28+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\cuadros\\snapshot_paraguay.py --capa geocolor --fecha 2026-11-04 --hora 15 --minuto 0 --mpp 250 --margen 0 --ultima --entrada <repo>\\app\\var\\media\\cache\\86214db86a85\\crudos --salidas <repo>\\app\\var\\media\\cache\\86214db86a85 --sin-borde"
          },
          {
            "at": "2026-11-04T20:57:29+00:00",
            "level": "info",
            "text": "Captura: <repo>\\app\\var\\media\\cache\\86214db86a85\\snapshot_paraguay_geocolor_2026-11-04T2000_3733px.png (3733x3733 px, 2340 KB)"
          },
          {
            "at": "2026-11-04T20:57:29+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "snapshot_paraguay_geocolor_2026-11-04T2000_3733px.webp",
            "url": "/media/8183969cab6e/snapshot_paraguay_geocolor_2026-11-04T2000_3733px.webp",
            "kind": "image",
            "bytes": 255526
          }
        ],
        "plan": [
          "bajando la captura de GIBS",
          "componiendo la captura"
        ],
        "error": null
      }
    },
    {
      "id": "f768b4541c9e",
      "product_id": "anomalia_2t",
      "params": {
        "snapshot": true,
        "paraguay": true,
        "margen": 6,
        "modelo": "ifs",
        "fecha": "2026-11-05",
        "corrida": "00",
        "horizonte": 12,
        "fondo": "claro",
        "resolucion": "1400",
        "animar": false,
        "fps": 12
      },
      "dates": [
        "2026-11-05"
      ],
      "snapshot": {
        "id": "f768b4541c9e",
        "product_id": "anomalia_2t",
        "product_name": "ECMWF - anomalia de 2 m",
        "params": {
          "snapshot": true,
          "paraguay": true,
          "margen": 6,
          "modelo": "ifs",
          "fecha": "2026-11-05",
          "corrida": "00",
          "horizonte": 12,
          "fondo": "claro",
          "resolucion": "1400",
          "animar": false,
          "fps": 12
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-05T22:41:47+00:00",
        "started_at": "2026-11-05T22:41:47+00:00",
        "finished_at": "2026-11-05T22:42:00+00:00",
        "logs": [
          {
            "at": "2026-11-05T22:41:47+00:00",
            "level": "info",
            "text": "job f768b4541c9e | anomalia_2t | modo=real"
          },
          {
            "at": "2026-11-05T22:41:49+00:00",
            "level": "info",
            "text": "[1/2] bajando anomalia_2t de ifs"
          },
          {
            "at": "2026-11-05T22:41:49+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\anomalia_2t_ecmwf.py --modelo ifs --fecha 2026-11-05 --ciclo 00 --hasta-hora 12 --paso 12"
          },
          {
            "at": "2026-11-05T22:41:53+00:00",
            "level": "info",
            "text": "Climatología en caché: <local> era5\\climatologia_era5_t2m_mes_hora.npz (12 meses x 4 horas)"
          },
          {
            "at": "2026-11-05T22:41:53+00:00",
            "level": "info",
            "text": "Temperatura a 2 m IFS | 2026-11-05 00z | 2 pasos (0h..12h cada 12 h)"
          },
          {
            "at": "2026-11-05T22:41:53+00:00",
            "level": "info",
            "text": "fuente: https://data.ecmwf.int/forecasts/20261105/00z/ifs/0p25/oper/20261105000000-0h-oper-fc.index"
          },
          {
            "at": "2026-11-05T22:41:53+00:00",
            "level": "info",
            "text": "crudos en <local> era5\\crudos_anom2t_ifs_2026-11-05_00z | 8 hilos"
          },
          {
            "at": "2026-11-05T22:41:55+00:00",
            "level": "info",
            "text": "  1/2 pasos listos (1 reutilizados, errores 0) 2s"
          },
          {
            "at": "2026-11-05T22:41:55+00:00",
            "level": "info",
            "text": "  2/2 pasos listos (1 reutilizados, errores 0) 3s"
          },
          {
            "at": "2026-11-05T22:41:55+00:00",
            "level": "info",
            "text": "2 pasos listos en 3s (1 reutilizados). Calculando anomalías..."
          },
          {
            "at": "2026-11-05T22:41:56+00:00",
            "level": "info",
            "text": "  2/2 pasos consolidados (1s)"
          },
          {
            "at": "2026-11-05T22:41:56+00:00",
            "level": "info",
            "text": "Anomalía de temperatura a 2 m (°C):"
          },
          {
            "at": "2026-11-05T22:41:56+00:00",
            "level": "info",
            "text": "  paso   mín global   máx global   mín Sudamérica   máx Sudamérica"
          },
          {
            "at": "2026-11-05T22:41:56+00:00",
            "level": "info",
            "text": "    0 h     -26.2        +15.0         -9.0            +9.2"
          },
          {
            "at": "2026-11-05T22:41:56+00:00",
            "level": "info",
            "text": "   12 h     -22.8        +16.2         -7.9            +7.4"
          },
          {
            "at": "2026-11-05T22:41:56+00:00",
            "level": "info",
            "text": "FH 12h: Sudamérica (lon -65..-45, lat -32..-18) -7.9 °C a +7.4 °C"
          },
          {
            "at": "2026-11-05T22:41:56+00:00",
            "level": "info",
            "text": "Serie consolidada: <local> era5\\crudos_anom2t_ifs_2026-11-05_00z\\serie_anom_2t_c.npz (2, 721, 1440) float32 | horas 0..12 cada 12 h"
          },
          {
            "at": "2026-11-05T22:41:56+00:00",
            "level": "info",
            "text": "Ahora renderizá con: .venv\\Scripts\\python.exe cuadros\\cuadros_anomalia_2t.py --fecha 2026-11-05 --ciclo 00 --hasta-hora 12 --paso 12"
          },
          {
            "at": "2026-11-05T22:41:56+00:00",
            "level": "info",
            "text": "[2/2] renderizando 2 cuadros"
          },
          {
            "at": "2026-11-05T22:41:56+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\cuadros\\cuadros_anomalia_2t.py --modelo ifs --fecha 2026-11-05 --ciclo 00 --hasta-hora 12 --paso 12 --px 1400 --fondo-globo claro --centro -58.4505 -23.4505 --radio 4.69493 --limpio --salidas <repo>\\app\\var\\media\\cache\\b4bce5063c8f --solo-poster"
          },
          {
            "at": "2026-11-05T22:41:56+00:00",
            "level": "info",
            "text": "Datos: <local> era5\\crudos_anom2t_ifs_2026-11-05_00z\\serie_anom_2t_c.npz | 2 pasos | rejilla 1440x721"
          },
          {
            "at": "2026-11-05T22:42:00+00:00",
            "level": "info",
            "text": "Póster FH +12h: <repo>\\app\\var\\media\\cache\\b4bce5063c8f\\poster_anom2t_ifs_2026-11-05_00z_fh012.png (1400x1400 px, 3.5s)"
          },
          {
            "at": "2026-11-05T22:42:00+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "poster_anom2t_ifs_2026-11-05_00z_fh012.webp",
            "url": "/media/f768b4541c9e/poster_anom2t_ifs_2026-11-05_00z_fh012.webp",
            "kind": "image",
            "bytes": 76954
          }
        ],
        "plan": [
          "bajando anomalia_2t de ifs",
          "renderizando 2 cuadros"
        ],
        "error": null
      }
    },
    {
      "id": "45ebff35d312",
      "product_id": "viento_250",
      "params": {
        "snapshot": true,
        "paraguay": true,
        "margen": 6,
        "modelo": "gfs",
        "fecha": "2026-11-04",
        "corrida": "00",
        "horizonte": 144,
        "fondo": "oscuro",
        "resolucion": "1400",
        "animar": false,
        "fps": 12
      },
      "dates": [
        "2026-11-04"
      ],
      "snapshot": {
        "id": "45ebff35d312",
        "product_id": "viento_250",
        "product_name": "Viento en 250 mb",
        "params": {
          "snapshot": true,
          "paraguay": true,
          "margen": 6,
          "modelo": "gfs",
          "fecha": "2026-11-04",
          "corrida": "00",
          "horizonte": 144,
          "fondo": "oscuro",
          "resolucion": "1400",
          "animar": false,
          "fps": 12
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-05T22:42:02+00:00",
        "started_at": "2026-11-05T22:42:02+00:00",
        "finished_at": "2026-11-05T22:42:18+00:00",
        "logs": [
          {
            "at": "2026-11-05T22:42:02+00:00",
            "level": "info",
            "text": "job 45ebff35d312 | viento_250 | modo=real"
          },
          {
            "at": "2026-11-05T22:42:03+00:00",
            "level": "info",
            "text": "[1/2] bajando el viento en 250 mb de gfs"
          },
          {
            "at": "2026-11-05T22:42:03+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\viento_250_mslp.py --modelo gfs --fecha 2026-11-04 --ciclo 00 --hasta-hora 144 --paso 144"
          },
          {
            "at": "2026-11-05T22:42:05+00:00",
            "level": "info",
            "text": "Viento 250 mb + MSLP GFS 0.25° | 2026-11-04 00z | 2 pasos (0h..144h cada 144 h)"
          },
          {
            "at": "2026-11-05T22:42:05+00:00",
            "level": "info",
            "text": "fuente: https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.20261104/00/atmos/gfs.t00z.pgrb2.0p25.f000.idx"
          },
          {
            "at": "2026-11-05T22:42:05+00:00",
            "level": "info",
            "text": "crudos en <local> era5\\crudos_viento250_gfs_2026-11-04_00z | 8 hilos"
          },
          {
            "at": "2026-11-05T22:42:06+00:00",
            "level": "info",
            "text": "  1/2 pasos listos (3 reutilizados, errores 0) 1s"
          },
          {
            "at": "2026-11-05T22:42:08+00:00",
            "level": "info",
            "text": "  2/2 pasos listos (3 reutilizados, errores 0) 3s"
          },
          {
            "at": "2026-11-05T22:42:08+00:00",
            "level": "info",
            "text": "2 pasos listos en 3s (3 reutilizados). Consolidando..."
          },
          {
            "at": "2026-11-05T22:42:08+00:00",
            "level": "info",
            "text": "  2/2 pasos consolidados (1s)"
          },
          {
            "at": "2026-11-05T22:42:08+00:00",
            "level": "info",
            "text": "Viento en 250 mb (kt) y MSLP (hPa):"
          },
          {
            "at": "2026-11-05T22:42:08+00:00",
            "level": "info",
            "text": "  paso   máx global   máx Sudamérica   MSLP mín/máx global"
          },
          {
            "at": "2026-11-05T22:42:08+00:00",
            "level": "info",
            "text": "    0 h      169.9         152.9        954.3 /  1058.2"
          },
          {
            "at": "2026-11-05T22:42:08+00:00",
            "level": "info",
            "text": "  144 h      196.2         122.2        949.5 /  1061.9"
          },
          {
            "at": "2026-11-05T22:42:08+00:00",
            "level": "info",
            "text": "FH 144h: máx global 196.2 kt en lat 45.00, lon 162.75"
          },
          {
            "at": "2026-11-05T22:42:08+00:00",
            "level": "info",
            "text": "FH 144h: máx Sudamérica (lon -65..-45, lat -32..-18) 122.2 kt en lat -29.00, lon -52.75"
          },
          {
            "at": "2026-11-05T22:42:08+00:00",
            "level": "info",
            "text": "FH 144h: MSLP global 949.5 .. 1061.9 hPa"
          },
          {
            "at": "2026-11-05T22:42:08+00:00",
            "level": "info",
            "text": "Serie consolidada: <local> era5\\crudos_viento250_gfs_2026-11-04_00z\\serie_viento_250.npz (2, 721, 1440) float32 | horas 0..144 cada 144 h"
          },
          {
            "at": "2026-11-05T22:42:08+00:00",
            "level": "info",
            "text": "Ahora renderizá con: .venv\\Scripts\\python.exe cuadros\\cuadros_viento_250.py --fecha 2026-11-04 --ciclo 00 --hasta-hora 144 --paso 144 --modelo gfs"
          },
          {
            "at": "2026-11-05T22:42:08+00:00",
            "level": "info",
            "text": "[2/2] renderizando 2 cuadros de viento"
          },
          {
            "at": "2026-11-05T22:42:08+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\cuadros\\cuadros_viento_250.py --modelo gfs --fecha 2026-11-04 --ciclo 00 --hasta-hora 144 --paso 144 --px 1400 --fondo-globo oscuro --centro -58.4505 -23.4505 --radio 4.69493 --limpio --salidas <repo>\\app\\var\\media\\cache\\157a64c714e6 --solo-poster"
          },
          {
            "at": "2026-11-05T22:42:09+00:00",
            "level": "info",
            "text": "Datos: <local> era5\\crudos_viento250_gfs_2026-11-04_00z\\serie_viento_250.npz | 2 pasos | rejilla 1440x721"
          },
          {
            "at": "2026-11-05T22:42:18+00:00",
            "level": "info",
            "text": "Póster FH +144h: <repo>\\app\\var\\media\\cache\\157a64c714e6\\poster_viento250_gfs_2026-11-04_00z_fh144.png (1400x1400 px, 8.6s)"
          },
          {
            "at": "2026-11-05T22:42:18+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "poster_viento250_gfs_2026-11-04_00z_fh144.webp",
            "url": "/media/45ebff35d312/poster_viento250_gfs_2026-11-04_00z_fh144.webp",
            "kind": "image",
            "bytes": 48668
          }
        ],
        "plan": [
          "bajando el viento en 250 mb de gfs",
          "renderizando 2 cuadros de viento"
        ],
        "error": null
      }
    },
    {
      "id": "940cc2826b09",
      "product_id": "mur_sst",
      "params": {
        "snapshot": true,
        "ventana": {
          "start": "2026-11-04",
          "end": "2026-11-04"
        },
        "resolucion": "1400",
        "animar": false,
        "fps": 12
      },
      "dates": [
        "2026-11-04"
      ],
      "snapshot": {
        "id": "940cc2826b09",
        "product_id": "mur_sst",
        "product_name": "MUR - temperatura del mar",
        "params": {
          "snapshot": true,
          "ventana": {
            "start": "2026-11-04",
            "end": "2026-11-04"
          },
          "resolucion": "1400",
          "animar": false,
          "fps": 12
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-05T22:43:17+00:00",
        "started_at": "2026-11-05T22:43:17+00:00",
        "finished_at": "2026-11-05T22:43:43+00:00",
        "logs": [
          {
            "at": "2026-11-05T22:43:17+00:00",
            "level": "info",
            "text": "job 940cc2826b09 | mur_sst | modo=real"
          },
          {
            "at": "2026-11-05T22:43:17+00:00",
            "level": "info",
            "text": "[1/2] bajando cuadros de SST"
          },
          {
            "at": "2026-11-05T22:43:17+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\mur_sst.py --desde 2026-11-04 --hasta 2026-11-04 --paso 1 --px 1400 --out <repo>\\app\\var\\media\\cache\\0a4f59e85579"
          },
          {
            "at": "2026-11-05T22:43:18+00:00",
            "level": "info",
            "text": "MUR SST (globo) | 1 cuadros desde 2026-11-04 UTC | paso 1 d | origen 8192x4096 px"
          },
          {
            "at": "2026-11-05T22:43:18+00:00",
            "level": "info",
            "text": "caja -180.0,-90.0,180.0,90.0 | frames en <repo>\\app\\var\\media\\cache\\0a4f59e85579\\frames_mur_globo_2026-11-04T0000_1f_1400px"
          },
          {
            "at": "2026-11-05T22:43:39+00:00",
            "level": "info",
            "text": "  1/1 listos (errores 0) 21s"
          },
          {
            "at": "2026-11-05T22:43:39+00:00",
            "level": "info",
            "text": "1 cuadros listos en 21s"
          },
          {
            "at": "2026-11-05T22:43:39+00:00",
            "level": "info",
            "text": "Ahora renderizá con: .venv\\Scripts\\python.exe cuadros\\cuadros_mur.py --desde 2026-11-04 --hasta 2026-11-04 --paso 1 --px 1400 --out \"<repo>\\app\\var\\media\\cache\\0a4f59e85579\""
          },
          {
            "at": "2026-11-05T22:43:39+00:00",
            "level": "info",
            "text": "[2/2] componiendo el globo"
          },
          {
            "at": "2026-11-05T22:43:39+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\cuadros\\cuadros_mur.py --desde 2026-11-04 --hasta 2026-11-04 --paso 1 --px 1400 --out <repo>\\app\\var\\media\\cache\\0a4f59e85579"
          },
          {
            "at": "2026-11-05T22:43:40+00:00",
            "level": "info",
            "text": "MUR SST globo | 1 cuadros desde 2026-11-04 UTC | salida 1400x1400 px | frames en <repo>\\app\\var\\media\\cache\\0a4f59e85579\\frames_mur_globo_2026-11-04T0000_1f_1400px"
          },
          {
            "at": "2026-11-05T22:43:43+00:00",
            "level": "info",
            "text": "  1/1 listos (3s)"
          },
          {
            "at": "2026-11-05T22:43:43+00:00",
            "level": "info",
            "text": "1 cuadros en <repo>\\app\\var\\media\\cache\\0a4f59e85579\\frames_mur_globo_2026-11-04T0000_1f_1400px"
          },
          {
            "at": "2026-11-05T22:43:43+00:00",
            "level": "info",
            "text": "Armá el video con: .venv\\Scripts\\python.exe animar\\armar.py --frames \"<repo>\\app\\var\\media\\cache\\0a4f59e85579\\frames_mur_globo_2026-11-04T0000_1f_1400px\""
          },
          {
            "at": "2026-11-05T22:43:43+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "cuadro_001.webp",
            "url": "/media/940cc2826b09/cuadro_001.webp",
            "kind": "image",
            "bytes": 288480
          }
        ],
        "plan": [
          "bajando cuadros de SST",
          "componiendo el globo"
        ],
        "error": null
      }
    },
    {
      "id": "bc488f72cd96",
      "product_id": "mur_realista",
      "params": {
        "snapshot": true,
        "ventana": {
          "start": "2026-11-04",
          "end": "2026-11-04"
        },
        "resolucion": "1400",
        "paleta": "realista",
        "trend": false
      },
      "dates": [
        "2026-11-04"
      ],
      "snapshot": {
        "id": "bc488f72cd96",
        "product_id": "mur_realista",
        "product_name": "MUR - SST poster realista",
        "params": {
          "snapshot": true,
          "ventana": {
            "start": "2026-11-04",
            "end": "2026-11-04"
          },
          "resolucion": "1400",
          "paleta": "realista",
          "trend": false
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-05T22:43:44+00:00",
        "started_at": "2026-11-05T22:43:44+00:00",
        "finished_at": "2026-11-05T22:44:05+00:00",
        "logs": [
          {
            "at": "2026-11-05T22:43:44+00:00",
            "level": "info",
            "text": "job bc488f72cd96 | mur_realista | modo=real"
          },
          {
            "at": "2026-11-05T22:43:44+00:00",
            "level": "info",
            "text": "[1/2] bajando la serie semanal de SST"
          },
          {
            "at": "2026-11-05T22:43:44+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\mur_sst.py --desde 2026-11-04 --hasta 2026-11-04 --paso 1 --px 2048 --out <repo>\\app\\var\\media\\cache\\e05b5761e386"
          },
          {
            "at": "2026-11-05T22:43:45+00:00",
            "level": "info",
            "text": "MUR SST (globo) | 1 cuadros desde 2026-11-04 UTC | paso 1 d | origen 8192x4096 px"
          },
          {
            "at": "2026-11-05T22:43:45+00:00",
            "level": "info",
            "text": "caja -180.0,-90.0,180.0,90.0 | frames en <repo>\\app\\var\\media\\cache\\e05b5761e386\\frames_mur_globo_2026-11-04T0000_1f_2048px"
          },
          {
            "at": "2026-11-05T22:43:48+00:00",
            "level": "info",
            "text": "  1/1 listos (errores 0) 3s"
          },
          {
            "at": "2026-11-05T22:43:48+00:00",
            "level": "info",
            "text": "1 cuadros listos en 3s"
          },
          {
            "at": "2026-11-05T22:43:48+00:00",
            "level": "info",
            "text": "Ahora renderizá con: .venv\\Scripts\\python.exe cuadros\\cuadros_mur.py --desde 2026-11-04 --hasta 2026-11-04 --paso 1 --px 2048 --out \"<repo>\\app\\var\\media\\cache\\e05b5761e386\""
          },
          {
            "at": "2026-11-05T22:43:48+00:00",
            "level": "info",
            "text": "[2/2] poster realista 1400px"
          },
          {
            "at": "2026-11-05T22:43:48+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\prototipos\\poster_mur_realista.py --crudo <repo>\\app\\var\\media\\cache\\e05b5761e386\\frames_mur_globo_2026-11-04T0000_1f_2048px\\crudo_001.jpg --px 1400 --paleta realista --rios --out <repo>\\app\\var\\media\\cache\\e05b5761e386\\mur_realista_1400px.png"
          },
          {
            "at": "2026-11-05T22:43:48+00:00",
            "level": "info",
            "text": "Crudo: <repo>\\app\\var\\media\\cache\\e05b5761e386\\frames_mur_globo_2026-11-04T0000_1f_2048px\\crudo_001.jpg"
          },
          {
            "at": "2026-11-05T22:43:48+00:00",
            "level": "info",
            "text": "Fecha: 2026-11-04 00:00 UTC | centro (-125.0, 0.0) | globo 1400 px | paleta realista"
          },
          {
            "at": "2026-11-05T22:43:57+00:00",
            "level": "info",
            "text": "Distribucion area-ponderada: media +0.54 C | desvio 1.03 C"
          },
          {
            "at": "2026-11-05T22:43:57+00:00",
            "level": "info",
            "text": "Reproyectando a Orthographic..."
          },
          {
            "at": "2026-11-05T22:44:05+00:00",
            "level": "info",
            "text": "PNG: <repo>\\app\\var\\media\\cache\\e05b5761e386\\mur_realista_1400px.png"
          },
          {
            "at": "2026-11-05T22:44:05+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "mur_realista_1400px.webp",
            "url": "/media/bc488f72cd96/mur_realista_1400px.webp",
            "kind": "image",
            "bytes": 253494
          }
        ],
        "plan": [
          "bajando la serie semanal de SST",
          "poster realista 1400px"
        ],
        "error": null
      }
    },
    {
      "id": "0307936700f8",
      "product_id": "precipitacion_ecmwf",
      "params": {
        "snapshot": true,
        "paraguay": true,
        "margen": 15,
        "modelo": "ifs",
        "fecha": "2026-11-06",
        "corrida": "00",
        "horizonte": 144,
        "fondo": "claro",
        "resolucion": "1400",
        "animar": true,
        "fps": 12
      },
      "dates": [
        "2026-11-06"
      ],
      "snapshot": {
        "id": "0307936700f8",
        "product_id": "precipitacion_ecmwf",
        "product_name": "ECMWF - precipitacion",
        "params": {
          "snapshot": true,
          "paraguay": true,
          "margen": 15,
          "modelo": "ifs",
          "fecha": "2026-11-06",
          "corrida": "00",
          "horizonte": 144,
          "fondo": "claro",
          "resolucion": "1400",
          "animar": true,
          "fps": 12
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-06T18:35:52+00:00",
        "started_at": "2026-11-06T18:35:52+00:00",
        "finished_at": "2026-11-06T18:36:06+00:00",
        "logs": [
          {
            "at": "2026-11-06T18:35:52+00:00",
            "level": "info",
            "text": "job 0307936700f8 | precipitacion_ecmwf | modo=real"
          },
          {
            "at": "2026-11-06T18:35:55+00:00",
            "level": "info",
            "text": "[1/2] bajando precipitacion de ifs"
          },
          {
            "at": "2026-11-06T18:35:55+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\precipitacion_ecmwf.py --modelo ifs --fecha 2026-11-06 --ciclo 00 --hasta-hora 144 --paso 144"
          },
          {
            "at": "2026-11-06T18:35:57+00:00",
            "level": "info",
            "text": "Precipitación total ECMWF IFS 0.25° | 2026-11-06 00z | 2 pasos (0h..144h cada 144 h)"
          },
          {
            "at": "2026-11-06T18:35:57+00:00",
            "level": "info",
            "text": "fuente: https://data.ecmwf.int/forecasts/20261106/00z/ifs/0p25/oper/20261106000000-0h-oper-fc.index"
          },
          {
            "at": "2026-11-06T18:35:57+00:00",
            "level": "info",
            "text": "crudos en <local> era5\\crudos_precip_ecmwf_2026-11-06_00z"
          },
          {
            "at": "2026-11-06T18:35:59+00:00",
            "level": "info",
            "text": "  1/2 pasos listos (0 reutilizados, errores 0) 2s"
          },
          {
            "at": "2026-11-06T18:36:00+00:00",
            "level": "info",
            "text": "  2/2 pasos listos (0 reutilizados, errores 0) 3s"
          },
          {
            "at": "2026-11-06T18:36:00+00:00",
            "level": "info",
            "text": "2 pasos listos en 3s (0 reutilizados). Consolidando..."
          },
          {
            "at": "2026-11-06T18:36:01+00:00",
            "level": "info",
            "text": "  2/2 pasos consolidados (1s)"
          },
          {
            "at": "2026-11-06T18:36:01+00:00",
            "level": "info",
            "text": "Precipitación acumulada (mm):"
          },
          {
            "at": "2026-11-06T18:36:01+00:00",
            "level": "info",
            "text": "  paso   máx global   máx Sudamérica (lon -65..-45, lat -32..-18)"
          },
          {
            "at": "2026-11-06T18:36:01+00:00",
            "level": "info",
            "text": "    0 h        0.0 mm        0.0 mm"
          },
          {
            "at": "2026-11-06T18:36:01+00:00",
            "level": "info",
            "text": "  144 h      517.8 mm      118.7 mm"
          },
          {
            "at": "2026-11-06T18:36:01+00:00",
            "level": "info",
            "text": "FH 144h: máx global 517.8 mm en lat 49.25, lon -125.50"
          },
          {
            "at": "2026-11-06T18:36:01+00:00",
            "level": "info",
            "text": "FH 144h: máx Sudamérica (lon -65..-45, lat -32..-18) 118.7 mm en lat -27.50, lon -52.75"
          },
          {
            "at": "2026-11-06T18:36:01+00:00",
            "level": "info",
            "text": "FH 144h: máx Paraguay / Sur de Brasil (lon -62..-54, lat -28..-19) 79.3 mm en lat -26.75, lon -54.75"
          },
          {
            "at": "2026-11-06T18:36:01+00:00",
            "level": "info",
            "text": "Serie consolidada: <local> era5\\crudos_precip_ecmwf_2026-11-06_00z\\serie_tp_mm.npz (2, 721, 1440) float32 | horas 0..144 cada 144 h"
          },
          {
            "at": "2026-11-06T18:36:01+00:00",
            "level": "info",
            "text": "Ahora renderizá con: .venv\\Scripts\\python.exe cuadros\\cuadros_precipitacion.py --fecha 2026-11-06 --ciclo 00 --hasta-hora 144 --paso 144"
          },
          {
            "at": "2026-11-06T18:36:01+00:00",
            "level": "info",
            "text": "[2/2] renderizando 2 cuadros"
          },
          {
            "at": "2026-11-06T18:36:01+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\cuadros\\cuadros_precipitacion.py --modelo ifs --fecha 2026-11-06 --ciclo 00 --hasta-hora 144 --paso 144 --px 1400 --fondo-globo claro --centro -58.4505 -23.4505 --radio 5.44947 --limpio --salidas <repo>\\app\\var\\media\\cache\\422e427360ed --solo-poster"
          },
          {
            "at": "2026-11-06T18:36:01+00:00",
            "level": "info",
            "text": "Datos: <local> era5\\crudos_precip_ecmwf_2026-11-06_00z\\serie_tp_mm.npz | 2 pasos | rejilla 1440x721"
          },
          {
            "at": "2026-11-06T18:36:05+00:00",
            "level": "info",
            "text": "Póster FH +144h: <repo>\\app\\var\\media\\cache\\422e427360ed\\poster_precip_ecmwf_2026-11-06_00z_fh144.png (1400x1400 px, 3.5s)"
          },
          {
            "at": "2026-11-06T18:36:06+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "poster_precip_ecmwf_2026-11-06_00z_fh144.webp",
            "url": "/media/0307936700f8/poster_precip_ecmwf_2026-11-06_00z_fh144.webp",
            "kind": "image",
            "bytes": 87592
          }
        ],
        "plan": [
          "bajando precipitacion de ifs",
          "renderizando 2 cuadros"
        ],
        "error": null
      }
    },
    {
      "id": "4ef3908faa92",
      "product_id": "follaje",
      "params": {
        "snapshot": true,
        "ventana": {
          "start": "2026-10-10",
          "end": "2026-10-10"
        },
        "proyeccion": "plano",
        "resolucion": "1400",
        "animar": false,
        "fps": 12
      },
      "dates": [
        "2026-10-10"
      ],
      "snapshot": {
        "id": "4ef3908faa92",
        "product_id": "follaje",
        "product_name": "PACE - follaje (LANDVI)",
        "params": {
          "snapshot": true,
          "ventana": {
            "start": "2026-10-10",
            "end": "2026-10-10"
          },
          "proyeccion": "plano",
          "resolucion": "1400",
          "animar": false,
          "fps": 12
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-05T22:44:05+00:00",
        "started_at": "2026-11-05T22:44:05+00:00",
        "finished_at": "2026-11-05T22:44:16+00:00",
        "logs": [
          {
            "at": "2026-11-05T22:44:05+00:00",
            "level": "info",
            "text": "job 4ef3908faa92 | follaje | modo=real"
          },
          {
            "at": "2026-11-05T22:44:05+00:00",
            "level": "info",
            "text": "[1/2] bajando LANDVI de PACE"
          },
          {
            "at": "2026-11-05T22:44:05+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\pace_landvi.py --desde 2026-10-10 --hasta 2026-10-10"
          },
          {
            "at": "2026-11-05T22:44:06+00:00",
            "level": "info",
            "text": "Falta autenticación: exportá las cookies del navegador con --cookies, o creá ~/.netrc con la entrada de urs.earthdata.nasa.gov."
          },
          {
            "at": "2026-11-05T22:44:06+00:00",
            "level": "warn",
            "text": "la descarga cerro con codigo 1: sigo con lo que hay"
          },
          {
            "at": "2026-11-05T22:44:06+00:00",
            "level": "info",
            "text": "[2/2] renderizando el follaje (plano)"
          },
          {
            "at": "2026-11-05T22:44:06+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\cuadros\\cuadros_follaje.py --desde 2026-10-10 --hasta 2026-10-10 --px 1400 --out <repo>\\app\\var\\media\\cache\\98b1ea7a7872\\frames"
          },
          {
            "at": "2026-11-05T22:44:08+00:00",
            "level": "info",
            "text": "1 cuadros -> <repo>\\app\\var\\media\\cache\\98b1ea7a7872\\frames"
          },
          {
            "at": "2026-11-05T22:44:16+00:00",
            "level": "info",
            "text": "  cuadro_001.png  Oct 4 - 10, 2026  (2.5s)"
          },
          {
            "at": "2026-11-05T22:44:16+00:00",
            "level": "info",
            "text": "Listo. Armá el video con:"
          },
          {
            "at": "2026-11-05T22:44:16+00:00",
            "level": "info",
            "text": "  .venv\\Scripts\\python.exe animar\\armar.py --frames \"<repo>\\app\\var\\media\\cache\\98b1ea7a7872\\frames\" --fps 6"
          },
          {
            "at": "2026-11-05T22:44:16+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "cuadro_001.webp",
            "url": "/media/4ef3908faa92/cuadro_001.webp",
            "kind": "image",
            "bytes": 103864
          }
        ],
        "plan": [
          "bajando LANDVI de PACE",
          "renderizando el follaje (plano)"
        ],
        "error": null
      }
    },
    {
      "id": "de71dcb4fe17",
      "product_id": "truecolor_viirs",
      "params": {
        "snapshot": true,
        "paraguay": false,
        "margen": 6,
        "ventana": {
          "start": "2026-11-04",
          "end": "2026-11-04"
        },
        "resolucion": "1400",
        "animar": false,
        "fps": 6
      },
      "dates": [
        "2026-11-04"
      ],
      "snapshot": {
        "id": "de71dcb4fe17",
        "product_id": "truecolor_viirs",
        "product_name": "NOAA-20 - true color (VIIRS)",
        "params": {
          "snapshot": true,
          "paraguay": false,
          "margen": 6,
          "ventana": {
            "start": "2026-11-04",
            "end": "2026-11-04"
          },
          "resolucion": "1400",
          "animar": false,
          "fps": 6
        },
        "mode": "real",
        "status": "done",
        "progress": 1.0,
        "stage": "resultado precalculado",
        "created_at": "2026-11-05T22:44:17+00:00",
        "started_at": "2026-11-05T22:44:17+00:00",
        "finished_at": "2026-11-05T22:44:54+00:00",
        "logs": [
          {
            "at": "2026-11-05T22:44:17+00:00",
            "level": "info",
            "text": "job de71dcb4fe17 | truecolor_viirs | modo=real"
          },
          {
            "at": "2026-11-05T22:44:17+00:00",
            "level": "info",
            "text": "[1/2] bajando true color NOAA-20 (1 dia(s))"
          },
          {
            "at": "2026-11-05T22:44:17+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\descargar\\truecolor.py --desde 2026-11-04 --hasta 2026-11-04 --paso 1 --px 1400 --capa VIIRS_NOAA20_CorrectedReflectance_TrueColor --out <repo>\\app\\var\\media\\cache\\50ecae621392"
          },
          {
            "at": "2026-11-05T22:44:18+00:00",
            "level": "info",
            "text": "True Color noaa20 (globo) | 1 cuadros desde 2026-11-04 UTC | paso 1 d | origen 8192x4096 px"
          },
          {
            "at": "2026-11-05T22:44:18+00:00",
            "level": "info",
            "text": "capa VIIRS_NOAA20_CorrectedReflectance_TrueColor | caja -180.0,-90.0,180.0,90.0 | frames en <repo>\\app\\var\\media\\cache\\50ecae621392\\frames_truecolor_noaa20_globo_2026-11-04T0000_1f_1400px"
          },
          {
            "at": "2026-11-05T22:44:50+00:00",
            "level": "info",
            "text": "  1/1 listos (errores 0) 32s"
          },
          {
            "at": "2026-11-05T22:44:50+00:00",
            "level": "info",
            "text": "1 cuadros listos en 32s"
          },
          {
            "at": "2026-11-05T22:44:50+00:00",
            "level": "info",
            "text": "Ahora renderizá con: .venv\\Scripts\\python.exe cuadros\\cuadros_truecolor.py --desde 2026-11-04 --hasta 2026-11-04 --paso 1 --capa VIIRS_NOAA20_CorrectedReflectance_TrueColor --px 1400 --out \"<repo>\\app\\var\\media\\cache\\50ecae621392\""
          },
          {
            "at": "2026-11-05T22:44:50+00:00",
            "level": "info",
            "text": "[2/2] renderizando 1 cuadro(s) de NOAA-20"
          },
          {
            "at": "2026-11-05T22:44:50+00:00",
            "level": "info",
            "text": "  python.exe <repo>\\cuadros\\cuadros_truecolor.py --desde 2026-11-04 --hasta 2026-11-04 --paso 1 --px 1400 --capa VIIRS_NOAA20_CorrectedReflectance_TrueColor --out <repo>\\app\\var\\media\\cache\\50ecae621392 --geojson "
          },
          {
            "at": "2026-11-05T22:44:50+00:00",
            "level": "info",
            "text": "True Color noaa20 globo | 1 cuadros desde 2026-11-04 UTC | salida 1400x1400 px | frames en <repo>\\app\\var\\media\\cache\\50ecae621392\\frames_truecolor_noaa20_globo_2026-11-04T0000_1f_1400px"
          },
          {
            "at": "2026-11-05T22:44:53+00:00",
            "level": "info",
            "text": "  1/1 listos (3s)"
          },
          {
            "at": "2026-11-05T22:44:53+00:00",
            "level": "info",
            "text": "1 cuadros en <repo>\\app\\var\\media\\cache\\50ecae621392\\frames_truecolor_noaa20_globo_2026-11-04T0000_1f_1400px"
          },
          {
            "at": "2026-11-05T22:44:53+00:00",
            "level": "info",
            "text": "Armá el video con: .venv\\Scripts\\python.exe animar\\armar.py --frames \"<repo>\\app\\var\\media\\cache\\50ecae621392\\frames_truecolor_noaa20_globo_2026-11-04T0000_1f_1400px\""
          },
          {
            "at": "2026-11-05T22:44:54+00:00",
            "level": "info",
            "text": "listo: 1 artefacto(s)"
          }
        ],
        "artifacts": [
          {
            "name": "cuadro_001.webp",
            "url": "/media/de71dcb4fe17/cuadro_001.webp",
            "kind": "image",
            "bytes": 440342
          }
        ],
        "plan": [
          "bajando true color NOAA-20 (1 dia(s))",
          "renderizando 1 cuadro(s) de NOAA-20"
        ],
        "error": null
      }
    }
  ],
  "catalog": {
    "products": [
      {
        "id": "goes_banda",
        "name": "GOES - banda cruda, estilo color real",
        "group": "satelite",
        "stage": "descargar/descargar_goes.py + prototipos/poster_goes_banda.py",
        "summary": "Una banda ABI real, no el compuesto de tres. Mismo encuadre y fondo del color real: globo completo, sin reticula, costas ni barra de color.",
        "params": [
          {
            "name": "snapshot",
            "label": "Snapshot",
            "kind": "toggle",
            "default": true,
            "options": [],
            "help": "un solo cuadro: no arma serie ni animación, y usa el cuadro de siempre",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "paraguay",
            "label": "Solo Paraguay",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "encuadra la captura o la animación en las coordenadas de Paraguay",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "margen",
            "label": "Margen Paraguay (%)",
            "kind": "slider",
            "default": 6,
            "options": [],
            "help": "aire alrededor del país dentro del encuadre",
            "min": 0.0,
            "max": 20.0,
            "step": 1.0,
            "enabled_when": {
              "paraguay": true
            }
          },
          {
            "name": "satelite",
            "label": "Satelite",
            "kind": "select",
            "default": "G19",
            "options": [
              {
                "value": "G19",
                "label": "GOES-East G19 (75.2 W)",
                "only_when": null
              },
              {
                "value": "G18",
                "label": "GOES-West G18 (137.2 W)",
                "only_when": null
              },
              {
                "value": "G16",
                "label": "GOES-East G16 (hasta 2025)",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "banda",
            "label": "Banda",
            "kind": "select",
            "default": "C13",
            "options": [
              {
                "value": "C01",
                "label": "C01 - 0.47 um (visible azul)",
                "only_when": null
              },
              {
                "value": "C02",
                "label": "C02 - 0.64 um (visible rojo)",
                "only_when": null
              },
              {
                "value": "C03",
                "label": "C03 - 0.86 um (veggie)",
                "only_when": null
              },
              {
                "value": "C04",
                "label": "C04 - 1.37 um (cirrus)",
                "only_when": null
              },
              {
                "value": "C05",
                "label": "C05 - 1.61 um (nieve y hielo)",
                "only_when": null
              },
              {
                "value": "C06",
                "label": "C06 - 2.25 um (particula de nube)",
                "only_when": null
              },
              {
                "value": "C07",
                "label": "C07 - 3.90 um (IR onda corta)",
                "only_when": null
              },
              {
                "value": "C08",
                "label": "C08 - 6.19 um (vapor de agua alto)",
                "only_when": null
              },
              {
                "value": "C09",
                "label": "C09 - 6.95 um (vapor de agua medio)",
                "only_when": null
              },
              {
                "value": "C10",
                "label": "C10 - 7.34 um (vapor de agua bajo)",
                "only_when": null
              },
              {
                "value": "C11",
                "label": "C11 - 8.50 um (fase de tope de nube)",
                "only_when": null
              },
              {
                "value": "C12",
                "label": "C12 - 9.61 um (ozono)",
                "only_when": null
              },
              {
                "value": "C13",
                "label": "C13 - 10.35 um (IR ventana limpia)",
                "only_when": null
              },
              {
                "value": "C14",
                "label": "C14 - 11.20 um (IR onda larga)",
                "only_when": null
              },
              {
                "value": "C15",
                "label": "C15 - 12.30 um (IR onda larga sucia)",
                "only_when": null
              },
              {
                "value": "C16",
                "label": "C16 - 13.30 um (CO2 onda larga)",
                "only_when": null
              }
            ],
            "help": "C01-C06 son reflectancia (visible e infrarrojo cercano); C07-C16, temperatura de brillo",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "paleta",
            "label": "Paleta",
            "kind": "select",
            "default": "clean_ir",
            "options": [
              {
                "value": "reflectancia",
                "label": "reflectancia - visible e infrarrojo cercano, negro a blanco (0 a 100 %)",
                "only_when": {
                  "banda": [
                    "C01",
                    "C02",
                    "C03",
                    "C04",
                    "C05",
                    "C06"
                  ]
                }
              },
              {
                "value": "clean_ir",
                "label": "clean_ir - Clean Infrared (GIBS), banda 13",
                "only_when": {
                  "banda": "C13"
                }
              },
              {
                "value": "c07_ir",
                "label": "c07_ir - IR oficial GOES, banda 7 (3.9 um, -83 a 127 C)",
                "only_when": {
                  "banda": "C07"
                }
              },
              {
                "value": "c08_ir",
                "label": "c08_ir - vapor de agua oficial GOES, banda 8 (6.2 um, -93 a 7 C)",
                "only_when": {
                  "banda": "C08"
                }
              },
              {
                "value": "c09_ir",
                "label": "c09_ir - vapor de agua oficial GOES, banda 9 (6.9 um, -93 a 7 C)",
                "only_when": {
                  "banda": "C09"
                }
              },
              {
                "value": "c10_ir",
                "label": "c10_ir - vapor de agua oficial GOES, banda 10 (7.3 um, -93 a 7 C)",
                "only_when": {
                  "banda": "C10"
                }
              },
              {
                "value": "c11_ir",
                "label": "c11_ir - IR oficial GOES, banda 11 (8.5 um, -110 a 57 C)",
                "only_when": {
                  "banda": "C11"
                }
              },
              {
                "value": "c12_ir",
                "label": "c12_ir - IR oficial GOES, banda 12 (9.6 um, -110 a 57 C)",
                "only_when": {
                  "banda": "C12"
                }
              },
              {
                "value": "c13_ir",
                "label": "c13_ir - IR oficial GOES, banda 13 (10.3 um, -110 a 57 C)",
                "only_when": {
                  "banda": "C13"
                }
              },
              {
                "value": "c14_ir",
                "label": "c14_ir - IR oficial GOES, banda 14 (11.2 um, -110 a 57 C)",
                "only_when": {
                  "banda": "C14"
                }
              },
              {
                "value": "c15_ir",
                "label": "c15_ir - IR oficial GOES, banda 15 (12.3 um, -110 a 57 C)",
                "only_when": {
                  "banda": "C15"
                }
              },
              {
                "value": "c16_ir",
                "label": "c16_ir - IR oficial GOES, banda 16 (13.3 um, -128 a 128 C)",
                "only_when": {
                  "banda": "C16"
                }
              },
              {
                "value": "gris",
                "label": "gris - reflectancia",
                "only_when": null
              },
              {
                "value": "termico",
                "label": "termico - gris termico",
                "only_when": null
              },
              {
                "value": "anomalia",
                "label": "anomalia - paleta de anomalia",
                "only_when": null
              },
              {
                "value": "magma",
                "label": "magma",
                "only_when": null
              },
              {
                "value": "inferno",
                "label": "inferno",
                "only_when": null
              },
              {
                "value": "turbo",
                "label": "turbo",
                "only_when": null
              }
            ],
            "help": "cada banda termica tiene su paleta oficial y solo se ofrece con ella: reflectancia es la de C01-C06 (negro a blanco, 0 a 100 %); clean_ir es la de GIBS (-92.1 a 56.9 C, C13), c07_ir la de la banda 7 (-83 a 127 C), c08_ir..c10_ir la de vapor de agua (-93 a 7 C), c11_ir..c15_ir la de la ventana IR (-110 a 57 C) y c16_ir va de -128 a 128 C",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "ventana",
            "label": "Ventana temporal",
            "kind": "date-range",
            "default": {
              "start": "2026-11-07",
              "end": "2026-11-08"
            },
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultimos": false
            }
          },
          {
            "name": "ultimos",
            "label": "Últimos datos",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "ignora la ventana de fechas: baja y anima los cuadros más nuevos publicados",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "snapshot": false
            }
          },
          {
            "name": "ultimos_n",
            "label": "Cuántos cuadros",
            "kind": "select",
            "default": "24",
            "options": [
              {
                "value": "10",
                "label": "10 cuadros",
                "only_when": null
              },
              {
                "value": "12",
                "label": "12 cuadros",
                "only_when": null
              },
              {
                "value": "24",
                "label": "24 cuadros",
                "only_when": null
              },
              {
                "value": "36",
                "label": "36 cuadros",
                "only_when": null
              },
              {
                "value": "48",
                "label": "48 cuadros",
                "only_when": null
              },
              {
                "value": "60",
                "label": "60 cuadros",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultimos": true,
              "snapshot": false
            }
          },
          {
            "name": "hora",
            "label": "Hora del cuadro (UTC)",
            "kind": "hour",
            "default": 15,
            "options": [],
            "help": "hora UTC, igual que el dataset crudo; Paraguay es UTC-3 (12 UTC = 09:00 local)",
            "min": 0.0,
            "max": 23.0,
            "step": 1.0,
            "enabled_when": {
              "snapshot": true
            }
          },
          {
            "name": "minuto",
            "label": "Minuto",
            "kind": "select",
            "default": "00",
            "options": [
              {
                "value": "00",
                "label": "00",
                "only_when": null
              },
              {
                "value": "10",
                "label": "10",
                "only_when": null
              },
              {
                "value": "20",
                "label": "20",
                "only_when": null
              },
              {
                "value": "30",
                "label": "30",
                "only_when": null
              },
              {
                "value": "40",
                "label": "40",
                "only_when": null
              },
              {
                "value": "50",
                "label": "50",
                "only_when": null
              }
            ],
            "help": "los slots del ABI caen cada 10 minutos",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "snapshot": true
            }
          },
          {
            "name": "resolucion",
            "label": "Resolucion",
            "kind": "select",
            "default": "2712",
            "options": [
              {
                "value": "1400",
                "label": "1400",
                "only_when": null
              },
              {
                "value": "1800",
                "label": "1800",
                "only_when": null
              },
              {
                "value": "2000",
                "label": "2000",
                "only_when": null
              },
              {
                "value": "2400",
                "label": "2400",
                "only_when": null
              },
              {
                "value": "2712",
                "label": "2712",
                "only_when": null
              },
              {
                "value": "3200",
                "label": "3200",
                "only_when": null
              },
              {
                "value": "4000",
                "label": "4000",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "hora_desde",
            "label": "Desde (UTC)",
            "kind": "hour",
            "default": 0,
            "options": [],
            "help": "hora UTC, igual que el dataset crudo; Paraguay es UTC-3 (12 UTC = 09:00 local)",
            "min": 0.0,
            "max": 23.0,
            "step": 1.0,
            "enabled_when": {
              "ultimos": false,
              "snapshot": false
            }
          },
          {
            "name": "hora_hasta",
            "label": "Hasta (UTC)",
            "kind": "hour",
            "default": 24,
            "options": [],
            "help": "fin exclusivo: 24 cierra el día UTC completo",
            "min": 1.0,
            "max": 24.0,
            "step": 1.0,
            "enabled_when": {
              "ultimos": false,
              "snapshot": false
            }
          },
          {
            "name": "animar",
            "label": "Animar",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultimos": false,
              "snapshot": false
            }
          },
          {
            "name": "fps",
            "label": "Cuadros por segundo",
            "kind": "slider",
            "default": 12,
            "options": [],
            "help": "",
            "min": 4.0,
            "max": 30.0,
            "step": 2.0,
            "enabled_when": {
              "snapshot": false
            }
          }
        ],
        "preview": "/previews/goes_banda.webp",
        "previews": [
          {
            "url": "/previews/goes_banda--G19--C01--reflectancia.webp",
            "when": {
              "satelite": "G19",
              "banda": "C01",
              "paleta": "reflectancia"
            }
          },
          {
            "url": "/previews/goes_banda--G19--C02--reflectancia.webp",
            "when": {
              "satelite": "G19",
              "banda": "C02",
              "paleta": "reflectancia"
            }
          },
          {
            "url": "/previews/goes_banda--G19--C03--reflectancia.webp",
            "when": {
              "satelite": "G19",
              "banda": "C03",
              "paleta": "reflectancia"
            }
          },
          {
            "url": "/previews/goes_banda--G19--C04--reflectancia.webp",
            "when": {
              "satelite": "G19",
              "banda": "C04",
              "paleta": "reflectancia"
            }
          },
          {
            "url": "/previews/goes_banda--G19--C05--reflectancia.webp",
            "when": {
              "satelite": "G19",
              "banda": "C05",
              "paleta": "reflectancia"
            }
          },
          {
            "url": "/previews/goes_banda--G19--C06--reflectancia.webp",
            "when": {
              "satelite": "G19",
              "banda": "C06",
              "paleta": "reflectancia"
            }
          },
          {
            "url": "/previews/goes_banda--G19--C07--c07_ir.webp",
            "when": {
              "satelite": "G19",
              "banda": "C07",
              "paleta": "c07_ir"
            }
          },
          {
            "url": "/previews/goes_banda--G19--C08--c08_ir.webp",
            "when": {
              "satelite": "G19",
              "banda": "C08",
              "paleta": "c08_ir"
            }
          },
          {
            "url": "/previews/goes_banda--G19--C09--c09_ir.webp",
            "when": {
              "satelite": "G19",
              "banda": "C09",
              "paleta": "c09_ir"
            }
          },
          {
            "url": "/previews/goes_banda--G19--C10--c10_ir.webp",
            "when": {
              "satelite": "G19",
              "banda": "C10",
              "paleta": "c10_ir"
            }
          },
          {
            "url": "/previews/goes_banda--G19--C11--c11_ir.webp",
            "when": {
              "satelite": "G19",
              "banda": "C11",
              "paleta": "c11_ir"
            }
          },
          {
            "url": "/previews/goes_banda--G19--C12--c12_ir.webp",
            "when": {
              "satelite": "G19",
              "banda": "C12",
              "paleta": "c12_ir"
            }
          },
          {
            "url": "/previews/goes_banda--G19--C13--clean_ir.webp",
            "when": {
              "satelite": "G19",
              "banda": "C13",
              "paleta": "clean_ir"
            }
          },
          {
            "url": "/previews/goes_banda--G19--C14--c14_ir.webp",
            "when": {
              "satelite": "G19",
              "banda": "C14",
              "paleta": "c14_ir"
            }
          },
          {
            "url": "/previews/goes_banda--G19--C15--c15_ir.webp",
            "when": {
              "satelite": "G19",
              "banda": "C15",
              "paleta": "c15_ir"
            }
          },
          {
            "url": "/previews/goes_banda--G19--C16--c16_ir.webp",
            "when": {
              "satelite": "G19",
              "banda": "C16",
              "paleta": "c16_ir"
            }
          },
          {
            "url": "/previews/goes_banda--G16--anomalia.webp",
            "when": {
              "satelite": "G16",
              "paleta": "anomalia"
            }
          },
          {
            "url": "/previews/goes_banda--G16--clean_ir.webp",
            "when": {
              "satelite": "G16",
              "paleta": "clean_ir"
            }
          },
          {
            "url": "/previews/goes_banda--G16--gris.webp",
            "when": {
              "satelite": "G16",
              "paleta": "gris"
            }
          },
          {
            "url": "/previews/goes_banda--G16--inferno.webp",
            "when": {
              "satelite": "G16",
              "paleta": "inferno"
            }
          },
          {
            "url": "/previews/goes_banda--G16--magma.webp",
            "when": {
              "satelite": "G16",
              "paleta": "magma"
            }
          },
          {
            "url": "/previews/goes_banda--G16--termico.webp",
            "when": {
              "satelite": "G16",
              "paleta": "termico"
            }
          },
          {
            "url": "/previews/goes_banda--G16--turbo.webp",
            "when": {
              "satelite": "G16",
              "paleta": "turbo"
            }
          },
          {
            "url": "/previews/goes_banda--G18--anomalia.webp",
            "when": {
              "satelite": "G18",
              "paleta": "anomalia"
            }
          },
          {
            "url": "/previews/goes_banda--G18--clean_ir.webp",
            "when": {
              "satelite": "G18",
              "paleta": "clean_ir"
            }
          },
          {
            "url": "/previews/goes_banda--G18--gris.webp",
            "when": {
              "satelite": "G18",
              "paleta": "gris"
            }
          },
          {
            "url": "/previews/goes_banda--G18--inferno.webp",
            "when": {
              "satelite": "G18",
              "paleta": "inferno"
            }
          },
          {
            "url": "/previews/goes_banda--G18--magma.webp",
            "when": {
              "satelite": "G18",
              "paleta": "magma"
            }
          },
          {
            "url": "/previews/goes_banda--G18--termico.webp",
            "when": {
              "satelite": "G18",
              "paleta": "termico"
            }
          },
          {
            "url": "/previews/goes_banda--G18--turbo.webp",
            "when": {
              "satelite": "G18",
              "paleta": "turbo"
            }
          },
          {
            "url": "/previews/goes_banda--G19--anomalia.webp",
            "when": {
              "satelite": "G19",
              "paleta": "anomalia"
            }
          },
          {
            "url": "/previews/goes_banda--G19--clean_ir.webp",
            "when": {
              "satelite": "G19",
              "paleta": "clean_ir"
            }
          },
          {
            "url": "/previews/goes_banda--G19--gris.webp",
            "when": {
              "satelite": "G19",
              "paleta": "gris"
            }
          },
          {
            "url": "/previews/goes_banda--G19--inferno.webp",
            "when": {
              "satelite": "G19",
              "paleta": "inferno"
            }
          },
          {
            "url": "/previews/goes_banda--G19--magma.webp",
            "when": {
              "satelite": "G19",
              "paleta": "magma"
            }
          },
          {
            "url": "/previews/goes_banda--G19--termico.webp",
            "when": {
              "satelite": "G19",
              "paleta": "termico"
            }
          },
          {
            "url": "/previews/goes_banda--G19--turbo.webp",
            "when": {
              "satelite": "G19",
              "paleta": "turbo"
            }
          }
        ],
        "command_ready": true,
        "command": null
      },
      {
        "id": "goes_c13",
        "name": "GOES - IR en globo (C13)",
        "group": "satelite",
        "stage": "descargar/descargar_goes.py + cuadros/cuadros_c13_ir.py",
        "summary": "Disco completo en globo, centrado en el punto subsatelital: entra el globo entero, sin recorte regional y sin perder el limbo.",
        "params": [
          {
            "name": "snapshot",
            "label": "Snapshot",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "un solo cuadro: no arma serie ni animación, y usa el cuadro de siempre",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "satelite",
            "label": "Satelite",
            "kind": "select",
            "default": "G19",
            "options": [
              {
                "value": "G19",
                "label": "GOES-East G19 (75.2 W)",
                "only_when": null
              },
              {
                "value": "G18",
                "label": "GOES-West G18 (137.2 W)",
                "only_when": null
              },
              {
                "value": "G16",
                "label": "GOES-East G16 (hasta 2025)",
                "only_when": null
              }
            ],
            "help": "define la carpeta de datos goes_c13_<sat>",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "ventana",
            "label": "Ventana temporal",
            "kind": "date-range",
            "default": {
              "start": "2026-11-03",
              "end": "2026-11-04"
            },
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultimos": false
            }
          },
          {
            "name": "ultimos",
            "label": "Últimos datos",
            "kind": "toggle",
            "default": true,
            "options": [],
            "help": "ignora la ventana de fechas: baja y anima los cuadros más nuevos publicados",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "snapshot": false
            }
          },
          {
            "name": "ultimos_n",
            "label": "Cuántos cuadros",
            "kind": "select",
            "default": "12",
            "options": [
              {
                "value": "10",
                "label": "10 cuadros",
                "only_when": null
              },
              {
                "value": "12",
                "label": "12 cuadros",
                "only_when": null
              },
              {
                "value": "24",
                "label": "24 cuadros",
                "only_when": null
              },
              {
                "value": "36",
                "label": "36 cuadros",
                "only_when": null
              },
              {
                "value": "48",
                "label": "48 cuadros",
                "only_when": null
              },
              {
                "value": "60",
                "label": "60 cuadros",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultimos": true,
              "snapshot": false
            }
          },
          {
            "name": "hora",
            "label": "Hora del cuadro (UTC)",
            "kind": "hour",
            "default": 15,
            "options": [],
            "help": "hora UTC, igual que el dataset crudo; Paraguay es UTC-3 (12 UTC = 09:00 local)",
            "min": 0.0,
            "max": 23.0,
            "step": 1.0,
            "enabled_when": {
              "snapshot": true
            }
          },
          {
            "name": "minuto",
            "label": "Minuto",
            "kind": "select",
            "default": "00",
            "options": [
              {
                "value": "00",
                "label": "00",
                "only_when": null
              },
              {
                "value": "10",
                "label": "10",
                "only_when": null
              },
              {
                "value": "20",
                "label": "20",
                "only_when": null
              },
              {
                "value": "30",
                "label": "30",
                "only_when": null
              },
              {
                "value": "40",
                "label": "40",
                "only_when": null
              },
              {
                "value": "50",
                "label": "50",
                "only_when": null
              }
            ],
            "help": "los slots del ABI caen cada 10 minutos",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "snapshot": true
            }
          },
          {
            "name": "paleta",
            "label": "Paleta",
            "kind": "select",
            "default": "clean_ir",
            "options": [
              {
                "value": "clean_ir",
                "label": "clean_ir - Clean Infrared (GIBS)",
                "only_when": null
              },
              {
                "value": "termico",
                "label": "termico - gris termico",
                "only_when": null
              },
              {
                "value": "gris",
                "label": "gris - reflectancia",
                "only_when": null
              },
              {
                "value": "anomalia",
                "label": "anomalia - paleta de anomalia",
                "only_when": null
              },
              {
                "value": "magma",
                "label": "magma",
                "only_when": null
              },
              {
                "value": "inferno",
                "label": "inferno",
                "only_when": null
              },
              {
                "value": "turbo",
                "label": "turbo",
                "only_when": null
              }
            ],
            "help": "clean_ir es la del modulo comun/paleta_gibs.py",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "resolucion",
            "label": "Resolucion",
            "kind": "select",
            "default": "1400",
            "options": [
              {
                "value": "1400",
                "label": "1400",
                "only_when": null
              },
              {
                "value": "1800",
                "label": "1800",
                "only_when": null
              },
              {
                "value": "2000",
                "label": "2000",
                "only_when": null
              },
              {
                "value": "2400",
                "label": "2400",
                "only_when": null
              },
              {
                "value": "2712",
                "label": "2712",
                "only_when": null
              },
              {
                "value": "3200",
                "label": "3200",
                "only_when": null
              },
              {
                "value": "4000",
                "label": "4000",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "hora_desde",
            "label": "Desde (UTC)",
            "kind": "hour",
            "default": 0,
            "options": [],
            "help": "hora UTC, igual que el dataset crudo; Paraguay es UTC-3 (12 UTC = 09:00 local)",
            "min": 0.0,
            "max": 23.0,
            "step": 1.0,
            "enabled_when": {
              "ultimos": false,
              "snapshot": false
            }
          },
          {
            "name": "hora_hasta",
            "label": "Hasta (UTC)",
            "kind": "hour",
            "default": 24,
            "options": [],
            "help": "fin exclusivo: 24 cierra el día UTC completo",
            "min": 1.0,
            "max": 24.0,
            "step": 1.0,
            "enabled_when": {
              "ultimos": false,
              "snapshot": false
            }
          },
          {
            "name": "animar",
            "label": "Animar",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultimos": false,
              "snapshot": false
            }
          },
          {
            "name": "fps",
            "label": "Cuadros por segundo",
            "kind": "slider",
            "default": 6,
            "options": [],
            "help": "",
            "min": 4.0,
            "max": 30.0,
            "step": 2.0,
            "enabled_when": {
              "snapshot": false
            }
          }
        ],
        "preview": "/previews/goes_c13.webp",
        "previews": [
          {
            "url": "/previews/goes_c13--G16--false.webp",
            "when": {
              "satelite": "G16",
              "paraguay": "false"
            }
          },
          {
            "url": "/previews/goes_c13--G18--false.webp",
            "when": {
              "satelite": "G18",
              "paraguay": "false"
            }
          },
          {
            "url": "/previews/goes_c13--G19--false.webp",
            "when": {
              "satelite": "G19",
              "paraguay": "false"
            }
          },
          {
            "url": "/previews/goes_c13--G19--true.webp",
            "when": {
              "satelite": "G19",
              "paraguay": "true"
            }
          }
        ],
        "command_ready": true,
        "command": null
      },
      {
        "id": "geocolor",
        "name": "GOES - GeoColor (dia real, IR y luces)",
        "group": "satelite",
        "stage": "descargar/geocolor.py + cuadros/cuadros_geocolor.py",
        "summary": "Producto RGB ya mezclado de NASA GIBS: color real de dia, IR de noche y luces de ciudad. No es el compuesto de tres bandas.",
        "params": [
          {
            "name": "snapshot",
            "label": "Snapshot",
            "kind": "toggle",
            "default": true,
            "options": [],
            "help": "un solo cuadro: no arma serie ni animación, y usa el cuadro de siempre",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "paraguay",
            "label": "Solo Paraguay",
            "kind": "toggle",
            "default": true,
            "options": [],
            "help": "encuadra la captura o la animación en las coordenadas de Paraguay",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "margen",
            "label": "Margen Paraguay (%)",
            "kind": "slider",
            "default": 10,
            "options": [],
            "help": "aire alrededor del país dentro del encuadre",
            "min": 0.0,
            "max": 20.0,
            "step": 1.0,
            "enabled_when": {
              "paraguay": true
            }
          },
          {
            "name": "satelite",
            "label": "Satelite",
            "kind": "select",
            "default": "G19",
            "options": [
              {
                "value": "G19",
                "label": "GOES-East G19 (75.2 W)",
                "only_when": null
              },
              {
                "value": "G18",
                "label": "GOES-West G18 (137.2 W)",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "ventana",
            "label": "Ventana temporal",
            "kind": "date-range",
            "default": {
              "start": "2026-11-03",
              "end": "2026-11-04"
            },
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultimos": false
            }
          },
          {
            "name": "ultimos",
            "label": "Últimos datos",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "ignora la ventana de fechas: baja y anima los cuadros más nuevos publicados",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "snapshot": false
            }
          },
          {
            "name": "ultimos_n",
            "label": "Cuántos cuadros",
            "kind": "select",
            "default": "24",
            "options": [
              {
                "value": "10",
                "label": "10 cuadros",
                "only_when": null
              },
              {
                "value": "12",
                "label": "12 cuadros",
                "only_when": null
              },
              {
                "value": "24",
                "label": "24 cuadros",
                "only_when": null
              },
              {
                "value": "36",
                "label": "36 cuadros",
                "only_when": null
              },
              {
                "value": "48",
                "label": "48 cuadros",
                "only_when": null
              },
              {
                "value": "60",
                "label": "60 cuadros",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultimos": true,
              "snapshot": false
            }
          },
          {
            "name": "hora",
            "label": "Hora del cuadro (UTC)",
            "kind": "hour",
            "default": 21,
            "options": [],
            "help": "hora UTC, igual que el dataset crudo; Paraguay es UTC-3 (12 UTC = 09:00 local)",
            "min": 0.0,
            "max": 23.0,
            "step": 1.0,
            "enabled_when": {
              "snapshot": true
            }
          },
          {
            "name": "minuto",
            "label": "Minuto",
            "kind": "select",
            "default": "00",
            "options": [
              {
                "value": "00",
                "label": "00",
                "only_when": null
              },
              {
                "value": "10",
                "label": "10",
                "only_when": null
              },
              {
                "value": "20",
                "label": "20",
                "only_when": null
              },
              {
                "value": "30",
                "label": "30",
                "only_when": null
              },
              {
                "value": "40",
                "label": "40",
                "only_when": null
              },
              {
                "value": "50",
                "label": "50",
                "only_when": null
              }
            ],
            "help": "los slots del ABI caen cada 10 minutos",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "snapshot": true
            }
          },
          {
            "name": "resolucion",
            "label": "Resolucion",
            "kind": "select",
            "default": "1400",
            "options": [
              {
                "value": "1400",
                "label": "1400",
                "only_when": null
              },
              {
                "value": "1800",
                "label": "1800",
                "only_when": null
              },
              {
                "value": "2000",
                "label": "2000",
                "only_when": null
              },
              {
                "value": "2400",
                "label": "2400",
                "only_when": null
              },
              {
                "value": "2712",
                "label": "2712",
                "only_when": null
              },
              {
                "value": "3200",
                "label": "3200",
                "only_when": null
              },
              {
                "value": "4000",
                "label": "4000",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "hora_desde",
            "label": "Desde (UTC)",
            "kind": "hour",
            "default": 0,
            "options": [],
            "help": "hora UTC, igual que el dataset crudo; Paraguay es UTC-3 (12 UTC = 09:00 local)",
            "min": 0.0,
            "max": 23.0,
            "step": 1.0,
            "enabled_when": {
              "ultimos": false,
              "snapshot": false
            }
          },
          {
            "name": "hora_hasta",
            "label": "Hasta (UTC)",
            "kind": "hour",
            "default": 24,
            "options": [],
            "help": "fin exclusivo: 24 cierra el día UTC completo",
            "min": 1.0,
            "max": 24.0,
            "step": 1.0,
            "enabled_when": {
              "ultimos": false,
              "snapshot": false
            }
          },
          {
            "name": "animar",
            "label": "Animar",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultimos": false,
              "snapshot": false
            }
          },
          {
            "name": "fps",
            "label": "Cuadros por segundo",
            "kind": "slider",
            "default": 8,
            "options": [],
            "help": "",
            "min": 4.0,
            "max": 30.0,
            "step": 2.0,
            "enabled_when": {
              "snapshot": false
            }
          }
        ],
        "preview": "/previews/geocolor.webp",
        "previews": [
          {
            "url": "/previews/geocolor--G18--false.webp",
            "when": {
              "satelite": "G18",
              "paraguay": "false"
            }
          },
          {
            "url": "/previews/geocolor--G19--false.webp",
            "when": {
              "satelite": "G19",
              "paraguay": "false"
            }
          },
          {
            "url": "/previews/geocolor--G19--true.webp",
            "when": {
              "satelite": "G19",
              "paraguay": "true"
            }
          }
        ],
        "command_ready": true,
        "command": null
      },
      {
        "id": "goes_truecolor",
        "name": "GOES - color real (3 bandas)",
        "group": "satelite",
        "stage": "descargar/truecolor_goes.py + prototipos/poster_goes_truecolor.py",
        "summary": "C01 + C02 + C03 sintetizadas con la receta CIMSS: color real de dia. Globo orthographic o disco nativo sin reproyectar.",
        "params": [
          {
            "name": "snapshot",
            "label": "Snapshot",
            "kind": "toggle",
            "default": true,
            "options": [],
            "help": "un solo cuadro: no arma serie ni animación, y usa el cuadro de siempre",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "satelite",
            "label": "Satelite",
            "kind": "select",
            "default": "G19",
            "options": [
              {
                "value": "G19",
                "label": "GOES-East G19 (75.2 W)",
                "only_when": null
              },
              {
                "value": "G18",
                "label": "GOES-West G18 (137.2 W)",
                "only_when": null
              },
              {
                "value": "G16",
                "label": "GOES-East G16 (hasta 2025)",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "encuadre",
            "label": "Encuadre",
            "kind": "select",
            "default": "globo",
            "options": [
              {
                "value": "globo",
                "label": "Globo orthographic",
                "only_when": null
              },
              {
                "value": "disco",
                "label": "Disco nativo (sin reproyectar)",
                "only_when": null
              }
            ],
            "help": "el disco nativo es la perspectiva geoestacionaria real, sin perder el limbo",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "limbo",
            "label": "Limbo",
            "kind": "select",
            "default": "completo",
            "options": [
              {
                "value": "completo",
                "label": "Completo: todo el disco captado",
                "only_when": null
              },
              {
                "value": "recortado",
                "label": "Recortado: sin la franja estirada",
                "only_when": null
              }
            ],
            "help": "el script recorta por defecto hasta 73.3 grados; el limite real del satelite es 81.3",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "nitidez",
            "label": "Nitidez",
            "kind": "select",
            "default": "maxima",
            "options": [
              {
                "value": "maxima",
                "label": "Maxima: sin mediana ni desenfoque",
                "only_when": null
              },
              {
                "value": "suave",
                "label": "Suave: mediana 3x3 y desenfoque 0.8 px",
                "only_when": null
              }
            ],
            "help": "el suavizado limpia el moteado del limbo pero borronea las nubes",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "ventana",
            "label": "Ventana temporal",
            "kind": "date-range",
            "default": {
              "start": "2026-11-03",
              "end": "2026-11-04"
            },
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultimos": false
            }
          },
          {
            "name": "hora",
            "label": "Hora del cuadro (UTC)",
            "kind": "hour",
            "default": 19,
            "options": [],
            "help": "hora UTC, igual que el dataset crudo; Paraguay es UTC-3 (12 UTC = 09:00 local)",
            "min": 0.0,
            "max": 23.0,
            "step": 1.0,
            "enabled_when": {
              "snapshot": true
            }
          },
          {
            "name": "minuto",
            "label": "Minuto",
            "kind": "select",
            "default": "00",
            "options": [
              {
                "value": "00",
                "label": "00",
                "only_when": null
              },
              {
                "value": "10",
                "label": "10",
                "only_when": null
              },
              {
                "value": "20",
                "label": "20",
                "only_when": null
              },
              {
                "value": "30",
                "label": "30",
                "only_when": null
              },
              {
                "value": "40",
                "label": "40",
                "only_when": null
              },
              {
                "value": "50",
                "label": "50",
                "only_when": null
              }
            ],
            "help": "los slots del ABI caen cada 10 minutos",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "snapshot": true
            }
          },
          {
            "name": "resolucion",
            "label": "Resolucion",
            "kind": "select",
            "default": "1400",
            "options": [
              {
                "value": "1400",
                "label": "1400",
                "only_when": null
              },
              {
                "value": "1800",
                "label": "1800",
                "only_when": null
              },
              {
                "value": "2000",
                "label": "2000",
                "only_when": null
              },
              {
                "value": "2400",
                "label": "2400",
                "only_when": null
              },
              {
                "value": "2712",
                "label": "2712",
                "only_when": null
              },
              {
                "value": "3200",
                "label": "3200",
                "only_when": null
              },
              {
                "value": "4000",
                "label": "4000",
                "only_when": null
              }
            ],
            "help": "2712 px es la resolucion del disco nativo: por debajo se pierde detalle",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "hora_desde",
            "label": "Desde (UTC)",
            "kind": "hour",
            "default": 0,
            "options": [],
            "help": "hora UTC, igual que el dataset crudo; Paraguay es UTC-3 (12 UTC = 09:00 local)",
            "min": 0.0,
            "max": 23.0,
            "step": 1.0,
            "enabled_when": {
              "ultimos": false,
              "snapshot": false
            }
          },
          {
            "name": "hora_hasta",
            "label": "Hasta (UTC)",
            "kind": "hour",
            "default": 24,
            "options": [],
            "help": "fin exclusivo: 24 cierra el día UTC completo",
            "min": 1.0,
            "max": 24.0,
            "step": 1.0,
            "enabled_when": {
              "ultimos": false,
              "snapshot": false
            }
          },
          {
            "name": "animar",
            "label": "Animar",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultimos": false,
              "snapshot": false
            }
          },
          {
            "name": "fps",
            "label": "Cuadros por segundo",
            "kind": "slider",
            "default": 8,
            "options": [],
            "help": "",
            "min": 4.0,
            "max": 30.0,
            "step": 2.0,
            "enabled_when": {
              "snapshot": false
            }
          }
        ],
        "preview": "/previews/goes_truecolor.webp",
        "previews": [
          {
            "url": "/previews/goes_truecolor--G16--disco--completo.webp",
            "when": {
              "satelite": "G16",
              "encuadre": "disco",
              "limbo": "completo"
            }
          },
          {
            "url": "/previews/goes_truecolor--G16--disco--recortado.webp",
            "when": {
              "satelite": "G16",
              "encuadre": "disco",
              "limbo": "recortado"
            }
          },
          {
            "url": "/previews/goes_truecolor--G16--globo--completo.webp",
            "when": {
              "satelite": "G16",
              "encuadre": "globo",
              "limbo": "completo"
            }
          },
          {
            "url": "/previews/goes_truecolor--G16--globo--recortado.webp",
            "when": {
              "satelite": "G16",
              "encuadre": "globo",
              "limbo": "recortado"
            }
          },
          {
            "url": "/previews/goes_truecolor--G18--disco--completo.webp",
            "when": {
              "satelite": "G18",
              "encuadre": "disco",
              "limbo": "completo"
            }
          },
          {
            "url": "/previews/goes_truecolor--G18--disco--recortado.webp",
            "when": {
              "satelite": "G18",
              "encuadre": "disco",
              "limbo": "recortado"
            }
          },
          {
            "url": "/previews/goes_truecolor--G18--globo--completo.webp",
            "when": {
              "satelite": "G18",
              "encuadre": "globo",
              "limbo": "completo"
            }
          },
          {
            "url": "/previews/goes_truecolor--G18--globo--recortado.webp",
            "when": {
              "satelite": "G18",
              "encuadre": "globo",
              "limbo": "recortado"
            }
          },
          {
            "url": "/previews/goes_truecolor--G19--disco--completo.webp",
            "when": {
              "satelite": "G19",
              "encuadre": "disco",
              "limbo": "completo"
            }
          },
          {
            "url": "/previews/goes_truecolor--G19--disco--recortado.webp",
            "when": {
              "satelite": "G19",
              "encuadre": "disco",
              "limbo": "recortado"
            }
          },
          {
            "url": "/previews/goes_truecolor--G19--globo--completo.webp",
            "when": {
              "satelite": "G19",
              "encuadre": "globo",
              "limbo": "completo"
            }
          },
          {
            "url": "/previews/goes_truecolor--G19--globo--recortado.webp",
            "when": {
              "satelite": "G19",
              "encuadre": "globo",
              "limbo": "recortado"
            }
          }
        ],
        "command_ready": true,
        "command": null
      },
      {
        "id": "goes_dust",
        "name": "GOES - Dust RGB",
        "group": "satelite",
        "stage": "descargar/descargar_goes_rgb.py + prototipos/poster_goes_rgb.py",
        "summary": "RGB oficial de tres canales (C15-C13 · C14-C11 · C13). Polvo en magenta/rosa (de noche, violeta bajo 3 km); nubes de agua violeta claro; desierto de día celeste; nubes medias gruesas tan; finas verdes; frías gruesas rojas; cirrus finos negros.",
        "params": [
          {
            "name": "snapshot",
            "label": "Snapshot",
            "kind": "toggle",
            "default": true,
            "options": [],
            "help": "un solo cuadro: no arma serie ni animación, y usa el cuadro de siempre",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "satelite",
            "label": "Satelite",
            "kind": "select",
            "default": "G19",
            "options": [
              {
                "value": "G19",
                "label": "GOES-East G19 (75.2 W)",
                "only_when": null
              },
              {
                "value": "G18",
                "label": "GOES-West G18 (137.2 W)",
                "only_when": null
              },
              {
                "value": "G16",
                "label": "GOES-East G16 (hasta 2025)",
                "only_when": null
              }
            ],
            "help": "define la carpeta de datos goes_<banda>_<sat>",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "ventana",
            "label": "Ventana temporal",
            "kind": "date-range",
            "default": {
              "start": "2026-11-03",
              "end": "2026-11-04"
            },
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultimos": false
            }
          },
          {
            "name": "ultimos",
            "label": "Últimos datos",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "ignora la ventana de fechas: baja y anima los cuadros más nuevos publicados",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "snapshot": false
            }
          },
          {
            "name": "ultimos_n",
            "label": "Cuántos cuadros",
            "kind": "select",
            "default": "24",
            "options": [
              {
                "value": "10",
                "label": "10 cuadros",
                "only_when": null
              },
              {
                "value": "12",
                "label": "12 cuadros",
                "only_when": null
              },
              {
                "value": "24",
                "label": "24 cuadros",
                "only_when": null
              },
              {
                "value": "36",
                "label": "36 cuadros",
                "only_when": null
              },
              {
                "value": "48",
                "label": "48 cuadros",
                "only_when": null
              },
              {
                "value": "60",
                "label": "60 cuadros",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultimos": true,
              "snapshot": false
            }
          },
          {
            "name": "hora",
            "label": "Hora del cuadro (UTC)",
            "kind": "hour",
            "default": 20,
            "options": [],
            "help": "hora UTC, igual que el dataset crudo; Paraguay es UTC-3 (12 UTC = 09:00 local)",
            "min": 0.0,
            "max": 23.0,
            "step": 1.0,
            "enabled_when": {
              "snapshot": true
            }
          },
          {
            "name": "minuto",
            "label": "Minuto",
            "kind": "select",
            "default": "10",
            "options": [
              {
                "value": "00",
                "label": "00",
                "only_when": null
              },
              {
                "value": "10",
                "label": "10",
                "only_when": null
              },
              {
                "value": "20",
                "label": "20",
                "only_when": null
              },
              {
                "value": "30",
                "label": "30",
                "only_when": null
              },
              {
                "value": "40",
                "label": "40",
                "only_when": null
              },
              {
                "value": "50",
                "label": "50",
                "only_when": null
              }
            ],
            "help": "los slots del ABI caen cada 10 minutos",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "snapshot": true
            }
          },
          {
            "name": "resolucion",
            "label": "Resolucion",
            "kind": "select",
            "default": "2712",
            "options": [
              {
                "value": "1400",
                "label": "1400",
                "only_when": null
              },
              {
                "value": "1800",
                "label": "1800",
                "only_when": null
              },
              {
                "value": "2000",
                "label": "2000",
                "only_when": null
              },
              {
                "value": "2400",
                "label": "2400",
                "only_when": null
              },
              {
                "value": "2712",
                "label": "2712",
                "only_when": null
              },
              {
                "value": "3200",
                "label": "3200",
                "only_when": null
              },
              {
                "value": "4000",
                "label": "4000",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "hora_desde",
            "label": "Desde (UTC)",
            "kind": "hour",
            "default": 0,
            "options": [],
            "help": "hora UTC, igual que el dataset crudo; Paraguay es UTC-3 (12 UTC = 09:00 local)",
            "min": 0.0,
            "max": 23.0,
            "step": 1.0,
            "enabled_when": {
              "ultimos": false,
              "snapshot": false
            }
          },
          {
            "name": "hora_hasta",
            "label": "Hasta (UTC)",
            "kind": "hour",
            "default": 24,
            "options": [],
            "help": "fin exclusivo: 24 cierra el día UTC completo",
            "min": 1.0,
            "max": 24.0,
            "step": 1.0,
            "enabled_when": {
              "ultimos": false,
              "snapshot": false
            }
          },
          {
            "name": "animar",
            "label": "Animar",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultimos": false,
              "snapshot": false
            }
          },
          {
            "name": "fps",
            "label": "Cuadros por segundo",
            "kind": "slider",
            "default": 12,
            "options": [],
            "help": "",
            "min": 4.0,
            "max": 30.0,
            "step": 2.0,
            "enabled_when": {
              "snapshot": false
            }
          }
        ],
        "preview": "/previews/goes_dust.webp",
        "previews": [
          {
            "url": "/previews/goes_dust--G19--false.webp",
            "when": {
              "satelite": "G19",
              "paraguay": "false"
            }
          },
          {
            "url": "/previews/goes_dust--G19--true.webp",
            "when": {
              "satelite": "G19",
              "paraguay": "true"
            }
          }
        ],
        "command_ready": true,
        "command": null
      },
      {
        "id": "goes_airmass",
        "name": "GOES - Air Mass RGB",
        "group": "satelite",
        "stage": "descargar/descargar_goes_rgb.py + prototipos/poster_goes_rgb.py",
        "summary": "RGB oficial de tres canales (C08-C10 · C12-C13 · C08). Aire polar azul/violeta oscuro; tropical verde; seco y cálido oliva/naranja; nubes altas gruesas blancas; medias tan/salmón; bajas verdes/azul oscuro.",
        "params": [
          {
            "name": "snapshot",
            "label": "Snapshot",
            "kind": "toggle",
            "default": true,
            "options": [],
            "help": "un solo cuadro: no arma serie ni animación, y usa el cuadro de siempre",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "satelite",
            "label": "Satelite",
            "kind": "select",
            "default": "G19",
            "options": [
              {
                "value": "G19",
                "label": "GOES-East G19 (75.2 W)",
                "only_when": null
              },
              {
                "value": "G18",
                "label": "GOES-West G18 (137.2 W)",
                "only_when": null
              },
              {
                "value": "G16",
                "label": "GOES-East G16 (hasta 2025)",
                "only_when": null
              }
            ],
            "help": "define la carpeta de datos goes_<banda>_<sat>",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "ventana",
            "label": "Ventana temporal",
            "kind": "date-range",
            "default": {
              "start": "2026-11-04",
              "end": "2026-11-04"
            },
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultimos": false
            }
          },
          {
            "name": "ultimos",
            "label": "Últimos datos",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "ignora la ventana de fechas: baja y anima los cuadros más nuevos publicados",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "snapshot": false
            }
          },
          {
            "name": "ultimos_n",
            "label": "Cuántos cuadros",
            "kind": "select",
            "default": "24",
            "options": [
              {
                "value": "10",
                "label": "10 cuadros",
                "only_when": null
              },
              {
                "value": "12",
                "label": "12 cuadros",
                "only_when": null
              },
              {
                "value": "24",
                "label": "24 cuadros",
                "only_when": null
              },
              {
                "value": "36",
                "label": "36 cuadros",
                "only_when": null
              },
              {
                "value": "48",
                "label": "48 cuadros",
                "only_when": null
              },
              {
                "value": "60",
                "label": "60 cuadros",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultimos": true,
              "snapshot": false
            }
          },
          {
            "name": "hora",
            "label": "Hora del cuadro (UTC)",
            "kind": "hour",
            "default": 19,
            "options": [],
            "help": "hora UTC, igual que el dataset crudo; Paraguay es UTC-3 (12 UTC = 09:00 local)",
            "min": 0.0,
            "max": 23.0,
            "step": 1.0,
            "enabled_when": {
              "snapshot": true
            }
          },
          {
            "name": "minuto",
            "label": "Minuto",
            "kind": "select",
            "default": "20",
            "options": [
              {
                "value": "00",
                "label": "00",
                "only_when": null
              },
              {
                "value": "10",
                "label": "10",
                "only_when": null
              },
              {
                "value": "20",
                "label": "20",
                "only_when": null
              },
              {
                "value": "30",
                "label": "30",
                "only_when": null
              },
              {
                "value": "40",
                "label": "40",
                "only_when": null
              },
              {
                "value": "50",
                "label": "50",
                "only_when": null
              }
            ],
            "help": "los slots del ABI caen cada 10 minutos",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "snapshot": true
            }
          },
          {
            "name": "resolucion",
            "label": "Resolucion",
            "kind": "select",
            "default": "2712",
            "options": [
              {
                "value": "1400",
                "label": "1400",
                "only_when": null
              },
              {
                "value": "1800",
                "label": "1800",
                "only_when": null
              },
              {
                "value": "2000",
                "label": "2000",
                "only_when": null
              },
              {
                "value": "2400",
                "label": "2400",
                "only_when": null
              },
              {
                "value": "2712",
                "label": "2712",
                "only_when": null
              },
              {
                "value": "3200",
                "label": "3200",
                "only_when": null
              },
              {
                "value": "4000",
                "label": "4000",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "hora_desde",
            "label": "Desde (UTC)",
            "kind": "hour",
            "default": 0,
            "options": [],
            "help": "hora UTC, igual que el dataset crudo; Paraguay es UTC-3 (12 UTC = 09:00 local)",
            "min": 0.0,
            "max": 23.0,
            "step": 1.0,
            "enabled_when": {
              "ultimos": false,
              "snapshot": false
            }
          },
          {
            "name": "hora_hasta",
            "label": "Hasta (UTC)",
            "kind": "hour",
            "default": 24,
            "options": [],
            "help": "fin exclusivo: 24 cierra el día UTC completo",
            "min": 1.0,
            "max": 24.0,
            "step": 1.0,
            "enabled_when": {
              "ultimos": false,
              "snapshot": false
            }
          },
          {
            "name": "animar",
            "label": "Animar",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultimos": false,
              "snapshot": false
            }
          },
          {
            "name": "fps",
            "label": "Cuadros por segundo",
            "kind": "slider",
            "default": 12,
            "options": [],
            "help": "",
            "min": 4.0,
            "max": 30.0,
            "step": 2.0,
            "enabled_when": {
              "snapshot": false
            }
          }
        ],
        "preview": "/previews/goes_airmass.webp",
        "previews": [
          {
            "url": "/previews/goes_airmass--G19--false.webp",
            "when": {
              "satelite": "G19",
              "paraguay": "false"
            }
          },
          {
            "url": "/previews/goes_airmass--G19--true.webp",
            "when": {
              "satelite": "G19",
              "paraguay": "true"
            }
          }
        ],
        "command_ready": true,
        "command": null
      },
      {
        "id": "goes_firetemp",
        "name": "GOES - Fire Temperature RGB",
        "group": "satelite",
        "stage": "descargar/descargar_goes_rgb.py + prototipos/poster_goes_rgb.py",
        "summary": "RGB oficial de tres canales (C07 · C06 · C05). Fuego tibio rojo; muy tibio naranja; caliente amarillo; muy caliente casi blanco; cicatrices de quema marrón; cielo claro púrpura/rosa; agua/nieve/noche casi negro; nubes de agua azules; de hielo verdes.",
        "params": [
          {
            "name": "snapshot",
            "label": "Snapshot",
            "kind": "toggle",
            "default": true,
            "options": [],
            "help": "un solo cuadro: no arma serie ni animación, y usa el cuadro de siempre",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "satelite",
            "label": "Satelite",
            "kind": "select",
            "default": "G19",
            "options": [
              {
                "value": "G19",
                "label": "GOES-East G19 (75.2 W)",
                "only_when": null
              },
              {
                "value": "G18",
                "label": "GOES-West G18 (137.2 W)",
                "only_when": null
              },
              {
                "value": "G16",
                "label": "GOES-East G16 (hasta 2025)",
                "only_when": null
              }
            ],
            "help": "define la carpeta de datos goes_<banda>_<sat>",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "ventana",
            "label": "Ventana temporal",
            "kind": "date-range",
            "default": {
              "start": "2026-11-04",
              "end": "2026-11-04"
            },
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultimos": false
            }
          },
          {
            "name": "ultimos",
            "label": "Últimos datos",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "ignora la ventana de fechas: baja y anima los cuadros más nuevos publicados",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "snapshot": false
            }
          },
          {
            "name": "ultimos_n",
            "label": "Cuántos cuadros",
            "kind": "select",
            "default": "24",
            "options": [
              {
                "value": "10",
                "label": "10 cuadros",
                "only_when": null
              },
              {
                "value": "12",
                "label": "12 cuadros",
                "only_when": null
              },
              {
                "value": "24",
                "label": "24 cuadros",
                "only_when": null
              },
              {
                "value": "36",
                "label": "36 cuadros",
                "only_when": null
              },
              {
                "value": "48",
                "label": "48 cuadros",
                "only_when": null
              },
              {
                "value": "60",
                "label": "60 cuadros",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultimos": true,
              "snapshot": false
            }
          },
          {
            "name": "hora",
            "label": "Hora del cuadro (UTC)",
            "kind": "hour",
            "default": 19,
            "options": [],
            "help": "hora UTC, igual que el dataset crudo; Paraguay es UTC-3 (12 UTC = 09:00 local)",
            "min": 0.0,
            "max": 23.0,
            "step": 1.0,
            "enabled_when": {
              "snapshot": true
            }
          },
          {
            "name": "minuto",
            "label": "Minuto",
            "kind": "select",
            "default": "00",
            "options": [
              {
                "value": "00",
                "label": "00",
                "only_when": null
              },
              {
                "value": "10",
                "label": "10",
                "only_when": null
              },
              {
                "value": "20",
                "label": "20",
                "only_when": null
              },
              {
                "value": "30",
                "label": "30",
                "only_when": null
              },
              {
                "value": "40",
                "label": "40",
                "only_when": null
              },
              {
                "value": "50",
                "label": "50",
                "only_when": null
              }
            ],
            "help": "los slots del ABI caen cada 10 minutos",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "snapshot": true
            }
          },
          {
            "name": "resolucion",
            "label": "Resolucion",
            "kind": "select",
            "default": "2712",
            "options": [
              {
                "value": "1400",
                "label": "1400",
                "only_when": null
              },
              {
                "value": "1800",
                "label": "1800",
                "only_when": null
              },
              {
                "value": "2000",
                "label": "2000",
                "only_when": null
              },
              {
                "value": "2400",
                "label": "2400",
                "only_when": null
              },
              {
                "value": "2712",
                "label": "2712",
                "only_when": null
              },
              {
                "value": "3200",
                "label": "3200",
                "only_when": null
              },
              {
                "value": "4000",
                "label": "4000",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "hora_desde",
            "label": "Desde (UTC)",
            "kind": "hour",
            "default": 0,
            "options": [],
            "help": "hora UTC, igual que el dataset crudo; Paraguay es UTC-3 (12 UTC = 09:00 local)",
            "min": 0.0,
            "max": 23.0,
            "step": 1.0,
            "enabled_when": {
              "ultimos": false,
              "snapshot": false
            }
          },
          {
            "name": "hora_hasta",
            "label": "Hasta (UTC)",
            "kind": "hour",
            "default": 24,
            "options": [],
            "help": "fin exclusivo: 24 cierra el día UTC completo",
            "min": 1.0,
            "max": 24.0,
            "step": 1.0,
            "enabled_when": {
              "ultimos": false,
              "snapshot": false
            }
          },
          {
            "name": "animar",
            "label": "Animar",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultimos": false,
              "snapshot": false
            }
          },
          {
            "name": "fps",
            "label": "Cuadros por segundo",
            "kind": "slider",
            "default": 12,
            "options": [],
            "help": "",
            "min": 4.0,
            "max": 30.0,
            "step": 2.0,
            "enabled_when": {
              "snapshot": false
            }
          }
        ],
        "preview": "/previews/goes_firetemp.webp",
        "previews": [
          {
            "url": "/previews/goes_firetemp--G19--false.webp",
            "when": {
              "satelite": "G19",
              "paraguay": "false"
            }
          },
          {
            "url": "/previews/goes_firetemp--G19--true.webp",
            "when": {
              "satelite": "G19",
              "paraguay": "true"
            }
          }
        ],
        "command_ready": true,
        "command": null
      },
      {
        "id": "goes_sandwich",
        "name": "GOES - Sandwich (visible + IR realzado)",
        "group": "satelite",
        "stage": "descargar/descargar_goes.py + prototipos/poster_goes_sandwich.py",
        "summary": "Mezcla el visible (C02, 0.64 um) con el IR ventana (C13, 10.3 um) realzado en color: morfologia y temperatura del tope nuboso en una imagen. Producto de dia.",
        "params": [
          {
            "name": "snapshot",
            "label": "Snapshot",
            "kind": "toggle",
            "default": true,
            "options": [],
            "help": "un solo cuadro: no arma serie ni animación, y usa el cuadro de siempre",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "paraguay",
            "label": "Solo Paraguay",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "encuadra la captura o la animación en las coordenadas de Paraguay",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "margen",
            "label": "Margen Paraguay (%)",
            "kind": "slider",
            "default": 6,
            "options": [],
            "help": "aire alrededor del país dentro del encuadre",
            "min": 0.0,
            "max": 20.0,
            "step": 1.0,
            "enabled_when": {
              "paraguay": true
            }
          },
          {
            "name": "satelite",
            "label": "Satelite",
            "kind": "select",
            "default": "G19",
            "options": [
              {
                "value": "G19",
                "label": "GOES-East G19 (75.2 W)",
                "only_when": null
              },
              {
                "value": "G18",
                "label": "GOES-West G18 (137.2 W)",
                "only_when": null
              },
              {
                "value": "G16",
                "label": "GOES-East G16 (hasta 2025)",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "alpha",
            "label": "Mezcla visible / IR",
            "kind": "slider",
            "default": 0.5,
            "options": [],
            "help": "1 = solo visible; 0 = solo IR realzado; 0.5 es el clasico",
            "min": 0.0,
            "max": 1.0,
            "step": 0.05,
            "enabled_when": null
          },
          {
            "name": "ventana",
            "label": "Ventana temporal",
            "kind": "date-range",
            "default": {
              "start": "2026-11-07",
              "end": "2026-11-08"
            },
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultimos": false
            }
          },
          {
            "name": "ultimos",
            "label": "Últimos datos",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "ignora la ventana de fechas: baja y anima los cuadros más nuevos publicados",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "snapshot": false
            }
          },
          {
            "name": "ultimos_n",
            "label": "Cuántos cuadros",
            "kind": "select",
            "default": "24",
            "options": [
              {
                "value": "10",
                "label": "10 cuadros",
                "only_when": null
              },
              {
                "value": "12",
                "label": "12 cuadros",
                "only_when": null
              },
              {
                "value": "24",
                "label": "24 cuadros",
                "only_when": null
              },
              {
                "value": "36",
                "label": "36 cuadros",
                "only_when": null
              },
              {
                "value": "48",
                "label": "48 cuadros",
                "only_when": null
              },
              {
                "value": "60",
                "label": "60 cuadros",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultimos": true,
              "snapshot": false
            }
          },
          {
            "name": "hora",
            "label": "Hora del cuadro (UTC)",
            "kind": "hour",
            "default": 15,
            "options": [],
            "help": "hora UTC, igual que el dataset crudo; Paraguay es UTC-3 (12 UTC = 09:00 local)",
            "min": 0.0,
            "max": 23.0,
            "step": 1.0,
            "enabled_when": {
              "snapshot": true
            }
          },
          {
            "name": "minuto",
            "label": "Minuto",
            "kind": "select",
            "default": "00",
            "options": [
              {
                "value": "00",
                "label": "00",
                "only_when": null
              },
              {
                "value": "10",
                "label": "10",
                "only_when": null
              },
              {
                "value": "20",
                "label": "20",
                "only_when": null
              },
              {
                "value": "30",
                "label": "30",
                "only_when": null
              },
              {
                "value": "40",
                "label": "40",
                "only_when": null
              },
              {
                "value": "50",
                "label": "50",
                "only_when": null
              }
            ],
            "help": "los slots del ABI caen cada 10 minutos",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "snapshot": true
            }
          },
          {
            "name": "resolucion",
            "label": "Resolucion",
            "kind": "select",
            "default": "2712",
            "options": [
              {
                "value": "1400",
                "label": "1400",
                "only_when": null
              },
              {
                "value": "1800",
                "label": "1800",
                "only_when": null
              },
              {
                "value": "2000",
                "label": "2000",
                "only_when": null
              },
              {
                "value": "2400",
                "label": "2400",
                "only_when": null
              },
              {
                "value": "2712",
                "label": "2712",
                "only_when": null
              },
              {
                "value": "3200",
                "label": "3200",
                "only_when": null
              },
              {
                "value": "4000",
                "label": "4000",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "hora_desde",
            "label": "Desde (UTC)",
            "kind": "hour",
            "default": 0,
            "options": [],
            "help": "hora UTC, igual que el dataset crudo; Paraguay es UTC-3 (12 UTC = 09:00 local)",
            "min": 0.0,
            "max": 23.0,
            "step": 1.0,
            "enabled_when": {
              "ultimos": false,
              "snapshot": false
            }
          },
          {
            "name": "hora_hasta",
            "label": "Hasta (UTC)",
            "kind": "hour",
            "default": 24,
            "options": [],
            "help": "fin exclusivo: 24 cierra el dia UTC completo",
            "min": 1.0,
            "max": 24.0,
            "step": 1.0,
            "enabled_when": {
              "ultimos": false,
              "snapshot": false
            }
          },
          {
            "name": "animar",
            "label": "Animar",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultimos": false,
              "snapshot": false
            }
          },
          {
            "name": "fps",
            "label": "Cuadros por segundo",
            "kind": "slider",
            "default": 8,
            "options": [],
            "help": "",
            "min": 4.0,
            "max": 30.0,
            "step": 2.0,
            "enabled_when": {
              "snapshot": false
            }
          }
        ],
        "preview": "/previews/goes_sandwich.webp",
        "previews": [],
        "command_ready": true,
        "command": null
      },
      {
        "id": "snapshot_paraguay",
        "name": "Snapshot - Paraguay",
        "group": "satelite",
        "stage": "descargar/snapshot_paraguay.py + cuadros/snapshot_paraguay.py",
        "summary": "Una sola captura recortada a los bordes de Paraguay, sin rotulos. VIIRS a 250 m de dia, o GeoColor de dia y noche.",
        "params": [
          {
            "name": "capa",
            "label": "Capa",
            "kind": "select",
            "default": "geocolor",
            "options": [
              {
                "value": "truecolor",
                "label": "NOAA-20 / VIIRS (250 m)",
                "only_when": null
              },
              {
                "value": "snpp",
                "label": "Suomi NPP / VIIRS (250 m)",
                "only_when": null
              },
              {
                "value": "aqua",
                "label": "Aqua / MODIS (250 m)",
                "only_when": null
              },
              {
                "value": "terra",
                "label": "Terra / MODIS (250 m)",
                "only_when": null
              },
              {
                "value": "geocolor",
                "label": "GOES-19 GeoColor (dia y noche, ~2 km)",
                "only_when": null
              }
            ],
            "help": "los cuatro True Color son diarios y de 250 m; GeoColor llega a 2 km",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "ultima",
            "label": "Ultima disponible",
            "kind": "toggle",
            "default": true,
            "options": [],
            "help": "resuelve el granulo mas nuevo; ignora fecha, hora y minuto",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "fecha",
            "label": "Fecha de la captura",
            "kind": "date",
            "default": "2026-11-04",
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultima": false
            }
          },
          {
            "name": "hora",
            "label": "Hora UTC",
            "kind": "hour",
            "default": 15,
            "options": [],
            "help": "15z es el mediodia en Paraguay; de noche se ve el IR",
            "min": 0.0,
            "max": 23.0,
            "step": 1.0,
            "enabled_when": {
              "ultima": false
            }
          },
          {
            "name": "minuto",
            "label": "Minuto",
            "kind": "select",
            "default": "00",
            "options": [
              {
                "value": "00",
                "label": "00",
                "only_when": null
              },
              {
                "value": "10",
                "label": "10",
                "only_when": null
              },
              {
                "value": "20",
                "label": "20",
                "only_when": null
              },
              {
                "value": "30",
                "label": "30",
                "only_when": null
              },
              {
                "value": "40",
                "label": "40",
                "only_when": null
              },
              {
                "value": "50",
                "label": "50",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "ultima": false
            }
          },
          {
            "name": "margen",
            "label": "Margen (%)",
            "kind": "slider",
            "default": 0,
            "options": [],
            "help": "aire alrededor del pais dentro del encuadre",
            "min": 0.0,
            "max": 20.0,
            "step": 1.0,
            "enabled_when": null
          },
          {
            "name": "detalle",
            "label": "Detalle (m/px)",
            "kind": "select",
            "default": "250",
            "options": [
              {
                "value": "125",
                "label": "125 m/px",
                "only_when": null
              },
              {
                "value": "250",
                "label": "250 m/px",
                "only_when": null
              },
              {
                "value": "500",
                "label": "500 m/px",
                "only_when": null
              },
              {
                "value": "1000",
                "label": "1000 m/px",
                "only_when": null
              },
              {
                "value": "2000",
                "label": "2000 m/px",
                "only_when": null
              }
            ],
            "help": "250 m/px es el detalle real de VIIRS; por debajo solo interpola",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "borde",
            "label": "Dibujar el contorno",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          }
        ],
        "preview": "/previews/snapshot_paraguay.webp",
        "previews": [
          {
            "url": "/previews/snapshot_paraguay--aqua.webp",
            "when": {
              "capa": "aqua"
            }
          },
          {
            "url": "/previews/snapshot_paraguay--geocolor.webp",
            "when": {
              "capa": "geocolor"
            }
          },
          {
            "url": "/previews/snapshot_paraguay--snpp.webp",
            "when": {
              "capa": "snpp"
            }
          },
          {
            "url": "/previews/snapshot_paraguay--terra.webp",
            "when": {
              "capa": "terra"
            }
          }
        ],
        "command_ready": true,
        "command": null
      },
      {
        "id": "anomalia_2t",
        "name": "ECMWF - anomalia de 2 m",
        "group": "modelo",
        "stage": "descargar/anomalia_2t_ecmwf.py + cuadros/cuadros_anomalia_2t.py",
        "summary": "Anomalia de temperatura a 2 m contra la climatologia horaria de ERA5.",
        "params": [
          {
            "name": "snapshot",
            "label": "Snapshot",
            "kind": "toggle",
            "default": true,
            "options": [],
            "help": "un solo cuadro: no arma serie ni animación, y usa el cuadro de siempre",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "paraguay",
            "label": "Solo Paraguay",
            "kind": "toggle",
            "default": true,
            "options": [],
            "help": "encuadra la captura o la animación en las coordenadas de Paraguay",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "margen",
            "label": "Margen Paraguay (%)",
            "kind": "slider",
            "default": 6,
            "options": [],
            "help": "aire alrededor del país dentro del encuadre",
            "min": 0.0,
            "max": 20.0,
            "step": 1.0,
            "enabled_when": {
              "paraguay": true
            }
          },
          {
            "name": "modelo",
            "label": "Modelo",
            "kind": "select",
            "default": "ifs",
            "options": [
              {
                "value": "ifs",
                "label": "IFS deterministico",
                "only_when": null
              },
              {
                "value": "aifs-single",
                "label": "AIFS single",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "fecha",
            "label": "Fecha de la corrida",
            "kind": "date",
            "default": "2026-11-05",
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "corrida",
            "label": "Ciclo",
            "kind": "select",
            "default": "00",
            "options": [
              {
                "value": "00",
                "label": "00z",
                "only_when": null
              },
              {
                "value": "06",
                "label": "06z",
                "only_when": null
              },
              {
                "value": "12",
                "label": "12z",
                "only_when": null
              },
              {
                "value": "18",
                "label": "18z",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "horizonte",
            "label": "Horizonte (h)",
            "kind": "slider",
            "default": 12,
            "options": [],
            "help": "los pasos de 3 h llegan hasta 144 h",
            "min": 6.0,
            "max": 144.0,
            "step": 6.0,
            "enabled_when": null
          },
          {
            "name": "fondo",
            "label": "Fondo del globo",
            "kind": "select",
            "default": "claro",
            "options": [
              {
                "value": "oscuro",
                "label": "Fondo oscuro",
                "only_when": null
              },
              {
                "value": "claro",
                "label": "Fondo claro",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "resolucion",
            "label": "Resolucion",
            "kind": "select",
            "default": "1400",
            "options": [
              {
                "value": "1400",
                "label": "1400",
                "only_when": null
              },
              {
                "value": "1800",
                "label": "1800",
                "only_when": null
              },
              {
                "value": "2000",
                "label": "2000",
                "only_when": null
              },
              {
                "value": "2400",
                "label": "2400",
                "only_when": null
              },
              {
                "value": "2712",
                "label": "2712",
                "only_when": null
              },
              {
                "value": "3200",
                "label": "3200",
                "only_when": null
              },
              {
                "value": "4000",
                "label": "4000",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "animar",
            "label": "Animar",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "snapshot": false
            }
          },
          {
            "name": "fps",
            "label": "Cuadros por segundo",
            "kind": "slider",
            "default": 12,
            "options": [],
            "help": "",
            "min": 4.0,
            "max": 30.0,
            "step": 2.0,
            "enabled_when": {
              "snapshot": false
            }
          }
        ],
        "preview": "/previews/anomalia_2t.webp",
        "previews": [
          {
            "url": "/previews/anomalia_2t--aifs-single--false.webp",
            "when": {
              "modelo": "aifs-single",
              "paraguay": "false"
            }
          },
          {
            "url": "/previews/anomalia_2t--ifs--false.webp",
            "when": {
              "modelo": "ifs",
              "paraguay": "false"
            }
          },
          {
            "url": "/previews/anomalia_2t--ifs--true.webp",
            "when": {
              "modelo": "ifs",
              "paraguay": "true"
            }
          }
        ],
        "command_ready": true,
        "command": null
      },
      {
        "id": "viento_250",
        "name": "Viento en 250 mb",
        "group": "modelo",
        "stage": "descargar/viento_250_mslp.py + cuadros/cuadros_viento_250.py",
        "summary": "Velocidad del viento en 250 mb (kt) con streamlines y extremos de presion a nivel del mar sobre globo.",
        "params": [
          {
            "name": "snapshot",
            "label": "Snapshot",
            "kind": "toggle",
            "default": true,
            "options": [],
            "help": "un solo cuadro: no arma serie ni animación, y usa el cuadro de siempre",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "paraguay",
            "label": "Solo Paraguay",
            "kind": "toggle",
            "default": true,
            "options": [],
            "help": "encuadra la captura o la animación en las coordenadas de Paraguay",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "margen",
            "label": "Margen Paraguay (%)",
            "kind": "slider",
            "default": 6,
            "options": [],
            "help": "aire alrededor del país dentro del encuadre",
            "min": 0.0,
            "max": 20.0,
            "step": 1.0,
            "enabled_when": {
              "paraguay": true
            }
          },
          {
            "name": "modelo",
            "label": "Modelo",
            "kind": "select",
            "default": "gfs",
            "options": [
              {
                "value": "ifs",
                "label": "ECMWF IFS 0.25",
                "only_when": null
              },
              {
                "value": "gfs",
                "label": "GFS 0.25 (NOAA)",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "fecha",
            "label": "Fecha de la corrida",
            "kind": "date",
            "default": "2026-11-04",
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "corrida",
            "label": "Ciclo",
            "kind": "select",
            "default": "00",
            "options": [
              {
                "value": "00",
                "label": "00z",
                "only_when": null
              },
              {
                "value": "06",
                "label": "06z",
                "only_when": null
              },
              {
                "value": "12",
                "label": "12z",
                "only_when": null
              },
              {
                "value": "18",
                "label": "18z",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "horizonte",
            "label": "Horizonte (h)",
            "kind": "slider",
            "default": 144,
            "options": [],
            "help": "los pasos de 3 h llegan hasta 144 h",
            "min": 6.0,
            "max": 144.0,
            "step": 6.0,
            "enabled_when": null
          },
          {
            "name": "fondo",
            "label": "Fondo del globo",
            "kind": "select",
            "default": "oscuro",
            "options": [
              {
                "value": "oscuro",
                "label": "Fondo oscuro",
                "only_when": null
              },
              {
                "value": "claro",
                "label": "Fondo claro",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "resolucion",
            "label": "Resolucion",
            "kind": "select",
            "default": "1400",
            "options": [
              {
                "value": "1400",
                "label": "1400",
                "only_when": null
              },
              {
                "value": "1800",
                "label": "1800",
                "only_when": null
              },
              {
                "value": "2000",
                "label": "2000",
                "only_when": null
              },
              {
                "value": "2400",
                "label": "2400",
                "only_when": null
              },
              {
                "value": "2712",
                "label": "2712",
                "only_when": null
              },
              {
                "value": "3200",
                "label": "3200",
                "only_when": null
              },
              {
                "value": "4000",
                "label": "4000",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "animar",
            "label": "Animar",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "snapshot": false
            }
          },
          {
            "name": "fps",
            "label": "Cuadros por segundo",
            "kind": "slider",
            "default": 12,
            "options": [],
            "help": "",
            "min": 4.0,
            "max": 30.0,
            "step": 2.0,
            "enabled_when": {
              "snapshot": false
            }
          }
        ],
        "preview": "/previews/viento_250.webp",
        "previews": [
          {
            "url": "/previews/viento_250--gfs--false.webp",
            "when": {
              "modelo": "gfs",
              "paraguay": "false"
            }
          },
          {
            "url": "/previews/viento_250--ifs--false.webp",
            "when": {
              "modelo": "ifs",
              "paraguay": "false"
            }
          },
          {
            "url": "/previews/viento_250--ifs--true.webp",
            "when": {
              "modelo": "ifs",
              "paraguay": "true"
            }
          }
        ],
        "command_ready": true,
        "command": null
      },
      {
        "id": "mur_sst",
        "name": "MUR - temperatura del mar",
        "group": "satelite",
        "stage": "descargar/mur_sst.py + cuadros/cuadros_mur.py",
        "summary": "SST diaria de 1 km: GIBS entrega el cuadro ya coloreado y aca se compone el globo.",
        "params": [
          {
            "name": "snapshot",
            "label": "Snapshot",
            "kind": "toggle",
            "default": true,
            "options": [],
            "help": "un solo cuadro: no arma serie ni animación, y usa el cuadro de siempre",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "ventana",
            "label": "Ventana temporal",
            "kind": "date-range",
            "default": {
              "start": "2026-11-04",
              "end": "2026-11-04"
            },
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "resolucion",
            "label": "Resolucion",
            "kind": "select",
            "default": "1400",
            "options": [
              {
                "value": "1400",
                "label": "1400",
                "only_when": null
              },
              {
                "value": "1800",
                "label": "1800",
                "only_when": null
              },
              {
                "value": "2000",
                "label": "2000",
                "only_when": null
              },
              {
                "value": "2400",
                "label": "2400",
                "only_when": null
              },
              {
                "value": "2712",
                "label": "2712",
                "only_when": null
              },
              {
                "value": "3200",
                "label": "3200",
                "only_when": null
              },
              {
                "value": "4000",
                "label": "4000",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "animar",
            "label": "Animar",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "snapshot": false
            }
          },
          {
            "name": "fps",
            "label": "Cuadros por segundo",
            "kind": "slider",
            "default": 12,
            "options": [],
            "help": "",
            "min": 4.0,
            "max": 30.0,
            "step": 2.0,
            "enabled_when": {
              "snapshot": false
            }
          }
        ],
        "preview": "/previews/mur_sst.webp",
        "previews": [],
        "command_ready": true,
        "command": null
      },
      {
        "id": "mur_realista",
        "name": "MUR - SST poster realista",
        "group": "satelite",
        "stage": "descargar/mur_sst.py + prototipos/poster_mur_realista.py",
        "summary": "Fondo blanco, globo inscripto y campana de distribucion: el diseno de poster del repo, no el globo oscuro.",
        "params": [
          {
            "name": "snapshot",
            "label": "Snapshot",
            "kind": "toggle",
            "default": true,
            "options": [],
            "help": "un solo cuadro: no arma serie ni animación, y usa el cuadro de siempre",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "ventana",
            "label": "Ventana temporal",
            "kind": "date-range",
            "default": {
              "start": "2026-11-04",
              "end": "2026-11-04"
            },
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "resolucion",
            "label": "Resolucion",
            "kind": "select",
            "default": "1400",
            "options": [
              {
                "value": "1400",
                "label": "1400",
                "only_when": null
              },
              {
                "value": "1800",
                "label": "1800",
                "only_when": null
              },
              {
                "value": "2000",
                "label": "2000",
                "only_when": null
              },
              {
                "value": "2400",
                "label": "2400",
                "only_when": null
              },
              {
                "value": "2712",
                "label": "2712",
                "only_when": null
              },
              {
                "value": "3200",
                "label": "3200",
                "only_when": null
              },
              {
                "value": "4000",
                "label": "4000",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "paleta",
            "label": "Paleta",
            "kind": "select",
            "default": "realista",
            "options": [
              {
                "value": "realista",
                "label": "realista (Earth Observatory)",
                "only_when": null
              },
              {
                "value": "gibs",
                "label": "gibs (SST oficial)",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "trend",
            "label": "Mostrar tendencia",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          }
        ],
        "preview": "/previews/mur_realista.webp",
        "previews": [],
        "command_ready": true,
        "command": null
      },
      {
        "id": "precipitacion_ecmwf",
        "name": "ECMWF - precipitacion",
        "group": "modelo",
        "stage": "descargar/precipitacion_ecmwf.py + cuadros/cuadros_precipitacion.py",
        "summary": "Precipitacion acumulada por horizonte de 6 h sobre globo.",
        "params": [
          {
            "name": "snapshot",
            "label": "Snapshot",
            "kind": "toggle",
            "default": true,
            "options": [],
            "help": "un solo cuadro: no arma serie ni animación, y usa el cuadro de siempre",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "paraguay",
            "label": "Solo Paraguay",
            "kind": "toggle",
            "default": true,
            "options": [],
            "help": "encuadra la captura o la animación en las coordenadas de Paraguay",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "margen",
            "label": "Margen Paraguay (%)",
            "kind": "slider",
            "default": 15,
            "options": [],
            "help": "aire alrededor del país dentro del encuadre",
            "min": 0.0,
            "max": 20.0,
            "step": 1.0,
            "enabled_when": {
              "paraguay": true
            }
          },
          {
            "name": "modelo",
            "label": "Modelo",
            "kind": "select",
            "default": "ifs",
            "options": [
              {
                "value": "ifs",
                "label": "IFS deterministico",
                "only_when": null
              },
              {
                "value": "aifs-ens",
                "label": "AIFS ensemble",
                "only_when": null
              },
              {
                "value": "aifs-single",
                "label": "AIFS single",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "fecha",
            "label": "Fecha de la corrida",
            "kind": "date",
            "default": "2026-11-06",
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "corrida",
            "label": "Ciclo",
            "kind": "select",
            "default": "00",
            "options": [
              {
                "value": "00",
                "label": "00z",
                "only_when": null
              },
              {
                "value": "06",
                "label": "06z",
                "only_when": null
              },
              {
                "value": "12",
                "label": "12z",
                "only_when": null
              },
              {
                "value": "18",
                "label": "18z",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "horizonte",
            "label": "Horizonte (h)",
            "kind": "slider",
            "default": 144,
            "options": [],
            "help": "los pasos de 3 h llegan hasta 144 h",
            "min": 6.0,
            "max": 144.0,
            "step": 6.0,
            "enabled_when": null
          },
          {
            "name": "fondo",
            "label": "Fondo del globo",
            "kind": "select",
            "default": "claro",
            "options": [
              {
                "value": "oscuro",
                "label": "Fondo oscuro",
                "only_when": null
              },
              {
                "value": "claro",
                "label": "Fondo claro",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "resolucion",
            "label": "Resolucion",
            "kind": "select",
            "default": "1400",
            "options": [
              {
                "value": "1400",
                "label": "1400",
                "only_when": null
              },
              {
                "value": "1800",
                "label": "1800",
                "only_when": null
              },
              {
                "value": "2000",
                "label": "2000",
                "only_when": null
              },
              {
                "value": "2400",
                "label": "2400",
                "only_when": null
              },
              {
                "value": "2712",
                "label": "2712",
                "only_when": null
              },
              {
                "value": "3200",
                "label": "3200",
                "only_when": null
              },
              {
                "value": "4000",
                "label": "4000",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "animar",
            "label": "Animar",
            "kind": "toggle",
            "default": true,
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "snapshot": false
            }
          },
          {
            "name": "fps",
            "label": "Cuadros por segundo",
            "kind": "slider",
            "default": 12,
            "options": [],
            "help": "",
            "min": 4.0,
            "max": 30.0,
            "step": 2.0,
            "enabled_when": {
              "snapshot": false
            }
          }
        ],
        "preview": "/previews/precipitacion_ecmwf.webp",
        "previews": [
          {
            "url": "/previews/precipitacion_ecmwf--aifs-ens--false.webp",
            "when": {
              "modelo": "aifs-ens",
              "paraguay": "false"
            }
          },
          {
            "url": "/previews/precipitacion_ecmwf--aifs-single--false.webp",
            "when": {
              "modelo": "aifs-single",
              "paraguay": "false"
            }
          },
          {
            "url": "/previews/precipitacion_ecmwf--ifs--false.webp",
            "when": {
              "modelo": "ifs",
              "paraguay": "false"
            }
          },
          {
            "url": "/previews/precipitacion_ecmwf--ifs--true.webp",
            "when": {
              "modelo": "ifs",
              "paraguay": "true"
            }
          }
        ],
        "command_ready": true,
        "command": null
      },
      {
        "id": "follaje",
        "name": "PACE - follaje (LANDVI)",
        "group": "vegetacion",
        "stage": "descargar/pace_landvi.py + cuadros/cuadros_follaje.py",
        "summary": "Indice de vegetacion de PACE sobre fondo de poster, ventana por dias.",
        "params": [
          {
            "name": "snapshot",
            "label": "Snapshot",
            "kind": "toggle",
            "default": true,
            "options": [],
            "help": "un solo cuadro: no arma serie ni animación, y usa el cuadro de siempre",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "ventana",
            "label": "Ventana temporal",
            "kind": "date-range",
            "default": {
              "start": "2026-10-10",
              "end": "2026-10-10"
            },
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "proyeccion",
            "label": "Proyeccion",
            "kind": "select",
            "default": "plano",
            "options": [
              {
                "value": "plano",
                "label": "Plano (Robinson)",
                "only_when": null
              },
              {
                "value": "globo",
                "label": "Globo (Orthographic)",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "resolucion",
            "label": "Resolucion",
            "kind": "select",
            "default": "1400",
            "options": [
              {
                "value": "1400",
                "label": "1400",
                "only_when": null
              },
              {
                "value": "1800",
                "label": "1800",
                "only_when": null
              },
              {
                "value": "2000",
                "label": "2000",
                "only_when": null
              },
              {
                "value": "2400",
                "label": "2400",
                "only_when": null
              },
              {
                "value": "2712",
                "label": "2712",
                "only_when": null
              },
              {
                "value": "3200",
                "label": "3200",
                "only_when": null
              },
              {
                "value": "4000",
                "label": "4000",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "animar",
            "label": "Animar",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "snapshot": false
            }
          },
          {
            "name": "fps",
            "label": "Cuadros por segundo",
            "kind": "slider",
            "default": 12,
            "options": [],
            "help": "",
            "min": 4.0,
            "max": 30.0,
            "step": 2.0,
            "enabled_when": {
              "snapshot": false
            }
          }
        ],
        "preview": "/previews/follaje.webp",
        "previews": [
          {
            "url": "/previews/follaje--globo.webp",
            "when": {
              "proyeccion": "globo"
            }
          },
          {
            "url": "/previews/follaje--plano.webp",
            "when": {
              "proyeccion": "plano"
            }
          }
        ],
        "command_ready": true,
        "command": null
      },
      {
        "id": "truecolor_viirs",
        "name": "NOAA-20 - true color (VIIRS)",
        "group": "satelite",
        "stage": "descargar/truecolor.py + cuadros/cuadros_truecolor.py",
        "summary": "Composicion diaria global de VIIRS en color real corregido. Un cuadro por dia: es un mosaico, no una captura instantanea.",
        "params": [
          {
            "name": "snapshot",
            "label": "Snapshot",
            "kind": "toggle",
            "default": true,
            "options": [],
            "help": "un solo cuadro: no arma serie ni animación, y usa el cuadro de siempre",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "paraguay",
            "label": "Solo Paraguay",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "encuadra la captura o la animación en las coordenadas de Paraguay",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "margen",
            "label": "Margen Paraguay (%)",
            "kind": "slider",
            "default": 6,
            "options": [],
            "help": "aire alrededor del país dentro del encuadre",
            "min": 0.0,
            "max": 20.0,
            "step": 1.0,
            "enabled_when": {
              "paraguay": true
            }
          },
          {
            "name": "ventana",
            "label": "Dias",
            "kind": "date-range",
            "default": {
              "start": "2026-11-04",
              "end": "2026-11-04"
            },
            "options": [],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "resolucion",
            "label": "Resolucion",
            "kind": "select",
            "default": "1400",
            "options": [
              {
                "value": "1400",
                "label": "1400",
                "only_when": null
              },
              {
                "value": "1800",
                "label": "1800",
                "only_when": null
              },
              {
                "value": "2000",
                "label": "2000",
                "only_when": null
              },
              {
                "value": "2400",
                "label": "2400",
                "only_when": null
              },
              {
                "value": "2712",
                "label": "2712",
                "only_when": null
              },
              {
                "value": "3200",
                "label": "3200",
                "only_when": null
              },
              {
                "value": "4000",
                "label": "4000",
                "only_when": null
              }
            ],
            "help": "",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": null
          },
          {
            "name": "animar",
            "label": "Animar los dias",
            "kind": "toggle",
            "default": false,
            "options": [],
            "help": "un cuadro por dia; la animacion muestra la evolucion entre fechas",
            "min": null,
            "max": null,
            "step": null,
            "enabled_when": {
              "snapshot": false
            }
          },
          {
            "name": "fps",
            "label": "Cuadros por segundo",
            "kind": "slider",
            "default": 6,
            "options": [],
            "help": "",
            "min": 2.0,
            "max": 30.0,
            "step": 1.0,
            "enabled_when": {
              "snapshot": false
            }
          }
        ],
        "preview": "/previews/truecolor_viirs.webp",
        "previews": [],
        "command_ready": true,
        "command": null
      }
    ],
    "data_root": "dataset congelado de la demo",
    "data_root_exists": true,
    "media_root": "/media",
    "repo_python": "cloudflare/workers",
    "repo_ready": true
  }
};
