"""B0: --project filter and project field."""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import FORBIDDEN_NAMES, SKILL
from core import DEFAULTS, Store
import engine

CORPUS = {
    "kb/alpha/a.md": "# Alpha topic\nShared word: invoice. See `b.md`.\n",
    "kb/alpha/b.md": "# Alpha second\ninvoice notes.\n",
    "kb/beta/c.md": "# Beta topic\ninvoice for beta. See `../alpha/a.md`.\n",
    "kb/root.md": "# Root page\ninvoice at the root.\n",
}


class ProjectTests(unittest.TestCase):
    def setUp(self, **extra):
        self.temp = tempfile.TemporaryDirectory(prefix="qkb-b0-project-")
        self.root = Path(self.temp.name)
        for path, text in CORPUS.items():
            dest = self.root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")
        self.cfg = {**DEFAULTS, "knowledge_paths": ["kb"], "source_paths": ["src"]}
        (self.root / ".qkb").mkdir()
        (self.root / ".qkb/config.json").write_text(json.dumps(self.cfg), encoding="utf-8")
        self.store = Store(self.root, self.cfg, create=True)
        engine.update(self.store)

    def tearDown(self):
        self.store.db.close()
        self.temp.cleanup()

    def test_project_field_default_roots(self):
        hits = engine.search(self.store, "invoice", 10)["results"]
        projects = {h["path"]: h["project"] for h in hits}
        self.assertEqual(projects["kb/alpha/a.md"], "alpha")
        self.assertEqual(projects["kb/beta/c.md"], "beta")
        self.assertIsNone(projects["kb/root.md"])   # directly below the root: no project

    def test_search_and_explore_filter(self):
        alpha = engine.search(self.store, "invoice", 10, "alpha")
        self.assertEqual(alpha["project"], "alpha")
        self.assertTrue(alpha["results"])
        self.assertTrue(all(h["path"].startswith("kb/alpha/") for h in alpha["results"]))
        explore = engine.explore(self.store, "invoice", 5, 2, "beta")
        self.assertTrue(all(h["path"].startswith("kb/beta/") for h in explore["results"]))
        self.assertTrue(all(n["project"] in ("beta", None) or n["path"].startswith("kb/beta/") for n in explore["nodes"]))

    def test_map_counts_and_filter(self):
        full = engine.knowledge_map(self.store, 30)
        self.assertEqual({p["project"]: p["files"] for p in full["projects"]}, {"alpha": 2, "beta": 1, None: 1})
        beta = engine.knowledge_map(self.store, 30, "beta")
        self.assertTrue(all(n["path"].startswith("kb/beta/") for n in beta["nodes"]))
        self.assertEqual(beta["groups"], [{"category": "markdown", "files": 1}])

    def test_related_and_impact_stay_in_project(self):
        both = engine.traverse(self.store, "kb/beta/c.md", depth=3)
        self.assertIn("kb/alpha/a.md", {n["path"] for n in both["nodes"]})
        only = engine.traverse(self.store, "kb/beta/c.md", depth=3, project="beta")
        self.assertEqual({n["path"] for n in only["nodes"]}, {"kb/beta/c.md"})
        impact = engine.traverse(self.store, "kb/alpha/a.md", depth=3, direction="in", impact=True, project="alpha")
        self.assertTrue(all(n["path"].startswith("kb/alpha/") for n in impact["nodes"]))

    def test_explicit_project_roots(self):
        self.store.db.close()
        cfg = {**self.cfg, "project_roots": ["kb/alpha"]}
        self.store = Store(self.root, cfg)
        self.assertEqual(self.store.scope.project("kb/alpha/a.md"), None)   # file directly under the root
        self.assertEqual(self.store.scope.project("kb/beta/c.md"), None)    # outside every project root

    def test_cli_project_option(self):
        cli = SKILL / "scripts/qkb.py"
        def run(*args):
            proc = subprocess.run([sys.executable, "-s", str(cli), "--root", str(self.root), *args, "--format", "json"],
                                  text=True, encoding="utf-8", capture_output=True, timeout=60)
            return proc.returncode, json.loads(proc.stdout)
        code, data = run("search", "invoice", "--project", "alpha")
        self.assertEqual(code, 0)
        self.assertTrue(all(h["path"].startswith("kb/alpha/") for h in data["results"]))
        for command in (("explore", "invoice"), ("map",), ("related", "kb/beta/c.md"), ("impact", "kb/alpha/a.md")):
            with self.subTest(command=command[0]):
                code, data = run(*command, "--project", "alpha")
                self.assertEqual(code, 0, data)

    def test_no_project_name_hard_coded(self):
        if not FORBIDDEN_NAMES:
            self.skipTest("set QKB_FORBIDDEN_NAMES to check for project names")
        for script in (SKILL / "scripts").glob("*.py"):
            text = script.read_text(encoding="utf-8").casefold()
            for name in FORBIDDEN_NAMES:
                self.assertIsNone(re.search(r"\b" + name + r"\b", text), (script.name, name))


if __name__ == "__main__":
    unittest.main()
