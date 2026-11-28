---
name: q-kb-update
description: "Chỉ có ở dạng cài solo (một người dùng, không có phiên quản lý KB riêng): một lệnh để ghi KB từ đầu tới cuối — nạp nguồn mới hoặc đã đổi, thêm thông tin, xử lý yêu cầu đang mở, rồi phát hành phiên bản mới. Keywords: cập nhật KB, nạp tài liệu, ghi nhớ, ナレッジ更新, update KB, ingest, publish."
argument-hint: "<dự án>/<phần> [nội dung cần thêm | file hoặc thư mục nguồn] | (trống = xử lý yêu cầu đang mở và nguồn mới)"
---

# KB update — solo profile, one command

For a project used by **one person**. There is no separate KB manager session: this session does the manager's work.
The safety steps stay: write to staging, review, publish with a new version, link gate, changelog.

## 0. Check the profile first

Read `kb.config.json` at the repository root, else `<manager folder>/kb.config.json`
(`.qkb/install/installed.json` → `options.manager_folder`; defaults `00_KB_Manager`, then `00_UpdateDocs`).

- `manager.solo` is not `true` → **stop**. This project has a KB manager session (`manager.session_name`). Tell the user
  (in `languages.reply`) that this project has its own KB manager session: send `/q-kb-request`, or open that session to write.
- Current directory is not the project root → stop and say so (paths in the steps are root-relative).
- A project with `.qkb/packs/<project>/PACK.json` came from a data pack: read-only, never written here.

## 1. Decide what to do (from the arguments)

| Argument | Work |
|---|---|
| `<project>/<sub>` only, or a source file / folder | **Ingest**: follow `../q-kb-ingest/SKILL.md` §§ 0–6 for that scope |
| `<project>/<sub>` + a fact, decision or verified result | **Add**: follow `../q-kb-add/SKILL.md` §§ 0–3 |
| nothing | Open requests in `requests_folder` (any prefix of `request_prefixes`, `Status: open`) grouped by target document; then new or changed sources of each project (ingest scan, § 2 of the ingest skill). Nothing to do → say `KB đã mới, không có gì cần cập nhật.` and stop |

One document at a time. Lock it in `locks_folder`, write only in `staging_folder`, as the two skills say.

## 2. Review

Check every staged file as in `<manager.folder>/README.md` § Procedure step 4: refs, policy, paths
(`../q-kb-ingest/references/kb-conventions.md`), conflicts with existing knowledge. Ask the user only for the `ask_first`
cases of `kb.config.json` (policy finding, conflict, deletion, very large change …).

## 3. Publish

Follow `../q-kb-publish/SKILL.md` "Publish steps" 1–12 for the files staged in this run. Skip `--whoami` and step 11
(no other session to notify). A failed link gate rolls back exactly as written there.

## 4. Report (in `languages.reply`, short list)

- New KB version · sources ingested / facts added · files published · requests closed
- Broken links before → after · open points and conflicts the user must decide (when any)

## When more people start using the KB

Solo has no single-writer barrier between sessions. Two sessions writing at once can overwrite each other. Then reinstall
with `--profile author`: the writing skills move to the manager folder and other sessions send `/q-kb-request`.
