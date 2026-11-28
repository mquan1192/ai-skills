#!/bin/sh
# Tải model cho bộ skill KB (dành cho bộ phận IT). macOS / Linux. Cần: Python 3.10+ (python3 hoặc python), curl.
# Lệnh Python: tự dò python3 rồi python; chỉ định lệnh khác bằng biến KB_PYTHON (ví dụ KB_PYTHON=/opt/venv/bin/python).
# Mặc định chỉ in kế hoạch (không tải gì). Làm thật: thêm --apply.
#
#   1) Đặt thẳng vào dự án:  sh tools/download-models.sh --target /work/demo --apply [--proxy http://proxy:8080]
#   2) Máy có mạng → 1 zip:  sh tools/download-models.sh --zip /tmp/KB-Model_multilingual-e5-small_20260105.zip --apply
#      (sha256 trong manifest được để trống; script in mã đã tính để IT đối chiếu với trang nguồn)
#   3) Máy dự án, từ zip:    sh tools/download-models.sh --target /work/demo --from-zip /tmp/KB-Model_<...>.zip --apply
#   --from <thư mục>: dùng file đã tải sẵn thay cho tải qua mạng (cách 1 và 2). --model <tên>: model khác trong manifest.
#
# Quy tắc như bản PowerShell: cách 1 cần sha256 điền sẵn; chỉ https và .onnx / .json; tải vào .partial, kiểm dung lượng
# + SHA256; MODEL.txt có dòng "<đường dẫn>  sha256 <mã>" (engine kiểm theo file này).
# Mã thoát: 0 xong / chỉ in kế hoạch · 1 kiểm không đạt · 2 sai tham số, manifest chưa điền đủ, zip không hợp lệ.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
TARGET=.
MODEL=
PROXY=
APPLY=0
FROM=
ZIP=
FROMZIP=
MANIFEST="$HERE/models.manifest.json"
while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET=$2; shift 2 ;;
    --model) MODEL=$2; shift 2 ;;
    --proxy) PROXY=$2; shift 2 ;;
    --manifest) MANIFEST=$2; shift 2 ;;
    --apply) APPLY=1; shift ;;
    --from) FROM=$2; shift 2 ;;
    --zip) ZIP=$2; shift 2 ;;
    --from-zip) FROMZIP=$2; shift 2 ;;
    *) echo "LỖI: tham số không hiểu: $1" >&2; exit 2 ;;
  esac
done

# Python launcher: KB_PYTHON when set, else the first of python3 / python that really runs Python 3.10+
# (a missing name, Python 2 and an old Python 3 are skipped).
PY=
if [ -n "${KB_PYTHON:-}" ]; then set -- "$KB_PYTHON"; else set -- python3 python; fi
for c in "$@"; do
  if "$c" -E -s -B -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then PY=$c; break; fi
done
[ -n "$PY" ] || { echo "LỖI: cần Python 3.10 trở lên (đã thử: $*). Đặt KB_PYTHON=<lệnh hoặc đường dẫn>." >&2; exit 2; }

# 3) --from-zip: one implementation for every caller (tools/kbmodel.py, also used by install.py --model-zip)
if [ -n "$FROMZIP" ]; then
  [ -d "$TARGET" ] || { echo "LỖI: không thấy thư mục dự án: $TARGET" >&2; exit 2; }
  if [ "$APPLY" = 1 ]; then
    exec "$PY" -E -s -B "$HERE/kbmodel.py" from-zip "$FROMZIP" --target "$TARGET" --apply
  fi
  exec "$PY" -E -s -B "$HERE/kbmodel.py" from-zip "$FROMZIP" --target "$TARGET"
fi

if [ -n "$ZIP" ]; then
  case "$ZIP" in *.zip) ;; *) echo "LỖI: --zip cần đường dẫn file .zip." >&2; exit 2 ;; esac
  WORK="$ZIP.work"
else
  [ -d "$TARGET" ] || { echo "LỖI: không thấy thư mục dự án: $TARGET" >&2; exit 2; }
fi
# The manifest is read and checked by Python (stdlib only); it prints one tab-separated line per file.
PLAN=$("$PY" -E -s -B - "$MANIFEST" "$MODEL" <<'PY'
import json, re, sys, os
m = json.load(open(sys.argv[1], encoding="utf-8"))
name = sys.argv[2] or m["default"]
e = m["models"].get(name)
if not e:
    print("ERR\tmanifest không có model " + name); sys.exit(0)
missing = []
for f in e["files"]:
    p = f["path"]
    if os.path.splitext(p)[1].lower() not in m["allowed_extensions"]:
        print("ERR\tđuôi file không được phép: " + p); sys.exit(0)
    if p.startswith("/") or ".." in p.split("/") or not f["url"].startswith("https://"):
        print("ERR\tđường dẫn hoặc địa chỉ không hợp lệ: " + p); sys.exit(0)
    if not re.fullmatch(r"[0-9a-fA-F]{64}", f.get("sha256") or ""):
        missing.append(p)
print("MODEL\t%s\t%s\t%s\t%s\t%s" % (name, e["dest"], e["source_page"], e["licence"], e.get("revision") or ""))
if missing:
    print("MISSING\t" + ", ".join(missing))
for f in e["files"]:
    mb = float(f["approx_mb"])
    lo = int(mb * 0.85 * 1048576) if mb >= 10 else 1
    hi = int(mb * 1.15 * 1048576)
    if f.get("bytes"):
        lo = hi = int(f["bytes"])
    print("FILE\t%s\t%s\t%s\t%d\t%d\t%s" % (f["path"], f["url"], (f.get("sha256") or "-").lower(), lo, hi,
                                           "bắt buộc" if f.get("required") else "nên có"))
PY
)
ERR=$(printf '%s\n' "$PLAN" | awk -F '\t' '$1=="ERR"{print $2}')
[ -z "$ERR" ] || { echo "LỖI: $ERR" >&2; exit 2; }
NAME=$(printf '%s\n' "$PLAN" | awk -F '\t' '$1=="MODEL"{print $2}')
SUB=$(printf '%s\n' "$PLAN" | awk -F '\t' '$1=="MODEL"{print $3}')
if [ -n "$ZIP" ]; then DEST="$WORK/$SUB"; else DEST="$TARGET/.qkb/models/$SUB"; fi
echo "TẢI MODEL — $NAME$( [ -z "$ZIP" ] || echo ' → zip')$( [ "$APPLY" = 1 ] || echo ' — KẾ HOẠCH (chưa tải gì)')"
printf '%s\n' "$PLAN" | awk -F '\t' '$1=="MODEL"{print "Nguồn: " $4 " · Giấy phép: " $5}'
if [ -n "$ZIP" ]; then echo "File zip: $ZIP"; else echo "Nơi đặt: $DEST"; fi
printf '%s\n' "$PLAN" | awk -F '\t' '$1=="FILE"{print "  - " $2 " (" $7 ")"}'
MISSING=$(printf '%s\n' "$PLAN" | awk -F '\t' '$1=="MISSING"{print $2}')
if [ -n "$MISSING" ] && [ -z "$ZIP" ]; then
  echo "DỪNG: chưa điền sha256 cho: $MISSING. Lấy mã trên trang nguồn rồi chạy lại (hoặc dùng --zip)." >&2; exit 2
fi
[ "$APPLY" = 1 ] || { echo "Để làm thật: chạy lại kèm --apply"; exit 0; }
hash() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }
FAILS=0
TAB=$(printf '\t')
LIST="${TMPDIR:-/tmp}/kbmodels.$$"
DONE="${TMPDIR:-/tmp}/kbmodels-done.$$"
[ -z "$ZIP" ] || rm -rf "$WORK"
printf '%s\n' "$PLAN" | awk -F '\t' '$1=="FILE"' > "$LIST"
: > "$DONE"
while IFS="$TAB" read -r _ path url sha lo hi _; do
  final="$DEST/$path"; partial="$final.partial"
  mkdir -p "$(dirname "$final")"
  if [ "$sha" != "-" ] && [ -f "$final" ] && [ "$(hash "$final")" = "$sha" ]; then
    echo "  ĐÃ CÓ, đúng mã: $path"; printf '%s  sha256 %s\n' "$path" "$sha" >> "$DONE"; continue
  fi
  if [ -n "$FROM" ]; then
    cp "$FROM/$path" "$partial" 2>/dev/null || { rm -f "$partial"; echo "  LỖI: không thấy $FROM/$path" >&2; FAILS=$((FAILS+1)); continue; }
  elif ! curl -fL --proto '=https' ${PROXY:+--proxy "$PROXY"} -o "$partial" "$url"; then
    rm -f "$partial"; echo "  LỖI tải: $path" >&2; FAILS=$((FAILS+1)); continue
  fi
  bytes=$(wc -c < "$partial" | tr -d ' ')
  got=$(hash "$partial")
  if [ "$bytes" -lt "$lo" ] || [ "$bytes" -gt "$hi" ]; then
    rm -f "$partial"; echo "  KHÔNG ĐẠT dung lượng: $path ($bytes byte)" >&2; FAILS=$((FAILS+1)); continue
  fi
  if [ "$sha" != "-" ] && [ "$got" != "$sha" ]; then
    rm -f "$partial"; echo "  KHÔNG ĐẠT SHA256: $path" >&2; FAILS=$((FAILS+1)); continue
  fi
  mv -f "$partial" "$final"
  printf '%s  sha256 %s\n' "$path" "$got" >> "$DONE"   # exactly the line form the engine reads
  if [ "$sha" = "-" ]; then echo "  ĐẠT: $path ($bytes byte) sha256 $got  <- IT đối chiếu với trang nguồn"; else echo "  ĐẠT: $path ($bytes byte)"; fi
done < "$LIST"
rm -f "$LIST"
if [ "$FAILS" -ne 0 ]; then
  rm -f "$DONE"; [ -z "$ZIP" ] || rm -rf "$WORK"
  echo "CHƯA XONG: $FAILS file không đạt (xem trên). Không ghi MODEL.txt / zip." >&2; exit 1
fi
{ echo "model: $NAME"; printf '%s\n' "$PLAN" | awk -F '\t' '$1=="MODEL"{print "source: " $4; print "revision: " $6; print "licence: " $5}'
  echo "downloaded: $(date '+%Y-%m-%d %H:%M')"; cat "$DONE"; } > "$DEST/MODEL.txt"
rm -f "$DONE"
if [ -z "$ZIP" ]; then echo "XONG: mọi file đạt. Ghi lại ở $DEST/MODEL.txt"; exit 0; fi
"$PY" -E -s -B - "$WORK" "$ZIP" <<'PY'
import os, sys, zipfile
work, out = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for folder, _, names in os.walk(work):
        for n in sorted(names):
            full = os.path.join(folder, n)
            z.write(full, os.path.relpath(full, work).replace(os.sep, "/"))
PY
rm -rf "$WORK"
echo "XONG: $ZIP · sha256 $(hash "$ZIP")"
echo "IT đối chiếu mã sha256 từng file ở trên với trang nguồn trước khi chuyển zip sang máy dự án."
echo "Máy dự án: sh tools/download-models.sh --target <dự án> --from-zip $ZIP --apply  (hoặc install.py --model local --model-zip <zip>)"
