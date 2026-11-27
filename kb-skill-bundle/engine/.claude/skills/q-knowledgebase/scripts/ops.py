"""Performance and maintenance helpers: read-only connections, writer lock, quick status,
history pruning after a backup."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone

from core import QError, connect_readonly, now, safe_path   # noqa: F401 (re-export)

LOCK = ".qkb/cache/writer.lock"


class WriterLock:
    """One writer at a time (build, update, migrate, semantic writes, maintain). The lock file holds the
    process id and time; a lock older than stale_seconds is taken over (a crashed writer)."""

    def __init__(self, root, stale_seconds=600):
        self.path = safe_path(root, LOCK)
        self.stale = stale_seconds
        self.took_over = False
        self.held = False

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(5):   # a few rounds: a stale take-over or a release may happen between steps
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                try:
                    age = time.time() - self.path.stat().st_mtime
                except FileNotFoundError:
                    continue   # released meanwhile: try again
                if age < self.stale:
                    raise QError("Another writer is running (lock %s, %d s old); retry when it ends" % (LOCK, age))
                if not self._take_over():
                    raise QError("Another writer is taking over a stale lock (%s); retry when it ends" % LOCK)
                continue   # the stale lock is gone: race on O_EXCL again; exactly one process wins
            except PermissionError:
                raise QError("Writer lock %s is in use; retry when the other writer ends" % LOCK)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(json.dumps({"pid": os.getpid(), "at": now()}))
            self.held = True
            return self
        raise QError("Writer lock could not be taken")

    def _take_over(self):
        """Stale take-over under a second O_EXCL guard file. Only the guard holder re-checks the lock
        and deletes it if it is still stale, so a process that saw the stale lock earlier can never delete the
        fresh lock of the winner. A guard left by a crash is removed once it is itself older than stale_seconds."""
        guard = self.path.with_name("writer.lock.takeover")
        try:
            fd = os.open(guard, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except (FileExistsError, PermissionError):
            try:
                if time.time() - guard.stat().st_mtime > self.stale:
                    guard.unlink()
            except OSError:
                pass
            return False
        os.close(fd)
        try:
            try:
                if time.time() - self.path.stat().st_mtime >= self.stale:
                    self.path.unlink()
                    self.took_over = True
            except FileNotFoundError:
                pass
            return True
        finally:
            try:
                guard.unlink()
            except OSError:
                pass

    def __exit__(self, *args):
        if self.held:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
            self.held = False


def quick_status(store):
    """status --quick: see engine.status(quick=True). Meant for hooks; "status" stays the full check."""
    import engine
    return engine.status(store, quick=True)


def prune_history(store, older_than_days, apply=False):
    """Delete history rows older than N days, only after a backup newer than every row to delete."""
    if older_than_days < 1:
        raise QError("--days must be at least 1")
    cutoff = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).isoformat()
    rows = store.db.execute("SELECT count(*), max(at) FROM history WHERE at < ?", (cutoff,)).fetchone()
    count, newest = rows[0], rows[1]
    result = {"rows": count, "older_than": cutoff, "dry_run": not apply}
    if not count:
        return {**result, "backup": None, "note": "Nothing to prune"}
    folder = safe_path(store.root, ".qkb/backups")
    backups = sorted((p for p in folder.glob("index-*.sqlite3") if p.is_file()), key=lambda p: p.stat().st_mtime) if folder.is_dir() else []
    newest_ts = datetime.fromisoformat(newest).timestamp()
    fresh = [p for p in backups if p.stat().st_mtime > newest_ts]
    if not fresh:
        raise QError("Run backup first: no backup in .qkb/backups is newer than the history rows to prune")
    result["backup"] = fresh[-1].relative_to(store.root).as_posix()
    if apply:
        with store.db:
            store.db.execute("DELETE FROM history WHERE at < ?", (cutoff,))
        result["note"] = "History rows deleted; restore them from the backup if needed"
    else:
        result["note"] = "Dry run; add --apply to delete"
    return result
