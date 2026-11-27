import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
# own scripts first; the skill scripts (core.py) after them (env QKB_SKILL_SCRIPTS, else the same folder once wired in)
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "scripts")))
if os.environ.get("QKB_SKILL_SCRIPTS"):
    sys.path.append(os.environ["QKB_SKILL_SCRIPTS"])

import codelinks as cl  # noqa: E402
import core  # noqa: E402


class SuffixTests(unittest.TestCase):
    def test_suffixes_extend_core(self):
        for ext in core.CODE_EXT:
            self.assertIn(ext, cl.CODE_SUFFIXES)
        for ext in (".hpp", ".hh", ".hxx", ".cc", ".cxx", ".inl", ".ui", ".qml"):
            self.assertIn(ext, cl.CODE_SUFFIXES)

    def test_case_insensitive(self):
        self.assertTrue(cl.is_code_path("Dir/Main.CPP"))
        self.assertFalse(cl.is_code_path("notes.md"))


class CodeRefsTests(unittest.TestCase):
    def test_plain_path(self):
        self.assertEqual(cl.code_refs("see `dir/a.cpp` here"),
                         [{"written": "dir/a.cpp", "start": None, "end": None, "column": 4}])

    def test_single_line(self):
        r = cl.code_refs("`a.h:7`")
        self.assertEqual((r[0]["start"], r[0]["end"]), (7, 7))

    def test_range_and_extra_spans(self):
        r = cl.code_refs("x `a.cpp:10-12, 40-45` y")
        self.assertEqual([(x["start"], x["end"]) for x in r], [(10, 12), (40, 45)])
        self.assertTrue(all(x["column"] == 2 and x["written"] == "a.cpp" for x in r))

    def test_reversed_span_skipped_others_kept(self):
        r = cl.code_refs("`a.cpp:12-10, 20`")
        self.assertEqual([(x["start"], x["end"]) for x in r], [(20, 20)])

    def test_backslash_and_case(self):
        r = cl.code_refs(r"`Dev\Stage.HPP:3`")
        self.assertEqual(r[0]["written"], r"Dev\Stage.HPP")

    def test_rejects(self):
        for text in ("`a.md:3`", "`a b.cpp`", "`*.cpp`", "`a.cpp:x`", "`<a.cpp>`", "a.cpp:3",
                     "`http://x/a.py`", "`a.cpp:3-`", "`{a}.cpp`"):
            self.assertEqual(cl.code_refs(text), [], text)

    def test_several_backticks(self):
        r = cl.code_refs("`a.py:1` and `b/c.ts:2-3`")
        self.assertEqual([x["written"] for x in r], ["a.py", "b/c.ts"])
        self.assertEqual(r[1]["column"], 13)


class AliasTests(unittest.TestCase):
    def test_forms(self):
        line = "`S/` = `src/stage/`; `w.cpp` → `threads/worker.cpp`, `M/` => `mod/`"
        self.assertEqual(cl.alias_declarations(line),
                         [("S/", "src/stage/"), ("w.cpp", "threads/worker.cpp"), ("M/", "mod/")])

    def test_invalid_pairs(self):
        for line in ("`S/` = `a.cpp`", "`a.cpp` = `b/`", "`x` = `y`", "`a.md` = `b.md`", "`a b/` = `c/`"):
            self.assertEqual(cl.alias_declarations(line), [], line)

    def test_backslash_normalised(self):
        self.assertEqual(cl.alias_declarations(r"`S\` = `src\stage\`"), [("S/", "src/stage/")])


class ExpandTests(unittest.TestCase):
    def test_order_and_longest_prefix(self):
        files = {"w.cpp": "threads/worker.cpp"}
        dirs = {"S/": "src/", "S/sub/": "deep/"}
        self.assertEqual(cl.expand_aliases("w.cpp", files, dirs), ["threads/worker.cpp", "w.cpp"])
        self.assertEqual(cl.expand_aliases(r"S\sub\a.cpp", files, dirs), ["deep/a.cpp", "S/sub/a.cpp"])
        self.assertEqual(cl.expand_aliases("other.cpp", files, dirs), ["other.cpp"])

    def test_no_duplicates(self):
        self.assertEqual(cl.expand_aliases("a.cpp", {"a.cpp": "a.cpp"}, {}), ["a.cpp"])

    def test_empty_maps(self):
        self.assertEqual(cl.expand_aliases("a.cpp", None, None), ["a.cpp"])


class LineStateTests(unittest.TestCase):
    def test_states(self):
        self.assertEqual(cl.line_state(10, None, None), "NO_LINES")
        self.assertEqual(cl.line_state(10, 1, 10), "OK")
        self.assertEqual(cl.line_state(10, 5, None), "OK")
        self.assertEqual(cl.line_state(10, 9, 11), "LINE_OUT_OF_RANGE")
        self.assertEqual(cl.line_state(10, 0, 2), "LINE_OUT_OF_RANGE")
        self.assertEqual(cl.line_state(0, 1, 1), "LINE_OUT_OF_RANGE")


if __name__ == "__main__":
    unittest.main()
