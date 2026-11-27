"""Optional local model search, tested with a mock embedder (no model file, no third-party package)."""
import array
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import SKILL
from core import DEFAULTS, QError, Store, fold, load_config
import engine
import vectors

SYNONYMS = {"automobile": "car", "vehicle": "car", "repair": "fix", "mend": "fix"}


class MockEmbedder:
    """Deterministic bag-of-words vectors; a few synonyms map to one word (simulates a paraphrase the text search
    cannot bridge)."""
    calls = 0

    def __init__(self, store, folder, prof):
        model, tokenizer, hashes = vectors.verified(store, folder)
        self.identity = {"model_sha256": hashes["onnx/model.onnx"], "tokenizer_sha256": hashes["tokenizer.json"]}

    def embed(self, texts, kind):
        MockEmbedder.calls += len(texts)
        out = []
        for text in texts:
            v = [0.0] * 64
            for word in fold(text).split():
                word = SYNONYMS.get(word.strip(".,?"), word.strip(".,?"))
                if len(word) > 2:
                    v[int(hashlib.md5(word.encode()).hexdigest(), 16) % 64] += 1.0
            norm = sum(x * x for x in v) ** 0.5 or 1.0
            out.append(array.array("f", [x / norm for x in v]))
        return out


PAGES = {
    "kb/demo/garage.md": "# Garage\n## Car fix guide\nHow to fix a car engine at the garage: open the hood, check oil.\n",
    "kb/demo/kitchen.md": "# Kitchen\n## Recipes\nBake bread with flour and water.\n",
    "kb/demo/codes.md": "# Codes\n## Error E-1001\nError E-1001 means the job stopped.\n",
}
TOKENIZER = {"model": {"type": "Unigram", "unk_id": 3,
                       "vocab": [["<s>", 0.0], ["<pad>", 0.0], ["</s>", 0.0], ["<unk>", 0.0], ["▁", -2.0], ["▁car", -1.0],
                                 ["▁ca", -3.0], ["r", -3.0], ["▁fix", -1.0], ["▁the", -0.5], ["▁engine", -1.5],
                                 ["▁en", -2.5], ["gine", -2.5], ["s", -2.0]]}}


class VectorCase(unittest.TestCase):
    def setUp(self):
        vectors.BACKENDS["mock"] = MockEmbedder
        self.addCleanup(vectors.BACKENDS.pop, "mock", None)
        temp = tempfile.TemporaryDirectory(prefix="qkb-e-vec-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for path, text in PAGES.items():
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            (self.root / path).write_text(text, encoding="utf-8")
        self.model = self.root / ".qkb/models/mock-model"
        (self.model / "onnx").mkdir(parents=True)
        (self.model / "onnx/model.onnx").write_bytes(b"not a real model")
        (self.model / "tokenizer.json").write_text(json.dumps(TOKENIZER), encoding="utf-8")
        self.write_record()
        self.cfg = {**DEFAULTS, "knowledge_paths": ["kb"], "source_paths": ["src"],
                    "embedding": {"backend": "mock", "model": "mock-model", "mode": "auto", "weight": 1.0, "min_words": 3}}
        self.store = self.open(self.cfg, create=True)
        engine.update(self.store)

    def write_record(self, model_hash=None):
        lines = ["model: mock-model"]
        for rel in ("onnx/model.onnx", "tokenizer.json"):
            h = hashlib.sha256((self.model / rel).read_bytes()).hexdigest()
            lines.append("%s  sha256 %s" % (rel, model_hash if (model_hash and rel.endswith(".onnx")) else h))
        (self.model / "MODEL.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def open(self, cfg, create=False):
        (self.root / ".qkb").mkdir(exist_ok=True)
        (self.root / ".qkb/config.json").write_text(json.dumps(cfg), encoding="utf-8")
        store = Store(self.root, load_config(self.root), create=create)
        self.addCleanup(store.db.close)
        return store


class TokenizerTests(unittest.TestCase):
    def test_unigram_viterbi(self):
        tok = vectors.UnigramTokenizer(TOKENIZER)
        ids = tok.encode("car engine", 32)
        self.assertEqual(ids, [0, 5, 10, 2])                      # <s> ▁car ▁engine </s>: best total score
        ids = tok.encode("cars", 32)
        self.assertEqual(ids, [0, 5, 13, 2])                      # ▁car + s
        ids = tok.encode("car ¤", 32)
        self.assertIn(3, ids)                                     # unknown character -> <unk>
        self.assertEqual(len(tok.encode("car " * 50, 8)), 8)      # truncated with <s> and </s>
        with self.assertRaises(QError):
            vectors.UnigramTokenizer({"model": {"type": "BPE", "vocab": []}})


class ModelFolderTests(VectorCase):
    def test_hashes_checked(self):
        model, tokenizer, hashes = vectors.verified(self.store, self.model)
        self.assertEqual(set(hashes), {"onnx/model.onnx", "tokenizer.json"})
        self.write_record(model_hash="0" * 64)
        with self.assertRaises(QError):
            vectors.verified(self.store, self.model)
        (self.model / "MODEL.txt").unlink()
        with self.assertRaises(QError):
            vectors.verified(self.store, self.model)

    def test_profile_and_folder_name(self):
        (self.model / "embedding-profile.json").write_text(json.dumps({"max_tokens": 128, "query_prefix": "q: ", "evil": 1}), encoding="utf-8")
        prof = vectors.profile(self.model, self.store.cfg)
        self.assertEqual((prof["max_tokens"], prof["query_prefix"]), (128, "q: "))
        self.assertNotIn("evil", prof)
        self.store.cfg = {**self.store.cfg, "embedding": {**self.cfg["embedding"], "model": "../x"}}
        with self.assertRaises(QError):
            vectors.model_folder(self.store)


class StoreTests(VectorCase):
    def test_refresh_changed_only_and_index_untouched(self):
        index = self.root / ".qkb/cache/index.sqlite3"
        before = index.read_bytes()
        dry = vectors.refresh(self.store, dry_run=True)
        self.assertEqual((dry["to_embed"], dry["dry_run"]), (dry["sections"], True))
        self.assertFalse((self.root / vectors.STORE).exists())
        first = vectors.refresh(self.store)
        self.assertEqual(first["to_embed"], first["sections"])
        self.assertEqual(index.read_bytes(), before)              # normal index never written by embed
        MockEmbedder.calls = 0
        again = vectors.refresh(self.store)
        self.assertEqual((again["to_embed"], MockEmbedder.calls), (0, 0))
        (self.root / "kb/demo/kitchen.md").write_text("# Kitchen\n## Recipes\nBake cake.\n", encoding="utf-8")
        self.store.hash_cache.clear()
        engine.update(self.store)
        third = vectors.refresh(self.store)
        self.assertEqual(third["to_embed"], 1)
        self.assertEqual(vectors.status(self.store)["vectors"], third["sections"])

    def test_model_change_reembeds_all(self):
        vectors.refresh(self.store)
        (self.model / "onnx/model.onnx").write_bytes(b"another model")
        self.write_record()
        result = vectors.refresh(self.store)
        self.assertTrue(result["model_changed"])
        self.assertEqual(result["to_embed"], result["sections"])


class GateTests(VectorCase):
    def gate(self, query, mode=None, match_mode="all_terms", hits=5, best=4, concepts=4):
        if match_mode == "partial_terms" and best == concepts:
            best = 1
        result = {"match_mode": match_mode, "results": [{"section_id": str(i)} for i in range(hits)],
                  "coverage": {"best": best, "concepts": concepts}}
        return vectors.gate(self.store, query, result, 5, mode)

    def test_exact_terms_never_use_the_model(self):
        for query in ("error E-1001 when the job stops", "job stops after 30 minutes", "see src/job.cpp for the fix",
                      "what does stopJob do here", "what does stop_job do here", "ERR50012B shown on screen", "version 2.1 changes",
                      "MaxRetryCount default value", "where is OrderService created"):   # PascalCase names
            with self.subTest(query=query):
                self.assertFalse(self.gate(query, match_mode="partial_terms", hits=0)[0])

    def test_weak_or_short(self):
        self.assertTrue(self.gate("how do I mend my automobile", match_mode="partial_terms")[0])
        self.assertTrue(self.gate("how do I mend my automobile", hits=2)[0])
        self.assertFalse(self.gate("how do I mend my automobile")[0])            # strong text search
        self.assertFalse(self.gate("how do I mend my automobile", best=3, concepts=5)[0])   # 60 % covered = strong enough
        self.assertTrue(self.gate("how do I mend my automobile", best=2, concepts=4)[0])    # 50 % is weak (default 0.6)
        self.assertTrue(self.gate("how do I mend my automobile", best=1, concepts=4)[0])
        self.assertFalse(self.gate("automobile", match_mode="partial_terms")[0])  # short
        self.assertTrue(self.gate("automobile", mode="on")[0])
        self.assertFalse(self.gate("how do I mend my automobile", mode="off", match_mode="partial_terms")[0])

    def test_backend_off_by_default(self):
        self.assertEqual(DEFAULTS["embedding"]["backend"], "none")
        self.store.cfg = {**self.store.cfg, "embedding": dict(DEFAULTS["embedding"])}
        use, reason = self.gate("how do I mend my automobile", match_mode="partial_terms")
        self.assertFalse(use)
        self.assertIn("off", reason)


class SearchTests(VectorCase):
    def test_paraphrase_found_by_model_only_when_needed(self):
        vectors.refresh(self.store)
        plain = engine.search(self.store, "how do I mend my automobile", 5, semantic="off")
        self.assertNotIn("kb/demo/garage.md", [r["path"] for r in plain["results"]])
        auto = engine.search(self.store, "how do I mend my automobile", 5)
        self.assertTrue(auto["semantic"]["used"], auto["semantic"])
        self.assertEqual(auto["results"][0]["path"], "kb/demo/garage.md")
        exact = engine.search(self.store, "Error E-1001", 5)
        self.assertFalse(exact["semantic"]["used"])
        self.assertEqual(exact["results"][0]["heading"], "Error E-1001")

    def test_any_problem_falls_back_to_text(self):
        # no vectors yet
        result = engine.search(self.store, "how do I mend my automobile", 5, semantic="on")
        self.assertEqual((result["semantic"]["used"], result["semantic"]["state"]), (False, "unavailable"))
        # broken model hash
        vectors.refresh(self.store)
        self.write_record(model_hash="1" * 64)
        result = engine.search(self.store, "how do I mend my automobile", 5, semantic="on")
        self.assertEqual(result["semantic"]["state"], "unavailable")
        # real backend without onnx files / runtime -> still a text result
        self.store.cfg = {**self.store.cfg, "embedding": {**self.cfg["embedding"], "backend": "onnx-local"}}
        result = engine.search(self.store, "how do I mend my automobile", 5, semantic="on")
        self.assertEqual(result["semantic"]["state"], "unavailable")
        self.assertIn("results", result)

    def test_project_filter_applies_to_model_hits(self):
        (self.root / "kb/other/car.md").parent.mkdir(parents=True)
        (self.root / "kb/other/car.md").write_text("# Other\n## Fix car\nFix the car engine elsewhere.\n", encoding="utf-8")
        self.store.hash_cache.clear()
        engine.update(self.store)
        vectors.refresh(self.store)
        result = engine.search(self.store, "how do I mend my automobile", 5, project="demo", semantic="on")
        self.assertTrue(all(r["path"].startswith("kb/demo/") for r in result["results"]))

    def test_status_and_cli(self):
        self.assertEqual(engine.status(self.store)["embedding"]["backend"], "mock")
        cfg = {**self.cfg, "embedding": dict(DEFAULTS["embedding"])}
        (self.root / ".qkb/config.json").write_text(json.dumps(cfg), encoding="utf-8")

        def run(*args):
            proc = subprocess.run([sys.executable, "-s", str(SKILL / "scripts/qkb.py"), "--root", str(self.root), *args, "--format", "json"],
                                  text=True, encoding="utf-8", capture_output=True, timeout=60)
            return proc.returncode, json.loads(proc.stdout)
        code, data = run("search", "how do I mend my automobile", "--semantic", "auto")
        self.assertEqual(code, 0, data)
        self.assertFalse(data["semantic"]["used"])
        code, data = run("embed")
        self.assertEqual(code, 2)                                  # backend none -> clear error, nothing written
        code, data = run("status", "--quick")
        self.assertEqual(data["embedding"]["backend"], "none")

    def test_invalid_embedding_config(self):
        for bad in ({"backend": "cloud"}, {"mode": "always"}, {"weight": "x"}, {"min_words": 0}, {"other": 1},
                    {"min_coverage": 2}):
            with self.subTest(bad=bad):
                cfg = {**self.cfg, "embedding": {**DEFAULTS["embedding"], **bad}}
                (self.root / ".qkb/config.json").write_text(json.dumps(cfg), encoding="utf-8")
                with self.assertRaises(QError):
                    load_config(self.root)


if __name__ == "__main__":
    unittest.main()
