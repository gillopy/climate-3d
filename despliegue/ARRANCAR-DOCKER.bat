@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Climate 3D - Docker

echo ==========================================
echo    Climate 3D en Docker
echo ==========================================
echo.

where docker >nul 2>&1
if errorlevel 1 goto sin_docker

echo [1/3] Verificando Docker...
docker info >nul 2>&1
if not errorlevel 1 goto docker_ok

echo       Docker esta apagado. Arrancandolo...
docker desktop start -d >nul 2>&1
if not errorlevel 1 goto esperar

if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" goto lanzar_programfiles
if exist "%LOCALAPPDATA%\Programs\DockerDesktop\Docker Desktop.exe" goto lanzar_usuario

echo       No encontre Docker Desktop instalado: abrilo a mano.
goto esperar

:lanzar_programfiles
start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
goto esperar

:lanzar_usuario
start "" "%LOCALAPPDATA%\Programs\DockerDesktop\Docker Desktop.exe"
goto esperar

:esperar
timeout /t 5 /nobreak >nul
docker info >nul 2>&1
if not errorlevel 1 goto docker_ok
set /a n+=1
if !n! LSS 36 goto esperar

echo.
echo [x] Docker no respondio en 3 minutos.
echo     Abri Docker Desktop a mano, espera a que diga "Engine running"
echo     y volve a ejecutar este archivo.
echo.
pause
exit /b 1

:docker_ok
echo       ok, Docker responde.
echo.

echo [2/3] Verificando la aplicacion...
docker image inspect climate3d:local >nul 2>&1
if errorlevel 1 goto sin_imagen
set "YA_EXISTIA=1"
goto imagen_ok

:sin_imagen
if not exist "%~dp0climate3d-image.tar" goto compilar
echo       Primera vez: cargando la imagen (tarda un minuto)...
docker load -i "%~dp0climate3d-image.tar"
if errorlevel 1 goto fallo
set "YA_EXISTIA=1"
echo       ok.
goto imagen_ok

:compilar
echo       No hay imagen local: se compila ahora (10-20 minutos la primera vez).

:imagen_ok
rem --- sello del commit: que Docker no sirva codigo viejo sin avisar ----------
set "COMMIT="
for /f "delims=" %%i in ('git -C "%~dp0.." rev-parse --short HEAD 2^>nul') do set "COMMIT=%%i"
if defined COMMIT set "CLIMATE3D_COMMIT=%COMMIT%"
if not defined YA_EXISTIA goto imagen_lista
if not defined COMMIT goto imagen_lista

set "IMAGEN_COMMIT="
docker image inspect climate3d:local --format "{{.Config.Labels.climate3d_commit}}" > "%TEMP%\climate3d_commit.txt" 2>nul
if exist "%TEMP%\climate3d_commit.txt" set /p IMAGEN_COMMIT=<"%TEMP%\climate3d_commit.txt"
del "%TEMP%\climate3d_commit.txt" >nul 2>&1

if not defined IMAGEN_COMMIT goto imagen_sin_sello
if /i "%IMAGEN_COMMIT%"=="%COMMIT%" goto imagen_lista

echo.
echo       ! La imagen se compilo con el commit %IMAGEN_COMMIT% y el repo esta en %COMMIT%.
echo         En Docker quedaria la app vieja y no te vas a enterar.
choice /c SN /n /m "  La recompilo ahora? Tarda 10-20 minutos [S/N] "
if errorlevel 2 goto imagen_lista
echo       Compilando...
docker compose build
if errorlevel 1 goto fallo
goto imagen_lista

:imagen_sin_sello
echo.
echo       ! La imagen no dice con que commit se compilo (vino de un .tar o es vieja).
echo         No puedo verificar si esta al dia.
goto imagen_lista

:imagen_lista
echo.
echo [3/3] Configurando la carpeta de datos y las claves...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
if errorlevel 1 goto fallo

echo.
echo Abriendo el navegador...
start "" "http://127.0.0.1:8080"

echo.
echo ==========================================
echo    Listo. La app queda corriendo en Docker.
echo.
echo    Para apagarla: doble clic en APAGAR.bat
echo ==========================================
echo.
pause
exit /b 0

:sin_docker
echo [x] Docker Desktop no esta instalado.
echo.
echo     1. Se va a abrir la pagina de descarga.
echo     2. Instalalo con las opciones por defecto.
echo     3. Si te pide reiniciar, reinicia.
echo     4. Volve a ejecutar este archivo.
echo.
pause
start "" "https://www.docker.com/products/docker-desktop/"
exit /b 1

:fallo
echo.
echo [x] Algo fallo.
echo     Copia el texto de arriba y mandalo.
echo.
pause
exit /b 1
