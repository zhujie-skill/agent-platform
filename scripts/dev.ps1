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

if (-not (Test-Path -LiteralPath "node_modules")) {
    throw "Node.js dependencies are missing. Run .\scripts\setup.ps1 first."
}

$apiCommand = "`"$python`" -m uvicorn app.main:app --app-dir apps/api --reload --reload-dir apps/api --host 127.0.0.1 --port 8000"
$webCommand = "corepack pnpm --filter @agent-platform/web dev"
$platformMcpCommand = "`"$python`" -m uvicorn services.platform_mcp.server:app --reload --reload-dir services/platform_mcp --host 127.0.0.1 --port 8100"
$demoMcpCommand = "`"$python`" -m services.demo_mcp.server"

Write-Host "Starting Control Plane on http://localhost:3000"
Write-Host "Starting Control API on http://127.0.0.1:8000"
Write-Host "Starting Platform MCP on http://127.0.0.1:8100/mcp"
Write-Host "Starting Demo MCP on http://127.0.0.1:8101/mcp"
Write-Host "Press Ctrl+C to stop all services."

corepack pnpm exec concurrently `
    --kill-others-on-fail `
    --names "WEB,API,PLATFORM-MCP,DEMO-MCP" `
    --prefix-colors "cyan,green,magenta,yellow" `
    $webCommand `
    $apiCommand `
    $platformMcpCommand `
    $demoMcpCommand

if ($LASTEXITCODE -ne 0) {
    throw "One or more development services exited with an error."
}

