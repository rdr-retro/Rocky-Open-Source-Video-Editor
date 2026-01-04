#!/bin/bash
echo "=== Rocky Video Editor - Compilation Script ==="

# 1. Setup Directories
mkdir -p lib bin

# 2. Automated Dependency Management
echo "Verificando dependencias en lib/..."

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

for url in "${LIBS[@]}"; do
    filename=$(basename "$url")
    if [ ! -f "lib/$filename" ]; then
        echo "Descargando $filename..."
        curl -L "$url" -o "lib/$filename"
    fi
done

# 3. Compilation
echo "Compilando código fuente..."
find src -name "*.java" > sources.txt
# Use bin_temp to avoid permission issues found previously
mkdir -p bin_temp
javac -encoding UTF-8 -d bin_temp -cp "lib/*:src" @sources.txt

if [ $? -eq 0 ]; then
    # 4. Plugin Packaging
    echo "Compilando y empaquetando plugins..."
    mkdir -p bin_plugins
    find plugins_src -name "*.java" > plugins_sources.txt
    javac -encoding UTF-8 -d bin_plugins -cp "lib/*:bin_temp" @plugins_sources.txt
    cp -r plugins_src/META-INF bin_plugins/
    mkdir -p plugins
    jar cf plugins/samples.jar -C bin_plugins .
    rm plugins_sources.txt
    rm -rf bin_plugins

    echo "==============================="
    echo "¡Compilación exitosa!"
    echo "Plugins empaquetados en plugins/samples.jar"
    echo "Usa ./run.sh para iniciar."
    echo "==============================="
else
    echo "Error en la compilación del núcleo."
    exit 1
fi
rm sources.txt
