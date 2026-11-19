<#
.SYNOPSIS
    Arranca la consola de Climate 3D: pregunta donde descargar y las claves.

.DESCRIPTION
    Cuatro pasos, todos con Enter para aceptar lo que ya esta:
      1. Carpeta de descargas y salidas (la recuerda en %LOCALAPPDATA%\climate3d).
      2. Claves de las fuentes (FIRMS, Copernicus CDS, Earthdata), tambien recordadas.
      3. Migra lo que hubiera quedado dentro del repo (app\var).
      4. Levanta la consola y abre http://127.0.0.1:8000 en el navegador por defecto,
         en cuanto la API responde.

    Las claves quedan en %LOCALAPPDATA%\climate3d\credenciales.json, fuera del repo, y
    se exportan al proceso: los scripts del pipeline las heredan.

.EXAMPLE
    .\ARRANCAR.ps1

.EXAMPLE
    .\ARRANCAR.ps1 -Raiz D:\climate3d -Port 8001

.EXAMPLE
    .\ARRANCAR.ps1 -SinPreguntar      # usa lo ya configurado, sin consola

.EXAMPLE
    .\ARRANCAR.ps1 -SinNavegador      # no abre el navegador (servidor headless)
#>
[CmdletBinding()]
param(
    [string]$Raiz,
    [int]$Port = 8000,
    [switch]$SinPreguntar,
    [switch]$SinMigrar,
    [switch]$SoloConfigurar,
    [switch]$SinNavegador
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

function Estado {
    param([string]$Valor)
    if ([string]::IsNullOrWhiteSpace($Valor)) { return 'no' }
    return 'si'
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


# --- [1/4] carpeta de descargas ---------------------------------------------

Paso '[1/4] Carpeta de descargas y salidas'
Write-Host '  Ahi van los datos crudos, los productos, las salidas y la cache.'
Write-Host '  Elegi un disco con espacio: una animacion de GOES son varios GB.'
Write-Host ("  hoy: descargas={0}" -f $config.datos)
if ($config.media) { Write-Host ("       cache={0}" -f $config.media) }
if ($config.nisar) { Write-Host ("       nisar={0}  (.h5, quedan donde estan)" -f $config.nisar) }

$sugerida = $Raiz
if ([string]::IsNullOrWhiteSpace($sugerida)) { $sugerida = $config.datos }
if ([string]::IsNullOrWhiteSpace($sugerida)) { $sugerida = 'D:\climate3d-data' }

if (-not $SinPreguntar) {
    $entrada = Preguntar "  Donde descargamos? [Enter = $sugerida]"
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

# Todo adentro de la misma carpeta: si la raiz no cambia se conserva la carpeta de
# los .h5 que ya estaba configurada (puede tener cientos de GB); si cambia, los .h5
# pasan a <raiz>\nisar.
# Si la carpeta elegida YA es una raiz NISAR (tiene subcarpetas NISAR_*), se usa tal
# cual: anidar un `nisar` mas adentro escondería los .h5 que ya estan.
$pareceNisar = Get-ChildItem $Raiz -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like 'NISAR_*' } |
    Select-Object -First 1
$nisarSugerido = if ($pareceNisar) { $Raiz } else { Join-Path $Raiz 'nisar' }
if (-not [string]::IsNullOrWhiteSpace($config.nisar) -and (Test-Path -LiteralPath $config.nisar)) {
    $mismaRaiz = ($config.datos -replace '[\\/]+$', '').ToLowerInvariant() -eq ($Raiz -replace '[\\/]+$', '').ToLowerInvariant()
    if ($mismaRaiz) { $nisarSugerido = $config.nisar }
}

Write-Host ''
Write-Host '  Los .h5 de NISAR (1.9 GB cada uno) van en una subcarpeta propia.'
if (-not $SinPreguntar) {
    $entrada = Preguntar "  Donde guardamos los .h5? [Enter = $nisarSugerido]"
    if (-not [string]::IsNullOrWhiteSpace($entrada)) { $nisarSugerido = $entrada.Trim().Trim('"').Trim("'") }
}
$nisarSugerido = $nisarSugerido.TrimEnd('\').TrimEnd('/')
if ($nisarSugerido.StartsWith('\\')) {
    Fallar 'la carpeta de los .h5 no puede ser una ruta de red.'
}
if (-not (Test-Path -LiteralPath $nisarSugerido)) {
    New-Item -ItemType Directory -Path $nisarSugerido -Force -ErrorAction SilentlyContinue | Out-Null
    if (-not (Test-Path -LiteralPath $nisarSugerido)) {
        Fallar "no pude crear '$nisarSugerido'. Revisa los permisos."
    }
}
Ok ("nisar: {0}" -f $nisarSugerido)

$media = Join-Path $Raiz '.media'
$json = & $python (Join-Path $raizRepo 'comun\rutas.py') --datos $Raiz --media $media --nisar $nisarSugerido 2>$null | Out-String
if ($LASTEXITCODE -ne 0) { Fallar 'no pude guardar la configuracion (comun\rutas.py).' }
$efectivo = $json | ConvertFrom-Json
Ok ("configuracion guardada en {0}" -f $efectivo.config)


# --- [2/4] claves ------------------------------------------------------------

$carpetaClaves = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'climate3d'
$archivoClaves = Join-Path $carpetaClaves 'credenciales.json'
if ([string]::IsNullOrWhiteSpace([Environment]::GetFolderPath('LocalApplicationData'))) {
    $archivoClaves = Join-Path $env:USERPROFILE '.config\climate3d\credenciales.json'
}

$claves = [ordered]@{ firms = ''; cds = ''; earthdata_user = ''; earthdata_password = '' }
if (Test-Path -LiteralPath $archivoClaves) {
    try {
        $leido = Get-Content -LiteralPath $archivoClaves -Raw | ConvertFrom-Json
        foreach ($clave in @('firms', 'cds', 'earthdata_user', 'earthdata_password')) {
            if ($leido.PSObject.Properties.Name -contains $clave) {
                $claves[$clave] = [string]$leido.$clave
            }
        }
    } catch {
        Write-Host '  !  el archivo de claves no se pudo leer; se piden de nuevo.' -ForegroundColor Yellow
    }
}

Paso '[2/4] Claves de las fuentes (opcionales, Enter para conservar)'
Write-Host '  FIRMS      focos de calor   https://firms.modaps.eosdis.nasa.gov/api/map_key/'
Write-Host '  CDS        ERA5             https://cds.climate.copernicus.eu/'
Write-Host '  Earthdata  NISAR y PACE     https://urs.earthdata.nasa.gov/'
Write-Host ("  hoy: FIRMS={0} | CDS={1} | Earthdata={2}" -f (Estado $claves.firms), (Estado $claves.cds), (Estado $claves.earthdata_user))

$tocar = $false
if (-not $SinPreguntar) {
    $respuesta = Preguntar '  Cargamos o cambiamos las claves? (s/N)'
    $tocar = $respuesta -match '^(s|si|y|yes)$'
}

if ($tocar) {
    $valor = Preguntar '  FIRMS MAP_KEY [Enter = conservar]'
    if (-not [string]::IsNullOrWhiteSpace($valor)) { $claves.firms = $valor.Trim() }

    $valor = Preguntar '  Copernicus CDS key [Enter = conservar]'
    if (-not [string]::IsNullOrWhiteSpace($valor)) { $claves.cds = $valor.Trim() }

    $valor = Preguntar '  Earthdata usuario [Enter = conservar]'
    if (-not [string]::IsNullOrWhiteSpace($valor)) { $claves.earthdata_user = $valor.Trim() }

    $valor = Preguntar '  Earthdata clave [Enter = conservar]'
    if (-not [string]::IsNullOrWhiteSpace($valor)) { $claves.earthdata_password = $valor.Trim() }

    $carpetaClaves | ForEach-Object { if ($_ -and -not (Test-Path -LiteralPath $_)) { New-Item -ItemType Directory -Path $_ -Force | Out-Null } }
    [ordered]@{
        firms = $claves.firms
        cds = $claves.cds
        earthdata_user = $claves.earthdata_user
        earthdata_password = $claves.earthdata_password
    } | ConvertTo-Json | Set-Content -LiteralPath $archivoClaves -Encoding UTF8
    Ok ("claves guardadas en {0} (fuera del repo)" -f $archivoClaves)
}

# Al proceso: los scripts del pipeline las heredan.
if ($claves.firms) { $env:FIRMS_MAP_KEY = $claves.firms }
if ($claves.cds) { $env:CDSAPI_KEY = $claves.cds }
if ($claves.earthdata_user) { $env:EARTHDATA_USER = $claves.earthdata_user }
if ($claves.earthdata_password) { $env:EARTHDATA_PASSWORD = $claves.earthdata_password }

if ($SoloConfigurar) {
    Write-Host ''
    Write-Host ("  descargas : {0}" -f $efectivo.datos)
    Write-Host ("  cache     : {0}" -f $efectivo.media)
    Write-Host ("  nisar     : {0}" -f $efectivo.nisar)
    Write-Host ("  claves    : FIRMS={0} | CDS={1} | Earthdata={2}" -f (Estado $claves.firms), (Estado $claves.cds), (Estado $claves.earthdata_user))
    Write-Host ("  archivo   : {0}" -f $archivoClaves)
    Write-Host ''
    Write-Host '  Listo. Para levantar la consola: .\despliegue\ARRANCAR.ps1' -ForegroundColor Green
    exit 0
}


# --- [3/4] migracion de lo que quedo en C: -----------------------------------

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
    Paso '[3/4] Quedo trabajo viejo dentro del repo'
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
    Paso '[3/4] Nada viejo que migrar'
    Ok 'el trabajo ya vive en la carpeta configurada.'
}


# --- [4/4] arranque ----------------------------------------------------------

Paso '[4/4] Levantando la consola'
$env:CLIMATE3D_DATOS = $efectivo.datos
$env:CLIMATE3D_MEDIA = $efectivo.media
if ($efectivo.nisar) { $env:CLIMATE3D_NISAR = $efectivo.nisar }

# Los temporales de los renders (h5py, matplotlib, PIL) tambien van al disco de trabajo:
# en C: un render grande se queda sin memoria al no poder crecer la pagina de archivo.
$temporal = Join-Path $Raiz '.tmp'
New-Item -ItemType Directory -Path $temporal -Force -ErrorAction SilentlyContinue | Out-Null
$env:TEMP = $temporal
$env:TMP = $temporal

Write-Host ("  descargas : {0}" -f $efectivo.datos)
Write-Host ("  cache     : {0}" -f $efectivo.media)
Write-Host ("  temp      : {0}" -f $temporal)
Write-Host ("  nisar     : {0}" -f $efectivo.nisar)
Write-Host ("  claves    : FIRMS={0} | CDS={1} | Earthdata={2}" -f (Estado $claves.firms), (Estado $claves.cds), (Estado $claves.earthdata_user))
Write-Host ''
Write-Host ("  Abri http://127.0.0.1:{0}  (Ctrl+C para cortar)" -f $Port) -ForegroundColor Green
Write-Host '  Con Docker en su lugar: .\despliegue\ARRANCAR-DOCKER.bat' -ForegroundColor DarkGray
Write-Host ''

# El navegador se abre solo cuando la API responde: abrirlo antes muestra una
# pestana con error. El que espera va en segundo plano para que uvicorn se quede
# en primer plano y Ctrl+C corte como siempre.
if (-not $SinNavegador) {
    $url = "http://127.0.0.1:$Port"
    Start-Job -ScriptBlock {
        param($url)
        for ($i = 0; $i -lt 120; $i++) {
            try {
                $r = Invoke-WebRequest -Uri "$url/api/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
                if ($r.StatusCode -eq 200) {
                    Start-Process $url
                    return
                }
            } catch {
                # Todavia no levanto: se reintenta.
            }
            Start-Sleep -Milliseconds 500
        }
    } -ArgumentList $url | Out-Null
}

& $python -m uvicorn api.main:app --app-dir app --port $Port
exit $LASTEXITCODE
