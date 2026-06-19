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
- If the client rejects `/karpathy wiki` as a slash command, tell the user to
  use `/karpathy:wiki` or type `karpathy wiki` as plain text. Do not invent a
  second command family.
- Treat source code, tests, and explicit user instructions as authoritative.
- Use the wiki to narrow where to look; read cited source files before editing
  code or making implementation claims.
- Ask before writing wiki files, Git hooks, or agent instruction files.
- Never stage or commit `CLAUDE.md`, `AGENTS.md`, `.cursor/rules`, or other
  agent instruction / memory files.
- Never copy large source files into the wiki. Summarize and cite them.

Resolve bundled resources relative to this `SKILL.md`. Use
`scripts/wiki_tool.py` for deterministic repo/wiki operations.

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

## First Step

Run:

```bash
python3 <skill-dir>/scripts/wiki_tool.py status --repo . --json
```

Use the result to choose a mode:

- **Setup**: no `knowledge/wiki/` exists, or the user says setup/init.
- **Doctor**: the user says doctor, health, lint, validate, or check wiki.
- **Question**: the intent is question-shaped.
- **Task brief**: the intent is task-shaped.
- **Update**: no explicit intent and git changes affect concepts in the
  manifest.
- **Status**: no explicit intent and no action is needed.

If status reports no wiki and the user asked a question or task, explain that
the wiki must be created first and ask whether to set it up.

Mode precedence:

1. Explicit setup/init/doctor/update/status words win.
2. Inputs ending in `?`, starting with `how/why/what/where/when/who`, or asking
   for explanation are questions.
3. Inputs with imperative coding verbs like add, fix, implement, refactor,
   remove, migrate, or debug are tasks.
4. If classification is ambiguous and the next action would write files, ask
   one clarifying question.

## Setup Mode

1. Say what will be created under `knowledge/` and ask for approval.
2. After approval, run:

   ```bash
   python3 <skill-dir>/scripts/wiki_tool.py init --repo .
   ```

3. Read the repo's high-signal files: `README*`, package/build config, docs,
   tests, and obvious source entry points.
   Start with the read-only scan helper:

   ```bash
   python3 <skill-dir>/scripts/wiki_tool.py scan --repo . --json
   ```

4. Create only a small starter wiki:
   - `knowledge/wiki/index.md` with repo overview, known commands, and links.
   - `knowledge/wiki/log.md` with the setup entry.
   - 2-5 concept pages max, only when they can be cited to specific source or
     docs.
   - A verification surface page when commands are discoverable.
   Every implementation-relevant claim must cite a source file or repo doc.
5. Ask whether to enable automation:
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
instruction files.

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
4. Ask before editing.
5. After approval, update only affected wiki files and append `log.md`.
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
- Warnings: missing frontmatter fields, uncited concepts, stale changed-file
  mappings.
- Clean checks.

Ask before applying fixes. Favor minimal repair: fix a link, add a missing
frontmatter field, refresh the manifest, or mark low-confidence content.

## Examples

- `/karpathy:wiki` in a repo with no wiki: setup mode. Explain the
  `knowledge/` structure, ask approval, run `init`, run `scan`, then create a
  small cited starter wiki.
- `/karpathy wiki add trial expiration handling`: task brief mode. Search the
  wiki, read cited source files, return likely files, invariants, risks, and
  verification commands with citations.
- `karpathy wiki how does auth work?`: question mode. Search concepts, read
  resources, answer from wiki first and source second, with stale/thin warnings
  when needed.
- `/karpathy:wiki` after a diff: update mode. Run `update-plan`, read only the
  changed files and affected concepts, then ask before touching wiki pages.
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
