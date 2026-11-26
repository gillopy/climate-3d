@echo off
cd /d "%~dp0"
title Climate 3D - apagar

echo Apagando Climate 3D...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0apagar.ps1" %*
rem La espera pisa errorlevel: hay que guardarlo antes de mostrarlo.
set "codigo=%errorlevel%"
if "%codigo%"=="0" exit /b 0
rem Si fallo, la ventana se queda unos segundos para que se lea el motivo y se
rem cierra sola. `ping` y no `timeout` porque `timeout` no funciona cuando la
rem entrada viene redirigida (por ejemplo, lanzado desde otro script).
echo.
ping -n 13 127.0.0.1 >nul
exit /b %codigo%
