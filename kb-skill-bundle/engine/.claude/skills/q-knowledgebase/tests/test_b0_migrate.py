"""Migrate from a 2.0.0 (schema 1) index keeps proposals / reviews / history."""
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
from contextlib import closing

from support import SKILL, Fixture
from core import DEFAULTS, QError, Store
import engine
import migrate
import semantic

OLD_REFS = """CREATE TABLE refs(id TEXT PRIMARY KEY, source TEXT, path TEXT, target_path TEXT,
 anchor TEXT, relation TEXT, start INTEGER, end INTEGER, evidence TEXT, hash TEXT);"""


def to_schema_1(path):
    """Turn a fresh index into the 2.0.0 layout: old refs table, schema 1 (the only DDL difference)."""
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("DROP TABLE refs")
        db.execute(OLD_REFS)
        db.execute("UPDATE meta SET value='1' WHERE key='schema'")


class MigrateTests(Fixture):
    def make_v200_index(self):
        pid = self.import_proposal()
        semantic.review(self.store, pid, "APPROVED", "Reviewer", "Checked both sections", True, False)
        self.write("docs/legacy.md", "# Old policy\nEdited so history gets a row.\n")
        engine.update(self.store)
        counts = {t: self.store.db.execute("SELECT count(*) FROM " + t).fetchone()[0] for t in ("proposals", "reviews", "history")}
        decision = self.store.rows("SELECT decision FROM proposals WHERE id=?", (pid,))[0]["decision"]
        self.store.db.close()
        to_schema_1(self.store.path)
        return pid, counts, decision

    def tearDown(self):
        try:
            self.store.db.close()
        except Exception:
            pass
        self.temp.cleanup()

    def test_old_index_is_refused_with_a_migrate_hint(self):
        self.make_v200_index()
        with self.assertRaises(QError) as ctx:
            Store(self.root, dict(DEFAULTS))
        self.assertIn("migrate", str(ctx.exception))

    def test_dry_run_changes_nothing(self):
        _, counts, _ = self.make_v200_index()
        before = hashlib.sha256(self.store.path.read_bytes()).hexdigest()
        plan = migrate.run(self.root, dict(DEFAULTS), dry_run=True)
        self.assertEqual((plan["state"], plan["from_schema"], plan["to_schema"]), ("PLANNED", "1", "2"))
        self.assertEqual(plan["keep"], counts)
        self.assertEqual(hashlib.sha256(self.store.path.read_bytes()).hexdigest(), before)
        self.assertFalse((self.root / ".qkb/backups").exists())

    def test_migrate_keeps_reviews_and_rebuilds(self):
        pid, counts, decision = self.make_v200_index()
        result = migrate.run(self.root, dict(DEFAULTS))
        self.assertEqual(result["state"], "MIGRATED")
        self.assertTrue((self.root / result["backup"]).exists())
        with Store(self.root, dict(DEFAULTS)) as store:
            after = {t: store.db.execute("SELECT count(*) FROM " + t).fetchone()[0] for t in ("proposals", "reviews")}
            self.assertEqual(after, {k: counts[k] for k in after})
            self.assertGreaterEqual(store.db.execute("SELECT count(*) FROM history").fetchone()[0], counts["history"])
            self.assertEqual(store.rows("SELECT decision FROM proposals WHERE id=?", (pid,))[0]["decision"], decision)
            self.assertEqual(store.getmeta("schema"), "2")
            self.assertEqual(engine.status(store)["state"], "CURRENT")
            self.assertTrue(engine.search(store, "Audit workflow", 3)["results"])
            self.assertIn(pid, [e["id"] for e in engine.graph_edges(store) if e["origin"] == "INFERRED"])
        self.assertEqual(migrate.run(self.root, dict(DEFAULTS))["state"], "CURRENT")   # idempotent

    def test_rollback_by_copying_the_backup(self):
        _, counts, _ = self.make_v200_index()
        result = migrate.run(self.root, dict(DEFAULTS))
        shutil.copyfile(self.root / result["backup"], self.store.path)
        with closing(sqlite3.connect(self.store.path)) as db:
            self.assertEqual(db.execute("SELECT value FROM meta WHERE key='schema'").fetchone()[0], "1")
            self.assertEqual(db.execute("SELECT count(*) FROM proposals").fetchone()[0], counts["proposals"])

    def test_failed_migration_restores_the_old_index(self):
        self.make_v200_index()
        before = hashlib.sha256(self.store.path.read_bytes()).hexdigest()
        original = engine.update
        engine.update = lambda store, force=False: (_ for _ in ()).throw(QError("simulated failure"))
        try:
            with self.assertRaises(QError):
                migrate.run(self.root, dict(DEFAULTS))
        finally:
            engine.update = original
        self.assertEqual(hashlib.sha256(self.store.path.read_bytes()).hexdigest(), before)

    def test_cli_migrate(self):
        self.make_v200_index()
        cli = SKILL / "scripts/qkb.py"
        run = lambda *a: subprocess.run([sys.executable, "-s", str(cli), "--root", str(self.root), *a, "--format", "json"],
                                        text=True, encoding="utf-8", capture_output=True, timeout=60)
        self.assertEqual(run("status").returncode, 2)
        dry = run("migrate", "--dry-run")
        self.assertEqual(dry.returncode, 0)
        self.assertEqual(json.loads(dry.stdout)["state"], "PLANNED")
        done = run("migrate")
        self.assertEqual(json.loads(done.stdout)["state"], "MIGRATED")
        self.assertEqual(run("verify").returncode in (0, 1), True)
