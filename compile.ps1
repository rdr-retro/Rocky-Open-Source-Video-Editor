# Rocky Video Editor - PowerShell Build Script
# Compatible with Windows 10/11

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Rocky Video Editor - Build System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Python Discovery
$PythonCmd = "python"
try {
    & $PythonCmd --version | Out-Null
}
catch {
    $PythonCmd = "py"
    try {
        & $PythonCmd --version | Out-Null
    }
    catch {
        Write-Error "[ERROR] Python not found. Please install Python 3.12+ from https://www.python.org/"
        Pause
        exit 1
    }
}

Write-Host "[INFO] Using: $PythonCmd" -ForegroundColor Green
& $PythonCmd --version

# 2. Environment Setup
if (-not (Test-Path "venv")) {
    Write-Host "[INFO] Creating virtual environment..." -ForegroundColor Yellow
    & $PythonCmd -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Error "[ERROR] Failed to create venv."
        Pause
        exit 1
    }
}

Write-Host "[INFO] Activating environment..." -ForegroundColor Yellow
$VenvScripts = Join-Path "venv" "Scripts"
$VenvPython = Join-Path $VenvScripts "python.exe"
$VenvPip = Join-Path $VenvScripts "pip.exe"

Write-Host "[INFO] Upgrading toolchain and installing requirements..." -ForegroundColor Yellow
& $VenvPython -m pip install --upgrade pip setuptools wheel
& $VenvPip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Error "[ERROR] Dependency installation failed."
    Pause
    exit 1
}

# 3. FFmpeg Check/Setup
$ExternalDir = "external"
$FFmpegDir = Join-Path $ExternalDir "ffmpeg"
if (-not (Test-Path $FFmpegDir)) {
    Write-Host "[INFO] FFmpeg not found. Downloading..." -ForegroundColor Yellow
    if (-not (Test-Path $ExternalDir)) { New-Item -ItemType Directory -Path $ExternalDir | Out-Null }
    
    # Ensure TLS 1.2 for downloads (fixes issues in older PowerShell versions)
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    
    # URL for FFmpeg shared build (Using BtbN GitHub releases for .zip compatibility)
    $Url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl-shared.zip"
    $ZipFile = Join-Path $ExternalDir "ffmpeg.zip"
    
    Write-Host "[INFO] Downloading from $Url" -ForegroundColor Gray
    try {
        # GitHub requires following redirects
        Invoke-WebRequest -Uri $Url -OutFile $ZipFile -ErrorAction Stop -UseBasicParsing
    }
    catch {
        Write-Host "[ERROR] Failed to download from $Url" -ForegroundColor Red
        Write-Error "[ERROR] Failed to download FFmpeg. Please check your internet connection."
        Pause
        exit 1
    }
    
    Write-Host "[INFO] Extracting FFmpeg..." -ForegroundColor Yellow
    try {
        Expand-Archive -Path $ZipFile -DestinationPath $ExternalDir -Force
    }
    catch {
        Write-Error "[ERROR] Extraction failed. Please extract $ZipFile manually to $ExternalDir\ffmpeg"
        Pause
        exit 1
    }
    
    # Give the OS a moment to release locks after extraction
    Start-Sleep -Seconds 2
    
    # Organize folder (it extracts into a subfolder like 'ffmpeg-master-latest-win64-gpl-shared')
    $ExtractedDir = Get-ChildItem -Path $ExternalDir -Directory | Where-Object { $_.Name -like "ffmpeg-*" } | Select-Object -First 1
    if ($ExtractedDir) {
        $DestPath = Join-Path $ExternalDir "ffmpeg"
        if (Test-Path $DestPath) { Remove-Item $DestPath -Recurse -Force }
        
        try {
            Move-Item -Path $ExtractedDir.FullName -Destination $DestPath -Force -ErrorAction Stop
        }
        catch {
            Write-Host "[WARN] Could not rename folder automatically ($($_.Exception.Message))." -ForegroundColor Yellow
            Write-Host "[INFO] Attempting to use the subfolder directly..." -ForegroundColor Gray
            $FFmpegDir = $ExtractedDir.FullName
        }
    }
    else {
        Write-Error "[ERROR] Extraction folder structure unexpected."
        Pause
        exit 1
    }
    
    # Cleanup temporary downloads
    Get-ChildItem -Path $ExternalDir -Include "*.zip", "*.7z" -Recurse | Remove-Item -Force
    Write-Host "[INFO] FFmpeg setup complete." -ForegroundColor Green
}
else {
    Write-Host "[INFO] FFmpeg already exists in external/ffmpeg" -ForegroundColor Green
}

# Add FFmpeg to environment for this session
# Add FFmpeg to environment for this session
# Ensure we have the absolute path
$FFmpegFullDir = (Resolve-Path $FFmpegDir).Path
$FFmpegBin = Join-Path $FFmpegFullDir "bin"
$FFmpegLib = Join-Path $FFmpegFullDir "lib"
$FFmpegInclude = Join-Path $FFmpegFullDir "include"

$env:PATH = "$FFmpegBin;" + $env:PATH
$env:LIB = "$FFmpegLib;" + $env:LIB
$env:INCLUDE = "$FFmpegInclude;" + $env:INCLUDE

# 4. Core Engine Compilation
Write-Host "[INFO] Compiling Rocky Core C++..." -ForegroundColor Yellow
& $VenvPython setup.py build_ext --inplace
if ($LASTEXITCODE -ne 0) {
    Write-Error "[ERROR] Compilation FAILED."
    Pause
    exit 1
}

# 5. Plugin Compilation
if (Test-Path "plugins") {
    Write-Host "[INFO] Checking for MSVC compiler (cl.exe)..." -ForegroundColor Yellow
    $ClPath = Get-Command cl -ErrorAction SilentlyContinue
    if ($ClPath) {
        Write-Host "[INFO] Compiling Plugins..." -ForegroundColor Yellow
        Push-Location plugins
        if (Test-Path "invert.cpp") {
            # Note: We assume the user is in a Developer Command Prompt/PowerShell if cl exists
            & cl /O2 /LD /I"../src/core/ofx/include" /I"../external/ffmpeg/include" invert.cpp /Fe:invert.ofx
        }
        Get-ChildItem -Filter *.obj | Remove-Item -Force
        Pop-Location
    }
    else {
        Write-Host "[SKIP] cl.exe not found. Run from 'Developer PowerShell for VS' to build plugins." -ForegroundColor Gray
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  COMPILATION FINISHED" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Run the editor with: ./run.ps1"
Pause
