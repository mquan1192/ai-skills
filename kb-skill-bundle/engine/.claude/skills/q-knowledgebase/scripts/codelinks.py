"""KB -> code references in Markdown text: pure text functions, no store.

code_refs(line)             code paths (with optional line spans) written inside backticks
alias_declarations(line)    `ALIAS` = `TARGET` pairs (directory or file aliases)
expand_aliases(...)         candidate written paths after alias replacement
line_state(count, s, e)     whether a written line span fits the current file
"""
import re

from core import CODE_EXT

CODE_SUFFIXES = tuple(sorted(set(CODE_EXT) | {".hpp", ".hh", ".hxx", ".cc", ".cxx", ".inl", ".ui", ".qml"}))

_BACKTICK = re.compile(r"`([^`\n]+)`")
# path: letters / digits / _ plus / \ . - ; no spaces or wildcard / markup characters.
_PATH = r"[\w./\\-]+"
_SPAN = r"(\d+)(?:-(\d+))?"
_REF = re.compile(r"^(" + _PATH + r")(?::" + _SPAN + r"((?:\s*,\s*\d+(?:-\d+)?)*))?$")
_EXTRA = re.compile(r"\s*,\s*" + _SPAN)
_ALIAS = re.compile(r"`([^`\n]+)`\s*(?:=>|=|→)\s*`([^`\n]+)`")


def _norm(path):
    return path.replace("\\", "/")


def is_code_path(path):
    """True when the path ends with a known code suffix (case-insensitive)."""
    return path.casefold().endswith(CODE_SUFFIXES)


def _span(written, start, end, column):
    s = int(start)
    e = int(end) if end is not None else s
    if e < s:
        return None
    return {"written": written, "start": s, "end": e, "column": column}


def code_refs(line):
    """References to code inside backticks of one Markdown line (fences are skipped by the caller).

    `a.cpp` -> start / end None; `a.cpp:10` -> 10-10; `a.cpp:10-12, 40-45` -> 2 refs.
    A span N-M with M < N is skipped; the other spans of the same backtick are kept."""
    out = []
    for m in _BACKTICK.finditer(line):
        body = m.group(1).strip()
        r = _REF.match(body)
        if not r or not is_code_path(r.group(1)):
            continue
        written, column = r.group(1), m.start()
        if r.group(2) is None:
            out.append({"written": written, "start": None, "end": None, "column": column})
            continue
        spans = [(r.group(2), r.group(3))] + [(x.group(1), x.group(2)) for x in _EXTRA.finditer(r.group(4) or "")]
        for start, end in spans:
            ref = _span(written, start, end, column)
            if ref:
                out.append(ref)
    return out


def alias_declarations(line):
    """`ALIAS` = `TARGET` pairs (also -> forms `→` and `=>`); several per line.

    Valid only when both end with "/" (directory alias) or both end with a code suffix (file alias)."""
    out = []
    for m in _ALIAS.finditer(line):
        alias, target = _norm(m.group(1).strip()), _norm(m.group(2).strip())
        if not alias or not target or " " in alias or " " in target:
            continue
        if (alias.endswith("/") and target.endswith("/")) or (is_code_path(alias) and is_code_path(target)):
            out.append((alias, target))
    return out


def expand_aliases(written, file_aliases, dir_aliases):
    """Candidate written paths in order: exact file alias, longest directory-alias prefix, written itself."""
    w = _norm(written)
    out = []

    def add(value):
        if value not in out:
            out.append(value)

    files = {_norm(k): _norm(v) for k, v in (file_aliases or {}).items()}
    dirs = {_norm(k): _norm(v) for k, v in (dir_aliases or {}).items()}
    # Aliases may chain (`LB/` = `S/lib/`, `S/` = `src/`): expand the result again, at most 5 steps.
    current, chain = w, []
    for _ in range(5):
        if current in files:
            nxt = files[current]
        else:
            best = max((k for k in dirs if k and current.startswith(k)), key=len, default=None)
            nxt = dirs[best] + current[len(best):] if best is not None else None
        if nxt is None or nxt == current or nxt in chain:
            break
        chain.append(nxt)
        current = nxt
    for value in reversed(chain):   # the fully expanded form first, then the partial ones
        add(value)
    if w in files:
        add(files[w])
    best = max((k for k in dirs if k and w.startswith(k)), key=len, default=None)
    if best is not None:
        add(dirs[best] + w[len(best):])
    add(w)
    return out


def line_state(line_count, start, end):
    """"OK" | "NO_LINES" | "LINE_OUT_OF_RANGE" for a written span against the current line count."""
    if start is None:
        return "NO_LINES"
    e = start if end is None else end
    if start < 1 or e < start or e > (line_count or 0):
        return "LINE_OUT_OF_RANGE"
    return "OK"
