"""Ordered path resolver, non-path strings, history_paths."""
import json
import tempfile
import unittest
from pathlib import Path

from support import SKILL  # noqa: F401  (adds scripts/ to sys.path)
from core import DEFAULTS, Store
import engine

CORPUS = {
    "kb/alpha/sub/topics/a.md": "# A\n"
        "Same folder: `b.md`.\n"                     # 1 relative
        "Root: `kb/alpha/sub/docs/c.md`.\n"          # 2 root
        "Sub-project root: `docs/c.md`.\n"           # 3 ancestor (kb/alpha/sub)
        "Project root: `shared/s.md`.\n"             # 4 ancestor (kb/alpha)
        "Bare unique: `deep.md`.\n"                  # 7 unique name in project alpha
        "Bare ambiguous: `twin.md`.\n"               # 7 -> AMBIGUOUS
        "Missing: `nothing-here.md`.\n"              # NOT_FOUND
        "Outside index: `notes/outside.md`.\n"       # existing file not in knowledge_paths
        "Pattern: `*.md`, placeholder `<name>.md`, prose `a b.md`.\n"
        "Code: `tool.py`.\n",                        # 6 source root
    "kb/alpha/sub/topics/b.md": "# B\n",
    "kb/alpha/sub/docs/c.md": "# C\n",
    "kb/alpha/shared/s.md": "# S\n",
    "kb/alpha/sub/very/deep/deep.md": "# Deep\n",
    "kb/alpha/sub/x/twin.md": "# Twin X\n",
    "kb/alpha/sub/y/twin.md": "# Twin Y\n",
    "kb/beta/deep.md": "# Other project's deep\n",   # same name in another project: ignored by step 7
    "kb/CHANGELOG.md": "# Changelog\n## 2026-11-17\nAdded `alpha/sub/topics/a.md` and `missing-old.md`.\n",
    "notes/outside.md": "# Outside\n",
    "src/tool.py": "def run():\n    return 1\n",
}


class ResolverTests(unittest.TestCase):
    def build(self, **extra):
        self.temp = tempfile.TemporaryDirectory(prefix="qkb-b0-")
        root = Path(self.temp.name)
        for path, text in CORPUS.items():
            dest = root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")
        cfg = {**DEFAULTS, "knowledge_paths": ["kb"], "source_paths": ["src"], **extra}
        (root / ".qkb").mkdir()
        (root / ".qkb/config.json").write_text(json.dumps(cfg), encoding="utf-8")
        self.store = Store(root, cfg, create=True)
        engine.update(self.store)
        return self.store

    def tearDown(self):
        self.store.db.close()
        self.temp.cleanup()

    def refs(self, path="kb/alpha/sub/topics/a.md"):
        return {r["written"]: r for r in self.store.rows("SELECT * FROM refs WHERE path=? AND relation='REFERENCES'", (path,))}

    def test_ordered_resolution_rules(self):
        self.build()
        refs = self.refs()
        expected = {"b.md": ("relative", "kb/alpha/sub/topics/b.md"),
                    "kb/alpha/sub/docs/c.md": ("root", "kb/alpha/sub/docs/c.md"),
                    "docs/c.md": ("ancestor", "kb/alpha/sub/docs/c.md"),
                    "shared/s.md": ("ancestor", "kb/alpha/shared/s.md"),
                    "deep.md": ("unique_name", "kb/alpha/sub/very/deep/deep.md"),
                    "tool.py": ("source_root", "src/tool.py")}
        edges = {(e["path"], e["start"]): e for e in engine.graph_edges(self.store) if e["relation"] == "REFERENCES"}
        for written, (rule, target) in expected.items():
            with self.subTest(written=written):
                ref = refs[written]
                self.assertEqual(ref["resolution"], rule)
                edge = edges[("kb/alpha/sub/topics/a.md", ref["start"])]
                self.assertEqual(edge["state"], "CURRENT")
                node = self.store.rows("SELECT path FROM nodes WHERE id=?", (edge["target"],))[0]
                self.assertEqual(node["path"], target)

    def test_ambiguous_is_never_guessed(self):
        self.build()
        ref = self.refs()["twin.md"]
        self.assertEqual(ref["resolution"], "AMBIGUOUS")
        self.assertEqual(sorted(json.loads(ref["candidates"])), ["kb/alpha/sub/x/twin.md", "kb/alpha/sub/y/twin.md"])
        targets = {self.store.rows("SELECT path FROM nodes WHERE id=?", (e["target"],))[0]["path"]
                   for e in engine.graph_edges(self.store) if e["path"] == "kb/alpha/sub/topics/a.md" and e["start"] == ref["start"]}
        self.assertFalse(targets & {"kb/alpha/sub/x/twin.md", "kb/alpha/sub/y/twin.md"})

    def test_unique_name_stays_inside_the_project(self):
        self.build()
        ref = self.refs()["deep.md"]
        self.assertEqual(ref["target_path"] if ref["resolution"] != "unique_name" else "kb/alpha/sub/very/deep/deep.md",
                         "kb/alpha/sub/very/deep/deep.md")
        self.assertEqual(ref["resolution"], "unique_name")   # kb/beta/deep.md (other project) is not a tie

    def test_not_found_and_outside_index(self):
        self.build()
        refs = self.refs()
        self.assertEqual(refs["nothing-here.md"]["resolution"], "NOT_FOUND")
        self.assertEqual(refs["notes/outside.md"]["resolution"], "OUTSIDE_INDEX")
        outside_edges = [e for e in engine.graph_edges(self.store)
                         if e["path"] == "kb/alpha/sub/topics/a.md" and e["start"] == refs["notes/outside.md"]["start"]]
        self.assertEqual(outside_edges, [])

    def test_non_path_strings_are_skipped(self):
        self.build()
        written = set(self.refs())
        self.assertFalse({"*.md", "<name>.md", "a b.md"} & written)
        meta = json.loads(self.store.rows("SELECT metadata FROM files WHERE path='kb/alpha/sub/topics/a.md'")[0]["metadata"])
        self.assertEqual(meta["qkb_skipped_refs"], 3)

    def test_history_paths_searchable_without_edges_and_ranked_last(self):
        self.build(history_paths=["**/CHANGELOG.md", "CHANGELOG.md"])
        self.assertEqual(self.refs("kb/CHANGELOG.md"), {})
        self.assertEqual([e for e in engine.graph_edges(self.store) if e["path"] == "kb/CHANGELOG.md" and e["relation"] == "REFERENCES"], [])
        hits = engine.search(self.store, "Changelog", 5)["results"]
        self.assertTrue(any(h["path"] == "kb/CHANGELOG.md" and h["history"] for h in hits))
        mixed = engine.search(self.store, "deep", 10)["results"]
        flags = [h.get("history", False) for h in mixed]
        self.assertEqual(flags, sorted(flags))   # non-history first

    def test_without_history_paths_changelog_links_like_2_0_0(self):
        self.build()
        refs = self.refs("kb/CHANGELOG.md")
        self.assertEqual(refs["alpha/sub/topics/a.md"]["resolution"], "relative")
        self.assertEqual(refs["missing-old.md"]["resolution"], "NOT_FOUND")

    def test_verify_links_groups_causes(self):
        self.build()
        links = engine.verify(self.store, links=True)["links"]
        self.assertEqual(links["broken_by_cause"]["AMBIGUOUS"]["count"], 1)
        self.assertEqual(links["outside_index"]["count"], 1)
        item = next(i for i in links["broken_by_cause"]["NOT_FOUND"]["items"] if i["path"] == "kb/alpha/sub/topics/a.md")
        self.assertEqual(item["written"], "nothing-here.md")
        self.assertEqual(item["line"], 8)
        self.assertNotIn("links", engine.verify(self.store))   # plain verify unchanged


if __name__ == "__main__":
    unittest.main()
