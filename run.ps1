# Rocky Video Editor - PowerShell Run Script
# Compatible with Windows 10/11

# 1. Verification
if (-not (Test-Path "venv")) {
    Write-Host "[INFO] Virtual environment not found. Running compilation..." -ForegroundColor Yellow
    powershell -ExecutionPolicy Bypass -File .\compile.ps1
}

$VenvScripts = Join-Path "venv" "Scripts"
$VenvPython = Join-Path $VenvScripts "python.exe"
$VenvPip = Join-Path $VenvScripts "pip.exe"

# 2. Integrity Check
Write-Host "[INFO] Checking dependencies..." -ForegroundColor Yellow
& $VenvPython -c "import PySide6" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[INFO] Missing dependencies. Installing..." -ForegroundColor Yellow
    & $VenvPip install -r requirements.txt
}

# Check for compiled engine
$EngineFound = $false
if (Get-ChildItem "rocky_core*.pyd" -ErrorAction SilentlyContinue) { $EngineFound = $true }

if (-not $EngineFound) {
    Write-Host "[INFO] Compiled engine not found. Building..." -ForegroundColor Yellow
    powershell -ExecutionPolicy Bypass -File .\compile.ps1
}

# 3. Environment Setup
$env:PYTHONPATH = (Get-Location).Path + ";" + $env:PYTHONPATH

# Add FFmpeg DLLs to PATH for runtime
$FFmpegBin = Join-Path (Get-Location) "external\ffmpeg\bin"
if (Test-Path $FFmpegBin) {
    $env:PATH = "$FFmpegBin;" + $env:PATH
}

# 4. Launch
Write-Host "[INFO] Starting Rocky Video Editor..." -ForegroundColor Green
& $VenvPython -m src.ui.rocky_ui
if ($LASTEXITCODE -ne 0) {
    Write-Error "[ERROR] Application crashed with exit code $LASTEXITCODE"
    Pause
}
