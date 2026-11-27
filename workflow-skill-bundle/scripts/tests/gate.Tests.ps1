# gate.ps1 - secret scan (value never shown), card tests, receipts/gate.json, STALE after a change. Fake tree only.
# Fake secrets are assembled at run time so this file itself never matches the scan.
param([switch]$Keep, [switch]$RedProof)
. (Join-Path $PSScriptRoot '_lib.ps1')
Test-Ps5Only @('gate.ps1')   # Windows PowerShell 5.1: only the refusal of gate.ps1, then exit
Write-Output '===== gate ====='
$W = New-FakeTree 'gate'
$z = '2026-11/09_01-fake-task/out/tools/fake'
$cd = New-FakeCard $W '001-fake' @($z)
WF (Join-Path $cd 'baseline.manifest') ''
$Z = P $W $z
WF (Join-Path $Z 'tool.ps1') 'Write-Output 1'
WF (Join-Path $Z 'tests\ok.Tests.ps1') 'Write-Output "fine"; exit 0'
$rec = Join-Path $cd 'receipts\gate.json'
# the example config holds gate.hosts ["ps7"]; the checks below need a project that must pass on ps5 + ps7
Set-Cfg $W { param($c) $c.gate.hosts = @('ps5', 'ps7') }

$r = Run 'gate' @{ Card = '001-fake'; As = 'BUILD' } $W
$g = if (Test-Path $rec) { RF $rec | ConvertFrom-Json } else { $null }
$dg = Get-Digest $W
Check 'clean zone + passing test on ps5 + ps7 (default) -> PASS, exit 0' ($r.Exit -eq 0 -and $r.Out -match 'gate: PASS') $r.Out
Check 'gate.json has manifest_digest = current, tests (ps5 + ps7), result, at' ($g -and $g.manifest_digest -eq $dg -and $g.result -eq 'PASS' -and @($g.tests).Count -eq 2 -and (@($g.tests | ForEach-Object { $_.host }) -join ',') -eq 'ps5,ps7' -and @($g.tests | Where-Object { $_.result -ne 'PASS' }).Count -eq 0 -and $g.at -match '^\d{4}-\d\d-\d\dT\d{2}:\d{2}$') ''
# F1: fewer hosts -> PARTIAL, never PASS
$r = Run 'gate' @{ Card = '001-fake'; Hosts = @('current') } $W
Check 'F1: clean run on one host -> PARTIAL, exit 1, receipt PARTIAL' ($r.Exit -eq 1 -and $r.Out -match 'gate: PARTIAL' -and (RF $rec | ConvertFrom-Json).result -eq 'PARTIAL') $r.Out
$r = Run 'gate' @{ Card = '001-fake'; Hosts = @('ps7') } $W
Check 'F1: ps7 only -> PARTIAL' ($r.Exit -eq 1 -and $r.Out -match 'gate: PARTIAL') $r.Out
# red proof: '#Requires -Version 7' in a test OUTSIDE paths.scripts does not drop the ps5 run
WF (Join-Path $Z 'tests\ok.Tests.ps1') "#Requires -Version 7`nWrite-Output 'fine'; exit 0"
$r = Run 'gate' @{ Card = '001-fake'; Hosts = @('ps7') } $W
Check 'red proof: "#Requires -Version 7" test with target tools/fake, -Hosts ps7 -> still PARTIAL (needs ps5 + ps7)' ($r.Exit -eq 1 -and $r.Out -match 'gate: PARTIAL' -and $r.Out -match 'not run: .*ok\.Tests\.ps1 on ps5') $r.Out
WF (Join-Path $Z 'tests\ok.Tests.ps1') 'Write-Output "fine"; exit 0'
# a test whose target is under paths.scripts AND that declares '#Requires -Version 7' runs on ps7 only and needs ps7 only
$zp = '2026-11/09_02-fake-proc/out/scripts/process'
$cdp = New-FakeCard $W '002-proc' @($zp)
WF (Join-Path $cdp 'baseline.manifest') ''
WF (Join-Path (P $W $zp) 'tests\p.Tests.ps1') "#Requires -Version 7`nWrite-Output 'fine'; exit 0"
$recp = Join-Path $cdp 'receipts\gate.json'
$r = Run 'gate' @{ Card = '002-proc'; Hosts = @('ps7') } $W
$g = RF $recp | ConvertFrom-Json
Check 'process test (target paths.scripts/tests) with "#Requires -Version 7", -Hosts ps7 -> PASS, one ps7 entry' ($r.Exit -eq 0 -and $r.Out -match 'gate: PASS' -and @($g.tests).Count -eq 1 -and $g.tests[0].host -eq 'ps7') $r.Out
$r = Run 'gate' @{ Card = '002-proc' } $W
$g = RF $recp | ConvertFrom-Json
Check 'same process test, default hosts ps5 + ps7 -> runs on ps7 only, PASS' ($r.Exit -eq 0 -and $r.Out -match 'gate: PASS' -and @($g.tests).Count -eq 1 -and $g.tests[0].host -eq 'ps7') $r.Out
WF (Join-Path (P $W $zp) 'tests\p.Tests.ps1') "Write-Output 'fine'; exit 0"
$r = Run 'gate' @{ Card = '002-proc'; Hosts = @('ps7') } $W
Check 'process test WITHOUT the line, -Hosts ps7 -> PARTIAL (needs ps5 + ps7)' ($r.Exit -eq 1 -and $r.Out -match 'gate: PARTIAL') $r.Out
# config gate.hosts ["ps7"] (example default): every test needs ps7 only; gate runs on ps7 only
Set-Cfg $W { param($c) $c.gate.hosts = @('ps7') }
$r = Run 'gate' @{ Card = '001-fake' } $W
$g = RF $rec | ConvertFrom-Json
Check 'config gate.hosts ["ps7"]: default run on ps7 only -> PASS, one ps7 entry' ($r.Exit -eq 0 -and $r.Out -match 'gate: PASS' -and @($g.tests).Count -eq 1 -and $g.tests[0].host -eq 'ps7') $r.Out
# no gate.hosts in config -> default ps7 only
Set-Cfg $W { param($c) $c.gate.PSObject.Properties.Remove('hosts') }
$r = Run 'gate' @{ Card = '001-fake' } $W
$g = RF $rec | ConvertFrom-Json
Check 'no gate.hosts in config: default ps7 only -> PASS, one ps7 entry' ($r.Exit -eq 0 -and $r.Out -match 'gate: PASS' -and @($g.tests).Count -eq 1 -and $g.tests[0].host -eq 'ps7') $r.Out
$r = Run 'gate' @{ Card = '001-fake'; Hosts = @('ps5', 'ps7') } $W
$g = RF $rec | ConvertFrom-Json
Check 'no gate.hosts, -Hosts ps5,ps7 -> ps5 not needed (skipped), PASS, one ps7 entry' ($r.Exit -eq 0 -and $r.Out -match 'gate: PASS' -and @($g.tests).Count -eq 1 -and $g.tests[0].host -eq 'ps7') $r.Out
Set-Cfg $W { param($c) $c.gate | Add-Member -NotePropertyName hosts -NotePropertyValue @('ps5', 'ps7') -Force }
Set-Cfg $W { param($c) $c.gate.hosts = @('ps5', 'ps7') }

# failing test, missing tests
WF (Join-Path $Z 'tests\bad.Tests.ps1') 'Write-Output "boom"; exit 3'
$r = Run 'gate' @{ Card = '001-fake'; Hosts = @('current') } $W
Check 'failing card test -> FAIL, exit 1, receipt FAIL' ($r.Exit -eq 1 -and $r.Out -match 'test FAIL' -and (RF $rec | ConvertFrom-Json).result -eq 'FAIL') $r.Out
Remove-Item -LiteralPath (Join-Path $Z 'tests') -Recurse -Force
$r = Run 'gate' @{ Card = '001-fake'; Hosts = @('current') } $W
Check 'no *.Tests.ps1 -> FAIL' ($r.Exit -eq 1 -and $r.Out -match 'no \*\.Tests\.ps1') $r.Out
WF (Join-Path $Z 'tests\ok.Tests.ps1') 'exit 0'

# planted secrets
$v1 = 'Zq' + 'x9Lm2Pw7Rt'
$v2 = 'AK' + 'IA' + 'QWERTYUIOPASDFGH'
$v3 = 'MIIEow' + 'IBAAKCAQEA7x'
$hdr = '-----BEGIN ' + 'RSA PRIVATE KEY-----'
WF (Join-Path $Z 'conf.ps1') ("`$a = 1`n`$cfg = @{ pass" + "word = '$v1' }`n# key: $v2`n")
WF (Join-Path $Z 'id_rsa.txt') ("$hdr`n$v3`n-----END RSA PRIVATE KEY-----`n")
[IO.File]::WriteAllText((Join-Path $Z 'utf16.txt'), "x`r`napi_key=`"$v1`"`r`n", [Text.Encoding]::Unicode)
[IO.File]::WriteAllBytes((Join-Path $Z 'blob.bin'), [byte[]](0, 1, 2, 0, 255, 0))
$r = Run 'gate' @{ Card = '001-fake'; Hosts = @('current') } $W
$gt = RF $rec
Check 'planted secrets -> FAIL, exit 1' ($r.Exit -eq 1 -and $r.Out -match 'gate: FAIL') $r.Out
Check 'file + line reported (conf.ps1:2, conf.ps1:3, id_rsa.txt:1, utf16.txt:2)' ($r.Out -match 'conf\.ps1:2 ' -and $r.Out -match 'conf\.ps1:3 ' -and $r.Out -match 'id_rsa\.txt:1 ' -and $r.Out -match 'utf16\.txt:2 ') $r.Out
$leak = @($v1, $v2, $v3) | Where-Object { $r.Out.Contains($_) -or $gt.Contains($_) }
Check 'no secret value in stdout or gate.json' (@($leak).Count -eq 0) "leaked: $($leak -join ',')"
Check 'binary file skipped without crash, named' ($r.Out -match 'skipped \(binary, not scanned\): .*blob\.bin') $r.Out
Remove-Item -LiteralPath (Join-Path $Z 'conf.ps1'), (Join-Path $Z 'id_rsa.txt'), (Join-Path $Z 'utf16.txt'), (Join-Path $Z 'blob.bin') -Force

# F3: unquoted forms are caught; placeholders / variables are not
$v4 = 'Hn4' + 'tR8wQ2zL'
$un = @(("pass" + "word=$v4"), ("`$env:API" + "_KEY = $v4"), ("Server=db;User Id=sa;Pass" + "word=$v4;"), ("to" + "ken: $v4"))
WF (Join-Path $Z 'unquoted.txt') (($un -join "`n") + "`n")
$ok = @(("pass" + "word = `$env:DB_PASS"), ("to" + "ken: <your-token>"), ("api" + "_key=[MASKED]"), ("pass" + "word: (Get-Secret db)"))
WF (Join-Path $Z 'placeholders.txt') (($ok -join "`n") + "`n")
$r = Run 'gate' @{ Card = '001-fake'; Hosts = @('current') } $W
Check 'F3: 4 unquoted forms -> FAIL with unquoted.txt:1..4' ($r.Exit -eq 1 -and $r.Out -match 'unquoted\.txt:1 ' -and $r.Out -match 'unquoted\.txt:2 ' -and $r.Out -match 'unquoted\.txt:3 ' -and $r.Out -match 'unquoted\.txt:4 ') $r.Out
Check 'F3: placeholders / variables / [MASKED] not flagged' ($r.Out -notmatch 'placeholders\.txt') $r.Out
Check 'F3: value never shown' (-not $r.Out.Contains($v4) -and -not (RF $rec).Contains($v4)) ''
Remove-Item -LiteralPath (Join-Path $Z 'unquoted.txt'), (Join-Path $Z 'placeholders.txt') -Force

# session IDs are flagged too; receipt goes STALE after a change
WF (Join-Path $Z 'ring.txt') ('send to local' + '_' + [guid]::NewGuid().ToString())
$r = Run 'gate' @{ Card = '001-fake'; Hosts = @('current') } $W
Check 'session ID in a zone file -> FAIL (rule session-id)' ($r.Exit -eq 1 -and $r.Out -match 'session-id') $r.Out
Remove-Item -LiteralPath (Join-Path $Z 'ring.txt') -Force
$r = Run 'gate' @{ Card = '001-fake'; Hosts = @('current') } $W
Check 'clean again -> only PARTIAL (one host), no FAIL reason' ($r.Out -match 'gate: PARTIAL' -and $r.Out -cnotmatch 'SECRET |test FAIL') $r.Out
WF (Join-Path $Z 'tool.ps1') 'Write-Output 2'
$r = Run 'intake' @{ Card = '001-fake' } $W
Check 'file changed after the gate -> intake shows OUTDATED (old: STALE)' ($r.Out -match 'Gate: OUTDATED') $r.Out
$msg = ''
try { $null = Run 'gate' @{ Card = '001-fake'; Hosts = @('nope') } $W } catch { $msg = $_.Exception.Message }
Check 'unknown host -> rejected by the parameter set (ps5, ps7, current)' ($msg -match 'nope') $msg
Finish 'gate'
