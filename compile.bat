@echo off
setlocal

echo --- Compilando Rocky Core (Windows) ---

if not exist "venv" (
    echo Creando entorno virtual...
    python -m venv venv
)

call venv\Scripts\activate
echo Instalando dependencias...
pip install -r requirements.txt

echo Compilando nucleo C++...
python setup.py build_ext --inplace

echo --- Compilacion finalizada ---
pause
