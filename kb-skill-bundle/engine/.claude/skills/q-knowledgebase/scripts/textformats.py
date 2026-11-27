"""Other text formats: JSON / YAML / TOML / TXT indexed as text, one section per top-level key.

No parser is run on YAML / TOML (no eval, no third-party library): top-level keys are found by their line
shape. JSON is validated with the standard json module and its top-level keys are located by a small
string-aware scanner. Sections have the same keys as core.markdown_sections, so search / read / graph code
treats them like Markdown sections.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from chunking import split_span
from core import ident, json_text, slug

YAML_KEY = re.compile(r"^([^\s#\-][^:#]*?)\s*:(?:\s|$)")
TOML_TABLE = re.compile(r"^\s*\[\[?\s*([^\]]+?)\s*\]\]?\s*(?:#.*)?$")


def _json_keys(text):
    """[(key, line index)] of the top-level object keys (depth 1), or None when not a JSON object."""
    try:
        if not isinstance(json.loads(text), dict):
            return None
    except ValueError:
        return None
    keys, depth, i, line = [], 0, 0, 0
    expect_key = False
    while i < len(text):
        c = text[i]
        if c == "\n":
            line += 1
        elif c == '"':
            j, raw = i + 1, []
            while text[j] != '"':
                if text[j] == "\\":
                    raw.append(text[j:j + 2]); j += 2; continue
                raw.append(text[j]); j += 1
            if depth == 1 and expect_key:
                keys.append((json.loads('"' + "".join(raw) + '"'), line))
                expect_key = False
            i = j
        elif c in "{[":
            depth += 1
            expect_key = c == "{" and depth == 1
        elif c in "}]":
            depth -= 1
        elif c == "," and depth == 1:
            expect_key = True
        i += 1
    return keys


def _starts(path, text, lines):
    suffix = Path(path).suffix.casefold()
    if suffix == ".json":
        keys = _json_keys(text)
        return ("json", keys) if keys is not None else ("json", None)
    if suffix in (".yaml", ".yml"):
        return "yaml", [(m[1].strip().strip("\"'"), i) for i, l in enumerate(lines) if (m := YAML_KEY.match(l))]
    if suffix == ".toml":
        return "toml", [(m[1], i) for i, l in enumerate(lines) if (m := TOML_TABLE.match(l))]
    return "txt", []


def text_sections(path, text, chunk_lines):
    lines = text.splitlines(keepends=True)
    fmt, keys = _starts(path, text, lines)
    meta = {"format": fmt}
    if keys is None:
        meta["parse_status"] = "TEXT_FALLBACK"
        keys = []
    doc = ident("doc", path)
    boundaries, occurrences = [], {}
    if not keys or keys[0][1] > 0:
        heading = Path(path).name if not keys else "(preamble)"
        boundaries.append({"start": 0, "heading": heading, "hierarchy": [] if keys else [heading], "parent": doc,
                           "section_id": ident("preamble", path) if keys else ident("section", path, [heading], 0),
                           "anchor": slug(heading) if not keys else ""})
    seen_lines = set()
    for key, line in keys:
        if line in seen_lines:
            continue   # several keys on one line (minified JSON): one section
        seen_lines.add(line)
        hierarchy = [str(key)]
        occurrence = occurrences.get(json_text(hierarchy), 0)
        occurrences[json_text(hierarchy)] = occurrence + 1
        boundaries.append({"start": line, "heading": str(key), "hierarchy": hierarchy, "parent": doc,
                           "section_id": ident("section", path, hierarchy, occurrence), "anchor": slug(str(key))})
    result = []
    for i, boundary in enumerate(boundaries):
        end = boundaries[i + 1]["start"] if i + 1 < len(boundaries) else len(lines)
        for order, chunk in enumerate(split_span(lines, boundary["start"], end, chunk_lines)):
            result.append({**boundary, "id": ident(boundary["section_id"], order), "start": chunk["start"] + 1,
                           "end": chunk["stop"], "order": order,
                           "content": chunk["prefix"] + "".join(lines[chunk["start"]:chunk["stop"]])})
    return meta, result
