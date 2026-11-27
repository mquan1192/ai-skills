import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from support import package_fixture, populate


class OfflineInstallTests(unittest.TestCase):
    def test_fresh_zip_repository_full_cli_and_uninstall(self):
        with tempfile.TemporaryDirectory(prefix="qkb-offline-") as temp:
            work = Path(temp)
            zip_path, repo = work/"Q-KnowledgeBase.zip", work/"repository with Unicode 日本語"
            # Fixture root built from package files only, never the folder around the skill.
            package = work/"package"
            package_fixture(package)
            with zipfile.ZipFile(zip_path,"w",zipfile.ZIP_DEFLATED) as archive:
                for file in sorted(package.rglob("*")):
                    if file.is_file():
                        archive.write(file,file.relative_to(package).as_posix())
            repo.mkdir()
            populate(repo)
            original_docs = {p.relative_to(repo).as_posix():p.read_bytes() for folder in (repo/"docs",repo/"src") for p in folder.rglob("*") if p.is_file()}
            (repo/"CLAUDE.md").write_text("Keep existing project rules\n")
            (repo/".claude").mkdir()
            (repo/".claude/settings.json").write_text('{"existing":true}')
            with zipfile.ZipFile(zip_path) as archive:
                self.assertIsNone(archive.testzip())
                self.assertIn(".claude/skills/q-knowledgebase/SKILL.md",archive.namelist())
                self.assertNotIn("CLAUDE.md",archive.namelist())
                self.assertNotIn(".claude/settings.json",archive.namelist())
                archive.extractall(repo)
            cli = repo/".claude/skills/q-knowledgebase/scripts/qkb.py"

            def run(*args, expected=0):
                proc = subprocess.run([sys.executable,"-s",str(cli),*args,"--format","json"],cwd=repo,text=True,encoding="utf-8",capture_output=True,timeout=30)
                self.assertEqual(proc.returncode,expected,proc.stdout+proc.stderr)
                return json.loads(proc.stdout)

            before_preview = {p.relative_to(repo).as_posix():p.read_bytes() for p in repo.rglob("*") if p.is_file()}
            self.assertTrue(run("doctor")["python_supported"])
            self.assertEqual(run("status")["state"],"UNVERIFIED")
            self.assertTrue(run("init","--dry-run")["dry_run"])
            after_preview = {p.relative_to(repo).as_posix():p.read_bytes() for p in repo.rglob("*") if p.is_file()}
            self.assertEqual(before_preview,after_preview)
            self.assertEqual(run("init")["config"],"preserved")
            self.assertEqual(run("build")["added"],11)
            hit = run("search","Audit workflow")["results"][0]
            self.assertIn("Deleting a user",run("read",hit["id"])["sections"][0]["content"])
            self.assertTrue(run("path","src/users.py","src/audit.py")["found"])
            self.assertTrue(run("verify")["ok"])
            self.assertTrue(run("explore","Audit workflow")["results"])
            self.assertEqual(run("update")["modified"],0)
            self.assertTrue((repo/run("backup")["output"]).exists())
            self.assertTrue((repo/run("export","--kind","html")["output"]).exists())
            with (repo/"docs/legacy.md").open("a",encoding="utf-8") as handle: handle.write("Updated historical note.\n")
            original_docs["docs/legacy.md"] = (repo/"docs/legacy.md").read_bytes()
            self.assertEqual(run("update")["modified"],1)
            self.assertTrue(run("verify")["ok"])
            # Uninstall package files and derived QKB data in the throwaway repo.
            shutil.rmtree(repo/".claude/skills/q-knowledgebase")
            (repo/".claude/rules/q-knowledgebase.md").unlink()
            shutil.rmtree(repo/".qkb")
            for path,raw in original_docs.items(): self.assertEqual((repo/path).read_bytes(),raw)
            self.assertEqual((repo/"CLAUDE.md").read_text(),"Keep existing project rules\n")
            self.assertEqual((repo/".claude/settings.json").read_text(),'{"existing":true}')
