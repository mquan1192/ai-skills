"""Human-reviewed inferred relationships. Never invokes an LLM or network API."""
from __future__ import annotations

import json

from core import QError, REL_TYPES, ident, json_text, now, read_text, safe_path


def validate(store, data):
    errors = []
    if not isinstance(data, dict):
        return {"state": "INVALID", "errors": ["Proposal must be an object"]}
    required = {"source", "target", "relation", "rationale", "evidence"}
    if set(data) != required:
        return {"state": "INVALID", "errors": ["Fields must be exactly source,target,relation,rationale,evidence"]}
    if any(not isinstance(data[k], str) or not data[k].strip() for k in ("source", "target", "relation", "rationale")):
        return {"state": "INVALID", "errors": ["Identifiers, relation and rationale must be nonempty strings"]}
    if data["relation"] not in REL_TYPES or data["relation"] == "CONTAINS":
        errors.append("Unsupported semantic relation (CONTAINS is structural only)")
    endpoints = []
    for key in ("source", "target"):
        row = store.db.execute("SELECT * FROM nodes WHERE id=?", (data[key],)).fetchone()
        if not row or row["status"] != "CONFIRMED":
            errors.append("Endpoint must be an existing confirmed node: " + key)
        else:
            endpoints.append(dict(row))
            if store.source_status(row["path"], row["hash"]) != "CURRENT":
                errors.append("Endpoint source is stale or missing: " + key)
    if data["source"] == data["target"]:
        errors.append("Semantic self-relationships are not accepted")
    evidence = data["evidence"]
    if not isinstance(evidence, list) or not evidence or len(evidence) > 16:
        return {"state": "INVALID", "errors": errors + ["Provide 1..16 exact evidence spans"]}
    covered = set()
    for ev in evidence:
        fields = {"path", "section_id", "start", "end", "quote", "hash"}
        if not isinstance(ev, dict) or set(ev) != fields:
            errors.append("Evidence fields must be exactly path,section_id,start,end,quote,hash"); continue
        if any(not isinstance(ev[k], str) for k in ("path", "quote", "hash")) or not ev["quote"]:
            errors.append("Evidence strings are invalid"); continue
        if type(ev["start"]) is not int or type(ev["end"]) is not int or ev["start"] < 1 or ev["end"] < ev["start"]:
            errors.append("Evidence line range is invalid"); continue
        if ev["section_id"] is not None and not isinstance(ev["section_id"], str):
            errors.append("section_id must be a string or null"); continue
        try:
            text, hash_, _ = store.scope.read(ev["path"])
            lines = text.splitlines()
            if hash_ != ev["hash"]:
                errors.append("Evidence hash does not match current source"); continue
            indexed = store.db.execute("SELECT hash FROM files WHERE path=?", (ev["path"],)).fetchone()
            if not indexed or indexed["hash"] != hash_:
                errors.append("Evidence is not indexed at its current hash; update first"); continue
            if ev["end"] > len(lines) or "\n".join(lines[ev["start"]-1:ev["end"]]) != ev["quote"]:
                errors.append("Evidence quote does not exactly match the specified source span"); continue
            if store.scope.category(ev["path"]) == "markdown":
                matches = store.rows("SELECT * FROM sections WHERE section_id=? AND path=?", (ev["section_id"], ev["path"]))
                if not matches or min(m["start"] for m in matches) > ev["start"] or max(m["end"] for m in matches) < ev["end"]:
                    errors.append("Evidence section and line range do not match"); continue
            covered.add(ev["path"])
        except (QError, OSError, TypeError):
            errors.append("Evidence file unavailable or outside permitted scope")
    if any(n["path"] not in covered for n in endpoints):
        errors.append("Evidence must cover the source files of both endpoints")
    return {"state": "INVALID" if errors else "VALID", "errors": errors,
            "note": "Matching evidence does not establish semantic truth; human review is required"}


def refresh(store):
    count = 0
    store.hash_cache.clear()
    for row in store.rows("SELECT * FROM proposals WHERE validation='VALID'"):
        if validate(store, json.loads(row["payload"]))["state"] != "VALID":
            store.db.execute("UPDATE proposals SET validation='STALE',updated_at=? WHERE id=?", (now(), row["id"]))
            store.db.execute("INSERT INTO reviews(proposal_id,at,action,reviewer,rationale) VALUES (?,?,?,?,?)",
                             (row["id"], now(), "INVALIDATED", "engine", "Source evidence or endpoint changed"))
            count += 1
    return count


def import_proposals(store, file):
    normalized = str(file).replace("\\", "/")
    if not normalized.startswith(".qkb/proposals/") or not normalized.endswith((".json", ".jsonl")):
        raise QError("Proposal input must be a .json/.jsonl file inside .qkb/proposals/")
    text = read_text(safe_path(store.root, normalized))
    data = [json.loads(line) for line in text.splitlines() if line.strip()] if normalized.endswith(".jsonl") else json.loads(text)
    data = data if isinstance(data, list) else [data]
    if not data or len(data) > 1000:
        raise QError("Import requires 1..1000 proposals")
    prepared = []
    for proposal in data:
        result = validate(store, proposal)
        if result["state"] != "VALID":
            raise QError("Proposal rejected: " + "; ".join(result["errors"]))
        prepared.append((ident("proposal", proposal), proposal))
    ids = []
    with store.db:
        for id_, proposal in prepared:
            store.db.execute("INSERT OR IGNORE INTO proposals VALUES (?,?,?,?,?,?,?,?)",
                             (id_, json_text(proposal), "PENDING", "VALID", None, None, now(), now()))
            ids.append(id_)
    return {"ids": ids, "decision": "PENDING (existing decisions preserved)", "note": "No edge is added to the approved graph"}


def conflicts(store, data):
    # A review aid for explicit contradictions, not an automated theorem prover.
    candidates = store.rows("SELECT source,target,relation,id FROM edges WHERE state='CURRENT'")
    for row in store.rows("SELECT * FROM proposals WHERE decision='APPROVED' AND validation='VALID'"):
        p = json.loads(row["payload"])
        if validate(store, p)["state"] == "VALID":
            candidates.append({**p, "id": row["id"]})
    found = []
    dependencies = {"DEPENDS_ON", "REQUIRES", "IMPLEMENTS", "USES"}
    for other in candidates:
        same_pair = {other["source"], other["target"]} == {data["source"], data["target"]}
        if not same_pair: continue
        if (data["relation"] == "CONFLICTS_WITH" and other["relation"] in dependencies) or (other["relation"] == "CONFLICTS_WITH" and data["relation"] in dependencies):
            found.append({"id": other["id"], "reason": "Conflict relation overlaps a dependency; review meaning"})
        if data["relation"] == other["relation"] == "SUPERSEDES" and data["source"] == other["target"]:
            found.append({"id": other["id"], "reason": "Reciprocal supersession"})
    return found


def review(store, id_, decision, reviewer, rationale, human_approved=False, ack_conflicts=False):
    row = store.db.execute("SELECT * FROM proposals WHERE id=?", (id_,)).fetchone()
    if not row:
        raise QError("Unknown proposal ID")
    if not reviewer.strip() or not rationale.strip():
        raise QError("Reviewer and review rationale are required")
    data = json.loads(row["payload"])
    validation = validate(store, data)
    warnings = conflicts(store, data)
    if decision == "APPROVED":
        if not human_approved:
            raise QError("Approval requires --human-approved after actual explicit human review")
        if validation["state"] != "VALID":
            raise QError("Stale/invalid evidence cannot be approved; retrieve current evidence and propose again")
        if warnings and not ack_conflicts:
            raise QError("Potential contradictory relationships; review semantic show, then use --ack-conflicts only after human resolution")
    with store.db:
        store.db.execute("UPDATE proposals SET decision=?,validation=?,reviewer=?,rationale=?,updated_at=? WHERE id=?",
                         (decision, "VALID" if validation["state"] == "VALID" else "STALE", reviewer, rationale, now(), id_))
        store.db.execute("INSERT INTO reviews(proposal_id,at,action,reviewer,rationale) VALUES (?,?,?,?,?)",
                         (id_, now(), decision, reviewer, rationale))
    return {"id": id_, "decision": decision, "origin": "INFERRED", "conflicts": warnings}


def show(store, id_=None):
    rows = store.rows("SELECT * FROM proposals WHERE id=?", (id_,)) if id_ else store.rows("SELECT * FROM proposals ORDER BY created_at DESC")
    results = []
    for row in rows:
        data = json.loads(row["payload"])
        validation = validate(store, data)
        # Never expose outdated coordinates/quotes as current evidence.
        if validation["state"] != "VALID":
            data["evidence"] = [{"path": e["path"], "hash": e["hash"], "start": None, "end": None, "quote": None, "source_status": "STALE"} for e in data["evidence"]]
        results.append({"id": row["id"], "decision": row["decision"], "stored_validation": row["validation"],
                        "current_validation": validation, "proposal": data, "conflicts": conflicts(store, json.loads(row["payload"]))})
    return {"proposals": results, "note": "CLI records an asserted human decision; it does not authenticate reviewer identity"}
