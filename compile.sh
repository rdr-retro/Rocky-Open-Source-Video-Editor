#!/bin/bash

# Script para compilar el núcleo C++ (Linux/macOS)

echo "--- Compilando Rocky Core ---"

# 1. Asegurar que el entorno virtual existe y tiene las dependencias
if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv venv
fi

source venv/bin/activate
echo "Verificando dependencias (setuptools, pybind11, pyqt5)..."
pip install -r requirements.txt

# 2. Compilar
echo "Ejecutando setup.py..."
python3 setup.py build_ext --inplace

echo "--- Compilación finalizada ---"
