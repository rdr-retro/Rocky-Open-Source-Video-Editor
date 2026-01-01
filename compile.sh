#!/bin/bash

# Directorio de librerías
LIB_DIR="lib"
mkdir -p "$LIB_DIR"

# Lista de librerías a descargar (JavaCV 1.5.9 y FFmpeg 6.0)
LIBS=(
    "https://repo1.maven.org/maven2/org/bytedeco/javacv/1.5.9/javacv-1.5.9.jar"
    "https://repo1.maven.org/maven2/org/bytedeco/javacv-platform/1.5.9/javacv-platform-1.5.9.jar"
    "https://repo1.maven.org/maven2/org/bytedeco/javacpp/1.5.9/javacpp-1.5.9.jar"
    "https://repo1.maven.org/maven2/org/bytedeco/javacpp/1.5.9/javacpp-1.5.9-linux-x86_64.jar"
    "https://repo1.maven.org/maven2/org/bytedeco/javacpp/1.5.9/javacpp-1.5.9-macosx-arm64.jar"
    "https://repo1.maven.org/maven2/org/bytedeco/javacpp/1.5.9/javacpp-1.5.9-macosx-x86_64.jar"
    "https://repo1.maven.org/maven2/org/bytedeco/javacpp/1.5.9/javacpp-1.5.9-windows-x86.jar"
    "https://repo1.maven.org/maven2/org/bytedeco/javacpp/1.5.9/javacpp-1.5.9-windows-x86_64.jar"
    "https://repo1.maven.org/maven2/org/bytedeco/ffmpeg/6.0-1.5.9/ffmpeg-6.0-1.5.9.jar"
    "https://repo1.maven.org/maven2/org/bytedeco/ffmpeg/6.0-1.5.9/ffmpeg-6.0-1.5.9-linux-x86_64.jar"
    "https://repo1.maven.org/maven2/org/bytedeco/ffmpeg/6.0-1.5.9/ffmpeg-6.0-1.5.9-macosx-arm64.jar"
    "https://repo1.maven.org/maven2/org/bytedeco/ffmpeg/6.0-1.5.9/ffmpeg-6.0-1.5.9-macosx-x86_64.jar"
    "https://repo1.maven.org/maven2/org/bytedeco/ffmpeg/6.0-1.5.9/ffmpeg-6.0-1.5.9-windows-x86.jar"
    "https://repo1.maven.org/maven2/org/bytedeco/ffmpeg/6.0-1.5.9/ffmpeg-6.0-1.5.9-windows-x86_64.jar"
)

echo "Verificando librerías en $LIB_DIR..."
for url in "${LIBS[@]}"; do
    filename=$(basename "$url")
    if [ ! -f "$LIB_DIR/$filename" ]; then
        echo "Descargando $filename..."
        curl -L "$url" -o "$LIB_DIR/$filename"
    fi
done

# --- FFmpeg Standalone Download ---
BIN_DIR="bin"
mkdir -p "$BIN_DIR"

if [ ! -f "$BIN_DIR/ffmpeg" ]; then
    OS_TYPE=$(uname -s)
    echo "FFmpeg no encontrado en $BIN_DIR. Detectando OS: $OS_TYPE..."
    
    if [ "$OS_TYPE" == "Linux" ]; then
        FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        echo "Descargando FFmpeg para Linux..."
        curl -L "$FFMPEG_URL" -o "$BIN_DIR/ffmpeg.tar.xz"
        tar -xJf "$BIN_DIR/ffmpeg.tar.xz" -C "$BIN_DIR" --strip-components=1
        rm "$BIN_DIR/ffmpeg.tar.xz"
    elif [ "$OS_TYPE" == "Darwin" ]; then
        FFMPEG_URL="https://evermeet.cx/ffmpeg/ffmpeg-6.0.zip"
        echo "Descargando FFmpeg para macOS..."
        curl -L "$FFMPEG_URL" -o "$BIN_DIR/ffmpeg.zip"
        unzip -o "$BIN_DIR/ffmpeg.zip" -d "$BIN_DIR"
        rm "$BIN_DIR/ffmpeg.zip"
    fi
    chmod +x "$BIN_DIR/ffmpeg"
    echo "FFmpeg configurado exitosamente."
fi

# Compilar todo el proyecto Rocky Open Source Video Editor incluyendo las librerías JavaCV
echo "Compilando proyecto..."
javac -cp "lib/*:." a/visor/*.java a/mastersound/*.java b/timeline/*.java c/toolbar/*.java egine/media/*.java egine/engine/*.java egine/render/*.java egine/persistence/*.java egine/blueline/*.java propiedades/*.java propiedades/timelinekeyframes/*.java MainAB.java

if [ $? -eq 0 ]; then
    echo "Compilación exitosa."
else
    echo "Error en la compilación."
    exit 1
fi
