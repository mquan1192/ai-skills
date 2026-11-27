"""2.1.0-e2: a data pack is untrusted input. Unsafe ID patterns and unsafe paths make the pack IGNORED;
only Markdown is indexed from a pack's data folder, whatever text_formats / source_paths say."""
import json
import time
import unittest

import support  # noqa: F401  (puts scripts/ on sys.path)
from core import load_config
import packs
from test_d_packs import PackCase, pack_manifest


class PatternTests(unittest.TestCase):
    def test_safe_patterns(self):
        for pattern in ("OP-\\d{3}", "C-\\d{2,3}", "[a-z]+-\\d+", "(OP|C)-\\d+", "(?:ab)+", "[1-9]x", "RQ-\\d+(?:\\.\\d+)?"):
            with self.subTest(pattern=pattern):
                self.assertIsNone(packs.unsafe_pattern(pattern))

    def test_unsafe_patterns(self):
        cases = {"(a+)+$": "nested", "((a+))*": "nested", "(a|aa)+": "nested", "(\\w*x)*": "nested",
                 "(x{1,9}){2,}": "nested", "([a-z]+)*-1": "nested", "x*": "empty", "(": "compile",
                 "(a)\\1": "back-reference", "(?P<n>a)(?P=n)": "back-reference", "(a)?(?(1)b|c)": "back-reference",
                 "": "length", "A" * 201: "length", 5: "length"}
        for pattern, word in cases.items():
            with self.subTest(pattern=pattern):
                self.assertIn(word, packs.unsafe_pattern(pattern) or "")

    def test_check_is_fast_on_hostile_pattern(self):
        started = time.perf_counter()
        self.assertIsNotNone(packs.unsafe_pattern("(" * 90 + "a+" + ")+" * 90))
        self.assertLess(time.perf_counter() - started, 0.5)


class CraftedPackTests(PackCase):
    def state(self, **extra):
        self.write_pack(pack_manifest(**extra))
        cfg = load_config(self.root)
        return cfg, cfg["_packs"][0]["state"]

    def test_unsafe_issue_pattern_ignored(self):
        cfg, state = self.state(issue_id_patterns=["LB-\\d{3}", "(a+)+$"])
        self.assertEqual(state, "IGNORED (unsafe ID pattern (nested or alternated repetition))")
        self.assertEqual(cfg["issue_id_patterns"], ["OWN-\\d+"])             # nothing of the pack merged
        self.assertNotIn("kb/lib/glossary.md", cfg["glossary_paths"])

    def test_unsafe_id_pattern_ignored(self):
        cfg, state = self.state(id_patterns={"requirement": ["RQ-\\d+"], "route": ["(\\w|\\d)+R"]})
        self.assertTrue(state.startswith("IGNORED (unsafe ID pattern"), state)
        self.assertEqual(cfg["id_patterns"], {})

    def test_back_reference_ignored(self):
        _, state = self.state(issue_id_patterns=["(LB)-\\1"])
        self.assertEqual(state, "IGNORED (unsafe ID pattern (back-reference))")

    def test_safe_pack_still_ok(self):
        cfg, state = self.state()
        self.assertEqual(state, "OK")
        self.assertIn("LB-\\d{3}", cfg["issue_id_patterns"])

    def test_unsafe_paths_ignored(self):
        cases = {"up": {"glossary_files": ["../own/notes.md"]}, "abs": {"history_paths": ["/etc/x.md"]},
                 "drive": {"glossary_files": ["C:/x.md"]}, "back": {"history_paths": ["..\\..\\x.md"]},
                 "not md": {"glossary_files": ["glossary.json"]}}
        for name, extra in cases.items():
            with self.subTest(name=name):
                cfg, state = self.state(**extra)
                self.assertTrue(state.startswith("IGNORED (unsafe path") or state == "IGNORED (glossary file is not Markdown)", state)
                self.assertEqual(cfg["issue_id_patterns"], ["OWN-\\d+"])

    def test_only_markdown_indexed_from_pack_folder(self):
        extra = {"kb/lib/run.ps1": "Write-Host loaderx\n", "kb/lib/data.json": "{\"k\": \"loaderjson\"}\n",
                 "kb/lib/notes.txt": "loadertxt\n", "kb/lib/tool.py": "print('loaderpy')\n",
                 "kb/own/extra.txt": "ownertxt\n"}
        for path, text in extra.items():
            (self.root / path).write_text(text, encoding="utf-8")
        cfg = {**self.cfg, "text_formats": [".json", ".txt"], "source_paths": ["src", "kb"]}
        (self.root / ".qkb/config.json").write_text(json.dumps(cfg), encoding="utf-8")
        store = self.build()
        files = {row[0] for row in store.db.execute("SELECT path FROM files")}
        self.assertIn("kb/lib/guide.md", files)
        self.assertIn("kb/own/extra.txt", files)                       # local folder: text formats as configured
        for path in ("kb/lib/run.ps1", "kb/lib/data.json", "kb/lib/notes.txt", "kb/lib/tool.py"):
            self.assertNotIn(path, files)
            self.assertIsNone(store.scope.category(path))

    def test_ignored_pack_folder_still_markdown_only(self):
        self.write_pack(pack_manifest(issue_id_patterns=["(a+)+$"]))
        (self.root / "kb/lib/notes.txt").write_text("loadertxt\n", encoding="utf-8")
        cfg = {**self.cfg, "text_formats": [".txt"]}
        (self.root / ".qkb/config.json").write_text(json.dumps(cfg), encoding="utf-8")
        store = self.build()
        self.assertTrue(store.cfg["_packs"][0]["state"].startswith("IGNORED"))
        self.assertIsNone(store.scope.category("kb/lib/notes.txt"))
        self.assertEqual(store.scope.category("kb/lib/guide.md"), "markdown")

    def test_route_keywords_carry_over(self):
        data = pack_manifest()
        del data["query_routes"]
        data["route_keywords"] = {"impact": {"vi": ["hỏng gì nếu"]}}
        self.write_pack(data)
        cfg = load_config(self.root)
        self.assertEqual(cfg["_packs"][0]["state"], "OK")
        self.assertIn("hỏng gì nếu", cfg["query_routes"]["impact"]["vi"])


if __name__ == "__main__":
    unittest.main()
