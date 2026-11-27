"""Offline, standard-library-only scope, Markdown parsing and SQLite primitives."""
from __future__ import annotations

import ast
import fnmatch
import hashlib
import json
import os
import re
import sqlite3
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

VERSION = "2.1.0-e3"
SCHEMA = 2
OLD_SCHEMAS = {"1"}   # migrate.py upgrades these (keeps proposals / reviews / history)
DEFAULTS = {
    "project_name": "MyProject", "knowledge_paths": ["docs", "knowledge", "requirements"],
    "source_paths": ["src"], "network_enabled": False, "auto_modify_docs": False,
    "semantic_mode": "approval_required", "query_top_k": 5, "query_max_chars": 5000,
    "graph_default_depth": 2, "chunk_lines": 100, "exclude_patterns": [], "fts_enabled": True,
    # B0 (2.1): both optional, defaults keep 2.0.0 behaviour.
    # history_paths: glob patterns of history / log documents (e.g. "**/CHANGELOG.md"): searchable,
    #   ranked after other sections, their references create no graph edges.
    # project_roots: path prefixes below which the first segment names the project (e.g. ["kb", "projects"]);
    #   empty = knowledge_paths. Used by --project and the "project" field; no project name is built in.
    "history_paths": [], "project_roots": [],
    # Phase B (2.1.0-b): every key optional; "ranking": "classic" + "chunk_mode": "lines" give 2.1.0-b0 behaviour.
    # ranking: "rrf" (word FTS + trigram FTS + exact evidence, fused by rank) or "classic" (2.1.0-b0 scoring).
    # trigram_enabled: extra FTS5 trigram table on accent-folded text (Vietnamese, Japanese, identifiers).
    # common_glossary: also use references/glossary-common.md of this skill (generic EN / JA / VI words).
    # glossary_paths: Markdown files with term tables (one column per language) used to expand queries;
    #   glossary_columns names the header cells of each language column.
    # stopwords: question words dropped from queries, per language. query_routes: keyword lists of the
    #   query command, per route and language. chunk_mode: "structure" (tables / code kept whole) or "lines".
    # text_formats: extra file suffixes indexed as text below knowledge_paths (".json", ".yaml", ".yml",
    #   ".toml", ".txt"); empty keeps Markdown only.
    "ranking": "rrf", "trigram_enabled": True, "glossary_paths": [], "common_glossary": True,
    "glossary_columns": {"en": ["English", "Term", "EN"], "ja": ["Japanese", "JA", "日本語"],
                         "vi": ["Vietnamese", "VI", "Tiếng Việt"]},
    "stopwords": {
        "en": ["a", "an", "the", "is", "are", "was", "were", "be", "been", "of", "to", "in", "on", "at", "for", "from",
               "by", "with", "and", "or", "how", "what", "which", "who", "whom", "whose", "why", "when", "where",
               "does", "do", "did", "can", "could", "should", "would", "will", "this", "that", "these", "those",
               "it", "its", "into", "about", "there", "work", "works", "happen", "happens"],
        "vi": ["là", "của", "thì", "và", "có", "không", "được", "cho", "với", "các", "những", "một", "này", "đó",
               "gì", "nào", "bao nhiêu", "ở đâu", "như thế nào", "thế nào", "tại sao", "vì sao", "khi", "nếu",
               "hoạt động", "ra sao", "làm sao", "đâu",
               # question patterns and particles
               "khi nào", "lúc nào", "bao giờ", "bao lâu", "là gì", "có phải", "làm thế nào", "bằng cách nào",
               "mấy", "hay", "hoặc", "bị", "đã", "sẽ", "đang", "rồi", "vậy", "nhé", "ạ", "theo", "về", "để", "trong",
               "diễn ra", "xảy ra", "mỗi", "sau bao nhiêu", "sau bao lâu", "mất bao lâu", "trong bao lâu",
               "gồm những", "có những", "những gì", "bao gồm những"],
        "ja": ["とは", "どう", "なぜ", "どこ", "いくつ"]},
    "query_routes": {
        "related": {"en": ["depends on", "dependencies of", "dependency of", "uses", "used by"],
                    "vi": ["phụ thuộc", "liên quan"], "ja": ["依存"]},
        "impact": {"en": ["impact", "affected by", "if i change", "what breaks"],
                   "vi": ["ảnh hưởng", "nếu sửa", "nếu đổi"], "ja": ["影響"]},
        "path": {"en": ["from * to *", "between * and *"], "vi": ["từ * đến *", "từ * tới *"], "ja": ["* から * まで", "* から * へ"]},
        "explore": {"en": ["how does", "how do", "how is", "how are", "explain"],
                    "vi": ["hoạt động thế nào", "như thế nào", "thế nào", "ra sao", "làm thế nào", "làm sao",
                           "bằng cách nào", "cơ chế"], "ja": ["仕組み", "どのように"]}},
    "chunk_mode": "structure", "text_formats": [],
    # Phase C1 + E (2.1.0-c1): every key optional; empty values keep 2.1.0-b1 behaviour.
    # cpp_include_paths: folders searched for #include "..." after the including file's folder (then source_paths).
    # code_aliases: {"alias": "path"} for KB -> code references: a file alias ("svc.cpp": "service/service.cpp") or a
    #   folder alias ending with "/" ("SV/": "service/"); KB pages may also declare `alias` = `path` lines (that page only).
    # issue_id_patterns: regular expressions of issue IDs (e.g. "OP-\d+"); id_patterns: {kind: [patterns]} for other IDs
    #   (requirement, test, document, ...). A list item, table row or heading starting with an ID defines it.
    # issue_fields: labels read on a definition line ("Status: open · Affects: `a.cpp`").
    # languages.kb_content = main language of the KB text: "vi", "en", "ja" or "mixed" (default).
    #   vi / mixed: accented words as written rank first; ja: no Latin phrase merging.
    "languages": {"kb_content": "mixed"},
    # Optional local model search, OFF by default. backend "none" | "onnx-local"; model = folder name under
    #   .qkb/models/ (placed by the bundle's download script with MODEL.txt); mode auto (only when the router needs it)
    #   | on | off; weight of the model list in the rank fusion; min_words of a question before auto may use it;
#   min_coverage: auto uses the model only when the best text hit covers less than this share of the question's concepts.
    "embedding": {"backend": "none", "model": "", "mode": "auto", "weight": 1.0, "min_words": 3, "min_coverage": 0.6},
    # usage_log (2.1.0-e3): optional log of search-type calls (usage.py); empty path = off. query_text: also log the question.
    "usage_log": {"path": "", "query_text": False, "miss_score": 0},
    "cpp_include_paths": [], "code_aliases": {}, "issue_id_patterns": [], "id_patterns": {},
    "issue_fields": {"status": ["Status", "State", "Trạng thái", "状態", "ステータス"],
                     "affects": ["Affects", "Impact", "Ảnh hưởng", "影響", "影響範囲"],
                     "source": ["Source", "Nguồn", "出典", "根拠"]},
}
TEXT_FORMATS = (".json", ".yaml", ".yml", ".toml", ".txt")
# Strings that are not paths (patterns, placeholders, prose): never extracted as references.
NOT_A_PATH = re.compile(r"[*?<>{}\[\]|\s]")
NODE_TYPES = set("PROJECT DOMAIN MODULE COMPONENT SERVICE API DATABASE TABLE ENTITY WORKFLOW BUSINESS_RULE REQUIREMENT DECISION DOCUMENT SECTION CODE_FILE CODE_SYMBOL ISSUE IDENTIFIER".split())
REL_TYPES = set("CONTAINS REFERENCES DOCUMENTS IMPLEMENTS DEPENDS_ON CALLS IMPORTS USES AFFECTS CONSTRAINS REQUIRES SUPERSEDES CONFLICTS_WITH RELATED_TO MENTIONS".split())
HARD_DENY = set(".git .qkb .claude .agents .codex .aws .ssh credentials secrets keys node_modules dist build target .venv venv __pycache__".split())
CODE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".cs", ".go", ".rs", ".sql", ".c", ".cpp", ".h",
            ".hpp", ".hh", ".hxx", ".cc", ".cxx", ".inl"}


class QError(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode("utf-8")).hexdigest()


def ident(*parts):
    return digest(json.dumps(parts, ensure_ascii=False, sort_keys=True))[:24]


def fold(text):
    text = unicodedata.normalize("NFKD", text.casefold()).replace("đ", "d")
    return "".join(c for c in text if not unicodedata.combining(c))


def slug(text):
    return re.sub(r"[^\w\- ]", "", text.casefold()).replace(" ", "-")


def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def safe_path(root, relative):
    """Reject traversal, drive/UNC paths, every symlink and Windows ADS."""
    root = Path(root).resolve()
    raw = str(relative).replace("\\", "/")
    if not raw or raw.startswith("/") or ":" in raw or ".." in raw.split("/"):
        raise QError("Path must be repository-relative without traversal or drive syntax")
    p = root
    for part in raw.split("/"):
        if part in ("", "."):
            continue
        p = p / part
        if p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction()):
            raise QError("Symlinks and junctions are not allowed")
    try:
        p.resolve().relative_to(root)
    except ValueError as exc:
        raise QError("Path escapes repository") from exc
    return p


def read_text(path):
    try:
        return path.read_bytes().decode("utf-8-sig")
    except UnicodeError as exc:
        raise QError("Expected UTF-8 or UTF-8 BOM text") from exc


def load_config(root, packs=True):
    """.qkb/config.json over DEFAULTS, validated; then the settings of imported data packs
    (.qkb/packs/<project>/PACK.json) merged in - local values always win. packs=False = the file only."""
    path = safe_path(root, ".qkb/config.json")
    cfg = dict(DEFAULTS)
    if path.exists():
        data = json.loads(read_text(path))
        if not isinstance(data, dict) or set(data) - set(DEFAULTS):
            raise QError("Unknown configuration keys or invalid configuration")
        cfg.update(data)
    validate_config(root, cfg)
    if packs:
        import packs as packs_module
        cfg = packs_module.merge(root, cfg)
    return cfg


def validate_config(root, cfg):
    if cfg["network_enabled"] is not False or cfg["auto_modify_docs"] is not False:
        raise QError("This engine only supports network_enabled=false and auto_modify_docs=false")
    if cfg["semantic_mode"] != "approval_required":
        raise QError("semantic_mode must be approval_required")
    for key in ("knowledge_paths", "source_paths", "exclude_patterns", "history_paths", "project_roots"):
        if not isinstance(cfg[key], list) or any(not isinstance(x, str) or not x for x in cfg[key]):
            raise QError("Configuration path/pattern lists must contain nonempty strings")
    for key in ("knowledge_paths", "source_paths"):
        for value in cfg[key]:
            safe_path(root, value)
            if value.replace("\\", "/").strip("/.") == "":
                raise QError("Configure explicit subdirectories or files, not repository root")
    for key in ("query_top_k", "query_max_chars", "graph_default_depth", "chunk_lines"):
        if type(cfg[key]) is not int or cfg[key] < 1:
            raise QError("Configuration budgets must be positive integers")
    if cfg["graph_default_depth"] > 8 or type(cfg["fts_enabled"]) is not bool:
        raise QError("Depth must be at most 8; fts_enabled must be boolean")
    # Phase B keys
    if cfg["ranking"] not in ("rrf", "classic") or cfg["chunk_mode"] not in ("structure", "lines"):
        raise QError("ranking must be rrf or classic; chunk_mode must be structure or lines")
    if type(cfg["trigram_enabled"]) is not bool or type(cfg["common_glossary"]) is not bool:
        raise QError("trigram_enabled and common_glossary must be boolean")
    for key in ("glossary_paths", "text_formats"):
        if not isinstance(cfg[key], list) or any(not isinstance(x, str) or not x for x in cfg[key]):
            raise QError("Configuration path/pattern lists must contain nonempty strings")
    for value in cfg["glossary_paths"]:
        safe_path(root, value)
    if any(x.casefold() not in TEXT_FORMATS for x in cfg["text_formats"]):
        raise QError("text_formats accepts only " + ", ".join(TEXT_FORMATS))

    def word_lists(value, depth):
        if depth == 0:
            return isinstance(value, list) and all(isinstance(x, str) and x.strip() for x in value)
        return isinstance(value, dict) and all(isinstance(k, str) and word_lists(v, depth - 1) for k, v in value.items())
    if not word_lists(cfg["glossary_columns"], 1) or not word_lists(cfg["stopwords"], 1):
        raise QError("glossary_columns and stopwords map a language code to a list of words")
    if not word_lists(cfg["query_routes"], 2) or set(cfg["query_routes"]) - {"related", "impact", "path", "explore"}:
        raise QError("query_routes maps related / impact / path / explore to {language: [keywords]}")
    # Phase C1 + E keys
    for value in cfg["cpp_include_paths"] if isinstance(cfg["cpp_include_paths"], list) else [None]:
        if not isinstance(value, str) or not value:
            raise QError("cpp_include_paths must list nonempty repository-relative folders")
        safe_path(root, value)
    if not isinstance(cfg["code_aliases"], dict) or any(not isinstance(k, str) or not isinstance(v, str) or not k or not v
                                                        or (k.endswith("/") != v.endswith("/")) for k, v in cfg["code_aliases"].items()):
        raise QError("code_aliases maps an alias to a path; folder aliases and their targets both end with '/'")
    patterns = cfg["issue_id_patterns"] if isinstance(cfg["issue_id_patterns"], list) else [None]
    if not word_lists(cfg["id_patterns"], 1) or not isinstance(cfg["issue_id_patterns"], list):
        raise QError("issue_id_patterns is a list of patterns; id_patterns maps a kind to a list of patterns")
    for pattern in patterns + [p for v in cfg["id_patterns"].values() for p in v]:
        try:
            if not isinstance(pattern, str) or not pattern or re.compile(pattern).match(""):
                raise QError("ID patterns must be nonempty and must not match an empty string")
        except re.error as exc:
            raise QError("Invalid ID pattern: " + str(exc)) from exc
    if not word_lists(cfg["issue_fields"], 1):
        raise QError("issue_fields maps status / affects / source to a list of labels")
    languages = cfg["languages"]
    if not isinstance(languages, dict) or set(languages) - {"kb_content"} or             languages.get("kb_content", "mixed") not in ("vi", "en", "ja", "mixed"):
        raise QError('languages must be {"kb_content": "vi" | "en" | "ja" | "mixed"}')
    emb = cfg["embedding"]
    import vectors
    if not isinstance(emb, dict) or set(emb) - {"backend", "model", "mode", "weight", "min_words", "min_coverage"}             or emb.get("backend", "none") not in ("none", *vectors.BACKENDS) or emb.get("mode", "auto") not in ("auto", "on", "off")             or not isinstance(emb.get("model", ""), str) or not isinstance(emb.get("weight", 1.0), (int, float))             or type(emb.get("min_words", 3)) is not int or emb.get("min_words", 3) < 1             or not isinstance(emb.get("min_coverage", 0.6), (int, float)) or not 0 <= emb.get("min_coverage", 0.6) <= 1:
        raise QError('embedding must be {"backend": "none" | "onnx-local", "model": "<folder>", "mode": "auto" | "on" | "off", "weight": <number>, "min_words": <int>}')
    log = cfg["usage_log"]
    if not isinstance(log, dict) or set(log) - {"path", "query_text", "miss_score"} or not isinstance(log.get("path", ""), str)             or not isinstance(log.get("query_text", False), bool) or type(log.get("miss_score", 0)) not in (int, float):
        raise QError('usage_log must be {"path": "<relative folder>", "query_text": true | false, "miss_score": <number>}')
    if log.get("path"):
        safe_path(root, log["path"])          # relative, inside the root, no traversal / drive / link
    return cfg


def glob_regex(pattern):
    # Git wildmatch essentials: * never crosses /, ** may cross directories.
    out, i = "", 0
    while i < len(pattern):
        c = pattern[i]
        if pattern[i:i+3] == "**/":
            out += "(?:.*/)?"; i += 3; continue
        if pattern[i:i+2] == "**":
            out += ".*"; i += 2; continue
        if c == "*": out += "[^/]*"
        elif c == "?": out += "[^/]"
        else: out += re.escape(c)
        i += 1
    return out


class Scope:
    def __init__(self, root, cfg):
        self.root, self.cfg = Path(root).resolve(), cfg
        self.ignore_cache = {}
        self.read_errors = []
        self._pack_folders = None

    def pack_folders(self):
        """'<kb_root>/<project>/' of every pack folder found (usable or ignored): data that came from a pack."""
        if self._pack_folders is None:
            import packs
            base = packs.kb_root(self.cfg)
            self._pack_folders = sorted({base + "/" + e["project"] + "/" for e in self.cfg.get("_packs", []) if e.get("project")})
        return self._pack_folders

    def _rules(self, folder):
        key = str(folder)
        if key not in self.ignore_cache:
            rules = []
            for name in (".gitignore", ".qkbignore"):
                file = safe_path(self.root, (folder / name).relative_to(self.root).as_posix())
                if file.is_file():
                    rules.extend(read_text(file).splitlines())
            self.ignore_cache[key] = rules
        return self.ignore_cache[key]

    @staticmethod
    def match(relative, is_dir, pattern):
        pattern = pattern.rstrip()
        directory = pattern.endswith("/")
        pattern = pattern.rstrip("/")
        anchored = pattern.startswith("/")
        pattern = pattern.lstrip("/")
        if not pattern:
            return False
        if directory and not is_dir:
            return False
        if "/" not in pattern and not anchored:
            return bool(re.fullmatch(glob_regex(pattern), relative.split("/")[-1]))
        return bool(re.fullmatch(glob_regex(pattern), relative))

    def allowed(self, relative, is_dir=False):
        raw = str(relative).replace("\\", "/")
        try:
            p = safe_path(self.root, raw)
        except QError:
            return False
        parts = Path(raw).parts
        if any(x.casefold() in HARD_DENY or x.casefold().startswith(".env") for x in parts):
            return False
        # Check every ancestor independently: an excluded directory cannot be
        # re-included just by unignoring its child (same principle as Git).
        for count in range(1, len(parts) + 1):
            partial = Path(*parts[:count])
            directory = count < len(parts) or is_dir
            excluded = False
            for depth in range(count):
                base = self.root.joinpath(*parts[:depth])
                rel = Path(*parts[depth:count]).as_posix()
                rules = self._rules(base)
                if depth == 0:
                    rules = rules + self.cfg["exclude_patterns"]
                for rule in rules:
                    if not rule or rule.startswith("#"):
                        continue
                    negate = rule.startswith("!")
                    pattern = rule[1:] if negate else rule
                    if self.match(rel, directory, pattern):
                        excluded = not negate
            if excluded:
                return False
        return p.exists()

    def category(self, relative):
        p = Path(str(relative).replace("\\", "/"))
        # In the folder of an imported data pack only Markdown is indexed (no text formats, no code),
        # whatever the pack or the local configuration says.
        rel = p.as_posix()
        if any(rel.startswith(folder) for folder in self.pack_folders()) and p.suffix.casefold() != ".md":
            return None
        for key, cat in (("knowledge_paths", "markdown"), ("source_paths", "code")):
            for value in self.cfg[key]:
                parent = Path(value.replace("\\", "/"))
                if p == parent or parent in p.parents:
                    if cat == "markdown" and p.suffix.casefold() == ".md":
                        return cat
                    if cat == "markdown" and p.suffix.casefold() in {x.casefold() for x in self.cfg["text_formats"]}:
                        return cat   # indexed as text sections (textformats.py)
                    if cat == "code" and p.suffix.casefold() in CODE_EXT:
                        return cat
        return None

    def is_history(self, relative):
        rel = str(relative).replace("\\", "/")
        return any(re.fullmatch(glob_regex(p.replace("\\", "/").lstrip("/")), rel) for p in self.cfg["history_paths"])

    def project(self, relative):
        """First path segment below the longest configured project root; None outside every root."""
        rel = str(relative).replace("\\", "/")
        roots = self.cfg["project_roots"] or self.cfg["knowledge_paths"]
        best = None
        for root in roots:
            r = root.replace("\\", "/").strip("/")
            if rel.startswith(r + "/") and (best is None or len(r) > len(best)):
                best = r
        if best is None:
            return None
        rest = rel[len(best)+1:].split("/")
        return rest[0] if len(rest) > 1 else None

    def in_project(self, relative, project):
        """--project filter. project = one name, a path below a project root
        ("name/sub") or a comma list of them ("name/sub,shared"); None = everything."""
        if project is None:
            return True
        wanted = [p.strip().replace("\\", "/").strip("/") for p in (project.split(",") if isinstance(project, str) else project)]
        wanted = [p for p in wanted if p]
        rel = str(relative).replace("\\", "/")
        roots = self.cfg["project_roots"] or self.cfg["knowledge_paths"]
        best = None
        for root in roots:
            r = root.replace("\\", "/").strip("/")
            if rel.startswith(r + "/") and (best is None or len(r) > len(best)):
                best = r
        if best is None:
            return False
        below = rel[len(best) + 1:]
        return any(below.startswith(w + "/") for w in wanted)

    def read(self, relative):
        if not self.category(relative) or not self.allowed(relative):
            raise QError("File is missing, ignored, or outside configured knowledge/source paths")
        p = safe_path(self.root, relative)
        if not p.is_file():
            raise QError("Expected a regular source file")
        raw = p.read_bytes()
        try:
            return raw.decode("utf-8-sig"), digest(raw), len(raw)
        except UnicodeError as exc:
            raise QError("Source is not UTF-8") from exc

    def scan(self):
        found = {}
        for key in ("knowledge_paths", "source_paths"):
            for value in self.cfg[key]:
                start = safe_path(self.root, value)
                if not start.exists() or not self.allowed(start.relative_to(self.root).as_posix(), start.is_dir()):
                    continue
                if start.is_file():
                    paths = [start]
                else:
                    paths = []
                    for folder, dirs, names in os.walk(start, followlinks=False):
                        dirs[:] = sorted(d for d in dirs if self.allowed((Path(folder)/d).relative_to(self.root).as_posix(), True))
                        paths.extend(Path(folder)/n for n in sorted(names))
                for p in paths:
                    rel = p.relative_to(self.root).as_posix()
                    cat = self.category(rel)
                    if cat and self.allowed(rel):
                        found[rel] = cat
        return dict(sorted(found.items()))


def metadata(lines):
    """Conservative YAML subset; keep unsupported values as raw text, never eval."""
    result, end = {}, 0
    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], 1):
            if line.strip() in ("---", "..."):
                end = i + 1
                break
        if end:
            for line in lines[1:end-1]:
                match = re.match(r"^([\w-]+):\s*(.*?)\s*$", line)
                if match:
                    key, value = match.groups()
                    try:
                        result[key] = json.loads(value)
                    except (ValueError, TypeError):
                        result[key] = value.strip("\"'")
    return result, end


def markdown_sections(path, text, chunk_lines, mode="lines"):
    """Disjoint spans cover every original line, including frontmatter and fences."""
    lines = text.splitlines(keepends=True)
    meta, front_end = metadata(lines)
    boundaries, stack, fence = [], [], None
    occurrences, anchors = {}, {}
    for i, raw in enumerate(lines):
        if i < front_end:
            continue
        fence_match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", raw.rstrip("\r\n"))
        if fence:
            if fence_match and fence_match[1][0] == fence[0] and len(fence_match[1]) >= fence[1] and not fence_match[2].strip():
                fence = None
            continue
        if fence_match:
            fence = (fence_match[1][0], len(fence_match[1])); continue
        match = re.match(r"^ {0,3}(#{1,6})(?:[ \t]+(.*)|[ \t]*)$", raw.rstrip("\r\n"))
        if match:
            level, heading = len(match[1]), re.sub(r"\s+#+\s*$", "", match[2] or "").strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            hierarchy = [x[1] for x in stack] + [heading]
            key = json_text(hierarchy)
            occurrence = occurrences.get(key, 0)
            occurrences[key] = occurrence + 1
            sid = ident("section", path, hierarchy, occurrence)
            base_anchor = slug(heading)
            n = anchors.get(base_anchor, 0); anchors[base_anchor] = n + 1
            anchor = base_anchor if n == 0 else base_anchor + "-" + str(n)
            boundaries.append({"start": i, "heading": heading, "hierarchy": hierarchy,
                               "parent": stack[-1][2] if stack else ident("doc", path),
                               "section_id": sid, "anchor": anchor})
            stack.append((level, heading, sid))
    if not boundaries or boundaries[0]["start"] > 0:
        boundaries.insert(0, {"start": 0, "heading": "(preamble)", "hierarchy": [],
                              "parent": ident("doc", path), "section_id": ident("preamble", path), "anchor": ""})
    result = []
    for i, boundary in enumerate(boundaries):
        end = boundaries[i+1]["start"] if i+1 < len(boundaries) else len(lines)
        if mode == "structure":
            # Tables / code blocks kept whole when they fit; long tables repeat their header.
            from chunking import split_span
            spans = [(c["start"], c["stop"], c["prefix"]) for c in split_span(lines, boundary["start"], end, chunk_lines)]
        else:
            spans = [(start, min(start + chunk_lines, end), "") for start in range(boundary["start"], end, chunk_lines)]
        for order, (start, stop, prefix) in enumerate(spans):
            result.append({**boundary, "id": ident(boundary["section_id"], order),
                           "start": start+1, "end": stop, "order": order,
                           "content": prefix + "".join(lines[start:stop])})
    return meta, result


DDL = """
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE files(path TEXT PRIMARY KEY, hash TEXT NOT NULL, bytes INTEGER, category TEXT,
 metadata TEXT NOT NULL, indexed_at TEXT NOT NULL);
CREATE TABLE sections(id TEXT PRIMARY KEY, section_id TEXT NOT NULL, path TEXT NOT NULL,
 heading TEXT, hierarchy TEXT, anchor TEXT, start INTEGER, end INTEGER, ordering INTEGER,
 content TEXT NOT NULL, normalized TEXT NOT NULL);
CREATE INDEX sections_path ON sections(path);
CREATE TABLE nodes(id TEXT PRIMARY KEY, type TEXT NOT NULL, label TEXT NOT NULL,
 path TEXT NOT NULL, start INTEGER, end INTEGER, heading TEXT, status TEXT NOT NULL,
 hash TEXT NOT NULL, metadata TEXT NOT NULL);
CREATE INDEX nodes_path ON nodes(path);
CREATE INDEX nodes_label ON nodes(label);
CREATE TABLE edges(id TEXT PRIMARY KEY, source TEXT NOT NULL, target TEXT NOT NULL,
 relation TEXT NOT NULL, origin TEXT NOT NULL, path TEXT NOT NULL, heading TEXT,
 start INTEGER, end INTEGER, evidence TEXT, hash TEXT NOT NULL, target_hash TEXT,
 state TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE INDEX edges_source ON edges(source,relation);
CREATE INDEX edges_target ON edges(target,relation);
CREATE TABLE refs(id TEXT PRIMARY KEY, source TEXT, path TEXT, target_path TEXT,
 anchor TEXT, relation TEXT, start INTEGER, end INTEGER, evidence TEXT, hash TEXT,
 written TEXT, resolution TEXT, candidates TEXT);
CREATE TABLE history(id INTEGER PRIMARY KEY, at TEXT, reason TEXT, path TEXT, snapshot TEXT);
CREATE TABLE proposals(id TEXT PRIMARY KEY, payload TEXT NOT NULL, decision TEXT NOT NULL,
 validation TEXT NOT NULL, reviewer TEXT, rationale TEXT, created_at TEXT, updated_at TEXT);
CREATE TABLE reviews(id INTEGER PRIMARY KEY, proposal_id TEXT, at TEXT, action TEXT,
 reviewer TEXT, rationale TEXT);
"""


TRIGRAM_FORMAT = "2"   # 2 = folded text + canonical number / date / unit tokens


def trigram_text(content):
    """Trigram row text: folded content plus one line of canonical number tokens ("1.234,5" -> "1234.5",
    "17/11/2026" -> "2026-11-17"), so a number written another way still finds the section."""
    import vntext
    tokens = vntext.numbers(content)
    return fold(content) + ("\n" + " ".join(sorted(tokens)) if tokens else "")


def connect_readonly(path):
    """SQLite connection that cannot write (URI mode=ro); works with spaces and non-ASCII paths."""
    db = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True, timeout=15)
    db.row_factory = sqlite3.Row
    return db


class Store:
    def __init__(self, root, cfg, create=False, readonly=False):
        self.root, self.cfg = Path(root).resolve(), cfg
        self.scope = Scope(self.root, cfg)
        self.path = safe_path(self.root, ".qkb/cache/index.sqlite3")
        for suffix in ("-journal", "-wal", "-shm"):
            safe_path(self.root, ".qkb/cache/index.sqlite3" + suffix)
        if not create and not self.path.exists():
            raise QError("Index missing. Preview with init --dry-run, configure scope, then build")
        new_db = not self.path.exists()
        if create:
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        # Read-only commands open the index read-only (no journal, no accidental write).
        self.readonly = readonly and not create
        self.db = connect_readonly(self.path) if self.readonly else sqlite3.connect(self.path, timeout=15)
        if new_db and os.name == "posix":
            self.path.chmod(0o600)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        if not self.db.execute("SELECT name FROM sqlite_master WHERE name='meta'").fetchone():
            if not create:
                self.db.close(); raise QError("Index schema missing; restore a valid backup")
            self.db.executescript(DDL)
            self.setmeta("schema", str(SCHEMA))
            self.setmeta("fts", "false")
            if cfg["fts_enabled"]:
                try:
                    self.db.execute("CREATE VIRTUAL TABLE search_fts USING fts5(id UNINDEXED, heading, content, tokenize='unicode61 remove_diacritics 2')")
                    self.setmeta("fts", "true")
                except sqlite3.OperationalError:
                    pass
            self.db.commit()
        if self.getmeta("schema") != str(SCHEMA):
            old = self.getmeta("schema")
            self.db.close()
            if old in OLD_SCHEMAS:
                raise QError("Index schema " + old + " is older than " + str(SCHEMA) + "; run migrate --dry-run, then migrate (keeps proposals, reviews, history)")
            raise QError("Unsupported index schema; preserve backup before migration")
        self.has_fts = self.getmeta("fts") == "true"
        self.fts = self.has_fts and cfg["fts_enabled"]
        self.has_tri = bool(self.db.execute("SELECT name FROM sqlite_master WHERE name='search_tri'").fetchone())
        self.trigram = self.has_tri and cfg["fts_enabled"] and cfg["trigram_enabled"]
        self.hash_cache = {}

    def ensure_indexes(self):
        """Phase C1: per-path deletes run on every changed file; code files add many edges, so edges and refs get a
        path index (plain SQL indexes, no schema change; created once by the next writer)."""
        self.db.execute("CREATE INDEX IF NOT EXISTS edges_path ON edges(path)")
        self.db.execute("CREATE INDEX IF NOT EXISTS refs_path ON refs(path)")
        # KB -> code line spans, rebuilt by resolve_refs on every update.
        self.db.execute("CREATE TABLE IF NOT EXISTS code_spans(ref_id TEXT, source_path TEXT, target_path TEXT,"
                        " start INTEGER, end INTEGER, target_hash TEXT)")

    def ensure_trigram(self):
        """Create and fill the trigram table once (2.1.0-b0 indexes get it on the next update / build).
        Text is accent-folded before indexing, so plain trigram matching works on SQLite >= 3.34."""
        if self.has_tri and self.getmeta("trigram_format") == TRIGRAM_FORMAT:
            return False
        if not (self.cfg["fts_enabled"] and self.cfg["trigram_enabled"]) and not self.has_tri:
            return False
        if not self.has_tri:
            try:
                self.db.execute("CREATE VIRTUAL TABLE search_tri USING fts5(id UNINDEXED, heading, content, tokenize='trigram')")
            except sqlite3.OperationalError:
                return False   # SQLite without the trigram tokenizer: substring fallback stays
        # Rows written by an older version lack the number tokens -> refill once.
        self.db.execute("DELETE FROM search_tri")
        for sec in self.db.execute("SELECT id, heading, content FROM sections").fetchall():
            self.db.execute("INSERT INTO search_tri VALUES (?,?,?)", (sec[0], fold(sec[1] or ""), trigram_text(sec[2])))
        self.setmeta("trigram_format", TRIGRAM_FORMAT)
        self.has_tri = True
        self.trigram = self.cfg["fts_enabled"] and self.cfg["trigram_enabled"]
        return True

    def __enter__(self): return self
    def __exit__(self, *args): self.db.close()
    def rows(self, sql, params=()): return [dict(r) for r in self.db.execute(sql, params)]
    def setmeta(self, key, value):
        self.db.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, str(value)))
    def getmeta(self, key):
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

    def source_status(self, path, expected_hash):
        if path not in self.hash_cache:
            try:
                self.hash_cache[path] = self.scope.read(path)[1]
            except (QError, OSError):
                self.hash_cache[path] = None
        current = self.hash_cache[path]
        return "BROKEN" if current is None else "CURRENT" if current == expected_hash else "STALE"

    def node(self, id_, type_, label, path, start, end, heading, hash_, meta=None, status="CONFIRMED"):
        if type_ not in NODE_TYPES:
            raise QError("Unsupported node type")
        self.db.execute("INSERT OR REPLACE INTO nodes VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (id_, type_, label, path, start, end, heading, status, hash_, json_text(meta or {})))

    def edge(self, source, target, relation, path, heading, start, end, evidence, hash_, state="CURRENT", target_hash=None):
        if relation not in REL_TYPES:
            raise QError("Unsupported relationship type")
        id_ = ident("edge", source, target, relation, path, start)
        timestamp = now()
        self.db.execute("""INSERT INTO edges VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET heading=excluded.heading,end=excluded.end,
            evidence=excluded.evidence,hash=excluded.hash,target_hash=excluded.target_hash,
            state=excluded.state,updated_at=excluded.updated_at""",
            (id_, source, target, relation, "EXTRACTED", path, heading, start, end,
             evidence, hash_, target_hash, state, timestamp, timestamp))

    def ref(self, source, path, target_path, anchor, relation, start, end, evidence, hash_, written=None, order=None):
        """order: ordered candidate list of an #include (the first one in the index wins, C search order)."""
        self.db.execute("INSERT OR REPLACE INTO refs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (ident(source, target_path, anchor, start, relation), source, path,
                         target_path, anchor, relation, start, end, evidence, hash_, written, None,
                         json_text(order) if order else None))

    def archive(self, path, reason):
        # Candidate symbols of partial parsers (C++ declarations) and their CONTAINS edges are re-derived from the
        # source on every parse; they are counted, not copied, so a code file change does not bloat history.
        nodes = self.rows("SELECT * FROM nodes WHERE path=?", (path,))
        candidates = {n["id"] for n in nodes if n["type"] == "CODE_SYMBOL" and n["status"] == "CANDIDATE"}
        edges = self.rows("SELECT * FROM edges WHERE path=?", (path,))
        snapshot = {"file": self.rows("SELECT * FROM files WHERE path=?", (path,)),
                    "nodes": [n for n in nodes if n["id"] not in candidates],
                    "edges": [e for e in edges if e["target"] not in candidates]}
        if candidates:
            snapshot["candidate_symbols"] = len(candidates)
        self.db.execute("INSERT INTO history(at,reason,path,snapshot) VALUES (?,?,?,?)",
                        (now(), reason, path, json_text(snapshot)))

    def remove_file(self, path, reason):
        self.archive(path, reason)
        if self.has_fts:
            self.db.execute("DELETE FROM search_fts WHERE id IN (SELECT id FROM sections WHERE path=?)", (path,))
        if self.has_tri:
            self.db.execute("DELETE FROM search_tri WHERE id IN (SELECT id FROM sections WHERE path=?)", (path,))
        for table in ("files", "sections", "nodes", "edges", "refs"):
            self.db.execute("DELETE FROM " + table + " WHERE path=?", (path,))


def candidate_paths(store, path, written):
    """Ordered resolver candidates (steps 1-6); each is a repository-relative path in scope.
    1 relative to the writing file, 2 from the repository root, 3-5 from each ancestor of the writing
    file up to its knowledge root (sub-project KB root, project KB root, knowledge root), 6 from each
    source root. Step 7 (unique file name) needs the file list and runs in engine.resolve_refs."""
    out, seen = [], set()
    written = written.replace("\\", "/")
    def add(candidate):
        try:
            rel = os.path.normpath(candidate).replace("\\", "/")
            safe_path(store.root, rel)
        except (QError, ValueError):
            return
        if rel not in seen and store.scope.category(rel):
            seen.add(rel); out.append(rel)
    add(str(Path(path).parent / written))
    add(written)
    parent = Path(path).parent
    roots = [k.replace("\\", "/").strip("/") for k in store.cfg["knowledge_paths"]]
    root = next((r for r in roots if path.startswith(r + "/")), None)
    while root is not None and parent.as_posix() != root and parent.as_posix() not in (".", ""):
        parent = parent.parent
        add(str(parent / written))
        if parent.as_posix() == root:
            break
    for source in store.cfg["source_paths"]:
        add(str(Path(source) / written))
    return out


def decode_link(value):
    # Pure parsing only, no network access; percent-encoded UTF-8 local filenames.
    from urllib.parse import unquote
    return unquote(value)


def extract_markdown(store, path, text, hash_):
    if Path(path).suffix.casefold() in TEXT_FORMATS:
        from textformats import text_sections   # JSON / YAML / TOML / TXT as text
        meta, sections = text_sections(path, text, store.cfg["chunk_lines"])
    else:
        meta, sections = markdown_sections(path, text, store.cfg["chunk_lines"], store.cfg["chunk_mode"])
    doc = ident("doc", path)
    title = meta.get("title") or next((x["heading"] for x in sections if x["hierarchy"]), Path(path).stem)
    line_count = len(text.splitlines())
    store.node(doc, "DOCUMENT", str(title), path, 1 if line_count else None, line_count or None, "", hash_, meta)
    module = Path(path).parent.as_posix()
    modid = ident("module", module, path)  # source-backed grouping per document
    store.node(modid, "MODULE", module, path, 1 if line_count else None, 1 if line_count else None, "", hash_, {"grouping": "directory", "business_identity": "unknown"}, "CANDIDATE")
    if line_count:
        store.edge(modid, doc, "CONTAINS", path, "", 1, 1, text.splitlines()[0], hash_)
    seen = set()
    for sec in sections:
        store.db.execute("INSERT INTO sections VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         (sec["id"], sec["section_id"], path, sec["heading"], json_text(sec["hierarchy"]),
                          sec["anchor"], sec["start"], sec["end"], sec["order"], sec["content"], fold(sec["content"])))
        if store.has_fts:
            store.db.execute("INSERT INTO search_fts VALUES (?,?,?)", (sec["id"], sec["heading"], sec["content"]))
        if store.has_tri:
            store.db.execute("INSERT INTO search_tri VALUES (?,?,?)", (sec["id"], fold(sec["heading"]), trigram_text(sec["content"])))
        if sec["section_id"] not in seen:
            last = max(s["end"] for s in sections if s["section_id"] == sec["section_id"])
            store.node(sec["section_id"], "SECTION", sec["heading"], path, sec["start"], last,
                       sec["heading"], hash_, {"hierarchy": sec["hierarchy"], "anchor": sec["anchor"]})
            store.edge(sec["parent"], sec["section_id"], "CONTAINS", path, sec["heading"], sec["start"], sec["start"], sec["content"].splitlines()[0], hash_)
            seen.add(sec["section_id"])
    # History documents (history_paths) stay searchable but create no reference edges.
    history = store.scope.is_history(path)
    text_file = Path(path).suffix.casefold() in TEXT_FORMATS
    meta = dict(meta)
    if history:
        meta["qkb_history"] = True
    skipped = 0
    import codelinks
    import idlinks
    id_patterns = idlinks.compile_patterns(store.cfg)
    # Code aliases = configuration + `alias` = `path` lines of this page (this page only).
    file_aliases = {k: v for k, v in store.cfg["code_aliases"].items() if not k.endswith("/")}
    dir_aliases = {k: v for k, v in store.cfg["code_aliases"].items() if k.endswith("/")}
    # An imported data pack's aliases apply to the pages of that pack's project only.
    import packs
    pack = packs.of_project(store.cfg, store.scope.project(path))
    for alias, target in (pack or {}).get("code_aliases", {}).items():
        (dir_aliases if alias.endswith("/") else file_aliases).setdefault(alias, target)
    for alias_line in text.splitlines():
        for alias, target in codelinks.alias_declarations(alias_line):
            (dir_aliases if alias.endswith("/") else file_aliases)[alias] = target
    # Ignore links inside code fences, but preserve them verbatim in stored spans.
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= fence[1] and not marker[2].strip(): fence = None
            continue
        if marker:
            fence = (marker[1][0], len(marker[1])); continue
        source = next((s["section_id"] for s in sections if s["start"] <= number <= s["end"]), doc)
        links = [(a or b, False) for a, b in re.findall(r"(?<!!)\[[^\]]*\]\((?:<([^>]+)>|([^\s)]+))(?:\s+[^)]*)?\)", line)]
        # Backtick path references are references, never inferred dependencies.
        # Code files in backticks (with optional :line / :line-line spans) are handled below by codelinks.
        links += [(x, True) for x in re.findall(r"`([^`\n]+)`", line) if re.search(r"\.md(?:#.*)?$", x, re.I)]
        if number == 1 and not sections:
            continue
        if history or text_file:
            continue   # history documents and JSON / YAML / TOML / TXT files create no reference edges
        if id_patterns:
            extract_ids(store, path, number, line, source, hash_, id_patterns)
        for link, code_reference in links:
            if re.match(r"^[a-zA-Z][\w+.-]*:", link) or link.startswith("//"):
                continue
            target, _, anchor = decode_link(link).partition("#")
            # Backtick text with spaces / patterns / placeholders is prose; an explicit Markdown link
            # may contain spaces (<a b.md>) and is only skipped for glob patterns.
            if target and (NOT_A_PATH.search(target) if code_reference else re.search(r"[*?{}]", target)):
                skipped += 1   # pattern, placeholder or prose, not a file reference
                continue
            if not target:
                store.ref(source, path, path, anchor, "REFERENCES", number, number, line, hash_, None)
                continue
            # 2.0.0 rule (relative path; bare code name from the root) is the default target. The
            # written text is kept so engine.resolve_refs can apply the ordered resolver on every update.
            target_path = os.path.normpath(str(Path(path).parent / target)).replace("\\", "/")
            if code_reference and not store.scope.category(target_path) and store.scope.category(target):
                target_path = target
            try:
                safe_path(store.root, target_path)
                in_scope = bool(store.scope.category(target_path))
            except QError:
                in_scope = False
            if not in_scope:
                existing = [c for c in candidate_paths(store, path, target) if (store.root / c).is_file()]
                if not existing:
                    continue   # outside every configured path: dropped as in 2.0.0
                target_path = existing[0]
            store.ref(source, path, target_path, anchor, "REFERENCES", number, number, line, hash_, target)
        # KB -> code references: never dropped at extraction (the resolver decides; no edge when unresolved).
        # The written line span is kept as anchor "L<start>[-<end>]" ("L" = no span). Alias lines create no reference.
        if not codelinks.alias_declarations(line):
            for code in codelinks.code_refs(line):
                written = codelinks.expand_aliases(code["written"], file_aliases, dir_aliases)[0]
                if code["start"] is None:
                    code_anchor = "L"
                elif code["end"] == code["start"]:
                    code_anchor = "L%d" % code["start"]
                else:
                    code_anchor = "L%d-%d" % (code["start"], code["end"])
                code_target = os.path.normpath(str(Path(path).parent / written)).replace("\\", "/")
                store.ref(source, path, code_target, code_anchor, "REFERENCES", number, number, line, hash_, written)
    if skipped:
        meta["qkb_skipped_refs"] = skipped
    # Optional explicit metadata, encoded as JSON values inside YAML frontmatter.
    entities = meta.get("qkb_entities", [])
    if isinstance(entities, list):
        for entity in entities:
            if isinstance(entity, dict) and isinstance(entity.get("type"), str) and entity["type"] in NODE_TYPES and isinstance(entity.get("name"), str):
                entity_id = ident("entity", path, entity["type"], entity["name"])
                row = next((i for i, l in enumerate(text.splitlines(), 1) if l.startswith("qkb_entities:")), 1)
                store.node(entity_id, entity["type"], entity["name"], path, row, row, "frontmatter", hash_, {"declaration": "explicit metadata"})
                store.edge(doc, entity_id, "DOCUMENTS", path, "frontmatter", row, row, text.splitlines()[row-1], hash_)
    supersedes = meta.get("supersedes")
    for target in ([supersedes] if isinstance(supersedes, str) else supersedes if isinstance(supersedes, list) else []):
        if not isinstance(target, str): continue
        target = os.path.normpath(str(Path(path).parent / target)).replace("\\", "/")
        if store.scope.category(target):
            number = next((i for i, l in enumerate(text.splitlines(), 1) if l.startswith("supersedes:")), 1)
            store.ref(doc, path, target, "", "SUPERSEDES", number, number, text.splitlines()[number-1], hash_)
    return meta


def extract_ids(store, path, number, line, section, hash_, compiled):
    """ID definitions (node + AFFECTS references) and mentions (MENTIONS references)."""
    import idlinks
    defined = idlinks.definition(line, compiled)
    if defined:
        value, kind = defined
        node_id = ident("id", kind, value, path)
        meta = {"kind": kind, "struck": idlinks.is_struck(line, value), **idlinks.fields(line, store.cfg["issue_fields"])}
        meta.pop("affects", None)
        store.node(node_id, "ISSUE" if kind == "issue" else "IDENTIFIER", value, path, number, number,
                   line.strip()[:200], hash_, meta)
        store.edge(section, node_id, "CONTAINS", path, value, number, number, line, hash_)
        for written in idlinks.affected_paths(line):
            target = os.path.normpath(str(Path(path).parent / written)).replace("\\", "/")
            store.ref(node_id, path, target, "", "AFFECTS", number, number, line, hash_, written)
    for value, kind, _ in idlinks.find_ids(line, compiled):
        if defined and value == defined[0]:
            continue
        store.ref(section, path, "", value, "MENTIONS", number, number, line, hash_, value)


def extract_code(store, path, text, hash_):
    """Code files through the parser interface: one parser per language, same result shape.
    Symbols become CODE_SYMBOL nodes (CONFIRMED for FULL coverage, CANDIDATE for PARTIAL); imports / includes become
    IMPORTS references resolved against the index later. No call is ever extracted."""
    import parsers
    file_id = ident("doc", path)
    lines = text.splitlines()
    store.node(file_id, "CODE_FILE", path, path, 1, len(lines), "", hash_)
    result = parsers.parse(path, text, {"source_paths": store.cfg["source_paths"],
                                        "include_paths": store.cfg["cpp_include_paths"]})
    status = "CONFIRMED" if result["coverage"] == "FULL" else "CANDIDATE"
    ids, occurrences = {None: file_id}, {}
    for sym in result["symbols"]:
        label = sym["name"]
        order = occurrences.get(label, 0)
        occurrences[label] = order + 1
        id_ = ident("symbol", path, label, order)
        meta = {"ast_type": sym["kind"]} if result["language"] == "python" else             {"kind": sym["kind"], "coverage": result["coverage"], "relation_basis": "static text"}
        store.node(id_, "CODE_SYMBOL", label, path, sym["start"], sym["end"], label, hash_, meta, status)
        parent = ids.get(sym["parent"], file_id)
        store.edge(parent, id_, "CONTAINS", path, label, sym["start"], sym["start"], lines[sym["start"] - 1] if lines else "", hash_)
        ids.setdefault(label, id_)
    for ref in result["references"]:
        candidates = ref["candidates"]
        kept = [c for c in candidates if store.scope.category(c)]
        if ref["kind"] == "include" and not kept and candidates:
            kept = candidates[:1]   # kept for the unresolved-include count; no edge is created for it
        for candidate in kept:
            store.ref(file_id, path, candidate, "", "IMPORTS", ref["start"], ref["end"], ref["evidence"], hash_,
                      ref.get("written"), candidates if ref.get("first_only") else None)
    if result["language"] == "python":
        meta = {"parser": "python-ast", **result["meta"]}
    elif result["coverage"] == "FILE_ONLY":
        meta = {"parser": "file-only", "symbol_coverage": "UNVERIFIED"}
    else:
        meta = {"parser": result["parser"], **result["meta"]}
    return {**meta, "language": result["language"], "coverage": result["coverage"]}
