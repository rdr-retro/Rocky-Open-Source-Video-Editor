#!/bin/bash

# --- Rocky Video Editor: Bootstrapper ---

echo "--- Iniciando Rocky Video Editor ---"

# 1. Comprobar Python 3
if ! command -v python3 &> /dev/null
then
    echo "ERROR: Python 3 no está instalado."
    echo "Por favor, descarga Python desde https://www.python.org/downloads/"
    exit 1
fi

# 2. Gestionar Entorno Virtual (VENV)
if [ ! -d "venv" ]; then
    echo "Creando entorno virtual aislado..."
    python3 -m venv venv
fi

# Activar venv
source venv/bin/activate

# 3. Instalar dependencias
echo "Verificando dependencias..."
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install PyQt5
fi

# 4. Compilar el Core (C++) si es necesario
echo "Compilando motor C++ (Core)..."
python3 setup.py build_ext --inplace

# 5. Ejecutar la Aplicación
echo "Lanzando UI..."
export PYTHONPATH=$PYTHONPATH:.
export PYTHONPYCACHEPREFIX="$(pwd)/.pycache"
python3 -m src.ui.rocky_ui

echo "--- Rocky Video Editor Cerrado ---"
