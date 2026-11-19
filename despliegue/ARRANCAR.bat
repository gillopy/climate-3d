@echo off
cd /d "%~dp0"
title Climate 3D
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ARRANCAR.ps1" %*
rem pause pisa errorlevel: hay que guardarlo antes de mostrarlo.
set "codigo=%errorlevel%"
if not "%codigo%"=="0" pause
exit /b %codigo%
