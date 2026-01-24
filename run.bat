@echo off
setlocal enabledelayedexpansion

REM Rocky Video Editor - Robust Windows Run Script

REM 1. Verification
if not exist "venv" (
    echo [INFO] Virtual environment not found. Running compilation...
    call compile.bat
)

REM 2. Environment Activation
echo [INFO] Activating environment...
call venv\Scripts\activate.bat
if !errorlevel! neq 0 (
    echo [ERROR] Failed to activate venv.
    pause
    exit /b 1
)

REM 3. Integrity Check
python -c "import PySide6" >nul 2>&1
if !errorlevel! neq 0 (
    echo [INFO] Missing dependencies. Installing...
    pip install -r requirements.txt
)

REM Check for any compiled module: rocky_core.pyd or rocky_core.so
set FOUND_ENGINE=0
if exist "rocky_core*.pyd" set FOUND_ENGINE=1
if exist "rocky_core*.so" set FOUND_ENGINE=1

if !FOUND_ENGINE! equ 0 (
    echo [INFO] Compiled engine not found. Building...
    call compile.bat
)

REM 4. Environment Setup
set PYTHONPATH=%CD%;%PYTHONPATH%

REM Add FFmpeg DLLs to PATH for runtime
if exist "%CD%\external\ffmpeg\bin" (
    set "PATH=%CD%\external\ffmpeg\bin;%PATH%"
)

REM 5. Launch
echo [INFO] Starting Rocky Video Editor...
python -m src.ui.rocky_ui
if %errorlevel% neq 0 (
    echo [ERROR] Application crashed with exit code %errorlevel%
    pause
)
