"""Optional local model search. Off by default; the engine never needs it.

- Used ONLY when the query router needs it: a natural-language question whose text search is weak (partial match or
  fewer hits than asked). Questions with numbers, dates, codes, paths, identifiers or error codes always stay on text
  search. `--semantic off` never uses it; `--semantic on` uses it whenever it is available.
- Model: a folder `.qkb/models/<name>/` prepared by the bundle's install / download scripts, with `onnx/model.onnx`
  (or `model.onnx`), `tokenizer.json` and `MODEL.txt` (sha256 per file). Only `.onnx` and `.json` files are opened;
  both hashes must match MODEL.txt. onnxruntime runs with CPUExecutionProvider only; numpy / onnxruntime are imported
  only when the backend is used.
- Vectors live in their own file `.qkb/cache/vectors.sqlite3` (model and tokenizer hash, profile hash, dimension in its
  meta table); `qkb embed` adds / refreshes vectors of changed sections only. Removing the file or turning the backend
  off leaves the normal index untouched.
- Any problem (no model, wrong hash, runtime error, no vectors) -> the text-search result unchanged plus
  `semantic: {"used": false, "state": "unavailable", "reason": ...}`. Search never fails because of the model.
"""
from __future__ import annotations

import array
import hashlib
import json
import math
import re
import sqlite3
import time
import unicodedata
from pathlib import Path

from core import QError, digest, json_text, read_text, safe_path

BACKENDS = {}          # name -> factory(store, folder, profile) -> embedder (tests register a mock backend)
STORE = ".qkb/cache/vectors.sqlite3"
HASH_CACHE = ".qkb/cache/model-hashes.json"
PROFILE_DEFAULTS = {"query_prefix": "query: ", "passage_prefix": "passage: ", "max_tokens": 512, "pooling": "mean",
                    "normalize": True, "batch": 16}
RRF_K = 60


# ---------------------------------------------------------------- model folder

def settings(cfg):
    e = cfg["embedding"]
    return {"backend": e.get("backend", "none"), "model": e.get("model", ""), "mode": e.get("mode", "auto"),
            "weight": float(e.get("weight", 1.0)), "min_words": int(e.get("min_words", 3)),
            "min_coverage": float(e.get("min_coverage", 0.6))}


def model_folder(store):
    name = settings(store.cfg)["model"]
    if not name or "/" in name or "\\" in name or name in (".", ".."):
        raise QError("embedding.model must name a folder under .qkb/models/")
    return safe_path(store.root, ".qkb/models/" + name)


def _linked(path):
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def _check_links(folder, *paths):
    """No symlink / junction anywhere below the model folder (the folder itself: safe_path)."""
    for path in paths:
        p = path
        while p != folder and folder in p.parents:
            if _linked(p):
                raise QError("symlinks and junctions are not allowed in the model folder")
            p = p.parent


def model_files(folder):
    """(model.onnx path, tokenizer.json path); only these two file kinds are ever opened (plus MODEL.txt,
    the hash record, and the optional embedding-profile.json)."""
    model = folder / "onnx" / "model.onnx"
    if not model.is_file():
        model = folder / "model.onnx"
    tokenizer = folder / "tokenizer.json"
    if not model.is_file() or not tokenizer.is_file():
        raise QError("model files missing (onnx/model.onnx and tokenizer.json) in " + folder.name)
    for p in (model, tokenizer):
        if p.suffix.casefold() not in (".onnx", ".json"):
            raise QError("only .onnx / .json files are accepted")
    _check_links(folder, model, tokenizer)
    return model, tokenizer


def recorded_hashes(folder):
    """MODEL.txt lines '<path>  sha256 <hex>' -> {path: hex}."""
    record = folder / "MODEL.txt"
    _check_links(folder, record)
    if not record.is_file():
        raise QError("MODEL.txt missing: the model was not placed by the download script")
    out = {}
    for line in read_text(record).splitlines():
        m = re.match(r"^\s*(\S+)\s+sha256\s+([0-9a-fA-F]{64})\s*$", line)
        if m:
            out[m.group(1).replace("\\", "/")] = m.group(2).lower()
    return out


def file_sha256(store, path, full=False):
    """sha256 of a (large) file. Searches may reuse .qkb/cache/model-hashes.json (key: path, size, modification and
    change times) but never write it; full=True (qkb embed --apply) always re-hashes and records the result."""
    stat = path.stat()
    key = "%s|%d|%d|%d" % (path.as_posix(), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    cache_path = safe_path(store.root, HASH_CACHE)
    cache = {}
    if cache_path.is_file():
        try:
            cache = json.loads(read_text(cache_path))
        except (ValueError, QError):
            cache = {}
        if not isinstance(cache, dict):
            cache = {}
    if key in cache and not full:
        return cache[key]
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    cache = {k: v for k, v in cache.items() if not k.startswith(path.as_posix() + "|")}   # one entry per file
    cache[key] = h.hexdigest()
    if not full:
        return cache[key]
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache), encoding="utf-8")
    except OSError:
        pass            # read-only store: recompute next time
    return cache[key]


def verified(store, folder, full=None):
    """Model + tokenizer paths and hashes, checked against MODEL.txt. full: re-hash and record (default: store.model_full_check)."""
    full = getattr(store, "model_full_check", False) if full is None else full
    model, tokenizer = model_files(folder)
    recorded = recorded_hashes(folder)
    out = {}
    for path in (model, tokenizer):
        rel = path.relative_to(folder).as_posix()
        if rel not in recorded:
            raise QError("MODEL.txt has no sha256 for " + rel)
        actual = file_sha256(store, path, full)
        if actual != recorded[rel]:
            raise QError("sha256 of " + rel + " does not match MODEL.txt")
        out[rel] = actual
    return model, tokenizer, out


def profile(folder, cfg):
    """Model profile: defaults < embedding-profile.json beside the model (optional)."""
    prof = dict(PROFILE_DEFAULTS)
    path = folder / "embedding-profile.json"
    _check_links(folder, path)
    if path.is_file():
        data = json.loads(read_text(path))
        if isinstance(data, dict):
            prof.update({k: v for k, v in data.items() if k in PROFILE_DEFAULTS})
    return prof


# ---------------------------------------------------------------- tokenizer (pure Python, Unigram)

class UnigramTokenizer:
    """SentencePiece Unigram segmentation from tokenizer.json: NFKC, "▁" before each word,
    Viterbi on piece scores, <unk> for unknown characters, <s> ... </s>."""

    def __init__(self, data):
        model = data.get("model", {})
        if model.get("type") != "Unigram":
            raise QError("tokenizer type %r not supported (Unigram only)" % model.get("type"))
        vocab = model["vocab"]
        self.pieces = {p: (i, float(score)) for i, (p, score) in enumerate(vocab)}
        self.max_len = max(len(p) for p in self.pieces)
        self.unk = model.get("unk_id", self.pieces.get("<unk>", (3, 0))[0])
        self.bos = self.pieces.get("<s>", (0, 0))[0]
        self.eos = self.pieces.get("</s>", (2, 0))[0]
        self.min_score = min(s for _, s in self.pieces.values()) - 10.0
        self.cache = {}
        self.unknown = 0
        self.total = 0

    @classmethod
    def from_file(cls, path):
        return cls(json.loads(read_text(path)))

    def _word(self, word):
        if word in self.cache:
            return self.cache[word]
        n = len(word)
        best = [(-math.inf, None)] * (n + 1)
        best[0] = (0.0, None)
        for i in range(1, n + 1):
            for j in range(max(0, i - self.max_len), i):
                if best[j][0] == -math.inf:
                    continue
                piece = word[j:i]
                hit = self.pieces.get(piece)
                if hit is not None:
                    score = best[j][0] + hit[1]
                    if score > best[i][0]:
                        best[i] = (score, (j, hit[0]))
            if best[i][0] == -math.inf:          # unknown character: one <unk>
                best[i] = (best[i - 1][0] + self.min_score, (i - 1, self.unk))
        ids, i = [], n
        while i > 0:
            j, piece_id = best[i][1]
            ids.append(piece_id)
            i = j
        ids.reverse()
        self.cache[word] = ids
        return ids

    def encode(self, text, max_tokens):
        text = unicodedata.normalize("NFKC", text)
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Cc" or ch in "\t\n ")
        ids = []
        for word in text.split():
            ids += self._word("▁" + word)
        self.total += len(ids)
        self.unknown += sum(1 for t in ids if t == self.unk)
        return [self.bos] + ids[:max(1, max_tokens - 2)] + [self.eos]


# ---------------------------------------------------------------- ONNX embedder

class OnnxEmbedder:
    def __init__(self, store, folder, prof):
        model, tokenizer, hashes = verified(store, folder)
        import onnxruntime   # only here: the engine itself needs no third-party package
        import numpy
        self.np = numpy
        options = onnxruntime.SessionOptions()
        options.log_severity_level = 3
        if hasattr(onnxruntime, "disable_telemetry_events"):
            onnxruntime.disable_telemetry_events()
        self.session = onnxruntime.InferenceSession(str(model), sess_options=options, providers=["CPUExecutionProvider"])
        self.inputs = [i.name for i in self.session.get_inputs()]
        self.tokenizer = UnigramTokenizer.from_file(tokenizer)
        self.profile = prof
        self.identity = {"model_sha256": hashes[model.relative_to(folder).as_posix()],
                         "tokenizer_sha256": hashes["tokenizer.json"]}

    def embed(self, texts, kind):
        np = self.np
        prefix = self.profile["query_prefix"] if kind == "query" else self.profile["passage_prefix"]
        encoded = [self.tokenizer.encode(prefix + t, int(self.profile["max_tokens"])) for t in texts]
        order = sorted(range(len(encoded)), key=lambda i: len(encoded[i]))     # similar lengths per batch
        size = int(self.profile["batch"])
        out = [None] * len(encoded)
        for start in range(0, len(order), size):
            index = order[start:start + size]
            batch = [encoded[i] for i in index]
            width = max(len(b) for b in batch)
            ids = np.zeros((len(batch), width), dtype=np.int64)
            mask = np.zeros((len(batch), width), dtype=np.int64)
            for r, b in enumerate(batch):
                ids[r, :len(b)] = b
                mask[r, :len(b)] = 1
            feed = {}
            for name in self.inputs:
                if "mask" in name:
                    feed[name] = mask
                elif "type" in name:
                    feed[name] = np.zeros_like(ids)
                else:
                    feed[name] = ids
            hidden = self.session.run(None, feed)[0]
            if hidden.ndim == 3:     # last_hidden_state -> mean over the mask
                summed = (hidden * mask[:, :, None]).sum(axis=1)
                hidden = summed / np.maximum(mask.sum(axis=1, keepdims=True), 1)
            if self.profile["normalize"]:
                hidden = hidden / np.maximum(np.linalg.norm(hidden, axis=1, keepdims=True), 1e-12)
            for i, row in zip(index, hidden):
                out[i] = array.array("f", row.astype("float32").tolist())
        return out


BACKENDS["onnx-local"] = lambda store, folder, prof: OnnxEmbedder(store, folder, prof)


def embedder(store, full_check=False):
    """full_check (qkb embed --apply): model files re-hashed against MODEL.txt, not taken from the hash cache."""
    s = settings(store.cfg)
    if s["backend"] == "none":
        raise QError("embedding backend is off")
    if s["backend"] not in BACKENDS:
        raise QError("unknown embedding backend " + s["backend"])
    folder = model_folder(store)
    prof = profile(folder, store.cfg)
    try:
        stamps = tuple((p.stat().st_size, p.stat().st_mtime_ns) for p in (*model_files(folder), folder / "MODEL.txt"))
    except OSError:
        stamps = None
    key = (s["backend"], str(folder), digest(json_text(prof)), stamps)   # a changed model file means a new load + check
    cached = getattr(store, "model_cache", None)
    if not full_check and cached and cached[0] == key:
        return cached[1]
    store.model_full_check = full_check
    try:
        model = BACKENDS[s["backend"]](store, folder, prof)
    finally:
        store.model_full_check = False
    model.profile_hash = digest(json_text(prof))
    store.model_cache = (key, model)
    return model


# ---------------------------------------------------------------- vector store

def _open(store, readonly):
    path = safe_path(store.root, STORE)
    if readonly:
        if not path.is_file():
            raise QError("no vectors yet: run qkb embed")
        from core import connect_readonly
        return connect_readonly(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS vec(id TEXT PRIMARY KEY, content_hash TEXT, vector BLOB)")
    return db


def _identity(model):
    return {**model.identity, "profile_hash": model.profile_hash}


def refresh(store, dry_run=False):
    """qkb embed: vectors for sections whose content changed; everything again when model / profile changed."""
    started = time.perf_counter()
    model = embedder(store, full_check=not dry_run)
    sections = store.rows("SELECT id, heading, hierarchy, content FROM sections")
    wanted = {s["id"]: digest(s["content"]) for s in sections}
    if dry_run and not safe_path(store.root, STORE).is_file():
        return {"sections": len(sections), "to_embed": len(sections), "removed": 0, "kept": 0, "model_changed": False,
                "dry_run": True}
    db = _open(store, dry_run)      # a dry run only reads
    try:
        meta = {r["key"]: r["value"] for r in db.execute("SELECT key, value FROM meta")}
        identity = _identity(model)
        same_model = all(meta.get(k) == v for k, v in identity.items())
        have = {r["id"]: r["content_hash"] for r in db.execute("SELECT id, content_hash FROM vec")} if same_model else {}
        todo = [s for s in sections if have.get(s["id"]) != wanted[s["id"]]]
        removed = [i for i in have if i not in wanted]
        result = {"sections": len(sections), "to_embed": len(todo), "removed": len(removed), "kept": len(sections) - len(todo),
                  "model_changed": not same_model and bool(meta), "dry_run": dry_run}
        if dry_run:
            return result
        with db:
            if not same_model:
                db.execute("DELETE FROM vec")
            for i in removed:
                db.execute("DELETE FROM vec WHERE id=?", (i,))
            texts = [" / ".join(json.loads(s["hierarchy"])) + "\n" + s["content"] for s in todo]
            vectors = model.embed(texts, "passage") if texts else []
            for s, v in zip(todo, vectors):
                db.execute("INSERT OR REPLACE INTO vec VALUES (?,?,?)", (s["id"], wanted[s["id"]], v.tobytes()))
            for k, v in {**identity, "dim": str(len(vectors[0]) if vectors else meta.get("dim", "")), "updated": time.strftime("%Y-%m-%d %H:%M")}.items():
                db.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (k, str(v)))
        result["seconds"] = round(time.perf_counter() - started, 3)
        tok = getattr(model, "tokenizer", None)
        if tok is not None and tok.total:
            result["unk_rate"] = round(tok.unknown / tok.total, 5)
        return result
    finally:
        db.close()


def _cosines(q, rows):
    """[(id, dot product)]; numpy when importable (6 ms instead of 55 ms for about 1,500 vectors), else pure Python."""
    try:
        import numpy
    except ImportError:
        numpy = None
    if numpy is not None and rows and all(len(r["vector"]) == 4 * len(q) for r in rows):
        matrix = numpy.frombuffer(b"".join(r["vector"] for r in rows), dtype=numpy.float32).reshape(len(rows), len(q))
        values = matrix @ numpy.asarray(q, dtype=numpy.float32)
        return [(r["id"], float(v)) for r, v in zip(rows, values)]
    scored = []
    for row in rows:
        v = array.array("f")
        v.frombytes(row["vector"])
        scored.append((row["id"], sum(a * b for a, b in zip(q, v))))
    return scored


def nearest(store, model, query, top):
    """[(section id, cosine)] best first."""
    db = _open(store, True)
    try:
        meta = {r["key"]: r["value"] for r in db.execute("SELECT key, value FROM meta")}
        if any(meta.get(k) != v for k, v in _identity(model).items()):
            raise QError("vectors were made with another model or profile: run qkb embed")
        q = model.embed([query], "query")[0]
        rows = db.execute("SELECT id, vector FROM vec").fetchall()
        scored = _cosines(q, rows)
    finally:
        db.close()
    scored.sort(key=lambda x: -x[1])
    return scored[:top]


def status(store):
    """Cheap view for status: no model load."""
    s = settings(store.cfg)
    out = {"backend": s["backend"], "model": s["model"] or None, "mode": s["mode"]}
    path = safe_path(store.root, STORE)
    if path.is_file():
        try:
            from core import connect_readonly
            db = connect_readonly(path)
            try:
                out["vectors"] = db.execute("SELECT count(*) FROM vec").fetchone()[0]
            finally:
                db.close()
        except sqlite3.Error:
            out["vectors"] = None
    else:
        out["vectors"] = 0
    return out


# ---------------------------------------------------------------- router gate and fusion

EXACT = re.compile(r"[/\\]|::|\w+\.\w{1,5}\b|\b[A-Z]{2,}[-_]?\d|\b\w*\d\w*\b|\b[a-z]+[A-Z]\w*|\b[A-Z][a-z0-9]+[A-Z]\w*|\b[A-Za-z]+_[A-Za-z_]+\b")


def gate(store, query, result, top, mode):
    """(use, reason). Never for exact terms (numbers, dates, codes, paths, identifiers, error codes)."""
    s = settings(store.cfg)
    mode = mode or s["mode"]
    if s["backend"] == "none":
        return False, "model search off (embedding.backend none)"
    if mode == "off":
        return False, "--semantic off"
    if mode == "on":
        return True, "--semantic on"
    if EXACT.search(query):
        return False, "exact terms (number / code / path / identifier) stay on text search"
    words = re.findall(r"[^\W\d_]{2,}", query)
    if len(words) < s["min_words"]:
        return False, "short query: text search"
    sections = [r for r in result.get("results", []) if r.get("section_id")]
    if len(sections) < top:
        return True, "weak text match (%d of %d hits)" % (len(sections), top)
    cov = result.get("coverage") or {}
    best, concepts = cov.get("best", 0), cov.get("concepts", 0)
    if concepts and best / concepts < s["min_coverage"]:
        return True, "weak text match (best section covers %d of %d concepts)" % (best, concepts)
    return False, "text search strong enough"


def apply(store, query, result, top, project, mode, present):
    """Fuse model results into a text-search result when the gate says so; never raises."""
    use, reason = gate(store, query, result, top, mode)
    if not use:
        result["semantic"] = {"used": False, "reason": reason}
        return result
    try:
        model = embedder(store)
        hits = nearest(store, model, query, max(50, top * 10))
        if project is not None:
            paths = {r["id"]: r["path"] for r in store.rows("SELECT id, path FROM sections WHERE id IN (%s)" % ",".join("?" * len(hits)), [h[0] for h in hits])} if hits else {}
            hits = [h for h in hits if h[0] in paths and store.scope.in_project(paths[h[0]], project)]
        weight = settings(store.cfg)["weight"]
        fused, items = {}, {}
        sections = [r for r in result.get("results", []) if r.get("section_id")]
        for rank, r in enumerate(sections):
            fused[r["id"]] = fused.get(r["id"], 0) + 1.0 / (RRF_K + rank + 1)
            items[r["id"]] = r
        for rank, (i, _) in enumerate(hits):
            fused[i] = fused.get(i, 0) + weight / (RRF_K + rank + 1)
        order = sorted(fused, key=lambda i: -fused[i])[:top]
        merged = []
        for i in order:
            if i not in items:
                row = store.rows("SELECT * FROM sections WHERE id=?", (i,))
                if not row:
                    continue
                items[i] = present(row[0])
            merged.append(items[i])
        others = [r for r in result.get("results", []) if not r.get("section_id")]
        result["results"] = (merged + others)[:top]
        result["semantic"] = {"used": True, "reason": reason, "model_hits": len(hits)}
    except Exception as exc:   # any model / runtime / store problem: keep the text-search result
        result["semantic"] = {"used": False, "state": "unavailable", "reason": "%s: %s" % (type(exc).__name__, str(exc)[:200])}
    return result
