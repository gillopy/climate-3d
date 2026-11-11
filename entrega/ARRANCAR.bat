@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Climate 3D

echo ==========================================
echo    Climate 3D - instalar y arrancar
echo ==========================================
echo.

where docker >nul 2>&1
if errorlevel 1 goto sin_docker

echo [1/3] Verificando Docker...
docker info >nul 2>&1
if not errorlevel 1 goto docker_ok

echo       Docker esta apagado. Arrancandolo...
docker desktop start >nul 2>&1
if errorlevel 1 start "" "Docker Desktop"

set /a n=0
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

echo [2/3] Configurando la aplicacion...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
if errorlevel 1 goto fallo

echo.
echo [3/3] Abriendo el navegador...
start "" "http://127.0.0.1:8080"

echo.
echo ==========================================
echo    Listo. La app queda corriendo.
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
echo [x] Algo fallo durante la configuracion.
echo     Copia el texto de arriba y mandalo.
echo.
pause
exit /b 1
