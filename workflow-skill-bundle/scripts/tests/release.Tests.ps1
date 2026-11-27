# release.ps1 - only -IfSafe, LEAD only, every refusal leaves the card untouched, dry-run = same reasons, happy path.
param([switch]$Keep, [switch]$RedProof)
. (Join-Path $PSScriptRoot '_lib.ps1')
Test-Ps5Only @('release.ps1')   # Windows PowerShell 5.1: only the refusal of release.ps1, then exit
Write-Output '===== release ====='
$RS = @{ Card = '001-fake'; IfSafe = $true; As = 'LEAD' }
function Refused([string]$Name, $T, [string]$Expect) {
    $h0 = Get-TreeHash $T.W
    $r = Run 'release' $RS $T.W
    Check "$Name -> refused, exit 1, tree unchanged" ($r.Exit -eq 1 -and $r.Out -match 'REFUSED' -and $r.Out -match $Expect -and (Get-TreeHash $T.W) -eq $h0) $r.Out
}

# parameter block: nothing that can skip a check (Q3)
$tok = $null; $err = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile((Join-Path $script:Src 'release.ps1'), [ref]$tok, [ref]$err)
$names = @($ast.ParamBlock.Parameters | ForEach-Object { $_.Name.VariablePath.UserPath }) | Sort-Object
Check 'release.ps1 params = Card, IfSafe, DryRun, As, Root only (no -Force / -Skip*)' (($names -join ',') -eq 'As,Card,DryRun,IfSafe,Root') ($names -join ',')

$T = New-ReleaseTree 'rel-flags'
$h0 = Get-TreeHash $T.W
$r = Run 'release' @{ Card = '001-fake'; As = 'LEAD' } $T.W
Check 'without -IfSafe -> refused, tree unchanged' ($r.Exit -eq 1 -and $r.Out -match 'no release without -IfSafe' -and (Get-TreeHash $T.W) -eq $h0) $r.Out
$r = Run 'release' @{ Card = '001-fake'; IfSafe = $true; As = 'BUILD' } $T.W
Check '-As BUILD -> refused (LEAD only, limit stated)' ($r.Exit -eq 1 -and $r.Out -match 'logged, not proven' -and (Get-TreeHash $T.W) -eq $h0) $r.Out

# REVIEW state
$T = New-ReleaseTree 'rel-norev'
Add-Ticket $T.W '001-fake' 2 'BUILD' 'REVIEW' 'REVIEW' 'ACCEPTED' $T.Digest
Refused 'REVIEW ticket still ACCEPTED (no REVIEW DONE)' $T 'no REVIEW ticket DONE'
$T = New-ReleaseTree 'rel-ng' -Verdict 'NG'
Refused 'REVIEW verdict NG (old name in the ticket, read as FAIL)' $T "verdict is 'FAIL'"
$T = New-ReleaseTree 'rel-old'
WF (Join-Path $T.Z2 'a.ps1') 'Write-Output 3'
Write-Gate $T.W (Get-Digest $T.W) 'PASS'
Refused 'PASS at an older digest (file changed after review)' $T 'files changed after review'

# gate receipt
$T = New-ReleaseTree 'rel-nogate' -NoGate
Refused 'gate.json missing' $T 'gate receipt missing'
$T = New-ReleaseTree 'rel-stale'
Write-Gate $T.W ('0' * 64) 'PASS'
Refused 'gate receipt OUTDATED (old: STALE)' $T 'gate receipt OUTDATED'
$T = New-ReleaseTree 'rel-gfail'
Write-Gate $T.W $T.Digest 'FAIL'
Refused 'gate result FAIL' $T "gate result is 'FAIL'"
# F1: one edition is not enough
$T = New-ReleaseTree 'rel-partial'
Write-Gate $T.W $T.Digest 'PARTIAL' -Hosts @('ps7')
Refused 'F1: gate result PARTIAL (one edition)' $T "gate result is 'PARTIAL'"
$T = New-ReleaseTree 'rel-onehost'
Write-Gate $T.W $T.Digest 'PASS' -Hosts @('ps7')
Refused 'F1: receipt says PASS but has no ps5 entry' $T 'gate receipt has no ps5 PASS for .*ok\.Tests\.ps1'
$T = New-ReleaseTree 'rel-current'
Write-Gate $T.W $T.Digest 'PASS' -Hosts @('current')
Refused 'F1: receipt with host "current" only' $T 'gate receipt has no ps5 PASS'
$T = New-ReleaseTree 'rel-notests'
Write-Gate $T.W $T.Digest 'PASS' -Hosts @()
Refused 'F1: receipt PASS with an empty tests list' $T 'gate receipt has no ps(5|7) PASS'
# old card states in CARD.md are read - MERGED / CLOSED count as RELEASED / CANCELLED (closed cards)
foreach ($p in @(@('MERGED', 'RELEASED'), @('CLOSED', 'CANCELLED'))) {
    $T = New-ReleaseTree ('rel-old-' + $p[0].ToLowerInvariant())
    $cm = Join-Path $T.Card 'CARD.md'; WF $cm ((RF $cm) -replace '(?m)^state:[ \t]*[A-Za-z_\-]+', ('state: ' + $p[0]))
    Refused "names: CARD.md state $($p[0]) (old name) is read as $($p[1])" $T "card is $($p[1])"
}
# a test file under paths.scripts that declares '#Requires -Version 7' needs a ps7 PASS only (red-proof partner: 'F1: receipt says PASS but has no ps5 entry')
$T = New-ReleaseTree 'rel-ps7only' -Ps7Test
Write-Gate $T.W $T.Digest 'PASS' -Hosts @('ps7')
$r = Run 'release' @{ Card = '001-fake'; IfSafe = $true; DryRun = $true; As = 'LEAD' } $T.W
Check 'receipt with a ps7 PASS only for a "#Requires -Version 7" test under paths.scripts -> dry run SAFE' ($r.Exit -eq 0 -and $r.Out -match 'all checks pass') $r.Out
# red proof: the same line in a test OUTSIDE paths.scripts still needs a ps5 PASS (gate.hosts ps5 + ps7)
$T = New-ReleaseTree 'rel-ps7outside' -Ps7Test -Ps7TestOutside
Write-Gate $T.W $T.Digest 'PASS' -Hosts @('ps7')
Refused '"#Requires -Version 7" test with target tools/fake, receipt ps7 only' $T 'gate receipt has no ps5 PASS for .*tools/fake/tests/x\.Tests\.ps1'
# F2: a misnamed ticket file cannot hide an open ticket
$T = New-ReleaseTree 'rel-misnamed'
WF (Join-Path $T.Card 'handoff\H-3.json') '{ "card": "001-fake", "n": 3, "from": "REVIEW", "to": "BUILD", "phase": "FIXES", "manifest_digest": "", "state": "SENT", "agent": "x", "history": [ { "at": "2026-11-09T09:00", "by": "REVIEW", "state": "SENT", "note": "x" } ] }'
Refused 'F2: open ticket in a misnamed file H-3.json' $T 'handoff/H-3\.json is not a ticket name'
# F6: .github/workflows/ is protected
$W6 = New-FakeTree 'rel-workflows'
$zw = '2026-11/09_01-fake-task/out/.github/workflows'
$cd6 = New-FakeCard $W6 '001-fake' @($zw)
WF (Join-Path $cd6 'baseline.manifest') ''
WF (Join-Path (P $W6 $zw) 'ci.yml') 'on: push'
WF (Join-Path (P $W6 $zw) 't\ok.Tests.ps1') 'exit 0'
$dg6 = Get-Digest $W6
Add-Ticket $W6 '001-fake' 1 'LEAD' 'BUILD' 'P1' 'DONE'
Add-Ticket $W6 '001-fake' 2 'BUILD' 'REVIEW' 'REVIEW' 'DONE' $dg6
Write-Gate $W6 $dg6 'PASS'
Refused 'F6: .github/workflows/ change not in protected_paths' ([pscustomobject]@{ W = $W6 }) 'not in protected_paths: \.github/workflows/ci\.yml'

# protected paths
$T = New-ReleaseTree 'rel-notlisted' -Protected @()
Refused 'protected path changed, not in protected_paths' $T 'not in protected_paths: scripts/process/a\.ps1'
$T = New-ReleaseTree 'rel-nosentence' -Decisions @('2026-11-09 LEAD: scripts/process/ is the install target')
Refused 'protected path listed but no owner sentence in Decisions' $T "no Decisions line with the owner's quoted sentence"
# F5: only the fixed approval form counts
$T = New-ReleaseTree 'rel-notapproved' -Decisions @('2026-11-09 owner has NOT approved "install later" for scripts/process/')
Refused 'F5: a line naming the path + owner + a quote but not the approval form' $T "no Decisions line with the owner's quoted sentence"
$T = New-ReleaseTree 'rel-otherpath' -Decisions @('owner 09/11 09:40: "ok, build and install it" -> approves scripts/other/')
Refused 'F5: approval form for another path' $T "no Decisions line with the owner's quoted sentence"
$T = New-ReleaseTree 'rel-trailing' -Decisions @('owner 09/11 09:40: "ok, build and install it" -> approves scripts/process/ but not yet')
Refused 'F5: approval form with extra words after the path' $T "no Decisions line with the owner's quoted sentence"
$uq = 'owner 09/11 09:40: ' + [char]0x201C + 'duoc, cai dat di' + [char]0x201D + ' ' + [char]0x2192 + ' approves tools/fake/, scripts/process/'
$T = New-ReleaseTree 'rel-unicode' -Decisions @($uq)
$r = Run 'release' ($RS + @{ DryRun = $true }) $T.W
Check 'F5: curly quotes + U+2192 arrow + path list accepted (dry run SAFE)' ($r.Exit -eq 0) $r.Out
$T = New-ReleaseTree 'rel-case' -Protected @('Scripts/Process/') -Decisions @('owner 09/11 09:40: "ok, go ahead" -> approves SCRIPTS\PROCESS\')
$r = Run 'release' ($RS + @{ DryRun = $true }) $T.W
Check 'protected_paths / Decisions match is case- and slash-insensitive (dry run SAFE)' ($r.Exit -eq 0 -and $r.Out -match 'DRY RUN: all checks pass') $r.Out

# protected file renamed / moved out of its path (baseline names it)
$T = New-ReleaseTree 'rel-moved' -Protected @()
Remove-Item -LiteralPath (Join-Path $T.Z2 'a.ps1') -Force
WF (Join-Path $T.Card 'baseline.manifest') ''
[IO.File]::Delete((Join-Path $T.Card 'baseline.manifest'))
WF (P $T.W 'scripts/process/guard.ps1') 'guard'
$sha = [Security.Cryptography.SHA256]::Create()
$gh = [BitConverter]::ToString($sha.ComputeHash($script:U8.GetBytes('guard'))).Replace('-', '').ToLowerInvariant()
WF (Join-Path $T.Card 'baseline.manifest') "$gh  scripts/process/guard.ps1`n"
WF (Join-Path $T.Z1 'guard.ps1') 'guard'          # moved out of scripts/process/ into tools/fake/
Remove-Item -LiteralPath (Join-Path $T.Z2 'tests') -Recurse -Force
WF (Join-Path $T.Z1 'tests\ok.Tests.ps1') 'exit 0'
$dg = Get-Digest $T.W
Add-Ticket $T.W '001-fake' 2 'BUILD' 'REVIEW' 'REVIEW' 'DONE' $dg
Write-Gate $T.W $dg 'PASS'
Refused 'protected file moved out of scripts/process/ (old name still listed)' $T 'scripts/process/guard\.ps1 \(removed\)'

# .Claude (case) and a junction into a protected path
$W3 = New-FakeTree 'rel-claude'
$zc = '2026-11/09_01-fake-task/out/.Claude/skills/x'
$cd3 = New-FakeCard $W3 '001-fake' @($zc)
WF (Join-Path $cd3 'baseline.manifest') ''
WF (Join-Path (P $W3 $zc) 'SKILL.md') 'x'
WF (Join-Path (P $W3 $zc) 't\ok.Tests.ps1') 'exit 0'
$dg3 = Get-Digest $W3
Add-Ticket $W3 '001-fake' 1 'LEAD' 'BUILD' 'P1' 'DONE'
Add-Ticket $W3 '001-fake' 2 'BUILD' 'REVIEW' 'REVIEW' 'DONE' $dg3
Write-Gate $W3 $dg3 'PASS'
Refused '.Claude\ (mixed case) path is protected' ([pscustomobject]@{ W = $W3 }) 'not in protected_paths: \.Claude/skills/x/SKILL\.md'
$T = New-ReleaseTree 'rel-junction'
[void][IO.Directory]::CreateDirectory((P $T.W '.claude\skills'))
New-Item -ItemType Junction -Path (Join-Path $T.Z1 'j') -Target (P $T.W '.claude\skills') | Out-Null
Refused 'junction inside a zone pointing into .claude\' $T 'junction / symlink'

# live target changed since the baseline; another open ticket
$T = New-ReleaseTree 'rel-drift'
WF (P $T.W 'tools/fake/sneaky.txt') 'added by someone else'
Refused 'live target changed since baseline.manifest' $T 'live target changed since baseline'
$T = New-ReleaseTree 'rel-open'
Add-Ticket $T.W '001-fake' 3 'REVIEW' 'BUILD' 'FIXES' 'SENT'
Refused 'an open ticket with BUILD' $T 'H-03 is open with BUILD'

# dry run = same reasons as the real run, and writes nothing
$T = New-ReleaseTree 'rel-same' -Protected @() -NoGate
$h0 = Get-TreeHash $T.W
$rd = Run 'release' ($RS + @{ DryRun = $true }) $T.W
$rr = Run 'release' $RS $T.W
Check 'dry run and real run give the same refusal reasons' ($rd.Exit -eq 1 -and ((Get-Reasons $rd.Out) -join '|') -eq ((Get-Reasons $rr.Out) -join '|') -and @(Get-Reasons $rd.Out).Count -eq 3) ((Get-Reasons $rd.Out) -join '|')
Check '... and neither wrote anything' ((Get-TreeHash $T.W) -eq $h0) ''

# happy path (with the last ticket REVIEW -> LEAD still open)
$T = New-ReleaseTree 'rel-happy'
Add-Ticket $T.W '001-fake' 3 'REVIEW' 'LEAD' 'RELEASE' 'ACCEPTED'
$h0 = Get-TreeHash $T.W
$rd = Run 'release' ($RS + @{ DryRun = $true }) $T.W
Check 'happy dry run -> exit 0, whole tree unchanged' ($rd.Exit -eq 0 -and $rd.Out -match 'DRY RUN: all checks pass' -and (Get-TreeHash $T.W) -eq $h0) $rd.Out
$r = Run 'release' $RS $T.W
$card = RF (Join-Path $T.Card 'CARD.md')
$t3 = RF (Join-Path $T.Card 'handoff\H-03.json') | ConvertFrom-Json
$log = RF (Join-Path $T.Card 'log.md')
Check 'release -> exit 0, card state RELEASED (old: MERGED)' ($r.Exit -eq 0 -and $card -match '(?m)^state: RELEASED$') $r.Out
Check 'State log line added under "## State log"' ($card -match "(?ms)## State log\n- 09/11 09:00 DRAFT - LEAD\n- \d\d/\d\d \d{2}:\d{2} BUILDING . RELEASED . LEAD \(release -IfSafe, manifest $($T.Digest.Substring(0, 12))") $card
Check 'last ticket (open with LEAD) closed DONE' ($t3.state -eq 'DONE' -and $t3.history[-1].by -eq 'LEAD') ''
Check 'log.md line records -As LEAD' ($log -match 'LEAD . done: release -IfSafe \(-As LEAD\)') $log
Check 'install request printed with the digest and target lines' ($r.Out -match 'install card 001-fake' -and $r.Out.Contains($T.Digest) -and $r.Out -match '  scripts/process/a\.ps1') $r.Out
Check 'nothing copied outside the card (no live scripts/process/)' (-not (Test-Path (P $T.W 'scripts/process'))) ''
$r = Run 'release' $RS $T.W
Check 'second release on a RELEASED card -> refused' ($r.Exit -eq 1 -and $r.Out -match 'card is RELEASED') $r.Out

# "-> waives review" line instead of a REVIEW PASS (deliverable cards only; gate PASS still needed)
$WL = 'owner 16/11 10:00: "ok, release without review" -> waives review'
function New-WaiverTree([string]$Tag, [string[]]$Decisions = @($WL), [string]$Extra = '', [string[]]$Protected = @(), [switch]$NoGate, [string]$Live = '') {
    $W = New-FakeTree $Tag
    if ($Live) { [void][IO.Directory]::CreateDirectory((P $W $Live)) }   # an existing (empty) live folder
    $z1 = '2026-11/09_01-fake-task/out/bundle_JP'; $zs = @($z1)   # type: live target bundle_JP/ does not exist
    if ($Extra) { $zs += "2026-11/09_01-fake-task/out/$Extra" }
    $cd = New-FakeCard $W '001-fake' $zs $Protected $Decisions
    WF (Join-Path $cd 'baseline.manifest') ''
    WF (Join-Path (P $W $z1) 'report.md') 'deliverable'
    WF (Join-Path (P $W $z1) 'tests\ok.Tests.ps1') 'exit 0'
    if ($Extra) { WF (Join-Path (P $W $zs[1]) 'x.md') 'x' }
    $dg = Get-Digest $W
    Add-Ticket $W '001-fake' 1 'LEAD' 'BUILD' 'P1' 'DONE'
    Add-Ticket $W '001-fake' 2 'BUILD' 'LEAD' 'RELEASE' 'ACCEPTED'
    if (-not $NoGate) { Write-Gate $W $dg 'PASS' }
    return [pscustomobject]@{ W = $W; Digest = $dg; Card = $cd }
}
$T = New-WaiverTree 'rel-waive'
$h0 = Get-TreeHash $T.W
$rd = Run 'release' ($RS + @{ DryRun = $true }) $T.W
Check 'waiver: out-only card, no REVIEW ticket -> dry run SAFE, says "review: waived by owner", writes nothing' ($rd.Exit -eq 0 -and $rd.Out -match 'review: waived by owner' -and (Get-TreeHash $T.W) -eq $h0) $rd.Out
$r = Run 'release' $RS $T.W
$card = RF (Join-Path $T.Card 'CARD.md'); $log = RF (Join-Path $T.Card 'log.md')
$t2 = RF (Join-Path $T.Card 'handoff\H-02.json') | ConvertFrom-Json
Check 'waiver: release -> RELEASED; State log says "released without review (waived by owner)"' ($r.Exit -eq 0 -and $card -match '(?m)^state: RELEASED$' -and $card -match '(?m)^- .*RELEASED .*released without review \(waived by owner\)') $card
Check 'waiver: log.md line and closed ticket note say "released without review (waived by owner)"' ($log -match 'release -IfSafe \(-As LEAD\) at \w+; released without review \(waived by owner\)' -and $t2.state -eq 'DONE' -and $t2.history[-1].note -match 'waived by owner') $log
$uw = 'owner 16/11 10:00: ' + [char]0x201C + 'khong can review' + [char]0x201D + ' ' + [char]0x2192 + ' waives review'
$T = New-WaiverTree 'rel-waive-uni' -Decisions @($uw)
$r = Run 'release' ($RS + @{ DryRun = $true }) $T.W
Check 'waiver: curly quotes + U+2192 arrow accepted (dry run SAFE)' ($r.Exit -eq 0 -and $r.Out -match 'review: waived by owner') $r.Out
$T = New-WaiverTree 'rel-waive-form' -Decisions @('owner 16/11 10:00: "ok, release without review" -> waives the review')
Refused 'waiver: wrong line form (extra word)' $T 'no REVIEW ticket DONE'
$T = New-WaiverTree 'rel-waive-notime' -Decisions @('owner: "ok, release without review" -> waives review')
Refused 'waiver: wrong line form (no dd/MM HH:mm)' $T 'no REVIEW ticket DONE'
$T = New-WaiverTree 'rel-waive-lead' -Decisions @('LEAD 16/11 10:00: "ok, release without review" -> waives review')
Refused 'waiver: line written as LEAD, not owner' $T 'no REVIEW ticket DONE'
$T = New-WaiverTree 'rel-waive-prot' -Extra 'scripts/process' -Protected @('scripts/process/') -Decisions @($WL, 'owner 16/11 10:00: "ok, install it" -> approves scripts/process/')
Refused 'waiver: refused when a protected path changed (even with its approval line)' $T 'review waiver not allowed: shared / protected or existing path changed \(scripts/process/x\.md\)'
$T = New-WaiverTree 'rel-waive-shared' -Extra 'docs/process/rules'
Refused 'waiver: refused when a shared path (config shared_paths) changed' $T 'review waiver not allowed: (live target exists in the workspace \(docs/process|shared / protected or existing path changed \(docs/process/rules/x\.md)'
# deliverable only - no live target, and no parent folder of one, may exist in the workspace
foreach ($c in @(@('projects/demo/core/src', 'projects/demo'), @('tools/fake', 'tools/fake'), @('lead/tasks', 'lead'), @('docs/cards/002-other', ''), @('2026-11/09_02-deliv/in', ''))) {
    $ex = $c[0]
    $T = New-WaiverTree ('rel-waive-live-' + $ex.Split('/')[0]) -Extra $ex -Live $c[1]
    Refused "waiver: target $ex/ (or a parent folder) exists in the workspace" $T ('review waiver not allowed: live target exists in the workspace \(.*' + [regex]::Escape($ex))
}
$T = New-WaiverTree 'rel-waive-046' -Extra 'bundle_EN'
$r = Run 'release' ($RS + @{ DryRun = $true }) $T.W
Check 'waiver: deliverable type (zones out/bundle_JP, out/bundle_EN; no live bundle_*/) -> dry run SAFE' ($r.Exit -eq 0 -and $r.Out -match 'review: waived by owner') $r.Out
# NG-1: a recorded review (DONE) is never overridden; PASS at the current digest is used as before
$T = New-WaiverTree 'rel-waive-ng'
Add-Ticket $T.W '001-fake' 2 'BUILD' 'REVIEW' 'REVIEW' 'DONE' $T.Digest -Verdict 'NG'
Add-Ticket $T.W '001-fake' 3 'REVIEW' 'LEAD' 'RELEASE' 'ACCEPTED'
Refused 'waiver NG-1: REVIEW DONE NG at the current digest + waiver line' $T "review waiver not allowed: H-02 is a REVIEW ticket DONE \('FAIL'\)"
$T = New-WaiverTree 'rel-waive-oldpass'
Add-Ticket $T.W '001-fake' 2 'BUILD' 'REVIEW' 'REVIEW' 'DONE' ('1' * 64)
Add-Ticket $T.W '001-fake' 3 'REVIEW' 'LEAD' 'RELEASE' 'ACCEPTED'
Refused 'waiver NG-1: REVIEW PASS at an older digest + waiver line' $T "review waiver not allowed: H-02 is a REVIEW ticket DONE \('PASS'\)"
$T = New-WaiverTree 'rel-waive-pass'
Add-Ticket $T.W '001-fake' 2 'BUILD' 'REVIEW' 'REVIEW' 'DONE' $T.Digest
Add-Ticket $T.W '001-fake' 3 'REVIEW' 'LEAD' 'RELEASE' 'ACCEPTED'
$r = Run 'release' $RS $T.W
$card = RF (Join-Path $T.Card 'CARD.md')
Check 'waiver NG-1: REVIEW PASS at the current digest + waiver line -> released through the review, no "waived" text' ($r.Exit -eq 0 -and $card -match '(?m)^state: RELEASED$' -and $r.Out -notmatch 'waived' -and $card -notmatch 'waived by owner\)') $r.Out
$T = New-WaiverTree 'rel-waive-nogate' -NoGate
Refused 'waiver: gate receipt still needed (missing)' $T 'gate receipt missing'
$T = New-WaiverTree 'rel-waive-gfail'
Write-Gate $T.W $T.Digest 'FAIL'
Refused 'waiver: gate result FAIL still refused' $T "gate result is 'FAIL'"
# open REVIEW ticket: HOLD with note "review waived" is ignored and closed by release; other open REVIEW tickets block
$at = (Get-Date).AddMinutes(-5).ToString('yyyy-MM-ddTHH:mm')
$T = New-WaiverTree 'rel-waive-hold'
[IO.File]::Delete((Join-Path $T.Card 'handoff\H-02.json'))
Add-Ticket $T.W '001-fake' 2 'BUILD' 'REVIEW' 'REVIEW' 'HOLD' $T.Digest -Hist @("$at|BUILD|SENT|sent", "$at|REVIEW|ACCEPTED|ok", "$at|REVIEW|HOLD|review waived by owner 16/11")
$r = Run 'release' $RS $T.W
$t2 = RF (Join-Path $T.Card 'handoff\H-02.json') | ConvertFrom-Json
Check 'waiver: REVIEW ticket in HOLD with note "review waived" -> release passes and closes it DONE' ($r.Exit -eq 0 -and $t2.state -eq 'DONE' -and $t2.history[-1].by -eq 'LEAD' -and $t2.history[-1].note -match 'waived by owner') $r.Out
# NG-4: intake Next line agrees with SAFE when the only open ticket is a waived REVIEW HOLD
$T = New-WaiverTree 'rel-waive-intake'
[IO.File]::Delete((Join-Path $T.Card 'handoff\H-02.json'))
Add-Ticket $T.W '001-fake' 2 'BUILD' 'REVIEW' 'REVIEW' 'HOLD' $T.Digest -Hist @("$at|BUILD|SENT|sent", "$at|REVIEW|HOLD|review waived by owner")
$r = Run 'intake' @{ Card = '001-fake' } $T.W
Check 'waiver NG-4: intake on a waived REVIEW HOLD -> Next = LEAD release, not "resolve the HOLD"' ($r.Out -match 'Next: LEAD: release 001-fake -IfSafe -As LEAD \(review waived by owner\)' -and $r.Out -notmatch 'resolve the HOLD') $r.Out
# NG-1: an earlier REVIEW NG, then the latest REVIEW ticket in HOLD "review waived" -> waiver allowed
$T = New-WaiverTree 'rel-waive-ng-hold'
[IO.File]::Delete((Join-Path $T.Card 'handoff\H-02.json'))
Add-Ticket $T.W '001-fake' 2 'BUILD' 'REVIEW' 'REVIEW' 'DONE' ('1' * 64) -Verdict 'NG'
Add-Ticket $T.W '001-fake' 3 'REVIEW' 'BUILD' 'FIXES' 'DONE'
Add-Ticket $T.W '001-fake' 4 'BUILD' 'REVIEW' 'VERIFY' 'HOLD' $T.Digest -Hist @("$at|BUILD|SENT|sent", "$at|REVIEW|HOLD|review waived by owner")
$r = Run 'release' ($RS + @{ DryRun = $true }) $T.W
Check 'waiver NG-1: older REVIEW NG, latest REVIEW ticket HOLD "review waived" -> dry run SAFE' ($r.Exit -eq 0 -and $r.Out -match 'review: waived by owner') $r.Out
# NG-3: the note must START with "review waived" and be the last history entry
$T = New-WaiverTree 'rel-waive-notnote'
[IO.File]::Delete((Join-Path $T.Card 'handoff\H-02.json'))
Add-Ticket $T.W '001-fake' 2 'BUILD' 'REVIEW' 'REVIEW' 'HOLD' $T.Digest -Hist @("$at|BUILD|SENT|sent", "$at|REVIEW|HOLD|NOT review waived yet - found NG-1")
Refused 'waiver NG-3: HOLD note "NOT review waived yet ..." (not at the start) still blocks' $T 'H-02 is open with REVIEW \(ON-HOLD\)'
$T = New-WaiverTree 'rel-waive-lastnote'
[IO.File]::Delete((Join-Path $T.Card 'handoff\H-02.json'))
Add-Ticket $T.W '001-fake' 2 'BUILD' 'REVIEW' 'REVIEW' 'HOLD' $T.Digest -Hist @("$at|BUILD|SENT|sent", "$at|REVIEW|HOLD|review waived", "$at|REVIEW|ACCEPTED|resumed", "$at|REVIEW|HOLD|waiting")
Refused 'waiver NG-3: "review waived" only in an older history entry still blocks' $T 'H-02 is open with REVIEW \(ON-HOLD\)'
$T = New-WaiverTree 'rel-waive-holdx'
[IO.File]::Delete((Join-Path $T.Card 'handoff\H-02.json'))
Add-Ticket $T.W '001-fake' 2 'BUILD' 'REVIEW' 'REVIEW' 'HOLD' $T.Digest -Hist @("$at|BUILD|SENT|sent", "$at|REVIEW|HOLD|waiting for the owner")
Refused 'waiver: REVIEW ticket in HOLD without the "review waived" note still blocks' $T 'H-02 is open with REVIEW \(ON-HOLD\)'
$T = New-WaiverTree 'rel-waive-acc'
[IO.File]::Delete((Join-Path $T.Card 'handoff\H-02.json'))
Add-Ticket $T.W '001-fake' 2 'BUILD' 'REVIEW' 'REVIEW' 'ACCEPTED' $T.Digest -Hist @("$at|BUILD|SENT|sent", "$at|REVIEW|ACCEPTED|review waived")
Refused 'waiver: REVIEW ticket ACCEPTED (not HOLD) still blocks' $T 'H-02 is open with REVIEW \(ACCEPTED\)'
$T = New-WaiverTree 'rel-waive-holdnoline' -Decisions @()
[IO.File]::Delete((Join-Path $T.Card 'handoff\H-02.json'))
Add-Ticket $T.W '001-fake' 2 'BUILD' 'REVIEW' 'REVIEW' 'HOLD' $T.Digest -Hist @("$at|BUILD|SENT|sent", "$at|REVIEW|HOLD|review waived")
Refused 'waiver: HOLD note "review waived" without the Decisions line -> refused' $T 'H-02 is open with REVIEW \(ON-HOLD\)'
# a STALE close has no verdict - never counted as PASS, not a recorded review (red proof b)
$T = New-ReleaseTree 'rel-staleclose' -Verdict 'STALE'
Refused 'red-proof b: latest REVIEW ticket DONE with a STALE note (at the current digest) -> no review result' $T 'no REVIEW ticket DONE'
$T = New-WaiverTree 'rel-waive-stale'
Add-Ticket $T.W '001-fake' 2 'BUILD' 'REVIEW' 'REVIEW' 'DONE' ('0' * 64) -Verdict 'STALE'
$r = Run 'release' ($RS + @{ DryRun = $true }) $T.W
Check 'a STALE-closed REVIEW ticket is not a "recorded review" - the waiver still applies (dry run SAFE)' ($r.Exit -eq 0 -and $r.Out -match 'review: waived by owner') $r.Out
# scenario end to end: freeze -> zone change -> STALE close -> new frozen send -> PASS -> release
$T = New-ReleaseTree 'rel-059'
$null = Run 'ticket' @{ Action = 'send'; Card = '001-fake'; As = 'LEAD'; To = 'REVIEW'; Phase = 'VERIFY'; Freeze = $true } $T.W
$null = Run 'ticket' @{ Action = 'accept'; Card = '001-fake'; As = 'REVIEW' } $T.W
WF (Join-Path $T.Z2 'a.ps1') 'Write-Output 59'
$d2 = Get-Digest $T.W
Write-Gate $T.W $d2 'PASS'
$null = Run 'ticket' @{ Action = 'hold'; Card = '001-fake'; As = 'REVIEW'; Note = 'STALE files changed' } $T.W
$r = Run 'release' ($RS + @{ DryRun = $true }) $T.W
Check 'before the STALE close release is refused (H-03 open with REVIEW)' ($r.Exit -eq 1 -and $r.Out -match 'H-03 is open with REVIEW') $r.Out
$r1 = Run 'ticket' @{ Action = 'done'; Card = '001-fake'; As = 'REVIEW'; Note = 'STALE zone changed after freeze' } $T.W
$r = Run 'release' ($RS + @{ DryRun = $true }) $T.W
Check 'after the STALE close release is still refused (old PASS is for another digest; STALE is no verdict)' ($r1.Exit -eq 0 -and $r.Exit -eq 1 -and $r.Out -match 'files changed after review' -and $r.Out -notmatch "verdict is 'STALE'") ($r1.Out + $r.Out)
$r2 = Run 'ticket' @{ Action = 'send'; Card = '001-fake'; As = 'LEAD'; To = 'REVIEW'; Phase = 'VERIFY'; Freeze = $true } $T.W
$null = Run 'ticket' @{ Action = 'accept'; Card = '001-fake'; As = 'REVIEW' } $T.W
$r3 = Run 'ticket' @{ Action = 'done'; Card = '001-fake'; As = 'REVIEW'; Note = 'PASS refrozen' } $T.W
$r = Run 'release' $RS $T.W
$card = RF (Join-Path $T.Card 'CARD.md')
Check 'new frozen send (H-04) -> PASS -> release -> RELEASED' ($r2.Exit -eq 0 -and $r3.Exit -eq 0 -and $r.Exit -eq 0 -and $card -match '(?m)^state: RELEASED$') ($r2.Out + $r3.Out + $r.Out)
Finish 'release'
