# stale.ps1 - SENT > 30 min, ACCEPTED with no zone change > 3 h, MERGED / CLOSED skipped, read-only. Fake tree only.
param([switch]$Keep, [switch]$RedProof)
. (Join-Path $PSScriptRoot '_lib.ps1')
Test-Ps5Only @('stale.ps1')   # Windows PowerShell 5.1: only the refusal of stale.ps1, then exit
Write-Output '===== stale ====='
$W = New-FakeTree 'stale'
$now = [datetime]::ParseExact('2026-11-09T15:00', 'yyyy-MM-ddTHH:mm', [Globalization.CultureInfo]::InvariantCulture)
$f = { param($min) $now.AddMinutes(-$min).ToString('yyyy-MM-ddTHH:mm') }
function Mk([string]$Card, [string]$State, [string]$TState, [int]$AgeMin, [int]$FileAgeMin, [string]$To = 'BUILD') {
    $z = "2026-11/09_01-fake-task/out/tools/$Card"
    $cd = New-FakeCard $W $Card @($z) @() @() $State
    $at = & $f $AgeMin
    $hist = @("$at|LEAD|SENT|go"); if ($TState -ne 'SENT') { $hist += "$at|$To|$TState|ok" }
    Add-Ticket $W $Card 1 'LEAD' $To 'P1' $TState '' $hist
    $file = Join-Path (P $W $z) 'work.txt'; WF $file 'w'
    (Get-Item -LiteralPath $file).LastWriteTime = $now.AddMinutes(-$FileAgeMin)
}
Mk '001-sent29' 'BUILDING' 'SENT' 29 600
Mk '002-sent31' 'BUILDING' 'SENT' 31 600
Mk '003-acc-quiet' 'BUILDING' 'ACCEPTED' 240 240
Mk '004-acc-busy' 'BUILDING' 'ACCEPTED' 240 60
Mk '005-merged' 'MERGED' 'SENT' 120 600
Mk '006-closed' 'CLOSED' 'ACCEPTED' 600 600
Mk '007-acc-new' 'BUILDING' 'ACCEPTED' 179 600
Mk '008-takeover' 'BUILDING' 'TAKEOVER' 200 200 'REVIEW'
Mk '009-hold' 'BUILDING' 'HOLD' 600 600
$h0 = Get-TreeHash $W
$r = Run 'stale' @{ Now = '2026-11-09T15:00' } $W
$o = $r.Out
Check 'SENT 29 min -> not listed' ($o -notmatch '001-sent29') $o
Check 'SENT 31 min -> listed' ($o -match 'STALE 002-sent31 H-01 SENT BUILD') $o
Check 'ACCEPTED 4 h, zone quiet 4 h -> listed' ($o -match 'STALE 003-acc-quiet H-01 ACCEPTED BUILD') $o
Check 'ACCEPTED 4 h, zone changed 1 h ago -> not listed' ($o -notmatch '004-acc-busy') $o
Check 'ACCEPTED 2 h 59 min -> not listed' ($o -notmatch '007-acc-new') $o
Check 'TAKEOVER (old name in the ticket) quiet > 3 h -> listed as TAKEN-OVER' ($o -match 'STALE 008-takeover H-01 TAKEN-OVER REVIEW') $o
Check 'MERGED / CLOSED cards skipped, HOLD not listed' ($o -notmatch '005-merged' -and $o -notmatch '006-closed' -and $o -notmatch '009-hold') $o
Check 'time base stated, exit 0, writes nothing' ($r.Exit -eq 0 -and $o -match 'time base: local clock' -and (Get-TreeHash $W) -eq $h0) $o
$W2 = New-FakeTree 'stale-empty'
$r = Run 'stale' @{ Now = '2026-11-09T15:00' } $W2
Check 'no cards -> "nothing stale"' ($r.Exit -eq 0 -and $r.Out -match 'nothing stale') $r.Out
Finish 'stale'
