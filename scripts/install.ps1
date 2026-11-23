$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw 'Install Python: winget install -e --id Python.Python.3.13' }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw 'Install Node LTS: winget install -e --id OpenJS.NodeJS.LTS' }
if (-not (Test-Path '.venv')) { python -m venv .venv }
& '.\.venv\Scripts\python.exe' -m pip install -r backend/requirements.txt -c backend/requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed' }
Push-Location frontend
try {
 npm ci
 if ($LASTEXITCODE -ne 0) { throw 'Node dependency installation failed' }
 npx playwright install chromium
 if ($LASTEXITCODE -ne 0) { throw 'Browser installation failed' }
} finally { Pop-Location }
