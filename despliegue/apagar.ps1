<#
.SYNOPSIS
    Apaga Climate 3D, este donde este: el contenedor de Docker o la consola nativa.

.DESCRIPTION
    Hay dos formas de levantar la app y cada una se apaga distinto:
      - ARRANCAR-DOCKER.bat  -> contenedor (docker compose down)
      - ARRANCAR.bat         -> uvicorn nativo, en una consola aparte

    Este script mira las dos. Si Docker responde, baja el contenedor. Si ademas (o
    en lugar de eso) hay un uvicorn del .venv de este repo corriendo, lo detiene.
    Si no encuentra nada, lo dice: no inventa un "listo".

    No borra datos: solo detiene procesos. Los .nc, las salidas y la cache quedan
    donde estan.

.EXAMPLE
    .\apagar.ps1

.EXAMPLE
    .\apagar.ps1 -SoloMirar      # muestra que apagaria, sin apagar nada
#>
[CmdletBinding()]
param(
    [switch]$SoloMirar
)

$ErrorActionPreference = 'Continue'
# Este script vive en despliegue/: la raiz del repo es la carpeta de arriba.
$carpeta = Split-Path -Parent $MyInvocation.MyCommand.Definition
$raizRepo = Split-Path -Parent $carpeta
$venv = Join-Path $raizRepo '.venv\Scripts'

function Ok {
    param([string]$Mensaje)
    Write-Host "  ok  $Mensaje" -ForegroundColor Green
}

function Aviso {
    param([string]$Mensaje)
    Write-Host "  !   $Mensaje" -ForegroundColor Yellow
}

function Mal {
    param([string]$Mensaje)
    Write-Host "  x   $Mensaje" -ForegroundColor Red
}

$apagado = $false
$encontrado = $false
$fallo = $false


# --- 1) Docker ---------------------------------------------------------------
# Ojo: si el daemon no responde, `docker compose down` tira el error del npipe y
# no baja nada. Por eso primero preguntamos si responde.

$dockerActivo = $false
if (Get-Command docker -ErrorAction SilentlyContinue) {
    & docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
    $dockerActivo = ($LASTEXITCODE -eq 0)
}

if (-not $dockerActivo) {
    Aviso 'Docker Desktop no esta corriendo: no hay contenedor que bajar.'
} elseif (-not (Test-Path -LiteralPath (Join-Path $carpeta '.env'))) {
    $encontrado = $true
    Aviso 'Docker responde pero falta despliegue\.env: no puedo bajar el contenedor por nombre.'
} elseif ($SoloMirar) {
    $encontrado = $true
    Aviso 'Docker responde: hay un contenedor para bajar (no lo toco, -SoloMirar).'
} else {
    $encontrado = $true
    Push-Location -LiteralPath $carpeta
    try {
        & docker compose down 2>&1 | ForEach-Object { Write-Host "      $_" }
        $codigo = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    if ($codigo -eq 0) {
        Ok 'contenedor de Docker detenido.'
        $apagado = $true
    } else {
        Mal ("docker compose down fallo (codigo {0})." -f $codigo)
        $fallo = $true
    }
}


# --- 2) Consola nativa (uvicorn del .venv de este repo) ----------------------
# Filtramos por ruta del ejecutable ademas de "uvicorn": asi no tocamos un
# python ajeno que tambien este sirviendo algo.

$patronVenv = [regex]::Escape($venv)
$todos = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue)

$directos = @($todos | Where-Object {
    $_.CommandLine -and
    $_.Name -match '(?i)^pythonw?\.exe$' -and
    $_.CommandLine -match '(?i)uvicorn' -and
    $_.CommandLine -match $patronVenv
})

# Los hijos de un uvicorn nuestro tambien son nuestros: con `--reload` el worker
# lo levanta multiprocessing y su linea de comandos ya no dice "uvicorn". Se
# arma el arbol y se mata de adentro hacia afuera (hijo primero): asi el puerto
# no queda tomado por un worker huerfano.
$objetivos = @()
$nivel = @{}
foreach ($p in $directos) { $nivel[$p.ProcessId] = 0 }
$pendientes = @($directos)
while ($pendientes.Count -gt 0) {
    $siguientes = @()
    foreach ($p in $pendientes) {
        $objetivos += $p
        foreach ($hijo in $todos) {
            if ($hijo.ParentProcessId -ne $p.ProcessId) { continue }
            if ($hijo.Name -notmatch '(?i)^pythonw?\.exe$') { continue }
            if ($nivel.ContainsKey($hijo.ProcessId)) { continue }
            $nivel[$hijo.ProcessId] = $nivel[$p.ProcessId] + 1
            $siguientes += $hijo
        }
    }
    $pendientes = $siguientes
}
$objetivos = @($objetivos | Sort-Object { $nivel[$_.ProcessId] } -Descending)

if ($objetivos.Count -eq 0) {
    Aviso 'la consola nativa no estaba corriendo.'
} elseif ($SoloMirar) {
    $encontrado = $true
    foreach ($p in $objetivos) {
        Aviso ("apagaria el proceso {0} ({1})" -f $p.ProcessId, $p.Name)
    }
} else {
    $encontrado = $true
    $matados = 0
    foreach ($p in $objetivos) {
        # El padre puede morir junto con el hijo: no es un fallo que ya no exista.
        if (-not (Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue)) { continue }
        try {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
            Ok ("detuve el proceso {0}" -f $p.ProcessId)
            $matados++
            $apagado = $true
        } catch {
            # Si ya no existe, murio junto con su padre (o lo cerro el usuario):
            # eso es el resultado buscado, no un fallo.
            if (Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue) {
                Mal ("no pude detener el proceso {0}: {1}" -f $p.ProcessId, $_.Exception.Message)
                $fallo = $true
            } else {
                Aviso ("el proceso {0} ya habia terminado" -f $p.ProcessId)
            }
        }
    }

    Start-Sleep -Milliseconds 700
    $vivos = @($objetivos | Where-Object { Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue })
    if ($vivos.Count -gt 0) {
        Mal ("quedaron vivos: {0}" -f (($vivos | ForEach-Object { $_.ProcessId }) -join ', '))
        $fallo = $true
    } elseif ($matados -gt 0) {
        Ok 'consola nativa detenida.'
    } else {
        # Se cerro sola entre la deteccion y el apagado: no la apagamos nosotros.
        Aviso 'la consola nativa ya estaba cerrandose.'
    }
}


# --- 3) Resultado ------------------------------------------------------------

Write-Host ''
if ($fallo) {
    Mal 'Algo no se pudo apagar. Copia el texto de arriba y mandalo.'
    exit 1
}
if ($SoloMirar) {
    if ($encontrado) { Ok 'Eso es lo que apagaria. No toque nada.' }
    else { Ok 'No hay nada de Climate 3D corriendo.' }
    exit 0
}
if ($apagado) {
    Ok 'Climate 3D apagado. Tus datos y tus salidas no se borraron.'
    exit 0
}
Ok 'No hay nada de Climate 3D corriendo.'
exit 0
