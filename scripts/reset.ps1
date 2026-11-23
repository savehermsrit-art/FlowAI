$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
docker compose exec -T backend python -m app.reset
if ($LASTEXITCODE -ne 0) { throw 'Demonstration reset failed' }
