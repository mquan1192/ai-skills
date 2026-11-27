#!/usr/bin/env python3
"""lint_text.py - kiểm máy các lỗi văn phong đọc bằng mắt khó thấy (skill q-writing-style).

Chỉ là gợi ý cho người viết; quyết định cuối là của người viết. Không sửa file, trừ --fix-nfc.
Chỉ dùng thư viện chuẩn Python 3.8+, không mạng, không ghi log.

Quy tắc:
  NFC001  error  Văn bản không ở dạng Unicode NFC (hỏng font, sai số ký tự, tìm kiếm không ra)
  TONE001 warn   (vi) Trộn kiểu đặt dấu thanh cũ ("hòa") và mới ("hoà") trong một văn bản
  PRON001 warn   (vi) Trộn "Quý khách" với "bạn" trong một văn bản
  DASH001 warn   Gạch ngang dài (— ― – --) dùng làm dấu nối trong văn xuôi. Không báo: khoảng số
                 ("5 – 10"), cặp tên hoặc từ ngắn ("Nhật – Việt", "em – anh/chị"), dòng phân cách bảng
  AIW001  warn   Cụm hay gặp trong văn AI (ai-tells.md); kiểm từng chỗ trong câu, không xóa máy móc
  BOLD001 warn   Từ 3 mục liền nhau mở bằng nhãn in đậm có dấu hai chấm
  LEN001  info   (en, --plain) Câu dài hơn giới hạn: 25 từ cho câu mô tả, 20 từ cho bước làm
                 (mục danh sách đánh số), theo ASD-STE100

Bỏ qua (trừ NFC001): khối code ``` / ~~~, khối code thụt lề 4 dấu cách sau dòng trống,
code nội dòng `...`, chú thích HTML <!-- ... -->.

Ví dụ:
  python lint_text.py report.md --lang vi
  python lint_text.py README.md --lang en --plain --json
  python lint_text.py notes.md --lang vi --fix-nfc
Mã thoát: 0 = không có lỗi (cảnh báo vẫn có thể có); 1 = có lỗi (hoặc có cảnh báo khi --strict); 2 = lỗi dùng lệnh.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata

# ---- danh sách cụm (giữ ngắn: chỉ các dấu hiệu mạnh, ít báo nhầm) ----
AI_PHRASES = {
    "en": [
        r"\bdelve[sd]?\b", r"\bdelving\b", r"\btapestry\b", r"\btestament to\b", r"\bpivotal\b",
        r"\bseamless(?:ly)?\b", r"\bshowcas(?:e|es|ed|ing)\b", r"\bunderscor(?:e|es|ed|ing)\b",
        r"\bit'?s not (?:just|only|merely)\b", r"\bnot just\b[^.]{0,80}\bbut\b", r"\blet'?s dive in\b",
        r"\bhere'?s the thing\b", r"\bi hope this helps\b", r"\bgreat question\b", r"\bin today'?s fast-paced\b",
        r"\bplays? a (?:key|crucial|pivotal|vital) role\b", r"\bevolving landscape\b", r"\bserves as a\b",
    ],
    "vi": [
        r"không chỉ\b[^.]{0,80}\bmà còn\b", r"không phải(?: là)?\b[^.]{0,80}\bmà là\b", r"đóng vai trò (?:là|như|quan trọng|then chốt)",
        r"bước ngoặt", r"nâng tầm", r"hành trình\b", r"có thể thấy rằng", r"điều đáng lưu ý là",
        r"hãy cùng (?:tìm hiểu|khám phá)", r"hy vọng (?:thông tin|bài viết) này", r"câu hỏi (?:rất )?hay(?=\s*[!.,]|\s*$)",
        r"trong thời đại (?:số|công nghệ)", r"mở ra (?:một )?kỷ nguyên",
    ],
    "ja": [
        r"(?:これ|それ|問題|本質|鍵)は[^。]{0,30}ではなく", r"本質的に", r"重要な役割を果たし", r"お役に立てれば幸いです", r"見ていきましょう",
        r"結論から言うと", r"一見[^。]{0,40}実は", r"示唆している",
    ],
}

# kiểu cũ: dấu trên nguyên âm đầu của oa / oe / uy ở âm tiết mở; kiểu mới: dấu trên nguyên âm sau
_OLD = "òóỏõọ" + "ÒÓỎÕỌ"
_TONED_A = "àáảãạ"
_TONED_E = "èéẻẽẹ"
_TONED_Y = "ỳýỷỹỵ"
_TONED_U = "ùúủũụ"
_LETTER = r"0-9A-Za-zÀ-ỹ"
TONE_OLD = re.compile(r"(?<![%s])[^\W\d_]*?(?:[òóỏõọ][ae]|[ùúủũụ]y)(?![%s])" % (_LETTER, _LETTER), re.IGNORECASE)
TONE_NEW = re.compile(r"(?<![%s])[^\W\d_]*?(?:o[%s%s]|(?<!q)u[%s])(?![%s])" % (_LETTER, _TONED_A, _TONED_E, _TONED_Y, _LETTER),
                      re.IGNORECASE)

DASH = re.compile(r"\s[—―–]\s|\S[—―]\S|\s--\s")
TABLE_RULE = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")
FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
HTML_COMMENT = re.compile(r"<!--.*?-->")
BOLD_LABEL = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\*\*[^*]{1,60}?(?:[:：]\*\*|\*\*[:：])\s")
NUMBERED = re.compile(r"^\s*\d+[.)]\s")
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
QUY_KHACH = re.compile(r"\bQuý khách\b")
BAN = re.compile(r"\bbạn\b", re.IGNORECASE)


def strip_code(lines):
    """Trả về (số dòng, dòng đã bỏ code nội dòng và chú thích HTML) cho các dòng văn xuôi.

    Bỏ khối code rào bằng ``` / ~~~ (đóng bằng cùng ký tự, dài ít nhất bằng rào mở) và khối thụt lề
    4 dấu cách / tab bắt đầu sau một dòng trống."""
    out, fence, indented, prev_blank = [], None, False, True
    for i, line in enumerate(lines, 1):
        m = FENCE.match(line)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not line.strip(fence[0] + " \t\r"):
                fence = None
            continue
        if m:
            fence = m.group(1)
            continue
        blank = not line.strip()
        if line.startswith(("    ", "\t")) and not blank and (prev_blank or indented):
            indented = True
            continue
        if not blank:
            indented = False
        prev_blank = blank
        line = HTML_COMMENT.sub(" ", line)
        out.append((i, re.sub(r"`[^`]*`", " ", line)))
    return out


def _word(tok):
    return re.sub(r"[^\w/]", "", tok)


def dash_count(line):
    """Đếm gạch ngang dài làm dấu nối; bỏ qua khoảng số và cặp tên / từ ngắn quanh " – "."""
    if TABLE_RULE.match(line):
        return 0
    n = 0
    for m in DASH.finditer(line):
        if "–" in m.group(0):
            before, after = line[:m.start() + 1].split(), line[m.end() - 1:].split()
            a, b = (_word(before[-1]) if before else ""), (_word(after[0]) if after else "")
            if a and b and ((a[0].isdigit() and b[0].isdigit()) or (a[0].isupper() and b[0].isupper())
                            or (len(a.split("/")[0]) <= 3 and len(b.split("/")[0]) <= 3)):
                continue
        n += 1
    return n


def check(text, lang, plain=False, max_words=25, max_words_proc=20):
    findings = []

    def add(line, code, level, msg):
        findings.append({"line": line, "code": code, "level": level, "message": msg})

    if unicodedata.normalize("NFC", text) != text:
        for i, line in enumerate(text.splitlines(), 1):
            if unicodedata.normalize("NFC", line) != line:
                add(i, "NFC001", "error", "không ở dạng Unicode NFC (dùng --fix-nfc để chuẩn hóa)")
                break
    text = unicodedata.normalize("NFC", text)
    prose = strip_code(text.splitlines())

    if lang == "vi":
        old, new = [], []
        for i, line in prose:
            old += [(i, m.group(0)) for m in TONE_OLD.finditer(line)]
            new += [(i, m.group(0)) for m in TONE_NEW.finditer(line)]
        if old and new:
            add(new[0][0] if new[0][0] > old[0][0] else old[0][0], "TONE001", "warn",
                "trộn kiểu dấu thanh: kiểu cũ %s và kiểu mới %s — chọn một kiểu cho cả văn bản"
                % (", ".join(sorted({w for _, w in old})[:4]), ", ".join(sorted({w for _, w in new})[:4])))

    if lang == "vi":
        qk = next((i for i, line in prose if QUY_KHACH.search(line)), None)
        ban = next((i for i, line in prose if BAN.search(line)), None)
        if qk and ban:
            add(max(qk, ban), "PRON001", "warn", "trộn \"Quý khách\" và \"bạn\" — một cách xưng hô cho cả văn bản "
                                              "(vietnamese-register.md § 1)")

    for i, line in prose:
        n = dash_count(line)
        if n:
            add(i, "DASH001", "warn", "%d gạch ngang dài làm dấu nối — thay bằng dấu chấm, phẩy, hai chấm hoặc ngoặc "
                                      "(giữ nếu giọng văn / quy ước file có dùng)" % n)

    for pat in AI_PHRASES.get(lang, []):
        rx = re.compile(pat, re.IGNORECASE)
        for i, line in prose:
            m = rx.search(line)
            if m:
                add(i, "AIW001", "warn", "cụm hay gặp trong văn AI: \"%s\" — kiểm trong câu (ai-tells.md)" % m.group(0))

    run = []
    for i, line in prose + [(0, "")]:
        if BOLD_LABEL.match(line):
            run.append(i)
            continue
        if len(run) >= 3:
            add(run[0], "BOLD001", "warn", "%d mục liền nhau mở bằng nhãn in đậm — nhãn không mang thông tin thì viết thành câu"
                % len(run))
        run = []

    if plain and lang == "en":
        for i, line in prose:
            if line.lstrip().startswith(("#", "|")):
                continue
            limit = max_words_proc if NUMBERED.match(line) else max_words
            for sent in SENT_SPLIT.split(line):
                words = len(sent.split())
                if words > limit:
                    add(i, "LEN001", "info", "câu %d từ (giới hạn %d) — tách câu" % (words, limit))
    findings.sort(key=lambda f: (f["line"], f["code"]))
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(description="Kiểm máy lỗi văn phong (gợi ý; không thay người đọc).")
    ap.add_argument("files", nargs="+", help="File văn bản (UTF-8)")
    ap.add_argument("--lang", choices=("vi", "ja", "en"), required=True, help="Ngôn ngữ văn bản")
    ap.add_argument("--plain", action="store_true", help="Thêm kiểm độ dài câu (en)")
    ap.add_argument("--max-words", type=int, default=25, help="Giới hạn từ mỗi câu mô tả cho --plain (mặc định 25)")
    ap.add_argument("--max-words-proc", type=int, default=20,
                    help="Giới hạn từ mỗi câu trong bước làm (mục đánh số) cho --plain (mặc định 20)")
    ap.add_argument("--json", action="store_true", help="Xuất JSON")
    ap.add_argument("--strict", action="store_true", help="Cảnh báo cũng làm mã thoát 1")
    ap.add_argument("--fix-nfc", action="store_true", help="Ghi lại file ở dạng NFC (chỉ sửa NFC001)")
    args = ap.parse_args(argv)
    report, worst = {}, 0
    for path in args.files:
        try:
            with open(path, "rb") as f:
                data = f.read()
            bom = data.startswith(b"\xef\xbb\xbf")
            text = data[3 if bom else 0:].decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            sys.stderr.write("Không đọc được %s: %s\n" % (path, exc))
            return 2
        if args.fix_nfc and unicodedata.normalize("NFC", text) != text:
            # giữ nguyên BOM và kiểu xuống dòng (CRLF / LF) của file
            text = unicodedata.normalize("NFC", text)
            with open(path, "wb") as f:
                f.write((b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8"))
        found = check(text, args.lang, args.plain, args.max_words, args.max_words_proc)
        report[path] = found
        for f in found:
            if f["level"] == "error" or (args.strict and f["level"] == "warn"):
                worst = 1
    if args.json:
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    else:
        total = 0
        for path, found in report.items():
            for f in found:
                total += 1
                sys.stdout.write("%s:%d: %s %s %s\n" % (path, f["line"], f["code"], f["level"], f["message"]))
        sys.stdout.write("%d gợi ý.\n" % total)
    return worst


if __name__ == "__main__":
    sys.exit(main())
