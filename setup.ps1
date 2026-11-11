<#
.SYNOPSIS
    Asistente de instalación de Climate 3D en Docker (Windows).

.DESCRIPTION
    Verifica Docker, pregunta la carpeta de datos, valida que se pueda escribir, pide
    las credenciales opcionales, escribe `.env` y levanta el contenedor.
    No edita código: lo único configurable es el lado host.

.EXAMPLE
    .\setup.ps1

.EXAMPLE
    .\setup.ps1 -DataDir D:\clima -Port 8080

.EXAMPLE
    .\setup.ps1 -SoloConfigurar
#>
[CmdletBinding()]
param(
    [string]$DataDir,
    [int]$Port = 8080,
    [string]$FirmsKey,
    [string]$CdsKey,
    [string]$EarthdataUser,
    [string]$EarthdataPassword,
    [switch]$SoloConfigurar
)

$ErrorActionPreference = 'Continue'
$raiz = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location -LiteralPath $raiz

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

function ValorEnv {
    # Compose corta el valor en un `#` y se come los espacios de los bordes.
    param([string]$Valor)
    if ($Valor -match '[\s#]') { return '"' + ($Valor -replace '"', '\"') + '"' }
    return $Valor
}

function Preguntar {
    # En una consola no interactiva `Read-Host` tira un error: devolvemos el default.
    param([string]$Texto)
    try { return Read-Host $Texto } catch { return '' }
}


Paso '[1/6] Docker'
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Fallar "no encontré 'docker'. Instalá Docker Desktop y volvé a correr este script."
}
& docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Fallar 'Docker está instalado pero el daemon no responde. Abrí Docker Desktop y esperá a que arranque.'
}
& docker compose version 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Fallar "falta el plugin 'docker compose'. Actualizá Docker Desktop."
}
Ok 'Docker responde.'


Paso '[2/6] Carpeta de datos (los .nc y las salidas)'
$sugerida = 'D:\climate3d-data'
if (-not (Test-Path -LiteralPath 'D:\')) {
    $sugerida = Join-Path $env:USERPROFILE 'climate3d-data'
}
if ([string]::IsNullOrWhiteSpace($DataDir)) {
    $entrada = Preguntar "  ¿Dónde guardamos los datos? [$sugerida]"
    if ([string]::IsNullOrWhiteSpace($entrada)) { $DataDir = $sugerida } else { $DataDir = $entrada }
}
$DataDir = $DataDir.Trim()
$DataDir = $DataDir.Trim('"').Trim("'")
# Adentro del contenedor la ruta es fija (/data): lo que configuramos es el lado host.
$DataDir = ($DataDir -replace '\\', '/').TrimEnd('/')
if ([string]::IsNullOrWhiteSpace($DataDir)) { Fallar 'la carpeta de datos quedó vacía.' }

if ($DataDir.StartsWith('//')) {
    Fallar "no puedo montar una ruta de red como volumen ('$DataDir'). Usá un disco local y copiá los datos ahí."
}

foreach ($od in @($env:OneDrive, $env:OneDriveCommercial, $env:OneDriveConsumer)) {
    if ([string]::IsNullOrWhiteSpace($od)) { continue }
    $odPosix = ($od -replace '\\', '/').TrimEnd('/').ToLowerInvariant()
    $destino = $DataDir.ToLowerInvariant()
    if ($destino -eq $odPosix -or $destino.StartsWith($odPosix + '/')) {
        Fallar 'esa carpeta está dentro de OneDrive. OneDrive intentaría sincronizar varios GB y se va a trabar: elegí una carpeta fuera de la nube.'
    }
}
# Respaldo por si la carpeta está redirigida y las variables de OneDrive no lo dicen:
# un segmento exacto, no una subcadena (D:/onedrive-archivo es válido).
if ($DataDir -match '(?i)/(onedrive)(/|$)') {
    Fallar 'esa carpeta está dentro de OneDrive. Elegí una carpeta fuera de la nube: son varios GB.'
}

$rutaWin = $DataDir -replace '/', '\'
if (Test-Path -LiteralPath $rutaWin) {
    Ok "usa $rutaWin (ya existía)"
} else {
    New-Item -ItemType Directory -Path $rutaWin -Force -ErrorAction SilentlyContinue | Out-Null
    if (-not (Test-Path -LiteralPath $rutaWin)) {
        Fallar "no pude crear '$rutaWin'. Revisá los permisos."
    }
    Ok "creé $rutaWin"
}

$prueba = Join-Path $rutaWin ('.escritura-' + [guid]::NewGuid().ToString('N'))
try {
    Set-Content -LiteralPath $prueba -Value 'ok' -Encoding ASCII -ErrorAction Stop
    Remove-Item -LiteralPath $prueba -Force -ErrorAction Stop
} catch {
    Fallar "no puedo escribir en '$rutaWin'. Elegí otra carpeta o dale permiso."
}
Ok 'la carpeta es escribible.'

New-Item -ItemType Directory -Path (Join-Path $rutaWin '.media') -Force -ErrorAction SilentlyContinue | Out-Null

$unidad = Split-Path -Qualifier $rutaWin
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


Paso '[3/6] Credenciales (opcionales: Enter para saltear)'
Write-Host '  FIRMS      -> focos de calor  (gratis: https://firms.modaps.eosdis.nasa.gov/api/map_key/)'
Write-Host '  CDS        -> descarga ERA5   (gratis: https://cds.climate.copernicus.eu/)'
Write-Host '  Earthdata  -> follaje PACE    (gratis: https://urs.earthdata.nasa.gov/)'

$hayFlags = -not ([string]::IsNullOrWhiteSpace($FirmsKey) -and
                  [string]::IsNullOrWhiteSpace($CdsKey) -and
                  [string]::IsNullOrWhiteSpace($EarthdataUser))

if (-not $hayFlags) {
    $quiere = Preguntar '  ¿Configuramos credenciales ahora? (s/N)'
    if ($quiere -match '^(s|si|sí|y|yes)$') {
        $FirmsKey = Preguntar '  FIRMS MAP_KEY'
        $CdsKey = Preguntar '  Copernicus CDS key'
        $EarthdataUser = Preguntar '  Earthdata usuario'
        $EarthdataPassword = Preguntar '  Earthdata clave'
    }
}


Paso '[4/6] Configuración (.env)'
$lineas = @(
    '# Generado por setup.ps1. Ver env.example para el detalle de cada variable.',
    '',
    '# --- host ---',
    ('DATA_DIR=' + (ValorEnv $DataDir)),
    ('PORT=' + $Port),
    '',
    '# --- credenciales (opcionales) ---',
    ('FIRMS_MAP_KEY=' + (ValorEnv $FirmsKey)),
    ('CDSAPI_KEY=' + (ValorEnv $CdsKey)),
    ('EARTHDATA_USER=' + (ValorEnv $EarthdataUser)),
    ('EARTHDATA_PASSWORD=' + (ValorEnv $EarthdataPassword))
)
$destino = Join-Path $raiz '.env'
$utf8SinBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($destino, (($lineas -join "`r`n") + "`r`n"), $utf8SinBom)
Ok "escribí $destino"


Paso '[5/6] Validación de docker-compose.yml'
& docker compose config --quiet 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Fallar 'docker-compose.yml no valida con el .env generado. Corré "docker compose config" para ver el detalle.'
}
Ok 'la configuración es válida.'

if ($SoloConfigurar) {
    Write-Host "`nListo: configuré .env. Para levantar la app: docker compose up -d --build" -ForegroundColor Green
    exit 0
}


Paso '[6/6] Levantando la app (el primer build tarda varios minutos)'
& docker compose up -d --build
if ($LASTEXITCODE -ne 0) {
    Fallar 'el build o el arranque falló: mirá la salida de arriba.'
}

$url = "http://127.0.0.1:$Port"
$limite = (Get-Date).AddMinutes(6)
$salud = $null
Write-Host '  esperando a que la API responda...'
while ((Get-Date) -lt $limite) {
    try {
        $salud = Invoke-RestMethod -Uri "$url/api/health" -TimeoutSec 4 -ErrorAction Stop
        if ($salud.ok) { break }
    } catch {
        $salud = $null
    }
    Start-Sleep -Seconds 3
}

if (-not $salud) {
    Fallar 'la app no respondió en 6 minutos. Mirá los logs con: docker compose logs --tail 50 app'
}
Ok 'la API responde.'

Write-Host ''
Write-Host '  Listo. Abrí esta dirección en el navegador:' -ForegroundColor Green
Write-Host "    $url" -ForegroundColor White
Write-Host ''
if (-not $salud.repo_ready) {
    Write-Host '  !  El pipeline no quedó listo (repo_ready=false). Mirá "docker compose logs app".' -ForegroundColor Yellow
}
if (-not $salud.data_root_exists) {
    Write-Host '  !  La carpeta de datos no se ve desde el contenedor. Revisá DATA_DIR en .env.' -ForegroundColor Yellow
}
Write-Host ("  datos: {0}  ({1} productos)" -f $salud.data_root, $salud.productos)
Write-Host '  Para apagarla: docker compose down'
