#!/bin/bash
# Rocky Video Editor - Robust Run Script

# 1. Verification
SO_FILE="rocky_core.cpython-312-darwin.so"
# Generic check for any .so file starting with rocky_core
if ! ls rocky_core.*.so &> /dev/null; then
    echo "Engine not found. Running compilation..."
    ./compile.sh
fi

# 2. Environment Setup
if [ ! -d "venv" ]; then
    ./compile.sh
fi
source venv/bin/activate

export PYTHONPATH="$(pwd):$PYTHONPATH"
export QT_AUTO_SCREEN_SCALE_FACTOR=1

# 3. Launch
echo "Starting Rocky Video Editor..."
python -m src.ui.rocky_ui
