<#
  Gate wrapper: runs all Python tests of the KB skill bundle (tests/test_*.py) on PowerShell 7 (pwsh).
  On Windows PowerShell 5.1 (2.0.4: the bundle's PowerShell scripts are PowerShell 7 only) it checks instead that
  tools/download-models.ps1 refuses 5.1 with one REFUSED line, exit 1, and writes nothing.
  Usage: pwsh -NoProfile -ExecutionPolicy Bypass -File bundle.Tests.ps1
  The Python tests use temp folders only (tempfile) and leave no __pycache__ (-B).
  Prints PASS / FAIL and one RESULT line; exit code = number of failures (0 = all green).
#>
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$bundle = (Resolve-Path -LiteralPath (Join-Path $here '..')).ProviderPath
$psName = 'PS ' + $PSVersionTable.PSVersion.ToString()
if ($PSVersionTable.PSVersion.Major -lt 7) {
    $dm = Join-Path $bundle 'tools\download-models.ps1'
    $tgt = Join-Path ([IO.Path]::GetTempPath()) ('kb-ps5-' + [Guid]::NewGuid().ToString('N').Substring(0, 8))
    [void][IO.Directory]::CreateDirectory($tgt)
    $ErrorActionPreference = 'Continue'
    $o = @(& powershell -NoProfile -ExecutionPolicy Bypass -File $dm -Target $tgt -Apply 2>&1 | ForEach-Object { [string]$_ })
    $code = $LASTEXITCODE
    $left = @(Get-ChildItem -LiteralPath $tgt -Force -Recurse).Count
    Remove-Item -LiteralPath $tgt -Recurse -Force
    $ok = ($o.Count -eq 1) -and ($o[0] -like 'REFUSED: download-models.ps1 needs PowerShell 7*') -and ($code -eq 1) -and ($left -eq 0)
    if ($ok) { Write-Host '  PASS 5.1 refused by download-models.ps1 (1 line, exit 1, nothing written)'; Write-Host ('RESULT 1/1 PASS (' + $psName + ')'); exit 0 }
    Write-Host ('  FAIL 5.1 not refused as expected: lines ' + $o.Count + ', exit ' + $code + ', files ' + $left)
    Write-Host ('RESULT 0/1 PASS (' + $psName + ')'); exit 1
}
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Write-Host '  FAIL python not found'; Write-Host ('RESULT 0/1 PASS (' + $psName + ')'); exit 1 }
Push-Location -LiteralPath $bundle
try {
    $ErrorActionPreference = 'Continue'
    $out = & $py.Source -E -s -B -m unittest discover -s tests -p 'test_*.py' 2>&1 | Out-String
    $code = $LASTEXITCODE
} finally {
    Pop-Location
    $ErrorActionPreference = 'Stop'
}
$ran = 0
if ($out -match 'Ran (\d+) test') { $ran = [int] $Matches[1] }
$skipped = 0
if ($out -match 'skipped=(\d+)') { $skipped = [int] $Matches[1] }
if ($code -eq 0 -and $ran -gt 0) {
    Write-Host ('  PASS python unittest: ' + $ran + ' tests, skipped ' + $skipped)
    Write-Host ('RESULT 1/1 PASS (' + $psName + ')')
    exit 0
}
Write-Host ('  FAIL python unittest (exit ' + $code + ')')
($out -split "`n" | Select-Object -Last 25) | ForEach-Object { Write-Host ('    ' + $_) }
Write-Host ('RESULT 0/1 PASS (' + $psName + ')')
exit 1
