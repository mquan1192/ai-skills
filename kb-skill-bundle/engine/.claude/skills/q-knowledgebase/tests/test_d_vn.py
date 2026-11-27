"""Vietnamese and number search, --project lists, cheap status --quick."""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from support import SKILL, Fixture
from core import DEFAULTS, QError, Store, load_config
import engine
import retrieval
import vntext

KB = {
    "kb/demo/thu-vien.md": "# Thư viện\n## Thời hạn mượn\nThẻ hạng Bạc được mượn tối đa 5 cuốn trong 14 ngày.\n"
                           "## Phí trễ hạn\nPhí trễ hạn là 2.000 đồng mỗi ngày, tối đa 1.234,5 nghìn đồng.\n"
                           "## Hòa giải\nQuy trình hoà giải khi tranh chấp.\n",
    "kb/demo/he-thong.md": "# Hệ thống\n## Bộ nhớ đệm\nDữ liệu phiên lưu trong cache 30 phút (TTL).\n"
                           "## Phiên bản\nBản phát hành v2.1 ngày 17/11/2026, tăng hiệu năng 5 %.\n"
                           "## Đường dẫn\nĐường dẫn đầu vào được kiểm tra.\n",
    "kb/demo/en.md": "# Engine\n## Version history\nRelease 2.1 shipped on 2026-11-17 with 1,234.5 MB of data.\n",
    "kb/shared/common.md": "# Common\n## Đường dẫn\nĐường dẫn means path.\n",
    "kb/other/x.md": "# Other\n## Đường dẫn\nđường dẫn ở project khác.\n",
}


class VnCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qkb-d-vn-")
        self.root = Path(self.temp.name)
        for path, text in KB.items():
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            (self.root / path).write_text(text, encoding="utf-8")
        (self.root / ".qkb").mkdir()
        self.cfg = {**DEFAULTS, "knowledge_paths": ["kb"], "source_paths": ["src"]}
        (self.root / ".qkb/config.json").write_text(json.dumps(self.cfg), encoding="utf-8")
        self.store = Store(self.root, load_config(self.root), create=True)
        engine.update(self.store)

    def tearDown(self):
        self.store.db.close()
        self.temp.cleanup()

    def top(self, query, n=1, **kw):
        return [(h["path"], h.get("heading")) for h in engine.search(self.store, query, 5, **kw)["results"][:n]]


class ToneTests(unittest.TestCase):
    def test_a1_tone_positions(self):
        for old, new in (("hoà", "hòa"), ("thuỷ", "thủy"), ("khoẻ", "khỏe"), ("Hoà Bình", "Hòa Bình"), ("quý", "qúy")):
            self.assertEqual(vntext.light(old), vntext.light(new), (old, new))
        self.assertNotEqual(vntext.light("bán"), vntext.light("bản"))
        self.assertEqual(vntext.tone("Engine 2.1"), "Engine 2.1")          # ASCII untouched
        self.assertEqual(vntext.light("ĐƯỜNG"), "đường")


class NumberTests(unittest.TestCase):
    def test_a5_canonical_tokens(self):
        cases = {"1.234,5 kg": {"1234.5", "1234.5kg"}, "1,234.5": {"1234.5"}, "17/11/2026": {"2026-11-17"},
                 "2026-11-17": {"2026-11-17"}, "2,5 triệu": {"2500000"}, "v2.1": {"v2.1"}, "phiên bản 2.1": {"v2.1"},
                 "5 %": {"5%"}, "5 mm": {"5mm"}, "18.450": {"18450", "18.450"}}
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertLessEqual(expected, vntext.numbers(text))

    def test_names_with_numbers_are_not_amounts(self):
        self.assertEqual(vntext.number_spans("rs-485"), [])
        self.assertEqual([t for _, _, t in vntext.number_spans("qt 6.9.1")], [])
        self.assertEqual(vntext.numbers("abc1.2.3"), set())


class SearchTests(VnCase):
    def test_a2_no_diacritics_finds_accented(self):
        self.assertEqual(self.top("phi tre han"), [("kb/demo/thu-vien.md", "Phí trễ hạn")])
        self.assertEqual(self.top("duong dan dau vao"), [("kb/demo/he-thong.md", "Đường dẫn")])

    def test_a1_a2_accented_exact_first(self):
        hits = self.top("hòa giải")
        self.assertEqual(hits, [("kb/demo/thu-vien.md", "Hòa giải")])   # written "hoà" in the text

    def test_a3_phrases_found(self):
        result = engine.search(self.store, "đường dẫn đầu vào")
        self.assertIn("duong dan", result["phrases"])          # "đầu vào" is a common-glossary term (input)
        self.assertEqual(result["results"][0]["heading"], "Đường dẫn")

    def test_a4_question_words_dropped(self):
        terms = retrieval.analyse(self.store, "Thẻ hạng Bạc được mượn tối đa bao nhiêu cuốn?")["groups"]
        texts = [g["text"] for g in terms]
        self.assertNotIn("bao", texts)
        self.assertNotIn("được", texts)
        self.assertEqual(self.top("Thẻ hạng Bạc được mượn tối đa bao nhiêu cuốn?"), [("kb/demo/thu-vien.md", "Thời hạn mượn")])

    def test_a5_number_variants_match(self):
        self.assertEqual(self.top("phí 1234,5 nghìn"), [("kb/demo/thu-vien.md", "Phí trễ hạn")])
        self.assertEqual(self.top("phát hành 2026-11-17"), [("kb/demo/he-thong.md", "Phiên bản")])
        hits = self.top("2026-11-17", 2)
        self.assertEqual({h[0] for h in hits}, {"kb/demo/he-thong.md", "kb/demo/en.md"})   # dd/mm/yyyy and ISO
        self.assertEqual(self.top("1234.5 MB"), [("kb/demo/en.md", "Version history")])
        self.assertEqual(self.top("phiên bản 2.1", 1)[0][0], "kb/demo/he-thong.md")

    def test_a6_common_words(self):
        result = engine.search(self.store, "cache tồn tại bao lâu")
        self.assertEqual(result["results"][0]["heading"], "Bộ nhớ đệm")

    def test_trigram_rows_carry_number_tokens(self):
        rows = self.store.db.execute("SELECT content FROM search_tri").fetchall()
        self.assertTrue(any("2026-11-17" in r[0] and "17/11/2026" in r[0] for r in rows))
        self.assertEqual(self.store.getmeta("trigram_format"), "2")

    def test_old_trigram_rows_refilled_once(self):
        self.store.setmeta("trigram_format", "1")
        self.store.db.execute("DELETE FROM search_tri")
        self.store.db.commit()
        engine.update(self.store)
        self.assertEqual(self.store.getmeta("trigram_format"), "2")
        count = self.store.db.execute("SELECT count(*) FROM search_tri").fetchone()[0]
        self.assertEqual(count, self.store.db.execute("SELECT count(*) FROM sections").fetchone()[0])


class LanguageConfigTests(VnCase):
    def test_b2_kb_content(self):
        for value in ("vi", "en", "ja", "mixed"):
            cfg = {**self.cfg, "languages": {"kb_content": value}}
            (self.root / ".qkb/config.json").write_text(json.dumps(cfg), encoding="utf-8")
            self.assertEqual(load_config(self.root)["languages"]["kb_content"], value)
        for bad in ({"kb_content": "fr"}, {"other": "x"}, "vi"):
            cfg = {**self.cfg, "languages": bad}
            (self.root / ".qkb/config.json").write_text(json.dumps(cfg), encoding="utf-8")
            with self.assertRaises(QError):
                load_config(self.root)
        self.store.cfg = {**self.store.cfg, "languages": {"kb_content": "ja"}}
        self.assertEqual(engine.search(self.store, "đường dẫn đầu vào")["phrases"], [])   # no Latin phrases for JA
        self.store.cfg = {**self.store.cfg, "languages": {"kb_content": "vi"}}
        self.assertTrue(engine.search(self.store, "đường dẫn đầu vào")["phrases"])


class ProjectListTests(VnCase):
    def test_project_list(self):
        def paths(project):
            return {h["path"] for h in engine.search(self.store, "đường dẫn", 10, project)["results"]}
        self.assertEqual(paths("demo"), {"kb/demo/he-thong.md"})
        self.assertEqual(paths("demo,shared"), {"kb/demo/he-thong.md", "kb/shared/common.md"})
        self.assertEqual(paths("demo, shared ,"), {"kb/demo/he-thong.md", "kb/shared/common.md"})
        self.assertNotIn("kb/other/x.md", paths("demo,shared"))
        self.assertEqual(paths("demo/sub"), set())                                # path below a project root
        self.assertTrue(self.store.scope.in_project("kb/demo/a/b.md", "demo/a"))
        self.assertFalse(self.store.scope.in_project("kb/demo/ab.md", "demo/a"))
        self.assertTrue(self.store.scope.in_project("kb/demo/x.md", None))
        self.assertFalse(self.store.scope.in_project("kb/root.md", "demo"))

    def test_cli_project_list(self):
        proc = subprocess.run([sys.executable, "-s", str(SKILL / "scripts/qkb.py"), "--root", str(self.root), "search", "đường dẫn",
                               "--project", "demo,shared", "--format", "json"], text=True, encoding="utf-8", capture_output=True, timeout=60)
        data = json.loads(proc.stdout)
        self.assertEqual(proc.returncode, 0, data)
        self.assertEqual({h["path"] for h in data["results"]}, {"kb/demo/he-thong.md", "kb/shared/common.md"})
        for command in (("map",), ("explore", "đường dẫn"), ("query", "đường dẫn")):
            proc = subprocess.run([sys.executable, "-s", str(SKILL / "scripts/qkb.py"), "--root", str(self.root), *command,
                                   "--project", "demo,shared", "--format", "json"], text=True, encoding="utf-8", capture_output=True, timeout=60)
            self.assertEqual(proc.returncode, 0, proc.stdout)


class QuickStatusTests(Fixture):
    def test_quick_detects_added_removed_and_changed(self):
        quick = engine.status(self.store, quick=True)
        self.assertEqual((quick["state"], quick["hashed"], quick["folders_changed"]), ("CURRENT", 0, []))
        self.write("docs/new.md", "# New\n")
        quick = engine.status(self.store, quick=True)
        self.assertEqual(quick["state"], "STALE")
        self.assertIn("docs", quick["folders_changed"])
        engine.update(self.store)
        self.assertEqual(engine.status(self.store, quick=True)["state"], "CURRENT")
        os.remove(self.root / "docs/new.md")
        quick = engine.status(self.store, quick=True)
        self.assertEqual(quick["state"], "STALE")
        self.assertIn("docs/new.md", quick["deleted"])

    def test_quick_does_not_walk_folders(self):
        import core
        calls = []
        original = core.Scope.scan
        core.Scope.scan = lambda self: calls.append(1) or original(self)
        try:
            engine.status(self.store, quick=True)
        finally:
            core.Scope.scan = original
        self.assertEqual(calls, [])

    def test_quick_without_folder_record(self):
        self.store.db.execute("DELETE FROM meta WHERE key='qkb_folder_mtimes'")
        self.store.db.commit()
        quick = engine.status(self.store, quick=True)
        self.assertEqual(quick["state"], "STALE")
        self.assertTrue(quick["folders_changed"])


if __name__ == "__main__":
    unittest.main()
