Set-Location (Split-Path $PSScriptRoot -Parent)
docker compose exec -T backend alembic -c backend/alembic.ini upgrade head
