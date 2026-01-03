@echo off
rem Ejecutar Rocky Open Source Video Editor

:: Verificar que FFmpeg esté disponible en el PATH
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ===============================
    echo ADVERTENCIA: FFmpeg no encontrado en el PATH
    echo Por favor, ejecuta compile.bat primero
    echo ===============================
    echo.
    pause
    exit /b 1
)

echo Iniciando Rocky Video Editor...
java -cp "lib/*;bin" MainAB
pause


