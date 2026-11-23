$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
& "$PSScriptRoot/setup.ps1"
docker info *> $null
if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop, then rerun this script. Install if absent: winget install -e --id Docker.DockerDesktop' }
docker compose up -d --build --wait --wait-timeout 300
if ($LASTEXITCODE -ne 0) { throw 'Startup failed. Run docker compose logs --tail 100.' }
Invoke-RestMethod http://localhost:8000/health | Format-List
Write-Host 'FormFlow: http://localhost:3000 | API: http://localhost:8000/docs'
