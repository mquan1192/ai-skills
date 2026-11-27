"""Structure chunking: never cut inside a table or a code block when it fits.

split_span works on one Markdown section (heading lines already found by core.markdown_sections). Line
numbers stay the original ones; a table cut into pieces repeats its header row + separator row in
"prefix", which is stored with the chunk text but never counted in start / stop.
"""
from __future__ import annotations

import re

FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
TABLE_ROW = re.compile(r"^ {0,3}\|")
TABLE_SEPARATOR = re.compile(r"^ {0,3}\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)*\|?\s*$")


def _blocks(lines, start, end):
    """[(kind, first, stop)] 0-based half-open: 'code', 'table' or 'text' (text split at blank lines)."""
    blocks, i = [], start
    while i < end:
        line = lines[i].rstrip("\r\n")
        fence = FENCE.match(line)
        if fence:
            char, size, j = fence[1][0], len(fence[1]), i + 1
            while j < end:
                close = FENCE.match(lines[j].rstrip("\r\n"))
                j += 1
                if close and close[1][0] == char and len(close[1]) >= size and not close[2].strip():
                    break
            blocks.append(("code", i, j))
            i = j
            continue
        if TABLE_ROW.match(line) and i + 1 < end and TABLE_SEPARATOR.match(lines[i + 1].rstrip("\r\n")):
            j = i + 2
            while j < end and TABLE_ROW.match(lines[j]):
                j += 1
            blocks.append(("table", i, j))
            i = j
            continue
        j = i + 1
        if line.strip():
            while j < end and lines[j].strip() and not FENCE.match(lines[j].rstrip("\r\n")) \
                    and not (TABLE_ROW.match(lines[j]) and j + 1 < end and TABLE_SEPARATOR.match(lines[j + 1].rstrip("\r\n"))):
                j += 1
        blocks.append(("text", i, j))
        i = j
    return blocks


def _cut(kind, first, stop, lines, size):
    """Pieces of one block longer than size: (first, stop, prefix)."""
    if kind == "table":
        header = "".join(lines[first:first + 2])
        pieces, i = [], first
        while i < stop:
            room = size if i == first else max(1, size)
            j = min(stop, i + room)
            pieces.append((i, j, "" if i == first else header))
            i = j
        return pieces
    if kind == "code":
        pieces, i = [], first
        while i < stop:
            j = min(stop, i + size)
            if j < stop:   # prefer the last blank line inside the window
                blank = [k for k in range(i + 1, j) if not lines[k].strip()]
                if blank:
                    j = blank[-1] + 1
            pieces.append((i, j, ""))
            i = j
        return pieces
    return [(i, min(stop, i + size), "") for i in range(first, stop, size)]


def split_span(lines, start, end, chunk_lines):
    """-> [{"start", "stop", "prefix"}] covering [start, end) once, in order (0-based, half-open)."""
    size = max(1, int(chunk_lines))
    if end <= start:
        return []
    if end - start <= size:
        return [{"start": start, "stop": end, "prefix": ""}]
    chunks, current = [], None
    for kind, first, stop in _blocks(lines, start, end):
        if stop - first > size:
            if current:
                chunks.append(current)
                current = None
            chunks.extend({"start": a, "stop": b, "prefix": p} for a, b, p in _cut(kind, first, stop, lines, size))
            continue
        if current and stop - current["start"] <= size:
            current["stop"] = stop
        else:
            if current:
                chunks.append(current)
            current = {"start": first, "stop": stop, "prefix": ""}
    if current:
        chunks.append(current)
    return chunks
