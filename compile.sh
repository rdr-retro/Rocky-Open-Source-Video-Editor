#!/bin/bash
# Rocky Video Editor - Compile Script for macOS/Linux

echo "========================================"
echo "  Rocky Video Editor - Compilación"
echo "========================================"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
echo "Instalando dependencias..."
pip install setuptools pybind11
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install PySide6 numpy
fi

# Compile C++ core
echo ""
echo "Compilando motor C++..."
python setup.py build_ext --inplace

echo ""
echo "Compilación completada!"
echo "Ejecuta ./run.sh para iniciar el editor."
