$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$backendPython = Join-Path $projectRoot "backend\.venv\Scripts\python.exe"
$frontendRoot = Join-Path $projectRoot "frontend"

if (-not (Test-Path -LiteralPath $backendPython)) {
    throw "Backend virtual environment is missing. Follow backend/README.md, then rerun this check."
}

try {
    & $backendPython --version | Out-Null
} catch {
    throw "Backend virtual environment is broken. Recreate backend/.venv using backend/README.md, then rerun this check."
}

Push-Location (Join-Path $projectRoot "backend")
try {
    & $backendPython -m ruff check app tests
    if ($LASTEXITCODE -ne 0) { throw "Backend lint failed." }
    & $backendPython -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "Backend tests failed." }
} finally {
    Pop-Location
}

Push-Location $frontendRoot
try {
    & pnpm run check
    if ($LASTEXITCODE -ne 0) { throw "Frontend check failed." }
} finally {
    Pop-Location
}

Write-Host "Growth Atlas checks passed."
