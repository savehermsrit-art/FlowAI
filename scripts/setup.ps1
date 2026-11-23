$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path -LiteralPath '.env')) {
  function New-LocalSecret { $bytes = New-Object byte[] 32; $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create(); try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }; [Convert]::ToBase64String($bytes) }
  $dbPassword = (New-LocalSecret).Replace('+','a').Replace('/','b').TrimEnd('=')
  $minioPassword = (New-LocalSecret).Replace('+','c').Replace('/','d').TrimEnd('=')
  $fernet = (New-LocalSecret).Replace('+','-').Replace('/','_')
  @("POSTGRES_PASSWORD=$dbPassword",'MINIO_ROOT_USER=formflow',"MINIO_ROOT_PASSWORD=$minioPassword", "FORMFLOW_KEY=$fernet",'FORMFLOW_MODE=DEMO','DEVELOPMENT=true','RETENTION_DAYS=30') | Set-Content -LiteralPath '.env' -Encoding utf8
  # Restrict generated secrets to the current user and SYSTEM.
  $account = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
  & icacls.exe '.env' /inheritance:r /grant:r "${account}:(F)" 'SYSTEM:(F)' | Out-Null
}
Write-Host 'Local secrets ready. No credentials printed.'
