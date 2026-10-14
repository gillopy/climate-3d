# `datos/` — datos auxiliares

Datos chicos que sí viven en el repositorio (a diferencia de los `.nc` satelitales,
que van a `D:\`).

---

## `paraguay_gadm.json`

Borde **del país Paraguay** a nivel 0 (contorno nacional), en GeoJSON.

| Campo | Valor |
|---|---|
| Origen | [GADM v4.1](https://gadm.org/) — `gadm41_PRY_0.json` |
| Entidad | `GID_0 = PRY`, `COUNTRY = Paraguay` |
| Geometría | `MultiPolygon`, **1893 vértices** |
| Tamaño | ~37 KB |

Se dibuja como **borde destacado** en blanco sobre el mapa, por encima de los datos
(`zorder=5`), pasándolo a `draw_goes_poster`:

```python
from poster_goes import draw_goes_poster

draw_goes_poster(
    campo, ..., globe_center=(-73.0, -18.0),
    highlight_geojson="datos/paraguay_gadm.json",
    highlight_color="#ffffff",     # opcional
    highlight_width=1.2,           # opcional, en puntos
)
```

Acepta cualquier GeoJSON con `Polygon` o `MultiPolygon` en lon/lat (también
`FeatureCollection`), así que sirve para resaltar otro país o una subdivisión.

### Por qué GADM y no otro

Se probó primero el GeoJSON de `johan/world.geo.json`, pero tiene solo **33 vértices**
para Paraguay: el contorno sale anguloso y no sigue el río. GADM trae 1893, suficiente
para que el trazo se vea fiel incluso en el zoom regional.
