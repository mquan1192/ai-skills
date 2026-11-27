"""Index schema upgrade: backup -> keep proposals / reviews / history -> rebuild the rest
from the sources -> verify. The index is derived data except those three tables, so the upgrade
rebuilds instead of altering columns. Rollback = copy the backup file back to .qkb/cache/index.sqlite3."""
from __future__ import annotations

import os
import sqlite3
from contextlib import closing

from core import OLD_SCHEMAS, SCHEMA, QError, Scope, Store, now, safe_path

KEEP = ("proposals", "reviews", "history")
INDEX = ".qkb/cache/index.sqlite3"


def _read_index(path):
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    try:
        if not db.execute("SELECT name FROM sqlite_master WHERE name='meta'").fetchone():
            raise QError("Index schema missing; restore a valid backup")
        row = db.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
        schema = row[0] if row else None
        kept = {}
        for table in KEEP:
            exists = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
            kept[table] = [dict(r) for r in db.execute("SELECT * FROM " + table)] if exists else []
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        return schema, kept, integrity
    finally:
        db.close()


def run(root, cfg, dry_run=False):
    import engine
    index = safe_path(root, INDEX)
    if not index.exists():
        raise QError("Index missing; nothing to migrate. Use init --dry-run, init and build")
    schema, kept, integrity = _read_index(index)
    counts = {t: len(kept[t]) for t in KEEP}
    stamp = now().replace(":", "").replace("+", "_")
    backup = safe_path(root, ".qkb/backups/index-" + stamp + "-schema" + str(schema) + "-pre-migrate.sqlite3")
    plan = {"from_schema": schema, "to_schema": str(SCHEMA), "keep": counts, "sqlite_integrity": integrity,
            "backup": backup.relative_to(root).as_posix(), "steps": ["backup", "keep proposals/reviews/history",
            "rebuild files/sections/nodes/edges/refs from sources", "verify"],
            "rollback": "copy the backup file to " + INDEX + " (and restore the old skill folder and .qkb/config.json)"}
    if schema == str(SCHEMA):
        return {**plan, "dry_run": dry_run, "state": "CURRENT", "note": "Index already at the current schema; nothing to do"}
    if schema not in OLD_SCHEMAS:
        # An unknown or newer schema is never rebuilt down to this version.
        raise QError("Index schema " + str(schema) + " is not a known older schema (" + ", ".join(sorted(OLD_SCHEMAS)) + "); use the engine version that wrote it or restore a backup")
    if integrity != "ok":
        raise QError("SQLite integrity check failed; restore a valid backup before migrating")
    if dry_run:
        return {**plan, "dry_run": True, "state": "PLANNED", "files_to_index": len(Scope(root, cfg).scan())}
    backup.parent.mkdir(parents=True, exist_ok=True)
    with backup.open("xb"):
        pass
    with closing(sqlite3.connect(index)) as source, closing(sqlite3.connect(backup)) as target:
        source.backup(target)   # closing(): a sqlite3 "with" block commits but does not close (Windows file locks)
    moved = safe_path(root, ".qkb/backups/index-" + stamp + "-schema" + str(schema) + "-replaced.sqlite3")
    os.replace(index, moved)   # keep the old file too; the backup copy above is the documented rollback
    try:
        with Store(root, cfg, create=True) as store:
            with store.db:
                for table in KEEP:
                    for row in kept[table]:
                        cols = list(row)
                        store.db.execute("INSERT INTO " + table + " (" + ",".join(cols) + ") VALUES (" + ",".join("?" * len(cols)) + ")",
                                         [row[c] for c in cols])
            update = engine.update(store, True)
            after = {t: store.db.execute("SELECT count(*) FROM " + t).fetchone()[0] for t in KEEP}
            check = store.db.execute("PRAGMA integrity_check").fetchone()[0]
        lost = {t: counts[t] - after[t] for t in ("proposals", "reviews") if after[t] < counts[t]}
        if check != "ok" or after["history"] < counts["history"] or lost:
            raise QError("Migration verification failed (kept rows or integrity); old index restored")
    except Exception:
        if index.exists():
            os.replace(index, safe_path(root, ".qkb/backups/index-" + stamp + "-failed-migrate.sqlite3"))
        os.replace(moved, index)   # automatic rollback
        raise
    return {**plan, "dry_run": False, "state": "MIGRATED", "kept_after": after, "sqlite_integrity_after": check,
            "rebuilt": {k: update[k] for k in ("added", "modified", "deleted", "unchanged")},
            "replaced_index": moved.relative_to(root).as_posix()}
