#!/bin/bash
# Rocky Video Editor - Run Script for macOS/Linux

echo "========================================"
echo "  Rocky Video Editor"
echo "========================================"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "ERROR: Entorno virtual no encontrado."
    echo "Ejecuta ./compile.sh primero."
    exit 1
fi

# Activate venv
source venv/bin/activate

# Set environment
export PYTHONPATH="$(pwd):$PYTHONPATH"
export QT_AUTO_SCREEN_SCALE_FACTOR=1

# Launch application
python -m src.ui.rocky_ui
