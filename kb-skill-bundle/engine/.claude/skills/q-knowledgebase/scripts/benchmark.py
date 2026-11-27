"""Labeled retrieval measurements. No model judge and no claims of QA accuracy."""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import statistics
import time

from core import QError, fold, read_text, safe_path
from engine import search, status


def percentile(values, q):
    """Nearest-rank percentile (q in 0..100) of a nonempty list; stable for small samples."""
    ordered = sorted(values)
    k = max(1, min(len(ordered), -(-len(ordered) * q // 100)))
    return ordered[int(k) - 1]


def run(store, question_file):
    # Explicit benchmark input, not an implicit repository-wide data scan.
    normalized = str(question_file).replace("\\", "/")
    if not normalized.endswith(".json") or any(p.casefold() in {"secrets", "credentials", "keys", ".ssh", ".aws"} or p.casefold().startswith(".env") for p in normalized.split("/")):
        raise QError("Benchmark input must be an explicitly selected nonsensitive repository JSON file")
    questions = json.loads(read_text(safe_path(store.root, normalized)))
    if not isinstance(questions, list) or not questions or len(questions) > 1000:
        raise QError("Benchmark requires 1..1000 labeled questions")
    if status(store)["state"] != "CURRENT":
        raise QError("Update the index before benchmarking")
    sections = store.rows("SELECT * FROM sections ORDER BY path,start")
    from qkb import emit
    rows, latencies, outputs, tokens, baseline_latencies = [], [], [], [], []
    recalls, precisions, baseline_recalls, baseline_precisions, trace = [], [], [], [], []
    precision5, categories = [], {}
    for q in questions:
        if not isinstance(q, dict) or not isinstance(q.get("query"), str) or not q.get("relevant"):
            raise QError("Each question needs query and nonempty relevant [{path,heading}] labels")
        for expected in q["relevant"]:
            if not isinstance(expected, dict) or not isinstance(expected.get("path"), str) or not isinstance(expected.get("heading"), str):
                raise QError("Each relevance label requires path and heading strings")
            if not any(s["path"] == expected["path"] and s["heading"] == expected["heading"] for s in sections):
                raise QError("A golden relevance label does not exist in the current index")
        start = time.perf_counter()
        result = search(store, q["query"], 5)
        latencies.append((time.perf_counter()-start)*1000)
        args = argparse.Namespace(max_chars=store.cfg["query_max_chars"], max_tokens=None, format="json")
        out = io.StringIO()
        with contextlib.redirect_stdout(out): emit(result, args, store.cfg)
        rendered = out.getvalue()
        outputs.append(len(rendered)); tokens.append(len(rendered.encode("utf-8")))
        delivered = json.loads(rendered).get("results", [])

        def measures(hits):
            expected = {(e["path"], e["heading"]) for e in q["relevant"]}
            actual = [(r["path"], r.get("heading", "")) for r in hits]
            return len(expected.intersection(actual))/len(expected), sum(p in expected for p in actual)/len(actual) if actual else 0

        recall, precision = measures(delivered)
        recalls.append(recall); precisions.append(precision)
        expected_set = {(e["path"], e["heading"]) for e in q["relevant"]}
        p5 = sum((r["path"], r.get("heading", "")) in expected_set for r in delivered[:5]) / 5
        precision5.append(p5)
        category = q.get("category", q.get("kind"))   # "kind" = older field name
        if category is not None:
            if not isinstance(category, str):
                raise QError("Optional question category must be a string")
            categories.setdefault(category, []).append((recall, p5))
        start = time.perf_counter()
        terms = fold(q["query"]).split()
        # Simple text baseline: literal normalized term counts, no heading/path/graph boost.
        baseline = sorted([(sum(s["normalized"].count(t) for t in terms), s) for s in sections],
                          key=lambda item: (-item[0], item[1]["path"], item[1]["start"]))
        baseline_hits = [s for count, s in baseline[:5] if count]
        baseline_latencies.append((time.perf_counter()-start)*1000)
        br, bp = measures(baseline_hits)
        baseline_recalls.append(br); baseline_precisions.append(bp)
        traced = 0
        for hit in delivered:
            if hit.get("source_status") != "CURRENT" or not hit.get("start"):
                continue
            _, hash_, _ = store.scope.read(hit["path"])
            if hash_ == hit.get("hash"):
                traced += 1
        trace.append(traced/len(delivered) if delivered else 0)
        rows.append({"query": q["query"], "recall_at_5": recall, "precision": precision, "precision_at_5": p5,
                     "baseline_recall_at_5": br, "output_chars": len(rendered), "search_ms": round(latencies[-1], 3),
                     **({"category": category} if category is not None else {})})
    corpus_bytes = store.db.execute("SELECT coalesce(sum(bytes),0) FROM files").fetchone()[0]
    corpus_chars = sum(len(store.scope.read(f["path"])[0]) for f in store.rows("SELECT path FROM files"))
    counts = {table: store.db.execute("SELECT count(*) FROM "+table).fetchone()[0] for table in ("files", "sections", "nodes", "edges")}
    report = {"dataset": normalized, "questions": len(questions), "corpus_bytes": corpus_bytes, "corpus_chars": corpus_chars,
              **counts, "index_bytes": store.path.stat().st_size,
              "indexed_content_bytes": sum(len(s["content"].encode("utf-8")) for s in sections),
              "recall_at_5": statistics.mean(recalls), "relevant_section_precision": statistics.mean(precisions),
              "evidence_traceability": statistics.mean(trace),
              "baseline_recall_at_5": statistics.mean(baseline_recalls), "baseline_precision": statistics.mean(baseline_precisions),
              "average_search_ms": statistics.mean(latencies), "baseline_average_search_ms": statistics.mean(baseline_latencies),
              "p50_search_ms": percentile(latencies, 50), "p95_search_ms": percentile(latencies, 95),
              "precision_at_5": statistics.mean(precision5),
              "by_category": {c: {"questions": len(v), "recall_at_5": statistics.mean(x[0] for x in v),
                                  "precision_at_5": statistics.mean(x[1] for x in v)} for c, v in sorted(categories.items())},
              "average_output_chars": statistics.mean(outputs), "average_estimated_tokens_utf8_upper": statistics.mean(tokens),
              "context_reduction_chars": 1-statistics.mean(outputs)/corpus_chars if corpus_chars else None,
              "build_seconds": float(store.getmeta("last_build_seconds") or 0),
              "last_update_seconds": float(store.getmeta("last_update_seconds") or 0),
              "results": rows,
              "scope_note": "Measured labeled local retrieval only; not answer accuracy, semantic discovery equivalence, real-project token savings or end-to-end model cost"}
    path = safe_path(store.root, ".qkb/exports/benchmark.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return {**report, "report": ".qkb/exports/benchmark.json"}
