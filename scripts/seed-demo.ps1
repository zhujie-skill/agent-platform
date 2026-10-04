$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repositoryRoot
$python = Join-Path $repositoryRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Python environment is missing. Run .\scripts\setup.ps1 first."
}

& $python "scripts\seed_demo_data.py"
if ($LASTEXITCODE -ne 0) { throw "Demo data seed failed." }
& $python "scripts\configure_phase3_demo.py"
if ($LASTEXITCODE -ne 0) { throw "Phase 3 registry configuration failed." }
Write-Host "Phase 3 demo is ready. Open http://localhost:3000."
