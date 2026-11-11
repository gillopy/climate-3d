@echo off
cd /d "%~dp0"
title Climate 3D - apagar

echo Apagando Climate 3D...
echo.
docker compose down
echo.
echo Listo. Tus datos y tus salidas no se borraron.
echo.
pause
