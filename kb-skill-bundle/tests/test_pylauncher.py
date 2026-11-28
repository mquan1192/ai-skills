"""Tests of tools/pylauncher.py and of the Python launcher install.py writes into a project. Stdlib only; temp folders only.

Run from the bundle folder:  python -B tests/test_pylauncher.py   (macOS / Linux: python3 -B tests/test_pylauncher.py)
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

os.environ["KBINSTALL_TEST_NO_MODEL_SEARCH"] = "1"
BUNDLE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
INSTALL = os.path.join(BUNDLE, "install.py")
sys.path.insert(0, os.path.join(BUNDLE, "tools"))
import pylauncher  # noqa: E402
import settings_fragment  # noqa: E402

FULL = ["--apply", "--yes", "--model", "none", "--project", "demo", "--sub", "core"]
ME = pylauncher.normalize(sys.executable)
GOOD = {"version": [3, 14, 0], "fts5": True, "executable": "x"}


def fake(table):
    return lambda command: table.get(command)


class ChooseTests(unittest.TestCase):
    def test_first_usable_candidate_wins(self):
        name, info, tried = pylauncher.choose((3, 10), probe_fn=fake({"python": GOOD, "python3": GOOD}))
        self.assertEqual((name, tried), ("python", []))

    def test_missing_python_falls_back_to_python3(self):          # macOS / Linux: no `python` on PATH
        name, _, tried = pylauncher.choose((3, 10), probe_fn=fake({"python3": GOOD}))
        self.assertEqual(name, "python3")
        self.assertEqual(tried, [("python", "không chạy được")])

    def test_store_shortcut_falls_back_to_py_launcher(self):       # Windows: python / python3 are Store shortcuts
        name, _, _ = pylauncher.choose((3, 10), probe_fn=fake({"py -3": GOOD}))
        self.assertEqual(name, "py -3")

    def test_old_python_is_refused(self):                          # `python` = Python 2 / 3.8
        table = {"python": {"version": [2, 7, 18], "fts5": True, "executable": "x"}, "python3": GOOD}
        name, _, tried = pylauncher.choose((3, 10), probe_fn=fake(table))
        self.assertEqual(name, "python3")
        self.assertIn("2.7", tried[0][1])

    def test_fts5_needed(self):
        table = {"python": dict(GOOD, fts5=False), "python3": GOOD}
        self.assertEqual(pylauncher.choose((3, 10), need_fts5=True, probe_fn=fake(table))[0], "python3")
        self.assertEqual(pylauncher.choose((3, 10), probe_fn=fake(table))[0], "python")

    def test_launcher_already_in_project_is_kept(self):            # a mixed team does not flip the shared settings
        name, _, _ = pylauncher.choose((3, 10), existing=["python3"], probe_fn=fake({"python": GOOD, "python3": GOOD}))
        self.assertEqual(name, "python3")

    def test_explicit_is_used_alone(self):
        self.assertEqual(pylauncher.choose((3, 10), explicit="py -3", probe_fn=fake({"python": GOOD, "py -3": GOOD}))[0], "py -3")
        with self.assertRaises(pylauncher.LauncherError):
            pylauncher.choose((3, 10), explicit="python3", probe_fn=fake({"python": GOOD}))

    def test_nothing_usable_names_every_try(self):
        with self.assertRaises(pylauncher.LauncherError) as ctx:
            pylauncher.choose((3, 10), probe_fn=fake({}))
        for name in pylauncher.CANDIDATES:
            self.assertIn("`%s`" % name, str(ctx.exception))


class TextTests(unittest.TestCase):
    def test_tokens(self):
        self.assertEqual(pylauncher.tokens("py -3"), ["py", "-3"])
        self.assertEqual(pylauncher.tokens('"C:/Program Files/Python/python.exe" -X utf8'),
                         ["C:/Program Files/Python/python.exe", "-X", "utf8"])

    def test_normalize(self):
        self.assertEqual(pylauncher.normalize("  python3 "), "python3")
        self.assertEqual(pylauncher.normalize("C:\\Python314\\python.exe"), "C:/Python314/python.exe")
        for bad in ("", "python; rm -rf x", "python && x", "$(x)", "python | x", "py'thon"):
            with self.assertRaises(pylauncher.LauncherError):
                pylauncher.normalize(bad)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "my python")
            open(path, "w").close()
            self.assertEqual(pylauncher.normalize(path), '"%s"' % path.replace("\\", "/"))

    def test_launcher_of_and_swap(self):
        safe = settings_fragment.safe_command("kbguard.py", "pre", "py -3")
        self.assertEqual(pylauncher.launcher_of(safe), "py -3")
        self.assertEqual(pylauncher.swap(safe, "python3"), settings_fragment.safe_command("kbguard.py", "pre", "python3"))
        self.assertEqual(pylauncher.launcher_of("python -E -s -B .claude/skills/q-knowledgebase/scripts/qkb.py status"), "python")
        self.assertIsNone(pylauncher.launcher_of("node build.js"))
        self.assertEqual(pylauncher.swap("node build.js", "python3"), "node build.js")

    def test_probe_real_interpreter(self):
        info = pylauncher.probe(ME)
        self.assertEqual(tuple(info["version"]), tuple(sys.version_info[:3]))
        self.assertIsNone(pylauncher.probe("no-such-python-launcher-xyz"))
        self.assertTrue(pylauncher.has_modules(ME, ("json",)))
        self.assertFalse(pylauncher.has_modules(ME, ("no_such_module_xyz",)))

    def test_fragment_and_upgrade_use_the_launcher(self):
        frag = settings_fragment.fragment("python3")
        cmds = [h["command"] for blocks in frag.values() for b in blocks for h in b["hooks"]]
        self.assertTrue(cmds and all(c.startswith("python3 -I -S -c ") for c in cmds))
        mine = {"type": "command", "command": "python mine.py"}
        settings = {"hooks": {"Stop": [{"hooks": [mine, {"type": "command", "timeout": 9,
                                                         "command": settings_fragment.safe_command("kbguard.py", "stop")}]}]}}
        new, old_form, switched = settings_fragment.upgrade_commands(settings, "python3")
        self.assertEqual((old_form, switched), (0, 1))
        entries = new["hooks"]["Stop"][0]["hooks"]
        self.assertEqual(entries[0], mine)                                        # someone else's hook is not touched
        self.assertEqual(entries[1], {"type": "command", "timeout": 9,
                                      "command": settings_fragment.safe_command("kbguard.py", "stop", "python3")})
        self.assertEqual(settings_fragment.upgrade_commands(new, "python3")[1:], (0, 0))


def install(target, *args, env=None):
    r = subprocess.run([sys.executable, "-E", "-s", "-B", INSTALL, "--target", target] + list(args), capture_output=True,
                       timeout=600, stdin=subprocess.DEVNULL, env=env)
    return r.returncode, r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")


def kb_commands(settings):
    return [h["command"] for groups in settings["hooks"].values() for g in groups for h in g["hooks"]
            if settings_fragment.hook_key(h["command"])]


class InstallTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.t = os.path.join(self._tmp.name, "dự án mẫu")
        os.makedirs(self.t)

    def tearDown(self):
        self._tmp.cleanup()

    def load(self, rel):
        with open(os.path.join(self.t, *rel.split("/")), encoding="utf-8") as f:
            return json.load(f)

    def only_python3(self):
        """PATH that holds one name, python3 (this interpreter): what a stock macOS / Linux machine looks like."""
        folder = os.path.join(self._tmp.name, "bin")
        os.makedirs(folder, exist_ok=True)
        if not os.path.exists(os.path.join(folder, "python3")):
            os.symlink(sys.executable, os.path.join(folder, "python3"))
        return dict(os.environ, PATH=folder)

    def test_explicit_launcher_everywhere(self):
        code, out = install(self.t, "--python", sys.executable, *FULL)
        self.assertEqual(code, 0, out)
        settings = self.load(".claude/settings.json")
        cmds = kb_commands(settings)
        self.assertEqual(len(cmds), 5)
        self.assertTrue(all(c.startswith(ME + " -I -S -c ") for c in cmds), cmds)
        kb_perms = [p for p in settings["permissions"]["allow"] if "qkb.py" in p or "kbscope.py" in p]
        self.assertEqual(len(kb_perms), 10)
        self.assertTrue(all(p.startswith("Bash(%s -" % ME) for p in kb_perms), kb_perms)
        self.assertEqual(self.load("00_KB_Manager/kb.config.json")["qkb_command"],
                         ME + " -E -s -B .claude/skills/q-knowledgebase/scripts/qkb.py")
        self.assertEqual(self.load(".qkb/install/installed.json")["options"]["python"], ME)

    def test_bad_explicit_launcher_writes_nothing(self):
        code, out = install(self.t, "--python", "no-such-python-launcher-xyz", *FULL)
        self.assertEqual(code, 2, out)
        self.assertIn("--python", out)
        self.assertEqual(os.listdir(self.t), [])

    @unittest.skipIf(os.name == "nt", "PATH with only python3: macOS / Linux case")
    def test_machine_with_only_python3(self):
        env = self.only_python3()
        code, out = install(self.t, *FULL, env=env)
        self.assertEqual(code, 0, out)
        self.assertIn("`python` không chạy được", out)
        cmds = kb_commands(self.load(".claude/settings.json"))
        self.assertTrue(all(c.startswith("python3 -I -S -c ") for c in cmds), cmds)
        self.assertTrue(self.load("00_KB_Manager/kb.config.json")["qkb_command"].startswith("python3 -E -s -B "))
        # one hook command, run the way Claude Code does (a shell string), finds its interpreter and exits 0
        r = subprocess.run(cmds[0], shell=True, input=b"{}", capture_output=True, cwd=self.t, timeout=60,
                           env=dict(env, PATH=env["PATH"] + os.pathsep + "/usr/bin" + os.pathsep + "/bin",
                                    CLAUDE_PROJECT_DIR=self.t))
        self.assertEqual(r.returncode, 0, r.stderr)

    @unittest.skipIf(os.name == "nt", "PATH with only python3: macOS / Linux case")
    def test_switch_keeps_working_launcher_and_follows_explicit(self):
        env = self.only_python3()
        self.assertEqual(install(self.t, "--python", sys.executable, *FULL)[0], 0)
        before = self.load(".claude/settings.json")
        code, out = install(self.t, *FULL, env=env)                 # the launcher in the project still works: kept
        self.assertEqual(code, 0, out)
        self.assertEqual(self.load(".claude/settings.json"), before)
        code, out = install(self.t, "--python", "python3", *FULL, env=env)
        self.assertEqual(code, 0, out)
        settings = self.load(".claude/settings.json")
        cmds = kb_commands(settings)
        self.assertEqual(len(cmds), 5)                              # switched in place, no second block
        self.assertTrue(all(c.startswith("python3 -I -S -c ") for c in cmds), cmds)
        kb_perms = [p for p in settings["permissions"]["allow"] if "qkb.py" in p or "kbscope.py" in p]
        self.assertEqual(len(kb_perms), 10)
        self.assertTrue(all(p.startswith("Bash(python3 -") for p in kb_perms), kb_perms)
        self.assertTrue(self.load("00_KB_Manager/kb.config.json")["qkb_command"].startswith("python3 -E -s -B "))
        code, out = install(self.t, "--uninstall", "--apply", "--yes", env=env)
        self.assertEqual(code, 0, out)
        left = self.load(".claude/settings.json") if os.path.exists(os.path.join(self.t, ".claude", "settings.json")) else {}
        self.assertEqual(kb_commands(left) if left.get("hooks") else [], [])
        self.assertFalse([p for p in (left.get("permissions") or {}).get("allow", []) if "qkb.py" in p or "kbscope.py" in p])


if __name__ == "__main__":
    unittest.main()
