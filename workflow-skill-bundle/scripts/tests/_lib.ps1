# Shared helpers for the card-flow tests (dot-sourced by every *.Tests.ps1). ASCII only; loads on Windows PowerShell 5.1
# too (no CardFlow.psm1 import here): on 5.1 every test only checks the refusal of its script(s) (Test-Ps5Only).
# Every test works on a FAKE project under %TEMP%\cardflow-tests\ (root path has a space + JP / VN letters) that holds
# .workflow/workflow.config.json (a copy of config/workflow.config.example.json) and passes -Root; nothing here touches a
# real project. Fake trees are removed at the end
# (keep them with -Keep). Prints PASS / FAIL per check and "RESULT ..." at the end; exit 1 on any FAIL.
Set-StrictMode -Off
$ErrorActionPreference = 'Continue'
$script:Src = Split-Path -Parent $PSScriptRoot
$script:Fails = 0; $script:Count = 0
$script:TestBase = Join-Path ([IO.Path]::GetTempPath()) 'cardflow-tests'
$script:U8 = New-Object System.Text.UTF8Encoding($false)
$script:Trees = New-Object System.Collections.ArrayList
$script:Dot = [string][char]0x00B7
# the example config of the bundle: <bundle>/config/workflow.config.example.json (scripts/tests -> ../../config)
$script:ConfigExample = Join-Path (Split-Path -Parent $script:Src) 'config\workflow.config.example.json'

function Check([string]$Name, [bool]$Ok, [string]$Info = '') {
    $script:Count++
    if (-not $Ok) { $script:Fails++ }
    $mark = if ($Ok) { 'PASS' } else { 'FAIL' }
    $tail = if ($Info -and -not $Ok) { "  [$Info]" } else { '' }
    Write-Output "  $mark $Name$tail"
}

function Finish([string]$Title) {
    if (-not $Keep) { foreach ($t in $script:Trees) { Remove-Item -LiteralPath $t -Recurse -Force -ErrorAction SilentlyContinue } }
    Write-Output "RESULT $($Title): $($script:Fails) FAIL / $($script:Count) checks (PS $($PSVersionTable.PSVersion))"
    if ($script:Fails -gt 0) { exit 1 }
    exit 0
}

# Windows PowerShell 5.1: the scripts are PowerShell 7 only. Run each named script on 5.1 against a fake tree ->
# exactly one line 'REFUSED: <script> needs PowerShell 7 (pwsh) ...', exit 1, fake tree unchanged (listing + hashes);
# then RESULT + exit. On PowerShell 7 this returns at once and the test runs in full.
# -RedProof (a switch of the calling test): the first script is run from a temp copy (in the fake tree's parent
# folder under %TEMP%) whose version-check line is removed - its check must FAIL.
function Test-Ps5Only([string[]]$Scripts) {
    if ($PSVersionTable.PSVersion.Major -ge 7) { return }
    $rp = [bool](Get-Variable -Name RedProof -ValueOnly -ErrorAction SilentlyContinue)
    Write-Output "===== $($Scripts -join ', ') on Windows PowerShell $($PSVersionTable.PSVersion) (refusal only)$(if ($rp) { ' - RED PROOF: ' + $Scripts[0] + ' without its version check' }) ====="
    $W = New-FakeTree 'ps5'
    $null = New-FakeCard $W
    $dir = $script:Src
    if ($rp) {
        $dir = Join-Path (Split-Path -Parent $W) 'redproof-scripts'
        [void][IO.Directory]::CreateDirectory($dir)
        foreach ($n in @([IO.Directory]::GetFiles($script:Src))) { if ($n -match '\.(ps1|psm1)$') { [IO.File]::Copy($n, (Join-Path $dir ([IO.Path]::GetFileName($n)))) } }
        $p0 = Join-Path $dir $Scripts[0]
        $kept = @([IO.File]::ReadAllLines($p0) | Where-Object { $_ -notmatch '^if \(\$PSVersionTable\.PSVersion\.Major -lt 7\)' })
        [IO.File]::WriteAllLines($p0, [string[]]$kept)
    }
    $exe = Join-Path $PSHOME 'powershell.exe'
    $before = Get-TreeHash $W
    Push-Location -LiteralPath $W
    try {
        foreach ($s in $Scripts) {
            $global:LASTEXITCODE = 0
            $out = @(& $exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $dir $s) -Root $W 2>&1 | ForEach-Object { [string]$_ } | Where-Object { $_.Trim() })
            $code = $LASTEXITCODE
            Check "5.1 refuses $s with one line, exit 1" ($code -eq 1 -and $out.Count -eq 1 -and $out[0] -like "REFUSED: $s needs PowerShell 7 (pwsh); this is Windows PowerShell 5.1*") ("exit $code / " + (@($out | Select-Object -First 2) -join ' / '))
        }
    }
    finally { Pop-Location }
    Check 'nothing written by the refused runs (fake tree listing + hashes unchanged)' ((Get-TreeHash $W) -eq $before) ''
    Finish ($Scripts[0] + ' on 5.1')
}

function New-FakeTree([string]$Tag) {
    $id = $Tag + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
    $name = 'Proj Work ' + [string][char]0x30C6 + [string][char]0x1EA1
    $top = Join-Path $script:TestBase $id
    $W = Join-Path $top $name
    foreach ($d in 'kb', 'docs\cards', 'docs\process', 'lead') { [void][IO.Directory]::CreateDirectory((Join-Path $W $d)) }
    [void][IO.Directory]::CreateDirectory((Join-Path $W '.workflow'))
    [IO.File]::WriteAllText((Join-Path $W '.workflow\workflow.config.json'), [IO.File]::ReadAllText($script:ConfigExample, $script:U8), $script:U8)
    # the fake project keeps the strict two-host rule (gate.hosts ps5 + ps7) so the ps5 checks stay testable;
    # gate.Tests / config.Tests set other values themselves
    Set-Cfg $W { param($c) $c.gate.hosts = @('ps5', 'ps7') }
    [void]$script:Trees.Add($top)
    return $W
}

# Changes keys of the fake project's config: Set-Cfg $W { param($c) $c.approval_name = 'boss' }
function Set-Cfg([string]$W, [scriptblock]$Change) {
    $f = Join-Path $W '.workflow\workflow.config.json'
    $c = ConvertFrom-Json -InputObject ([IO.File]::ReadAllText($f, $script:U8))
    & $Change $c
    [IO.File]::WriteAllText($f, (ConvertTo-Json -InputObject $c -Depth 10), $script:U8)
}

function WF([string]$Path, [string]$Text = 'x') {
    [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($Path))
    [IO.File]::WriteAllText($Path, $Text, $script:U8)
}

function RF([string]$Path) { return [IO.File]::ReadAllText($Path, $script:U8) }

function P([string]$W, [string]$Rel) { return (Join-Path $W $Rel.Replace('/', '\')) }

function New-FakeCard([string]$W, [string]$Card = '001-fake', [string[]]$Zones = @('2026-11/09_01-fake-task/out/tools/fake'),
    [string[]]$Protected = @(), [string[]]$Decisions = @(), [string]$State = 'BUILDING') {
    $d = Join-Path $W "docs\cards\$Card"
    [void][IO.Directory]::CreateDirectory((Join-Path $d 'handoff'))
    $fm = "---`ncard: $Card`ntitle: fake card`ntask: T-20260109-99`nzones: [$($Zones -join ', ')]   # comment, with: [brackets]`nstate: $State`nrisk_class: low`nprotected_paths: [$($Protected -join ', ')]`n---`n"
    $dec = ($Decisions | ForEach-Object { "- $_" }) -join "`n"
    $body = "`n# fake card`n`n## Decisions`n$dec`n`n## Takeover`n- x`n`n## State log`n- 09/11 09:00 DRAFT - LEAD`n`n## NEXT`n- x`n"
    WF (Join-Path $d 'CARD.md') ($fm + $body)
    WF (Join-Path $d 'log.md') "# log - $Card`n`n- 09/11 09:00 LEAD $($script:Dot) done: card $($script:Dot) doing: - $($script:Dot) next: - $($script:Dot) check: -`n"
    foreach ($z in $Zones) { try { [void][IO.Directory]::CreateDirectory((P $W $z)) } catch { } }   # invalid test zones: no folder
    return $d
}

# Hand-made ticket (like LEAD writes them). $Hist entries: 'at|by|state|note'.
function Add-Ticket([string]$W, [string]$Card, [int]$N, [string]$From, [string]$To, [string]$Phase, [string]$State,
    [string]$Digest = '', [string[]]$Hist = @(), [string]$Verdict = 'PASS') {
    if ($Hist.Count -eq 0) {
        $at = (Get-Date).AddMinutes(-5).ToString('yyyy-MM-ddTHH:mm')
        $Hist = @("$at|$From|SENT|sent")
        if ($State -ne 'SENT') {
            $note = 'x'; if ($State -eq 'DONE' -and $To -eq 'REVIEW') { $note = "$Verdict reviewed" }
            if ($State -eq 'DONE') { $Hist += "$at|$To|ACCEPTED|ok" }
            $Hist += "$at|$To|$State|$note"
        }
    }
    $h = ($Hist | ForEach-Object { $p = $_.Split('|'); '    { "at": "' + $p[0] + '", "by": "' + $p[1] + '", "state": "' + $p[2] + '", "note": "' + $p[3] + '" }' }) -join ",`n"
    $json = "{`n  `"card`": `"$Card`",`n  `"n`": $N,`n  `"from`": `"$From`",`n  `"to`": `"$To`",`n  `"phase`": `"$Phase`",`n  `"manifest_digest`": `"$Digest`",`n  `"state`": `"$State`",`n  `"agent`": `"test`",`n  `"history`": [`n$h`n  ]`n}`n"
    WF (Join-Path $W ("docs\cards\$Card\handoff\H-{0:D2}.json" -f $N)) $json
}

# Hand-made receipt: one PASS entry per *.Tests.ps1 under the fake task folders for each host in $Hosts.
function Write-Gate([string]$W, [string]$Digest, [string]$Result = 'PASS', [string]$Card = '001-fake', [string[]]$Hosts = @('ps5', 'ps7')) {
    $tests = @(Get-ChildItem -LiteralPath (Join-Path $W '2026-11') -Recurse -File -Filter '*.Tests.ps1' -ErrorAction SilentlyContinue | ForEach-Object {
            $rel = $_.FullName.Substring($W.Length + 1).Replace('\', '/')
            foreach ($h in $Hosts) { '    { "file": "' + $rel + '", "host": "' + $h + '", "version": "x", "exit": 0, "result": "PASS" }' }
        })
    $t = if ($tests.Count) { "[`n" + ($tests -join ",`n") + "`n  ]" } else { '[]' }
    WF (Join-Path $W "docs\cards\$Card\receipts\gate.json") "{`n  `"manifest_digest`": `"$Digest`",`n  `"tests`": $t,`n  `"result`": `"$Result`",`n  `"at`": `"2026-11-09T10:00`"`n}`n"
}

# Runs one command script in this process: Run 'ticket' @{ Action = 'send'; Card = '001-fake'; As = 'LEAD' } $W
function Run([string]$Cmd, [hashtable]$A, [string]$W) {
    $a2 = @{}; foreach ($k in $A.Keys) { $a2[$k] = $A[$k] }
    if ($W) { $a2['Root'] = $W }
    $global:LASTEXITCODE = 0
    $out = & (Join-Path $script:Src "$Cmd.ps1") @a2 *>&1 | Out-String -Width 500
    return [pscustomobject]@{ Exit = $global:LASTEXITCODE; Out = $out }
}

function Get-Digest([string]$W, [string]$Card = '001-fake') {
    $r = Run 'manifest' @{ Card = $Card } $W
    if ($r.Out -match 'digest: ([0-9a-f]{64})') { return $Matches[1] }
    return "(no digest: $($r.Out.Trim()))"
}

function Get-TreeHash([string]$Dir) {
    $files = @(Get-ChildItem -LiteralPath $Dir -Recurse -Force -File | Sort-Object FullName)
    $lines = foreach ($f in $files) { $f.FullName.Substring($Dir.Length) + '|' + (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash }
    return ($lines -join "`n")
}

function Get-Reasons([string]$Out) { return @(($Out -split "`r?`n") | Where-Object { $_ -match '^  - ' } | ForEach-Object { $_.Trim() }) }

# A card ready for release: zones tools/fake + scripts/process, empty baseline, H-01 DONE, H-02 REVIEW DONE <Verdict>, gate PASS.
function New-ReleaseTree([string]$Tag, [string[]]$Protected = @('scripts/process/'),
    [string[]]$Decisions = @('owner 09/11 09:40: "ok, build and install it" -> approves scripts/process/'),
    [switch]$NoGate, [string]$Verdict = 'PASS', [switch]$Ps7Test, [switch]$Ps7TestOutside) {
    $W = New-FakeTree $Tag
    $z1 = '2026-11/09_01-fake-task/out/tools/fake'; $z2 = '2026-11/09_01-fake-task/out/scripts/process'
    $cd = New-FakeCard $W '001-fake' @($z1, $z2) $Protected $Decisions
    WF (Join-Path $cd 'baseline.manifest') ''
    WF (Join-Path (P $W $z1) 'tool.ps1') 'Write-Output 1'
    WF (Join-Path (P $W $z2) 'a.ps1') 'Write-Output 2'
    WF (Join-Path (P $W $z2) 'tests\ok.Tests.ps1') $(if ($Ps7Test) { "#Requires -Version 7`nexit 0" } else { 'exit 0' })
    if ($Ps7TestOutside) { WF (Join-Path (P $W $z1) 'tests\x.Tests.ps1') "#Requires -Version 7`nexit 0" }   # target tools/fake
    $dg = Get-Digest $W
    Add-Ticket $W '001-fake' 1 'LEAD' 'BUILD' 'P1' 'DONE'
    Add-Ticket $W '001-fake' 2 'BUILD' 'REVIEW' 'REVIEW' 'DONE' $dg -Verdict $Verdict
    if (-not $NoGate) { Write-Gate $W $dg 'PASS' }
    return [pscustomobject]@{ W = $W; Digest = $dg; Z1 = (P $W $z1); Z2 = (P $W $z2); Card = $cd }
}
