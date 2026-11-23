$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
docker compose exec -T backend python -m pytest backend/tests -q
if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed' }
Push-Location frontend
try {
 npm run typecheck
 if ($LASTEXITCODE -ne 0) { throw 'Type check failed' }
 npm test
 if ($LASTEXITCODE -ne 0) { throw 'Frontend tests failed' }
 npm run test:e2e
 if ($LASTEXITCODE -ne 0) { throw 'Browser tests failed' }
} finally { Pop-Location }
