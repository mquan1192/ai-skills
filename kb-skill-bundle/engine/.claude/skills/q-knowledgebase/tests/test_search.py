import argparse
import contextlib
import io
import json
import sqlite3
from unittest.mock import patch
from support import Fixture
from core import DEFAULTS, Store, QError
import engine
from qkb import emit


class SearchTests(Fixture):
    def test_heading_and_exact_keyword(self):
        result = engine.search(self.store, "Audit workflow")
        self.assertEqual(result["results"][0]["heading"], "Audit workflow")
        self.assertEqual(result["results"][0]["source_status"], "CURRENT")

    def test_multiple_terms(self):
        rows = engine.search(self.store, "UserService audit_events")["results"]
        self.assertEqual(rows[0]["path"], "docs/api.md")

    def test_multi_term_search_avoids_irrelevant_single_word_hits(self):
        result = engine.search(self.store,"Authentication UserService")
        self.assertEqual(result["results"][0]["path"],"docs/auth.md")
        self.assertNotIn("docs/second/auth.md", [r["path"] for r in result["results"]])
        fallback = engine.search(self.store,"UserService UnknownBusinessTerm")
        self.assertTrue(fallback["results"])
        self.assertEqual(fallback["match_mode"],"partial_terms")

    def test_cjk_substring_and_vietnamese_without_accents(self):
        self.assertEqual(engine.search(self.store, "監査ログ")["results"][0]["path"], "docs/auth.md")
        self.assertEqual(engine.search(self.store, "xoa nguoi dung")["results"][0]["path"], "docs/auth.md")

    def test_exact_path_and_python_symbol(self):
        self.assertEqual(engine.search(self.store, "docs/audit.md")["results"][0]["path"], "docs/audit.md")
        symbol = engine.search(self.store, "UserService.delete_user")["results"][0]
        self.assertEqual(symbol["type"], "CODE_SYMBOL")
        self.assertEqual(symbol["start"], 4)
        self.assertEqual(engine.search(self.store,"src/client.ts")["results"][0]["type"],"CODE_FILE")

    def test_read_returns_exact_original_lines(self):
        row = engine.search(self.store, "Audit workflow")["results"][0]
        result = engine.read_section(self.store, row["id"])["sections"][0]
        text, _, _ = self.store.scope.read(result["path"])
        self.assertEqual(result["content"], "".join(text.splitlines(keepends=True)[result["start"]-1:result["end"]]))

    def test_stale_source_withholds_old_lines_and_text(self):
        row = engine.search(self.store, "Audit workflow")["results"][0]
        self.write("docs/auth.md", "# New document\nChanged source\n")
        stale = engine.search(self.store, "Audit workflow")["results"][0]
        self.assertEqual(stale["source_status"], "STALE")
        self.assertIsNone(stale["start"])
        self.assertIsNone(stale["snippet"])
        with self.assertRaises(QError): engine.read_section(self.store, row["id"])

    def test_budget_keeps_json_valid_and_cjk_token_bound(self):
        for chars, tokens in ((1000,None), (5000,1200), (200,None)):
            args = argparse.Namespace(max_chars=chars,max_tokens=tokens,format="json")
            out = io.StringIO()
            with contextlib.redirect_stdout(out): emit(engine.search(self.store, "audit", 100), args, DEFAULTS)
            rendered = out.getvalue()
            self.assertLessEqual(len(rendered), chars)
            if tokens: self.assertLessEqual(len(rendered.encode("utf-8")), tokens)
            self.assertTrue(json.loads(rendered)["_output"]["truncated"])

    def test_no_fts5_fallback(self):
        other = self.root/"fallback"
        from support import populate
        populate(other)
        cfg = {**DEFAULTS, "fts_enabled": False}
        with Store(other, cfg, create=True) as store:
            engine.update(store)
            self.assertFalse(store.fts)
            self.assertEqual(engine.search(store,"監査ログ")["results"][0]["path"], "docs/auth.md")
            self.assertIn("slower", engine.search(store,"audit")["warning"])

    def test_sqlite_build_without_fts5_module(self):
        from support import populate
        other = self.root/"no-fts-extension"
        populate(other)
        connect = sqlite3.connect
        class WithoutFTS:
            def __init__(self,*args,**kwargs):
                object.__setattr__(self,"db",connect(*args,**kwargs))
            def __getattr__(self,key): return getattr(self.db,key)
            def __setattr__(self,key,value): setattr(self.db,key,value)
            def execute(self,sql,*args):
                if "CREATE VIRTUAL TABLE" in sql: raise sqlite3.OperationalError("no such module: fts5")
                return self.db.execute(sql,*args)
            def __enter__(self): self.db.__enter__(); return self
            def __exit__(self,*args): return self.db.__exit__(*args)
        with patch("core.sqlite3.connect",WithoutFTS):
            with Store(other,dict(DEFAULTS),create=True) as store:
                self.assertFalse(store.fts)
                engine.update(store)
                self.assertTrue(engine.search(store,"authentication")["results"])

    def test_query_metacharacters_are_data(self):
        for query in ('" OR 1=1; --', '"*{}[]', "認証", "audit%_", ""):
            engine.search(self.store, query)
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM files").fetchone()[0], 11)
