@echo off
REM Rocky Video Editor - Standalone EXE Builder
REM Creates a single-file executable with all dependencies included.

echo ========================================
echo   Rocky Video Editor - EXE Builder
echo ========================================

REM 1. Setup Environment
if not exist "venv" (
    echo Virtual environment not found. Running compile.bat...
    call compile.bat
    if %errorlevel% neq 0 exit /b %errorlevel%
)

call venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing PyInstaller and Pillow...
pip install pyinstaller Pillow

REM 2. Ensure Core is Built
if not exist "rocky_core*.pyd" (
    echo Compiling Rocky Core...
    python setup.py build_ext --inplace
    if %errorlevel% neq 0 (
        echo Compilation failed.
        pause
        exit /b 1
    )
)

REM 2b. Ensure FFmpeg is present
if not exist "external\ffmpeg\bin\ffmpeg.exe" (
    echo FFmpeg not found. Downloading dependencies...
    python scripts/download_ffmpeg_win.py
    if %errorlevel% neq 0 (
        echo Failed to download FFmpeg.
        pause
        exit /b 1
    )
)

REM 3. Clean previous builds and kill hanging processes
echo Closing existing RockyVideoEditor instances...
taskkill /f /im RockyVideoEditor.exe >nul 2>&1
timeout /t 2 /nobreak >nul

if exist "build" (
    echo Cleaning build folder...
    rd /s /q "build"
)
if exist "dist" (
    echo Cleaning dist folder...
    rd /s /q "dist"
)

echo.
echo ========================================
echo   Building Standalone EXE with PyInstaller
echo ========================================
echo Note: This may take a few minutes. UPX is disabled for stability.

REM Arguments explanation:
REM --noconfirm: Overwrite existing
REM --onefile: Create a single .exe file
REM --windowed: No console window
REM --name: Output filename
REM --add-binary: Include FFmpeg binaries
REM --noupx: Disable UPX (essential for large torch installations to prevent freezing)

pyinstaller --noconfirm RockyVideoEditor.spec

if %errorlevel% neq 0 (
    echo.
    echo BUILD FAILED!
    pause
    exit /b 1
)

echo.
echo ========================================
echo   BUILD SUCCESSFUL!
echo ========================================
echo.
echo The executable is located in the "dist" folder:
echo   dist\RockyVideoEditor.exe
echo.
echo You can copy this .exe to any Windows PC (even without Python).
echo.
pause
