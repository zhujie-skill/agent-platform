$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repositoryRoot

if (-not (Get-Command "corepack" -ErrorAction SilentlyContinue)) {
    throw "Corepack was not found. Install Node.js 22+ and reopen the terminal."
}

$python = Join-Path $repositoryRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Python environment is missing. Run .\scripts\setup.ps1 first."
}

Write-Host "Running Python static checks..."
& $python -m ruff check apps/api migrations services scripts/*.py examples packages/python-sdk
if ($LASTEXITCODE -ne 0) {
    throw "Python static checks failed."
}

Write-Host "Running API tests..."
Push-Location "apps\api"
try {
    & $python -m pytest
    $pytestExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}
if ($pytestExitCode -ne 0) {
    throw "API tests failed."
}

Write-Host "Running Python SDK tests..."
Push-Location "packages\python-sdk"
try {
    & $python -m pytest
    $sdkPytestExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}
if ($sdkPytestExitCode -ne 0) {
    throw "Python SDK tests failed."
}

Write-Host "Running TypeScript checks..."
corepack pnpm typecheck
if ($LASTEXITCODE -ne 0) {
    throw "TypeScript checks failed."
}

Write-Host "Building the Control Plane..."
corepack pnpm build
if ($LASTEXITCODE -ne 0) {
    throw "Control Plane build failed."
}

Write-Host "All checks passed."

