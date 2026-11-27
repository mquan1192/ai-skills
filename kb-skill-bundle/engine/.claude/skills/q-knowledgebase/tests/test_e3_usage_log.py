"""2.1.0-e3: optional usage log - one JSON line per search-type call, no result text, never breaks a search."""
import contextlib
import io
import json

import support  # noqa: F401  (puts scripts/ on sys.path)
from support import Fixture
from core import DEFAULTS, QError, validate_config
import qkb
import usage


class UsageLogTests(Fixture):
    def configure(self, log):
        cfg = json.loads((self.root / ".qkb/config.json").read_text(encoding="utf-8"))
        cfg["usage_log"] = log
        (self.root / ".qkb/config.json").write_text(json.dumps(cfg), encoding="utf-8")

    def run_cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = qkb.main(["--root", str(self.root), *args, "--format", "json"])
        return code, out.getvalue()

    def lines(self, folder="logs/usage"):
        files = list((self.root / folder).glob("*.jsonl"))
        return [json.loads(l) for f in files for l in f.read_text(encoding="utf-8").splitlines()]

    def test_off_by_default(self):
        self.assertEqual(DEFAULTS["usage_log"]["path"], "")
        self.assertEqual(self.run_cli("search", "audit workflow")[0], 0)
        self.assertFalse((self.root / "logs").exists())

    def test_one_line_per_call_without_result_text(self):
        self.configure({"path": "logs/usage", "query_text": True})
        self.run_cli("search", "audit workflow")
        self.run_cli("query", "Which service owns authentication?")
        self.run_cli("search", "zzqx nothingmatches")
        self.run_cli("status")                                         # not a search-type command: no line
        rows = self.lines()
        self.assertEqual([r["command"] for r in rows], ["search", "query", "search"])
        first = rows[0]
        for key in ("time", "scope", "route", "reason", "model", "model_reason", "ms", "results", "top_score", "coverage", "miss"):
            self.assertIn(key, first)
        self.assertEqual(first["query"], "audit workflow")
        self.assertFalse(first["model"])
        self.assertGreater(first["results"], 0)
        self.assertFalse(first["miss"])
        self.assertTrue(rows[2]["miss"])
        text = "".join(f.read_text(encoding="utf-8") for f in (self.root / "logs/usage").glob("*.jsonl"))
        self.assertNotIn("Deleting a user requires an audit event", text)    # never section text / snippets

    def test_query_text_switch(self):
        self.configure({"path": "logs/usage", "query_text": False})
        self.run_cli("search", "audit workflow")
        self.assertNotIn("query", self.lines()[0])

    def test_write_failure_is_ignored(self):
        (self.root / "blocked").write_text("a file where the log folder should be", encoding="utf-8")
        self.configure({"path": "blocked/usage", "query_text": True})
        code, out = self.run_cli("search", "audit workflow")
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["results"])

    def test_path_must_stay_inside_the_root(self):
        for bad in ("../outside", "C:/temp/log", {"path": 1}):
            cfg = dict(DEFAULTS, usage_log=bad if isinstance(bad, dict) else {"path": bad})
            with self.assertRaises(QError):
                validate_config(self.root, cfg)
