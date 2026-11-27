# intake.ps1 - read-only, same reasons as release -IfSafe -DryRun, a suggested next step. Fake tree only.
param([switch]$Keep, [switch]$RedProof)
. (Join-Path $PSScriptRoot '_lib.ps1')
Test-Ps5Only @('intake.ps1')   # Windows PowerShell 5.1: only the refusal of intake.ps1, then exit
Write-Output '===== intake ====='
$RS = @{ Card = '001-fake'; IfSafe = $true; As = 'LEAD'; DryRun = $true }

$T = New-ReleaseTree 'intake-refuse' -Protected @() -Verdict 'NG'
$h0 = Get-TreeHash $T.W
$r = Run 'intake' @{ Card = '001-fake' } $T.W
$rd = Run 'release' $RS $T.W
Check 'refusing card: intake exit 0, whole tree unchanged' ($r.Exit -eq 0 -and (Get-TreeHash $T.W) -eq $h0) $r.Out
Check 'intake reasons = release -IfSafe -DryRun reasons' (((Get-Reasons $r.Out) -join '|') -eq ((Get-Reasons $rd.Out) -join '|') -and @(Get-Reasons $r.Out).Count -ge 2) ((Get-Reasons $r.Out) -join '|')
Check 'shows open ticket, manifest vs frozen, gate, protected, next step (FIX after FAIL)' ($r.Out -match 'Open ticket: none' -and $r.Out -match 'last frozen .* MATCH' -and $r.Out -match 'Gate: PASS' -and $r.Out -match 'Protected changed: scripts/process/a\.ps1 \(added\): NOT in protected_paths' -and $r.Out -match 'Next: LEAD: send the FIX ticket to BUILD \(ticket send -To BUILD -Phase FIX\)') $r.Out

$T = New-ReleaseTree 'intake-safe'
$h0 = Get-TreeHash $T.W
$r = Run 'intake' @{ Card = '001-fake' } $T.W
Check 'safe card: "Release dry-run: SAFE", next = release, tree unchanged' ($r.Exit -eq 0 -and $r.Out -match 'Release dry-run: SAFE' -and $r.Out -match 'Next: LEAD: release 001-fake -IfSafe -As LEAD' -and (Get-TreeHash $T.W) -eq $h0) $r.Out

$W = New-FakeTree 'intake-early'
$cd = New-FakeCard $W '001-fake'
Add-Ticket $W '001-fake' 1 'LEAD' 'BUILD' 'P1' 'SENT'
$h0 = Get-TreeHash $W
$r = Run 'intake' @{ Card = '001-fake' } $W
Check 'P1 start: no baseline -> manifest not available, next = baseline, tree unchanged' ($r.Exit -eq 0 -and $r.Out -match 'Manifest: not available' -and $r.Out -match 'Next: BUILD: manifest 001-fake -Baseline' -and (Get-TreeHash $W) -eq $h0) $r.Out
$r = Run 'intake' @{ Card = '999-none' } $W
Check 'unknown card -> refused' ($r.Exit -eq 1 -and $r.Out -match 'not found') $r.Out
# open REVIEW ticket at an old digest -> next step = STALE close; a STALE close is not shown as a review result
$T = New-ReleaseTree 'intake-stale'
$null = Run 'ticket' @{ Action = 'send'; Card = '001-fake'; As = 'LEAD'; To = 'REVIEW'; Phase = 'VERIFY'; Freeze = $true } $T.W
$null = Run 'ticket' @{ Action = 'accept'; Card = '001-fake'; As = 'REVIEW' } $T.W
WF (Join-Path $T.Z2 'a.ps1') 'Write-Output 61'
$r = Run 'intake' @{ Card = '001-fake' } $T.W
Check 'open REVIEW ticket at an old digest -> Next suggests the OUTDATED close (old: STALE)' ($r.Exit -eq 0 -and $r.Out -match "Next: REVIEW \(or LEAD\): H-03 is OUTDATED .* ticket done -Note 'OUTDATED") $r.Out
$null = Run 'ticket' @{ Action = 'done'; Card = '001-fake'; As = 'REVIEW'; Note = 'STALE' } $T.W
$r = Run 'intake' @{ Card = '001-fake' } $T.W
Check 'after the STALE close intake shows no review result for it (REFUSED, no "STALE" verdict)' ($r.Exit -eq 0 -and $r.Out -match 'Release dry-run: REFUSED' -and $r.Out -notmatch "verdict is 'STALE'" -and $r.Out -match 'files changed after review') $r.Out
# the OUTDATED hint also for a SENT and an ON-HOLD REVIEW ticket at an old digest
foreach ($st in 'SENT', 'ON-HOLD') {
    $T = New-ReleaseTree ('intake-out-' + $st.ToLowerInvariant())
    $null = Run 'ticket' @{ Action = 'send'; Card = '001-fake'; As = 'LEAD'; To = 'REVIEW'; Phase = 'VERIFY-FIX'; Freeze = $true } $T.W
    if ($st -eq 'ON-HOLD') { $null = Run 'ticket' @{ Action = 'hold'; Card = '001-fake'; As = 'REVIEW'; Note = 'waiting' } $T.W }
    WF (Join-Path $T.Z2 'a.ps1') 'Write-Output 65'
    $r = Run 'intake' @{ Card = '001-fake' } $T.W
    Check "open REVIEW ticket $st at an old digest -> Next suggests the OUTDATED close" ($r.Exit -eq 0 -and $r.Out -match "Next: REVIEW \(or LEAD\): H-03 is OUTDATED") $r.Out
}
Finish 'intake'
