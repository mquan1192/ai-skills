#!/usr/bin/env python3
"""Đặt model (zip do tools/download-models.ps1 -Zip / .sh --zip tạo) vào chỗ đặt .qkb/models/<tên>/. Chỉ thư viện chuẩn.

    python -E -s -B tools/kbmodel.py from-zip <KB-Model_….zip> --target <dự án> [--apply]
    python -E -s -B tools/kbmodel.py check --target <dự án> [--model <tên>]

Zip hợp lệ: 1 thư mục gốc <tên>/ chứa MODEL.txt và chỉ file .onnx / .json; mỗi file có dòng "<đường dẫn>  sha256 <mã>"
trong MODEL.txt và đúng mã đó. Không đường dẫn tuyệt đối, không "..", không liên kết. Bản cũ (nếu có) chuyển vào
.qkb/backups/model-<tên>-<thời điểm>/. Mã thoát: 0 xong / chỉ in kế hoạch · 2 từ chối (zip không an toàn, sai mã, thiếu file).
"""
import argparse
import datetime
import hashlib
import os
import re
import shutil
import sys
import zipfile

sys.dont_write_bytecode = True
ALLOWED = (".onnx", ".json")
REQUIRED = ("tokenizer.json",)
MODEL_FILES = ("onnx/model.onnx", "model.onnx")
NOTE = "LICENSE_NOTE.txt"          # licence note beside MODEL.txt (plain text, never opened by the engine)
NOTE_MAX = 64 * 1024
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
LINE = re.compile(r"^\s*(\S+)\s+sha256\s+([0-9a-fA-F]{64})\s*$")
MAX_BYTES = 8 * 1024 * 1024 * 1024


class Stop(Exception):
    pass


def parse_model_txt(text):
    out = {}
    for line in text.splitlines():
        m = LINE.match(line)
        if m:
            out[m.group(1).replace("\\", "/")] = m.group(2).lower()
    return out


def check_zip(path):
    """(model name, {relative path: sha256}) of a safe model zip; raises Stop otherwise."""
    try:
        z = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile):
        raise Stop("LỖI: không mở được file zip model: %s" % path)
    with z:
        infos = [i for i in z.infolist() if not i.filename.endswith("/")]
        if not infos or sum(i.file_size for i in infos) > MAX_BYTES:
            raise Stop("LỖI: zip model rỗng hoặc quá lớn.")
        tops = set()
        for i in infos:
            n = i.filename
            mode = (i.external_attr >> 16) & 0o170000
            if n.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", n) or "\\" in n or ".." in n.split("/") or mode == 0o120000:
                raise Stop("LỖI: zip model không an toàn (đường dẫn hoặc liên kết lạ): %s" % n)
            if "/" not in n:
                raise Stop("LỖI: zip model phải có 1 thư mục gốc <tên model>/: %s" % n)
            tops.add(n.split("/", 1)[0])
        if len(tops) != 1:
            raise Stop("LỖI: zip model phải có đúng 1 thư mục gốc.")
        name = tops.pop()
        if not NAME.match(name):
            raise Stop("LỖI: tên model không hợp lệ: %r" % name)
        files = {i.filename.split("/", 1)[1]: i for i in infos}
        if "MODEL.txt" not in files:
            raise Stop("LỖI: zip model thiếu MODEL.txt.")
        record = parse_model_txt(z.read(files["MODEL.txt"]).decode("utf-8", "replace"))
        note = files.get(NOTE)
        if note is not None and note.file_size > NOTE_MAX:
            raise Stop("LỖI: %s trong zip model quá lớn." % NOTE)
        data_files = {p: i for p, i in files.items() if p not in ("MODEL.txt", NOTE)}
        for p in data_files:
            if os.path.splitext(p)[1].lower() not in ALLOWED:
                raise Stop("LỖI: zip model chỉ được có file .onnx / .json (gặp %s)." % p)
            if p not in record:
                raise Stop("LỖI: MODEL.txt không có mã sha256 cho %s." % p)
        missing = [p for p in REQUIRED if p not in data_files]
        if missing or not any(p in data_files for p in MODEL_FILES):
            raise Stop("LỖI: zip model thiếu file bắt buộc (onnx/model.onnx và tokenizer.json).")
        for p, info in data_files.items():
            h = hashlib.sha256()
            with z.open(info) as f:
                for block in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(block)
            if h.hexdigest() != record[p]:
                raise Stop("LỖI: sha256 của %s không khớp MODEL.txt. Không đặt model." % p)
        return name, {p: record[p] for p in data_files}


def from_zip(path, target, apply, out):
    """Check the zip, then (apply) unpack it into <target>/.qkb/models/<name>/. Returns the model name."""
    target = os.path.abspath(target)
    if not os.path.isdir(target):
        raise Stop("LỖI: không thấy thư mục dự án: %s" % target)
    name, files = check_zip(path)
    dest = os.path.join(target, ".qkb", "models", name)
    out.append("MODEL — %s%s" % (name, "" if apply else " — KẾ HOẠCH (chưa ghi gì)"))
    out.append("1. File: %d, đều đúng sha256 theo MODEL.txt" % len(files))
    for p, digest in sorted(files.items()):
        out.append("   - %s  %s" % (p, digest))
    out.append("2. Nơi đặt: %s" % dest)
    if not apply:
        out.append("Để đặt model: chạy lại kèm --apply")
        return name
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    work = os.path.join(target, ".qkb", "tmp-model-" + stamp)
    try:
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                if info.filename.endswith("/"):
                    continue
                rel = info.filename.split("/", 1)[1]
                dst = os.path.join(work, *rel.split("/"))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with z.open(info) as src, open(dst, "wb") as f:
                    shutil.copyfileobj(src, f, 1024 * 1024)
        if os.path.isdir(dest):
            keep = os.path.join(target, ".qkb", "backups", "model-%s-%s" % (name, stamp))
            os.makedirs(os.path.dirname(keep), exist_ok=True)
            os.replace(dest, keep)
            out.append("3. Bản cũ chuyển vào: %s" % os.path.relpath(keep, target))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        os.replace(work, dest)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    out.append("ĐÃ ĐẶT MODEL: %s (%d file)." % (name, len(files)))
    return name


def check_folder(target, name):
    """True when <target>/.qkb/models/<name>/ holds the required files and MODEL.txt hashes match."""
    folder = os.path.join(os.path.abspath(target), ".qkb", "models", name)
    try:
        with open(os.path.join(folder, "MODEL.txt"), encoding="utf-8") as f:
            record = parse_model_txt(f.read())
    except OSError:
        return False
    if "tokenizer.json" not in record or not any(p in record for p in MODEL_FILES):
        return False
    for p, digest in record.items():
        full = os.path.join(folder, *p.split("/"))
        if not os.path.isfile(full):
            return False
        h = hashlib.sha256()
        with open(full, "rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        if h.hexdigest() != digest:
            return False
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description="Đặt model vào chỗ đặt của dự án từ file zip model.")
    sub = ap.add_subparsers(dest="command", required=True)
    fz = sub.add_parser("from-zip")
    fz.add_argument("zip")
    fz.add_argument("--target", default=".")
    fz.add_argument("--apply", action="store_true")
    ck = sub.add_parser("check")
    ck.add_argument("--target", default=".")
    ck.add_argument("--model", default="multilingual-e5-small")
    args = ap.parse_args(argv)
    out = []
    try:
        if args.command == "from-zip":
            from_zip(args.zip, args.target, args.apply, out)
            code = 0
        else:
            ok = check_folder(args.target, args.model)
            out.append("MODEL %s: %s" % (args.model, "ĐẠT (đủ file, đúng sha256)" if ok else "CHƯA CÓ hoặc KHÔNG ĐẠT"))
            code = 0 if ok else 1
    except Stop as stop:
        out.append(str(stop))
        code = 2
    (sys.stdout if code == 0 else sys.stderr).write("\n".join(out) + "\n")
    return code


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
