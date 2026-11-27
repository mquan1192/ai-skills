# Test hooks/stylewatch.py (Python unittest) + keywords of config/style.config.example.json (v1.1). Run with PowerShell 7 (pwsh) or Windows PowerShell 5.1. Exit 0 = PASS.
# STYLEWATCH_EXAMPLE_CONFIG=<path> checks another example config (red proof: the v1.0.1 config must FAIL). STYLEWATCH_HOOK=<path> uses another hook file.
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$hooks = Join-Path $root 'hooks'
$fail = $false

$out = @(& python -E -s -B (Join-Path $hooks 'test_stylewatch.py') 2>&1 | ForEach-Object { [string]$_ })
$code = $LASTEXITCODE
$out | Select-Object -Last 3 | ForEach-Object { Write-Output $_ }
if ($code -ne 0) { Write-Output '  FAIL python unittest'; $fail = $true } else { Write-Output '  PASS python unittest' }

# keywords of the example config: 12 old keywords first (same order), then the 9 new ones (ASCII source: code points)
function C([string]$hex) { return (-join ($hex.Split(' ') | ForEach-Object { [char][Convert]::ToInt32($_, 16) })) }
$old = @((C '0062 00e1 006f 0020 0063 00e1 006f'), 'report', (C '0074 00e0 0069 0020 006c 0069 1ec7 0075'), (C '0062 0069 00ea 006e 0020 0062 1ea3 006e'), 'mail', 'chat', 'jira', 'ticket', (C '5831 544a 66f8'), (C '8cc7 6599'), (C '30e1 30fc 30eb'), (C '8b70 4e8b 9332'))
$new = @((C '0064 1ecb 0063 0068'), (C '7ffb 8a33'), (C '8a33'), 'translate', 'slide', 'pptx', 'powerpoint', (C '8a2d 8a08 66f8'), (C '5831 544a'))
$cfgPath = $env:STYLEWATCH_EXAMPLE_CONFIG
if (-not $cfgPath) { $cfgPath = Join-Path $root 'config\style.config.example.json' }
$kw = @()
try {
    $u8 = New-Object System.Text.UTF8Encoding($false, $true)
    $kw = @((ConvertFrom-Json ([System.IO.File]::ReadAllText($cfgPath, $u8))).prompt_reminder.keywords)
} catch { Write-Output "  FAIL cannot read $cfgPath : $($_.Exception.Message)"; $fail = $true }
$want = @($old) + @($new)
if (($kw -join '|') -ceq ($want -join '|')) { Write-Output "  PASS example config keywords: $($old.Count) old + $($new.Count) new, order kept" }
else { Write-Output "  FAIL example config keywords (got $($kw.Count), want $($want.Count))"; $fail = $true }

if ($fail) { Write-Output 'RESULT FAIL'; exit 1 }
Write-Output 'RESULT PASS'
exit 0
