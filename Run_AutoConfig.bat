@echo off
chcp 65001 >nul
title Vigela AI - MicroStation V8i 1-Click AutoConfigurator

echo ======================================================================
echo   Vigela AI - MicroStation V8i 1-Click AutoConfigurator
echo ======================================================================
echo.

set "DIST_EXE=%~dp0dist\Vigela_AutoConfig.exe"

if exist "%DIST_EXE%" (
    echo [*] Đang khởi chạy Vigela_AutoConfig.exe...
    start "" "%DIST_EXE%"
) else (
    echo [*] Khởi chạy qua môi trường Python...
    "%~dp0.venv\Scripts\python.exe" "%~dp0installer\native_configurator.py"
)

exit /b 0
