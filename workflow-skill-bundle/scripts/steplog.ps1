<#
.SYNOPSIS
  steplog - process time log: named steps per task.
    start  <task> -Step <CODE> -As <session title> [-Type <task type>] [-Model <model effort>] [-Note <t>]
    end    <task> -Step <CODE> [-As <session title>] [-Result OK|NG|PARTIAL] [-Note <t>]
    wait   <task> -Note <what the owner must answer> [-As <session title>]
    resume <task> [-As <session title>] [-Note <t>]
    report [-Task <id>] [-Type <type>] [-From yyyy-MM-dd] [-To yyyy-MM-dd] [-Csv <path>]
    purge  [-Days 90] -As <session title> [-DryRun]   (default: config steplog.purge_days, else 90)
  <task> = T-ID (T-20260105-01), card (012-sample-card) or task folder (05_01-sample-task).
  Time comes from the local clock only. One JSON line per event, append-only, to <process_log>/steps/<yyyy-MM>.jsonl:
  {at, event, task, step, type, session, model, result, note}. Never prompt text or file contents.
.EXAMPLE
  .\steplog.ps1 start T-20260105-01 -Step BUILD -As Dev -Type card -Model 'Opus high'
  .\steplog.ps1 end T-20260105-01 -Step BUILD -Result OK
  .\steplog.ps1 report -Type card
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)][string]$Action,
    [Parameter(Position = 1)][string]$Task,
    [string]$Step, [string]$As, [string]$Type, [string]$Model, [string]$Note, [string]$Result,
    [string]$From, [string]$To, [string]$Csv,
    [int]$Days = -1, [switch]$DryRun,   # -1 = config steplog.purge_days (default 90)
    [string]$Root = ''
)
if ($PSVersionTable.PSVersion.Major -lt 7) { [Console]::Out.WriteLine('REFUSED: steplog.ps1 needs PowerShell 7 (pwsh); this is Windows PowerShell ' + $PSVersionTable.PSVersion + '.'); exit 1 }
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'CardFlow.psm1') -Force -DisableNameChecking

$script:Steps = @('INTAKE', 'POLICY', 'READ', 'PLAN', 'CONFIRM', 'BUILD', 'SELFCHECK', 'QA', 'FIX', 'KB', 'DELIVER', 'CLEANUP', 'OTHER')
$script:Results = @('OK', 'NG', 'PARTIAL')
$script:TaskRe = '^(T-\d{8}-\d{2,3}|\d{3}-[A-Za-z0-9][A-Za-z0-9-]*|\d{2}_\d{2}-[A-Za-z0-9][A-Za-z0-9-]*)$'
$script:TypeRe = '^[a-z0-9][a-z0-9-]{0,39}$'
$script:Inv = [Globalization.CultureInfo]::InvariantCulture
$script:AtFormat = 'yyyy-MM-ddTHH:mm:ss'
$script:U8 = New-Object System.Text.UTF8Encoding($false)
$script:HasDateKind = (Get-Command ConvertFrom-Json).Parameters.ContainsKey('DateKind')
$script:Arrow = ' > '

# ---------------- input checks ----------------
function Get-OneLine([string]$s) {
    if ($null -eq $s) { return '' }
    return (($s -replace '[\r\n\t]+', ' ') -replace '\s{2,}', ' ').Trim()
}

function Get-CleanText([string]$Name, [string]$Value, [int]$Max) {
    $v = Get-OneLine $Value
    if ($v.Length -gt $Max) { throw "REFUSED: -$Name is longer than $Max characters (the step log keeps short notes, never prompt text or file contents)." }
    $h = @(Find-CfSecretInText $v)
    if ($h.Count -gt 0) { throw "REFUSED: -$Name looks like a secret or session ID (rule $($h[0].Rule)); the step log never carries them." }
    return $v
}

function Get-TaskId([string]$t) {
    # one spelling per id - T-IDs upper case (T-20260105-01), card / task-folder names lower case.
    if (-not $t) { throw 'REFUSED: <task> is required (T-ID, card NNN-slug or task folder DD_NN-slug).' }
    if ($t -notmatch $script:TaskRe) { throw "REFUSED: task '$t' is not a T-ID (T-YYYYMMDD-NN), card (NNN-slug) or task folder (DD_NN-slug)." }
    return (ConvertTo-TaskKey $t)
}

function ConvertTo-TaskKey([string]$t) {
    if ($t -match '^[Tt]-\d') { return $t.ToUpperInvariant() }
    return $t.ToLowerInvariant()
}

# alias map card name / task-folder name -> T-ID, read from <cards>/*/CARD.md (front matter task: + zones)
# and <lead>/board.md (rows starting with a T-ID). An alias that points at two different T-IDs is not used.
function Get-AliasMap([string]$R) {
    $pairs = New-Object System.Collections.ArrayList
    $cardsDir = Get-CfCfgPath $R 'cards'
    foreach ($card in @(Get-PathList -In $cardsDir -Directory)) {
        if ($card -notmatch '^\d{3}-[A-Za-z0-9][A-Za-z0-9-]*$') { continue }
        $f = Join-Path $cardsDir "$card\CARD.md"
        if (-not [IO.File]::Exists($f)) { continue }
        $text = [IO.File]::ReadAllText($f, $script:U8)
        $end = $text.IndexOf("`n---", 3); if ($end -lt 0) { continue }
        $fm = $text.Substring(0, $end)
        if ($fm -notmatch '(?m)^task:\s*([Tt]-\d{8}-\d{2,3})\b') { continue }
        $tid = $Matches[1].ToUpperInvariant()
        [void]$pairs.Add(@($card.ToLowerInvariant(), $tid))
        foreach ($m in [regex]::Matches($fm, '\d{4}-\d{2}/(\d{2}_\d{2}-[A-Za-z0-9][A-Za-z0-9-]*)/')) { [void]$pairs.Add(@($m.Groups[1].Value.ToLowerInvariant(), $tid)) }
    }
    $board = Join-Path (Get-CfCfgPath $R 'lead') 'board.md'
    if ([IO.File]::Exists($board)) {
        foreach ($l in [IO.File]::ReadAllText($board, $script:U8).Replace("`r`n", "`n").Split("`n")) {
            if ($l -notmatch '^\|\s*([Tt]-\d{8}-\d{2,3})\s*\|') { continue }
            $tid = $Matches[1].ToUpperInvariant()
            foreach ($m in [regex]::Matches($l, '\d{4}-\d{2}/(\d{2}_\d{2}-[A-Za-z0-9][A-Za-z0-9-]*)/')) { [void]$pairs.Add(@($m.Groups[1].Value.ToLowerInvariant(), $tid)) }
            foreach ($m in [regex]::Matches($l, '(?i)card\s+`(\d{3}-[a-z0-9][a-z0-9-]*)`')) { [void]$pairs.Add(@($m.Groups[1].Value.ToLowerInvariant(), $tid)) }
        }
    }
    $map = @{}; $bad = @{}
    foreach ($p in $pairs) {
        $a = $p[0]; $tid = $p[1]
        if ($bad.ContainsKey($a)) { continue }
        if ($map.ContainsKey($a) -and $map[$a] -ne $tid) { $map.Remove($a); $bad[$a] = $true; continue }
        $map[$a] = $tid
    }
    return $map
}

function Resolve-TaskKey([string]$t, $Map) {
    $k = ConvertTo-TaskKey $t
    if ($null -ne $Map -and $Map.ContainsKey($k)) { return $Map[$k] }
    return $k
}

function Get-StepCode([string]$s) {
    if (-not $s) { throw "REFUSED: -Step is required ($($script:Steps -join ', '))." }
    $u = $s.ToUpperInvariant()
    if ($script:Steps -notcontains $u) { throw "REFUSED: unknown step code '$s' (allowed: $($script:Steps -join ', '))." }
    return $u
}

function ConvertTo-Day([string]$s, [string]$Name) {
    $d = [datetime]::MinValue
    if (-not [datetime]::TryParseExact($s, 'yyyy-MM-dd', $script:Inv, [Globalization.DateTimeStyles]::None, [ref]$d)) { throw "REFUSED: -$Name '$s' is not a date yyyy-MM-dd." }
    return $d
}

# ---------------- JSON line writer / reader ----------------
function ConvertTo-JStr($v) {
    if ($null -eq $v -or [string]$v -eq '') { return 'null' }
    $sb = New-Object System.Text.StringBuilder
    [void]$sb.Append('"')
    foreach ($ch in ([string]$v).ToCharArray()) {
        $c = [int]$ch
        if ($ch -eq '"') { [void]$sb.Append('\"') }
        elseif ($ch -eq '\') { [void]$sb.Append('\\') }
        elseif ($c -lt 32) { [void]$sb.Append(('\u{0:x4}' -f $c)) }
        else { [void]$sb.Append($ch) }
    }
    [void]$sb.Append('"')
    return $sb.ToString()
}

function Get-LogDir([string]$R) { return (Join-Path (Get-CfCfgPath $R 'process_log') 'steps') }

function Add-StepLine([string]$R, [datetime]$Now, [System.Collections.Specialized.OrderedDictionary]$Ev) {
    $dir = Get-LogDir $R
    [void][IO.Directory]::CreateDirectory($dir)
    $file = Join-Path $dir ($Now.ToString('yyyy-MM', $script:Inv) + '.jsonl')
    $line = '{' + (($Ev.Keys | ForEach-Object { (ConvertTo-JStr $_) + ':' + (ConvertTo-JStr $Ev[$_]) }) -join ',') + '}'
    $bytes = $script:U8.GetBytes($line + "`n")
    $done = $false
    for ($i = 0; $i -lt 40 -and -not $done; $i++) {
        try {
            # exclusive write lock: several sessions may append at the same moment
            $fs = [IO.File]::Open($file, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::Read)
            try {
                if ($fs.Length -gt 0) {
                    [void]$fs.Seek(-1, [IO.SeekOrigin]::End)
                    if ($fs.ReadByte() -ne 10) { $fs.WriteByte(10) }
                }
                [void]$fs.Seek(0, [IO.SeekOrigin]::End)
                $fs.Write($bytes, 0, $bytes.Length)
                $fs.Flush()
                $done = $true
            }
            finally { $fs.Dispose() }
        }
        catch [System.IO.IOException] { Start-Sleep -Milliseconds 25 }
    }
    if (-not $done) { throw "ERROR: could not append to '$file' (locked)." }
    # re-read after write
    $fs2 = [IO.File]::Open($file, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
    try { $sr = New-Object IO.StreamReader($fs2, $script:U8); $back = $sr.ReadToEnd() } finally { $fs2.Dispose() }
    if (-not ("`n" + $back).Contains("`n" + $line + "`n")) { throw "ERROR: re-read of '$file' does not contain the line just written." }
    return $file
}

function Get-Prop($o, [string]$n) {
    $p = $o.PSObject.Properties[$n]
    if ($null -eq $p -or $null -eq $p.Value) { return '' }
    if ($p.Value -is [datetime]) { return $p.Value.ToString($script:AtFormat, $script:Inv) }
    return [string]$p.Value
}

# Reads <process_log>/steps/*.jsonl (only month files between $FromDay and $ToDay when given), in file + line order.
function Read-StepEvents([string]$R, $FromDay, $ToDay, $Map) {
    $dir = Get-LogDir $R
    $events = New-Object System.Collections.ArrayList
    $bad = New-Object System.Collections.ArrayList
    $seq = 0
    foreach ($name in @(Get-PathList -In $dir -Filter '*.jsonl')) {
        if ($name -notmatch '^(\d{4}-\d{2})\.jsonl$') { continue }
        if ($null -ne $FromDay -and [string]::CompareOrdinal($Matches[1], $FromDay.ToString('yyyy-MM', $script:Inv)) -lt 0) { continue }
        if ($null -ne $ToDay -and [string]::CompareOrdinal($Matches[1], $ToDay.ToString('yyyy-MM', $script:Inv)) -gt 0) { continue }
        $full = Join-Path $dir $name
        $fs = [IO.File]::Open($full, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
        try { $sr = New-Object IO.StreamReader($fs, $script:U8); $text = $sr.ReadToEnd() } finally { $fs.Dispose() }
        $no = 0
        foreach ($l in $text.Replace("`r`n", "`n").Split("`n")) {
            $no++
            if ($l.Trim() -eq '') { continue }
            $o = $null
            try {
                $p = @{}; if ($script:HasDateKind) { $p['DateKind'] = 'String' }
                $o = ConvertFrom-Json -InputObject $l @p
            }
            catch { $o = $null }
            $at = [datetime]::MinValue
            $ok = ($null -ne $o) -and [datetime]::TryParseExact((Get-Prop $o 'at'), $script:AtFormat, $script:Inv, [Globalization.DateTimeStyles]::None, [ref]$at)
            $evName = ''; if ($ok) { $evName = Get-Prop $o 'event' }
            if (-not $ok -or @('start', 'end', 'wait', 'resume') -notcontains $evName -or -not (Get-Prop $o 'task')) {
                [void]$bad.Add("$($script:LG)/steps/$($name):$no"); continue
            }
            $seq++
            [void]$events.Add([pscustomobject]@{
                    Seq = $seq; At = $at; Event = $evName; Task = (Resolve-TaskKey (Get-Prop $o 'task') $Map); Raw = (ConvertTo-TaskKey (Get-Prop $o 'task')); Step = (Get-Prop $o 'step'); Type = (Get-Prop $o 'type')
                    Session = (Get-Prop $o 'session'); Model = (Get-Prop $o 'model'); Result = (Get-Prop $o 'result'); Note = (Get-Prop $o 'note')
                    Src = "$($script:LG)/steps/$($name):$no"; File = $name; Line = $no; Text = $l
                })
        }
    }
    $list = New-Object 'System.Collections.Generic.List[object]'
    foreach ($e in $events) { $list.Add($e) }
    # chronological; same second keeps the written order
    $list.Sort([Comparison[object]] { param($a, $b) $c = $a.At.CompareTo($b.At); if ($c -ne 0) { return $c }; return $a.Seq.CompareTo($b.Seq) })
    return [pscustomobject]@{ Events = $list.ToArray(); Bad = [string[]]$bad.ToArray() }
}

# Pairs start/end (key task|STEP, matched by session) and wait/resume (key task). Never guesses: leftovers are unpaired.
function Get-Pairs($Events) {
    $open = @{}; $waitOpen = @{}
    $steps = New-Object System.Collections.ArrayList
    $waits = New-Object System.Collections.ArrayList
    $unpaired = New-Object System.Collections.ArrayList
    foreach ($e in $Events) {
        $k = ($e.Task + '|' + $e.Step).ToUpperInvariant()
        $tk = $e.Task.ToUpperInvariant()
        switch ($e.Event) {
            'start' {
                if (-not $open.ContainsKey($k)) { $open[$k] = New-Object System.Collections.ArrayList }
                $dup = @($open[$k] | Where-Object { $_.Session -ieq $e.Session })
                if ($dup.Count -gt 0) { [void]$unpaired.Add([pscustomobject]@{ Kind = 'start again while open'; Ev = $e }); continue }
                [void]$open[$k].Add($e)
            }
            'end' {
                $cand = @(); if ($open.ContainsKey($k)) { $cand = @($open[$k]) }
                if ($e.Session) { $cand = @($cand | Where-Object { $_.Session -ieq $e.Session }) }
                if ($cand.Count -ne 1) { [void]$unpaired.Add([pscustomobject]@{ Kind = 'end without start'; Ev = $e }); continue }
                $s = $cand[0]; $open[$k].Remove($s)
                [void]$steps.Add([pscustomobject]@{ Task = $s.Task; Step = $s.Step; Session = $s.Session; Model = $s.Model; Type = $s.Type; Start = $s.At; End = $e.At; Result = $e.Result; StartEv = $s; EndEv = $e })
            }
            'wait' {
                if ($waitOpen.ContainsKey($tk)) { [void]$unpaired.Add([pscustomobject]@{ Kind = 'wait while waiting'; Ev = $e }); continue }
                $waitOpen[$tk] = $e
            }
            'resume' {
                if (-not $waitOpen.ContainsKey($tk)) { [void]$unpaired.Add([pscustomobject]@{ Kind = 'resume without wait'; Ev = $e }); continue }
                $w = $waitOpen[$tk]; $waitOpen.Remove($tk)
                [void]$waits.Add([pscustomobject]@{ Task = $w.Task; Start = $w.At; End = $e.At; Note = $w.Note; WaitEv = $w; ResumeEv = $e })
            }
        }
    }
    $openStarts = New-Object System.Collections.ArrayList
    foreach ($k in $open.Keys) { foreach ($s in $open[$k]) { [void]$openStarts.Add($s); [void]$unpaired.Add([pscustomobject]@{ Kind = 'start without end'; Ev = $s }) } }
    foreach ($k in $waitOpen.Keys) { [void]$unpaired.Add([pscustomobject]@{ Kind = 'wait without resume'; Ev = $waitOpen[$k] }) }
    return [pscustomobject]@{ Steps = $steps.ToArray(); Waits = $waits.ToArray(); Unpaired = $unpaired.ToArray(); OpenStarts = $openStarts.ToArray(); OpenWaits = @($waitOpen.Values) }
}

function Get-Min([datetime]$a, [datetime]$b) { return [Math]::Round(($b - $a).TotalMinutes, 1) }
function Format-Min([double]$m) { return $m.ToString('0.0', $script:Inv) }
function Format-At([datetime]$d) { return $d.ToString('yyyy-MM-dd HH:mm', $script:Inv) }

function Get-WaitIn($Waits, [string]$TaskId, [datetime]$a, [datetime]$b) {
    $sum = 0.0
    foreach ($w in $Waits) {
        if ($w.Task -ine $TaskId) { continue }
        $s = if ($w.Start -gt $a) { $w.Start } else { $a }
        $e = if ($w.End -lt $b) { $w.End } else { $b }
        if ($e -gt $s) { $sum += ($e - $s).TotalMinutes }
    }
    return [Math]::Round($sum, 1)
}

function ConvertTo-Cell([string]$s) { if ($null -eq $s -or $s -eq '') { return '-' } return $s.Replace('|', '\|') }

function ConvertTo-CsvField([string]$s) {
    if ($null -eq $s) { $s = '' }
    if ($s -match '^[=+@\t\r-]') { $s = "'" + $s }   # a cell Excel would read as a formula becomes text
    if ($s -match '[",\r\n]') { return '"' + $s.Replace('"', '""') + '"' }
    return $s
}

# ---------------- commands ----------------
function Invoke-Start([string]$R) {
    $t = Get-TaskId $Task; $code = Get-StepCode $Step
    if (-not $As) { throw 'REFUSED: -As <session title> is required for start.' }
    $who = Get-CleanText 'As' $As 60
    $ty = ''
    if ($Type) { if ($Type -notmatch $script:TypeRe) { throw "REFUSED: -Type '$Type' must be a short lowercase slug (a-z 0-9 -, max 40)." }; $ty = $Type }
    $mo = Get-CleanText 'Model' $Model 40
    $no = Get-CleanText 'Note' $Note 300
    if ($code -eq 'OTHER' -and -not $no) { throw 'REFUSED: step OTHER needs -Note (what the step is).' }
    $now = Get-Date
    $map = Get-AliasMap $R; $key = Resolve-TaskKey $t $map
    $p = Get-Pairs (Read-StepEvents $R $now.AddMonths(-1) $now $map).Events
    $same = @($p.OpenStarts | Where-Object { $_.Task -ieq $key -and $_.Step -ieq $code -and $_.Session -ieq $who })
    if ($same.Count -gt 0) { throw "REFUSED: $t $code already started at $(Format-At $same[0].At) by $who; end it first (end $t -Step $code -Result PARTIAL)." }
    $ev = [ordered]@{ at = $now.ToString($script:AtFormat, $script:Inv); event = 'start'; task = $t; step = $code; type = $ty; session = $who; model = $mo; result = ''; note = $no }
    $f = Add-StepLine $R $now $ev
    Write-Output "OK: start $t$(if ($key -ne $t) { ' (= ' + $key + ')' }) $code $(Format-At $now) ($who) -> $($script:LG)/steps/$([IO.Path]::GetFileName($f))"
}

function Invoke-End([string]$R) {
    $t = Get-TaskId $Task; $code = Get-StepCode $Step
    $res = 'OK'
    if ($Result) { $res = $Result.ToUpperInvariant(); if ($script:Results -notcontains $res) { throw "REFUSED: -Result '$Result' (allowed: $($script:Results -join ', '))." } }
    $who = Get-CleanText 'As' $As 60
    $no = Get-CleanText 'Note' $Note 300
    $now = Get-Date
    $map = Get-AliasMap $R; $key = Resolve-TaskKey $t $map
    $all = Read-StepEvents $R $now.AddMonths(-1) $now $map
    $p = Get-Pairs $all.Events
    $cand = @($p.OpenStarts | Where-Object { $_.Task -ieq $key -and $_.Step -ieq $code })
    if ($who) { $cand = @($cand | Where-Object { $_.Session -ieq $who }) }
    if ($cand.Count -eq 0) { throw "REFUSED: no open start for $t $code$(if ($who) { " by $who" }) (start it first; nothing is guessed)." }
    if ($cand.Count -gt 1) { throw "REFUSED: $($cand.Count) open starts for $t $code ($(($cand | ForEach-Object { $_.Session }) -join ', ')); give -As <session title>." }
    $s = $cand[0]
    $ev = [ordered]@{ at = $now.ToString($script:AtFormat, $script:Inv); event = 'end'; task = $t; step = $code; type = $s.Type; session = $s.Session; model = $s.Model; result = $res; note = $no }
    [void](Add-StepLine $R $now $ev)
    $done = @($p.Waits) + @($p.OpenWaits | ForEach-Object { [pscustomobject]@{ Task = $_.Task; Start = $_.At; End = $now } })
    $wm = Get-WaitIn $done $key $s.At $now
    Write-Output "OK: end $t $code $res $(Format-At $now) - $(Format-Min (Get-Min $s.At $now)) min (waiting $(Format-Min $wm) min)"
}

function Invoke-Wait([string]$R, [bool]$Resume) {
    $t = Get-TaskId $Task
    $who = Get-CleanText 'As' $As 60
    $no = Get-CleanText 'Note' $Note 300
    if (-not $Resume -and -not $no) { throw 'REFUSED: wait needs -Note (what the owner must answer).' }
    $now = Get-Date
    $map = Get-AliasMap $R; $key = Resolve-TaskKey $t $map
    $p = Get-Pairs (Read-StepEvents $R $now.AddMonths(-1) $now $map).Events
    $w = @($p.OpenWaits | Where-Object { $_.Task -ieq $key })
    if (-not $Resume -and $w.Count -gt 0) { throw "REFUSED: $t is already waiting since $(Format-At $w[0].At); resume it first." }
    if ($Resume -and $w.Count -eq 0) { throw "REFUSED: $t is not waiting (no open wait)." }
    $name = if ($Resume) { 'resume' } else { 'wait' }
    $ev = [ordered]@{ at = $now.ToString($script:AtFormat, $script:Inv); event = $name; task = $t; step = ''; type = ''; session = $who; model = ''; result = ''; note = $no }
    [void](Add-StepLine $R $now $ev)
    if ($Resume) { Write-Output "OK: resume $t $(Format-At $now) - waited $(Format-Min (Get-Min $w[0].At $now)) min" }
    else { Write-Output "OK: wait $t $(Format-At $now)" }
}

function Invoke-Report([string]$R) {
    $fromDay = $null; $toDay = $null
    if ($From) { $fromDay = ConvertTo-Day $From 'From' }
    if ($To) { $toDay = ConvertTo-Day $To 'To' }
    if ($Type -and $Type -notmatch $script:TypeRe) { throw "REFUSED: -Type '$Type' must be a short lowercase slug." }
    $map = Get-AliasMap $R
    $tf = ''; if ($Task) { $tf = Resolve-TaskKey (Get-TaskId $Task) $map }
    # read one month more on each side so pairs across a month edge stay whole; filter after pairing
    $rf = $null; $rt = $null
    if ($null -ne $fromDay) { $rf = $fromDay.AddMonths(-1) }
    if ($null -ne $toDay) { $rt = $toDay.AddMonths(1) }
    $all = Read-StepEvents $R $rf $rt $map
    $p = Get-Pairs $all.Events
    # task type = first non-empty type of the task's start events
    $taskType = @{}
    foreach ($e in $all.Events) { if ($e.Event -eq 'start' -and $e.Type -and -not $taskType.ContainsKey($e.Task.ToUpperInvariant())) { $taskType[$e.Task.ToUpperInvariant()] = $e.Type } }
    $typeOf = { param($tk) $k = $tk.ToUpperInvariant(); if ($taskType.ContainsKey($k)) { return $taskType[$k] } return '' }
    $keep = {
        param($tk, [datetime]$at)
        if ($tf -and $tk -ine $tf) { return $false }
        if ($Type -and (& $typeOf $tk) -ne $Type) { return $false }
        if ($null -ne $fromDay -and $at -lt $fromDay) { return $false }
        if ($null -ne $toDay -and $at -ge $toDay.AddDays(1)) { return $false }
        return $true
    }
    $rows = @($p.Steps | Where-Object { & $keep $_.Task $_.Start })
    $un = @($p.Unpaired | Where-Object { & $keep $_.Ev.Task $_.Ev.At })

    if ($Csv) {
        $path = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Csv)
        if ([IO.File]::Exists($path)) { throw "REFUSED: '$path' exists; choose a new file name (report never overwrites)." }
        $sb = New-Object System.Text.StringBuilder
        [void]$sb.Append("task,type,step,session,model,start,end,minutes,waiting_minutes,result`r`n")
        foreach ($row in $rows) {
            $f = @($row.Task, (& $typeOf $row.Task), $row.Step, $row.Session, $row.Model, (Format-At $row.Start), (Format-At $row.End),
                (Format-Min (Get-Min $row.Start $row.End)), (Format-Min (Get-WaitIn $p.Waits $row.Task $row.Start $row.End)), $row.Result)
            [void]$sb.Append((($f | ForEach-Object { ConvertTo-CsvField ([string]$_) }) -join ',') + "`r`n")
        }
        $enc = New-Object System.Text.UTF8Encoding($true)   # BOM: Excel opens it as UTF-8
        $fs = [IO.File]::Open($path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        try { $pre = $enc.GetPreamble(); $fs.Write($pre, 0, $pre.Length); $b = $enc.GetBytes($sb.ToString()); $fs.Write($b, 0, $b.Length) } finally { $fs.Dispose() }
        Write-Output "OK: CSV $($rows.Count) step row(s) -> $path"
        if ($un.Count -gt 0 -or @($all.Bad).Count -gt 0) { Write-Output "note: $($un.Count) unpaired event(s), $(@($all.Bad).Count) unreadable line(s) - not in the CSV; run report without -Csv to list them." }
        return
    }

    $filt = @(); if ($Task) { $filt += "task $Task" }; if ($Type) { $filt += "type $Type" }; if ($From) { $filt += "from $From" }; if ($To) { $filt += "to $To" }
    Write-Output "# Step log report$(if ($filt.Count) { ' (' + ($filt -join ', ') + ')' })"
    Write-Output ''
    Write-Output '## Steps'
    Write-Output ''
    Write-Output '| Task | Type | Step | Session | Start | End | Minutes | Waiting min | Result |'
    Write-Output '|---|---|---|---|---|---|---:|---:|---|'
    foreach ($row in $rows) {
        Write-Output ('| {0} | {1} | {2} | {3} | {4} | {5} | {6} | {7} | {8} |' -f (ConvertTo-Cell $row.Task), (ConvertTo-Cell (& $typeOf $row.Task)), $row.Step, (ConvertTo-Cell $row.Session),
            (Format-At $row.Start), (Format-At $row.End), (Format-Min (Get-Min $row.Start $row.End)), (Format-Min (Get-WaitIn $p.Waits $row.Task $row.Start $row.End)), (ConvertTo-Cell $row.Result))
    }
    if ($rows.Count -eq 0) { Write-Output '| - | - | - | - | - | - | - | - | - |' }

    # per task total
    Write-Output ''
    Write-Output '## Per task'
    Write-Output ''
    Write-Output '| Task | Type | Steps | First start | Last end | Span min | Step min (sum) | Waiting min | Work min (span - waiting) |'
    Write-Output '|---|---|---:|---|---|---:|---:|---:|---:|'
    $tasks = New-Object 'System.Collections.Generic.List[string]'
    foreach ($row in $rows) { if (-not ($tasks | Where-Object { $_ -ieq $row.Task })) { $tasks.Add($row.Task) } }
    foreach ($tk in $tasks) {
        $tr = @($rows | Where-Object { $_.Task -ieq $tk })
        $first = ($tr | Sort-Object Start | Select-Object -First 1).Start
        $last = ($tr | Sort-Object End | Select-Object -Last 1).End
        $sum = 0.0; foreach ($x in $tr) { $sum += (Get-Min $x.Start $x.End) }
        $span = Get-Min $first $last
        $wm = Get-WaitIn $p.Waits $tk $first $last
        Write-Output ('| {0} | {1} | {2} | {3} | {4} | {5} | {6} | {7} | {8} |' -f $tk, (ConvertTo-Cell (& $typeOf $tk)), $tr.Count, (Format-At $first), (Format-At $last),
            (Format-Min $span), (Format-Min $sum), (Format-Min $wm), (Format-Min ([Math]::Round($span - $wm, 1))))
    }
    if ($tasks.Count -eq 0) { Write-Output '| - | - | - | - | - | - | - | - | - |' }

    # per type: step order (for flowcharts) + average minutes per step
    Write-Output ''
    Write-Output '## Per type - step order'
    Write-Output ''
    Write-Output '| Type | Tasks | Step order (start time, repeats folded) |'
    Write-Output '|---|---:|---|'
    $types = New-Object 'System.Collections.Generic.List[string]'
    foreach ($tk in $tasks) { $ty = & $typeOf $tk; if (-not $ty) { $ty = '(none)' }; if (-not $types.Contains($ty)) { $types.Add($ty) } }
    $avgLines = New-Object System.Collections.ArrayList
    foreach ($ty in $types) {
        $seqs = @{}; $order = New-Object 'System.Collections.Generic.List[string]'
        foreach ($tk in $tasks) {
            $t2 = & $typeOf $tk; if (-not $t2) { $t2 = '(none)' }
            if ($t2 -ne $ty) { continue }
            $codes = New-Object 'System.Collections.Generic.List[string]'
            foreach ($x in @($rows | Where-Object { $_.Task -ieq $tk } | Sort-Object Start)) { if ($codes.Count -eq 0 -or $codes[$codes.Count - 1] -ne $x.Step) { $codes.Add($x.Step) } }
            $s = ($codes.ToArray()) -join $script:Arrow
            if (-not $seqs.ContainsKey($s)) { $seqs[$s] = 0; $order.Add($s) }
            $seqs[$s]++
        }
        $sorted = @($order | Sort-Object @{ Expression = { $seqs[$_] }; Descending = $true }, @{ Expression = { $order.IndexOf($_) } })
        $first = $true
        foreach ($s in $sorted) {
            $label = if ($first) { 'usual: ' } else { '' }
            Write-Output ('| {0} | {1} | {2}{3} |' -f $ty, $seqs[$s], $label, $s)
            $first = $false
        }
        $tyRows = @($rows | Where-Object { $t3 = & $typeOf $_.Task; if (-not $t3) { $t3 = '(none)' }; $t3 -eq $ty })
        foreach ($code in $script:Steps) {
            $sr = @($tyRows | Where-Object { $_.Step -eq $code })
            if ($sr.Count -eq 0) { continue }
            $tot = 0.0; $wt = 0.0
            foreach ($x in $sr) { $tot += (Get-Min $x.Start $x.End); $wt += (Get-WaitIn $p.Waits $x.Task $x.Start $x.End) }
            [void]$avgLines.Add(('| {0} | {1} | {2} | {3} | {4} |' -f $ty, $code, $sr.Count, (Format-Min ([Math]::Round($tot / $sr.Count, 1))), (Format-Min ([Math]::Round($wt / $sr.Count, 1)))))
        }
    }
    if ($types.Count -eq 0) { Write-Output '| - | - | - |' }
    Write-Output ''
    Write-Output '## Per type - average minutes per step'
    Write-Output ''
    Write-Output '| Type | Step | Count | Avg min | Avg waiting min |'
    Write-Output '|---|---|---:|---:|---:|'
    foreach ($l in $avgLines) { Write-Output $l }
    if ($avgLines.Count -eq 0) { Write-Output '| - | - | - | - | - |' }

    # ids written as a card / task-folder name and counted under their T-ID (CARD.md task: / <lead>/board.md)
    $merged = New-Object 'System.Collections.Generic.List[string]'
    foreach ($e in $all.Events) {
        if ($e.Raw -ne $e.Task -and (& $keep $e.Task $e.At)) { $s2 = "$($e.Raw) -> $($e.Task)"; if (-not $merged.Contains($s2)) { $merged.Add($s2) } }
    }
    if ($merged.Count -gt 0) {
        Write-Output ''
        Write-Output '## Task ids merged (alias -> T-ID)'
        Write-Output ''
        foreach ($m in $merged) { Write-Output "- $m" }
    }

    # unpaired / unreadable: listed, never guessed
    Write-Output ''
    Write-Output '## Unpaired events (not counted)'
    Write-Output ''
    if ($un.Count -eq 0 -and @($all.Bad).Count -eq 0) { Write-Output '- none' }
    foreach ($u in $un) {
        $e = $u.Ev
        Write-Output ('- {0}: {1} {2}{3} at {4}{5} ({6})' -f $u.Kind, $e.Event, $e.Task, $(if ($e.Step) { ' ' + $e.Step } else { '' }), (Format-At $e.At), $(if ($e.Session) { ' by ' + $e.Session } else { '' }), $e.Src)
    }
    foreach ($b in $all.Bad) { Write-Output "- unreadable line: $b" }
}

# ---------------- purge ----------------
function Format-Size([long]$b) { if ($b -ge 1MB) { return ('{0:N1} MB' -f ($b / 1MB)) } elseif ($b -ge 1KB) { return ('{0:N1} KB' -f ($b / 1KB)) } return "$b B" }

# One line in <trash>/TRASH-LOG.md, same table and header as the trash script of the project (CRLF, UTF-8 without BOM).
function Add-TrashLog([string]$R, [datetime]$Now, [string]$Act, [string]$Who, [string]$Why, [string]$FromPath, [string]$ToPath, [string]$Size) {
    $tr = Get-CfCfgPath $R 'trash'
    $lf = Join-Path $tr 'TRASH-LOG.md'
    $enc = New-Object System.Text.UTF8Encoding($false)
    if (-not [IO.File]::Exists($lf)) {
        [void][IO.Directory]::CreateDirectory($tr)
        [IO.File]::WriteAllText($lf, "# TRASH-LOG`r`n`r`n| Time | Action | By | Reason | Original path | Trash path | Size |`r`n|---|---|---|---|---|---|---|`r`n", $enc)
    }
    $cell = { param($s) ([string]$s) -replace '\|', '/' -replace '[\r\n]+', ' ' }
    $line = "| $($Now.ToString('yyyy-MM-dd HH:mm:ss', $script:Inv)) | $Act | $(& $cell $Who) | $(& $cell $Why) | $(& $cell $FromPath) | $(& $cell $ToPath) | $Size |`r`n"
    [IO.File]::AppendAllText($lf, $line, $enc)
}

function Open-Locked([string]$File) {
    # same lock as Add-StepLine: write access for us, read-only sharing for others; retry while another writer holds it
    for ($i = 0; $i -lt 40; $i++) {
        try { return [IO.File]::Open($File, [IO.FileMode]::Open, [IO.FileAccess]::ReadWrite, [IO.FileShare]::Read) }
        catch [System.IO.IOException] { Start-Sleep -Milliseconds 25 }
    }
    throw "ERROR: could not lock '$File' (another writer holds it); nothing was moved from it - run purge again."
}

function Invoke-Purge([string]$R) {
    $pg = Get-CfCfg 'steplog'
    $on = Get-CfProp $pg 'purge_enabled'
    if ($null -ne $on -and -not [bool]$on) { throw "REFUSED: purge is off (steplog.purge_enabled = false in .workflow/workflow.config.json); remove old log files with the project's own cleanup route." }
    if ($Days -eq -1) { $Days = [int](Get-CfCfgNumber 'steplog' 'purge_days' 90) }
    if ($Days -lt 1 -or $Days -gt 3650) { throw "REFUSED: -Days must be between 1 and 3650 (got $Days)." }
    $who = ''
    if (-not $DryRun) {
        if (-not $As) { throw "REFUSED: -As <session title> is required for purge (it is the By column of $($script:TR)/TRASH-LOG.md); -DryRun only lists." }
        $who = Get-CleanText 'As' $As 60
    }
    $now = Get-Date
    $cut = $now.Date.AddDays(-$Days)          # items dated before this day move; this day and newer stay
    $stamp = $now.ToString('yyyyMMdd', $script:Inv)
    $why = "$($script:LG) retention $Days days"
    $trashBase = Join-Path (Get-CfCfgPath $R 'trash') "$stamp\$((Get-CfCfgRel 'process_log').Replace('/', '\'))"
    $tag = if ($DryRun) { 'would move' } else { 'moved' }
    $nLines = 0; $nFiles = 0; $nTurns = 0

    # --- step lines: whole pairs only (start + end, wait + resume) whose newer event is before the cut-off, plus
    #     orphan end / resume / repeated start / repeated wait before the cut-off. Open starts / waits stay.
    $all = Read-StepEvents $R $null $null (Get-AliasMap $R)
    $p = Get-Pairs $all.Events
    $sel = New-Object System.Collections.ArrayList
    foreach ($s in $p.Steps) { $t = if ($s.EndEv.At -gt $s.StartEv.At) { $s.EndEv.At } else { $s.StartEv.At }; if ($t -lt $cut) { [void]$sel.Add($s.StartEv); [void]$sel.Add($s.EndEv) } }
    foreach ($w in $p.Waits) { $t = if ($w.ResumeEv.At -gt $w.WaitEv.At) { $w.ResumeEv.At } else { $w.WaitEv.At }; if ($t -lt $cut) { [void]$sel.Add($w.WaitEv); [void]$sel.Add($w.ResumeEv) } }
    $orphan = @('end without start', 'resume without wait', 'start again while open', 'wait while waiting')
    foreach ($u in $p.Unpaired) { if ($orphan -contains $u.Kind -and $u.Ev.At -lt $cut) { [void]$sel.Add($u.Ev) } }
    $keptOpen = @($p.Unpaired | Where-Object { @('start without end', 'wait without resume') -contains $_.Kind -and $_.Ev.At -lt $cut }).Count

    $byFile = @{}
    foreach ($e in $sel) { if (-not $byFile.ContainsKey($e.File)) { $byFile[$e.File] = @{} }; $byFile[$e.File][[int]$e.Line] = $e.Text }
    $stepDir = Get-LogDir $R
    foreach ($name in @($byFile.Keys | Sort-Object)) {
        $lines = $byFile[$name]
        $src = Join-Path $stepDir $name
        $dst = Join-Path $trashBase "steps\$name"
        if ($DryRun) {
            Write-Output "  $tag $($lines.Count) step line(s): $($script:LG)/steps/$name -> $($script:TR)/$stamp/$($script:LG)/steps/$name"
            $nLines += $lines.Count; $nFiles++; continue
        }
        $fs = Open-Locked $src
        try {
            $buf = New-Object byte[] ([int]$fs.Length)
            $read = 0; while ($read -lt $buf.Length) { $k = $fs.Read($buf, $read, $buf.Length - $read); if ($k -le 0) { break }; $read += $k }
            $cur = $script:U8.GetString($buf, 0, $read).Replace("`r`n", "`n").Split("`n")
            foreach ($no in $lines.Keys) {
                if ($no -gt $cur.Length -or $cur[$no - 1] -ne $lines[$no]) { throw "ERROR: $($script:LG)/steps/$name changed while purge ran (line $no); nothing was moved from it - run purge again." }
            }
            # 1. copy the lines to the trash (append; restorable), re-read
            $moved = New-Object System.Text.StringBuilder
            foreach ($no in @($lines.Keys | Sort-Object)) { [void]$moved.Append($lines[$no] + "`n") }
            [void][IO.Directory]::CreateDirectory((Split-Path -Parent $dst))
            [IO.File]::AppendAllText($dst, $moved.ToString(), $script:U8)
            if (-not ([IO.File]::ReadAllText($dst, $script:U8)).Contains($moved.ToString())) { throw "ERROR: re-read of '$dst' does not contain the moved lines; $name left unchanged." }
            # 2. rewrite the month file without them (under the lock)
            $keep = New-Object System.Text.StringBuilder
            for ($i = 0; $i -lt $cur.Length; $i++) { if (-not $lines.ContainsKey($i + 1) -and $cur[$i].Trim() -ne '') { [void]$keep.Append($cur[$i] + "`n") } }
            $kb = $script:U8.GetBytes($keep.ToString())
            [void]$fs.Seek(0, [IO.SeekOrigin]::Begin); $fs.SetLength(0); $fs.Write($kb, 0, $kb.Length); $fs.Flush()
        }
        finally { $fs.Dispose() }
        if ([IO.File]::ReadAllText($src, $script:U8) -ne $keep.ToString()) { throw "ERROR: re-read of '$src' differs after the rewrite (the moved lines are safe in '$dst')." }
        Add-TrashLog $R $now 'MoveLines' $who $why $src $dst "$($lines.Count) lines, $(Format-Size $script:U8.GetByteCount($moved.ToString()))"
        Write-Output "  $tag $($lines.Count) step line(s): $($script:LG)/steps/$name -> $($script:TR)/$stamp/$($script:LG)/steps/$name"
        $nLines += $lines.Count; $nFiles++
    }

    # --- turn day files dated before the cut-off: the whole file moves
    $turnDir = Join-Path (Get-CfCfgPath $R 'process_log') 'turns'
    foreach ($name in @(Get-PathList -In $turnDir -Filter '*.jsonl')) {
        if ($name -notmatch '^(\d{4}-\d{2}-\d{2})\.jsonl$') { continue }
        $d = [datetime]::MinValue
        if (-not [datetime]::TryParseExact($Matches[1], 'yyyy-MM-dd', $script:Inv, [Globalization.DateTimeStyles]::None, [ref]$d)) { continue }
        if ($d -ge $cut) { continue }
        $src = Join-Path $turnDir $name
        $dst = Join-Path $trashBase "turns\$name"
        $n = 2; while ([IO.File]::Exists($dst)) { $dst = Join-Path $trashBase ("turns\" + [IO.Path]::GetFileNameWithoutExtension($name) + "-$n.jsonl"); $n++ }
        if ($DryRun) { Write-Output "  $tag turn file: $($script:LG)/turns/$name -> $($script:TR)/$stamp/$($script:LG)/turns/$([IO.Path]::GetFileName($dst))"; $nTurns++; continue }
        $size = (New-Object IO.FileInfo $src).Length
        [void][IO.Directory]::CreateDirectory((Split-Path -Parent $dst))
        try { [IO.File]::Move($src, $dst) }
        catch { Write-Output "  skipped (in use, try again later): $($script:LG)/turns/$name"; continue }
        Add-TrashLog $R $now 'Move' $who $why $src $dst (Format-Size $size)
        Write-Output "  $tag turn file: $($script:LG)/turns/$name -> $($script:TR)/$stamp/$($script:LG)/turns/$([IO.Path]::GetFileName($dst))"
        $nTurns++
    }

    $head = if ($DryRun) { 'DRY RUN (nothing changed)' } else { 'OK' }
    Write-Output "$($head): purge -Days $Days (cut-off $($cut.ToString('yyyy-MM-dd', $script:Inv)), older items $tag): $nLines step line(s) from $nFiles month file(s), $nTurns turn file(s)$(if (-not $DryRun -and ($nLines + $nTurns) -gt 0) { " -> $($script:TR)/$stamp/$($script:LG)/ (logged in $($script:TR)/TRASH-LOG.md)" })"
    if ($keptOpen -gt 0) { Write-Output "note: $keptOpen open start / wait older than the cut-off kept (no half pairs); close them or they stay." }
}

Invoke-CfMain {
    $R = Resolve-CfRoot $Root $PSScriptRoot
    $script:LG = Get-CfCfgRel 'process_log'; $script:TR = Get-CfCfgRel 'trash'
    $a = ''; if ($Action) { $a = $Action.ToLowerInvariant() }
    switch ($a) {
        'start' { Invoke-Start $R }
        'end' { Invoke-End $R }
        'wait' { Invoke-Wait $R $false }
        'resume' { Invoke-Wait $R $true }
        'report' { Invoke-Report $R }
        'purge' { Invoke-Purge $R }
        default { throw "REFUSED: action '$Action' is not start, end, wait, resume, report or purge." }
    }
}
exit (Get-CfExitCode)
