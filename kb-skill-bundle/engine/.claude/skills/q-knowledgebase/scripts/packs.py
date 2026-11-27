"""Imported KB data packs. Read-only for the engine: kbpack.py writes .qkb/packs/<project>/.

A pack's settings are merged into the configuration at load time; the local .qkb/config.json always wins (lists are
extended, dictionaries only get missing keys). A pack that cannot be used (wrong format, needs a newer engine,
invalid settings) is listed with state "IGNORED (<reason>)" and changes nothing.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from core import VERSION, QError, read_text, safe_path

FORMAT = "kb-data-pack"
FORMAT_VERSION = 1
INFO_KEYS = ("pack_id", "project", "title", "kb_version", "created", "previous_version", "engine_min")
LIST_KEYS = ()


def version_key(text):
    """Comparable form of "2.1.0-d2": (2, 1, 0, "d", 2); a release without suffix ranks after its pre-releases."""
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:-([a-z]+)(\d*))?", str(text or "").strip())
    if not m:
        return None
    major, minor, patch, tag, number = m.groups()
    return (int(major), int(minor), int(patch), tag or "~", int(number or 0))


def kb_root(cfg):
    return (cfg["knowledge_paths"][0] if cfg["knowledge_paths"] else "kb").replace("\\", "/").strip("/")


def read_all(root):
    """[(project, manifest dict or None, problem or None, changelog path or None)] for every pack folder."""
    folder = safe_path(root, ".qkb/packs")
    out = []
    if not folder.is_dir():
        return out
    for item in sorted(folder.iterdir(), key=lambda p: p.name):
        if not item.is_dir():
            continue
        manifest = item / "PACK.json"
        changelog = item / "CHANGELOG.md"
        rel_changelog = changelog.relative_to(Path(root).resolve()).as_posix() if changelog.is_file() else None
        if not manifest.is_file():
            out.append((item.name, None, "PACK.json missing", rel_changelog))
            continue
        try:
            data = json.loads(read_text(manifest))
        except (ValueError, QError) as exc:
            out.append((item.name, None, "PACK.json unreadable: " + type(exc).__name__, rel_changelog))
            continue
        out.append((item.name, data if isinstance(data, dict) else None, None if isinstance(data, dict) else "not an object", rel_changelog))
    return out


def _folder_project(folder):
    """Folder name -> (project, sub): "<project>" or "<project>__<sub>" (sub-project pack)."""
    project, _, sub = folder.partition("__")
    return project, sub or None


def _problem(folder, data):
    if data.get("format") != FORMAT or data.get("format_version") != FORMAT_VERSION:
        return "format %s v%s not supported" % (data.get("format"), data.get("format_version"))
    project, sub = _folder_project(folder)
    if data.get("project") != project:
        return "project %r does not match folder %r" % (data.get("project"), folder)
    if sub is not None and data.get("sub") not in (None, sub):
        return "sub %r does not match folder %r" % (data.get("sub"), folder)
    need = data.get("engine_min")
    if need:
        have, want = version_key(VERSION), version_key(need)
        if want is None:
            return "engine_min %r unreadable" % need
        if have < want:
            return "needs engine %s or newer (this is %s)" % (need, VERSION)
    return None


def _strings(value):
    return isinstance(value, list) and all(isinstance(x, str) and x for x in value)


def _word_map(value, depth):
    if depth == 0:
        return _strings(value)
    return isinstance(value, dict) and all(isinstance(k, str) and _word_map(v, depth - 1) for k, v in value.items())


# key -> type check; PACK.json is untrusted input: a key of the wrong type makes the pack IGNORED, never a traceback.
CHECKS = {"glossary_files": _strings, "history_paths": _strings, "issue_id_patterns": _strings,
          "id_patterns": lambda v: _word_map(v, 1), "issue_fields": lambda v: _word_map(v, 1),
          "query_routes": lambda v: _word_map(v, 2), "source_roots_expected": _strings,
          "code_aliases": lambda v: isinstance(v, dict) and all(isinstance(k, str) and isinstance(x, str) and k and x
                                                               and k.endswith("/") == x.endswith("/") for k, x in v.items())}


MAX_PATTERN = 200


def _risky_repetition(pattern):
    r"""True when a group that repeats (+, *, {n,}, {n,m}) holds another repetition or an alternation, at any depth:
    "(a+)+", "((a+))*", "(a|aa)+", "(\w*x)*" - the shapes that backtrack catastrophically."""
    stack, i, n = [], 0, len(pattern)
    while i < n:
        c = pattern[i]
        if c == "\\":
            i += 2
            continue
        if c == "[":
            j = i + 1
            if j < n and pattern[j] == "^":
                j += 1
            if j < n and pattern[j] == "]":
                j += 1
            while j < n and pattern[j] != "]":
                j += 2 if pattern[j] == "\\" else 1
            i = j + 1
            continue
        if c == "(":
            stack.append(i)
        elif c == ")" and stack:
            start = stack.pop()
            following = pattern[i + 1:i + 12]
            repeats = following[:1] in ("+", "*") or re.match(r"\{\d*,\d*\}", following) is not None
            if repeats:
                inner = re.sub(r"\.", "", pattern[start + 1:i])
                inner = re.sub(r"\[[^\]]*\]", "x", inner)
                if re.search(r"[+*|]|\{\d*,\d*\}", inner):
                    return True
        i += 1
    return False


def unsafe_pattern(pattern):
    """Reason why a pack-supplied ID pattern is refused, or None. Same rules as the importer:
    length, back-references, nested / alternated repetition, compile test, never an empty match."""
    if not isinstance(pattern, str) or not pattern or len(pattern) > MAX_PATTERN:
        return "length 1-%d" % MAX_PATTERN
    if re.search(r"\\[1-9]|\\g<|\(\?P=|\(\?\(", pattern):
        return "back-reference"
    if _risky_repetition(pattern):
        return "nested or alternated repetition"
    try:
        compiled = re.compile(pattern)
    except re.error:
        return "does not compile"
    if compiled.match(""):
        return "matches empty text"
    return None


def unsafe_paths(data):
    """Pack file paths stay inside the pack's data folder: relative, no "..", glossaries are Markdown."""
    for key in ("glossary_files", "history_paths"):
        for value in data.get(key) or []:
            p = value.replace("\\", "/")
            if p.startswith("/") or re.match(r"[A-Za-z]:", p) or ".." in p.split("/"):
                return "unsafe path in %s" % key
            if key == "glossary_files" and not p.casefold().endswith(".md"):
                return "glossary file is not Markdown"
    return None


def router_routes(data):
    """Router keywords of a pack: "query_routes", else "route_keywords" when it has the router shape
    {route: {lang: [kw]}}. A plain list under "route_keywords" (older hook word list) is not for the engine."""
    if data.get("query_routes"):
        return data["query_routes"]
    value = data.get("route_keywords")
    return value if isinstance(value, dict) and value else None


def _bad_key(data):
    value = data.get("route_keywords")
    if isinstance(value, dict) and value and not _word_map(value, 2):
        return "route_keywords"
    for key, check in CHECKS.items():
        if key in data and data[key] not in (None, [], {}) and not check(data[key]):
            return key
    return None


def _settings(cfg, project, data):
    """The pack's settings with paths made repository-relative (data lives in <kb_root>/<project>/).
    Router keywords come from "query_routes" (same shape as the engine key); "route_keywords" belongs to the hooks."""
    base = kb_root(cfg) + "/" + project + "/"
    out = {}
    if data.get("glossary_files"):
        out["glossary_paths"] = [base + str(p).replace("\\", "/").lstrip("/") for p in data["glossary_files"]]
    if data.get("history_paths"):
        out["history_paths"] = [base + str(p).replace("\\", "/").lstrip("/") for p in data["history_paths"]]
    if data.get("issue_id_patterns"):
        out["issue_id_patterns"] = list(data["issue_id_patterns"])
    for key in ("id_patterns", "issue_fields"):
        if data.get(key):
            out[key] = dict(data[key])
    routes = router_routes(data)
    if routes:
        out["query_routes"] = {r: v for r, v in routes.items() if r in ("related", "impact", "path", "explore")}
    return out


def _merge_into(cfg, settings):
    merged = copy.deepcopy(cfg)
    for key, value in settings.items():
        if key in ("glossary_paths", "history_paths", "issue_id_patterns"):
            merged[key] = list(dict.fromkeys(list(merged[key]) + list(value)))
        elif key in ("id_patterns", "issue_fields"):
            for kind, items in value.items():
                merged[key][kind] = list(dict.fromkeys(list(merged[key].get(kind, [])) + list(items)))
        elif key == "query_routes":
            for route, langs in value.items():
                target = merged[key].setdefault(route, {})
                for lang, words in langs.items():
                    target[lang] = list(dict.fromkeys(list(target.get(lang, [])) + list(words)))
    return merged


def merge(root, cfg):
    """cfg with every usable pack merged; cfg["_packs"] lists all packs (state, version, changelog).
    Other files in a pack folder (kbpack's state.json, ...) are ignored."""
    from core import validate_config
    result, info = cfg, []
    for folder, data, problem, changelog in read_all(root):
        project, sub = _folder_project(folder)
        entry = {"folder": folder, "project": project, "sub": sub, "changelog": changelog}
        if data:
            entry.update({k: data.get(k) for k in INFO_KEYS if k != "project"})
            problem = problem or _problem(folder, data)
            bad = None if problem else _bad_key(data)
            if bad:
                problem = "invalid key " + bad
            if not problem:
                patterns = list(data.get("issue_id_patterns") or []) + [p for v in (data.get("id_patterns") or {}).values() for p in v]
                for pattern in patterns:
                    reason = unsafe_pattern(pattern)
                    if reason:
                        problem = "unsafe ID pattern (%s)" % reason
                        break
            if not problem:
                problem = unsafe_paths(data)
        if not problem:
            try:
                candidate = _merge_into(result, _settings(result, project, data))
                validate_config(root, candidate)
                result = candidate
                entry.update({"state": "OK", "code_aliases": dict(data.get("code_aliases") or {}),
                              "source_roots_expected": [r.replace("\\", "/").strip("/") for r in data.get("source_roots_expected") or []]})
            except (QError, TypeError, ValueError, AttributeError) as exc:
                problem = "invalid settings: " + (str(exc) if isinstance(exc, QError) else type(exc).__name__)
        if problem:
            entry["state"] = "IGNORED (" + problem + ")"
        info.append(entry)
    if info:
        result = dict(result)
        result["_packs"] = info
    return result


def of_project(cfg, project):
    """Combined view of the usable packs of a project (a project may come as several sub-project packs):
    {"code_aliases": ..., "source_roots_expected": [...]}, or None when the project has no usable pack."""
    entries = [e for e in cfg.get("_packs", []) if e["project"] == project and e["state"] == "OK"]
    if not entries:
        return None
    aliases, roots = {}, []
    for e in entries:
        for k, v in e.get("code_aliases", {}).items():
            aliases.setdefault(k, v)
        roots += [r for r in e.get("source_roots_expected", []) if r not in roots]
    return {"code_aliases": aliases, "source_roots_expected": roots}


def summary(cfg):
    """status / verify view of the packs (no settings, no aliases)."""
    return [{k: e.get(k) for k in ("folder", "project", "sub", "pack_id", "title", "kb_version", "created",
                                   "previous_version", "engine_min", "changelog", "state")} for e in cfg.get("_packs", [])]
