#!/usr/bin/env python3
"""Gói dữ liệu KB: xuất, nhập, kiểm, gỡ một dự án (hoặc một phần của dự án). Chỉ thư viện chuẩn, không dùng mạng.

Mặc định chỉ in kế hoạch; thêm --apply để làm thật. Chạy từ thư mục gốc dự án (hoặc --root <thư mục>).

    python -E -s -B .claude/tools/kbpack.py export --project <dự án> [--sub <phần>] [--requires <dự án>] [--accept MÃ,…] [--apply]
    python -E -s -B .claude/tools/kbpack.py import <file.zip> [--discard-local] [--apply]
    python -E -s -B .claude/tools/kbpack.py verify [--project <dự án> [--sub <phần>]]
    python -E -s -B .claude/tools/kbpack.py remove --project <dự án> [--sub <phần>] [--apply]

Mã thoát: 0 xong / chỉ in kế hoạch · 1 cần người quyết định (cảnh báo chưa chấp nhận, xung đột, file bị sửa)
          2 từ chối (sai tham số, gói lệch / không an toàn, phát hiện bị cấm, hạ bản) · 4 lỗi khi ghi, đã trả lại bản cũ
Gói chỉ là file trong máy: công cụ không gửi gói đi đâu.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import uuid
import zipfile

sys.dont_write_bytecode = True
FORMAT = "kb-data-pack"
FORMAT_VERSION = 1
QKB = ".claude/skills/q-knowledgebase/scripts/qkb.py"
CONFIG_NAMES = ("kb.config.json", "00_UpdateDocs/kb.config.json")
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
DATA_EXT = {".md", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
PACK_ROOT_FILES = {"PACK.json", "README_VN.md", "CHANGELOG.md"}
SUB_SHARED = ("shared", "rules", "README.md")          # parts of a project that every sub-project pack carries
MAX_FILES, MAX_BYTES = 20000, 1024 * 1024 * 1024
ENGINE_MIN = "2.1.0-d2"      # the engine merges pack settings from 2.1.0-d2 on

FORBIDDEN = [   # 🚫: never in a pack (value never printed)
    ("PRIVATE_KEY", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("CREDENTIAL", re.compile(r"(?i)\b(?:password|passwd|pwd|secret|api[_-]?key|access[_-]?key|auth[_-]?token|client[_-]?secret)"
                              r"\s*[:=]\s*[\"']?(?![\[<$%{(]|MASKED)[^\s\"'<>`|]{6,}")),
    ("CLOUD_KEY", re.compile(r"\b(?:AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}|xox[baprs]-[A-Za-z0-9-]{10,})\b")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}")),
]
WARNINGS = [    # ⚠️: the reviewer accepts each kind with --accept
    ("PERSONAL", re.compile(r"[\w.+-]+@[\w-]+\.[A-Za-z]{2,}|\+\d{2,3}[ -]?\d{2,4}[ -]?\d{3,4}[ -]?\d{3,4}")),
    ("ABS_PATH", re.compile(r"(?<![\w/\\])[A-Za-z]:[\\/][^\s`)\]|]+|(?<![\w.])/(?:home|Users|mnt|opt|srv)/[^\s`)]+")),
    ("SESSION_ID", re.compile(r"local_[0-9a-f]{8}-[0-9a-f]{4}", re.I)),
]


class Stop(Exception):
    def __init__(self, code, message):
        Exception.__init__(self, message)
        self.code = code


# ----------------------------------------------------------------------------- small helpers

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def version_key(v):
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-([a-z]+)(\d+))?$", v or "")
    if m:
        a, b, c, stage, n = m.groups()
        return (0, int(a), int(b), int(c), stage or "~", int(n or 0))
    m = re.match(r"^(\d{4})\.(\d{2})\.(\d{2})-(\d+)$", v or "")          # KB version YYYY.MM.DD-NN
    if m:
        return (1,) + tuple(int(x) for x in m.groups())
    return None


def newer(a, b):
    ka, kb = version_key(a), version_key(b)
    return (ka > kb) if ka is not None and kb is not None and ka[0] == kb[0] else (a or "") > (b or "")


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".kbtmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def stamp():
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def unlock(path):
    """Clear the read-only flag of every file below path (imported copies are read-only)."""
    for folder, _, names in os.walk(path) if os.path.isdir(path) else [(os.path.dirname(path), [], [os.path.basename(path)])]:
        for n in names:
            p = os.path.join(folder, n)
            try:
                os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
            except OSError:
                pass


def set_readonly(path):
    for folder, _, names in os.walk(path) if os.path.isdir(path) else [(os.path.dirname(path), [], [os.path.basename(path)])]:
        for n in names:
            try:
                os.chmod(os.path.join(folder, n), stat.S_IREAD)
            except OSError:
                pass


class Project:
    """The working project: config files, kb root, pack records."""

    def __init__(self, root):
        self.root = os.path.abspath(root)
        if not os.path.isdir(self.root):
            raise Stop(2, "LỖI: không thấy thư mục dự án: %s" % root)
        self.cfg_path = self.find_config()
        self.cfg = read_json(self.cfg_path, {}) if self.cfg_path else {}
        self.kb_root = (self.cfg.get("kb_root") or "kb").strip("/\\")
        self.qcfg_path = os.path.join(self.root, ".qkb", "config.json")

    def find_config(self):
        names = [CONFIG_NAMES[0]]
        rec = read_json(os.path.join(self.root, ".qkb", "install", "installed.json"), {}) or {}
        folder = (rec.get("options") or {}).get("manager_folder")
        if isinstance(folder, str) and folder and ".." not in folder.replace("\\", "/").split("/"):
            names.append(folder.strip("/\\") + "/kb.config.json")
        names += [n for n in CONFIG_NAMES[1:] if n not in names]
        for n in names:
            p = os.path.join(self.root, *n.split("/"))
            if os.path.isfile(p):
                return p
        return None

    def path(self, rel):
        # an absolute path is kept as given (accepted only inside the project), never re-rooted
        if os.path.isabs(rel):
            full = os.path.normpath(rel)
        else:
            full = os.path.normpath(os.path.join(self.root, *rel.replace("\\", "/").split("/")))
        try:
            inside = os.path.commonpath([os.path.normcase(self.root), os.path.normcase(full)]) == os.path.normcase(self.root)
        except ValueError:          # another drive
            inside = False
        if not inside:
            raise Stop(2, "LỖI: đường dẫn ra ngoài thư mục dự án: %s" % rel)
        return full

    def kb(self, rel=""):
        return self.path(self.kb_root + ("/" + rel if rel else ""))

    def record_dir(self, name):
        return os.path.join(self.root, ".qkb", "packs", name.replace("/", "__"))

    def records(self):
        top = os.path.join(self.root, ".qkb", "packs")
        out = {}
        if os.path.isdir(top):
            for d in sorted(os.listdir(top)):
                state = read_json(os.path.join(top, d, "state.json"))
                pack = read_json(os.path.join(top, d, "PACK.json"))
                if state and pack:
                    out[pack["name"]] = {"state": state, "pack": pack}
        return out

    def engine_version(self):
        try:
            with open(self.path(".claude/skills/q-knowledgebase/scripts/core.py"), encoding="utf-8") as f:
                m = re.search(r'^VERSION\s*=\s*"([^"]+)"', f.read(), re.M)
            return m.group(1) if m else None
        except OSError:
            return None

    def run_qkb(self, args, timeout=900):
        script = self.path(QKB)
        if not os.path.isfile(script) or not os.path.isfile(self.qcfg_path):
            return None
        flags = 0x08000000 if os.name == "nt" else 0
        r = subprocess.run([sys.executable, "-E", "-s", "-B", script] + args + ["--format", "json"], cwd=self.root,
                           capture_output=True, timeout=timeout, creationflags=flags)
        try:
            return json.loads(r.stdout.decode("utf-8", "replace") or "{}")
        except ValueError:
            return {}


def pack_name(project, sub):
    for label, value in (("--project", project), ("--sub", sub)):
        if value is not None and not NAME.match(value):
            raise Stop(2, "LỖI: %s chỉ được chứa chữ, số và . _ - (tối đa 64 ký tự): %r" % (label, value))
    return project + ("/" + sub if sub else "")


def units_of(proj, project, sub):
    """kb-relative units (folders or files) of a pack."""
    if not sub:
        return [project]
    units = [project + "/" + sub]
    for extra in SUB_SHARED:
        if os.path.exists(proj.kb(project + "/" + extra)):
            units.append(project + "/" + extra)
    return units


def list_files(proj, units, include_ext):
    files, skipped = [], {}
    for unit in units:
        full = proj.kb(unit)
        entries = [(full, os.path.basename(full))] if os.path.isfile(full) else []
        for folder, dirs, names in (os.walk(full) if os.path.isdir(full) else []):
            dirs[:] = sorted(d for d in dirs if not d.startswith("."))
            entries += [(os.path.join(folder, n), n) for n in sorted(names)]
        for p, n in entries:
            if os.path.islink(p):
                continue
            ext = os.path.splitext(n)[1].lower()
            rel = os.path.relpath(p, proj.kb()).replace("\\", "/")
            if ext in DATA_EXT or ext in include_ext:
                files.append(rel)
            else:
                skipped[ext or "(không đuôi)"] = skipped.get(ext or "(không đuôi)", 0) + 1
    return sorted(set(files)), skipped


def digest_of(files):
    text = "".join("%s  %s\n" % (f["sha256"], f["path"]) for f in sorted(files, key=lambda x: x["path"]))
    return sha256_bytes(text.encode("utf-8"))


# ----------------------------------------------------------------------------- export

def scan(proj, rel, text, other_projects, forbidden_extra):
    found, warn = [], []
    for no, line in enumerate(text.splitlines(), 1):
        for code, rx in FORBIDDEN + forbidden_extra:
            if rx.search(line):
                found.append((rel, no, code))
        for code, rx in WARNINGS:
            if rx.search(line):
                warn.append((rel, no, code))
        low = line.lower()
        for other in other_projects:
            if re.search(r"(?:^|[\s(`/\"'])(?:%s/|\.\./)+%s/" % (re.escape(proj.kb_root.lower()), re.escape(other.lower())), low) \
                    or (len(other) >= 4 and re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(other.lower()), low)):
                warn.append((rel, no, "OTHER_PROJECT"))
                break
    return found, warn


def settings_for(proj, project, units):
    """Data-bound settings of the pack (flat PACK.json keys, contract with the engine).
    Paths are relative to <kb_root>/<project>/; the engine merges glossary / history / ID / alias keys at load time,
    kbpack merges scopes and hook keywords into kb.config.json."""
    cfg, qcfg = proj.cfg, read_json(proj.qcfg_path, {}) or {}
    base = proj.kb_root + "/" + project + "/"
    pre = [proj.kb_root + "/" + u + ("/" if os.path.isdir(proj.kb(u)) else "") for u in units]
    norm = lambda p: p.replace("\\", "/") if isinstance(p, str) else ""
    under = lambda p: any(norm(p).startswith(x) or norm(p) + "/" == x for x in pre)
    rel = lambda p: norm(p)[len(base):] if norm(p).startswith(base) else None
    scopes = {k: v for k, v in (cfg.get("project_scopes") or {}).items()
              if not k.startswith("_") and (k == project or k.startswith(project + "/") or any(under(p) for p in v))}
    hooks = cfg.get("hooks") or {}
    glossaries = sorted({rel(p) for p in (cfg.get("glossary_files") or []) + (qcfg.get("glossary_paths") or [])
                         if under(p) and rel(p)})
    history = sorted({rel(p) for p in (qcfg.get("history_paths") or []) if rel(p)})
    sources = [norm(p) for p in (qcfg.get("source_paths") or []) if project in norm(p).split("/")]
    aliases = {k: v for k, v in (qcfg.get("code_aliases") or {}).items()
               if any(norm(v).startswith(s.rstrip("/") + "/") or norm(v) == s for s in sources)}
    policy = rel(cfg.get("policy_file")) if under(cfg.get("policy_file")) else ""
    return {
        "glossary_files": glossaries, "history_paths": history, "code_aliases": aliases,
        "issue_id_patterns": sorted(set((cfg.get("issue_id_patterns") or []) + (qcfg.get("issue_id_patterns") or []))),
        "id_patterns": qcfg.get("id_patterns") or {}, "issue_fields": qcfg.get("issue_fields") or {},
        # query_routes = the engine's router dict ({route: {lang: [words]}}, contract "Agreed 18/11")
        "query_routes": qcfg.get("query_routes") or {}, "source_roots_expected": sources,
        # kbpack / hook / skill keys (the engine ignores them)
        "scopes": scopes, "route_keywords": hooks.get("route_keywords") or [],
        "route_id_patterns": hooks.get("route_id_patterns") or [], "policy_file": policy or "",
    }


def export(args, out):
    proj = Project(args.root)
    name = pack_name(args.project, args.sub)
    if args.project in proj.records() or any(r.startswith(args.project + "/") for r in proj.records()) \
            or name in proj.records():
        raise Stop(2, "LỖI: dự án %s là bản đã nhập từ gói; chỉ bên soạn mới xuất gói." % args.project)
    if not os.path.isdir(proj.kb(args.project)) or (args.sub and not os.path.isdir(proj.kb(name))):
        raise Stop(2, "LỖI: không thấy %s/%s." % (proj.kb_root, name))
    units = units_of(proj, args.project, args.sub)
    # step 1: published? (no staged file, no open lock under the pack)
    staging = proj.path((proj.cfg.get("staging_folder") or "00_UpdateDocs/staging"))
    open_items = []
    for unit in units:
        if os.path.exists(os.path.join(staging, *(proj.kb_root + "/" + unit).split("/"))):
            open_items.append("staging: " + unit)
    locks = proj.path((proj.cfg.get("locks_folder") or "00_UpdateDocs/locks"))
    if os.path.isdir(locks):
        for n in os.listdir(locks):
            target = n[:-5].replace("__", "/") if n.endswith(".lock") else ""
            if any(target.startswith(proj.kb_root + "/" + u) for u in units):
                with open(os.path.join(locks, n), encoding="utf-8", errors="replace") as f:
                    lines = [l for l in f.read().splitlines() if l.strip()]
                if lines and not lines[-1].startswith("released"):
                    open_items.append("lock: " + target)
    if open_items:
        raise Stop(2, "DỪNG: dự án còn phần đang cập nhật (chưa phát hành):\n" + "\n".join("  - " + x for x in open_items))
    include_ext = {e if e.startswith(".") else "." + e for e in (args.include_ext or "").split(",") if e}
    files, skipped = list_files(proj, units, include_ext)
    if not files:
        raise Stop(2, "LỖI: không có file nào để đóng gói.")
    others = [d for d in os.listdir(proj.kb()) if os.path.isdir(proj.kb(d)) and d != args.project
              and d not in (args.requires or [])]
    forbidden_extra = []
    for p in proj.cfg.get("pack_forbidden_patterns") or []:
        try:
            forbidden_extra.append(("POLICY_PATTERN", re.compile(p)))
        except re.error:
            raise Stop(2, "LỖI: mẫu cấm trong kb.config.json không hợp lệ: %r" % p)
    found, warn, entries = [], [], []
    for rel in files:
        full = proj.kb(rel)
        with open(full, "rb") as f:
            data = f.read()
        entries.append({"path": rel, "sha256": sha256_bytes(data), "bytes": len(data)})
        if rel.endswith(".md"):
            f_, w_ = scan(proj, rel, data.decode("utf-8", "replace"), others, forbidden_extra)
            found += f_
            warn += w_
    # requires
    requires = []
    for req in args.requires or []:
        last = read_json(os.path.join(proj.root, ".qkb", "packs-out", req, "PACK.json"))
        if not last:
            raise Stop(2, "LỖI: gói %s cần gói %s, nhưng gói %s chưa được xuất lần nào trên máy này. Xuất gói %s trước."
                       % (name, req, req, req))
        requires.append({"pack_id": last["pack_id"], "project": req, "min_version": last["kb_version"]})
    out_dir = os.path.join(proj.root, ".qkb", "packs-out", name.replace("/", "__"))
    last = read_json(os.path.join(out_dir, "PACK.json"))
    kb_version = "0000.00.00-00"
    vf = proj.path(proj.cfg.get("version_file") or (proj.kb_root + "/VERSION"))
    if os.path.isfile(vf):
        with open(vf, encoding="utf-8") as f:
            kb_version = (f.readline().strip() or kb_version)
    accepted = {c.strip().upper() for c in (args.accept or "").split(",") if c.strip()}
    warn_codes = sorted({c for _, _, c in warn})
    not_accepted = [c for c in warn_codes if c not in accepted]
    say(out, "XUẤT GÓI DỮ LIỆU KB — %s (KB v%s)%s" % (name, kb_version, "" if args.apply else " — KẾ HOẠCH (chưa ghi gì)"))
    say(out, "1. File vào gói: %d (%s byte)" % (len(entries), sum(e["bytes"] for e in entries)))
    if skipped:
        say(out, "2. File không vào gói (không phải Markdown / ảnh): %s" % ", ".join("%s × %d" % kv for kv in sorted(skipped.items())))
    say(out, "3. Quét chính sách: %d phát hiện bị cấm · %d cảnh báo (%s)" % (len(found), len(warn), ", ".join(warn_codes) or "—"))
    for rel, no, code in found[:50]:
        say(out, "  🚫 %s:%d %s" % (rel, no, code))
    for rel, no, code in warn[:50]:
        say(out, "  ⚠️ %s:%d %s" % (rel, no, code))
    links = proj.run_qkb(["verify", "--links"], timeout=300)
    if links and isinstance(links.get("links"), dict):
        say(out, "4. Liên kết hỏng (toàn chỉ mục của máy này): %s" % links["links"].get("broken"))
    if found:
        raise Stop(2, "DỪNG: có %d phát hiện bị cấm (thông tin đăng nhập hoặc mẫu cấm của dự án). Sửa trong KB, phát hành lại, "
                      "rồi xuất lại. Không ghi gì." % len(found))
    if not_accepted:
        say(out, "CẦN DUYỆT: cảnh báo %s. Xem từng dòng ở trên; đồng ý thì chạy lại kèm --accept %s"
            % (", ".join(not_accepted), ",".join(not_accepted)))
        return 1, {"name": name, "warnings": warn_codes}
    pack = {
        "format": FORMAT, "format_version": FORMAT_VERSION, "pack_id": (last or {}).get("pack_id") or str(uuid.uuid4()),
        "name": name, "project": args.project, "sub": args.sub or "", "units": units,
        "title": args.title or name, "kb_version": kb_version,
        "created": datetime.datetime.now().isoformat(timespec="seconds"), "previous_version": (last or {}).get("kb_version", ""),
        "engine_min": ENGINE_MIN, "kb_root_name": proj.kb_root, "languages": proj.cfg.get("languages") or {},
        "requires": requires,
        "files": entries, "digest": digest_of(entries),
        "policy": {"data_class": "B", "scan": {"date": datetime.date.today().isoformat(), "rules": [c for c, _ in FORBIDDEN + WARNINGS]
                                               + ["OTHER_PROJECT"] + (["POLICY_PATTERN"] if forbidden_extra else []),
                                               "forbidden": 0, "warnings": len(warn), "accepted": sorted(accepted & set(warn_codes))}},
        "excluded": {"rule": "chỉ Markdown và ảnh" + (" + " + ",".join(sorted(include_ext)) if include_ext else ""),
                     "skipped": skipped},
    }
    pack.update(settings_for(proj, args.project, units))
    # one KB version = one content; a changed KB needs a publish (new version) before the next export
    if last and last.get("kb_version") == kb_version and last.get("digest") != pack["digest"]:
        raise Stop(2, "DỪNG: nội dung %s đã đổi so với gói v%s đã xuất, nhưng phiên bản KB chưa tăng. "
                      "Phát hành KB trước (/q-kb-publish) rồi xuất lại." % (name, kb_version))
    old = {f["path"]: f["sha256"] for f in (last or {}).get("files", [])}
    new = {f["path"]: f["sha256"] for f in entries}
    added = len([p for p in new if p not in old])
    changed = len([p for p in new if p in old and new[p] != old[p]])
    removed = len([p for p in old if p not in new])
    log_line = "- v%s · %s · thêm %d · sửa %d · bỏ %d file" % (kb_version, datetime.date.today().strftime("%d/%m/%Y"),
                                                              added, changed, removed)
    old_log = ""
    if last and os.path.isfile(os.path.join(out_dir, "CHANGELOG.md")):
        with open(os.path.join(out_dir, "CHANGELOG.md"), encoding="utf-8") as f:
            old_log = "".join(f.readlines()[2:])
    changelog = "# Lịch sử gói %s\n\n%s\n%s" % (name, log_line, old_log)
    readme = ("# Gói dữ liệu KB: %s (KB v%s)\n\n- Máy nhận cần cài bộ skill KB (dạng người đọc là đủ).\n"
              "- Xem trước: `python -E -s -B .claude/tools/kbpack.py import <file zip>`\n"
              "- Nhập: thêm `--apply`. Bản nhập là bản chỉ đọc; cập nhật bằng gói mới hơn.\n"
              "- Kiểm bản đã nhập: `python -E -s -B .claude/tools/kbpack.py verify`\n"
              "- Gỡ: `python -E -s -B .claude/tools/kbpack.py remove --project %s%s --apply`\n"
              "- Chỉ mục không đi theo gói; công cụ nhập tự dựng lại.\n"
              % (name, kb_version, args.project, (" --sub " + args.sub) if args.sub else ""))
    out_root = proj.path(args.out) if args.out else os.path.join(
        proj.path((proj.cfg.get("manager") or {}).get("folder") or "00_UpdateDocs"), "exports")
    zip_name = "KB-Data_%s_v%s_%s.zip" % (name.replace("/", "-"), kb_version, datetime.date.today().strftime("%Y%m%d"))
    zip_path = os.path.join(out_root, zip_name)
    say(out, "5. File gói: %s" % zip_path)
    if not args.apply:
        say(out, "Để xuất: chạy lại kèm --apply%s" % ((" --accept " + ",".join(warn_codes)) if warn_codes else ""))
        return 0, {"name": name, "files": len(entries)}
    os.makedirs(out_root, exist_ok=True)
    tmp = zip_path + ".kbtmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("PACK.json", json.dumps(pack, ensure_ascii=False, indent=1) + "\n")
        z.writestr("README_VN.md", readme)
        z.writestr("CHANGELOG.md", changelog)
        for e in entries:
            z.write(proj.kb(e["path"]), "data/" + e["path"])
    os.replace(tmp, zip_path)
    write_json(os.path.join(out_dir, "PACK.json"), pack)
    with open(os.path.join(out_dir, "CHANGELOG.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(changelog)
    digest = sha256_file(zip_path)
    say(out, "ĐÃ XUẤT: %s · sha256 %s · %d file · %d byte" % (zip_name, digest, len(entries), os.path.getsize(zip_path)))
    say(out, "Gói chỉ nằm trên máy này. Gửi cho người khác là việc của người có quyền duyệt; báo kèm mã sha256 ở trên.")
    return 0, {"name": name, "zip": zip_path, "sha256": digest}


# ----------------------------------------------------------------------------- import

WIN_RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(\..*)?$", re.I)
NESTED_QUANTIFIER = re.compile(r"[+*}?]\)*[+*{]|\((?:[^()\\]|\\.)*[+*](?:[^()\\]|\\.)*\)[+*{]")
PATTERN_MAX = 200


def unsafe_name(path):
    """Reason a pack path is unsafe on Windows , or None."""
    for seg in path.split("/"):
        if ":" in seg:
            return "dấu ':'"
        if WIN_RESERVED.match(seg):
            return "tên dành riêng của Windows (%s)" % seg
        if seg != seg.rstrip(". "):
            return "tên kết thúc bằng dấu chấm hoặc dấu cách"
    return None


# same shape rule as the engine (q-knowledgebase scripts/packs.py), so a pack the importer takes is never IGNORED there
def risky_repetition(pattern):
    r"""True when a group that repeats (+, *, {n,}, {n,m}) holds another repetition or an alternation, at any depth:
    "(a+)+", "((a+))*", "(a|aa)+", "(\w*x)*" - the shapes that backtrack catastrophically."""
    stack, i, n = [], 0, len(pattern)
    while i < n:
        c = pattern[i]
        if c == "\\":
            i += 2
            continue
        if c == "[":
            j = i + 1
            if j < n and pattern[j] == "^":
                j += 1
            if j < n and pattern[j] == "]":
                j += 1
            while j < n and pattern[j] != "]":
                j += 2 if pattern[j] == "\\" else 1
            i = j + 1
            continue
        if c == "(":
            stack.append(i)
        elif c == ")" and stack:
            start = stack.pop()
            following = pattern[i + 1:i + 12]
            repeats = following[:1] in ("+", "*") or re.match(r"\{\d*,\d*\}", following) is not None
            if repeats:
                inner = re.sub(r"\.", "", pattern[start + 1:i])
                inner = re.sub(r"\[[^\]]*\]", "x", inner)
                if re.search(r"[+*|]|\{\d*,\d*\}", inner):
                    return True
        i += 1
    return False


def vet_patterns(patterns):
    """regexes from an untrusted pack. Returns (ok list, problems list of (pattern, reason)).
    Refused: not a string, empty or longer than PATTERN_MAX, back-reference, does not compile, matches empty text,
    nested / alternated repetition (backtracking traps; same rule as the engine),
    or slow on a short adversarial input."""
    import time
    ok, bad = [], []
    for p in patterns or []:
        if not isinstance(p, str):
            bad.append((repr(p)[:60], "không phải chuỗi"))
            continue
        if not p or len(p) > PATTERN_MAX:
            bad.append((p[:60] + "…", "độ dài phải từ 1 đến %d ký tự" % PATTERN_MAX))
            continue
        if re.search(r"\\[1-9]|\\g<|\(\?P=|\(\?\(", p):
            bad.append((p, "có tham chiếu ngược (back-reference)"))
            continue
        try:
            rx = re.compile(p)
        except re.error:
            bad.append((p, "không biên dịch được"))
            continue
        if rx.match(""):
            bad.append((p, "khớp cả chuỗi rỗng"))
            continue
        if NESTED_QUANTIFIER.search(p) or risky_repetition(p):
            bad.append((p, "lượng từ lồng nhau (có thể treo máy)"))
            continue
        start = time.perf_counter()
        for probe in ("a" * 24 + "!", "1" * 24 + "x", "A-" * 12 + "#", " " * 24 + "\x00"):
            rx.search(probe)
        if time.perf_counter() - start > 0.05:
            bad.append((p, "chạy quá chậm trên chuỗi thử"))
            continue
        ok.append(p)
    return ok, bad


def read_pack(zip_path, allow_ext=()):
    """Open and check a pack zip; returns (zipfile, PACK dict). Raises Stop 2 on anything unsafe or inconsistent.
    The pack never decides its own safety rules: allowed extensions = DATA_EXT + what the importer passes (allow_ext)."""
    try:
        z = zipfile.ZipFile(zip_path)
    except (OSError, zipfile.BadZipFile):
        raise Stop(2, "LỖI: không mở được file gói: %s" % zip_path)
    names = z.namelist()
    if len(names) > MAX_FILES or sum(i.file_size for i in z.infolist()) > MAX_BYTES:
        raise Stop(2, "LỖI: gói quá lớn hoặc quá nhiều file.")
    for info in z.infolist():
        n = info.filename
        mode = (info.external_attr >> 16) & 0o170000
        if n.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", n) or "\\" in n or ".." in n.split("/") or mode == 0o120000:
            raise Stop(2, "LỖI: gói không an toàn (đường dẫn hoặc liên kết lạ): %s" % n)
        reason = unsafe_name(n.rstrip("/"))
        if reason:
            raise Stop(2, "LỖI: gói có tên file không an toàn trên Windows (%s): %s" % (reason, n))
        if n.endswith("/"):
            continue
        if not (n in PACK_ROOT_FILES or n.startswith("data/")):
            raise Stop(2, "LỖI: gói có file ngoài khuôn: %s" % n)
    if "PACK.json" not in names:
        raise Stop(2, "LỖI: gói thiếu PACK.json.")
    try:
        pack = json.loads(z.read("PACK.json").decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise Stop(2, "LỖI: PACK.json không đọc được.")
    if pack.get("format") != FORMAT or pack.get("format_version") != FORMAT_VERSION:
        raise Stop(2, "LỖI: không phải gói dữ liệu KB (hoặc khuôn mới hơn công cụ này).")
    project, sub = pack.get("project", ""), pack.get("sub", "")
    pack_name(project, sub or None)
    units = pack.get("units") or []
    for u in units:
        if not (u == project or u.startswith(project + "/")) or ".." in u.split("/"):
            raise Stop(2, "LỖI: PACK.json có phần nằm ngoài dự án: %s" % u)
    listed = {f["path"]: f for f in pack.get("files", [])}
    data_names = {n[5:] for n in names if n.startswith("data/") and not n.endswith("/")}
    if set(listed) != data_names:
        raise Stop(2, "LỖI: danh sách file trong gói khác PACK.json.")
    allowed = set(DATA_EXT) | {e.lower() for e in allow_ext}          # never from PACK.json 
    for path, f in listed.items():
        if os.path.splitext(path)[1].lower() not in allowed:
            raise Stop(2, "LỖI: đuôi file không được phép trong gói: %s. Chỉ nhận Markdown / ảnh; đuôi khác phải do "
                          "người nhập cho phép rõ bằng --allow-ext." % path)
        if not any(path == u or path.startswith(u + "/") for u in units):
            raise Stop(2, "LỖI: file nằm ngoài phần của gói: %s" % path)
        if sha256_bytes(z.read("data/" + path)) != f["sha256"]:
            raise Stop(2, "LỖI: file %s trong gói không đúng mã kiểm tra. Lấy lại gói gốc." % path)
    if digest_of(pack.get("files", [])) != pack.get("digest"):
        raise Stop(2, "LỖI: mã tổng (digest) của gói không khớp.")
    return z, pack


def local_changes(proj, files_before):
    """Files of an imported copy changed on this machine: (modified, missing, extra) kb-relative lists."""
    modified, missing = [], []
    for path, digest in files_before.items():
        full = proj.kb(path)
        if not os.path.isfile(full):
            missing.append(path)
        elif sha256_file(full) != digest:
            modified.append(path)
    return modified, missing


def merge_settings(proj, pack):
    """Merge the hook / skill keys of the pack into kb.config.json and return what was added (for remove).
    The engine reads glossary / history / ID / alias keys from .qkb/packs/ itself (contract), so
    .qkb/config.json is only created when missing (minimal, so the index can be built) and never edited."""
    project = pack["project"]
    to_repo = lambda p: proj.kb_root + "/" + project + "/" + p
    added = {"kb": {}, "qkb": {}}
    cfg_path = proj.cfg_path or os.path.join(proj.root, "kb.config.json")
    cfg = read_json(cfg_path, None)
    if cfg is None:
        cfg = {"kb_root": proj.kb_root, "version_file": proj.kb_root + "/VERSION", "project_scopes": {},
               "default_scope": "all", "languages": {"reply": "vi"}}
        added["kb"]["_created"] = True
    scopes = cfg.setdefault("project_scopes", {})
    for k, v in (pack.get("scopes") or {}).items():
        if k not in scopes:
            scopes[k] = v
            added["kb"].setdefault("project_scopes", []).append(k)
    for key, values in (("glossary_files", [to_repo(p) for p in pack.get("glossary_files") or []]),
                        ("issue_id_patterns", pack.get("issue_id_patterns") or [])):
        cur = cfg.setdefault(key, [])
        for v in values:
            if v not in cur:
                cur.append(v)
                added["kb"].setdefault(key, []).append(v)
    hooks = cfg.setdefault("hooks", {})
    for key in ("route_keywords", "route_id_patterns"):
        cur = hooks.setdefault(key, [])
        values = pack.get(key) or []
        for v in values if isinstance(values, list) else []:
            if v not in cur:
                cur.append(v)
                added["kb"].setdefault("hooks." + key, []).append(v)
    write_json(cfg_path, cfg)
    added["kb"]["_path"] = os.path.relpath(cfg_path, proj.root).replace("\\", "/")
    if read_json(proj.qcfg_path, None) is None:
        write_json(proj.qcfg_path, {"project_name": os.path.basename(proj.root), "knowledge_paths": [proj.kb_root],
                                    "source_paths": [], "project_roots": [proj.kb_root]})
        added["qkb"]["_created"] = True
    return added


def unmerge_settings(proj, added):
    cfg_path = proj.path(added.get("kb", {}).get("_path", "kb.config.json"))
    cfg = read_json(cfg_path, None)
    if cfg is not None:
        for k in added["kb"].get("project_scopes", []):
            (cfg.get("project_scopes") or {}).pop(k, None)
        for key in ("glossary_files", "issue_id_patterns"):
            cfg[key] = [v for v in cfg.get(key, []) if v not in added["kb"].get(key, [])]
        for key in ("route_keywords", "route_id_patterns"):
            h = cfg.get("hooks") or {}
            h[key] = [v for v in h.get(key, []) if v not in added["kb"].get("hooks." + key, [])]
        write_json(cfg_path, cfg)


def import_pack(args, out):
    proj = Project(args.root)
    allow_ext = {e if e.startswith(".") else "." + e for e in (args.allow_ext or "").split(",") if e.strip()}
    z, pack = read_pack(args.zip, allow_ext)
    name, units = pack["name"], pack["units"]
    # ID / route regexes from an untrusted pack: vetted, and merged only with --accept-patterns
    id_values = pack.get("id_patterns") if isinstance(pack.get("id_patterns"), dict) else {}
    patterns = [p for key in ("issue_id_patterns", "route_id_patterns") for p in (pack.get(key) or [])] \
        + [p for v in id_values.values() for p in (v if isinstance(v, list) else [v])]
    _, bad = vet_patterns(patterns)
    if bad:
        raise Stop(2, "LỖI: gói có mẫu tìm mã không an toàn, không nhập:\n" +
                   "\n".join("  - %s → %s" % (p, why) for p, why in bad))
    records = proj.records()
    engine = proj.engine_version()
    if engine and version_key(engine) and version_key(pack.get("engine_min")) and newer(pack["engine_min"], engine):
        raise Stop(2, "LỖI: gói cần engine %s trở lên; máy này có %s. Nâng bộ skill trước." % (pack["engine_min"], engine))
    for req in pack.get("requires") or []:
        have = [r for r in records.values() if r["pack"]["pack_id"] == req["pack_id"]]
        if not have or newer(req["min_version"], have[0]["pack"]["kb_version"]):
            raise Stop(2, "LỖI: gói cần gói %s v%s trở lên. Nhập gói đó trước." % (req["project"], req["min_version"]))
    rec = records.get(name)
    # owners of each unit among the other records (sub-project packs share shared/, rules/, README.md)
    owners = {u: [r for n, r in records.items() if n != name and u in r["pack"]["units"]] for u in units}
    state = "mới"
    if rec:
        if rec["pack"]["pack_id"] != pack["pack_id"]:
            raise Stop(2, "LỖI: đã có gói khác cùng tên %s (khác mã gói). Không nhập." % name)
        same = rec["pack"]["kb_version"] == pack["kb_version"] and rec["pack"]["digest"] == pack["digest"]
        if same:
            changed = sum(local_changes(proj, rec["state"]["files"]), [])
            if not changed:
                say(out, "ĐÃ CÓ: gói %s v%s đã nhập, không có gì mới." % (name, pack["kb_version"]))
                return 0, {"name": name, "state": "đã có"}
            # same pack over local edits: say so, and allow restoring it with --discard-local
            state = "khôi phục"
        elif not newer(pack["kb_version"], rec["pack"]["kb_version"]):
            raise Stop(2, "LỖI: gói v%s không mới hơn bản đã nhập v%s. Không hạ bản." % (pack["kb_version"], rec["pack"]["kb_version"]))
        else:
            state = "cập nhật"
    else:
        for u in units:
            if os.path.exists(proj.kb(u)) and not owners[u]:
                raise Stop(2, "LỖI: %s/%s đã có trên máy này và không phải bản nhập từ gói (dự án tự soạn). Không nhập."
                           % (proj.kb_root, u))
    # shared units owned by another pack: identical content -> keep; different -> conflict
    shared_keep = []
    new_files = {f["path"]: f["sha256"] for f in pack["files"]}
    for u, owner in owners.items():
        if not owner:
            continue
        theirs = {p: d for p, d in owner[0]["state"]["files"].items() if p == u or p.startswith(u + "/")}
        mine = {p: d for p, d in new_files.items() if p == u or p.startswith(u + "/")}
        if theirs == mine:
            shared_keep.append(u)
        else:
            raise Stop(1, "XUNG ĐỘT: phần chung %s/%s khác với bản của gói %s đã nhập. Nhập bản mới hơn của gói đó trước."
                       % (proj.kb_root, u, owner[0]["pack"]["name"]))
    modified, missing = local_changes(proj, {p: d for p, d in (rec["state"]["files"] if rec else {}).items()
                                              if not any(p == u or p.startswith(u + "/") for u in shared_keep)})
    say(out, "NHẬP GÓI DỮ LIỆU KB — %s v%s (%s)%s" % (name, pack["kb_version"], state, "" if args.apply else " — KẾ HOẠCH (chưa ghi gì)"))
    say(out, "1. File: %d · phần: %s" % (len(new_files), ", ".join(proj.kb_root + "/" + u for u in units)))
    if shared_keep:
        say(out, "2. Phần chung giữ nguyên (giống gói khác đã nhập): %s" % ", ".join(shared_keep))
    if modified or missing:
        say(out, "XUNG ĐỘT: %d file của bản đã nhập bị sửa, %d file bị xóa trên máy này:" % (len(modified), len(missing)))
        for p in (modified + missing)[:50]:
            say(out, "  - " + p)
        if not args.discard_local:
            say(out, "Chưa ghi gì. Muốn bỏ thay đổi tại chỗ (chuyển vào sao lưu) thì chạy lại kèm --discard-local.")
            return 1, {"name": name, "conflicts": modified + missing}
    if patterns:
        say(out, "3. Mẫu tìm mã trong gói (đã kiểm an toàn): %s" % ", ".join(patterns[:10]))
        if not args.accept_patterns:
            say(out, "CẦN DUYỆT: gói mang %d mẫu tìm mã sẽ được dùng trên máy này. Xem danh sách trên; đồng ý thì chạy lại "
                     "kèm --accept-patterns. Chưa ghi gì." % len(patterns))
            return 1, {"name": name, "patterns": patterns}
    if not args.apply:
        say(out, "Để nhập: chạy lại kèm --apply")
        return 0, {"name": name, "state": state}
    ts = stamp()
    backup = os.path.join(proj.root, ".qkb", "backups", "pack-%s-%s" % (name.replace("/", "__"), ts))
    work = os.path.join(proj.root, ".qkb", "tmp-pack-" + ts)
    moved = []
    try:
        for path in new_files:
            dst = os.path.join(work, *path.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            data = z.read("data/" + path)
            if sha256_bytes(data) != new_files[path]:
                raise OSError("sha256 " + path)
            with open(dst, "wb") as f:
                f.write(data)
        for u in units:
            if u in shared_keep:
                continue
            live, new = proj.kb(u), os.path.join(work, *u.split("/"))
            if os.path.exists(live):
                keep = os.path.join(backup, *u.split("/"))
                os.makedirs(os.path.dirname(keep), exist_ok=True)
                unlock(live)
                os.replace(live, keep)
                moved.append((live, keep))
            if os.path.exists(new):
                os.makedirs(os.path.dirname(live), exist_ok=True)
                os.replace(new, live)
                moved.append((None, live))
                set_readonly(live)
        if rec:
            unmerge_settings(proj, rec["state"]["merged"])
        added = merge_settings(proj, pack)
        recdir = proj.record_dir(name)
        write_json(os.path.join(recdir, "PACK.json"), pack)
        write_json(os.path.join(recdir, "state.json"), {"files": new_files, "units": units, "shared_kept": shared_keep,
                                                        "merged": added, "imported": ts, "backup": backup})
        with open(os.path.join(recdir, "CHANGELOG.md"), "wb") as f:
            f.write(z.read("CHANGELOG.md") if "CHANGELOG.md" in z.namelist() else b"")
    except (OSError, ValueError, KeyError):
        for src, dst in reversed(moved):
            try:
                if src is None:
                    unlock(dst)
                    shutil.rmtree(dst) if os.path.isdir(dst) else os.remove(dst)
                else:
                    os.replace(dst, src)
            except OSError:
                pass
        shutil.rmtree(work, ignore_errors=True)
        raise Stop(4, "LỖI khi nhập. Đã trả lại bản cũ của %s." % ", ".join(units))
    shutil.rmtree(work, ignore_errors=True)
    result = proj.run_qkb(["update"]) if os.path.isfile(os.path.join(proj.root, ".qkb", "cache", "index.sqlite3")) \
        else proj.run_qkb(["build"])
    links = proj.run_qkb(["verify", "--links"], timeout=300) or {}
    say(out, "ĐÃ NHẬP: %s v%s · %d file (chỉ đọc)%s" % (name, pack["kb_version"], len(new_files),
                                                       (" · bản cũ ở " + os.path.relpath(backup, proj.root)) if os.path.isdir(backup) else ""))
    if result is None:
        say(out, "Chỉ mục: chưa dựng (máy chưa có engine hoặc .qkb/config.json).")
    elif isinstance(links.get("links"), dict):
        say(out, "Chỉ mục đã cập nhật · liên kết hỏng (toàn chỉ mục): %s" % links["links"].get("broken"))
    return 0, {"name": name, "state": state}


# ----------------------------------------------------------------------------- verify / remove

def verify(args, out):
    proj = Project(args.root)
    records = proj.records()
    want = pack_name(args.project, args.sub) if args.project else None
    bad = 0
    if not records:
        say(out, "Chưa nhập gói nào.")
        return 0, {}
    for name, r in records.items():
        if want and name != want and not name.startswith(want + "/"):
            continue
        modified, missing = local_changes(proj, r["state"]["files"])
        extra = []
        for u in r["state"]["units"]:
            full = proj.kb(u)
            for folder, _, names in (os.walk(full) if os.path.isdir(full) else []):
                for n in names:
                    rel = os.path.relpath(os.path.join(folder, n), proj.kb()).replace("\\", "/")
                    if rel not in r["state"]["files"]:
                        extra.append(rel)
        ok = not (modified or missing or extra)
        bad += 0 if ok else 1
        say(out, "%s %s v%s: %s" % ("ĐẠT" if ok else "KHÁC", name, r["pack"]["kb_version"],
                                    "đúng như gói" if ok else "%d sửa · %d thiếu · %d thêm" % (len(modified), len(missing), len(extra))))
        for p in (modified + missing + extra)[:30]:
            say(out, "  - " + p)
    return (1 if bad else 0), {"changed_packs": bad}


def remove(args, out):
    proj = Project(args.root)
    name = pack_name(args.project, args.sub)
    records = proj.records()
    rec = records.get(name)
    if not rec:
        raise Stop(2, "LỖI: không có gói %s đã nhập trên máy này." % name)
    dependants = [n for n, r in records.items() if n != name and any(q["pack_id"] == rec["pack"]["pack_id"]
                                                                     for q in r["pack"].get("requires") or [])]
    if dependants:
        raise Stop(2, "LỖI: gói %s đang được gói khác cần tới: %s. Gỡ các gói đó trước." % (name, ", ".join(dependants)))
    still_used = [u for u in rec["state"]["units"] if any(u in r["pack"]["units"] for n, r in records.items() if n != name)]
    move = [u for u in rec["state"]["units"] if u not in still_used]
    say(out, "GỠ GÓI DỮ LIỆU KB — %s v%s%s" % (name, rec["pack"]["kb_version"], "" if args.apply else " — KẾ HOẠCH (chưa ghi gì)"))
    say(out, "1. Chuyển vào sao lưu (không xóa hẳn): %s" % (", ".join(proj.kb_root + "/" + u for u in move) or "—"))
    if still_used:
        say(out, "2. Giữ lại (gói khác còn dùng): %s" % ", ".join(still_used))
    say(out, "3. Bỏ các thiết lập đã ghép khi nhập; xóa bản ghi gói.")
    if not args.apply:
        say(out, "Để gỡ: chạy lại kèm --apply")
        return 0, {"name": name}
    backup = os.path.join(proj.root, ".qkb", "backups", "pack-removed-%s-%s" % (name.replace("/", "__"), stamp()))
    for u in move:
        live = proj.kb(u)
        if os.path.exists(live):
            keep = os.path.join(backup, *u.split("/"))
            os.makedirs(os.path.dirname(keep), exist_ok=True)
            unlock(live)
            os.replace(live, keep)
    parent = proj.kb(rec["pack"]["project"])
    if os.path.isdir(parent) and not os.listdir(parent):
        os.rmdir(parent)
    unmerge_settings(proj, rec["state"]["merged"])
    recdir = proj.record_dir(name)
    shutil.move(recdir, os.path.join(backup, "_record"))
    if os.path.isfile(os.path.join(proj.root, ".qkb", "cache", "index.sqlite3")):
        proj.run_qkb(["update"])
    say(out, "ĐÃ GỠ: %s. Bản sao lưu: %s (xóa hẳn là việc làm tay)." % (name, os.path.relpath(backup, proj.root)))
    return 0, {"name": name, "backup": backup}


def say(out, text):
    out.append(text)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gói dữ liệu KB: xuất, nhập, kiểm, gỡ.")
    ap.add_argument("--root", default=".", help="Thư mục gốc dự án (mặc định: thư mục hiện tại)")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    sub = ap.add_subparsers(dest="command", required=True)
    ex = sub.add_parser("export", help="Xuất 1 dự án hoặc 1 phần thành file zip (chỉ trên máy này)")
    ex.add_argument("--project", required=True)
    ex.add_argument("--sub")
    ex.add_argument("--requires", action="append", help="Dự án khác mà gói này cần (đã xuất trước), ví dụ common")
    ex.add_argument("--accept", help="Mã cảnh báo đã duyệt, ví dụ PERSONAL,OTHER_PROJECT")
    ex.add_argument("--include-ext", help="Thêm đuôi file ngoài Markdown / ảnh (cần duyệt riêng), ví dụ .xlsx")
    ex.add_argument("--title")
    ex.add_argument("--out", help="Thư mục ghi file gói (mặc định <thư mục quản lý>/exports)")
    ex.add_argument("--apply", action="store_true")
    im = sub.add_parser("import", help="Nhập hoặc cập nhật từ file gói")
    im.add_argument("zip")
    im.add_argument("--discard-local", action="store_true", help="Bỏ thay đổi tại chỗ (chuyển vào sao lưu) rồi thay")
    im.add_argument("--allow-ext", help="Cho phép thêm đuôi file ngoài Markdown / ảnh (người nhập quyết định), ví dụ .xlsx")
    im.add_argument("--accept-patterns", action="store_true", help="Đồng ý dùng các mẫu tìm mã (regex) mà gói mang theo")
    im.add_argument("--apply", action="store_true")
    ve = sub.add_parser("verify", help="Kiểm bản đã nhập có bị sửa không")
    ve.add_argument("--project")
    ve.add_argument("--sub")
    rm = sub.add_parser("remove", help="Gỡ 1 gói đã nhập (chuyển vào sao lưu)")
    rm.add_argument("--project", required=True)
    rm.add_argument("--sub")
    rm.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    out = []
    try:
        code, result = {"export": export, "import": import_pack, "verify": verify, "remove": remove}[args.command](args, out)
    except Stop as stop:
        code, result = stop.code, {"error": str(stop)}
        out.append(str(stop))
    if args.format == "json":
        result.update({"exit_code": code, "messages": out})
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=1) + "\n")
    else:
        (sys.stdout if code in (0, 1) else sys.stderr).write("\n".join(out) + "\n")
    return code


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
