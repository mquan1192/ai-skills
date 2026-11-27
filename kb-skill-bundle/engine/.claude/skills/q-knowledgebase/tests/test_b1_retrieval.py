"""Trigram table, glossary bridge, stop words, rrf / classic ranking."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from support import FORBIDDEN_NAMES, Fixture, populate
from core import DEFAULTS, QError, Store, load_config
import engine
import retrieval

GLOSSARY = """# Terms

| English | Japanese | Vietnamese | Note |
|---|---|---|---|
| Order ID | 注文ID | mã đơn | Unique per order. |
| Rollback (order cancel) | 取消 | hủy đơn* | `code` |
| Batch method | 一括バッチ法（日次法／月次法） | phương pháp theo lô | |
| sale | 販売 | bán | |

| Japanese | English | Vietnamese |
|---|---|---|
| 返金処理 | refund process | hoàn tiền |

| Name | Owner |
|---|---|
| not a language table | nobody |
"""

CORPUS = {
    "kb/order.md": "# Order\n## Order ID length\nThe order ID has at most 12 characters; maximum length is fixed.\n"
                   "## Order cancel\nBefore a refund is paid the service will rollback the stock (order cancel).\n",
    "kb/sale.md": "# Sale summary\nSale filter of the monthly summary.\n",
    "kb/vi.md": "# Ghi chú\nCó bản ghi cần hỏi.\n",
    "kb/glossary.md": GLOSSARY,
}


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qkb-b1-retrieval-")
        self.root = Path(self.temp.name)
        for path, text in CORPUS.items():
            dest = self.root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")
        (self.root / ".qkb").mkdir()
        self.cfg = {**DEFAULTS, "knowledge_paths": ["kb"], "source_paths": ["src"],
                    "glossary_paths": ["kb/glossary.md"], "common_glossary": False}
        self.store = self.open(self.cfg, create=True)
        engine.update(self.store)

    def tearDown(self):
        self.store.db.close()
        self.temp.cleanup()

    def open(self, cfg, create=False):
        (self.root / ".qkb/config.json").write_text(json.dumps(cfg), encoding="utf-8")
        return Store(self.root, load_config(self.root), create=create)

    def reopen(self, **changes):
        self.store.db.close()
        self.cfg = {**self.cfg, **changes}
        self.store = self.open(self.cfg)

    # ---- glossary parsing
    def test_glossary_tables_and_cells(self):
        entries = retrieval.parse_glossary(GLOSSARY, DEFAULTS["glossary_columns"])
        self.assertEqual(len(entries), 5)                     # table without two language columns ignored
        folded = [{f for _, _, f in e} for e in entries]
        self.assertIn({"order id", "注文id", "ma don"}, folded)
        cancel = folded[1]
        self.assertTrue({"rollback", "order cancel", "取消", "huy don"} <= cancel)   # parentheses + "*" marker
        batch = folded[2]
        self.assertTrue({"一括ハッチ法", "日次法", "月次法"} <= batch)           # split after the parentheses
        home = folded[4]
        self.assertIn("refund process", home)                 # JA | EN | VI column order read from the header

    def test_parsed_glossary_kept_in_index_and_refreshed(self):
        cached = json.loads(self.store.getmeta("qkb_glossary"))
        self.assertEqual(len(cached["entries"]), 5)
        retrieval._GLOSSARY_CACHE.clear()
        self.assertEqual(len(retrieval.glossary(self.store)), 5)          # read from the index
        path = self.root / "kb/glossary.md"
        path.write_text(GLOSSARY + "\n| English | Vietnamese |\n|---|---|\n| warehouse | kho |\n", encoding="utf-8")
        retrieval._GLOSSARY_CACHE.clear()
        self.assertEqual(len(retrieval.glossary(self.store)), 6)          # file changed: parsed again
        self.store.hash_cache.clear()
        engine.update(self.store)
        self.assertEqual(len(json.loads(self.store.getmeta("qkb_glossary"))["entries"]), 6)

    def test_term_inside_joined_token_not_matched(self):
        self.assertEqual(retrieval.analyse(self.store, "sale-filter-2")["expanded"], [])
        self.assertTrue(retrieval.analyse(self.store, "sale filter")["expanded"])

    def test_no_glossary_configured_means_no_expansion(self):
        self.reopen(glossary_paths=[])
        analysis = retrieval.analyse(self.store, "mã đơn")
        self.assertEqual(analysis["expanded"], [])

    def test_vietnamese_query_bridged_to_english(self):
        analysis = retrieval.analyse(self.store, "mã đơn dài tối đa bao nhiêu")
        groups = {g["text"]: g["alternatives"] for g in analysis["groups"]}
        self.assertIn("order id", groups["mã đơn"])
        self.assertNotIn("bao", groups)                       # multi-word stop phrase removed
        hits = engine.search(self.store, "mã đơn")["results"]
        # The glossary page holds the words as written and ranks first; the English page is found too.
        self.assertEqual(hits[0]["path"], "kb/glossary.md")
        self.assertIn("kb/order.md", [h["path"] for h in hits[:3]])

    def test_accents_keep_words_apart(self):
        # "bản" (copy) must not match the glossary row "bán" (sale) through accent folding.
        analysis = retrieval.analyse(self.store, "bản ghi")
        self.assertEqual(analysis["expanded"], [])
        # Typed without accents, the folded form is the only one available and may match.
        self.assertTrue(retrieval.analyse(self.store, "ban")["expanded"])

    def test_stop_words_from_configuration(self):
        groups = [g["text"] for g in retrieval.analyse(self.store, "how does the order cancel work")["groups"]]
        self.assertEqual(groups, ["order cancel"])
        self.reopen(stopwords={"en": ["cancel"]})
        groups = [g["text"] for g in retrieval.analyse(self.store, "how cancel")["groups"]]
        self.assertEqual(groups, ["how"])
        only_stop = retrieval.analyse(self.store, "cancel")["groups"]   # nothing left -> words kept
        self.assertEqual([g["text"] for g in only_stop], ["cancel"])

    def test_written_term_ranks_before_translation(self):
        hits = engine.search(self.store, "Order cancel")["results"]
        self.assertEqual(hits[0]["heading"], "Order cancel")

    def test_common_glossary_switch(self):
        self.reopen(glossary_paths=[], common_glossary=True)
        alternatives = [g["alternatives"] for g in retrieval.analyse(self.store, "hóa đơn khách hàng")["groups"]]
        self.assertTrue(any("invoice" in a for a in alternatives))
        self.assertTrue(retrieval.COMMON_GLOSSARY.is_file())
        text = retrieval.COMMON_GLOSSARY.read_text(encoding="utf-8").casefold()
        for name in FORBIDDEN_NAMES:            # from QKB_FORBIDDEN_NAMES; nothing to check when unset
            self.assertNotIn(name, text)

    # ---- trigram table
    def test_trigram_table_follows_updates(self):
        self.assertTrue(self.store.trigram)
        count = self.store.db.execute("SELECT count(*) FROM search_tri").fetchone()[0]
        self.assertEqual(count, self.store.db.execute("SELECT count(*) FROM sections").fetchone()[0])
        (self.root / "kb/sale.md").write_text("# Kho\nHàng tồn của kho.\n", encoding="utf-8")
        self.store.hash_cache.clear()
        engine.update(self.store)
        rows = self.store.db.execute("SELECT content FROM search_tri").fetchall()
        self.assertTrue(any("hang ton cua kho" in r[0] for r in rows))   # folded text
        self.assertFalse(any("sale filter" in r[0] for r in rows))
        self.assertEqual(engine.search(self.store, "kho")["results"][0]["path"], "kb/sale.md")

    def test_index_without_trigram_gets_it_on_update(self):
        self.store.db.execute("DROP TABLE search_tri")
        self.store.db.commit()
        self.reopen()
        self.assertFalse(self.store.trigram)
        self.assertTrue(engine.search(self.store, "rollback")["results"])       # substring fallback
        engine.update(self.store)
        self.assertTrue(self.store.trigram)

    def test_trigram_off_by_configuration(self):
        self.reopen(trigram_enabled=False)
        self.assertFalse(self.store.trigram)
        self.assertEqual(engine.search(self.store, "rollback")["trigram"], False)
        self.assertTrue(engine.search(self.store, "rollback")["results"])

    # ---- ranking flag
    def test_classic_ranking_kept_behind_flag(self):
        new = engine.search(self.store, "Order cancel")
        self.assertEqual(new["ranking_mode"], "rrf")
        for key in ("results", "candidates", "fts5", "match_mode", "ranking", "warning", "query_terms", "expanded"):
            self.assertIn(key, new)
        self.reopen(ranking="classic")
        old = engine.search(self.store, "Order cancel")
        self.assertEqual(old["ranking_mode"], "classic")
        self.assertEqual(old["results"][0]["heading"], engine.search_classic(self.store, "Order cancel")["results"][0]["heading"])

    def test_invalid_phase_b_configuration(self):
        for bad in ({"ranking": "bm25"}, {"chunk_mode": "pages"}, {"trigram_enabled": 1},
                    {"glossary_paths": ["../outside.md"]}, {"stopwords": {"en": "the"}},
                    {"query_routes": {"teleport": {"en": ["x"]}}}, {"text_formats": [".pdf"]},
                    {"glossary_columns": {"en": [""]}}, {"common_glossary": "yes"}):
            with self.subTest(bad=bad):
                (self.root / ".qkb/config.json").write_text(json.dumps({**self.cfg, **bad}), encoding="utf-8")
                with self.assertRaises(QError):
                    load_config(self.root)
        (self.root / ".qkb/config.json").write_text(json.dumps(self.cfg), encoding="utf-8")


class DefaultFixtureTests(Fixture):
    """The 2.0.0 fixture questions still work with the Phase B defaults."""

    def test_defaults_are_rrf_with_trigram(self):
        self.assertEqual(DEFAULTS["ranking"], "rrf")
        result = engine.search(self.store, "監査ログ")
        self.assertEqual(result["results"][0]["path"], "docs/auth.md")
        self.assertTrue(result["trigram"])

    def test_one_and_two_character_cjk_terms(self):
        self.write("docs/short.md", "# 表\n表の一覧。\n")
        engine.update(self.store)
        self.assertEqual(engine.search(self.store, "表")["results"][0]["path"], "docs/short.md")


if __name__ == "__main__":
    unittest.main()
