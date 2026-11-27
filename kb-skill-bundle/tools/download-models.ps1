<#
  Tải model cho bộ skill KB (dành cho bộ phận IT). Chỉ PowerShell 7 (pwsh); Windows PowerShell 5.1 bị từ chối (2.0.4).
  Mặc định chỉ in kế hoạch (không tải gì). Làm thật: thêm -Apply.

  3 cách dùng (chạy từ thư mục gói):
    1) Đặt thẳng vào dự án (máy dự án có mạng):
       pwsh -NoProfile -ExecutionPolicy Bypass -File tools\download-models.ps1 -Target "D:\work\demo" -Apply [-Proxy http://proxy:8080]
    2) Máy có mạng: tải và đóng 1 file zip (sha256 trong manifest được phép để trống; script in mã đã tính để IT đối chiếu):
       pwsh -NoProfile -ExecutionPolicy Bypass -File tools\download-models.ps1 -Zip "E:\KB-Model_multilingual-e5-small_20260105.zip" -Apply
    3) Máy dự án: đặt model từ file zip đó (kiểm an toàn + sha256 theo MODEL.txt):
       pwsh -NoProfile -ExecutionPolicy Bypass -File tools\download-models.ps1 -Target "D:\work\demo" -FromZip "E:\KB-Model_<...>.zip" -Apply
    -FromFolder <thư mục>: dùng file đã tải sẵn thay cho tải qua mạng (cách 1 và 2).

  Quy tắc:
  - Cách 1: IT điền "sha256" của từng file trong tools\models.manifest.json trước; còn file thiếu mã -> dừng, không tải.
  - Chỉ nhận địa chỉ https và file .onnx / .json. Tải vào file tạm, kiểm dung lượng + SHA256, đạt mới dùng.
  - Nơi đặt: <Target>\.qkb\models\<tên model>\ kèm MODEL.txt (dòng "<đường dẫn>  sha256 <mã>", engine kiểm theo file này).
  - Mã thoát: 0 xong / chỉ in kế hoạch · 1 kiểm không đạt · 2 sai tham số, manifest chưa điền đủ, zip không hợp lệ.
#>
param(
    [string] $Target = '.',
    [string] $Model = '',
    [string] $Manifest = '',
    [string] $Proxy = '',
    [string] $FromFolder = '',
    [string] $Zip = '',
    [string] $FromZip = '',
    [switch] $Apply
)
if ($PSVersionTable.PSVersion.Major -lt 7) {
    Write-Output 'REFUSED: download-models.ps1 needs PowerShell 7 (pwsh); run: pwsh -NoProfile -File tools\download-models.ps1 ...'
    exit 1
}
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Manifest) { $Manifest = Join-Path $here 'models.manifest.json' }
$utf8 = New-Object System.Text.UTF8Encoding($false)

function Fail([int] $Code, [string] $Text) { Write-Host $Text -ForegroundColor Red; exit $Code }

function Sha256Of([string] $Path) {
    # .NET hashing (no module needed): works also when PowerShell 5.1 is started from PowerShell 7
    $stream = [System.IO.File]::OpenRead($Path)
    try { $sha = [System.Security.Cryptography.SHA256]::Create(); return ([System.BitConverter]::ToString($sha.ComputeHash($stream)) -replace '-', '').ToLowerInvariant() }
    finally { $stream.Dispose() }
}

# ---- 3) -FromZip: one implementation for every caller (tools\kbmodel.py, also used by install.py --model-zip)
if ($FromZip) {
    if (-not (Test-Path -LiteralPath $Target -PathType Container)) { Fail 2 ('LỖI: không thấy thư mục dự án: ' + $Target) }
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
    if (-not $py) { Fail 2 'LỖI: cần Python 3.10 trở lên (bộ skill KB đã cần sẵn).' }
    $pyArgs = @('-E', '-s', '-B', (Join-Path $here 'kbmodel.py'), 'from-zip', $FromZip, '--target', $Target)
    if ($Apply) { $pyArgs += '--apply' }
    & $py.Source @pyArgs
    exit $LASTEXITCODE
}

try { $m = Get-Content -LiteralPath $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json } catch { Fail 2 ('LỖI: không đọc được ' + $Manifest) }
if (-not $Model) { $Model = $m.default }
$entry = $m.models.$Model
if (-not $entry) { Fail 2 ('LỖI: manifest không có model "' + $Model + '".') }
$allowed = @($m.allowed_extensions)

if ($Zip) {
    if ([System.IO.Path]::GetExtension($Zip).ToLowerInvariant() -ne '.zip') { Fail 2 'LỖI: -Zip cần đường dẫn file .zip.' }
    $zipFull = [System.IO.Path]::GetFullPath($Zip)
    $dest = $zipFull + '.work'
    $folder = Join-Path $dest $entry.dest
} else {
    if (-not (Test-Path -LiteralPath $Target -PathType Container)) { Fail 2 ('LỖI: không thấy thư mục dự án: ' + $Target) }
    $targetFull = (Resolve-Path -LiteralPath $Target).ProviderPath
    $folder = Join-Path (Join-Path (Join-Path $targetFull '.qkb') 'models') $entry.dest
}

# Kiểm manifest trước khi tải: đuôi file, đường dẫn, https, sha256 (bắt buộc trừ chế độ -Zip)
$missing = @()
foreach ($f in $entry.files) {
    $ext = [System.IO.Path]::GetExtension($f.path).ToLowerInvariant()
    if ($allowed -notcontains $ext) { Fail 2 ('LỖI: đuôi file không được phép: ' + $f.path) }
    if ($f.path -match '(^|[\\/])\.\.([\\/]|$)' -or [System.IO.Path]::IsPathRooted($f.path)) { Fail 2 ('LỖI: đường dẫn không hợp lệ: ' + $f.path) }
    if ($f.url -notmatch '^https://') { Fail 2 ('LỖI: chỉ nhận địa chỉ https: ' + $f.url) }
    if (-not ($f.sha256 -match '^[0-9a-fA-F]{64}$')) { $missing += $f.path }
}

Write-Host ('TẢI MODEL — ' + $Model + $(if ($Zip) { ' → zip' } else { '' }) + $(if ($Apply) { '' } else { ' — KẾ HOẠCH (chưa tải gì)' }))
Write-Host ('Nguồn: ' + $entry.source_page + ' · Giấy phép: ' + $entry.licence)
Write-Host $(if ($Zip) { 'File zip: ' + $zipFull } else { 'Nơi đặt: ' + $folder })
foreach ($f in $entry.files) {
    Write-Host ('  - ' + $f.path + ' (~' + $f.approx_mb + ' MB' + $(if ($f.required) { ', bắt buộc' } else { ', nên có' }) + ')')
}
if ($missing.Count -gt 0 -and -not $Zip) {
    Fail 2 ('DỪNG: chưa điền sha256 cho ' + $missing.Count + ' file trong ' + $Manifest + ': ' + ($missing -join ', ') + '. Lấy mã trên trang nguồn rồi chạy lại (hoặc dùng -Zip).')
}
if (-not $Apply) { Write-Host 'Để làm thật: chạy lại kèm -Apply'; exit 0 }

function Size-Ok($f, [long] $bytes) {
    if ($f.bytes) { return $bytes -eq [long] $f.bytes }
    $mb = [double] $f.approx_mb
    $max = $mb * 1.15 * 1MB
    $min = $(if ($mb -ge 10) { $mb * 0.85 * 1MB } else { 1 })
    return ($bytes -ge $min -and $bytes -le $max)
}

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$fails = 0
$got = @{}
if ($Zip -and (Test-Path -LiteralPath $dest)) { Remove-Item -LiteralPath $dest -Recurse -Force }
foreach ($f in $entry.files) {
    $final = Join-Path $folder ($f.path -replace '/', [IO.Path]::DirectorySeparatorChar)
    $partial = $final + '.partial'
    [void] (New-Item -ItemType Directory -Force -Path (Split-Path -Parent $final))
    $want = $(if ($f.sha256 -match '^[0-9a-fA-F]{64}$') { $f.sha256.ToLowerInvariant() } else { '' })
    if ((Test-Path -LiteralPath $final) -and $want) {
        if ((Sha256Of $final) -eq $want) { Write-Host ('  ĐÃ CÓ, đúng mã: ' + $f.path); $got[$f.path] = $want; continue }
        Write-Host ('  CÓ SẴN nhưng khác mã, tải lại: ' + $f.path)
    }
    try {
        if ($FromFolder) {
            Copy-Item -LiteralPath (Join-Path $FromFolder ($f.path -replace '/', [IO.Path]::DirectorySeparatorChar)) -Destination $partial -Force
        } else {
            $req = @{ Uri = $f.url; OutFile = $partial; UseBasicParsing = $true }
            if ($Proxy) { $req.Proxy = $Proxy; $req.ProxyUseDefaultCredentials = $true }
            Invoke-WebRequest @req
        }
    } catch {
        if (Test-Path -LiteralPath $partial) { Remove-Item -LiteralPath $partial -Force }
        Write-Host ('  LỖI tải: ' + $f.path + ' (' + $_.Exception.Message + ')') -ForegroundColor Red; $fails++; continue
    }
    $bytes = (Get-Item -LiteralPath $partial).Length
    $hash = (Sha256Of $partial)
    if (-not (Size-Ok $f $bytes)) {
        Remove-Item -LiteralPath $partial -Force
        Write-Host ('  KHÔNG ĐẠT dung lượng: ' + $f.path + ' (' + $bytes + ' byte)') -ForegroundColor Red; $fails++; continue
    }
    if ($want -and $hash -ne $want) {
        Remove-Item -LiteralPath $partial -Force
        Write-Host ('  KHÔNG ĐẠT SHA256: ' + $f.path) -ForegroundColor Red; $fails++; continue
    }
    Move-Item -LiteralPath $partial -Destination $final -Force
    $got[$f.path] = $hash
    Write-Host ('  ĐẠT: ' + $f.path + ' (' + $bytes + ' byte) sha256 ' + $hash + $(if ($want) { '' } else { '  <- IT đối chiếu với trang nguồn' }))
}
if ($fails -gt 0) {
    if ($Zip -and (Test-Path -LiteralPath $dest)) { Remove-Item -LiteralPath $dest -Recurse -Force }
    Write-Host ('CHƯA XONG: ' + $fails + ' file không đạt (xem trên). Không ghi MODEL.txt / zip.') -ForegroundColor Red
    exit 1
}
$lines = @('model: ' + $Model, 'source: ' + $entry.source_page, 'revision: ' + $entry.revision, 'licence: ' + $entry.licence,
           'downloaded: ' + (Get-Date).ToString('yyyy-MM-dd HH:mm'))
foreach ($f in $entry.files) {
    $p = Join-Path $folder ($f.path -replace '/', [IO.Path]::DirectorySeparatorChar)
    $lines += ($f.path + '  sha256 ' + $got[$f.path])     # exactly the line form the engine reads
}
[System.IO.File]::WriteAllLines((Join-Path $folder 'MODEL.txt'), [string[]] $lines, $utf8)
if (-not $Zip) { Write-Host ('XONG: mọi file đạt. Ghi lại ở ' + (Join-Path $folder 'MODEL.txt')); exit 0 }
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
if (Test-Path -LiteralPath $zipFull) { Remove-Item -LiteralPath $zipFull -Force }
[void] (New-Item -ItemType Directory -Force -Path (Split-Path -Parent $zipFull))
# entry names with "/" on every .NET version (PowerShell 5.1 may write "\" with CreateFromDirectory)
$archive = [System.IO.Compression.ZipFile]::Open($zipFull, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($file in (Get-ChildItem -LiteralPath $dest -Recurse -File)) {
        $name = $file.FullName.Substring($dest.Length).TrimStart('\', '/') -replace '\\', '/'
        [void] [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $file.FullName, $name,
                                                                              [System.IO.Compression.CompressionLevel]::Optimal)
    }
} finally { $archive.Dispose() }
Remove-Item -LiteralPath $dest -Recurse -Force
Write-Host ('XONG: ' + $zipFull + ' · sha256 ' + (Sha256Of $zipFull))
Write-Host 'IT đối chiếu mã sha256 từng file ở trên với trang nguồn trước khi chuyển zip sang máy dự án.'
Write-Host ('Máy dự án: download-models.ps1 -Target <dự án> -FromZip "' + $zipFull + '" -Apply  (hoặc install.py --model local --model-zip <zip>)')
exit 0
