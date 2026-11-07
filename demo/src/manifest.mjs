// Generado por demo/tools/export_demo.py. No editar a mano.
export default {
  "version": 1,
  "generated_at": "2026-11-06T19:02:53+00:00",
  "days": [
    "2026-10-10",
    "2026-11-03",
    "2026-11-04",
    "2026-11-05"
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
                "label": "GOES-East G19 (75.2 W)"
              },
              {
                "value": "G18",
                "label": "GOES-West G18 (137.2 W)"
              },
              {
                "value": "G16",
                "label": "GOES-East G16 (hasta 2025)"
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
                "label": "10 cuadros"
              },
              {
                "value": "12",
                "label": "12 cuadros"
              },
              {
                "value": "24",
                "label": "24 cuadros"
              },
              {
                "value": "36",
                "label": "36 cuadros"
              },
              {
                "value": "48",
                "label": "48 cuadros"
              },
              {
                "value": "60",
                "label": "60 cuadros"
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
                "label": "00"
              },
              {
                "value": "10",
                "label": "10"
              },
              {
                "value": "20",
                "label": "20"
              },
              {
                "value": "30",
                "label": "30"
              },
              {
                "value": "40",
                "label": "40"
              },
              {
                "value": "50",
                "label": "50"
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
                "label": "clean_ir - Clean Infrared (GIBS)"
              },
              {
                "value": "termico",
                "label": "termico - gris termico"
              },
              {
                "value": "gris",
                "label": "gris - reflectancia"
              },
              {
                "value": "anomalia",
                "label": "anomalia - paleta de anomalia"
              },
              {
                "value": "magma",
                "label": "magma"
              },
              {
                "value": "inferno",
                "label": "inferno"
              },
              {
                "value": "turbo",
                "label": "turbo"
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
                "label": "1400"
              },
              {
                "value": "1800",
                "label": "1800"
              },
              {
                "value": "2000",
                "label": "2000"
              },
              {
                "value": "2400",
                "label": "2400"
              },
              {
                "value": "2712",
                "label": "2712"
              },
              {
                "value": "3200",
                "label": "3200"
              },
              {
                "value": "4000",
                "label": "4000"
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
                "label": "GOES-East G19 (75.2 W)"
              },
              {
                "value": "G18",
                "label": "GOES-West G18 (137.2 W)"
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
                "label": "10 cuadros"
              },
              {
                "value": "12",
                "label": "12 cuadros"
              },
              {
                "value": "24",
                "label": "24 cuadros"
              },
              {
                "value": "36",
                "label": "36 cuadros"
              },
              {
                "value": "48",
                "label": "48 cuadros"
              },
              {
                "value": "60",
                "label": "60 cuadros"
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
                "label": "00"
              },
              {
                "value": "10",
                "label": "10"
              },
              {
                "value": "20",
                "label": "20"
              },
              {
                "value": "30",
                "label": "30"
              },
              {
                "value": "40",
                "label": "40"
              },
              {
                "value": "50",
                "label": "50"
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
                "label": "1400"
              },
              {
                "value": "1800",
                "label": "1800"
              },
              {
                "value": "2000",
                "label": "2000"
              },
              {
                "value": "2400",
                "label": "2400"
              },
              {
                "value": "2712",
                "label": "2712"
              },
              {
                "value": "3200",
                "label": "3200"
              },
              {
                "value": "4000",
                "label": "4000"
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
                "label": "GOES-East G19 (75.2 W)"
              },
              {
                "value": "G18",
                "label": "GOES-West G18 (137.2 W)"
              },
              {
                "value": "G16",
                "label": "GOES-East G16 (hasta 2025)"
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
                "label": "Globo orthographic"
              },
              {
                "value": "disco",
                "label": "Disco nativo (sin reproyectar)"
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
                "label": "Completo: todo el disco captado"
              },
              {
                "value": "recortado",
                "label": "Recortado: sin la franja estirada"
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
                "label": "Maxima: sin mediana ni desenfoque"
              },
              {
                "value": "suave",
                "label": "Suave: mediana 3x3 y desenfoque 0.8 px"
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
                "label": "00"
              },
              {
                "value": "10",
                "label": "10"
              },
              {
                "value": "20",
                "label": "20"
              },
              {
                "value": "30",
                "label": "30"
              },
              {
                "value": "40",
                "label": "40"
              },
              {
                "value": "50",
                "label": "50"
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
                "label": "1400"
              },
              {
                "value": "1800",
                "label": "1800"
              },
              {
                "value": "2000",
                "label": "2000"
              },
              {
                "value": "2400",
                "label": "2400"
              },
              {
                "value": "2712",
                "label": "2712"
              },
              {
                "value": "3200",
                "label": "3200"
              },
              {
                "value": "4000",
                "label": "4000"
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
                "label": "GOES-East G19 (75.2 W)"
              },
              {
                "value": "G18",
                "label": "GOES-West G18 (137.2 W)"
              },
              {
                "value": "G16",
                "label": "GOES-East G16 (hasta 2025)"
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
                "label": "10 cuadros"
              },
              {
                "value": "12",
                "label": "12 cuadros"
              },
              {
                "value": "24",
                "label": "24 cuadros"
              },
              {
                "value": "36",
                "label": "36 cuadros"
              },
              {
                "value": "48",
                "label": "48 cuadros"
              },
              {
                "value": "60",
                "label": "60 cuadros"
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
                "label": "00"
              },
              {
                "value": "10",
                "label": "10"
              },
              {
                "value": "20",
                "label": "20"
              },
              {
                "value": "30",
                "label": "30"
              },
              {
                "value": "40",
                "label": "40"
              },
              {
                "value": "50",
                "label": "50"
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
                "label": "1400"
              },
              {
                "value": "1800",
                "label": "1800"
              },
              {
                "value": "2000",
                "label": "2000"
              },
              {
                "value": "2400",
                "label": "2400"
              },
              {
                "value": "2712",
                "label": "2712"
              },
              {
                "value": "3200",
                "label": "3200"
              },
              {
                "value": "4000",
                "label": "4000"
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
                "label": "GOES-East G19 (75.2 W)"
              },
              {
                "value": "G18",
                "label": "GOES-West G18 (137.2 W)"
              },
              {
                "value": "G16",
                "label": "GOES-East G16 (hasta 2025)"
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
                "label": "10 cuadros"
              },
              {
                "value": "12",
                "label": "12 cuadros"
              },
              {
                "value": "24",
                "label": "24 cuadros"
              },
              {
                "value": "36",
                "label": "36 cuadros"
              },
              {
                "value": "48",
                "label": "48 cuadros"
              },
              {
                "value": "60",
                "label": "60 cuadros"
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
                "label": "00"
              },
              {
                "value": "10",
                "label": "10"
              },
              {
                "value": "20",
                "label": "20"
              },
              {
                "value": "30",
                "label": "30"
              },
              {
                "value": "40",
                "label": "40"
              },
              {
                "value": "50",
                "label": "50"
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
                "label": "1400"
              },
              {
                "value": "1800",
                "label": "1800"
              },
              {
                "value": "2000",
                "label": "2000"
              },
              {
                "value": "2400",
                "label": "2400"
              },
              {
                "value": "2712",
                "label": "2712"
              },
              {
                "value": "3200",
                "label": "3200"
              },
              {
                "value": "4000",
                "label": "4000"
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
                "label": "GOES-East G19 (75.2 W)"
              },
              {
                "value": "G18",
                "label": "GOES-West G18 (137.2 W)"
              },
              {
                "value": "G16",
                "label": "GOES-East G16 (hasta 2025)"
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
                "label": "10 cuadros"
              },
              {
                "value": "12",
                "label": "12 cuadros"
              },
              {
                "value": "24",
                "label": "24 cuadros"
              },
              {
                "value": "36",
                "label": "36 cuadros"
              },
              {
                "value": "48",
                "label": "48 cuadros"
              },
              {
                "value": "60",
                "label": "60 cuadros"
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
                "label": "00"
              },
              {
                "value": "10",
                "label": "10"
              },
              {
                "value": "20",
                "label": "20"
              },
              {
                "value": "30",
                "label": "30"
              },
              {
                "value": "40",
                "label": "40"
              },
              {
                "value": "50",
                "label": "50"
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
                "label": "1400"
              },
              {
                "value": "1800",
                "label": "1800"
              },
              {
                "value": "2000",
                "label": "2000"
              },
              {
                "value": "2400",
                "label": "2400"
              },
              {
                "value": "2712",
                "label": "2712"
              },
              {
                "value": "3200",
                "label": "3200"
              },
              {
                "value": "4000",
                "label": "4000"
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
                "label": "NOAA-20 / VIIRS (250 m)"
              },
              {
                "value": "snpp",
                "label": "Suomi NPP / VIIRS (250 m)"
              },
              {
                "value": "aqua",
                "label": "Aqua / MODIS (250 m)"
              },
              {
                "value": "terra",
                "label": "Terra / MODIS (250 m)"
              },
              {
                "value": "geocolor",
                "label": "GOES-19 GeoColor (dia y noche, ~2 km)"
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
                "label": "00"
              },
              {
                "value": "10",
                "label": "10"
              },
              {
                "value": "20",
                "label": "20"
              },
              {
                "value": "30",
                "label": "30"
              },
              {
                "value": "40",
                "label": "40"
              },
              {
                "value": "50",
                "label": "50"
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
                "label": "125 m/px"
              },
              {
                "value": "250",
                "label": "250 m/px"
              },
              {
                "value": "500",
                "label": "500 m/px"
              },
              {
                "value": "1000",
                "label": "1000 m/px"
              },
              {
                "value": "2000",
                "label": "2000 m/px"
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
                "label": "IFS deterministico"
              },
              {
                "value": "aifs-single",
                "label": "AIFS single"
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
                "label": "00z"
              },
              {
                "value": "06",
                "label": "06z"
              },
              {
                "value": "12",
                "label": "12z"
              },
              {
                "value": "18",
                "label": "18z"
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
                "label": "Fondo oscuro"
              },
              {
                "value": "claro",
                "label": "Fondo claro"
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
                "label": "1400"
              },
              {
                "value": "1800",
                "label": "1800"
              },
              {
                "value": "2000",
                "label": "2000"
              },
              {
                "value": "2400",
                "label": "2400"
              },
              {
                "value": "2712",
                "label": "2712"
              },
              {
                "value": "3200",
                "label": "3200"
              },
              {
                "value": "4000",
                "label": "4000"
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
                "label": "ECMWF IFS 0.25"
              },
              {
                "value": "gfs",
                "label": "GFS 0.25 (NOAA)"
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
                "label": "00z"
              },
              {
                "value": "06",
                "label": "06z"
              },
              {
                "value": "12",
                "label": "12z"
              },
              {
                "value": "18",
                "label": "18z"
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
                "label": "Fondo oscuro"
              },
              {
                "value": "claro",
                "label": "Fondo claro"
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
                "label": "1400"
              },
              {
                "value": "1800",
                "label": "1800"
              },
              {
                "value": "2000",
                "label": "2000"
              },
              {
                "value": "2400",
                "label": "2400"
              },
              {
                "value": "2712",
                "label": "2712"
              },
              {
                "value": "3200",
                "label": "3200"
              },
              {
                "value": "4000",
                "label": "4000"
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
                "label": "1400"
              },
              {
                "value": "1800",
                "label": "1800"
              },
              {
                "value": "2000",
                "label": "2000"
              },
              {
                "value": "2400",
                "label": "2400"
              },
              {
                "value": "2712",
                "label": "2712"
              },
              {
                "value": "3200",
                "label": "3200"
              },
              {
                "value": "4000",
                "label": "4000"
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
                "label": "1400"
              },
              {
                "value": "1800",
                "label": "1800"
              },
              {
                "value": "2000",
                "label": "2000"
              },
              {
                "value": "2400",
                "label": "2400"
              },
              {
                "value": "2712",
                "label": "2712"
              },
              {
                "value": "3200",
                "label": "3200"
              },
              {
                "value": "4000",
                "label": "4000"
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
                "label": "realista (Earth Observatory)"
              },
              {
                "value": "gibs",
                "label": "gibs (SST oficial)"
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
        "id": "follaje",
        "name": "PACE - follaje (LANDVI)",
        "group": "satelite",
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
                "label": "Plano (Robinson)"
              },
              {
                "value": "globo",
                "label": "Globo (Orthographic)"
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
                "label": "1400"
              },
              {
                "value": "1800",
                "label": "1800"
              },
              {
                "value": "2000",
                "label": "2000"
              },
              {
                "value": "2400",
                "label": "2400"
              },
              {
                "value": "2712",
                "label": "2712"
              },
              {
                "value": "3200",
                "label": "3200"
              },
              {
                "value": "4000",
                "label": "4000"
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
                "label": "1400"
              },
              {
                "value": "1800",
                "label": "1800"
              },
              {
                "value": "2000",
                "label": "2000"
              },
              {
                "value": "2400",
                "label": "2400"
              },
              {
                "value": "2712",
                "label": "2712"
              },
              {
                "value": "3200",
                "label": "3200"
              },
              {
                "value": "4000",
                "label": "4000"
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
