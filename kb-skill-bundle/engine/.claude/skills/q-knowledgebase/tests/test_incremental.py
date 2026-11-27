import json
from unittest.mock import patch
from support import Fixture
from core import ident
import engine


class IncrementalTests(Fixture):
    def test_unchanged_files_not_reparsed(self):
        timestamps = self.store.rows("SELECT path,indexed_at FROM files ORDER BY path")
        result = engine.update(self.store)
        self.assertEqual(result["unchanged"],11)
        self.assertEqual(result["modified"],0)
        self.assertEqual(timestamps, self.store.rows("SELECT path,indexed_at FROM files ORDER BY path"))

    def test_add_modify_delete_and_history(self):
        self.write("docs/new.md", "# New\nNew facts\n")
        self.assertEqual(engine.update(self.store)["added"],1)
        self.write("docs/new.md", "# Changed heading\nModified\n")
        self.assertEqual(engine.update(self.store)["modified"],1)
        self.assertTrue(engine.search(self.store,"Changed heading")["results"])
        (self.root/"docs/new.md").unlink()
        self.assertEqual(engine.update(self.store)["deleted"],1)
        self.assertFalse(self.store.rows("SELECT * FROM sections WHERE path='docs/new.md'"))
        self.assertGreaterEqual(self.store.db.execute("SELECT count(*) FROM history").fetchone()[0],2)

    def test_rename_detected_as_hash_preserving_move(self):
        (self.root/"docs/second/auth.md").rename(self.root/"docs/second/moved.md")
        result = engine.update(self.store)
        self.assertIn({"from":"docs/second/auth.md","to":"docs/second/moved.md"}, result["renamed"])
        self.assertFalse(self.store.rows("SELECT * FROM files WHERE path='docs/second/auth.md'"))

    def test_changed_anchor_invalidates_incoming_reference(self):
        text = (self.root/"docs/audit.md").read_text(encoding="utf-8").replace("## Events", "## Renamed")
        self.write("docs/audit.md",text)
        engine.update(self.store)
        refs = self.store.rows("SELECT * FROM edges WHERE path='docs/auth.md' AND relation='REFERENCES'")
        self.assertTrue(any(r["state"] == "BROKEN" for r in refs))

    def test_modified_hash_detected_even_with_unchanged_timestamp(self):
        import os
        p = self.root/"docs/legacy.md"
        stamp = p.stat()
        self.write("docs/legacy.md", "# Old policy\nChanged content\n")
        os.utime(p, ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
        self.assertEqual(engine.status(self.store)["state"],"STALE")
        self.assertEqual(engine.update(self.store)["modified"],1)

    def test_transaction_rolls_back_partial_update(self):
        previous = self.store.rows("SELECT * FROM files ORDER BY path")
        self.write("docs/legacy.md", "# Changed\nNew\n")
        with patch("engine.extract_markdown", side_effect=RuntimeError("forced test interruption")):
            with self.assertRaises(RuntimeError): engine.update(self.store)
        self.assertEqual(previous,self.store.rows("SELECT * FROM files ORDER BY path"))
        self.assertTrue(self.store.rows("SELECT * FROM edges WHERE relation='SUPERSEDES'"))

    def test_scope_change_removes_indexed_content_retains_history(self):
        self.store.cfg["exclude_patterns"] = ["docs/legacy.md"]
        self.store.scope.cfg = self.store.cfg
        self.assertEqual(engine.status(self.store)["state"], "STALE")
        engine.update(self.store)
        self.assertFalse(self.store.rows("SELECT * FROM files WHERE path='docs/legacy.md'"))
        self.assertTrue(self.store.rows("SELECT * FROM history WHERE path='docs/legacy.md'"))
