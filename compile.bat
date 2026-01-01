@echo off
setlocal enabledelayedexpansion

:: Directorio de librerías
set LIB_DIR=lib
if not exist "%LIB_DIR%" mkdir "%LIB_DIR%"

echo Verificando librerías en %LIB_DIR%...

:: Lista de librerías
set "LIBS=https://repo1.maven.org/maven2/org/bytedeco/javacv/1.5.9/javacv-1.5.9.jar https://repo1.maven.org/maven2/org/bytedeco/javacv-platform/1.5.9/javacv-platform-1.5.9.jar https://repo1.maven.org/maven2/org/bytedeco/javacpp/1.5.9/javacpp-1.5.9.jar https://repo1.maven.org/maven2/org/bytedeco/javacpp/1.5.9/javacpp-1.5.9-linux-x86_64.jar https://repo1.maven.org/maven2/org/bytedeco/javacpp/1.5.9/javacpp-1.5.9-macosx-arm64.jar https://repo1.maven.org/maven2/org/bytedeco/javacpp/1.5.9/javacpp-1.5.9-macosx-x86_64.jar https://repo1.maven.org/maven2/org/bytedeco/javacpp/1.5.9/javacpp-1.5.9-windows-x86.jar https://repo1.maven.org/maven2/org/bytedeco/javacpp/1.5.9/javacpp-1.5.9-windows-x86_64.jar https://repo1.maven.org/maven2/org/bytedeco/ffmpeg/6.0-1.5.9/ffmpeg-6.0-1.5.9.jar https://repo1.maven.org/maven2/org/bytedeco/ffmpeg/6.0-1.5.9/ffmpeg-6.0-1.5.9-linux-x86_64.jar https://repo1.maven.org/maven2/org/bytedeco/ffmpeg/6.0-1.5.9/ffmpeg-6.0-1.5.9-macosx-arm64.jar https://repo1.maven.org/maven2/org/bytedeco/ffmpeg/6.0-1.5.9/ffmpeg-6.0-1.5.9-macosx-x86_64.jar https://repo1.maven.org/maven2/org/bytedeco/ffmpeg/6.0-1.5.9/ffmpeg-6.0-1.5.9-windows-x86.jar https://repo1.maven.org/maven2/org/bytedeco/ffmpeg/6.0-1.5.9/ffmpeg-6.0-1.5.9-windows-x86_64.jar"

for %%u in (%LIBS%) do (
    set "url=%%u"
    for %%f in ("!url!") do set "filename=%%~nxf"
    if not exist "%LIB_DIR%\!filename!" (
        echo Descargando !filename!...
        curl -L "!url!" -o "%LIB_DIR%\!filename!"
    )
)

:: --- FFmpeg Standalone Download ---
set BIN_DIR=bin
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"
if not exist "%BIN_DIR%\ffmpeg.exe" (
    echo FFmpeg no encontrado en %BIN_DIR%. Descargando version portable...
    set "FFMPEG_URL=https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    curl -L "!FFMPEG_URL!" -o "%BIN_DIR%\ffmpeg.zip"
    echo Extrayendo FFmpeg...
    powershell -Command "Expand-Archive -Path '%BIN_DIR%\ffmpeg.zip' -DestinationPath '%BIN_DIR%\temp' -Force"
    move "%BIN_DIR%\temp\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe" "%BIN_DIR%\ffmpeg.exe"
    move "%BIN_DIR%\temp\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe" "%BIN_DIR%\ffprobe.exe"
    rd /s /q "%BIN_DIR%\temp"
    del "%BIN_DIR%\ffmpeg.zip"
    echo FFmpeg configurado exitosamente.
)

echo Compilando proyecto...
javac -cp "lib/*;." a/visor/*.java a/mastersound/*.java b/timeline/*.java c/toolbar/*.java egine/media/*.java egine/engine/*.java egine/render/*.java egine/persistence/*.java egine/blueline/*.java propiedades/*.java propiedades/timelinekeyframes/*.java MainAB.java

if %errorlevel% equ 0 (
    echo Compilación exitosa.
) else (
    echo Error en la compilación.
    exit /b 1
)

pause
