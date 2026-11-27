import json
from support import Fixture
from core import markdown_sections


class MarkdownTests(Fixture):
    def test_nested_headings_and_fence_exclusion(self):
        rows = self.store.rows("SELECT * FROM sections WHERE path='docs/auth.md' ORDER BY start")
        self.assertEqual([r["heading"] for r in rows], ["(preamble)", "Authentication", "Audit workflow", "Constraints"])
        self.assertEqual(json.loads(rows[-1]["hierarchy"]), ["Authentication", "Audit workflow", "Constraints"])
        self.assertIn("## Also not a heading", rows[2]["content"])

    def test_all_original_lines_covered_without_loss(self):
        for row in self.store.rows("SELECT * FROM files WHERE category='markdown'"):
            text, _, _ = self.store.scope.read(row["path"])
            sections = self.store.rows("SELECT * FROM sections WHERE path=? ORDER BY start", (row["path"],))
            self.assertEqual("".join(s["content"] for s in sections), text)
            for s in sections:
                self.assertEqual(s["content"], "".join(text.splitlines(keepends=True)[s["start"]-1:s["end"]]))

    def test_tables_vietnamese_japanese_and_bom(self):
        contents = "".join(r["content"] for r in self.store.rows("SELECT content FROM sections WHERE path='docs/auth.md' ORDER BY start"))
        self.assertIn("| Delete | Audit required |", contents)
        self.assertIn("Xóa người dùng", contents)
        self.assertIn("監査ログ", contents)
        self.assertNotIn("\ufeff", contents)
        self.assertTrue((self.root/"docs/auth.md").read_bytes().startswith(b'\xef\xbb\xbf'))

    def test_same_filename_distinct_ids(self):
        rows = self.store.rows("SELECT id,path FROM sections WHERE heading='Authentication'")
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0]["id"], rows[1]["id"])

    def test_chunk_order_stable_and_line_spans(self):
        text = "# Topic\n" + "line\n"*12
        _, parts = markdown_sections("docs/test.md", text, 4)
        self.assertEqual([p["order"] for p in parts], [0,1,2,3])
        self.assertEqual([p["start"] for p in parts], [1,5,9,13])
        self.assertEqual("".join(p["content"] for p in parts), text)
        _, changed = markdown_sections("docs/test.md", "intro\n"+text, 4)
        self.assertEqual(parts[0]["id"], changed[1]["id"])

    def test_long_fence_and_heading_levels(self):
        text = "# One\n````md\n## Hidden\n```\n### Still hidden\n````\n###### Six\n"
        _, parts = markdown_sections("docs/test.md", text, 100)
        self.assertEqual([p["heading"] for p in parts], ["One", "Six"])

    def test_duplicate_headings_have_distinct_anchors(self):
        _, parts = markdown_sections("docs/test.md", "# Same\na\n# Same\nb\n", 100)
        self.assertEqual([p["anchor"] for p in parts], ["same", "same-1"])
        self.assertNotEqual(parts[0]["section_id"], parts[1]["section_id"])

    def test_empty_document_is_preserved(self):
        from engine import update
        from engine import read_section
        from core import ident
        self.write("docs/empty.md", "")
        update(self.store)
        self.assertTrue(self.store.rows("SELECT path FROM files WHERE path='docs/empty.md'"))
        result = read_section(self.store,ident("doc","docs/empty.md"))["sections"][0]
        self.assertEqual(result["content"],"")
        self.assertIsNone(result["start"])

    def test_invalid_optional_entity_metadata_does_not_execute_or_crash(self):
        from engine import update
        self.write("docs/metadata.md", '---\nqkb_entities: [{"type":[],"name":"invalid"}]\n---\n# Safe\nOriginal content.\n')
        update(self.store)
        self.assertFalse(self.store.rows("SELECT * FROM nodes WHERE label='invalid'"))
