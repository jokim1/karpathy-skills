# LLM Wiki Principles Adoption Plan

## Summary

This plan turns the LLM-WIKI audit into a concrete next-pass roadmap for
`/karpathy:wiki`. The goal is not to replace the existing roadmap. It is to add
a decision-complete implementation plan for the gaps found in the audit:
external raw-source immutability, one-source compilation, index-first
navigation, deterministic doctor lint, and dogfooding this repo with its own
small wiki.

The public product stays simple: users keep typing `/karpathy:wiki` or
`karpathy wiki`. New mechanics belong behind internal `wiki_tool.py` helper
operations and skill instructions.

## What Already Exists

- `wiki_tool.py` already supports scaffold, status, scan, concept planning,
  manifest refresh, search, affected-concept mapping, update planning, doctor,
  hook install, and local improvement notes.
- `karpathy-wiki/SKILL.md` already tells the agent to keep helper commands
  internal, cite source files, create only 2-5 starter concepts, read cited
  source before implementation claims, and update only affected concept pages.
- `tests/test_wiki_tool.py` and `tests/test_wiki_skill_contract.py` already
  cover manifest/source mapping, affected concepts, doctor basics, hooks,
  improvement notes, and key skill/command text contracts.

## Implementation Plan

### 1. External Raw Ingest Contract

Raw ingest is for non-Git sources only: tickets, screenshots, external docs,
meeting notes, transcripts, pasted user context, and other material that does
not already have Git history. Repo code remains authoritative through path plus
commit citations.

Add internal helper support for append-only raw records:

```text
external source
  -> sanitized raw record
  -> source id + sha256 hash + metadata
  -> optional correction record
  -> wiki concepts cite raw id or repo path
```

Required contract:

- Store text raw records as `knowledge/raw/<kind>/<source_id>.md`.
- Use frontmatter fields: `type: Raw Source`, `source_id`, `kind`,
  `title`, `timestamp`, `sha256`, `source_url` when available,
  `source_commit` when captured from a repo state, `supersedes` for correction
  records, and `redacted: true` only for safety removals.
- Add internal helper commands:
  - `raw-add --repo . --kind <kind> --title <title> --body-file <path>`
  - `raw-correct --repo . --source-id <id> --body-file <path>`
  - `raw-redact --repo . --source-id <id> --reason <text>`
  - `raw-show --repo . --source-id <id> --json`
- Helper JSON output must include `path`, `source_id`, `sha256`, `created`,
  `supersedes`, and `redacted`.
- Source IDs are stable slugs derived from kind, title, and date. If a slug
  already exists, append `-2`, `-3`, and so on without changing the existing
  record.
- Hashes use `sha256` over stored raw content.
- Existing raw records are never overwritten.
- Corrections create a new record that references the prior source ID.
- Binary and large files are rejected or represented by metadata unless an
  explicit future design adds storage support.
- Secret and PII handling is conservative: the helper refuses obvious secrets
  and tells the agent to summarize sensitive material instead of storing it.
  If a secret or personal data still slips through, `raw-redact` is the only
  sanctioned mutation: it replaces stored body content with a redaction
  placeholder, preserves the original `source_id`, records `redacted: true`,
  and appends the reason to the record. This is a safety exception to
  append-only immutability, not a normal correction path.

### 2. One-Source Compile Workflow

Keep the LLM responsible for semantic writing, but make the inspection scope
explicit and bounded.

One compile unit is either:

- one external raw source record, or
- one Git-tracked file, or
- one narrow repo source set required to explain a single concept, capped by the
  helper and named in the plan output.

No "source cluster" can silently mean half the repo. The helper should return
the chosen source paths, affected concept candidates, and questions the agent
must answer before writing. It must not generate semantic claims by itself.

### 3. Deterministic Index And Link Health

Strengthen `doctor` with exact, testable graph rules:

- Every concept page must be reachable from `knowledge/wiki/index.md` through
  Markdown links or directory index links. Unreachable concept pages are
  warnings, not critical failures, because the page may still be cited by source
  mapping and can usually be repaired by adding an index link.
- Broken local links are critical.
- Pages outside `index.md`, `log.md`, and generated manifests that no concept
  links to are warnings unless explicitly marked as drafts.
- Backlinks are reported as generated diagnostics only. Do not require authors
  to maintain manual backlink sections.

### 4. Deterministic Knowledge Lint

Keep `doctor` reliable. Do not make it a fuzzy semantic judge in the default
path.

Add deterministic warnings for:

- missing required frontmatter
- missing `resource` or source citation
- missing or stale manifest entries
- missing per-concept source commit metadata
- cited repo paths that no longer exist
- external raw source IDs that no longer resolve

Defer duplicate and contradiction detection to optional advisory heuristics or a
future eval-backed workflow. They are useful, but they are not reproducible
enough for the core `doctor` contract yet.

### 5. Skill Contract Updates

Update `karpathy-wiki/SKILL.md` and command guidance so agents:

- treat raw ingest as external-source capture, not a copy of Git
- use the wiki to narrow the search, then read cited source before claims
- compile one bounded source unit at a time
- run deep graph/index lint only through `doctor`, not through Git hooks
- keep hooks fast and limited to manifest-based stale reminders

### 6. Dogfood Validation Phase

After helper and doctor changes land, create a small `knowledge/wiki/` for this
repo in a separate validation phase.

The dogfood bundle should include 2-5 cited concepts, but it must validate more
than setup:

- one external raw ingest example or fixture
- one correction-record example
- one one-source compile pass
- one reachable index path
- one doctor run covering graph/index checks
- one update-plan run proving changed source maps only to affected concepts

## Test Plan

Run the existing suite:

```bash
python3 -m unittest tests/test_wiki_tool.py tests/test_wiki_skill_contract.py
```

Add helper tests for:

- raw ingest never overwrites an existing record
- raw ingest writes the required frontmatter and JSON output fields
- `sha256` hashes are stable
- correction records reference the prior source ID
- redaction replaces body content, sets `redacted: true`, and preserves audit
  metadata
- large/binary/secret-like inputs are rejected or safely summarized
- compile planning returns exactly one bounded source unit
- graph doctor reports unreachable concept pages as warnings
- graph doctor reports broken local links and missing source IDs
- update planning still maps only changed source files to affected concepts

Add skill-contract or transcript smoke tests for:

- setup keeps helper commands internal
- update mode reads changed files and only affected concept pages
- doctor mode reports graph/index issues in user-facing language
- raw ingest is described as external-source capture, not repo-code copying

## NOT In Scope

- Vector databases or embeddings. The current product bet is inspectable files,
  indexes, links, and source citations.
- A graph database. Generated graph diagnostics are enough for this pass.
- LLM semantic edits from Git hooks. Hooks stay deterministic and fast.
- Auto-staging wiki, raw, or agent-instruction files.
- Full semantic contradiction detection in core `doctor`.
- Copying Git-tracked source files into `knowledge/raw/`.

## Failure Modes

- Raw records may capture secrets or personal data. The helper should reject
  obvious secrets and the skill should instruct agents to summarize sensitive
  material instead.
- Raw records may grow without bound. Large and binary inputs are out of scope
  for storage in this pass.
- Doctor may become noisy. Keep core checks deterministic and severity-ranked.
- One-source compile may under-explain cross-file concepts. Allow one narrow
  source set only when the helper names every file and the agent cites them.
- Dogfooding may validate only the happy path. The validation phase must include
  raw ingest, correction, graph lint, and update-plan checks.

## Worktree Strategy

This is parallelizable after the plan doc lands:

| Step | Modules touched | Depends on |
| --- | --- | --- |
| Raw ingest helper | `plugins/karpathy/skills/karpathy-wiki/scripts/`, `tests/` | plan doc |
| Doctor graph/index lint | `plugins/karpathy/skills/karpathy-wiki/scripts/`, `tests/` | plan doc |
| Skill contract updates | `plugins/karpathy/skills/`, `plugins/karpathy/commands/`, `tests/` | helper contracts chosen |
| Dogfood wiki bundle | `knowledge/` | helper + doctor changes |

Run raw ingest and doctor lint sequentially if one engineer owns `wiki_tool.py`;
they touch the same module. Skill-contract wording can happen in parallel once
helper contracts are named. Dogfood waits for both.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 1 | issues_found | outside voice found underspecified raw ingest, lint, dogfood, and helper contracts; scope refinements incorporated |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 2 | clean | 18 issues/gaps reviewed, 0 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | — |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

- **UNRESOLVED:** 0
- **VERDICT:** ENG CLEARED. Outside voice issues were incorporated into this plan.
