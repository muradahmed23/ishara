<#
.SYNOPSIS
  One-time setup of the iShara desktop app: virtual environment, dependencies, speech models.
.EXAMPLE
  .\scripts\setup.ps1              # base models (~200 MB)
  .\scripts\setup.ps1 -BestDictation   # also whisper small.en (~480 MB)
#>
param([switch]$BestDictation)
$ErrorActionPreference = "Stop"
$Desktop = Join-Path $PSScriptRoot "..\desktop" | Resolve-Path
$Models  = Join-Path $Desktop "models"
Set-Location $Desktop

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
}
$py = Join-Path $Desktop ".venv\Scripts\python.exe"
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements-dev.txt

# Vosk command model
$vosk = Join-Path $Models "vosk-model-small-en-us-0.15"
if (-not (Test-Path $vosk)) {
    Write-Host "Downloading Vosk command model..." -ForegroundColor Cyan
    $zip = Join-Path $env:TEMP "vosk-small-en.zip"
    Invoke-WebRequest "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip" -OutFile $zip
    Expand-Archive $zip -DestinationPath $Models -Force
    Remove-Item $zip
}

# Whisper dictation models
$sizes = @("base.en") + $(if ($BestDictation) { "small.en" })
foreach ($s in $sizes) {
    $dir = Join-Path $Models "whisper-$s"
    if (-not (Test-Path $dir)) {
        Write-Host "Downloading Whisper $s..." -ForegroundColor Cyan
        & $py -c "from faster_whisper import download_model; download_model('$s', output_dir=r'$dir')"
    }
}

Write-Host "`nRunning tests..." -ForegroundColor Cyan
& $py -m pytest -q
Write-Host "`nSetup complete. Start the app with .\scripts\run.ps1" -ForegroundColor Green
