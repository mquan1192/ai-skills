# steplog.ps1 (named steps per task) + hooks/turnlog.py (turn times, Python hook). Fake projects only.
# The hook is <bundle>/hooks/turnlog.py (one folder above scripts/); its own unit tests are hooks/test_turnlog.py.
param([switch]$Keep, [switch]$RedProof)
. (Join-Path $PSScriptRoot '_lib.ps1')
Test-Ps5Only @('steplog.ps1')   # Windows PowerShell 5.1: only the refusal of steplog.ps1, then exit
Write-Output '===== steplog ====='
$Inv = [Globalization.CultureInfo]::InvariantCulture
$Base = Split-Path -Parent $script:Src
$Hook = Join-Path $Base 'hooks\turnlog.py'
$TurnRoot = 'process-log'   # paths.process_log of the example config
Write-Output "  info: hook $Hook writes under <root>\$TurnRoot\turns"
$Py = @(Get-Command python.exe -CommandType Application -ErrorAction SilentlyContinue | Where-Object { $_.Source -notmatch 'WindowsApps' } | ForEach-Object { $_.Source }) | Select-Object -First 1
$T = 'T-20260112-99'

# the old folder name (as a path segment) and raw-log file names must not appear in steplog / hook / tests /
# README. The word is built at run time so this file does not contain it.

function Invoke-StepLog([hashtable]$A, [string]$W) { return (Run 'steplog' $A $W) }
function Get-Lines([string]$File) {
    if (-not [IO.File]::Exists($File)) { return @() }
    return @((RF $File).Split("`n") | Where-Object { $_ -ne '' })
}
function J([string]$Line) { return (ConvertFrom-Json -InputObject $Line) }

# ---------------- A: start / end / wait / resume ----------------
$W = New-FakeTree 'steplog'
$month = (Get-Date).ToString('yyyy-MM', $Inv)
$log = Join-Path $W "process-log\steps\$month.jsonl"

$r = Invoke-StepLog @{ Action = 'start'; Task = $T; Step = 'FOO'; As = 'Dev' } $W
Check 'unknown step code -> refused, no log written' ($r.Exit -eq 1 -and $r.Out -match 'unknown step code' -and -not [IO.File]::Exists($log)) $r.Out
$r = Invoke-StepLog @{ Action = 'start'; Task = 'T-1'; Step = 'BUILD'; As = 'Dev' } $W
Check 'bad task id -> refused' ($r.Exit -eq 1 -and $r.Out -match 'is not a T-ID' -and -not [IO.File]::Exists($log)) $r.Out
$r = Invoke-StepLog @{ Action = 'start'; Task = $T; Step = 'BUILD' } $W
Check 'start without -As -> refused' ($r.Exit -eq 1 -and $r.Out -match '-As' -and -not [IO.File]::Exists($log)) $r.Out
$r = Invoke-StepLog @{ Action = 'start'; Task = $T; Step = 'OTHER'; As = 'Dev' } $W
Check 'OTHER without -Note -> refused' ($r.Exit -eq 1 -and $r.Out -match 'OTHER needs -Note') $r.Out
$r = Invoke-StepLog @{ Action = 'start'; Task = $T; Step = 'BUILD'; As = 'Dev'; Type = 'Bad Type' } $W
Check 'bad -Type slug -> refused' ($r.Exit -eq 1 -and -not [IO.File]::Exists($log)) $r.Out
$secretVal = 'Zq' + 'x9Abcdefgh12345'
$r = Invoke-StepLog @{ Action = 'start'; Task = $T; Step = 'BUILD'; As = 'Dev'; Note = ('pass' + 'word = "' + $secretVal + '"') } $W
Check 'secret-like note -> refused, value not echoed, no log' ($r.Exit -eq 1 -and $r.Out -match 'secret' -and -not $r.Out.Contains($secretVal) -and -not [IO.File]::Exists($log)) $r.Out
$sidText = 'lo' + 'cal_' + [guid]::NewGuid().ToString()
$r = Invoke-StepLog @{ Action = 'start'; Task = $T; Step = 'BUILD'; As = 'Dev'; Note = "ring $sidText" } $W
Check 'session-ID-like note -> refused' ($r.Exit -eq 1 -and $r.Out -match 'session-id' -and -not [IO.File]::Exists($log)) $r.Out
$r = Invoke-StepLog @{ Action = 'start'; Task = $T; Step = 'BUILD'; As = 'Dev'; Note = ('x' * 301) } $W
Check 'note longer than 300 characters -> refused' ($r.Exit -eq 1 -and $r.Out -match 'longer than 300') $r.Out
$r = Invoke-StepLog @{ Action = 'jump'; Task = $T } $W
Check 'unknown action -> refused' ($r.Exit -eq 1 -and $r.Out -match 'not start, end') $r.Out

$before = Get-Date
$r = Invoke-StepLog @{ Action = 'start'; Task = $T; Step = 'build'; As = 'Dev-1'; Type = 'card'; Model = 'Opus high'; Note = "two`nlines" } $W
$after = Get-Date
$L = @(Get-Lines $log)
$o = $null; if ($L.Count -eq 1) { $o = J $L[0] }
Check 'start -> one JSON line in process-log/steps/<yyyy-MM>.jsonl' ($r.Exit -eq 0 -and $L.Count -eq 1) $r.Out
$keys = ''; if ($o) { $keys = (@($o.PSObject.Properties | ForEach-Object { $_.Name }) -join ',') }
Check 'keys are exactly at,event,task,step,type,session,model,result,note (in this order)' ($keys -eq 'at,event,task,step,type,session,model,result,note') $keys
$at = [datetime]::MinValue
$atText = ''; if ($o) { $atText = [string]$o.at; if ($o.at -is [datetime]) { $atText = $o.at.ToString('yyyy-MM-ddTHH:mm:ss', $Inv) } }
$okAt = [datetime]::TryParseExact($atText, 'yyyy-MM-ddTHH:mm:ss', $Inv, [Globalization.DateTimeStyles]::None, [ref]$at)
Check 'at = local clock (yyyy-MM-ddTHH:mm:ss, between call start and end)' ($okAt -and $at -ge $before.AddSeconds(-1) -and $at -le $after.AddSeconds(1)) $atText
Check 'step upper-cased, fields kept, newline in note folded' ($o -and $o.event -eq 'start' -and $o.step -eq 'BUILD' -and $o.type -eq 'card' -and $o.session -eq 'Dev-1' -and $o.model -eq 'Opus high' -and $o.note -eq 'two lines' -and $null -eq $o.result) $L[0]
Check 'log file is UTF-8 without BOM, LF line end' ($L.Count -eq 1 -and ([IO.File]::ReadAllBytes($log))[0] -eq 0x7B -and (RF $log).EndsWith("}`n")) ''

$b1 = RF $log
$r = Invoke-StepLog @{ Action = 'start'; Task = $T; Step = 'BUILD'; As = 'Dev-1' } $W
Check 'second start of the same task + step + session while open -> refused' ($r.Exit -eq 1 -and $r.Out -match 'already started' -and (RF $log) -eq $b1) $r.Out
$r = Invoke-StepLog @{ Action = 'start'; Task = $T; Step = 'BUILD'; As = 'Dev-2' } $W
Check 'same step by another session (parallel part) -> allowed' ($r.Exit -eq 0) $r.Out

$r = Invoke-StepLog @{ Action = 'wait'; Task = $T } $W
Check 'wait without -Note -> refused' ($r.Exit -eq 1 -and $r.Out -match 'wait needs -Note') $r.Out
$r = Invoke-StepLog @{ Action = 'resume'; Task = $T } $W
Check 'resume without an open wait -> refused' ($r.Exit -eq 1 -and $r.Out -match 'not waiting') $r.Out
$r = Invoke-StepLog @{ Action = 'wait'; Task = $T; Note = 'owner chooses A or B'; As = 'Lead-1' } $W
Check 'wait -> allowed' ($r.Exit -eq 0) $r.Out
$r = Invoke-StepLog @{ Action = 'wait'; Task = $T; Note = 'again' } $W
Check 'second wait while waiting -> refused' ($r.Exit -eq 1 -and $r.Out -match 'already waiting') $r.Out
$r = Invoke-StepLog @{ Action = 'resume'; Task = $T } $W
Check 'resume -> allowed' ($r.Exit -eq 0 -and $r.Out -match 'waited') $r.Out

$b2 = RF $log
$r = Invoke-StepLog @{ Action = 'end'; Task = $T; Step = 'BUILD' } $W
Check 'end with two open starts and no -As -> refused (no guessing)' ($r.Exit -eq 1 -and $r.Out -match 'give -As' -and (RF $log) -eq $b2) $r.Out
$r = Invoke-StepLog @{ Action = 'end'; Task = $T; Step = 'BUILD'; As = 'Dev-2'; Result = 'maybe' } $W
Check 'bad -Result -> refused' ($r.Exit -eq 1 -and (RF $log) -eq $b2) $r.Out
$r = Invoke-StepLog @{ Action = 'end'; Task = $T; Step = 'BUILD'; As = 'Dev-2'; Result = 'partial' } $W
$last = J (@(Get-Lines $log))[-1]
Check 'end -As Dev-2 -Result partial -> PARTIAL, session kept' ($r.Exit -eq 0 -and $last.event -eq 'end' -and $last.result -eq 'PARTIAL' -and $last.session -eq 'Dev-2') $r.Out
$r = Invoke-StepLog @{ Action = 'end'; Task = $T; Step = 'BUILD' } $W
$last = J (@(Get-Lines $log))[-1]
Check 'end without -As (one open start left) -> closes it, result OK by default, type + model copied' ($r.Exit -eq 0 -and $last.session -eq 'Dev-1' -and $last.result -eq 'OK' -and $last.type -eq 'card' -and $last.model -eq 'Opus high') $r.Out
$b3 = RF $log
$r = Invoke-StepLog @{ Action = 'end'; Task = $T; Step = 'BUILD' } $W
Check 'end with no open start -> refused, log unchanged' ($r.Exit -eq 1 -and $r.Out -match 'no open start' -and (RF $log) -eq $b3) $r.Out
$all = @(Get-Lines $log)
$parsed = @($all | ForEach-Object { try { J $_ } catch { $null } } | Where-Object { $_ })
Check 'every line is valid JSON (6 events) and old lines never change (append-only)' ($parsed.Count -eq 6 -and $all.Count -eq 6 -and $b3.StartsWith($b1)) "$($all.Count)"

# ---------------- B: report on a hand-made log (known times) ----------------
$W2 = New-FakeTree 'steplog-report'
$d2 = Join-Path $W2 'process-log\steps'
function E([string]$at, [string]$ev, [string]$task, [string]$step = '', [string]$type = '', [string]$ses = 'S1', [string]$res = '', [string]$note = '') {
    $v = { param($x) if ($x -eq '') { 'null' } else { '"' + $x + '"' } }
    return ('{"at":"' + $at + '","event":"' + $ev + '","task":"' + $task + '","step":' + (& $v $step) + ',"type":' + (& $v $type) + ',"session":' + (& $v $ses) + ',"model":null,"result":' + (& $v $res) + ',"note":' + (& $v $note) + '}')
}
$oct = @(
    (E '2026-10-31T23:50:00' 'start' '31_01-late-task' 'INTAKE' 'translate'),
    (E '2026-10-31T23:58:00' 'end' '31_01-late-task' 'INTAKE' 'translate' 'S1' 'OK')
) -join "`n"
$nov = @(
    (E '2026-10-31T23:59:00' 'start' '31_01-late-task' 'BUILD' 'translate'),
    (E '2026-11-01T00:09:00' 'end' '31_01-late-task' 'BUILD' 'translate' 'S1' 'OK'),
    (E '2026-11-05T10:00:00' 'start' 'T-20260105-01' 'INTAKE' 'card'),
    (E '2026-11-05T10:05:00' 'end' 'T-20260105-01' 'INTAKE' 'card' 'S1' 'OK'),
    (E '2026-11-05T10:05:00' 'start' 'T-20260105-01' 'BUILD' 'card'),
    (E '2026-11-05T10:20:00' 'wait' 'T-20260105-01' '' '' 'S1' '' 'owner: A or B'),
    (E '2026-11-05T10:30:00' 'resume' 'T-20260105-01'),
    (E '2026-11-05T10:45:00' 'end' 'T-20260105-01' 'BUILD' 'card' 'S1' 'OK'),
    (E '2026-11-05T10:45:00' 'start' 'T-20260105-01' 'QA' 'card' 'S2'),
    (E '2026-11-05T11:00:00' 'end' 'T-20260105-01' 'QA' 'card' 'S2' 'NG'),
    (E '2026-11-06T09:00:00' 'start' '024-other-card' 'INTAKE' 'card'),
    (E '2026-11-06T09:10:00' 'end' '024-other-card' 'INTAKE' 'card' 'S1' 'OK'),
    (E '2026-11-06T09:10:00' 'start' '024-other-card' 'BUILD' 'card'),
    (E '2026-11-06T09:40:00' 'end' '024-other-card' 'BUILD' 'card' 'S1' 'OK'),
    (E '2026-11-06T09:40:00' 'start' '024-other-card' 'QA' 'card' 'S2'),
    (E '2026-11-06T09:50:00' 'end' '024-other-card' 'QA' 'card' 'S2' 'OK'),
    (E '2026-11-07T08:00:00' 'start' '07_01-odd-task' 'READ' 'report'),
    (E '2026-11-07T08:30:00' 'end' '07_01-odd-task' 'PLAN' 'report' 'S1' 'OK'),
    (E '2026-11-07T08:40:00' 'wait' '07_01-odd-task' '' '' 'S1' '' 'q'),
    'this is { not json',
    (E '2026-11-07T09:00:00' 'resume' '024-other-card')
) -join "`n"
WF (Join-Path $d2 '2026-10.jsonl') ($oct + "`n")
WF (Join-Path $d2 '2026-11.jsonl') ($nov + "`n")
WF (Join-Path $d2 'notes.txt') 'not a log'

$r = Invoke-StepLog @{ Action = 'report' } $W2
$o = $r.Out
Check 'report exit 0' ($r.Exit -eq 0) $o
Check 'step row: BUILD 40.0 min, waiting 10.0, result OK' ($o -match '\| T-20260105-01 \| card \| BUILD \| S1 \| 2026-11-05 10:05 \| 2026-11-05 10:45 \| 40\.0 \| 10\.0 \| OK \|') $o
Check 'step row: QA 15.0 min, waiting 0.0, result NG' ($o -match '\| T-20260105-01 \| card \| QA \| S2 \| 2026-11-05 10:45 \| 2026-11-05 11:00 \| 15\.0 \| 0\.0 \| NG \|') $o
Check 'pair across a month file edge (start 2026-10-31, end 2026-11-01) = 10.0 min' ($o -match '\| 31_01-late-task \| translate \| BUILD \| S1 \| 2026-10-31 23:59 \| 2026-11-01 00:09 \| 10\.0 \|') $o
Check 'per task: T-20260105-01 3 steps, span 60.0, step sum 60.0, waiting 10.0, work 50.0' ($o -match '\| T-20260105-01 \| card \| 3 \| 2026-11-05 10:00 \| 2026-11-05 11:00 \| 60\.0 \| 60\.0 \| 10\.0 \| 50\.0 \|') $o
Check 'per type: card usual order INTAKE > BUILD > QA (2 tasks)' ($o -match '\| card \| 2 \| usual: INTAKE > BUILD > QA \|') $o
Check 'per type averages: card BUILD 2 steps avg 35.0 min, avg waiting 5.0' ($o -match '\| card \| BUILD \| 2 \| 35\.0 \| 5\.0 \|') $o
Check 'unpaired listed: start without end (READ)' ($o -match 'start without end: start 07_01-odd-task READ at 2026-11-07 08:00') $o
Check 'unpaired listed: end without start (PLAN)' ($o -match 'end without start: end 07_01-odd-task PLAN') $o
Check 'unpaired listed: wait without resume, resume without wait' ($o -match 'wait without resume: wait 07_01-odd-task' -and $o -match 'resume without wait: resume 024-other-card') $o
Check 'unreadable line listed with file:line, not guessed' ($o -match 'unreadable line: process-log/steps/2026-11\.jsonl:20') $o
Check 'unpaired / odd task not counted as a step row' ($o -notmatch '\| 07_01-odd-task \| report \| (READ|PLAN) \|') $o

$r = Invoke-StepLog @{ Action = 'report'; Task = '024-other-card' } $W2
Check '-Task filter: only that task' ($r.Exit -eq 0 -and $r.Out -match '\| 024-other-card \| card \| BUILD' -and $r.Out -notmatch '\| T-20260105-01 \|') $r.Out
$r = Invoke-StepLog @{ Action = 'report'; Type = 'translate' } $W2
Check '-Type filter: only translate tasks' ($r.Exit -eq 0 -and $r.Out -match '31_01-late-task' -and $r.Out -notmatch '\| T-20260105-01 \|' -and $r.Out -match '\| translate \| 1 \| usual: INTAKE > BUILD \|') $r.Out
$r = Invoke-StepLog @{ Action = 'report'; From = '2026-11-06'; To = '2026-11-06' } $W2
Check '-From / -To (inclusive day): only 2026-11-06' ($r.Exit -eq 0 -and $r.Out -match '\| 024-other-card \|' -and $r.Out -notmatch '\| T-20260105-01 \|' -and $r.Out -notmatch '31_01-late-task') $r.Out
$r = Invoke-StepLog @{ Action = 'report'; From = '06/11/2026' } $W2
Check 'bad -From date -> refused' ($r.Exit -eq 1 -and $r.Out -match 'yyyy-MM-dd') $r.Out

$csv = Join-Path $W2 'out\steps report.csv'
[void][IO.Directory]::CreateDirectory((Split-Path -Parent $csv))
$r = Invoke-StepLog @{ Action = 'report'; Csv = $csv } $W2
$bytes = [byte[]]@(); if ([IO.File]::Exists($csv)) { $bytes = [IO.File]::ReadAllBytes($csv) }
$ctext = ''; if ($bytes.Length -gt 3) { $ctext = [Text.Encoding]::UTF8.GetString($bytes, 3, $bytes.Length - 3) }
$crows = @($ctext.Split("`n") | Where-Object { $_.Trim() -ne '' })
Check '-Csv: file written with UTF-8 BOM, header + 8 step rows' ($r.Exit -eq 0 -and $bytes.Length -gt 3 -and $bytes[0] -eq 0xEF -and $crows.Count -eq 9 -and $crows[0].Trim() -eq 'task,type,step,session,model,start,end,minutes,waiting_minutes,result') "$($crows.Count) $($r.Out)"
Check '-Csv: BUILD row values' ($ctext -match '(?m)^T-20260105-01,card,BUILD,S1,,2026-11-05 10:05,2026-11-05 10:45,40\.0,10\.0,OK\r?$') $ctext
Check '-Csv: unpaired events reported as a note, not as rows' ($r.Out -match '4 unpaired event\(s\), 1 unreadable line') $r.Out
$h0 = [IO.File]::ReadAllBytes($csv)
$r = Invoke-StepLog @{ Action = 'report'; Csv = $csv } $W2
Check '-Csv on an existing file -> refused, file unchanged' ($r.Exit -eq 1 -and $r.Out -match 'never overwrites' -and [Convert]::ToBase64String([IO.File]::ReadAllBytes($csv)) -eq [Convert]::ToBase64String($h0)) $r.Out

$W3 = New-FakeTree 'steplog-empty'
$r = Invoke-StepLog @{ Action = 'report' } $W3
Check 'report with no process-log folder -> exit 0, empty tables, "none"' ($r.Exit -eq 0 -and $r.Out -match '- none') $r.Out

# ---------------- B2: F2 task-id case + aliases, F3 CSV formula guard ----------------
$W7 = New-FakeTree 'steplog-alias'
[void](New-FakeCard $W7 '024-fake-card' @('2026-11/12_05-fake-folder/out/tools/x'))   # CARD.md task: T-20260109-99
WF (Join-Path $W7 'lead\board.md') ("# board`n`n| Task | What | Who | State | QA | Folder | Note |`n|---|---|---|---|---|---|---|`n" +
    "| T-20260110-05 | thing " + [string][char]0x2192 + " card ``030-board-card`` | x | doing | no | ``2026-11/10_04-board-folder/out/`` | x |`n" +
    "| T-20260110-06 | dup one | x | doing | no | ``2026-11/10_09-dup-folder/out/`` | x |`n" +
    "| T-20260110-07 | dup two | x | doing | no | ``2026-11/10_09-dup-folder/out/`` | x |`n")
$log7 = Join-Path $W7 "process-log\steps\$month.jsonl"
$r = Invoke-StepLog @{ Action = 'start'; Task = '024-FAKE-CARD'; Step = 'INTAKE'; As = 'S1'; Type = 'card' } $W7
$first = J (@(Get-Lines $log7))[0]
Check 'F2: card name stored lower case; start output names the T-ID from CARD.md task:' ($r.Exit -eq 0 -and $first.task -eq '024-fake-card' -and $r.Out -match '\(= T-20260109-99\)') $r.Out
$r = Invoke-StepLog @{ Action = 'end'; Task = 'T-20260109-99'; Step = 'INTAKE' } $W7
Check 'F2: end by T-ID closes the start written with the card name' ($r.Exit -eq 0) $r.Out
$r = Invoke-StepLog @{ Action = 'start'; Task = '12_05-Fake-Folder'; Step = 'BUILD'; As = 'S1' } $W7
$r2 = Invoke-StepLog @{ Action = 'end'; Task = 't-20260109-99'; Step = 'BUILD' } $W7
$lastLine = J (@(Get-Lines $log7))[-1]
Check 'F2: task folder (zone in CARD.md) = same task; lower-case t- id stored upper case' ($r.Exit -eq 0 -and $r2.Exit -eq 0 -and $lastLine.task -eq 'T-20260109-99') "$($r.Out) $($r2.Out)"
$r = Invoke-StepLog @{ Action = 'start'; Task = '030-board-card'; Step = 'QA'; As = '=HYPERLINK("x")' } $W7
$r2 = Invoke-StepLog @{ Action = 'end'; Task = 'T-20260110-05'; Step = 'QA'; As = '=HYPERLINK("x")' } $W7
Check 'F2: card named in <lead>/board.md row = that row''s T-ID' ($r.Exit -eq 0 -and $r2.Exit -eq 0) "$($r.Out) $($r2.Out)"
$r = Invoke-StepLog @{ Action = 'start'; Task = '10_09-dup-folder'; Step = 'READ'; As = '@S2' } $W7
$r2 = Invoke-StepLog @{ Action = 'end'; Task = 'T-20260110-06'; Step = 'READ' } $W7
Check 'F2: alias listed under two T-IDs is not used (no guessing)' ($r.Exit -eq 0 -and $r.Out -notmatch '\(= ' -and $r2.Exit -eq 1 -and $r2.Out -match 'no open start') "$($r.Out) $($r2.Out)"
[void](Invoke-StepLog @{ Action = 'end'; Task = '10_09-dup-folder'; Step = 'READ' } $W7)
$r = Invoke-StepLog @{ Action = 'report' } $W7
$o = $r.Out
Check 'F2 report: steps counted under T-20260109-99 (INTAKE + BUILD), T-20260110-05 (QA)' ($r.Exit -eq 0 -and $o -match '\| T-20260109-99 \| card \| INTAKE \|' -and $o -match '\| T-20260109-99 \| card \| BUILD \|' -and $o -match '\| T-20260110-05 \| - \| QA \|' -and $o -match '\| 10_09-dup-folder \| - \| READ \|') $o
Check 'F2 report: per task T-20260109-99 = one task with 2 steps' ($o -match '\| T-20260109-99 \| card \| 2 \|') $o
Check 'F2 report: merged aliases listed' ($o -match '- 024-fake-card -> T-20260109-99' -and $o -match '- 12_05-fake-folder -> T-20260109-99' -and $o -match '- 030-board-card -> T-20260110-05' -and $o -notmatch '10_09-dup-folder ->') $o
$r = Invoke-StepLog @{ Action = 'report'; Task = '024-Fake-Card' } $W7
Check 'F2 report -Task <card alias> = its T-ID rows' ($r.Exit -eq 0 -and $r.Out -match '\| T-20260109-99 \| card \| BUILD \|' -and $r.Out -notmatch 'T-20260110-05 \|') $r.Out
$csv7 = Join-Path $W7 'r.csv'
$r = Invoke-StepLog @{ Action = 'report'; Csv = $csv7 } $W7
$c7 = ''; if ([IO.File]::Exists($csv7)) { $c7 = [IO.File]::ReadAllText($csv7, [Text.Encoding]::UTF8) }
Check 'F3 CSV: a cell starting with = or @ gets a leading apostrophe (text, not a formula)' ($r.Exit -eq 0 -and $c7.Contains(',"''=HYPERLINK(""x"")",') -and $c7.Contains(",'@S2,") -and $c7 -notmatch ',=|,@') $c7

# ---------------- C: hook turnlog.py ----------------
function Invoke-Hook([string]$Json, [string]$Root) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Py
    $psi.Arguments = '-I -S "' + $Hook + '" --root "' + $Root + '"'
    $psi.UseShellExecute = $false
    $psi.RedirectStandardInput = $true; $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $p = [Diagnostics.Process]::Start($psi)
    $b = (New-Object System.Text.UTF8Encoding($false)).GetBytes($Json)
    $p.StandardInput.BaseStream.Write($b, 0, $b.Length); $p.StandardInput.Close()
    $so = $p.StandardOutput.ReadToEndAsync(); $se = $p.StandardError.ReadToEndAsync()
    $p.WaitForExit(); $sw.Stop()
    return [pscustomobject]@{ Exit = $p.ExitCode; Out = $so.Result; Err = $se.Result; Ms = [int]$sw.ElapsedMilliseconds }
}

Check 'hook script exists in hooks/ next to scripts/' ([IO.File]::Exists($Hook)) $Hook
Check 'python.exe (Python 3) found for the hook' ([bool]$Py) 'python.exe not on PATH'
$W4 = New-FakeTree 'turnlog'
$day = (Get-Date).ToString('yyyy-MM-dd', $Inv)
$tl = Join-Path $W4 "$TurnRoot\turns\$day.jsonl"
$marker = 'PROMPT-MARKER-' + [guid]::NewGuid().ToString('N')
$cwdJp = 'D' + ':\Proj Work ' + [string][char]0x30C6 + '\x'
$inJson = '{"session_id":"0f1e2d3c-aaaa-bbbb-cccc-123456789abc","transcript_path":"C\u003a\\Users\\u\\.claude\\projects\\p\\TRANSCRIPT-' + $marker + '.jsonl","cwd":"' + $cwdJp.Replace('\', '\\') + '","permission_mode":"default","hook_event_name":"UserPromptSubmit","prompt":"' + $marker + ' please read the file"}'
$times = New-Object System.Collections.ArrayList
$h = Invoke-Hook $inJson $W4; [void]$times.Add($h.Ms)
$L = @(Get-Lines $tl)
$o = $null; if ($L.Count -eq 1) { $o = J $L[0] }
Check 'UserPromptSubmit -> exit 0, no stdout, one line in process-log/turns/<yyyy-MM-dd>.jsonl' ($h.Exit -eq 0 -and $h.Out -eq '' -and $L.Count -eq 1) "exit=$($h.Exit) out=[$($h.Out)] err=[$($h.Err)] lines=$($L.Count)"
$keys = ''; if ($o) { $keys = (@($o.PSObject.Properties | ForEach-Object { $_.Name }) -join ',') }
Check 'hook line keys are exactly at,event,session_id,cwd' ($keys -eq 'at,event,session_id,cwd') $keys
Check 'values: event, session_id, cwd (non-ASCII path kept as UTF-8)' ($o -and $o.event -eq 'UserPromptSubmit' -and $o.session_id -eq '0f1e2d3c-aaaa-bbbb-cccc-123456789abc' -and $o.cwd -eq $cwdJp) $(if ($L.Count) { $L[0] } else { '' })
Check 'prompt text and transcript path are NOT in the log' (-not (RF $tl).Contains($marker) -and (RF $tl) -notmatch 'please read|transcript|"prompt"') ''
foreach ($ev in 'Stop', 'SubagentStop', 'SessionStart') {
    $h = Invoke-Hook ('{"session_id":"s-1","cwd":"D\u003a\\w","hook_event_name":"' + $ev + '","stop_hook_active":false,"source":"startup"}') $W4; [void]$times.Add($h.Ms)
    $last = J (@(Get-Lines $tl))[-1]
    Check "$ev -> exit 0, no stdout, logged" ($h.Exit -eq 0 -and $h.Out -eq '' -and $last.event -eq $ev) "exit=$($h.Exit) out=[$($h.Out)]"
}
$n0 = @(Get-Lines $tl).Count
$h = Invoke-Hook '{"session_id":"s-1","cwd":"D\u003a\\w","hook_event_name":"PreToolUse","tool_input":{"command":"x"}}' $W4
Check 'other event (PreToolUse) -> exit 0, nothing written' ($h.Exit -eq 0 -and $h.Out -eq '' -and @(Get-Lines $tl).Count -eq $n0) ''
$h = Invoke-Hook 'this is { not json' $W4
Check 'malformed stdin -> exit 0, no stdout, nothing written' ($h.Exit -eq 0 -and $h.Out -eq '' -and @(Get-Lines $tl).Count -eq $n0) "exit=$($h.Exit) out=[$($h.Out)]"
$h = Invoke-Hook '{"session_id":"bad id; rm","cwd":"D\u003a\\w","hook_event_name":"Stop"}' $W4
$last = J (@(Get-Lines $tl))[-1]
Check 'odd session_id -> stored as null (only [A-Za-z0-9_-])' ($h.Exit -eq 0 -and $null -eq $last.session_id) ''

$W5 = New-FakeTree 'turnlog-ro'
WF (Join-Path $W5 $TurnRoot) 'a FILE with the log folder name: the folder <name>\turns cannot be created'
$h = Invoke-Hook $inJson $W5
Check 'unwritable log folder -> exit 0, no stdout, no stderr' ($h.Exit -eq 0 -and $h.Out -eq '' -and $h.Err.Trim() -eq '') "exit=$($h.Exit) out=[$($h.Out)] err=[$($h.Err)]"

# parallel sessions: 6 hooks at once -> 6 whole lines
$W6 = New-FakeTree 'turnlog-par'
$procs = @(foreach ($i in 1..6) {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $Py; $psi.UseShellExecute = $false; $psi.RedirectStandardInput = $true; $psi.RedirectStandardOutput = $true
        $psi.Arguments = '-I -S "' + $Hook + '" --root "' + $W6 + '"'
        $pp = [Diagnostics.Process]::Start($psi)
        $pp.StandardInput.Write('{"session_id":"par-' + $i + '","cwd":"D\u003a\\w","hook_event_name":"Stop"}'); $pp.StandardInput.Close()
        $pp
    })
foreach ($pp in $procs) { [void]$pp.StandardOutput.ReadToEnd(); $pp.WaitForExit() }
$pl = @(Get-Lines (Join-Path $W6 "$TurnRoot\turns\$day.jsonl"))
$ids = @($pl | ForEach-Object { try { (J $_).session_id } catch { 'BAD' } } | Sort-Object -Unique)
Check '6 hooks at the same time -> 6 whole JSON lines, one per session' ($pl.Count -eq 6 -and $ids.Count -eq 6 -and $ids -notcontains 'BAD') "$($pl.Count) lines"

foreach ($i in 1..3) { $h = Invoke-Hook '{"session_id":"t-1","cwd":"D\u003a\\w","hook_event_name":"Stop"}' $W4; [void]$times.Add($h.Ms) }
$best = ($times | Measure-Object -Minimum).Minimum
Write-Output "  info: hook wall time per call incl. Python start (ms): $(($times | ForEach-Object { $_ }) -join ', ')"
Check 'hook finishes fast: best call < 200 ms (incl. Python start; F1 target)' ($best -lt 200) "best=$best ms"

$hookText = RF $Hook
$imports = @([regex]::Matches($hookText, '(?m)^\s*(?:import|from)\s+([A-Za-z_.]+)') | ForEach-Object { $_.Groups[1].Value })
$extra = @($imports | Where-Object { @('sys', 'json', 'os', 're', 'time', 'msvcrt') -notcontains $_ })
Check 'hook source: stdlib only (sys, json, os, re, time, msvcrt)' ($imports.Count -gt 0 -and $extra.Count -eq 0) ($extra -join ', ')
Check 'hook source: no network, no subprocess, no print / stdout write' ($hookText -notmatch '(?i)socket|urllib|http|subprocess|print\(|stdout\.write') ''
Check 'hook source: ASCII only' (@([IO.File]::ReadAllBytes($Hook) | Where-Object { $_ -gt 127 }).Count -eq 0) ''

# ---------------- E: purge -Days 10 ----------------
$W8 = New-FakeTree 'steplog-purge'
$today = (Get-Date).Date
$at = { param([int]$dd, [int]$hh, [int]$mm = 0) $today.AddDays(-$dd).AddHours($hh).AddMinutes($mm) }
$fmtAt = { param([datetime]$d) $d.ToString('yyyy-MM-ddTHH:mm:ss', $Inv) }
$evs = @(
    @{ T = (& $at 20 10); L = (E (& $fmtAt (& $at 20 10)) 'start' 'T-20260101-01' 'BUILD' 'card'); Move = $true },        # A pair, both old
    @{ T = (& $at 20 10 30); L = (E (& $fmtAt (& $at 20 10 30)) 'end' 'T-20260101-01' 'BUILD' 'card' 'S1' 'OK'); Move = $true },
    @{ T = (& $at 15 9); L = (E (& $fmtAt (& $at 15 9)) 'start' 'T-20260101-02' 'BUILD' 'card'); Move = $false },        # B start old, end new: kept whole
    @{ T = (& $at 2 9); L = (E (& $fmtAt (& $at 2 9)) 'end' 'T-20260101-02' 'BUILD' 'card' 'S1' 'OK'); Move = $false },
    @{ T = (& $at 14 9); L = (E (& $fmtAt (& $at 14 9)) 'wait' 'T-20260101-03' '' '' 'S1' '' 'q'); Move = $true },       # C wait + resume, old
    @{ T = (& $at 13 9); L = (E (& $fmtAt (& $at 13 9)) 'resume' 'T-20260101-03'); Move = $true },
    @{ T = (& $at 30 9); L = (E (& $fmtAt (& $at 30 9)) 'start' 'T-20260101-04' 'READ' 'card'); Move = $false },        # D open start: kept
    @{ T = (& $at 25 9); L = (E (& $fmtAt (& $at 25 9)) 'end' 'T-20260101-05' 'PLAN' 'card' 'S1' 'OK'); Move = $true },  # E orphan end, old
    @{ T = (& $at 1 9); L = (E (& $fmtAt (& $at 1 9)) 'start' 'T-20260101-06' 'QA' 'card'); Move = $false },            # F recent pair
    @{ T = (& $at 1 10); L = (E (& $fmtAt (& $at 1 10)) 'end' 'T-20260101-06' 'QA' 'card' 'S1' 'OK'); Move = $false }
)
$sd = Join-Path $W8 'process-log\steps'
$files = @{}
foreach ($x in ($evs | Sort-Object { $_.T })) { $m = $x.T.ToString('yyyy-MM', $Inv); if (-not $files.ContainsKey($m)) { $files[$m] = New-Object System.Collections.ArrayList }; [void]$files[$m].Add($x.L) }
$badMonth = (& $at 20 10).ToString('yyyy-MM', $Inv)
[void]$files[$badMonth].Add('this is { not json')
foreach ($m in $files.Keys) { WF (Join-Path $sd "$m.jsonl") (($files[$m] -join "`n") + "`n") }
$td = Join-Path $W8 'process-log\turns'
foreach ($dd in 12, 11, 10, 3) { WF (Join-Path $td ($today.AddDays(-$dd).ToString('yyyy-MM-dd', $Inv) + '.jsonl')) ('{"at":"x","event":"Stop","session_id":"s","cwd":"d' + $dd + '"}' + "`n") }
WF (Join-Path $td 'notes.txt') 'not a day file'
WF (Join-Path $W8 'process-log\other.txt') 'outside steps / turns'
$tree0 = Get-TreeHash $W8

$r = Invoke-StepLog @{ Action = 'purge' } $W8
Check 'purge without -As -> refused, nothing changed' ($r.Exit -eq 1 -and $r.Out -match '-As' -and (Get-TreeHash $W8) -eq $tree0) $r.Out
$r = Invoke-StepLog @{ Action = 'purge'; Days = 0; As = 'Tester' } $W8
Check 'purge -Days 0 -> refused' ($r.Exit -eq 1 -and $r.Out -match '-Days') $r.Out
$r = Invoke-StepLog @{ Action = 'purge'; Days = 10; DryRun = $true } $W8
Check '-DryRun: lists 5 step lines + 2 turn files, changes nothing (no _trash)' ($r.Exit -eq 0 -and $r.Out -match 'DRY RUN' -and $r.Out -match ': 5 step line\(s\) from \d month file\(s\), 2 turn file\(s\)' -and (Get-TreeHash $W8) -eq $tree0 -and -not [IO.Directory]::Exists((Join-Path $W8 '_trash'))) $r.Out

$r = Invoke-StepLog @{ Action = 'purge'; Days = 10; As = 'Tester' } $W8
$stamp = (Get-Date).ToString('yyyyMMdd', $Inv)
$tb = Join-Path $W8 "_trash\$stamp\process-log"
$srcLines = @(); $trLines = @()
foreach ($m in $files.Keys) {
    $srcLines += @(Get-Lines (Join-Path $sd "$m.jsonl"))
    $trLines += @(Get-Lines (Join-Path $tb "steps\$m.jsonl"))
}
$expMove = @($evs | Where-Object { $_.Move } | ForEach-Object { $_.L } | Sort-Object)
$expKeep = @(@($evs | Where-Object { -not $_.Move } | ForEach-Object { $_.L }) + 'this is { not json' | Sort-Object)
Check 'purge: exit 0, summary 5 step lines + 2 turn files' ($r.Exit -eq 0 -and $r.Out -match '(?m)^OK: purge -Days 10' -and $r.Out -match ': 5 step line\(s\)' -and $r.Out -match '2 turn file\(s\)') $r.Out
Check 'purge: exactly the old whole pairs + the old orphan end moved to _trash/<yyyyMMdd>/process-log/steps/' ((@($trLines | Sort-Object) -join "`n") -eq ($expMove -join "`n")) ($trLines -join ' / ')
Check 'purge: month files keep the rest (pair with a new end, open start, recent pair, unreadable line)' ((@($srcLines | Sort-Object) -join "`n") -eq ($expKeep -join "`n")) ($srcLines -join ' / ')
$turnsLeft = @(Get-ChildItem -LiteralPath $td -File -ErrorAction SilentlyContinue | ForEach-Object { $_.Name } | Sort-Object)
$turnsMoved = @(Get-ChildItem -LiteralPath (Join-Path $tb 'turns') -File -ErrorAction SilentlyContinue | ForEach-Object { $_.Name } | Sort-Object)
$d12 = $today.AddDays(-12).ToString('yyyy-MM-dd', $Inv) + '.jsonl'; $d11 = $today.AddDays(-11).ToString('yyyy-MM-dd', $Inv) + '.jsonl'
$d10 = $today.AddDays(-10).ToString('yyyy-MM-dd', $Inv) + '.jsonl'; $d3 = $today.AddDays(-3).ToString('yyyy-MM-dd', $Inv) + '.jsonl'
Check 'purge: turn files older than 10 days moved whole; the cut-off day and newer stay; other files untouched' (
    ($turnsMoved -join ',') -eq ((@($d11, $d12) | Sort-Object) -join ',') -and ($turnsLeft -join ',') -eq ((@($d10, $d3, 'notes.txt') | Sort-Object) -join ',') -and
    (RF (Join-Path $W8 'process-log\other.txt')) -eq 'outside steps / turns' -and (RF (Join-Path $tb "turns\$d12")).Contains('"cwd":"d12"')) "left=$($turnsLeft -join ',') moved=$($turnsMoved -join ',')"
$tlog = Join-Path $W8 '_trash\TRASH-LOG.md'
$tl8 = ''; if ([IO.File]::Exists($tlog)) { $tl8 = RF $tlog }
$rows = @(($tl8 -split "`r?`n") | Where-Object { $_ -match '^\| \d{4}-\d\d-\d\d \d{2}:\d{2}:\d\d \| (Move|MoveLines) \| Tester \| process-log retention 10 days \|' })
Check 'TRASH-LOG.md: header of the trash script + one row per moved month file / turn file (By, Reason)' ($tl8.StartsWith("# TRASH-LOG`r`n`r`n| Time | Action | By | Reason | Original path | Trash path | Size |") -and $rows.Count -eq (@($files.Keys | Where-Object { $mk = $_; @($evs | Where-Object { $_.Move -and $_.T.ToString('yyyy-MM', $Inv) -eq $mk }).Count -gt 0 }).Count + 2) -and $tl8 -match '\| MoveLines \|.*\| \d+ lines, ') "$($rows.Count) rows"
$r = Invoke-StepLog @{ Action = 'report' } $W8
Check 'after purge: the kept pair still reports whole; the open start is still listed' ($r.Exit -eq 0 -and $r.Out -match '\| T-20260101-02 \| card \| BUILD \|' -and $r.Out -match 'start without end: start T-20260101-04 READ') $r.Out
$tree1 = Get-TreeHash $W8
$r = Invoke-StepLog @{ Action = 'purge'; Days = 10; As = 'Tester' } $W8
Check 'second purge: nothing older left -> 0 moved, nothing changed; open start noted' ($r.Exit -eq 0 -and $r.Out -match ': 0 step line\(s\) from 0 month file\(s\), 0 turn file\(s\)' -and $r.Out -match '1 open start' -and (Get-TreeHash $W8) -eq $tree1) $r.Out
Finish 'steplog'
