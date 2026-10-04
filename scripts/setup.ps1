$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repositoryRoot

function Assert-Command {
    param([Parameter(Mandatory)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found. See README.md for prerequisites."
    }
}

Assert-Command "python"
Assert-Command "node"
Assert-Command "corepack"

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
    Write-Host "Created .env from .env.example."
}

if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    Write-Host "Creating Python virtual environment..."
    python -m venv .venv
}

$python = Join-Path $repositoryRoot ".venv\Scripts\python.exe"

Write-Host "Installing Python dependencies..."
& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Failed to upgrade pip."
}
& $python -m pip install -r "apps\api\requirements-dev.txt"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install Python dependencies."
}

Write-Host "Installing the Agent Platform Python SDK..."
& $python -m pip install --editable "packages\python-sdk"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install the Python SDK."
}

Write-Host "Installing Node.js dependencies..."
corepack pnpm install
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install Node.js dependencies."
}

Write-Host "Setup complete. Run .\scripts\dev.ps1 to start the platform."

