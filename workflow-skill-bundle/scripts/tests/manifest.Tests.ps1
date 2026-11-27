# manifest.ps1 - baseline (write-once), added / changed / removed, rename rule, digest, links, same digest on 5.1 and 7.
param([switch]$Keep, [switch]$RedProof)
. (Join-Path $PSScriptRoot '_lib.ps1')
Test-Ps5Only @('manifest.ps1')   # Windows PowerShell 5.1: only the refusal of manifest.ps1, then exit
Write-Output '===== manifest ====='
$W = New-FakeTree 'manifest'
$z1 = '2026-11/09_01-fake-task/out/tools/fake'; $z2 = '2026-11/09_01-fake-task/out/scripts/process'
$cd = New-FakeCard $W '001-fake' @($z1, $z2) @('scripts/process/')
$base = Join-Path $cd 'baseline.manifest'
# live targets before P1: tools/fake/{keep.txt, old.txt}, scripts/process/guard.ps1
WF (P $W 'tools/fake/keep.txt') 'keep'
WF (P $W 'tools/fake/old.txt') 'old content'
WF (P $W 'scripts/process/guard.ps1') 'guard'

$r = Run 'manifest' @{ Card = '001-fake' } $W
Check 'baseline missing -> refused (never treated as empty)' ($r.Exit -eq 1 -and $r.Out -match 'baseline.manifest missing') $r.Out
$r = Run 'manifest' @{ Card = '001-fake'; Baseline = $true; As = 'BUILD' } $W
Check 'baseline without an open ticket for the caller -> refused' ($r.Exit -eq 1 -and -not (Test-Path $base)) $r.Out
Add-Ticket $W '001-fake' 1 'LEAD' 'BUILD' 'P1' 'ACCEPTED'
$r = Run 'manifest' @{ Card = '001-fake'; Baseline = $true; As = 'REVIEW' } $W
Check 'baseline by a non-holder -> refused' ($r.Exit -eq 1 -and -not (Test-Path $base)) $r.Out
$r = Run 'manifest' @{ Card = '001-fake'; Baseline = $true; As = 'BUILD' } $W
$bl = @((RF $base) -split "`n" | Where-Object { $_ })
Check 'baseline = live TARGET paths, 3 lines, sorted ordinal, same line format' ($r.Exit -eq 0 -and $bl.Count -eq 3 -and $bl[0] -match '^[0-9a-f]{64}  scripts/process/guard\.ps1$' -and $bl[1] -match '  tools/fake/keep\.txt$' -and $bl[2] -match '  tools/fake/old\.txt$') ($bl -join ' | ')
$b0 = RF $base
$r = Run 'manifest' @{ Card = '001-fake'; Baseline = $true; As = 'BUILD' } $W
Check 'second -Baseline -> refused (write-once), file unchanged' ($r.Exit -eq 1 -and $r.Out -match 'write-once' -and (RF $base) -eq $b0) $r.Out

# BUILD: full copy of the targets into the zones, then edit
WF (Join-Path (P $W $z1) 'keep.txt') 'keep'                    # unchanged copy -> not in the manifest
WF (Join-Path (P $W $z1) 'new.txt') 'old content'              # old.txt renamed to new.txt
WF (Join-Path (P $W $z1) 'guard.ps1') 'guard'                  # protected file moved OUT of scripts/process/
WF (Join-Path (P $W $z2) 'run.ps1') 'run'
WF (Join-Path (P $W $z1) 'empty.txt') ''                       # zero-byte
WF (Join-Path (P $W $z1) '.hidden') 'h'; (Get-Item -LiteralPath (Join-Path (P $W $z1) '.hidden') -Force).Attributes = 'Hidden'
$r = Run 'manifest' @{ Card = '001-fake' } $W
$ml = @(($r.Out -split "`r?`n") | Where-Object { $_ -match '^([0-9a-f]{64}|-)  ' })
$paths = @($ml | ForEach-Object { $_.Substring($_.IndexOf('  ') + 2) })
$sorted = [string[]]$paths.Clone(); [Array]::Sort($sorted, [StringComparer]::Ordinal)
Check 'manifest = added / changed / removed only (keep.txt not listed), 7 entries' ($r.Exit -eq 0 -and $ml.Count -eq 7 -and -not ($paths -contains 'tools/fake/keep.txt')) ($ml -join ' | ')
Check 'sorted by path, ordinal' ((@($paths) -join '|') -ceq ($sorted -join '|')) ($paths -join '|')
Check 'rename = old path removed (-) + new path added' (($ml -contains '-  tools/fake/old.txt') -and @($ml | Where-Object { $_ -match '^[0-9a-f]{64}  tools/fake/new\.txt$' }).Count -eq 1) ''
Check 'protected file moved out keeps its old name: "-  scripts/process/guard.ps1"' (($ml -contains '-  scripts/process/guard.ps1') -and $r.Out -match 'protected: .*scripts/process/guard\.ps1 \(removed\)') $r.Out
Check 'zero-byte and hidden files are listed' (($paths -contains 'tools/fake/empty.txt') -and ($paths -contains 'tools/fake/.hidden')) ''
$text = (($ml -join "`n") + "`n")
$sha = [Security.Cryptography.SHA256]::Create()
$exp = [BitConverter]::ToString($sha.ComputeHash($script:U8.GetBytes($text))).Replace('-', '').ToLowerInvariant()
$d1 = Get-Digest $W
Check 'digest = SHA-256 of the manifest text (UTF-8, LF, final LF)' ($d1 -eq $exp) "$d1 / $exp"
Check 'deterministic: same tree -> same digest' ((Get-Digest $W) -eq $d1) ''
WF (Join-Path (P $W $z2) 'run.ps1') 'run!'
$d2 = Get-Digest $W
Check '1-byte change -> new digest' ($d2 -ne $d1) ''
WF (Join-Path (P $W $z2) 'run.ps1') 'run'
Check 'change undone -> old digest again' ((Get-Digest $W) -eq $d1) ''

# PowerShell 7 only (v1.1): the cross-edition digest check is replaced by the 5.1 refusal (tests/ps7.Tests.ps1)

# links, missing zone, bad zones
$j = Join-Path (P $W $z1) 'junc'
New-Item -ItemType Junction -Path $j -Target (Join-Path $W 'kb') | Out-Null
$r = Run 'manifest' @{ Card = '001-fake' } $W
Check 'junction inside a zone -> refused, link + target named' ($r.Exit -eq 1 -and $r.Out -match 'junction / symlink' -and $r.Out -match 'junc') $r.Out
[IO.Directory]::Delete($j)   # removes only the junction entry (test-made), never the target
$W2 = New-FakeTree 'manifest2'
$cd2 = New-FakeCard $W2 '002-zones' @('2026-11/09_01-fake-task/out/tools/a')
WF (Join-Path $cd2 'baseline.manifest') ''
[IO.Directory]::Delete((P $W2 '2026-11/09_01-fake-task/out/tools/a'))
$r = Run 'manifest' @{ Card = '002-zones' } $W2
Check 'missing zone folder -> refused' ($r.Exit -eq 1 -and $r.Out -match 'zone folder missing') $r.Out
foreach ($bad in @('2026-11/09_01-fake-task/out/../../kb', '2026-11/09_01-fake-task/out/_m/part', 'kb/x', 'C:/x/out/y', '2026-11/09_01-fake-task/in/x')) {
    $cd3 = New-FakeCard $W2 '003-bad' @($bad)
    WF (Join-Path $cd3 'baseline.manifest') ''
    $r = Run 'manifest' @{ Card = '003-bad' } $W2
    Check "bad zone '$bad' -> refused" ($r.Exit -eq 1 -and $r.Out -match 'REFUSED: zone') $r.Out
}
$cd4 = New-FakeCard $W2 '004-overlap' @('2026-11/09_01-fake-task/out/tools', '2026-11/09_01-fake-task/out/tools/a')
WF (Join-Path $cd4 'baseline.manifest') ''
$r = Run 'manifest' @{ Card = '004-overlap' } $W2
Check 'overlapping zones -> refused' ($r.Exit -eq 1 -and $r.Out -match 'overlap') $r.Out
WF (Join-Path $cd2 'baseline.manifest') 'not a manifest line'
[void][IO.Directory]::CreateDirectory((P $W2 '2026-11/09_01-fake-task/out/tools/a'))
$r = Run 'manifest' @{ Card = '002-zones' } $W2
Check 'malformed baseline -> refused' ($r.Exit -eq 1 -and $r.Out -match 'malformed') $r.Out

# ---------------- a zone that is ONE FILE under <task>/out/ ----------------
Write-Output '----- single-file zone -----'
$F = New-FakeTree 'filezone'
$fz = '2026-11/09_01-fake-task/out/README.md'; $dz = '2026-11/09_01-fake-task/out/tools/b'
$cf = New-FakeCard $F '005-file' @($fz, $dz)
[IO.Directory]::Delete((P $F $fz))   # New-FakeCard creates a folder per zone; this zone is a file
WF (P $F 'README.md') 'old readme'
WF (P $F 'tools/b/x.txt') 'x'
Add-Ticket $F '005-file' 1 'LEAD' 'BUILD' 'P1' 'ACCEPTED'
$r = Run 'manifest' @{ Card = '005-file'; Baseline = $true; As = 'BUILD' } $F
$bl = @((RF (Join-Path $cf 'baseline.manifest')) -split "`n" | Where-Object { $_ })
Check 'file zone: baseline lists the live target file as "README.md" (no trailing /)' ($r.Exit -eq 0 -and $bl.Count -eq 2 -and $bl[0] -match '^[0-9a-f]{64}  README\.md$' -and $bl[1] -match '  tools/b/x\.txt$') ($bl -join ' | ')
WF (P $F $fz) 'old readme'
WF (P $F "$dz/x.txt") 'x'
$r = Run 'manifest' @{ Card = '005-file' } $F
Check 'file zone: unchanged copy -> no entry' ($r.Exit -eq 0 -and $r.Out -match 'entries: 0' -and $r.Out -match [regex]::Escape("$fz") ) $r.Out
WF (P $F $fz) 'new readme'
$r = Run 'manifest' @{ Card = '005-file' } $F
$hNew = (Get-FileHash -LiteralPath (P $F $fz) -Algorithm SHA256).Hash.ToLowerInvariant()
Check 'file zone changed -> "<sha256 of the zone file>  README.md" (changed)' ($r.Exit -eq 0 -and $r.Out -match "(?m)^$hNew  README\.md\r?$" -and $r.Out -match 'changed 1') $r.Out
$dFile = Get-Digest $F '005-file'
WF (P $F $fz) 'new readme!'
Check 'file zone: 1-byte change -> new digest' ((Get-Digest $F '005-file') -ne $dFile) ''
[IO.File]::Delete((P $F $fz))
$r = Run 'manifest' @{ Card = '005-file' } $F
Check 'file zone removed (live target still there) -> "-  README.md" (removed)' ($r.Exit -eq 0 -and $r.Out -match '(?m)^-  README\.md\r?$' -and $r.Out -match 'removed 1') $r.Out
WF (P $F $fz) 'new readme'

# added: a file zone whose live target does not exist yet
$cfa = New-FakeCard $F '006-added' @('2026-11/09_02-other/out/docs/guide/NEW.md')
[IO.Directory]::Delete((P $F '2026-11/09_02-other/out/docs/guide/NEW.md'))
Add-Ticket $F '006-added' 1 'LEAD' 'BUILD' 'P1' 'ACCEPTED'
$r = Run 'manifest' @{ Card = '006-added'; Baseline = $true; As = 'BUILD' } $F
Check 'file zone, no live target yet: empty baseline' ($r.Exit -eq 0 -and (RF (Join-Path $cfa 'baseline.manifest')) -eq '') $r.Out
$r = Run 'manifest' @{ Card = '006-added' } $F
Check 'file zone and live target both missing -> REFUSED (neither a folder nor a file)' ($r.Exit -eq 1 -and $r.Out -match 'zone folder missing' -and $r.Out -match 'neither a folder nor a file') $r.Out
WF (P $F '2026-11/09_02-other/out/docs/guide/NEW.md') 'new guide'
$r = Run 'manifest' @{ Card = '006-added' } $F
Check 'file zone added -> "<sha256>  docs/guide/NEW.md" (added)' ($r.Exit -eq 0 -and $r.Out -match '(?m)^[0-9a-f]{64}  docs/guide/NEW\.md\r?$' -and $r.Out -match 'added 1') $r.Out

# overlap file vs folder, <task>/out/ itself, file vs folder mismatch, protected target
$cfo = New-FakeCard $F '007-overlap' @('2026-11/09_01-fake-task/out/tools', '2026-11/09_01-fake-task/out/tools/b/x.txt')
WF (Join-Path $cfo 'baseline.manifest') ''
$r = Run 'manifest' @{ Card = '007-overlap' } $F
Check 'overlap folder zone / file zone inside it -> refused' ($r.Exit -eq 1 -and $r.Out -match 'overlap') $r.Out
foreach ($bad in @('2026-11/09_01-fake-task/out', '2026-11/09_01-fake-task/out/')) {
    $cfx = New-FakeCard $F '008-out' @($bad)
    WF (Join-Path $cfx 'baseline.manifest') ''
    $r = Run 'manifest' @{ Card = '008-out' } $F
    Check "'$bad' (task out/ itself) -> refused" ($r.Exit -eq 1 -and $r.Out -match 'REFUSED: zone' -and $r.Out -match 'not a zone') $r.Out
}
$cfm = New-FakeCard $F '009-mismatch' @('2026-11/09_01-fake-task/out/tools/b')
WF (Join-Path $cfm 'baseline.manifest') ''
[IO.Directory]::Delete((P $F '2026-11/09_01-fake-task/out/tools/b'), $true)
WF (P $F '2026-11/09_01-fake-task/out/tools/b') 'a file where the live target is a folder'
$r = Run 'manifest' @{ Card = '009-mismatch' } $F
Check 'zone is a file but the live target is a folder -> refused' ($r.Exit -eq 1 -and $r.Out -match 'is a file but the live target') $r.Out
[IO.File]::Delete((P $F '2026-11/09_01-fake-task/out/tools/b'))
WF (P $F "$dz/x.txt") 'x'

# protected target, gate, ticket freeze and release -IfSafe with a file zone
$pz = '2026-11/09_03-proc/out/scripts/process/README.md'; $tz = '2026-11/09_03-proc/out/tools/t'
$cpp = New-FakeCard $F '010-prot' @($pz, $tz) @('scripts/process/README.md')
[IO.Directory]::Delete((P $F $pz))
WF (P $F 'scripts/process/README.md') 'live readme'
Add-Ticket $F '010-prot' 1 'LEAD' 'BUILD' 'P1' 'ACCEPTED'
$r = Run 'manifest' @{ Card = '010-prot'; Baseline = $true; As = 'BUILD' } $F
WF (P $F $pz) 'changed readme'
WF (P $F "$tz/tests/ok.Tests.ps1") 'exit 0'
$r = Run 'manifest' @{ Card = '010-prot' } $F
Check 'protected file zone -> listed as protected: scripts/process/README.md (changed)' ($r.Exit -eq 0 -and $r.Out -match 'protected: .*scripts/process/README\.md \(changed\)') $r.Out
$r = Run 'gate' @{ Card = '010-prot'; As = 'BUILD' } $F
$g = RF (Join-Path $cpp 'receipts\gate.json') | ConvertFrom-Json
$dp = Get-Digest $F '010-prot'
Check 'gate with a file zone -> PASS at the current digest' ($r.Exit -eq 0 -and $r.Out -match 'gate: PASS' -and $g.manifest_digest -eq $dp) $r.Out
$r = Run 'ticket' @{ Action = 'done'; Card = '010-prot'; As = 'BUILD'; Note = 'P1 done' } $F
$r = Run 'ticket' @{ Action = 'send'; Card = '010-prot'; As = 'BUILD'; To = 'REVIEW'; Phase = 'REVIEW'; Note = 'review' } $F
$t2 = RF (Join-Path $cpp 'handoff\H-02.json') | ConvertFrom-Json
Check 'ticket send to REVIEW freezes the file zone (digest + "README.md" line)' ($r.Exit -eq 0 -and $t2.manifest_digest -eq $dp -and (@($t2.manifest) -join '|') -match 'scripts/process/README\.md') $r.Out
$r = Run 'ticket' @{ Action = 'accept'; Card = '010-prot'; As = 'REVIEW' } $F
$r = Run 'ticket' @{ Action = 'done'; Card = '010-prot'; As = 'REVIEW'; Note = 'PASS light review' } $F
$r = Run 'release' @{ Card = '010-prot'; IfSafe = $true; As = 'LEAD'; DryRun = $true } $F
Check 'release -IfSafe: protected file zone without the owner''s approval line -> refused' ($r.Exit -eq 1 -and $r.Out -match "no Decisions line with the owner's quoted sentence") $r.Out
$cardFile = Join-Path $cpp 'CARD.md'
$txt = RF $cardFile
WF $cardFile ($txt.Replace("## Decisions`n", "## Decisions`n- owner 13/11 16:30: `"ok install`" -> approves scripts/process/README.md`n"))
$r = Run 'release' @{ Card = '010-prot'; IfSafe = $true; As = 'LEAD'; DryRun = $true } $F
Check 'release -IfSafe: with the approval line -> dry run SAFE' ($r.Exit -eq 0 -and $r.Out -match 'DRY RUN: all checks pass') $r.Out
WF (P $F 'scripts/process/README.md') 'live readme edited after P1'
$r = Run 'release' @{ Card = '010-prot'; IfSafe = $true; As = 'LEAD'; DryRun = $true } $F
Check 'release -IfSafe: live target file changed since the baseline -> refused' ($r.Exit -eq 1 -and $r.Out -match 'scripts/process/README\.md') $r.Out
Finish 'manifest'
