Set-Location (Split-Path $PSScriptRoot -Parent)
docker compose exec -T backend python -m app.seed
