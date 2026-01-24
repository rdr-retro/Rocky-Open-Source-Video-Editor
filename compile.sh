#!/bin/bash
# Rocky Video Editor - Robust Multi-Platform Compile Script
# Supports: macOS, Linux (Ubuntu, Fedora, Arch)

echo "========================================"
echo "  Rocky Video Editor - Build System"
echo "========================================"

# 1. OS Detection
OS="$(uname)"
echo "Detected OS: $OS"

# 2. Dependency Check
if [ "$OS" == "Darwin" ]; then
    # macOS Logic
    if ! command -v brew &> /dev/null; then
        echo "Note: Homebrew is recommended (https://brew.sh)"
    else
        echo "Updating dependencies via Homebrew..."
        brew install ffmpeg pkg-config python@3.12
    fi
    
    if ! command -v clang++ &> /dev/null; then
        echo "Installing Xcode Command Line Tools..."
        xcode-select --install
    fi
elif [ "$OS" == "Linux" ]; then
    # Linux Logic - Attempt to detect package manager
    if command -v apt-get &> /dev/null; then
        echo "Detected Debian/Ubuntu system..."
        sudo apt-get update
        sudo apt-get install -y build-essential python3-dev libavformat-dev libavcodec-dev libswscale-dev libavutil-dev libswresample-dev pkg-config
    elif command -v dnf &> /dev/null; then
        echo "Detected Fedora/RHEL system..."
        sudo dnf install -y gcc-c++ python3-devel ffmpeg-devel pkg-config
    elif command -v pacman &> /dev/null; then
        echo "Detected Arch Linux system..."
        sudo pacman -S --needed base-devel python ffmpeg pkgconf
    else
        echo "Unknown Linux distribution. Please ensure FFmpeg-devel, Python3-devel, and G++ are installed."
    fi
fi

# 3. Python Selection
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

# 4. Environment Setup
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
fi
source venv/bin/activate

echo "Upgrading toolchain..."
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# 5. Core Engine Compilation
echo "Compiling Rocky Core C++..."
# Using --inplace ensures the .so/.pyd is next to the python files
python setup.py build_ext --inplace

# 6. Plugin Compilation
echo "Compiling Plugins..."
python3 scripts/compile_plugins.py

echo ""
echo "========================================"
echo "  COMPILATION FINISHED"
echo "========================================"
echo "Run with: ./run.sh"
