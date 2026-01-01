#!/bin/bash
echo "Verificando librerías en lib..."
if [ ! -d "lib" ]; then
    mkdir lib
fi

# Note: javac needs the classpath to find dependencies and the new src structure
echo "Compilando proyecto (Estructura Rocky)..."
find src -name "*.java" > sources.txt
javac -encoding UTF-8 -d bin -cp "lib/*:src" @sources.txt
if [ $? -eq 0 ]; then
    echo "Compilación exitosa."
else
    echo "Error en la compilación."
    exit 1
fi
rm sources.txt
