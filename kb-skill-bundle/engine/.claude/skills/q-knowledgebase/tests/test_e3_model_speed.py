"""2.1.0-e3 (real-model measurement): default min_coverage 0.6, batches in length order with results in
input order, one model load per process, numpy dot products with a pure-Python fallback."""
import array
import builtins
import unittest
from unittest import mock

import support  # noqa: F401  (puts scripts/ on sys.path)
from core import DEFAULTS
import vectors
from test_e_vectors import MockEmbedder, VectorCase

try:
    import numpy
except ImportError:      # the engine runs without numpy; only the batching test needs it
    numpy = None


class FakeTokenizer:
    def encode(self, text, max_tokens):
        return [0] + [len(w) for w in text.split()][:max_tokens - 2] + [2]


class FakeSession:
    def __init__(self):
        self.widths = []

    def run(self, _, feed):
        ids = feed["input_ids"]
        self.widths.append(ids.shape[1])
        return [numpy.repeat(ids[:, :, None].astype("float32"), 2, axis=2)]


@unittest.skipIf(numpy is None, "numpy not installed")
class BatchOrderTests(unittest.TestCase):
    def test_length_order_and_input_order(self):
        e = object.__new__(vectors.OnnxEmbedder)
        e.np, e.session, e.tokenizer = numpy, FakeSession(), FakeTokenizer()
        e.inputs = ["input_ids", "attention_mask"]
        e.profile = {**vectors.PROFILE_DEFAULTS, "batch": 2, "normalize": False, "passage_prefix": ""}
        texts = ["a " * 9, "bb", "c " * 5, "dd ee", "f " * 9]
        out = e.embed(texts, "passage")
        for text, vec in zip(texts, out):                   # mean over the mask of [0, len(word)..., 2]
            ids = FakeTokenizer().encode(text, 512)
            self.assertAlmostEqual(vec[0], sum(ids) / len(ids), places=5)
        self.assertEqual(e.session.widths, [4, 11, 11])     # input order would give [11, 7, 11]


class DefaultsTests(unittest.TestCase):
    def test_min_coverage_default(self):
        self.assertEqual(DEFAULTS["embedding"]["min_coverage"], 0.6)
        self.assertEqual(vectors.settings({"embedding": {}})["min_coverage"], 0.6)


class CosineTests(unittest.TestCase):
    def rows(self):
        return [{"id": "a", "vector": array.array("f", [1, 0, 0]).tobytes()},
                {"id": "b", "vector": array.array("f", [0.5, 0.5, 0]).tobytes()}]

    def test_same_with_and_without_numpy(self):
        q = array.array("f", [1, 0.5, 0])
        fast = vectors._cosines(q, self.rows())
        real_import = builtins.__import__

        def no_numpy(name, *args, **kwargs):
            if name == "numpy":
                raise ImportError(name)
            return real_import(name, *args, **kwargs)
        with mock.patch.object(builtins, "__import__", no_numpy):
            slow = vectors._cosines(q, self.rows())
        self.assertEqual([i for i, _ in fast], ["a", "b"])
        for (_, x), (_, y) in zip(fast, slow):
            self.assertAlmostEqual(x, y, places=5)
        self.assertAlmostEqual(dict(slow)["b"], 0.75, places=5)


class ModelCacheTests(VectorCase):
    def test_one_load_per_process(self):
        with mock.patch.object(MockEmbedder, "__init__", autospec=True, side_effect=MockEmbedder.__init__) as init:
            first = vectors.embedder(self.store)
            self.assertIs(vectors.embedder(self.store), first)
            self.assertEqual(init.call_count, 1)
            self.assertIsNot(vectors.embedder(self.store, full_check=True), first)   # embed --apply: fresh load + full hash
            self.assertEqual(init.call_count, 2)

    def test_changed_model_file_reloads_and_rechecks(self):
        vectors.embedder(self.store)
        (self.model / "onnx/model.onnx").write_bytes(b"replaced after the first load")
        with self.assertRaises(Exception):
            vectors.embedder(self.store)                   # new stamp -> new load -> sha256 no longer matches MODEL.txt


if __name__ == "__main__":
    unittest.main()
