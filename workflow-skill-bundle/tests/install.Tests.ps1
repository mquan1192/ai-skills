# Test install.py (Python unittest trên thư mục tạm). Chạy bằng PowerShell 7 (pwsh). Exit 0 = PASS.
$ErrorActionPreference = 'Continue'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$out = @(& python -B (Join-Path $here 'test_install.py') 2>&1 | ForEach-Object { [string]$_ })
$code = $LASTEXITCODE
$out | Select-Object -Last 4 | ForEach-Object { Write-Output $_ }
$pyc = @(Get-ChildItem -LiteralPath (Split-Path -Parent $here) -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue)
foreach ($d in $pyc) { Remove-Item -LiteralPath $d.FullName -Recurse -Force }
if ($code -ne 0) { Write-Output 'RESULT FAIL'; exit 1 }
Write-Output 'RESULT PASS'
exit 0
