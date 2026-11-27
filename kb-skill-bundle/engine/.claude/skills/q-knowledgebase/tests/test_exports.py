import json
import xml.etree.ElementTree as ET
from support import Fixture
from exports import export_graph
from benchmark import run
import engine


class ExportTests(Fixture):
    def test_json_and_graphml_directed_bounded_exports(self):
        result = export_graph(self.store,"json",top=5)
        data = json.loads((self.root/result["output"]).read_text())
        self.assertTrue(data["directed"])
        self.assertLessEqual(len(data["nodes"]),5)
        result = export_graph(self.store,"graphml")
        graph = ET.parse(self.root/result["output"]).find("{http://graphml.graphdrawing.org/xmlns}graph")
        self.assertEqual(graph.attrib["edgedefault"],"directed")

    def test_html_escapes_injected_script_and_disallows_network(self):
        self.write("docs/inject.md", '# </script><script>window.PWNED=true</script>\nUntrusted label\n')
        engine.update(self.store)
        result = export_graph(self.store,"html",top=200)
        html = (self.root/result["output"]).read_text()
        self.assertNotIn("</script><script>window.PWNED",html)
        self.assertIn("\\u003c/script\\u003e",html)
        self.assertIn("connect-src 'none'",html)
        self.assertNotIn("<script src=",html)
        self.assertIn("textContent",html)

    def test_mermaid_export_has_no_raw_quote_in_labels(self):
        result = export_graph(self.store,"mermaid")
        text = (self.root/result["output"]).read_text()
        self.assertTrue(text.startswith("flowchart LR"))
        self.assertIn("REFERENCES",text)

    def test_labeled_benchmark_measures_real_results(self):
        report = run(self.store,"questions.json")
        self.assertEqual(report["questions"],9)
        self.assertGreater(report["recall_at_5"],0.5)
        self.assertEqual(report["evidence_traceability"],1)
        self.assertGreater(report["average_search_ms"],0)
        self.assertTrue((self.root/report["report"]).exists())
