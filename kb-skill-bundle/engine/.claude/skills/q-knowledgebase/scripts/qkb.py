#!/usr/bin/env python3
"""Q-KnowledgeBase: offline, source-grounded repository knowledge tools."""
from __future__ import annotations

import argparse
import copy
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True

from core import DEFAULTS, VERSION, QError, Scope, Store, load_config, now, safe_path
import engine
import semantic
import usage


def positive(value):
    result = int(value)
    if result < 1: raise argparse.ArgumentTypeError("must be positive")
    return result


def parser():
    p = argparse.ArgumentParser(description="Q-KnowledgeBase " + VERSION + " — offline Markdown knowledge engine")
    p.add_argument("--root", default=".", help="Repository root; place this option before the command")
    p.add_argument("--version", action="version", version=VERSION)
    sub = p.add_subparsers(dest="command", required=True)
    parsers = {}
    for name, help_ in {
        "doctor": "Check Python, SQLite, FTS5 and configuration without modifying files",
        "init": "Preview scope or create missing configuration without overwrite",
        "build": "Index configured corpus; existing history and approvals preserved",
        "update": "Hash-based incremental update",
        "status": "Check live file hashes and current scope",
        "search": "Compact ranked section/symbol search",
        "explore": "Compact search plus bounded graph context in one response",
        "read": "Read exact current source spans by chunk/section/node ID",
        "map": "Compact project map and directory subsystem candidates",
        "related": "Explore current graph relationships",
        "path": "Find a directed current approved path",
        "impact": "Traverse incoming known dependency edges",
        "verify": "Validate SQLite, source freshness and graph integrity",
        "semantic": "Import, inspect and explicitly review inferred proposals",
        "export": "Bounded offline JSON/GraphML/Mermaid/HTML export",
        "benchmark": "Run labeled local retrieval benchmark against a text baseline",
        "backup": "Create a consistent SQLite backup inside .qkb/backups",
        "migrate": "Upgrade an older index schema: backup, keep proposals/reviews/history, rebuild, verify",
        "embed": "Optional model search: add / refresh vectors of changed sections (needs embedding.backend; dry run unless --apply)",
        "maintain": "Maintenance: prune-history (after backup; dry run unless --apply)",
        "query": "Route one question to search / explore / related / impact / path (deterministic; route and reason shown)",
    }.items():
        child = sub.add_parser(name, help=help_)
        child.add_argument("--format", choices=("json", "text"), default="text")
        child.add_argument("--max-chars", type=positive, default=None, help="Maximum rendered response characters, including metadata")
        child.add_argument("--max-tokens", type=positive, default=None, help="Conservative UTF-8 byte-based token estimate budget; not exact tokenization")
        parsers[name] = child
    parsers["init"].add_argument("--dry-run", action="store_true")
    parsers["build"].add_argument("--full", action="store_true", help="Reparse all scoped files; preserve review/history tables")
    parsers["search"].add_argument("query")
    for name in ("search", "explore", "query"):
        parsers[name].add_argument("--semantic", choices=("auto", "on", "off"), default=None,
                                   help="Model search: auto (only when the router needs it; default), on, off")
    parsers["embed"].add_argument("--apply", action="store_true", help="Write vectors; without it only report what would change")
    parsers["explore"].add_argument("query")
    parsers["read"].add_argument("id")
    parsers["query"].add_argument("question")
    parsers["read"].add_argument("--expand", type=int, nargs="?", const=1, default=None, metavar="N",
                                 help="Also return N neighbouring chunks before and after (default 1)")
    for name in ("map", "search", "explore", "related", "impact", "export", "query"):
        parsers[name].add_argument("--top", type=positive, default=None)
    for name in ("related", "path", "impact", "export", "explore", "query"):
        parsers[name].add_argument("--depth", type=positive, default=None)
    for name in ("related", "impact"):
        parsers[name].add_argument("node")
    for name in ("search", "explore", "map", "related", "impact", "query"):
        parsers[name].add_argument("--project", default=None, help="Only paths of this project (first segment below a project root)")
    parsers["verify"].add_argument("--links", action="store_true", help="Group extracted references by resolution; broken ones with file and line")
    parsers["verify"].add_argument("--top", type=positive, default=None)
    parsers["migrate"].add_argument("--dry-run", action="store_true")
    parsers["status"].add_argument("--quick", action="store_true", help="Hash only files whose size or modification time changed")
    parsers["maintain"].add_argument("action", choices=("prune-history",))
    parsers["maintain"].add_argument("--days", type=positive, default=90, help="Prune history rows older than this many days")
    parsers["maintain"].add_argument("--apply", action="store_true", help="Delete; without it the command only reports")
    parsers["related"].add_argument("--direction", choices=("in", "out", "both"), default="both")
    parsers["path"].add_argument("source")
    parsers["path"].add_argument("target")
    parsers["path"].add_argument("--direction", choices=("in", "out", "both"), default="out")
    parsers["export"].add_argument("--kind", choices=("json", "graphml", "mermaid", "html"), default="html")
    parsers["export"].add_argument("--node", default=None)
    parsers["benchmark"].add_argument("questions", help="Repository-relative JSON file containing labeled questions")
    parsers["semantic"].add_argument("action", choices=("import", "list", "show", "validate", "approve", "reject"))
    parsers["semantic"].add_argument("value", nargs="?")
    parsers["semantic"].add_argument("--reviewer", default="")
    parsers["semantic"].add_argument("--reason", default="")
    parsers["semantic"].add_argument("--human-approved", action="store_true")
    parsers["semantic"].add_argument("--ack-conflicts", action="store_true")
    return p


def render(data, format_):
    if format_ == "json":
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    # Structured text retains identifiers/provenance and is readable in terminals.
    return json.dumps(data, ensure_ascii=False, indent=2)


def emit(data, args, cfg):
    limit = args.max_chars or cfg["query_max_chars"]
    # One UTF-8 byte per estimated token is intentionally conservative; actual
    # tokenizer behavior differs. Apply the cap to the entire rendered payload.
    tokens = args.max_tokens
    if limit < 200 or (tokens is not None and tokens < 200):
        raise QError("Output budgets below 200 cannot hold a valid provenance envelope")
    result = copy.deepcopy(data)
    result["_output"] = {"truncated": False, "token_estimate": "conservative UTF-8 bytes, not exact tokens"}

    def fits(text):
        return len(text)+1 <= limit and (tokens is None or len((text+"\n").encode("utf-8")) <= tokens)

    def strings(obj):
        found = []
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in ("content", "snippet", "evidence", "rationale") and isinstance(value, str) and len(value) > 80:
                    found.append((obj, key, len(value)))
                elif key != "_output": found.extend(strings(value))
        elif isinstance(obj, list):
            for value in obj: found.extend(strings(value))
        return found

    while not fits(render(result, args.format)):
        result["_output"]["truncated"] = True
        candidates = sorted(strings(result), key=lambda x: -x[2])
        if candidates:
            obj, key, length = candidates[0]
            obj[key] = obj[key][:max(40, length//2)] + "… [output truncated]"
            continue
        lists = [(k, v) for k, v in result.items() if isinstance(v, list) and v]
        if lists:
            key, value = max(lists, key=lambda kv: len(render(kv[1], args.format)))
            value.pop()
            result["_output"]["omitted_items"] = result["_output"].get("omitted_items", 0)+1
            continue
        removable = [k for k in result if k not in ("_output", "error", "ok", "state")]
        if removable:
            result.pop(max(removable, key=lambda k: len(render(result[k], args.format))))
            continue
        # Error strings also must fit; never slice serialized JSON into invalid JSON.
        if isinstance(result.get("error"), str) and len(result["error"]) > 30:
            result["error"] = result["error"][:len(result["error"])//2] + "…"
            continue
        result = {"_output": {"truncated": True}, "error": "Increase output budget"}
        break
    print(render(result, args.format))


def initialize(root, cfg, dry_run):
    scope = Scope(root, cfg)
    scan = scope.scan()
    result = {"dry_run": dry_run, "knowledge_paths": cfg["knowledge_paths"], "source_paths": cfg["source_paths"],
              "files": list(scan), "count": len(scan), "bytes": sum(scope.read(p)[2] for p in scan),
              "note": "Review scope and edit .qkb/config.json before build; original docs/code are not changed"}
    if dry_run:
        return result
    file = safe_path(root, ".qkb/config.json")
    file.parent.mkdir(parents=True, exist_ok=True)
    if not file.exists():
        # never write merged data-pack settings: the file holds this machine's own settings only
        plain = {k: v for k, v in load_config(root, packs=False).items() if not k.startswith("_")}
        with file.open("x", encoding="utf-8") as handle:
            json.dump(plain, handle, ensure_ascii=False, indent=2); handle.write("\n")
        result["config"] = "created"
    else:
        result["config"] = "preserved"
    ignore = safe_path(root, ".qkb/.gitignore")
    if not ignore.exists():
        with ignore.open("x", encoding="utf-8") as handle:
            handle.write("cache/\nexports/\nproposals/\nbackups/\n")
    return result


def doctor(root, cfg):
    with sqlite3.connect(":memory:") as db:
        try:
            db.execute("CREATE VIRTUAL TABLE t USING fts5(text)")
            fts = True
        except sqlite3.OperationalError:
            fts = False
    safe_path(root, ".qkb/cache/index.sqlite3")
    return {"version": VERSION, "python": sys.version.split()[0], "python_supported": sys.version_info >= (3,10),
            "sqlite": sqlite3.sqlite_version, "fts5_available": fts, "fts5_enabled": cfg["fts_enabled"],
            "dependencies": "Python standard library only", "network": "engine never connects",
            "configuration": "present" if safe_path(root, ".qkb/config.json").exists() else "defaults; preview with init --dry-run",
            "data_location": ".qkb/cache/index.sqlite3", "warning": None if fts and cfg["fts_enabled"] else "Fallback search active; large corpus queries may be slower"}


def dispatch(args, root, cfg):
    name = args.command
    if name == "doctor": return doctor(root, cfg)
    if name == "init": return initialize(root, cfg, args.dry_run)
    if name == "status" and not safe_path(root, ".qkb/cache/index.sqlite3").exists():
        return {"state": "UNVERIFIED", "note": "Index missing; use init --dry-run before build"}
    depth = getattr(args, "depth", None) or cfg["graph_default_depth"]
    top = getattr(args, "top", None) or (cfg["query_top_k"] if name in ("search", "explore", "query") else 30)
    if depth > 8 or top > 1000:
        raise QError("Depth must be at most 8; top must be at most 1000")
    import ops
    if name == "migrate":
        import migrate
        if args.dry_run:
            return migrate.run(root, cfg, True)
        with ops.WriterLock(root):
            return migrate.run(root, cfg, False)
    if name in ("build", "update"):
        if not safe_path(root, ".qkb/config.json").exists():
            raise QError("Configuration missing; preview with init --dry-run, then init and review scope before build")
    # Item 7: writers take the lock file; read-only commands open SQLite read-only.
    writes = name in ("build", "update", "backup") or (name == "semantic" and args.action in ("import", "approve", "reject"))         or (name == "maintain" and args.apply) or (name == "embed" and args.apply)
    readonly = not writes and name not in ("maintain", "embed")
    lock = ops.WriterLock(root) if writes and name != "backup" else None
    if lock:
        lock.__enter__()
    try:
        return _dispatch_store(args, root, cfg, name, top, depth, readonly)
    finally:
        if lock:
            lock.__exit__(None, None, None)


def _dispatch_store(args, root, cfg, name, top, depth, readonly):
    import ops
    with Store(root, cfg, create=name == "build", readonly=readonly) as store:
        if name == "maintain":
            return ops.prune_history(store, args.days, args.apply)
        if name in ("build", "update"): return engine.update(store, getattr(args, "full", False))
        if name == "status": return ops.quick_status(store) if args.quick else engine.status(store)
        project = getattr(args, "project", None)
        if name == "search": return engine.search(store, args.query, top, project, args.semantic)
        if name == "explore": return engine.explore(store, args.query, top, depth, project, args.semantic)
        if name == "query":
            import router
            return router.query(store, args.question, top, depth, project, args.semantic)
        if name == "embed":
            import vectors
            return vectors.refresh(store, dry_run=not args.apply)
        if name == "read":
            if args.expand is not None:
                if not 0 <= args.expand <= 20:
                    raise QError("--expand must be between 0 and 20")
                import context
                return context.expand(store, args.id, args.expand)
            return engine.read_section(store, args.id)
        if name == "map": return engine.knowledge_map(store, top, project)
        if name == "related": return engine.traverse(store, args.node, depth, args.direction, top=top, project=project)
        if name == "impact": return engine.traverse(store, args.node, depth, "in", impact=True, top=top, project=project)
        if name == "path": return engine.find_path(store, args.source, args.target, depth, args.direction)
        if name == "verify": return engine.verify(store, args.links, top)
        if name == "semantic":
            if args.action == "list": return semantic.show(store)
            if not args.value: raise QError("This semantic action requires a file or proposal ID")
            if args.action == "import": return semantic.import_proposals(store, args.value)
            if args.action in ("show", "validate"): return semantic.show(store, args.value)
            return semantic.review(store, args.value, "APPROVED" if args.action == "approve" else "REJECTED",
                                   args.reviewer, args.reason, args.human_approved, args.ack_conflicts)
        if name == "export":
            from exports import export_graph
            return export_graph(store, args.kind, args.node, top, depth)
        if name == "benchmark":
            from benchmark import run
            return run(store, args.questions)
        if name == "backup":
            out = safe_path(root, ".qkb/backups/index-"+now().replace(":", "").replace("+", "_")+".sqlite3")
            out.parent.mkdir(parents=True, exist_ok=True)
            with out.open("xb"): pass
            with sqlite3.connect(out) as backup:
                store.db.backup(backup)
            return {"output": out.relative_to(root).as_posix(), "note": "Backup contains sensitive knowledge and review history"}
    raise QError("Unknown command")


def main(argv=None):
    # Console Unicode support on Windows; process settings unchanged.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parser().parse_args(argv)
    cfg = dict(DEFAULTS)
    try:
        if sys.version_info < (3,10): raise QError("Python 3.10+ required; request an IT-approved offline installation")
        root = Path(args.root).resolve()
        cfg = load_config(root)
        if args.max_chars is not None and args.max_chars < 200 or args.max_tokens is not None and args.max_tokens < 200:
            raise QError("Minimum response budget is 200")
        started = time.perf_counter()
        try:
            result = dispatch(args, root, cfg)
        except (QError, OSError, ValueError, sqlite3.Error):
            usage.record(root, cfg, args, {"ok": False}, (time.perf_counter() - started) * 1000)
            raise
        usage.record(root, cfg, args, result, (time.perf_counter() - started) * 1000)
        emit(result, args, cfg)
        return 1 if args.command == "verify" and not result["ok"] else 0
    except (QError, OSError, ValueError, sqlite3.Error) as exc:
        # No raw source text, SQL statements or payloads in error logs.
        message = str(exc) if isinstance(exc, QError) else type(exc).__name__ + ": operation failed; check configuration, permissions and UTF-8 input"
        args.max_chars = max(args.max_chars or cfg["query_max_chars"], 200)
        args.max_tokens = max(args.max_tokens, 200) if args.max_tokens is not None else None
        emit({"ok": False, "error": message}, args, cfg)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
