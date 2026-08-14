@echo off
E:\KEIL\UV4\UV4.exe -b control.uvprojx -o build.log
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Build SUCCESS!
    echo ========================================
    type build.log | findstr /C:"Error(s)" /C:"Warning(s)"
) else (
    echo.
    echo ========================================
    echo Build FAILED!
    echo ========================================
    type build.log
)
pause
