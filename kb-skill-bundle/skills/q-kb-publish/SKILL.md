---
name: q-kb-publish
description: "Chỉ dùng trong phiên quản lý KB: phát hành thay đổi KB từ staging ra đường dẫn thật, tăng version, ghi changelog, cập nhật chỉ mục, kiểm liên kết hỏng, đóng yêu cầu, báo người gửi. /q-kb-publish --whoami: ghi ID phiên quản lý để phiên khác báo được. Keywords: phát hành KB, publish, 公開, release KB."
argument-hint: "[--whoami] [tùy chọn: mã yêu cầu cần phát hành; mặc định: mọi file staging đã duyệt]"
---

# KB publish

> **Run only in the KB manager session.** Protocol: `<manager.folder>/README.md`.
> **Solo profile** (`manager.solo` = true in `kb.config.json`): there is no separate manager session. The session opened
> at the project root is the manager, and the usual entry is `/q-kb-update`. Staging, locks and publish stay the same.
> **Imported projects are read-only.** A project with `.qkb/packs/<project>/PACK.json` (or `<project>__<sub>`) came from a
> data pack: do not write into it (no staging, no publish); tell the user it is updated only by a newer pack.

## 0. Config

`kb.config.json` keys: `manager.*`, `requests_folder`, `locks_folder`, `staging_folder`, `version_file`, `changelog_file`,
`qkb_command`, `ask_first`, `languages.reply`.

## `--whoami` (one time, after the manager session is created)

Solo profile: not needed (no other session rings this one). Say so and stop.

Write `manager.session_file` = `{"session_name": "<this session's title>", "session_id": "<this session's ID>",
"written_at": "<YYYY-MM-DD>"}`. Tell the user: `Đã ghi ID phiên quản lý KB vào <session_file>. Các phiên khác sẽ báo yêu cầu tới
phiên này.` Then stop.

## Publish steps

1. **List** staged files (`<staging_folder>/**`) with their lock and request IDs. Publish only files whose review is done.
2. **Check** each staged file: refs present, paths per `../q-kb-ingest/references/kb-conventions.md` § 1, no credentials / personal
   data / policy-file findings, no undecided `⚠️ Conflict:`. A failed check → stop and ask. Otherwise publish **without asking**,
   except the `ask_first` cases (policy finding, conflict or reversed user decision, deletion or loosened rule, permissions or
   settings, unclear source, very large change).
3. **Links before**: `<qkb_command> verify --links --format json` → note the broken-link count (`broken`) of the live KB.
   Older engine without `--links` → skip the link gate (steps 3, 6, 7), say so in the report.
4. **Save the live state** to `<staging_folder>/_rollback/<YYYYMMDD-HHMM>/`: a copy of every live file the batch will overwrite
   (same relative path) and a list `new-files.txt` of the batch files that have no live file yet. `version_file` and
   `changelog_file` are **not** touched before step 7.
5. **Copy** each staged file to its live path (same relative path from the repository root). The staged copy stays until the weekly
   sweep.
6. **Search index**: `<qkb_command> update`, then `status` (state `CURRENT`). When a source tree was switched (a new tree replaces
   an old one), first set `source_paths` in `.qkb/config.json`.
7. **Link gate**: `<qkb_command> verify --links --format json`.
   - Broken count **higher** than in step 3 → **roll back**: copy every saved file back from `_rollback/`, move each file of
     `new-files.txt` back into `<staging_folder>/` (same relative path), run `update` again, and confirm the broken count equals
     step 3. No version, no changelog entry, no release: list the new broken links (file, line, written path), tell the user, keep
     locks and requests open, fix in staging, then repeat from step 2.
   - Same or lower → continue.
8. **Version** `YYYY.MM.DD-NN` (NN = next publish number that day) → `version_file`; entries at the top of `changelog_file`:
   one line **per project** touched, each starting with its tag `[<project>]` or `[<project>/<sub>]`:
   `[<project>/<sub>] version · date time · files · request IDs · one-line summary` (data packs take each project's history
   from these tags).
9. **Index files**: update the `Last update:` line (version + date) of every `INDEX.md` whose folder changed, then `update` once
   more so the index holds these lines.
10. **Release**: append `released <YYYY-MM-DD HH:MM> <version>` to each published document's lock file (never delete a lock; a
   lock whose last line starts with `released` is free). Set each request `Status: done`, `Result: <version> + files`.
11. **Notify** each requesting session (solo profile: skip, the report of step 12 is enough): `REQ-… done — KB <version>: <files>`.
12. **Report** to the user (in `languages.reply`, short list): `Phiên bản`, `File đã phát hành`, `Yêu cầu đã đóng`,
    `Liên kết hỏng: <trước> → <sau>`, `Còn trong staging / còn khoá`.
    After a roll back: `Không phát hành: liên kết hỏng tăng <trước> → <sau>; đã khôi phục bản cũ.` + the new broken links.

The `_rollback/` folders are removed with the weekly sweep once the next publish succeeded.

**Weekly sweep** (once a week, one user confirm): remove released lock files and staged copies already published (live file
identical, or older than the latest publish of that path). Never remove a lock without a `released` line or a staged file that
differs from its live file.
