@echo off
chcp 65001 >nul
title Vigela - Công Cụ Trích Xuất Tọa Độ & Chiều Dài Cạnh Thửa Đất (MicroStation V8i)

echo ======================================================================
echo   Vigela - Trích Xuất Tọa Độ & Chiều Dài Cạnh Thửa Đất (MicroStation V8i)
echo ======================================================================
echo.
echo [*] Đang kiểm tra môi trường và khởi động công cụ...

set "SCRIPT_PATH=%~dp0tools_gui\cadastral_extractor.py"
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

start "" "%PYTHON_EXE%" "%SCRIPT_PATH%"

exit /b 0
