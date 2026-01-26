#!/bin/bash
# Rocky Video Editor - Robust Multi-Platform Run Script
# Supports: macOS, Linux

# 1. Verification
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Compiling first..."
    chmod +x compile.sh
    ./compile.sh
fi

# 2. Environment Setup
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

# 3. Engine Check
# Check for any compiled module: rocky_core.so or rocky_core.pyd
if ! ls rocky_core.*.so &> /dev/null && ! ls rocky_core.*.pyd &> /dev/null; then
    echo "Compiled engine (rocky_core) not found. Compiling now..."
    ./compile.sh
fi

export PYTHONPATH="$(pwd):$PYTHONPATH"
export QT_AUTO_SCREEN_SCALE_FACTOR=1

# 4. Launch
echo "Starting Rocky Video Editor..."
python -m src.ui.rocky_ui
