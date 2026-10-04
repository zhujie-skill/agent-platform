$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repositoryRoot

$python = Join-Path $repositoryRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Python environment is missing. Run .\scripts\setup.ps1 first."
}

Write-Host "Applying database migrations..."
& $python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    throw "Database migration failed."
}
Write-Host "Database is up to date."

