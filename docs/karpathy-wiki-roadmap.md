# Karpathy Wiki Roadmap

`/karpathy:wiki` has shipped as an MVP: the command exists, the plugin packages
it, the repo-local `knowledge/` structure is defined, and the helper script can
scaffold, scan, search, health-check, plan updates, refresh manifests, and
install stale-wiki reminders.

This does not mean the full product vision is complete. The MVP proves the
basic workflow and architecture. The remaining work is about making the wiki
consistently useful for real vibe-coding sessions.

## What Is Left

### Quality Pass On Real Repos

Use `/karpathy:wiki` on a few actual projects and evaluate whether the main
flows feel useful:

- setup
- task briefs
- Q&A
- update mode
- doctor / health checks

The goal is to find rough edges that only show up in real projects: confusing
prompts, missing context, noisy output, weak citations, or awkward follow-up
steps.

#### Rocketboard Pass

Status: first setup pass completed.

What happened:

- `init` created the required wiki scaffold.
- `doctor` was clean except for "no concept pages found yet."
- Three cited starter concepts were added manually:
  - `knowledge/wiki/components/app-boot.md`
  - `knowledge/wiki/invariants/sql-migrations.md`
  - `knowledge/wiki/tests/verification-surface.md`
- `refresh-manifest` indexed 3 concepts and `doctor` reported no issues.
- Search worked for both a Q&A-style query and a task-orientation query:
  - "what verification commands should I run?" returned the verification
    surface first.
  - "change app boot provider wiring" returned the app boot concept first.

Product finding:

- The command needed a clearer intermediate state between "wiki exists" and
  "wiki is useful." A healthy scaffold with zero concept pages should be called
  `needs-starter-concepts`, and the next step should be obvious.
- `scan`/`status` should offer concrete candidate starter pages from detected
  entrypoints, verification commands, and docs.
- The setup flow should not make users run helper scripts, create files in an
  editor, or paste Markdown by hand. The agent should run helper scripts
  internally, read cited sources, write starter pages itself after setup/update
  intent is clear, and report verification results.

Second dogfood finding:

- The initial three pages made the wiki valid, but not yet very useful for
  Rocketboard work. The useful follow-up pages were auth/session,
  routing/shell, project data flow, MCP server behavior, and a repeatable wiki
  smoke-test recipe.
- This should not become Rocketboard-specific hard-coding. The long-term fix is
  a deterministic concept planner that detects source-shape signals like
  feature directories, routing files, integration packages, verification
  commands, and docs, then gives the agent a ranked candidate list with source
  files to read before writing wiki pages.
- The agent remains responsible for semantic content and citations. The helper
  should plan what to inspect, not pretend it understands the code by itself.

Third dogfood finding:

- Static repo shape is useful, but it does not always tell us which pages are
  most worth creating first. Recent Git history adds a practical signal:
  frequently changed directories, bug-fix commits, risky migrations/auth paths,
  and test touchpoints usually identify concepts that will help future agents.
- The first implementation keeps this behind `concept-plan --include-history`
  so the existing default output stays stable. The helper now derives planning
  tasks from Git history, scores deterministic candidates, and uses a small
  weighted set-cover pass to prefer pages that explain multiple useful areas.
- The remaining product question is whether those ranked pages actually improve
  real task briefs and Q&A. That needs dogfood and benchmarks, not more planner
  complexity yet.

### Benchmarking

Add a wiki orientation benchmark.

The benchmark should answer:

- Does the wiki help agents find the right files faster?
- Does it help preserve known invariants?
- Does it reduce repeated token spend on recurring repo questions?
- Does it improve task briefs compared with an unaided baseline?
- Does it create false confidence when the wiki is stale or thin?

Useful metrics:

- file-finding accuracy
- invariant recall
- verification-command recall
- answer citation quality
- task-brief usefulness
- token count
- wall-clock time

### Better Compile Behavior

The helper can scan the repo and propose a deterministic concept plan, but the
LLM still writes the starter wiki.

Improve templates, examples, and instructions so the first generated wiki is
consistently:

- small
- cited
- useful
- not a bloated encyclopedia
- clear about low-confidence claims
- focused on durable repo knowledge

The quality bar is not "summarize everything." The quality bar is "help the
next coding agent orient faster without trusting stale or uncited claims."

### Better Update Workflow

`update-plan` exists, but semantic edits are still LLM-guided.

Strengthen examples and guardrails so update mode reliably:

- reads changed files first
- reads only affected concept pages
- proposes minimal wiki edits
- avoids touching unrelated wiki pages
- appends a useful `log.md` entry
- never stages wiki changes automatically
- never edits `CLAUDE.md`, `AGENTS.md`, or rule files as part of a wiki update

The core rule: only update affected concepts unless the change introduced a new
durable component, invariant, workflow, test surface, decision, recipe, or
failure mode.

### UX Polish

Make setup and daily use more conversational and harder to misuse.

Specific areas:

- clearer setup prompts
- better stale-wiki messages
- better "what should I do next?" behavior
- clearer distinction between question, task brief, update, and doctor modes
- more helpful behavior when a repo has no wiki yet
- less command memorization for users

The user should be able to type `/karpathy:wiki` and trust the skill to pick the
right next step from repo state and intent.

### Self-Improvement Loop

Capture local dogfood lessons while the skill is being used.

The first version should be deliberately simple:

- append short notes to `knowledge/outputs/wiki-improvements.md`
- include observation, evidence path(s), and suggested skill change
- keep notes local; no telemetry, network upload, or cross-user aggregation
- never include secrets, personal data, raw transcripts, or large source
  excerpts
- never stage the improvement log automatically

This is useful while the skill has one primary user and can still scale later if
collection becomes explicit, for example by turning selected notes into GitHub
issues or PR checklist items. Do not build background reporting.

### Docs And Examples

Add concrete examples so vibe coders immediately understand what good output
looks like.

Useful additions:

- screenshots of a generated wiki in Obsidian or a normal editor
- sample `knowledge/wiki/` output
- sample task brief
- sample Q&A answer with citations
- sample update plan after a code change
- sample doctor report
- before/after comparison showing raw repo context versus compiled wiki context

These examples should be small enough to read quickly, but realistic enough to
show why the wiki is useful.

## Non-Goals For The Next Pass

- Do not add embeddings or a vector database yet.
- Do not add a graph database yet.
- Do not run LLM semantic edits from Git hooks.
- Do not auto-stage wiki changes.
- Do not auto-edit or commit `CLAUDE.md`, `AGENTS.md`, or rule files.
- Do not optimize for a huge generated wiki before the small-wiki workflow is
  proven.

## Next Practical Step

Run `/karpathy:wiki` on one or two more real repos, capture the transcripts and
outputs, and compare them against Rocketboard. The next validation target should
exercise either history-aware starter planning on a thin wiki, update mode after
a real code change, or Q&A on a repo with a stale wiki.
