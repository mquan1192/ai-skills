# {{MANAGER_FOLDER}} — KB manager (single writer of the knowledge base)

Tóm tắt (cho người dùng):
- Chỉ phiên quản lý KB (`{{SESSION_NAME}}`) được sửa KB và tài liệu chung.
- Phiên khác gửi yêu cầu bằng `/q-kb-request`; yêu cầu nằm trong `requests/`.
- Phiên quản lý xử lý yêu cầu, viết bản nháp trong `staging/`, phát hành bằng `/q-kb-publish`.
- Lần đầu mở phiên quản lý: gõ `/q-kb-publish --whoami` để các phiên khác báo được tới phiên này.

Config: `kb.config.json` (this folder). Session ID of the manager: `session.json` (written by `/q-kb-publish --whoami`).

## What only the manager session may change

- Everything under `kb_root` (`VERSION`, `CHANGELOG.md`, project READMEs, policy / glossary files, knowledge bases).
- Shared files the project names in its own rules (agent instructions, skills, settings) — when the project uses this protocol for them.

Other sessions write **only** `requests/` (with `/q-kb-request`). Raw sources (`projects_root`) are added by the user.

## Folders

| Folder | Content | Who writes |
|---|---|---|
| `requests/` | One file per request: `<prefix>YYYYMMDD-HHMM-<topic>.md`, prefix = first entry of `request_prefixes` (default `REQ-`); files with any listed prefix are read | any session (`/q-kb-request`) |
| `locks/` | One file per document being updated: `<doc path with / replaced by __>.lock` | manager agents |
| `staging/` | Draft copies, same relative path as the target | manager agents |
| `.claude/skills/` | `q-kb-sync`, `q-kb-add`, `q-kb-publish` (only this session has them) | install script |

## Request file

```markdown
# REQ-YYYYMMDD-HHMM-<topic>
- Status: open | in-progress | done | rejected   (Type improvement: open | in-digest | chosen | rejected | parked)
- From: <session title> · <date time>
- Target: <project>/<sub> · <document(s) to change, if known>
- Type: add-fact | sync-sources | rule-change | glossary | template | improvement | other
- Issue IDs: <IDs, new, or —>
- Content: one line per fact / change, each with a source label:
  [USER] user, verbatim + date · [CODE] code path:line + version · [DOC] doc + § / page ·
  [INFER] inference: basis, confidence cao / vừa / thấp, who confirms (thấp is not sent)
  (old labels [U] [C] [D] [I] are accepted with the same meaning)
- Policy check: done by requester
- Result: <KB version + files changed>   ← filled by the manager
```

## Procedure (manager session)

1. **Collect** open requests; group by target document. One document = one work item.
2. **Lock**: before touching a document, write its lock file (agent, request IDs, start time). A locked document is never taken by
   another agent; a lock whose last line starts with `released` is free (overwrite it with the new lock line). Different documents
   may run in parallel (subagents).
3. **Work in staging**: copy the current file into `staging/` and edit only that copy (or write a new file there).
4. **Review** every staged file: refs, policy, paths (`q-kb-sync/references/kb-conventions.md`), conflicts with existing knowledge
   (conflict → ask the user, do not overwrite). A Content line without a source label goes back to the requester; every `[CODE]` ref is
   re-read; `[INFER]` only under "Open points" as `Suy luận (cao|vừa):`.
   Ask the user first **only** for the `ask_first` cases of `kb.config.json` (policy finding, conflict or reversed user decision,
   deletion or loosened rule, permissions or settings, unclear source or unknown requester, very large change).
5. **Publish** with `/q-kb-publish` (version, changelog, index, broken-link check, lock release, requests done).
   **Rule changes are batched**: changes to the project's rule files, `AGENTS.md`, skills, hooks and settings go live at most
   twice a day (fixed windows the project chooses, e.g. ~12:00 and ~17:30) or with the weekly retro change; an urgent or
   owner-approved (🔴) fix may go at once. Project KB content (`<kb_root>/<project>/…`) publishes as soon as it is ready.
   Time stamps (local time `HH:MM`, 24 h, no seconds; new lines only, no rewrite of old lines):
   - `CHANGELOG.md` entry: `(YYYY-MM-DD HH:MM, <manager session>, <request IDs>)`;
   - `notes.md` new heading: `## YYYY-MM-DD HH:MM — <topic>`;
   - `INDEX.md` "Last update" line: `YYYY-MM-DD HH:MM`.
6. **Notify** each requesting session.

Stale locks (older than one working day, no agent running) are reported to the user, not silently removed.

## Improvement ideas (Type `improvement`)

Rate (priority, needed / not needed / user's choice, cost, conflicts), collect into one daily digest, let the user choose.
An idea is never applied directly; a chosen idea becomes a normal `rule-change` request.

## Readers (all sessions)

- Read `version_file` first and note `KB v<version>` in task outputs — **not** in deliverables for readers outside the team:
  those give only the date and version (or commit) of the original source, never the KB version or KB paths.
- Search: `qkb query` / `/q-kb-search` first; `Grep` / `Glob` only inside one `<kb_root>/<project>/<sub>/`, never over all of
  `<kb_root>/`. The `kbguard` hook only reports a broad search (no block, no rights check).
- Topic with an open request or a lock here → note `🔸 KB đang cập nhật phần này` and use the published version.
