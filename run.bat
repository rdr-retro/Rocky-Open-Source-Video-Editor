@echo off
REM Rocky Video Editor - Run Script for Windows

echo ========================================
echo   Rocky Video Editor
echo ========================================
echo.

REM Check if venv exists
if not exist "venv" (
    echo ERROR: Entorno virtual no encontrado.
    echo Ejecuta compile.bat primero.
    pause
    exit /b 1
)

REM Activate venv
call venv\Scripts\activate.bat

REM Set environment
set PYTHONPATH=%CD%;%PYTHONPATH%

REM Launch application
python -m src.ui.rocky_ui

pause
