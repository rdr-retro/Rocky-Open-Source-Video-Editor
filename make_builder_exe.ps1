Write-Host "Creating builder_runner.exe with PyInstaller..."

# Check if PyInstaller is installed
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "PyInstaller not found. Installing..."
    pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to install PyInstaller."
        exit 1
    }
}

# Run PyInstaller
# --onefile: Create a single exe
# --clean: Clean cache
# --name: Name of the output exe
pyinstaller --onefile --clean --name "RockyBuilder" builder_runner.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build successful."
    if (Test-Path "dist\RockyBuilder.exe") {
        Write-Host "Moving executable to root..."
        Move-Item -Path "dist\RockyBuilder.exe" -Destination ".\RockyBuilder.exe" -Force
        Write-Host "RockyBuilder.exe is ready in the root folder."
    }
}
else {
    Write-Error "Build failed."
}
