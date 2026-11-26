@echo off
cd /d "%~dp0"
title Climate 3D
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ARRANCAR.ps1" %*
rem La espera pisa errorlevel: hay que guardarlo antes de mostrarlo.
set "codigo=%errorlevel%"
if "%codigo%"=="0" exit /b 0
rem Arranque fallido: unos segundos para leer el motivo y la ventana se cierra
rem sola. `ping` y no `timeout` porque `timeout` no funciona cuando la entrada
rem viene redirigida (por ejemplo, lanzado desde otro script).
echo.
ping -n 13 127.0.0.1 >nul
exit /b %codigo%
