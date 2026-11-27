"""Build MANIFEST.json (and optionally manifests/known-engine.json) of the KB skill bundle. Stdlib only.

    python -E -s -B tools/build_manifest.py [--bundle-version 2.0] \
        [--known 2.0.0=<folder> --known 2.1.0-b1=<folder> ...]

--known <version>=<folder>: a folder that holds `.claude/skills/q-knowledgebase/` (+ `.claude/rules/q-knowledgebase.md`)
of that engine version; its sha256 list goes to manifests/known-engine.json (lets install.py recognise unmodified old files).
"""
import argparse
import hashlib
import json
import os
import re
import sys

BUNDLE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
MANAGER_SKILLS = ("q-kb-sync", "q-kb-add", "q-kb-publish")
SKIP_DIRS = {"__pycache__", ".git"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def classify(rel):
    """(component, dest, mode) for one bundle path (POSIX). dest uses {manager}."""
    p = rel.split("/")
    if rel.startswith("engine/.claude/") or rel.startswith("engine/.qkb/"):
        dest = rel[len("engine/"):]
        return "engine", dest, "create-only" if dest.startswith(".qkb/") else "replace"
    if p[0] == "skills" and len(p) > 2:
        if p[1] in MANAGER_SKILLS:
            return "manager-skills", "{manager}/.claude/skills/" + "/".join(p[1:]), "replace"
        return "skills", ".claude/skills/" + "/".join(p[1:]), "replace"
    if rel == "tools/kbpack.py":
        return "skills", ".claude/tools/kbpack.py", "replace"
    if p[0] == "hooks" and p[-1].endswith(".py"):
        return "hooks", ".claude/hooks/" + p[-1], "replace"
    if p[0] == "templates" and (p[1] == "pages" or p[1] in ("request.md", "kb-policy.default.md", "kb.config.example.json")):
        return "templates", "{manager}/templates/" + "/".join(p[1:]), "create-only"
    return "bundle", None, "not-installed"


def engine_version():
    with open(os.path.join(BUNDLE, "engine", ".claude", "skills", "q-knowledgebase", "scripts", "core.py"), encoding="utf-8") as f:
        m = re.search(r'^VERSION\s*=\s*"([^"]+)"', f.read(), re.M)
    return m.group(1) if m else "unknown"


def walk(root):
    for folder, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(names):
            if name.endswith(".pyc"):
                continue
            full = os.path.join(folder, name)
            yield os.path.relpath(full, root).replace("\\", "/"), full


def build(bundle_version):
    files = []
    for rel, full in walk(BUNDLE):
        if rel == "MANIFEST.json":
            continue
        component, dest, mode = classify(rel)
        files.append({"path": rel, "sha256": sha256(full), "bytes": os.path.getsize(full), "component": component,
                      "dest": dest, "mode": mode})
    return {"product": "KB-Skill-Bundle", "bundle_version": bundle_version, "engine_version": engine_version(),
            "note": "Per-file sha256; this file is not listed. install.py checks every entry before writing.",
            "files": files}


def known(pairs):
    """Versions already in manifests/known-engine.json are kept; --known adds or replaces versions."""
    try:
        with open(os.path.join(BUNDLE, "manifests", "known-engine.json"), encoding="utf-8") as f:
            out = json.load(f).get("versions", {})
    except (OSError, ValueError):
        out = {}
    for pair in pairs:
        version, _, folder = pair.partition("=")
        entries = {}
        for sub in (os.path.join(".claude", "skills", "q-knowledgebase"), os.path.join(".claude", "rules")):
            top = os.path.join(folder, sub)
            if not os.path.isdir(top):
                continue
            for rel, full in walk(top):
                dest = (sub.replace("\\", "/") + "/" + rel)
                if sub.endswith("rules") and rel != "q-knowledgebase.md":
                    continue
                entries[dest] = sha256(full)
        if not entries:
            print("LỖI: không thấy engine trong %s" % folder, file=sys.stderr)
            sys.exit(2)
        out[version] = entries
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Sinh MANIFEST.json của gói.")
    ap.add_argument("--bundle-version", default="2.0.4")
    ap.add_argument("--known", action="append", default=[], metavar="VERSION=FOLDER")
    args = ap.parse_args(argv)
    if args.known:
        data = known(args.known)
        os.makedirs(os.path.join(BUNDLE, "manifests"), exist_ok=True)
        with open(os.path.join(BUNDLE, "manifests", "known-engine.json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump({"note": "sha256 of unmodified engine files per released version (dest paths)", "versions": data},
                      f, indent=1, sort_keys=True)
            f.write("\n")
    manifest = build(args.bundle_version)
    with open(os.path.join(BUNDLE, "MANIFEST.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
        f.write("\n")
    counts = {}
    for e in manifest["files"]:
        counts[e["component"]] = counts.get(e["component"], 0) + 1
    print("MANIFEST.json: %d file, engine %s, %s" % (len(manifest["files"]), manifest["engine_version"], counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
