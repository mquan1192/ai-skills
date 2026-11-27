"""Phase B: structure chunking, context and text formats."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import SKILL, Fixture
from core import DEFAULTS, Store, markdown_sections
from chunking import split_span
from textformats import text_sections
import context
import engine


def table(rows):
    return ["| Code | Meaning |\n", "|---|---|\n"] + ["| C%02d | value %d |\n" % (i, i) for i in range(rows)]


class ChunkingTests(unittest.TestCase):
    def covers(self, chunks, start, end):
        lines = [i for c in chunks for i in range(c["start"], c["stop"])]
        self.assertEqual(lines, list(range(start, end)))

    def test_small_blocks_never_cut(self):
        lines = ["intro\n"] * 3 + ["\n"] + table(4) + ["\n", "```\n", "code 1\n", "code 2\n", "```\n", "tail\n"]
        chunks = split_span(lines, 0, len(lines), 8)
        self.covers(chunks, 0, len(lines))
        for c in chunks:
            self.assertLessEqual(c["stop"] - c["start"], 8)
        table_lines = range(4, 10)
        holders = [c for c in chunks if any(c["start"] <= i < c["stop"] for i in table_lines)]
        self.assertEqual(len(holders), 1)                              # table kept whole
        fence_lines = range(11, 15)
        self.assertEqual(len([c for c in chunks if any(c["start"] <= i < c["stop"] for i in fence_lines)]), 1)

    def test_long_table_cut_at_rows_with_header(self):
        lines = table(30)
        chunks = split_span(lines, 0, len(lines), 10)
        self.covers(chunks, 0, len(lines))
        self.assertEqual(chunks[0]["prefix"], "")
        for c in chunks[1:]:
            self.assertEqual(c["prefix"], "| Code | Meaning |\n|---|---|\n")
            self.assertTrue(lines[c["start"]].startswith("| C"))       # cut at a row border

    def test_long_code_cut_at_blank_lines(self):
        lines = ["```\n"] + ["a\n"] * 5 + ["\n"] + ["b\n"] * 5 + ["```\n"]
        chunks = split_span(lines, 0, len(lines), 8)
        self.covers(chunks, 0, len(lines))
        self.assertEqual(chunks[0]["stop"], 7)                           # after the blank line

    def test_degenerate_sizes_and_determinism(self):
        lines = table(5) + ["x\n"] * 3
        for size in (1, 2):
            chunks = split_span(lines, 0, len(lines), size)
            self.covers(chunks, 0, len(lines))
            self.assertEqual(chunks, split_span(lines, 0, len(lines), size))
        self.assertEqual(split_span(lines, 3, 3, 5), [])

    def test_markdown_sections_keep_ids_and_lines(self):
        text = "# Codes\n" + "".join(table(30)) + "## After\ntext\n"
        _, by_lines = markdown_sections("doc.md", text, 10, "lines")
        _, by_structure = markdown_sections("doc.md", text, 10, "structure")
        self.assertEqual({s["section_id"] for s in by_lines}, {s["section_id"] for s in by_structure})   # stable IDs
        for s in by_structure:
            original = "".join(text.splitlines(keepends=True)[s["start"] - 1:s["end"]])
            self.assertTrue(s["content"].endswith(original))             # original lines, header only prepended
        cut = [s for s in by_structure if s["heading"] == "Codes" and s["order"] > 0]
        self.assertTrue(cut and all(s["content"].startswith("| Code | Meaning |") for s in cut))


class ContextTests(Fixture):
    def test_compact_merges_chunks_of_one_section(self):
        results = [{"id": "a1", "section_id": "A", "path": "p.md", "start": 10, "end": 20, "score": 9},
                   {"id": "b", "section_id": "B", "path": "p.md", "start": 1, "end": 5, "score": 8},
                   {"id": "a2", "section_id": "A", "path": "p.md", "start": 21, "end": 30, "score": 7},
                   {"id": "sym", "type": "CODE_SYMBOL", "path": "x.py", "score": 6}]
        out = context.compact(results)
        self.assertEqual([r["id"] for r in out], ["a1", "b", "sym"])
        self.assertEqual((out[0]["start"], out[0]["end"], out[0]["merged"]), (10, 30, 2))
        self.assertNotIn("merged", out[1])

    def test_search_returns_distinct_sections(self):
        self.write("docs/long.md", "# Long\n" + "audit line\n" * 250)
        engine.update(self.store)
        hits = engine.search(self.store, "audit line", 5)["results"]
        keys = [(h["path"], h.get("section_id")) for h in hits]
        self.assertEqual(len(keys), len(set(keys)))

    def test_expand_neighbours(self):
        hit = engine.search(self.store, "Audit workflow")["results"][0]
        data = context.expand(self.store, hit["id"], 1)
        self.assertTrue(any(c["requested"] for c in data["chunks"]))
        self.assertGreaterEqual(len(data["chunks"]), 2)
        for chunk in data["chunks"]:
            for key in ("id", "section_id", "path", "heading", "start", "end", "hash", "source_status", "content"):
                self.assertIn(key, chunk)
        starts = [c["start"] for c in data["chunks"]]
        self.assertEqual(starts, sorted(starts))
        self.write("docs/auth.md", "# Changed\n")
        self.assertIsNone(context.expand(self.store, hit["id"], 0)["chunks"][0]["content"])   # STALE -> no content

    def test_cli_read_expand(self):
        hit = engine.search(self.store, "Audit workflow")["results"][0]
        proc = subprocess.run([sys.executable, "-s", str(SKILL / "scripts/qkb.py"), "--root", str(self.root), "read", hit["id"],
                               "--expand", "--format", "json"], text=True, encoding="utf-8", capture_output=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("chunks", json.loads(proc.stdout))
        proc = subprocess.run([sys.executable, "-s", str(SKILL / "scripts/qkb.py"), "--root", str(self.root), "read", "nope",
                               "--expand", "2", "--format", "json"], text=True, encoding="utf-8", capture_output=True, timeout=60)
        self.assertEqual(proc.returncode, 2)


class TextFormatTests(unittest.TestCase):
    def test_json_top_level_keys(self):
        text = '{\n  "alpha": {"x": "a, b"},\n  "beta": [1,\n    2],\n  "gamma \\"q\\"": "}"\n}\n'
        meta, sections = text_sections("cfg/app.json", text, 50)
        self.assertEqual(meta["format"], "json")
        self.assertEqual([s["heading"] for s in sections], ["(preamble)", "alpha", "beta", 'gamma "q"'])
        self.assertEqual([s["start"] for s in sections], [1, 2, 3, 5])
        lines = [i for s in sections for i in range(s["start"], s["end"] + 1)]
        self.assertEqual(lines, list(range(1, len(text.splitlines()) + 1)))

    def test_invalid_json_falls_back(self):
        meta, sections = text_sections("bad.json", "{ not json\n", 50)
        self.assertEqual(meta["parse_status"], "TEXT_FALLBACK")
        self.assertEqual(len(sections), 1)

    def test_yaml_toml_txt(self):
        _, y = text_sections("a.yaml", "# comment\nname: x\nlist:\n  - a\n  - b\nother: 1\n", 50)
        self.assertEqual([s["heading"] for s in y], ["(preamble)", "name", "list", "other"])
        _, t = text_sections("a.toml", 'title = "x"\n[server]\nport = 1\n[[items]]\nn = 2\n', 50)
        self.assertEqual([s["heading"] for s in t], ["(preamble)", "server", "items"])
        _, x = text_sections("notes.txt", "line\n" * 120, 50)
        self.assertEqual({s["heading"] for s in x}, {"notes.txt"})
        self.assertEqual(len(x), 3)

    def test_indexed_only_when_configured(self):
        with tempfile.TemporaryDirectory(prefix="qkb-b1-formats-") as temp:
            root = Path(temp)
            (root / "kb").mkdir()
            (root / "kb/a.md").write_text("# A\nalpha\n", encoding="utf-8")
            (root / "kb/settings.yaml").write_text("timeout: 30\nretry_count: 3\n", encoding="utf-8")
            (root / ".qkb").mkdir()
            cfg = {**DEFAULTS, "knowledge_paths": ["kb"], "source_paths": ["src"]}
            with Store(root, cfg, create=True) as store:
                engine.update(store)
                self.assertEqual([r["path"] for r in store.rows("SELECT path FROM files")], ["kb/a.md"])
            cfg["text_formats"] = [".yaml"]
            with Store(root, cfg) as store:
                engine.update(store)
                hit = engine.search(store, "retry_count")["results"][0]
                self.assertEqual((hit["path"], hit["heading"]), ("kb/settings.yaml", "retry_count"))
                self.assertEqual(store.rows("SELECT count(*) AS n FROM refs WHERE path='kb/settings.yaml'")[0]["n"], 0)


if __name__ == "__main__":
    unittest.main()
