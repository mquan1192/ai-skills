"""Structural tests of the KB skill bundle . Stdlib only; temp folders only.

Run from the bundle folder:  python -E -s -B -m unittest discover -s tests -p "test_*.py"
Engine for the scaffold test: env QKB_ENGINE = path of qkb.py (default: the 2.1 copy next to this bundle when present).
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

BUNDLE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
GENERIC = ("skills", "hooks", "templates", "scripts", "tools", "README_VN.md", "install.py", "CHANGELOG.md", "SECURITY.md")
SKILLS = ("q-kb-search", "q-kb-request", "q-kb-sync", "q-kb-add", "q-kb-publish")
DEFAULT_ENGINE = os.path.join(BUNDLE, "engine", ".claude", "skills", "q-knowledgebase", "scripts", "qkb.py")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import localcfg  # noqa: E402

# One project's own config / alias skills stay outside the generic package; checked only when the local test file names them.
WORKSPACE = localcfg.LOCAL.get("workspace_files")
MANAGER_SKILLS = ("q-kb-sync", "q-kb-add", "q-kb-publish")


def alias_skills():
    """SKILL.md files of the local project's alias skills (folders holding SKILL.md under workspace_files)."""
    if not WORKSPACE or not os.path.isdir(WORKSPACE):
        return []
    return sorted(os.path.join(WORKSPACE, d, "SKILL.md") for d in os.listdir(WORKSPACE)
                  if os.path.isfile(os.path.join(WORKSPACE, d, "SKILL.md")))


def skill_dir(name):
    return os.path.join(BUNDLE, "skills", name)

VI_CHARS = re.compile(r"[ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]", re.I)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip().strip('"')
    return out


def generic_files():
    for top in GENERIC:
        if os.path.isfile(os.path.join(BUNDLE, top)):
            yield os.path.join(BUNDLE, top)
            continue
        for folder, _, names in os.walk(os.path.join(BUNDLE, top)):
            for name in names:
                yield os.path.join(folder, name)


class SkillTests(unittest.TestCase):
    def skill_paths(self):
        paths = [os.path.join(skill_dir(s), "SKILL.md") for s in SKILLS]
        paths += alias_skills()
        return paths

    def test_all_skills_present(self):
        for path in self.skill_paths():
            self.assertTrue(os.path.isfile(path), path)

    def test_frontmatter_name_and_vn_description(self):
        for path in self.skill_paths():
            meta = frontmatter(read(path))
            self.assertEqual(meta.get("name"), os.path.basename(os.path.dirname(path)), path)
            self.assertTrue(VI_CHARS.search(meta.get("description", "")), "description not Vietnamese: " + path)
            self.assertTrue(VI_CHARS.search(meta.get("argument-hint", "")) or "argument-hint" not in meta, path)

    def test_body_english(self):
        # Body = model instructions in English; Vietnamese only in quoted user-facing lines.
        for path in self.skill_paths():
            body = re.sub(r"^---\n.*?\n---\n", "", read(path), flags=re.S)
            words = re.findall(r"[^\W\d_]+", body)
            vi = sum(1 for w in words if VI_CHARS.search(w))
            self.assertLess(vi / max(1, len(words)), 0.12, path)

    def test_references_exist(self):
        refs = os.path.join(skill_dir("q-kb-sync"), "references")
        for name in ("kb-conventions.md", "ingest-templates.md"):
            self.assertTrue(os.path.isfile(os.path.join(refs, name)), name)
        for skill in ("q-kb-add", "q-kb-publish"):
            self.assertIn("../q-kb-sync/references/kb-conventions.md", read(os.path.join(skill_dir(skill), "SKILL.md")))

    def test_search_skill_rules(self):
        text = read(os.path.join(skill_dir("q-kb-search"), "SKILL.md"))
        for needle in ("🔎 Phạm vi KB:", ".qkb/local/scope.json", "query", "--project", "Read only", "No inference"):
            self.assertIn(needle, text)
        aliases = alias_skills()
        if not aliases:
            return
        alias = read(aliases[0])
        self.assertIn(".claude/skills/q-kb-search/SKILL.md", alias)
        self.assertIn("`all`", alias)

    def test_publish_checks_links(self):
        text = read(os.path.join(skill_dir("q-kb-publish"), "SKILL.md"))
        self.assertIn("verify --links", text)
        self.assertIn("--whoami", text)
        # live state saved before the copy, link gate before version / changelog, roll back on a rise
        order = ["**Links before**", "**Save the live state**", "**Copy**", "**Search index**", "**Link gate**",
                 "**Version**", "**Release**"]
        positions = [text.index(s) for s in order]
        self.assertEqual(positions, sorted(positions))
        gate = text[text.index("**Link gate**"):text.index("**Version**")]
        for needle in ("roll back", "_rollback/", "new-files.txt", "No version, no changelog entry, no release"):
            self.assertIn(needle, gate)
        self.assertIn("are **not** touched before step 7", text)
        readme = read(os.path.join(BUNDLE, "README_VN.md"))
        self.assertIn("đã khôi phục bản cũ", readme)
        self.assertIn("không** tăng version", read(os.path.join(BUNDLE, "CHANGELOG.md")))

    def test_search_query_variants(self):
        text = read(os.path.join(skill_dir("q-kb-search"), "SKILL.md"))
        step = text[text.index("**Query variants**"):text.index("4. `read <SECTION_ID>`")]
        for needle in ("at most **3** variants", "never invent a term", "at most 3 calls", "Merge the hits by section ID",
                       "best rank", "name the variant that found each source", "full diacritics", "glossary"):
            self.assertIn(needle, step)
        # a scope spanning several folders runs without --project
        self.assertIn("span several folders", step)

    def test_engine_requirement_stated(self):
        self.assertIn("2.1.0-c1", read(os.path.join(BUNDLE, "README_VN.md")))
        self.assertIn("2.1.0-c1", read(os.path.join(BUNDLE, "scripts", "kb_scaffold.py")))

    def test_request_issue_field(self):
        text = read(os.path.join(skill_dir("q-kb-request"), "SKILL.md"))
        self.assertIn("Issue IDs", text)
        self.assertIn("Mã vấn đề", text)
        self.assertIn("manager.session_file", text)


class ConfigTests(unittest.TestCase):
    def test_example_has_documented_keys(self):
        example = json.loads(read(os.path.join(BUNDLE, "templates", "kb.config.example.json")))
        for key in ("kb_root", "projects_root", "manager", "requests_folder", "locks_folder", "staging_folder", "policy_file",
                    "glossary_files", "version_file", "changelog_file", "languages", "project_scopes", "issue_id_patterns",
                    "confirmer_roles", "hooks", "search"):
            self.assertIn(key, example)
        self.assertEqual(set(example["manager"]), {"folder", "session_name", "session_file"})
        self.assertEqual(example["search"]["model"], "none")

    @unittest.skipUnless(WORKSPACE, "no local project files (kb-test-local.json: workspace_files)")
    def test_local_project_config(self):
        example = json.loads(read(os.path.join(BUNDLE, "templates", "kb.config.example.json")))
        ws = json.loads(read(os.path.join(WORKSPACE, "kb.config.json")))
        keys = lambda d: {k for k in d if not k.startswith("_")}
        # "hooks" is optional (defaults in hooks/kbcommon.py); install.py writes hooks.mode at install;
        # "request_prefixes" (v2.0.3) is optional too (default ["REQ-", "KB-REQ-"] in hooks/kbwatch.py since 2.0.4)
        optional = {"hooks", "request_prefixes"}
        self.assertEqual(keys(example) - optional, keys(ws) - optional)
        for pattern in ws["issue_id_patterns"]:
            re.compile(pattern)
        data = json.loads(read(os.path.join(WORKSPACE, "session.json")))
        self.assertEqual(set(k for k in data if not k.startswith("_")), {"session_name", "session_id", "written_at"})


class NameScanTests(unittest.TestCase):
    def test_no_project_names_anywhere_in_bundle(self):
        # the whole bundle (tests included); names come from the local test file, patterns are neutral
        hits = []
        for folder, dirs, names in os.walk(BUNDLE):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in names:
                path = os.path.join(folder, name)
                try:
                    text = read(path)
                except (UnicodeDecodeError, OSError):
                    continue
                hits += ["%s: %s" % (os.path.relpath(path, BUNDLE), h) for h in localcfg.scan_hits(text)]
        self.assertEqual(hits, [])


class ScaffoldTests(unittest.TestCase):
    def run_py(self, args, cwd):
        return subprocess.run([sys.executable, "-E", "-s", "-B"] + args, cwd=cwd, capture_output=True,
                              text=True, encoding="utf-8", timeout=120)

    def test_scaffold_creates_and_never_overwrites(self):
        script = os.path.join(BUNDLE, "scripts", "kb_scaffold.py")
        with tempfile.TemporaryDirectory() as tmp:
            r = self.run_py([script, "--project", "demo", "--sub", "core"], tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            for rel in (".qkb/config.json", "kb/VERSION", "kb/demo/core/INDEX.md", "kb/demo/core/notes.md",
                        "00_UpdateDocs/kb.config.json", "00_UpdateDocs/README.md", "projects/demo/core/docs"):
                self.assertTrue(os.path.exists(os.path.join(tmp, rel)), rel)
            index = read(os.path.join(tmp, "kb", "demo", "core", "INDEX.md"))
            self.assertNotIn("{{", index)
            cfg = json.loads(read(os.path.join(tmp, "00_UpdateDocs", "kb.config.json")))
            self.assertEqual(cfg["project_scopes"], {"demo/core": ["kb/demo/core/", "kb/demo/shared/"]})
            with open(os.path.join(tmp, "kb", "VERSION"), "w", encoding="utf-8") as f:
                f.write("keep\n")
            r = self.run_py([script, "--project", "demo", "--sub", "core"], tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Giữ nguyên", r.stdout)
            self.assertEqual(read(os.path.join(tmp, "kb", "VERSION")), "keep\n")

    def test_bad_name_rejected(self):
        script = os.path.join(BUNDLE, "scripts", "kb_scaffold.py")
        with tempfile.TemporaryDirectory() as tmp:
            r = self.run_py([script, "--project", "../x"], tmp)
            self.assertEqual(r.returncode, 2)
            self.assertIn("LỖI", r.stderr)
            self.assertEqual(os.listdir(tmp), [])

    def test_dry_run_writes_nothing(self):
        script = os.path.join(BUNDLE, "scripts", "kb_scaffold.py")
        with tempfile.TemporaryDirectory() as tmp:
            r = self.run_py([script, "--project", "demo", "--dry-run"], tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Sẽ tạo", r.stdout)
            self.assertEqual(os.listdir(tmp), [])

    def test_qkb_init_build_verify_on_scaffold(self):
        engine = os.environ.get("QKB_ENGINE") or os.path.normpath(DEFAULT_ENGINE)
        if not os.path.isfile(engine):
            self.skipTest("Q-KnowledgeBase engine not found (set QKB_ENGINE)")
        script = os.path.join(BUNDLE, "scripts", "kb_scaffold.py")
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self.run_py([script, "--project", "demo", "--sub", "core"], tmp).returncode, 0)
            for step in (["init"], ["build"]):
                r = self.run_py([engine] + step + ["--format", "json"], tmp)
                self.assertEqual(r.returncode, 0, step + [r.stdout[-400:], r.stderr[-400:]])
            r = self.run_py([engine, "verify", "--links", "--format", "json"], tmp)
            self.assertEqual(r.returncode, 0, r.stdout[-400:] + r.stderr[-400:])
            data = json.loads(r.stdout)
            self.assertTrue(data["ok"])
            self.assertGreaterEqual(data["files"], 4)
            self.assertEqual(data["links"]["broken"], 0)
            r = self.run_py([engine, "search", "notes", "--format", "json"], tmp)
            self.assertEqual(r.returncode, 0, r.stderr[-400:])
            self.assertIn("kb/demo/core/notes.md", r.stdout)


if __name__ == "__main__":
    unittest.main()
