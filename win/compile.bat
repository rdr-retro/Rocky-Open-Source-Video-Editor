@echo off
REM Rocky Video Editor - Windows Build Script
REM Compatible with Windows 10/11
REM For Mac/Linux support, use compile.sh

echo ========================================
echo   Rocky Video Editor - Build System
echo ========================================

REM 1. Python Check
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    goto :found_python
)

echo Python not found! Checking for 'py' launcher...
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    goto :found_python
)

echo Python not found! Please install Python 3.12+ from python.org
pause
exit /b 1

:found_python
%PYTHON_CMD% --version

REM 2. Environment Setup
if exist "venv" goto :venv_exists
echo Creating virtual environment...
%PYTHON_CMD% -m venv venv
if %errorlevel% neq 0 (
    echo Failed to create venv.
    pause
    exit /b 1
)

:venv_exists
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo Failed to activate venv.
    pause
    exit /b 1
)

echo Upgrading pip and installing requirements...
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install requirements.
    pause
    exit /b 1
)

REM 3. FFmpeg Check
echo Checking for FFmpeg...
if exist "external\ffmpeg" goto :ffmpeg_exists
echo Downloading and setting up FFmpeg for Windows...
python scripts/download_ffmpeg_win.py
if %errorlevel% neq 0 (
    echo Failed to download FFmpeg.
    pause
    exit /b 1
)
:ffmpeg_exists

REM Add FFmpeg to PATH for this session
set "PATH=%CD%\external\ffmpeg\bin;%PATH%"
set "LIB=%CD%\external\ffmpeg\lib;%LIB%"
set "INCLUDE=%CD%\external\ffmpeg\include;%INCLUDE%"

REM 4. Core Engine Compilation
echo Compiling Rocky Core C++...
python setup.py build_ext --inplace
if %errorlevel% neq 0 (
    echo Compilation FAILED.
    pause
    exit /b 1
)

REM 5. Plugin Compilation
if not exist "plugins" goto :skip_plugins
echo Checking for MSVC compiler (cl.exe)...
where cl >nul 2>&1
if %errorlevel% neq 0 (
    echo Compiler cl.exe not found in PATH.
    echo Tip: Run this from a "Developer Command Prompt for VS".
    echo Skipping plugin compilation.
    goto :skip_plugins
)

echo Compiling OFX Plugins...
pushd plugins
cl /O2 /LD /I"../src/core/ofx/include" invert.cpp /Fe:invert.ofx
if %errorlevel% neq 0 (
    echo Plugin compilation failed.
    popd
    pause
    exit /b 1
)
del *.obj
popd

:skip_plugins
echo.
echo ========================================
echo   COMPILATION FINISHED
echo ========================================
pause
