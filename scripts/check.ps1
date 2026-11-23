$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
docker compose exec -T backend python -m ruff check backend
if ($LASTEXITCODE -ne 0) { throw 'Python lint failed' }
Push-Location frontend
try { npm run lint; if ($LASTEXITCODE -ne 0) { throw 'Frontend checks failed' } } finally { Pop-Location }
