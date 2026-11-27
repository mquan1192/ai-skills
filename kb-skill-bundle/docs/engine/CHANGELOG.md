# Q-KnowledgeBase

## 2.1.0-e3 — 2026-11-18 (tuned with the real model, not yet installed)

Measured with multilingual-e5-small on CPU: auto router default `min_coverage` 0.5 -> 0.6 (paraphrases reach
the model; number / code / name questions still never do), PascalCase identifiers (`MaxRetryCount`) count as exact
terms, passages embedded in token-length order (less padding; vectors returned in input order), one model load per
process (reloaded when a model file changes), numpy dot products when numpy is present (pure-Python fallback).
Optional usage log (`usage_log.path`, off by default): one JSON line per search / query / explore / related / impact
call (route, model used, latency, result count, top score, coverage, miss flag; question only with `query_text`; never
result text); write errors are ignored.

## 2.1.0-e2 — 2026-11-18 (pack trust + model hash fixes, not yet installed)

Pack-supplied ID patterns are checked like the importer (length, back-references, nested / alternated
repetition, compile, empty match) and pack paths must stay in the pack folder (glossaries Markdown) - otherwise the pack
is IGNORED with the reason; only `.md` files are indexed from a pack's data folder, whatever `text_formats` /
`source_paths` say. qkb-d `route_keywords` router-dict carry-over confirmed by test. `embed --apply`
always re-hashes the model files; searches only read the hash cache (stronger key) and never write it; no symlink /
junction anywhere below the model folder.

## 2.1.0-e1 — 2026-11-18 (optional local model search, off by default, not yet installed)

`embedding` settings (backend none | onnx-local), model folder `.qkb/models/<name>/` checked against MODEL.txt
(sha256, .onnx / .json only, CPUExecutionProvider only), pure-Python Unigram tokenizer, separate vector store with
model / tokenizer / profile identity, `qkb embed [--apply]` re-embedding changed sections only, router gate (natural
language + weak text match; never numbers, codes, paths, identifiers), RRF fusion, `--semantic auto|on|off`, text-search
fallback on any error. Search results add `semantic` and `coverage`; `status` adds `embedding`.

## 2.1.0-d2 — 2026-11-18 (data packs, not yet installed)

Imported KB data packs (`.qkb/packs/<project>/PACK.json`, written by kbpack.py): settings merged at configuration
load time with local values winning, per-pack version / changelog / state in `status` and `verify --links`, packs never
add source paths, KB -> code references of a pack whose source is not on the machine resolve to
`SOURCE_NOT_ON_MACHINE` (no edge). Unusable packs are ignored with a reason. `init` writes only the local settings.

## 2.1.0-d1 — 2026-11-18 (Vietnamese + number search, not yet installed)

NFC and one tone-mark position for accented matching; accent-free queries find accented text and accented words as
written rank first; Vietnamese question words dropped and routed; 2-3 word phrase bonus; canonical number / date /
version / percent / unit tokens at index (trigram rows) and query time with number-first ranking; extended generic
EN / JA / VI word list; `languages.kb_content`; `--project` takes a comma list or a path below a project root;
`status --quick` without a folder walk. Earlier review fixes carried over. Index schema unchanged (2); the trigram
table is refilled once on the first update.

## 2.1.0-c1 — 2026-11-17 (Phase C1 + E, not yet installed)

Parser interface (one module per language: Python AST FULL, C / C++ / Qt standard-library PARTIAL with the
`#include "..."` graph and declaration candidates, JS / TS FILE_ONLY; no call graph, no inferred relation). KB -> code
references from backticks with optional line spans, configured / page aliases (chained), stale and out-of-range line
checks; `impact` on a code file lists the citing KB sections and the issues that affect it. Issue / ID links from
declared patterns: ISSUE / IDENTIFIER nodes, AFFECTS and MENTIONS edges, undefined IDs reported. `verify --links`
adds code / includes / issues / parsers; `status` adds parser coverage. Writer-lock stale take-over made atomic.
New config keys default to empty; index schema unchanged (2).

## 2.1.0-b1 — 2026-11-17 (Phase B, not yet installed)

Search: FTS5 trigram table on accent-folded text (replaces the substring scan), query analysis with
per-language stop words and a glossary bridge (project glossary files + generic EN / JA / VI word list),
rank fusion of word FTS, trigram FTS and exact evidence (`"ranking": "classic"` keeps the 2.1.0-b0
scoring). New `query` command with deterministic routing and a stated reason; `read --expand`; merged
duplicate sections; structure chunking (tables / code blocks kept whole, table header repeated);
JSON / YAML / TOML / TXT as text by top-level key (opt-in `text_formats`); read-only SQLite for
read-only commands, writer lock file, `status --quick`, `maintain prune-history`. Fixes of the B0 review:
no edge for AMBIGUOUS names, `migrate` refuses unknown or newer schemas, unique-name resolution never
crosses projects. Install / offline tests build a fixture root instead of copying the parent folder.
Index schema unchanged (2); commands, options, JSON keys and exit codes of 2.1.0-b0 unchanged.

## 2.1.0-b0 — 2026-11-17 (Phase B0, not yet installed)

Ordered reference resolver (relative, repository root, each ancestor up to the knowledge root, source
roots, unique file name inside the project; AMBIGUOUS / OUTSIDE_INDEX are reported, never guessed);
non-path strings skipped; `history_paths` (searchable, ranked last, no edges); `project_roots` and
`--project` for search / explore / map / related / impact with a `project` field on every result;
`verify --links`; index schema 2 with `migrate [--dry-run]` (backup, keep proposals / reviews / history,
rebuild, verify, automatic rollback on failure); benchmark P50 / P95 / precision@5 and question
categories. Commands, options, JSON keys and exit codes of 2.0.0 unchanged.

## 2.0.0 — 2026-11-11

Initial independently implemented offline distribution. Markdown section indexing,
SQLite FTS5/local fallback, exact source provenance, deterministic directed graph,
incremental reconciliation, explicit semantic review workflow, compact explore,
bounded exports/offline viewer, consistent SQLite backup and labeled fixture tests.
No reliance on installed CodeGraph/Graphify.
