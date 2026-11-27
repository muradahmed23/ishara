<#
.SYNOPSIS
  Start the iShara desktop app.
.EXAMPLE
  .\scripts\run.ps1          # with the headband (Bluetooth)
  .\scripts\run.ps1 -Sim     # without hardware (simulated head motion)
#>
param([switch]$Sim)
$Desktop = Join-Path $PSScriptRoot "..\desktop" | Resolve-Path
$venv = Join-Path $Desktop ".venv\Scripts\pythonw.exe"
$py = if (Test-Path $venv) { $venv } else { "pythonw" }
$argv = @("ishara_app.py") + $(if ($Sim) { "--sim" })
Start-Process -FilePath $py -ArgumentList $argv -WorkingDirectory $Desktop
