---
name: karpathy-wiki
description: >-
  Build, maintain, query, and health-check a local repo wiki / LLM knowledge
  base for coding agents. Use when the user says "/karpathy:wiki",
  "/karpathy wiki", "karpathy wiki", asks to set up a repo wiki, asks a repo
  question that should use a wiki first, wants a task brief before coding,
  wants wiki updates after code changes, or asks for wiki doctor/lint/health.
  Implements an OKF-compatible Markdown knowledge bundle under knowledge/wiki
  with citations to source files, task briefs, surgical updates, and optional
  advisory stale-wiki reminders.
---

# Karpathy Wiki

Maintain a local Markdown repo wiki that helps coding agents orient before
editing. The wiki is an LLM-maintained knowledge layer, not a replacement for
source code.

## Contract

- Use one public command: `/karpathy:wiki` or the human phrase
  `/karpathy wiki`.
- Infer the internal mode from repo state and user intent.
- Treat `scripts/wiki_tool.py` as an internal helper for the agent. Do not make
  the user run helper commands during normal setup, question, task brief,
  update, or doctor flows. Run the helper yourself, then report the result in
  plain language.
- If the client rejects `/karpathy wiki` as a slash command, tell the user to
  use `/karpathy:wiki` or type `karpathy wiki` as plain text. Do not invent a
  second command family.
- Treat source code, tests, and explicit user instructions as authoritative.
- Use the wiki to narrow where to look; read cited source files before editing
  code or making implementation claims.
- Treat raw ingest as external-source capture only. Do not copy Git-tracked
  source files into `knowledge/raw/`; repo code stays authoritative through
  path and commit citations.
- Compile one bounded source unit at a time before semantic wiki writing: one
  raw source record, one Git-tracked file, or one helper-capped repo source set.
- For normal wiki writes, state the exact files you will create or update and
  proceed when the user has asked for setup/update or has accepted your proposed
  wiki action. Ask a clarifying question only when the write scope is ambiguous
  or broader than the active mode.
- Always ask before installing Git hooks or editing agent instruction files.
- Never stage or commit `CLAUDE.md`, `AGENTS.md`, `.cursor/rules`, or other
  agent instruction / memory files.
- Never copy large source files into the wiki. Summarize and cite them.

Resolve bundled resources relative to this `SKILL.md`. Use
`scripts/wiki_tool.py` for deterministic repo/wiki operations.

## UX Contract

`/karpathy:wiki` is the product. `wiki_tool.py` is plumbing.

- Do not hand the user a terminal checklist of helper commands unless they
  explicitly ask to operate manually or debug the helper itself.
- Do not ask the user to paste concept pages into an editor. If wiki files need
  semantic content, read the cited sources and write the pages yourself.
- Keep user-facing responses about state and decisions: missing wiki, starter
  concepts needed, affected concepts, doctor issues, proposed files, and
  verification result.
- It is fine to mention helper command names in concise verification summaries,
  but not as instructions the user must execute.
- When user approval is needed, ask for the decision, not for mechanical steps.

## Self-Improvement Notes

The skill can dogfood itself by writing local improvement notes when real usage
exposes reusable product lessons. This is for local learning, not telemetry.

Use `knowledge/outputs/wiki-improvements.md` as the default append-only log.
When writing through the helper, run internally:

```bash
python3 <skill-dir>/scripts/wiki_tool.py note-improvement --repo . --title "<short title>" --body "<observation>" --suggestion "<suggested skill change>" --evidence "<path>" --tag "<tag>"
```

Write an improvement note only when the run reveals a reusable problem or
opportunity in the karpathy-wiki skill itself, such as:

- the mode choice was confusing or wrong
- the agent exposed helper-script mechanics to the user
- starter concept suggestions were missing, noisy, or poorly cited
- doctor/update output was technically correct but hard to act on
- the skill needed a stronger guardrail, example, or regression test

Do not write improvement notes for ordinary repo facts, user preferences, raw
transcripts, secrets, personal data, or large source excerpts. Keep entries
short and actionable: observation, evidence path(s), and a concrete suggested
skill change. Never stage or commit the improvement log automatically.

Scaling rule: keep this local by default. If more users adopt the skill, collect
these notes only through an explicit export or issue-filing flow; do not add
background network upload or cross-user aggregation.

## Directory Shape

Create and maintain this structure:

```text
knowledge/
  raw/
    tickets/
    screenshots/
    external-docs/
  wiki/
    index.md
    log.md
    components/
    workflows/
    invariants/
    decisions/
    tests/
    recipes/
    failure-modes/
    .karpathy-wiki.json
  outputs/
    task-briefs/
    qa-reports/
    diagrams/
  rules.md
```

The wiki should be OKF-compatible Markdown with YAML frontmatter. Use these
concept types: `Component`, `Workflow`, `Invariant`, `Decision`,
`Test Surface`, `Task Recipe`, and `Failure Mode`.

Supported frontmatter subset for the helper script:

- Scalar fields: `type`, `title`, `description`, `resource`, `timestamp`,
  `source_commit`, `confidence`
- Inline arrays: `tags: [auth, security]`, `verified_by: ["npm test"]`
- Required concept fields: `type`, `title`, `description`, `timestamp`

The manifest at `knowledge/wiki/.karpathy-wiki.json` is generated from concept
frontmatter and citations. It contains `version`, `generated_at`,
`source_commit`, `wiki_root`, `concept_count`, `concepts`, and `source_map`.
Do not edit the manifest manually; regenerate it with `refresh-manifest`.
`doctor` reports when the saved manifest is stale, but it does not rewrite it.

## Raw Source Capture

Raw ingest is only for non-Git sources: tickets, screenshots, external docs,
meeting notes, transcripts, pasted user context, and other material that lacks
repo history. Use raw records to preserve external evidence, then cite raw IDs
from wiki concepts as `raw:<source_id>` or in `raw_source` / `raw_sources`
frontmatter.

Run raw helper commands internally when needed:

```bash
python3 <skill-dir>/scripts/wiki_tool.py raw-add --repo . --kind <kind> --title <title> --body-file <path> --json
python3 <skill-dir>/scripts/wiki_tool.py raw-correct --repo . --source-id <id> --body-file <path> --json
python3 <skill-dir>/scripts/wiki_tool.py raw-redact --repo . --source-id <id> --reason "<reason>" --json
python3 <skill-dir>/scripts/wiki_tool.py raw-show --repo . --source-id <id> --json
```

Do not expose these as public slash commands. Summarize helper results to the
user. Corrections create new records that supersede older raw IDs. Redaction is
the safety exception: it may replace stored body content when secrets or
personal data slipped into a raw record.

## Compile Scope

Before turning external or repo source material into concept text, run the
read-only compile planner internally:

```bash
python3 <skill-dir>/scripts/wiki_tool.py compile-plan --repo . --source <git-tracked-file-or-directory> --json
python3 <skill-dir>/scripts/wiki_tool.py compile-plan --repo . --source-id <raw-source-id> --json
```

Use the output to name the exact source paths, candidate concepts, and questions
the semantic wiki edit must answer. The helper does not generate claims; the
agent must read the bounded source unit and write cited wiki prose. If a concept
needs more than one source unit, do multiple compile passes and cite each unit
explicitly.

## First Step

Internally run:

```bash
python3 <skill-dir>/scripts/wiki_tool.py status --repo . --json
```

Use the result to choose a mode:

- **Setup**: `setup_state` is `missing` or `incomplete-setup`, or the user
  says setup/init.
- **Starter concepts**: `setup_state` is `needs-starter-concepts`.
- **Doctor**: the user says doctor, health, lint, validate, or check wiki.
- **Question**: the intent is question-shaped.
- **Task brief**: the intent is task-shaped.
- **Update**: no explicit intent and git changes affect concepts in the
  manifest.
- **Status**: no explicit intent and no action is needed.

If status reports no wiki, incomplete setup, or no starter concepts and the
user asked a question or task, explain that the wiki must be finished first and
ask whether to set it up or add starter concepts.

Mode precedence:

1. Explicit setup/init/doctor/update/status words win.
2. Inputs ending in `?`, starting with `how/why/what/where/when/who`, or asking
   for explanation are questions.
3. Inputs with imperative coding verbs like add, fix, implement, refactor,
   remove, migrate, or debug are tasks.
4. If classification is ambiguous and the next action would write files, ask
   one clarifying question.

## Setup Mode

1. Say what will be created under `knowledge/`. If the user explicitly asked to
   set up the wiki, this is enough context to proceed with wiki file writes. If
   setup is inferred from an ambiguous request, ask one clarifying question.
2. Run internally:

   ```bash
   python3 <skill-dir>/scripts/wiki_tool.py init --repo .
   ```

3. Read the repo's high-signal files: `README*`, package/build config, docs,
   tests, and obvious source entry points.
   Start with the read-only scan and concept-plan helpers:

   ```bash
   python3 <skill-dir>/scripts/wiki_tool.py scan --repo . --json
   python3 <skill-dir>/scripts/wiki_tool.py concept-plan --repo . --json
   ```

4. Create only a small starter wiki in the same flow:
   - `knowledge/wiki/index.md` with repo overview, known commands, and links.
   - `knowledge/wiki/log.md` with the setup entry.
   - 2-5 concept pages max, chosen from the concept plan only after reading
     the candidate `read` files.
   - A verification surface page when commands are discoverable.
   Every implementation-relevant claim must cite a source file or repo doc.
5. Run `refresh-manifest` and `doctor` internally. Report whether doctor is
   clean and how many concepts are indexed.
6. Ask whether to enable automation:
   - Manual only.
   - Remind me when stale.
   - Strict stale reminder, only for users who explicitly want commits blocked.

If the user chooses stale reminders, ask approval, then run:

```bash
python3 <skill-dir>/scripts/wiki_tool.py install-hook --repo .
```

If the user explicitly chooses strict stale reminders, ask approval and run:

```bash
python3 <skill-dir>/scripts/wiki_tool.py install-hook --repo . --strict
```

Git hooks must stay non-semantic: they can remind or block in strict mode, but
they must not run an LLM update, edit wiki pages, stage files, or change agent
instruction files. Do not run deep graph/index lint from hooks; keep that in
doctor mode.

Agent-instruction setup is proposal-only. If `CLAUDE.md`, `AGENTS.md`, or rule
files exist, offer this snippet, but do not edit unless the user approves:

```markdown
## Repo Wiki

Use /karpathy:wiki before non-trivial code changes to orient on relevant
components, invariants, tests, and risks. You can also type "karpathy wiki" as
plain text. If code changes affect documented
concepts, update the affected wiki pages before finishing. Treat the wiki as
advisory: read cited source files before editing, and keep changes surgical.
```

Do not stage or commit those instruction files.

## Starter Concepts Mode

Use this when `status` reports `setup_state: needs-starter-concepts`. The
scaffold is healthy, but the wiki is not useful yet.

1. Run or reuse scan output:

   ```bash
   python3 <skill-dir>/scripts/wiki_tool.py scan --repo . --json
   python3 <skill-dir>/scripts/wiki_tool.py concept-plan --repo . --json
   ```

2. Use `concept-plan` candidates as concrete options, not as generated content
   or a mandate. Read each chosen candidate's `read` files before writing
   claims. Use `starter_candidates` only as the simpler fallback when the
   concept plan finds nothing useful.
3. Propose 2-5 small concept pages. Prefer:
   - one component page for the app/server entrypoint when detected
   - one high-value auth/session, routing/shell, domain data-flow, or
     integration/server page when the repo shape supports it
   - one test surface page when verification commands are detected
   - one invariant/workflow page only when a cited doc supports it
   - one repeatable smoke-test recipe only after the first useful concept pages
     exist or are being created in the same pass
4. If the user explicitly asked for setup or starter concepts, create only the
   proposed pages after briefly listing them. If the intent is ambiguous, ask
   whether to create the starter concepts. Do not create every candidate in the
   plan just because it was detected.
5. Create the agreed concept pages yourself, then run internally:

   ```bash
   python3 <skill-dir>/scripts/wiki_tool.py refresh-manifest --repo .
   python3 <skill-dir>/scripts/wiki_tool.py doctor --repo .
   ```

Stop after the starter set is useful. Do not grow the wiki into a broad repo
summary during this pass.

## Question Mode

1. Search the wiki:

   ```bash
   python3 <skill-dir>/scripts/wiki_tool.py search --repo . --limit 8 "<question>"
   ```

2. Read the top matching concepts and their cited source files.
   Search results include `resources` and `confidence`; prioritize high
   confidence concepts with concrete resources.
3. Answer from the wiki first, then source where needed.
4. Include citations to concept pages and source files.
5. If the wiki appears stale or thin, say so and propose a focused update.
6. Do not make implementation claims from the wiki alone. Read the cited source
   before claiming how code currently behaves.

## Task Brief Mode

1. Search the wiki for the task.
2. Read matching concepts and cited source files before proposing implementation
   details.
3. Write a task brief in the response by default.
4. If the user asks for a filed output, ask before writing and place it under
   `knowledge/outputs/task-briefs/<slug>.md`.
5. The brief should cite concept pages and source files. Do not include a likely
   file, invariant, or verification command unless it is backed by a wiki page,
   repo file, or source read.
6. Use this shape:

```markdown
# Task Brief: <task>

## Likely Files
- <file> - <why>

## Relevant Concepts
- [Concept](../../wiki/<path>.md) - <why it matters>

## Invariants
- <rule to preserve, with citation>

## Risks
- <likely mistake or ambiguity>

## Verification
- <test/typecheck/lint/build command>

## Source Check
- Read the cited source files before editing. The wiki narrows the search; it is
  not the authority.
```

End by asking whether to proceed with coding if the user has not already asked
for implementation.

## Update Mode

Use this when `status` reports changed files that map to concept pages.

1. Run the read-only update planner:

   ```bash
   python3 <skill-dir>/scripts/wiki_tool.py update-plan --repo . --scope all --json
   ```

2. Read the changed files and affected concept pages.
3. Propose the smallest wiki edits that make those concept pages current.
4. If the user invoked update mode or asked to update the wiki, make those
   minimal edits after listing the affected wiki files. If `/karpathy:wiki`
   inferred update mode from repo state with no explicit update request, ask
   before editing.
5. Update only affected wiki files and append `log.md`.
6. Re-run doctor or status.

Do not rewrite unrelated wiki pages. If changed files do not map to concepts,
say no wiki update is required and recommend adding a concept only if the
change introduced a durable new component, invariant, workflow, or test surface.
Never auto-stage wiki changes. Never update `CLAUDE.md`, `AGENTS.md`, or rule
files as part of an update pass.

## Doctor Mode

Run:

```bash
python3 <skill-dir>/scripts/wiki_tool.py doctor --repo .
```

Report:

- Critical issues: broken local links, missing required index/log, concept
  source references that no longer exist.
- Warnings: missing frontmatter fields, missing `source_commit`, uncited
  concepts, unreachable concept pages, unresolved raw source IDs, stale
  manifests, and stale changed-file mappings.
- Clean checks.

Favor minimal repair: fix a link, add a missing frontmatter field, refresh the
manifest, or mark low-confidence content. If the user explicitly asked for
doctor fixes, apply minimal wiki-file repairs after listing them. Ask before
larger semantic rewrites, Git hooks, or agent instruction edits.

## Examples

- `/karpathy:wiki` in a repo with no wiki: setup mode. Explain the
  `knowledge/` structure, run the helper internally, read high-signal sources,
  then create a small cited starter wiki if setup was explicitly requested or
  accepted.
- `/karpathy:wiki` after `init` but before concept pages: starter concepts
  mode. Say the scaffold is healthy but empty, propose 2-5 cited pages from
  scan, write the accepted starter pages yourself, then refresh the manifest and
  run doctor internally.
- `/karpathy wiki add trial expiration handling`: task brief mode. Search the
  wiki, read cited source files, return likely files, invariants, risks, and
  verification commands with citations.
- `karpathy wiki how does auth work?`: question mode. Search concepts, read
  resources, answer from wiki first and source second, with stale/thin warnings
  when needed.
- `/karpathy:wiki` after a diff: update mode. Run `update-plan` internally,
  read only the changed files and affected concepts, then make or propose the
  smallest wiki edits depending on whether update intent was explicit.
- `/karpathy:wiki doctor`: doctor mode. Report broken links, stale manifest,
  missing frontmatter, missing citations, and proposed minimal fixes.
- `/karpathy:wiki auth`: ambiguous. If answering is safe and read-only, treat it
  as a question. If the next step would write files, ask whether the user wants
  a task brief, update, or health check.

## Concept Template

Use this compact template for concept pages:

```markdown
---
type: Component
title: Example Component
description: One sentence describing what this owns.
resource: ../../../src/example.ts
tags: [example]
timestamp: 2026-06-19T00:00:00Z
source_commit: abc123
confidence: medium
verified_by: ["npm test"]
---

# Role

# Public Surface

# Invariants

# Depends On

# Common Changes

# Citations

[1] [source](../../../src/example.ts)
```

Use the right `type` for the page. Keep claims short, cited, and useful for a
future coding agent.
