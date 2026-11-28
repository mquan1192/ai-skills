"""Test install.py của gói văn phong trên thư mục tạm (không đụng tới dự án nào). Chạy: python -B tests/test_install.py
STYLE_INSTALL=<đường dẫn install.py> chạy cùng bộ test trên một bản installer khác (dùng cho red proof)."""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

BUNDLE = Path(__file__).resolve().parent.parent
_src = Path(os.environ.get("STYLE_INSTALL") or (BUNDLE / "install.py"))
_spec = importlib.util.spec_from_file_location("install", _src)
install = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(install)
install.BUNDLE = BUNDLE


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = install.main(list(argv))
    return code, out.getvalue()


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="style-install-")
        self.target = Path(self.tmp.name) / "du-an"
        self.target.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def files(self):
        return sorted(p.relative_to(self.target).as_posix() for p in self.target.rglob("*") if p.is_file())

    def test_dry_run_writes_nothing(self):
        code, out = run("--target", str(self.target))
        self.assertEqual(code, 0, out)
        self.assertIn("Chạy thử", out)
        self.assertEqual(self.files(), [])

    def test_apply_installs_and_is_idempotent(self):
        code, out = run("--target", str(self.target), "--apply", "--yes")
        self.assertEqual(code, 0, out)
        for rel in (".claude/skills/q-writing-style/SKILL.md", ".claude/skills/q-writing-style/references/style-guide.md",
                    ".claude/skills/q-writing-style/references/document-patterns.md", ".claude/hooks/stylewatch.py",
                    "CLAUDE.md", ".claude/settings.json", ".writing-style/style.config.json",
                    ".writing-style/DOC-TRUOC.md", ".writing-style/install-record.json"):
            self.assertTrue((self.target / rel).is_file(), rel)
        self.assertFalse((self.target / ".claude/hooks/test_stylewatch.py").exists())
        self.assertIn("stylewatch.py", (self.target / ".claude/settings.json").read_text(encoding="utf-8"))
        before = self.files()
        code, out = run("--target", str(self.target), "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertIn("Sẽ ghi: 0 file", out)
        self.assertEqual(self.files(), before)

    def test_existing_claude_and_settings_never_overwritten(self):
        (self.target / ".claude").mkdir()
        for rel, text in (("CLAUDE.md", "# của tôi\n"), (".claude/settings.json", "{}\n")):
            (self.target / rel).write_text(text, encoding="utf-8")
        code, out = run("--target", str(self.target), "--apply", "--yes")
        self.assertEqual(code, 0, out)
        for rel, text in (("CLAUDE.md", "# của tôi\n"), (".claude/settings.json", "{}\n")):
            self.assertEqual((self.target / rel).read_text(encoding="utf-8"), text, rel)
        for rel in ("CLAUDE-fragment.md", "hooks.json"):
            self.assertTrue((self.target / ".writing-style/merge" / rel).is_file(), rel)

    def test_existing_skill_reported_with_diff_kept_then_adopted(self):
        own = self.target / ".claude/skills/q-writing-style/SKILL.md"
        own.parent.mkdir(parents=True)
        own.write_text("bản riêng của dự án\n", encoding="utf-8")
        code, out = run("--target", str(self.target), "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertIn("xung đột: 1", out)
        self.assertIn("dòng", out)
        self.assertIn("Dự án đã có skill q-writing-style", out)
        self.assertEqual(own.read_text(encoding="utf-8"), "bản riêng của dự án\n")
        code, out = run("--target", str(self.target), "--apply", "--yes", "--adopt")
        self.assertEqual(code, 0, out)
        self.assertNotEqual(own.read_text(encoding="utf-8"), "bản riêng của dự án\n")
        self.assertEqual(len(list((self.target / ".writing-style/backup").rglob("SKILL.md"))), 1)
        code, out = run("--target", str(self.target), "--uninstall", "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertEqual(own.read_text(encoding="utf-8"), "bản riêng của dự án\n")

    def test_uninstall_by_hash_keeps_edited_files(self):
        run("--target", str(self.target), "--apply", "--yes")
        cfg = self.target / ".writing-style/style.config.json"
        cfg.write_text(cfg.read_text(encoding="utf-8").replace('"glossary": ""', '"glossary": "docs/glossary.md"'),
                       encoding="utf-8")
        code, out = run("--target", str(self.target), "--uninstall", "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.files(), [".writing-style/style.config.json"])

    def test_upgrade_refreshes_untouched_skill_file(self):
        run("--target", str(self.target), "--apply", "--yes")
        f = self.target / ".claude/skills/q-writing-style/references/style-guide.md"
        f.write_text("bản cũ của gói\n", encoding="utf-8")
        rec_path = self.target / install.RECORD
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
        rec["files"][".claude/skills/q-writing-style/references/style-guide.md"] = install.sha256(f)
        rec["version"] = "0.9"
        rec_path.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        code, out = run("--target", str(self.target), "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertIn("nâng cấp từ bản 0.9", out)
        self.assertEqual(install.sha256(f), install.sha256(BUNDLE / "skills/q-writing-style/references/style-guide.md"))

    def _fake_legacy_install(self, edited=False):
        """Bản ghi như một lần cài trước 1.2.0: skill tên q-doc-edit do gói cài."""
        run("--target", str(self.target), "--apply", "--yes")
        rec_path = self.target / install.RECORD
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
        old = {}
        for rel in ("SKILL.md", "references/style-guide.md"):
            f = self.target / ".claude/skills/q-doc-edit" / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("bản cũ %s\n" % rel, encoding="utf-8")
            rec["files"][".claude/skills/q-doc-edit/" + rel] = install.sha256(f)
            old[rel] = f
        rec["version"] = "1.1.0"
        rec_path.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        if edited:
            old["SKILL.md"].write_text("chủ dự án đã sửa\n", encoding="utf-8")
        return old

    def test_upgrade_removes_untouched_legacy_skill(self):
        self._fake_legacy_install()
        code, out = run("--target", str(self.target))
        self.assertEqual(code, 0, out)
        self.assertIn("không còn trong bản này", out)
        self.assertTrue((self.target / ".claude/skills/q-doc-edit/SKILL.md").exists())      # dry run
        code, out = run("--target", str(self.target), "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertFalse((self.target / ".claude/skills/q-doc-edit").exists())
        self.assertTrue((self.target / ".claude/skills/q-writing-style/SKILL.md").is_file())
        self.assertEqual(len(list((self.target / ".writing-style/backup").rglob("q-doc-edit/SKILL.md"))), 1)
        rec = json.loads((self.target / install.RECORD).read_text(encoding="utf-8"))
        self.assertFalse(any(r.startswith(".claude/skills/q-doc-edit/") for r in rec["files"]))
        code, out = run("--target", str(self.target), "--uninstall", "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertFalse((self.target / ".claude/skills").exists())

    def test_upgrade_keeps_edited_legacy_file(self):
        old = self._fake_legacy_install(edited=True)
        code, out = run("--target", str(self.target), "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertIn("đã sửa sau khi cài → giữ nguyên", out)
        self.assertEqual(old["SKILL.md"].read_text(encoding="utf-8"), "chủ dự án đã sửa\n")
        self.assertFalse(old["references/style-guide.md"].exists())

    def test_foreign_legacy_skill_reported_not_touched(self):
        own = self.target / ".claude/skills/q-doc-edit/SKILL.md"
        own.parent.mkdir(parents=True)
        own.write_text("skill riêng\n", encoding="utf-8")
        code, out = run("--target", str(self.target), "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertIn("không do gói cài", out)
        self.assertEqual(own.read_text(encoding="utf-8"), "skill riêng\n")

    def test_hooks_only_install_does_not_touch_skills(self):
        self._fake_legacy_install()
        code, out = run("--target", str(self.target), "--apply", "--yes", "--components", "hooks")
        self.assertEqual(code, 0, out)
        self.assertTrue((self.target / ".claude/skills/q-doc-edit/SKILL.md").exists())

    def test_tampered_bundle_refused(self):
        copy = Path(self.tmp.name) / "bundle"
        shutil.copytree(BUNDLE, copy, ignore=shutil.ignore_patterns("__pycache__"))
        with open(copy / "skills/q-writing-style/SKILL.md", "a", encoding="utf-8") as f:
            f.write("\nsửa lén\n")
        spec = importlib.util.spec_from_file_location("install_copy", copy / "install.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = mod.main(["--target", str(self.target), "--apply", "--yes"])
        self.assertEqual(code, 2)
        self.assertIn("MANIFEST", out.getvalue())
        self.assertEqual(self.files(), [])

    def test_paths_outside_target_refused(self):
        for bad in ("../ra-ngoai.md", "C:/x.md", "/tuyet-doi.md", "a/../../b.md"):
            with self.assertRaises(install.InstallError):
                install.inside(self.target.resolve(), bad)

    def test_target_inside_bundle_refused(self):
        code, out = run("--target", str(BUNDLE / "skills"))
        self.assertEqual(code, 2)
        self.assertIn("DỪNG", out)


HOOKS_JSON = Path(os.environ.get("STYLE_HOOKS_JSON") or (BUNDLE / "hooks/hooks.json"))


class HookSafetyTests(unittest.TestCase):
    """A hook entry must never block a prompt when its script is missing."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="style-h1-")
        self.target = Path(self.tmp.name) / "du-an"
        self.target.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def commands(self):
        data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        return [h["command"] for groups in data["hooks"].values() for g in groups for h in g["hooks"]]

    def run_command(self, command, payload):
        import shlex
        import subprocess
        argv = shlex.split(command)
        argv[0] = sys.executable if argv[0] == "python" else argv[0]
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.target))
        r = subprocess.run(argv, input=json.dumps(payload, ensure_ascii=False).encode("utf-8"), capture_output=True,
                           env=env, cwd=str(self.target), timeout=20)
        return r.returncode, r.stdout.decode("ascii", "replace")

    def test_a_components_without_hooks_write_no_hook_entry(self):
        code, out = run("--target", str(self.target), "--apply", "--yes", "--components", "skills,docs")
        self.assertEqual(code, 0, out)
        self.assertFalse((self.target / ".claude/settings.json").exists())
        self.assertFalse((self.target / ".writing-style/merge/hooks.json").exists())
        (self.target / ".claude/settings.json").write_text("{}\n", encoding="utf-8")       # settings of the project
        code, out = run("--target", str(self.target), "--apply", "--yes", "--components", "skills,docs")
        self.assertEqual(code, 0, out)
        self.assertFalse((self.target / ".writing-style/merge/hooks.json").exists())

    def test_b_hook_command_with_missing_script_exits_0(self):
        payload = {"hook_event_name": "UserPromptSubmit", "prompt": "Viết báo cáo tuần", "cwd": str(self.target)}
        for command in self.commands():
            code, out = self.run_command(command, payload)
            self.assertEqual(code, 0, command)           # exit 2 would block every prompt
            self.assertEqual(out, "")

    def test_b_hook_command_with_script_reminds(self):
        run("--target", str(self.target), "--apply", "--yes")
        payload = {"hook_event_name": "UserPromptSubmit", "prompt": "Viết báo cáo tuần", "cwd": str(self.target)}
        code, out = self.run_command(self.commands()[0], payload)
        self.assertEqual(code, 0)
        self.assertIn("q-writing-style", json.loads(out)["hookSpecificOutput"]["additionalContext"])

    def test_c_uninstall_strips_bundle_hook_from_edited_settings(self):
        run("--target", str(self.target), "--apply", "--yes")
        s = self.target / ".claude/settings.json"
        data = json.loads(s.read_text(encoding="utf-8"))
        data["permissions"] = {"allow": ["Read"]}                                   # edited after install
        s.write_text(json.dumps(data), encoding="utf-8")
        code, out = run("--target", str(self.target), "--uninstall", "--apply", "--yes")
        self.assertEqual(code, 0, out)
        left = json.loads(s.read_text(encoding="utf-8"))
        self.assertNotIn("stylewatch.py", json.dumps(left))
        self.assertEqual(left["permissions"], {"allow": ["Read"]})

    def test_c_uninstall_warns_on_hand_merged_hook(self):
        s = self.target / ".claude/settings.json"
        s.parent.mkdir(parents=True)
        s.write_text("{}\n", encoding="utf-8")
        run("--target", str(self.target), "--apply", "--yes")
        merged = json.loads((self.target / ".writing-style/merge/hooks.json").read_text(encoding="utf-8"))
        s.write_text(json.dumps(merged), encoding="utf-8")                          # owner merged by hand
        before = s.read_text(encoding="utf-8")
        code, out = run("--target", str(self.target), "--uninstall", "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertIn("gộp tay", out)
        self.assertIn("README_VN.md § 6", out)
        self.assertEqual(s.read_text(encoding="utf-8"), before)


class LauncherTests(unittest.TestCase):
    """Lệnh Python đứng đầu lệnh hook: tự dò theo máy (python → python3 → py -3) hoặc do --python chỉ định."""
    SCRIPT = "stylewatch.py"
    MERGE = ".writing-style/merge/hooks.json"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="launcher-")
        self.target = Path(self.tmp.name) / "demo"
        self.target.mkdir()
        self._probe = install.pylauncher.probe

    def tearDown(self):
        install.pylauncher.probe = self._probe
        install.LAUNCHER = "python"
        self.tmp.cleanup()

    def only(self, *names):
        """Giả lập máy chỉ có các lệnh Python này (ví dụ macOS / Linux chỉ có python3)."""
        good = {"version": [3, 14, 0], "fts5": True, "executable": "x"}
        install.pylauncher.probe = lambda command, timeout=20: good if command in names else None

    def commands(self, rel=".claude/settings.json"):
        data = json.loads((self.target / rel).read_text(encoding="utf-8"))
        return [h["command"] for groups in data["hooks"].values() for g in groups for h in g["hooks"]]

    def test_machine_with_only_python3(self):
        self.only("python3")
        code, out = run("--target", str(self.target), "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertIn("`python` không chạy được", out)
        cmds = self.commands()
        self.assertTrue(cmds and all(c.startswith("python3 -I -S -c ") for c in cmds), cmds)
        code, out = run("--target", str(self.target), "--apply", "--yes")          # chạy lại: không đổi gì
        self.assertEqual(code, 0, out)
        self.assertIn(".claude/settings.json đã có nội dung của bản này", out)
        self.assertEqual(self.commands(), cmds)
        code, out = run("--target", str(self.target), "--uninstall", "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertFalse((self.target / ".claude/settings.json").exists())

    def test_python_available_keeps_bundle_bytes(self):
        self.only("python", "python3")
        code, out = run("--target", str(self.target), "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertEqual((self.target / ".claude/settings.json").read_bytes(), (BUNDLE / "hooks/hooks.json").read_bytes())

    def test_launcher_in_project_is_kept_then_refreshed_when_it_stops_working(self):
        self.only("python3")
        run("--target", str(self.target), "--apply", "--yes")
        self.only("python", "python3")                 # máy khác trong nhóm có cả hai: giữ python3, không đổi qua lại
        code, out = run("--target", str(self.target), "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertTrue(all(c.startswith("python3 ") for c in self.commands()))
        self.only("py -3")                             # máy chỉ có py -3: tệp do gói tạo, chưa ai sửa → thay
        code, out = run("--target", str(self.target), "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertTrue(all(c.startswith("py -3 -I -S -c ") for c in self.commands()), self.commands())

    def test_explicit_launcher_is_really_runnable(self):
        import os
        import shlex
        import subprocess
        me = install.pylauncher.normalize(sys.executable)
        code, out = run("--target", str(self.target), "--apply", "--yes", "--python", sys.executable)
        self.assertEqual(code, 0, out)
        cmds = self.commands()
        self.assertTrue(all(c.startswith(me + " -I -S -c ") for c in cmds), cmds)
        r = subprocess.run(shlex.split(cmds[0]), input=b"{}", capture_output=True, timeout=30, cwd=str(self.target),
                           env=dict(os.environ, CLAUDE_PROJECT_DIR=str(self.target)))
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_no_usable_python_writes_nothing(self):
        self.only()
        code, out = run("--target", str(self.target), "--apply", "--yes")
        self.assertEqual(code, 2, out)
        self.assertIn("--python", out)
        self.assertEqual(list(self.target.iterdir()), [])
        code, out = run("--target", str(self.target), "--apply", "--yes", "--python", "python; x")
        self.assertEqual(code, 2, out)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_owner_settings_with_other_launcher_is_reported_not_edited(self):
        self.only("python3")
        s = self.target / ".claude/settings.json"
        s.parent.mkdir(parents=True)
        mine = json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command":
            "python -I -S -c \"import os,runpy;p=os.path.join('.claude','hooks','" + self.SCRIPT
            + "');os.path.isfile(p) and runpy.run_path(p,run_name='__main__')\""}]}]}})
        s.write_text(mine, encoding="utf-8")
        code, out = run("--target", str(self.target), "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertIn("đang bắt đầu bằng `python`, lần cài này dùng `python3`", out)
        self.assertEqual(s.read_text(encoding="utf-8"), mine)
        self.assertTrue(all(c.startswith("python3 -I -S -c ") for c in self.commands(self.MERGE)))


if __name__ == "__main__":
    unittest.main()
