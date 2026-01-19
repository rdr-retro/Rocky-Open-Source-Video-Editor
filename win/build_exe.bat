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

REM 3. Clean previous builds
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"

echo.
echo ========================================
echo   Building Standalone EXE with PyInstaller
echo ========================================
echo Note: This may take a few minutes.

REM Arguments explanation:
REM --noconfirm: Overwrite existing
REM --onefile: Create a single .exe file (extracts to temp dir at runtime)
REM --windowed: No console window (GUI only)
REM --name: Output filename
REM --clean: Clean cache
REM --add-binary: Include FFmpeg binaries. FORMAT: Source;Dest
REM               We place them in "external/ffmpeg/bin" inside the temp bundle
REM               so rocky_ui.py logic finds them.
REM --add-data: Include Image Assets. Source;Dest
REM --collect-all: Ensure PySide6 and numpy plugins are fully collected

pyinstaller --noconfirm --onefile --windowed --clean ^
    --name "RockyVideoEditor" ^
    --add-binary "external/ffmpeg/bin;external/ffmpeg/bin" ^
    --add-data "src/img;src/img" ^
    --hidden-import "rocky_core" ^
    --collect-all "PySide6" ^
    --icon "src/img/logo.png" ^
    launcher.py

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
