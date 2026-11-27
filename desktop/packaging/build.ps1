<#
.SYNOPSIS
  Build the iShara Windows installer.
.DESCRIPTION
  1. Reads the version from ishara\__init__.py (single source of truth).
  2. Writes models\MODELS.sha256 (the app verifies the models against it).
  3. PyInstaller -> dist\iShara\iShara.exe
  4. Inno Setup  -> dist\installer\iShara-Setup-<version>.exe
  5. Writes dist\installer\release-draft.json with the installer SHA-256 and size;
     copy its values into release\latest.json when you publish the release.
.EXAMPLE
  cd desktop; .\packaging\build.ps1
#>
param([switch]$SkipPyInstaller)
# Native tools (PyInstaller, ISCC) log to stderr; PowerShell 5.1 would treat that as an
# error under "Stop". Failures are detected through $LASTEXITCODE instead.
$ErrorActionPreference = "Continue"
$Desktop = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Desktop
$py = Join-Path $Desktop ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Run ..\scripts\setup.ps1 first (creates desktop\.venv)." }

# ---- version -------------------------------------------------------------
$version = (& $py -c "import ishara; print(ishara.__version__)").Trim()
Write-Host "iShara $version" -ForegroundColor Cyan
$v = ($version.Split(".") + @("0", "0", "0"))[0..3] -join ","
@"
VSVersionInfo(
  ffi=FixedFileInfo(filevers=($v), prodvers=($v)),
  kids=[StringFileInfo([StringTable('040904B0', [
    StringStruct('CompanyName', 'iShara'),
    StringStruct('FileDescription', 'iShara - hands-free computer control'),
    StringStruct('FileVersion', '$version'),
    StringStruct('ProductName', 'iShara'),
    StringStruct('ProductVersion', '$version')])]),
  VarFileInfo([VarStruct('Translation', [1033, 1200])])]
)
"@ | Set-Content -Encoding utf8 (Join-Path $PSScriptRoot "version_info.txt")

# ---- model checksums -----------------------------------------------------
foreach ($m in "vosk-model-small-en-us-0.15", "whisper-base.en") {
    if (-not (Test-Path "models\$m")) { throw "Missing models\$m. Run ..\scripts\setup.ps1" }
}
Write-Host "Hashing bundled models..." -ForegroundColor Cyan
# whisper-small.en is an optional download, not part of the installer
& $py -m ishara.integrity --write models --exclude whisper-small.en
if ($LASTEXITCODE) { throw "model hashing failed" }

# ---- PyInstaller -----------------------------------------------------------
if (-not $SkipPyInstaller) {
    Write-Host "PyInstaller..." -ForegroundColor Cyan
    & $py -m PyInstaller packaging\ishara.spec --noconfirm --clean --distpath dist --workpath build
    if ($LASTEXITCODE) { throw "PyInstaller failed" }
}

# ---- Inno Setup ------------------------------------------------------------
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
          "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
          "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup 6 not found (winget install JRSoftware.InnoSetup)" }
Write-Host "Inno Setup..." -ForegroundColor Cyan
& $iscc "/DAppVersion=$version" /Qp packaging\ishara.iss
if ($LASTEXITCODE) { throw "Inno Setup failed" }

# ---- release draft ---------------------------------------------------------
$setup = Get-Item "dist\installer\iShara-Setup-$version.exe"
$sha = (Get-FileHash $setup.FullName -Algorithm SHA256).Hash.ToLower()
$draft = [ordered]@{
    version      = $version
    file         = $setup.Name
    url          = "https://github.com/muradahmed23/ishara/releases/download/v$version/$($setup.Name)"
    sha256       = $sha
    sizeBytes    = $setup.Length
}
$draft | ConvertTo-Json | Set-Content -Encoding utf8 "dist\installer\release-draft.json"
Write-Host ("`nInstaller: {0}  ({1:N0} MB)`nSHA-256:   {2}" -f $setup.FullName, ($setup.Length / 1MB), $sha) -ForegroundColor Green
