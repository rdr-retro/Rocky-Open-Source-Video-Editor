Write-Host "Compiling Installer to EXE..."

# Ensure pyinstaller and dependencies
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    pip install pyinstaller
}
pip install requests winshell pywin32

# Build the installer
# --noconsole: Hide the console window
# --onefile: Single exe
# --clean: Clean cache
pyinstaller --noconsole --onefile --uac-admin --clean --name "RockySetup" rocky_setup.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "Installer created successfully: dist\RockySetup.exe"
}
else {
    Write-Error "Installer build failed."
}
