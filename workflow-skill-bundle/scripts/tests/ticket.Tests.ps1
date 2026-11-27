# ticket.ps1 - send / accept / done / hold / takeover, one open ticket, bell, freeze, REVIEW verdict + STALE. Fake tree only.
param([switch]$Keep, [switch]$RedProof)
. (Join-Path $PSScriptRoot '_lib.ps1')
Test-Ps5Only @('ticket.ps1')   # Windows PowerShell 5.1: only the refusal of ticket.ps1, then exit
Write-Output '===== ticket ====='
$W = New-FakeTree 'ticket'
$cd = New-FakeCard $W '001-fake'
$hd = Join-Path $cd 'handoff'
$zone = P $W '2026-11/09_01-fake-task/out/tools/fake'
WF (Join-Path $zone 'a.ps1') 'Write-Output 1'
$T = { param($n) Join-Path $hd ('H-{0:D2}.json' -f $n) }

# first ticket only by LEAD
$r = Run 'ticket' @{ Action = 'send'; Card = '001-fake'; As = 'BUILD'; To = 'REVIEW'; Phase = 'P1' } $W
Check 'first ticket by BUILD -> refused, no file' ($r.Exit -eq 1 -and $r.Out -match 'REFUSED' -and -not (Test-Path (& $T 1))) $r.Out

# session map (local, outside the workspace): the receiver's id is printed, never stored
$fakeId = 'local' + '_' + [guid]::NewGuid().ToString()
$map = Join-Path (Split-Path $W) 'sessions.json'
WF $map ('{ "BUILD": { "title": "Dev-H", "id": "' + $fakeId + '" }, "LEAD": { "title": "Lead-0", "id": "x" } }')
$r = Run 'ticket' @{ Action = 'send'; Card = '001-fake'; As = 'LEAD'; To = 'BUILD'; Phase = 'P1'; Note = 'start P1'; Agent = 'Claude Opus high'; SessionMap = $map } $W
Check 'LEAD send H-01 -> exit 0, H-01.json' ($r.Exit -eq 0 -and (Test-Path (& $T 1))) $r.Out
$lines = @($r.Out -split "`r?`n")
$i = [array]::FindIndex([string[]]$lines, [Predicate[string]] { param($l) $l.StartsWith('[TICKET ') })
$bell = if ($i -ge 0) { $lines[$i..($i + 4)] } else { @('', '', '', '', '') }
$arrow = [string][char]0x2192; $dash = [string][char]0x2014
Check 'bell = exactly 4 lines in README format' (
    $bell[0] -eq "[TICKET 001-fake H-01] LEAD $arrow BUILD $($script:Dot) BUILD" -and
    $bell[1] -eq 'Card: docs/cards/001-fake/CARD.md (Takeover)' -and
    $bell[2] -eq "Ticket: docs/cards/001-fake/handoff/H-01.json $($script:Dot) manifest $dash" -and
    $bell[3] -match '^Sent \d\d/\d\d \d{2}:\d{2} by Lead-0$' -and $bell[4] -eq '') ($bell -join ' / ')
Check 'ring line shows the map id on the console only' ($r.Out.Contains($fakeId) -and -not (RF (& $T 1)).Contains('local' + '_')) ''
$j = RF (& $T 1) | ConvertFrom-Json
$fields = @('card', 'n', 'from', 'to', 'phase', 'manifest_digest', 'state', 'agent', 'history')
Check 'H-01 has every README field, state SENT, n=1' ((@($fields | Where-Object { $null -eq $j.PSObject.Properties[$_] }).Count -eq 0) -and $j.state -eq 'SENT' -and $j.n -eq 1 -and @($j.history).Count -eq 1)

# second open ticket refused (SENT counts as open)
$r = Run 'ticket' @{ Action = 'send'; Card = '001-fake'; As = 'LEAD'; To = 'REVIEW'; Phase = 'REVIEW' } $W
Check '2nd send while H-01 SENT -> refused, no H-02' ($r.Exit -eq 1 -and -not (Test-Path (& $T 2))) $r.Out

# illegal transitions
$before = RF (& $T 1)
$r = Run 'ticket' @{ Action = 'accept'; Card = '001-fake'; As = 'LEAD' } $W
Check 'accept by the sender (LEAD) -> refused, file unchanged' ($r.Exit -eq 1 -and (RF (& $T 1)) -eq $before) $r.Out
$r = Run 'ticket' @{ Action = 'done'; Card = '001-fake'; As = 'BUILD' } $W
Check 'done before accept -> refused, file unchanged' ($r.Exit -eq 1 -and (RF (& $T 1)) -eq $before) $r.Out
$r = Run 'ticket' @{ Action = 'hold'; Card = '001-fake'; As = 'LEAD'; Note = 'pause' } $W
Check 'hold by the sender -> refused' ($r.Exit -eq 1 -and (RF (& $T 1)) -eq $before) $r.Out
$r = Run 'ticket' @{ Action = 'accept'; Card = '001-fake'; As = 'BUILD'; Note = 'ok' } $W
$j = RF (& $T 1) | ConvertFrom-Json
Check 'BUILD accept -> ACCEPTED, history 2, first entry unchanged' ($r.Exit -eq 0 -and $j.state -eq 'ACCEPTED' -and @($j.history).Count -eq 2 -and $j.history[0].note -eq 'start P1' -and $j.history[0].by -eq 'LEAD') $r.Out
$r = Run 'ticket' @{ Action = 'accept'; Card = '001-fake'; As = 'BUILD' } $W
Check 'accept on ACCEPTED -> refused' ($r.Exit -eq 1) $r.Out

# baseline (P1 start), then done + freeze send to REVIEW
$r = Run 'ticket' @{ Action = 'send'; Card = '001-fake'; As = 'BUILD'; To = 'REVIEW'; Phase = 'REVIEW' } $W
Check 'send while own ticket still open -> refused' ($r.Exit -eq 1 -and -not (Test-Path (& $T 2))) $r.Out
$r = Run 'manifest' @{ Card = '001-fake'; Baseline = $true; As = 'BUILD' } $W
Check 'baseline written by the holder' ($r.Exit -eq 0 -and (Test-Path (Join-Path $cd 'baseline.manifest'))) $r.Out
$r = Run 'ticket' @{ Action = 'done'; Card = '001-fake'; As = 'BUILD'; Note = 'P1 done' } $W
Check 'BUILD done -> DONE' ($r.Exit -eq 0 -and (RF (& $T 1) | ConvertFrom-Json).state -eq 'DONE') $r.Out
$r = Run 'ticket' @{ Action = 'done'; Card = '001-fake'; As = 'BUILD' } $W
Check 'done on DONE -> refused (no open ticket)' ($r.Exit -eq 1) $r.Out
$r = Run 'ticket' @{ Action = 'send'; Card = '001-fake'; As = 'REVIEW'; To = 'BUILD'; Phase = 'FIXES' } $W
Check 'send by a role whose turn it is not (REVIEW) -> refused' ($r.Exit -eq 1 -and -not (Test-Path (& $T 2))) $r.Out
$r = Run 'ticket' @{ Action = 'send'; Card = '001-fake'; As = 'BUILD'; To = 'REVIEW'; Phase = 'review'; Session = 'Dev-H' } $W
$j2 = RF (& $T 2) | ConvertFrom-Json
$dg = Get-Digest $W
Check 'BUILD send to REVIEW -> H-02 (two digits) frozen: digest + manifest lines' ($r.Exit -eq 0 -and $j2.manifest_digest -eq $dg -and @($j2.manifest).Count -eq 1 -and $j2.manifest[0] -match '^[0-9a-f]{64}  tools/fake/a\.ps1$' -and $j2.phase -eq 'REVIEW') $r.Out
Check 'bell shows the first 12 of the digest' ($r.Out.Contains("manifest $($dg.Substring(0, 12))")) $r.Out
Check 'no map entry for REVIEW -> paste hint, no error' ($r.Out -match 'paste the 4 bell lines') $r.Out

# REVIEW: verdict required, STALE refused
$null = Run 'ticket' @{ Action = 'accept'; Card = '001-fake'; As = 'REVIEW' } $W
$before = RF (& $T 2)
$r = Run 'ticket' @{ Action = 'done'; Card = '001-fake'; As = 'REVIEW'; Note = 'looks good' } $W
Check 'REVIEW done without PASS / NG / FIXES_VERIFIED -> refused' ($r.Exit -eq 1 -and (RF (& $T 2)) -eq $before) $r.Out
$r = Run 'ticket' @{ Action = 'done'; Card = '001-fake'; As = 'REVIEW'; Note = 'pass' } $W
Check 'lower-case verdict -> refused' ($r.Exit -eq 1) $r.Out
WF (Join-Path $zone 'a.ps1') 'Write-Output 2'
$r = Run 'ticket' @{ Action = 'done'; Card = '001-fake'; As = 'REVIEW'; Note = 'PASS' } $W
Check 'REVIEW done after a zone change -> OUTDATED refused' ($r.Exit -eq 1 -and $r.Out -match 'OUTDATED' -and (RF (& $T 2)) -eq $before) $r.Out
WF (Join-Path $zone 'a.ps1') 'Write-Output 1'
$r = Run 'ticket' @{ Action = 'done'; Card = '001-fake'; As = 'REVIEW'; Note = 'NG 2 findings' } $W
Check 'REVIEW done NG at the frozen digest -> DONE' ($r.Exit -eq 0 -and (RF (& $T 2) | ConvertFrom-Json).state -eq 'DONE') $r.Out

# FIXES ticket by REVIEW (last receiver), takeover, hold, never overwrite
$r = Run 'ticket' @{ Action = 'send'; Card = '001-fake'; As = 'REVIEW'; To = 'BUILD'; Phase = 'FIXES'; Note = 'see qa report' } $W
Check 'last receiver (REVIEW) may send the next ticket -> H-03' ($r.Exit -eq 0 -and (Test-Path (& $T 3))) $r.Out
$r = Run 'ticket' @{ Action = 'takeover'; Card = '001-fake'; As = 'BUILD' } $W
Check 'takeover without -Session -> refused' ($r.Exit -eq 1) $r.Out
$r = Run 'ticket' @{ Action = 'takeover'; Card = '001-fake'; As = 'BUILD'; Session = 'Dev-X' } $W
$log = RF (Join-Path $cd 'log.md')
Check 'takeover -> TAKEN-OVER (new name written) + log line "<session> as <ROLE> took over <card> at <digest>"' ($r.Exit -eq 0 -and (RF (& $T 3) | ConvertFrom-Json).state -eq 'TAKEN-OVER' -and $log -match "Dev-X as BUILD took over 001-fake at $dg") $r.Out
$r = Run 'ticket' @{ Action = 'hold'; Card = '001-fake'; As = 'BUILD' } $W
Check 'hold without -Note -> refused' ($r.Exit -eq 1) $r.Out
$r = Run 'ticket' @{ Action = 'hold'; Card = '001-fake'; As = 'BUILD'; Note = 'waiting for LEAD' } $W
Check 'hold with note -> ON-HOLD (new name written; still open)' ($r.Exit -eq 0 -and (RF (& $T 3) | ConvertFrom-Json).state -eq 'ON-HOLD') $r.Out
$r = Run 'ticket' @{ Action = 'send'; Card = '001-fake'; As = 'LEAD'; To = 'OPS'; Phase = 'GATE' } $W
Check 'send while H-03 HOLD -> refused (HOLD counts as open)' ($r.Exit -eq 1 -and -not (Test-Path (& $T 4))) $r.Out
$r = Run 'ticket' @{ Action = 'accept'; Card = '001-fake'; As = 'BUILD' } $W
$null = Run 'ticket' @{ Action = 'done'; Card = '001-fake'; As = 'BUILD'; Note = 'fixed' } $W
$j3 = RF (& $T 3) | ConvertFrom-Json
Check 'history keeps every entry (SENT TAKEOVER HOLD ACCEPTED DONE) after many writes (no depth loss)' (@($j3.history).Count -eq 5 -and $j3.state -eq 'DONE' -and $j3.history[0].note -eq 'see qa report') "count=$(@($j3.history).Count)"
[void][IO.Directory]::CreateDirectory((& $T 4))   # something already sits at H-04.json -> CreateNew must fail
$r = Run 'ticket' @{ Action = 'send'; Card = '001-fake'; As = 'LEAD'; To = 'REVIEW'; Phase = 'VERIFY' } $W
Check 'existing H-04.json path -> send fails, nothing overwritten' ($r.Exit -eq 1 -and (Test-Path (& $T 4) -PathType Container)) $r.Out

# guards
$sid = 'local' + '_' + [guid]::NewGuid().ToString()
$W2 = New-FakeTree 'ticket2'
$cd2 = New-FakeCard $W2 '002-other'
$r = Run 'ticket' @{ Action = 'send'; Card = '002-other'; As = 'LEAD'; To = 'BUILD'; Phase = 'P1'; Note = "ring $sid" } $W2
Check 'session ID in the note -> refused, no ticket' ($r.Exit -eq 1 -and -not (Test-Path (Join-Path $cd2 'handoff\H-01.json'))) $r.Out
$r = Run 'ticket' @{ Action = 'send'; Card = '002-other'; As = 'LEAD'; To = 'BUILD'; Phase = 'P9' } $W2
Check 'unknown phase -> refused' ($r.Exit -eq 1) $r.Out
$r = Run 'ticket' @{ Action = 'send'; Card = '009-missing'; As = 'LEAD'; To = 'BUILD'; Phase = 'P1' } $W2
Check 'unknown card -> refused' ($r.Exit -eq 1 -and $r.Out -match 'not found') $r.Out
WF (Join-Path $cd2 'handoff\H-01.json') '{ "card": "002-other", "n": 1, '
$r = Run 'ticket' @{ Action = 'accept'; Card = '002-other'; As = 'BUILD' } $W2
Check 'malformed ticket JSON -> refused, file unchanged' ($r.Exit -eq 1 -and $r.Out -match 'malformed' -and (RF (Join-Path $cd2 'handoff\H-01.json')) -eq '{ "card": "002-other", "n": 1, ') $r.Out
# F2: misnamed / stray files in handoff/ are refused (a hidden open ticket would allow a 2nd one)
$cd3 = New-FakeCard $W2 '003-misnamed'
WF (Join-Path $cd3 'handoff\H-3.json') '{ "card": "003-misnamed", "n": 3, "from": "LEAD", "to": "BUILD", "phase": "P1", "manifest_digest": "", "state": "SENT", "agent": "x", "history": [ { "at": "2026-11-09T09:00", "by": "LEAD", "state": "SENT", "note": "x" } ] }'
$r = Run 'ticket' @{ Action = 'send'; Card = '003-misnamed'; As = 'LEAD'; To = 'BUILD'; Phase = 'P1' } $W2
Check 'F2: open ticket in H-3.json -> send refused, no H-01 / H-03 written' ($r.Exit -eq 1 -and $r.Out -match 'H-3\.json is not a ticket name' -and @(Get-ChildItem -LiteralPath (Join-Path $cd3 'handoff')).Count -eq 1) $r.Out
$cd4 = New-FakeCard $W2 '004-stray'
WF (Join-Path $cd4 'handoff\notes.txt') 'x'
$r = Run 'ticket' @{ Action = 'send'; Card = '004-stray'; As = 'LEAD'; To = 'BUILD'; Phase = 'P1' } $W2
Check 'F2: stray file in handoff/ -> refused' ($r.Exit -eq 1 -and $r.Out -match 'notes\.txt is not a ticket name') $r.Out
$cd5 = New-FakeCard $W2 '005-dup'
Add-Ticket $W2 '005-dup' 1 'LEAD' 'BUILD' 'P1' 'DONE'
Copy-Item -LiteralPath (Join-Path $cd5 'handoff\H-01.json') -Destination (Join-Path $cd5 'handoff\H-001.json')
$r = Run 'ticket' @{ Action = 'send'; Card = '005-dup'; As = 'LEAD'; To = 'BUILD'; Phase = 'P1' } $W2
Check 'F2: two files with the same n (H-01, H-001) -> refused' ($r.Exit -eq 1 -and $r.Out -match 'two tickets with n=1') $r.Out
$tok = 'to' + 'ken: Hn4tR8wQ2zL'
$r = Run 'ticket' @{ Action = 'send'; Card = '002-other'; As = 'LEAD'; To = 'BUILD'; Phase = 'P1'; Note = $tok } $W2
Check 'F3: unquoted secret form in a note -> refused' ($r.Exit -eq 1 -and $r.Out -match 'looks like a secret' -and -not $r.Out.Contains('Hn4tR8wQ2zL')) $r.Out
$r = Run 'ticket' @{ Action = 'send'; Card = '002-other'; As = 'LEAD'; To = 'BUILD'; Phase = 'P1' } (Join-Path $W2 'kb')
Check 'wrong -Root (no .workflow/workflow.config.json) -> refused with the install hint' ($r.Exit -eq 1 -and $r.Out -match 'not a project root' -and $r.Out -match 'chay install\.py') $r.Out
# STALE close of a REVIEW ticket (no verdict), LEAD fallback, then a new frozen send
$W6 = New-FakeTree 'ticket-stale'
$cd6 = New-FakeCard $W6 '006-stale'
$z6 = P $W6 '2026-11/09_01-fake-task/out/tools/fake'
WF (Join-Path $z6 'a.ps1') 'Write-Output 1'
$T6 = { param($n) Join-Path $cd6 ('handoff\H-{0:D2}.json' -f $n) }
$null = Run 'ticket' @{ Action = 'send'; Card = '006-stale'; As = 'LEAD'; To = 'BUILD'; Phase = 'P1' } $W6
$null = Run 'ticket' @{ Action = 'accept'; Card = '006-stale'; As = 'BUILD' } $W6
$null = Run 'manifest' @{ Card = '006-stale'; Baseline = $true; As = 'BUILD' } $W6
$null = Run 'ticket' @{ Action = 'done'; Card = '006-stale'; As = 'BUILD'; Note = 'built' } $W6
$r = Run 'ticket' @{ Action = 'send'; Card = '006-stale'; As = 'LEAD'; To = 'REVIEW'; Phase = 'REVIEW'; Freeze = $true } $W6
$d1 = Get-Digest $W6 '006-stale'
Check 'LEAD frozen send to REVIEW -> H-02 at the current digest' ($r.Exit -eq 0 -and (RF (& $T6 2) | ConvertFrom-Json).manifest_digest -eq $d1) $r.Out
$null = Run 'ticket' @{ Action = 'accept'; Card = '006-stale'; As = 'REVIEW' } $W6
$before = RF (& $T6 2)
$r = Run 'ticket' @{ Action = 'done'; Card = '006-stale'; As = 'REVIEW'; Note = 'STALE nothing changed' } $W6
Check 'red-proof a: STALE close at the frozen digest -> refused, ticket unchanged' ($r.Exit -eq 1 -and $r.Out -match 'is not OUTDATED' -and (RF (& $T6 2)) -eq $before) $r.Out
WF (Join-Path $z6 'a.ps1') 'Write-Output 2'
$d2 = Get-Digest $W6 '006-stale'
$null = Run 'ticket' @{ Action = 'hold'; Card = '006-stale'; As = 'REVIEW'; Note = 'files changed after the freeze' } $W6
$r = Run 'ticket' @{ Action = 'send'; Card = '006-stale'; As = 'LEAD'; To = 'REVIEW'; Phase = 'REVIEW'; Freeze = $true } $W6
Check 'dead end - LEAD send while the STALE ticket is open -> refused' ($r.Exit -eq 1 -and -not (Test-Path (& $T6 3))) $r.Out
$null = Run 'ticket' @{ Action = 'accept'; Card = '006-stale'; As = 'REVIEW' } $W6
$r = Run 'ticket' @{ Action = 'done'; Card = '006-stale'; As = 'REVIEW'; Note = 'PASS' } $W6
Check 'a verdict on an OUTDATED ticket is still refused (and hints the OUTDATED close)' ($r.Exit -eq 1 -and $r.Out -match "close it with -Note 'OUTDATED") $r.Out
$r = Run 'ticket' @{ Action = 'done'; Card = '006-stale'; As = 'BUILD'; Note = 'STALE' } $W6
Check 'STALE close by BUILD (not receiver, not LEAD) -> refused' ($r.Exit -eq 1 -and $r.Out -match 'only the receiver') $r.Out
$null = Run 'ticket' @{ Action = 'hold'; Card = '006-stale'; As = 'REVIEW'; Note = 'waiting for LEAD' } $W6
$r = Run 'ticket' @{ Action = 'done'; Card = '006-stale'; As = 'REVIEW'; Note = 'STALE zone changed' } $W6
$j6 = RF (& $T6 2) | ConvertFrom-Json
$log6 = RF (Join-Path $cd6 'log.md')
$tag = "closed OUTDATED at $($d1.Substring(0, 12)) (current $($d2.Substring(0, 12)))"
Check 'REVIEW close typed "STALE ..." (old) from ON-HOLD -> DONE, note written "OUTDATED ... closed OUTDATED at <frozen> (current <digest>)"' ($r.Exit -eq 0 -and $j6.state -eq 'DONE' -and $j6.history[-1].note.StartsWith('OUTDATED zone changed') -and $j6.history[-1].note.Contains($tag) -and $r.Out -match 'no verdict') $r.Out
Check 'log.md line "<role> H-02 closed OUTDATED at ... (no verdict)"' ($log6.Contains("REVIEW H-02 $tag (no verdict)")) $log6
$r = Run 'ticket' @{ Action = 'send'; Card = '006-stale'; As = 'LEAD'; To = 'REVIEW'; Phase = 'REVIEW'; Freeze = $true } $W6
Check 'after the STALE close LEAD sends a new frozen ticket at the current digest -> H-03' ($r.Exit -eq 0 -and (RF (& $T6 3) | ConvertFrom-Json).manifest_digest -eq $d2) $r.Out
WF (Join-Path $z6 'a.ps1') 'Write-Output 3'
$r = Run 'ticket' @{ Action = 'done'; Card = '006-stale'; As = 'LEAD'; Note = 'STALE REVIEW gone' } $W6
$j7 = RF (& $T6 3) | ConvertFrom-Json
Check 'LEAD fallback STALE close (ticket still SENT) -> DONE by LEAD' ($r.Exit -eq 0 -and $j7.state -eq 'DONE' -and $j7.history[-1].by -eq 'LEAD') $r.Out
$null = Run 'ticket' @{ Action = 'send'; Card = '006-stale'; As = 'LEAD'; To = 'REVIEW'; Phase = 'REVIEW'; Freeze = $true } $W6
$r = Run 'ticket' @{ Action = 'done'; Card = '006-stale'; As = 'LEAD'; Note = 'PASS' } $W6
Check 'LEAD cannot give a verdict on a REVIEW ticket' ($r.Exit -eq 1 -and $r.Out -match 'only the receiver') $r.Out
$r = Run 'ticket' @{ Action = 'done'; Card = '006-stale'; As = 'LEAD'; Note = 'STALE' } $W6
Check 'LEAD STALE close at the frozen digest -> refused' ($r.Exit -eq 1 -and $r.Out -match 'is not OUTDATED') $r.Out

# ---------- readable names: old names are read, new names are written, old records are not rewritten ----------
$W8 = New-FakeTree 'ticket-names'
$null = New-FakeCard $W8 '008-names' @('2026-11/09_01-fake-task/out/tools/fake')
WF (P $W8 '2026-11/09_01-fake-task/out/tools/fake/a.ps1') 'Write-Output 1'
$T8 = { param($n) Join-Path $W8 ("docs\cards\008-names\handoff\H-{0:D2}.json" -f $n) }
Add-Ticket $W8 '008-names' 1 'LEAD' 'BUILD' 'P1' 'HOLD' -Hist @('2026-01-05T09:00|LEAD|SENT|start', '2026-01-05T09:10|BUILD|HOLD|wait for LEAD')
$null = Run 'manifest' @{ Card = '008-names'; Baseline = $true; As = 'BUILD' } $W8
$r = Run 'ticket' @{ Action = 'accept'; Card = '008-names'; As = 'BUILD' } $W8
$j = RF (& $T8 1) | ConvertFrom-Json
Check 'names: old ticket (phase P1, state HOLD) is read: accept -> ACCEPTED, shown as ON-HOLD; old phase + history lines kept as written' ($r.Exit -eq 0 -and $r.Out -match 'ON-HOLD' -and $j.state -eq 'ACCEPTED' -and $j.phase -eq 'P1' -and $j.history[1].state -eq 'HOLD' -and @($j.history).Count -eq 3) $r.Out
$null = Run 'ticket' @{ Action = 'done'; Card = '008-names'; As = 'BUILD'; Note = 'built' } $W8
$r = Run 'ticket' @{ Action = 'send'; Card = '008-names'; As = 'BUILD'; To = 'REVIEW'; Phase = 'VERIFY' } $W8
Check 'names: -Phase VERIFY (old) accepted, written VERIFY-FIX' ($r.Exit -eq 0 -and (RF (& $T8 2) | ConvertFrom-Json).phase -eq 'VERIFY-FIX') $r.Out
$null = Run 'ticket' @{ Action = 'accept'; Card = '008-names'; As = 'REVIEW' } $W8
$r = Run 'ticket' @{ Action = 'done'; Card = '008-names'; As = 'REVIEW'; Note = 'NG 2 findings' } $W8
$j = RF (& $T8 2) | ConvertFrom-Json
Check 'names: REVIEW -Note "NG ..." (old) accepted, written "FAIL ..."' ($r.Exit -eq 0 -and $j.history[-1].note -ceq 'FAIL 2 findings') $r.Out
$r = Run 'ticket' @{ Action = 'send'; Card = '008-names'; As = 'REVIEW'; To = 'BUILD'; Phase = 'NOPE' } $W8
Check 'names: unknown -Phase -> refused, message lists the new names' ($r.Exit -eq 1 -and $r.Out -match 'BUILD, TEST-GATE, REVIEW, FIX, VERIFY-FIX, RELEASE, RETRO') $r.Out
$r = Run 'ticket' @{ Action = 'send'; Card = '008-names'; As = 'REVIEW'; To = 'BUILD'; Phase = 'fix' } $W8
Check 'names: -Phase fix (new, any case) -> written FIX' ($r.Exit -eq 0 -and (RF (& $T8 3) | ConvertFrom-Json).phase -eq 'FIX') $r.Out
$null = Run 'ticket' @{ Action = 'accept'; Card = '008-names'; As = 'BUILD' } $W8
$null = Run 'ticket' @{ Action = 'done'; Card = '008-names'; As = 'BUILD'; Note = 'fixed' } $W8
$null = Run 'ticket' @{ Action = 'send'; Card = '008-names'; As = 'BUILD'; To = 'REVIEW'; Phase = 'VERIFY-FIX' } $W8
$null = Run 'ticket' @{ Action = 'accept'; Card = '008-names'; As = 'REVIEW' } $W8
$r = Run 'ticket' @{ Action = 'done'; Card = '008-names'; As = 'REVIEW'; Note = 'FIX-VERIFIED all closed' } $W8
Check 'names: REVIEW -Note "FIX-VERIFIED ..." (new) accepted as written' ($r.Exit -eq 0 -and (RF (& $T8 4) | ConvertFrom-Json).history[-1].note -ceq 'FIX-VERIFIED all closed') $r.Out
Finish 'ticket'
