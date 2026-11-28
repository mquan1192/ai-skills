"""v2.0.3 K1 / K3: readable names in the bundle texts (old names still accepted) and the time-stamp rule.
Reads the bundle files only; the engine ID parser is imported from the bundled engine (no install)."""
import json
import os
import re
import sys
import unittest

BUNDLE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ENGINE_SCRIPTS = os.path.join(BUNDLE, "engine", ".claude", "skills", "q-knowledgebase", "scripts")


def read(rel):
    with open(os.path.join(BUNDLE, *rel.split("/")), encoding="utf-8") as f:
        return f.read()


class ReadableNamesTests(unittest.TestCase):
    def test_request_forms_use_new_labels_and_accept_old(self):
        for rel in ("skills/q-kb-request/SKILL.md", "templates/request.md", "templates/manager/README.md"):
            text = read(rel)
            for label in ("[USER]", "[CODE]", "[DOC]", "[INFER]"):
                self.assertIn(label, text, rel)
            self.assertRegex(text, r"(?i)old (short )?labels .*\[U\].*\[C\].*\[D\].*\[I\].* accepted", rel)
        conv = read("skills/q-kb-ingest/references/kb-conventions.md")
        self.assertIn("`[USER]`, `[CODE]`, `[DOC]`, `[INFER]`", conv)
        self.assertIn("old `[U]`, `[C]`, `[D]`, `[I]` mean the same", conv)

    def test_open_points_use_open_and_old_op_stays_valid(self):
        conv = read("skills/q-kb-ingest/references/kb-conventions.md")
        self.assertIn("**OPEN-012**", conv)
        self.assertIn("existing `OP-…` IDs are kept", conv)
        for rel in ("templates/pages/document.md", "templates/pages/topic.md"):
            text = read(rel)
            self.assertIn("**OPEN-001**", text, rel)
            self.assertNotIn("**OP-001**", text, rel)
        cfg = json.loads(read("templates/kb.config.example.json"))
        self.assertEqual(cfg["issue_id_patterns"][:2], ["OPEN-\\d+", "OP-\\d+"])
        self.assertIn('"issue_id_patterns": ["OPEN-\\\\d+", "OP-\\\\d+"]', read("install.py"))

    def test_engine_parses_both_open_and_op_with_the_default_patterns(self):
        sys.path.insert(0, ENGINE_SCRIPTS)
        try:
            import idlinks
        finally:
            sys.path.remove(ENGINE_SCRIPTS)
        cfg = json.loads(read("templates/kb.config.example.json"))
        compiled = idlinks.compile_patterns({"issue_id_patterns": cfg["issue_id_patterns"], "id_patterns": {}})
        self.assertEqual(idlinks.definition("- **OPEN-012** · Trạng thái: mở · Ảnh hưởng: `src/a.cpp`", compiled), ("OPEN-012", "issue"))
        self.assertEqual(idlinks.definition("- **OP-003** · Trạng thái: mở", compiled), ("OP-003", "issue"))
        ids = [i for i, _, _ in idlinks.find_ids("xem OPEN-012 và OP-003", compiled)]
        self.assertEqual(ids, ["OPEN-012", "OP-003"])


class RequestPrefixTextTests(unittest.TestCase):
    def test_request_skill_and_templates_name_request_prefixes(self):
        skill = read("skills/q-kb-request/SKILL.md")
        self.assertIn("first entry of `request_prefixes`", skill)
        self.assertIn("read files with any listed prefix", skill)
        self.assertIn("first entry of `request_prefixes`", read("templates/manager/README.md"))
        cfg = json.loads(read("templates/kb.config.example.json"))
        self.assertEqual(cfg["request_prefixes"], ["REQ-", "KB-REQ-"])     # 2.0.4: both read, REQ- written


class TimeStampRuleTests(unittest.TestCase):
    def test_manager_template_publish_step_has_hh_mm(self):
        text = read("templates/manager/README.md")
        self.assertIn("local time `HH:MM`", text)
        self.assertIn("`(YYYY-MM-DD HH:MM, <manager session>, <request IDs>)`", text)
        self.assertIn("`## YYYY-MM-DD HH:MM — <topic>`", text)
        self.assertRegex(text, r'"Last update" line: `YYYY-MM-DD HH:MM`')
        self.assertIn("new lines only", text)


class LogRetentionNoteTests(unittest.TestCase):
    def test_readme_names_the_log_folders_and_14_days_and_never_deletes(self):
        text = read("README_VN.md")
        for folder in ("process-log/kb-usage/", "process-log/kb-hooks/", "process-log/kb-observe/"):
            self.assertIn(folder, text)
        self.assertIn("**90 ngày**", text)
        self.assertIn("**không bao giờ tự xóa**", text)

    def test_no_code_deletes_log_files(self):
        for rel in ("hooks/kbcommon.py", "hooks/kbwatch.py", "hooks/kbguard.py", "hooks/kbroute.py"):   # kbscope.py only removes its own scope.json on clear
            text = read(rel)
            self.assertNotRegex(text, r"os\.(remove|unlink)\(|shutil\.rmtree\(", rel)


if __name__ == "__main__":
    unittest.main()
