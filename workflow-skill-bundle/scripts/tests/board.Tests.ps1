# board.ps1 - PROGRESS.md from cards + tickets; errors are warnings only, also when called by another command.
param([switch]$Keep, [switch]$RedProof)
. (Join-Path $PSScriptRoot '_lib.ps1')
Test-Ps5Only @('board.ps1')   # Windows PowerShell 5.1: only the refusal of board.ps1, then exit
Write-Output '===== board ====='
$W = New-FakeTree 'board'
$cd1 = New-FakeCard $W '001-good'
Add-Ticket $W '001-good' 1 'LEAD' 'BUILD' 'P1' 'ACCEPTED'
$cd2 = New-FakeCard $W '002-broken'
WF (Join-Path $cd2 'handoff\H-01.json') '{ broken'
$prog = P $W 'docs/process/PROGRESS.md'

$h0 = Get-TreeHash $W
$r = Run 'board' @{} $W
$p = if (Test-Path $prog) { RF $prog } else { '' }
Check 'malformed ticket in one card -> exit 0, warning, both rows' ($r.Exit -eq 0 -and $r.Out -match 'WARNING|board: card 002-broken skipped' -and $p -match '\| 001-good \| BUILDING \| H-01 LEAD.BUILD ACCEPTED' -and $p -match '\| 002-broken \| \(unreadable') $r.Out
$diff = @(Compare-Object @($h0 -split "`n") @((Get-TreeHash $W) -split "`n") | ForEach-Object { ($_.InputObject -split '\|')[0] } | Sort-Object -Unique)
Check 'writes only docs/process/PROGRESS.md' ($diff.Count -eq 1 -and $diff[0] -match 'PROGRESS\.md$') ($diff -join ', ')

# board failure inside another command must not change that command's exit code
Remove-Item -LiteralPath $prog -Force
[void][IO.Directory]::CreateDirectory($prog)            # PROGRESS.md is now a folder -> board cannot write
$r = Run 'ticket' @{ Action = 'done'; Card = '001-good'; As = 'BUILD'; Note = 'ok' } $W
Check 'ticket with a failing board -> exit 0 + "board: not refreshed" warning' ($r.Exit -eq 0 -and $r.Out -match 'OK: H-01 ACCEPTED' -and $r.Out -match 'board: not refreshed') $r.Out
$r = Run 'checkpoint' @{ Card = '001-good'; As = 'LEAD'; Done = 'a'; Doing = 'b'; Next = 'c'; Check = 'd' } $W
Check 'checkpoint with a failing board -> exit 0' ($r.Exit -eq 0 -and $r.Out -match 'board: not refreshed') $r.Out
$r = Run 'checkpoint' @{ Card = '001-good'; As = 'BUILD'; Done = 'a'; Doing = 'b'; Next = 'c'; Check = 'd' } $W
Check 'a refusal stays exit 1 (board does not mask it)' ($r.Exit -eq 1) $r.Out
$r = Run 'board' @{} $W
Check 'board.ps1 itself failing to write -> still exit 0 (warning)' ($r.Exit -eq 0 -and $r.Out -match 'WARNING|board:') $r.Out
$r = Run 'board' @{} (Join-Path $W 'kb')
Check 'board.ps1 with a wrong root -> exit 0 (warning)' ($r.Exit -eq 0) $r.Out
Finish 'board'
