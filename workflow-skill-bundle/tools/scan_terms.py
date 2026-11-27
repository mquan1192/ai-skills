#!/usr/bin/env python3
"""scan_terms.py - find project-specific words in a folder or a .zip before it is shared.

Usage:
    python scan_terms.py <folder or .zip> --terms <list.txt> [--exclude <glob> ...]

Output: one line per hit, ``<file>:<line>: <term>``; a hit in a file or folder NAME prints
``<path>:0: <term> [name]``; a hit inside a .zip prints ``<archive>!<inner path>:<line>: <term>``.
The last line is a summary. Exit code: 0 = no hit, 1 = at least one hit, 2 = usage error.

Term list (UTF-8, BOM ok): one term per line; empty lines and lines starting with ``#`` are ignored.
A plain term is matched anywhere, case-insensitively (so ``JOB-2026`` also finds ``JOB-20260105-01``).
A term that starts with ``=`` is matched as a whole word only (``=abc`` finds ``abc`` but not ``abcd``).
Vietnamese text is compared after Unicode NFC normalisation.

Built-in patterns, always on (the matched value is never printed, only its label):
    <session-id>  the word ``local``, an underscore and a UUID (a session identifier)
    <abs-path>    an absolute path: a drive letter with a backslash, or a Unix home folder
    <email>       an e-mail address

The bundle ships no project word list: write your own list next to the folder you check and keep it out of the bundle.
Standard library only (Python 3.8+).
"""
from __future__ import annotations

import argparse
import fnmatch
import io
import os
import re
import sys
import unicodedata
import zipfile

ARCHIVE_SUFFIXES = (".zip", ".docx", ".xlsx", ".pptx")
MAX_ARCHIVE_DEPTH = 3
BUILTIN = [
    ("<session-id>", re.compile("local" + "_" + r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")),
    ("<abs-path>", re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:\\|(?<![\w.])/(?:Users|home)/")),
    ("<email>", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")),
]


def nfc(text):
    return unicodedata.normalize("NFC", text)


def load_terms(path):
    """Return a list of (label, compiled regex) from the term list file."""
    with open(path, "rb") as handle:
        text = handle.read().decode("utf-8-sig", errors="replace")
    terms = []
    for raw in text.splitlines():
        line = nfc(raw.strip())
        if not line or line.startswith("#"):
            continue
        whole = line.startswith("=")
        word = line[1:].strip() if whole else line
        if not word:
            continue
        pattern = re.escape(word)
        if whole:
            pattern = r"(?<!\w)" + pattern + r"(?!\w)"
        terms.append((word, re.compile(pattern, re.IGNORECASE)))
    return terms


def match_labels(text, matchers):
    """Labels of every matcher that finds something in text (each label once)."""
    text = nfc(text)
    return [label for label, rx in matchers if rx.search(text)]


class Scanner:
    def __init__(self, matchers, excludes, skip_paths):
        self.matchers = matchers
        self.excludes = excludes
        self.skip_paths = skip_paths
        self.hits = 0
        self.files_with_hits = set()
        self.files_scanned = 0

    def report(self, shown, line, label, is_name=False):
        self.hits += 1
        self.files_with_hits.add(shown)
        suffix = " [name]" if is_name else ""
        print("%s:%d: %s%s" % (shown, line, label, suffix))

    def check_name(self, shown, name):
        for label in match_labels(name, self.matchers):
            self.report(shown, 0, label, is_name=True)

    def check_text(self, shown, data):
        if b"\x00" in data[:8192]:
            return  # binary: only its name is checked
        text = data.decode("utf-8-sig", errors="replace")
        for number, line in enumerate(text.splitlines(), 1):
            for label in match_labels(line, self.matchers):
                self.report(shown, number, label)

    def scan_archive(self, shown, data, depth):
        try:
            archive = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile:
            self.check_text(shown, data)
            return
        with archive:
            for info in archive.infolist():
                inner = "%s!%s" % (shown, info.filename)
                self.check_name(inner, info.filename.rstrip("/"))
                if info.is_dir():
                    continue
                payload = archive.read(info)
                if info.filename.lower().endswith(ARCHIVE_SUFFIXES) and depth < MAX_ARCHIVE_DEPTH:
                    self.scan_archive(inner, payload, depth + 1)
                else:
                    self.files_scanned += 1
                    self.check_text(inner, payload)

    def scan_file(self, path, shown):
        name = os.path.basename(path)
        if any(fnmatch.fnmatch(name, pattern) for pattern in self.excludes):
            return
        if os.path.abspath(path) in self.skip_paths:
            return
        self.check_name(shown, name)
        with open(path, "rb") as handle:
            data = handle.read()
        if name.lower().endswith(ARCHIVE_SUFFIXES):
            self.scan_archive(shown, data, 1)
        else:
            self.files_scanned += 1
            self.check_text(shown, data)

    def scan(self, target):
        if os.path.isdir(target):
            root = os.path.abspath(target)
            base = os.path.dirname(root)
            for current, dirs, files in os.walk(root):
                dirs.sort()
                for directory in dirs:
                    full = os.path.join(current, directory)
                    self.check_name(os.path.relpath(full, base).replace(os.sep, "/"), directory)
                for filename in sorted(files):
                    full = os.path.join(current, filename)
                    self.scan_file(full, os.path.relpath(full, base).replace(os.sep, "/"))
        else:
            self.scan_file(target, os.path.basename(target))


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Find project-specific words before a folder or .zip is shared.")
    parser.add_argument("target", help="folder or .zip to scan")
    parser.add_argument("--terms", required=True, help="term list file (one term per line)")
    parser.add_argument("--exclude", action="append", default=[], help="file name pattern to skip (repeatable)")
    args = parser.parse_args(argv)
    if not os.path.exists(args.target):
        print("scan_terms: target not found", file=sys.stderr)
        return 2
    try:
        terms = load_terms(args.terms)
    except OSError:
        print("scan_terms: cannot read the term list", file=sys.stderr)
        return 2
    matchers = terms + BUILTIN
    scanner = Scanner(matchers, args.exclude, {os.path.abspath(args.terms)})
    scanner.scan(args.target)
    print("scan_terms: %d hit(s) in %d file(s); %d file(s) scanned; %d listed term(s) + %d built-in"
          % (scanner.hits, len(scanner.files_with_hits), scanner.files_scanned, len(terms), len(BUILTIN)))
    return 1 if scanner.hits else 0


if __name__ == "__main__":
    sys.exit(main())
