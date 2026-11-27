"""Phase B retrieval (2.1.0-b): query analysis, glossary bridge, trigram candidates and RRF ranking.

Everything is deterministic and local: no model, no network. Inputs that steer the analysis (stop words,
glossary files and their column names) come from the configuration; no project name or path is built in.
"""
from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from pathlib import Path

from core import QError, fold, read_text, safe_path
import vntext

CJK = re.compile(r"[぀-ヿ㐀-鿿豈-﫿ｦ-ﾟ]")
CELL_SPLIT = re.compile(r"\s+/\s+|／|\s+—\s+|\s+-\s+|;|；|、")
RRF_K = 60
PHRASE_BONUS = 15   # score added per whole query phrase found in a section
_GLOSSARY_CACHE = {}
COMMON_GLOSSARY = Path(__file__).resolve().parent.parent / "references" / "glossary-common.md"


# ---------------------------------------------------------------- glossary bridge

def light(text):
    """Case-folded text that keeps accents (NFC, one tone-mark position): "bán" and "bản" stay
    different, "hoà" and "hòa" are equal."""
    return vntext.light(text)


def kb_content(cfg):
    """Main language of the KB content: vi / en / ja / mixed (default)."""
    return cfg["languages"].get("kb_content", "mixed")


def has_marks(text):
    """True when Latin letters of the text carry accents (the writer typed Vietnamese with accents)."""
    return "đ" in text.casefold() or any(unicodedata.combining(c) for c in unicodedata.normalize("NFD", text)
                                         if not CJK.search(c))


def _cell_variants(cell):
    """Term variants of one table cell: markup removed, parenthesised parts taken apart, then alternatives split."""
    cell = re.sub(r"\*\*|`|\*", "", cell).strip()
    if not cell or cell in ("—", "-", "–"):
        return []
    inner = re.findall(r"[(（]([^()（）]*)[)）]", cell)
    outer = re.sub(r"[(（][^()（）]*[)）]", " ", cell)
    out = []
    for piece in CELL_SPLIT.split(outer) + [x for i in inner for x in CELL_SPLIT.split(i)]:
        piece = re.sub(r"\s+", " ", piece).strip(" =.,:;\"'")
        if piece and piece not in out:
            out.append(piece)
    return out


def parse_glossary(text, columns):
    """Markdown tables whose header names at least two language columns -> list of entries.
    An entry is a list of (language, accented form, folded form) per variant; one entry per table row."""
    names = {fold(name).strip(): lang for lang, values in columns.items() for name in values}
    entries, header = [], None
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            header = {}
            if re.match(r"^\s*\|?\s*:?-{2,}", nxt):
                langs = {j: names.get(fold(c).strip()) for j, c in enumerate(cells)}
                header = {j: lang for j, lang in langs.items() if lang}
                if len(set(header.values())) < 2:
                    header = {}
            continue
        if not header or re.match(r"^:?-{2,}:?$", cells[0] if cells else ""):
            continue
        entry = []
        for j, lang in header.items():
            if j < len(cells):
                for variant in _cell_variants(cells[j]):
                    triple = (lang, light(variant), fold(variant))
                    if triple not in entry:
                        entry.append(triple)
        if len({f for _, _, f in entry}) >= 2:
            entries.append(entry)
    return entries


def _glossary_files(store):
    files = [COMMON_GLOSSARY] if store.cfg["common_glossary"] else []
    return files + [safe_path(store.root, rel) for rel in store.cfg["glossary_paths"]]


def _glossary_key(store):
    """File states (path, size, mtime) + column names: the parsed glossary is valid while this is unchanged."""
    key = [json.dumps(store.cfg["glossary_columns"], sort_keys=True)]
    for path in _glossary_files(store):
        if path.is_file():
            stat = path.stat()
            key.append([str(path), stat.st_size, stat.st_mtime_ns])
    return key


def _parse_all(store):
    entries = []
    for path in _glossary_files(store):
        if path.is_file():
            entries.extend(parse_glossary(read_text(path), store.cfg["glossary_columns"]))
    return entries


def refresh_glossary(store):
    """Called by update: keep the parsed glossary in the index (meta qkb_glossary) so that a search
    process does not parse the glossary files again."""
    key = _glossary_key(store)
    cached = store.getmeta("qkb_glossary")
    if cached and json.loads(cached).get("key") == key:
        return
    store.setmeta("qkb_glossary", json.dumps({"key": key, "entries": _parse_all(store)}, ensure_ascii=False))


def glossary(store):
    """Entries of every configured glossary file: from the index when its stored file states still match,
    else parsed now (cached for this process)."""
    key = _glossary_key(store)
    marker = json.dumps(key)
    if marker in _GLOSSARY_CACHE:
        return _GLOSSARY_CACHE[marker]
    cached = store.getmeta("qkb_glossary")
    data = json.loads(cached) if cached else None
    entries = data["entries"] if data and data.get("key") == key else _parse_all(store)
    _GLOSSARY_CACHE[marker] = entries
    return entries


def _matchable(variant, stop):
    if CJK.search(variant):
        return len(variant) >= 2
    return len(variant) >= 3 and variant not in stop and not variant.isdigit()


def _find(variant, text):
    """Positions of a variant in text; Latin variants on word borders, CJK as substring."""
    if variant not in text:
        return []
    if CJK.search(variant):
        return [m.start() for m in re.finditer(re.escape(variant), text)]
    # A term inside a joined token ("user" in "req-user-01", "stock" in "stock.cpp") is not a match.
    return [m.start() for m in re.finditer(r"(?<!\w)(?<!\w[./_-])" + re.escape(variant) + r"(?!\w)(?![./_-]\w)", text)]


# ---------------------------------------------------------------- query analysis

def analyse(store, query):
    """-> {"groups": [{"text", "alternatives", "source"}], "expanded": [...]}.
    A group is one concept of the question; a section satisfies it when any alternative occurs
    (alternatives are accent-folded like the indexed text). Glossary phrases become one group with the
    other-language variants; other words are single groups; stop words (per language, configured) are
    dropped unless nothing else is left. A query typed with Vietnamese accents is matched with accents,
    so folding cannot join different words ("bán" / "bản", "thất" / "that")."""
    accented = has_marks(query)
    form = light if accented else fold
    q = form(query)
    stop = {form(w).strip() for words in store.cfg["stopwords"].values() for w in words if w.strip()}
    # 1. multi-word question phrases ("bao nhiêu", "how does") are removed first
    for phrase in sorted((w for w in stop if " " in w), key=len, reverse=True):
        q = re.sub(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", lambda m: " " * len(m.group(0)), q)
    # 2. glossary phrases, longest first, never overlapping
    found = []
    for entry in glossary(store):
        for _, accented_form, folded_form in entry:
            variant = accented_form if accented else folded_form
            if _matchable(variant, stop):
                for pos in _find(variant, q):
                    found.append((pos, pos + len(variant), variant, folded_form, entry))
    found.sort(key=lambda m: (-(m[1] - m[0]), m[0], m[2]))
    taken, groups, expanded, rest = [], [], [], list(q)
    for start, end, variant, folded_form, entry in found:
        if any(start < e and s < end for s, e in taken):
            continue
        taken.append((start, end))
        alternatives = [folded_form] + [f for _, _, f in entry if len(f) >= 2]
        alternatives = list(dict.fromkeys(alternatives))[:8]
        groups.append({"text": variant, "alternatives": alternatives, "source": "glossary", "at": start})
        expanded.append({"term": variant, "alternatives": alternatives[1:]})
        for k in range(start, end):
            rest[k] = " "
    # 3. numbers, dates, versions, amounts with units: one group with the canonical readings
    rest = "".join(rest)
    for start, end, tokens in vntext.number_spans(rest):
        span = rest[start:end].strip()
        bare = [t[1:] for t in tokens if t.startswith("v") and t[1:2].isdigit()]
        alternatives = list(dict.fromkeys(sorted(tokens) + [fold(span)] + bare))
        groups.append({"text": span, "alternatives": alternatives, "source": "number", "at": start})
        rest = rest[:start] + " " * (end - start) + rest[end:]
    # 4. remaining words
    words = []
    for m in re.finditer(r"[\w./-]+", rest):
        word = m.group(0).strip("./-")
        if word and word not in stop:
            words.append({"text": word, "alternatives": [fold(word)], "source": "word", "at": m.start(),
                          "end": m.end(), "written": light(word) if accented else None})
    phrases = find_phrases(store, words, rest)
    groups += words
    if not groups:
        groups = [{"text": t, "alternatives": [t], "source": "word", "at": i}
                  for i, t in enumerate(re.findall(r"[\w./-]+", fold(query)))]
    groups.sort(key=lambda g: g["at"])
    seen, unique = set(), []
    for g in groups:
        key = tuple(g["alternatives"])
        if key not in seen:
            seen.add(key)
            unique.append({k: v for k, v in g.items() if k not in ("at", "end")})
    return {"groups": unique, "expanded": expanded, "phrases": phrases}


def _phrase_in_index(store, phrase):
    try:
        return store.db.execute("SELECT 1 FROM search_tri WHERE search_tri MATCH ? LIMIT 1", (_fts_phrase(phrase),)).fetchone() is not None
    except sqlite3.OperationalError:
        return False


def find_phrases(store, words, text):
    """Adjacent query words (only spaces between them) that occur as a 2- or 3-word phrase in the
    index ("di chuyển", "bộ nhớ đệm", "access token"); longest first, left to right, not overlapping. A phrase
    does not replace its words (each word still counts as a concept); sections that contain the whole phrase
    rank first inside their tier. -> [{"folded": ..., "written": accented form or None}].
    Off for Japanese KBs and without the trigram table."""
    if not store.trigram or kb_content(store.cfg) == "ja" or len(words) < 2:
        return []
    out, i = [], 0
    while i < len(words):
        size_found = 0
        for size in (3, 2):
            run = words[i:i + size]
            if len(run) < size or any(CJK.search(w["text"]) or w["text"].isdigit() for w in run):
                continue
            if any(text[a["end"]:b["at"]].strip() for a, b in zip(run, run[1:])):
                continue            # something other than spaces between the words
            phrase = " ".join(w["alternatives"][0] for w in run)
            if len(phrase) >= 5 and _phrase_in_index(store, phrase):
                out.append({"folded": phrase,
                            "written": " ".join(w["written"] for w in run) if run[0].get("written") else None})
                size_found = size
                break
        i += size_found or 1
    return out


# ---------------------------------------------------------------- candidates

def _fts_phrase(text):
    return '"' + text.replace('"', '""') + '"'


def word_fts(store, groups, limit=400):
    """Ranked ids from the unicode61 table (Latin words; CJK cannot be segmented there)."""
    if not store.fts:
        return []
    terms = []
    for g in groups:
        # The accented form as written too - unicode61 folds most accents but not "đ".
        for alt in g["alternatives"] + ([g["written"]] if g.get("written") else []):
            words = re.findall(r"\w+", alt)
            if words and not CJK.search(alt):
                terms.append(_fts_phrase(" ".join(words)))
    if not terms:
        return []
    try:
        rows = store.db.execute("SELECT id FROM search_fts WHERE search_fts MATCH ? ORDER BY bm25(search_fts,0,4,1) LIMIT ?",
                                (" OR ".join(dict.fromkeys(terms)), limit)).fetchall()
    except sqlite3.OperationalError:
        return []
    return [r[0] for r in rows]


def trigram_fts(store, groups, limit=400):
    """Ranked ids from the trigram table (folded text: Vietnamese without accents, Japanese, identifiers)."""
    if not store.trigram:
        return []
    terms = [_fts_phrase(alt) for g in groups for alt in g["alternatives"] if len(alt) >= 3]
    if not terms:
        return []
    try:
        rows = store.db.execute("SELECT id FROM search_tri WHERE search_tri MATCH ? ORDER BY bm25(search_tri,0,4,1) LIMIT ?",
                                (" OR ".join(dict.fromkeys(terms)), limit)).fetchall()
    except sqlite3.OperationalError:
        return []
    return [r[0] for r in rows]


def like_candidates(store, groups, limit=400):
    """Substring fallback: every term when the trigram table is off, else only what trigrams cannot match
    (terms shorter than 3 characters that are CJK, and literal paths)."""
    ids = []
    for g in groups[:16]:
        for alt in g["alternatives"]:
            short_cjk = len(alt) < 3 and CJK.search(alt)
            pathlike = "/" in alt or re.search(r"\.\w+$", alt)
            if store.trigram and not short_cjk and not pathlike:
                continue
            escaped = alt.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = "%" + escaped + "%"
            if pathlike and store.trigram:
                sql, params = "SELECT id FROM sections WHERE lower(path) LIKE ? ESCAPE '\\' LIMIT ?", (pattern, limit)
            else:
                sql = ("SELECT id FROM sections WHERE normalized LIKE ? ESCAPE '\\' OR lower(path) LIKE ? ESCAPE '\\'"
                       " OR lower(heading) LIKE ? ESCAPE '\\' LIMIT ?")
                params = (pattern, pattern, pattern, limit)
            ids.extend(r[0] for r in store.db.execute(sql, params))
    return list(dict.fromkeys(ids))


# ---------------------------------------------------------------- ranking

_PATTERNS = {}


def _pattern(alt):
    """Short Latin terms (<= 3 chars) must be whole words; longer ones may be a word prefix
    ("image" finds "images"); CJK and paths match as substrings."""
    if alt not in _PATTERNS:
        if CJK.search(alt) or "/" in alt:
            _PATTERNS[alt] = None
        elif len(alt) <= 3:
            _PATTERNS[alt] = re.compile(r"(?<!\w)" + re.escape(alt) + r"(?!\w)")
        else:   # an underscore before the term is a joiner ("_reload_x" contains "reload_x"), a letter is not
            _PATTERNS[alt] = re.compile(r"(?<![^\W_])" + re.escape(alt))
    return _PATTERNS[alt]


def _occurs(alt, text):
    if alt not in text:
        return False
    pattern = _pattern(alt)
    return pattern is None or pattern.search(text) is not None


def number_hits(store, groups):
    """Per number group, the sections whose trigram row holds one of its canonical tokens (the row
    carries the section's normalised numbers). None for a group whose tokens are too short for trigrams."""
    out = {}
    for i, g in enumerate(groups):
        if g["source"] != "number":
            continue
        tokens = [a for a in g["alternatives"] if len(a) >= 3]
        if not store.trigram or len(tokens) < len(g["alternatives"]):
            out[i] = None
            continue
        try:
            rows = store.db.execute("SELECT id FROM search_tri WHERE search_tri MATCH ?",
                                    (" OR ".join(_fts_phrase(t) for t in tokens),)).fetchall()
            out[i] = {r[0] for r in rows}
        except sqlite3.OperationalError:
            out[i] = None
    return out


def coverage(sec, groups, q, numbers=None):
    """Exact-match evidence of one section: groups satisfied, by the words as written, in the heading / path,
    number groups satisfied (canonical readings of the section's numbers), whole-query hits."""
    heading, path, content = fold(sec["heading"] or ""), fold(sec["path"]), sec["normalized"]
    context = fold(" ".join(json.loads(sec["hierarchy"])))
    matched = written = in_heading = numbers_hit = 0
    section_numbers = None
    numbers = numbers or {}
    for gi, g in enumerate(groups):
        hit = False
        for n, alt in enumerate(g["alternatives"]):
            if alt in path or _occurs(alt, content) or _occurs(alt, context):
                hit = True
            elif g["source"] == "number":
                known = numbers.get(gi)
                if known is not None:          # trigram rows already hold the section's canonical numbers
                    hit = sec["id"] in known
                else:
                    # short tokens: cheap pre-check, then the section's canonical numbers
                    digits = re.findall(r"\d+", g["text"])
                    if digits and digits[0] not in sec["content"]:
                        continue
                    if section_numbers is None:
                        section_numbers = vntext.numbers(sec["content"]) | vntext.numbers(sec["heading"] or "")
                    hit = alt in section_numbers
            if hit:
                matched += 1
                written += n == 0
                numbers_hit += g["source"] == "number"
                if alt in path or _occurs(alt, heading):
                    in_heading += 1
                break
    whole = (100 if q == path else 50 if q in path else 0) + (80 if q == heading else 30 if q in heading else 0)
    return matched, written, in_heading, whole, numbers_hit


_LIGHT = {}


def _light_section(sec):
    """Accent-kept, tone-normalised heading + content of a section, cached per section id and content hash."""
    key = (sec["id"], len(sec["content"]), hash(sec["content"]))
    if key not in _LIGHT:
        if len(_LIGHT) > 4000:
            _LIGHT.clear()
        _LIGHT[key] = light(sec["heading"] or "") + " \n " + light(sec["content"])
    return _LIGHT[key]


def rank(store, query, groups, top, project, history, phrases=()):
    """RRF over three ranked lists (word FTS, trigram FTS, exact evidence); sections that satisfy more
    concept groups always come first. Returns (ranked [(score, sec, matched)], candidates, mode)."""
    q = fold(query)
    # Words as written rank first; glossary translations form separate, half-weight lists so that a
    # term that exists in the documents as written is not pushed down by its translations.
    written = [dict(g, alternatives=g["alternatives"][:1]) for g in groups]
    bridged = [dict(g, alternatives=g["alternatives"][1:]) for g in groups if len(g["alternatives"]) > 1]
    word = word_fts(store, written)
    tri = trigram_fts(store, written)
    bridge_word = word_fts(store, bridged) if bridged else []
    bridge_tri = trigram_fts(store, bridged) if bridged else []
    like = like_candidates(store, groups)
    ids = list(dict.fromkeys(word + tri + bridge_word + bridge_tri + like))
    sections = {}
    for chunk in range(0, len(ids), 500):
        part = ids[chunk:chunk + 500]
        for row in store.db.execute("SELECT * FROM sections WHERE id IN (%s)" % ",".join("?" * len(part)), part):
            sections[row["id"]] = dict(row)
    if project is not None:
        sections = {k: v for k, v in sections.items() if store.scope.in_project(v["path"], project)}
    numbers = number_hits(store, groups)
    evidence = {}
    for id_, sec in sections.items():
        found = coverage(sec, groups, q, numbers)
        if found[0]:
            evidence[id_] = found   # (matched, written, in_heading, whole)
    # Third list = exact evidence only (whole query or a concept in the heading / path); no ordering by name.
    exact_list = sorted((i for i in evidence if evidence[i][2] or evidence[i][3]),
                        key=lambda i: (-evidence[i][3], -evidence[i][2], -evidence[i][0], sections[i]["path"], sections[i]["start"]))
    fused = {}
    for weight, ranked_ids in ((1.0, word), (1.0, tri), (1.0, exact_list), (0.5, bridge_word), (0.5, bridge_tri)):
        for position, id_ in enumerate(i for i in ranked_ids if i in evidence):
            fused[id_] = fused.get(id_, 0.0) + weight / (RRF_K + position + 1)
    total = len(groups)
    ranked = []
    for id_, (matched, written_hits, in_heading, whole, numbers_hit) in evidence.items():
        score = fused.get(id_, 0.0) * 1000 + whole + matched * 4 + in_heading * 6 + (12 if matched == total else 0)
        ranked.append((score, sections[id_], matched, written_hits, numbers_hit))
    exact = any(evidence[i][3] >= 30 for i in evidence)
    complete = any(r[2] == total for r in ranked)
    mode = "exact_heading_or_path" if exact else "all_terms" if complete else "partial_terms"
    # As in 2.0.0: an exact heading / path hit wins alone; partial matches are only a fallback. Questions of
    # 4+ concepts (natural sentences) keep sections that miss one concept.
    exact_hits = [r for r in ranked if q in (fold(r[1]["path"]), fold(r[1]["heading"] or ""))]
    if exact_hits:
        ranked = exact_hits
    elif complete:
        ranked = [r for r in ranked if r[2] == total or (total >= 4 and r[2] >= total - 1)]
    # Order: history last; more number groups matched; more concepts covered; more concepts covered by
    # the words as written; score (fused rank + exact evidence + phrase bonus).
    phrase_hits = {}
    for r in ranked:
        text = r[1]["normalized"] + " \n " + fold(r[1]["heading"] or "")
        phrase_hits[id(r)] = sum(1 for p in phrases if _occurs(p["folded"], text))
    # A whole query phrase found in the section adds to its score (a bonus inside the tier, not a tier).
    ranked = [(score + PHRASE_BONUS * phrase_hits[id(r)], sec, matched, written, numbers)
              for r in ranked for score, sec, matched, written, numbers in [r]]
    ranked.sort(key=lambda x: (x[1]["path"] in history, -x[4], -x[2], -x[3], -x[0], x[1]["path"], x[1]["start"]))
    # For a query typed with accents (VN / mixed KB), sections that contain the accented words as
    # written move up inside their tier (only the first 60 are re-checked, on accent-kept, tone-normalised text).
    accented = [g["written"] for g in groups if g.get("written")] + [p["written"] for p in phrases if p.get("written")]
    if accented and kb_content(store.cfg) in ("vi", "mixed"):
        head = ranked[:60]
        hits = {id(r): sum(1 for w in accented if w in _light_section(r[1])) for r in head}
        head.sort(key=lambda x: (x[1]["path"] in history, -x[4], -x[2], -x[3], -hits[id(x)], -x[0],
                                 x[1]["path"], x[1]["start"]))
        ranked = head + ranked[60:]
    return [(score, sec, matched) for score, sec, matched, _, _ in ranked], len(sections), mode
