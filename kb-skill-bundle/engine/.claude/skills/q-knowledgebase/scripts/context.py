"""Context helpers: merge duplicate sections in results; expand one hit to its neighbours."""
from __future__ import annotations

from core import QError


def compact(results):
    """Merge results of the same file section (several chunks of one heading). The first, best-ranked
    entry keeps its place and score; its line span grows to cover the merged chunks; "merged" counts them.
    Entries without section_id (code symbols, files) pass unchanged."""
    out, index = [], {}
    for item in results:
        key = (item.get("path"), item.get("section_id")) if item.get("section_id") else None
        if key is None or key not in index:
            if key is not None:
                index[key] = len(out)
            out.append(dict(item))
            continue
        kept = out[index[key]]
        kept["merged"] = kept.get("merged", 1) + 1
        if kept.get("start") is not None and item.get("start") is not None:
            kept["start"] = min(kept["start"], item["start"])
            kept["end"] = max(kept["end"], item["end"])
    return out


def expand(store, id_, around=1):
    """The chunk(s) of a chunk id or section id plus up to `around` neighbouring chunks before and after in
    the same file (ordered by line). Content only for CURRENT sources, like read."""
    import engine
    rows = store.rows("SELECT * FROM sections WHERE id=? OR section_id=? ORDER BY start", (id_, id_))
    if not rows:
        raise QError("Unknown section or chunk ID; search first")
    path = rows[0]["path"]
    ordered = store.rows("SELECT * FROM sections WHERE path=? ORDER BY start, ordering", (path,))
    ids = [r["id"] for r in ordered]
    first, last = ids.index(rows[0]["id"]), ids.index(rows[-1]["id"])
    chunks = []
    for sec in ordered[max(0, first - around):last + around + 1]:
        result = engine.section_result(store, sec, 0, False)
        chunks.append({key: result[key] for key in ("id", "section_id", "path", "heading", "start", "end", "hash", "source_status")}
                      | {"content": sec["content"] if result["source_status"] == "CURRENT" else None,
                         "requested": sec["id"] in {r["id"] for r in rows}})
    return {"id": id_, "path": path, "around": around, "chunks": chunks,
            "note": "Neighbouring chunks of the same file; content omitted when the source changed (re-run update)"}
