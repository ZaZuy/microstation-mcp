@echo off
setlocal enabledelayedexpansion

echo ======================================================================
echo   MsNativePipe - Bentley MicroStation V8i MDL Build Tool
echo ======================================================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: 1. Kiem tra xem bmake da co trong PATH chua
where bmake.exe >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Phat hien bmake trong PATH.
    goto :DO_BUILD
)

:: 2. Tim kiem Bentley MicroStation SDK
set "BENTLEY_SDK_CANDIDATES="
set "BENTLEY_SDK_CANDIDATES=%BENTLEY_SDK_CANDIDATES% C:\Program Files (x86)\Bentley\MicroStation V8i (SELECTseries)\SDK"
set "BENTLEY_SDK_CANDIDATES=%BENTLEY_SDK_CANDIDATES% C:\Bentley\SDK"
set "BENTLEY_SDK_CANDIDATES=%BENTLEY_SDK_CANDIDATES% C:\Program Files (x86)\Bentley\MicroStation_SDK"
set "BENTLEY_SDK_CANDIDATES=%BENTLEY_SDK_CANDIDATES% D:\Bentley\SDK"

for %%P in (%BENTLEY_SDK_CANDIDATES%) do (
    if exist "%%~P\bin\mstndevvars.bat" (
        echo [OK] Phat hien MicroStation SDK tai: "%%~P"
        call "%%~P\bin\mstndevvars.bat"
        goto :DO_BUILD
    )
    if exist "%%~P\mstndevvars.bat" (
        echo [OK] Phat hien MicroStation SDK tai: "%%~P"
        call "%%~P\mstndevvars.bat"
        goto :DO_BUILD
    )
)

:: 3. Tim kiem Visual Studio Command Prompts (VS2005 / VS2008 / VS2010 / VS Community)
set "VS_CANDIDATES="
set "VS_CANDIDATES=%VS_CANDIDATES% C:\Program Files (x86)\Microsoft Visual Studio 8\VC\vcvarsall.bat"
set "VS_CANDIDATES=%VS_CANDIDATES% C:\Program Files (x86)\Microsoft Visual Studio 9.0\VC\vcvarsall.bat"
set "VS_CANDIDATES=%VS_CANDIDATES% C:\Program Files (x86)\Microsoft Visual Studio 10.0\VC\vcvarsall.bat"
set "VS_CANDIDATES=%VS_CANDIDATES% C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars32.bat"
set "VS_CANDIDATES=%VS_CANDIDATES% C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars32.bat"

for %%V in (%VS_CANDIDATES%) do (
    if exist "%%~V" (
        echo [OK] Phat hien moi truong C/C++: "%%~V"
        call "%%~V" >nul 2>nul
        goto :CHECK_BMAKE_AFTER_VS
    )
)

:CHECK_BMAKE_AFTER_VS
where bmake.exe >nul 2>nul
if %ERRORLEVEL% equ 0 (
    goto :DO_BUILD
)

echo [CANH BAO] Khong tim thay cong cu bmake.exe tren he thong.
echo Neu da co file MsNativePipe.ma xay dung san, trinh cai dat se su dung file do.
exit /b 1

:DO_BUILD
echo.
echo [*] Dang bien dich MsNativePipe bang bmake...
bmake -f MsNativePipe.mke
if %ERRORLEVEL% neq 0 (
    echo [LOI] Bien dich that bai! Vui long kiem tra log o tren.
    exit /b %ERRORLEVEL%
)

echo.
echo [THANH CONG] Da bien dich thanh cong MsNativePipe!
exit /b 0
