"""Query routing."""
import json
import subprocess
import sys
import unittest

from support import SKILL, Fixture
from core import DEFAULTS
import router


class QueryTests(Fixture):
    def route(self, question, **kw):
        return router.query(self.store, question, **kw)

    def test_every_route_has_a_reason(self):
        cases = {
            "src/users.py": "exact",
            "UserService.delete_user": "exact",
            "REQ-USER-01": "exact",
            "audit_events": "exact",
            "what depends on src/users.py": "related",
            "src/audit.py phụ thuộc gì": "related",
            "impact of changing src/audit.py": "impact",
            "nếu sửa src/audit.py thì ảnh hưởng gì": "impact",
            "src/users.py -> src/audit.py": "path",
            "path from src/users.py to src/audit.py": "path",
            "how does the audit workflow work": "explore",
            "xóa người dùng hoạt động thế nào": "explore",
            "監査ログの仕組み": "explore",
            "audit history deletion": "text",
        }
        for question, route in cases.items():
            with self.subTest(question=question):
                result = self.route(question)
                self.assertEqual(result["route"], route, result.get("reason"))
                self.assertTrue(result["reason"])

    def test_route_results_match_the_commands(self):
        path = self.route("src/users.py -> src/audit.py")
        self.assertTrue(path["found"])
        self.assertEqual(path["arguments"], {"source": "src/users.py", "target": "src/audit.py"})
        impact = self.route("impact of changing src/audit.py")
        self.assertIn("src/users.py", {n["path"] for n in impact["nodes"]})
        explore = self.route("how does the audit workflow work")
        self.assertIn("nodes", explore)
        self.assertTrue(explore["results"])

    def test_keyword_without_known_node_falls_back(self):
        result = self.route("what depends on NoSuchThing")
        self.assertEqual(result["route"], "text")
        self.assertIn("results", result)

    def test_routes_come_from_configuration(self):
        self.store.cfg = {**self.store.cfg, "query_routes": {**DEFAULTS["query_routes"], "impact": {"en": ["blast radius"]}}}
        self.assertEqual(self.route("blast radius src/audit.py")["route"], "impact")
        # The default impact keyword is no longer configured, so the same question is not routed to impact.
        self.assertNotEqual(self.route("impact of changing src/audit.py")["route"], "impact")

    def test_cli_query_and_old_commands(self):
        cli = SKILL / "scripts/qkb.py"

        def run(*args):
            proc = subprocess.run([sys.executable, "-s", str(cli), "--root", str(self.root), *args, "--format", "json"],
                                  text=True, encoding="utf-8", capture_output=True, timeout=60)
            return proc.returncode, json.loads(proc.stdout)
        code, data = run("query", "how does the audit workflow work", "--top", "3")
        self.assertEqual(code, 0, data)
        self.assertEqual(data["route"], "explore")
        self.assertLessEqual(len(data["results"]), 3)
        code, data = run("query", "Audit workflow", "--project", "nope")
        self.assertEqual(code, 0, data)
        self.assertEqual(data["results"], [])
        self.assertEqual(run("query", " ")[0], 2)


if __name__ == "__main__":
    unittest.main()
