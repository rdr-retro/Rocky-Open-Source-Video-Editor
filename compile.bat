@echo off
REM Rocky Video Editor - Windows Build Script

echo ========================================
echo   Rocky Video Editor - Build System
echo ========================================

REM 1. Python Check
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found! Please install Python 3.12+ from python.org
    pause
    exit /b 1
)

REM 2. Environment Setup
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat

echo Upgrading pip and installing requirements...
python -m pip install --upgrade pip
pip install -r requirements.txt

REM 3. Core Engine Compilation
echo Compiling Rocky Core C++...
python setup.py build_ext --inplace

REM 4. Plugin Compilation (Requires MSVC)
if exist "plugins" (
    echo Checking for MSVC compiler (cl.exe)...
    where cl >nul 2>&1
    if %errorlevel% equ 0 (
        echo Compiling OFX Plugins...
        cd plugins
        cl /O2 /LD /I"../src/core/ofx/include" invert.cpp /Fe:invert.ofx
        del *.obj
        cd ..
    ) else (
        echo Compiler cl.exe not found in PATH. 
        echo Tip: Run this from a "Developer Command Prompt for VS".
    )
)

echo.
echo ========================================
echo   COMPILATION FINISHED
echo ========================================
pause
