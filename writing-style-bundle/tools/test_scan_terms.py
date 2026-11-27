"""Tests for scan_terms.py (standard library only). Run: python -m unittest test_scan_terms -v

Invented words only; values that the scanner treats as sensitive are built at run time, so this file stays clean.
"""
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest
import uuid
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scan_terms  # noqa: E402

SCRIPT = os.path.join(HERE, "scan_terms.py")


class ScanTermsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="scan-terms-test-")
        self.root = os.path.join(self.tmp, "bundle")
        os.makedirs(self.root)
        self.terms = os.path.join(self.tmp, "terms.txt")
        self.write_terms("Zebrafish\n# comment\n\n=tom\nTang 9\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_terms(self, text):
        with open(self.terms, "w", encoding="utf-8") as handle:
            handle.write(text)

    def write(self, rel, text, encoding="utf-8"):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(text.encode(encoding))
        return path

    def run_scan(self, target):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = scan_terms.main([target, "--terms", self.terms])
        return code, out.getvalue()

    def test_hit_in_text_with_line_number(self):
        self.write("a/notes.md", "first line\nsecond ZEBRAFISH line\n")
        code, out = self.run_scan(self.root)
        self.assertEqual(code, 1)
        self.assertIn("bundle/a/notes.md:2: Zebrafish", out)

    def test_hit_in_file_name_and_folder_name(self):
        self.write("zebrafish-docs/readme.md", "clean text\n")
        self.write("plain/zebrafish_notes.md", "clean text\n")
        code, out = self.run_scan(self.root)
        self.assertEqual(code, 1)
        self.assertIn("bundle/zebrafish-docs:0: Zebrafish [name]", out)
        self.assertIn("bundle/plain/zebrafish_notes.md:0: Zebrafish [name]", out)

    def test_hit_inside_zip_text_and_inner_name(self):
        path = os.path.join(self.root, "pack.zip")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("inner/readme.md", "line one\nmentions zebrafish here\n")
            archive.writestr("inner/zebrafish.txt", "clean")
        code, out = self.run_scan(path)
        self.assertEqual(code, 1)
        self.assertIn("pack.zip!inner/readme.md:2: Zebrafish", out)
        self.assertIn("pack.zip!inner/zebrafish.txt:0: Zebrafish [name]", out)

    def test_zip_inside_folder_and_nested_zip(self):
        inner = io.BytesIO()
        with zipfile.ZipFile(inner, "w") as archive:
            archive.writestr("deep.md", "zebrafish\n")
        with zipfile.ZipFile(os.path.join(self.root, "outer.zip"), "w") as archive:
            archive.writestr("inner.zip", inner.getvalue())
        code, out = self.run_scan(self.root)
        self.assertEqual(code, 1)
        self.assertIn("outer.zip!inner.zip!deep.md:1: Zebrafish", out)

    def test_clean_folder_exit_zero(self):
        self.write("a/notes.md", "nothing special here\nplain Vietnamese: Xin chào\n")
        code, out = self.run_scan(self.root)
        self.assertEqual(code, 0)
        self.assertIn("0 hit(s)", out)

    def test_whole_word_term(self):
        self.write("a/words.md", "a tomato salad\nthe tom said hi\n")
        code, out = self.run_scan(self.root)
        self.assertEqual(code, 1)
        self.assertIn("words.md:2: tom", out)
        self.assertNotIn("words.md:1:", out)

    def test_plain_term_matches_prefix_of_longer_id(self):
        self.write_terms("JOB-2026\n")
        self.write("a/ids.md", "see JOB-20260105-01 for details\n")
        code, out = self.run_scan(self.root)
        self.assertEqual(code, 1)
        self.assertIn("ids.md:1: JOB-2026", out)

    def test_bom_and_nfd_text(self):
        self.write("a/bom.md", "﻿header\nTang 9 appears\n", encoding="utf-8")
        decomposed = unicodedata.normalize("NFD", "Tầng 9")
        self.write_terms("Tầng 9\n")
        self.write("a/nfd.md", "line\n" + decomposed + " appears\n")
        self.write("a/plain.md", "just text\n")
        code, out = self.run_scan(self.root)
        self.assertEqual(code, 1)
        self.assertIn("nfd.md:2: Tầng 9", out)
        self.assertNotIn("bom.md:2:", out)  # "Tang 9" without diacritics is a different term here

    def test_builtin_patterns_do_not_print_the_value(self):
        session = "local" + "_" + str(uuid.uuid4())
        drive_path = "C" + ":" + "\\" + "work" + "\\" + "file.txt"
        home_path = "/" + "home" + "/someone/project"
        address = "someone" + "@" + "example.org"
        self.write("a/builtin.md", "id %s\npath %s\nunix %s\nmail %s\n" % (session, drive_path, home_path, address))
        code, out = self.run_scan(self.root)
        self.assertEqual(code, 1)
        for label in ("<session-id>", "<abs-path>", "<email>"):
            self.assertIn(label, out)
        for value in (session, "someone", "example.org", "work"):
            self.assertNotIn(value, out)

    def test_binary_file_only_name_is_checked(self):
        path = os.path.join(self.root, "image.bin")
        with open(path, "wb") as handle:
            handle.write(b"\x00\x01zebrafish\x00")
        code, out = self.run_scan(self.root)
        self.assertEqual(code, 0)

    def test_terms_file_inside_folder_is_skipped(self):
        inside = os.path.join(self.root, "terms.local.txt")
        shutil.copy(self.terms, inside)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = scan_terms.main([self.root, "--terms", inside])
        self.assertEqual(code, 0)

    def test_exit_code_two_for_missing_target_and_list(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(scan_terms.main([os.path.join(self.tmp, "missing"), "--terms", self.terms]), 2)
            self.assertEqual(scan_terms.main([self.root, "--terms", os.path.join(self.tmp, "missing.txt")]), 2)

    def test_command_line_exit_codes(self):
        self.write("a/notes.md", "zebrafish\n")
        hit = subprocess.run([sys.executable, "-I", "-B", SCRIPT, self.root, "--terms", self.terms],
                             capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(hit.returncode, 1)
        self.assertIn("notes.md:1: Zebrafish", hit.stdout)
        os.remove(os.path.join(self.root, "a", "notes.md"))
        clean = subprocess.run([sys.executable, "-I", "-B", SCRIPT, self.root, "--terms", self.terms],
                               capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(clean.returncode, 0)


if __name__ == "__main__":
    unittest.main()
