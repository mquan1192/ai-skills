"""Local test settings that must not ship with the bundle (names to scan for, paths of old engines, project files).

Read from (first found): env KB_TEST_LOCAL (path of a JSON file), then `kb-test-local.json` next to the bundle folder.
Keys (all optional):
  forbidden_names  list of words that must not appear in the bundle (project, customer, session names, local paths)
  old_engines      {"2.0.0": folder, "2.1.0-b1": folder} - folders holding .claude/skills/q-knowledgebase
  workspace_files  folder with one project's own kb.config.json / session.json / alias skills (checked when given)
Without the file the tests use the neutral check only (session-ID pattern) and skip the cases that need
old engines or project files.
"""
import json
import os
import re

BUNDLE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
NEUTRAL_PATTERNS = [
    re.compile(r"local_[0-9a-f]{8}-[0-9a-f]{4}", re.I),     # session IDs (REQ-… is the bundle's own request format)
]


def load():
    path = os.environ.get("KB_TEST_LOCAL") or os.path.join(os.path.dirname(BUNDLE), "kb-test-local.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    base = os.path.dirname(os.path.abspath(path))
    resolve = lambda p: p if os.path.isabs(p) else os.path.normpath(os.path.join(base, p))
    out = {"forbidden_names": [str(n).casefold() for n in data.get("forbidden_names", []) if str(n).strip()]}
    out["old_engines"] = {k: resolve(v) for k, v in (data.get("old_engines") or {}).items()}
    if data.get("workspace_files"):
        out["workspace_files"] = resolve(data["workspace_files"])
    return out


LOCAL = load()


def scan_hits(text):
    """Names / patterns found in one text (case-insensitive for names)."""
    folded = text.casefold()
    hits = [n for n in LOCAL.get("forbidden_names", [])
            if re.search(r"(?<![a-z0-9])" + re.escape(n) + r"(?![a-z0-9])", folded)]
    hits += [p.pattern for p in NEUTRAL_PATTERNS if p.search(text)]
    return hits
