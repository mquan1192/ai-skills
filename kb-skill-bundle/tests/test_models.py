"""Offline tests of tools/download-models.ps1 / .sh (no network: files come from a local folder via -FromFolder / --from).
Each case uses a temp manifest with small fake files. Skipped when the shell is not available."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

# a real KB-Model_*.zip may sit beside the bundle (auto-detect): only AutoDetectModelZipTests looks for it
os.environ["KBINSTALL_TEST_NO_MODEL_SEARCH"] = "1"
BUNDLE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
TOOLS = os.path.join(BUNDLE, "tools")
POWERSHELL = shutil.which("pwsh")     # 2.0.4: download-models.ps1 is PowerShell 7 only (5.1 is refused)
# The .sh script targets macOS / Linux (it tries python3, then python), so the .sh case runs only there.
SH = shutil.which("sh") if (os.name != "nt" and (shutil.which("python3") or shutil.which("python"))
                            and (shutil.which("sha256sum") or shutil.which("shasum"))) else None


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.target = os.path.join(self.tmp, "proj")
        self.src = os.path.join(self.tmp, "downloaded")
        os.makedirs(self.target)
        os.makedirs(os.path.join(self.src, "onnx"))
        self.files = {"onnx/model.onnx": b"\x08\x01" * 4000, "tokenizer.json": b'{"v": 1}' * 100}
        for path, data in self.files.items():
            with open(os.path.join(self.src, *path.split("/")), "wb") as f:
                f.write(data)

    def tearDown(self):
        self._tmp.cleanup()

    def manifest(self, wrong_hash=False, ext=".onnx", fill=True):
        files = []
        for path, data in self.files.items():
            p = path if path.endswith(".json") else path.replace(".onnx", ext)
            files.append({"path": p, "url": "https://example.invalid/" + p, "approx_mb": 1, "bytes": None,
                          "sha256": ("0" * 64 if wrong_hash else sha(data)) if fill else "", "required": True})
        data = {"version": 1, "default": "demo-model", "allowed_extensions": [".onnx", ".json"],
                "models": {"demo-model": {"source_page": "https://example.invalid", "licence": "MIT", "revision": "",
                                          "dest": "demo-model", "files": files}}}
        path = os.path.join(self.tmp, "m.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return path

    def dest(self, *parts):
        return os.path.join(self.target, ".qkb", "models", "demo-model", *parts)


@unittest.skipUnless(POWERSHELL, "PowerShell not available")
class PowerShellTests(Base):
    def run_ps(self, *args):
        r = subprocess.run([POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                            os.path.join(TOOLS, "download-models.ps1"), "-Target", self.target] + list(args),
                           capture_output=True, timeout=120)
        return r.returncode, (r.stdout + r.stderr).decode("utf-8", "replace")

    def test_shipped_manifest_refuses_without_hashes(self):
        code, out = self.run_ps()
        self.assertEqual(code, 2, out)
        self.assertIn("chưa điền sha256", out)
        self.assertFalse(os.path.exists(os.path.join(self.target, ".qkb")))

    def test_plan_then_apply_from_folder(self):
        m = self.manifest()
        code, out = self.run_ps("-Manifest", m)
        self.assertEqual(code, 0, out)
        self.assertIn("KẾ HOẠCH", out)
        self.assertFalse(os.path.exists(os.path.join(self.target, ".qkb")))
        code, out = self.run_ps("-Manifest", m, "-Apply", "-FromFolder", self.src)
        self.assertEqual(code, 0, out)
        for path, data in self.files.items():
            with open(self.dest(*path.split("/")), "rb") as f:
                self.assertEqual(f.read(), data)
        self.assertTrue(os.path.isfile(self.dest("MODEL.txt")))
        code, out = self.run_ps("-Manifest", m, "-Apply", "-FromFolder", self.src)     # second run: already there
        self.assertEqual(code, 0, out)
        self.assertIn("ĐÃ CÓ, đúng mã", out)

    def test_wrong_hash_leaves_nothing(self):
        code, out = self.run_ps("-Manifest", self.manifest(wrong_hash=True), "-Apply", "-FromFolder", self.src)
        self.assertEqual(code, 1, out)
        self.assertIn("KHÔNG ĐẠT SHA256", out)
        left = [n for _, _, ns in os.walk(self.target) for n in ns]
        self.assertEqual(left, [])

    def test_bad_extension_refused(self):
        code, out = self.run_ps("-Manifest", self.manifest(ext=".exe"), "-Apply", "-FromFolder", self.src)
        self.assertEqual(code, 2, out)
        self.assertIn("đuôi file không được phép", out)


@unittest.skipUnless(SH, "sh + python3 / python + sha256sum not available")
class ShTests(Base):
    def run_sh(self, *args):
        r = subprocess.run([SH, os.path.join(TOOLS, "download-models.sh"), "--target", self.target] + list(args),
                           capture_output=True, timeout=120)
        return r.returncode, (r.stdout + r.stderr).decode("utf-8", "replace")

    def test_sh_refuses_without_hashes_and_applies_from_folder(self):
        code, out = self.run_sh("--manifest", self.manifest(fill=False))
        self.assertEqual(code, 2, out)
        code, out = self.run_sh("--manifest", self.manifest(), "--apply", "--from", self.src)
        self.assertEqual(code, 0, out)
        self.assertTrue(os.path.isfile(self.dest("onnx", "model.onnx")))
        code, out = self.run_sh("--manifest", self.manifest(wrong_hash=True), "--apply", "--from", self.src)
        self.assertIn(code, (0, 1))      # files already present with the right content are kept; wrong manifest hash -> re-check


class ManifestTests(unittest.TestCase):
    def test_shipped_manifest(self):
        with open(os.path.join(TOOLS, "models.manifest.json"), encoding="utf-8") as f:
            m = json.load(f)
        e = m["models"][m["default"]]
        self.assertEqual(m["default"], "multilingual-e5-small")
        self.assertEqual([f["path"] for f in e["files"]], ["onnx/model.onnx", "tokenizer.json", "config.json",
                                                            "tokenizer_config.json"])
        for f in e["files"]:
            self.assertTrue(f["url"].startswith("https://huggingface.co/intfloat/multilingual-e5-small/resolve/main/"))
            self.assertEqual(f["sha256"], "")             # IT fills these from the source page
            self.assertIn(os.path.splitext(f["path"])[1], m["allowed_extensions"])


if __name__ == "__main__":
    unittest.main()


def make_model_zip(folder, name="demo-model", files=None, bad_hash=False, extra=None):
    """A model zip as download-models -Zip writes it: <name>/MODEL.txt + .onnx / .json files."""
    import zipfile
    files = files or {"onnx/model.onnx": b"\x08\x01" * 500, "tokenizer.json": b'{"model": {"type": "Unigram"}}'}
    path = os.path.join(folder, "KB-Model_%s.zip" % name)
    lines = ["model: " + name]
    for p, data in files.items():
        lines.append("%s  sha256 %s" % (p, "0" * 64 if bad_hash else sha(data)))
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(name + "/MODEL.txt", "\n".join(lines) + "\n")
        for p, data in files.items():
            z.writestr(name + "/" + p, data)
        for n, data in (extra or {}).items():
            z.writestr(n, data)
    return path


class KbModelTests(Base):
    def run_py(self, *args):
        r = subprocess.run([sys.executable, "-E", "-s", "-B", os.path.join(TOOLS, "kbmodel.py")] + list(args),
                           capture_output=True, timeout=120)
        return r.returncode, (r.stdout + r.stderr).decode("utf-8", "replace")

    def test_from_zip_plan_apply_and_check(self):
        z = make_model_zip(self.tmp)
        code, out = self.run_py("from-zip", z, "--target", self.target)
        self.assertEqual(code, 0, out)
        self.assertFalse(os.path.exists(os.path.join(self.target, ".qkb")))
        code, out = self.run_py("from-zip", z, "--target", self.target, "--apply")
        self.assertEqual(code, 0, out)
        self.assertTrue(os.path.isfile(self.dest("onnx", "model.onnx")))
        self.assertEqual(self.run_py("check", "--target", self.target, "--model", "demo-model")[0], 0)
        with open(self.dest("tokenizer.json"), "ab") as f:
            f.write(b" ")
        self.assertEqual(self.run_py("check", "--target", self.target, "--model", "demo-model")[0], 1)
        code, out = self.run_py("from-zip", z, "--target", self.target, "--apply")      # replace; old copy to backups
        self.assertEqual(code, 0, out)
        self.assertTrue(any(n.startswith("model-demo-model-") for n in os.listdir(os.path.join(self.target, ".qkb", "backups"))))

    def test_unsafe_or_wrong_zips_refused(self):
        cases = {
            "hash": make_model_zip(self.tmp, "h1", bad_hash=True),
            "traversal": make_model_zip(self.tmp, "h2", extra={"h2/../evil.json": b"x"}),
            "ext": make_model_zip(self.tmp, "h3", extra={"h3/run.exe": b"x"}),
            "two-roots": make_model_zip(self.tmp, "h4", extra={"other/x.json": b"x"}),
            "missing": make_model_zip(self.tmp, "h5", files={"tokenizer.json": b"{}"}),
        }
        for label, z in cases.items():
            code, out = self.run_py("from-zip", z, "--target", self.target, "--apply")
            self.assertEqual(code, 2, (label, out))
        self.assertFalse(os.path.exists(os.path.join(self.target, ".qkb", "models")))


@unittest.skipUnless(POWERSHELL, "PowerShell not available")
class ZipRoundTripTests(Base):
    def run_ps(self, *args):
        r = subprocess.run([POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                            os.path.join(TOOLS, "download-models.ps1")] + list(args), capture_output=True, timeout=120)
        return r.returncode, (r.stdout + r.stderr).decode("utf-8", "replace")

    def test_zip_then_from_zip(self):
        m = self.manifest(fill=False)                         # -Zip accepts empty sha256 and prints the computed ones
        z = os.path.join(self.tmp, "out", "KB-Model_demo-model_20260105.zip")
        code, out = self.run_ps("-Manifest", m, "-Zip", z, "-Apply", "-FromFolder", self.src)
        self.assertEqual(code, 0, out)
        self.assertIn("IT đối chiếu", out)
        self.assertIn(sha(self.files["onnx/model.onnx"]), out)
        import zipfile
        with zipfile.ZipFile(z) as f:
            names = sorted(f.namelist())
        self.assertEqual(names, ["demo-model/MODEL.txt", "demo-model/onnx/model.onnx", "demo-model/tokenizer.json"])
        self.assertFalse(os.path.exists(z + ".work"))
        code, out = self.run_ps("-Target", self.target, "-FromZip", z, "-Apply")
        self.assertEqual(code, 0, out)
        for path, data in self.files.items():
            with open(self.dest(*path.split("/")), "rb") as f:
                self.assertEqual(f.read(), data)


class AutoDetectModelZipTests(Base):
    """A KB-Model_*.zip placed beside the bundle is found without --model / --model-zip."""
    def setUp(self):
        super().setUp()
        self.dl = os.path.join(self.tmp, "dl")
        self.bundle = os.path.join(self.dl, "kb-skill-bundle")
        shutil.copytree(BUNDLE, self.bundle, ignore=shutil.ignore_patterns("__pycache__"))

    def run_install(self, *args):
        r = subprocess.run([sys.executable, "-E", "-s", "-B", os.path.join(self.bundle, "install.py"),
                            "--target", self.target] + list(args), capture_output=True, timeout=600, stdin=subprocess.DEVNULL,
                           env={k: v for k, v in os.environ.items() if k != "KBINSTALL_TEST_NO_MODEL_SEARCH"})
        return r.returncode, (r.stdout + r.stderr).decode("utf-8", "replace")

    def test_one_zip_beside_the_bundle_is_used(self):
        z = make_model_zip(self.dl, extra={"demo-model/LICENSE_NOTE.txt": "MIT - keep this note"})
        code, out = self.run_install()                                      # dry-run, no flags
        self.assertEqual(code, 0, out)
        self.assertIn("Tìm thấy model: " + z, out)
        self.assertIn("đặt từ zip: demo-model", out)
        code, out = self.run_install("--model", "none")                     # --model none always wins
        self.assertEqual(code, 0, out)
        self.assertIn("--model none, không dùng", out)
        self.assertNotIn("Tìm thấy model", out)
        code, out = self.run_install("--apply", "--yes", "--project", "demo", "--sub", "core")
        self.assertEqual(code, 0, out)
        cfg = json.load(open(os.path.join(self.target, ".qkb", "config.json"), encoding="utf-8"))
        self.assertEqual(cfg["embedding"]["backend"], "onnx-local")
        self.assertTrue(os.path.isfile(self.dest("LICENSE_NOTE.txt")))

    def test_several_zips_stop_and_bad_zip_is_skipped(self):
        os.makedirs(os.path.join(self.bundle, "models"))
        a = make_model_zip(self.dl)
        b = make_model_zip(os.path.join(self.bundle, "models"), name="other-model")
        code, out = self.run_install()
        self.assertEqual(code, 2, out)
        self.assertIn("DỪNG", out)
        self.assertIn(a, out)
        self.assertIn(b, out)
        os.remove(a)
        os.remove(b)
        bad = make_model_zip(self.dl, bad_hash=True)
        code, out = self.run_install()
        self.assertEqual(code, 0, out)
        self.assertIn("bỏ qua file zip model " + bad, out)
        self.assertIn("model = chưa chọn", out)

    def test_licence_note_too_large_refused(self):
        sys.path.insert(0, TOOLS)
        import kbmodel
        z = make_model_zip(self.tmp, extra={"demo-model/LICENSE_NOTE.txt": "x" * (70 * 1024)})
        with self.assertRaises(kbmodel.Stop):
            kbmodel.check_zip(z)


class InstallModelZipTests(Base):
    def test_install_model_zip_turns_backend_on_and_none_turns_it_off(self):
        z = make_model_zip(self.tmp)
        install = os.path.join(BUNDLE, "install.py")
        run = lambda *a: subprocess.run([sys.executable, "-E", "-s", "-B", install, "--target", self.target] + list(a),
                                        capture_output=True, timeout=600, stdin=subprocess.DEVNULL)
        r = run("--apply", "--yes", "--model", "none", "--model-zip", z)
        self.assertEqual(r.returncode, 2)                    # --model-zip needs --model local
        r = run("--apply", "--yes", "--model", "local", "--project", "demo", "--sub", "core", "--model-zip", z)
        self.assertEqual(r.returncode, 0, r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace"))
        cfg = json.load(open(os.path.join(self.target, ".qkb", "config.json"), encoding="utf-8"))
        self.assertEqual(cfg["embedding"]["backend"], "onnx-local")
        self.assertEqual(cfg["embedding"]["model"], "demo-model")
        self.assertNotIn("mode", cfg["embedding"])           # mode stays the engine default (auto)
        r = run("--apply", "--yes", "--model", "none")
        self.assertEqual(r.returncode, 0)
        cfg = json.load(open(os.path.join(self.target, ".qkb", "config.json"), encoding="utf-8"))
        self.assertEqual(cfg["embedding"]["backend"], "none")
        self.assertTrue(os.path.isfile(self.dest("MODEL.txt")))        # files stay; only the switch changed
