# .workflow/workflow.config.json - root detection, refusals, custom paths, approval_name, thresholds, purge switch. Fake projects only.
param([switch]$Keep, [switch]$RedProof)
. (Join-Path $PSScriptRoot '_lib.ps1')
Test-Ps5Only @('intake.ps1')   # Windows PowerShell 5.1: only the refusal of intake.ps1, then exit
Write-Output '===== config ====='
$TA = @{ Action = 'send'; Card = '001-fake'; As = 'LEAD'; To = 'BUILD'; Phase = 'P1' }

# missing / unreadable / wrong schema -> refused with the install hint, nothing written
$W = New-FakeTree 'cfg-missing'
$null = New-FakeCard $W
Remove-Item -LiteralPath (Join-Path $W '.workflow\workflow.config.json') -Force
$r = Run 'ticket' $TA $W
Check 'config missing -> refused with the install hint, no ticket' ($r.Exit -eq 1 -and $r.Out -match 'REFUSED' -and $r.Out -match 'chay install\.py' -and -not (Test-Path (Join-Path $W 'docs\cards\001-fake\handoff\H-01.json'))) $r.Out
WF (Join-Path $W '.workflow\workflow.config.json') '{ "schema": 1, "paths": '
$r = Run 'ticket' $TA $W
Check 'config unreadable (bad JSON) -> refused with the hint' ($r.Exit -eq 1 -and $r.Out -match 'unreadable' -and $r.Out -match 'chay install\.py') $r.Out
WF (Join-Path $W '.workflow\workflow.config.json') '{ "schema": 2 }'
$r = Run 'ticket' $TA $W
Check 'config schema 2 -> refused' ($r.Exit -eq 1 -and $r.Out -match 'schema must be 1') $r.Out
$W = New-FakeTree 'cfg-badpath'
$null = New-FakeCard $W
Set-Cfg $W { param($c) $c.paths.cards = '../outside' }
$r = Run 'ticket' $TA $W
Check 'paths.cards with ".." -> refused' ($r.Exit -eq 1 -and $r.Out -match 'paths\.cards .* plain relative path') $r.Out

# root found from the current folder (no -Root)
$W = New-FakeTree 'cfg-cwd'
$null = New-FakeCard $W
$sub = Join-Path $W 'docs\cards'
Push-Location -LiteralPath $sub
try { $global:LASTEXITCODE = 0; $out = & (Join-Path $script:Src 'ticket.ps1') @TA *>&1 | Out-String -Width 500; $code = $global:LASTEXITCODE }
finally { Pop-Location }
Check 'no -Root: the root is found from the current folder upward' ($code -eq 0 -and (Test-Path (Join-Path $W 'docs\cards\001-fake\handoff\H-01.json'))) $out

# custom paths.cards / paths.process_docs
$W = New-FakeTree 'cfg-paths'
$null = New-FakeCard $W
[void][IO.Directory]::CreateDirectory((Join-Path $W 'work'))
Move-Item -LiteralPath (Join-Path $W 'docs\cards') -Destination (Join-Path $W 'work\cards')
Move-Item -LiteralPath (Join-Path $W 'docs\process') -Destination (Join-Path $W 'work\proc')
Set-Cfg $W { param($c) $c.paths.cards = 'work/cards'; $c.paths.process_docs = 'work/proc' }
$r = Run 'ticket' $TA $W
Check 'custom paths.cards: ticket written there, bell names it' ($r.Exit -eq 0 -and (Test-Path (Join-Path $W 'work\cards\001-fake\handoff\H-01.json')) -and $r.Out -match 'Card: work/cards/001-fake/CARD\.md') $r.Out
Check 'custom paths.process_docs: PROGRESS.md written there' (Test-Path (Join-Path $W 'work\proc\PROGRESS.md')) ''

# custom paths.lead: the steplog alias map reads <lead>/board.md
$W = New-FakeTree 'cfg-lead'
Set-Cfg $W { param($c) $c.paths.lead = 'team/lead'; $c.paths.process_log = 'logs/proc' }
WF (Join-Path $W 'team\lead\board.md') ("# board`n`n| Task | What |`n|---|---|`n| T-20260105-07 | card ``077-from-board`` |`n")
$r = Run 'steplog' @{ Action = 'start'; Task = '077-from-board'; Step = 'BUILD'; As = 'Dev' } $W
$f = @(Get-ChildItem -LiteralPath (Join-Path $W 'logs\proc\steps') -Filter '*.jsonl' -ErrorAction SilentlyContinue)
Check 'custom paths.lead + paths.process_log: alias from <lead>/board.md, log under logs/proc/steps' ($r.Exit -eq 0 -and $r.Out -match 'T-20260105-07' -and $f.Count -eq 1) $r.Out

# approval_name: custom name accepted, the old name refused
$T = New-ReleaseTree 'cfg-appr' -Decisions @('boss 09/11 09:40: "ok, build and install it" -> approves scripts/process/')
Set-Cfg $T.W { param($c) $c.approval_name = 'boss' }
$r = Run 'release' @{ Card = '001-fake'; IfSafe = $true; As = 'LEAD'; DryRun = $true } $T.W
Check 'approval_name "boss": line "boss dd/MM HH:mm: ... -> approves" accepted (dry run SAFE)' ($r.Exit -eq 0 -and $r.Out -match 'DRY RUN: all checks pass') $r.Out
$T = New-ReleaseTree 'cfg-appr-old' -Decisions @('admin 09/11 09:40: "ok, build and install it" -> approves scripts/process/')
$r = Run 'release' @{ Card = '001-fake'; IfSafe = $true; As = 'LEAD'; DryRun = $true } $T.W
Check 'approval_name "owner" (example): an old-name line is refused' ($r.Exit -eq 1 -and $r.Out -match "no Decisions line with the owner's quoted sentence") $r.Out
$T = New-ReleaseTree 'cfg-appr-bad'
Set-Cfg $T.W { param($c) $c.approval_name = 'two words' }
$r = Run 'release' @{ Card = '001-fake'; IfSafe = $true; As = 'LEAD'; DryRun = $true } $T.W
Check 'approval_name with a space -> refused' ($r.Exit -eq 1 -and $r.Out -match 'approval_name .* one word') $r.Out

# stale thresholds from config
$W = New-FakeTree 'cfg-stale'
$null = New-FakeCard $W '001-fake' @('2026-11/09_01-fake-task/out/tools/fake')
Add-Ticket $W '001-fake' 1 'LEAD' 'BUILD' 'P1' 'SENT' '' @("2026-11-09T14:50|LEAD|SENT|go")
$r = Run 'stale' @{ Now = '2026-11-09T15:00' } $W
Check 'stale default 30 min: SENT 10 min ago is not stale' ($r.Exit -eq 0 -and $r.Out -notmatch 'STALE 001-fake') $r.Out
Set-Cfg $W { param($c) $c.stale.sent_minutes = 5 }
$r = Run 'stale' @{ Now = '2026-11-09T15:00' } $W
Check 'stale.sent_minutes 5: SENT 10 min ago is stale' ($r.Out -match 'STALE 001-fake') $r.Out

# steplog purge switch
$W = New-FakeTree 'cfg-purge'
Set-Cfg $W { param($c) $c.steplog.purge_enabled = $false }
$r = Run 'steplog' @{ Action = 'purge'; As = 'Dev'; DryRun = $true } $W
Check 'steplog.purge_enabled false -> purge refused (also -DryRun)' ($r.Exit -eq 1 -and $r.Out -match 'purge is off') $r.Out
Set-Cfg $W { param($c) $c.steplog.purge_enabled = $true; $c.steplog.purge_days = 3 }
$r = Run 'steplog' @{ Action = 'purge'; As = 'Dev'; DryRun = $true } $W
Check 'steplog.purge_days 3 is the default -Days' ($r.Exit -eq 0 -and $r.Out -match 'purge -Days 3 ') $r.Out
$r = Run 'steplog' @{ Action = 'purge'; As = 'Dev'; DryRun = $true } (New-FakeTree 'cfg-purge-ex')
Check 'example config: purge -Days 90 (steplog.purge_days of the example)' ($r.Exit -eq 0 -and $r.Out -match 'purge -Days 90 ') $r.Out
Set-Cfg $W { param($c) $c.steplog.PSObject.Properties.Remove('purge_days') }
$r = Run 'steplog' @{ Action = 'purge'; As = 'Dev'; DryRun = $true } $W
Check 'steplog.purge_days missing -> code default -Days 90' ($r.Exit -eq 0 -and $r.Out -match 'purge -Days 90 ') $r.Out

# session map from config (relative path inside the project)
$W = New-FakeTree 'cfg-map'
$null = New-FakeCard $W
WF (Join-Path $W '.workflow\sessions.local.json') '{ "BUILD": { "title": "Dev main", "id": "dev-42" } }'
$r = Run 'ticket' $TA $W
Check 'session_map_file from config: ring line names the receiver' ($r.Exit -eq 0 -and $r.Out -match 'Ring \(local map, not stored\): Dev main dev-42') $r.Out
Finish 'config'
