$ErrorActionPreference = "Stop"

Write-Host "Connecting the Dots - optional InsightFace setup" -ForegroundColor Cyan
Write-Host ""
Write-Host "Prerequisite: install Visual Studio 2022 Build Tools with the C++ workload." -ForegroundColor Yellow
Write-Host "Use these official workload/component IDs:" -ForegroundColor Yellow
Write-Host "  - Microsoft.VisualStudio.Workload.VCTools" -ForegroundColor Yellow
Write-Host "  - Microsoft.VisualStudio.Component.VC.Tools.x86.x64" -ForegroundColor Yellow
Write-Host "  - Microsoft.VisualStudio.Component.Windows11SDK.22621" -ForegroundColor Yellow
Write-Host ""
Write-Host "If Build Tools are already installed, this script will install the Python packages." -ForegroundColor Yellow

$cl = Get-Command cl.exe -ErrorAction SilentlyContinue
$msbuild = Get-Command msbuild.exe -ErrorAction SilentlyContinue

if (-not $cl -or -not $msbuild) {
    Write-Host ""
    Write-Host "C++ build tools were not found on PATH." -ForegroundColor Red
    Write-Host "Install them first, then reopen a fresh PowerShell window and rerun this script." -ForegroundColor Red
    Write-Host ""
    Write-Host "Official docs:" -ForegroundColor Cyan
    Write-Host "  - https://learn.microsoft.com/en-us/visualstudio/install/workload-component-id-vs-build-tools?view=visualstudio"
    Write-Host "  - https://learn.microsoft.com/en-us/cpp/build/vscpp-step-0-installation?view=msvc-160"
    exit 1
}

Write-Host ""
Write-Host "Build tools detected. Installing optional ML packages..." -ForegroundColor Green

python -m pip install --upgrade pip
python -m pip install insightface==0.7.3 onnxruntime==1.25.1

Write-Host ""
Write-Host "Done. Verify with:" -ForegroundColor Green
Write-Host "  python scripts/test_insightface.py" -ForegroundColor Green
