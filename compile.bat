@echo off
REM Rocky Video Editor - Compile Script for Windows

echo ========================================
echo   Rocky Video Editor - Compilacion
echo ========================================
echo.

REM Check if venv exists
if not exist "venv" (
    echo Creando entorno virtual...
    python -m venv venv
)

REM Activate venv
call venv\Scripts\activate.bat

REM Upgrade pip
python -m pip install --upgrade pip

REM Install dependencies
echo Instalando dependencias...
pip install setuptools pybind11
if exist "requirements.txt" (
    pip install -r requirements.txt
) else (
    pip install PySide6 numpy
)

REM Compile C++ core
echo.
echo Compilando motor C++...
python setup.py build_ext --inplace

echo.
echo Compilacion completada!
echo Ejecuta run.bat para iniciar el editor.
pause
