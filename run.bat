@echo off
setlocal

if not exist "venv" (
    echo Error: No se encontro el entorno virtual. Ejecuta compile.bat primero.
    pause
    exit /b 1
)

echo --- Iniciando Rocky Video Editor ---
call venv\Scripts\activate
python rocky_ui.py
pause
