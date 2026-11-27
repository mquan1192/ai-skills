"""Parser interface: one module per language, one function each.

    parse(path, text, options) -> {
        "language": "python" | "cpp" | "javascript" | "typescript" | "other",
        "coverage": "FULL" | "PARTIAL" | "FILE_ONLY",
        "parser": <name>,
        "symbols": [{"name": "A.b", "kind": "...", "start": n, "end": n, "parent": "A" | None}],
        "references": [{"kind": "import" | "include", "candidates": [path, ...], "first_only": bool,
                        "start": n, "end": n, "evidence": "...", "written": "..."}],
        "meta": {...},
    }

options = {"source_paths": [...], "include_paths": [...]}. Parsers are pure functions of the text: they never read
other files, never infer calls and never guess a target - candidates are checked against the index by the caller.
"""
from __future__ import annotations

from pathlib import Path

import parser_cpp
import parser_python

LANGUAGES = {".py": "python", ".js": "javascript", ".jsx": "javascript", ".ts": "typescript", ".tsx": "typescript",
             ".c": "cpp", ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".h": "cpp", ".hpp": "cpp", ".hh": "cpp",
             ".hxx": "cpp", ".inl": "cpp"}
PARSERS = {"python": parser_python.parse, "cpp": parser_cpp.parse}


def language(path):
    return LANGUAGES.get(Path(path).suffix.casefold(), "other")


def file_only(path, text, options):
    """Fallback for languages without a parser yet (JS / TS until a syntax parser is approved)."""
    return {"language": language(path), "coverage": "FILE_ONLY", "parser": "file-only",
            "symbols": [], "references": [], "meta": {}}


def parse(path, text, options):
    return PARSERS.get(language(path), file_only)(path, text, options)
