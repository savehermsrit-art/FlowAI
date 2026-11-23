Set-Location (Split-Path $PSScriptRoot -Parent)
docker compose logs --tail 100 -f
