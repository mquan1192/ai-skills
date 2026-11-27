#Requires -Version 7
# CardFlow.psm1 - process scripts for the card / ticket flow (workflow skill bundle).
# One module, thin entry scripts (ticket, checkpoint, manifest, gate, release, intake, board, stale, steplog).
# Every path, list and threshold comes from <project root>/.workflow/workflow.config.json (schema 1).
# Formats: the cards README (tickets, bell), AGENTS.md "Versioning without git" (manifest, digest, rename rule),
# baseline.manifest at BUILD start, checkpoint without open ticket, release only with -IfSafe.
# PowerShell 7 only (v1.1): every entry script refuses Windows PowerShell 5.1 with one line. No dependency. ASCII only.
# Every file listing and every path comparison is done by ONE function: Get-PathList (a test scans for any other).

Set-StrictMode -Version 2.0

$script:Roles = @('LEAD', 'DOCS', 'BUILD', 'REVIEW', 'OPS')
# Readable names (v1.1, templates NAMES section 3): every value read from a file or a parameter goes through
# ConvertTo-CfName (old -> new); comparisons use the new names; new records are written with the new names;
# old records are never rewritten (a ticket keeps its old phase and history lines; reading them gives the new names).
$script:Phases = @('BUILD', 'TEST-GATE', 'REVIEW', 'FIX', 'VERIFY-FIX', 'RELEASE', 'RETRO')
$script:States = @('SENT', 'ACCEPTED', 'DONE', 'ON-HOLD', 'TAKEN-OVER')
$script:OpenStates = @('SENT', 'ACCEPTED', 'ON-HOLD', 'TAKEN-OVER')
$script:Verdicts = @('PASS', 'FAIL', 'FIX-VERIFIED')
$script:Closed = @('RELEASED', 'CANCELLED')
$script:NameMap = @{
    CardState   = @{ 'CANDIDATE' = 'IN-REVIEW'; 'FIXES' = 'FIXING'; 'MERGED' = 'RELEASED'; 'CLOSED' = 'CANCELLED' }
    Phase       = @{ 'P1' = 'BUILD'; 'GATE' = 'TEST-GATE'; 'FIXES' = 'FIX'; 'VERIFY' = 'VERIFY-FIX' }
    TicketState = @{ 'HOLD' = 'ON-HOLD'; 'TAKEOVER' = 'TAKEN-OVER' }
    Verdict     = @{ 'NG' = 'FAIL'; 'FIXES_VERIFIED' = 'FIX-VERIFIED'; 'STALE' = 'OUTDATED' }
    Receipt     = @{ 'STALE' = 'OUTDATED' }
}
$script:WordRe = '^\s*([A-Z][A-Z_\-]*)(?![A-Za-z0-9_\-])'   # first word of a note (verdict / OUTDATED)
$script:CardRe = '^\d{3}-[A-Za-z0-9][A-Za-z0-9-]*$'
$script:Utf8 = New-Object System.Text.UTF8Encoding($false)
$script:Arrow = [string][char]0x2192   # ->
$script:Dot = [string][char]0x00B7     # middle dot
$script:Dash = [string][char]0x2014    # em dash
$script:CfExit = 0
$script:HasDateKind = (Get-Command ConvertFrom-Json).Parameters.ContainsKey('DateKind')   # PS 7.5+: keep ISO strings as strings

# Secret patterns (values are never printed: only file + line + rule). Also used to refuse ticket / log text.
$script:SecretRules = @(
    @{ Id = 'private-key'; Re = '-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----' },
    @{ Id = 'aws-key'; Re = '\bAKIA[0-9A-Z]{16}\b' },
    @{ Id = 'anthropic-key'; Re = '\bsk-ant-[A-Za-z0-9_\-]{20,}' },
    @{ Id = 'api-key'; Re = '\bsk-[A-Za-z0-9]{32,}\b' },
    @{ Id = 'github-token'; Re = '\bgh[pousr]_[A-Za-z0-9]{30,}\b' },
    @{ Id = 'slack-token'; Re = '\bxox[abposr]-[A-Za-z0-9\-]{10,}' },
    @{ Id = 'google-key'; Re = '\bAIza[0-9A-Za-z_\-]{35}\b' },
    @{ Id = 'jwt'; Re = '\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}' },
    @{ Id = 'assignment'; Re = '(?i)\b(?:password|passwd|pwd|secret|api[_-]?key|access[_-]?key|auth[_-]?token|access[_-]?token|token|client[_-]?secret)\b["'']?\s*[:=]\s*["''][^"''\s]{8,}["'']' },
    # unquoted forms (key=value, $env:KEY = value, ;Password=value; connection strings, YAML key: value).
    # Not a secret: a value that starts with $ < [ ( @ { % or a quote (variables, <placeholder>, [MASKED], code).
    @{ Id = 'assignment-unquoted'; Re = '(?i)\b(?:password|passwd|pwd|secret|api[_-]?key|access[_-]?key|auth[_-]?token|access[_-]?token|token|client[_-]?secret)\b\s*[:=]\s*(?![\$<\[\(@\{%"''])[^\s;,"'']{8,}' },
    @{ Id = 'session-id'; Re = '\blocal' + '_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b' }
)

# ======================================================================================
# THE path-list function. Every file listing, folder listing and path comparison is here.
# ======================================================================================
function Get-PathList {
    <#
      -Under <dir>            all files below <dir> (recursive, hidden included), sorted by relative path (ordinal);
                              a junction / symlink anywhere below -> REFUSED (it would escape the zone). Missing dir -> none.
      -Item <file>            the one file <file> as a list of one entry (Rel = ''), for a single-file zone;
                              a junction / symlink file -> REFUSED. Missing file or a folder -> none.
      -In <dir> [-Directory] [-Filter]   names of the direct children (files, or folders with -Directory), sorted ordinal.
      -Old <entries> -New <entries>      compare two path lists (objects with Path + Hash) by path, case-insensitive:
                              added / changed (hash or case differs) / removed (Hash '-'). A rename is old path removed +
                              new path added. Output sorted by Path (ordinal).
    #>
    [CmdletBinding(DefaultParameterSetName = 'Under')]
    param(
        [Parameter(ParameterSetName = 'Under', Mandatory = $true)][string]$Under,
        [Parameter(ParameterSetName = 'Item', Mandatory = $true)][string]$Item,
        [Parameter(ParameterSetName = 'In', Mandatory = $true)][string]$In,
        [Parameter(ParameterSetName = 'In')][switch]$Directory,
        [Parameter(ParameterSetName = 'In')][string]$Filter = '*',
        [Parameter(ParameterSetName = 'Compare', Mandatory = $true)][AllowEmptyCollection()][object[]]$Old,
        [Parameter(ParameterSetName = 'Compare', Mandatory = $true)][AllowEmptyCollection()][object[]]$New
    )
    $ord = [StringComparer]::Ordinal
    switch ($PSCmdlet.ParameterSetName) {
        'Under' {
            $base = [IO.Path]::GetFullPath($Under).TrimEnd('\')
            if (-not [IO.Directory]::Exists($base)) { return }
            $items = New-Object 'System.Collections.Generic.List[object]'
            $stack = New-Object System.Collections.Stack
            $stack.Push((New-Object IO.DirectoryInfo $base))
            while ($stack.Count -gt 0) {
                $d = $stack.Pop()
                foreach ($e in $d.GetFileSystemInfos()) {
                    if ($e.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                        $tgt = ''
                        try { $tgt = [string]((Get-Item -LiteralPath $e.FullName -Force).Target) } catch { $tgt = '?' }
                        throw "REFUSED: junction / symlink '$($e.FullName)' -> '$tgt' (links are not allowed in a zone or target; list the target as its own zone)."
                    }
                    if ($e -is [IO.DirectoryInfo]) { $stack.Push($e) }
                    else {
                        $items.Add([pscustomobject]@{
                                Rel = $e.FullName.Substring($base.Length + 1).Replace('\', '/'); Full = $e.FullName
                                Length = $e.Length; Time = $e.LastWriteTime
                            })
                    }
                }
            }
            $items.Sort([Comparison[object]] { param($a, $b) [string]::CompareOrdinal([string]$a.Rel, [string]$b.Rel) })
            return $items.ToArray()
        }
        'Item' {
            $full = [IO.Path]::GetFullPath($Item)
            if (-not [IO.File]::Exists($full)) { return }
            $e = New-Object IO.FileInfo $full
            if ($e.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                $tgt = ''
                try { $tgt = [string]((Get-Item -LiteralPath $e.FullName -Force).Target) } catch { $tgt = '?' }
                throw "REFUSED: junction / symlink '$($e.FullName)' -> '$tgt' (links are not allowed in a zone or target; list the target as its own zone)."
            }
            return [pscustomobject]@{ Rel = ''; Full = $e.FullName; Length = $e.Length; Time = $e.LastWriteTime }
        }
        'In' {
            if (-not [IO.Directory]::Exists($In)) { return }
            $names = if ($Directory) { [IO.Directory]::GetDirectories($In) } else { [IO.Directory]::GetFiles($In, $Filter) }
            $n = [string[]]@($names | ForEach-Object { [IO.Path]::GetFileName($_) })
            [Array]::Sort($n, $ord)
            return $n
        }
        'Compare' {
            $oldMap = New-Object 'System.Collections.Generic.Dictionary[string,object]' ([StringComparer]::OrdinalIgnoreCase)
            foreach ($o in $Old) { $oldMap[[string]$o.Path] = $o }
            $seen = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
            $out = New-Object 'System.Collections.Generic.List[object]'
            foreach ($x in $New) {
                $p = [string]$x.Path; [void]$seen.Add($p)
                if (-not $oldMap.ContainsKey($p)) { [void]$out.Add([pscustomobject]@{ Path = $p; Hash = [string]$x.Hash; Change = 'added' }) }
                else {
                    $o = $oldMap[$p]
                    if ([string]$o.Hash -ne [string]$x.Hash -or -not [string]::Equals([string]$o.Path, $p, [StringComparison]::Ordinal)) {
                        [void]$out.Add([pscustomobject]@{ Path = $p; Hash = [string]$x.Hash; Change = 'changed' })
                    }
                }
            }
            foreach ($o in $Old) { if (-not $seen.Contains([string]$o.Path)) { [void]$out.Add([pscustomobject]@{ Path = [string]$o.Path; Hash = '-'; Change = 'removed' }) } }
            $out.Sort([Comparison[object]] { param($a, $b) [string]::CompareOrdinal([string]$a.Path, [string]$b.Path) })
            return $out.ToArray()
        }
    }
}

# ======================================================================================
# Small helpers
# ======================================================================================
function Get-CfExitCode { return $script:CfExit }

function Invoke-CfMain([scriptblock]$Body) {
    # Runs one command; any exception -> one "REFUSED: ..." / "ERROR: ..." line and exit code 1.
    $script:CfExit = 0
    try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch { }
    try { & $Body }
    catch {
        $m = $_.Exception.Message
        if ($m -notmatch '^(REFUSED|ERROR):') { $m = "ERROR: $m" }
        Write-Output $m
        $script:CfExit = 1
    }
}

# ---------------- project root + config (.workflow/workflow.config.json) ----------------
$script:CfgRel = '.workflow/workflow.config.json'
$script:CfgHint = 'chay install.py hoac chep config/workflow.config.example.json thanh .workflow/workflow.config.json'
$script:Cfg = $null
$script:CfRoot = ''
# defaults = the example config; used only for keys the project config leaves out
$script:CfgDefaultPaths = @{ cards = 'docs/cards'; process_docs = 'docs/process'; roles_docs = 'docs/process/roles'; lead = 'lead'; scripts = 'scripts/process'; process_log = 'process-log'; trash = '_trash' }

function Test-CfWorkspace([string]$Dir) {
    return [IO.File]::Exists((Join-Path $Dir $script:CfgRel.Replace('/', '\')))
}

function Read-CfConfig([string]$Root) {
    $f = Join-Path $Root $script:CfgRel.Replace('/', '\')
    if (-not [IO.File]::Exists($f)) { throw "REFUSED: $($script:CfgRel) not found in '$Root' - $($script:CfgHint)." }
    $c = $null
    try { $c = ConvertFrom-CfJsonText ([IO.File]::ReadAllText($f, $script:Utf8)) $f } catch { throw "REFUSED: $($script:CfgRel) unreadable ($($_.Exception.Message)) - $($script:CfgHint)." }
    if ([string](Get-CfProp $c 'schema') -ne '1') { throw "REFUSED: $($script:CfgRel): schema must be 1 (got '$([string](Get-CfProp $c 'schema'))') - $($script:CfgHint)." }
    $script:Cfg = $c; $script:CfRoot = $Root
    return $c
}

function Resolve-CfRoot([string]$Root, [string]$From) {
    # -Root, else the current folder upward, else the script folder upward: the first folder holding the config.
    $full = ''
    if ($Root) {
        $full = [IO.Path]::GetFullPath($Root).TrimEnd('\')
        if (-not (Test-CfWorkspace $full)) { throw "REFUSED: '$full' is not a project root (no $($script:CfgRel)) - $($script:CfgHint)." }
    }
    else {
        foreach ($start in @((Get-Location).ProviderPath, $From)) {
            if (-not $start) { continue }
            $d = [IO.Path]::GetFullPath($start).TrimEnd('\')
            while ($d) {
                if (Test-CfWorkspace $d) { $full = $d; break }
                $p = [IO.Path]::GetDirectoryName($d)
                if (-not $p -or $p -eq $d) { break }
                $d = $p.TrimEnd('\')
            }
            if ($full) { break }
        }
        if (-not $full) { throw "REFUSED: no project root ($($script:CfgRel)) above the current folder or '$From'; pass -Root - $($script:CfgHint)." }
    }
    $null = Read-CfConfig $full
    return $full
}

function Get-CfCfg([string]$Name) { return (Get-CfProp $script:Cfg $Name) }

function Get-CfCfgRel([string]$Key) {
    # paths.<key> as a relative path with '/' (no leading / trailing slash); a rooted path or '..' is refused
    $v = ''; $p = Get-CfCfg 'paths'; if ($p) { $v = [string](Get-CfProp $p $Key) }
    if (-not $v) { $v = [string]$script:CfgDefaultPaths[$Key] }
    $v = $v.Replace('\', '/').Trim().Trim('/')
    if (-not $v -or $v.Contains(':') -or @($v.Split('/') | Where-Object { $_ -eq '..' -or $_ -eq '' }).Count -gt 0) { throw "REFUSED: $($script:CfgRel): paths.$Key '$v' must be a plain relative path." }
    return $v
}

function Get-CfCfgPath([string]$Root, [string]$Key) { return (Join-Path $Root (Get-CfCfgRel $Key).Replace('/', '\')) }

function Get-CfCfgList([string]$Name) { return [string[]]@(@(Get-CfCfg $Name) | Where-Object { $null -ne $_ -and [string]$_ } | ForEach-Object { [string]$_ }) }

function Get-CfCfgNumber([string]$Group, [string]$Key, [double]$Default) {
    $g = Get-CfCfg $Group; $v = $null; if ($g) { $v = Get-CfProp $g $Key }
    if ($null -eq $v -or [string]$v -eq '') { return $Default }
    $d = 0.0
    if (-not [double]::TryParse([string]$v, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$d) -or $d -le 0) { throw "REFUSED: $($script:CfgRel): $Group.$Key must be a positive number." }
    return $d
}

function Get-CfApprovalName {
    $n = [string](Get-CfCfg 'approval_name')
    if (-not $n) { $n = 'owner' }
    if ($n -notmatch '^[A-Za-z0-9_.-]{1,40}$') { throw "REFUSED: $($script:CfgRel): approval_name '$n' must be one word (letters, digits, _ . -)." }
    return $n
}

function Assert-CfRole([string]$Role, [string]$What = '-As') {
    if (-not $Role) { throw "REFUSED: $What is required (one of $($script:Roles -join ', '))." }
    if ($script:Roles -notcontains $Role.ToUpperInvariant()) { throw "REFUSED: $What '$Role' is not a role ($($script:Roles -join ', '))." }
    return $Role.ToUpperInvariant()
}

function Get-CfNowText([datetime]$Now) { return $Now.ToString('yyyy-MM-ddTHH:mm', [Globalization.CultureInfo]::InvariantCulture) }
function Get-CfShortTime([datetime]$Now) { return $Now.ToString('dd/MM HH:mm', [Globalization.CultureInfo]::InvariantCulture) }
function Get-CfShort([string]$Digest) { if ($Digest -and $Digest.Length -ge 12) { return $Digest.Substring(0, 12) } return $script:Dash }

function ConvertTo-CfAt($v) {
    if ($v -is [datetime]) { return $v.ToString('yyyy-MM-ddTHH:mm:ss', [Globalization.CultureInfo]::InvariantCulture) }
    return [string]$v
}

function ConvertFrom-CfAt([string]$At) {
    $f = [string[]]@('yyyy-MM-ddTHH:mm', 'yyyy-MM-ddTHH:mm:ss')
    $r = [datetime]::MinValue
    if ([datetime]::TryParseExact($At, $f, [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::None, [ref]$r)) { return $r }
    return $null
}

function Get-CfSha256Text([string]$Text) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($sha.ComputeHash($script:Utf8.GetBytes($Text))).Replace('-', '').ToLowerInvariant() }
    finally { $sha.Dispose() }
}

function Get-CfFileHash([string]$Full) {
    $sha = [Security.Cryptography.SHA256]::Create()
    $fs = [IO.File]::Open($Full, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
    try { return [BitConverter]::ToString($sha.ComputeHash($fs)).Replace('-', '').ToLowerInvariant() }
    finally { $fs.Dispose(); $sha.Dispose() }
}

function Get-CfProp($Obj, [string]$Name) {
    if ($null -eq $Obj) { return $null }
    $p = $Obj.PSObject.Properties[$Name]
    if ($null -eq $p) { return $null }
    return $p.Value
}

function Find-CfSecretInText([string]$Text) {
    # Returns @(@{ Line; Rule }) - never the matched value.
    $hits = New-Object System.Collections.ArrayList
    $lines = $Text.Replace("`r`n", "`n").Split("`n")
    for ($i = 0; $i -lt $lines.Length; $i++) {
        foreach ($r in $script:SecretRules) {
            if ([regex]::IsMatch($lines[$i], $r.Re)) { [void]$hits.Add([pscustomobject]@{ Line = $i + 1; Rule = $r.Id }) }
        }
    }
    return $hits.ToArray()
}

function Assert-CfCleanText([string[]]$Texts) {
    foreach ($t in $Texts) {
        if (-not $t) { continue }
        $h = @(Find-CfSecretInText $t)
        if ($h.Count -gt 0) { throw "REFUSED: text looks like a secret or session ID (rule $($h[0].Rule)); tickets and logs never carry them." }
    }
}

function Write-CfTextFile([string]$File, [string]$Text, [switch]$New) {
    # -New: never overwrites (CreateNew). Otherwise write to <file>.tmp and replace (no half-written file).
    if ($New) {
        $fs = [IO.File]::Open($File, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        try { $b = $script:Utf8.GetBytes($Text); $fs.Write($b, 0, $b.Length) } finally { $fs.Dispose() }
    }
    else {
        $tmp = "$File.tmp"
        [IO.File]::WriteAllText($tmp, $Text, $script:Utf8)
        if ([IO.File]::Exists($File)) { [IO.File]::Replace($tmp, $File, [NullString]::Value) } else { [IO.File]::Move($tmp, $File) }
    }
    $back = [IO.File]::ReadAllText($File, $script:Utf8)
    if ($back -ne $Text) { throw "ERROR: re-read of '$File' differs from what was written." }
}

function Add-CfLine([string]$File, [string]$Line) {
    # Append-only: one line, old content untouched.
    $prefix = ''
    if ([IO.File]::Exists($File)) {
        $len = (New-Object IO.FileInfo $File).Length
        if ($len -gt 0) {
            $fs = [IO.File]::Open($File, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
            try { [void]$fs.Seek(-1, [IO.SeekOrigin]::End); if ($fs.ReadByte() -ne 10) { $prefix = "`n" } } finally { $fs.Dispose() }
        }
    }
    [IO.File]::AppendAllText($File, $prefix + $Line + "`n", $script:Utf8)
}

function ConvertTo-CfOneLine([string]$s) {
    if ($null -eq $s) { return '' }
    return (($s -replace '[\r\n\t]+', ' ') -replace '\s{2,}', ' ').Trim()
}

# ---------------- JSON (own writer: identical output on 5.1 and 7, no depth limit, no BOM) ----------------
function ConvertTo-CfJsonString([string]$s) {
    $sb = New-Object System.Text.StringBuilder
    [void]$sb.Append('"')
    foreach ($ch in $s.ToCharArray()) {
        $c = [int]$ch
        if ($ch -eq '"') { [void]$sb.Append('\"') }
        elseif ($ch -eq '\') { [void]$sb.Append('\\') }
        elseif ($c -eq 10) { [void]$sb.Append('\n') }
        elseif ($c -eq 13) { [void]$sb.Append('\r') }
        elseif ($c -eq 9) { [void]$sb.Append('\t') }
        elseif ($c -lt 32) { [void]$sb.Append(('\u{0:x4}' -f $c)) }
        else { [void]$sb.Append($ch) }
    }
    [void]$sb.Append('"')
    return $sb.ToString()
}

function Test-CfScalar($v) { return ($null -eq $v -or $v -is [string] -or $v -is [bool] -or $v -is [int] -or $v -is [long] -or $v -is [double]) }

function ConvertTo-CfJson($v, [int]$Indent = 0) {
    $pad = ' ' * $Indent; $pad2 = ' ' * ($Indent + 2)
    if ($null -eq $v) { return 'null' }
    if ($v -is [string]) { return (ConvertTo-CfJsonString $v) }
    if ($v -is [bool]) { if ($v) { return 'true' } else { return 'false' } }
    if ($v -is [int] -or $v -is [long]) { return $v.ToString([Globalization.CultureInfo]::InvariantCulture) }
    if ($v -is [double]) { return $v.ToString('R', [Globalization.CultureInfo]::InvariantCulture) }
    if ($v -is [System.Collections.IDictionary]) {
        $keys = @($v.Keys)
        if ($keys.Count -eq 0) { return '{}' }
        $allScalar = $true; foreach ($k in $keys) { if (-not (Test-CfScalar $v[$k])) { $allScalar = $false } }
        if ($Indent -gt 0 -and $allScalar) {
            return '{ ' + (($keys | ForEach-Object { (ConvertTo-CfJsonString ([string]$_)) + ': ' + (ConvertTo-CfJson $v[$_] 0) }) -join ', ') + ' }'
        }
        $parts = foreach ($k in $keys) { $pad2 + (ConvertTo-CfJsonString ([string]$k)) + ': ' + (ConvertTo-CfJson $v[$k] ($Indent + 2)) }
        return "{`n" + ($parts -join ",`n") + "`n$pad}"
    }
    if ($v -is [System.Collections.IEnumerable]) {
        $items = @($v)
        if ($items.Count -eq 0) { return '[]' }
        $parts = foreach ($i in $items) { $pad2 + (ConvertTo-CfJson $i ($Indent + 2)) }
        return "[`n" + ($parts -join ",`n") + "`n$pad]"
    }
    return (ConvertTo-CfJsonString ([string]$v))
}

function ConvertFrom-CfJsonText([string]$Text, [string]$What) {
    $p = @{}
    if ($script:HasDateKind) { $p['DateKind'] = 'String' }
    try { return ($Text | ConvertFrom-Json @p) } catch { throw "REFUSED: malformed JSON in '$What': $($_.Exception.Message)" }
}

function Read-CfJson([string]$File) { return (ConvertFrom-CfJsonText ([IO.File]::ReadAllText($File, $script:Utf8)) $File) }

function ConvertTo-CfName([string]$Kind, [string]$Value) {
    # Old name -> new name (NAMES section 3). A new name or an unknown value comes back unchanged (the caller refuses it).
    $m = $script:NameMap[$Kind]
    if ($null -eq $m) { throw "ERROR: unknown name kind '$Kind' (CardState, Phase, TicketState, Verdict, Receipt)." }
    if ($Value -and $m.ContainsKey($Value)) { return [string]$m[$Value] }
    return $Value
}

function Get-CfTState($t) { return (ConvertTo-CfName 'TicketState' ([string]$t['state'])) }
function Get-CfTPhase($t) { return (ConvertTo-CfName 'Phase' ([string]$t['phase'])) }

# ======================================================================================
# Card
# ======================================================================================
function ConvertFrom-CfFrontMatter([string]$Text, [string]$File) {
    $t = $Text.Replace("`r`n", "`n")
    if (-not $t.StartsWith("---`n")) { throw "REFUSED: '$File' has no front matter (--- ... ---)." }
    $end = $t.IndexOf("`n---", 4)
    if ($end -lt 0) { throw "REFUSED: '$File' front matter is not closed." }
    $h = @{}
    foreach ($line in $t.Substring(4, $end - 4).Split("`n")) {
        if ($line -match '^([A-Za-z_]+):\s*(.*)$') {
            $k = $Matches[1]; $v = ($Matches[2] -replace '\s+#.*$', '').Trim()
            if ($v.StartsWith('[')) {
                $close = $v.LastIndexOf(']')
                if ($close -lt 0) { throw "REFUSED: '$File' front matter '$k' list is not closed." }
                $h[$k] = @($v.Substring(1, $close - 1).Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ })
            }
            else { $h[$k] = $v }
        }
    }
    return $h
}

function Get-CfSection([string]$Text, [string]$Heading) {
    $lines = $Text.Replace("`r`n", "`n").Split("`n")
    $out = New-Object System.Collections.ArrayList; $in = $false
    foreach ($l in $lines) {
        if ($l -match '^##\s+(.+?)\s*$') { $in = ($Matches[1] -eq $Heading); continue }
        if ($in) { [void]$out.Add($l) }
    }
    return [string[]]$out.ToArray()
}

function Get-CfCard([string]$Root, [string]$Card) {
    if (-not $Card) { throw 'REFUSED: card name is required (NNN-slug).' }
    if ($Card -notmatch $script:CardRe) { throw "REFUSED: card name '$Card' is not NNN-slug." }
    $dir = Join-Path (Get-CfCfgPath $Root 'cards') $Card
    $file = Join-Path $dir 'CARD.md'
    if (-not [IO.File]::Exists($file)) { throw "REFUSED: card '$Card' not found ($(Get-CfCfgRel 'cards')/$Card/CARD.md)." }
    $text = [IO.File]::ReadAllText($file, $script:Utf8)
    $fm = ConvertFrom-CfFrontMatter $text $file
    if ($fm['card'] -and $fm['card'] -ne $Card) { throw "REFUSED: CARD.md says card '$($fm['card'])', folder is '$Card'." }
    $zones = @(); if ($null -ne $fm['zones']) { $zones = @($fm['zones']) }
    $prot = @(); if ($null -ne $fm['protected_paths']) { $prot = @($fm['protected_paths']) }
    return [pscustomobject]@{
        Name = $Card; Dir = $dir; File = $file; Text = $text; Front = $fm
        State = (ConvertTo-CfName 'CardState' ([string]$fm['state'])); StateRaw = [string]$fm['state']; Risk = [string]$fm['risk_class']
        Zones = $zones; Protected = $prot; Decisions = @(Get-CfSection $text 'Decisions')
    }
}

function Get-CfZoneMap([string]$Root, $Card) {
    if (@($Card.Zones).Count -eq 0) { throw "REFUSED: card '$($Card.Name)' has no zones." }
    $list = New-Object System.Collections.ArrayList
    foreach ($z in $Card.Zones) {
        $n = $z.Replace('\', '/').Trim().TrimEnd('/')
        $segs = $n.Split('/')
        if ($n.StartsWith('/') -or $n.Contains(':') -or @($segs | Where-Object { $_ -eq '..' -or $_ -eq '.' -or $_ -eq '' }).Count -gt 0) {
            throw "REFUSED: zone '$z' must be a plain relative path (no drive, no '..')."
        }
        if ($n -notmatch '^\d{4}-\d{2}/\d{2}_\d{2}-[^/]+/out/(.+)$') { throw "REFUSED: zone '$z' must be <YYYY-MM>/<DD_NN-task>/out/<target path> (a folder or one file; <task>/out/ itself is not a zone)." }
        $target = $Matches[1]
        if ($target -match '^_(m|s)(/|$)') { throw "REFUSED: zone '$z' is a part sub-zone (_m / _s); list the merged zone instead." }
        $zf = (Join-Path $Root $n.Replace('/', '\')); $tf = (Join-Path $Root $target.Replace('/', '\'))
        # a zone is a folder (Dir) or one file (File). The zone decides; when the zone does not exist yet the
        # live target decides; neither -> Missing (refused when the zone files are listed). File vs folder mismatch -> refused.
        $zk = if ([IO.Directory]::Exists($zf)) { 'Dir' } elseif ([IO.File]::Exists($zf)) { 'File' } else { '' }
        $tk = if ([IO.Directory]::Exists($tf)) { 'Dir' } elseif ([IO.File]::Exists($tf)) { 'File' } else { '' }
        if ($zk -and $tk -and $zk -ne $tk) {
            throw "REFUSED: zone '$n' is a $(if ($zk -eq 'File') { 'file' } else { 'folder' }) but the live target '$target' is a $(if ($tk -eq 'File') { 'file' } else { 'folder' })."
        }
        $kind = if ($zk) { $zk } elseif ($tk) { $tk } else { 'Missing' }
        [void]$list.Add([pscustomobject]@{ Zone = $n; ZoneFull = $zf; Target = $target; TargetFull = $tf; Kind = $kind })
    }
    for ($i = 0; $i -lt $list.Count; $i++) {
        for ($j = $i + 1; $j -lt $list.Count; $j++) {
            foreach ($k in 'Zone', 'Target') {
                $a = $list[$i].$k; $b = $list[$j].$k
                if ($a -ieq $b -or $a.StartsWith($b + '/', [StringComparison]::OrdinalIgnoreCase) -or $b.StartsWith($a + '/', [StringComparison]::OrdinalIgnoreCase)) {
                    throw "REFUSED: zones overlap ($k '$a' / '$b')."
                }
            }
        }
    }
    foreach ($m in $list) {
        foreach ($start in $m.ZoneFull, $m.TargetFull) {
            $d = $start
            while ($d.Length -gt $Root.Length) {
                if ((Test-Path -LiteralPath $d) -and ((Get-Item -LiteralPath $d -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
                    throw "REFUSED: '$d' is a junction / symlink (a zone or target path must not pass through a link)."
                }
                $d = [IO.Path]::GetDirectoryName($d)
            }
        }
    }
    return $list.ToArray()
}

function Get-CfMapFiles($m, [string]$Full) {
    # files of one zone map entry on one side (zone or live target): a folder zone lists the folder, a file zone the one file
    if ($m.Kind -eq 'File') { return @(Get-PathList -Item $Full) }
    return @(Get-PathList -Under $Full)
}

function Join-CfRel([string]$Base, [string]$Rel) { if ($Rel) { return "$Base/$Rel" } return $Base }

function Get-CfZoneEntries($Map) {
    $out = New-Object System.Collections.ArrayList
    foreach ($m in $Map) {
        if ($m.Kind -eq 'Missing') { throw "REFUSED: zone folder missing: $($m.Zone) (neither a folder nor a file exists at the zone or at its live target)" }
        if ($m.Kind -eq 'Dir' -and -not [IO.Directory]::Exists($m.ZoneFull)) { throw "REFUSED: zone folder missing: $($m.Zone)" }
        # a file zone whose file is gone while the live target exists lists nothing -> the target file shows as removed
        foreach ($f in @(Get-CfMapFiles $m $m.ZoneFull)) {
            [void]$out.Add([pscustomobject]@{ Path = (Join-CfRel $m.Target $f.Rel); Hash = (Get-CfFileHash $f.Full); ZoneRel = (Join-CfRel $m.Zone $f.Rel); Full = $f.Full; Time = $f.Time })
        }
    }
    return $out.ToArray()
}

function Get-CfTargetEntries($Map) {
    $out = New-Object System.Collections.ArrayList
    foreach ($m in $Map) {
        foreach ($f in @(Get-CfMapFiles $m $m.TargetFull)) {
            [void]$out.Add([pscustomobject]@{ Path = (Join-CfRel $m.Target $f.Rel); Hash = (Get-CfFileHash $f.Full); Full = $f.Full; Time = $f.Time })
        }
    }
    return $out.ToArray()
}

function Format-CfManifestLines($Entries) { return [string[]]@($Entries | ForEach-Object { '{0}  {1}' -f $_.Hash, $_.Path }) }
function Join-CfManifestText($Lines) { $l = @($Lines | Where-Object { $null -ne $_ }); if ($l.Count -eq 0) { return '' } return (($l -join "`n") + "`n") }

function Read-CfBaseline($Card) {
    $f = Join-Path $Card.Dir 'baseline.manifest'
    if (-not [IO.File]::Exists($f)) {
        throw "REFUSED: $(Get-CfCfgRel 'cards')/$($Card.Name)/baseline.manifest missing - run 'manifest $($Card.Name) -Baseline -As BUILD' at BUILD start (a missing baseline is never treated as empty)."
    }
    $out = New-Object System.Collections.ArrayList; $no = 0
    foreach ($l in [IO.File]::ReadAllText($f, $script:Utf8).Replace("`r`n", "`n").Split("`n")) {
        $no++
        if ($l -eq '') { continue }
        if ($l -notmatch '^([0-9a-f]{64})  (.+)$') { throw "REFUSED: baseline.manifest line $no is malformed." }
        [void]$out.Add([pscustomobject]@{ Path = $Matches[2]; Hash = $Matches[1] })
    }
    return $out.ToArray()
}

function Get-CfManifest([string]$Root, $Card) {
    $map = Get-CfZoneMap $Root $Card
    $base = @(Read-CfBaseline $Card)
    $zone = @(Get-CfZoneEntries $map)
    $changes = @(Get-PathList -Old $base -New $zone)
    $lines = @(Format-CfManifestLines $changes)
    $text = Join-CfManifestText $lines
    return [pscustomobject]@{ Map = $map; Baseline = $base; Zone = $zone; Changes = $changes; Lines = $lines; Text = $text; Digest = (Get-CfSha256Text $text) }
}

# ---------------- protected / shared paths (config: protected_paths, shared_paths, shared_paths_except) ----------------
# Match rules, case-insensitive, '\' = '/':
#   entry ending in '/'            -> a folder: the path starts with it, or the folder appears anywhere in the path
#                                     (".claude/", "hooks/", ".github/workflows/" are caught below any folder);
#   entry without '/'              -> a file name: the last segment equals it (e.g. AGENTS.md anywhere);
#   entry with '/' not at the end  -> one file: the whole path equals it.
function Test-CfPathInList([string]$Path, [string[]]$Entries) {
    $p = $Path.Replace('\', '/').ToLowerInvariant().TrimStart('/')
    $segs = $p.Split('/')
    $leaf = $segs[$segs.Length - 1]
    foreach ($e in $Entries) {
        $n = ([string]$e).Replace('\', '/').Trim().ToLowerInvariant().TrimStart('/')
        if (-not $n) { continue }
        if ($n.EndsWith('/')) { if ($p.StartsWith($n) -or $p.Contains('/' + $n)) { return $true } }
        elseif (-not $n.Contains('/')) { if ($leaf -eq $n) { return $true } }
        elseif ($p -eq $n) { return $true }
    }
    return $false
}

function Test-CfProtected([string]$Path) {
    $segs = $Path.Replace('\', '/').Split('/')
    if ($segs -contains '..') { return $true }
    return (Test-CfPathInList $Path (Get-CfCfgList 'protected_paths'))
}

function Test-CfShared([string]$Path) {
    if (Test-CfProtected $Path) { return $true }
    if (Test-CfPathInList $Path (Get-CfCfgList 'shared_paths_except')) { return $false }
    return (Test-CfPathInList $Path (Get-CfCfgList 'shared_paths'))
}

function Get-CfCoveringEntry([string]$Path, [string[]]$Entries) {
    $p = $Path.Replace('\', '/')
    foreach ($e in $Entries) {
        $n = $e.Replace('\', '/').Trim()
        if (-not $n -or $n.Split('/') -contains '..') { continue }
        if ($n.EndsWith('/')) { if ($p.StartsWith($n, [StringComparison]::OrdinalIgnoreCase)) { return $e } }
        elseif ($p -ieq $n) { return $e }
    }
    return $null
}

function Test-CfApproval([string]$Entry, [string[]]$Decisions) {
    # The owner's typed approval has ONE fixed form in Decisions (strict, whole line; <name> = config approval_name):
    #   - <name> <dd/MM HH:mm>: "<the owner's sentence, 3+ chars>" -> approves <path>[, <path>...]
    # (arrow '->' or U+2192; quotes "" or U+201C/U+201D). <path> must equal the protected_paths entry (case, \ or / ignored).
    $n = $Entry.Replace('\', '/').Trim()
    $q1 = '["' + [char]0x201C + ']'; $q2 = '["' + [char]0x201D + ']'; $nq = '[^"' + [char]0x201C + [char]0x201D + ']'
    $re = '^\s*(?:-\s+)?' + [regex]::Escape((Get-CfApprovalName)) + '\s+\d{2}/\d{2}\s+\d{2}:\d{2}:\s+' + $q1 + $nq + '{3,}' + $q2 + '\s+(?:->|' + [char]0x2192 + ')\s+approves\s+(.+?)\s*$'
    foreach ($l in $Decisions) {
        $m = [regex]::Match($l, $re)
        if (-not $m.Success) { continue }
        foreach ($p in $m.Groups[1].Value.Split(',')) { if ($p.Trim().Replace('\', '/') -ieq $n) { return $true } }
    }
    return $false
}

function Test-CfWaiver([string[]]$Decisions) {
    # The owner may waive the REVIEW ticket of a card with one whole line in Decisions (same quote / arrow rules):
    #   - <name> <dd/MM HH:mm>: "<the owner's sentence, 3+ chars>" -> waives review
    # Only the line form is checked here; Test-CfRelease decides whether the card may use it (no shared / protected change).
    $q1 = '["' + [char]0x201C + ']'; $q2 = '["' + [char]0x201D + ']'; $nq = '[^"' + [char]0x201C + [char]0x201D + ']'
    $re = '^\s*(?:-\s+)?' + [regex]::Escape((Get-CfApprovalName)) + '\s+\d{2}/\d{2}\s+\d{2}:\d{2}:\s+' + $q1 + $nq + '{3,}' + $q2 + '\s+(?:->|' + [char]0x2192 + ')\s+waives\s+review\s*$'
    foreach ($l in $Decisions) { if ([regex]::IsMatch($l, $re)) { return $true } }
    return $false
}

function Test-CfWaivedNote($t) {
    # the LAST history entry of the ticket has a note starting with "review waived".
    $hh = @($t['history']); if ($hh.Count -eq 0) { return $false }
    $he = $hh[$hh.Count - 1]
    $hn = if ($he -is [System.Collections.IDictionary]) { [string]$he['note'] } else { [string](Get-CfProp $he 'note') }
    return $hn -match '^\s*review waived\b'
}

# ======================================================================================
# Tickets
# ======================================================================================
function ConvertTo-CfTicket($d, [string]$File) {
    $t = [ordered]@{}
    foreach ($k in 'card', 'n', 'from', 'to', 'phase', 'manifest_digest', 'state', 'agent', 'history') {
        if ($null -eq $d.PSObject.Properties[$k]) { throw "REFUSED: ticket '$File' has no field '$k'." }
    }
    $t['card'] = [string]$d.card
    $t['n'] = [int]$d.n
    $t['from'] = [string]$d.from
    $t['to'] = [string]$d.to
    $t['phase'] = [string]$d.phase
    $t['manifest_digest'] = [string]$d.manifest_digest
    if ($null -ne $d.PSObject.Properties['manifest']) { $t['manifest'] = [string[]]@($d.manifest | ForEach-Object { [string]$_ }) }
    $t['state'] = [string]$d.state
    $t['agent'] = [string]$d.agent
    $h = New-Object System.Collections.ArrayList
    foreach ($e in @($d.history)) {
        if ($null -eq $e) { continue }
        [void]$h.Add([ordered]@{ at = (ConvertTo-CfAt (Get-CfProp $e 'at')); by = [string](Get-CfProp $e 'by'); state = [string](Get-CfProp $e 'state'); note = [string](Get-CfProp $e 'note') })
    }
    $t['history'] = $h.ToArray()
    if ($script:States -notcontains (ConvertTo-CfName 'TicketState' $t['state'])) { throw "REFUSED: ticket '$File' has unknown state '$($t['state'])'." }
    if ($script:Roles -notcontains $t['from'] -or $script:Roles -notcontains $t['to']) { throw "REFUSED: ticket '$File' has an unknown role in from / to." }
    if (@($t['history']).Count -eq 0) { throw "REFUSED: ticket '$File' has an empty history." }
    return $t
}

function Get-CfTickets($Card) {
    $hd = Join-Path $Card.Dir 'handoff'
    $list = New-Object 'System.Collections.Generic.List[object]'
    $seenN = @{}
    foreach ($name in @(Get-PathList -In $hd)) {
        # every file in handoff/ must be a ticket H-NN.json - a misnamed one would hide an open ticket.
        if ($name -notmatch '^H-(\d{2,})\.json$') { throw "REFUSED: handoff/$name is not a ticket name (H-NN.json, at least two digits) - LEAD renames or removes it by hand." }
        $num = [int]$Matches[1]
        if ($seenN.ContainsKey($num)) { throw "REFUSED: handoff/ holds two tickets with n=$num ($($seenN[$num]), $name)." }
        $seenN[$num] = $name
        $file = Join-Path $hd $name
        $t = ConvertTo-CfTicket (Read-CfJson $file) $file
        if ($t['n'] -ne $num) { throw "REFUSED: ticket '$name' says n=$($t['n'])." }
        if ($t['card'] -ne $Card.Name) { throw "REFUSED: ticket '$name' belongs to card '$($t['card'])'." }
        $t['_file'] = $file
        [void]$list.Add($t)
    }
    $list.Sort([Comparison[object]] { param($a, $b) ([int]$a['n']).CompareTo([int]$b['n']) })
    $arr = $list.ToArray()
    $open = @($arr | Where-Object { $script:OpenStates -contains (Get-CfTState $_) })
    if ($open.Count -gt 1) { throw "REFUSED: card '$($Card.Name)' has $($open.Count) open tickets (only one allowed) - LEAD must fix by hand." }
    return $arr
}

function Get-CfOpen($Tickets) {
    foreach ($t in $Tickets) { if ($script:OpenStates -contains (Get-CfTState $t)) { return $t } }
    return $null
}

function Get-CfTicketName($t) { return ('H-{0:D2}' -f [int]$t['n']) }

function Save-CfTicket($t, [switch]$New) {
    $file = $t['_file']
    $o = [ordered]@{}
    foreach ($k in @($t.Keys)) { if ($k -ne '_file') { $o[$k] = $t[$k] } }
    $text = (ConvertTo-CfJson $o) + "`n"
    $back = ConvertTo-CfTicket (ConvertFrom-CfJsonText $text $file) $file   # validates before anything is written
    if ($back['state'] -ne $t['state'] -or $back['n'] -ne $t['n']) { throw 'ERROR: ticket serialisation check failed.' }
    Write-CfTextFile $file $text -New:$New
    $re = ConvertTo-CfTicket (Read-CfJson $file) $file
    if ($re['state'] -ne $t['state'] -or @($re['history']).Count -ne @($t['history']).Count) { throw "ERROR: re-read of '$file' does not match." }
}

function Get-CfVerdict($t) {
    $h = @($t['history'] | Where-Object { $_['state'] -eq 'DONE' })
    if ($h.Count -eq 0) { return '' }
    $note = [string]$h[$h.Count - 1]['note']
    if ($note -cmatch $script:WordRe) { return (ConvertTo-CfName 'Verdict' $Matches[1]) }
    return ''
}

function Read-CfSessionMap([string]$MapFile) {
    if (-not $MapFile) {
        $rel = [string](Get-CfCfg 'session_map_file')
        if (-not $rel -or -not $script:CfRoot) { return $null }
        $rel = $rel.Replace('\', '/').Trim().Trim('/')
        if ($rel.Contains(':') -or @($rel.Split('/') | Where-Object { $_ -eq '..' }).Count) { Write-Warning "session_map_file '$rel' must be a relative path inside the project - paste the bell by hand."; return $null }
        $MapFile = Join-Path $script:CfRoot $rel.Replace('/', '\')
    }
    if (-not [IO.File]::Exists($MapFile)) { return $null }
    try { return (Read-CfJson $MapFile) } catch { Write-Warning "session map unreadable ($MapFile) - paste the bell by hand."; return $null }
}

function Get-CfBell($t, [string]$Session, [datetime]$Now) {
    $n = Get-CfTicketName $t; $c = $t['card']
    return @(
        "[TICKET $c $n] $($t['from']) $($script:Arrow) $($t['to']) $($script:Dot) $(Get-CfTPhase $t)",
        "Card: $(Get-CfCfgRel 'cards')/$c/CARD.md (Takeover)",
        "Ticket: $(Get-CfCfgRel 'cards')/$c/handoff/$n.json $($script:Dot) manifest $(Get-CfShort $t['manifest_digest'])",
        "Sent $(Get-CfShortTime $Now) by $Session"
    )
}

function Get-CfLogFile($Card) { return (Join-Path $Card.Dir 'log.md') }

function Get-CfCheckpointLine([datetime]$Now, [string]$Who, [string]$Done, [string]$Doing, [string]$Next, [string]$Check) {
    $d = $script:Dot
    return "- $(Get-CfShortTime $Now) $Who $d done: $Done $d doing: $Doing $d next: $Next $d check: $Check"
}

# ======================================================================================
# Commands
# ======================================================================================
function Invoke-CfTicket {
    param([string]$Root, [string]$Action, [string]$Card, [string]$As, [string]$To, [string]$Phase, [string]$Note,
        [string]$Agent, [string]$Session, [switch]$Freeze, [string]$SessionMap)
    $acts = @('send', 'accept', 'done', 'hold', 'takeover')
    if (-not $Action -or $acts -notcontains $Action.ToLowerInvariant()) { throw "REFUSED: action must be one of $($acts -join ' | ')." }
    $Action = $Action.ToLowerInvariant()
    $As = Assert-CfRole $As
    $c = Get-CfCard $Root $Card
    if ($script:Closed -contains $c.State) { throw "REFUSED: card '$Card' is $($c.State)." }
    $Note = ConvertTo-CfOneLine $Note; $Agent = ConvertTo-CfOneLine $Agent; $Session = ConvertTo-CfOneLine $Session
    Assert-CfCleanText @($Note, $Agent, $Session)
    $ts = @(Get-CfTickets $c)
    $open = Get-CfOpen $ts
    $now = Get-Date
    $map = $null

    if ($Action -eq 'send') {
        if ($open) { throw "REFUSED: $(Get-CfTicketName $open) is still open ($($open['state']), turn $($open['to'])) - one open ticket per card; the holder closes it first (ticket done)." }
        if ($ts.Count -gt 0) {
            $last = $ts[$ts.Count - 1]
            if ($As -ne $last['to'] -and $As -ne 'LEAD') { throw "REFUSED: not $As's turn to send (last ticket $(Get-CfTicketName $last) went to $($last['to']); LEAD may always send)." }
        }
        elseif ($As -ne 'LEAD') { throw 'REFUSED: the first ticket of a card is sent by LEAD.' }
        $To = Assert-CfRole $To '-To'
        if ($To -eq $As) { throw 'REFUSED: -To must be another role.' }
        $pn = ''; if ($Phase) { $pn = ConvertTo-CfName 'Phase' $Phase.ToUpperInvariant() }
        if ($script:Phases -notcontains $pn) { throw "REFUSED: -Phase must be one of $($script:Phases -join ', ') (old names P1, GATE, FIXES, VERIFY are still read)." }
        $Phase = $pn
        $doFreeze = $Freeze -or $To -eq 'REVIEW'
        $digest = ''; $lines = $null
        if ($doFreeze) { $m = Get-CfManifest $Root $c; $digest = $m.Digest; $lines = $m.Lines }
        $num = 1; if ($ts.Count -gt 0) { $num = [int]$ts[$ts.Count - 1]['n'] + 1 }
        $hd = Join-Path $c.Dir 'handoff'
        if (-not [IO.Directory]::Exists($hd)) { [void][IO.Directory]::CreateDirectory($hd) }
        $t = [ordered]@{ card = $c.Name; n = $num; from = $As; to = $To; phase = $Phase; manifest_digest = $digest }
        if ($doFreeze) { $t['manifest'] = $lines }
        $t['state'] = 'SENT'; $t['agent'] = $Agent
        $t['history'] = @([ordered]@{ at = (Get-CfNowText $now); by = $As; state = 'SENT'; note = $Note })
        $t['_file'] = Join-Path $hd ('H-{0:D2}.json' -f $num)
        Save-CfTicket $t -New
        $map = Read-CfSessionMap $SessionMap
        if (-not $Session) { $Session = $As; $me = Get-CfProp $map $As; if ($me -and (Get-CfProp $me 'title')) { $Session = [string](Get-CfProp $me 'title') } }
        Write-Output "OK: $(Get-CfTicketName $t) written ($As $($script:Arrow) $To, $Phase, SENT$(if ($doFreeze) { ', manifest ' + (Get-CfShort $digest) + ', ' + @($lines).Count + ' line(s)' }))."
        Write-Output ''
        Get-CfBell $t $Session $now | Write-Output
        Write-Output ''
        $rcv = Get-CfProp $map $To
        if ($rcv -and (Get-CfProp $rcv 'id')) { Write-Output "Ring (local map, not stored): $([string](Get-CfProp $rcv 'title')) $([string](Get-CfProp $rcv 'id'))" }
        else { Write-Output "Ring: no local session map entry for $To - paste the 4 bell lines to that session." }
    }
    else {
        if (-not $open) { throw "REFUSED: no open ticket on card '$Card'." }
        $name = Get-CfTicketName $open
        # a REVIEW ticket whose frozen manifest no longer matches the zone can be closed with a note starting OUTDATED
        # (old: STALE; no verdict) by REVIEW, or by LEAD as fallback when REVIEW is gone; then the normal next-ticket rule applies.
        $isStale = $Action -eq 'done' -and $open['to'] -eq 'REVIEW' -and $Note -cmatch '^\s*(STALE|OUTDATED)(?![A-Za-z0-9_\-])'
        if ($As -ne $open['to'] -and -not ($isStale -and $As -eq 'LEAD')) { throw "REFUSED: only the receiver ($($open['to'])) changes $name; $As cannot $Action it." }
        $old = Get-CfTState $open
        $new = ''
        $staleText = ''
        switch ($Action) {
            'accept' { if (@('SENT', 'ON-HOLD', 'TAKEN-OVER') -notcontains $old) { throw "REFUSED: $name is $old; accept needs SENT, ON-HOLD or TAKEN-OVER." }; $new = 'ACCEPTED' }
            'done' {
                if ($isStale) {
                    # OUTDATED close (no verdict) - only when the current manifest really differs from the frozen one.
                    # Also from SENT / ON-HOLD (an OUTDATED ticket need not be accepted first).
                    if (@('SENT', 'ACCEPTED', 'ON-HOLD', 'TAKEN-OVER') -notcontains $old) { throw "REFUSED: $name is $old; an OUTDATED close needs SENT, ACCEPTED, ON-HOLD or TAKEN-OVER." }
                    $m = Get-CfManifest $Root $c
                    if ($m.Digest -eq $open['manifest_digest']) { throw "REFUSED: $name is not OUTDATED - the current manifest equals the frozen $(Get-CfShort $open['manifest_digest']); REVIEW closes with -Note starting PASS, FAIL or FIX-VERIFIED." }
                    $staleText = "closed OUTDATED at $(Get-CfShort $open['manifest_digest']) (current $(Get-CfShort $m.Digest))"
                }
                else {
                    if (@('ACCEPTED', 'TAKEN-OVER') -notcontains $old) { throw "REFUSED: $name is $old; accept it first (done needs ACCEPTED)." }
                    if ($open['to'] -eq 'REVIEW') {
                        $v = ''; if ($Note -cmatch $script:WordRe) { $v = ConvertTo-CfName 'Verdict' $Matches[1] }
                        if ($script:Verdicts -notcontains $v) { throw "REFUSED: REVIEW closes with -Note starting PASS, FAIL or FIX-VERIFIED (old NG / FIXES_VERIFIED are read too; OUTDATED when the zone changed after the freeze)." }
                        $m = Get-CfManifest $Root $c
                        if ($m.Digest -ne $open['manifest_digest']) { throw "REFUSED: OUTDATED review - current manifest $(Get-CfShort $m.Digest) differs from the frozen $(Get-CfShort $open['manifest_digest']) in $name; close it with -Note 'OUTDATED ...' (no verdict), then send a new frozen ticket." }
                    }
                }
                $new = 'DONE'
            }
            'hold' { if (@('SENT', 'ACCEPTED', 'TAKEN-OVER') -notcontains $old) { throw "REFUSED: $name is $old; hold needs SENT, ACCEPTED or TAKEN-OVER." }; if (-not $Note) { throw 'REFUSED: hold needs -Note (why).' }; $new = 'ON-HOLD' }
            'takeover' { if (@('SENT', 'ACCEPTED', 'ON-HOLD') -notcontains $old) { throw "REFUSED: $name is $old; takeover needs SENT, ACCEPTED or ON-HOLD." }; if (-not $Session) { throw 'REFUSED: takeover needs -Session <new session title>.' }; $new = 'TAKEN-OVER' }
        }
        $digestNow = ''
        if ($Action -eq 'takeover') { try { $digestNow = (Get-CfManifest $Root $c).Digest } catch { $digestNow = $open['manifest_digest'] } }
        $n2 = $Note; if ($Action -eq 'takeover' -and -not $n2) { $n2 = "$Session took over" }
        # write the new name: an old first word (NG, FIXES_VERIFIED, STALE) of a REVIEW close becomes the new one (FAIL, FIX-VERIFIED, OUTDATED)
        if ($Action -eq 'done' -and $open['to'] -eq 'REVIEW' -and $n2 -cmatch $script:WordRe) {
            $w = $Matches[1]; $nw = ConvertTo-CfName 'Verdict' $w
            if ($nw -cne $w) { $i = $n2.IndexOf($w); $n2 = $n2.Substring(0, $i) + $nw + $n2.Substring($i + $w.Length) }
        }
        if ($staleText) { $n2 = "$n2 - $staleText" }
        $open['history'] = @($open['history']) + @([ordered]@{ at = (Get-CfNowText $now); by = $As; state = $new; note = $n2 })
        $open['state'] = $new
        Save-CfTicket $open
        Write-Output "OK: $name $old $($script:Arrow) $new ($As)$(if ($staleText) { ', ' + $staleText + ' - no verdict' })."
        if ($staleText) {
            Add-CfLine (Get-CfLogFile $c) "- $(Get-CfShortTime $now) $As $name $staleText (no verdict)"
            Write-Output "log.md: OUTDATED line appended. Next: LEAD (or $As) sends a new ticket, e.g. ticket send -To REVIEW -Freeze at the current manifest."
        }
        if ($Action -eq 'takeover') {
            $dg = $digestNow; if (-not $dg) { $dg = $script:Dash }
            Add-CfLine (Get-CfLogFile $c) "- $(Get-CfShortTime $now) $Session as $As took over $($c.Name) at $dg"
            Write-Output "log.md: takeover line appended."
        }
    }
    Invoke-CfBoardSafe $Root
}

function Invoke-CfCheckpoint {
    param([string]$Root, [string]$Card, [string]$As, [string]$Done, [string]$Doing, [string]$Next, [string]$Check)
    $As = Assert-CfRole $As
    $vals = [ordered]@{ Done = $Done; Doing = $Doing; Next = $Next; Check = $Check }
    foreach ($k in @($vals.Keys)) {
        $v = ConvertTo-CfOneLine $vals[$k]
        if (-not $v) { throw "REFUSED: -$k is required (use '-' when there is nothing)." }
        $vals[$k] = $v
    }
    Assert-CfCleanText @($vals.Values)
    $c = Get-CfCard $Root $Card
    $ts = @(Get-CfTickets $c)
    $open = Get-CfOpen $ts
    if ($open) {
        if ($As -ne $open['to']) { throw "REFUSED: turn holder is $($open['to']) ($(Get-CfTicketName $open) $($open['state'])); $As cannot write a checkpoint now." }
    }
    elseif ($As -ne 'LEAD') { throw "REFUSED: no open ticket on '$Card' - only LEAD writes a checkpoint now (card start / close)." }
    $line = Get-CfCheckpointLine (Get-Date) $As $vals['Done'] $vals['Doing'] $vals['Next'] $vals['Check']
    Add-CfLine (Get-CfLogFile $c) $line
    Write-Output "OK: log.md + 1 line"
    Write-Output $line
    Invoke-CfBoardSafe $Root
}

function Invoke-CfManifest {
    param([string]$Root, [string]$Card, [switch]$Baseline, [string]$As)
    $c = Get-CfCard $Root $Card
    if ($Baseline) {
        $As = Assert-CfRole $As
        $open = Get-CfOpen @(Get-CfTickets $c)
        if (-not $open -or $open['to'] -ne $As) { throw "REFUSED: baseline is written by the turn holder at BUILD start (open ticket holder: $(if ($open) { $open['to'] } else { 'none' }))." }
        $f = Join-Path $c.Dir 'baseline.manifest'
        if ([IO.File]::Exists($f)) { throw "REFUSED: baseline.manifest exists and is write-once (Q4); a new baseline needs a LEAD Decision line and is done by hand." }
        $map = Get-CfZoneMap $Root $c
        $live = @(Get-PathList -Old @() -New @(Get-CfTargetEntries $map))
        $lines = @(Format-CfManifestLines $live)
        Write-CfTextFile $f (Join-CfManifestText $lines) -New
        Write-Output "OK: baseline.manifest written ($($lines.Count) live target file(s): $(($map | ForEach-Object { $_.Target }) -join ', '))."
        return
    }
    $m = Get-CfManifest $Root $c
    $m.Lines | Write-Output
    Write-Output '---'
    Write-Output "digest: $($m.Digest)"
    $a = @($m.Changes | Where-Object { $_.Change -eq 'added' }).Count
    $ch = @($m.Changes | Where-Object { $_.Change -eq 'changed' }).Count
    $r = @($m.Changes | Where-Object { $_.Change -eq 'removed' }).Count
    Write-Output "entries: $($m.Lines.Count) (added $a, changed $ch, removed $r) $($script:Dot) zone files: $($m.Zone.Count) $($script:Dot) zones: $(($m.Map | ForEach-Object { $_.Zone + ' ' + $script:Arrow + ' ' + $_.Target }) -join '; ')"
    $p = @($m.Changes | Where-Object { Test-CfProtected $_.Path } | ForEach-Object { "$($_.Path) ($($_.Change))" })
    Write-Output "protected: $(if ($p.Count) { $p -join ', ' } else { 'none' })"
}

function Read-CfGate($Card) {
    $f = Join-Path $Card.Dir 'receipts\gate.json'
    if (-not [IO.File]::Exists($f)) { return $null }
    return (Read-CfJson $f)
}

function Find-CfSecrets($Zone) {
    $hits = New-Object System.Collections.ArrayList; $skipped = New-Object System.Collections.ArrayList
    foreach ($z in $Zone) {
        $bytes = [IO.File]::ReadAllBytes($z.Full)
        $text = $null
        if ($bytes.Length -ge 2 -and $bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE) { $text = [Text.Encoding]::Unicode.GetString($bytes, 2, $bytes.Length - 2) }
        elseif ($bytes.Length -ge 2 -and $bytes[0] -eq 0xFE -and $bytes[1] -eq 0xFF) { $text = [Text.Encoding]::BigEndianUnicode.GetString($bytes, 2, $bytes.Length - 2) }
        else {
            $lim = [Math]::Min($bytes.Length, 8000); $bin = $false
            for ($i = 0; $i -lt $lim; $i++) { if ($bytes[$i] -eq 0) { $bin = $true; break } }
            if ($bin) { [void]$skipped.Add($z.ZoneRel); continue }
            $text = $script:Utf8.GetString($bytes)
        }
        foreach ($h in @(Find-CfSecretInText $text)) { [void]$hits.Add([ordered]@{ file = $z.ZoneRel; line = [int]$h.Line; rule = $h.Rule }) }
    }
    return [pscustomobject]@{ Hits = $hits.ToArray(); Skipped = [string[]]$skipped.ToArray() }
}

function Resolve-CfHost([string]$Name) {
    switch ($Name.ToLowerInvariant()) {
        'ps5' { $p = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'; if ([IO.File]::Exists($p)) { return $p }; return $null }
        'ps7' {
            $c = Get-Command 'pwsh.exe' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($c) { return $c.Source }
            $p = Join-Path $env:ProgramFiles 'PowerShell\7\pwsh.exe'; if ([IO.File]::Exists($p)) { return $p }; return $null
        }
        'current' { return (Get-Process -Id $PID).Path }
    }
    throw "REFUSED: unknown host '$Name' (ps5, ps7, current)."
}

function Get-CfHostKind([string]$h) {
    # 'current' (tests only) counts as the edition that runs this script; ps5 / ps7 as named.
    if ($h -eq 'current') { if ($PSVersionTable.PSVersion.Major -ge 7) { return 'ps7' } return 'ps5' }
    return $h
}

function Get-CfGateHosts {
    # config gate.hosts (ps5 / ps7 / current), else ps7 only: the hosts gate runs on by default AND the hosts every
    # test file must pass on (see Get-CfTestHosts).
    $h = @(@(Get-CfProp (Get-CfCfg 'gate') 'hosts') | Where-Object { $_ } | ForEach-Object { ([string]$_).ToLowerInvariant() })
    if ($h.Count -eq 0) { $h = @('ps7') }
    $bad = @($h | Where-Object { @('ps5', 'ps7', 'current') -notcontains $_ })
    if ($bad.Count) { throw "REFUSED: $($script:CfgRel): gate.hosts may hold only ps5, ps7, current (got $($bad -join ', '))." }
    return $h
}

function Get-CfTestHosts($Entry) {
    # Hosts a test file (a zone entry: Path = live target path, Full = zone file) must pass on: the hosts of config
    # gate.hosts (default ps7), except ps7 only when its live target lies under config paths.scripts (the bundle's
    # own process scripts, PowerShell 7 only) AND one of its first 20 lines is '#Requires -Version 7' (or higher).
    # Any other test keeps every gate.hosts host even with that line (a deliverable that must run on 5.1 cannot drop
    # its ps5 run with one line).
    $need = @(Get-CfGateHosts | ForEach-Object { Get-CfHostKind $_ } | Sort-Object -Unique)
    $pre = (Get-CfCfgRel 'scripts') + '/'
    if (-not ([string]$Entry.Path).Replace('\', '/').StartsWith($pre, [StringComparison]::OrdinalIgnoreCase)) { return $need }
    # StreamReader + finally: the file must be closed before the test runs.
    $sr = New-Object IO.StreamReader($Entry.Full, $script:Utf8, $true)
    try {
        for ($n = 0; $n -lt 20; $n++) {
            $l = $sr.ReadLine(); if ($null -eq $l) { break }
            if ($l -match '^\s*#Requires\s+-Version\s+([0-9]+)' -and [int]$Matches[1] -ge 7) { return @('ps7') }
        }
    }
    finally { $sr.Dispose() }
    return $need
}

function Invoke-CfGate {
    param([string]$Root, [string]$Card, [string]$As, [string[]]$Hosts)
    if (@($Hosts).Count -eq 0) { $Hosts = @(Get-CfGateHosts) }   # default hosts: config gate.hosts, else ps7
    $c = Get-CfCard $Root $Card
    if ($script:Closed -contains $c.State) { throw "REFUSED: card '$Card' is $($c.State)." }
    $by = ''; if ($As) { $by = Assert-CfRole $As }
    if (-not $Hosts -or $Hosts.Count -eq 0) { $Hosts = @('ps5', 'ps7') }
    $Hosts = @($Hosts | ForEach-Object { $_.ToLowerInvariant() })
    $m = Get-CfManifest $Root $c
    $reasons = New-Object System.Collections.ArrayList
    $sec = Find-CfSecrets $m.Zone
    if (@($sec.Hits).Count -gt 0) { [void]$reasons.Add("secret scan: $(@($sec.Hits).Count) finding(s)") }
    $testFiles = @($m.Zone | Where-Object { $_.Path -like '*.Tests.ps1' })
    if ($testFiles.Count -eq 0) { [void]$reasons.Add('no *.Tests.ps1 in the zones (a card without tests cannot pass)') }
    $results = New-Object System.Collections.ArrayList
    $ErrorActionPreference = 'Continue'   # native stderr + 2>&1 must not become a terminating error
    foreach ($h in $Hosts) {
        $exe = Resolve-CfHost $h
        if (-not $exe) { [void]$reasons.Add("host $h not installed"); [void]$results.Add([ordered]@{ file = '-'; host = $h; version = ''; exit = -1; result = 'MISSING' }); continue }
        $ver = (& $exe -NoProfile -NonInteractive -Command '$PSVersionTable.PSVersion.ToString()' 2>$null | Select-Object -First 1)
        foreach ($tf in $testFiles) {
            if (@(Get-CfTestHosts $tf) -notcontains (Get-CfHostKind $h)) { continue }   # a ps7-only process-script test runs on ps7 only
            $out = @(& $exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $tf.Full 2>&1 | ForEach-Object { [string]$_ })
            $code = $LASTEXITCODE
            $res = if ($code -eq 0) { 'PASS' } else { 'FAIL' }
            [void]$results.Add([ordered]@{ file = $tf.ZoneRel; host = $h; version = [string]$ver; exit = [int]$code; result = $res })
            if ($res -ne 'PASS') {
                [void]$reasons.Add("test FAIL: $($tf.ZoneRel) on $h (exit $code)")
                Write-Output "  -- last lines of $($tf.ZoneRel) on $($h):"
                $out | Select-Object -Last 8 | ForEach-Object { Write-Output "     $_" }
            }
        }
    }
    $m2 = Get-CfManifest $Root $c
    if ($m2.Digest -ne $m.Digest) { [void]$reasons.Add('zone changed during the gate run') }
    # PASS only when every test file ran on every host it needs: config gate.hosts, or ps7 only for a test file whose
    # target is under config paths.scripts and that declares '#Requires -Version 7' (Get-CfTestHosts). Fewer -> PARTIAL.
    $kinds = @($Hosts | ForEach-Object { Get-CfHostKind $_ })
    $miss = @($testFiles | ForEach-Object { $f = $_; Get-CfTestHosts $f | Where-Object { $kinds -notcontains $_ } | ForEach-Object { "$($f.ZoneRel) on $_" } })
    $result = if ($reasons.Count -gt 0) { 'FAIL' } elseif ($miss.Count -gt 0) { 'PARTIAL' } else { 'PASS' }
    if ($result -eq 'PARTIAL') { [void]$reasons.Add("PARTIAL: not run: $(@($miss | Select-Object -First 3) -join ', ') - PASS needs every gate.hosts host (ps7 only for '#Requires -Version 7' tests under paths.scripts)") }
    $now = Get-Date
    $rec = [ordered]@{ manifest_digest = $m.Digest; tests = $results.ToArray(); secrets = @($sec.Hits); skipped = @($sec.Skipped); result = $result; by = $by; at = (Get-CfNowText $now) }
    $rd = Join-Path $c.Dir 'receipts'
    if (-not [IO.Directory]::Exists($rd)) { [void][IO.Directory]::CreateDirectory($rd) }
    Write-CfTextFile (Join-Path $rd 'gate.json') ((ConvertTo-CfJson $rec) + "`n")
    $pass = @($results | Where-Object { $_['result'] -eq 'PASS' }).Count
    Write-Output "gate: $result $($script:Dot) manifest $(Get-CfShort $m.Digest) $($script:Dot) tests $pass/$($results.Count) PASS ($(($Hosts) -join ', ')) $($script:Dot) secrets $(@($sec.Hits).Count) $($script:Dot) receipt $(Get-CfCfgRel 'cards')/$Card/receipts/gate.json"
    foreach ($s in @($sec.Hits)) { Write-Output "  SECRET $($s['file']):$($s['line']) ($($s['rule'])) - value not shown" }
    foreach ($s in @($sec.Skipped)) { Write-Output "  skipped (binary, not scanned): $s" }
    foreach ($r in $reasons) { Write-Output "  - $r" }
    if ($result -ne 'PASS') { $script:CfExit = 1 }
}

function Test-CfRelease([string]$Root, $Card) {
    # The single release check, used by release -IfSafe, release -IfSafe -DryRun and intake. Read-only.
    $reasons = New-Object System.Collections.ArrayList
    $res = [pscustomobject]@{ Reasons = $reasons; Manifest = $null; Tickets = @(); Open = $null; Review = $null; Gate = $null; GateState = 'missing'; Protected = @(); Shared = @(); Waived = $false }
    if ($script:Closed -contains $Card.State) { [void]$reasons.Add("card is $($Card.State)") }
    try { $res.Tickets = @(Get-CfTickets $Card) } catch { [void]$reasons.Add("tickets: $($_.Exception.Message)") }
    try { $res.Manifest = Get-CfManifest $Root $Card } catch { [void]$reasons.Add("manifest: $($_.Exception.Message)") }
    $res.Open = Get-CfOpen $res.Tickets
    $revWhy = New-Object System.Collections.ArrayList
    # an OUTDATED close (old: STALE) has no verdict - it is not a review result and not a "recorded review" for the review waiver.
    $rev = @($res.Tickets | Where-Object { $_['to'] -eq 'REVIEW' -and $_['state'] -eq 'DONE' -and (Get-CfVerdict $_) -ne 'OUTDATED' })
    if ($rev.Count -eq 0) { [void]$revWhy.Add('no REVIEW ticket DONE') }
    else {
        $res.Review = $rev[$rev.Count - 1]
        $v = Get-CfVerdict $res.Review
        if (@('PASS', 'FIX-VERIFIED') -notcontains $v) { [void]$revWhy.Add("REVIEW verdict is '$v' in $(Get-CfTicketName $res.Review) (needs PASS or FIX-VERIFIED)") }
        if ($res.Manifest -and $res.Review['manifest_digest'] -ne $res.Manifest.Digest) {
            [void]$revWhy.Add("reviewed manifest $(Get-CfShort $res.Review['manifest_digest']) != current $(Get-CfShort $res.Manifest.Digest) (files changed after review)")
        }
    }
    # a valid "-> waives review" line replaces the REVIEW PASS only when
    #   - no REVIEW ticket is DONE, or the latest REVIEW ticket is ON-HOLD (old: HOLD) with "review waived" as its last note
    #     (a recorded review - FAIL or an old PASS - is never overridden);
    #   - deliverable only: no live target of the card exists in the workspace (nothing is installed anywhere), so every
    #     change is 'added', and no changed path is shared or protected (a deliverable that is only added under out/).
    # Gate, drift and open-ticket checks below stay. A REVIEW PASS at the current digest, when there is one, is used as before.
    if ($revWhy.Count -gt 0 -and (Test-CfWaiver $Card.Decisions)) {
        $allRev = @($res.Tickets | Where-Object { $_['to'] -eq 'REVIEW' })
        $held = $false
        if ($allRev.Count -gt 0) { $lr = $allRev[$allRev.Count - 1]; $held = (Get-CfTState $lr) -eq 'ON-HOLD' -and (Test-CfWaivedNote $lr) }
        if ($rev.Count -gt 0 -and -not $held) { [void]$revWhy.Add("review waiver not allowed: $(Get-CfTicketName $res.Review) is a REVIEW ticket DONE ('$(Get-CfVerdict $res.Review)'); a recorded review is not overridden") }
        elseif (-not $res.Manifest) { [void]$revWhy.Add('review waiver: manifest unreadable') }
        else {
            # the target and every parent folder below the root must be absent (a new folder inside a shared folder is an install, too)
            $live = @($res.Manifest.Map | Where-Object {
                    $sg = $_.Target.Split('/'); $hit = $false
                    for ($k = 1; $k -le $sg.Length; $k++) { $q = Join-Path $Root (($sg[0..($k - 1)]) -join '\'); if ([IO.File]::Exists($q) -or [IO.Directory]::Exists($q)) { $hit = $true; break } }
                    $hit })
            $blk = @($res.Manifest.Changes | Where-Object { (Test-CfShared $_.Path) -or $_.Change -ne 'added' -or [IO.File]::Exists((Join-Path $Root $_.Path.Replace('/', '\'))) })
            if ($live.Count -gt 0) { [void]$revWhy.Add("review waiver not allowed: live target exists in the workspace ($(@($live | Select-Object -First 3 | ForEach-Object { $_.Target }) -join ', ')) - deliverable cards only") }
            elseif ($blk.Count -gt 0) { [void]$revWhy.Add("review waiver not allowed: shared / protected or existing path changed ($(@($blk | Select-Object -First 3 | ForEach-Object { $_.Path }) -join ', '))") }
            else { $res.Waived = $true; $revWhy.Clear() }
        }
    }
    foreach ($x in $revWhy) { [void]$reasons.Add($x) }
    if ($res.Open -and $res.Open['to'] -ne 'LEAD') {
        # with a valid waiver, a REVIEW ticket in HOLD whose last note starts with "review waived" does not block; release closes it.
        $skip = $res.Waived -and $res.Open['to'] -eq 'REVIEW' -and (Get-CfTState $res.Open) -eq 'ON-HOLD' -and (Test-CfWaivedNote $res.Open)
        if (-not $skip) { [void]$reasons.Add("$(Get-CfTicketName $res.Open) is open with $($res.Open['to']) ($(Get-CfTState $res.Open))") }
    }
    try { $res.Gate = Read-CfGate $Card } catch { [void]$reasons.Add("gate.json: $($_.Exception.Message)"); $res.GateState = 'unreadable' }
    if ($null -ne $res.Gate) {
        $gd = [string](Get-CfProp $res.Gate 'manifest_digest'); $gr = [string](Get-CfProp $res.Gate 'result')
        if ($res.Manifest -and $gd -ne $res.Manifest.Digest) { $res.GateState = 'OUTDATED'; [void]$reasons.Add("gate receipt OUTDATED ($(Get-CfShort $gd) != current $(Get-CfShort $res.Manifest.Digest))") }
        elseif ($gr -ne 'PASS') { $res.GateState = $gr; [void]$reasons.Add("gate result is '$gr'") }
        else {
            # the receipt must show PASS on every host each *.Tests.ps1 in the zones needs: config gate.hosts, or ps7 only for a test
            # under config paths.scripts that declares '#Requires -Version 7' - a hand-made or one-host receipt does not count.
            $res.GateState = 'PASS'
            $gt = @(Get-CfProp $res.Gate 'tests')
            $tf = @(); if ($res.Manifest) { $tf = @($res.Manifest.Zone | Where-Object { $_.Path -like '*.Tests.ps1' }) }
            if ($tf.Count -eq 0) { $res.GateState = 'INCOMPLETE'; [void]$reasons.Add('gate receipt: no *.Tests.ps1 in the zones') }
            foreach ($f in $tf) {
                foreach ($h in @(Get-CfTestHosts $f)) {
                    $ok = @($gt | Where-Object { [string](Get-CfProp $_ 'file') -eq $f.ZoneRel -and [string](Get-CfProp $_ 'host') -eq $h -and [string](Get-CfProp $_ 'result') -eq 'PASS' }).Count -gt 0
                    if (-not $ok) { $res.GateState = 'INCOMPLETE'; [void]$reasons.Add("gate receipt has no $h PASS for $($f.ZoneRel)") }
                }
            }
        }
    }
    elseif ($res.GateState -eq 'missing') { [void]$reasons.Add('gate receipt missing (receipts/gate.json)') }
    if ($res.Manifest) {
        $drift = @()
        try { $drift = @(Get-PathList -Old $res.Manifest.Baseline -New @(Get-CfTargetEntries $res.Manifest.Map)) } catch { [void]$reasons.Add("live target: $($_.Exception.Message)") }
        if ($drift.Count -gt 0) { [void]$reasons.Add("live target changed since baseline.manifest ($(@($drift | Select-Object -First 3 | ForEach-Object { $_.Path }) -join ', ')) - LEAD decides") }
        $plist = New-Object System.Collections.ArrayList
        foreach ($ch in $res.Manifest.Changes) {
            if (-not (Test-CfProtected $ch.Path)) { continue }
            $e = Get-CfCoveringEntry $ch.Path @($Card.Protected)
            $st = 'ok'
            if (-not $e) { $st = 'NOT in protected_paths'; [void]$reasons.Add("protected path changed but not in protected_paths: $($ch.Path) ($($ch.Change))") }
            elseif (-not (Test-CfApproval $e $Card.Decisions)) { $st = "no $(Get-CfApprovalName) sentence for '$e' in Decisions"; [void]$reasons.Add("protected path $($ch.Path): no Decisions line with the owner's quoted sentence naming '$e'") }
            [void]$plist.Add("$($ch.Path) ($($ch.Change)): $st")
        }
        $res.Protected = $plist.ToArray()
        $res.Shared = @($res.Manifest.Changes | Where-Object { Test-CfShared $_.Path })
    }
    return $res
}

function Invoke-CfRelease {
    param([string]$Root, [string]$Card, [string]$As, [switch]$IfSafe, [switch]$DryRun)
    if (-not $IfSafe) { throw 'REFUSED: there is no release without -IfSafe (use: release <card> -IfSafe -As LEAD [-DryRun]).' }
    if (-not $As -or $As.ToUpperInvariant() -ne 'LEAD') { throw 'REFUSED: release is LEAD only (-As LEAD). Limit: -As is logged, not proven - without worktrees a script cannot prove which session calls it.' }
    $c = Get-CfCard $Root $Card
    $r = Test-CfRelease $Root $c
    $dg = ''; if ($r.Manifest) { $dg = $r.Manifest.Digest }
    Write-Output "release -IfSafe $Card $(if ($DryRun) { '(DRY RUN) ' })$($script:Dot) manifest $(Get-CfShort $dg) $($script:Dot) gate $($r.GateState) $($script:Dot) caller -As LEAD (logged, not proven)"
    if ($r.Waived) { Write-Output "  review: waived by $(Get-CfApprovalName) (Decisions line `"-> waives review`"; no shared / protected change)" }
    if ($r.Reasons.Count -gt 0) {
        foreach ($x in $r.Reasons) { Write-Output "  - $x" }
        throw "REFUSED: release -IfSafe: $($r.Reasons.Count) check(s) failed$(if ($DryRun) { ' (dry run, nothing written)' } else { '; nothing written' })."
    }
    if ($DryRun) { Write-Output 'DRY RUN: all checks pass; nothing written.'; return }
    $now = Get-Date
    # 1. close the last ticket (open with LEAD)
    $wv = ''; if ($r.Waived) { $wv = "; released without review (waived by $(Get-CfApprovalName))" }
    if ($r.Open) {
        $r.Open['history'] = @($r.Open['history']) + @([ordered]@{ at = (Get-CfNowText $now); by = 'LEAD'; state = 'DONE'; note = "released at $(Get-CfShort $dg) (-As LEAD logged)$wv" })
        $r.Open['state'] = 'DONE'
        Save-CfTicket $r.Open
    }
    # 2. CARD.md: state -> RELEASED (old: MERGED) + State log line
    $text = $c.Text
    $nl = "`n"; if ($text.Contains("`r`n")) { $nl = "`r`n" }
    $fmEnd = $text.IndexOf("$nl---", 3)
    $front = [regex]::Replace($text.Substring(0, $fmEnd), '(?m)^state:[ \t]*[A-Za-z_\-]+', 'state: RELEASED')
    $text = $front + $text.Substring($fmEnd)
    $logLine = "- $(Get-CfShortTime $now) $($c.State) $($script:Arrow) RELEASED $($script:Dash) LEAD (release -IfSafe, manifest $(Get-CfShort $dg)$wv; -As LEAD logged, not proven)"
    $lines = New-Object System.Collections.ArrayList
    [void]$lines.AddRange([string[]]$text.Split([string[]]@($nl), [StringSplitOptions]::None))
    $hi = -1; for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -match '^##\s+State log\s*$') { $hi = $i; break } }
    if ($hi -lt 0) { [void]$lines.Add(''); [void]$lines.Add('## State log'); [void]$lines.Add($logLine) }
    else {
        $ins = $lines.Count
        for ($i = $hi + 1; $i -lt $lines.Count; $i++) { if ($lines[$i] -match '^##\s') { $ins = $i; break } }
        while ($ins -gt $hi + 1 -and [string]::IsNullOrWhiteSpace($lines[$ins - 1])) { $ins-- }
        $lines.Insert($ins, $logLine)
    }
    Write-CfTextFile $c.File ($lines.ToArray() -join $nl)
    # 3. log.md
    $next = if (@($r.Shared).Count) { 'DOCS install request' } else { '-' }
    Add-CfLine (Get-CfLogFile $c) (Get-CfCheckpointLine $now 'LEAD' "release -IfSafe (-As LEAD) at $(Get-CfShort $dg)$wv" '-' $next 'all release checks passed')
    Write-Output "OK: $Card RELEASED (manifest $dg)$wv."
    if (@($r.Shared).Count) {
        $targets = ($r.Manifest.Map | ForEach-Object { $_.Zone + ' ' + $script:Arrow + ' ' + $_.Target }) -join '; '
        $a = @($r.Shared | Where-Object { $_.Change -eq 'added' }).Count; $ch = @($r.Shared | Where-Object { $_.Change -eq 'changed' }).Count; $rm = @($r.Shared | Where-Object { $_.Change -eq 'removed' }).Count
        Write-Output ''
        Write-Output '--- install request for DOCS (shared / protected paths; DOCS installs and re-hashes) ---'
        Write-Output "install card $Card"
        Write-Output "Type: install $($script:Dot) Card: $(Get-CfCfgRel 'cards')/$Card/CARD.md $($script:Dot) Manifest digest: $dg"
        Write-Output "Source $($script:Arrow) target: $targets"
        Write-Output "Content:"
        Write-Output "- [C] install the frozen manifest $dg ($a added, $ch changed, $rm removed; lines in the REVIEW ticket $(Get-CfTicketName $r.Review)); after copying, re-hash the targets - every line must match, else stop (cao)"
        foreach ($s in $r.Shared) { Write-Output "  $($s.Hash)  $($s.Path)" }
    }
    Invoke-CfBoardSafe $Root
}

function Get-CfNextStep($Card, $Rel, [bool]$HasBaseline) {
    if ($script:Closed -contains $Card.State) { return "none (card $($Card.State))" }
    if (-not $HasBaseline) { return "BUILD: manifest $($Card.Name) -Baseline -As BUILD (BUILD start)" }
    if ($Rel.Waived -and $Rel.Reasons.Count -eq 0) { return "LEAD: release $($Card.Name) -IfSafe -As LEAD (review waived by $(Get-CfApprovalName))" }
    $o = $Rel.Open
    if ($o) {
        $n = Get-CfTicketName $o
        # the OUTDATED hint comes first, for every open state (SENT and ON-HOLD too)
        if ($o['to'] -eq 'REVIEW' -and $o['manifest_digest'] -and $Rel.Manifest -and $Rel.Manifest.Digest -ne $o['manifest_digest']) { return "REVIEW (or LEAD): $n is OUTDATED (frozen $(Get-CfShort $o['manifest_digest']), current $(Get-CfShort $Rel.Manifest.Digest)) - ticket done -Note 'OUTDATED ...', then LEAD sends a new frozen ticket" }
        switch (Get-CfTState $o) {
            'SENT' { return "$($o['to']): ticket accept $($Card.Name) -As $($o['to'])  ($n)" }
            'ON-HOLD' { return "$($o['to']) / LEAD: resolve the ON-HOLD on $n" }
        }
        switch ($o['to']) {
            'BUILD' { return "BUILD: finish $(Get-CfTPhase $o), gate $($Card.Name), ticket done, then ticket send -To REVIEW" }
            'REVIEW' { return "REVIEW: review manifest $(Get-CfShort $o['manifest_digest']), then ticket done -Note PASS | FAIL | FIX-VERIFIED" }
            'LEAD' { if ($Rel.Reasons.Count -eq 0) { return "LEAD: release $($Card.Name) -IfSafe -As LEAD" } return "LEAD: decide ($($Rel.Reasons[0]))" }
        }
        return "$($o['to']): finish $(Get-CfTPhase $o) on $n"
    }
    if ($Rel.Reasons.Count -eq 0) { return "LEAD: release $($Card.Name) -IfSafe -As LEAD" }
    if ($Rel.Review -and (Get-CfVerdict $Rel.Review) -eq 'FAIL') { return 'LEAD: send the FIX ticket to BUILD (ticket send -To BUILD -Phase FIX)' }
    if ($Rel.GateState -ne 'PASS') { return "BUILD / OPS: gate $($Card.Name)" }
    return "LEAD: send the next ticket ($($Rel.Reasons[0]))"
}

function Invoke-CfIntake {
    param([string]$Root, [string]$Card)
    $c = Get-CfCard $Root $Card
    $r = Test-CfRelease $Root $c
    $d = $script:Dot; $ar = $script:Arrow
    Write-Output "Card $Card $d state $($c.State) $d risk $($c.Risk) $d protected_paths: $(if (@($c.Protected).Count) { $c.Protected -join ', ' } else { 'none' })"
    if ($r.Open) { Write-Output "Open ticket: $(Get-CfTicketName $r.Open) $($r.Open['from']) $ar $($r.Open['to']) $d $(Get-CfTPhase $r.Open) $d $(Get-CfTState $r.Open) $d manifest $(Get-CfShort $r.Open['manifest_digest'])" }
    else { Write-Output "Open ticket: none ($(@($r.Tickets).Count) ticket(s))" }
    if ($r.Manifest) {
        $cmp = ''
        $last = @($r.Tickets | Where-Object { $_['manifest_digest'] })
        if ($last.Count) { $lt = $last[$last.Count - 1]; $cmp = " $d last frozen $(Get-CfShort $lt['manifest_digest']) in $(Get-CfTicketName $lt): $(if ($lt['manifest_digest'] -eq $r.Manifest.Digest) { 'MATCH' } else { 'DIFFERENT' })" }
        Write-Output "Manifest: $(Get-CfShort $r.Manifest.Digest) ($($r.Manifest.Lines.Count) entr$(if ($r.Manifest.Lines.Count -eq 1) { 'y' } else { 'ies' }))$cmp"
    }
    else { Write-Output 'Manifest: not available (see reasons)' }
    $gAt = ''; if ($r.Gate) { $gAt = " at $([string](Get-CfProp $r.Gate 'at')) for $(Get-CfShort ([string](Get-CfProp $r.Gate 'manifest_digest')))" }
    Write-Output "Gate: $($r.GateState)$gAt"
    Write-Output "Protected changed: $(if (@($r.Protected).Count) { $r.Protected -join '; ' } else { 'none' })"
    if ($r.Reasons.Count -eq 0) { Write-Output 'Release dry-run: SAFE' }
    else { Write-Output "Release dry-run: REFUSED ($($r.Reasons.Count))"; foreach ($x in $r.Reasons) { Write-Output "  - $x" } }
    $hasBase = [IO.File]::Exists((Join-Path $c.Dir 'baseline.manifest'))
    Write-Output "Next: $(Get-CfNextStep $c $r $hasBase)"
}

function ConvertTo-CfCell([string]$s) { if ($null -eq $s) { return '' } return $s.Replace('|', '\|') }

function Invoke-CfBoard([string]$Root) {
    $cardsDir = Get-CfCfgPath $Root 'cards'
    $rows = New-Object System.Collections.ArrayList; $warn = 0
    foreach ($name in @(Get-PathList -In $cardsDir -Directory)) {
        if ($name -notmatch $script:CardRe) { continue }
        try {
            $c = Get-CfCard $Root $name
            $ts = @(Get-CfTickets $c); $o = Get-CfOpen $ts
            $openTxt = '-'; if ($o) { $openTxt = "$(Get-CfTicketName $o) $($o['from'])$($script:Arrow)$($o['to']) $(Get-CfTState $o)" }
            $lastTxt = '-'; $dg = '-'
            if ($ts.Count) { $l = $ts[$ts.Count - 1]; $lastTxt = "$(Get-CfTicketName $l) $(Get-CfTPhase $l) $(Get-CfTState $l)"; $v = Get-CfVerdict $l; if ($l['to'] -eq 'REVIEW' -and $v) { $lastTxt += " $v" } }
            $fz = @($ts | Where-Object { $_['manifest_digest'] }); if ($fz.Count) { $dg = Get-CfShort $fz[$fz.Count - 1]['manifest_digest'] }
            $g = '-'; $gj = Read-CfGate $c; if ($gj) { $g = "$([string](Get-CfProp $gj 'result')) @ $(Get-CfShort ([string](Get-CfProp $gj 'manifest_digest')))" }
            $lg = '-'; $lf = Get-CfLogFile $c
            if ([IO.File]::Exists($lf)) { $ll = @([IO.File]::ReadAllText($lf, $script:Utf8).Replace("`r`n", "`n").Split("`n") | Where-Object { $_ -match '^- ' }); if ($ll.Count) { $lg = $ll[$ll.Count - 1].Substring(2) } }
            if ($lg.Length -gt 90) { $lg = $lg.Substring(0, 87) + '...' }
            [void]$rows.Add("| $name | $(ConvertTo-CfCell $c.State) | $(ConvertTo-CfCell $openTxt) | $(ConvertTo-CfCell $lastTxt) | $dg | $(ConvertTo-CfCell $g) | $(ConvertTo-CfCell $lg) |")
        }
        catch {
            $warn++
            Write-Warning "board: card $name skipped - $($_.Exception.Message)"
            [void]$rows.Add("| $name | (unreadable - see the card) | - | - | - | - | - |")
        }
    }
    $sb = New-Object System.Text.StringBuilder
    [void]$sb.Append("# PROGRESS`n`nGenerated by board.ps1 at $(Get-CfShortTime (Get-Date)) from $(Get-CfCfgRel 'cards')/ - do not edit by hand.`n`n")
    [void]$sb.Append("| Card | State | Open ticket | Last ticket | Frozen manifest | Gate | Last checkpoint |`n|---|---|---|---|---|---|---|`n")
    foreach ($r in $rows) { [void]$sb.Append($r + "`n") }
    $pd = Get-CfCfgPath $Root 'process_docs'
    if (-not [IO.Directory]::Exists($pd)) { throw "$(Get-CfCfgRel 'process_docs')/ missing" }
    Write-CfTextFile (Join-Path $pd 'PROGRESS.md') $sb.ToString()
    Write-Output "board: $($rows.Count) card(s) -> $(Get-CfCfgRel 'process_docs')/PROGRESS.md$(if ($warn) { " ($warn warning(s))" })"
}

function Invoke-CfBoardSafe([string]$Root) {
    # board never changes another command's exit code: every failure is a warning.
    try { $null = Invoke-CfBoard $Root; Write-Output 'board: PROGRESS.md refreshed' }
    catch { Write-Warning "board: not refreshed - $($_.Exception.Message) (warning only)" }
}

function Invoke-CfStale {
    param([string]$Root, [datetime]$Now)
    $sentMin = Get-CfCfgNumber 'stale' 'sent_minutes' 30; $accHrs = Get-CfCfgNumber 'stale' 'accepted_hours' 3
    $cardsDir = Get-CfCfgPath $Root 'cards'
    $found = 0
    foreach ($name in @(Get-PathList -In $cardsDir -Directory)) {
        if ($name -notmatch $script:CardRe) { continue }
        try {
            $c = Get-CfCard $Root $name
            if ($script:Closed -contains $c.State) { continue }
            $o = Get-CfOpen @(Get-CfTickets $c)
            if (-not $o) { continue }
            $h = @($o['history']); $lastAt = ConvertFrom-CfAt $h[$h.Count - 1]['at']
            if ($null -eq $lastAt) { Write-Warning "stale: $name $(Get-CfTicketName $o) has an unreadable time '$($h[$h.Count - 1]['at'])'"; continue }
            $n = Get-CfTicketName $o
            $os = Get-CfTState $o
            if ($os -eq 'SENT') {
                $age = ($Now - $lastAt).TotalMinutes
                if ($age -gt $sentMin) { $found++; Write-Output ("STALE {0} {1} SENT {2} {3} for {4:N0} min (not accepted)" -f $name, $n, $o['to'], $script:Dash, $age) }
            }
            elseif (@('ACCEPTED', 'TAKEN-OVER') -contains $os) {
                $quiet = $lastAt
                foreach ($m in @(Get-CfZoneMap $Root $c)) { foreach ($f in @(Get-CfMapFiles $m $m.ZoneFull)) { if ($f.Time -gt $quiet) { $quiet = $f.Time } } }
                $hrs = ($Now - $quiet).TotalHours
                if ($hrs -gt $accHrs) { $found++; Write-Output ("STALE {0} {1} {2} {3} {4} no change in the zones for {5:N1} h" -f $name, $n, $os, $o['to'], $script:Dash, $hrs) }
            }
        }
        catch { Write-Warning "stale: card $name skipped - $($_.Exception.Message)" }
    }
    if ($found -eq 0) { Write-Output 'stale: nothing stale' }
    Write-Output "(time base: local clock of this machine; history[].at has no time zone; output stays on this machine)"
}

Export-ModuleMember -Function ConvertTo-CfName, Get-CfCard, Get-CfZoneMap, Get-PathList, Invoke-CfMain, Get-CfExitCode, Resolve-CfRoot, Invoke-CfTicket, Invoke-CfCheckpoint, Invoke-CfManifest, Invoke-CfGate, Invoke-CfRelease, Invoke-CfIntake, Invoke-CfBoard, Invoke-CfBoardSafe, Invoke-CfStale, Test-CfProtected, Test-CfShared, Find-CfSecretInText, Read-CfConfig, Get-CfCfg, Get-CfCfgRel, Get-CfCfgPath, Get-CfCfgList, Get-CfCfgNumber, Get-CfApprovalName, Get-CfProp
