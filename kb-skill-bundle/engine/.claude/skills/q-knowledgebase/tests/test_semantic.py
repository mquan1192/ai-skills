import copy
import json
from support import Fixture
from core import QError
import engine
import semantic


class SemanticTests(Fixture):
    def test_valid_evidence_and_unapproved_exclusion(self):
        data = self.proposal()
        self.assertEqual(semantic.validate(self.store,data)["state"], "VALID")
        id_ = self.import_proposal(data)
        self.assertNotIn(id_, [e["id"] for e in engine.graph_edges(self.store)])

    def test_missing_incorrect_quote_and_wrong_section(self):
        for edit in ("missing", "quote", "section", "hash", "range"):
            data = self.proposal()
            if edit == "missing": data["evidence"] = []
            if edit == "quote": data["evidence"][0]["quote"] = "Fabricated evidence"
            if edit == "section": data["evidence"][0]["section_id"] = "bad-section"
            if edit == "hash": data["evidence"][0]["hash"] = "0"*64
            if edit == "range": data["evidence"][0]["end"] = 99999
            self.assertEqual(semantic.validate(self.store,data)["state"], "INVALID", edit)

    def test_approval_requires_explicit_human_assertion(self):
        id_ = self.import_proposal()
        with self.assertRaises(QError): semantic.review(self.store,id_,"APPROVED","Reviewer","Valid",False)
        semantic.review(self.store,id_,"APPROVED","Reviewer","Reviewed exact evidence and direction",True)
        edge = [e for e in engine.graph_edges(self.store) if e["id"] == id_][0]
        self.assertEqual(edge["origin"], "INFERRED")
        self.assertEqual(edge["state"], "CURRENT")
        data = self.proposal()
        self.assertTrue(engine.find_path(self.store,data["source"],data["target"])["found"])
        impact = engine.traverse(self.store,data["target"],direction="in",impact=True)
        self.assertIn(data["source"], [n["id"] for n in impact["nodes"]])

    def test_reject_preserved_on_duplicate_import(self):
        data = self.proposal()
        id_ = self.import_proposal(data)
        semantic.review(self.store,id_,"REJECTED","Reviewer","Insufficient semantic support")
        self.assertEqual(self.import_proposal(data), id_)
        self.assertEqual(self.store.rows("SELECT decision FROM proposals WHERE id=?", (id_,))[0]["decision"], "REJECTED")
        self.assertNotIn(id_, [e["id"] for e in engine.graph_edges(self.store)])
        reordered = dict(reversed(list(data.items())))
        self.assertEqual(self.import_proposal(reordered),id_)

    def test_approved_relation_stales_on_change_and_keeps_history(self):
        id_ = self.import_proposal()
        semantic.review(self.store,id_,"APPROVED","Reviewer","Reviewed",True)
        old = (self.root/"docs/auth.md").read_text(encoding="utf-8-sig")
        self.write("docs/auth.md", "New preamble\n"+old)
        # Before update the graph must also refuse to present stale evidence.
        edge = [e for e in engine.graph_edges(self.store) if e["id"] == id_][0]
        self.assertEqual(edge["state"], "STALE")
        self.assertIsNone(edge["start"])
        self.assertIsNone(edge["evidence"])
        engine.update(self.store)
        self.assertEqual(self.store.rows("SELECT validation FROM proposals WHERE id=?",(id_,))[0]["validation"],"STALE")
        self.assertTrue(self.store.rows("SELECT * FROM reviews WHERE action='INVALIDATED'"))

    def test_contradictory_relationship_requires_acknowledgment(self):
        first = self.import_proposal()
        semantic.review(self.store,first,"APPROVED","Reviewer","Reviewed",True)
        second = self.import_proposal(self.proposal("CONFLICTS_WITH"))
        with self.assertRaises(QError): semantic.review(self.store,second,"APPROVED","Reviewer","Reviewed",True)
        result = semantic.review(self.store,second,"APPROVED","Reviewer","Human resolved contextual distinction",True,True)
        self.assertTrue(result["conflicts"])

    def test_evidence_must_cover_both_endpoint_sources(self):
        data = self.proposal()
        data["evidence"] = data["evidence"][:1]
        self.assertEqual(semantic.validate(self.store,data)["state"], "INVALID")

    def test_candidate_endpoint_and_unknown_relation_refused(self):
        for change in ("candidate", "relation"):
            data = self.proposal()
            if change == "candidate": data["source"] = self.store.rows("SELECT id FROM nodes WHERE type='MODULE'")[0]["id"]
            else: data["relation"] = "MAGIC_CAUSES"
            self.assertEqual(semantic.validate(self.store,data)["state"], "INVALID")

    def test_invalid_import_is_atomic(self):
        data = self.proposal()
        bad = copy.deepcopy(data); bad["evidence"][0]["quote"] = "incorrect"
        self.write(".qkb/proposals/input.json",json.dumps([data,bad]))
        with self.assertRaises(QError): semantic.import_proposals(self.store,".qkb/proposals/input.json")
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM proposals").fetchone()[0],0)
