@echo off
setlocal enabledelayedexpansion

echo === Rocky Video Editor - Windows Compilation Script ===

:: 1. Setup Directories
set LIB_DIR=lib
set BIN_DIR=bin
if not exist "%LIB_DIR%" mkdir "%LIB_DIR%"
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"

:: 2. Automated Dependency Management
echo Verificando dependencias en %LIB_DIR%...

set "LIBS=https://repo1.maven.org/maven2/org/bytedeco/javacv/1.5.9/javacv-1.5.9.jar https://repo1.maven.org/maven2/org/bytedeco/javacv-platform/1.5.9/javacv-platform-1.5.9.jar https://repo1.maven.org/maven2/org/bytedeco/javacpp/1.5.9/javacpp-1.5.9.jar https://repo1.maven.org/maven2/org/bytedeco/javacpp/1.5.9/javacpp-1.5.9-linux-x86_64.jar https://repo1.maven.org/maven2/org/bytedeco/javacpp/1.5.9/javacpp-1.5.9-macosx-arm64.jar https://repo1.maven.org/maven2/org/bytedeco/javacpp/1.5.9/javacpp-1.5.9-macosx-x86_64.jar https://repo1.maven.org/maven2/org/bytedeco/javacpp/1.5.9/javacpp-1.5.9-windows-x86.jar https://repo1.maven.org/maven2/org/bytedeco/javacpp/1.5.9/javacpp-1.5.9-windows-x86_64.jar https://repo1.maven.org/maven2/org/bytedeco/ffmpeg/6.0-1.5.9/ffmpeg-6.0-1.5.9.jar https://repo1.maven.org/maven2/org/bytedeco/ffmpeg/6.0-1.5.9/ffmpeg-6.0-1.5.9-linux-x86_64.jar https://repo1.maven.org/maven2/org/bytedeco/ffmpeg/6.0-1.5.9/ffmpeg-6.0-1.5.9-macosx-arm64.jar https://repo1.maven.org/maven2/org/bytedeco/ffmpeg/6.0-1.5.9/ffmpeg-6.0-1.5.9-macosx-x86_64.jar https://repo1.maven.org/maven2/org/bytedeco/ffmpeg/6.0-1.5.9/ffmpeg-6.0-1.5.9-windows-x86.jar https://repo1.maven.org/maven2/org/bytedeco/ffmpeg/6.0-1.5.9/ffmpeg-6.0-1.5.9-windows-x86_64.jar"

for %%u in (%LIBS%) do (
    set "url=%%u"
    for %%f in ("!url!") do set "filename=%%~nxf"
    if not exist "%LIB_DIR%\!filename!" (
        echo Descargando !filename!...
        curl -L "!url!" -o "%LIB_DIR%\!filename!"
    )
)

:: 3. Compilation
echo Compilando codigo fuente...
dir /s /b src\*.java > sources.txt
javac -encoding UTF-8 -d bin -cp "lib/*;src" @sources.txt

if %errorlevel% equ 0 (
    echo ===============================
    echo ¡Compilacion exitosa!
    echo Usa run.bat para iniciar.
    echo ===============================
) else (
    echo Error en la compilacion.
    exit /b 1
)

del sources.txt
pause
