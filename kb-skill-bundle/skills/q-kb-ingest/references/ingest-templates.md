# Ingest templates

Full page templates: `<manager.folder>/templates/pages/` (document.md, module.md, topic.md; copied there at install). Short form below.
Paths follow `kb-conventions.md` § 1 (repository-root-relative or page-relative).

**Document → `KB/docs/<ShortID>.md`** (≤ ~150 lines):

```markdown
# <ShortID> — <title>
- Source: `projects/<project>/<sub>/docs/<file>` · Rev/version · Date · Language · Pages · State: current
- Ref format: `(<ShortID> - <section>)` · Authority: <primary | reference only | as stated in notes.md>
## Scope            (2–4 lines)
## Section map      | § | Title | Page | Key content (1 line) |
## Key facts        - fact (<ShortID> - 3.2)
## Parameters       | Name | Value | Unit | Ref |
## Open points      - **<ISSUE-ID>** · Trạng thái: mở · Ảnh hưởng: … · Nguồn: …
```

**Module → `KB/code/<module>.md`** (≤ ~150 lines):

```markdown
# <module> — <one-line responsibility>
- Source: `projects/<project>/<sub>/src/<tree>/<path>/` · Files: N · Version / commit: … · State: current
- Alias: `SRC/` = `projects/<project>/<sub>/src/<tree>/`
## Responsibility
## Entry points     | Symbol | `SRC/file.cpp:line` | Role |
## Main flow        1. ... (`SRC/file.cpp:line`)
## Parameters / config keys / constants   | Name | Value/Default | `SRC/file.cpp:line` |
## Dependencies     calls → / called by ←
## Differences between source trees (if more than one)
## Open points
```

**Topic → `KB/topics/<topic>.md`**: cross-source synthesis; every statement cites its source; conflicts list all versions and the
priority rule from `notes.md` / the policy file — never pick silently.
