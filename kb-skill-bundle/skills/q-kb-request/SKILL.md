---
name: q-kb-request
description: "Gửi yêu cầu cho phiên quản lý KB cập nhật KB hoặc tài liệu chung (rule, glossary, template, skill) thay vì tự sửa. Dùng khi cần ghi nhớ thông tin dự án, KB đã cũ, hoặc có nguồn mới. Keywords: cập nhật KB, ghi nhớ, ナレッジ更新, update KB, remember."
argument-hint: "<dự án>/<phần> <nội dung cần thêm / sửa> | sync <dự án>/<phần>"
---

# KB request

Shared KB files are written only by the **KB manager session**. Do not edit them here.

## 0. Config

`kb.config.json` at the repository root, else `00_UpdateDocs/kb.config.json`. Keys used: `manager.folder`,
`manager.session_name`, `manager.session_file`, `requests_folder`, `policy_file`, `issue_id_patterns`, `confirmer_roles`,
`source_labels`, `languages.reply`. No config → defaults: folder `00_UpdateDocs`, requests `00_UpdateDocs/requests`,
manager name `KB_UpdateDocs`, policy = default rules only.

## 1. Policy check first

Default rules (always): no credentials (passwords, keys, tokens) → `[MASKED]`; no personal data; no content of one project copied
into another project's target. Then the rules of `policy_file` when set (it adds rules, never removes the default ones).
A 🚫 finding → do not write the request; tell the user what and where, without repeating the value.

## 2. Write the request

File `<requests_folder>/<prefix>YYYYMMDD-HHMM-<short-topic>.md`, `<prefix>` = first entry of `request_prefixes` in
`kb.config.json` (default list `REQ-`, `KB-REQ-`: new files use `REQ-`; when looking for open requests, read files with any listed prefix) (template: `<manager.folder>/README.md` § Request file, or the form
below):

```markdown
# REQ-YYYYMMDD-HHMM-<topic>
- Status: open
- From: <this session's title> · <date time>
- Target: <project>/<sub> · <documents, if known>
- Type: add-fact | sync-sources | rule-change | glossary | template | improvement | other
- Issue IDs: <IDs this request defines or changes, e.g. OPEN-012 (old form OP-012 still accepted); or —>
- Content:
  - [USER] ... | [CODE] ... | [DOC] ... | [INFER] ...
- Policy check: done by requester
- Result:
```

- Content = only facts the user stated or you verified, one per line, each with its source.
- **Source label on every Content line** (when `source_labels` is true, the default):
  - `[USER]` the user said it — verbatim quote + date; also say where the user's own turn is (e.g. "the owner's own turn, right
    after the lead's prepared question of HH:MM", plus the first words when they differ from a prepared template), so the KB
    manager can verify it in one call (it still verifies);
  - `[CODE]` code — `path:line` (repository-relative, or relative to a configured source root) + version / commit; you read it;
  - `[DOC]` document — document name + section / page;
  - `[INFER]` inference — its basis, confidence **cao / vừa / thấp**, who must confirm it (one of `confirmer_roles`).
  - `[INFER]` thấp → do not send; keep it in the task output. `[INFER]` cao / vừa → the KB keeps it only under "Open points" as
    `Suy luận (cao|vừa):`. It becomes a fact only when a later `[USER]` / `[CODE]` / `[DOC]` confirms it; that request names it.
  - Old short labels `[U]` `[C]` `[D]` `[I]` are still accepted with the same meaning (v2.0.3).
- **Issue IDs** ("Mã vấn đề"): when the content defines, closes or changes an issue, give its ID in the form of
  `issue_id_patterns` (new issue without an ID → write `new`; the manager assigns one). One line per issue in Content:
  `**<ID>** · Trạng thái: <mở | đóng | …> · Ảnh hưởng: <files / sections> · Nguồn: <ref>`.
- `sync <project>/<sub>` = new or changed raw sources → Type `sync-sources`, list the paths.
- Type `improvement` = an idea to change the workflow: problem seen, proposed change, expected gain, cost / risk. Never applied
  directly; the manager rates it and the user chooses.
- Send what your own session found (you hold the source context).

## 3. Ring the manager session

Read `manager.session_file` (`{"session_name", "session_id"}`); send a short message to that session ID (fallback: the session
titled `manager.session_name`; a `session_id` starting with `<` is not set yet → use the title): first line `KB request REQ-… : <topic>`, then the request path.
No session file or the session is not available → the request file alone is enough; say so.

## 4. Tell the user (in `languages.reply`, default Vietnamese)

Short list:
- `Đã gửi yêu cầu <REQ-ID>: <nội dung chính>.`
- `KB chỉ thay đổi sau khi phiên quản lý KB phát hành phiên bản mới.`
- `Chưa báo được phiên quản lý KB: yêu cầu nằm trong <requests_folder>.` (only when the ring failed)
Then continue the current task with the current KB version.
