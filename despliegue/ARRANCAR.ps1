<#
.SYNOPSIS
    Arranca la consola de Climate 3D preguntando donde guardar todo.

.DESCRIPTION
    Pregunta la carpeta donde viven los datos, las salidas y la cache (por defecto, la
    que ya esta configurada), la valida, la guarda en el archivo de configuracion del
    usuario, migra lo que hubiera quedado en `app\var` y levanta el servidor.

    El archivo de configuracion lo escribe `comun\rutas.py`: es la unica fuente de las
    raices, tambien para el pipeline.

.EXAMPLE
    .\ARRANCAR.ps1

.EXAMPLE
    .\ARRANCAR.ps1 -Raiz D:\climate3d -Port 8001

.EXAMPLE
    .\ARRANCAR.ps1 -SinPreguntar      # usa lo ya configurado, sin consola
#>
[CmdletBinding()]
param(
    [string]$Raiz,
    [int]$Port = 8000,
    [switch]$SinPreguntar,
    [switch]$SinMigrar,
    [switch]$SoloConfigurar
)

$ErrorActionPreference = 'Continue'
# Este lanzador vive en despliegue/: la raiz del repo es la carpeta de arriba.
$raizRepo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
Set-Location -LiteralPath $raizRepo

function Fallar {
    param([string]$Mensaje)
    Write-Host "`n  x  $Mensaje" -ForegroundColor Red
    exit 1
}

function Ok {
    param([string]$Mensaje)
    Write-Host "  ok  $Mensaje" -ForegroundColor Green
}

function Paso {
    param([string]$Mensaje)
    Write-Host "`n$Mensaje" -ForegroundColor Cyan
}

function Preguntar {
    param([string]$Texto)
    try { return Read-Host $Texto } catch { return '' }
}

$python = Join-Path $raizRepo '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    Fallar 'falta .venv en la raiz del repo. Es el unico entorno: pipeline y consola. Ver app\README.md.'
}
# Un solo entorno: si falta la parte web, el mensaje dice que instalar.
& $python -c "import fastapi, uvicorn" 2>$null
if ($LASTEXITCODE -ne 0) {
    Fallar 'al .venv le faltan las dependencias de la consola. Corre: uv sync'
}

# --- configuracion actual ---------------------------------------------------

$config = $null
try {
    $json = & $python (Join-Path $raizRepo 'comun\rutas.py') --show 2>$null | Out-String
    if ($LASTEXITCODE -eq 0 -and $json.Trim()) { $config = $json | ConvertFrom-Json }
} catch {
    $config = $null
}
if (-not $config) {
    $config = [pscustomobject]@{
        datos = (Join-Path $env:USERPROFILE 'climate3d-data')
        media = ''
        nisar = ''
        config = ''
    }
}

Paso '[1/3] Donde guardar todo'
Write-Host '  Datos crudos, productos, salidas y cache van a una sola carpeta.'
Write-Host '  Elegi un disco con espacio: una animacion de GOES son varios GB.'
Write-Host ("  hoy: datos={0}" -f $config.datos)
if ($config.media) { Write-Host ("       cache={0}" -f $config.media) }
if ($config.nisar) { Write-Host ("       nisar={0}  (.h5, quedan donde estan)" -f $config.nisar) }

$sugerida = $Raiz
if ([string]::IsNullOrWhiteSpace($sugerida)) { $sugerida = $config.datos }
if ([string]::IsNullOrWhiteSpace($sugerida)) { $sugerida = 'D:\climate3d-data' }

if (-not $SinPreguntar) {
    $entrada = Preguntar "  Carpeta base [Enter = $sugerida]"
    if ([string]::IsNullOrWhiteSpace($entrada)) { $Raiz = $sugerida } else { $Raiz = $entrada }
} else {
    $Raiz = $sugerida
}

$Raiz = $Raiz.Trim().Trim('"').Trim("'")
if ([string]::IsNullOrWhiteSpace($Raiz)) { Fallar 'la carpeta quedo vacia.' }
if ($Raiz.StartsWith('\\')) {
    Fallar 'no puedo usar una ruta de red. Elegi un disco local.'
}

foreach ($od in @($env:OneDrive, $env:OneDriveCommercial, $env:OneDriveConsumer)) {
    if ([string]::IsNullOrWhiteSpace($od)) { continue }
    $odPosix = ($od -replace '\\', '/').TrimEnd('/').ToLowerInvariant()
    $destino = ($Raiz -replace '\\', '/').TrimEnd('/').ToLowerInvariant()
    if ($destino -eq $odPosix -or $destino.StartsWith($odPosix + '/')) {
        Fallar 'esa carpeta esta dentro de OneDrive: la sincronizacion de varios GB la traba. Elegi otra.'
    }
}
if ($Raiz -match '(?i)(^|[\\/])onedrive([\\/]|$)') {
    Fallar 'esa carpeta esta dentro de OneDrive. Elegi un disco local.'
}

# Dentro del repo tampoco: es OneDrive y ademas la cache se mezcla con el codigo.
$repoPosix = ($raizRepo -replace '\\', '/').TrimEnd('/').ToLowerInvariant()
$destinoPosix = ($Raiz -replace '\\', '/').TrimEnd('/').ToLowerInvariant()
if ($destinoPosix -eq $repoPosix -or $destinoPosix.StartsWith($repoPosix + '/')) {
    Fallar 'esa carpeta esta dentro del repo. Elegi una carpeta fuera (por ejemplo D:\climate3d-data).'
}

if (-not (Test-Path -LiteralPath $Raiz)) {
    New-Item -ItemType Directory -Path $Raiz -Force -ErrorAction SilentlyContinue | Out-Null
    if (-not (Test-Path -LiteralPath $Raiz)) { Fallar "no pude crear '$Raiz'. Revisa los permisos." }
    Ok "cree $Raiz"
} else {
    Ok "uso $Raiz"
}

$prueba = Join-Path $Raiz ('.escritura-' + [guid]::NewGuid().ToString('N'))
try {
    Set-Content -LiteralPath $prueba -Value 'ok' -Encoding ASCII -ErrorAction Stop
    Remove-Item -LiteralPath $prueba -Force -ErrorAction Stop
} catch {
    Fallar "no puedo escribir en '$Raiz'. Elegi otra carpeta o dale permisos."
}
Ok 'la carpeta es escribible.'

$unidad = Split-Path -Qualifier $Raiz
if ($unidad) {
    $disco = Get-PSDrive -Name $unidad.TrimEnd(':') -ErrorAction SilentlyContinue
    if ($disco -and $disco.Free -gt 0) {
        $libres = [math]::Round($disco.Free / 1GB, 1)
        if ($libres -lt 20) {
            Write-Host ("  !  quedan {0} GB libres: un render largo genera muchos cuadros." -f $libres) -ForegroundColor Yellow
        } else {
            Ok ("espacio libre: {0} GB" -f $libres)
        }
    }
}

$media = Join-Path $Raiz '.media'
$json = & $python (Join-Path $raizRepo 'comun\rutas.py') --datos $Raiz --media $media 2>$null | Out-String
if ($LASTEXITCODE -ne 0) { Fallar 'no pude guardar la configuracion (comun\rutas.py).' }
$efectivo = $json | ConvertFrom-Json
Ok ("configuracion guardada en {0}" -f $efectivo.config)

if ($SoloConfigurar) {
    Write-Host ''
    Write-Host ("  datos: {0}" -f $efectivo.datos)
    Write-Host ("  cache: {0}" -f $efectivo.media)
    Write-Host ("  nisar: {0}" -f $efectivo.nisar)
    Write-Host ''
    Write-Host '  Listo. Para levantar la consola: .\despliegue\ARRANCAR.ps1' -ForegroundColor Green
    exit 0
}


# --- migracion de lo que quedo en C: ---------------------------------------

$origenMedia = Join-Path $raizRepo 'app\var\media'
$origenNisar = Join-Path $raizRepo 'app\var\nisar\cache'
$pendientes = @()
foreach ($par in @(@($origenMedia, $media), @($origenNisar, (Join-Path $media 'nisar\cache')))) {
    $desde = $par[0]
    $hasta = $par[1]
    if (-not (Test-Path -LiteralPath $desde)) { continue }
    $archivos = Get-ChildItem -LiteralPath $desde -Recurse -File -ErrorAction SilentlyContinue
    if (-not $archivos) { continue }
    $peso = [math]::Round(($archivos | Measure-Object Length -Sum).Sum / 1MB, 0)
    $pendientes += [pscustomobject]@{ Desde = $desde; Hasta = $hasta; MB = $peso; Archivos = $archivos.Count }
}

if ($pendientes.Count -gt 0) {
    Paso '[2/3] Quedo trabajo viejo dentro del repo'
    foreach ($p in $pendientes) {
        Write-Host ("  {0} MB en {1}" -f $p.MB, $p.Desde)
    }
    $mover = -not $SinMigrar
    if (-not $SinPreguntar) {
        $respuesta = Preguntar "  Los muevo a la carpeta nueva? (s/N)"
        $mover = $respuesta -match '^(s|si|y|yes)$'
    }
    if ($mover) {
        foreach ($p in $pendientes) {
            New-Item -ItemType Directory -Path $p.Hasta -Force | Out-Null
            & robocopy $p.Desde $p.Hasta /E /NFL /NDL /NJH /NJS /R:1 /W:1 | Out-Null
            # robocopy: 0-7 son exito; 8 o mas es un error real y no se borra el origen.
            if ($LASTEXITCODE -lt 8) {
                Remove-Item -LiteralPath $p.Desde -Recurse -Force -ErrorAction SilentlyContinue
                Ok ("movido: {0} MB -> {1}" -f $p.MB, $p.Hasta)
            } else {
                Write-Host ("  !  robocopy fallo ({0}); dejo el original en su lugar." -f $LASTEXITCODE) -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host '  quedan donde estan; se pueden mover a mano cuando quieras.'
    }
} else {
    Paso '[2/3] Nada viejo que migrar'
    Ok 'el trabajo ya vive en la carpeta configurada.'
}


# --- arranque ---------------------------------------------------------------

Paso '[3/3] Levantando la consola'
$env:CLIMATE3D_DATOS = $efectivo.datos
$env:CLIMATE3D_MEDIA = $efectivo.media
if ($efectivo.nisar) { $env:CLIMATE3D_NISAR = $efectivo.nisar }

# Los temporales de los renders (h5py, matplotlib, PIL) tambien van al disco de trabajo:
# en C: un render grande se queda sin memoria al no poder crecer la pagina de archivo.
$temporal = Join-Path $Raiz '.tmp'
New-Item -ItemType Directory -Path $temporal -Force -ErrorAction SilentlyContinue | Out-Null
$env:TEMP = $temporal
$env:TMP = $temporal

Write-Host ("  datos  : {0}" -f $efectivo.datos)
Write-Host ("  cache  : {0}" -f $efectivo.media)
Write-Host ("  temp   : {0}" -f $temporal)
Write-Host ("  nisar  : {0}" -f $efectivo.nisar)
Write-Host ''
Write-Host ("  Abri http://127.0.0.1:{0}  (Ctrl+C para cortar)" -f $Port) -ForegroundColor Green
Write-Host ''

& $python -m uvicorn api.main:app --app-dir app --port $Port
exit $LASTEXITCODE
