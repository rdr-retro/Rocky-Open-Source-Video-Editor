# Build Script for Standalone Rocky Installer EXE
# Bundles the installer logic and UI into a single file with an embedded Python interpreter.

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Generando RockyInstaller.exe (.onefile)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Ensure build dependencies are in the CURRENT environment
python -m pip install --upgrade pyinstaller pyside6

# 2. Build the Installer Wrapper
pyinstaller RockyInstaller.spec --clean

Write-Host "`n[EXITO] Instalador generado en: dist/RockyInstaller.exe" -ForegroundColor Green
Write-Host "Este archivo ya es 100% independiente y contiene su propio Python para ejecutarse." -ForegroundColor Gray
