#!/usr/bin/env python3
"""Cài / gỡ gói quy trình nhóm (workflow skill bundle) vào một dự án.

Mặc định chỉ chạy thử (in kế hoạch). Ghi thật cần --apply (thêm --yes khi không có bàn phím).
Chỉ ghi bên trong --target. Không bao giờ ghi đè CLAUDE.md, AGENTS.md hay .claude/settings.json đã có:
in đoạn cần chèn và kế hoạch gộp, đồng thời để một bản chép trong .workflow/merge/.
Chỉ dùng thư viện chuẩn của Python (3.8+).

Ví dụ:
  python install.py --target <thư mục dự án>                 # chạy thử
  python install.py --target <thư mục dự án> --apply         # cài
  python install.py --target <thư mục dự án> --uninstall --apply
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

BUNDLE = Path(__file__).resolve().parent
sys.path.insert(0, str(BUNDLE / "tools"))
import pylauncher  # noqa: E402

MIN_PYTHON = (3, 8)
LAUNCHER = "python"     # lệnh gọi Python của máy này; pick_launcher() đặt một lần mỗi lần chạy
NAME = "workflow-skill-bundle"
RECORD = ".workflow/install-record.json"
CONFIG = ".workflow/workflow.config.json"
FRAG_BEGIN = "<!-- BEGIN workflow-skill-bundle -->"
FRAG_END = "<!-- END workflow-skill-bundle -->"
COMPONENTS = ("skills", "scripts", "hooks", "templates", "docs")


class InstallError(Exception):
    pass


def source_bytes(src_rel):
    """Nội dung file của gói như sẽ ghi vào dự án. hooks/hooks.json: lệnh hook bắt đầu bằng lệnh Python của máy này
    (python → giữ nguyên từng byte)."""
    data = (BUNDLE / src_rel).read_bytes()
    if src_rel == "hooks/hooks.json" and LAUNCHER != "python":
        data = data.replace(b'"command": "python -I -S ',
                            ('"command": "%s -I -S ' % json.dumps(LAUNCHER, ensure_ascii=False)[1:-1]).encode("utf-8"))
    return data


def settings_launchers(target):
    """Các lệnh Python đang đứng đầu lệnh hook của gói trong .claude/settings.json của dự án."""
    try:
        data = json.loads((target / ".claude/settings.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return []
    return pylauncher.used_in(data, HOOK_SCRIPTS)


def pick_launcher(target, explicit):
    """Đặt LAUNCHER = lệnh thật sự chạy được Python 3.8+ trên máy này (xem tools/pylauncher.py)."""
    global LAUNCHER
    try:
        LAUNCHER, info, tried = pylauncher.choose(MIN_PYTHON, explicit=explicit, existing=settings_launchers(target))
    except pylauncher.LauncherError as exc:
        raise InstallError("Không tìm được lệnh gọi Python 3.8+ cho hook (%s). Cài Python bản chính thức, "
                           "hoặc chỉ rõ bằng --python <lệnh hoặc đường dẫn>." % exc)
    say("Lệnh Python ghi vào lệnh hook: %s (Python %s)%s"
        % (LAUNCHER, ".".join(str(n) for n in info["version"]),
           "; bỏ qua: " + "; ".join("`%s` %s" % t for t in tried) if tried else ""))


def launcher_lines(target, merge_file):
    """Dòng báo khi settings.json của chủ dự án (gói không sửa) gọi hook của gói bằng lệnh Python khác lần cài này."""
    return ["! .claude/settings.json: lệnh hook của gói đang bắt đầu bằng `%s`, lần cài này dùng `%s` → hook có thể "
            "không chạy trên máy này; đổi phần đầu các lệnh đó thành `%s` (bản mẫu: %s)" % (old, LAUNCHER, LAUNCHER, merge_file)
            for old in settings_launchers(target) if old != LAUNCHER]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def say(text=""):
    sys.stdout.write(text + "\n")


def load_manifest():
    """Đọc MANIFEST.json và kiểm SHA-256 từng file của gói (gói bị sửa / thiếu file → dừng)."""
    data = json.loads((BUNDLE / "MANIFEST.json").read_text(encoding="utf-8"))
    files = data.get("files", {})
    bad = [rel for rel, meta in files.items()
           if not (BUNDLE / rel).is_file() or sha256(BUNDLE / rel) != meta.get("sha256")]
    if bad:
        raise InstallError("Gói không khớp MANIFEST.json (%d file): %s" % (len(bad), ", ".join(sorted(bad)[:5])))
    return data


def inside(target, rel):
    """Đường dẫn đích tuyệt đối, bảo đảm nằm trong target và không đi qua symlink / junction."""
    rel = str(rel).replace("\\", "/")
    if not rel or rel.startswith("/") or ":" in rel or ".." in rel.split("/"):
        raise InstallError("Đường dẫn không hợp lệ: " + rel)
    p = target
    for part in rel.split("/"):
        if part in ("", "."):
            continue
        p = p / part
        if p.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(p)):
            raise InstallError("Không ghi qua symlink / junction: " + str(p))
    if os.path.commonpath([str(target), str(p.resolve())]) != str(target):
        raise InstallError("Đường dẫn ra ngoài thư mục đích: " + rel)
    return p


def check_target(raw):
    target = Path(raw).resolve()
    if not target.is_dir():
        raise InstallError("Thư mục đích không có: " + str(target))
    if target == BUNDLE or BUNDLE in target.parents or target in BUNDLE.parents:
        raise InstallError("Thư mục đích không được chứa gói hoặc nằm trong gói.")
    return target


def read_config(target, args):
    """Config của dự án nếu đã có, ngược lại bản mẫu của gói (+ --owner-name / --project-name)."""
    cfg_path = target / CONFIG
    if cfg_path.is_file():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
        return cfg, False
    cfg = json.loads((BUNDLE / "config/workflow.config.example.json").read_text(encoding="utf-8"))
    if args.owner_name:
        cfg["owner_name"] = args.owner_name
    if args.project_name:
        cfg["project_name"] = args.project_name
    return cfg, True


def plan(target, cfg, manifest, components):
    """Danh sách (nguồn trong gói, đích tương đối, loại). loại: 'copy' = file của gói; 'seed' = khuôn, chỉ tạo khi chưa có."""
    p = cfg["paths"]
    rows = []
    for rel in sorted(manifest["files"]):
        top = rel.split("/", 1)[0]
        rest = rel.split("/", 1)[1] if "/" in rel else ""
        if top == "skills" and "skills" in components:
            rows.append((rel, ".claude/skills/" + rest, "copy"))
        elif top == "scripts" and "scripts" in components:
            rows.append((rel, p["scripts"].rstrip("/") + "/" + rest, "copy"))
        elif top == "hooks" and "hooks" in components and rest.endswith(".py") and "/" not in rest and not rest.startswith("test_"):
            rows.append((rel, ".claude/hooks/" + rest, "copy"))      # turnlog.py, ctxwatch.py
        elif top == "docs" and "docs" in components:
            rows.append((rel, ".workflow/docs/" + rest, "copy"))
        elif rel in ("DOC-TRUOC.md", "README_VN.md", "CHANGELOG.md", "SECURITY.md") and "docs" in components:
            rows.append((rel, ".workflow/" + rel, "copy"))
        elif top == "templates" and "templates" in components:
            dest = template_dest(rest, cfg)
            if dest:
                rows.append((rel, dest, "seed"))
    return rows


def template_dest(rest, cfg):
    p = cfg["paths"]
    simple = {
        "ROLES.md": p["process_docs"] + "/ROLES.md",
        "NAMES.md": p["process_docs"] + "/NAMES.md",
        "RULES-HISTORY.md": p["process_docs"] + "/RULES-HISTORY.md",
        "cards/README.md": p["cards"] + "/README.md",
        "lead/board.md": p["lead"] + "/board.md",
        "lead/INBOX.md": p["lead"] + "/INBOX.md",
        "lead/backlog.md": p["lead"] + "/backlog.md",
        "POLICY.default.md": cfg.get("policy_file") or (p["process_docs"] + "/POLICY.md"),
    }
    if rest in simple:
        return simple[rest]
    if rest.startswith("cards/_TEMPLATE/"):
        return p["cards"] + "/" + rest[len("cards/"):]
    if rest.startswith("lead/sprint/"):
        return p["lead"] + "/sprint/_TEMPLATE/" + rest[len("lead/sprint/"):]
    if rest.startswith("roles/"):
        return p["roles_docs"] + "/_TEMPLATE/" + rest[len("roles/"):]
    return None   # CLAUDE-fragment.md: xử lý riêng (không bao giờ ghi đè CLAUDE.md)


def read_record(target):
    path = target / RECORD
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"bundle": NAME, "files": {}, "backups": {}, "created_dirs": []}


def install(args):
    target = check_target(args.target)
    manifest = load_manifest()
    pick_launcher(target, args.python)
    components = tuple(c.strip() for c in (args.components or ",".join(COMPONENTS)).split(",") if c.strip())
    unknown = [c for c in components if c not in COMPONENTS]
    if unknown:
        raise InstallError("Thành phần không có: " + ", ".join(unknown))
    cfg, new_cfg = read_config(target, args)
    record = read_record(target)
    rows = plan(target, cfg, manifest, components)

    writes, skips, conflicts = [], [], []
    for src_rel, dest_rel, kind in rows:
        dest = inside(target, dest_rel)
        src_hash = manifest["files"][src_rel]["sha256"]
        if not dest.exists():
            writes.append((src_rel, dest_rel, kind, None))
        elif dest.is_file() and sha256(dest) == src_hash:
            skips.append((dest_rel, "giống bản trong gói"))
        elif kind == "seed":
            skips.append((dest_rel, "đã có (khuôn chỉ tạo khi chưa có)"))
        elif dest_rel in record["files"] and sha256(dest) == record["files"][dest_rel]:
            writes.append((src_rel, dest_rel, kind, "update"))      # bản cũ của gói, chưa ai sửa
        elif args.adopt:
            writes.append((src_rel, dest_rel, kind, "backup"))
        else:
            conflicts.append(dest_rel)

    merges = merge_plan(target, record, components)
    # settings.json do gói tạo (create / refresh) được thay bằng bản mới → lệnh cũ trong đó tự hết
    replaced = tuple(rel for rel, src, _ in merge_pairs(components)
                     if rel == ".claude/settings.json" and merge_state(target, record, rel, src) in ("create", "refresh"))
    if "hooks" in components and not replaced:
        merges += launcher_lines(target, ".workflow/merge/hooks.json")
    merges += legacy_lines(legacy_hooks(target, skip=replaced),
                           ".workflow/merge/hooks.json" if "hooks" in components else "hooks/hooks.json của gói")
    old = record.get("version")
    say("Gói %s %s → %s%s" % (NAME, manifest.get("version", "?"), target,
                             (" (nâng cấp từ bản %s đã cài)" % old) if old and old != manifest.get("version") else ""))
    say("Config: %s" % ("tạo mới " + CONFIG if new_cfg else "dùng " + CONFIG + " đã có"))
    say("Sẽ ghi: %d file · bỏ qua: %d · xung đột: %d" % (len(writes), len(skips), len(conflicts)))
    for _, d, kind, how in writes:
        say("  + %s%s" % (d, {"update": " (cập nhật bản cũ của gói)", "backup": " (sao lưu rồi thay, --adopt)"}.get(how, "")))
    for d, why in skips:
        say("  = %s (%s)" % (d, why))
    for d in conflicts:
        say("  ! %s: file đã có và khác gói, không phải do gói cài → giữ nguyên (dùng --adopt để sao lưu rồi thay)" % d)
    for line in merges:
        say("  > " + line)
    if not args.apply:
        say("Chạy thử: chưa ghi gì. Thêm --apply để cài.")
        return 0
    if not args.yes and not confirm("Cài %d file vào %s? [y/N] " % (len(writes), target)):
        say("Đã hủy.")
        return 1

    stamp = time.strftime("%Y%m%d-%H%M%S")
    record["complete"] = False
    try:
        # Bản ghi được ghi lại sau từng bước (nhật ký): cài dở thì --uninstall vẫn biết đã ghi những gì.
        add_dirs(record, missing_dirs(target, inside(target, RECORD).parent))
        save_record(target, record)
        for src_rel, dest_rel, kind, how in writes:
            dest = inside(target, dest_rel)
            if how == "backup" or (how == "update" and dest_rel not in record["backups"]):
                bak_rel = ".workflow/backup/%s/%s" % (stamp, dest_rel)
                bak = inside(target, bak_rel)
                add_dirs(record, missing_dirs(target, bak.parent))
                bak.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest, bak)
                if how == "backup":
                    # chỉ bản sao lưu file của chủ dự án (--adopt) mới được khôi phục khi gỡ;
                    # bản cũ của gói (update) không khôi phục, và không đè con trỏ tới bản gốc của chủ dự án
                    record["backups"][dest_rel] = bak_rel
            add_dirs(record, missing_dirs(target, dest.parent))
            record["pending"] = dest_rel
            save_record(target, record)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(BUNDLE / src_rel, dest)
            if kind == "copy":
                record["files"][dest_rel] = sha256(dest)
            else:
                record.setdefault("seeded", {})[dest_rel] = sha256(dest)
            record.pop("pending", None)
            save_record(target, record)
        if new_cfg:
            cfg_path = inside(target, CONFIG)
            record["pending"] = CONFIG
            save_record(target, record)
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            record.setdefault("seeded", {})[CONFIG] = sha256(cfg_path)
            record.pop("pending", None)
            save_record(target, record)
        for rel in ("STATUS.md",):
            f = inside(target, cfg["paths"]["process_docs"] + "/" + rel)
            if not f.exists():
                add_dirs(record, missing_dirs(target, f.parent))
                record["pending"] = cfg["paths"]["process_docs"] + "/" + rel
                save_record(target, record)
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text("# STATUS\n\nTrạng thái các card đang chạy (trưởng nhóm ghi).\n", encoding="utf-8")
                record.setdefault("seeded", {})[cfg["paths"]["process_docs"] + "/" + rel] = sha256(f)
                record.pop("pending", None)
                save_record(target, record)
        write_merges(target, record, stamp, components)
        record["version"] = manifest.get("version")
        record["installed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        record["complete"] = True
        save_record(target, record)
    except Exception as exc:
        raise InstallError("Cài dở dang (%s). Bản ghi từng bước: %s. Chạy --uninstall --apply để gỡ phần đã ghi." % (exc, RECORD))
    say("Đã cài. Bản ghi: %s. Bước tiếp: sửa %s cho dự án, gộp các đoạn trong .workflow/merge/ (nếu có)." % (RECORD, CONFIG))
    return 0


MERGE_PAIRS = (("CLAUDE.md", "templates/CLAUDE-fragment.md", "CLAUDE-fragment.md"),
               ("AGENTS.md", "AGENTS.md", "AGENTS.workflow.md"),
               (".claude/settings.json", "hooks/hooks.json", "hooks.json"))


def fragment_block(text):
    """Đoạn của gói trong CLAUDE.md (từ dòng BEGIN tới hết dòng END), hoặc None."""
    i = text.find(FRAG_BEGIN)
    j = text.find(FRAG_END, i + 1) if i >= 0 else -1
    return text[i:j + len(FRAG_END)] if i >= 0 and j >= 0 else None


def merge_state(target, record, live_rel, src_rel):
    """create | same | refresh (tệp do gói tạo, chưa ai sửa → thay, có sao lưu) | old_fragment | merge"""
    live = target / live_rel
    if not live.exists():
        return "create"
    if live.is_file() and sha256(live) == hashlib.sha256(source_bytes(src_rel)).hexdigest():
        return "same"
    if live.is_file() and record.get("seeded", {}).get(live_rel) == sha256(live):
        return "refresh"
    if live_rel == "CLAUDE.md":
        block = fragment_block(live.read_text(encoding="utf-8-sig", errors="replace"))
        if block is not None:
            new = fragment_block((BUNDLE / src_rel).read_text(encoding="utf-8"))
            return "same" if block.strip() == (new or "").strip() else "old_fragment"
    return "merge"


def merge_pairs(components):
    """settings.json (hook block) only when the hooks are installed: never a hook entry without its script."""
    return [m for m in MERGE_PAIRS if m[0] != ".claude/settings.json" or "hooks" in components]


def merge_plan(target, record, components=COMPONENTS):
    """CLAUDE.md / AGENTS.md / settings.json: tạo khi chưa có; tệp do gói tạo mà chưa ai sửa thì thay (có sao lưu);
    tệp của chủ dự án thì KHÔNG sửa, chỉ để bản mới trong .workflow/merge/."""
    text = {
        "create": "%s chưa có → tạo từ gói (%s)",
        "same": "%s đã có nội dung của bản này → bỏ qua",
        "refresh": "%s do bản cài trước tạo, chưa ai sửa → thay bằng bản mới (sao lưu bản cũ vào .workflow/backup/)",
        "old_fragment": "%s có đoạn của gói bản cũ → KHÔNG sửa; chép đoạn mới vào .workflow/merge/%s để bạn tự thay",
        "merge": "%s đã có → KHÔNG sửa; chép bản của gói vào .workflow/merge/%s để bạn tự gộp",
    }
    lines = []
    for live_rel, src_rel, merge_name in merge_pairs(components):
        st = merge_state(target, record, live_rel, src_rel)
        lines.append(text[st] % ((live_rel, merge_name) if st in ("old_fragment", "merge") else (live_rel, src_rel)
                                 if st == "create" else (live_rel,)))
    return lines


def write_merges(target, record, stamp, components=COMPONENTS):
    created = record.setdefault("seeded", {})
    for live_rel, src_rel, merge_name in merge_pairs(components):
        st = merge_state(target, record, live_rel, src_rel)
        live = inside(target, live_rel)
        if st == "same":
            continue
        if st in ("create", "refresh"):
            if st == "refresh":
                bak = inside(target, ".workflow/backup/%s/%s" % (stamp, live_rel))
                add_dirs(record, missing_dirs(target, bak.parent))
                bak.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(live, bak)       # bản cũ của gói: không khôi phục khi gỡ (giống tệp "update")
            add_dirs(record, missing_dirs(target, live.parent))
            record["pending"] = live_rel
            save_record(target, record)
            live.parent.mkdir(parents=True, exist_ok=True)
            live.write_bytes(source_bytes(src_rel))
            created[live_rel] = sha256(live)
        else:
            m = inside(target, ".workflow/merge/" + merge_name)
            add_dirs(record, missing_dirs(target, m.parent))
            record["pending"] = ".workflow/merge/" + merge_name
            save_record(target, record)
            m.parent.mkdir(parents=True, exist_ok=True)
            m.write_bytes(source_bytes(src_rel))
            record["files"][".workflow/merge/" + merge_name] = sha256(m)
        record.pop("pending", None)
        save_record(target, record)


def missing_dirs(target, folder):
    out = []
    while folder != target and not folder.exists():
        out.append(folder.relative_to(target).as_posix())
        folder = folder.parent
    return out


def add_dirs(record, dirs):
    record["created_dirs"] = sorted(set(record.get("created_dirs", [])) | set(dirs))


def save_record(target, record):
    """Ghi bản ghi cài đặt (ghi file tạm rồi thay, để không bao giờ còn một bản ghi viết dở)."""
    rec = inside(target, RECORD)
    rec.parent.mkdir(parents=True, exist_ok=True)
    tmp = rec.with_name(rec.name + ".tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(str(tmp), str(rec))


HOOK_SCRIPTS = ("turnlog.py", "ctxwatch.py")
SETTINGS_FILES = (".claude/settings.json", ".claude/settings.local.json")


def is_safe_hook_command(command):
    """Dạng an toàn (từ 1.1): python kiểm có file rồi mới chạy bằng runpy → thiếu script thì thoát 0."""
    return "runpy" in command and "isfile" in command


def legacy_hooks(target, skip=()):
    """{settings file: [(event, script)]}: lệnh hook gọi script của gói mà không ở dạng an toàn (dạng v1.0:
    `python -I -S "${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/turnlog.py"` → thoát mã 2 khi thiếu script)."""
    found = {}
    for rel in SETTINGS_FILES:
        f = target / rel
        if rel in skip or not f.is_file():
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8-sig"))
        except ValueError:
            continue
        hooks = data.get("hooks") if isinstance(data, dict) else None
        for event, groups in (hooks.items() if isinstance(hooks, dict) else ()):
            for g in groups if isinstance(groups, list) else ():
                for h in (g.get("hooks") if isinstance(g, dict) else None) or ():
                    cmd = str(h.get("command", "")) if isinstance(h, dict) else ""
                    for s in HOOK_SCRIPTS:
                        if s in cmd and not is_safe_hook_command(cmd):
                            found.setdefault(rel, []).append((event, s))
    return found


def legacy_lines(found, replacement):
    out = []
    for rel, items in found.items():
        scripts = sorted({s for _, s in items})
        events = sorted({e for e, _ in items})
        out.append("! %s: %d lệnh hook dạng cũ (v1.0) gọi %s (%s) — thoát mã 2 khi thiếu script, có thể chặn mọi prompt "
                   "→ thay bằng khối trong %s (README_VN.md § 6)"
                   % (rel, len(items), " / ".join(scripts), ", ".join(events), replacement))
    return out


def strip_hook_entries(data):
    """settings dict without the hook commands that name one of HOOK_SCRIPTS; (new dict, number removed)."""
    removed = 0
    hooks = data.get("hooks") if isinstance(data, dict) else None
    if not isinstance(hooks, dict):
        return data, 0
    for event in list(hooks):
        groups = hooks[event] if isinstance(hooks[event], list) else []
        kept_groups = []
        for g in groups:
            inner = g.get("hooks") if isinstance(g, dict) else None
            if not isinstance(inner, list):
                kept_groups.append(g)
                continue
            keep = [h for h in inner if not (isinstance(h, dict) and any(s in str(h.get("command", "")) for s in HOOK_SCRIPTS))]
            removed += len(inner) - len(keep)
            if keep:
                g = dict(g, hooks=keep)
                kept_groups.append(g)
        if kept_groups:
            hooks[event] = kept_groups
        else:
            del hooks[event]
    if not hooks:
        data.pop("hooks", None)
    return data, removed


def settings_plan(target, record, remove):
    """What uninstall does with .claude/settings.json: ('none'|'strip'|'warn', text)."""
    rel = ".claude/settings.json"
    f = target / rel
    if rel in remove or not f.is_file():
        return "none", ""
    text = f.read_text(encoding="utf-8-sig", errors="replace")
    if not any(s in text for s in HOOK_SCRIPTS):
        return "none", ""
    if rel in record.get("seeded", {}):
        return "strip", "  - %s: do gói tạo rồi đã được sửa → chỉ bỏ các mục hook %s, giữ phần còn lại" % (rel, " / ".join(HOOK_SCRIPTS))
    return "warn", "  ! %s: còn mục hook %s do bạn gộp tay → giữ nguyên; gỡ tay theo README_VN.md § 6" % (rel, " / ".join(HOOK_SCRIPTS))


def uninstall(args):
    target = check_target(args.target)
    if not (target / RECORD).is_file():
        say("Không thấy bản ghi cài đặt (%s) → không có gì để gỡ." % RECORD)
        return 0
    record = read_record(target)
    backups = record.get("backups", {})
    pending = record.get("pending")
    # Luật: chỉ xóa / khôi phục file còn đúng hash lúc cài. File chủ dự án đã sửa (hoặc đã xóa) sau khi cài → giữ nguyên.
    remove, keep, gone, restore = [], [], [], []
    for rel, digest in list(record["files"].items()) + list(record.get("seeded", {}).items()):
        if rel == pending:
            continue
        f = target / rel
        if not f.is_file():
            if rel in backups:
                gone.append(rel)
            continue
        if sha256(f) == digest:
            remove.append(rel)
            if rel in backups:
                restore.append(rel)
        else:
            keep.append(rel)
    if pending:
        # file đang ghi khi lần cài dừng: gói chỉ ghi vào chỗ chưa có file, file cũ của gói, hoặc file đã sao lưu (--adopt)
        if pending in backups:
            restore.append(pending)
        elif (target / pending).is_file():
            remove.append(pending)
    s_kind, s_text = settings_plan(target, record, remove)
    # Lệnh hook dạng cũ (v1.0) còn lại sau khi gỡ → giữ script nó gọi, nếu không lệnh đó thoát mã 2 (chặn prompt).
    after = tuple(rel for rel in SETTINGS_FILES if rel in remove) + ((".claude/settings.json",) if s_kind == "strip" else ())
    legacy = legacy_hooks(target, skip=after)
    held = {}
    for s in sorted({s for items in legacy.values() for _, s in items}):
        rel = ".claude/hooks/" + s
        if rel in remove and rel in record["files"]:
            remove.remove(rel)
            held[rel] = record["files"][rel]
    say("Gỡ %s khỏi %s" % (NAME, target))
    if not record.get("complete", True):
        say("Lần cài trước dừng giữa chừng → gỡ theo bản ghi từng bước.")
    say("Sẽ xóa: %d file (còn đúng như lúc cài) · giữ lại: %d file (đã sửa sau khi cài) · khôi phục: %d bản sao lưu"
        % (len(remove), len(keep) + len(gone), len(restore)))
    for rel in keep:
        say("  ! %s: đã sửa sau khi cài — giữ nguyên%s"
            % (rel, ("; bản trước khi cài: " + backups[rel]) if rel in backups else ""))
    for rel in gone:
        say("  ! %s: đã bị xóa sau khi cài — không khôi phục; bản trước khi cài: %s" % (rel, backups[rel]))
    if pending:
        say("  ~ %s: đang ghi dở khi lần cài dừng → %s" % (pending, "khôi phục bản sao lưu" if pending in backups else "xóa"))
    if s_text:
        say(s_text)
    for line in legacy_lines(legacy, "hooks/hooks.json của gói"):
        say("  " + line)
    for rel in held:
        say("  ! %s: giữ lại vì còn lệnh hook dạng cũ gọi tệp này; thay / xóa lệnh cũ rồi chạy gỡ lại để xóa" % rel)
    if s_kind == "warn" and not legacy:
        say("    (các lệnh hook còn lại đều ở dạng an toàn: thoát 0 khi thiếu script, không chặn prompt)")
    if not args.apply:
        say("Chạy thử: chưa xóa gì. Thêm --apply để gỡ.")
        return 0
    if not args.yes and not confirm("Gỡ %d file khỏi %s? [y/N] " % (len(remove), target)):
        say("Đã hủy.")
        return 1
    for rel in remove:
        inside(target, rel).unlink()
    if s_kind == "strip":
        f = inside(target, ".claude/settings.json")
        try:
            data, n = strip_hook_entries(json.loads(f.read_text(encoding="utf-8-sig")))
            f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            say("  - .claude/settings.json: đã bỏ %d mục hook %s" % (n, " / ".join(HOOK_SCRIPTS)))
        except ValueError:
            say("  ! .claude/settings.json không đọc được (JSON lỗi) → giữ nguyên; gỡ tay theo README_VN.md § 6")
    for rel in restore:
        bak = inside(target, backups[rel])
        if bak.is_file():
            dest = inside(target, rel)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(bak, dest)
    if held:
        # còn script giữ lại → bản ghi chỉ còn các script đó, để lần gỡ sau xóa được
        save_record(target, {"bundle": NAME, "version": record.get("version"), "files": held, "seeded": {},
                             "backups": {}, "created_dirs": record.get("created_dirs", []), "complete": True})
    else:
        inside(target, RECORD).unlink()
    tmp = inside(target, RECORD + ".tmp")
    if tmp.is_file():
        tmp.unlink()
    for rel in sorted(record.get("created_dirs", []), key=lambda r: -r.count("/")):
        d = target / rel
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    for rel in (".workflow/merge", ".workflow/docs", ".workflow"):
        d = target / rel
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    say("Đã gỡ. Giữ nguyên %d file đã sửa / đã xóa sau khi cài; bản sao lưu (nếu có) nằm trong .workflow/backup/."
        % (len(keep) + len(gone)))
    if held:
        say("Còn %d script hook giữ cho lệnh dạng cũ (bản ghi: %s); thay / xóa lệnh cũ rồi chạy gỡ lại." % (len(held), RECORD))
    say("Nhật ký do hook ghi (process-log/) là dữ liệu của dự án → giữ nguyên.")
    return 0


def confirm(prompt):
    if not sys.stdin or not sys.stdin.isatty():
        raise InstallError("Không có bàn phím để xác nhận: thêm --yes.")
    return input(prompt).strip().lower() in ("y", "yes", "c", "co", "có")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Cài / gỡ gói quy trình nhóm vào một dự án (mặc định chỉ chạy thử).")
    ap.add_argument("--target", required=True, help="Thư mục gốc dự án đích")
    ap.add_argument("--apply", action="store_true", help="Ghi thật (không có thì chỉ in kế hoạch)")
    ap.add_argument("--yes", action="store_true", help="Không hỏi lại (cần khi chạy không có bàn phím)")
    ap.add_argument("--uninstall", action="store_true", help="Gỡ những gì gói đã cài (file đã sửa được giữ lại)")
    ap.add_argument("--components", help="skills,scripts,hooks,templates,docs (mặc định: tất cả)")
    ap.add_argument("--owner-name", help="Cách gọi chủ dự án trong hướng dẫn (mặc định: chủ dự án)")
    ap.add_argument("--project-name", help="Tên dự án ghi vào config mới")
    ap.add_argument("--python", help="Lệnh gọi Python ghi vào lệnh hook (mặc định tự dò: lệnh đang dùng trong dự án, "
                                     "python, python3, py -3). Ví dụ: python3, \"py -3\", đường dẫn python của venv")
    ap.add_argument("--adopt", action="store_true", help="Cho thay file đã có mà gói không nhận ra (sau khi sao lưu)")
    args = ap.parse_args(argv)
    if sys.version_info < MIN_PYTHON:
        say("Cần Python 3.8 trở lên.")
        return 2
    try:
        return uninstall(args) if args.uninstall else install(args)
    except InstallError as exc:
        say("DỪNG: " + str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
