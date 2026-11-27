"""Phase B review fixes, and the fixture root of the install tests."""
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from support import SKILL, package_fixture, populate
from core import DEFAULTS, QError, Store
import engine
import migrate

CORPUS = {
    "kb/alpha/a.md": "# A\nSee `twin.md` and `only-beta.md` and `root-note.md`.\n",
    "kb/alpha/x/twin.md": "# Twin 1\n",
    "kb/alpha/y/twin.md": "# Twin 2\n",
    "kb/beta/only-beta.md": "# Only beta\n",
    "kb/beta/b.md": "# B\nSee `a.md`.\n",
    "kb/root.md": "# Root\nSee `only-beta.md` and `root-note.md`.\n",
    "kb/root-note.md": "# Root note\n",
}


class LowFixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qkb-b1-low-")
        self.root = Path(self.temp.name)
        for path, text in CORPUS.items():
            dest = self.root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")
        (self.root / ".qkb").mkdir()
        self.cfg = {**DEFAULTS, "knowledge_paths": ["kb"], "source_paths": ["src"]}
        (self.root / ".qkb/config.json").write_text(json.dumps(self.cfg), encoding="utf-8")
        self.store = Store(self.root, self.cfg, create=True)
        engine.update(self.store)

    def tearDown(self):
        self.store.db.close()
        self.temp.cleanup()

    def refs(self, path):
        return {r["written"]: r for r in self.store.rows("SELECT * FROM refs WHERE path=? AND relation='REFERENCES'", (path,))}

    def test_l1_ambiguous_creates_no_edge(self):
        ref = self.refs("kb/alpha/a.md")["twin.md"]
        self.assertEqual(ref["resolution"], "AMBIGUOUS")
        self.assertEqual(len(json.loads(ref["candidates"])), 2)
        edges = self.store.rows("SELECT * FROM edges WHERE relation='REFERENCES' AND path='kb/alpha/a.md'")
        targets = {e["target"]: e["state"] for e in edges}
        twin_nodes = {n["id"] for n in self.store.rows("SELECT id FROM nodes WHERE path LIKE '%twin.md'")}
        self.assertFalse(set(targets) & twin_nodes)           # no edge to either twin or a placeholder
        broken = [e for e in edges if e["state"] == "BROKEN"]
        self.assertEqual(len(broken), 1)                      # only the NOT_FOUND reference (only-beta.md)
        placeholders = self.store.rows("SELECT * FROM nodes WHERE status='CANDIDATE' AND hash='' AND path LIKE '%twin.md'")
        self.assertEqual(placeholders, [])
        links = engine.verify(self.store, links=True)["links"]
        self.assertEqual(links["broken_by_cause"]["AMBIGUOUS"]["count"], 1)   # still reported

    def test_l3_unique_name_never_crosses_projects(self):
        alpha = self.refs("kb/alpha/a.md")
        self.assertEqual(alpha["only-beta.md"]["resolution"], "NOT_FOUND")    # exists only in project beta
        root = self.refs("kb/root.md")
        # A file without a project matches only files without a project.
        self.assertEqual(root["only-beta.md"]["resolution"], "NOT_FOUND")
        self.assertEqual(root["root-note.md"]["resolution"], "relative")
        self.assertEqual(alpha["root-note.md"]["resolution"], "ancestor")   # written path steps, not step 7
        beta = self.refs("kb/beta/b.md")
        self.assertEqual(beta["a.md"]["resolution"], "NOT_FOUND")


class MigrateSchemaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qkb-b1-migrate-")
        self.root = Path(self.temp.name)
        populate(self.root)
        self.cfg = dict(DEFAULTS)
        with Store(self.root, self.cfg, create=True) as store:
            engine.update(store)
        self.index = self.root / ".qkb/cache/index.sqlite3"

    def tearDown(self):
        self.temp.cleanup()

    def set_schema(self, value):
        with closing(sqlite3.connect(self.index)) as db:
            db.execute("UPDATE meta SET value=? WHERE key='schema'", (value,))
            db.commit()

    def test_l2_newer_or_unknown_schema_refused(self):
        for value in ("3", "99", "x"):
            with self.subTest(schema=value):
                self.set_schema(value)
                before = self.index.read_bytes()
                for dry in (True, False):
                    with self.assertRaises(QError):
                        migrate.run(self.root, self.cfg, dry)
                self.assertEqual(self.index.read_bytes(), before)
                self.assertFalse((self.root / ".qkb/backups").exists())

    def test_current_schema_is_a_no_op(self):
        self.assertEqual(migrate.run(self.root, self.cfg, False)["state"], "CURRENT")


class PackageFixtureTests(unittest.TestCase):
    def test_fixture_takes_package_files_only(self):
        with tempfile.TemporaryDirectory(prefix="qkb-b1-package-") as temp:
            dest = Path(temp)
            package_fixture(dest)
            top = {p.name for p in dest.iterdir()}
            allowed = {".claude", ".qkb", "CHANGELOG.md", "MANIFEST.json", "Q-KnowledgeBase-README.md",
                       "Q-KnowledgeBase-install.py", "Q-KnowledgeBase-VALIDATION.md", "SECURITY.md"}
            self.assertLessEqual(top, allowed)
            self.assertEqual({p.name for p in (dest / ".claude").iterdir()} - {"skills", "rules"}, set())
            self.assertEqual([p.name for p in (dest / ".claude/skills").iterdir()], ["q-knowledgebase"])
            self.assertTrue((dest / ".claude/skills/q-knowledgebase/scripts/qkb.py").is_file())
            self.assertFalse(list(dest.rglob("__pycache__")))
            self.assertFalse(list(dest.rglob("*.Tests.ps1")))
            self.assertFalse((dest / "CHANGES_VN.md").exists())
            # Bounded size: the skill plus a few root files, never a repository copy.
            self.assertLess(sum(1 for p in dest.rglob("*") if p.is_file()), 80)

    def test_install_tests_do_not_copy_the_parent_folder(self):
        for name in ("test_install.py", "test_offline.py"):
            text = (SKILL / "tests" / name).read_text(encoding="utf-8")
            self.assertNotIn("parents[2]", text, name)
            self.assertIn("package_fixture", text, name)


if __name__ == "__main__":
    unittest.main()
