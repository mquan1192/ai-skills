"""Imported KB data packs in the engine (settings merge, per-pack version / changelog,
no source scan for imported projects, "source not on this machine" for KB -> code references)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import SKILL
from core import DEFAULTS, VERSION, QError, Store, load_config
import engine
import packs
import retrieval

PAGES = {
    "kb/own/notes.md": "# Own\n## Local page\nSee `main.cpp:1`.\n",
    "kb/lib/guide.md": "# Guide\n## Loader\nThe loader is in `LD/loader.cpp:3` and `gone.cpp:1`. Ticket LB-001 is open.\n"
                       "## Terms\n- LB-001 · Status: open · Affects: `LD/loader.cpp`\n",
    "kb/lib/glossary.md": "# Glossary\n| English | Vietnamese |\n|---|---|\n| loader | bộ nạp |\n",
    "kb/lib/CHANGELOG.md": "# Changes\nloader renamed.\n",
    "src/main.cpp": "int main() { return 0; }\n",
}


def pack_manifest(**extra):
    data = {"format": "kb-data-pack", "format_version": 1, "pack_id": "pk-lib-1", "project": "lib", "title": "Library",
            "kb_version": "2026.11.18-01", "created": "2026-11-18", "previous_version": None, "engine_min": "2.1.0-d2",
            "glossary_files": ["glossary.md"], "history_paths": ["CHANGELOG.md"], "code_aliases": {"LD/": "loader/"},
            "issue_id_patterns": ["LB-\\d{3}"], "id_patterns": {"requirement": ["RQ-\\d+"]},
            "query_routes": {"impact": {"en": ["what breaks if"]}}, "route_keywords": ["loader", "nạp"],   # hook list, not read
            "source_roots_expected": ["src/lib"]}
    data.update(extra)
    return data


class PackCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qkb-d-packs-")
        self.addCleanup(self.temp.cleanup)          # runs last: after the index is closed
        self.root = Path(self.temp.name)
        for path, text in PAGES.items():
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            (self.root / path).write_text(text, encoding="utf-8")
        (self.root / ".qkb/packs/lib").mkdir(parents=True)
        self.cfg = {**DEFAULTS, "knowledge_paths": ["kb"], "source_paths": ["src"], "issue_id_patterns": ["OWN-\\d+"]}
        (self.root / ".qkb/config.json").write_text(json.dumps(self.cfg), encoding="utf-8")
        self.write_pack(pack_manifest())
        (self.root / ".qkb/packs/lib/CHANGELOG.md").write_text("# Pack changes\n", encoding="utf-8")

    def write_pack(self, data):
        (self.root / ".qkb/packs/lib/PACK.json").write_text(json.dumps(data), encoding="utf-8")

    def build(self):
        store = Store(self.root, load_config(self.root), create=True)
        self.addCleanup(store.db.close)
        engine.update(store)
        return store


class MergeTests(PackCase):
    def test_settings_merged_local_wins(self):
        cfg = load_config(self.root)
        self.assertIn("kb/lib/glossary.md", cfg["glossary_paths"])
        self.assertIn("kb/lib/CHANGELOG.md", cfg["history_paths"])
        self.assertEqual(cfg["issue_id_patterns"], ["OWN-\\d+", "LB-\\d{3}"])           # local first, then pack
        self.assertEqual(cfg["id_patterns"], {"requirement": ["RQ-\\d+"]})
        self.assertIn("what breaks if", cfg["query_routes"]["impact"]["en"])
        self.assertIn("impact", cfg["query_routes"]["impact"]["en"])                  # defaults kept
        self.assertEqual(cfg["source_paths"], ["src"])                                # never extended by a pack
        plain = load_config(self.root, packs=False)
        self.assertNotIn("_packs", plain)
        self.assertEqual(plain["glossary_paths"], [])

    def test_ignored_packs(self):
        cases = {"format": {"format": "zip"}, "engine": {"engine_min": "9.0.0"},
                 "project": {"project": "other"}, "settings": {"issue_id_patterns": ["("]},
                 "aliases": {"code_aliases": {"A/": "b.cpp"}}, "routes list": {"query_routes": ["x"]},
                 "routes depth": {"query_routes": {"impact": ["x"]}}, "glossary type": {"glossary_files": "g.md"},
                 "fields": {"issue_fields": {"status": "open"}}, "roots": {"source_roots_expected": "src"}}
        for name, extra in cases.items():
            with self.subTest(name=name):
                self.write_pack(pack_manifest(**extra))
                cfg = load_config(self.root)
                state = cfg["_packs"][0]["state"]
                self.assertTrue(state.startswith("IGNORED"), state)
                self.assertNotIn("kb/lib/glossary.md", cfg["glossary_paths"])
        (self.root / ".qkb/packs/lib/PACK.json").write_text("{not json", encoding="utf-8")
        self.assertTrue(load_config(self.root)["_packs"][0]["state"].startswith("IGNORED"))

    def test_version_order(self):
        self.assertLess(packs.version_key("2.1.0-c1"), packs.version_key("2.1.0-d2"))
        self.assertLess(packs.version_key("2.1.0-d2"), packs.version_key("2.1.0"))
        self.assertLess(packs.version_key("2.1.0"), packs.version_key("2.2.0-a1"))
        self.assertIsNone(packs.version_key("v2"))
        self.assertGreaterEqual(packs.version_key(VERSION), packs.version_key("2.1.0-d2"))

    def test_init_never_writes_pack_settings(self):
        (self.root / ".qkb/config.json").unlink()
        proc = subprocess.run([sys.executable, "-s", str(SKILL / "scripts/qkb.py"), "--root", str(self.root), "init", "--format", "json"],
                              text=True, encoding="utf-8", capture_output=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        written = json.loads((self.root / ".qkb/config.json").read_text(encoding="utf-8"))
        self.assertNotIn("_packs", written)
        self.assertEqual(written["glossary_paths"], [])


class SubPackTests(PackCase):
    def test_sub_project_folder(self):
        import shutil
        shutil.move(str(self.root / ".qkb/packs/lib"), str(self.root / ".qkb/packs/lib__core"))
        self.write_sub(pack_manifest(sub="core"))
        cfg = load_config(self.root)
        entry = cfg["_packs"][0]
        self.assertEqual((entry["folder"], entry["project"], entry["sub"], entry["state"]), ("lib__core", "lib", "core", "OK"))
        self.assertIsNotNone(packs.of_project(cfg, "lib"))
        self.write_sub(pack_manifest(sub="other"))
        self.assertTrue(load_config(self.root)["_packs"][0]["state"].startswith("IGNORED"))
        self.write_sub(pack_manifest(project="core"))
        self.assertTrue(load_config(self.root)["_packs"][0]["state"].startswith("IGNORED"))

    def write_sub(self, data):
        (self.root / ".qkb/packs/lib__core/PACK.json").write_text(json.dumps(data), encoding="utf-8")

    def test_other_files_in_pack_folder_ignored(self):
        (self.root / ".qkb/packs/lib/state.json").write_text("{not json", encoding="utf-8")
        self.assertEqual(load_config(self.root)["_packs"][0]["state"], "OK")

    def test_no_traceback_on_untrusted_types(self):
        self.write_pack(pack_manifest(route_keywords={"bad": 1}, query_routes={"impact": {"en": "x"}}))
        proc = subprocess.run([sys.executable, "-s", str(SKILL / "scripts/qkb.py"), "--root", str(self.root), "status", "--format", "json"],
                              text=True, encoding="utf-8", capture_output=True, timeout=60)
        self.assertNotIn("Traceback", proc.stderr)


class RouterKeyTests(PackCase):
    def test_route_keywords_dict_accepted_list_ignored(self):
        data = pack_manifest()
        data.pop("query_routes")
        data["route_keywords"] = {"impact": {"en": ["what breaks if"]}}
        self.write_pack(data)
        cfg = load_config(self.root)
        self.assertEqual(cfg["_packs"][0]["state"], "OK")
        self.assertIn("what breaks if", cfg["query_routes"]["impact"]["en"])
        data["route_keywords"] = ["loader"]                     # hook word list: not for the engine, not an error
        self.write_pack(data)
        self.assertEqual(load_config(self.root)["_packs"][0]["state"], "OK")
        data["route_keywords"] = {"impact": ["x"]}               # router dict of the wrong shape
        self.write_pack(data)
        self.assertTrue(load_config(self.root)["_packs"][0]["state"].startswith("IGNORED"))


class EngineTests(PackCase):
    def test_status_lists_packs(self):
        store = self.build()
        for status in (engine.status(store), engine.status(store, quick=True)):
            entry = status["packs"][0]
            self.assertEqual((entry["project"], entry["pack_id"], entry["kb_version"], entry["state"]),
                             ("lib", "pk-lib-1", "2026.11.18-01", "OK"))
            self.assertEqual(entry["changelog"], ".qkb/packs/lib/CHANGELOG.md")
        self.assertIn("packs", engine.verify(store, links=True)["links"])

    def test_pack_settings_used(self):
        store = self.build()
        issue = store.rows("SELECT label FROM nodes WHERE type='ISSUE'")
        self.assertEqual([r["label"] for r in issue], ["LB-001"])
        groups = retrieval.analyse(store, "bộ nạp")["groups"]
        self.assertTrue(any("loader" in g["alternatives"] for g in groups))           # pack glossary
        history = store.rows("SELECT metadata FROM files WHERE path='kb/lib/CHANGELOG.md'")[0]["metadata"]
        self.assertTrue(json.loads(history).get("qkb_history"))

    def test_source_not_on_this_machine(self):
        store = self.build()
        refs = {r["written"]: r["resolution"] for r in store.rows("SELECT written, resolution FROM refs WHERE path='kb/lib/guide.md' AND relation='REFERENCES'")}
        self.assertEqual(refs["loader/loader.cpp"], "SOURCE_NOT_ON_MACHINE")         # pack alias LD/ applied
        self.assertEqual(refs["gone.cpp"], "SOURCE_NOT_ON_MACHINE")
        own = store.rows("SELECT resolution FROM refs WHERE path='kb/own/notes.md' AND relation='REFERENCES'")[0]
        self.assertNotEqual(own["resolution"], "SOURCE_NOT_ON_MACHINE")              # local pages unchanged
        code = engine.link_report(store, 30)["code"]
        self.assertEqual(code["by_resolution"].get("SOURCE_NOT_ON_MACHINE"), 3)   # 2 in "Loader" + the Affects line
        self.assertFalse(store.rows("SELECT * FROM edges WHERE relation='REFERENCES' AND path='kb/lib/guide.md' AND state='BROKEN'"))

    def test_source_present_means_not_found(self):
        (self.root / "src/lib").mkdir(parents=True)
        store = self.build()
        refs = {r["written"]: r["resolution"] for r in store.rows("SELECT written, resolution FROM refs WHERE path='kb/lib/guide.md' AND relation='REFERENCES'")}
        self.assertEqual(refs["gone.cpp"], "NOT_FOUND")

    def test_alias_only_for_pack_project(self):
        (self.root / "kb/own/more.md").write_text("# More\nSee `LD/x.cpp`.\n", encoding="utf-8")
        store = self.build()
        written = store.rows("SELECT written FROM refs WHERE path='kb/own/more.md' AND relation='REFERENCES'")[0]["written"]
        self.assertEqual(written, "LD/x.cpp")                                         # pack alias not applied

    def test_no_packs_folder(self):
        import shutil
        shutil.rmtree(self.root / ".qkb/packs")
        cfg = load_config(self.root)
        self.assertNotIn("_packs", cfg)
        store = self.build()
        self.assertEqual(engine.status(store)["packs"], [])


if __name__ == "__main__":
    unittest.main()
