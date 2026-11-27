# Source scan: ONE function (Get-PathList) builds every path list (adaptation of "git diff --name-only --no-renames"),
# plus source hygiene: ASCII only, no dependency, no session ID / secret. Mutation check: a second routine turns it red.
param([switch]$Keep, [switch]$RedProof)
. (Join-Path $PSScriptRoot '_lib.ps1')
Test-Ps5Only @('manifest.ps1')   # Windows PowerShell 5.1: only the refusal of manifest.ps1, then exit
Write-Output '===== path-list scan + source hygiene ====='
$ForbiddenCmds = @('get-childitem', 'gci', 'ls', 'dir', 'compare-object', 'compare', 'diff')
$ForbiddenMembers = @('GetFiles', 'GetDirectories', 'GetFileSystemEntries', 'GetFileSystemInfos', 'EnumerateFiles', 'EnumerateDirectories', 'EnumerateFileSystemEntries', 'EnumerateFileSystemInfos')

# Scans every *.ps1 / *.psm1 directly in $Dir (the scripts; tests\ is not scanned). Returns violations + Get-PathList count.
function Get-PathListViolations([string]$Dir) {
    $v = New-Object System.Collections.ArrayList; $defs = 0
    foreach ($f in @(Get-ChildItem -LiteralPath $Dir -File | Where-Object { $_.Extension -eq '.ps1' -or $_.Extension -eq '.psm1' })) {
        $tok = $null; $err = $null
        $ast = [System.Management.Automation.Language.Parser]::ParseFile($f.FullName, [ref]$tok, [ref]$err)
        if (@($err).Count -gt 0) { [void]$v.Add("$($f.Name): parse error"); continue }
        $fn = @($ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Get-PathList' }, $true))
        $defs += $fn.Count
        $inside = { param($n) foreach ($d in $fn) { if ($n.Extent.StartOffset -ge $d.Extent.StartOffset -and $n.Extent.EndOffset -le $d.Extent.EndOffset) { return $true } }; return $false }
        foreach ($c in @($ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.CommandAst] }, $true))) {
            $name = $c.GetCommandName()
            if ($name -and $ForbiddenCmds -contains $name.ToLowerInvariant() -and -not (& $inside $c)) { [void]$v.Add("$($f.Name):$($c.Extent.StartLineNumber) $name") }
            foreach ($e in $c.CommandElements) {
                if ($e -is [System.Management.Automation.Language.CommandParameterAst] -and $e.ParameterName -ieq 'Recurse' -and -not (& $inside $c)) { [void]$v.Add("$($f.Name):$($c.Extent.StartLineNumber) -Recurse") }
            }
        }
        foreach ($m in @($ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.InvokeMemberExpressionAst] }, $true))) {
            $mn = [string]$m.Member.Value
            if ($ForbiddenMembers -contains $mn -and -not (& $inside $m)) { [void]$v.Add("$($f.Name):$($m.Extent.StartLineNumber) .$mn()") }
        }
    }
    return [pscustomobject]@{ Violations = [string[]]$v.ToArray(); Defs = $defs }
}

$s = Get-PathListViolations $script:Src
Check 'exactly one function Get-PathList in the scripts' ($s.Defs -eq 1) "defs=$($s.Defs)"
Check 'no file listing / path comparison outside Get-PathList' (@($s.Violations).Count -eq 0) (@($s.Violations) -join '; ')

# mutation check: copy the sources to %TEMP%, add a second path-list routine -> the scan must go red
$W = New-FakeTree 'scan'
$mut = Join-Path $W 'mut'; [void][IO.Directory]::CreateDirectory($mut)
foreach ($f in @(Get-ChildItem -LiteralPath $script:Src -File)) { Copy-Item -LiteralPath $f.FullName -Destination $mut }
$mod = Join-Path $mut 'CardFlow.psm1'
[IO.File]::AppendAllText($mod, "`nfunction Get-ChangedFiles([string]`$d) { Get-ChildItem -LiteralPath `$d -Recurse -File }`n", $script:U8)
$s2 = Get-PathListViolations $mut
Check 'mutation: extra Get-ChildItem -Recurse routine -> scan red' (@($s2.Violations).Count -ge 1) (@($s2.Violations) -join '; ')
Copy-Item -LiteralPath (Join-Path $script:Src 'CardFlow.psm1') -Destination $mod -Force
[IO.File]::AppendAllText($mod, "`nfunction Get-Diff2(`$a, `$b) { Compare-Object `$a `$b }`n", $script:U8)
Check 'mutation: extra Compare-Object routine -> scan red' (@((Get-PathListViolations $mut).Violations).Count -ge 1) ''
Copy-Item -LiteralPath (Join-Path $script:Src 'CardFlow.psm1') -Destination $mod -Force
[IO.File]::AppendAllText($mod, "`nfunction Get-Names2(`$d) { [IO.Directory]::EnumerateFiles(`$d) }`nfunction Get-PathList { }`n", $script:U8)
$s3 = Get-PathListViolations $mut
Check 'mutation: .NET EnumerateFiles + a 2nd Get-PathList -> scan red' (@($s3.Violations).Count -ge 1 -and $s3.Defs -eq 2) "defs=$($s3.Defs)"

# hygiene over the scripts AND the tests
$all = @(Get-ChildItem -LiteralPath $script:Src -Recurse -File | Where-Object { $_.Extension -eq '.ps1' -or $_.Extension -eq '.psm1' })
$nonAscii = @($all | Where-Object { @([IO.File]::ReadAllBytes($_.FullName) | Where-Object { $_ -gt 127 }).Count -gt 0 } | ForEach-Object { $_.Name })
Check 'every .ps1 / .psm1 is ASCII only (PS 5.1 reads BOM-less files as ANSI)' ($nonAscii.Count -eq 0) ($nonAscii -join ', ')
$dep = @($all | Where-Object { (RF $_.FullName) -match '(?im)^\s*(Install-Module|Install-Package|Invoke-Pester|Describe\s|#Requires\s+-Modules|Import-Module\s+(?!\(Join-Path \$(PSScriptRoot|script:Src) .CardFlow\.psm1.\)))' } | ForEach-Object { $_.Name })
Check 'no dependency: no Install-Module / Pester / other Import-Module' ($dep.Count -eq 0) ($dep -join ', ')
Import-Module (Join-Path $script:Src 'CardFlow.psm1') -Force -DisableNameChecking
$hits = @(foreach ($f in $all) { foreach ($h in @(Find-CfSecretInText (RF $f.FullName))) { "$($f.Name):$($h.Line) $($h.Rule)" } })
Check 'no secret / session ID pattern in any source (fake ones are built at run time)' ($hits.Count -eq 0) ($hits -join '; ')
$bad = @($all | Where-Object { (RF $_.FullName) -match '\?\?|\?\.' } | ForEach-Object { $_.Name })
Check 'no PS 7-only null operators in any source' ($bad.Count -eq 0) ($bad -join ', ')
$null = Read-CfConfig (New-FakeTree 'pathlist')
Check 'Test-CfProtected with the example config (AGENTS.md, CLAUDE.md, .claude/, scripts/process/, .github/workflows/, hooks/, migrations/)' (
    (Test-CfProtected '.github/workflows/ci.yml') -and (Test-CfProtected 'repo/.GitHub/Workflows/build.yml') -and -not (Test-CfProtected '.github/ISSUE_TEMPLATE/x.md') -and
    (Test-CfProtected 'AGENTS.md') -and (Test-CfProtected 'x/CLAUDE.md') -and (Test-CfProtected '.Claude/settings.json') -and
    (Test-CfProtected 'scripts/process/a.ps1') -and (Test-CfProtected 'app/.git/hooks/pre-commit') -and (Test-CfProtected 'db/migrations/001.sql') -and
    -not (Test-CfProtected 'tools/fake/a.ps1') -and -not (Test-CfProtected 'scripts/other/a.ps1')) ''
Check 'Test-CfShared with the example config: docs/process/ yes, STATUS.md / PROGRESS.md / roles/ no; kb/ is not built in' (
    (Test-CfShared 'docs/process/ROLES.md') -and (Test-CfShared 'docs/cards/README.md') -and (Test-CfShared 'docs/cards/_TEMPLATE/CARD.md') -and
    -not (Test-CfShared 'docs/process/STATUS.md') -and -not (Test-CfShared 'docs/process/roles/QUEUE_X.md') -and -not (Test-CfShared 'kb/a.md') -and
    (Test-CfShared 'scripts/process/a.ps1')) ''
$Wc = New-FakeTree 'pathlist-cfg'
Set-Cfg $Wc { param($c) $c.protected_paths = @('tools/secret/', 'Makefile'); $c.shared_paths = @('kb/'); $c.shared_paths_except = @('kb/drafts/') }
$null = Read-CfConfig $Wc
Check 'custom config lists: protected tools/secret/ + Makefile (anywhere), .claude/ no longer built in; shared kb/ except kb/drafts/' (
    (Test-CfProtected 'tools/secret/a.txt') -and (Test-CfProtected 'sub/Makefile') -and -not (Test-CfProtected '.claude/settings.json') -and
    (Test-CfShared 'kb/x.md') -and -not (Test-CfShared 'kb/drafts/x.md') -and (Test-CfProtected '../x')) ''
Finish 'pathlist'
