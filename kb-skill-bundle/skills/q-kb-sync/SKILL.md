---
name: q-kb-sync
description: "Tên cũ của /q-kb-ingest (đổi tên từ bản 2.1.0), giữ lại để lệnh cũ vẫn chạy. Chỉ dùng trong phiên quản lý KB: nạp nguồn gốc của một dự án vào KB. Lệnh mới: /q-kb-ingest."
argument-hint: "<dự án>/<phần> | <dự án> (phần chung) [tùy chọn: file hoặc thư mục để giới hạn]"
---

# KB sync (old name of KB ingest)

`q-kb-sync` was renamed `q-kb-ingest` in bundle 2.1.0. This skill only keeps the old command working.

1. Read `../q-kb-ingest/SKILL.md` and follow it exactly, with the arguments given to this command.
2. In the report, add one line (in `languages.reply`): `Lệnh /q-kb-sync đã đổi tên thành /q-kb-ingest; lệnh cũ vẫn dùng được.`

`../q-kb-ingest/SKILL.md` missing → stop and tell the user to reinstall the bundle; do not improvise the procedure.
