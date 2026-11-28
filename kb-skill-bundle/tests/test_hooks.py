"""Tests of the KB hooks . Stdlib only; fake project trees in temp folders; each hook run is timed (≤ 2 s).

Run from the bundle-hooks folder:  python -E -s -B -m unittest discover -s tests -p "test_*.py"
Timings are printed at the end (KB_HOOK_TIMINGS) and kept in TIMINGS.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest

BUNDLE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
HOOKS = os.path.join(BUNDLE, "hooks")
PLUGIN_JSON = os.path.join(BUNDLE, "hooks", "hooks.json")
TIMINGS = {}
MARK = "ZZPROMPTMARKER42"
FAKE_QKB = """import json, sys
args = sys.argv[1:]
if args and args[0] == 'status':
    print(json.dumps({'state': 'STALE', 'changed': ['kb/demo/core/a.md'], 'deleted': []}))
else:
    print('{}')
"""


def make_tree(tmp, mode="observe", with_index=True, with_config=True, sources=True, extra_cfg=None):
    def w(rel, text):
        p = os.path.join(tmp, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
    if with_index:
        os.makedirs(os.path.join(tmp, ".qkb"), exist_ok=True)
    w("kb/VERSION", "2026.01.05-02\n")
    w("kb/demo/core/_sources.md", "| Path | Size |\n|---|---|\n| `docs/old.pdf` | 1 |\n| `src/tree1/mod` | 2 |\n")
    w("kb/demo/core/notes.md", "# notes\nSECRETKBCONTENT\n")
    if sources:
        w("projects/demo/core/docs/old.pdf", "x")
        w("projects/demo/core/docs/new-spec.pdf", "x")
        w("projects/demo/core/src/tree1/mod/a.cpp", "x")
        w("projects/demo/core/src/tree2/b.cpp", "x")
    w("tools/fakeqkb.py", FAKE_QKB)
    w("00_UpdateDocs/requests/REQ-20260101-0900-old.md", "# REQ\n- Status: open\n")
    if with_config:
        cfg = {"kb_root": "kb", "projects_root": "projects", "qkb_command": "python tools/fakeqkb.py",
               "version_file": "kb/VERSION", "requests_folder": "00_UpdateDocs/requests",
               "project_scopes": {"demo/core": ["kb/demo/core/"], "other": ["kb/other/"]},
               "default_scope": "all", "issue_id_patterns": ["OP-\\d+"], "hooks": {"mode": mode, "index_check": "status"}}
        cfg["hooks"].update(extra_cfg or {})
        w("00_UpdateDocs/kb.config.json", json.dumps(cfg))


def readtext(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def run_hook(name, tmp, payload, *args):
    cmd = [sys.executable, "-I", "-S", os.path.join(HOOKS, name)] + list(args) + ["--root", tmp]
    t0 = time.perf_counter()
    r = subprocess.run(cmd, input=json.dumps(payload).encode("utf-8"), capture_output=True, timeout=10, cwd=tmp)
    ms = (time.perf_counter() - t0) * 1000
    key = name + (" " + args[0] if args else "")
    TIMINGS[key] = max(TIMINGS.get(key, 0), ms)
    out = r.stdout.decode("utf-8", "replace").strip()
    return r.returncode, (json.loads(out) if out else None), ms


def logs(tmp):
    folder = os.path.join(tmp, ".qkb", "local", "observe")
    if not os.path.isdir(folder):
        return []
    lines = []
    for name in os.listdir(folder):
        with open(os.path.join(folder, name), encoding="utf-8") as f:
            lines += [json.loads(l) for l in f if l.strip()]
    return lines


def all_log_text(tmp):
    folder = os.path.join(tmp, ".qkb", "local", "observe")
    if not os.path.isdir(folder):
        return ""
    return "".join(readtext(os.path.join(folder, n)) for n in os.listdir(folder))


def requests(tmp):
    return sorted(os.listdir(os.path.join(tmp, "00_UpdateDocs", "requests")))


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def assertFast(self, ms):
        self.assertLess(ms, 2000)


class WatchTests(Base):
    def test_silent_without_index_or_config(self):
        make_tree(self.tmp, with_index=False)
        code, out, ms = run_hook("kbwatch.py", self.tmp, {"hook_event_name": "SessionStart"})
        self.assertEqual((code, out, logs(self.tmp)), (0, None, []))
        self.assertFast(ms)
        with tempfile.TemporaryDirectory() as t2:
            make_tree(t2, with_config=False)
            code, out, _ = run_hook("kbwatch.py", t2, {})
            self.assertEqual((code, out, logs(t2)), (0, None, []))

    def test_observe_logs_only(self):
        make_tree(self.tmp)
        before = requests(self.tmp)
        code, out, ms = run_hook("kbwatch.py", self.tmp, {"hook_event_name": "SessionStart"})
        self.assertEqual((code, out), (0, None))
        self.assertEqual(requests(self.tmp), before)          # observe: no request written
        entry = logs(self.tmp)[0]
        self.assertEqual(entry["hook"], "kbwatch")
        self.assertIn("📚 KB v2026.01.05-02", entry["would_show"])
        self.assertIn("chỉ mục cũ (1 file đổi)", entry["would_show"])
        self.assertIn("2 nguồn mới chưa nạp (demo/core) → sẽ tạo yêu cầu", entry["would_show"])
        self.assertIn("1 request đang mở", entry["would_show"])
        self.assertNotIn("SECRETKBCONTENT", all_log_text(self.tmp))
        self.assertFast(ms)

    def test_on_mode_creates_one_request_no_duplicate(self):
        make_tree(self.tmp, mode="on")
        code, out, ms = run_hook("kbwatch.py", self.tmp, {})
        self.assertEqual(code, 0)
        line = out["systemMessage"]
        self.assertTrue(line.startswith("📚 KB v2026.01.05-02 · "), line)
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "SessionStart")
        made = [r for r in requests(self.tmp) if "sync-demo-core" in r]
        self.assertEqual(len(made), 1)
        text = readtext(os.path.join(self.tmp, "00_UpdateDocs", "requests", made[0]))
        self.assertIn("- Type: sync-sources", text)
        self.assertIn("projects/demo/core/docs/new-spec.pdf", text)
        self.assertIn("projects/demo/core/src/tree2", text)
        self.assertNotIn("old.pdf", text)
        self.assertNotIn("tree1", text)
        self.assertIn("2 request đang mở", line)
        code, out, _ = run_hook("kbwatch.py", self.tmp, {})
        self.assertEqual(len([r for r in requests(self.tmp) if "sync-demo-core" in r]), 1)
        self.assertIn("đã có yêu cầu", out["systemMessage"])
        entries = logs(self.tmp)                               # v2.0.2: mode "on" logs too
        self.assertEqual([e["mode"] for e in entries], ["on", "on"])
        self.assertTrue(all(e["hook"] == "kbwatch" and isinstance(e["ms"], int) and "shown" in e for e in entries))
        self.assertFast(ms)

    def _set_cfg(self, **top):
        p = os.path.join(self.tmp, "00_UpdateDocs", "kb.config.json")
        cfg = json.loads(readtext(p))
        cfg.update(top)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cfg, f)

    def test_k4_no_request_for_paths_named_in_an_open_request(self):
        # v2.0.3 K4 (red proof): a manual source-intake request (open, other author, no source-list hash) already names
        # the new tree and the new document -> kbwatch must not raise a second sync request for them.
        make_tree(self.tmp, mode="on")
        with open(os.path.join(self.tmp, "00_UpdateDocs", "requests", "REQ-20260105-1118-intake.md"), "w", encoding="utf-8") as f:
            f.write("# REQ-20260105-1118-intake\n- Status: open\n- From: a session\n- Content:\n"
                    "  - [CODE] new tree `projects/demo/core/src/tree2/sub/` from a zip\n"
                    "  - [DOC] new file `projects/demo/core/docs/new-spec.pdf`\n")
        before = requests(self.tmp)
        code, out, _ = run_hook("kbwatch.py", self.tmp, {})
        self.assertEqual(code, 0)
        self.assertEqual(requests(self.tmp), before)                      # no new sync request
        self.assertIn("đã có yêu cầu", out["systemMessage"])
        # a closed request does not cover anything: once it is done, the same paths are requested again
        p = os.path.join(self.tmp, "00_UpdateDocs", "requests", "REQ-20260105-1118-intake.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write(readtext(p).replace("- Status: open", "- Status: done"))
        run_hook("kbwatch.py", self.tmp, {})
        made = [r for r in requests(self.tmp) if "sync-demo-core" in r]
        self.assertEqual(len(made), 1)
        text = readtext(os.path.join(self.tmp, "00_UpdateDocs", "requests", made[0]))
        self.assertIn("projects/demo/core/src/tree2", text)

    def test_k4_folder_mentions_above_a_source_unit_cover_nothing(self):
        # an open request of any type that names the project, the part, docs/ or src/ as context
        # must not silence new sources below it -> the sync request is still written.
        make_tree(self.tmp, mode="on")
        with open(os.path.join(self.tmp, "00_UpdateDocs", "requests", "REQ-20260105-1200-idea.md"), "w", encoding="utf-8") as f:
            f.write("# REQ-20260105-1200-idea\n- Status: open\n- Type: improvement\n- Content:\n"
                    "  - [DOC] context: `projects/demo/core/`, `projects/demo/`, `projects/demo/core/docs/`, `projects/demo/core/src/`\n")
        code, out, _ = run_hook("kbwatch.py", self.tmp, {})
        made = [r for r in requests(self.tmp) if "sync-demo-core" in r]
        self.assertEqual(len(made), 1)
        text = readtext(os.path.join(self.tmp, "00_UpdateDocs", "requests", made[0]))
        self.assertIn("projects/demo/core/docs/new-spec.pdf", text)
        self.assertIn("projects/demo/core/src/tree2", text)
        self.assertNotIn("đã có yêu cầu", out["systemMessage"])

    def test_k4_status_line_names_the_covering_request(self):
        # the line names the request that covers the sources (+ n others)
        make_tree(self.tmp, mode="on")
        for name, body in (("REQ-20260105-1118-intake.md", "`projects/demo/core/src/tree2/sub/` and `projects/demo/core/docs/new-spec.pdf`"),
                           ("REQ-20260105-1119-more.md", "`projects/demo/core/docs/new-spec.pdf`")):
            with open(os.path.join(self.tmp, "00_UpdateDocs", "requests", name), "w", encoding="utf-8") as f:
                f.write("# x\n- Status: open\n- Content: " + body + "\n")
        code, out, _ = run_hook("kbwatch.py", self.tmp, {})
        self.assertEqual([r for r in requests(self.tmp) if "sync-demo-core" in r], [])
        self.assertIn("đã có yêu cầu REQ-20260105-1118-intake + 1 yêu cầu khác", out["systemMessage"])
        # a request written by the hook itself (same source-list hash) is named too
        with tempfile.TemporaryDirectory() as t2:
            make_tree(t2, mode="on")
            run_hook("kbwatch.py", t2, {})
            mine = [r for r in requests(t2) if "sync-demo-core" in r][0][:-3]
            code, out, _ = run_hook("kbwatch.py", t2, {})
            self.assertIn("đã có yêu cầu " + mine, out["systemMessage"])

    def test_k4_partly_covered_requests_only_the_rest(self):
        make_tree(self.tmp, mode="on")
        with open(os.path.join(self.tmp, "00_UpdateDocs", "requests", "REQ-20260105-1118-intake.md"), "w", encoding="utf-8") as f:
            f.write("# x\n- Status: in-progress\n- Content: `projects/demo/core/src/tree2`\n")
        run_hook("kbwatch.py", self.tmp, {})
        made = [r for r in requests(self.tmp) if "sync-demo-core" in r]
        self.assertEqual(len(made), 1)
        text = readtext(os.path.join(self.tmp, "00_UpdateDocs", "requests", made[0]))
        self.assertIn("projects/demo/core/docs/new-spec.pdf", text)
        self.assertNotIn("tree2", text)

    def test_k2_request_prefixes_read_all_write_first(self):
        # default: writes REQ-…; reads only REQ-* files (a stray note file is ignored)
        make_tree(self.tmp, mode="on")
        with open(os.path.join(self.tmp, "00_UpdateDocs", "requests", "README.md"), "w", encoding="utf-8") as f:
            f.write("# requests\n- Status: open\n")
        code, out, _ = run_hook("kbwatch.py", self.tmp, {})
        made = [r for r in requests(self.tmp) if "sync-demo-core" in r]
        self.assertEqual(len(made), 1)
        self.assertTrue(made[0].startswith("REQ-"))
        self.assertIn("2 request đang mở", out["systemMessage"])          # old + new; README.md not counted
        # configured list: both prefixes are read (open count, hashes), the first one is written
        with tempfile.TemporaryDirectory() as t2:
            make_tree(t2, mode="on")
            self.tmp, keep = t2, self.tmp
            try:
                self._set_cfg(request_prefixes=["KB-REQ-", "REQ-"])
                with open(os.path.join(t2, "00_UpdateDocs", "requests", "KB-REQ-20260105-1000-x.md"), "w", encoding="utf-8") as f:
                    f.write("# x\n- Status: open\n")
                code, out, _ = run_hook("kbwatch.py", t2, {})
                made = [r for r in requests(t2) if "sync-demo-core" in r]
                self.assertEqual(len(made), 1)
                self.assertTrue(made[0].startswith("KB-REQ-"))
                self.assertIn("3 request đang mở", out["systemMessage"])  # REQ- old + KB-REQ- x + new one
                run_hook("kbwatch.py", t2, {})                              # no duplicate across prefixes
                self.assertEqual(len([r for r in requests(t2) if "sync-demo-core" in r]), 1)
                self._set_cfg(request_prefixes=["../bad", 5])              # invalid list -> default REQ-
                os.remove(os.path.join(t2, "00_UpdateDocs", "requests", made[0]))
                run_hook("kbwatch.py", t2, {})
                self.assertTrue(any(r.startswith("REQ-") and "sync-demo-core" in r for r in requests(t2)))
            finally:
                self.tmp = keep

    def test_off_and_unknown_engine(self):
        make_tree(self.tmp, mode="off")
        self.assertEqual(run_hook("kbwatch.py", self.tmp, {})[1], None)
        self.assertEqual(logs(self.tmp), [])
        with tempfile.TemporaryDirectory() as t2:
            make_tree(t2, mode="on", sources=False)
            os.remove(os.path.join(t2, "tools", "fakeqkb.py"))
            code, out, _ = run_hook("kbwatch.py", t2, {})
            self.assertEqual(code, 0)
            self.assertIn("chỉ mục chưa kiểm", out["systemMessage"])
            self.assertNotIn("nguồn mới", out["systemMessage"])

    def test_broken_stdin(self):
        make_tree(self.tmp, mode="on")
        r = subprocess.run([sys.executable, "-I", "-S", os.path.join(HOOKS, "kbwatch.py"), "--root", self.tmp],
                           input=b"not json{", capture_output=True, timeout=10)
        self.assertEqual(r.returncode, 0)


class RouteTests(Base):
    def test_project_question_model_only(self):
        make_tree(self.tmp, mode="on")
        code, out, ms = run_hook("kbroute.py", self.tmp, {"prompt": "Trong demo core, OP-12 xử lý thế nào? " + MARK})
        self.assertEqual(code, 0)
        self.assertNotIn("systemMessage", out)
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("tra KB trước · phạm vi = demo/core (đoán)", ctx)
        self.assertIn("--project demo", ctx)
        self.assertNotIn(MARK, ctx)
        self.assertFast(ms)

    def test_saved_scope_wins(self):
        make_tree(self.tmp, mode="on")
        os.makedirs(os.path.join(self.tmp, ".qkb", "local"))
        with open(os.path.join(self.tmp, ".qkb", "local", "scope.json"), "w", encoding="utf-8") as f:
            json.dump({"scope": "all"}, f)
        out = run_hook("kbroute.py", self.tmp, {"prompt": "OP-3 ảnh hưởng tới phần nào?"})[1]
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("phạm vi = all (đã lưu)", ctx)
        self.assertNotIn("--project", ctx)

    def test_silent_cases(self):
        make_tree(self.tmp, mode="on", extra_cfg={"route_keywords": ["widget"]})
        for prompt in ("Viết giúp tôi một email cảm ơn khách hàng", "/q-kb-search demo core OP-1", "ok", ""):
            self.assertIsNone(run_hook("kbroute.py", self.tmp, {"prompt": prompt})[1], prompt)
        self.assertIsNotNone(run_hook("kbroute.py", self.tmp, {"prompt": "the widget behaviour please"})[1])

    def test_observe_log_has_no_prompt(self):
        make_tree(self.tmp)
        code, out, _ = run_hook("kbroute.py", self.tmp, {"prompt": "demo core OP-7 " + MARK})
        self.assertIsNone(out)
        text = all_log_text(self.tmp)
        self.assertNotIn(MARK, text)
        self.assertNotIn("OP-7", text)
        entry = logs(self.tmp)[0]
        self.assertEqual(entry["codes"], ["SCOPE_NAME", "ISSUE_ID"])
        self.assertTrue(entry["would_tell_model"])
        self.assertEqual(entry["would_show"], "")


    def test_on_mode_log_has_no_prompt_and_can_be_turned_off_or_moved(self):
        make_tree(self.tmp, mode="on")
        code, out, _ = run_hook("kbroute.py", self.tmp, {"prompt": "demo core OP-7 " + MARK})
        self.assertIsNotNone(out)                                         # the hint is still sent
        self.assertNotIn(MARK, all_log_text(self.tmp))
        self.assertNotIn("OP-7", all_log_text(self.tmp))
        entry = logs(self.tmp)[0]
        self.assertEqual((entry["mode"], entry["hook"], entry["event"]), ("on", "kbroute", "UserPromptSubmit"))
        self.assertEqual(entry["codes"], ["SCOPE_NAME", "ISSUE_ID"])
        self.assertTrue(entry["told_model"])
        self.assertIsInstance(entry["ms"], int)
        with tempfile.TemporaryDirectory() as t2:
            make_tree(t2, mode="on", extra_cfg={"log": False})
            self.assertIsNotNone(run_hook("kbroute.py", t2, {"prompt": "demo core OP-7"})[1])
            self.assertEqual(logs(t2), [])
        with tempfile.TemporaryDirectory() as t3:
            make_tree(t3, mode="on", extra_cfg={"log_dir": "process-log/kb-hooks"})
            run_hook("kbroute.py", t3, {"prompt": "demo core OP-7"})
            folder = os.path.join(t3, "process-log", "kb-hooks")
            self.assertEqual(len(os.listdir(folder)), 1)
            self.assertEqual(logs(t3), [])                                # not in the old default folder


class GuardTests(Base):
    def test_pre_grep_into_kb(self):
        make_tree(self.tmp, mode="on")
        for ti in ({"pattern": "x", "path": "kb/demo"}, {"pattern": "x", "path": os.path.join(self.tmp, "projects")}):
            code, out, ms = run_hook("kbguard.py", self.tmp, {"tool_name": "Grep", "tool_input": ti}, "pre")
            self.assertIn("qkb query", out["hookSpecificOutput"]["additionalContext"])
            self.assertNotIn("systemMessage", out)
            self.assertFast(ms)
        out = run_hook("kbguard.py", self.tmp, {"tool_name": "Glob", "tool_input": {"pattern": "kb/**/*.md"}}, "pre")[1]
        self.assertIsNotNone(out)

    def test_pre_silent(self):
        make_tree(self.tmp, mode="on")
        for payload in ({"tool_name": "Read", "tool_input": {"file_path": "kb/demo/core/notes.md"}},
                        {"tool_name": "Grep", "tool_input": {"pattern": "x", "path": "src"}},
                        {"tool_name": "Grep", "tool_input": {"pattern": "x"}},
                        {"tool_name": "Grep", "tool_input": {"pattern": "x", "path": "/elsewhere/kb"}}):
            self.assertIsNone(run_hook("kbguard.py", self.tmp, payload, "pre")[1], payload)

    def test_post_stale_and_broken(self):
        make_tree(self.tmp, mode="on")
        payload = {"tool_name": "Bash", "tool_input": {"command": "python x/qkb.py search foo --format json"},
                   "tool_response": {"stdout": '{"results": [{"source_status": "STALE"}], "broken": 3}'}}
        code, out, ms = run_hook("kbguard.py", self.tmp, payload, "post")
        self.assertIn("kết quả có đoạn đã cũ", out["systemMessage"])
        self.assertNotIn("liên kết hỏng", out["systemMessage"])          # first count = baseline, no warning
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PostToolUse")
        self.assertFast(ms)
        clean = dict(payload, tool_response={"stdout": '{"results": [{"source_status": "CURRENT"}], "broken": 0}'})
        self.assertIsNone(run_hook("kbguard.py", self.tmp, clean, "post")[1])
        rose = dict(payload, tool_response={"stdout": '{"broken": 5}'})
        out = run_hook("kbguard.py", self.tmp, rose, "post")[1]
        self.assertIn("liên kết hỏng tăng 0 → 5", out["systemMessage"])
        self.assertIsNone(run_hook("kbguard.py", self.tmp, rose, "post")[1])   # same count again: silent
        other = dict(payload, tool_input={"command": "grep STALE file"})
        self.assertIsNone(run_hook("kbguard.py", self.tmp, other, "post")[1])

    def test_post_observe_keeps_baseline(self):
        # observe mode stores the baseline too, so a rise is logged as "would warn"
        make_tree(self.tmp)
        payload = {"tool_name": "Bash", "tool_input": {"command": "python x/qkb.py verify --links --format json"},
                   "tool_response": {"stdout": '{"links": {"broken": 2}}'}}
        self.assertIsNone(run_hook("kbguard.py", self.tmp, payload, "post")[1])
        rose = dict(payload, tool_response={"stdout": '{"links": {"broken": 4}}'})
        self.assertIsNone(run_hook("kbguard.py", self.tmp, rose, "post")[1])
        entry = logs(self.tmp)[-1]
        self.assertEqual(entry["codes"], ["BROKEN_LINKS_ROSE"])
        self.assertIn("liên kết hỏng tăng 2 → 4", entry["would_show"])

    def transcript(self, tool_uses):
        path = os.path.join(self.tmp, "t.jsonl")
        rows = [{"type": "user", "message": {"role": "user", "content": "earlier " + MARK}},
                {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Write",
                                                               "input": {"file_path": "2026-01/05_01-x/out/old.md"}}]}},
                {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "new turn"}]}}]
        rows += [{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": n, "input": i}]}}
                 for n, i in tool_uses]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(json.dumps(r) for r in rows) + "\n")
        return path

    def test_stop_default_logs_only(self):
        make_tree(self.tmp, mode="on")                                   # stop_notice off by default
        t = self.transcript([("Write", {"file_path": os.path.join(self.tmp, "2026-01", "05_01-x", "out", "r.md")})])
        code, out, ms = run_hook("kbguard.py", self.tmp, {"transcript_path": t, "session_id": "s1"}, "stop")
        self.assertIsNone(out)
        self.assertEqual(logs(self.tmp)[0]["codes"], ["TASK_OUTPUT_NO_REQUEST"])
        self.assertFast(ms)

    def test_stop_once_per_session(self):
        make_tree(self.tmp, mode="on", extra_cfg={"stop_notice": "once"})
        t = self.transcript([("Write", {"file_path": "2026-01/05_01-x/out/r.md"})])
        out = run_hook("kbguard.py", self.tmp, {"transcript_path": t, "session_id": "s1"}, "stop")[1]
        self.assertIn("/q-kb-request", out["systemMessage"])
        self.assertNotIn("hookSpecificOutput", out)
        self.assertIsNone(run_hook("kbguard.py", self.tmp, {"transcript_path": t, "session_id": "s1"}, "stop")[1])
        self.assertIsNotNone(run_hook("kbguard.py", self.tmp, {"transcript_path": t, "session_id": "s2"}, "stop")[1])

    def test_stop_solo_profile_names_update_command(self):
        make_tree(self.tmp, mode="on", extra_cfg={"stop_notice": "once"})
        path = os.path.join(self.tmp, "00_UpdateDocs", "kb.config.json")
        cfg = json.loads(readtext(path))
        cfg["manager"] = {"folder": "00_UpdateDocs", "solo": True}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        t = self.transcript([("Write", {"file_path": "2026-01/05_01-x/out/r.md"})])
        out = run_hook("kbguard.py", self.tmp, {"transcript_path": t, "session_id": "s1"}, "stop")[1]
        self.assertIn("/q-kb-update", json.dumps(out, ensure_ascii=False))
        self.assertNotIn("/q-kb-request", json.dumps(out, ensure_ascii=False))

    def test_stop_silent(self):
        make_tree(self.tmp, mode="on", extra_cfg={"stop_notice": "once"})
        cases = [
            [("Read", {"file_path": "a.md"})],                                             # no output this turn
            [("Write", {"file_path": "2026-01/05_01-x/out/r.md"}), ("Skill", {"skill": "q-kb-request"})],
            [("Write", {"file_path": "2026-01/05_01-x/out/r.md"}),
             ("Write", {"file_path": "00_UpdateDocs/requests/REQ-1.md"})],
        ]
        for tools in cases:
            t = self.transcript(tools)
            self.assertIsNone(run_hook("kbguard.py", self.tmp, {"transcript_path": t}, "stop")[1], tools)
        t = self.transcript([("Write", {"file_path": "2026-01/05_01-x/out/r.md"})])
        self.assertIsNone(run_hook("kbguard.py", self.tmp, {"transcript_path": t, "stop_hook_active": True}, "stop")[1])
        self.assertIsNone(run_hook("kbguard.py", self.tmp, {"transcript_path": "missing.jsonl"}, "stop")[1])

    def test_observe_stop_logs_no_transcript_text(self):
        make_tree(self.tmp)
        t = self.transcript([("Write", {"file_path": "2026-01/05_01-x/out/r.md"})])
        self.assertIsNone(run_hook("kbguard.py", self.tmp, {"transcript_path": t}, "stop")[1])
        self.assertEqual(logs(self.tmp)[0]["codes"], ["TASK_OUTPUT_NO_REQUEST"])
        self.assertNotIn(MARK, all_log_text(self.tmp))
        self.assertNotIn("r.md", all_log_text(self.tmp))


class IndexMetaTests(Base):
    def test_meta_check_without_engine(self):
        import sqlite3
        make_tree(self.tmp, mode="on", sources=False, extra_cfg={"index_check": "meta"})
        os.makedirs(os.path.join(self.tmp, ".qkb", "cache"))
        con = sqlite3.connect(os.path.join(self.tmp, ".qkb", "cache", "index.sqlite3"))
        con.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT)")
        con.execute("INSERT INTO meta VALUES ('last_indexed', '2000-01-01T00:00:00+00:00')")
        con.commit()
        con.close()
        out, ms = run_hook("kbwatch.py", self.tmp, {})[1:]
        self.assertIn("chỉ mục cũ (3 file đổi)", out["systemMessage"])          # kb/VERSION, _sources.md, notes.md newer
        self.assertFast(ms)
        con = sqlite3.connect(os.path.join(self.tmp, ".qkb", "cache", "index.sqlite3"))
        con.execute("UPDATE meta SET value='2999-01-01T00:00:00+00:00'")
        con.commit()
        con.close()
        self.assertIn("chỉ mục mới", run_hook("kbwatch.py", self.tmp, {})[1]["systemMessage"])

    def test_meta_check_no_index_db(self):
        make_tree(self.tmp, mode="on", sources=False, extra_cfg={"index_check": "meta"})
        self.assertIn("chỉ mục chưa kiểm", run_hook("kbwatch.py", self.tmp, {})[1]["systemMessage"])


class ScopeTests(Base):
    def run_scope(self, *args):
        r = subprocess.run([sys.executable, "-I", "-S", os.path.join(HOOKS, "kbscope.py")] + list(args) + ["--root", self.tmp],
                           capture_output=True, timeout=10)
        return r.returncode, r.stdout.decode("utf-8"), r.stderr.decode("utf-8")

    def test_set_get_clear(self):
        make_tree(self.tmp)
        self.assertIn("all (mặc định)", self.run_scope("get")[1])
        code, out, _ = self.run_scope("set", "demo/core")
        self.assertEqual(code, 0)
        self.assertIn("Đã lưu phạm vi KB: demo/core", out)
        with open(os.path.join(self.tmp, ".qkb", "local", "scope.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["scope"], "demo/core")
        self.assertIn("demo/core (đã lưu)", self.run_scope("get")[1])
        self.assertEqual(self.run_scope("set", "demo")[0], 0)          # kb folder name is a scope too
        code, out, _ = self.run_scope("clear")
        self.assertEqual(code, 0)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, ".qkb", "local", "scope.json")))

    def test_errors(self):
        make_tree(self.tmp)
        code, _, err = self.run_scope("set", "nowhere")
        self.assertEqual(code, 2)
        self.assertIn("không có phạm vi", err)
        self.assertEqual(self.run_scope("bogus")[0], 2)
        with tempfile.TemporaryDirectory() as t2:
            r = subprocess.run([sys.executable, "-I", "-S", os.path.join(HOOKS, "kbscope.py"), "get", "--root", t2],
                               capture_output=True, timeout=10)
            self.assertEqual(r.returncode, 2)


class PackagingTests(unittest.TestCase):
    def test_hooks_json_and_fragment(self):
        with open(PLUGIN_JSON, encoding="utf-8") as f:
            plugin = json.load(f)
        self.assertEqual(set(plugin["hooks"]), {"SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop"})
        for blocks in plugin["hooks"].values():
            for b in blocks:
                for h in b["hooks"]:
                    self.assertTrue(h["command"].startswith("python -I -S \"${CLAUDE_PLUGIN_ROOT}/hooks/kb"))
                    self.assertLessEqual(h["timeout"], 5)
        sys.path.insert(0, os.path.join(BUNDLE, "tools"))
        import settings_fragment as sf
        existing = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "python a.py"}]}]}, "other": 1}
        merged = sf.merge(existing, sf.fragment())
        self.assertEqual(merged["hooks"]["Stop"][0], existing["hooks"]["Stop"][0])   # existing block first, unchanged
        self.assertEqual(len(merged["hooks"]["Stop"]), 2)
        self.assertEqual(merged["other"], 1)
        self.assertEqual(sf.merge(merged, sf.fragment()), merged)                     # idempotent
        self.assertNotIn("CLAUDE_PLUGIN_ROOT", json.dumps(merged))

    def test_no_bytecode_left(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_tree(tmp, mode="on")
            run_hook("kbroute.py", tmp, {"prompt": "demo core OP-1 question"})
        self.assertFalse(os.path.exists(os.path.join(HOOKS, "__pycache__")))

    def test_no_project_names_in_code(self):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import localcfg
        hits = []
        for top in (HOOKS, os.path.join(BUNDLE, "tools"), os.path.join(BUNDLE, "scripts")):
            for folder, _, names in os.walk(top):
                for n in names:
                    if n.endswith((".py", ".json")):
                        hits += ["%s: %s" % (n, h) for h in localcfg.scan_hits(readtext(os.path.join(folder, n)))]
        self.assertEqual(hits, [])


def tearDownModule():
    print("\nKB_HOOK_TIMINGS (max ms per hook): " + json.dumps({k: round(v) for k, v in sorted(TIMINGS.items())}))


class V204Tests(Base):
    """2.0.4: Grep scope check (report only), one-meaning icons, default request prefixes REQ- + KB-REQ-."""

    def test_pre_broad_kb_search_reports_subfolder_rule(self):
        make_tree(self.tmp, mode="on")
        for path in ("kb", "kb/demo", os.path.join(self.tmp, "kb")):
            out = run_hook("kbguard.py", self.tmp, {"tool_name": "Grep", "tool_input": {"pattern": "x", "path": path}}, "pre")[1]
            ctx = out["hookSpecificOutput"]["additionalContext"]
            self.assertIn("quá rộng", ctx, path)
            self.assertIn("kb/<dự án>/<phần>/", ctx)
            self.assertNotIn("permissionDecision", json.dumps(out))         # report only, never a block
        out = run_hook("kbguard.py", self.tmp, {"tool_name": "Glob", "tool_input": {"pattern": "kb/**/*.md"}}, "pre")[1]
        self.assertIn("quá rộng", out["hookSpecificOutput"]["additionalContext"])

    def test_pre_subfolder_search_plain_reminder(self):
        make_tree(self.tmp, mode="on")
        out = run_hook("kbguard.py", self.tmp, {"tool_name": "Grep", "tool_input": {"pattern": "x", "path": "kb/demo/core"}}, "pre")[1]
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("qkb query", ctx)
        self.assertNotIn("quá rộng", ctx)

    def test_post_user_line_uses_small_risk_icon(self):
        make_tree(self.tmp, mode="on")
        payload = {"tool_name": "Bash", "tool_input": {"command": "python x/qkb.py search foo --format json"},
                   "tool_response": {"stdout": '{"results": [{"source_status": "STALE"}]}'}}
        msg = run_hook("kbguard.py", self.tmp, payload, "post")[1]["systemMessage"]
        self.assertTrue(msg.startswith("🔸 KB:"), msg)                 # 🔸, not the old ⚠️
        self.assertNotIn("⚠", msg)

    def test_default_prefixes_read_kb_req_write_req(self):
        make_tree(self.tmp, mode="on")
        with open(os.path.join(self.tmp, "00_UpdateDocs", "requests", "KB-REQ-20260105-1000-x.md"), "w", encoding="utf-8") as f:
            f.write("# x\n- Status: open\n")
        out = run_hook("kbwatch.py", self.tmp, {})[1]
        self.assertIn("3 request đang mở", out["systemMessage"])             # REQ- old + KB-REQ- x + new one
        made = [r for r in requests(self.tmp) if "sync-demo-core" in r]
        self.assertEqual(len(made), 1)
        self.assertTrue(made[0].startswith("REQ-"))

    def test_search_skill_icons_one_meaning(self):
        with open(os.path.join(BUNDLE, "skills", "q-kb-search", "SKILL.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("🔸 KB đang cập nhật phần này", text)
        self.assertNotIn("⚠️ KB", text)
        self.assertNotIn("⚠️ chỉ mục", text)


if __name__ == "__main__":
    unittest.main()
