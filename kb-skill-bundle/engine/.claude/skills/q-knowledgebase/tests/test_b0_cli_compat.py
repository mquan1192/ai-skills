"""B0 through the CLI, plus 2.0.0 compatibility of commands, options, keys and exit codes."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import QUESTIONS, SKILL, populate
from core import DEFAULTS

V200_KEYS = ["project_name", "knowledge_paths", "source_paths", "network_enabled", "auto_modify_docs", "semantic_mode",
             "query_top_k", "query_max_chars", "graph_default_depth", "chunk_lines", "exclude_patterns", "fts_enabled"]


class CliCompatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="qkb-b0-cli-")
        cls.root = Path(cls.temp.name)
        populate(cls.root)
        # A 2.0.0 configuration file: exactly the 12 old keys, none of the new ones.
        cfg = {k: DEFAULTS[k] for k in V200_KEYS}
        (cls.root / ".qkb/config.json").write_text(json.dumps(cfg), encoding="utf-8")
        questions = [dict(q, kind="k%d" % (i % 2)) for i, q in enumerate(QUESTIONS)]
        (cls.root / "questions-kind.json").write_text(json.dumps(questions, ensure_ascii=False), encoding="utf-8")
        questions[0] = dict(questions[0], category=7)
        (cls.root / "questions-bad.json").write_text(json.dumps(questions, ensure_ascii=False), encoding="utf-8")
        assert cls.cli("build")[0] == 0

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @classmethod
    def cli(cls, *args, fmt=True):
        cli = SKILL / "scripts/qkb.py"
        extra = ["--format", "json"] if fmt else []
        proc = subprocess.run([sys.executable, "-s", str(cli), "--root", str(cls.root), *args, *extra],
                              text=True, encoding="utf-8", capture_output=True, timeout=90)
        try:
            data = json.loads(proc.stdout)
        except ValueError:
            data = {"raw": proc.stdout, "stderr": proc.stderr}
        return proc.returncode, data

    def test_v200_commands_keep_their_keys(self):
        auth = self.cli("search", "Authentication")[1]
        section = auth["results"][0]["id"]
        cases = {("doctor",): ["version", "python", "sqlite", "fts5_available"],
                 ("init", "--dry-run"): ["dry_run", "files", "count"],
                 ("update",): ["added", "modified", "deleted", "unchanged"],
                 ("status",): ["state", "changed", "deleted", "files", "edges"],
                 ("search", "Audit workflow"): ["results", "candidates", "match_mode"],
                 ("explore", "Audit workflow"): ["results", "nodes", "edges"],
                 ("read", section): ["sections"],
                 ("map",): ["nodes", "groups"],
                 ("related", "docs/auth.md"): ["nodes", "edges", "direction", "depth"],
                 ("path", "src/users.py", "src/audit.py"): ["found"],
                 ("impact", "src/audit.py"): ["nodes", "edges"],
                 ("semantic", "list"): [],
                 ("export", "--kind", "json"): [],
                 ("backup",): ["output"]}
        for args, keys in cases.items():
            with self.subTest(command=args[0]):
                code, data = self.cli(*args)
                self.assertEqual(code, 0, data)
                for key in keys:
                    self.assertIn(key, data)
        for key in ("project",):
            self.assertIn(key, auth["results"][0])   # new keys are only added

    def test_verify_exit_codes_and_links(self):
        code, data = self.cli("verify")
        self.assertIn(code, (0, 1))
        self.assertNotIn("links", data)
        code_links, data = self.cli("verify", "--links", "--top", "5")
        self.assertEqual(code_links, code)
        links = data["links"]
        for key in ("references", "resolved", "by_resolution", "broken", "broken_by_cause", "outside_index", "skipped_not_a_path"):
            self.assertIn(key, links)
        self.assertEqual(links["broken"], sum(v["count"] for v in links["broken_by_cause"].values()))

    def test_errors_and_budgets_unchanged(self):
        self.assertEqual(self.cli("search", "x", "--max-chars", "199")[0], 2)
        self.assertEqual(self.cli("read", "no-such-id")[0], 2)
        code, data = self.cli("search", "Authentication", "--max-chars", "400")
        self.assertEqual(code, 0)
        self.assertLessEqual(len(json.dumps(data, ensure_ascii=False, separators=(",", ":"))), 400)
        bad = dict(DEFAULTS, unknown_key=1)
        (self.root / ".qkb/config.json").write_text(json.dumps(bad), encoding="utf-8")
        try:
            self.assertEqual(self.cli("status")[0], 2)
        finally:
            (self.root / ".qkb/config.json").write_text(json.dumps({k: DEFAULTS[k] for k in V200_KEYS}), encoding="utf-8")

    def test_benchmark_new_measures(self):
        code, data = self.cli("benchmark", "questions.json", "--max-chars", "100000")
        self.assertEqual(code, 0, data)
        for key in ("recall_at_5", "relevant_section_precision", "average_search_ms", "p50_search_ms", "p95_search_ms", "precision_at_5"):
            self.assertIn(key, data)
        self.assertLessEqual(data["p50_search_ms"], data["p95_search_ms"])
        self.assertTrue(0 <= data["precision_at_5"] <= 1)
        self.assertEqual(data["by_category"], {})
        row = data["results"][0]
        self.assertAlmostEqual(row["precision_at_5"] * 5, round(row["precision_at_5"] * 5))

    def test_benchmark_kind_and_category(self):
        code, data = self.cli("benchmark", "questions-kind.json", "--max-chars", "100000")
        self.assertEqual(code, 0, data)
        self.assertEqual(set(data["by_category"]), {"k0", "k1"})
        self.assertEqual(sum(v["questions"] for v in data["by_category"].values()), len(QUESTIONS))
        self.assertEqual(self.cli("benchmark", "questions-bad.json")[0], 2)

    def test_percentile_nearest_rank(self):
        import benchmark
        self.assertEqual(benchmark.percentile([5.0], 95), 5.0)
        self.assertEqual(benchmark.percentile([1, 2, 3, 4], 50), 2)
        self.assertEqual(benchmark.percentile(list(range(1, 101)), 95), 95)


if __name__ == "__main__":
    unittest.main()
