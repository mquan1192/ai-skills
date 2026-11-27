from support import Fixture
from core import QError, ident
import engine


class GraphTests(Fixture):
    def test_reference_direction_and_exact_anchor(self):
        row = self.store.rows("SELECT e.* FROM edges e JOIN nodes n ON n.id=e.target WHERE e.path='docs/auth.md' AND e.relation='REFERENCES' AND e.state='CURRENT' AND n.label='Events'")[0]
        source = self.store.rows("SELECT * FROM nodes WHERE id=?", (row["source"],))[0]
        target = self.store.rows("SELECT * FROM nodes WHERE id=?", (row["target"],))[0]
        self.assertEqual(source["label"], "Audit workflow")
        self.assertEqual(target["label"], "Events")
        self.assertEqual(row["origin"], "EXTRACTED")

    def test_directed_path_and_reverse_option(self):
        a = self.store.rows("SELECT * FROM nodes WHERE label='Audit workflow'")[0]["id"]
        b = self.store.rows("SELECT * FROM nodes WHERE label='Events'")[0]["id"]
        self.assertTrue(engine.find_path(self.store,a,b)["found"])
        self.assertFalse(engine.find_path(self.store,b,a)["found"])
        reverse = engine.find_path(self.store,b,a,direction="both")
        self.assertTrue(reverse["steps"][0]["traversed_reverse"])

    def test_ast_import_and_incoming_impact(self):
        result = engine.find_path(self.store,"src/users.py","src/audit.py")
        self.assertTrue(result["found"])
        self.assertEqual(result["steps"][0]["relation"], "IMPORTS")
        impact = engine.traverse(self.store,"src/audit.py",direction="in",impact=True)
        self.assertIn("src/users.py", [n["path"] for n in impact["nodes"]])
        self.assertEqual(len([e for e in engine.graph_edges(self.store) if e["relation"] == "IMPORTS"]),1)

    def test_unresolved_external_import_not_fabricated_as_local_file(self):
        self.write("src/external.py", "import json\nimport missing_local\n")
        engine.update(self.store)
        self.assertFalse(self.store.rows("SELECT * FROM edges WHERE path='src/external.py' AND relation='IMPORTS'"))
        self.assertGreaterEqual(engine.status(self.store)["unresolved_import_sites"],2)
        self.write("src/missing_local.py", "def available():\n    pass\n")
        engine.update(self.store)
        self.assertTrue(engine.find_path(self.store,"src/external.py","src/missing_local.py")["found"])

    def test_repo_relative_backtick_code_reference(self):
        edges = self.store.rows("SELECT * FROM edges WHERE path='docs/auth.md' AND relation='REFERENCES'")
        target = self.store.rows("SELECT id FROM nodes WHERE path='src/users.py' AND type='CODE_FILE'")[0]["id"]
        self.assertIn(target,[e["target"] for e in edges])

    def test_relative_link_with_spaces_and_unicode(self):
        self.write("docs/日本 語.md", "# 認証\nDetails\n")
        self.write("docs/link.md", "# Link\n[local](<日本 語.md>)\n")
        engine.update(self.store)
        self.assertTrue(engine.find_path(self.store,"docs/link.md","docs/日本 語.md",depth=2)["found"])

    def test_non_python_has_no_fabricated_calls(self):
        self.assertFalse(self.store.rows("SELECT * FROM edges WHERE path='src/client.ts' AND relation='CALLS'"))
        node = self.store.rows("SELECT * FROM nodes WHERE path='src/client.ts'")[0]
        self.assertEqual(node["type"], "CODE_FILE")

    def test_reference_is_not_dependency_impact(self):
        impact = engine.traverse(self.store, "docs/audit.md", direction="in", impact=True)
        self.assertEqual(impact["edges"], [])

    def test_supersedes_direction(self):
        path = engine.find_path(self.store,"docs/decision.md","docs/legacy.md")
        self.assertTrue(path["found"])
        self.assertEqual(path["steps"][0]["relation"], "SUPERSEDES")

    def test_broken_link_report_and_recovery(self):
        self.write("docs/broken.md", "# Broken\n[bad](missing.md)\n")
        engine.update(self.store)
        self.assertFalse(engine.verify(self.store)["ok"])
        edges = [e for e in engine.graph_edges(self.store) if e["path"] == "docs/broken.md" and e["relation"] == "REFERENCES"]
        self.assertEqual(edges[0]["state"], "BROKEN")
        self.assertIsNone(edges[0]["start"])
        self.write("docs/missing.md", "# Found\nHere\n")
        engine.update(self.store)
        self.assertTrue(engine.find_path(self.store,"docs/broken.md","docs/missing.md",depth=2)["found"])

    def test_ambiguous_labels_require_id(self):
        with self.assertRaises(QError): engine.resolve_node(self.store,"Authentication")

    def test_stale_target_edge_not_traversed(self):
        self.write("docs/audit.md", "# Different\nChanged\n")
        result = engine.find_path(self.store,"Audit workflow","Events")
        self.assertFalse(result["found"])
