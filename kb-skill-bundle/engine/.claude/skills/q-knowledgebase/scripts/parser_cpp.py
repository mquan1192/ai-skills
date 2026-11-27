"""C / C++ / Qt parser with the standard library only.

What it gives:
- `#include "..."` references (text facts, EXTRACTED once resolved against the index): candidates in C order -
  the including file's folder, then each configured include path, then each source root. `<...>` includes
  are system headers: counted, never resolved.
- Declarations of namespaces, classes / structs / unions, enums and functions as CANDIDATES (coverage PARTIAL).

What it does not do: no call graph, no relation guessed from names, no macro expansion, no template
instantiation, no preprocessor evaluation except skipping `#if 0` blocks. Comments and string literals are
blanked before scanning, so includes or declarations inside them are ignored.
"""
from __future__ import annotations

import posixpath
import re

KEYWORDS = {"if", "for", "while", "switch", "return", "catch", "sizeof", "alignof", "decltype", "static_assert",
            "else", "do", "case", "new", "delete", "throw", "typeid", "co_return", "co_await", "emit", "Q_EMIT",
            "foreach", "Q_FOREACH", "forever", "defined"}
INCLUDE = re.compile(r'^\s*#\s*include\s*(?:"([^"\n]+)"|<([^>\n]+)>)')
IF_ZERO = re.compile(r"^\s*#\s*if\s+(0|false)\b")
IF_ANY = re.compile(r"^\s*#\s*if(n?def)?\b")
ENDIF = re.compile(r"^\s*#\s*endif\b")
ELSE = re.compile(r"^\s*#\s*(else|elif)\b")
DEFINE = re.compile(r"^\s*#\s*define\s+([A-Za-z_]\w*)\(")
NAMESPACE = re.compile(r"^\s*(?:inline\s+)?namespace\s+([A-Za-z_]\w*(?:::\w+)*)\s*(\{|$)")
TYPE = re.compile(r"^\s*(?:template\s*<.*>\s*)?(?:typedef\s+)?(class|struct|union)\s+(?:[A-Z_][A-Z0-9_]*\s+)?"
                  r"([A-Za-z_]\w*)\s*(?:final\s*)?(?::[^;{]*)?(\{|$)")
ENUM = re.compile(r"^\s*enum\s+(?:class\s+|struct\s+)?([A-Za-z_]\w*)\s*(?::\s*[\w:\s]+)?(\{|$)")
FUNCTION = re.compile(r"^\s*(?:[\w:<>,\*&~\s\[\]]+?\s+[\*&]*)?((?:[A-Za-z_]\w*::)*~?[A-Za-z_]\w*)\s*\(([^;]*)\)"
                      r"\s*(?:const\s*)?(?:noexcept\s*)?(?:override\s*)?(?:final\s*)?(?:=\s*\w+\s*)?(?::[^;{]*)?(;|\{|$)")


TOKENS = re.compile(r"""//[^\n]*|/\*.*?(?:\*/|\Z)|"(?:\\.|[^"\\\n])*"?|'(?:\\.|[^'\\\n])*'?""", re.S)
NOT_NEWLINE = re.compile(r"[^\n]")


def blank(text):
    """Comments and string / char literals replaced by spaces (line structure kept). Literals keep their quotes."""
    def spaces(m):
        piece = m.group(0)
        if piece[0] in "\"'":
            closed = len(piece) > 1 and piece[-1] == piece[0]
            inner = piece[1:-1] if closed else piece[1:]
            return piece[0] + NOT_NEWLINE.sub(" ", inner) + (piece[0] if closed else "")
        return NOT_NEWLINE.sub(" ", piece)
    return TOKENS.sub(spaces, text)


def _active_lines(lines):
    """False for lines inside `#if 0` / `#if false` blocks (the #else branch stays active)."""
    active, stack = [], []
    for line in lines:
        if IF_ANY.match(line):
            stack.append("zero" if IF_ZERO.match(line) else "other")
            active.append(all(s != "zero" for s in stack[:-1]))
            continue
        if ELSE.match(line) and stack:
            if stack[-1] == "zero":
                stack[-1] = "zero-else"
            active.append(all(s != "zero" for s in stack))
            continue
        if ENDIF.match(line) and stack:
            stack.pop()
            active.append(all(s != "zero" for s in stack))
            continue
        active.append(all(s != "zero" for s in stack))
    return active


def _block_end(lines, start):
    """Line index of the brace that closes the first `{` at or after `start` (blanked text); None if none."""
    depth, opened = 0, False
    for j in range(start, len(lines)):
        for ch in lines[j]:
            if ch == "{":
                depth += 1; opened = True
            elif ch == "}":
                depth -= 1
                if opened and depth == 0:
                    return j
        if not opened and ";" in lines[j]:
            return None
    return None


def _not_forward(line):
    """A forward declaration (`class X;`) has no body on the line and ends with ';'."""
    return "{" in line or not line.rstrip().endswith(";")


def include_candidates(path, written, options):
    written = written.replace("\\", "/")
    bases = [posixpath.dirname(path)] + [p.replace("\\", "/").strip("/") for p in options.get("include_paths", [])] \
        + [p.replace("\\", "/").strip("/") for p in options["source_paths"]]
    out = []
    for base in bases:
        rel = posixpath.normpath(posixpath.join(base, written)) if base else posixpath.normpath(written)
        if not rel.startswith("../") and rel != ".." and rel not in out:
            out.append(rel)
    return out


def parse(path, text, options):
    raw = text.splitlines()
    lines = blank(text).splitlines()
    lines += [""] * (len(raw) - len(lines))
    active = _active_lines(lines)
    result = {"language": "cpp", "coverage": "PARTIAL", "parser": "cpp-stdlib", "symbols": [], "references": [],
              "meta": {"calls": "not extracted", "relations": "static (text facts)", "system_includes": 0,
                       "qt_object_classes": 0}}
    # Includes: the quoted name sits inside a literal, so it is read from the raw line (comment-free check on blanked).
    for i, line in enumerate(lines):
        if not active[i] or not re.match(r"^\s*#\s*include\b", line):
            continue
        match = INCLUDE.match(raw[i])
        if not match:
            continue
        if match.group(2):
            result["meta"]["system_includes"] += 1
            continue
        written = match.group(1).strip()
        result["references"].append({"kind": "include", "written": written, "first_only": True,
                                     "candidates": include_candidates(path, written, options),
                                     "start": i + 1, "end": i + 1, "evidence": raw[i].strip()})
    # Declarations (candidates). A scope stack of (name, closing line) gives qualified names.
    scopes, i = [], 0
    while i < len(lines):
        while scopes and i > scopes[-1][1]:
            scopes.pop()
        line = lines[i]
        macro = DEFINE.match(line) if active[i] else None
        if macro:   # function-like macro: a candidate of kind "macro" (never expanded)
            prefix = "::".join(s[0] for s in scopes if s[0])
            result["symbols"].append({"name": macro.group(1), "kind": "macro", "start": i + 1, "end": i + 1,
                                      "parent": prefix or None})
        if not active[i] or line.lstrip().startswith("#") or not line.strip():
            i += 1
            continue
        prefix = "::".join(s[0] for s in scopes if s[0])
        in_type = bool(scopes) and scopes[-1][2]
        found = None
        m = NAMESPACE.match(line)
        if m:
            found = ("namespace", m.group(1), True)
        else:
            m = TYPE.match(line)
            if m and _not_forward(line):
                found = (m.group(1), m.group(2), True)
            else:
                m = ENUM.match(line)
                if m and _not_forward(line):
                    found = ("enum", m.group(1), False)
        if found is None:
            joined, j = line, i
            while joined.count("(") > joined.count(")") and j + 1 < len(lines) and j - i < 6:
                j += 1
                joined += " " + lines[j].strip()
            m = FUNCTION.match(joined)
            # Without a return type, only constructors / destructors (inside a type, or written Type::name) are
            # declarations; "NAME(args)" at namespace scope is a call or a macro use, not a declaration.
            typed = bool(m) and bool(joined[:m.start(1)].strip())
            if m and not typed and not in_type and "::" not in m.group(1):
                m = None
            if m and m.group(1).split("::")[-1].lstrip("~") not in KEYWORDS and "=" not in joined.split("(")[0]:
                name = m.group(1)
                terminator = m.group(3)
                if terminator == "$" or terminator == "":
                    nxt = next((k for k in range(j + 1, min(j + 3, len(lines))) if lines[k].strip()), None)
                    terminator = "{" if nxt is not None and lines[nxt].lstrip().startswith(("{", ":")) else ";"
                kind = "declaration" if terminator == ";" else ("method" if "::" in name else "function")
                end = j if kind == "declaration" else (_block_end(lines, j) or j)
                qualified = name if "::" in name or not prefix else prefix + "::" + name
                result["symbols"].append({"name": qualified, "kind": kind, "start": i + 1, "end": end + 1,
                                          "parent": prefix or None})
                i = (end + 1) if kind != "declaration" else (j + 1)
                continue
            i += 1
            continue
        kind, name, scoped = found
        end = _block_end(lines, i)
        qualified = name if not prefix else prefix + "::" + name
        if kind in ("class", "struct", "union") and end is not None and any("Q_OBJECT" in lines[k] for k in range(i, end + 1)):
            result["meta"]["qt_object_classes"] += 1
        result["symbols"].append({"name": qualified, "kind": kind, "start": i + 1,
                                  "end": (end if end is not None else i) + 1, "parent": prefix or None})
        if scoped and end is not None:
            scopes.append((name, end, kind in ("class", "struct", "union")))
        elif kind == "enum" and end is not None:
            i = end
        i += 1
    return result
