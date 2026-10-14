# `logs/` — registros de descarga

Salida de las descargas largas (hoy, solo la de ERA5 desde Copernicus CDS).

| Archivo | Qué contiene |
|---|---|
| `descarga_era5.log` | Progreso de la descarga: solicitud enviada a CDS y confirmación final con el tamaño del archivo |
| `descarga_era5.err.log` | Salida de error, que incluye la **barra de progreso** de `cdsapi` (por eso aparece ahí y no en el `.log`) |

Son **descartables**: se pueden borrar en cualquier momento, no los lee ningún script,
solo sirven para diagnosticar una descarga que falló o tardó de más. Están cubiertos
por `*.log` en el `.gitignore`.
