# Build Script for Standalone Rocky Installer EXE
# Bundles the installer logic and UI into a single file with an embedded Python interpreter.

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Generando RockyInstaller.exe (.onefile)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Ensure build dependencies are in the CURRENT environment
python -m pip install --upgrade pyinstaller pyside6

# 2. Build the Installer Wrapper
# --onefile: Bundles everything into a single EXE
# --noconsole: Prevents the background terminal window
# --add-data: Includes the core and gui folder inside the EXE bundle
& pyinstaller --noconsole --onefile --uac-admin --icon="logo.ico" --version-file="version.txt" --name "RockyInstaller" `
    --add-data "installer/core;core" `
    --add-data "installer/gui;gui" `
    --add-data "logo.png;." `
    --add-data "logo.ico;." `
    --add-data "requirements.txt;." `
    --add-data "setup.py;." `
    --add-data "src;src" `
    --hidden-import "urllib.request" `
    --hidden-import "urllib.error" `
    --hidden-import "xml.etree.ElementTree" `
    --hidden-import "ctypes" `
    --hidden-import "platform" `
    --hidden-import "socket" `
    --clean `
    installer/main.py

Write-Host "`n[EXITO] Instalador generado en: dist/RockyInstaller.exe" -ForegroundColor Green
Write-Host "Este archivo ya es 100% independiente y contiene su propio Python para ejecutarse." -ForegroundColor Gray
