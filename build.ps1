$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "1/5 Checking PyInstaller..." -ForegroundColor Cyan
python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    python -m pip install pyinstaller
}

Write-Host "2/5 Generating multi-resolution app icon..." -ForegroundColor Cyan
python make_icon.py

Write-Host "3/5 Verifying Python syntax..." -ForegroundColor Cyan
python -m py_compile src\thermalpulse.py

Write-Host "4/5 Compiling ThermalPulse with PyInstaller..." -ForegroundColor Cyan
python -m PyInstaller --noconfirm --clean ThermalPulse.spec

Write-Host "5/5 Building Inno Setup Installer..." -ForegroundColor Cyan
$iscc = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($iscc) {
    & $iscc installer.iss
    Write-Host "`nBuild complete! Installer ready at: $PSScriptRoot\release\ThermalPulse_Setup_v1.0.0.exe" -ForegroundColor Green
} else {
    Write-Host "`nPyInstaller app ready at: $PSScriptRoot\dist\ThermalPulse\ThermalPulse.exe" -ForegroundColor Yellow
    Write-Host "Install Inno Setup 6 (winget install JRSoftware.InnoSetup) to build the Setup .exe." -ForegroundColor Yellow
}