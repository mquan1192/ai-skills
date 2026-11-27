"""Phase C1 + E on the shared fixture (tests/fixtures_code.py): parser interface,
#include graph, KB -> code references, impact on code, issue / ID links, verify --links / status, writer lock."""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from support import SKILL
import fixtures_code as fx
from core import DEFAULTS, QError, Store, load_config
import engine
import ops
import parser_cpp
import parsers


class FixtureCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="qkb-c-engine-")
        cls.root = Path(cls.temp.name)
        fx.populate_code(cls.root)
        cls.store = Store(cls.root, load_config(cls.root), create=True)
        engine.update(cls.store)
        cls.links = engine.verify(cls.store, links=True)["links"]

    @classmethod
    def tearDownClass(cls):
        cls.store.db.close()
        cls.temp.cleanup()

    def node(self, label, type_):
        rows = self.store.rows("SELECT * FROM nodes WHERE label=? AND type=?", (label, type_))
        self.assertEqual(len(rows), 1, (label, type_, rows))
        return rows[0]

    def sections_citing(self, code_path):
        impact = engine.traverse(self.store, code_path, 1, "in", impact=True)
        return sorted(n["path"].split("/")[-1] + "#" + n["heading"] for n in impact["nodes"] if n["type"] == "SECTION")


class ParserTests(FixtureCase):
    def test_coverage_per_language(self):
        coverage = {r["path"]: json.loads(r["metadata"]) for r in self.store.rows("SELECT path, metadata FROM files WHERE category='code'")}
        self.assertEqual(coverage["src/app/tool.py"]["coverage"], "FULL")
        self.assertEqual(coverage["src/app/web/app.ts"]["coverage"], "FILE_ONLY")
        cpp = [p for p, m in coverage.items() if m["language"] == "cpp"]
        self.assertEqual(len(cpp), 10)
        self.assertTrue(all(coverage[p]["coverage"] == "PARTIAL" for p in cpp))
        self.assertEqual(self.links["parsers"]["languages"]["cpp"], {"files": 10, "FULL": 0, "PARTIAL": 10, "FILE_ONLY": 0})
        self.assertIn("parsers", engine.status(self.store))

    def test_interface_shape(self):
        for path, text in (("a.py", "def f():\n    pass\n"), ("a.cpp", "int main() { return 0; }\n"), ("a.ts", "export const x = 1;\n")):
            result = parsers.parse(path, text, {"source_paths": [], "include_paths": []})
            for key in ("language", "coverage", "parser", "symbols", "references", "meta"):
                self.assertIn(key, result)
            self.assertIn(result["coverage"], ("FULL", "PARTIAL", "FILE_ONLY"))

    def test_cpp_declarations_are_candidates(self):
        expected = {("src/app/core/engine.h", "app::Engine", "class", 20), ("src/app/core/engine.h", "app::Config", "struct", 9),
                    ("src/app/core/engine.h", "app::State", "enum", 7), ("src/app/core/engine.h", "app::Buffer", "class", 15),
                    ("src/app/core/engine.h", "app::computeScore", "declaration", 29),
                    ("src/app/core/engine.cpp", "app::computeScore", "function", 20),
                    ("src/app/inventory/stock.cpp", "Stock::setCount", "method", 8), ("src/app/main.cpp", "main", "function", 6),
                    ("src/app/core/util.h", "MAKE_ADDER", "macro", 10), ("src/app/legacy/old.c", "legacy_sum", "function", 7),
                    ("src/app/ui/mainwindow.h", "MainWindow", "class", 4)}
        rows = self.store.rows("SELECT path, label, start, status, metadata FROM nodes WHERE type='CODE_SYMBOL'")
        found = {(r["path"], r["label"], json.loads(r["metadata"]).get("kind"), r["start"]) for r in rows}
        self.assertLessEqual(expected, found)
        for r in rows:
            if r["path"].endswith((".cpp", ".h", ".c")):
                self.assertEqual(r["status"], "CANDIDATE")
                self.assertEqual(json.loads(r["metadata"])["coverage"], "PARTIAL")
        self.assertNotIn("addTwo", {r["label"].split("::")[-1] for r in rows})   # macro use is not a declaration
        python = {r["label"]: r["status"] for r in rows if r["path"].endswith(".py")}
        self.assertEqual(python, {"parse": "CONFIRMED", "Runner": "CONFIRMED", "Runner.run": "CONFIRMED"})

    def test_no_call_edges(self):
        relations = {r["relation"] for r in self.store.rows("SELECT DISTINCT relation FROM edges")}
        self.assertNotIn("CALLS", relations)
        self.assertEqual(self.store.rows("SELECT count(*) AS n FROM edges WHERE origin != 'EXTRACTED'")[0]["n"], 0)


class IncludeTests(FixtureCase):
    def edges_into(self, path):
        target = self.node(path, "CODE_FILE")["id"]
        sources = self.store.rows("SELECT n.path FROM edges e JOIN nodes n ON n.id = e.source "
                                  "WHERE e.relation='IMPORTS' AND e.target=?", (target,))
        return sorted(r["path"].replace("src/app/", "") for r in sources)

    def test_include_graph(self):
        report = self.links["includes"]
        self.assertEqual((report["sites"], report["resolved"], report["unresolved"]), (11, 10, 1))
        self.assertEqual(report["unresolved_items"], [{"path": "src/app/main.cpp", "line": 4, "written": "missing.h"}])
        self.assertEqual(self.edges_into("src/app/core/engine.h"), ["core/engine.cpp", "main.cpp", "ui/mainwindow.cpp"])
        self.assertEqual(self.edges_into("src/app/core/util.h"), ["core/engine.h", "inventory/stock.cpp"])
        self.assertEqual(self.edges_into("src/app/inventory/util.h"), ["inventory/stock.h"])   # same folder first
        system = sum(json.loads(r["metadata"]).get("system_includes", 0) for r in self.store.rows("SELECT metadata FROM files"))
        self.assertEqual(system, 5)
        for ignored in ("commented_line.h", "commented_block.h", "disabled.h"):
            self.assertEqual(self.store.rows("SELECT count(*) AS n FROM refs WHERE evidence LIKE ?", ("%" + ignored + "%",))[0]["n"], 0)

    def test_include_path_only_variant(self):
        with tempfile.TemporaryDirectory(prefix="qkb-c-incl-") as temp:
            root = Path(temp)
            fx.populate_code(root)
            cfg = json.loads((root / ".qkb/config.json").read_text(encoding="utf-8"))
            cfg["cpp_include_paths"] = []
            (root / ".qkb/config.json").write_text(json.dumps(cfg), encoding="utf-8")
            with Store(root, load_config(root), create=True) as store:
                engine.update(store)
                import reports
                report = reports.include_report(store)
            # Design order: including folder -> cpp_include_paths -> source_paths. The fixture's include path equals
            # its source root, so "core/engine.h" from ui/ still resolves through the source root (the other variant
            # assumed no source-root step).
            self.assertEqual((report["resolved"], report["unresolved"]), (10, 1))
        candidates = parser_cpp.include_candidates("src/app/ui/mainwindow.cpp", "core/engine.h",
                                                   {"include_paths": ["inc"], "source_paths": ["src/app"]})
        self.assertEqual(candidates, ["src/app/ui/core/engine.h", "inc/core/engine.h", "src/app/core/engine.h"])

    def test_impact_follows_includes(self):
        impact = engine.traverse(self.store, "src/app/inventory/util.h", 2, "in", impact=True)
        self.assertIn("src/app/inventory/stock.h", {n["path"] for n in impact["nodes"]})


class CodeLinkTests(FixtureCase):
    def test_reference_states(self):
        code = self.links["code"]
        by = code["by_resolution"]
        self.assertEqual(code["total"], 22)            # expected rows (design-en has 9)
        self.assertEqual((by["AMBIGUOUS"], by["NOT_FOUND"]), (2, 2))
        self.assertEqual(sum(v for k, v in by.items() if k not in ("AMBIGUOUS", "NOT_FOUND")), 18)
        self.assertEqual(code["lines_out_of_range"], 1)
        states = {(i["written"], i["state"]) for i in code["items"]}
        self.assertIn(("ui/mainwindow.cpp", "LINE_OUT_OF_RANGE"), states)
        self.assertEqual(self.links["references"], self.store.rows(
            "SELECT count(*) AS n FROM refs WHERE relation='REFERENCES' AND anchor NOT LIKE 'L%'")[0]["n"])

    def test_aliases(self):
        rows = {(r["written"], r["anchor"]): r["resolution"] for r in self.store.rows(
            "SELECT written, anchor, resolution FROM refs WHERE path='kb/demo/design-en.md' AND start=20")}
        self.assertEqual(rows, {("inventory/stock.h", "L1-3"): "source_root", ("core/engine.cpp", "L7"): "source_root"})
        alias_lines = self.store.rows("SELECT count(*) AS n FROM refs WHERE path='kb/demo/design-en.md' AND start IN (16, 17) "
                                      "AND relation='REFERENCES'")[0]["n"]
        self.assertEqual(alias_lines, 0)

    def test_impact_lists_citing_sections(self):
        self.assertEqual(self.sections_citing("src/app/core/engine.cpp"),
                         ["design-en.md#Alias use", "design-en.md#Overview", "open-points.md#Open points",
                          "sekkei-ja.md#OP-003 起動時の確認", "sekkei-ja.md#概要", "thiet-ke-vi.md#Mục còn mở",
                          "thiet-ke-vi.md#Tổng quan"])
        self.assertEqual(self.sections_citing("src/app/inventory/stock.cpp"),
                         ["design-en.md#Stock and window", "sekkei-ja.md#概要", "thiet-ke-vi.md#Mục còn mở", "thiet-ke-vi.md#Tổng quan"])
        self.assertEqual(self.sections_citing("src/app/inventory/util.h"), ["thiet-ke-vi.md#Hàm tiện ích"])
        self.assertEqual(self.sections_citing("src/app/core/util.h"), [])          # bare util.h is ambiguous
        self.assertEqual(self.sections_citing("src/app/tool.py"), [])

    def test_stale_and_out_of_range_after_code_change(self):
        with tempfile.TemporaryDirectory(prefix="qkb-c-stale-") as temp:
            root = Path(temp)
            fx.populate_code(root)
            with Store(root, load_config(root), create=True) as store:
                engine.update(store)
                path = root / "src/app/core/engine.cpp"
                original = path.read_text(encoding="utf-8")
                path.write_text("".join(original.splitlines(keepends=True)[:10]), encoding="utf-8")
                store.hash_cache.clear()
                code = engine.link_report(store, 100)["code"]
                states = {(i["path"], i["line"], i["written"], i["state"]) for i in code["items"]}
                self.assertIn(("kb/demo/design-en.md", 7, "engine.cpp", "LINE_OUT_OF_RANGE"), states)
                self.assertIn(("kb/demo/sekkei-ja.md", 7, "engine.cpp", "LINE_OUT_OF_RANGE"), states)
                self.assertIn(("kb/demo/open-points.md", 8, "engine.cpp", "STALE"), states)
                path.write_text(original, encoding="utf-8")
                store.hash_cache.clear()
                engine.update(store)
                after = engine.link_report(store, 100)["code"]
                self.assertEqual(after["lines_stale"], 0)


class IssueTests(FixtureCase):
    def test_issue_nodes(self):
        issues = {r["label"]: json.loads(r["metadata"]) for r in self.store.rows("SELECT label, metadata FROM nodes WHERE type='ISSUE'")}
        self.assertEqual(set(issues), {"OP-001", "OP-002", "OP-003", "C-01", "C-02"})
        self.assertEqual((issues["OP-001"]["status"], issues["OP-002"]["status"]), ("mở", "đã đóng"))
        self.assertEqual(issues["OP-001"]["source"], "REQ-010")
        self.assertEqual(self.node("REQ-010", "IDENTIFIER")["path"], "kb/demo/open-points.md")
        self.assertFalse(self.store.rows("SELECT * FROM nodes WHERE label IN ('OP-099','T-100')"))

    def test_affects_and_mentions(self):
        report = self.links["issues"]
        self.assertEqual((report["issues"], report["affects"], report["mentions"]), (5, 4, 4))
        self.assertEqual({i["id"] for i in report["undefined_ids"]["items"]}, {"OP-099", "T-100"})
        affects = {(self.store.rows("SELECT label FROM nodes WHERE id=?", (e["source"],))[0]["label"],
                    self.store.rows("SELECT path FROM nodes WHERE id=?", (e["target"],))[0]["path"])
                   for e in self.store.rows("SELECT source, target FROM edges WHERE relation='AFFECTS'")}
        self.assertEqual(affects, {("OP-001", "src/app/core/engine.cpp"), ("OP-001", "kb/demo/design-en.md"),
                                   ("OP-002", "src/app/inventory/stock.cpp"), ("C-02", "src/app/core/engine.cpp")})
        mention_refs = self.store.rows("SELECT written FROM refs WHERE relation='MENTIONS' AND path='kb/demo/sekkei-ja.md' AND start=11")
        self.assertEqual(sorted(r["written"] for r in mention_refs), ["OP-001", "OP-099", "T-100"])

    def test_impact_and_search_by_id(self):
        impact = engine.traverse(self.store, "src/app/inventory/stock.cpp", 1, "in", impact=True)
        self.assertIn("OP-002", {n["label"] for n in impact["nodes"] if n["type"] == "ISSUE"})
        hit = engine.search(self.store, "OP-001")["results"][0]
        self.assertEqual((hit["type"], hit["label"]), ("ISSUE", "OP-001"))
        related = engine.traverse(self.store, self.node("C-01", "ISSUE")["id"], 1, "in")
        self.assertEqual({n["path"] for n in related["nodes"] if n["type"] == "SECTION"},
                         {"kb/demo/design-en.md", "kb/demo/thiet-ke-vi.md", "kb/demo/open-points.md"})

    def test_no_patterns_no_ids(self):
        with tempfile.TemporaryDirectory(prefix="qkb-c-noid-") as temp:
            root = Path(temp)
            fx.populate_code(root)
            cfg = json.loads((root / ".qkb/config.json").read_text(encoding="utf-8"))
            cfg.update(issue_id_patterns=[], id_patterns={})
            (root / ".qkb/config.json").write_text(json.dumps(cfg), encoding="utf-8")
            with Store(root, load_config(root), create=True) as store:
                engine.update(store)
                self.assertFalse(store.rows("SELECT * FROM nodes WHERE type IN ('ISSUE','IDENTIFIER')"))
                self.assertFalse(store.rows("SELECT * FROM refs WHERE relation IN ('MENTIONS','AFFECTS')"))


class ConfigTests(unittest.TestCase):
    def test_defaults_hold_no_workspace_convention(self):
        for key in ("cpp_include_paths", "issue_id_patterns"):
            self.assertEqual(DEFAULTS[key], [])
        self.assertEqual((DEFAULTS["id_patterns"], DEFAULTS["code_aliases"]), ({}, {}))

    def test_invalid_values(self):
        with tempfile.TemporaryDirectory(prefix="qkb-c-cfg-") as temp:
            root = Path(temp)
            (root / ".qkb").mkdir()
            for bad in ({"issue_id_patterns": ["("]}, {"issue_id_patterns": ["x*"]}, {"id_patterns": {"req": "REQ"}},
                        {"code_aliases": {"A/": "b.cpp"}}, {"cpp_include_paths": ["../out"]}, {"issue_fields": {"status": "x"}}):
                with self.subTest(bad=bad):
                    (root / ".qkb/config.json").write_text(json.dumps({**DEFAULTS, **bad}), encoding="utf-8")
                    with self.assertRaises(QError):
                        load_config(root)

    def test_config_aliases(self):
        with tempfile.TemporaryDirectory(prefix="qkb-c-alias-") as temp:
            root = Path(temp)
            fx.populate_code(root)
            (root / "kb/demo/alias.md").write_text("# A\nSee `X/stock.cpp:1` and `mw.cpp`.\n", encoding="utf-8")
            cfg = json.loads((root / ".qkb/config.json").read_text(encoding="utf-8"))
            cfg["code_aliases"] = {"X/": "inventory/", "mw.cpp": "ui/mainwindow.cpp"}
            (root / ".qkb/config.json").write_text(json.dumps(cfg), encoding="utf-8")
            with Store(root, load_config(root), create=True) as store:
                engine.update(store)
                rows = {r["written"]: r["resolution"] for r in store.rows("SELECT written, resolution FROM refs WHERE path='kb/demo/alias.md'")}
            self.assertEqual(rows, {"inventory/stock.cpp": "source_root", "ui/mainwindow.cpp": "source_root"})


class CrossProjectTests(unittest.TestCase):
    """A bare code name never links to code of another project; code_aliases can still name it."""

    def build(self, aliases=None):
        temp = tempfile.TemporaryDirectory(prefix="qkb-c-xproj-")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        files = {"kb/alpha/main/a.md": "# A\nSee `foo.cpp:1` and `bar.cpp`.\n",
                 "projects/beta/main/src/foo.cpp": "int foo() { return 1; }\n",
                 "projects/alpha/main/src/bar.cpp": "int bar() { return 2; }\n"}
        for path, text in files.items():
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_text(text, encoding="utf-8")
        cfg = {**DEFAULTS, "knowledge_paths": ["kb"], "source_paths": ["projects"], "project_roots": ["kb", "projects"],
               "code_aliases": aliases or {}}
        (root / ".qkb").mkdir()
        (root / ".qkb/config.json").write_text(json.dumps(cfg), encoding="utf-8")
        store = Store(root, load_config(root), create=True)
        self.addCleanup(store.db.close)
        engine.update(store)
        linked = {r["path"] for r in store.rows("SELECT n.path FROM edges e JOIN nodes n ON n.id = e.target "
                                                "WHERE e.relation='REFERENCES' AND n.type='CODE_FILE'")}
        return {r["written"]: r["resolution"] for r in store.rows("SELECT * FROM refs WHERE relation='REFERENCES'")}, linked

    def test_other_project_code_not_linked(self):
        refs, linked = self.build()
        self.assertEqual(refs["foo.cpp"], "NOT_FOUND")                        # only in project beta
        self.assertEqual(refs["bar.cpp"], "unique_name")                      # same project (alpha)
        self.assertEqual(linked, {"projects/alpha/main/src/bar.cpp"})

    def test_alias_names_other_project_code(self):
        refs, linked = self.build({"foo.cpp": "projects/beta/main/src/foo.cpp"})
        self.assertEqual(refs["projects/beta/main/src/foo.cpp"], "root")
        self.assertIn("projects/beta/main/src/foo.cpp", linked)


class NodeNameTests(FixtureCase):
    """Impact / related accept a unique file name or path tail."""

    def test_unique_tail(self):
        by_name = engine.traverse(self.store, "stock.cpp", 1, "in", impact=True)
        by_path = engine.traverse(self.store, "src/app/inventory/stock.cpp", 1, "in", impact=True)
        self.assertEqual({n["id"] for n in by_name["nodes"]}, {n["id"] for n in by_path["nodes"]})
        self.assertTrue(engine.traverse(self.store, "core/engine.cpp", 1, "in", impact=True)["nodes"])
        with self.assertRaises(QError):
            engine.traverse(self.store, "util.h", 1, "in", impact=True)        # two files
        with self.assertRaises(QError):
            engine.traverse(self.store, "nothing.cpp", 1, "in", impact=True)


class AliasChainTests(unittest.TestCase):
    def test_chained_and_cyclic_aliases(self):
        import codelinks
        dirs = {"LB/": "S/lib/", "S/": "src/"}
        self.assertEqual(codelinks.expand_aliases("LB/m.cpp", {}, dirs)[0], "src/lib/m.cpp")
        self.assertEqual(codelinks.expand_aliases("x.cpp", {"x.cpp": "S/x.cpp"}, dirs)[0], "src/x.cpp")
        cyclic = codelinks.expand_aliases("a/x.cpp", {}, {"a/": "b/", "b/": "a/"})
        self.assertEqual(set(cyclic), {"a/x.cpp", "b/x.cpp"})          # stops, no endless loop


class CppParserUnitTests(unittest.TestCase):
    def test_blank_keeps_lines_and_ignores_literals(self):
        text = 'a; // c "x"\n/* b\n c */ s = "{ // }"; ch = \'}\';\n'
        out = parser_cpp.blank(text)
        self.assertEqual(out.count("\n"), text.count("\n"))
        self.assertNotIn("//", out)
        self.assertEqual(out.count("{"), 0)

    def test_if_zero_else_branch(self):
        src = '#if 0\n#include "a.h"\n#else\n#include "b.h"\n#endif\n#ifdef X\n#include "c.h"\n#endif\n'
        refs = parser_cpp.parse("x.cpp", src, {"source_paths": [], "include_paths": []})["references"]
        self.assertEqual([r["written"] for r in refs], ["b.h", "c.h"])


class WriterLockTests(unittest.TestCase):
    def test_stale_takeover_is_atomic(self):
        with tempfile.TemporaryDirectory(prefix="qkb-c-lock-") as temp:
            root = Path(temp)
            (root / ".qkb/cache").mkdir(parents=True)
            for _ in range(5):
                lock = root / ".qkb/cache/writer.lock"
                lock.write_text("{}", encoding="utf-8")
                old = time.time() - 3600
                os.utime(lock, (old, old))
                holders, errors, gate = [], [], threading.Barrier(6)

                def take():
                    gate.wait()
                    try:
                        held = ops.WriterLock(root).__enter__()
                        holders.append(held)
                    except QError as exc:
                        errors.append(exc)
                threads = [threading.Thread(target=take) for _ in range(6)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()
                self.assertEqual(len(holders), 1, (len(holders), errors))
                self.assertEqual(len(errors), 5)
                holders[0].__exit__(None, None, None)
                self.assertFalse(lock.exists())
                self.assertFalse(list((root / ".qkb/cache").glob("writer.lock.stale-*")))


class CliTests(FixtureCase):
    def test_cli_verify_links_and_status(self):
        def run(*args):
            proc = subprocess.run([sys.executable, "-s", str(SKILL / "scripts/qkb.py"), "--root", str(self.root), *args,
                                   "--format", "json", "--max-chars", "200000"], text=True, encoding="utf-8",
                                  capture_output=True, timeout=90)
            return proc.returncode, json.loads(proc.stdout)
        code, data = run("verify", "--links")
        self.assertIn(code, (0, 1))
        for key in ("code", "includes", "issues", "parsers"):
            self.assertIn(key, data["links"])
        code, data = run("status", "--quick")
        self.assertEqual(code, 0, data)
        self.assertIn("cpp", data["parsers"]["languages"])
        code, data = run("impact", "src/app/core/engine.cpp")
        self.assertEqual(code, 0, data)
        self.assertTrue(any(n["type"] == "SECTION" for n in data["nodes"]))


if __name__ == "__main__":
    unittest.main()
