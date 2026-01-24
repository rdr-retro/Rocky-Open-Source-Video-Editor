@echo off
setlocal enabledelayedexpansion

REM Rocky Video Editor - Robust Windows Build Script
REM Compatible with Windows 10/11

echo ========================================
echo   Rocky Video Editor - Build System
echo ========================================

REM 1. Python Discovery
set PYTHON_CMD=python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    set PYTHON_CMD=py
    py --version >nul 2>&1
    if !errorlevel! neq 0 (
        echo [ERROR] Python not found. Please install Python 3.12+ 
        echo from https://www.python.org/
        pause
        exit /b 1
    )
)

echo [INFO] Using: %PYTHON_CMD%
%PYTHON_CMD% --version

REM 2. Environment Setup
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    %PYTHON_CMD% -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
)

echo [INFO] Activating environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate environment.
    pause
    exit /b 1
)

echo [INFO] Upgrading toolchain and installing requirements...
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)

REM 3. FFmpeg Check/Setup
echo [INFO] Checking for FFmpeg...
if not exist "external\ffmpeg" (
    if exist "scripts\download_ffmpeg_win.py" (
        echo [INFO] Downloading FFmpeg for Windows...
        python scripts/download_ffmpeg_win.py
    ) else (
        echo [WARN] external\ffmpeg not found and scripts\download_ffmpeg_win.py missing.
        echo Please ensure FFmpeg binaries are in external\ffmpeg\bin
    )
)

REM Add FFmpeg to PATH for this session
if exist "%CD%\external\ffmpeg\bin" (
    set "PATH=%CD%\external\ffmpeg\bin;%PATH%"
    set "LIB=%CD%\external\ffmpeg\lib;%LIB%"
    set "INCLUDE=%CD%\external\ffmpeg\include;%INCLUDE%"
)

REM 4. Core Engine Compilation
echo [INFO] Compiling Rocky Core C++...
python setup.py build_ext --inplace
if %errorlevel% neq 0 (
    echo [ERROR] Compilation FAILED.
    pause
    exit /b 1
)

REM 5. Plugin Compilation
echo [INFO] Compiling Plugins...
python scripts/compile_plugins.py
if %errorlevel% neq 0 (
    echo [WARN] Plugin compilation encountered errors.
)
echo.
echo ========================================
echo   COMPILATION FINISHED
echo ========================================
echo Run the editor with: run.bat
pause
