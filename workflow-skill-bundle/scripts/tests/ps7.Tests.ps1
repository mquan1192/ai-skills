# ps7.Tests.ps1 - the process scripts are PowerShell 7 only. Every entry script refuses Windows PowerShell 5.1 with ONE
# line 'REFUSED: <script> needs PowerShell 7 (pwsh) ...' (exit 1, nothing written); CardFlow.psm1 declares
# '#Requires -Version 7'; the test files do not (they run on 5.1 too, where each checks only the refusal). ASCII only.
# -RedProof: runs the same checks on a temp copy of the scripts (inside the fake tree) where the refusal line of
# board.ps1 is removed - the 5.1 check for board.ps1 must FAIL (exit 1). Without -RedProof every check must PASS.
param([switch]$Keep, [switch]$RedProof)
. (Join-Path $PSScriptRoot '_lib.ps1')
Test-Ps5Only @('board.ps1', 'checkpoint.ps1', 'gate.ps1', 'intake.ps1', 'manifest.ps1', 'release.ps1', 'stale.ps1', 'steplog.ps1', 'ticket.ps1')   # Windows PowerShell 5.1: only the refusal of these scripts, then exit
Write-Output "===== ps7$(if ($RedProof) { ' (red proof: board.ps1 without its refusal line)' }) ====="
$ps5 = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$W = New-FakeTree 'ps7'
$Dir = $script:Src
if ($RedProof) {
    # the copy lives in the fake tree's parent folder (removed by Finish), never next to the real scripts
    $Dir = Join-Path (Split-Path -Parent $W) 'redproof-scripts'
    [void][IO.Directory]::CreateDirectory($Dir)
    foreach ($f in @(Get-ChildItem -LiteralPath $script:Src -File | Where-Object { $_.Extension -in '.ps1', '.psm1' })) { Copy-Item -LiteralPath $f.FullName -Destination $Dir }
    $b = Join-Path $Dir 'board.ps1'
    $kept = @([IO.File]::ReadAllLines($b) | Where-Object { $_ -notmatch '^if \(\$PSVersionTable\.PSVersion\.Major -lt 7\)' })
    [IO.File]::WriteAllLines($b, [string[]]$kept)
}
$before = @(Get-ChildItem -LiteralPath $W -Recurse -Force -File).Count
$scripts = @(Get-ChildItem -LiteralPath $Dir -File -Filter '*.ps1' | ForEach-Object { $_.Name } | Sort-Object)
Check 'entry scripts found (at least 9)' ($scripts.Count -ge 9) ($scripts -join ', ')
if (-not (Test-Path -LiteralPath $ps5)) { Check 'Windows PowerShell 5.1 present for the refusal check' $false $ps5 }
else {
    Push-Location -LiteralPath $W
    try {
        foreach ($s in $scripts) {
            $global:LASTEXITCODE = 0
            # -Root = the fake tree: a script without the guard must never reach a real project
            $out = @(& $ps5 -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $Dir $s) -Root $W 2>&1 | ForEach-Object { [string]$_ } | Where-Object { $_.Trim() })
            $code = $LASTEXITCODE
            Check "5.1 refuses $s with one line, exit 1" ($code -eq 1 -and $out.Count -eq 1 -and $out[0] -like "REFUSED: $s needs PowerShell 7 (pwsh); this is Windows PowerShell 5.1*") ("exit $code / " + (@($out | Select-Object -First 2) -join ' / '))
        }
    }
    finally { Pop-Location }
}
Check 'nothing written by the refused runs' (@(Get-ChildItem -LiteralPath $W -Recurse -Force -File).Count -eq $before) ''
$first = @([IO.File]::ReadLines((Join-Path $script:Src 'CardFlow.psm1')) | Select-Object -First 1)
Check "CardFlow.psm1 starts with '#Requires -Version 7'" ($first.Count -eq 1 -and $first[0] -ceq '#Requires -Version 7') ''
foreach ($t in @(Get-ChildItem -LiteralPath $PSScriptRoot -File -Filter '*.Tests.ps1' | Sort-Object Name)) {
    # no '#Requires' (the test must run on 5.1 too) and one Test-Ps5Only call naming existing scripts only
    $txt = [IO.File]::ReadAllText($t.FullName)
    $calls = @([regex]::Matches($txt, "(?m)^Test-Ps5Only @\(([^)]*)\)") | ForEach-Object { $_.Groups[1].Value })
    $names = @(); if ($calls.Count -eq 1) { $names = @([regex]::Matches($calls[0], "'([^']+)'") | ForEach-Object { $_.Groups[1].Value }) }
    $okNames = $names.Count -gt 0 -and @($names | Where-Object { -not [IO.File]::Exists((Join-Path $script:Src $_)) }).Count -eq 0
    Check "$($t.Name): no '#Requires', one Test-Ps5Only call with existing scripts ($($names -join ', '))" ($txt -notmatch '(?im)^\s*#Requires' -and $calls.Count -eq 1 -and $okNames) ''
}
Finish 'ps7'
