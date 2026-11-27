# checkpoint.ps1 - turn holder only, LEAD only without an open ticket (Q2), append-only, one line. Fake tree only.
param([switch]$Keep, [switch]$RedProof)
. (Join-Path $PSScriptRoot '_lib.ps1')
Test-Ps5Only @('checkpoint.ps1')   # Windows PowerShell 5.1: only the refusal of checkpoint.ps1, then exit
Write-Output '===== checkpoint ====='
$W = New-FakeTree 'checkpoint'
$cd = New-FakeCard $W '001-fake'
$log = Join-Path $cd 'log.md'
$A = { param($as, $done) @{ Card = '001-fake'; As = $as; Done = $done; Doing = 'b'; Next = 'c'; Check = 'd' } }

# no ticket at all
$b0 = RF $log
$r = Run 'checkpoint' (& $A 'BUILD' 'x') $W
Check 'no open ticket: BUILD -> refused, log.md byte-identical' ($r.Exit -eq 1 -and (RF $log) -eq $b0) $r.Out
$r = Run 'checkpoint' (& $A 'LEAD' 'card start') $W
$b1 = RF $log
Check 'no open ticket: LEAD -> allowed, exactly one new line, old text kept as prefix' ($r.Exit -eq 0 -and $b1.StartsWith($b0) -and @(($b1.Substring($b0.Length)) -split "`n" | Where-Object { $_ }).Count -eq 1) $r.Out
Check 'line format "- dd/MM HH:mm ROLE . done: . doing: . next: . check:"' ($b1 -match ("(?m)^- \d\d/\d\d \d{2}:\d{2} LEAD $($script:Dot) done: card start $($script:Dot) doing: b $($script:Dot) next: c $($script:Dot) check: d$")) $b1

# open ticket with BUILD
Add-Ticket $W '001-fake' 1 'LEAD' 'BUILD' 'P1' 'ACCEPTED'
$r = Run 'checkpoint' (& $A 'LEAD' 'x') $W
Check 'open ticket with BUILD: LEAD -> refused (LEAD exception only without an open ticket)' ($r.Exit -eq 1 -and (RF $log) -eq $b1) $r.Out
$r = Run 'checkpoint' (& $A 'REVIEW' 'x') $W
Check 'open ticket with BUILD: REVIEW -> refused' ($r.Exit -eq 1 -and (RF $log) -eq $b1) $r.Out
$r = Run 'checkpoint' (& $A 'BUILD' "line one`nline two`r`nthree") $W
$b2 = RF $log
$new = @(($b2.Substring($b1.Length)) -split "`n" | Where-Object { $_ })
Check 'BUILD (holder) with newlines in -Done -> exactly one new line, old lines unchanged' ($r.Exit -eq 0 -and $b2.StartsWith($b1) -and $new.Count -eq 1 -and $new[0] -match 'done: line one line two three ') $r.Out

# missing / bad parameters
$r = Run 'checkpoint' @{ Card = '001-fake'; As = 'BUILD'; Done = 'a'; Doing = 'b'; Next = 'c' } $W
Check 'missing -Check -> refused' ($r.Exit -eq 1 -and $r.Out -match '-Check is required' -and (RF $log) -eq $b2) $r.Out
$r = Run 'checkpoint' @{ Card = '001-fake'; As = 'BUILD'; Done = '   '; Doing = 'b'; Next = 'c'; Check = 'd' } $W
Check 'blank -Done -> refused' ($r.Exit -eq 1 -and (RF $log) -eq $b2) $r.Out
$r = Run 'checkpoint' @{ Card = '001-fake'; As = 'BOSS'; Done = 'a'; Doing = 'b'; Next = 'c'; Check = 'd' } $W
Check 'unknown role -> refused' ($r.Exit -eq 1 -and (RF $log) -eq $b2) $r.Out
$secret = 'pass' + 'word = "' + 'Abcdefgh12345' + '"'
$r = Run 'checkpoint' (& $A 'BUILD' $secret) $W
Check 'secret-like text -> refused, value not echoed' ($r.Exit -eq 1 -and -not $r.Out.Contains('Abcdefgh12345') -and (RF $log) -eq $b2) $r.Out

# log.md without trailing newline: still one clean line
[IO.File]::WriteAllText($log, $b2.TrimEnd("`n"), $script:U8)
$r = Run 'checkpoint' (& $A 'BUILD' 'z') $W
$b3 = RF $log
Check 'log.md without a final newline -> new line starts on its own line' ($r.Exit -eq 0 -and $b3.StartsWith($b2.TrimEnd("`n") + "`n- ")) $r.Out
Finish 'checkpoint'
