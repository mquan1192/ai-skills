"""query command: deterministic routing of one question to an existing command.

No model is called. The keyword lists come from the configuration ("query_routes", per route and language);
the output always names the route and the reason, so the caller can run another command when the route is
not the one it wanted.
"""
from __future__ import annotations

import re

from core import QError, fold
import engine
import retrieval

IDENTIFIER = re.compile(
    r"^(?:[\w.-]*/[\w./-]+"                     # path with a slash
    r"|[\w-]+\.[A-Za-z0-9]{1,5}"                # file name with a suffix
    r"|[A-Za-z_]\w*::\w+(?:::\w+)*"             # a::b
    r"|[a-z]+[A-Z]\w*|[A-Z][a-z0-9]+[A-Z]\w*"   # camelCase / CamelCase
    r"|[A-Za-z]\w*_\w+"                         # snake_case / SCREAMING_CASE
    r"|[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+"         # qualified name: Class.method
    r"|[A-Z]{2,}[A-Z0-9]*-?\d+[A-Z0-9]*"        # codes: ABC-123, ERR500123
    r"|(?=[A-Z0-9-]*\d)[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+"   # codes with several parts: REQ-USER-01
    r")$")


def _keyword_regex(phrase):
    """A configured keyword; "*" marks an object slot (used by the path route)."""
    def word(p):
        return re.escape(p) if retrieval.CJK.search(p) else r"(?<!\w)" + re.escape(p) + r"(?!\w)"
    parts = [p.strip() for p in fold(phrase).split("*")]
    regex = word(parts[0]) if parts[0] else ""
    for i, part in enumerate(parts[1:], 1):
        last = i == len(parts) - 1
        if part:
            regex += r"\s*(.+?)\s*" + word(part)
        else:
            regex += r"\s*(.+)$" if last else r"\s*(.+?)\s*"
    return re.compile(regex)


def _keywords(cfg, route, text):
    """Every configured keyword of a route found in the folded question, in configuration order."""
    hits = []
    for lang, words in cfg["query_routes"].get(route, {}).items():
        for word in words:
            match = _keyword_regex(word).search(text)
            if match:
                hits.append((word, lang, match))
    return hits


def _first_keyword(cfg, route, text):
    hits = _keywords(cfg, route, text)
    return hits[0] if hits else None


def _node_for(store, phrase):
    """A graph node for a written object: node id, exact path or label, or a unique file name / path tail."""
    phrase = phrase.strip(" \t\"'`?.,:;()[]")
    if not phrase:
        return None
    try:
        return engine.resolve_node(store, phrase)
    except QError:
        pass
    tail = phrase.replace("\\", "/").casefold()
    files = [r for r in store.rows("SELECT * FROM nodes WHERE type IN ('DOCUMENT','CODE_FILE') AND hash != ''")
             if r["path"].casefold() == tail or r["path"].casefold().endswith("/" + tail)]
    return files[0] if len(files) == 1 else None


def _object(store, question, keyword_match):
    """Object of a related / impact question: identifier-like words first, then the rest of the sentence."""
    rest = (question[:keyword_match.start()] + " " + question[keyword_match.end():]) if keyword_match else question
    words = re.findall(r"[^\s\"'`?,;()]+", rest)
    for word in sorted((w for w in words if IDENTIFIER.match(w.strip("."))), key=len, reverse=True):
        node = _node_for(store, word.strip("."))
        if node:
            return node
    return _node_for(store, rest)


def query(store, question, top=5, depth=2, project=None, semantic=None):
    if not question.strip():
        raise QError("Empty question")
    text = fold(question)
    cfg = store.cfg

    def done(route, reason, result, **extra):
        return {"route": route, "reason": reason, **extra, **result}

    # 1. path: "from A to B" / "A -> B" with two known nodes
    arrow = re.search(r"(.+?)\s*(?:->|→|⇒)\s*(.+)", question)
    pairs = []
    if arrow:
        pairs.append((arrow.group(1), arrow.group(2), "arrow"))
    for word, lang, match in _keywords(cfg, "path", text):
        if match.lastindex and match.lastindex >= 2:
            pairs.append((match.group(1), match.group(2), "keyword '%s' (%s)" % (word, lang)))
    for left, right, why in pairs:
        src = _object(store, left, None)
        dst = _object(store, right, None)
        if src and dst:
            return done("path", "%s with two known nodes" % why,
                        engine.find_path(store, src["id"], dst["id"], depth, "out"),
                        arguments={"source": src["path"] if src["type"] in ("DOCUMENT", "CODE_FILE") else src["id"],
                                   "target": dst["path"] if dst["type"] in ("DOCUMENT", "CODE_FILE") else dst["id"]})
    # 2. impact and 3. related: keyword + one known node
    for route in ("impact", "related"):
        hit = _first_keyword(cfg, route, text)
        if not hit:
            continue
        # keyword offsets are on the folded text; folding keeps the length of Latin and kana text
        node = _object(store, question if len(text) == len(question) else text, hit[2])
        if node:
            args = {"node": node["path"] if node["type"] in ("DOCUMENT", "CODE_FILE") else node["id"]}
            if route == "impact":
                result = engine.traverse(store, node["id"], depth, "in", impact=True, top=top * 6, project=project)
            else:
                result = engine.traverse(store, node["id"], depth, "both", top=top * 6, project=project)
            return done(route, "keyword '%s' (%s) and known node '%s'" % (hit[0], hit[1], node["label"]), result, arguments=args)
    # 4. explore: "how does / như thế nào / 仕組み"
    hit = _first_keyword(cfg, "explore", text)
    if hit:
        return done("explore", "keyword '%s' (%s): search plus graph context" % (hit[0], hit[1]),
                    engine.explore(store, question, top, depth, project, semantic))
    # 5. exact: the whole question is one identifier, file name, path or code
    words = question.split()
    if len(words) <= 2 and all(IDENTIFIER.match(w) for w in words):
        return done("exact", "identifier, file name, path or code: exact search and symbols",
                    engine.search(store, question, top, project, semantic))
    # 6. text search with the glossary bridge
    analysis = retrieval.analyse(store, question)
    reason = "text search" + (" with glossary expansion" if analysis["expanded"] else "")
    return done("text", reason, engine.search(store, question, top, project, semantic))
