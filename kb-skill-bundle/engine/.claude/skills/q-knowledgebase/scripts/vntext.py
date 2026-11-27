"""Vietnamese text and number normalisation (A1 and A5). Standard library only, deterministic.

A1  tone(text): NFC, and one tone-mark position per syllable, so "hoà" / "hòa", "thuỷ" / "thủy", "quý" / "qúy"
    compare equal. The placement rule only has to be the same at index and query time; it follows the common
    "new style" (mark on the vowel with a quality mark ă â ê ô ơ ư; else on the second vowel of oa / oe / uy and
    of a cluster followed by a final consonant; else on the first vowel).
A5  numbers(text): canonical tokens for numbers, dates, versions, percentages and units, e.g.
    "1.234,5" / "1,234.5" -> "1234.5"; "17/11/2026" / "2026-11-17" -> "2026-11-17"; "2,5 triệu" -> "2500000";
    "v2.1" / "phiên bản 2.1" / "version 2.1" -> "v2.1"; "5 %" -> "5%"; "5 mm" -> "5mm".
    Ambiguous forms produce every reading ("1.234" -> "1234" and "1.234"), never a guess between them.
"""
from __future__ import annotations

import functools
import re
import unicodedata

TONES = {"̀", "́", "̃", "̉", "̣"}          # huyền sắc ngã hỏi nặng
QUALITY = {"̆", "̂", "̛"}                              # ă / â ê ô / ơ ư
VOWELS = set("aeiouy")
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


@functools.lru_cache(maxsize=65536)
def _syllable(word):
    """One word with its tone mark moved to the canonical vowel (NFD in, NFC out)."""
    chars = unicodedata.normalize("NFD", word)
    tone, base = None, []
    for ch in chars:
        if ch in TONES:
            tone = ch
            continue
        if unicodedata.combining(ch):
            if base:
                base[-1] += ch          # keep quality marks with their letter
            continue
        base.append(ch)
    if tone is None:
        return unicodedata.normalize("NFC", word)
    letters = [b[0].casefold() for b in base]
    vowel_idx = [i for i, ch in enumerate(letters) if ch in VOWELS]
    # "qu" and "gi" + vowel: the u / i belongs to the consonant
    if len(vowel_idx) > 1 and letters[:2] in (["q", "u"], ["g", "i"]) and vowel_idx[0] == 1:
        vowel_idx = vowel_idx[1:]
    if not vowel_idx:
        return unicodedata.normalize("NFC", word)
    # the vowel cluster = the first run of adjacent vowels
    cluster = [vowel_idx[0]]
    for i in vowel_idx[1:]:
        if i == cluster[-1] + 1:
            cluster.append(i)
    quality = [i for i in cluster if any(m in base[i] for m in QUALITY)]
    final_consonant = cluster[-1] + 1 < len(base)
    if quality:
        target = quality[-1]                                   # ươ -> ơ, uyê -> ê
    elif len(cluster) == 1:
        target = cluster[0]
    elif final_consonant or len(cluster) == 3:
        target = cluster[1] if len(cluster) == 3 else cluster[-1]
    elif "".join(letters[i] for i in cluster) in ("oa", "oe", "uy"):
        target = cluster[-1]
    else:
        target = cluster[0]
    base[target] += tone
    return unicodedata.normalize("NFC", "".join(base))


def tone(text):
    """NFC text with one canonical tone-mark position per word (A1). Non-Latin text is only NFC-normalised."""
    text = unicodedata.normalize("NFC", text)
    return WORD.sub(lambda m: _syllable(m.group(0)) if not m.group(0).isascii() else m.group(0), text)


def light(text):
    """Case-folded, accent-keeping form used for accented matching (A1 applied)."""
    return tone(text.casefold())


# ---------------------------------------------------------------- A5 numbers

SCALE = {"nghìn": 1_000, "ngàn": 1_000, "nghin": 1_000, "ngan": 1_000, "k": 1_000, "triệu": 1_000_000,
         "trieu": 1_000_000, "tr": 1_000_000, "million": 1_000_000, "tỷ": 1_000_000_000, "tỉ": 1_000_000_000,
         "ty": 1_000_000_000, "ti": 1_000_000_000, "billion": 1_000_000_000, "thousand": 1_000}
UNITS = ("mm", "cm", "km", "m", "kg", "g", "mg", "ms", "s", "min", "h", "gb", "mb", "kb", "tb", "hz", "khz", "mhz",
         "ghz", "v", "mv", "a", "ma", "w", "kw", "µm", "um", "nm", "°c", "c", "px", "dpi", "fps", "rpm", "bps",
         "kbps", "mbps", "phút", "giây", "giờ", "ngày", "tháng", "năm", "đ", "vnd", "usd", "%")
# A number joined to other characters ("RS-485", "6.9.1", "v2") is part of a name, not an amount.
NUM = r"(?<![\w.,/-])(\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)(?![.,]\d)"
NUMBER = re.compile(NUM + r"(?![\w-])")
DATE_DMY = re.compile(r"(?<!\d)(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})(?!\d)")
DATE_YMD = re.compile(r"(?<!\d)(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})(?!\d)")
VERSION = re.compile(r"(?i)(?:\bv|\bversion\s+|phiên\s+bản\s+|phien\s+ban\s+|バージョン\s*)(\d+(?:\.\d+)+|\d+)\b")
SCALED = re.compile(r"(?i)" + NUM + r"\s*(" + "|".join(sorted(map(re.escape, SCALE), key=len, reverse=True)) + r")\b")
UNIT = re.compile(r"(?i)" + NUM + r"\s?(" + "|".join(sorted(map(re.escape, UNITS), key=len, reverse=True)) + r")(?![\w])")


def _readings(raw):
    """Plain decimal readings of one written number ("1.234,5" -> {"1234.5"}; "1.234" -> {"1234", "1.234"})."""
    out = set()
    if re.fullmatch(r"\d+", raw):
        return {str(int(raw))}
    for thousands, decimal in ((".", ","), (",", ".")):
        parts = raw.split(decimal)
        if len(parts) > 2:
            continue
        whole = parts[0]
        groups = whole.split(thousands)
        if len(groups) > 1 and not all(len(g) == 3 for g in groups[1:]):
            continue
        number = "".join(groups)
        if not number.isdigit() or (len(parts) == 2 and not parts[1].isdigit()):
            continue
        value = str(int(number)) + ("." + parts[1] if len(parts) == 2 else "")
        out.add(value)
    if not out:   # "12.5" style with one separator and not 3 digits after it
        out.add(raw.replace(",", "."))
    return out


def _plain(value):
    text = ("%.6f" % value).rstrip("0").rstrip(".")
    return text


def numbers(text):
    """Canonical number / date / version / unit tokens of a text (set of strings; empty when none)."""
    found = set()
    low = text.casefold()
    for d, m, y in DATE_DMY.findall(low):
        if 1 <= int(d) <= 31 and 1 <= int(m) <= 12:
            found.add("%s-%02d-%02d" % (y, int(m), int(d)))
    for y, m, d in DATE_YMD.findall(low):
        if 1 <= int(d) <= 31 and 1 <= int(m) <= 12:
            found.add("%s-%02d-%02d" % (y, int(m), int(d)))
    for v in VERSION.findall(low):
        found.add("v" + v)
    for raw, scale in SCALED.findall(low):
        for reading in _readings(raw):
            try:
                found.add(_plain(float(reading) * SCALE[scale.casefold()]))
            except ValueError:
                pass
    for raw, unit in UNIT.findall(low):
        for reading in _readings(raw):
            found.add(reading + unit.casefold())
    for raw in NUMBER.findall(low):
        found.update(_readings(raw))
    return found


def number_spans(text):
    """Non-overlapping number expressions of a (case-folded) query text: [(start, end, tokens)] in text order.
    Dates, versions, scaled amounts and amounts with a unit win over a bare number at the same place."""
    spans = []

    def take(start, end, tokens):
        if tokens and not any(start < e and s < end for s, e, _ in spans):
            spans.append((start, end, tokens))
    for m in DATE_DMY.finditer(text):
        d, mo, y = m.groups()
        if 1 <= int(d) <= 31 and 1 <= int(mo) <= 12:
            take(m.start(), m.end(), {"%s-%02d-%02d" % (y, int(mo), int(d))})
    for m in DATE_YMD.finditer(text):
        y, mo, d = m.groups()
        if 1 <= int(d) <= 31 and 1 <= int(mo) <= 12:
            take(m.start(), m.end(), {"%s-%02d-%02d" % (y, int(mo), int(d))})
    for m in VERSION.finditer(text):
        take(m.start(), m.end(), {"v" + m.group(1)})
    for m in SCALED.finditer(text):
        tokens = set()
        for reading in _readings(m.group(1)):
            try:
                tokens.add(_plain(float(reading) * SCALE[m.group(2).casefold()]))
            except ValueError:
                pass
        take(m.start(), m.end(), tokens)
    for m in UNIT.finditer(text):
        take(m.start(), m.end(), {r + m.group(2).casefold() for r in _readings(m.group(1))})
    for m in NUMBER.finditer(text):
        take(m.start(), m.end(), _readings(m.group(1)))
    return sorted(spans)
