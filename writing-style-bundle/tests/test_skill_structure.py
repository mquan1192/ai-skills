"""Kiểm cấu trúc skill q-writing-style bằng Python (cùng các luật chính của skills/q-writing-style/evals/structure.Tests.ps1,
cho máy không có PowerShell). Chỉ đọc. Chạy: python -B tests/test_skill_structure.py"""
import json
import re
import unicodedata
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent / "skills/q-writing-style"
REFS = ["style-guide.md", "document-patterns.md", "before-after-examples.md", "ng-vocab-vi.md", "ng-vocab-ja.md",
        "ng-vocab-en.md", "ai-tells.md", "plain-language.md", "vietnamese-register.md", "translation.md",
        "voice-profile.md"]
FILES = ["SKILL.md"] + ["references/" + r for r in REFS]


def read(rel):
    return (SKILL_DIR / rel).read_text(encoding="utf-8")


def frontmatter(text):
    lines = text.replace("\r\n", "\n").split("\n")
    assert lines[0] == "---"
    end = lines.index("---", 1)
    fm = {}
    for line in lines[1:end]:
        m = re.match(r"^([a-z][a-z0-9-]*):\s?(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2)
    return fm, len(lines) - end - 1


class SkillStructureTests(unittest.TestCase):
    def test_files_exist_utf8_nfc(self):
        for rel in FILES + ["NOTICES.md", "scripts/lint_text.py"]:
            text = read(rel)
            self.assertEqual(text, unicodedata.normalize("NFC", text), rel)

    def test_frontmatter_and_description(self):
        fm, body = frontmatter(read("SKILL.md"))
        self.assertEqual(fm["name"].strip(), "q-writing-style")
        desc = fm["description"].strip()
        self.assertTrue(100 <= len(desc) <= 520, len(desc))
        for need in ("VI / JA / EN", "báo cáo", "report", "tài liệu", "mail", "biên bản", "chat", "Jira", "報告書", "資料",
                     "メール", "dịch", "humanize", "Keywords:", "Không dùng cho:"):
            self.assertIn(need, desc)
        self.assertLessEqual(body, 120)
        self.assertLessEqual(len(read("SKILL.md").encode("utf-8")), 10240)

    def test_references_named_both_ways(self):
        skill = read("SKILL.md")
        named = set(re.findall(r"references/[a-z0-9-]+\.md", skill))
        self.assertEqual(named, {"references/" + r for r in REFS})
        self.assertIn("## Ranh giới", skill)
        for must in ("Đúng → Đủ → Rõ → Gọn → Tự nhiên", "Polish", "Restructure", "Summarize", "Rewrite", "Translate",
                     "Humanize", "Plain", "Voice", "Check", "Cổng tự soát", "Quy tắc dự án được ưu tiên", "project_rules",
                     "glossary", "Khi viết báo cáo / tài liệu"):
            self.assertIn(must, skill)

    def test_section_links_point_to_existing_sections(self):
        # "§ n" in SKILL.md / references for files that number their sections
        self.assertIn("### 1.1", read("references/style-guide.md"))
        for rel, sec in (("references/vietnamese-register.md", ("## 1.", "## 3.", "## 6.")),
                         ("references/translation.md", ("## 2.", "## 3.", "## 7.")),
                         ("references/plain-language.md", ("## 5.",))):
            for s in sec:
                self.assertIn(s, read(rel), (rel, s))
        dp = read("references/document-patterns.md")
        for letter in "ABCDEFGHIJKLMNOPQR":
            self.assertRegex(dp, r"(?m)^## %s\. " % letter)

    def test_no_line_repeated_across_files(self):
        seen, dups = {}, []
        for rel in FILES:
            local = set()
            for line in read(rel).split("\n"):
                t = line.strip()
                if len(t) < 40 or t in local:
                    continue
                local.add(t)
                if t in seen:
                    dups.append("%s + %s: %s" % (seen[t], rel, t[:60]))
                else:
                    seen[t] = rel
        self.assertEqual(dups, [])

    def test_third_party_notices_present(self):
        notices = read("NOTICES.md")
        for name in ("humanizer", "SimpleEnglish", "vietnamese-language-skill", "writing-dna-skill"):
            self.assertIn(name, notices)
        self.assertEqual(notices.count("Permission is hereby granted"), 3)
        self.assertIn("Permission is hereby granted", read("references/ng-vocab-ja.md"))
        for rel in ("references/ai-tells.md", "references/plain-language.md", "references/vietnamese-register.md"):
            self.assertIn("NOTICES.md", read(rel))
        # writing-dna-skill (PolyForm Noncommercial): ideas only, no license text or file copied
        self.assertNotIn("PolyForm Noncommercial License 1.0.0\n", "".join(read(r) for r in FILES))

    def test_evals(self):
        ev = json.loads(read("evals/evals.json"))
        self.assertEqual(ev["skill"], "q-writing-style")
        cases = ev["cases"]
        self.assertGreaterEqual(len(cases), 10)
        ids = [c["id"] for c in cases]
        self.assertEqual(len(ids), len(set(ids)))
        check_ids = []
        for c in cases:
            self.assertTrue(c["input"] and c["prompt"], c["id"])
            kinds = {x["kind"] for x in c["checks"]}
            self.assertTrue({"meaning", "numbers"} <= kinds, c["id"])
            self.assertGreaterEqual(sum(1 for x in c["checks"] if x["must"] is True), 2, c["id"])
            check_ids += [x["id"] for x in c["checks"]]
        self.assertEqual(len(check_ids), len(set(check_ids)))
        modes = {c["mode"] for c in cases}
        for m in ("humanize", "plain", "translate", "voice"):
            self.assertIn(m, modes)

    def test_trigger(self):
        tr = json.loads(read("evals/trigger.json"))
        self.assertEqual(tr["skill"], "q-writing-style")
        self.assertGreaterEqual(len(tr["should_trigger"]), 10)
        self.assertGreaterEqual(len(tr["near_miss"]), 5)
        self.assertTrue(all(n.get("expect") for n in tr["near_miss"]))
        joined = "\n".join(tr["should_trigger"])
        self.assertIn("báo cáo", joined)
        self.assertRegex(joined, "報告書|資料|メール")


if __name__ == "__main__":
    unittest.main()
