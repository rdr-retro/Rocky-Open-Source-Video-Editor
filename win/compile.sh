#!/bin/bash
# Rocky Video Editor - Robust Compile Script
# Supports: macOS, Linux

echo "========================================"
echo "  Rocky Video Editor - Build System"
echo "========================================"

# 1. System Dependency Check
OS="$(uname)"
echo "Detected OS: $OS"

if [ "$OS" == "Darwin" ]; then
    # macOS
    if ! command -v brew &> /dev/null; then
        echo "Tip: Homebrew is recommended for dependency management (https://brew.sh)"
    fi
    
    if ! command -v clang++ &> /dev/null; then
        echo "Installing Command Line Tools..."
        xcode-select --install
    fi
    
    # Check for FFmpeg via brew if possible
    if command -v brew &> /dev/null; then
        echo "Checking for FFmpeg libraries..."
        brew install ffmpeg pkg-config
    fi
else
    # Linux (assuming Debian/Ubuntu)
    echo "Checking for Linux build tools..."
    sudo apt-get update
    sudo apt-get install -y build-essential python3-dev libavformat-dev libavcodec-dev libswscale-dev libavutil-dev libswresample-dev
fi

# 2. Python Environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate

echo "Upgrading pip and installing requirements..."
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3. Core Engine Compilation
echo "Compiling Rocky Core C++..."
python setup.py build_ext --inplace

# 4. Plugin Compilation
if [ -d "plugins" ]; then
    echo "Compiling OFX Plugins..."
    cd plugins
    make clean
    make
    cd ..
fi

echo ""
echo "========================================"
echo "  COMPILATION SUCCESSFUL"
echo "========================================"
echo "Run the application with: ./run.sh"
