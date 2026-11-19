@echo off
cd /d "%~dp0"
title Climate 3D - apagar

echo Apagando Climate 3D...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0apagar.ps1" %*
rem pause pisa errorlevel: hay que guardarlo antes de mostrarlo.
set "codigo=%errorlevel%"
echo.
pause
exit /b %codigo%
