# KB conventions (shared by q-kb-sync, q-kb-add, q-kb-publish)

## 1. Paths (one convention, matches the index resolver)

The index resolves a written path in this order: (1) relative to the writing file, (2) from the repository root,
(3) from each parent folder up to the knowledge root, (4) from each configured source root, (5) a unique file name inside the
same project. Anything else is reported as a broken link by `qkb verify --links`.

Write every path so that rule (1) or (2) finds it.

**Project boundary** (data packs ship one project at a time): a page links only inside its own project or to a shared part
the project declares (e.g. `<kb_root>/common/`). A link to another project is reference only and is written as such
(`(tham khảo, dự án <other>)`); `kbpack.py export` lists every such link for the reviewer.

- **KB → KB**: relative to the page (`../topics/x.md`) or repository-root-relative (`kb/<project>/<sub>/topics/x.md`).
- **KB → raw document**: repository-root-relative: `projects/<project>/<sub>/docs/<file>`. Do not write a bare `docs/<file>`
  in new or touched lines (old lines are fixed when their page is touched, not in bulk).
- **KB → code**: `path:line` or `path:start-end` inside backticks, repository-root-relative
  (`projects/<project>/<sub>/src/<tree>/<path>`), or a short path declared once on the page:
  `` `SRC/` = `projects/<project>/<sub>/src/<tree>/` `` (folder alias, both end with `/`) or a file alias
  (`` `w.cpp` = `<full path>/worker.cpp` ``). Project-wide aliases go to `code_aliases` in `.qkb/config.json` (manager only).
- Several spans of one file: `` `a.cpp:10-12, 40-45` ``.
- No absolute paths, no drive letters, no `..` above the repository root.

## 2. Current vs historical

- Each source row in `_sources.md` and each page row in `INDEX.md` has a `State` column: `current` or
  `historical (YYYY-MM-DD, replaced by <path>)`.
- A superseded source keeps its page; the page gets a first line `> Historical since YYYY-MM-DD — replaced by <path>.`
  and moves to `<KB>/history/` when the project's `history_paths` covers that folder (history pages stay searchable and rank last).
- Never delete a page because its source was removed: mark it `(source removed YYYY-MM-DD)`.

## 3. Issue lines

IDs follow `issue_id_patterns` of `kb.config.json` (also set in `.qkb/config.json` so the index builds ISSUE nodes).
One definition per issue, as a list item or heading starting with the ID, in the page that owns it (usually `notes.md` § Open points
or the topic page):

```text
- **OPEN-012** · Trạng thái: mở · Ảnh hưởng: `projects/<p>/<sub>/src/<tree>/a.cpp:10-20`, `kb/<p>/<sub>/topics/x.md` · Nguồn: REQ-20260105-0930
```

- Field labels: `Trạng thái` / `Status`, `Ảnh hưởng` / `Affects`, `Nguồn` / `Source` (the index reads both languages).
- Status values: `mở`, `đang xử lý`, `đóng`, `bỏ` (or the project's own list in its policy file).
- Other pages mention the ID only (`OPEN-012`); do not repeat the definition.
- New open points use `OPEN-NNN` and continue the number sequence after the last `OP-NNN`; existing `OP-…` IDs are kept as they are (no bulk rename) and stay valid in references (`issue_id_patterns` lists both forms).
- New issue without an ID: next free number of the first pattern; existing ID conventions of a project are kept (no mass rename).

## 4. Markers

`✅` verified · `⚠️` conflict / to confirm · `Suy luận:` inference (only under "Open points" as `Suy luận (cao|vừa):`).
Source labels from requests (`[USER]`, `[CODE]`, `[DOC]`, `[INFER]`; old `[U]`, `[C]`, `[D]`, `[I]` mean the same) become refs: `User (chat, YYYY-MM-DD)`, `path:line`,
`(<ShortID> - §)`, `Task <folder>, <file>`.
