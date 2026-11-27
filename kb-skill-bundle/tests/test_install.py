"""Tests of install.py on temp sample projects. Stdlib only; temp folders only.

Old engine trees for the upgrade cases come from the local test file (tests/localcfg.py, key old_engines);
the upgrade cases are skipped when it is absent.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

# a real KB-Model_*.zip may sit beside the bundle (auto-detect): only AutoDetectModelZipTests looks for it
os.environ["KBINSTALL_TEST_NO_MODEL_SEARCH"] = "1"
BUNDLE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
INSTALL = os.path.join(BUNDLE, "install.py")
HERE = os.path.dirname(BUNDLE)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import localcfg  # noqa: E402

OLD_200 = localcfg.LOCAL.get("old_engines", {}).get("2.0.0", "")
OLD_B1 = localcfg.LOCAL.get("old_engines", {}).get("2.1.0-b1", "")
FULL = ["--apply", "--yes", "--model", "none", "--project", "demo", "--sub", "core"]


def run(target, *args, bundle=BUNDLE):
    r = subprocess.run([sys.executable, "-E", "-s", "-B", os.path.join(bundle, "install.py"), "--target", target] + list(args),
                       capture_output=True, timeout=600, stdin=subprocess.DEVNULL)
    return r.returncode, r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")


def run_json(target, *args):
    r = subprocess.run([sys.executable, "-E", "-s", "-B", INSTALL, "--target", target, "--format", "json"] + list(args),
                       capture_output=True, timeout=600, stdin=subprocess.DEVNULL)
    return r.returncode, json.loads(r.stdout.decode("utf-8"))


def tree(root):
    out = {}
    for folder, dirs, names in os.walk(root):
        for n in names:
            p = os.path.join(folder, n)
            with open(p, "rb") as f:
                out[os.path.relpath(p, root).replace("\\", "/")] = hashlib.sha256(f.read()).hexdigest()
    return out


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def qkb(target, *args):
    r = subprocess.run([sys.executable, "-E", "-s", "-B", os.path.join(target, ".claude", "skills", "q-knowledgebase", "scripts",
                                                                       "qkb.py")] + list(args) + ["--format", "json"],
                       cwd=target, capture_output=True, timeout=600)
    return r.returncode, json.loads(r.stdout.decode("utf-8") or "{}")


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.t = os.path.join(self._tmp.name, "dự án mẫu")       # space + Vietnamese letters in the path
        os.makedirs(self.t)

    def tearDown(self):
        self._tmp.cleanup()


class FreshTests(Base):
    def test_t01_dry_run_writes_nothing(self):
        code, out = run(self.t)
        self.assertEqual(code, 0, out)
        self.assertEqual(os.listdir(self.t), [])
        for n in ("1. File sẽ thêm", "2. File giữ nguyên", "3. .claude/settings.json", "4. KB rỗng", "5. Lựa chọn",
                  "6. Sao lưu sẽ tạo"):
            self.assertIn(n, out)

    def test_t02_t03_install_rerun_t18_uninstall(self):
        code, out = run(self.t, *FULL)
        self.assertEqual(code, 0, out)
        self.assertIn("ĐÃ CÀI XONG", out)
        self.assertIn("doctor đạt", out)
        self.assertIn("liên kết hỏng: 0", out)
        record = json.loads(read(os.path.join(self.t, ".qkb", "install", "installed.json")))
        self.assertEqual(record["options"]["model"], "none")
        for rel in (".claude/skills/q-knowledgebase/scripts/qkb.py", ".claude/skills/q-kb-search/SKILL.md",
                    "00_UpdateDocs/.claude/skills/q-kb-publish/SKILL.md", ".claude/hooks/kbwatch.py",
                    "00_UpdateDocs/templates/pages/module.md", "00_UpdateDocs/kb.config.json", "kb/demo/core/INDEX.md",
                    ".qkb/cache/index.sqlite3"):
            self.assertTrue(os.path.exists(os.path.join(self.t, *rel.split("/"))), rel)
        cfg = json.loads(read(os.path.join(self.t, "00_UpdateDocs", "kb.config.json")))
        self.assertEqual((cfg["hooks"]["mode"], cfg["search"]["model"]), ("observe", "none"))
        self.assertFalse(os.path.exists(os.path.join(self.t, "Q-KnowledgeBase-README.md")))
        settings = read(os.path.join(self.t, ".claude", "settings.json"))
        self.assertEqual(settings.count("kbwatch.py"), 1)
        self.assertEqual(qkb(self.t, "status")[1]["state"], "CURRENT")
        qcfg = json.loads(read(os.path.join(self.t, ".qkb", "config.json")))      # v2.0.2: usage log on by default
        self.assertEqual(qcfg["usage_log"], {"path": "process-log/kb-usage", "query_text": True})
        qcfg["usage_log"] = {"path": ""}                                          # a project turned it off: kept
        with open(os.path.join(self.t, ".qkb", "config.json"), "w", encoding="utf-8") as f:
            json.dump(qcfg, f)
        # second run changes nothing in the files and adds no duplicate block
        before = tree(os.path.join(self.t, ".claude"))
        code, data = run_json(self.t, *FULL)
        self.assertEqual(code, 0, data)
        self.assertEqual({r["action"] for r in data["files"]}, {"same"})
        self.assertEqual(data["settings"], "same")
        self.assertEqual(tree(os.path.join(self.t, ".claude")), before)
        self.assertEqual(json.loads(read(os.path.join(self.t, ".qkb", "config.json")))["usage_log"], {"path": ""})
        # uninstall keeps kb/, .qkb/, requests; a modified file is kept and listed
        with open(os.path.join(self.t, ".claude", "hooks", "kbroute.py"), "a", encoding="utf-8") as f:
            f.write("# local change\n")
        code, out = run(self.t, "--uninstall")
        self.assertEqual(code, 0, out)
        self.assertTrue(os.path.exists(os.path.join(self.t, ".claude", "hooks", "kbwatch.py")))   # preview only
        code, out = run(self.t, "--uninstall", "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertIn("GIỮ LẠI 1 file", out)
        self.assertTrue(os.path.exists(os.path.join(self.t, ".claude", "hooks", "kbroute.py")))
        self.assertFalse(os.path.exists(os.path.join(self.t, ".claude", "hooks", "kbwatch.py")))
        self.assertFalse(os.path.exists(os.path.join(self.t, ".claude", "skills", "q-knowledgebase", "scripts", "qkb.py")))
        for rel in ("kb/demo/core/notes.md", ".qkb/config.json", "00_UpdateDocs/kb.config.json"):
            self.assertTrue(os.path.exists(os.path.join(self.t, *rel.split("/"))), rel)
        self.assertNotIn("kbwatch", read(os.path.join(self.t, ".claude", "settings.json")))
        # a second uninstall is not an error
        code, out = run(self.t, "--uninstall", "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertIn("Không còn gì để gỡ", out)

    def test_rerun_keeps_restore_point(self):
        self.assertEqual(run(self.t, *FULL)[0], 0)
        self.assertEqual(run(self.t, *FULL)[0], 0)                    # no-op re-run
        code, out = run(self.t, "--restore-previous", "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertFalse(os.path.exists(os.path.join(self.t, ".claude", "hooks", "kbwatch.py")))
        self.assertFalse(os.path.exists(os.path.join(self.t, ".claude", "settings.json")) and
                         "kbwatch" in read(os.path.join(self.t, ".claude", "settings.json")))

    def test_t04_missing_choice(self):
        code, out = run(self.t, "--apply", "--yes", "--project", "demo")
        self.assertEqual(code, 3)
        self.assertIn("CHỌN CÁCH TÌM KIẾM", out)
        self.assertIn("Không dùng model (mặc định, khuyên dùng)", out)
        self.assertEqual(os.listdir(self.t), [])
        code, out = run(self.t, "--apply", "--yes", "--model", "none")
        self.assertEqual(code, 3)
        self.assertIn("CẦN CHỌN: tên dự án", out)
        code, out = run(self.t, "--apply", "--model", "none", "--project", "demo")   # no --yes, no keyboard
        self.assertEqual(code, 3)
        self.assertIn("CẦN XÁC NHẬN", out)
        self.assertEqual(os.listdir(self.t), [])

    def test_t05_model_slot(self):
        code, out = run(self.t, "--apply", "--yes", "--model", "local", "--project", "demo", "--sub", "core")
        self.assertEqual(code, 0, out)
        self.assertTrue(os.path.isfile(os.path.join(self.t, ".qkb", "models", "DOC_TRUOC_VN.md")))
        cfg = json.loads(read(os.path.join(self.t, "00_UpdateDocs", "kb.config.json")))
        self.assertEqual(cfg["search"]["model"], "local")
        self.assertIn("models/", read(os.path.join(self.t, ".qkb", ".gitignore")))

    def test_change_model_choice_without_reinstall(self):
        self.assertEqual(run(self.t, *FULL)[0], 0)
        index = os.path.join(self.t, ".qkb", "cache", "index.sqlite3")
        import sqlite3
        con = sqlite3.connect(index)
        sections = con.execute("SELECT count(*) FROM sections").fetchone()[0]
        con.close()
        code, data = run_json(self.t, "--apply", "--yes", "--model", "local")
        self.assertEqual(code, 0, data)
        self.assertEqual({r["action"] for r in data["files"]}, {"same"})          # no package file written again
        cfg = json.loads(read(os.path.join(self.t, "00_UpdateDocs", "kb.config.json")))
        self.assertEqual(cfg["search"]["model"], "local")
        self.assertTrue(os.path.isfile(os.path.join(self.t, ".qkb", "models", "DOC_TRUOC_VN.md")))
        code, data = run_json(self.t, "--apply", "--yes", "--model", "none")
        self.assertEqual(code, 0, data)
        self.assertEqual(json.loads(read(os.path.join(self.t, "00_UpdateDocs", "kb.config.json")))["search"]["model"], "none")
        con = sqlite3.connect(index)
        self.assertEqual(con.execute("SELECT count(*) FROM sections").fetchone()[0], sections)
        con.close()

    def test_t06_existing_settings_kept(self):
        os.makedirs(os.path.join(self.t, ".claude"))
        existing = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "python mine.py"}]}]},
                    "permissions": {"allow": ["Bash(git status)"], "deny": ["Read(secret/**)"]}, "model": "x"}
        with open(os.path.join(self.t, ".claude", "settings.json"), "w", encoding="utf-8") as f:
            json.dump(existing, f)
        code, out = run(self.t, *FULL)
        self.assertEqual(code, 0, out)
        merged = json.loads(read(os.path.join(self.t, ".claude", "settings.json")))
        self.assertEqual(merged["hooks"]["Stop"][0], existing["hooks"]["Stop"][0])
        self.assertEqual(len(merged["hooks"]["Stop"]), 2)
        self.assertEqual(merged["permissions"]["allow"][0], "Bash(git status)")
        self.assertEqual(merged["permissions"]["deny"], ["Read(secret/**)"])
        self.assertEqual(merged["model"], "x")
        record = json.loads(read(os.path.join(self.t, ".qkb", "install", "installed.json")))
        backup = os.path.join(self.t, *record["backup"].split("/"), "files", ".claude", "settings.json")
        self.assertEqual(json.loads(read(backup)), existing)

    def test_t07_broken_settings_untouched(self):
        os.makedirs(os.path.join(self.t, ".claude"))
        with open(os.path.join(self.t, ".claude", "settings.json"), "w", encoding="utf-8") as f:
            f.write("{ not json")
        code, out = run(self.t, *FULL)
        self.assertEqual(code, 0, out)
        self.assertIn("không đọc được dạng JSON", out)
        self.assertEqual(read(os.path.join(self.t, ".claude", "settings.json")), "{ not json")
        self.assertTrue(os.path.exists(os.path.join(self.t, ".claude", "hooks", "kbwatch.py")))

    def test_t11_conflict_then_adopt(self):
        self.assertEqual(run(self.t, *FULL)[0], 0)
        path = os.path.join(self.t, ".claude", "skills", "q-kb-search", "SKILL.md")
        with open(path, "a", encoding="utf-8") as f:
            f.write("\nlocal edit\n")
        record = os.path.join(self.t, ".qkb", "install", "installed.json")
        os.remove(record)                      # no install record -> the edited file is not recognised
        before = tree(self.t)
        code, out = run(self.t, *FULL)
        self.assertEqual(code, 1, out)
        self.assertIn("DỪNG: 1 file", out)
        self.assertEqual(tree(self.t), before)
        code, out = run(self.t, *(FULL + ["--adopt"]))
        self.assertEqual(code, 0, out)
        self.assertNotIn("local edit", read(path))
        rec = json.loads(read(record))
        saved = os.path.join(self.t, *rec["backup"].split("/"), "files", ".claude", "skills", "q-kb-search", "SKILL.md")
        self.assertIn("local edit", read(saved))

    def test_t13_tampered_bundle(self):
        copy = os.path.join(self._tmp.name, "bundle")
        shutil.copytree(BUNDLE, copy, ignore=shutil.ignore_patterns("__pycache__"))
        with open(os.path.join(copy, "hooks", "kbwatch.py"), "a", encoding="utf-8") as f:
            f.write(" ")
        code, out = run(self.t, *FULL, bundle=copy)
        self.assertEqual(code, 2)
        self.assertIn("không đúng mã kiểm tra", out)
        self.assertEqual(os.listdir(self.t), [])

    def test_t17_other_manager_folder(self):
        code, out = run(self.t, *(FULL + ["--manager-folder", "kbadmin", "--session-name", "KB_Admin"]))
        self.assertEqual(code, 0, out)
        self.assertTrue(os.path.isfile(os.path.join(self.t, "kbadmin", ".claude", "skills", "q-kb-sync", "SKILL.md")))
        self.assertFalse(os.path.exists(os.path.join(self.t, "00_UpdateDocs")))
        r = subprocess.run([sys.executable, "-I", "-S", "-c",
                            "import sys; sys.path.insert(0, sys.argv[1]); import kbcommon as k; "
                            "c = k.load_config(sys.argv[2]); print(c['manager']['folder'])",
                            os.path.join(self.t, ".claude", "hooks"), self.t], capture_output=True, timeout=30)
        self.assertEqual(r.stdout.decode().strip(), "kbadmin")

    def test_t20_newer_engine_refused(self):
        core = os.path.join(self.t, ".claude", "skills", "q-knowledgebase", "scripts")
        os.makedirs(core)
        with open(os.path.join(core, "core.py"), "w", encoding="utf-8") as f:
            f.write('VERSION = "9.0.0"\n')
        code, out = run(self.t, *FULL)
        self.assertEqual(code, 2)
        self.assertIn("mới hơn engine trong gói", out)

    def test_no_fts5_simulated(self):
        env = dict(os.environ, KBINSTALL_TEST_NO_FTS5="1")
        r = subprocess.run([sys.executable, "-E", "-s", "-B", INSTALL, "--target", self.t], capture_output=True, timeout=60,
                           env=env, stdin=subprocess.DEVNULL)
        self.assertEqual(r.returncode, 2)
        self.assertIn("không có FTS5", r.stderr.decode("utf-8"))
        self.assertEqual(os.listdir(self.t), [])

    def test_bad_args(self):
        self.assertEqual(run(self.t, "--components", "engine,nope")[0], 2)
        self.assertEqual(run(self.t, "--project", "../x")[0], 2)
        self.assertEqual(run(os.path.join(self.t, "missing"))[0], 2)
        self.assertEqual(run(self.t, "--uninstall")[0], 2)          # no install record
        self.assertEqual(run(BUNDLE)[0], 2)                         # the bundle itself is not a target
        code, out = run(os.path.join(BUNDLE, "skills"))             # a folder inside the bundle
        self.assertEqual(code, 2)
        self.assertIn("nằm trong thư mục gói", out)

    def test_hash_in_path(self):
        # '#' / '?' in the target path must not break the read-only SQLite URI
        t = os.path.join(self._tmp.name, "dự#án ?x" if os.name != "nt" else "dự#án")
        os.makedirs(t)
        self.assertEqual(run(t, *FULL)[0], 0)
        code, data = run_json(t, *FULL)
        self.assertEqual(code, 0, data)
        self.assertNotIn("schema 1", " ".join(data["messages"]))


KB_SCRIPTS = ("kbwatch.py", "kbroute.py", "kbguard.py")
OLD_FORM = 'python -I -S "${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/%s"%s'      # hook command of 2.0.3 and older


def commands(settings):
    return [(ev, h) for ev, groups in (settings.get("hooks") or {}).items() for g in groups for h in g.get("hooks", [])]


def run_hook(command, project, event):
    """Run one hook command the way Claude Code does (shell string, CLAUDE_PROJECT_DIR set); exit code."""
    import shlex
    argv = shlex.split(command.replace("${CLAUDE_PROJECT_DIR:-.}", project.replace("\\", "/")))
    argv[0] = sys.executable
    r = subprocess.run(argv, input=json.dumps({"hook_event_name": event, "cwd": project, "prompt": "x",
                                               "tool_name": "Grep", "tool_input": {"path": "."}}).encode(),
                       capture_output=True, env=dict(os.environ, CLAUDE_PROJECT_DIR=project), cwd=project, timeout=60)
    return r.returncode


class HookSafetyTests(Base):
    """K2 and the old hook command form: no KB hook entry is ever left calling a missing script."""

    def settings(self, rel=".claude/settings.json"):
        return json.loads(read(os.path.join(self.t, *rel.split("/"))))

    def write(self, data, rel=".claude/settings.json"):
        path = os.path.join(self.t, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def test_k2_edited_hook_block_then_uninstall(self):
        self.write({"permissions": {"allow": ["Read"]}})
        code, out = run(self.t, *FULL)
        self.assertEqual(code, 0, out)
        s = self.settings()
        for _, h in commands(s):
            if any(n in h["command"] for n in KB_SCRIPTS):
                self.assertIn("runpy", h["command"])
        for _, h in commands(s):                                    # the owner edits every KB block (timeout)
            h["timeout"] = 9
        self.write(s)
        code, out = run(self.t, "--uninstall", "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertIn("bỏ 5 lệnh hook KB (5 khối)", out)
        left = self.settings()
        self.assertFalse(any(n in json.dumps(left) for n in KB_SCRIPTS), left)
        self.assertEqual(left["permissions"]["allow"], ["Read"])
        self.assertFalse(os.path.exists(os.path.join(self.t, ".claude", "hooks", "kbguard.py")))

    def test_hook_commands_exit_0_when_scripts_missing(self):
        code, out = run(self.t, *FULL)
        self.assertEqual(code, 0, out)
        cmds = commands(self.settings())
        self.assertEqual(len(cmds), 5)
        for ev, h in cmds:
            self.assertEqual(run_hook(h["command"], self.t, ev), 0, (ev, "installed"))
        shutil.rmtree(os.path.join(self.t, ".claude", "hooks"))
        for ev, h in cmds:
            self.assertEqual(run_hook(h["command"], self.t, ev), 0, (ev, "scripts missing"))

    def test_upgrade_rewrites_old_form_commands_keeps_edits(self):
        args = {"kbwatch.py": "", "kbroute.py": "", "kbguard.py": " pre"}
        old = {"hooks": {
            "SessionStart": [{"matcher": "startup", "hooks": [{"type": "command", "command": OLD_FORM % ("kbwatch.py", ""), "timeout": 9}]}],
            "UserPromptSubmit": [{"hooks": [{"type": "command", "command": OLD_FORM % ("kbroute.py", ""), "timeout": 5}]}],
            "PreToolUse": [{"matcher": "Grep|Glob", "hooks": [{"type": "command", "command": OLD_FORM % ("kbguard.py", args["kbguard.py"]), "timeout": 5}]}],
            "PostToolUse": [{"matcher": "Bash|PowerShell", "hooks": [{"type": "command", "command": OLD_FORM % ("kbguard.py", " post"), "timeout": 5}]}],
            "Stop": [{"hooks": [{"type": "command", "command": OLD_FORM % ("kbguard.py", " stop"), "timeout": 5}]}]}}
        self.write(old)
        code, out = run(self.t, *FULL)
        self.assertEqual(code, 0, out)
        self.assertIn("đổi 5 lệnh hook KB dạng cũ", out)
        s = self.settings()
        cmds = commands(s)
        self.assertEqual(len(cmds), 5, cmds)                        # no duplicate block next to the old one
        self.assertTrue(all("runpy" in h["command"] for _, h in cmds))
        self.assertEqual(s["hooks"]["SessionStart"][0]["hooks"][0]["timeout"], 9)
        self.assertEqual(s["hooks"]["SessionStart"][0]["matcher"], "startup")
        self.assertIn("'stop'", s["hooks"]["Stop"][0]["hooks"][0]["command"])

    def test_old_form_in_user_settings_file_holds_scripts(self):
        code, out = run(self.t, *FULL)
        self.assertEqual(code, 0, out)
        user_local = {"hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command", "command": OLD_FORM % ("kbroute.py", "")}]}]}}
        self.write(user_local, ".claude/settings.local.json")
        code, out = run(self.t, "--uninstall", "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertIn("settings.local.json: còn lệnh hook KB dạng cũ", out)
        self.assertIn("GIỮ .claude/hooks/kbroute.py", out)
        for n in ("kbroute.py", "kbcommon.py"):
            self.assertTrue(os.path.exists(os.path.join(self.t, ".claude", "hooks", n)), n)
        self.assertEqual(run_hook(OLD_FORM % ("kbroute.py", ""), self.t, "UserPromptSubmit"), 0)
        self.assertFalse(os.path.exists(os.path.join(self.t, ".claude", "skills", "q-knowledgebase", "scripts", "qkb.py")))
        os.remove(os.path.join(self.t, ".claude", "settings.local.json"))  # the owner removes the old command
        code, out = run(self.t, "--uninstall", "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertFalse(os.path.exists(os.path.join(self.t, ".claude", "hooks", "kbroute.py")))


class UpgradeTests(Base):
    def old(self, folder, label):
        if not os.path.isdir(os.path.join(folder, ".claude", "skills", "q-knowledgebase")):
            self.skipTest("old engine %s not available" % label)
        shutil.copytree(os.path.join(folder, ".claude"), os.path.join(self.t, ".claude"),
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        os.makedirs(os.path.join(self.t, "kb", "demo", "core"))
        with open(os.path.join(self.t, "kb", "demo", "core", "notes.md"), "w", encoding="utf-8") as f:
            f.write("# notes\n\n## Decisions\n\n- an old fact\n")
        os.makedirs(os.path.join(self.t, ".qkb"))
        with open(os.path.join(self.t, ".qkb", "config.json"), "w", encoding="utf-8") as f:
            json.dump({"project_name": "demo", "knowledge_paths": ["kb"], "source_paths": []}, f)
        code, _ = qkb(self.t, "build")
        self.assertIn(code, (0, 1))

    def test_t08_from_200_with_migrate(self):
        self.old(OLD_200, "2.0.0")
        code, out = run(self.t, *(FULL + ["--migrate"]))
        self.assertEqual(code, 0, out)
        self.assertIn("doctor đạt", out)
        code, data = qkb(self.t, "search", "old fact")
        self.assertEqual(code, 0)
        self.assertTrue(data.get("results"), data)

    def test_t09_from_200_without_migrate(self):
        self.old(OLD_200, "2.0.0")
        db = os.path.join(self.t, ".qkb", "cache", "index.sqlite3")
        with open(db, "rb") as f:
            before = hashlib.sha256(f.read()).hexdigest()
        code, out = run(self.t, *FULL)
        self.assertEqual(code, 0, out)
        self.assertIn("migrate --dry-run", out)
        with open(db, "rb") as f:
            self.assertEqual(hashlib.sha256(f.read()).hexdigest(), before)

    def test_failed_post_check_restores_index(self):
        # a failure at step 14 puts back files, settings AND the index
        self.old(OLD_B1, "2.1.0-b1")
        db = os.path.join(self.t, ".qkb", "cache", "index.sqlite3")
        import sqlite3
        con = sqlite3.connect(db)
        before = con.execute("SELECT value FROM meta WHERE key='last_indexed'").fetchone()[0]
        con.close()
        old_core = read(os.path.join(self.t, ".claude", "skills", "q-knowledgebase", "scripts", "core.py"))
        env = dict(os.environ, KBINSTALL_TEST_FAIL_STEP="14")
        r = subprocess.run([sys.executable, "-E", "-s", "-B", INSTALL, "--target", self.t] + FULL, capture_output=True,
                           timeout=600, env=env, stdin=subprocess.DEVNULL)
        out = r.stdout.decode("utf-8") + r.stderr.decode("utf-8")
        self.assertEqual(r.returncode, 4, out)
        self.assertIn("Đã trả lại file, cấu hình và chỉ mục", out)
        self.assertEqual(read(os.path.join(self.t, ".claude", "skills", "q-knowledgebase", "scripts", "core.py")), old_core)
        self.assertFalse(os.path.exists(os.path.join(self.t, ".claude", "hooks", "kbwatch.py")))
        con = sqlite3.connect(db)
        self.assertEqual(con.execute("SELECT value FROM meta WHERE key='last_indexed'").fetchone()[0], before)
        con.close()

    @unittest.skipUnless(os.name == "nt", "an open handle blocks a rename only on Windows")
    def test_t12_write_error_leaves_no_trace(self):
        # a write error at step 11 -> exit 4, files as before, no *.kbtmp, no new empty folders
        self.old(OLD_B1, "2.1.0-b1")
        def snapshot():
            # the index comes back through the SQLite backup API: same content, bytes may differ -> compare content
            import sqlite3
            files = {k: v for k, v in tree(self.t).items()
                     if not k.startswith(".qkb/backups/") and not k.startswith(".qkb/cache/index.sqlite3")}
            con = sqlite3.connect(os.path.join(self.t, ".qkb", "cache", "index.sqlite3"))
            try:
                files["<index>"] = (con.execute("SELECT key, value FROM meta ORDER BY key").fetchall(),
                                    con.execute("SELECT count(*) FROM sections").fetchone()[0])
            finally:
                con.close()
            return files
        dirs_before = sorted(d for d, _, _ in os.walk(self.t) if ".qkb" + os.sep + "backups" not in d)
        before = snapshot()
        locked = open(os.path.join(self.t, ".claude", "skills", "q-knowledgebase", "scripts", "core.py"), "rb")
        try:
            code, out = run(self.t, *FULL)
        finally:
            locked.close()
        self.assertEqual(code, 4, out)
        self.assertIn("Đã trả lại file, cấu hình", out)
        self.assertEqual(snapshot(), before)
        self.assertEqual([p for p in tree(self.t) if p.endswith(".kbtmp")], [])
        dirs_after = sorted(d for d, _, _ in os.walk(self.t) if ".qkb" + os.sep + "backups" not in d)
        self.assertEqual(dirs_after, dirs_before)

    def test_read_only_target_rolls_back_with_exit_4(self):
        # an unchanged read-only file needs no restore copy -> exit 4 ("đã trả lại"), not 5
        import stat
        self.old(OLD_B1, "2.1.0-b1")
        core = os.path.join(self.t, ".claude", "skills", "q-knowledgebase", "scripts", "core.py")
        before = read(core)
        os.chmod(core, stat.S_IREAD)
        try:
            code, out = run(self.t, *FULL)
        finally:
            os.chmod(core, stat.S_IWRITE | stat.S_IREAD)
        self.assertEqual(code, 4, out)
        self.assertEqual(read(core), before)

    def test_t10_t19_from_b1_then_restore(self):
        self.old(OLD_B1, "2.1.0-b1")
        old_core = read(os.path.join(self.t, ".claude", "skills", "q-knowledgebase", "scripts", "core.py"))
        code, data = run_json(self.t, *FULL)
        self.assertEqual(code, 0, data)
        self.assertIn("replace", {r["action"] for r in data["files"]})
        self.assertNotIn("conflict", {r["action"] for r in data["files"]})
        self.assertIn('VERSION = "%s"' % json.loads(read(os.path.join(BUNDLE, "MANIFEST.json")))["engine_version"], read(os.path.join(self.t, ".claude", "skills", "q-knowledgebase", "scripts",
                                                                "core.py")))
        code, out = run(self.t, "--restore-previous", "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertEqual(read(os.path.join(self.t, ".claude", "skills", "q-knowledgebase", "scripts", "core.py")), old_core)
        self.assertFalse(os.path.exists(os.path.join(self.t, ".claude", "hooks", "kbwatch.py")))
        self.assertFalse(os.path.exists(os.path.join(self.t, ".claude", "skills", "q-kb-search", "SKILL.md")))


class ContentTests(unittest.TestCase):
    def test_t22_no_cache_and_manifest_complete(self):
        manifest = json.loads(read(os.path.join(BUNDLE, "MANIFEST.json")))
        listed = {e["path"] for e in manifest["files"]}
        actual = set(tree(BUNDLE)) - {"MANIFEST.json"}
        self.assertEqual(actual, listed)
        self.assertFalse([p for p in actual if "__pycache__" in p or p.endswith(".pyc")])


if __name__ == "__main__":
    unittest.main()
