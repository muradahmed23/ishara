<#
.SYNOPSIS
  Compile and upload the headband firmware to the ESP32 over USB.
.EXAMPLE
  .\scripts\flash-firmware.ps1             # auto-detect the USB port
  .\scripts\flash-firmware.ps1 -Port COM6
  .\scripts\flash-firmware.ps1 -CompileOnly
#>
param([string]$Port, [switch]$CompileOnly)
$ErrorActionPreference = "Stop"
$Root = Join-Path $PSScriptRoot ".." | Resolve-Path
$Sketch = Join-Path $Root "firmware\ishara_headband"
$Libs = Join-Path $Root "firmware\libraries"

$cli = (Get-Command arduino-cli -ErrorAction SilentlyContinue).Source
if (-not $cli) {   # Arduino IDE 2 ships its own copy
    $cli = "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe"
}
if (-not (Test-Path $cli)) { throw "arduino-cli not found. Install Arduino IDE 2 or arduino-cli." }

$common = @("--fqbn", "esp32:esp32:esp32", "--board-options", "PartitionScheme=huge_app", "--libraries", $Libs)
if ($CompileOnly) { & $cli compile @common $Sketch; exit $LASTEXITCODE }

if (-not $Port) {
    $Port = (& $cli board list | Select-String "Serial Port \(USB\)" | ForEach-Object { ($_ -split "\s+")[0] } | Select-Object -First 1)
    if (-not $Port) { throw "No ESP32 found on USB. Plug in the headband (data cable) and retry." }
}
Write-Host "Uploading to $Port..." -ForegroundColor Cyan
& $cli compile --upload -p $Port @common $Sketch
