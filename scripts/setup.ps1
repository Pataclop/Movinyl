# Movinyl one-shot setup for Windows (PowerShell).
#
#   ./scripts/setup.ps1
#
# A local virtual environment (.venv) is created so `pip install` always works.
# OpenCV on Windows is easiest via vcpkg: install it once, then
#     vcpkg install opencv4 ffmpeg
#     $env:VCPKG_ROOT = "C:\vcpkg"
# and CMake is pointed at the vcpkg toolchain automatically.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command python3 -ErrorAction SilentlyContinue).Source }
if (-not $py) { Write-Error "Python 3 is required but was not found on PATH." ; exit 1 }

$venv = Join-Path $Root ".venv"
if (-not (Test-Path $venv)) {
    Write-Host "Creating virtual environment in .venv ..."
    & $py -m venv $venv
}
$vpy = Join-Path $venv "Scripts\python.exe"

if (-not $env:VCPKG_ROOT) {
    Write-Host "Tip: set VCPKG_ROOT and run 'vcpkg install opencv4 ffmpeg' so CMake finds OpenCV." -ForegroundColor Yellow
}

Write-Host "Installing Python dependencies ..."
& $vpy -m pip install --upgrade pip | Out-Null
& $vpy -m pip install -r requirements.txt

& $vpy -m movinyl setup --no-python @args

Write-Host "`nDone. Activate the environment and launch the dashboard:"
Write-Host "    .venv\Scripts\Activate.ps1"
Write-Host "    python -m movinyl tui"
