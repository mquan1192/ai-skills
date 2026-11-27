"""Issue / ID links: IDs that the project declares by pattern, never guessed.

- Definition: a list item, a table row or a heading whose text starts with an ID, e.g.
  `- **OP-012** · Status: open · Affects: `src/a.cpp`, `docs/api.md` · Source: REQ-012`,
  `| C-12 | ... |`, `## OP-003 Start-up check`.
  -> node ISSUE (issue_id_patterns) or IDENTIFIER (id_patterns, kind in metadata); status / source fields and a
  struck-through line (~~...~~) are kept in metadata.
- AFFECTS: file paths written in backticks or Markdown links on the definition line.
- MENTIONS: every other occurrence of an ID in a section -> edge to its definition(s); an ID without a definition is
  reported, not linked.
All of this is text written in the documents (EXTRACTED). AI proposals stay in the semantic review workflow.
"""
from __future__ import annotations

import re

LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
HEADING = re.compile(r"^\s{0,3}#{1,6}\s+")
TABLE_ROW = re.compile(r"^\s*\|\s*")
DECOR = re.compile(r"^(?:\*\*|__|~~|\*|_|`|\[)*")
PATH_IN_TICKS = re.compile(r"`([^`\s]+?\.[A-Za-z0-9]{1,6})(?::\d+(?:-\d+)?(?:,\s*\d+(?:-\d+)?)*)?`")
PATH_IN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\((?:<([^>]+)>|([^\s)]+))\)")
FIELD_SPLIT = re.compile(r"\s+·\s+|\s+\|\s+|;\s+")


def compile_patterns(cfg):
    """[(kind, compiled)]; kind "issue" for issue_id_patterns, else the id_patterns key."""
    out = []
    for pattern in cfg["issue_id_patterns"]:
        out.append(("issue", re.compile(r"(?<![\w-])(" + pattern + r")(?![\w-])")))
    for kind, patterns in sorted(cfg["id_patterns"].items()):
        for pattern in patterns:
            out.append((kind, re.compile(r"(?<![\w-])(" + pattern + r")(?![\w-])")))
    return out


def find_ids(line, compiled):
    """[(id, kind, start)] in line order; one kind per position (first pattern wins)."""
    hits, taken = [], set()
    for kind, regex in compiled:
        for m in regex.finditer(line):
            if m.start(1) not in taken:
                taken.add(m.start(1))
                hits.append((m.group(1), kind, m.start(1)))
    return sorted(hits, key=lambda h: h[2])


def definition(line, compiled):
    """(id, kind) when the line defines an ID: list item / table row / heading whose text starts with it."""
    for form in (LIST_ITEM, TABLE_ROW, HEADING):
        m = form.match(line)
        if not m:
            continue
        rest = line[m.end():]
        rest = rest[len(DECOR.match(rest).group(0)):]
        for kind, regex in compiled:
            hit = regex.match(rest)
            if hit:
                return hit.group(1), kind
        return None
    return None


def fields(line, labels):
    """{"status": ..., "source": ...} from "Label: value" parts of a definition line."""
    found = {}
    plain = re.sub(r"\*\*|__", "", line)
    for part in FIELD_SPLIT.split(plain):
        if ":" not in part:
            continue
        label, value = part.split(":", 1)
        label = label.strip(" -*|`").casefold()
        for key, names in labels.items():
            if label in {n.casefold() for n in names} and key not in found:
                found[key] = value.strip(" |~*`_")
    return found


def affected_paths(line):
    """File paths on a definition line (backticks with a file suffix, Markdown links), in order, no duplicates."""
    out = []
    for m in PATH_IN_TICKS.finditer(line):
        out.append(m.group(1))
    for m in PATH_IN_LINK.finditer(line):
        target = (m.group(1) or m.group(2)).split("#")[0]
        if target and not re.match(r"^[a-zA-Z][\w+.-]*:", target):
            out.append(target)
    return list(dict.fromkeys(out))


def is_struck(line, ident_):
    return bool(re.search(r"~~[^~]*" + re.escape(ident_), line)) or line.strip().startswith("~~")
