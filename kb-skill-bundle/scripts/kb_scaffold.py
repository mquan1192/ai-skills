"""Dựng KB rỗng cho một dự án mới (chỉ thư viện chuẩn, không ghi đè file có sẵn).

Cách dùng (từ thư mục gốc của dự án):
    python -E -s -B <bundle>/scripts/kb_scaffold.py --project <dự án> [--sub <phần>] [--root .]
        [--manager-folder 00_KB_Manager] [--session-name KB_Manager] [--dry-run]

Cần: Q-KnowledgeBase 2.1.0-c1 trở lên (bản cũ từ chối .qkb/config.json do script này ghi).

Tạo:
    .qkb/config.json (phạm vi chỉ mục: kb/ và projects/)
    kb/VERSION, kb/CHANGELOG.md, kb/<dự án>/README.md, kb/<dự án>/<phần>/INDEX.md, _sources.md, notes.md
    projects/<dự án>/<phần>/docs/, src/
    <manager-folder>/README.md, kb.config.json, requests/, locks/, staging/
"""
import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.normpath(os.path.join(HERE, "..", "templates"))
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def _fail(message):
    print("LỖI: " + message, file=sys.stderr)
    sys.exit(2)


def _read(rel):
    with open(os.path.join(TEMPLATES, rel), encoding="utf-8") as f:
        return f.read()


def _fill(text, values):
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def plan(root, project, sub, manager, session_name, today):
    """List of (relative path, content or None for a folder)."""
    values = {"PROJECT": project, "SUB": sub, "DATE": today, "MANAGER_FOLDER": manager, "SESSION_NAME": session_name}
    kb = "kb/%s/%s" % (project, sub)
    cfg = json.loads(_read("kb.config.example.json"))
    cfg["manager"] = {"folder": manager, "session_name": session_name, "session_file": manager + "/session.json"}
    for key, folder in (("requests_folder", "requests"), ("locks_folder", "locks"), ("staging_folder", "staging")):
        cfg[key] = manager + "/" + folder
    cfg["search"]["never_read"] = ["projects/", manager + "/staging/"]
    cfg["project_scopes"] = {"%s/%s" % (project, sub): [kb + "/", "kb/%s/shared/" % project]}
    # Index scope for Q-KnowledgeBase (written only when .qkb/config.json is absent; `qkb init` keeps an existing file).
    qkb = {"project_name": project, "knowledge_paths": ["kb"], "source_paths": ["projects"],
           "project_roots": ["kb", "projects"], "history_paths": ["kb/**/history/**"],
           "exclude_patterns": [manager + "/**"], "issue_id_patterns": cfg.get("issue_id_patterns", [])}
    items = [
        (".qkb/config.json", json.dumps(qkb, ensure_ascii=False, indent=2) + "\n"),
        ("kb/VERSION", _read("kb/VERSION")),
        ("kb/CHANGELOG.md", _read("kb/CHANGELOG.md")),
        ("kb/%s/README.md" % project, _fill(_read("pages/project-README.md"), values)),
        (kb + "/INDEX.md", _fill(_read("pages/INDEX.md"), values)),
        (kb + "/_sources.md", _fill(_read("pages/_sources.md"), values)),
        (kb + "/notes.md", _fill(_read("pages/notes.md"), values)),
        ("projects/%s/%s/docs" % (project, sub), None),
        ("projects/%s/%s/src" % (project, sub), None),
        (manager + "/README.md", _fill(_read("manager/README.md"), values)),
        (manager + "/kb.config.json", json.dumps(cfg, ensure_ascii=False, indent=2) + "\n"),
        (manager + "/requests", None),
        (manager + "/locks", None),
        (manager + "/staging", None),
    ]
    return items


def main(argv=None):
    ap = argparse.ArgumentParser(description="Dựng KB rỗng cho một dự án (không ghi đè file có sẵn).")
    ap.add_argument("--project", required=True, help="Tên dự án (chữ, số, . _ -)")
    ap.add_argument("--sub", default="main", help="Tên phần của dự án (mặc định: main)")
    ap.add_argument("--root", default=".", help="Thư mục gốc của dự án (mặc định: thư mục hiện tại)")
    ap.add_argument("--manager-folder", default="00_KB_Manager", help="Thư mục phiên quản lý KB")
    ap.add_argument("--session-name", default="KB_Manager", help="Tên phiên quản lý KB")
    ap.add_argument("--dry-run", action="store_true", help="Chỉ liệt kê, không tạo gì")
    args = ap.parse_args(argv)
    for label, value in (("--project", args.project), ("--sub", args.sub), ("--manager-folder", args.manager_folder)):
        if not NAME.match(value):
            _fail("%s chỉ được chứa chữ, số và . _ - (tối đa 64 ký tự): %r" % (label, value))
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        _fail("không thấy thư mục gốc: %s" % root)
    today = datetime.date.today().isoformat()
    created, kept = [], []
    for rel, content in plan(root, args.project, args.sub, args.manager_folder, args.session_name, today):
        target = os.path.join(root, *rel.split("/"))
        if os.path.exists(target):
            kept.append(rel)
            continue
        created.append(rel)
        if args.dry_run:
            continue
        if content is None:
            os.makedirs(target, exist_ok=True)
        else:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
    head = "Sẽ tạo" if args.dry_run else "Đã tạo"
    print("%s %d mục:" % (head, len(created)))
    for rel in created:
        print("  - " + rel)
    if kept:
        print("Giữ nguyên %d mục có sẵn:" % len(kept))
        for rel in kept:
            print("  - " + rel)
    if not args.dry_run:
        print("Bước tiếp theo:")
        print("  - Dựng chỉ mục: python -E -s -B .claude/skills/q-knowledgebase/scripts/qkb.py build")
        print("  - Chép tài liệu gốc vào projects/%s/%s/docs/ và code vào src/." % (args.project, args.sub))
        print("  - Tạo phiên quản lý KB tên %s, thư mục làm việc %s/." % (args.session_name, args.manager_folder))
        print("  - Trong phiên đó gõ: /q-kb-publish --whoami")
    return 0


if __name__ == "__main__":
    sys.exit(main())
