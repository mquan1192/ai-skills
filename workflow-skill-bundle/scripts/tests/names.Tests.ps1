# names.Tests.ps1 - ConvertTo-CfName maps the old script values (NAMES template, section 3) to the new names. ASCII only.
# Per kind (CardState / Phase / TicketState / Verdict / Receipt): old -> new, new -> itself, unknown or foreign value -> returned
# as is (the calling script reports the error). Part A: pure function, nothing written. Part B: the scripts on a fake tree
# read old values from the files and write only the new ones (old records are not rewritten).
param([switch]$Keep, [switch]$RedProof)
. (Join-Path $PSScriptRoot '_lib.ps1')
Test-Ps5Only @('ticket.ps1')   # Windows PowerShell 5.1: only the refusal of ticket.ps1, then exit
Write-Output '===== names ====='
Import-Module (Join-Path $script:Src 'CardFlow.psm1') -Force -DisableNameChecking
$have = [bool](Get-Command ConvertTo-CfName -ErrorAction SilentlyContinue)
Check 'ConvertTo-CfName is exported by CardFlow.psm1' $have

# ---------------- A: the table ----------------
# Old (script value) -> New. Unchanged values have Old = New.
$table = [ordered]@{
    CardState   = @(
        @('DRAFT', 'DRAFT'), @('READY', 'READY'), @('BUILDING', 'BUILDING'),
        @('CANDIDATE', 'IN-REVIEW'), @('FIXES', 'FIXING'), @('MERGED', 'RELEASED'), @('CLOSED', 'CANCELLED'))
    Phase       = @(
        @('P1', 'BUILD'), @('GATE', 'TEST-GATE'),
        @('REVIEW', 'REVIEW'), @('RELEASE', 'RELEASE'), @('RETRO', 'RETRO'),
        @('FIXES', 'FIX'), @('VERIFY', 'VERIFY-FIX'))
    TicketState = @(
        @('SENT', 'SENT'), @('ACCEPTED', 'ACCEPTED'), @('DONE', 'DONE'),
        @('HOLD', 'ON-HOLD'), @('TAKEOVER', 'TAKEN-OVER'))
    Verdict     = @(
        @('PASS', 'PASS'), @('NG', 'FAIL'), @('FIXES_VERIFIED', 'FIX-VERIFIED'))
    Receipt     = @(
        @('STALE', 'OUTDATED'), @('PARTIAL', 'PARTIAL'))
}

function CfName([string]$Kind, [string]$Value) {
    try { return [string](ConvertTo-CfName -Kind $Kind -Value $Value) } catch { return '(error: ' + $_.Exception.Message + ')' }
}

foreach ($kind in $table.Keys) {
    foreach ($pair in $table[$kind]) {
        $old = $pair[0]; $new = $pair[1]
        $got = CfName $kind $old
        Check "$kind old '$old' -> '$new'" ($got -ceq $new) "got '$got'"
        if ($old -cne $new) {
            $got2 = CfName $kind $new
            Check "$kind new '$new' -> itself" ($got2 -ceq $new) "got '$got2'"
        }
    }
}
Check 'FIXES is kind dependent: CardState FIXING, Phase FIX' (((CfName 'CardState' 'FIXES') -ceq 'FIXING') -and ((CfName 'Phase' 'FIXES') -ceq 'FIX'))
foreach ($kind in $table.Keys) {
    $got = CfName $kind 'NO-SUCH-VALUE'
    Check "$kind unknown value is returned as is" ($got -ceq 'NO-SUCH-VALUE') "got '$got'"
}
Check 'TicketState: phase word P1 is returned as is' ((CfName 'TicketState' 'P1') -ceq 'P1')
Check 'Receipt: card word MERGED is returned as is' ((CfName 'Receipt' 'MERGED') -ceq 'MERGED')
$news = @($table.Values | ForEach-Object { $_ } | ForEach-Object { $_[1] } | Sort-Object -Unique)
$expect = @('ACCEPTED', 'BUILD', 'BUILDING', 'CANCELLED', 'DONE', 'DRAFT', 'FAIL', 'FIX', 'FIX-VERIFIED', 'FIXING', 'IN-REVIEW', 'ON-HOLD', 'OUTDATED', 'PARTIAL', 'PASS', 'READY', 'RELEASE', 'RELEASED', 'RETRO', 'REVIEW', 'SENT', 'TAKEN-OVER', 'TEST-GATE', 'VERIFY-FIX')
Check 'table targets = the new names of section 3' (($news -join ',') -ceq (($expect | Sort-Object) -join ',')) ($news -join ',')

# ---------------- B: scripts read old values, write new ones ----------------
# old card state CANDIDATE + old tickets (P1 DONE, REVIEW DONE "NG ...") -> board / intake show the new names
$W = New-FakeTree 'names-scripts'
$cd = New-FakeCard $W '001-fake' -State 'CANDIDATE'
WF (Join-Path $cd 'baseline.manifest') ''
WF (P $W '2026-11/09_01-fake-task/out/tools/fake/a.ps1') 'Write-Output 1'
$dg = Get-Digest $W
Add-Ticket $W '001-fake' 1 'LEAD' 'BUILD' 'P1' 'DONE'
Add-Ticket $W '001-fake' 2 'BUILD' 'REVIEW' 'REVIEW' 'DONE' $dg -Verdict 'NG'
$t2before = RF (Join-Path $cd 'handoff\H-02.json')
$r = Run 'board' @{} $W
$prog = RF (P $W 'docs/process/PROGRESS.md')
Check 'board: old card state CANDIDATE shown as IN-REVIEW, old verdict NG shown as FAIL' ($r.Exit -eq 0 -and $prog -match '\| 001-fake \| IN-REVIEW \|' -and $prog -match 'H-02 REVIEW DONE FAIL') $prog
$r = Run 'intake' @{ Card = '001-fake' } $W
Check 'intake: state IN-REVIEW; Next = FIX ticket after FAIL' ($r.Exit -eq 0 -and $r.Out -match 'state IN-REVIEW' -and $r.Out -match 'Phase FIX\)') $r.Out
Check 'old records are not rewritten (H-02 unchanged, CARD.md still CANDIDATE)' ((RF (Join-Path $cd 'handoff\H-02.json')) -ceq $t2before -and (RF (Join-Path $cd 'CARD.md')) -match '(?m)^state: CANDIDATE$') ''
# old -Phase value on send -> new value written; the bell shows the new name
$r = Run 'ticket' @{ Action = 'send'; Card = '001-fake'; As = 'LEAD'; To = 'BUILD'; Phase = 'FIXES' } $W
$j3 = RF (Join-Path $cd 'handoff\H-03.json') | ConvertFrom-Json
Check 'ticket send -Phase FIXES (old) -> H-03 phase FIX, bell names FIX' ($r.Exit -eq 0 -and $j3.phase -ceq 'FIX' -and $r.Out -match "BUILD $([char]0x00B7) FIX") $r.Out
# no old value is written by any script: the files written in part B hold only new names
$written = (RF (Join-Path $cd 'handoff\H-03.json')) + (RF (P $W 'docs/process/PROGRESS.md'))
Check 'files written hold no old name (P1, FIXES, VERIFY, HOLD, TAKEOVER, NG, FIXES_VERIFIED, STALE, CANDIDATE, MERGED, CLOSED) except in old records' ($written -cnotmatch '"(P1|FIXES|VERIFY|HOLD|TAKEOVER|NG|FIXES_VERIFIED|STALE)"' -and $prog -cnotmatch '\| (CANDIDATE|MERGED|CLOSED|FIXES) \|') ''

Finish 'names'
