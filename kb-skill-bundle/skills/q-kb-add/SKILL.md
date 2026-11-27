---
name: q-kb-add
description: "Chỉ dùng trong phiên quản lý KB: thêm thông tin vào KB Markdown của dự án (lời người dùng, kết quả đã kiểm chứng, vấn đề có mã) khi xử lý yêu cầu. Phiên khác dùng /q-kb-request. Keywords: thêm KB, ナレッジ追加, add to KB."
argument-hint: "<dự án>/<phần> <nội dung | đường dẫn file>"
---

# KB add

> **Run only in the KB manager session.** Protocol: `<manager.folder>/README.md`: lock each target document in `locks_folder`,
> write to `staging_folder` (never the live file), publish with `q-kb-publish`. One document = one agent.
> **Imported projects are read-only.** A project with `.qkb/packs/<project>/PACK.json` (or `<project>__<sub>`) came from a
> data pack: do not write into it (no staging, no publish); tell the user it is updated only by a newer pack.

## 0. Config and target

- `kb.config.json` keys: `kb_root`, `locks_folder`, `staging_folder`, `policy_file`, `issue_id_patterns`, `confirmer_roles`.
- Target: `<kb_root>/<project>/<sub>/` or `<kb_root>/<project>/shared/` for facts of the whole project (IDs, naming, teams,
  policy decisions, templates → `shared/notes.md`).
- Read the target `INDEX.md`, `notes.md`, the default policy + `policy_file`, and `../q-kb-sync/references/kb-conventions.md`.

## 1. Input types

| Input | Where it goes | Ref written |
|---|---|---|
| Fact / decision stated by the user | `notes.md` (+ the related `code/`, `docs/`, `topics/` page) | `User (chat, YYYY-MM-DD)` |
| Verified task result | related `code/` / `topics/` pages; keep the original `path:line` / `(Doc - §)` refs | `Task <folder>, <file>` |
| Issue (request field "Issue IDs") | the owning page, one issue line (`kb-conventions.md` § 3); mentions elsewhere = ID only | the request's source |
| A new document or source folder | copying it is the user's job; then run `/q-kb-sync` for that one path | — |

## 2. Rules

1. Policy check first; 🚫 items are never written.
2. Record only what was said or verified. Inference → `Suy luận (cao|vừa):` under "Open points"; uncertain → `⚠️`.
3. `notes.md` entry (newest first): `- YYYY-MM-DD · <ref> · <fact> → <page updated>`.
4. Issue lines: `**<ID>** · Trạng thái: … · Ảnh hưởng: … · Nguồn: …`. Status change → edit the definition line in place and add
   a `notes.md` entry; never a second definition. ID missing (`new`) → assign the next free ID of the first pattern.
5. **Conflict** with existing knowledge: do not overwrite. Add `⚠️ Conflict:` next to the old statement with both sources and ask
   the user which wins. Source priority = the project's policy / `notes.md`; when none is written: provided documents > user
   statements > existing KB text — state it, do not decide silently.
6. Paths per `kb-conventions.md` § 1; superseded content → `historical` per § 2.
7. Keep files compact: update the existing line / section instead of appending duplicates. New page → add it to `INDEX.md`.

## 3. Report (to the user in `languages.reply`, short list)

- Đã thêm gì, ở đâu (file + mục) · Mã vấn đề mới / đổi trạng thái · Mâu thuẫn và câu hỏi cho người dùng.
