"""Tests of tools/kbpack.py  on temp sample projects (neutral names). Stdlib only; temp folders only."""
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile

# a real KB-Model_*.zip may sit beside the bundle (auto-detect): only AutoDetectModelZipTests looks for it
os.environ["KBINSTALL_TEST_NO_MODEL_SEARCH"] = "1"
BUNDLE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
KBPACK = os.path.join(BUNDLE, "tools", "kbpack.py")
INSTALL = os.path.join(BUNDLE, "install.py")


def write(root, rel, text):
    p = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if os.path.exists(p):
        os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def run(root, *args, script=KBPACK):
    args = list(args)
    if args and args[0] == "import" and "--no-accept" not in args:
        args.append("--accept-patterns")         # the sample pack carries OP-\d+ ( opt-in)
    args = [x for x in args if x != "--no-accept"]
    r = subprocess.run([sys.executable, "-E", "-s", "-B", script, "--root", root] + args, capture_output=True,
                       timeout=600, stdin=subprocess.DEVNULL)
    return r.returncode, r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")


def run_json(root, *args):
    r = subprocess.run([sys.executable, "-E", "-s", "-B", KBPACK, "--root", root, "--format", "json"] + list(args),
                       capture_output=True, timeout=600, stdin=subprocess.DEVNULL)
    return r.returncode, json.loads(r.stdout.decode("utf-8"))


def author(root, version="2026.01.05-01"):
    write(root, "kb/VERSION", version + "\n")
    write(root, "kb/demo/README.md", "# demo\n")
    write(root, "kb/demo/core/INDEX.md", "# demo/core index\n\n- [notes](notes.md)\n")
    write(root, "kb/demo/core/notes.md", "# notes\n\n- **OP-1** · Trạng thái: mở · Ảnh hưởng: `x.md` · Nguồn: test\n")
    write(root, "kb/demo/api/INDEX.md", "# demo/api index\n")
    write(root, "kb/demo/shared/terms.md", "# terms\n\n| VI | EN |\n|---|---|\n| bộ đếm | counter |\n")
    write(root, "kb/demo/tpl.xlsx", "not really excel")
    write(root, "kb/common/glossary.md", "# common glossary\n")
    write(root, "kb/other/o.md", "# other project\n")
    cfg = {"kb_root": "kb", "version_file": "kb/VERSION", "staging_folder": "00_UpdateDocs/staging",
           "locks_folder": "00_UpdateDocs/locks", "manager": {"folder": "00_UpdateDocs"},
           "project_scopes": {"demo/core": ["kb/demo/core/", "kb/demo/shared/", "kb/common/"], "other": ["kb/other/"]},
           "glossary_files": ["kb/demo/shared/terms.md"], "issue_id_patterns": ["OP-\\d+"],
           "hooks": {"route_keywords": ["counter"]}}
    write(root, "kb.config.json", json.dumps(cfg))


def zips(root):
    folder = os.path.join(root, "00_UpdateDocs", "exports")
    return sorted(os.path.join(folder, n) for n in os.listdir(folder)) if os.path.isdir(folder) else []


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.a = os.path.join(self._tmp.name, "author")
        self.m = os.path.join(self._tmp.name, "member")
        os.makedirs(self.a)
        os.makedirs(self.m)
        author(self.a)

    def tearDown(self):
        for folder, _, names in os.walk(self._tmp.name):          # imported copies are read-only
            for n in names:
                try:
                    os.chmod(os.path.join(folder, n), stat.S_IWRITE | stat.S_IREAD)
                except OSError:
                    pass
        self._tmp.cleanup()

    def export(self, *extra):
        code, data = run_json(self.a, "export", *extra, "--apply")
        self.assertEqual(code, 0, data)
        return data["zip"]


class ExportTests(Base):
    def test_dry_run_then_export(self):
        code, out = run(self.a, "export", "--project", "demo")
        self.assertEqual(code, 0, out)
        self.assertIn("KẾ HOẠCH", out)
        self.assertEqual(zips(self.a), [])
        z = self.export("--project", "demo")
        self.assertTrue(os.path.basename(z).startswith("KB-Data_demo_v2026.01.05-01_"))
        with zipfile.ZipFile(z) as f:
            pack = json.loads(f.read("PACK.json"))
            names = f.namelist()
        self.assertEqual(pack["format"], "kb-data-pack")
        self.assertIn("data/demo/core/notes.md", names)
        self.assertNotIn("data/demo/tpl.xlsx", names)                 # non-Markdown stays out by default
        self.assertNotIn("data/common/glossary.md", names)            # one project per pack
        self.assertFalse([n for n in names if "sqlite" in n or ".qkb" in n])
        self.assertEqual(pack["excluded"]["skipped"], {".xlsx": 1})
        self.assertEqual(list(pack["scopes"]), ["demo/core"])
        self.assertEqual(pack["glossary_files"], ["shared/terms.md"])          # relative to kb/<project>/
        self.assertEqual(pack["route_keywords"], ["counter"])                 # hook word list (kbpack / hooks only)
        self.assertEqual(pack["query_routes"], {})                            # engine router dict (contract)
        self.assertEqual(pack["engine_min"], "2.1.0-d2")
        self.assertNotIn("settings", pack)

    def test_secret_stops_without_printing_value(self):
        fake = "Fake" + "Value" + "0042"                    # synthetic test value, built at run time
        write(self.a, "kb/demo/core/notes.md", "# notes\n" + "api" + "_key = " + fake + "\n")
        code, out = run(self.a, "export", "--project", "demo", "--apply")
        self.assertEqual(code, 2)
        self.assertIn("demo/core/notes.md:2 CREDENTIAL", out)
        self.assertNotIn(fake, out)
        self.assertEqual(zips(self.a), [])
        write(self.a, "kb/demo/core/notes.md", "# notes\npassword: [MASKED]\n")       # masked value is fine
        self.assertEqual(run(self.a, "export", "--project", "demo")[0], 0)

    def test_warnings_need_accept(self):
        write(self.a, "kb/demo/core/notes.md", "# notes\nmail: someone@example.com · see kb/other/o.md\n")
        code, out = run(self.a, "export", "--project", "demo", "--apply")
        self.assertEqual(code, 1, out)
        self.assertIn("CẦN DUYỆT", out)
        self.assertIn("OTHER_PROJECT", out)
        self.assertIn("PERSONAL", out)
        code, out = run(self.a, "export", "--project", "demo", "--accept", "PERSONAL,OTHER_PROJECT", "--apply")
        self.assertEqual(code, 0, out)
        with zipfile.ZipFile(zips(self.a)[-1]) as f:
            self.assertEqual(json.loads(f.read("PACK.json"))["policy"]["scan"]["accepted"], ["OTHER_PROJECT", "PERSONAL"])

    def test_unpublished_work_blocks_export(self):
        write(self.a, "00_UpdateDocs/staging/kb/demo/core/notes.md", "draft")
        code, out = run(self.a, "export", "--project", "demo")
        self.assertEqual(code, 2)
        self.assertIn("chưa phát hành", out)

    def test_changelog_and_stable_pack_id(self):
        z1 = self.export("--project", "demo")
        write(self.a, "kb/VERSION", "2026.01.06-01\n")
        write(self.a, "kb/demo/core/new.md", "# new\n")
        z2 = self.export("--project", "demo")
        with zipfile.ZipFile(z1) as f1, zipfile.ZipFile(z2) as f2:
            p1, p2 = json.loads(f1.read("PACK.json")), json.loads(f2.read("PACK.json"))
            log = f2.read("CHANGELOG.md").decode("utf-8")
        self.assertEqual(p1["pack_id"], p2["pack_id"])
        self.assertEqual(p2["previous_version"], "2026.01.05-01")
        self.assertIn("v2026.01.06-01", log)
        self.assertIn("thêm 1", log)
        self.assertIn("v2026.01.05-01", log)


class ImportTests(Base):
    def test_round_trip_read_only_verify_update_conflict_remove(self):
        z1 = self.export("--project", "demo")
        code, out = run(self.m, "import", z1)
        self.assertEqual(code, 0, out)
        self.assertFalse(os.path.exists(os.path.join(self.m, "kb")))       # plan only
        code, out = run(self.m, "import", z1, "--apply")
        self.assertEqual(code, 0, out)
        notes = os.path.join(self.m, "kb", "demo", "core", "notes.md")
        self.assertEqual(read(notes), read(os.path.join(self.a, "kb", "demo", "core", "notes.md")))
        self.assertFalse(os.stat(notes).st_mode & stat.S_IWRITE)            # read-only copy
        cfg = json.loads(read(os.path.join(self.m, "kb.config.json")))
        self.assertIn("demo/core", cfg["project_scopes"])
        self.assertNotIn("other", cfg["project_scopes"])
        self.assertIn("OP-\\d+", cfg["issue_id_patterns"])
        self.assertIn("kb/demo/shared/terms.md", cfg["glossary_files"])            # back to a repo path for the skills
        qcfg = json.loads(read(os.path.join(self.m, ".qkb", "config.json")))
        self.assertNotIn("glossary_paths", qcfg)                                     # the engine merges pack keys itself
        self.assertTrue(os.path.isfile(os.path.join(self.m, ".qkb", "packs", "demo", "PACK.json")))
        self.assertEqual(run(self.m, "verify")[0], 0)
        self.assertIn("ĐÃ CÓ", run(self.m, "import", z1, "--apply")[1])
        # local edit -> verify flags it; a newer pack stops on the conflict until --discard-local
        write(self.m, "kb/demo/core/notes.md", "local edit\n")
        code, out = run(self.m, "verify")
        self.assertEqual(code, 1)
        self.assertIn("1 sửa", out)
        # same pack again over the local edit: names the edit instead of "nothing new"
        code, out = run(self.m, "import", z1, "--apply")
        self.assertEqual(code, 1, out)
        self.assertNotIn("ĐÃ CÓ", out)
        self.assertIn("demo/core/notes.md", out)
        write(self.a, "kb/VERSION", "2026.01.06-01\n")
        write(self.a, "kb/demo/core/notes.md", "# notes v2\n")
        z2 = self.export("--project", "demo")
        code, out = run(self.m, "import", z2, "--apply")
        self.assertEqual(code, 1, out)
        self.assertIn("XUNG ĐỘT", out)
        code, out = run(self.m, "import", z2, "--apply", "--discard-local")
        self.assertEqual(code, 0, out)
        self.assertEqual(read(notes), "# notes v2\n")
        backups = os.listdir(os.path.join(self.m, ".qkb", "backups"))
        self.assertTrue(any(b.startswith("pack-demo-") for b in backups))
        # downgrade refused
        code, out = run(self.m, "import", z1, "--apply")
        self.assertEqual(code, 2)
        self.assertIn("không mới hơn", out)
        # remove: data to backup, settings taken out, record gone
        code, out = run(self.m, "remove", "--project", "demo", "--apply")
        self.assertEqual(code, 0, out)
        self.assertFalse(os.path.exists(os.path.join(self.m, "kb", "demo")))
        self.assertNotIn("demo/core", json.loads(read(os.path.join(self.m, "kb.config.json")))["project_scopes"])
        self.assertFalse(os.path.exists(os.path.join(self.m, ".qkb", "packs", "demo")))

    def test_same_name_other_source_and_self_authored_refused(self):
        z = self.export("--project", "demo")
        other = os.path.join(self._tmp.name, "author2")
        os.makedirs(other)
        author(other, "2026.02.01-01")
        code, out = run(other, "export", "--project", "demo", "--apply")
        self.assertEqual(code, 0, out)
        self.assertEqual(run(self.m, "import", z, "--apply")[0], 0)
        code, out = run(self.m, "import", zips(other)[-1], "--apply")
        self.assertEqual(code, 2)
        self.assertIn("khác mã gói", out)
        mine = os.path.join(self._tmp.name, "mine")
        os.makedirs(mine)
        write(mine, "kb/demo/own.md", "# my own demo\n")
        code, out = run(mine, "import", z, "--apply")
        self.assertEqual(code, 2)
        self.assertIn("tự soạn", out)

    def test_imported_project_is_not_exported_again(self):
        z = self.export("--project", "demo")
        self.assertEqual(run(self.m, "import", z, "--apply")[0], 0)
        code, out = run(self.m, "export", "--project", "demo")
        self.assertEqual(code, 2)
        self.assertIn("bản đã nhập", out)

    def test_sub_project_packs_share_project_parts(self):
        z_core = self.export("--project", "demo", "--sub", "core")
        z_api = self.export("--project", "demo", "--sub", "api")
        with zipfile.ZipFile(z_core) as f:
            names = f.namelist()
        self.assertIn("data/demo/core/notes.md", names)
        self.assertIn("data/demo/shared/terms.md", names)
        self.assertIn("data/demo/README.md", names)
        self.assertNotIn("data/demo/api/INDEX.md", names)
        self.assertEqual(run(self.m, "import", z_core, "--apply")[0], 0)
        code, out = run(self.m, "import", z_api, "--apply")
        self.assertEqual(code, 0, out)
        self.assertIn("Phần chung giữ nguyên", out)
        code, out = run(self.m, "remove", "--project", "demo", "--sub", "core", "--apply")
        self.assertEqual(code, 0, out)
        self.assertFalse(os.path.exists(os.path.join(self.m, "kb", "demo", "core")))
        self.assertTrue(os.path.isfile(os.path.join(self.m, "kb", "demo", "shared", "terms.md")))   # api still uses it
        self.assertEqual(run(self.m, "remove", "--project", "demo", "--sub", "api", "--apply")[0], 0)
        self.assertFalse(os.path.exists(os.path.join(self.m, "kb", "demo")))

    def test_requires(self):
        z_common = self.export("--project", "common")
        z_demo = self.export("--project", "demo", "--requires", "common")
        code, out = run(self.m, "import", z_demo, "--apply")
        self.assertEqual(code, 2)
        self.assertIn("Nhập gói đó trước", out)
        self.assertEqual(run(self.m, "import", z_common, "--apply")[0], 0)
        self.assertEqual(run(self.m, "import", z_demo, "--apply")[0], 0)
        code, out = run(self.m, "remove", "--project", "common", "--apply")
        self.assertEqual(code, 2)
        self.assertIn("đang được gói khác cần tới", out)


class ZipSafetyTests(Base):
    def craft(self, mutate):
        z = self.export("--project", "demo")
        with zipfile.ZipFile(z) as f:
            items = {n: f.read(n) for n in f.namelist()}
        mutate(items)
        bad = os.path.join(self._tmp.name, "bad.zip")
        with zipfile.ZipFile(bad, "w") as f:
            for n, data in items.items():
                f.writestr(n, data)
        return bad

    def test_unsafe_or_tampered_packs_refused(self):
        cases = {
            "traversal": lambda i: i.__setitem__("data/../../evil.md", b"x"),
            "outside": lambda i: i.__setitem__("evil.py", b"x"),
            "tampered": lambda i: i.__setitem__("data/demo/core/notes.md", b"changed"),
            "unlisted": lambda i: i.__setitem__("data/demo/core/extra.md", b"x"),
        }
        for label, mutate in cases.items():
            code, out = run(self.m, "import", self.craft(mutate), "--apply")
            self.assertEqual(code, 2, (label, out))
            self.assertFalse(os.path.exists(os.path.join(self.m, "kb")), label)
        self.assertFalse(os.path.exists(os.path.join(self._tmp.name, "evil.md")))


class CraftedPackTests(Base):
    """the pack never sets its own safety rules; unsafe names and regexes are refused."""

    def repack(self, mutate):
        z = self.export("--project", "demo")
        with zipfile.ZipFile(z) as f:
            items = {n: f.read(n) for n in f.namelist()}
        pack = json.loads(items["PACK.json"])
        mutate(items, pack)
        for f in pack["files"]:                      # keep the pack self-consistent: only the importer's rules may stop it
            f["sha256"] = hashlib.sha256(items["data/" + f["path"]]).hexdigest()
            f["bytes"] = len(items["data/" + f["path"]])
        text = "".join("%s  %s\n" % (f["sha256"], f["path"]) for f in sorted(pack["files"], key=lambda x: x["path"]))
        pack["digest"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        items["PACK.json"] = json.dumps(pack).encode("utf-8")
        out = os.path.join(self._tmp.name, "crafted.zip")
        with zipfile.ZipFile(out, "w") as f:
            for n, data in items.items():
                f.writestr(n, data)
        return out

    def add_file(self, path, data=b"x"):
        def mutate(items, pack):
            items["data/" + path] = data
            pack["files"].append({"path": path})
        return mutate

    def test_script_file_refused_even_if_pack_says_allowed(self):
        def mutate(items, pack):
            self.add_file("demo/core/run.ps1", b"Write-Host hi")(items, pack)
            pack["excluded"]["rule"] += " + .ps1"
        z = self.repack(mutate)
        code, out = run(self.m, "import", z, "--apply")
        self.assertEqual(code, 2, out)
        self.assertIn("--allow-ext", out)
        self.assertFalse(os.path.exists(os.path.join(self.m, "kb")))

    def test_importer_can_allow_an_extension(self):
        z = self.repack(self.add_file("demo/core/table.csv", b"a,b\n"))
        self.assertEqual(run(self.m, "import", z, "--apply")[0], 2)
        code, out = run(self.m, "import", z, "--apply", "--allow-ext", ".csv")
        self.assertEqual(code, 0, out)

    def test_redos_and_bad_patterns_refused(self):
        for bad in ("(a+)+$", r"(\w*)*x", "x" * 300, "([a-z]", "(a|aa)+", r"(\w)\1", "x*"):     # same refusals as the engine (e2)
            def mutate(items, pack, bad=bad):
                pack["issue_id_patterns"] = [r"OP-\d+", bad]
            code, out = run(self.m, "import", self.repack(mutate), "--apply")
            self.assertEqual(code, 2, (bad, out))
            self.assertIn("không an toàn", out)
            self.assertFalse(os.path.exists(os.path.join(self.m, "kb")))

    def test_patterns_need_opt_in(self):
        z = self.export("--project", "demo")
        code, out = run(self.m, "import", z, "--apply", "--no-accept")
        self.assertEqual(code, 1, out)
        self.assertIn("--accept-patterns", out)
        self.assertFalse(os.path.exists(os.path.join(self.m, "kb")))
        self.assertEqual(run(self.m, "import", z, "--apply")[0], 0)          # helper adds --accept-patterns

    def test_windows_unsafe_names_refused(self):
        for path in ("demo/core/x.md:s", "demo/core/CON.md", "demo/core/aux", "demo/core/name.md.", "demo/core/ space /a.md"):
            code, out = run(self.m, "import", self.repack(self.add_file(path)), "--apply")
            self.assertEqual(code, 2, (path, out))
            self.assertIn("không an toàn trên Windows", out)


class ExportRulesTests(Base):
    def test_absolute_out_inside_kept_outside_refused(self):
        inside = os.path.join(self.a, "packs-here")
        code, data = run_json(self.a, "export", "--project", "demo", "--out", inside, "--apply")
        self.assertEqual(code, 0, data)
        self.assertTrue(data["zip"].startswith(inside))
        self.assertTrue(os.path.isfile(data["zip"]))
        outside = os.path.join(self._tmp.name, "elsewhere")
        code, out = run(self.a, "export", "--project", "demo", "--out", outside, "--apply")
        self.assertEqual(code, 2)
        self.assertIn("ra ngoài thư mục dự án", out)
        self.assertFalse(os.path.exists(outside))

    def test_same_version_new_content_refused(self):
        self.export("--project", "demo")
        self.assertEqual(run(self.a, "export", "--project", "demo", "--apply")[0], 0)        # same content: fine
        write(self.a, "kb/demo/core/notes.md", "# notes changed without a publish\n")
        code, out = run(self.a, "export", "--project", "demo", "--apply")
        self.assertEqual(code, 2)
        self.assertIn("Phát hành KB trước", out)


class ReaderInstallTests(Base):
    def test_reader_profile_then_import_and_search(self):
        code = subprocess.run([sys.executable, "-E", "-s", "-B", INSTALL, "--target", self.m, "--profile", "reader",
                               "--apply", "--yes", "--model", "none"], capture_output=True, timeout=600,
                              stdin=subprocess.DEVNULL)
        self.assertEqual(code.returncode, 0, code.stdout.decode("utf-8", "replace") + code.stderr.decode("utf-8", "replace"))
        self.assertTrue(os.path.isfile(os.path.join(self.m, ".claude", "tools", "kbpack.py")))
        self.assertTrue(os.path.isfile(os.path.join(self.m, ".claude", "skills", "q-kb-search", "SKILL.md")))
        self.assertFalse(os.path.exists(os.path.join(self.m, "00_UpdateDocs")))
        self.assertFalse(os.path.exists(os.path.join(self.m, ".claude", "skills", "q-kb-publish")))
        self.assertTrue(os.path.isfile(os.path.join(self.m, "kb.config.json")))
        z = self.export("--project", "demo")
        installed = os.path.join(self.m, ".claude", "tools", "kbpack.py")
        code, out = run(self.m, "import", z, "--apply", script=installed)
        self.assertEqual(code, 0, out)
        self.assertIn("Chỉ mục đã cập nhật", out)
        r = subprocess.run([sys.executable, "-E", "-s", "-B", os.path.join(self.m, ".claude", "skills", "q-knowledgebase",
                                                                         "scripts", "qkb.py"), "search", "counter",
                            "--format", "json"], cwd=self.m, capture_output=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("kb/demo/shared/terms.md", r.stdout.decode("utf-8"))
        # the engine reads the pack record (contract): project pack and a sub-project pack both "OK"
        z_sub = self.export("--project", "demo", "--sub", "api")
        self.assertEqual(run(self.m, "remove", "--project", "demo", "--apply", script=installed)[0], 0)
        self.assertEqual(run(self.m, "import", z_sub, "--apply", script=installed)[0], 0)
        r = subprocess.run([sys.executable, "-E", "-s", "-B", os.path.join(self.m, ".claude", "skills", "q-knowledgebase",
                                                                         "scripts", "qkb.py"), "status", "--format", "json"],
                           cwd=self.m, capture_output=True, timeout=300)
        packs = json.loads(r.stdout.decode("utf-8")).get("packs") or []
        self.assertEqual([(p["changelog"], p["state"]) for p in packs], [(".qkb/packs/demo__api/CHANGELOG.md", "OK")])


if __name__ == "__main__":
    unittest.main()
