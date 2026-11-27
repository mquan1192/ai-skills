"""Read-only commands, writer lock, status --quick, history pruning."""
import json
import os
import sqlite3
import subprocess
import sys
import time
import unittest

from support import SKILL, Fixture
from core import QError, Store, connect_readonly
import engine
import ops


class OpsTests(Fixture):
    def cli(self, *args):
        proc = subprocess.run([sys.executable, "-s", str(SKILL / "scripts/qkb.py"), "--root", str(self.root), *args, "--format", "json"],
                              text=True, encoding="utf-8", capture_output=True, timeout=90)
        return proc.returncode, json.loads(proc.stdout)

    def test_readonly_connection_cannot_write(self):
        db = connect_readonly(self.store.path)
        try:
            self.assertTrue(db.execute("SELECT count(*) FROM files").fetchone()[0])
            with self.assertRaises(sqlite3.OperationalError):
                db.execute("DELETE FROM files")
        finally:
            db.close()
        with Store(self.root, self.store.cfg, readonly=True) as store:
            self.assertTrue(store.readonly)
            self.assertTrue(engine.search(store, "Audit workflow")["results"])

    def test_writer_lock(self):
        with ops.WriterLock(self.root) as lock:
            self.assertTrue(lock.path.exists())
            with self.assertRaises(QError):
                ops.WriterLock(self.root).__enter__()
            code, data = self.cli("update")
            self.assertEqual(code, 2)
            self.assertIn("writer", data["error"])
            self.assertEqual(self.cli("search", "Audit workflow")[0], 0)      # readers are not blocked
        self.assertFalse(lock.path.exists())
        # A stale lock (crashed writer) is taken over.
        lock.path.write_text("{}", encoding="utf-8")
        old = time.time() - 3600
        os.utime(lock.path, (old, old))
        with ops.WriterLock(self.root) as taken:
            self.assertTrue(taken.took_over)
        self.assertEqual(self.cli("update")[0], 0)
        self.assertFalse(lock.path.exists())

    def test_quick_status(self):
        quick = ops.quick_status(self.store)
        self.assertEqual((quick["state"], quick["hashed"], quick["quick"]), ("CURRENT", 0, True))
        full = engine.status(self.store)
        for key in full:
            self.assertIn(key, quick)
        path = self.root / "docs/legacy.md"
        stamp = path.stat().st_mtime_ns + 5_000_000_000
        os.utime(path, ns=(stamp, stamp))                      # touched, same content
        quick = ops.quick_status(self.store)
        self.assertEqual((quick["state"], quick["hashed"]), ("CURRENT", 1))
        self.write("docs/legacy.md", "# Old policy\nchanged\n")
        quick = ops.quick_status(self.store)
        self.assertEqual(quick["state"], "STALE")
        self.assertEqual(quick["changed"], ["docs/legacy.md"])
        engine.update(self.store)
        self.assertEqual(ops.quick_status(self.store)["hashed"], 0)
        code, data = self.cli("status", "--quick")
        self.assertEqual((code, data["quick"]), (0, True))

    def test_prune_history_needs_backup(self):
        self.store.db.execute("INSERT INTO history(at,reason,path,snapshot) VALUES (?,?,?,?)",
                              ("2020-01-01T00:00:00+00:00", "old", "docs/x.md", "{}"))
        self.store.db.commit()
        with self.assertRaises(QError):
            ops.prune_history(self.store, 30)
        code, data = self.cli("maintain", "prune-history", "--days", "30")
        self.assertEqual(code, 2)
        self.assertEqual(self.cli("backup")[0], 0)
        dry = ops.prune_history(self.store, 30)
        self.assertEqual((dry["rows"], dry["dry_run"]), (1, True))
        self.assertTrue(dry["backup"].startswith(".qkb/backups/"))
        code, data = self.cli("maintain", "prune-history", "--days", "30", "--apply")
        self.assertEqual(code, 0, data)
        self.assertEqual(data["rows"], 1)
        left = self.store.db.execute("SELECT count(*) FROM history WHERE at < '2021'").fetchone()[0]
        self.assertEqual(left, 0)
        self.assertEqual(ops.prune_history(self.store, 30)["rows"], 0)


if __name__ == "__main__":
    unittest.main()
