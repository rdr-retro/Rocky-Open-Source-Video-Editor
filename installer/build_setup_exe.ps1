Write-Host "Compiling Installer to EXE..."

# Ensure pyinstaller and dependencies
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    pip install pyinstaller
}
pip install requests winshell pywin32

# Build the installer
# --onefile: Single exe
# --clean: Clean cache
pyinstaller RockySetup.spec --clean

if ($LASTEXITCODE -eq 0) {
    Write-Host "Installer created successfully: dist\RockySetup.exe"
}
else {
    Write-Error "Installer build failed."
}
