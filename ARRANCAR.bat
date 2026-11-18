@echo off
cd /d "%~dp0"
title Climate 3D
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ARRANCAR.ps1" %*
if errorlevel 1 pause
