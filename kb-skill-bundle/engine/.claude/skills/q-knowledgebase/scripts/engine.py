"""Transactional indexing, bounded retrieval, and directed graph operations."""
from __future__ import annotations

import collections
import json
import re
import sqlite3
import time
from pathlib import Path

from core import (CODE_EXT, QError, Store, candidate_paths, digest, extract_code, extract_markdown, fold, ident,
                  json_text, now, safe_path)
import context    # Phase B: loaded with the engine, not inside the first search
import reports
import retrieval

DEPENDENCIES = {"DEPENDS_ON", "CALLS", "IMPORTS", "USES", "REQUIRES", "IMPLEMENTS"}


RESOLVED_RULES = ("relative", "root", "ancestor", "source_root", "unique_name", "unique_code_name")


class Resolver:
    """Ordered path resolver. A candidate counts only when it is a file of the index.
    Steps 1-6 come from core.candidate_paths (relative, root, ancestors up to the knowledge root,
    source roots); step 7 = unique file name inside the same project (files without a project only
    among themselves). Several equal candidates in step 7 -> AMBIGUOUS (no edge); nothing is guessed."""

    def __init__(self, store):
        self.store = store
        self.files = {r["path"] for r in store.rows("SELECT path FROM files")}
        self.roots = [k.replace("\\", "/").strip("/") for k in store.cfg["knowledge_paths"]]
        self.exists = {}
        self.by_name = collections.defaultdict(list)
        for f in sorted(self.files):
            self.by_name[Path(f).name.casefold()].append(f)

    @staticmethod
    def _norm(base, written):
        import posixpath
        rel = posixpath.normpath(posixpath.join(base, written)) if base not in ("", ".") else posixpath.normpath(written)
        return None if rel.startswith("../") or rel in ("..", ".") or rel.startswith("/") else rel

    def ordered(self, path, written):
        """Steps 1-6 as (rule, path) pairs, pure string work (no file system access)."""
        import posixpath
        written = written.replace("\\", "/")
        parent = posixpath.dirname(path)
        steps = [("relative", self._norm(parent, written)), ("root", self._norm("", written))]
        root = next((r for r in self.roots if path.startswith(r + "/")), None)
        while root is not None and parent and parent != root:
            parent = posixpath.dirname(parent)
            steps.append(("ancestor", self._norm(parent, written)))
        steps += [("source_root", self._norm(src.replace("\\", "/").strip("/"), written)) for src in self.store.cfg["source_paths"]]
        return [(rule, rel) for rule, rel in steps if rel]

    def resolve(self, path, written):
        """-> (target_path or None, resolution, candidates)."""
        for rule, candidate in self.ordered(path, written):
            if candidate in self.files:
                return candidate, rule, []
        # Step 7: unique file name (same project). Partial paths must match the end of the file path.
        name = Path(written).name.casefold()
        tail = written.replace("\\", "/").strip("/").casefold()
        project = self.store.scope.project(path)
        # Never across projects; a file without a project matches only files without one.
        matching = [f for f in self.by_name.get(name, []) if f.casefold() == tail or f.casefold().endswith("/" + tail)]
        same = [f for f in matching if self.store.scope.project(f) == project]
        if not same and Path(written).suffix.casefold() in CODE_EXT:
            # Phase C1: a KB page cites code that lives under the source roots, usually outside every project root
            # (project None). A code name may then match such code files - but never code of ANOTHER project;
            # that needs an explicit code_aliases entry. Still unique or AMBIGUOUS, never guessed.
            same = [f for f in matching if self.store.scope.category(f) == "code" and self.store.scope.project(f) is None]
            if len(same) == 1:
                return same[0], "unique_code_name", []
        if len(same) == 1:
            return same[0], "unique_name", []
        if len(same) > 1:
            return None, "AMBIGUOUS", same[:10]
        # An existing file outside the index (raw source, workspace file, excluded path) is not a
        # broken link: report it, but create no graph edge.
        for variant in self.outside_variants(path, written):
            if variant not in self.exists:
                # Existence only (no read); traversal / drive / absolute forms were rejected above.
                self.exists[variant] = (self.store.root / variant).is_file()
            if self.exists[variant]:
                return None, "OUTSIDE_INDEX", [variant]
        return None, "NOT_FOUND", []

    def outside_variants(self, path, written):
        import posixpath
        written = written.replace("\\", "/")
        if ":" in written or written.startswith("/"):
            return []
        bases, parent = [posixpath.dirname(path), ""], posixpath.dirname(path)
        while parent:
            parent = posixpath.dirname(parent)
            bases.append(parent)
        bases += [src.replace("\\", "/").strip("/") for src in self.store.cfg["source_paths"]]
        out = []
        for base in bases:
            rel = self._norm(base, written)
            if rel and rel not in out:
                out.append(rel)
        return out


def packs_summary(store):
    """Imported data packs (project, version, changelog, state); [] when none."""
    import packs
    return packs.summary(store.cfg)


def source_missing(store, path):
    """True when the page belongs to an imported data pack whose expected source roots are not on this
    machine (none of them exists, or the pack names none). Cached per project for one update."""
    import packs
    project = store.scope.project(path)
    cache = store.__dict__.setdefault("_source_missing", {})
    if project not in cache:
        pack = packs.of_project(store.cfg, project)
        if pack is None:
            cache[project] = False
        else:
            roots = pack.get("source_roots_expected") or []
            cache[project] = not any((store.root / r).is_dir() for r in roots if r and ".." not in r.split("/"))
    return cache[project]


CODE_ANCHOR = re.compile(r"^L(?:(\d+)(?:-(\d+))?)?$")   # KB -> code reference: "L", "L12", "L12-30"


def resolve_refs(store):
    refs = store.rows("SELECT * FROM refs ORDER BY id")
    store.db.execute("DELETE FROM code_spans")
    resolver = Resolver(store)
    # Import module.py and module/__init__.py are resolution alternatives.
    groups = collections.defaultdict(list)
    for ref in refs:
        key = (ref["source"], ref["start"], ref["evidence"]) if ref["relation"] == "IMPORTS" else (ref["id"],)
        groups[key].append(ref)
    definitions = collections.defaultdict(list)
    for node in store.rows("SELECT id,label,hash FROM nodes WHERE type IN ('ISSUE','IDENTIFIER')"):
        definitions[node["label"]].append(node)
    for alternatives in groups.values():
        first = alternatives[0]
        if first["relation"] == "MENTIONS":
            # Phase E: an ID mention links to every definition of that ID; undefined IDs get no edge.
            targets = definitions.get(first["written"], [])
            store.db.execute("UPDATE refs SET resolution=? WHERE id=?", ("DEFINED" if targets else "UNDEFINED", first["id"]))
            for node in targets:
                store.edge(first["source"], node["id"], "MENTIONS", first["path"], "mention", first["start"], first["end"],
                           first["evidence"], first["hash"], "CURRENT", node["hash"])
            continue
        code_ref = CODE_ANCHOR.match(first["anchor"] or "") if first["relation"] == "REFERENCES" else None
        if first["relation"] in ("REFERENCES", "AFFECTS") and first.get("written"):
            target, resolution, candidates = resolver.resolve(first["path"], first["written"])
            store.db.execute("UPDATE refs SET resolution=?, candidates=? WHERE id=?",
                             (resolution, json_text(candidates) if candidates else None, first["id"]))
            if not target and code_ref and resolution == "NOT_FOUND" and source_missing(store, first["path"]):
                # A page of an imported pack cites code that is not on this machine - not a broken link.
                resolution = "SOURCE_NOT_ON_MACHINE"
                store.db.execute("UPDATE refs SET resolution=? WHERE id=?", (resolution, first["id"]))
            if target:
                first = {**first, "target_path": target}
            elif resolution in ("OUTSIDE_INDEX", "AMBIGUOUS", "SOURCE_NOT_ON_MACHINE") or (resolution == "NOT_FOUND" and (code_ref or first["relation"] == "AFFECTS")):
                # No edge for an ambiguous name either (nothing is guessed, no BROKEN
                # placeholder); verify --links lists it with its candidates.
                continue
            alternatives = [first]
        valid = [r for r in alternatives if r["target_path"] in resolver.files]
        if alternatives[0]["relation"] == "IMPORTS" and alternatives[0]["candidates"] and valid:
            # #include "...": C search order (including folder, include paths, source roots); first indexed file only.
            order = json.loads(alternatives[0]["candidates"])
            valid = sorted(valid, key=lambda r: order.index(r["target_path"]) if r["target_path"] in order else len(order))[:1]
        if alternatives[0]["relation"] == "IMPORTS" and not valid:
            # Could be a standard-library/external/dynamic module. Keep the
            # unresolved reference for future reconciliation without inventing
            # a local target or labeling an external dependency as a broken file.
            continue
        for ref in valid if valid else alternatives[:1]:
            target = store.db.execute("SELECT * FROM nodes WHERE id=?", (ident("doc", ref["target_path"]),)).fetchone()
            target_id, target_hash = ident("doc", ref["target_path"]), None
            state = "CURRENT" if target else "BROKEN"
            if target:
                target_hash = target["hash"]
                if code_ref:
                    if code_ref.group(1):   # line span written in the KB: kept with the code file's hash of now
                        start = int(code_ref.group(1))
                        store.db.execute("INSERT INTO code_spans VALUES (?,?,?,?,?,?)",
                                         (ref["id"], ref["path"], ref["target_path"], start,
                                          int(code_ref.group(2) or start), target_hash))
                elif ref["anchor"]:
                    matches = [n for n in store.rows("SELECT * FROM nodes WHERE path=? AND type='SECTION'", (ref["target_path"],))
                               if json.loads(n["metadata"]).get("anchor") == ref["anchor"]]
                    if matches:
                        target_id = matches[0]["id"]
                    else:
                        state = "BROKEN"
                        if ref["relation"] in ("REFERENCES", "AFFECTS"):
                            store.db.execute("UPDATE refs SET resolution=? WHERE id=?", ("ANCHOR_NOT_FOUND", ref["id"]))
            else:
                store.node(target_id, "DOCUMENT" if ref["target_path"].endswith(".md") else "CODE_FILE",
                           ref["target_path"], ref["target_path"], None, None, "", "", {"unresolved": True}, "CANDIDATE")
            store.edge(ref["source"], target_id, ref["relation"], ref["path"], "reference",
                       ref["start"], ref["end"], ref["evidence"], ref["hash"], state, target_hash)


def update(store, force=False):
    started = time.perf_counter()
    scan = store.scope.scan()
    old = {r["path"]: r for r in store.rows("SELECT * FROM files")}
    current = {}
    # Hash every scoped file; timestamps alone cannot establish freshness.
    for path in scan:
        current[path] = store.scope.read(path)
    config_hash = digest(json_text(store.cfg))
    scope_changed = config_hash != store.getmeta("config_hash")
    changed = [p for p in scan if force or scope_changed or p not in old or old[p]["hash"] != current[p][1]]
    deleted = sorted(set(old) - set(scan))
    renamed = [{"from": p, "to": q} for p in deleted for q in changed
               if q not in old and old[p]["hash"] == current[q][1]]
    with store.db:
        store.ensure_indexes()
        store.ensure_trigram()
        # Archive the lightweight resolved-link layer before rewiring it. Parsing
        # and FTS writes remain limited to changed files.
        old_links = store.rows("SELECT * FROM edges WHERE relation IN ('REFERENCES','SUPERSEDES','IMPORTS','AFFECTS','MENTIONS')")
        store.db.execute("DELETE FROM edges WHERE relation IN ('REFERENCES','SUPERSEDES','IMPORTS','AFFECTS','MENTIONS')")
        for path in deleted + changed:
            if path in old:
                store.remove_file(path, "deleted" if path in deleted else "modified")
        for path in changed:
            text, hash_, size = current[path]
            meta = extract_markdown(store, path, text, hash_) if scan[path] == "markdown" else extract_code(store, path, text, hash_)
            meta = {**meta, "qkb_mtime": safe_path(store.root, path).stat().st_mtime_ns}   # status --quick
            store.db.execute("INSERT INTO files VALUES (?,?,?,?,?,?)", (path, hash_, size, scan[path], json_text(meta), now()))
        # Unchanged content with a new modification time: refresh the stored time so status --quick stays cheap.
        for path in scan:
            if path in old and path not in changed:
                stored = json.loads(old[path]["metadata"])
                mtime = safe_path(store.root, path).stat().st_mtime_ns
                if stored.get("qkb_mtime") != mtime:
                    store.db.execute("UPDATE files SET metadata=? WHERE path=?", (json_text({**stored, "qkb_mtime": mtime}), path))
        # Unresolved placeholders are refreshed against the current permitted corpus.
        store.db.execute("DELETE FROM nodes WHERE hash='' AND status='CANDIDATE'")
        resolve_refs(store)
        link_by_id = {r["id"]: r for r in store.rows("SELECT * FROM edges WHERE relation IN ('REFERENCES','SUPERSEDES','IMPORTS','AFFECTS','MENTIONS')")}
        for row in old_links:
            after = link_by_id.get(row["id"])
            keys = ("source", "target", "state", "hash", "target_hash", "evidence")
            if after is None or any(row[k] != after[k] for k in keys):
                store.db.execute("INSERT INTO history(at,reason,path,snapshot) VALUES (?,?,?,?)",
                                 (now(), "reference invalidated", row["path"], json_text(row)))
        # No approval silently survives changed evidence or endpoints.
        import semantic
        stale = semantic.refresh(store)
        elapsed = time.perf_counter() - started
        import retrieval
        retrieval.refresh_glossary(store)   # parsed glossary kept in the index (search speed)
        store.setmeta("config_hash", config_hash)
        store.setmeta("last_indexed", now())
        store.setmeta("last_update_seconds", elapsed)
        if force or not store.getmeta("last_build_seconds"):
            store.setmeta("last_build_seconds", elapsed)
        store.setmeta("last_scan_files", len(scan))
        store.setmeta("qkb_folder_mtimes", json_text(folder_mtimes(store, scan)))   # status --quick
    store.hash_cache.clear()
    return {"added": sum(p not in old for p in changed), "modified": sum(p in old for p in changed),
            "deleted": len(deleted), "unchanged": len(scan)-len(changed), "renamed": renamed,
            "semantic_stale": stale, "seconds": round(elapsed, 6), "fts5": store.fts,
            "note": "Changed files parsed; explicit references reconciled across the graph"}


def folder_mtimes(store, paths):
    """Modification times of the folders that hold indexed files (and their parents up to the scope roots)."""
    roots = {r.replace("\\", "/").strip("/") for r in store.cfg["knowledge_paths"] + store.cfg["source_paths"]}
    folders = set()
    for p in paths:
        parent = Path(p).parent.as_posix()
        while parent not in ("", ".") and parent not in folders:
            folders.add(parent)
            if parent in roots:
                break
            parent = Path(parent).parent.as_posix()
    out = {}
    for folder in sorted(folders | {r for r in roots if r}):
        try:
            out[folder] = (store.root / folder).stat().st_mtime_ns
        except OSError:
            out[folder] = None
    return out


def quick_status(store):
    """status --quick: no folder walk and no hashing of unchanged files. Each indexed file
    is stat-ed (size + modification time) and hashed only when one of them changed; added or removed files show
    up as a changed folder modification time (recorded at the last update). Meant for hooks (target <= 1 s);
    "status" stays the full check."""
    old = store.rows("SELECT path,hash,bytes,metadata FROM files")
    changed, deleted, hashed = [], [], 0
    for row in old:
        try:
            stat = (store.root / row["path"]).stat()
        except OSError:
            deleted.append(row["path"])
            continue
        if stat.st_size == row["bytes"] and json.loads(row["metadata"]).get("qkb_mtime") == stat.st_mtime_ns:
            continue
        hashed += 1
        if store.source_status(row["path"], row["hash"]) != "CURRENT":
            changed.append(row["path"])
    recorded = json.loads(store.getmeta("qkb_folder_mtimes") or "null")
    if recorded is None:
        folders_changed = ["(no folder record yet: run update once)"]
    else:
        folders_changed = []
        for folder, mtime in recorded.items():
            try:
                now_mtime = (store.root / folder).stat().st_mtime_ns
            except OSError:
                now_mtime = None
            if now_mtime != mtime:
                folders_changed.append(folder)
    config_changed = digest(json_text(store.cfg)) != store.getmeta("config_hash")
    result = {"state": "STALE" if changed or deleted or folders_changed or config_changed else "CURRENT",
              "changed": sorted(changed), "deleted": sorted(deleted), "config_changed": config_changed,
              "folders_changed": sorted(folders_changed)[:30],
              "fts5": store.fts, "last_indexed": store.getmeta("last_indexed"), "database": ".qkb/cache/index.sqlite3",
              "quick": True, "hashed": hashed,
              "note": "Quick check: changed folders may hold added or removed files; run status or update to see them"}
    for table in ("files", "sections", "nodes", "edges", "proposals", "history"):
        result[table] = store.db.execute("SELECT count(*) FROM " + table).fetchone()[0]
    result["unresolved_import_sites"] = None   # full status only
    if not store.fts:
        result["warning"] = "FTS5 unavailable or disabled: normalized local search may be slower"
    result["parsers"] = reports.parser_coverage(store)
    result["packs"] = packs_summary(store)
    import vectors
    result["embedding"] = vectors.status(store)   # no model load
    return result


def status(store, quick=False):
    """Full check hashes every scoped file. quick=True: see quick_status (no scan)."""
    if quick:
        return quick_status(store)
    scan = store.scope.scan()
    old = {r["path"]: r for r in store.rows("SELECT path,hash,bytes,metadata FROM files")}
    hashed = 0
    changed = []
    for p in scan:
        if p not in old:
            changed.append(p)
            continue
        if quick:
            stat = safe_path(store.root, p).stat()
            if stat.st_size == old[p]["bytes"] and json.loads(old[p]["metadata"]).get("qkb_mtime") == stat.st_mtime_ns:
                continue
        hashed += 1
        if store.source_status(p, old[p]["hash"]) != "CURRENT":
            changed.append(p)
    deleted = sorted(set(old)-set(scan))
    config_changed = digest(json_text(store.cfg)) != store.getmeta("config_hash")
    result = {"state": "STALE" if changed or deleted or config_changed else "CURRENT",
              "changed": changed, "deleted": deleted, "config_changed": config_changed,
              "fts5": store.fts, "last_indexed": store.getmeta("last_indexed"),
              "database": ".qkb/cache/index.sqlite3"}
    for table in ("files", "sections", "nodes", "edges", "proposals", "history"):
        result[table] = store.db.execute("SELECT count(*) FROM " + table).fetchone()[0]
    result["unresolved_import_sites"] = store.db.execute("""SELECT count(*) FROM
        (SELECT source,start,evidence FROM refs WHERE relation='IMPORTS'
         GROUP BY source,start,evidence HAVING max(target_path IN (SELECT path FROM files))=0)""").fetchone()[0]
    if not store.fts:
        result["warning"] = "FTS5 unavailable or disabled: normalized local search may be slower"
    # Parser coverage per language (file metadata only; cheap).
    result["parsers"] = reports.parser_coverage(store)
    result["packs"] = packs_summary(store)
    import vectors
    result["embedding"] = vectors.status(store)   # no model load
    if quick:
        result.update({"quick": True, "hashed": hashed})
    return result


def metadata_for(store, path):
    row = store.db.execute("SELECT metadata FROM files WHERE path=?", (path,)).fetchone()
    return json.loads(row[0]) if row else {}


def section_result(store, sec, score, snippet=True):
    file = store.db.execute("SELECT * FROM files WHERE path=?", (sec["path"],)).fetchone()
    state = store.source_status(sec["path"], file["hash"]) if file else "BROKEN"
    meta = json.loads(file["metadata"]) if file else {}
    return {"id": sec["id"], "section_id": sec["section_id"], "title": meta.get("title", Path(sec["path"]).stem),
            "module": meta.get("module", Path(sec["path"]).parent.as_posix()), "domain": meta.get("domain", "unknown"),
            "path": sec["path"], "heading": sec["heading"], "hierarchy": json.loads(sec["hierarchy"]),
            "start": sec["start"] if state == "CURRENT" else None, "end": sec["end"] if state == "CURRENT" else None,
            "score": round(score, 3), "source_status": state, "hash": file["hash"] if file else None,
            "document_status": meta.get("status", "unknown"), "authority": meta.get("authority", "unknown"),
            "snippet": sec["content"][:300] if state == "CURRENT" and snippet else None,
            "relation": None, "project": store.scope.project(sec["path"]), "history": bool(meta.get("qkb_history"))}


def history_files(store):
    """Paths flagged by history_paths; empty (no query) when the key is not configured."""
    if not store.cfg["history_paths"]:
        return set()
    return {r["path"] for r in store.rows("SELECT path,metadata FROM files") if json.loads(r["metadata"]).get("qkb_history")}


def search_classic(store, query, top=5, project=None):
    """2.1.0-b0 ranking, kept behind "ranking": "classic"."""
    tokens = re.findall(r"[\w./-]+", fold(query))
    if not tokens:
        return {"results": [], "note": "No searchable terms"}
    # FTS provides bounded candidate generation. CJK/identifier/path substring
    # matching supplements it because unicode61 does not segment Japanese words.
    candidates, fts_scores = {}, {}
    if store.fts:
        fts_tokens = re.findall(r"\w+", query)
        if fts_tokens:
            expression = " OR ".join('"' + t.replace('"', '""') + '"' for t in fts_tokens)
            try:
                rows = store.rows("SELECT id,bm25(search_fts,0,4,1) AS rank FROM search_fts WHERE search_fts MATCH ? ORDER BY rank LIMIT 400", (expression,))
                for row in rows:
                    sec = store.db.execute("SELECT * FROM sections WHERE id=?", (row["id"],)).fetchone()
                    if sec:
                        candidates[sec["id"]] = dict(sec)
                        fts_scores[sec["id"]] = min(8.0, -row["rank"])
            except sqlite3.OperationalError:
                pass
    # Local fallback works with Vietnamese accents, literal paths and CJK.
    # Bound SQL candidate generation to 400 per term; do not copy the corpus
    # into the Python process just to score it.
    for token in tokens[:16]:
        escaped = token.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        for sec in store.rows("SELECT * FROM sections WHERE normalized LIKE ? ESCAPE '\\' OR lower(path) LIKE ? ESCAPE '\\' OR lower(heading) LIKE ? ESCAPE '\\' LIMIT 400", ("%"+escaped+"%", "%"+escaped+"%", "%"+escaped+"%")):
            candidates[sec["id"]] = sec
    ranked = []
    q = fold(query)
    if project is not None:
        candidates = {k: v for k, v in candidates.items() if store.scope.in_project(v["path"], project)}
    history = history_files(store)
    for sec in candidates.values():
        heading, path, content = fold(sec["heading"]), fold(sec["path"]), sec["normalized"]
        heading_context = fold(" ".join(json.loads(sec["hierarchy"])))
        matched = sum(t in content or t in path or t in heading_context for t in tokens)
        if not matched:
            continue
        score = (100 if q == path else 50 if q in path else 0)
        score += (80 if q == heading else 30 if q in heading else 0)
        score += matched * 4 + sum(6 for t in tokens if t in heading) + (12 if matched == len(tokens) else 0)
        score += fts_scores.get(sec["id"], 0)
        ranked.append((score, sec, matched))
    # Broad OR hits waste context when a precise heading/path or all-term hit
    # exists. Keep partial matches only as an explicit fallback for coverage gaps.
    exact = [r for r in ranked if q in (fold(r[1]["path"]), fold(r[1]["heading"]))]
    complete = [r for r in ranked if r[2] == len(tokens)]
    mode = "exact_heading_or_path" if exact else "all_terms" if complete else "partial_terms"
    ranked = exact or complete or ranked
    # History documents (history_paths) rank after every other section.
    ranked.sort(key=lambda x: (x[1]["path"] in history, -x[0], x[1]["path"], x[1]["start"]))
    results = [section_result(store, sec, score) for score, sec, matched in ranked[:top]]
    # Symbol retrieval uses confirmed Python AST nodes (no regex call graph).
    symbols = store.rows("SELECT * FROM nodes WHERE type IN ('CODE_SYMBOL','CODE_FILE') AND (label=? COLLATE NOCASE OR label LIKE ?) ORDER BY label,id LIMIT ?", (query, "%"+query+"%", top))
    if project is not None:
        symbols = [x for x in symbols if store.scope.in_project(x["path"], project)]
    for symbol in symbols:
        node = present_node(store, symbol)
        node.update({"score": 120 if fold(symbol["label"]) == q else 45, "title": symbol["label"],
                     "module": Path(symbol["path"]).parent.as_posix(), "domain": "unknown", "relation": None,
                     "snippet": "Source file/symbol; use read with this ID for exact current source"})
        results.append(node)
    results.sort(key=lambda x: (bool(x.get("history")), -x["score"]))
    out = {"results": results[:top], "candidates": len(candidates), "fts5": store.fts, "match_mode": mode,
            "ranking": "exact path/symbol > heading > all terms > partial FTS/keyword fallback; inspect graph with related",
            "warning": None if store.fts else "FTS5 disabled/unavailable; local fallback may be slower"}
    if project is not None:
        out["project"] = project
    return out

def search(store, query, top=5, project=None, semantic=None):
    """Section + symbol search. Default ranking "rrf"; "classic" = 2.1.0-b0 scoring."""
    if store.cfg["ranking"] == "classic":
        out = search_classic(store, query, top, project)
        out["ranking_mode"] = "classic"
        return out
    import retrieval
    analysis = retrieval.analyse(store, query)
    groups = analysis["groups"]
    if not groups:
        return {"results": [], "note": "No searchable terms"}
    history = history_files(store)
    ranked, count, mode = retrieval.rank(store, query, groups, top, project, history, analysis.get("phrases", ()))
    # Item 6: chunks of one section are merged into one result, so the top slots hold different sections.
    import context
    sections = context.compact([section_result(store, sec, score) for score, sec, matched in ranked[:top * 4]])[:top]
    q = fold(query)
    symbols = store.rows("SELECT * FROM nodes WHERE type IN ('CODE_SYMBOL','CODE_FILE') AND (label=? COLLATE NOCASE OR label LIKE ?) ORDER BY label,id LIMIT ?", (query, "%"+query+"%", top))
    # Phase E: an ID query returns its definition node(s) first.
    symbols = store.rows("SELECT * FROM nodes WHERE type IN ('ISSUE','IDENTIFIER') AND label=? ORDER BY path,id LIMIT ?", (query.strip(), top)) + symbols
    if project is not None:
        symbols = [x for x in symbols if store.scope.in_project(x["path"], project)]
    exact_symbols, partial_symbols = [], []
    for symbol in symbols:
        node = present_node(store, symbol)
        exact = fold(symbol["label"]) == fold(query.strip()) or fold(symbol["label"]) == q
        node.update({"score": 120 if exact else 45, "title": symbol["label"],
                     "module": Path(symbol["path"]).parent.as_posix(), "domain": "unknown", "relation": None,
                     "snippet": "Source file/symbol; use read with this ID for exact current source"})
        # Candidate symbols (PARTIAL parsers, e.g. C++ declarations) never push KB sections down.
        (exact_symbols if exact and symbol["status"] != "CANDIDATE" else partial_symbols).append(node)
    results = exact_symbols + sections + partial_symbols
    results.sort(key=lambda x: bool(x.get("history")))
    out = {"results": results[:top], "candidates": count, "fts5": store.fts, "match_mode": mode,
           "ranking": "concept groups matched > rank fusion of word FTS, trigram FTS and exact heading/path evidence; history last",
           "ranking_mode": "rrf", "trigram": store.trigram,
           "query_terms": [g["text"] for g in groups], "expanded": analysis["expanded"],
           "phrases": [p["folded"] for p in analysis.get("phrases", [])],
           # concepts covered by the best section (the router uses it to decide on model search)
           "coverage": {"best": max((m for _, _, m in ranked), default=0), "concepts": len(groups)},
           "warning": None if store.fts else "FTS5 disabled/unavailable; local fallback may be slower"}
    if project is not None:
        out["project"] = project
    # Optional local model search, only when the router gate allows it; never fails the search.
    import vectors
    return vectors.apply(store, query, out, top, project, semantic, lambda sec: section_result(store, sec, 0))


def read_section(store, id_):
    rows = store.rows("SELECT * FROM sections WHERE id=? OR section_id=? ORDER BY ordering", (id_, id_))
    if rows:
        sections = []
        for sec in rows:
            result = section_result(store, sec, 0, False)
            if result["source_status"] != "CURRENT":
                raise QError("Source is " + result["source_status"] + "; update before retrieving line spans")
            text, hash_, _ = store.scope.read(sec["path"])
            if hash_ != result["hash"]:
                raise QError("Source changed during retrieval; update and retry")
            result["content"] = "".join(text.splitlines(keepends=True)[sec["start"]-1:sec["end"]])
            sections.append(result)
        return {"sections": sections}
    nodes = store.rows("SELECT * FROM nodes WHERE id=?", (id_,))
    if not nodes:
        raise QError("Unknown section/chunk/node ID; search first")
    node = nodes[0]
    text, hash_, _ = store.scope.read(node["path"])
    if hash_ != node["hash"]:
        raise QError("Source is STALE; update before retrieving line spans")
    content = "".join(text.splitlines(keepends=True)[node["start"]-1:node["end"]]) if node["start"] else ""
    return {"sections": [{**present_node(store, node), "content": content}]}


def present_node(store, node):
    state = store.source_status(node["path"], node["hash"]) if node["hash"] else "BROKEN"
    return {"id": node["id"], "type": node["type"], "label": node["label"], "path": node["path"],
            "heading": node["heading"], "start": node["start"] if state == "CURRENT" else None,
            "end": node["end"] if state == "CURRENT" else None, "source_status": state,
            "status": node["status"], "hash": node["hash"], "metadata": json.loads(node["metadata"]),
            "project": store.scope.project(node["path"])}


def resolve_node(store, value):
    rows = store.rows("SELECT * FROM nodes WHERE id=?", (value,))
    if not rows:
        rows = store.rows("SELECT * FROM nodes WHERE label=? COLLATE NOCASE OR path=?", (value, value))
        file_rows = [r for r in rows if r["type"] in ("DOCUMENT", "CODE_FILE") and r["path"] == value]
        if file_rows:
            rows = file_rows
    if not rows:
        # A unique file name or path tail ("main.cpp", "app/main.cpp") names its file, as in query.
        tail = value.replace("\\", "/").strip("/").casefold()
        if tail:
            rows = [r for r in store.rows("SELECT * FROM nodes WHERE type IN ('DOCUMENT','CODE_FILE') AND hash != ''")
                    if r["path"].casefold() == tail or r["path"].casefold().endswith("/" + tail)]
            if len(rows) > 1:
                raise QError("Ambiguous file name; candidates: " + ", ".join(sorted(r["path"] for r in rows)[:10]))
    if len(rows) == 1:
        return rows[0]
    if not rows:
        raise QError("Node not found. Search or map first, then use a node ID")
    raise QError("Ambiguous node label; choose an ID from map/search or scope by exact file path")


def edge_state(store, edge):
    state = store.source_status(edge["path"], edge["hash"])
    if state != "CURRENT": return state
    for endpoint in (edge["source"], edge["target"]):
        row = store.db.execute("SELECT * FROM nodes WHERE id=?", (endpoint,)).fetchone()
        if not row or not row["hash"]: return "BROKEN"
        result = store.source_status(row["path"], row["hash"])
        if result != "CURRENT": return result
    return edge["state"]


def graph_edges(store, include_candidates=False):
    edges = []
    for edge in store.rows("SELECT * FROM edges ORDER BY id"):
        state = edge_state(store, edge)
        edges.append({**edge, "state": state, "start": edge["start"] if state == "CURRENT" else None,
                      "end": edge["end"] if state == "CURRENT" else None,
                      "evidence": edge["evidence"][:350] if state == "CURRENT" else None})
    import semantic
    for proposal in store.rows("SELECT * FROM proposals ORDER BY id"):
        if proposal["decision"] != "APPROVED" and not include_candidates:
            continue
        data = json.loads(proposal["payload"])
        validation = semantic.validate(store, data)
        state = "CURRENT" if validation["state"] == "VALID" and proposal["validation"] == "VALID" else "STALE"
        if proposal["decision"] != "APPROVED": state = "UNVERIFIED"
        edges.append({"id": proposal["id"], "source": data["source"], "target": data["target"],
                      "relation": data["relation"], "origin": "INFERRED", "state": state,
                      "decision": proposal["decision"], "rationale": data["rationale"],
                      "path": data["evidence"][0]["path"], "start": data["evidence"][0]["start"] if state == "CURRENT" else None,
                      "end": data["evidence"][0]["end"] if state == "CURRENT" else None,
                      "evidence": data["evidence"] if state == "CURRENT" else None})
    return edges


def traverse(store, start, depth=2, direction="both", impact=False, top=30, project=None):
    root = resolve_node(store, start)
    edges = graph_edges(store)
    adjacency = collections.defaultdict(list)
    in_project = None
    if project is not None:
        in_project = {r["id"] for r in store.rows("SELECT id,path FROM nodes") if store.scope.in_project(r["path"], project)}
        in_project.add(root["id"])
    code_nodes = {r["id"] for r in store.rows("SELECT id FROM nodes WHERE type IN ('CODE_FILE','CODE_SYMBOL')")} if impact else set()
    for edge in edges:
        if edge["state"] != "CURRENT":
            continue
        # impact: dependencies, plus (Phase C1 / E) issues that AFFECT the node and KB sections that cite code.
        if impact and not (edge["relation"] in DEPENDENCIES or edge["relation"] == "AFFECTS"
                           or (edge["relation"] == "REFERENCES" and edge["target"] in code_nodes)):
            continue
        if in_project is not None and (edge["source"] not in in_project or edge["target"] not in in_project):
            continue
        if direction in ("out", "both"): adjacency[edge["source"]].append((edge["target"], edge))
        if direction in ("in", "both"): adjacency[edge["target"]].append((edge["source"], edge))
    queue, seen, selected = collections.deque([(root["id"], 0)]), {root["id"]}, {}
    while queue and len(seen) <= top:
        node, distance = queue.popleft()
        if distance >= depth: continue
        for other, edge in adjacency[node]:
            if other not in seen and len(seen) < top:
                seen.add(other); queue.append((other, distance+1))
            if other in seen: selected[edge["id"]] = edge
    nodes = [present_node(store, n) for id_ in sorted(seen) for n in store.rows("SELECT * FROM nodes WHERE id=?", (id_,))]
    result_project = {} if project is None else {"project": project}
    return {**result_project, "nodes": nodes, "edges": list(selected.values())[:top*3], "direction": direction, "depth": depth,
            "note": "Incoming dependencies, issues that affect it and KB sections citing code; conservative known impact, not a complete runtime blast radius" if impact else "Direction shown on each edge; co-reference does not establish dependency"}


def find_path(store, source, target, depth=2, direction="out"):
    src, dst = resolve_node(store, source), resolve_node(store, target)
    adjacency = collections.defaultdict(list)
    for edge in graph_edges(store):
        if edge["state"] != "CURRENT": continue
        if direction in ("out", "both"): adjacency[edge["source"]].append((edge["target"], edge, False))
        if direction in ("in", "both"): adjacency[edge["target"]].append((edge["source"], edge, True))
    queue, seen = collections.deque([(src["id"], [])]), {src["id"]}
    while queue:
        node, steps = queue.popleft()
        if node == dst["id"]:
            return {"found": True, "source": src["id"], "target": dst["id"], "steps": steps,
                    "confidence": "INFERRED" if any(s["origin"] == "INFERRED" for s in steps) else "EXTRACTED",
                    "direction": direction}
        if len(steps) >= depth: continue
        for other, edge, reverse in adjacency[node]:
            if other not in seen:
                seen.add(other); queue.append((other, steps + [{**edge, "traversed_reverse": reverse}]))
        if len(seen) > 10000:
            raise QError("Path exploration exceeded 10000 nodes; narrow the query")
    return {"found": False, "depth": depth, "direction": direction, "note": "No current approved path within depth; this does not prove absence of a relationship"}


def knowledge_map(store, top=30, project=None):
    if project is None:
        rows = store.rows("SELECT * FROM nodes WHERE type NOT IN ('SECTION','CODE_SYMBOL') ORDER BY path,type,label LIMIT ?", (top,))
        groups = store.rows("SELECT category,count(*) AS files FROM files GROUP BY category")
    else:
        rows = [n for n in store.rows("SELECT * FROM nodes WHERE type NOT IN ('SECTION','CODE_SYMBOL') ORDER BY path,type,label")
                if store.scope.in_project(n["path"], project)][:top]
        counts = collections.Counter(r["category"] for r in store.rows("SELECT path,category FROM files") if store.scope.in_project(r["path"], project))
        groups = [{"category": k, "files": v} for k, v in sorted(counts.items())]
    projects = collections.Counter(store.scope.project(r["path"]) for r in store.rows("SELECT path FROM files"))
    return {**({} if project is None else {"project": project}), "nodes": [present_node(store, n) for n in rows],
            "groups": groups, "projects": [{"project": k, "files": v} for k, v in sorted(projects.items(), key=lambda kv: (kv[0] is None, kv[0] or ""))],
            "note": "Directory-based subsystems are candidates, not discovered business domains"}


def explore(store, query, top=5, depth=2, project=None, semantic=None):
    result = search(store, query, top, project, semantic)
    nodes, edges = {}, {}
    for hit in result["results"][:3]:
        if hit["source_status"] != "CURRENT": continue
        node_id = hit.get("section_id", hit["id"])
        graph = traverse(store, node_id, depth, "both", top=top*3, project=project)
        nodes.update((n["id"], n) for n in graph["nodes"])
        edges.update((e["id"], e) for e in graph["edges"])
    return {**result, "nodes": list(nodes.values())[:top*3],
            "edges": list(edges.values())[:top*4],
            "note": "Bounded search + graph orientation. Read exact sections and current code before editing"}


def link_report(store, top=30):
    """verify --links: every extracted reference grouped by how it resolved, broken ones
    with file and line. resolution is set by resolve_refs on the last update."""
    rows = store.rows("SELECT path,start,written,target_path,anchor,resolution,candidates FROM refs WHERE relation='REFERENCES' ORDER BY path,start")
    # Phase C1: KB -> code references (anchor "L…") are reported apart ("code"), so document-link numbers stay comparable.
    rows = [r for r in rows if not CODE_ANCHOR.match(r["anchor"] or "")]
    by = collections.Counter(r["resolution"] or "same_file" for r in rows)
    broken = [r for r in rows if r["resolution"] in ("NOT_FOUND", "AMBIGUOUS", "ANCHOR_NOT_FOUND")]
    outside = [r for r in rows if r["resolution"] == "OUTSIDE_INDEX"]
    files = store.rows("SELECT path,metadata FROM files")
    meta = {f["path"]: json.loads(f["metadata"]) for f in files}
    groups = {}
    for cause in ("AMBIGUOUS", "NOT_FOUND", "ANCHOR_NOT_FOUND"):
        items = [{"path": r["path"], "line": r["start"], "written": r["written"],
                  **({"candidates": json.loads(r["candidates"])} if r["candidates"] else {}),
                  **({"anchor": r["anchor"]} if cause == "ANCHOR_NOT_FOUND" else {})}
                 for r in broken if r["resolution"] == cause]
        groups[cause] = {"count": len(items), "items": items[:top]}
    return {"references": len(rows), "resolved": sum(by[k] for k in RESOLVED_RULES) + by["same_file"],
            "by_resolution": dict(sorted(by.items())), "broken": len(broken), "broken_by_cause": groups,
            "outside_index": {"count": len(outside), "note": "existing files the index does not hold; no edge created",
                              "items": [{"path": r["path"], "line": r["start"], "written": r["written"]} for r in outside[:top]]},
            "skipped_not_a_path": sum(m.get("qkb_skipped_refs", 0) for m in meta.values()),
            "history_files_without_edges": sorted(p for p, m in meta.items() if m.get("qkb_history"))[:top],
            # Phase C1 / E: KB -> code references and line spans, #include graph, issue / ID links, parsers.
            "code": reports.code_link_report(store, top), "includes": reports.include_report(store, top),
            "packs": packs_summary(store),
            "issues": reports.issue_report(store, top), "parsers": reports.parser_coverage(store),
            "note": "AMBIGUOUS = several files of the same name in the project; write the path. NOT_FOUND = no indexed file matches. "
                    "code: KB references to code files (no edge when unresolved); line spans checked against the code file "
                    "hash of the last KB update (STALE) and its current length (LINE_OUT_OF_RANGE)."}


def verify(store, links=False, top=30):
    integrity = store.db.execute("PRAGMA integrity_check").fetchone()[0]
    result = status(store)
    edges = graph_edges(store)
    problems = [{"id": e["id"], "state": e["state"], "path": e["path"]} for e in edges if e["state"] != "CURRENT"]
    parse_errors = [{"path": f["path"], "state": "BROKEN", "reason": "Python syntax could not be parsed"}
                    for f in store.rows("SELECT path,metadata FROM files") if json.loads(f["metadata"]).get("parse_status") == "BROKEN"]
    result.update({"sqlite_integrity": integrity, "problems": problems + parse_errors,
                   "ok": integrity == "ok" and result["state"] == "CURRENT" and not problems and not parse_errors})
    if links:
        result["links"] = link_report(store, top)
    return result
