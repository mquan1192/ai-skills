import json
import os
import sqlite3
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
# own scripts first; the skill scripts (core.py) after them (env QKB_SKILL_SCRIPTS, else the same folder once wired in)
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "scripts")))
if os.environ.get("QKB_SKILL_SCRIPTS"):
    sys.path.append(os.environ["QKB_SKILL_SCRIPTS"])

import reports  # noqa: E402

DDL = """
CREATE TABLE files(path TEXT PRIMARY KEY, hash TEXT, bytes INTEGER, category TEXT, metadata TEXT, indexed_at TEXT);
CREATE TABLE nodes(id TEXT PRIMARY KEY, type TEXT, label TEXT, path TEXT, start INTEGER, end INTEGER,
 heading TEXT, status TEXT, hash TEXT, metadata TEXT);
CREATE TABLE edges(id TEXT PRIMARY KEY, source TEXT, target TEXT, relation TEXT, origin TEXT, path TEXT, start INTEGER);
CREATE TABLE refs(id TEXT PRIMARY KEY, source TEXT, path TEXT, target_path TEXT, anchor TEXT, relation TEXT,
 start INTEGER, end INTEGER, evidence TEXT, hash TEXT, written TEXT, resolution TEXT, candidates TEXT);
CREATE TABLE code_spans(ref_id TEXT, source_path TEXT, target_path TEXT, start INTEGER, end INTEGER, target_hash TEXT);
"""


class FakeScope:
    def __init__(self, files):
        self.files = files  # path -> (text, hash)
        self.reads = []

    def read(self, path):
        self.reads.append(path)
        if path not in self.files:
            raise OSError("missing")
        text, hash_ = self.files[path]
        return text, hash_, len(text)


class FakeStore:
    def __init__(self, folder, files=None):
        self.db = sqlite3.connect(os.path.join(folder, "t.sqlite"))
        self.db.row_factory = sqlite3.Row
        self.db.executescript(DDL)
        self.scope = FakeScope(files or {})

    def rows(self, sql, params=()):
        return [dict(r) for r in self.db.execute(sql, params)]

    def add(self, table, **values):
        cols = ",".join(values)
        self.db.execute("INSERT INTO %s(%s) VALUES (%s)" % (table, cols, ",".join("?" * len(values))),
                        tuple(values.values()))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = FakeStore(self.tmp.name, {
            "src/a.cpp": ("\n".join("l%d" % i for i in range(1, 21)), "H_A"),   # 20 lines, unchanged
            "src/b.cpp": ("x\ny\nz", "H_B_NEW"),                                 # 3 lines, changed
        })

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()


class CoverageTests(Base):
    def test_languages_and_symbols(self):
        s = self.store
        s.add("files", path="src/a.cpp", category="code", metadata=json.dumps({"language": "cpp", "coverage": "PARTIAL"}))
        s.add("files", path="src/b.cpp", category="code", metadata=json.dumps({"language": "cpp", "coverage": "FILE_ONLY"}))
        s.add("files", path="t.py", category="code", metadata=json.dumps({"language": "python", "coverage": "FULL"}))
        s.add("files", path="x.qml", category="code", metadata="{}")
        s.add("files", path="kb/n.md", category="markdown", metadata="{}")
        for i in range(3):
            s.add("nodes", id="s%d" % i, type="CODE_SYMBOL", label="f%d" % i, path="t.py", metadata="{}")
        s.add("nodes", id="f", type="CODE_FILE", label="t.py", path="t.py", metadata="{}")
        r = reports.parser_coverage(s)
        self.assertEqual(r["symbols"], 3)
        self.assertEqual(r["languages"]["cpp"], {"files": 2, "FULL": 0, "PARTIAL": 1, "FILE_ONLY": 1})
        self.assertEqual(r["languages"]["python"]["FULL"], 1)
        self.assertEqual(r["languages"]["other"]["files"], 1)
        self.assertNotIn("markdown", r["languages"])


class CodeLinkTests(Base):
    def fill(self):
        s = self.store
        s.add("files", path="src/a.cpp", category="code", metadata="{}")
        s.add("files", path="src/b.cpp", category="code", metadata="{}")
        s.add("files", path="src/gone.cpp", category="code", metadata="{}")
        rows = [
            # id, kb line, written, target, anchor, resolution, span
            ("r1", 1, "a.cpp:2-4", "src/a.cpp", "L2-4", "RESOLVED", (2, 4, "H_A")),        # current
            ("r2", 2, "a.cpp:19-25", "src/a.cpp", "L19-25", "RESOLVED", (19, 25, "H_A")),  # out of range
            ("r3", 3, "b.cpp:1", "src/b.cpp", "L1", "RESOLVED", (1, 1, "H_B_OLD")),       # stale
            ("r4", 4, "gone.cpp:1", "src/gone.cpp", "L1", "RESOLVED", (1, 1, "H_G")),      # unreadable
            ("r5", 5, "nowhere.h:3", None, "L3", "NOT_FOUND", None),                      # with lines, no span
            ("r6", 6, "a.cpp", "src/a.cpp", "", "RESOLVED", None),                         # no lines
            ("r7", 7, "other.md", "kb/other.md", "", "RESOLVED", None),                    # not code
        ]
        for id_, line, written, target, anchor, res, span in rows:
            s.add("refs", id=id_, path="kb/p.md", start=line, written=written, target_path=target,
                  anchor=anchor, relation="REFERENCES", resolution=res)
            if span:
                s.add("code_spans", ref_id=id_, source_path="kb/p.md", target_path=target,
                      start=span[0], end=span[1], target_hash=span[2])
        s.add("refs", id="i1", path="src/a.cpp", start=1, written="b.h", relation="IMPORTS", evidence="#include")

    def test_counts(self):
        self.fill()
        r = reports.code_link_report(self.store)
        self.assertEqual(r["total"], 6)
        self.assertEqual(r["by_resolution"], {"NOT_FOUND": 1, "RESOLVED": 5})
        self.assertEqual(r["with_lines"], 5)
        self.assertEqual((r["lines_current"], r["lines_stale"], r["lines_out_of_range"], r["missing"],
                          r["lines_unresolved"]), (1, 1, 1, 1, 1))
        self.assertEqual([i["state"] for i in r["items"]],
                         ["LINE_OUT_OF_RANGE", "STALE", "MISSING", "UNRESOLVED"])
        self.assertEqual(r["items"][0], {"path": "kb/p.md", "line": 2, "written": "a.cpp:19-25",
                                         "state": "LINE_OUT_OF_RANGE"})

    def test_top_cap_and_single_read_per_file(self):
        self.fill()
        r = reports.code_link_report(self.store, top=2)
        self.assertEqual(len(r["items"]), 2)
        self.assertEqual(r["items_total"], 4)
        self.assertEqual(self.store.scope.reads.count("src/a.cpp"), 1)

    def test_without_code_spans_table(self):
        self.store.db.execute("DROP TABLE code_spans")
        self.store.add("refs", id="r1", path="kb/p.md", start=1, written="a.cpp:2", target_path="src/a.cpp",
                       anchor="L2", relation="REFERENCES", resolution="RESOLVED")
        r = reports.code_link_report(self.store)
        self.assertEqual((r["with_lines"], r["lines_unresolved"]), (1, 1))


class IncludeTests(Base):
    def test_sites(self):
        s = self.store
        # One row per candidate path; a site is resolved when an IMPORTS edge exists for its file + line.
        s.add("refs", id="i1", path="a.cpp", start=1, written="b.h", target_path="b.h", relation="IMPORTS",
              evidence='#include "b.h"')
        s.add("refs", id="i2", path="a.cpp", start=1, written="b.h", target_path="inc/b.h", relation="IMPORTS",
              evidence='#include "b.h"')
        s.add("edges", id="ie1", source="a", target="b", relation="IMPORTS", origin="x", path="a.cpp", start=1)
        for n in range(3):
            s.add("refs", id="u%d" % n, path="a.cpp", start=2 + n, written="x%d.h" % n, target_path="x%d.h" % n,
                  relation="IMPORTS", evidence='  #include "x%d.h"' % n)
        s.add("refs", id="p1", path="m.py", start=1, written="os", relation="IMPORTS", evidence="import os")
        r = reports.include_report(s, top=2)
        self.assertEqual((r["sites"], r["resolved"], r["unresolved"]), (4, 1, 3))
        self.assertEqual(r["unresolved_items"], [{"path": "a.cpp", "line": 2, "written": "x0.h"},
                                                 {"path": "a.cpp", "line": 3, "written": "x1.h"}])


class IssueTests(Base):
    def test_issues(self):
        s = self.store
        s.add("nodes", id="n1", type="ISSUE", label="OP-1", path="kb/i.md", metadata=json.dumps({"status": "OPEN"}))
        s.add("nodes", id="n2", type="ISSUE", label="OP-2", path="kb/i.md", metadata=json.dumps({"status": "CLOSED"}))
        s.add("nodes", id="n3", type="ISSUE", label="OP-3", path="kb/i.md", metadata="{}")
        s.add("edges", id="e1", source="n1", target="f", relation="AFFECTS", origin="x", path="kb/i.md")
        for n in range(3):
            s.add("edges", id="m%d" % n, source="s", target="n1", relation="MENTIONS", origin="x", path="kb/a.md")
        s.add("refs", id="k1", path="kb/a.md", start=5, written="OP-1", relation="MENTIONS")
        s.add("refs", id="k2", path="kb/a.md", start=6, written="OP-9", relation="MENTIONS")
        s.add("refs", id="k3", path="kb/b.md", start=1, written="OP-9", relation="MENTIONS")
        s.add("refs", id="k4", path="kb/b.md", start=2, written="OP-7", relation="MENTIONS")
        r = reports.issue_report(s, top=1)
        self.assertEqual(r["issues"], 3)
        self.assertEqual(r["by_status"], {"CLOSED": 1, "OPEN": 1, "UNKNOWN": 1})
        self.assertEqual((r["affects"], r["mentions"]), (1, 3))
        self.assertEqual(r["undefined_ids"]["count"], 2)
        self.assertEqual(r["undefined_ids"]["items"], [{"id": "OP-9", "mentions": 2, "path": "kb/a.md", "line": 6}])


if __name__ == "__main__":
    unittest.main()
