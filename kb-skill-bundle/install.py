#!/usr/bin/env python3
"""Cài bộ skill KB vào một dự án (chỉ thư viện chuẩn, không dùng mạng, chỉ ghi trong thư mục đích).

Xem trước (mặc định, không ghi gì):
    python -E -s -B install.py --target <thư mục dự án>
Cài:
    python -E -s -B install.py --target <thư mục dự án> --apply --yes --model none [--project <dự án> --sub <phần>]
Gỡ / lùi lại:
    python -E -s -B install.py --target <thư mục dự án> --uninstall --apply --yes
    python -E -s -B install.py --target <thư mục dự án> --restore-previous --apply --yes

Mã thoát: 0 xong · 1 xung đột (chưa ghi gì) · 2 sai tham số / môi trường / gói lệch / bản đang cài mới hơn (chưa ghi gì)
          3 thiếu lựa chọn hoặc xác nhận (chưa ghi gì) · 4 lỗi khi ghi, đã lùi lại đủ · 5 lỗi, lùi lại chưa đủ
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import shutil
import sqlite3
import subprocess
import sys

sys.dont_write_bytecode = True
BUNDLE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BUNDLE, "tools"))
import settings_fragment  # noqa: E402

COMPONENTS = ("engine", "skills", "hooks", "scaffold")
COMPONENT_OF = {"engine": "engine", "skills": "skills", "manager-skills": "skills", "templates": "skills", "hooks": "hooks"}
QKB = ".claude/skills/q-knowledgebase/scripts/qkb.py"
QKB_CMD = "python -E -s -B " + QKB
READ_COMMANDS = ("status", "search", "query", "explore", "read", "related", "path", "impact", "map")
PERMISSIONS = ["Bash(%s %s *)" % (QKB_CMD, c) for c in READ_COMMANDS] + ["Bash(python -I -S .claude/hooks/kbscope.py *)"]
RECORD = ".qkb/install/installed.json"
INDEX = ".qkb/cache/index.sqlite3"
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

MODEL_TEXT = """CHỌN CÁCH TÌM KIẾM
[1] Không dùng model (mặc định, khuyên dùng)
    + Không tải, không cài thêm; chạy trên mọi máy; đúng chính sách công ty.
    + Nhanh; kết quả giải thích được và luôn giống nhau.
    + Tốt với số, mã, tên hàm, thuật ngữ chính xác.
    - Yếu khi câu hỏi diễn đạt khác hẳn tài liệu, hoặc dùng từ đồng nghĩa chưa có trong bảng thuật ngữ.
    - Hỏi khác ngôn ngữ của KB: phụ thuộc bảng thuật ngữ và các biến thể câu hỏi do Claude viết.
[2] Có model chạy trên máy (thử nghiệm)
    + Hiểu nghĩa: diễn đạt khác, đồng nghĩa, Việt ↔ Anh ↔ Nhật; ít phải chăm bảng thuật ngữ.
    - Phải tự tải 0,5–2,3 GB và phải được công ty cho phép.
    - Mỗi lần tìm nạp model 1–3 giây; dựng vector lần đầu vài phút tới khoảng 1 giờ; tốn RAM và đĩa.
    - Kết quả khó giải thích; yếu với số và mã.
    - Cần model đã tải (IT: tools/download-models) và 2 gói Python onnxruntime + numpy trên máy (IT cài).
Đổi lựa chọn bất cứ lúc nào: chạy lại install.py với --model none hoặc --model local (không cài lại KB, chỉ mục).
Bật model: dựng vector 1 lần (vài phút) vào file riêng bằng "qkb embed --apply"; tắt: về cách tìm thường ngay;
chỉ mục thường không bị đụng tới. Với model, mỗi lần tìm chậm thêm khoảng 1–3 giây (ước tính).
Chế độ dùng model (embedding.mode trong .qkb/config.json): auto (mặc định, chỉ khi câu hỏi cần) / on / off.
Chọn bằng: --model none   hoặc   --model local [--model-zip <file zip model>]"""

MODEL_README = """# Chỗ đặt model (thử nghiệm)

- Mỗi model 1 thư mục: `.qkb/models/<tên model>/` kèm `MODEL.txt` (sha256 từng file). Engine kiểm mã trước khi dùng.
- Gói không kèm và không tự tải model. Chỉ đặt model khi công ty cho phép tải và dùng.
- Cách đặt: IT chạy `tools/download-models` (`-Zip` ở máy có mạng, `-FromZip` ở máy dự án),
  hoặc `install.py --model local --model-zip <file zip>`.
- Máy cần 2 gói Python `onnxruntime` và `numpy` (IT cài); thiếu thì engine tự quay về cách tìm thường.
- Sau khi đặt: `python -E -s -B .claude/skills/q-knowledgebase/scripts/qkb.py embed --apply` (dựng vector 1 lần).
- Thư mục này không đưa lên kho mã (`.qkb/.gitignore` có `models/`).
"""


class Stop(Exception):
    def __init__(self, code, message):
        Exception.__init__(self, message)
        self.code = code


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def version_key(v):
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-([a-z]+)(\d+))?$", v or "")
    if not m:
        return None
    major, minor, patch, stage, num = m.groups()
    return (int(major), int(minor), int(patch), stage or "~", int(num or 0))   # "~" sorts after letters = final


def ask(prompt, missing):
    """Keyboard answer; no keyboard (EOF, e.g. NUL on Windows reports a tty) -> Stop 3 with the missing-choice text."""
    try:
        return input(prompt).strip()
    except EOFError:
        raise Stop(3, missing)


def say(out, text=""):
    out.append(text)


# ----------------------------------------------------------------------------- checks

def is_under(path, folder):
    """True when path is folder or inside it (different drives -> False)."""
    try:
        return os.path.commonpath([os.path.normcase(folder), os.path.normcase(path)]) == os.path.normcase(folder)
    except ValueError:
        return False


def check_target(target):
    if not os.path.isdir(target):
        raise Stop(2, "LỖI: không thấy thư mục đích: %s" % target)
    real = os.path.realpath(target)
    bundle = os.path.realpath(BUNDLE)
    # the bundle itself, any folder inside it, and the folder that directly holds a bundle are refused
    holds_bundle = bundle.startswith(real + os.sep) and os.path.isfile(os.path.join(real, "install.py")) \
        and os.path.isfile(os.path.join(real, "MANIFEST.json"))
    if is_under(real, bundle) or holds_bundle:
        raise Stop(2, "LỖI: thư mục đích là thư mục gói hoặc nằm trong thư mục gói. Chọn thư mục dự án.")
    return real


def inside(target, rel):
    """Absolute path of rel under target; refuse anything that leaves the target (also through links)."""
    full = os.path.normpath(os.path.join(target, *rel.split("/")))
    if os.path.commonpath([target, full]) != target:
        raise Stop(2, "LỖI: đường dẫn ra ngoài thư mục đích: %s" % rel)
    probe = full
    while probe != target:
        if os.path.islink(probe):
            raise Stop(2, "LỖI: đường dẫn đi qua liên kết: %s" % rel)
        probe = os.path.dirname(probe)
    return full


def check_env():
    if sys.version_info < (3, 10):
        raise Stop(2, "LỖI: cần Python 3.10 trở lên (đang có %d.%d)." % sys.version_info[:2])
    try:
        if os.environ.get("KBINSTALL_TEST_NO_FTS5") == "1":     # test seam for the install check (IC-02); never set in use
            raise sqlite3.OperationalError("no fts5 (simulated)")
        con = sqlite3.connect(":memory:")
        con.execute("CREATE VIRTUAL TABLE t USING fts5(x)")
        con.close()
    except sqlite3.Error:
        raise Stop(2, "LỖI: SQLite của Python này không có FTS5. Cài Python bản chính thức rồi chạy lại.")


def load_manifest():
    try:
        with open(os.path.join(BUNDLE, "MANIFEST.json"), encoding="utf-8") as f:
            manifest = json.load(f)
    except (OSError, ValueError):
        raise Stop(2, "LỖI: không đọc được MANIFEST.json của gói. Giải nén lại từ file zip gốc.")
    if manifest.get("product") != "KB-Skill-Bundle" or not isinstance(manifest.get("files"), list):
        raise Stop(2, "LỖI: MANIFEST.json không phải của bộ skill KB.")
    for entry in manifest["files"]:
        src = os.path.join(BUNDLE, *entry["path"].split("/"))
        if not os.path.isfile(src) or sha256(src) != entry["sha256"]:
            raise Stop(2, "LỖI: file %s trong gói không đúng mã kiểm tra. Giải nén lại từ file zip gốc." % entry["path"])
    return manifest


def load_known():
    try:
        with open(os.path.join(BUNDLE, "manifests", "known-engine.json"), encoding="utf-8") as f:
            return json.load(f).get("versions", {})
    except (OSError, ValueError):
        return {}


def read_json(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def installed_engine(target):
    core = os.path.join(target, ".claude", "skills", "q-knowledgebase", "scripts", "core.py")
    try:
        with open(core, encoding="utf-8") as f:
            m = re.search(r'^VERSION\s*=\s*"([^"]+)"', f.read(), re.M)   # read only; never run the target's code
        return m.group(1) if m else "không rõ"
    except OSError:
        return None


def index_schema(target):
    db = os.path.join(target, ".qkb", "cache", "index.sqlite3")
    if not os.path.isfile(db):
        return None
    try:
        con = sqlite3.connect(pathlib.Path(db).resolve().as_uri() + "?mode=ro", uri=True)   # safe for # and ? in paths
        try:
            row = con.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
        finally:
            con.close()
        return int(row[0]) if row else 1
    except (sqlite3.Error, ValueError):
        return 1


# ----------------------------------------------------------------------------- plan

def plan_files(target, manifest, components, manager, record, known, adopt):
    known_sha = {}
    for files in known.values():
        for dest, digest in files.items():
            known_sha.setdefault(dest, set()).add(digest)
    previous = {f["dest"]: f["sha256"] for f in (record or {}).get("files", [])}
    rows = []
    for entry in manifest["files"]:
        if entry["mode"] == "not-installed" or COMPONENT_OF.get(entry["component"]) not in components:
            continue
        dest = entry["dest"].replace("{manager}", manager)
        full = inside(target, dest)
        if not os.path.exists(full):
            action = "add"
        elif os.path.isdir(full):
            action = "conflict"
        else:
            current = sha256(full)
            if current == entry["sha256"]:
                action = "same"
            elif entry["mode"] == "create-only":
                action = "keep-existing"
            elif previous.get(dest) == current or current in known_sha.get(dest, ()):
                action = "replace"
            else:
                action = "replace" if adopt else "conflict"
        rows.append({"dest": dest, "src": entry["path"], "sha256": entry["sha256"], "component": entry["component"],
                     "action": action})
    return rows


def plan_settings(target):
    """(state, new settings dict or None, added blocks, added permissions, old-form commands rewritten).
    state: create | merge | same | broken."""
    path = os.path.join(target, ".claude", "settings.json")
    frag = settings_fragment.fragment()
    current = {}
    state = "create"
    if os.path.exists(path):
        try:
            current = read_json(path)
            if not isinstance(current, dict):
                raise ValueError
            state = "merge"
        except (OSError, ValueError):
            return "broken", None, frag, PERMISSIONS, 0
    # old-form KB hook commands (2.0.3 and older: exit 2 when the script is missing) -> safe form, other keys kept
    current, upgraded = settings_fragment.upgrade_commands(current)
    merged = settings_fragment.merge(current, frag)
    allow = merged.setdefault("permissions", {}).setdefault("allow", [])
    added_perms = [p for p in PERMISSIONS if p not in allow]
    allow.extend(added_perms)
    added_blocks = {ev: [b for b in blocks if b not in (current.get("hooks") or {}).get(ev, [])] for ev, blocks in frag.items()}
    added_blocks = {ev: b for ev, b in added_blocks.items() if b}
    if not preserved(current, merged):
        raise Stop(4, "LỖI: bản ghép .claude/settings.json làm mất nội dung đang có. Không ghi.")
    if state == "merge" and not added_blocks and not added_perms and not upgraded:
        state = "same"
    return state, merged, added_blocks, added_perms, upgraded


def preserved(old, new):
    """Every value of old is still in new (dicts by key, lists as an ordered prefix)."""
    if isinstance(old, dict):
        return isinstance(new, dict) and all(k in new and preserved(v, new[k]) for k, v in old.items())
    if isinstance(old, list):
        return isinstance(new, list) and len(new) >= len(old) and all(preserved(a, b) for a, b in zip(old, new))
    return old == new


# ----------------------------------------------------------------------------- main install

MODEL_ZIP_NAME = re.compile(r"^KB-Model_.+\.zip$", re.I)


def model_zip_places():
    """Where a model zip placed beside the bundle can be: the bundle folder, the folder that holds it
    (where the bundle zip was unpacked) and models/ in either."""
    parent = os.path.dirname(BUNDLE)
    return [BUNDLE, os.path.join(BUNDLE, "models"), parent, os.path.join(parent, "models")]


def find_model_zip(args, out):
    """KB-Model_*.zip beside the bundle. Exactly one valid zip -> its path (used as --model local
    --model-zip); none -> None (current behaviour); several valid -> Stop 2 with the list. --model none always wins."""
    if os.environ.get("KBINSTALL_TEST_NO_MODEL_SEARCH") == "1":    # test seam: tests that must not see zips beside the bundle
        return None
    seen, candidates = set(), []
    for folder in model_zip_places():
        try:
            names = sorted(os.listdir(folder))
        except OSError:
            continue
        for n in names:
            full = os.path.normcase(os.path.realpath(os.path.join(folder, n)))
            if MODEL_ZIP_NAME.match(n) and os.path.isfile(full) and full not in seen:
                seen.add(full)
                candidates.append(os.path.join(folder, n))
    if not candidates:
        return None
    if args.model == "none":
        for c in candidates:
            say(out, "Ghi chú: thấy file zip model %s nhưng đã chọn --model none, không dùng." % c)
        return None
    if os.path.join(BUNDLE, "tools") not in sys.path:
        sys.path.insert(0, os.path.join(BUNDLE, "tools"))
    import kbmodel
    valid = []
    for c in candidates:
        try:
            kbmodel.check_zip(c)
            valid.append(c)
        except kbmodel.Stop as stop:
            say(out, "Ghi chú: bỏ qua file zip model %s (%s)" % (c, str(stop).replace("LỖI: ", "")))
    if len(valid) > 1:
        raise Stop(2, "DỪNG: thấy %d file zip model hợp lệ cạnh bộ skill, không tự chọn:\n%s\n"
                      "Chỉ để lại 1 file, hoặc chạy lại kèm --model-zip <file> (hoặc --model none)."
                   % (len(valid), "\n".join("  - " + v for v in valid)))
    if valid:
        say(out, "Tìm thấy model: %s (đã kiểm an toàn zip + mã sha256 theo MODEL.txt) -> dùng như --model local --model-zip."
            % valid[0])
        return valid[0]
    return None


def choose(args, interactive, out):
    """Return (model, project, sub) or raise Stop 3 for a missing choice (apply only)."""
    model = args.model
    if model is None and args.apply:
        if interactive:
            print(MODEL_TEXT)
            answer = ask("Chọn 1 hoặc 2 [1]: ", "CẦN CHỌN: cách tìm kiếm. Chạy lại kèm --model none hoặc --model local.")
            model = "local" if answer == "2" else "none"
        else:
            raise Stop(3, MODEL_TEXT + "\nCẦN CHỌN: cách tìm kiếm. Chạy lại kèm --model none hoặc --model local.")
    return model


def run_qkb(target, args_list, timeout=600):
    flags = 0x08000000 if os.name == "nt" else 0
    r = subprocess.run([sys.executable, "-E", "-s", "-B", os.path.join(target, *QKB.split("/"))] + args_list + ["--format", "json"],
                       cwd=target, capture_output=True, timeout=timeout, creationflags=flags)
    text = r.stdout.decode("utf-8", "replace")
    try:
        data = json.loads(text) if text.strip() else {}
    except ValueError:
        data = {}
    return r.returncode, data


def install(args, out):
    target = check_target(os.path.abspath(args.target))
    check_env()
    manifest = load_manifest()
    known = load_known()
    for label, value in (("--manager-folder", args.manager_folder), ("--project", args.project), ("--sub", args.sub)):
        if value is not None and not NAME.match(value):
            raise Stop(2, "LỖI: %s chỉ được chứa chữ, số và . _ - (tối đa 64 ký tự): %r" % (label, value))
    reader = args.profile == "reader"
    default_components = ["engine", "skills", "hooks"] if reader else list(COMPONENTS)
    components = [c.strip() for c in args.components.split(",")] if args.components else default_components
    if any(c not in COMPONENTS for c in components):
        raise Stop(2, "LỖI: --components chỉ nhận: %s" % ", ".join(COMPONENTS))
    if reader and "scaffold" in components:
        raise Stop(2, "LỖI: dạng người đọc không dựng KB rỗng (bỏ scaffold khỏi --components).")
    manager = args.manager_folder
    record_path = os.path.join(target, *RECORD.split("/"))
    record = read_json(record_path) if os.path.isfile(record_path) else None
    engine_now = installed_engine(target)
    bundle_engine = manifest["engine_version"]
    if engine_now and engine_now != "không rõ" and version_key(engine_now) and version_key(bundle_engine) \
            and version_key(engine_now) > version_key(bundle_engine) and "engine" in components:
        raise Stop(2, "LỖI: engine đang cài (%s) mới hơn engine trong gói (%s). Không hạ bản." % (engine_now, bundle_engine))
    state = ("gói %s" % record.get("bundle_version")) if record else ("engine %s" % engine_now if engine_now else "chưa cài")
    has_kb = os.path.isdir(os.path.join(target, "kb"))
    scaffold = "scaffold" in components and not has_kb
    rows = plan_files(target, manifest, components, manager, record, known, args.adopt)
    if reader:   # reader = engine + read skills + hooks + kbpack; no KB-writing skills, no manager templates
        rows = [r for r in rows if r["component"] not in ("manager-skills", "templates")]
    settings_state, settings_new, added_blocks, added_perms, upgraded = plan_settings(target) if "hooks" in components \
        else ("skip", None, {}, [], 0)
    interactive = sys.stdin.isatty() and not args.yes
    found = None if args.model_zip else find_model_zip(args, out)     # model zip placed next to the bundle
    if found:
        args.model, args.model_zip = "local", found
    model = choose(args, interactive, out)
    model_name = None
    if args.model_zip:
        if model != "local":
            raise Stop(2, "LỖI: --model-zip chỉ dùng cùng --model local.")
        if os.path.join(BUNDLE, "tools") not in sys.path:
            sys.path.insert(0, os.path.join(BUNDLE, "tools"))
        import kbmodel
        try:
            model_name = kbmodel.check_zip(args.model_zip)[0]     # checked before anything is written
        except kbmodel.Stop as stop:
            raise Stop(2, str(stop))
    project, sub = args.project, args.sub or "main"
    if scaffold and args.apply and not project:
        if interactive:
            project = ask("Tên dự án cho KB rỗng (chữ, số, . _ -): ", "CẦN CHỌN: tên dự án cho KB rỗng. Chạy lại kèm --project <dự án> [--sub <phần>].")
            if not NAME.match(project or ""):
                raise Stop(2, "LỖI: tên dự án không hợp lệ.")
        else:
            raise Stop(3, "CẦN CHỌN: tên dự án cho KB rỗng. Chạy lại kèm --project <dự án> [--sub <phần>].")
    conflicts = [r for r in rows if r["action"] == "conflict"]
    counts = {}
    for r in rows:
        counts[r["action"]] = counts.get(r["action"], 0) + 1
    by_comp = {}
    for r in rows:
        if r["action"] == "add":
            by_comp[r["component"]] = by_comp.get(r["component"], 0) + 1
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_rel = ".qkb/backups/install-" + stamp
    mode_word = "KẾ HOẠCH CÀI (chưa ghi gì)" if not args.apply else "CÀI ĐẶT"
    say(out, "BỘ SKILL KB %s (engine %s) — %s" % (manifest.get("bundle_version"), bundle_engine, mode_word))
    say(out, "Đích: %s   ·   Hiện trạng: %s" % (target, state))
    say(out, "1. File sẽ thêm: %d      (%s)" % (counts.get("add", 0),
                                              " · ".join("%s %d" % (k, v) for k, v in sorted(by_comp.items())) or "—"))
    say(out, "2. File giữ nguyên: %d   ·   File sẽ thay: %d   ·   Xung đột: %d   ·   Giữ bản đang có: %d"
        % (counts.get("same", 0), counts.get("replace", 0), counts.get("conflict", 0), counts.get("keep-existing", 0)))
    if settings_state == "broken":
        say(out, "3. CHÚ Ý: .claude/settings.json không đọc được dạng JSON. Không sửa file này. Dán tay đoạn dưới đây.")
        say(out, json.dumps({"hooks": added_blocks, "permissions": {"allow": added_perms}}, ensure_ascii=False, indent=2))
    elif settings_state == "skip":
        say(out, "3. .claude/settings.json: không đổi (không cài hook)")
    else:
        say(out, "3. .claude/settings.json: %s %d khối hook (sau các khối đang có), thêm %d quyền chạy lệnh đọc; dòng bị xóa: 0"
            % ("tạo mới," if settings_state == "create" else "thêm", sum(len(b) for b in added_blocks.values()), len(added_perms)))
        if upgraded:
            say(out, "   + đổi %d lệnh hook KB dạng cũ sang dạng an toàn (thiếu script thì thoát 0); matcher / timeout giữ nguyên"
                % upgraded)
    for rel, items in untouched_legacy(target).items():
        say(out, "   ! %s: %d lệnh hook KB dạng cũ (%s) — thoát mã 2 khi thiếu script; installer không sửa file này, "
                 "thay tay bằng lệnh trong .claude/settings.json (README_VN.md § 9)"
            % (rel, len(items), ", ".join(sorted(set(e for e, _ in items)))))
    say(out, "4. KB rỗng: %s" % (("kb/%s/%s/, projects/%s/%s/, %s/" % (project or "<dự án>", sub, project or "<dự án>", sub, manager))
                                if scaffold else "không (đã có kb/ hoặc không chọn)"))
    say(out, "5. Lựa chọn: dạng cài = %s · model = %s · hook = %s · %s"
        % ("người đọc" if reader else "đầy đủ",
           ("trên máy, đặt từ zip: " + model_name) if model_name else {"none": "không", "local": "trên máy (thử nghiệm)", None: "chưa chọn"}[model],
           "quan sát (chỉ ghi log)" if args.hooks == "observe" else "tắt",
           "không có phiên quản lý (cấu hình: kb.config.json ở gốc dự án)" if reader
           else "phiên quản lý = %s (%s/)" % (args.session_name, manager)))
    say(out, "6. Sao lưu sẽ tạo: %s/" % backup_rel)
    say(out, "7. Log sử dụng của engine (.qkb/config.json \"usage_log\"): bật, ghi vào %s/ (kèm câu tìm, trên máy) "
             "nếu dự án chưa tự đặt; muốn tắt: đặt \"path\" rỗng." % USAGE_LOG_DEFAULT["path"])
    schema = index_schema(target)
    if schema == 1:
        say(out, "CHÚ Ý: chỉ mục đang ở schema 1. Xem trước: %s migrate --dry-run. Chạy lại kèm --migrate để nâng." % QKB_CMD)
    for name in ("Q-KnowledgeBase-README.md", "Q-KnowledgeBase-install.py", "Q-KnowledgeBase-VALIDATION.md"):
        if os.path.isfile(os.path.join(target, name)):
            say(out, "Ghi chú: %s là file của gói cũ ở gốc dự án; có thể xóa tay." % name)
    if conflicts:
        say(out, "DỪNG: %d file đang có khác với gói và không nhận ra nguồn gốc (danh sách dưới). Chưa ghi gì. "
                 "Xem lại, rồi chạy thêm --adopt nếu muốn thay (có sao lưu)." % len(conflicts))
        for r in conflicts:
            say(out, "  - " + r["dest"])
    result = {"target": target, "state": state, "engine_installed": engine_now, "engine_bundle": bundle_engine,
              "files": rows, "settings": settings_state, "scaffold": scaffold, "model": model, "conflicts": len(conflicts)}
    if conflicts:
        return 1, result
    if not args.apply:
        say(out, "Chi tiết từng file: thêm --format json")
        say(out, "Để cài: python -E -s -B install.py --target \"%s\" --apply --yes --model %s%s"
            % (target, model or "none", (" --project %s --sub %s" % (project or "<dự án>", sub)) if scaffold else ""))
        return 0, result
    if not args.yes:
        if not interactive or ask("Gõ CO để cài: ", "CẦN XÁC NHẬN: chạy lại kèm --apply --yes (không có bàn phím) hoặc gõ CO.").upper() != "CO":
            raise Stop(3, "CẦN XÁC NHẬN: chạy lại kèm --apply --yes (không có bàn phím) hoặc gõ CO.")
    return apply(target, manifest, rows, manager, record, settings_state, settings_new, added_blocks, added_perms,
                 scaffold, project, sub, model, schema, backup_rel, args, out, result)


def apply(target, manifest, rows, manager, record, settings_state, settings_new, added_blocks, added_perms,
          scaffold, project, sub, model, schema, backup_rel, args, out, result):
    backup = inside(target, backup_rel)
    created, restored_ok = [], True
    # step 10: backup (files to replace, settings, configs) + index backup with the OLD engine
    to_save = [r["dest"] for r in rows if r["action"] == "replace"]
    to_save += [".claude/settings.json", ".qkb/config.json", "kb.config.json", manager + "/kb.config.json"]
    saved = []
    try:
        for rel in to_save:
            src = inside(target, rel)
            if os.path.isfile(src):
                dst = os.path.join(backup, "files", *rel.split("/"))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                saved.append(rel)
        if schema is not None:
            # a consistent copy of the index (SQLite backup API) that rollback can put back
            src = inside(target, INDEX)
            dst = os.path.join(backup, "files", *INDEX.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            con_src = sqlite3.connect(pathlib.Path(src).resolve().as_uri() + "?mode=ro", uri=True)
            con_dst = sqlite3.connect(dst)
            try:
                con_src.backup(con_dst)
            finally:
                con_dst.close()
                con_src.close()
            saved.append(INDEX)
        if schema is not None and os.path.isfile(os.path.join(target, *QKB.split("/"))):
            code, data = run_qkb(target, ["backup"], timeout=600)
            if code != 0:
                raise OSError("qkb backup")
    except (OSError, sqlite3.Error, subprocess.SubprocessError):
        raise Stop(2, "LỖI: không tạo được bản sao lưu ở %s. Chưa ghi gì." % backup_rel)
    step = 11
    temps, new_dirs = [], []        # leftover temp files and new empty folders are removed on rollback
    try:
        # step 11: files (temp file + rename, sha256 check)
        for r in rows:
            if r["action"] not in ("add", "replace"):
                continue
            dst = inside(target, r["dest"])
            existed = os.path.exists(dst)
            make_dirs(os.path.dirname(dst), new_dirs)
            tmp = dst + ".kbtmp"
            temps.append(tmp)
            shutil.copyfile(os.path.join(BUNDLE, *r["src"].split("/")), tmp)
            os.replace(tmp, dst)
            temps.remove(tmp)
            if not existed:
                created.append(r["dest"])
            if sha256(dst) != r["sha256"]:
                raise OSError("sha256 " + r["dest"])
        # step 12: settings
        step = 12
        if settings_state in ("create", "merge"):
            path = inside(target, ".claude/settings.json")
            if settings_state == "create":
                created.append(".claude/settings.json")
            make_dirs(os.path.dirname(path), new_dirs)
            temps.append(path + ".kbtmp")
            with open(path + ".kbtmp", "w", encoding="utf-8", newline="\n") as f:
                json.dump(settings_new, f, ensure_ascii=False, indent=2)
                f.write("\n")
            os.replace(path + ".kbtmp", path)
            temps.remove(path + ".kbtmp")
        # step 13: scaffold + configs
        step = 13
        if scaffold:
            flags = 0x08000000 if os.name == "nt" else 0
            r = subprocess.run([sys.executable, "-E", "-s", "-B", os.path.join(BUNDLE, "scripts", "kb_scaffold.py"),
                                "--project", project, "--sub", sub, "--root", target, "--manager-folder", manager,
                                "--session-name", args.session_name], capture_output=True, timeout=120, creationflags=flags)
            if r.returncode != 0:
                raise OSError("kb_scaffold")
            created.extend(scaffold_items(r.stdout.decode("utf-8", "replace")))
        created.extend(write_configs(target, manager, model, args))
        # step 14: post-install checks with the NEW engine
        step = 14
        if schema is None:
            created.append(INDEX)          # a first build creates the index; rollback removes it
        checks = post_checks(target, schema, args, out) if os.path.isfile(os.path.join(target, *QKB.split("/"))) else {}
    except (OSError, subprocess.SubprocessError, Stop) as exc:
        restored_ok = rollback(target, backup, saved, created, temps, new_dirs)
        if restored_ok:
            raise Stop(4, "LỖI khi cài ở bước %d. Đã trả lại file, cấu hình%s từ %s/." % (
                step, " và chỉ mục" if INDEX in saved or schema is None else "", backup_rel))
        raise Stop(5, "LỖI khi cài ở bước %d và chưa trả lại đủ. Chép lại các file trong %s/files/ vào đúng chỗ."
                   % (step, backup_rel))
    # step 15: install record
    # The record is cumulative: a file the bundle installed earlier stays "add" / "replace" when it is "same" now,
    # and hook blocks / permissions added earlier stay listed, so uninstall still finds them after a re-run.
    before = {f["dest"]: f.get("action") for f in (record or {}).get("files", [])}
    files = []
    for r in rows:
        if r["action"] not in ("add", "replace", "same"):
            continue
        action = r["action"]
        if action == "same" and before.get(r["dest"]) in ("add", "replace"):
            action = before[r["dest"]]
        files.append({"dest": r["dest"], "sha256": r["sha256"], "action": action})
    old_settings = (record or {}).get("settings") or {}
    blocks = {ev: list(b) for ev, b in (old_settings.get("blocks") or {}).items()}
    if settings_new is not None:      # old-form blocks rewritten at this run are no longer in settings.json
        now = settings_new.get("hooks") or {}
        blocks = {ev: [x for x in b if x in now.get(ev, [])] for ev, b in blocks.items()}
        blocks = {ev: b for ev, b in blocks.items() if b}
    for ev, b in added_blocks.items():
        blocks.setdefault(ev, []).extend(x for x in b if x not in blocks[ev])
    perms = list(old_settings.get("permissions") or []) + [p for p in added_perms if p not in (old_settings.get("permissions") or [])]
    created = sorted(set(created) | set((record or {}).get("created") or []))
    record_new = {"bundle_version": manifest.get("bundle_version"), "engine_version": manifest.get("engine_version"),
                  "at": datetime.datetime.now().isoformat(timespec="seconds"), "files": files,
                  "created": created, "settings": {"blocks": blocks, "permissions": perms},
                  "options": {"manager_folder": manager, "session_name": args.session_name, "model": model,
                              "hooks": args.hooks, "project": project, "sub": sub, "profile": args.profile},
                  "backup": backup_rel,
                  "previous": record}
    # A re-run that wrote no package file and no settings keeps the earlier restore point, so --restore-previous still
    # returns to the state before the real install (not to the state of the re-run).
    changed = any(r["action"] in ("add", "replace") for r in rows) or settings_state in ("create", "merge")
    if record and not changed:
        record_new["backup"], record_new["previous"] = record.get("backup", backup_rel), record.get("previous")
    path = inside(target, RECORD)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(record_new, f, ensure_ascii=False, indent=1)
        f.write("\n")
    result.update({"applied": True, "backup": backup_rel, "checks": checks})
    say(out, "ĐÃ CÀI XONG. Việc cần làm:")
    say(out, "1. Khởi động lại phiên Claude Code (hook và skill mới có hiệu lực sau khi khởi động lại).")
    if args.profile == "reader":
        say(out, "2. Nhập gói dữ liệu KB nhận được: python -E -s -B .claude/tools/kbpack.py import <file.zip> --apply")
        say(out, "3. Tra cứu: /q-kb-search <câu hỏi>. Bản nhập là bản chỉ đọc; cập nhật bằng gói mới hơn.")
    else:
        say(out, "2. Tạo phiên quản lý KB: tên %s, thư mục làm việc %s/." % (args.session_name, manager))
        say(out, "3. Trong phiên đó gõ: /q-kb-publish --whoami")
    if scaffold:
        say(out, "4. Chép tài liệu gốc vào projects/%s/%s/docs/, code vào src/, rồi gõ: /q-kb-request sync %s/%s"
            % (project, sub, project, sub))
    say(out, "5. Hook đang ở chế độ %s. Muốn bật: sửa \"hooks.mode\" thành \"on\" trong kb.config.json (%s)."
        % ("quan sát (không hiện gì; log ở .qkb/local/observe/)" if args.hooks == "observe" else "tắt",
           "gốc dự án" if args.profile == "reader" else manager + "/"))
    if model == "local":
        say(out, "6. Model: cần onnxruntime + numpy trên máy (IT cài); dựng vector 1 lần: "
                 "python -E -s -B .claude/skills/q-knowledgebase/scripts/qkb.py embed --apply")
    say(out, "Lùi lại: python -E -s -B install.py --target \"%s\" --restore-previous --apply --yes" % target)
    return 0, result


def scaffold_items(text):
    return [line.strip()[2:].strip() for line in text.splitlines() if line.strip().startswith("- ")
            and not line.strip().startswith("- Chép") and "/" in line and " " not in line.strip()[2:].strip()]


def write_configs(target, manager, model, args):
    """Manager kb.config.json (create or set hooks.mode / search.model), .qkb/config.json when absent, model slot."""
    created = []
    reader = args.profile == "reader"
    # reader: no manager folder; the config sits at the project root (hooks and skills look there first)
    cfg_path = inside(target, "kb.config.json" if reader else manager + "/kb.config.json")
    if os.path.isfile(cfg_path):
        try:
            cfg = read_json(cfg_path)
        except ValueError:
            cfg = None
    else:
        cfg = read_json(os.path.join(BUNDLE, "templates", "kb.config.example.json"))
        cfg["manager"] = {"folder": manager, "session_name": args.session_name, "session_file": manager + "/session.json"}
        for key, folder in (("requests_folder", "requests"), ("locks_folder", "locks"), ("staging_folder", "staging")):
            cfg[key] = manager + "/" + folder
        if reader:
            cfg["_profile"] = "reader: KB projects come from data packs (.claude/tools/kbpack.py); requests are handed to the author"
        created.append(os.path.relpath(cfg_path, target).replace("\\", "/"))
    if isinstance(cfg, dict):
        cfg.setdefault("hooks", {})["mode"] = args.hooks
        cfg.setdefault("search", {})["model"] = model or "none"
        os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
        with open(cfg_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
            f.write("\n")
    for folder in (() if reader else ("requests", "locks", "staging")):
        path = inside(target, manager + "/" + folder)
        if not os.path.isdir(path):
            os.makedirs(path)
            created.append(manager + "/" + folder)
    readme = inside(target, manager + "/README.md")
    if not reader and not os.path.exists(readme):
        with open(os.path.join(BUNDLE, "templates", "manager", "README.md"), encoding="utf-8") as f:
            text = f.read().replace("{{MANAGER_FOLDER}}", manager).replace("{{SESSION_NAME}}", args.session_name)
        with open(readme, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        created.append(manager + "/README.md")
    qcfg = inside(target, ".qkb/config.json")
    if not os.path.exists(qcfg) and os.path.isdir(inside(target, "kb")):
        os.makedirs(os.path.dirname(qcfg), exist_ok=True)
        with open(qcfg, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"project_name": os.path.basename(target), "knowledge_paths": ["kb"], "source_paths": ["projects"],
                       "project_roots": ["kb", "projects"], "history_paths": ["kb/**/history/**"],
                       "exclude_patterns": [manager + "/**"], "issue_id_patterns": ["OPEN-\\d+", "OP-\\d+"]}, f, indent=2)
            f.write("\n")
        created.append(".qkb/config.json")
    if model == "local":
        doc = inside(target, ".qkb/models/DOC_TRUOC_VN.md")
        if not os.path.exists(doc):
            os.makedirs(os.path.dirname(doc), exist_ok=True)
            with open(doc, "w", encoding="utf-8", newline="\n") as f:
                f.write(MODEL_README)
            created.append(".qkb/models/DOC_TRUOC_VN.md")
    created.extend(set_embedding(target, model, args))
    set_usage_log(target)
    return created


USAGE_LOG_DEFAULT = {"path": "process-log/kb-usage", "query_text": True}


def set_usage_log(target):
    """v2.0.2 (owner: logs for 1-2 weeks of review): engine usage log on by default. Added only when .qkb/config.json has
    no "usage_log" key, so a project that set it (or turned it off with an empty path) keeps its choice.
    .qkb/config.json is in the install backup (step 10), so a rollback restores it."""
    path = inside(target, ".qkb/config.json")
    if not os.path.isfile(path):
        return False
    try:
        qcfg = read_json(path)
    except ValueError:
        return False
    if not isinstance(qcfg, dict) or "usage_log" in qcfg:
        return False
    qcfg["usage_log"] = dict(USAGE_LOG_DEFAULT)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(qcfg, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return True


def set_embedding(target, model, args):
    """Engine 2.1.0-e1 model search: --model local + a valid model folder -> embedding.backend onnx-local for it;
    --model none -> backend none. embedding.mode (auto / on / off) is never changed here."""
    if os.path.join(BUNDLE, "tools") not in sys.path:
        sys.path.insert(0, os.path.join(BUNDLE, "tools"))
    import kbmodel
    name, made = None, []
    if model == "local" and getattr(args, "model_zip", None):
        try:
            existed = os.path.isdir(inside(target, ".qkb/models/" + kbmodel.check_zip(args.model_zip)[0]))
            name = kbmodel.from_zip(args.model_zip, target, True, [])
            if not existed:
                made.append(".qkb/models/" + name)
        except kbmodel.Stop as stop:
            raise Stop(2, str(stop))
    elif model == "local":
        folder = inside(target, ".qkb/models")
        names = [n for n in sorted(os.listdir(folder)) if os.path.isdir(os.path.join(folder, n))] if os.path.isdir(folder) else []
        name = names[0] if len(names) == 1 else None
    qcfg_path = inside(target, ".qkb/config.json")
    if not os.path.isfile(qcfg_path):
        if not (model == "local" and name):
            return made
        os.makedirs(os.path.dirname(qcfg_path), exist_ok=True)       # reader machine before the first data pack
        qcfg = {"project_name": os.path.basename(target), "knowledge_paths": ["kb"], "source_paths": [], "project_roots": ["kb"]}
    else:
        try:
            qcfg = read_json(qcfg_path)
        except ValueError:
            return made
    emb = dict(qcfg.get("embedding") or {})
    if model == "local" and name and kbmodel.check_folder(target, name):
        emb.update({"backend": "onnx-local", "model": name})
    elif model == "none" and emb.get("backend", "none") != "none":
        emb["backend"] = "none"
    else:
        return made
    if not os.path.isfile(qcfg_path):
        made.append(".qkb/config.json")
    qcfg["embedding"] = emb
    with open(qcfg_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(qcfg, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return made


def post_checks(target, schema, args, out):
    checks = {}
    if os.environ.get("KBINSTALL_TEST_FAIL_STEP") == "14":     # test seam (rollback check); never set in use
        raise Stop(4, "simulated failure at step 14")
    code, data = run_qkb(target, ["doctor"], timeout=120)
    checks["doctor"] = code
    if code != 0:
        raise Stop(4, "doctor")
    if os.path.isfile(inside(target, ".qkb/config.json")):
        if schema == 1:
            if args.migrate:
                code, data = run_qkb(target, ["migrate"], timeout=3600)
                checks["migrate"] = code
                if code != 0:
                    raise Stop(4, "migrate")
            else:
                say(out, "CHÚ Ý: chỉ mục đang ở schema 1. Xem trước: %s migrate --dry-run. Chạy lại kèm --migrate để nâng." % QKB_CMD)
                return checks
        elif schema is None:
            code, data = run_qkb(target, ["build"], timeout=3600)
            checks["build"] = code
            if code not in (0, 1):
                raise Stop(4, "build")
        else:
            code, data = run_qkb(target, ["update"], timeout=3600)
            checks["update"] = code
            if code not in (0, 1):
                raise Stop(4, "update")
        code, data = run_qkb(target, ["verify", "--links"], timeout=600)
        broken = (data.get("links") or {}).get("broken")
        checks["broken_links"] = broken
        say(out, "Kiểm sau cài: doctor đạt · chỉ mục %s · liên kết hỏng: %s"
            % ("đã nâng" if checks.get("migrate") == 0 else "đã dựng" if "build" in checks else "đã cập nhật",
               "?" if broken is None else broken))
    return checks


def make_dirs(path, new_dirs):
    """os.makedirs that remembers every folder it created (deepest last)."""
    missing = []
    probe = path
    while probe and not os.path.isdir(probe):
        missing.append(probe)
        probe = os.path.dirname(probe)
    os.makedirs(path, exist_ok=True)
    new_dirs.extend(reversed(missing))


def rollback(target, backup, saved, created, temps=(), new_dirs=()):
    ok = True
    for tmp in temps:
        try:
            if os.path.isfile(tmp):
                os.remove(tmp)
        except OSError:
            ok = False
    for rel in reversed(created):
        path = os.path.join(target, *rel.split("/"))
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
        except OSError:
            ok = False
    for rel in saved:
        try:
            dst = os.path.join(target, *rel.split("/"))
            src = os.path.join(backup, "files", *rel.split("/"))
            # a file that still equals its backup needs no copy (a read-only target would fail the copy)
            if rel != INDEX and os.path.isfile(dst) and sha256(dst) == sha256(src):
                continue
            if rel == INDEX:
                for extra in ("-wal", "-shm"):     # stale journal files of the new engine must not replay
                    if os.path.isfile(dst + extra):
                        os.remove(dst + extra)
            shutil.copy2(os.path.join(backup, "files", *rel.split("/")), dst)
        except OSError:
            ok = False
    for folder in reversed(list(new_dirs)):          # only folders this run created, and only when empty
        try:
            if os.path.isdir(folder) and not os.listdir(folder):
                os.rmdir(folder)
        except OSError:
            pass
    return ok


# ----------------------------------------------------------------------------- uninstall / restore

HOOK_FILES = tuple(".claude/hooks/" + n for n in settings_fragment.HOOK_SCRIPTS + ("kbcommon.py",))
USER_SETTINGS_FILE = ".claude/settings.local.json"


def untouched_legacy(target):
    """{file: [(event, script)]} old-form KB hook commands in the settings file the installer never writes."""
    path = os.path.join(target, *USER_SETTINGS_FILE.split("/"))
    try:
        found = settings_fragment.legacy_entries(read_json(path)) if os.path.isfile(path) else []
    except (OSError, ValueError):
        found = []
    return {USER_SETTINGS_FILE: found} if found else {}


def plan_remove_settings(target, record, by_name):
    """What uninstall does to .claude/settings.json: (new settings or None, entries removed, groups removed,
    [(file, event, script)] old-form KB hook commands that stay after it)."""
    path = os.path.join(target, ".claude", "settings.json")
    left = [(USER_SETTINGS_FILE, ev, sc) for ev, sc in untouched_legacy(target).get(USER_SETTINGS_FILE, [])]
    if not os.path.isfile(path):
        return None, 0, 0, left
    try:
        data = read_json(path)
    except (OSError, ValueError):
        return None, 0, 0, left + [(".claude/settings.json", "?", "?")]
    if by_name:
        # every entry that calls a KB hook script, found by script name (an edited block, e.g. timeout, included)
        data, entries, groups = settings_fragment.strip_kb_hooks(data)
    else:
        hooks = data.get("hooks") or {}
        entries = groups = 0
        for event, blocks in (record.get("settings", {}).get("blocks") or {}).items():
            keep = [b for b in hooks.get(event, []) if b not in blocks]
            gone = [b for b in hooks.get(event, []) if b in blocks]
            groups += len(gone)
            entries += sum(len(b.get("hooks", [])) for b in gone if isinstance(b, dict))
            hooks[event] = keep
            if not hooks[event]:
                hooks.pop(event)
    left += [(".claude/settings.json", ev, sc) for ev, sc in settings_fragment.legacy_entries(data)]
    allow = (data.get("permissions") or {}).get("allow")
    if isinstance(allow, list):
        data["permissions"]["allow"] = [p for p in allow if p not in (record.get("settings", {}).get("permissions") or [])]
    return data, entries, groups, left


def remove_settings(target, plan):
    data = plan[0]
    if data is None:
        return False
    path = os.path.join(target, ".claude", "settings.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return True


def uninstall(args, out, restore):
    target = check_target(os.path.abspath(args.target))
    record_path = os.path.join(target, *RECORD.split("/"))
    if not os.path.isfile(record_path):
        folder = os.path.dirname(record_path)
        done = os.path.isdir(folder) and any(n.startswith("installed-uninstalled-") for n in os.listdir(folder))
        if done and not restore:      # a second uninstall is not an error
            say(out, "Không còn gì để gỡ: bộ skill KB đã được gỡ trước đó.")
            return 0, {"target": target, "remove": [], "keep": [], "restore": []}
        raise Stop(2, "LỖI: không thấy biên bản cài (%s). Không gỡ được tự động." % RECORD)
    record = read_json(record_path)
    remove, keep = [], []
    for f in record.get("files", []):
        if f.get("action") not in ("add", "replace") and not restore:
            continue
        path = os.path.join(target, *f["dest"].split("/"))
        if not os.path.isfile(path):
            continue
        (remove if sha256(path) == f["sha256"] else keep).append(f["dest"])
    backup = os.path.join(target, *record.get("backup", "").split("/"), "files")
    restore_files = []
    if restore and os.path.isdir(backup):
        for folder, _, names in os.walk(backup):
            for name in names:
                restore_files.append(os.path.relpath(os.path.join(folder, name), backup).replace("\\", "/"))
    if restore:
        remove = [r for r in remove if r not in restore_files and any(r == f["dest"] and f["action"] == "add"
                                                                     for f in record.get("files", []))]
    # hook entries: found by KB script name when the bundle installed its hook scripts; else (and for --restore-previous,
    # which puts the previous settings back) only the blocks listed in the record
    by_name = not restore and any(f["dest"] in HOOK_FILES for f in record.get("files", []))
    s_plan = None if (restore and ".claude/settings.json" in restore_files) else plan_remove_settings(target, record, by_name)
    left = s_plan[3] if s_plan else []
    held = []
    if left and not restore:
        # an old-form command still calls a KB hook script: deleting the scripts would make it exit 2 (blocks prompts)
        held = [r for r in remove if r in HOOK_FILES]
        remove = [r for r in remove if r not in held]
    title = "LÙI LẠI bản trước lần cài gần nhất" if restore else "GỠ BỘ SKILL KB"
    say(out, "%s — %s" % (title, "chưa ghi gì" if not (args.apply and args.yes) else "thực hiện"))
    say(out, "Đích: %s" % target)
    say(out, "1. File của gói sẽ xóa: %d" % len(remove))
    for r in remove:
        say(out, "  - " + r)
    if restore:
        say(out, "2. File chép lại từ %s: %d" % (record.get("backup"), len(restore_files)))
    else:
        if s_plan and s_plan[0] is not None:
            say(out, "2. .claude/settings.json: bỏ %d lệnh hook KB (%d khối) và %d quyền đã thêm"
                % (s_plan[1], s_plan[2], len(record.get("settings", {}).get("permissions") or [])))
        else:
            say(out, "2. .claude/settings.json: không đổi (không có, hoặc không đọc được dạng JSON)")
    for rel, ev, sc in left:
        say(out, "  ! %s: còn lệnh hook KB dạng cũ%s — thoát mã 2 khi thiếu script, có thể chặn prompt / tool"
            % (rel, "" if sc == "?" else " (%s, %s)" % (ev, sc)))
    for r in held:
        say(out, "  ! GIỮ %s: còn lệnh hook dạng cũ gọi script KB; sửa / xóa lệnh đó (README_VN.md § 9) rồi chạy gỡ lại" % r)
    if keep:
        say(out, "GIỮ LẠI %d file đã bị sửa sau khi cài (danh sách dưới)." % len(keep))
        for r in keep:
            say(out, "  - " + r)
    say(out, "Giữ nguyên: kb/, .qkb/ (chỉ mục, cấu hình, sao lưu, biên bản), thư mục quản lý, log quan sát.")
    result = {"target": target, "remove": remove, "keep": keep, "restore": restore_files, "held": held}
    if not (args.apply and args.yes):
        say(out, "Để thực hiện: chạy lại kèm --apply --yes")
        return 0, result
    for rel in remove:
        os.remove(os.path.join(target, *rel.split("/")))
    if restore:
        for rel in restore_files:
            dst = os.path.join(target, *rel.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(backup, *rel.split("/")), dst)
        if s_plan:
            remove_settings(target, s_plan)
        say(out, "Chỉ mục: nếu cần bản chỉ mục cũ, chép file sao lưu trong .qkb/backups/ về .qkb/cache/index.sqlite3, "
                 "hoặc chạy: %s build --full" % QKB_CMD)
        previous = record.get("previous")
        with open(record_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(previous or {"restored_from": record.get("backup")}, f, ensure_ascii=False, indent=1)
            f.write("\n")
    else:
        if s_plan:
            remove_settings(target, s_plan)
        os.replace(record_path, record_path.replace(".json", "-uninstalled-%s.json"
                                                    % datetime.datetime.now().strftime("%Y%m%d-%H%M%S")))
        if held:      # a small record of the held scripts, so a later uninstall removes them
            small = {"bundle_version": record.get("bundle_version"),
                     "files": [f for f in record.get("files", []) if f["dest"] in held], "created": [],
                     "settings": {"blocks": {}, "permissions": []}, "backup": record.get("backup", ""),
                     "held_for_old_hook_commands": True}
            with open(record_path, "w", encoding="utf-8", newline="\n") as f:
                json.dump(small, f, ensure_ascii=False, indent=1)
                f.write("\n")
            say(out, "Còn %d script hook KB giữ cho lệnh dạng cũ (biên bản: %s)." % (len(held), RECORD))
    say(out, "ĐÃ XONG. Khởi động lại phiên Claude Code.")
    return 0, result


def main(argv=None):
    ap = argparse.ArgumentParser(description="Cài, gỡ hoặc lùi lại bộ skill KB trong một dự án.")
    ap.add_argument("--target", required=True, help="Thư mục gốc dự án đích")
    ap.add_argument("--dry-run", action="store_true", help="Chỉ in kế hoạch (mặc định khi không có --apply)")
    ap.add_argument("--apply", action="store_true", help="Ghi thật")
    ap.add_argument("--yes", action="store_true", help="Không hỏi lại (cần khi chạy không có bàn phím)")
    ap.add_argument("--components", help="engine,skills,hooks,scaffold (mặc định: tất cả)")
    ap.add_argument("--project", help="Tên dự án cho KB rỗng")
    ap.add_argument("--sub", help="Tên phần cho KB rỗng (mặc định main)")
    ap.add_argument("--manager-folder", default="00_UpdateDocs", help="Thư mục phiên quản lý KB")
    ap.add_argument("--session-name", default="KB_UpdateDocs", help="Tên phiên quản lý KB")
    ap.add_argument("--model", choices=("none", "local"), help="none = không model (khuyên dùng); local = dùng model trên máy (thử nghiệm)")
    ap.add_argument("--model-zip", help="Với --model local: file zip model do tools/download-models -Zip tạo; kiểm rồi đặt vào .qkb/models/. Không cần khi đúng 1 file KB-Model_*.zip đặt cạnh bộ skill (tự nhận)")
    ap.add_argument("--hooks", choices=("observe", "off"), default="observe", help="Chế độ hook lúc cài")
    ap.add_argument("--profile", choices=("full", "reader"), default="full",
                    help="full = đầy đủ (máy soạn KB); reader = người đọc (engine, skill tra cứu, hook, kbpack; nhập KB từ gói)")
    ap.add_argument("--adopt", action="store_true", help="Cho thay file đang có mà gói không nhận ra (sau sao lưu)")
    ap.add_argument("--migrate", action="store_true", help="Cho nâng chỉ mục schema cũ")
    ap.add_argument("--uninstall", action="store_true", help="Gỡ theo biên bản cài")
    ap.add_argument("--restore-previous", action="store_true", help="Trả lại bản trước lần cài gần nhất")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    args = ap.parse_args(argv)
    if args.dry_run:
        args.apply = False
    out = []
    code, result = 0, {}
    try:
        if args.uninstall and args.restore_previous:
            raise Stop(2, "LỖI: chọn một trong --uninstall hoặc --restore-previous.")
        if args.uninstall or args.restore_previous:
            code, result = uninstall(args, out, args.restore_previous)
        else:
            code, result = install(args, out)
    except Stop as stop:
        code = stop.code
        out.append(str(stop))
        result = {"error": str(stop)}
    except KeyboardInterrupt:
        code = 3
        out.append("Đã dừng. Chưa ghi gì.")
    if args.format == "json":
        result["exit_code"] = code
        result["messages"] = out
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=1) + "\n")
    else:
        stream = sys.stdout if code in (0, 1) else sys.stderr
        stream.write("\n".join(out) + "\n")
    return code


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
