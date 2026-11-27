"""Tạo lại MANIFEST.json của gói (SHA-256 + kích thước mọi file, trừ chính MANIFEST.json và __pycache__).
Dùng: python tools/make_manifest.py <phiên bản>   (chạy trong thư mục gói)"""
import hashlib
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
version = sys.argv[1] if len(sys.argv) > 1 else "1.0"
files = {}
for p in sorted(root.rglob("*")):
    rel = p.relative_to(root).as_posix()
    if not p.is_file() or rel == "MANIFEST.json" or "__pycache__" in p.parts or p.suffix == ".pyc":
        continue
    data = p.read_bytes()
    files[rel] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
out = {"product": "writing-style-bundle", "version": version,
       "note": "install.py kiểm SHA-256 mọi file trong danh sách này trước khi cài", "files": files}
(root / "MANIFEST.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("%d file" % len(files))
