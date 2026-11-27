# structure.Tests.ps1 - kiểm cấu trúc skill q-writing-style của gói văn phong (chỉ đọc). Chạy bằng PowerShell 7:
#   pwsh -NoProfile -File .\structure.Tests.ps1 [-SkillDir <thư mục skill>] [-TermsFile <danh sách từ riêng của dự án>]
# -TermsFile (tùy chọn, để ngoài gói): mỗi dòng một từ; có thì kiểm skill + evals không chứa từ nào trong đó.
param([string]$SkillDir = (Join-Path $PSScriptRoot '..'), [string]$TermsFile = '')
Set-StrictMode -Version 2
$ErrorActionPreference = 'Continue'
$script:Fails = 0; $script:Count = 0

function Check([string]$Name, [bool]$Ok, [string]$Info = '') {
    $script:Count++
    if (-not $Ok) { $script:Fails++ }
    $mark = if ($Ok) { 'PASS' } else { 'FAIL' }
    $tail = if ($Info -and -not $Ok) { "  [$Info]" } else { '' }
    Write-Output "  $mark $Name$tail"
}

$Utf8 = New-Object System.Text.UTF8Encoding($false, $true)
function Read-Text([string]$Path) { return [System.IO.File]::ReadAllText($Path, $Utf8) }

$SkillDir = (Resolve-Path -LiteralPath $SkillDir).Path
$Files = [ordered]@{
    'SKILL.md'                            = (Join-Path $SkillDir 'SKILL.md')
    'references/style-guide.md'           = (Join-Path $SkillDir 'references/style-guide.md')
    'references/document-patterns.md'     = (Join-Path $SkillDir 'references/document-patterns.md')
    'references/before-after-examples.md' = (Join-Path $SkillDir 'references/before-after-examples.md')
    'references/ng-vocab-vi.md'           = (Join-Path $SkillDir 'references/ng-vocab-vi.md')
    'references/ng-vocab-ja.md'           = (Join-Path $SkillDir 'references/ng-vocab-ja.md')
    'references/ng-vocab-en.md'           = (Join-Path $SkillDir 'references/ng-vocab-en.md')
    'references/ai-tells.md'              = (Join-Path $SkillDir 'references/ai-tells.md')
    'references/plain-language.md'        = (Join-Path $SkillDir 'references/plain-language.md')
    'references/vietnamese-register.md'   = (Join-Path $SkillDir 'references/vietnamese-register.md')
    'references/translation.md'           = (Join-Path $SkillDir 'references/translation.md')
    'references/voice-profile.md'         = (Join-Path $SkillDir 'references/voice-profile.md')
}
$EvalPath = Join-Path $SkillDir 'evals/evals.json'
$TrigPath = Join-Path $SkillDir 'evals/trigger.json'
Write-Output "structure.Tests.ps1 - $SkillDir"

# 1. Tệp có đủ, UTF-8 hợp lệ
$Text = @{}
foreach ($k in $Files.Keys) {
    $p = $Files[$k]; $ok = Test-Path -LiteralPath $p -PathType Leaf; $info = 'missing'
    if ($ok) { try { $Text[$k] = Read-Text $p; $info = '' } catch { $ok = $false; $info = 'not valid UTF-8' } }
    Check "file $k exists, UTF-8" $ok $info
}
if ($Text.Count -ne $Files.Count) { Write-Output "RESULT structure: $($script:Fails) FAIL / $($script:Count) checks"; exit 1 }

# 2. Frontmatter và mô tả (tự kích hoạt khi viết báo cáo / tài liệu)
$skill = $Text['SKILL.md'] -replace "`r`n", "`n"
$lines = @($skill -split "`n")
$end = -1
if ($lines.Count -gt 0 -and $lines[0] -eq '---') { for ($i = 1; $i -lt $lines.Count; $i++) { if ($lines[$i] -eq '---') { $end = $i; break } } }
Check 'SKILL.md starts with a closed YAML frontmatter' ($end -gt 1)
$fm = @{}
if ($end -gt 1) { foreach ($l in $lines[1..($end - 1)]) { if ($l -match '^([a-z][a-z0-9-]*):\s?(.*)$') { $fm[$Matches[1]] = $Matches[2] } } }
Check 'frontmatter name = q-writing-style' ($fm.ContainsKey('name') -and $fm['name'].Trim() -eq 'q-writing-style')
$desc = if ($fm.ContainsKey('description')) { $fm['description'].Trim() } else { '' }
Check 'description present, 100..520 chars, one line' ($desc.Length -ge 100 -and $desc.Length -le 520) ("length $($desc.Length)")
$need = @('VI / JA / EN', 'báo cáo', 'report', 'tài liệu', 'mail', 'biên bản', 'chat', 'Jira', '報告書', '資料', 'メール', 'Keywords:', 'Không dùng cho:')
$miss = @($need | Where-Object { $desc -notmatch [regex]::Escape($_) })
Check 'description has languages, report keywords and a "Không dùng cho" clause' ($miss.Count -eq 0) ('missing: ' + ($miss -join ', '))
Check 'SKILL.md has a "Ranh giới" section' ($skill -match '(?m)^## Ranh giới$')

# 3. SKILL.md ngắn, trỏ đúng mọi tệp tham khảo
$bodyLines = $lines.Count - $end - 1
Check 'SKILL.md body <= 120 lines' ($bodyLines -le 120) ("$bodyLines lines")
Check 'SKILL.md <= 10 KB' ([Text.Encoding]::UTF8.GetByteCount($Text['SKILL.md']) -le 10240)
$refs = @([regex]::Matches($skill, 'references/[a-z0-9-]+\.md') | ForEach-Object { $_.Value } | Sort-Object -Unique)
$bad = @($refs | Where-Object { -not $Files.Contains($_) })
Check 'every reference named in SKILL.md exists' ($bad.Count -eq 0) ('unknown: ' + ($bad -join ', '))
$unref = @($Files.Keys | Where-Object { $_ -ne 'SKILL.md' -and $refs -notcontains $_ })
Check 'every reference file is named in SKILL.md' ($unref.Count -eq 0) ('not named: ' + ($unref -join ', '))
$must = @('Đúng → Đủ → Rõ → Gọn → Tự nhiên', 'Polish', 'Restructure', 'Summarize', 'Rewrite', 'Translate',
    'Humanize', 'Plain', 'Voice', 'Check', 'Cổng tự soát', 'Quy tắc dự án được ưu tiên', 'project_rules', 'glossary', 'Khi viết báo cáo / tài liệu')
$miss = @($must | Where-Object { $skill -notmatch [regex]::Escape($_) })
Check 'SKILL.md has priority order, 9 modes, self-check gate, project rules, report trigger' ($miss.Count -eq 0) ('missing: ' + ($miss -join ', '))

# 4. Khung báo cáo tiếng Việt (§ 1.1) có trong style guide
$sg = $Text['references/style-guide.md']
$must = @('### 1.1', 'Nhận xét:', 'Kết luận:', 'Định hướng:', '1.234,5', 'dd/mm/yyyy', 'trung tính')
$miss = @($must | Where-Object { $sg -notmatch [regex]::Escape($_) })
Check 'style guide § 1.1: neutral tone, report frame, VN numbers and dates' ($miss.Count -eq 0) ('missing: ' + ($miss -join ', '))

# 5. Không dữ liệu dự án (khi có -TermsFile) và không lặp quy tắc giữa các tệp
$evalText = ''; try { $evalText = Read-Text $EvalPath } catch { }
$trigText = ''; try { $trigText = Read-Text $TrigPath } catch { }
if ($TermsFile) {
    # cùng luật với tools/scan_terms.py: từ thường = chứa chuỗi; '=từ' = cả từ; không phân biệt hoa thường
    $terms = @(Get-Content -LiteralPath $TermsFile -Encoding utf8 | ForEach-Object { $_.Trim() } | Where-Object { $_ -and -not $_.StartsWith('#') })
    $hits = @()
    $blobs = @{} + $Text; $blobs['evals.json'] = $evalText; $blobs['trigger.json'] = $trigText
    foreach ($k in $blobs.Keys) {
        $body = $blobs[$k].Normalize([Text.NormalizationForm]::FormC)
        foreach ($t in $terms) {
            $word = $t.StartsWith('=')
            $w = [regex]::Escape($t.TrimStart('=').Normalize([Text.NormalizationForm]::FormC))
            $re = if ($word) { '(?<![\w])' + $w + '(?![\w])' } else { $w }
            if ([regex]::IsMatch($body, $re, 'IgnoreCase')) { $hits += "$k ($($t.TrimStart('=')))" }
        }
    }
    Check 'no project term in skill files and evals' ($hits.Count -eq 0) (@($hits | Select-Object -First 5) -join ', ')
}
$seen = @{}; $dups = @()
foreach ($k in $Files.Keys) {
    $set = @{}
    foreach ($l in @(($Text[$k] -replace "`r`n", "`n") -split "`n")) {
        $t = $l.Trim()
        if ($t.Length -lt 40 -or $set.ContainsKey($t)) { continue }
        $set[$t] = 1
        if ($seen.ContainsKey($t)) { $dups += "$($seen[$t]) + $k" } else { $seen[$t] = $k }
    }
}
Check 'no line repeated across skill files' ($dups.Count -eq 0) (@($dups | Select-Object -First 3) -join '; ')

# 6. Bộ thử chất lượng (evals.json)
$ev = $null; try { $ev = $evalText | ConvertFrom-Json } catch { }
Check 'evals.json parses' ($null -ne $ev)
if ($null -ne $ev) {
    $cases = @($ev.cases)
    Check 'evals.json has >= 10 cases' ($cases.Count -ge 10) ("$($cases.Count) cases")
    $ids = @($cases | ForEach-Object { $_.id })
    Check 'case ids unique' (@($ids | Sort-Object -Unique).Count -eq $ids.Count)
    $probs = @(); $checkIds = @()
    foreach ($c in $cases) {
        if (-not $c.input -or -not $c.prompt) { $probs += "$($c.id): empty input / prompt" }
        $ck = @($c.checks)
        foreach ($x in $ck) { $checkIds += $x.id }
        foreach ($kd in @('meaning', 'numbers')) { if (@($ck | Where-Object { $_.kind -eq $kd }).Count -eq 0) { $probs += "$($c.id): no $kd check" } }
        if (@($ck | Where-Object { $_.must -eq $true }).Count -lt 2) { $probs += "$($c.id): < 2 must-keep checks" }
    }
    Check 'every case has input, prompt, meaning + numbers checks, >= 2 must checks' ($probs.Count -eq 0) (@($probs | Select-Object -First 4) -join '; ')
    Check 'check ids unique' (@($checkIds | Sort-Object -Unique).Count -eq $checkIds.Count)
}

# 7. Bộ thử kích hoạt (trigger.json): >= 10 nên gọi, >= 5 gần giống không nên gọi
$tr = $null; try { $tr = $trigText | ConvertFrom-Json } catch { }
Check 'trigger.json parses' ($null -ne $tr)
if ($null -ne $tr) {
    $pos = @($tr.should_trigger); $neg = @($tr.near_miss)
    Check 'trigger: >= 10 should_trigger' ($pos.Count -ge 10) ("$($pos.Count)")
    Check 'trigger: >= 5 near_miss with expect' ($neg.Count -ge 5 -and @($neg | Where-Object { -not $_.expect }).Count -eq 0) ("$($neg.Count)")
    $joined = ($pos | ForEach-Object { [string]$_ }) -join "`n"
    $miss = @(@('báo cáo', '報告書|資料|メール') | Where-Object { $joined -notmatch $_ })
    Check 'trigger: report prompts in VI and JA' ($miss.Count -eq 0) ('missing: ' + ($miss -join ', '))
}

Write-Output "RESULT structure: $($script:Fails) FAIL / $($script:Count) checks (PS $($PSVersionTable.PSVersion))"
if ($script:Fails -gt 0) { exit 1 }
exit 0
