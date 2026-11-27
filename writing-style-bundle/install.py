#!/usr/bin/env python3
"""Cài / gỡ gói văn phong (writing style bundle: skill q-writing-style, hook nhắc văn phong) vào một dự án.

Mặc định chỉ chạy thử (in kế hoạch). Ghi thật cần --apply (thêm --yes khi không có bàn phím).
Chỉ ghi bên trong --target. Không bao giờ ghi đè CLAUDE.md hay .claude/settings.json đã có:
in đoạn cần chèn và kế hoạch gộp, đồng thời để một bản chép trong .writing-style/merge/.
Dự án đã có skill q-writing-style khác bản của gói: báo từng file khác bao nhiêu dòng, giữ nguyên;
--adopt sao lưu rồi thay.
Nâng cấp: file do bản cũ của gói cài mà bản này không còn (ví dụ skill q-doc-edit trước 1.2.0) được xóa nếu
chưa ai sửa (sao lưu vào .writing-style/backup/); file đã sửa thì giữ và báo.
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
NAME = "writing-style-bundle"
HOME = ".writing-style"
RECORD = HOME + "/install-record.json"
CONFIG = HOME + "/style.config.json"
FRAG_BEGIN = "<!-- BEGIN writing-style-bundle -->"
FRAG_END = "<!-- END writing-style-bundle -->"
COMPONENTS = ("skills", "hooks", "docs")
SKILL = "q-writing-style"
LEGACY_SKILLS = ("q-doc-edit",)     # tên skill của gói trước 1.2.0


class InstallError(Exception):
    pass


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
    """Config của dự án nếu đã có, ngược lại bản mẫu của gói."""
    cfg_path = target / CONFIG
    if cfg_path.is_file():
        return json.loads(cfg_path.read_text(encoding="utf-8-sig")), False
    return json.loads((BUNDLE / "config/style.config.example.json").read_text(encoding="utf-8")), True


def plan(target, cfg, manifest, components):
    """Danh sách (nguồn trong gói, đích tương đối, loại 'copy')."""
    rows = []
    for rel in sorted(manifest["files"]):
        top = rel.split("/", 1)[0]
        rest = rel.split("/", 1)[1] if "/" in rel else ""
        if top == "skills" and "skills" in components:
            rows.append((rel, ".claude/skills/" + rest, "copy"))
        elif top == "hooks" and "hooks" in components and rest.endswith(".py") and "/" not in rest and not rest.startswith("test_"):
            rows.append((rel, ".claude/hooks/" + rest, "copy"))
        elif rel in ("DOC-TRUOC.md", "README_VN.md", "CHANGELOG.md", "SECURITY.md") and "docs" in components:
            rows.append((rel, HOME + "/" + rel, "copy"))
    return rows


def diff_lines(a, b):
    """Số dòng khác giữa hai file văn bản (thêm + bớt), chỉ để báo cho chủ dự án."""
    import difflib
    ta = a.read_text(encoding="utf-8", errors="replace").splitlines()
    tb = b.read_text(encoding="utf-8", errors="replace").splitlines()
    return sum(1 for l in difflib.unified_diff(ta, tb, lineterm="", n=0)
               if l[:1] in "+-" and not l.startswith(("+++", "---")))


def read_record(target):
    path = target / RECORD
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"bundle": NAME, "files": {}, "backups": {}, "created_dirs": []}


def install(args):
    target = check_target(args.target)
    manifest = load_manifest()
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
    old = record.get("version")
    say("Gói %s %s → %s%s" % (NAME, manifest.get("version", "?"), target,
                             (" (nâng cấp từ bản %s đã cài)" % old) if old and old != manifest.get("version") else ""))
    say("Config: %s" % ("tạo mới " + CONFIG if new_cfg else "dùng " + CONFIG + " đã có"))
    say("Sẽ ghi: %d file · bỏ qua: %d · xung đột: %d" % (len(writes), len(skips), len(conflicts)))
    for _, d, kind, how in writes:
        say("  + %s%s" % (d, {"update": " (cập nhật bản cũ của gói)", "backup": " (sao lưu rồi thay, --adopt)"}.get(how, "")))
    for d, why in skips:
        say("  = %s (%s)" % (d, why))
    src_of = {r[1]: r[0] for r in rows}
    for d in conflicts:
        say("  ! %s: file đã có, khác bản của gói %d dòng, không phải do gói cài → giữ nguyên (dùng --adopt để sao lưu rồi thay)"
            % (d, diff_lines(target / d, BUNDLE / src_of[d])))
    if any(d.startswith(".claude/skills/%s/" % SKILL) for d in conflicts):
        say("  ! Dự án đã có skill %s khác bản của gói: so sánh các dòng trên trước khi --adopt." % SKILL)
    stale, stale_kept = stale_files(target, record, rows, components)
    for d in stale:
        say("  - %s (bản cũ của gói, không còn trong bản này, chưa ai sửa → xóa, có sao lưu)" % d)
    for d in stale_kept:
        say("  ! %s: bản cũ của gói, không còn trong bản này, đã sửa sau khi cài → giữ nguyên; xóa tay khi không dùng" % d)
    for legacy in LEGACY_SKILLS:
        if (target / ".claude/skills" / legacy).is_dir() and not any(
                r.startswith(".claude/skills/%s/" % legacy) for r in record["files"]):
            say("  ! Dự án có skill %s không do gói cài (hoặc bản ghi cũ đã mất): giữ nguyên; skill mới là %s, "
                "cân nhắc xóa bản cũ để tránh hai skill văn phong cùng chạy." % (legacy, SKILL))
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
                bak_rel = HOME + "/backup/%s/%s" % (stamp, dest_rel)
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
        for dest_rel in stale:
            dest = inside(target, dest_rel)
            bak = inside(target, HOME + "/backup/%s/%s" % (stamp, dest_rel))
            add_dirs(record, missing_dirs(target, bak.parent))
            bak.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, bak)
            record["pending"] = dest_rel
            save_record(target, record)
            dest.unlink()
            record["files"].pop(dest_rel, None)
            record.pop("pending", None)
            save_record(target, record)
            prune_empty(target, dest.parent)
        write_merges(target, record, stamp, components)
        record["version"] = manifest.get("version")
        record["installed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        record["complete"] = True
        save_record(target, record)
    except Exception as exc:
        raise InstallError("Cài dở dang (%s). Bản ghi từng bước: %s. Chạy --uninstall --apply để gỡ phần đã ghi." % (exc, RECORD))
    say("Đã cài. Bản ghi: %s. Bước tiếp: sửa %s cho dự án (project_rules, glossary, thư mục đầu ra), gộp các đoạn trong %s/merge/ (nếu có) khi chủ dự án duyệt." % (RECORD, CONFIG, HOME))
    return 0


def component_of(dest_rel):
    if dest_rel.startswith(".claude/skills/"):
        return "skills"
    if dest_rel.startswith(".claude/hooks/"):
        return "hooks"
    if dest_rel.startswith(HOME + "/") and "/" not in dest_rel[len(HOME) + 1:]:
        return "docs"
    return None


def stale_files(target, record, rows, components):
    """File do bản trước của gói cài (trong bản ghi) mà bản này không còn: (xóa được, đã sửa → giữ)."""
    planned = {r[1] for r in rows}
    stale, kept = [], []
    for rel, digest in sorted(record.get("files", {}).items()):
        if rel in planned or component_of(rel) not in components or rel in record.get("backups", {}):
            continue
        f = target / rel
        if not f.is_file():
            continue
        (stale if sha256(f) == digest else kept).append(rel)
    return stale, kept


def prune_empty(target, folder):
    """Xóa thư mục rỗng từ folder đi lên, dừng ở .claude/skills, .claude/hooks hoặc thư mục gốc."""
    stop = {target, target / ".claude", target / ".claude/skills", target / ".claude/hooks", target / HOME}
    while folder not in stop and folder.is_dir() and not any(folder.iterdir()):
        folder.rmdir()
        folder = folder.parent


MERGE_PAIRS = (("CLAUDE.md", "templates/CLAUDE-fragment.md", "CLAUDE-fragment.md"),
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
    if live.is_file() and sha256(live) == sha256(BUNDLE / src_rel):
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
    """CLAUDE.md / settings.json: tạo khi chưa có; tệp do gói tạo mà chưa ai sửa thì thay (có sao lưu);
    tệp của chủ dự án thì KHÔNG sửa, chỉ để bản mới trong .writing-style/merge/."""
    text = {
        "create": "%s chưa có → tạo từ gói (%s)",
        "same": "%s đã có nội dung của bản này → bỏ qua",
        "refresh": "%s do bản cài trước tạo, chưa ai sửa → thay bằng bản mới (sao lưu bản cũ vào .writing-style/backup/)",
        "old_fragment": "%s có đoạn của gói bản cũ → KHÔNG sửa; chép đoạn mới vào .writing-style/merge/%s để bạn tự thay",
        "merge": "%s đã có → KHÔNG sửa; chép bản của gói vào .writing-style/merge/%s để bạn tự gộp",
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
                bak = inside(target, HOME + "/backup/%s/%s" % (stamp, live_rel))
                add_dirs(record, missing_dirs(target, bak.parent))
                bak.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(live, bak)       # bản cũ của gói: không khôi phục khi gỡ (giống tệp "update")
            add_dirs(record, missing_dirs(target, live.parent))
            record["pending"] = live_rel
            save_record(target, record)
            live.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(BUNDLE / src_rel, live)
            created[live_rel] = sha256(live)
        else:
            m = inside(target, HOME + "/merge/" + merge_name)
            add_dirs(record, missing_dirs(target, m.parent))
            record["pending"] = HOME + "/merge/" + merge_name
            save_record(target, record)
            m.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(BUNDLE / src_rel, m)
            record["files"][HOME + "/merge/" + merge_name] = sha256(m)
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


HOOK_SCRIPT = "stylewatch.py"


def strip_hook_entries(data):
    """settings dict without the hook commands that name HOOK_SCRIPT; (new dict, number removed)."""
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
            keep = [h for h in inner if not (isinstance(h, dict) and HOOK_SCRIPT in str(h.get("command", "")))]
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
    if HOOK_SCRIPT not in text:
        return "none", ""
    if rel in record.get("seeded", {}):
        return "strip", "  - %s: do gói tạo rồi đã được sửa → chỉ bỏ các mục hook %s, giữ phần còn lại" % (rel, HOOK_SCRIPT)
    return "warn", ("  ! %s: còn mục hook %s do bạn gộp tay → giữ nguyên; gỡ tay theo README_VN.md § 6 "
                    "(lệnh hook thoát 0 khi thiếu script nên không chặn prompt)" % (rel, HOOK_SCRIPT))


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
    s_kind, s_text = settings_plan(target, record, remove)
    if s_text:
        say(s_text)
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
            say("  - .claude/settings.json: đã bỏ %d mục hook %s" % (n, HOOK_SCRIPT))
        except ValueError:
            say("  ! .claude/settings.json không đọc được (JSON lỗi) → giữ nguyên; gỡ tay theo README_VN.md § 6")
    for rel in restore:
        bak = inside(target, backups[rel])
        if bak.is_file():
            dest = inside(target, rel)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(bak, dest)
    inside(target, RECORD).unlink()
    tmp = inside(target, RECORD + ".tmp")
    if tmp.is_file():
        tmp.unlink()
    for rel in sorted(record.get("created_dirs", []), key=lambda r: -r.count("/")):
        d = target / rel
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    for rel in (HOME + "/merge", HOME):
        d = target / rel
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    say("Đã gỡ. Giữ nguyên %d file đã sửa / đã xóa sau khi cài; bản sao lưu (nếu có) nằm trong .writing-style/backup/."
        % (len(keep) + len(gone)))
    return 0


def confirm(prompt):
    if not sys.stdin or not sys.stdin.isatty():
        raise InstallError("Không có bàn phím để xác nhận: thêm --yes.")
    return input(prompt).strip().lower() in ("y", "yes", "c", "co", "có")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Cài / gỡ gói văn phong vào một dự án (mặc định chỉ chạy thử).")
    ap.add_argument("--target", required=True, help="Thư mục gốc dự án đích")
    ap.add_argument("--apply", action="store_true", help="Ghi thật (không có thì chỉ in kế hoạch)")
    ap.add_argument("--yes", action="store_true", help="Không hỏi lại (cần khi chạy không có bàn phím)")
    ap.add_argument("--uninstall", action="store_true", help="Gỡ những gì gói đã cài (file đã sửa được giữ lại)")
    ap.add_argument("--components", help="skills,hooks,docs (mặc định: tất cả)")
    ap.add_argument("--adopt", action="store_true", help="Cho thay file đã có mà gói không nhận ra (sau khi sao lưu)")
    args = ap.parse_args(argv)
    if sys.version_info < (3, 8):
        say("Cần Python 3.8 trở lên.")
        return 2
    try:
        return uninstall(args) if args.uninstall else install(args)
    except InstallError as exc:
        say("DỪNG: " + str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
