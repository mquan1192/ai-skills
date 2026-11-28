---
name: q-kb-search
description: "Tra nhanh thông tin dự án chỉ từ KB đã phát hành: chỉ đọc, tra chỉ mục trước, ghi nguồn, không suy luận; mỗi kết quả ghi rõ thuộc dự án nào. Chọn phạm vi: /q-kb-search --project <phạm vi> <câu hỏi>. Keywords: tra cứu KB, tìm kiếm, 検索, 調べる, quick search, lookup."
argument-hint: "[--project <phạm vi> | --project all] <câu hỏi>"
allowed-tools: Read, Grep, Glob, Bash(python -E -s -B .claude/skills/q-knowledgebase/scripts/qkb.py status *), Bash(python -E -s -B .claude/skills/q-knowledgebase/scripts/qkb.py query *), Bash(python -E -s -B .claude/skills/q-knowledgebase/scripts/qkb.py search *), Bash(python -E -s -B .claude/skills/q-knowledgebase/scripts/qkb.py read *), Bash(python -E -s -B .claude/skills/q-knowledgebase/scripts/qkb.py related *), Bash(python -E -s -B .claude/skills/q-knowledgebase/scripts/qkb.py path *), Bash(python -E -s -B .claude/skills/q-knowledgebase/scripts/qkb.py impact *), Bash(python -E -s -B .claude/skills/q-knowledgebase/scripts/qkb.py explore *)
---

# KB quick search — read-only, any project

Four rules never change: **read only · index first · cite the source · no inference**.
Project rules (policy file, confidentiality) stay in force on top of this skill.

## 0. Config

Read once per session (re-read when the user changes it):
1. `kb.config.json` at the repository root, else `00_KB_Manager/kb.config.json`, else `00_UpdateDocs/kb.config.json` (default name up to 2.0.5), else defaults below.
2. Keys used: `kb_root` (default `kb`), `version_file` (`kb/VERSION`), `qkb_command`
   (`python -E -s -B .claude/skills/q-knowledgebase/scripts/qkb.py`), `project_scopes`, `default_scope` (`all`),
   `search.read_paths` (`["kb/"]`), `search.never_read` (`["projects/"]`), `requests_folder`, `locks_folder`,
   `glossary_files`, `policy_file`, `languages.reply` (`vi`).
3. No config and no `kb/` → answer `Chưa có KB trong thư mục này.` and stop.

## 1. Scope (which project to search)

Order: (1) `--project <scope>` in this call → use it and remember it for this conversation;
(2) `.qkb/local/scope.json` `{"scope": "<name>"}` when present (saved choice; this skill never writes it — the user saves it
with `python -I -S .claude/hooks/kbscope.py set <scope>`);
(3) `default_scope` of the config; (4) `all`.
- `<scope>` = a key of `project_scopes` (path prefixes) or a path prefix below `kb_root`; `all` = whole `kb_root`.
- Unknown scope → list the keys of `project_scopes` and ask once.
- Every answer ends with one scope line (user-facing, Vietnamese):
  `🔎 Phạm vi KB: <scope> (<đã lưu | lần này | mặc định>) · đổi: /q-kb-search --project <phạm vi | all>`

## 2. Read only

- Answer in chat only. Create, edit or delete no file (no task folder, memory, KB file, request file).
- Do not run the KB-writing skills; do not message the KB manager session.
- Gap, stale part or wrong-looking fact → say so (what, which KB file) and suggest sending `/q-kb-request` from a working session.
  If the user asks for an update here, remind them of this rule; act only if they explicitly override it.

## 3. Sources

- Allowed: files under `search.read_paths`; the `Status` / `Target` lines of request files and the names of lock files
  (only to warn about updates in progress).
- Not allowed: `search.never_read` (raw sources), task folders, staging, web, any other document. A file the user names outside
  the KB → say this skill reads only the KB and ask before opening it.
- Read `version_file` at the start of every answer; changed since the last answer → re-open KB files, do not rely on memory.
- Open request or lock covering the topic → `🔸 KB đang cập nhật phần này (<REQ-ID>)`; answer from the published version.

## 4. Lookup with the index first

From the repository root, `<qkb_command> <command>`:
1. `status` with `version_file`. State not `CURRENT` or no index → `🔸 chỉ mục KB chưa cập nhật`, use the fallback (step 6).
2. **Query variants** (the calling model replaces an embedding model): write at most **3** variants of the user's question, only
   from words of the question and of `glossary_files` / the KB's own term lists — never invent a term:
   (a) the question in Vietnamese with full diacritics; (b) the key terms in the KB content language (`languages.kb_content`,
   e.g. the EN / JA forms from the glossary); (c) a short keyword form (2–5 words). Drop a variant that equals another one.
3. **Run** `query "<variant>"` once per variant (at most 3 calls in this step), same scope for all:
   - all prefixes of the scope lie in **one** project folder (`<kb_root>/<p>/…`) → add `--project <p>`;
   - the prefixes span several folders (e.g. a project part plus `<kb_root>/common/`) or the scope is `all` → no `--project`.
   Merge the hits by section ID, keep the best rank of each, then keep only hits inside the scope prefixes and
   `search.read_paths` (drop raw-source hits). Older engine without `query` → `search "<variant>"` the same way.
   In the answer, name the variant that found each source (`tìm bởi: (a) | (b) | (c)`).
4. `read <SECTION_ID>` for the best 2–4 hits → answer from the read text and cite path + heading from that output.
5. `related` / `path` / `impact` only for "what depends on / what changes if" questions (KB nodes only).
6. Open a whole KB file (Read / Grep) only when a section is cut off, a full table is needed, two hits disagree, the index finds
   nothing, or a quote must be exact. `Grep` / `Glob` only inside **one** sub-folder `<kb_root>/<project>/<sub>/`, never over
   all of `<kb_root>/` or a whole project (hook `kbguard` reports a broad search; it never blocks and never checks rights). Fallback order: `<kb_root>/<project>/README.md` → `INDEX.md` files of the scope → only the
   needed knowledge files.
7. Never run `init`, `build`, `update`, `migrate`, `maintain`, `export`, `benchmark`, `semantic approve`.
- Possibly stale (`_sources.md` shows a source changed after its ingest date) → `🔸 KB có thể chưa cập nhật phần này`
  (do not open the raw source).
- Not in the KB → `KB v<version> chưa có thông tin này.` Name an original document only if a KB file points to it.

## 5. Answer (in `languages.reply`, default Vietnamese)

- Summary first; lists rather than paragraphs; one fact per bullet. Shape (drop empty parts):
  - **Kết luận:** ✅ / ❓ + 1–3 bullets
  - **Chi tiết:** facts from the KB only
  - **Thuật ngữ:** table of 3–8 key terms in the glossary languages (from `glossary_files`, in that order; missing → `—` +
    `(chưa có trong glossary)`)
  - **Nguồn tham chiếu:** list (§ 6)
  - last lines: `KB v<version>` + warnings, then the scope line (§ 1). A project imported from a data pack
    (`.qkb/packs/<project>/PACK.json`) shows its own version: `KB <project> v<kb_version of the pack>`.
- ✅ = stated in the KB · ❓ = KB marks conflict / to confirm, or two KB files disagree (show both with refs, do not choose).
  Icons have one meaning each: 🔸 = small risk, information only (stale index / page, update in progress) · ❓ = to check.
  Keep markers inside KB pages (`Suy luận:`, `⚠️ Conflict:`, `*`) as they are.
- **Deliverable for readers outside the team** (customer document, external mail): do not write `KB v<version>` or KB paths;
  give the date and version / commit of the original source the KB page names.
- **Project label**: every fact line names the project it comes from when the scope covers more than one project
  (e.g. `[<project>/<sub>]`). A fact from another project is for reference only — never copy it into that project's deliverables.

## 6. References

For each important fact: (1) KB file path + section heading; (2) the original document as the KB cites it (exact file name +
section / page if given; translate a foreign title in parentheses); (3) code `path:line` as written in the KB (do not open code);
(4) design documents and task outputs as the KB names them (folder / file / sheet); (5) user decisions with date + request ID as
in the KB. No section given → `KB không ghi mục`; never invent one.

## 7. No inference

Say only what the KB says: no combining facts into a new conclusion, no computed values, no general knowledge.
Unavoidable inference → its own line `Suy luận: …` + its basis, after the facts.
