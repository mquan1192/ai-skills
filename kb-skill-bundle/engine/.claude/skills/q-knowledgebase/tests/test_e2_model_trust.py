"""2.1.0-e2: model hash cache only helps searches; qkb embed --apply always re-hashes;
a read-only search never writes the cache; no symlink / junction below the model folder."""
import json
import unittest
from pathlib import Path
from unittest import mock

import support  # noqa: F401  (puts scripts/ on sys.path)
from core import QError
import engine
import vectors
from test_e_vectors import VectorCase

CACHE = ".qkb/cache/model-hashes.json"


class HashCacheTests(VectorCase):
    def cache(self):
        path = self.root / CACHE
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def test_search_never_writes_cache(self):
        (self.root / CACHE).unlink(missing_ok=True)
        vectors.verified(self.store, self.model)
        engine.search(self.store, "how do I repair my automobile today", 3, None, "on")
        self.assertIsNone(self.cache())

    def test_apply_rehashes_and_records(self):
        vectors.refresh(self.store)
        cache = self.cache()
        self.assertEqual(len(cache), 2)                                   # one entry per model file
        poisoned = {k: "0" * 64 for k in cache}                          # cache says something else
        (self.root / CACHE).write_text(json.dumps(poisoned), encoding="utf-8")
        with self.assertRaises(QError):                                   # a search trusts the cache entry ...
            vectors.verified(self.store, self.model)
        vectors.refresh(self.store)                                       # ... embed --apply re-hashes and repairs it
        self.assertNotIn("0" * 64, self.cache().values())
        vectors.verified(self.store, self.model)

    def test_apply_detects_changed_model(self):
        vectors.refresh(self.store)
        (self.model / "onnx/model.onnx").write_bytes(b"other bytes, same story")
        with self.assertRaises(QError):
            vectors.refresh(self.store)

    def test_dry_run_uses_no_full_hash(self):
        with mock.patch.object(vectors, "file_sha256", wraps=vectors.file_sha256) as spy:
            vectors.refresh(self.store, dry_run=True)
        self.assertTrue(spy.call_args_list)
        self.assertTrue(all(call.args[2] is False for call in spy.call_args_list))
        self.assertFalse(getattr(self.store, "model_full_check", False))


class LinkTests(VectorCase):
    def linked(self, name):
        original = Path.is_symlink
        return mock.patch.object(Path, "is_symlink", lambda p: p.name == name or original(p))

    def test_linked_subfolder_refused(self):
        with self.linked("onnx"), self.assertRaises(QError):
            vectors.model_files(self.model)

    def test_linked_files_refused(self):
        for name in ("tokenizer.json", "MODEL.txt", "embedding-profile.json"):
            with self.subTest(name=name), self.linked(name), self.assertRaises(QError):
                vectors.verified(self.store, self.model)
                vectors.profile(self.model, self.store.cfg)

    def test_linked_model_folder_refused(self):
        with self.linked("mock-model"), self.assertRaises(QError):
            vectors.model_folder(self.store)

    def test_link_falls_back_to_text_search(self):
        with self.linked("onnx"):
            res = engine.search(self.store, "how do I repair my automobile today", 3, None, "on")
        self.assertFalse(res["semantic"]["used"])
        self.assertEqual(res["semantic"]["state"], "unavailable")


if __name__ == "__main__":
    unittest.main()
