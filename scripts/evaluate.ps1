Set-Location (Split-Path $PSScriptRoot -Parent)
docker compose exec -T backend python -m app.evaluation
docker compose exec -T backend python -m app.ocr_benchmark
