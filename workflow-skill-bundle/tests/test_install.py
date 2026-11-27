"""Test install.py trên thư mục tạm (không đụng tới dự án nào). Chạy: python -B tests/test_install.py"""
import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

BUNDLE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUNDLE))
import install  # noqa: E402


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = install.main(list(argv))
    return code, out.getvalue()


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-install-")
        self.target = Path(self.tmp.name) / "demo"
        self.target.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def files(self):
        return sorted(p.relative_to(self.target).as_posix() for p in self.target.rglob("*") if p.is_file())

    def test_dry_run_writes_nothing(self):
        code, out = run("--target", str(self.target))
        self.assertEqual(code, 0)
        self.assertIn("Chạy thử", out)
        self.assertEqual(self.files(), [])

    def test_apply_installs_and_is_idempotent(self):
        code, out = run("--target", str(self.target), "--apply", "--yes", "--owner-name", "trưởng phòng")
        self.assertEqual(code, 0, out)
        cfg = json.loads((self.target / ".workflow/workflow.config.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["owner_name"], "trưởng phòng")
        for rel in (".claude/skills/q-wf-team/SKILL.md", ".claude/skills/q-wf-lead/SKILL.md", ".claude/skills/q-wf-card/SKILL.md",
                    "scripts/process/CardFlow.psm1", "scripts/process/ticket.ps1", ".claude/hooks/turnlog.py",
                    "CLAUDE.md", "AGENTS.md", ".claude/settings.json", "docs/process/ROLES.md", "docs/process/STATUS.md",
                    "docs/cards/_TEMPLATE/CARD.md", "lead/board.md", "docs/process/POLICY.md", ".workflow/install-record.json",
                    ".claude/hooks/ctxwatch.py", "docs/process/RULES-HISTORY.md", ".claude/skills/q-wf-team/references/quy-tac-bo-sung.md"):
            self.assertTrue((self.target / rel).is_file(), rel)
        self.assertFalse((self.target / ".claude/hooks/test_ctxwatch.py").exists())     # test của hook không được cài
        settings = json.loads((self.target / ".claude/settings.json").read_text(encoding="utf-8"))
        self.assertIn("ctxwatch.py", json.dumps(settings))
        before = self.files()
        code, out = run("--target", str(self.target), "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertIn("Sẽ ghi: 0 file", out)
        self.assertEqual(self.files(), before)

    def test_existing_claude_agents_settings_never_overwritten(self):
        (self.target / ".claude").mkdir()
        for rel, text in (("CLAUDE.md", "# của tôi\n"), ("AGENTS.md", "# của tôi\n"), (".claude/settings.json", "{}\n")):
            (self.target / rel).write_text(text, encoding="utf-8")
        code, out = run("--target", str(self.target), "--apply", "--yes")
        self.assertEqual(code, 0, out)
        for rel, text in (("CLAUDE.md", "# của tôi\n"), ("AGENTS.md", "# của tôi\n"), (".claude/settings.json", "{}\n")):
            self.assertEqual((self.target / rel).read_text(encoding="utf-8"), text, rel)
        for rel in ("CLAUDE-fragment.md", "AGENTS.workflow.md", "hooks.json"):
            self.assertTrue((self.target / ".workflow/merge" / rel).is_file(), rel)

    def test_foreign_file_is_a_conflict_unless_adopt(self):
        dest = self.target / ".claude/skills/q-wf-team/SKILL.md"
        dest.parent.mkdir(parents=True)
        dest.write_text("bản khác\n", encoding="utf-8")
        code, out = run("--target", str(self.target), "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertIn("xung đột: 1", out)
        self.assertEqual(dest.read_text(encoding="utf-8"), "bản khác\n")
        code, out = run("--target", str(self.target), "--apply", "--yes", "--adopt")
        self.assertEqual(code, 0, out)
        self.assertNotEqual(dest.read_text(encoding="utf-8"), "bản khác\n")
        backups = list((self.target / ".workflow/backup").rglob("SKILL.md"))
        self.assertEqual(len(backups), 1)
        code, out = run("--target", str(self.target), "--uninstall", "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertEqual(dest.read_text(encoding="utf-8"), "bản khác\n")    # khôi phục bản trước --adopt

    def test_uninstall_keeps_edited_files(self):
        run("--target", str(self.target), "--apply", "--yes")
        board = self.target / "lead/board.md"
        board.write_text(board.read_text(encoding="utf-8") + "\n| TASK-1 | việc thật |\n", encoding="utf-8")
        code, out = run("--target", str(self.target), "--uninstall", "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.files(), ["lead/board.md"])

    def _adopted(self):
        own = self.target / ".claude/skills/q-wf-team/SKILL.md"
        own.parent.mkdir(parents=True)
        own.write_text("MINE\n", encoding="utf-8")
        code, out = run("--target", str(self.target), "--adopt", "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertNotEqual(own.read_text(encoding="utf-8"), "MINE\n")
        return own

    def test_uninstall_keeps_owner_edit_of_adopted_file(self):
        # File sao lưu khi cài (--adopt) rồi chủ dự án sửa sau khi cài → gỡ KHÔNG chép bản sao lưu đè lên
        own = self._adopted()
        edited = own.read_text(encoding="utf-8") + "\nSỬA SAU KHI CÀI\n"
        own.write_text(edited, encoding="utf-8")
        code, out = run("--target", str(self.target), "--uninstall", "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertEqual(own.read_text(encoding="utf-8"), edited)
        self.assertIn("đã sửa sau khi cài — giữ nguyên; bản trước khi cài: .workflow/backup/", out)

    def test_uninstall_restores_untouched_adopted_file(self):
        own = self._adopted()
        code, out = run("--target", str(self.target), "--uninstall", "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertEqual(own.read_text(encoding="utf-8"), "MINE\n")

    def test_partial_install_then_uninstall(self):
        # Lỗi giữa lúc chép → bản ghi từng bước có sẵn → --uninstall gỡ sạch phần đã ghi
        notes = self.target / "ghi-chu.md"
        notes.write_text("của chủ dự án\n", encoding="utf-8")
        real = install.shutil.copyfile
        calls = {"n": 0}

        def flaky(src, dst, *a, **k):
            calls["n"] += 1
            if calls["n"] == 6:
                with open(dst, "w", encoding="utf-8") as f:
                    f.write("chép dở")
                raise OSError("lỗi giả giữa chừng")
            return real(src, dst, *a, **k)

        install.shutil.copyfile = flaky
        try:
            code, out = run("--target", str(self.target), "--apply", "--yes")
        finally:
            install.shutil.copyfile = real
        self.assertEqual(code, 2, out)
        self.assertIn("Cài dở dang", out)
        record = json.loads((self.target / install.RECORD).read_text(encoding="utf-8"))
        self.assertFalse(record["complete"])
        self.assertEqual(len(record["files"]), 5)
        self.assertTrue(record.get("pending"))
        code, out = run("--target", str(self.target), "--uninstall", "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertIn("dừng giữa chừng", out)
        self.assertEqual(self.files(), ["ghi-chu.md"])
        self.assertEqual([p.name for p in self.target.iterdir()], ["ghi-chu.md"])

    def test_tampered_bundle_refused(self):
        copy = Path(self.tmp.name) / "bundle"
        shutil.copytree(BUNDLE, copy, ignore=shutil.ignore_patterns("__pycache__"))
        with open(copy / "skills/q-wf-team/SKILL.md", "a", encoding="utf-8") as f:
            f.write("\nsửa lén\n")
        sys.path.insert(0, str(copy))
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("install_copy", copy / "install.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = mod.main(["--target", str(self.target), "--apply", "--yes"])
        finally:
            sys.path.remove(str(copy))
        self.assertEqual(code, 2)
        self.assertIn("MANIFEST", out.getvalue())
        self.assertEqual(self.files(), [])

    def test_paths_outside_target_refused(self):
        for bad in ("../ra-ngoai.md", "C:/x.md", "/tuyet-doi.md", "a/../../b.md"):
            with self.assertRaises(install.InstallError):
                install.inside(self.target.resolve(), bad)

    def test_target_inside_bundle_refused(self):
        code, out = run("--target", str(BUNDLE / "docs"))
        self.assertEqual(code, 2)
        self.assertIn("DỪNG", out)


    # ---- nâng cấp (bản 1.1): tệp gói chưa sửa được cập nhật, tệp chủ dự án đã sửa được giữ ----
    def _fake_old(self, rel, text, key="files"):
        f = self.target / rel
        f.write_text(text, encoding="utf-8")
        rec_path = self.target / install.RECORD
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
        rec[key][rel] = install.sha256(f)
        rec["version"] = "1.0"
        rec_path.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        return f

    def test_upgrade_updates_untouched_keeps_edited(self):
        run("--target", str(self.target), "--apply", "--yes")
        old = self._fake_old(".claude/skills/q-wf-lead/SKILL.md", "bản 1.0 của gói\n")
        edited = self.target / ".claude/skills/q-wf-card/SKILL.md"
        edited.write_text(edited.read_text(encoding="utf-8") + "\nchủ dự án sửa\n", encoding="utf-8")
        mine = edited.read_text(encoding="utf-8")
        code, out = run("--target", str(self.target), "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertIn("nâng cấp từ bản 1.0", out)
        self.assertEqual(install.sha256(old), install.sha256(BUNDLE / "skills/q-wf-lead/SKILL.md"))
        self.assertEqual(edited.read_text(encoding="utf-8"), mine)
        self.assertIn("xung đột: 1", out)

    def test_upgrade_refreshes_untouched_seeded_agents(self):
        run("--target", str(self.target), "--apply", "--yes")
        agents = self._fake_old("AGENTS.md", "# AGENTS bản 1.0\n", key="seeded")
        code, out = run("--target", str(self.target), "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertEqual(install.sha256(agents), install.sha256(BUNDLE / "AGENTS.md"))
        self.assertEqual(len(list((self.target / ".workflow/backup").rglob("AGENTS.md"))), 1)

    def test_upgrade_old_fragment_goes_to_merge(self):
        claude = self.target / "CLAUDE.md"
        text = "# của tôi\n\n" + install.FRAG_BEGIN + "\n## Quy trình nhóm (gói workflow v1.0)\n" + install.FRAG_END + "\n"
        claude.write_text(text, encoding="utf-8")
        code, out = run("--target", str(self.target), "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertIn("bản cũ", out)
        self.assertEqual(claude.read_text(encoding="utf-8"), text)
        self.assertTrue((self.target / ".workflow/merge/CLAUDE-fragment.md").is_file())

    # ---- an toàn hook: lệnh hook không bao giờ chặn prompt khi thiếu script ----
    def _hook_commands(self):
        data = json.loads((BUNDLE / "hooks/hooks.json").read_text(encoding="utf-8"))
        return [(ev, h["command"]) for ev, groups in data["hooks"].items() for g in groups for h in g["hooks"]]

    def test_hook_commands_exit_0_when_script_missing(self):
        import os
        import shlex
        import subprocess
        for ev, command in self._hook_commands():
            argv = shlex.split(command)
            argv[0] = sys.executable
            r = subprocess.run(argv, input=json.dumps({"hook_event_name": ev, "cwd": str(self.target)}).encode(),
                               capture_output=True, env=dict(os.environ, CLAUDE_PROJECT_DIR=str(self.target)), timeout=20)
            self.assertEqual(r.returncode, 0, (ev, command))

    def test_components_without_hooks_write_no_hook_entry(self):
        code, out = run("--target", str(self.target), "--apply", "--yes", "--components", "skills,scripts,templates,docs")
        self.assertEqual(code, 0, out)
        self.assertFalse((self.target / ".claude/settings.json").exists())
        self.assertFalse((self.target / ".workflow/merge/hooks.json").exists())

    def test_uninstall_strips_bundle_hooks_from_edited_settings(self):
        run("--target", str(self.target), "--apply", "--yes")
        s = self.target / ".claude/settings.json"
        data = json.loads(s.read_text(encoding="utf-8"))
        data["permissions"] = {"allow": ["Read"]}
        s.write_text(json.dumps(data), encoding="utf-8")
        code, out = run("--target", str(self.target), "--uninstall", "--apply", "--yes")
        self.assertEqual(code, 0, out)
        left = json.loads(s.read_text(encoding="utf-8"))
        self.assertNotIn("turnlog.py", json.dumps(left))
        self.assertNotIn("ctxwatch.py", json.dumps(left))
        self.assertEqual(left["permissions"], {"allow": ["Read"]})

    # ---- U1: v1.0 + khối hook gộp tay dạng cũ → nâng 1.1 → gỡ ----
    LEGACY = 'python -I -S "${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/turnlog.py"'

    def _owner_settings(self, command):
        s = self.target / ".claude/settings.json"
        s.parent.mkdir(parents=True, exist_ok=True)
        hooks = {ev: [{"hooks": [{"type": "command", "command": command}]}]
                 for ev in ("SessionStart", "UserPromptSubmit", "Stop", "SubagentStop")}
        s.write_text(json.dumps({"permissions": {"allow": ["Read"]}, "hooks": hooks}), encoding="utf-8")
        return s

    def test_u1_upgrade_from_10_hand_merged_legacy_hook_then_uninstall(self):
        s = self._owner_settings(self.LEGACY)
        run("--target", str(self.target), "--apply", "--yes")              # như bản 1.0 đã cài
        rec_path = self.target / install.RECORD
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
        rec["version"] = "1.0"
        rec_path.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        code, out = run("--target", str(self.target), "--apply", "--yes")  # nâng cấp
        self.assertEqual(code, 0, out)
        self.assertIn("dạng cũ (v1.0)", out)
        self.assertIn(".workflow/merge/hooks.json", out)
        self.assertTrue((self.target / ".workflow/merge/hooks.json").is_file())
        code, out = run("--target", str(self.target), "--uninstall", "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertIn("dạng cũ (v1.0)", out)
        self.assertNotIn("thoát 0", out)
        script = self.target / ".claude/hooks/turnlog.py"
        self.assertTrue(script.is_file(), "script gọi bởi lệnh dạng cũ phải được giữ")
        self.assertIn("turnlog.py", s.read_text(encoding="utf-8"))   # settings của chủ dự án không bị sửa
        # chủ dự án thay khối hook cũ theo README § 6 → gỡ lại thì script được xóa
        s.write_text(json.dumps({"permissions": {"allow": ["Read"]}}), encoding="utf-8")
        code, out = run("--target", str(self.target), "--uninstall", "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertFalse(script.exists())
        self.assertFalse((self.target / install.RECORD).exists())

    def test_uninstall_safe_hand_merged_hook_removes_scripts(self):
        safe = self._hook_commands()[0][1]
        self.assertTrue(install.is_safe_hook_command(safe))
        self._owner_settings(safe)
        run("--target", str(self.target), "--apply", "--yes")
        code, out = run("--target", str(self.target), "--uninstall", "--apply", "--yes")
        self.assertEqual(code, 0, out)
        self.assertNotIn("dạng cũ", out)
        self.assertIn("thoát 0", out)
        self.assertFalse((self.target / ".claude/hooks/turnlog.py").exists())


if __name__ == "__main__":
    unittest.main()
