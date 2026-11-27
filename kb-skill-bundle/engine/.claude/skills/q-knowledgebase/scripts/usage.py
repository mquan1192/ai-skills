"""Optional usage log (2.1.0-e3): one JSON line per search / query / explore / related / impact call, so the routing
and the misses can be reviewed later. Off unless the configuration names a folder:

    "usage_log": {"path": "<folder relative to the root>", "query_text": true | false, "miss_score": <number>}

Line: time, command, scope, route + reason, model used + reason, latency in ms (model load included), result count,
top score, coverage (best / concepts), miss flag, query text only when query_text is true. Never result text.
Fail-safe: any error while writing (locked folder, full disk, bad path) is ignored; the command result is unchanged."""
from __future__ import annotations

import json
import time

COMMANDS = ("search", "query", "explore", "related", "impact")


def _query(args):
    for name in ("query", "question", "node"):
        value = getattr(args, name, None)
        if isinstance(value, str):
            return value
    return ""


def entry(cfg, args, result, ms):
    """The log line (dict) for one call; result may be an error dict."""
    s = cfg.get("usage_log") or {}
    result = result if isinstance(result, dict) else {}
    items = result.get("results") or result.get("nodes") or []
    top = items[0].get("score") if items and isinstance(items[0], dict) else None
    sem = result.get("semantic") or {}
    cov = result.get("coverage") or {}
    error = result.get("ok") is False
    miss = error or not items or (isinstance(top, (int, float)) and top < s.get("miss_score", 0))
    line = {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "command": args.command,
            "scope": getattr(args, "project", None) or "all",
            "route": result.get("route") or ("graph" if args.command in ("related", "impact") else "text"),
            "reason": result.get("reason", ""), "model": bool(sem.get("used")), "model_reason": sem.get("reason", ""),
            "ms": round(ms, 1), "results": len(items), "top_score": round(top, 2) if isinstance(top, (int, float)) else None,
            "coverage": "%s/%s" % (cov.get("best"), cov.get("concepts")) if cov else None,
            "miss": bool(miss), "error": error}
    if s.get("query_text"):
        line["query"] = _query(args)[:500]
    return line


def record(root, cfg, args, result, ms):
    """Append one line to <path>/<yyyy-MM-dd>.jsonl below root; never raises."""
    try:
        s = cfg.get("usage_log") or {}
        if not s.get("path") or getattr(args, "command", None) not in COMMANDS:
            return False
        from core import safe_path
        folder = safe_path(root, s["path"])
        folder.mkdir(parents=True, exist_ok=True)
        text = json.dumps(entry(cfg, args, result, ms), ensure_ascii=False) + "\n"
        with open(folder / (time.strftime("%Y-%m-%d") + ".jsonl"), "a", encoding="utf-8") as f:
            f.write(text)
        return True
    except Exception:      # noqa: BLE001 - a log must never break a search
        return False
