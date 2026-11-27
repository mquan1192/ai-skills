# Test tools/scan_terms.py (Python unittest). Chạy bằng PowerShell 7 (pwsh). Exit 0 = PASS.
$ErrorActionPreference = 'Continue'
$tools = Join-Path (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)) 'tools'
$out = @(& python -B (Join-Path $tools 'test_scan_terms.py') 2>&1 | ForEach-Object { [string]$_ })
$code = $LASTEXITCODE
$out | Select-Object -Last 3 | ForEach-Object { Write-Output $_ }
if ($code -ne 0) { Write-Output 'RESULT FAIL'; exit 1 }
Write-Output 'RESULT PASS'
exit 0
