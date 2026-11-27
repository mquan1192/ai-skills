import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import SKILL, package_fixture
from core import VERSION


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qkb-install-")
        self.base = Path(self.temp.name)
        self.stage, self.repo = self.base/"stage", self.base/"repo"
        self.repo.mkdir()
        # Fixture root built from package files only, never the folder around the skill.
        if not package_fixture(self.stage):
            self.temp.cleanup()
            self.skipTest("installer files not present (installed copy); run from the package folder")
        files = {}
        for file in self.stage.rglob("*"):
            if file.is_file() and file.name != "MANIFEST.json":
                files[file.relative_to(self.stage).as_posix()] = {"sha256":hashlib.sha256(file.read_bytes()).hexdigest()}
        (self.stage/"MANIFEST.json").write_text(json.dumps({"product":"Q-KnowledgeBase","version":VERSION,"files":files}))

    def tearDown(self): self.temp.cleanup()

    def invoke(self,*args):
        proc = subprocess.run([sys.executable,"-s",str(self.stage/"Q-KnowledgeBase-install.py"),"--target",str(self.repo),*args],text=True,encoding="utf-8",capture_output=True,timeout=30)
        return proc.returncode,json.loads(proc.stdout)

    def test_dry_run_has_no_filesystem_mutation(self):
        code,result = self.invoke("--dry-run")
        self.assertEqual(code,0)
        self.assertTrue(result["would_copy"])
        self.assertEqual(list(self.repo.iterdir()),[])

    def test_preserves_claude_config_other_skills_and_existing_ignore(self):
        originals = {"CLAUDE.md":"Company rules", ".claude/settings.json":'{"keep":true}', ".claude/skills/other/SKILL.md":"Other skill", ".qkb/config.json":'{"project_name":"Existing"}', ".qkb/.gitignore":"custom-pattern\n"}
        for name,text in originals.items():
            path = self.repo/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(text)
        code,result = self.invoke()
        self.assertEqual(code,0,result)
        for name,text in originals.items(): self.assertEqual((self.repo/name).read_text(),text)
        self.assertTrue((self.repo/".claude/skills/q-knowledgebase/SKILL.md").exists())
        code,result = self.invoke()
        self.assertEqual(code,0,result)
        self.assertEqual(result["copied"],0)

    def test_collision_preflight_prevents_partial_install(self):
        path = self.repo/".claude/skills/q-knowledgebase/SKILL.md"
        path.parent.mkdir(parents=True); path.write_text("Existing edited skill")
        code,result = self.invoke()
        self.assertEqual(code,2)
        self.assertIn(".claude/skills/q-knowledgebase/SKILL.md",result["conflicts"])
        self.assertEqual(path.read_text(),"Existing edited skill")
        self.assertFalse((self.repo/"Q-KnowledgeBase-README.md").exists())

    def test_tampered_package_fails_before_copy(self):
        with (self.stage/".claude/skills/q-knowledgebase/scripts/qkb.py").open("a") as handle: handle.write("\n# Tampered\n")
        code,result = self.invoke()
        self.assertEqual(code,2)
        self.assertEqual(list(self.repo.iterdir()),[])

    def test_destination_symlink_refused(self):
        outside = self.base/"outside"; outside.mkdir()
        try: (self.repo/".claude").symlink_to(outside,target_is_directory=True)
        except OSError: self.skipTest("OS does not allow symlink creation")
        code,result = self.invoke()
        self.assertEqual(code,2)
        self.assertEqual(list(outside.iterdir()),[])
