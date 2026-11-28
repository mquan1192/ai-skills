---
name: q-kb-ingest
description: "Chỉ dùng trong phiên quản lý KB: tạo hoặc làm mới KB Markdown của một dự án từ nguồn gốc (chỉ nguồn mới hoặc đã đổi), cập nhật INDEX.md và _sources.md. Phiên khác dùng /q-kb-request. Tên cũ: /q-kb-sync. Keywords: nạp nguồn, đồng bộ KB, ナレッジ取込, ナレッジ同期, ingest, sync KB."
argument-hint: "<dự án>/<phần> | <dự án> (phần chung) [tùy chọn: file hoặc thư mục để giới hạn]"
---

# KB ingest

Named `q-kb-sync` up to bundle 2.0.5; `/q-kb-sync` still works and points here.

> **Run only in the KB manager session** (`manager.session_name` of `kb.config.json`). Protocol: `<manager.folder>/README.md`:
> lock each target document in `locks_folder`, write to `staging_folder` (never the live file), publish with `q-kb-publish`.
> One document = one agent.
> **Solo profile** (`manager.solo` = true in `kb.config.json`): there is no separate manager session. The session opened
> at the project root is the manager, and the usual entry is `/q-kb-update`. Staging, locks and publish stay the same.
> **Imported projects are read-only.** A project with `.qkb/packs/<project>/PACK.json` (or `<project>__<sub>`) came from a
> data pack: do not write into it (no staging, no publish); tell the user it is updated only by a newer pack.

## 0. Config and paths

- `kb.config.json` in the manager folder (or the repository root). Keys: `kb_root`, `projects_root`, `locks_folder`,
  `staging_folder`, `policy_file`, `glossary_files`, `languages.kb_content` (default `en`), `issue_id_patterns`.
- Sources: `<projects_root>/<project>/<sub>/docs/`, `src/`. Target: `<kb_root>/<project>/<sub>/` (via
  `<staging_folder>/<kb_root>/<project>/<sub>/`). `<project>` alone → `<kb_root>/<project>/shared/` (sources given by the user).
- Below, `KB/` = the target folder. Conventions for paths, current / historical, issue lines: `references/kb-conventions.md`
  (read it before the first write of a session).

## 1. Read first

1. Default policy (no credentials, no personal data, no cross-project copy) + `policy_file` when set.
2. `KB/INDEX.md`, `KB/_sources.md`, `KB/notes.md` (source priority and decisions the user already gave).

## 2. Scan (no content reading yet)

- `docs/`: one row per file (path, size, modified date). `src/`: one row per source tree and per module folder (path, file count,
  total size, newest modified date).
- Compare with `_sources.md` → **new**, **changed**, **removed**, **unchanged**. Unchanged sources are not read again.
- A newer version of a document or tree replaces an older one → the old one becomes `historical` (`kb-conventions.md` § 2).
- More than ~10 documents or ~20 modules new / changed → show the list and planned order, ask before continuing.
  Large repos may be split across subagents (one module group each, same templates, checked by you before writing).

## 3. Policy check (before and while reading)

- Skip and report: personal data, credentials (never copy; `[MASKED]` + `path:line` in the report), anything the policy file
  marks as forbidden.
- Skip: binaries, build output, generated files, UI-only images, `.git/`.
- Third-party code or data the policy file names → ask before extracting knowledge.

## 4. Ingest

- Write in `languages.kb_content`; keep official terms, UI strings, IDs and original-language terms unchanged. Facts only,
  each with a ref. Markers per `kb-conventions.md` § 4. Never invent.
- Page templates: `references/ingest-templates.md` (read before the first file of a kind).
- Paths: `kb-conventions.md` § 1 — repository-root-relative or page-relative; code refs `path:line` or a declared alias.
- Open points: one issue line per point (`kb-conventions.md` § 3) when `issue_id_patterns` is set; else a plain `⚠️` bullet.
- Topics (`KB/topics/<topic>.md`): cross-source synthesis; conflicts list all versions + the priority rule; never pick silently.
- New terms: do not edit the glossary; list proposed entries in the report.

## 5. Index files

- `INDEX.md`: one row per knowledge file (file, source, version / date, State, ≤ 15-word content); update "Last sync".
- `_sources.md`: path, size, modified, ingested date, knowledge files, State, policy-check result.
- Removed sources: mark their pages `(source removed YYYY-MM-DD)`; do not delete.

## 6. Report (to the user in `languages.reply`, short list)

- Nguồn đã đọc (mới / đổi / bỏ qua + lý do) · File KB tạo / cập nhật · Phát hiện chính sách 🚫 / ⚠️ ·
  Mâu thuẫn và điểm mở (mã vấn đề) · Thuật ngữ đề xuất · Tài liệu chuyển sang `historical`.
