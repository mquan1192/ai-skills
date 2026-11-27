"""Read-only reports on the index store, used by `verify --links` and `status`.

Each function returns a JSON-ready dict; item lists are capped by `top`.
Relies only on: files(category, metadata), nodes(type, label, metadata), edges(relation),
refs(relation, path, start, written, target_path, anchor, resolution, evidence) and
code_spans(ref_id, source_path, target_path, start, end, target_hash)."""
import collections
import json

from codelinks import is_code_path, line_state

LANGUAGES = ("python", "cpp", "javascript", "typescript", "other")
COVERAGE = ("FULL", "PARTIAL", "FILE_ONLY")


def _meta(text):
    try:
        value = json.loads(text or "{}")
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _has_table(store, name):
    return bool(store.rows("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)))


def _written_path(written):
    """Path part of a written reference: drop '#anchor' and ':line' tails."""
    w = (written or "").split("#", 1)[0]
    head, sep, tail = w.rpartition(":")
    if sep and tail.replace("-", "").replace(",", "").replace(" ", "").isdigit():
        w = head
    return w


def parser_coverage(store):
    languages = {}
    for row in store.rows("SELECT metadata FROM files WHERE category='code'"):
        meta = _meta(row["metadata"])
        lang = meta.get("language") or "other"
        entry = languages.setdefault(lang, {"files": 0, "FULL": 0, "PARTIAL": 0, "FILE_ONLY": 0})
        entry["files"] += 1
        cov = meta.get("coverage")
        if cov in COVERAGE:
            entry[cov] += 1
    symbols = store.rows("SELECT COUNT(*) AS n FROM nodes WHERE type='CODE_SYMBOL'")[0]["n"]
    return {"languages": dict(sorted(languages.items())), "symbols": symbols}


def code_link_report(store, top=30):
    """KB -> code references (REFERENCES to a code file) and the state of their line spans."""
    code_files = {r["path"] for r in store.rows("SELECT path FROM files WHERE category='code'")}
    refs = [r for r in store.rows(
        "SELECT id, path, start, written, target_path, anchor, resolution FROM refs "
        "WHERE relation='REFERENCES' ORDER BY path, start")
        if (r["target_path"] in code_files) or is_code_path(_written_path(r["written"]))]
    by_resolution = collections.Counter(r["resolution"] or "same_file" for r in refs)
    # Line spans are stored as anchor "L<start>[-<end>]"; anchor "L" = code reference without a line.
    with_lines = [r for r in refs if (r["anchor"] or "").startswith("L") and r["anchor"][1:2].isdigit()]
    spans = {}
    if _has_table(store, "code_spans"):
        for s in store.rows("SELECT ref_id, target_path, start, end, target_hash FROM code_spans"):
            spans[s["ref_id"]] = s
    counts = collections.Counter()
    items = []
    cache = {}
    for r in with_lines:
        span = spans.get(r["id"])
        if span is None:
            state = "UNRESOLVED"
        else:
            target = span["target_path"]
            if target not in cache:
                try:
                    text, hash_, _ = store.scope.read(target)
                    cache[target] = (len(text.splitlines()), hash_)
                except Exception:
                    cache[target] = None
            current = cache[target]
            if current is None:
                state = "MISSING"
            elif line_state(current[0], span["start"], span["end"]) != "OK":
                state = "LINE_OUT_OF_RANGE"
            elif current[1] != span["target_hash"]:
                state = "STALE"
            else:
                state = "CURRENT"
        counts[state] += 1
        if state != "CURRENT":
            items.append({"path": r["path"], "line": r["start"], "written": r["written"], "state": state})
    return {"total": len(refs), "by_resolution": dict(sorted(by_resolution.items())),
            "with_lines": len(with_lines), "lines_current": counts["CURRENT"],
            "lines_stale": counts["STALE"], "lines_out_of_range": counts["LINE_OUT_OF_RANGE"],
            "missing": counts["MISSING"], "lines_unresolved": counts["UNRESOLVED"],
            "items": items[:top], "items_total": len(items)}


def include_report(store, top=30):
    """C++ #include sites (one site = one directive; the index keeps one row per candidate path).
    resolved = an IMPORTS edge exists for that file and line (candidates always have a target_path)."""
    sites = collections.OrderedDict()
    for r in store.rows("SELECT path, start, written, evidence FROM refs WHERE relation='IMPORTS' ORDER BY path, start"):
        if (r["evidence"] or "").lstrip().startswith("#include"):
            sites.setdefault((r["path"], r["start"]), r)
    linked = {(e["path"], e["start"]) for e in store.rows("SELECT path, start FROM edges WHERE relation='IMPORTS'")}
    unresolved = [r for key, r in sites.items() if key not in linked]
    return {"sites": len(sites), "resolved": len(sites) - len(unresolved), "unresolved": len(unresolved),
            "unresolved_items": [{"path": r["path"], "line": r["start"], "written": r["written"]}
                                 for r in unresolved[:top]]}


def issue_report(store, top=30):
    """Issue IDs: defined nodes, AFFECTS / MENTIONS edges, IDs mentioned but never defined."""
    nodes = store.rows("SELECT label, metadata FROM nodes WHERE type='ISSUE'")
    others = store.rows("SELECT label, metadata FROM nodes WHERE type='IDENTIFIER'")
    defined = {n["label"] for n in nodes} | {n["label"] for n in others}
    by_status = collections.Counter(_meta(n["metadata"]).get("status") or "UNKNOWN" for n in nodes)
    edges = collections.Counter(r["relation"] for r in store.rows(
        "SELECT relation FROM edges WHERE relation IN ('AFFECTS','MENTIONS')"))
    undefined = collections.OrderedDict()
    for r in store.rows("SELECT path, start, written FROM refs WHERE relation='MENTIONS' ORDER BY path, start"):
        key = r["written"]
        if not key or key in defined:
            continue
        entry = undefined.setdefault(key, {"id": key, "mentions": 0, "path": r["path"], "line": r["start"]})
        entry["mentions"] += 1
    items = list(undefined.values())
    by_kind = collections.Counter(_meta(n["metadata"]).get("kind") or "id" for n in others)
    return {"issues": len(nodes), "other_ids": dict(sorted(by_kind.items())), "by_status": dict(sorted(by_status.items())),
            "affects": edges["AFFECTS"], "mentions": edges["MENTIONS"],
            "undefined_ids": {"count": len(items), "items": items[:top]}}
