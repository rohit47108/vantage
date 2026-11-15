param([ValidateRange(1024,65535)][int]$Port = 8000)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Push-Location -LiteralPath $projectRoot
try {
    & npm run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    & "$projectRoot\.venv\Scripts\python.exe" -m uvicorn backend.app:app --host 127.0.0.1 --port $Port
} finally {
    Pop-Location
}
