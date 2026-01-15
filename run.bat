@echo off
REM Rocky Video Editor - Windows Run Script

if not exist "venv" (
    echo Engine not found. Running compilation...
    call compile.bat
)

call venv\Scripts\activate.bat

REM Check for compiled module
if not exist "rocky_core*.pyd" (
    if not exist "rocky_core*.so" (
        echo Compiled engine not found. Compiling now...
        call compile.bat
    )
)

set PYTHONPATH=%CD%;%PYTHONPATH%

echo Starting Rocky Video Editor...
python -m src.ui.rocky_ui
pause
