# karpathy-skills

Karpathy Skills turns Andrej Karpathy-inspired AI coding practices into
practical skills that vibe coders can use inside Claude Code and Codex.

The goal is simple: when an AI agent writes code for you, these skills help you
catch the common failure modes before they turn into bugs, bloated code, or
messy commits.

This repo ships one plugin, `karpathy`, with three skills:

- `/karpathy:audit` - reviews your AI agent instruction files.
- `/karpathy:diff` - reviews AI-generated code changes before you commit.
- `/karpathy:wiki` - a repo wiki / memory layer for helping agents understand
  the codebase before they edit it.

The wiki skill's product rationale and longer-term design are documented in
[docs/repo-knowledge-bases.html](docs/repo-knowledge-bases.html).

---

## Why This Exists

Vibe coding is powerful, but AI coding agents have predictable failure modes:

- They make assumptions without telling you.
- They overbuild simple requests.
- They refactor or reformat unrelated code.
- They delete comments or code they do not fully understand.
- They finish without a clear test or verification step.

Karpathy described these problems after extensive agentic coding. This project
turns those observations into concrete workflows that an agent can run for you.

The four principles behind the plugin are:

| Principle | Plain-English Meaning |
| --- | --- |
| Think Before Coding | Do not silently guess. State assumptions, ask when unclear, and surface tradeoffs. |
| Simplicity First | Write the smallest thing that solves the real task. No speculative abstractions. |
| Surgical Changes | Touch only what the task requires. No drive-by cleanup or unrelated rewrites. |
| Goal-Driven Execution | Define how success will be checked, then run the checks. |

---

## The Skills

| Skill | Status | What It Is | What It Is For | Impact |
| --- | --- | --- | --- | --- |
| `/karpathy:audit` | Shipped | A review of your `CLAUDE.md`, `AGENTS.md`, or Cursor rules. | Making sure your agent instructions are clear, current, and useful. | Better standing instructions, fewer vague rules, less stale context. |
| `/karpathy:diff` | Shipped | A review of the code changes an AI agent just made. | Catching scope creep before you commit. | Smaller diffs, fewer surprise edits, safer commits. |
| `/karpathy:wiki` | Shipped MVP | A local repo wiki that the agent maintains and reads before coding. | Helping the agent understand your project without rereading everything every time. | Faster orientation, better task briefs, less repeated context work. |

If you only remember one thing:

```text
Run /karpathy:diff before accepting or committing AI-generated code.
```

That is the highest-leverage habit.

---

## Install

### Claude Code

Inside Claude Code:

```text
/plugin marketplace add jokim1/karpathy-skills
/plugin install karpathy@karpathy-skills
```

To update later:

```text
/plugin marketplace update karpathy-skills
/reload-plugins
```

Claude Code can also auto-update installed plugins at startup. Third-party
marketplaces default to manual updates, so enable it from:

```text
/plugin -> Marketplaces -> karpathy-skills -> Enable auto-update
```

### Codex

Codex can install from this repo's native marketplace at
`.agents/plugins/marketplace.json`:

```bash
codex plugin marketplace add jokim1/karpathy-skills
```

Then install `karpathy` from the Codex plugin directory.

On Codex CLI builds that expose plugin installation directly:

```bash
codex plugin add karpathy@karpathy-skills
```

To update later:

```bash
codex plugin marketplace upgrade karpathy-skills
```

After a plugin update, start a new Codex thread so the refreshed skills and
hooks are loaded.

### Update Reminders

The plugin includes an advisory `SessionStart` hook for Claude Code and Codex
clients that have plugin hooks trusted or enabled.

At most once per day, it compares your installed plugin version with the GitHub
version and surfaces update instructions if a newer version is available. It does
not update files automatically and it does not block your session.

To disable the reminder:

```bash
export KARPATHY_DISABLE_UPDATE_CHECK=1
```

---

## Quick Usage

```text
/karpathy:audit [path]
/karpathy:diff [ref/path]
/karpathy:wiki [question/task/doctor]
```

You can also ask in normal words:

```text
audit my AGENTS.md
review my changes before I commit
did the agent touch anything it should not have?
karpathy wiki how does auth work?
```

Claude Code command form:

```text
/karpathy:audit
/karpathy:diff
/karpathy:wiki
```

Human-friendly phrasing that should also trigger the skills:

```text
karpathy audit
karpathy diff
karpathy wiki
```

Some clients may reject `/karpathy wiki` as a slash command because plugin
commands are namespaced with a colon. If that happens, use `/karpathy:wiki` or
type `karpathy wiki` as normal text.

---

## Skill 1: `/karpathy:audit`

### What It Does

`/karpathy:audit` reviews the files that tell your coding agent how to behave:

- `CLAUDE.md`
- `AGENTS.md`
- `.cursor/rules/*.mdc`
- similar project or global agent instruction files

These files matter because the agent reads them repeatedly. If they are bloated,
stale, vague, or contradictory, the agent will behave worse.

### When To Use It

Use `/karpathy:audit` when:

- You first add this plugin to a project.
- You create or edit `CLAUDE.md` or `AGENTS.md`.
- The agent starts making weird assumptions.
- The agent keeps overbuilding or ignoring conventions.
- You want to clean up your project instructions.

You do not need to run this every day. Monthly, after major edits, or when the
agent starts misbehaving is usually enough.

### User Journey

1. You run:

   ```text
   /karpathy:audit
   ```

2. The skill looks for an instruction file:

   ```text
   ./CLAUDE.md
   ./AGENTS.md
   .cursor/rules/*.mdc
   ```

3. It reports two things:

   - Coverage: does the file teach the agent the four principles?
   - Quality: is the file itself clear, current, and useful?

4. It gives findings like:

   ```text
   [WARNING] Stale sprint notes
   Location: Roadmap section
   Issue: The file includes "current sprint" notes that will go stale.
   Fix: Move this to docs/ or delete it from the always-read agent file.
   ```

5. It also tells you what is already good.

6. It proposes exact changes.

7. It stops and asks before editing anything.

Even when you approve edits, the skill does not stage or commit `CLAUDE.md`,
`AGENTS.md`, `.cursor/rules`, or other agent instruction files. You decide
whether those changes belong in git.

### What It Catches

| Problem | Why It Matters |
| --- | --- |
| Generic advice like "write clean code" | Costs tokens but does not change behavior. |
| Stale notes like "currently", "for now", or old roadmap items | Misleads future agents. |
| Vague rules like "handle errors properly" | Forces the agent to guess. |
| Missing test or build commands | Makes it hard for the agent to know when it is done. |
| Contradictory instructions | Guarantees inconsistent behavior. |

### Example Use

```text
/karpathy:audit AGENTS.md
```

Possible result:

```text
Coverage: 2/4 principles present
Quality: 3 findings

Critical:
- No verification commands listed.

Warnings:
- Roadmap content is living in the always-read instruction file.
- Several rules are vague and not checkable.

Want me to apply the proposed changes?
```

---

## Skill 2: `/karpathy:diff`

### What It Does

`/karpathy:diff` reviews the code changes an AI agent made before you commit or
accept them.

The core question is:

```text
Does every changed line trace back to the task that was asked?
```

If the answer is no, the skill flags it.

### When To Use It

Use `/karpathy:diff`:

- Before every commit that includes AI-generated code.
- After an agent finishes a batch of edits.
- When you did not read every changed line yourself.
- When you suspect the agent touched unrelated files.

This is the daily-driver skill.

### User Journey

1. You ask the agent to make a change:

   ```text
   add a lastLogin timestamp to the user model
   ```

2. The agent edits files.

3. Before committing, you run:

   ```text
   /karpathy:diff
   ```

4. The skill reads the git diff.

5. If the original task is clear from the conversation, it uses that. If not, it
   asks one question:

   ```text
   What was this change meant to do?
   ```

6. It reviews the diff hunk by hunk.

7. It reports:

   - what traces to the task
   - what does not trace
   - what is unclear
   - what to revert, restore, split out, or test

8. It stops and asks before changing anything.

### What It Catches

| Problem | Example |
| --- | --- |
| Collateral files | The task was about login, but the agent edited billing files. |
| Drive-by refactors | The agent renamed helpers next to the real change. |
| Reformatting noise | The agent changed quote style or reordered imports across a file. |
| Unexplained deletions | The agent deleted a comment explaining an edge case. |
| Over-engineering | The task needed one field, but the agent added a framework. |
| Missing verification | A bug fix has no test or command showing it is fixed. |
| Orphans | The change leaves unused imports or variables behind. |

### Why It Helps

Normal code review asks whether the code is good. That matters, but it is not
the first failure mode for AI-generated code.

`/karpathy:diff` asks the narrower question first:

```text
Did this change do only what was asked?
```

That catches problems that can look harmless in a normal review:

| Advantage | What It Prevents |
| --- | --- |
| Smaller diffs | Less unrelated code for you to review and debug. |
| Fewer surprise edits | The agent cannot quietly change neighboring systems. |
| Better commit hygiene | Real work and drive-by cleanup do not get mixed together. |
| Safer acceptance | You can reject only the bad hunks instead of distrusting the whole change. |
| Better agent behavior over time | The agent gets trained by the review loop to stay surgical. |

### Example Use

```text
/karpathy:diff
```

Possible result:

```text
Task: Add lastLogin timestamp to the user model
Change: 4 files, +82 / -41 lines
Traceability: 6 of 8 hunks trace to the task

Critical:
- auth/session.ts deleted an edge-case comment unrelated to the task.

Warning:
- models/user.ts was reformatted even though only one field changed.

Clean:
- The migration and user model field both trace directly to the task.

Want me to apply the proposed fixes?
```

### Common Targets

```text
/karpathy:diff                 # all uncommitted changes
/karpathy:diff --staged        # only staged changes
/karpathy:diff main...HEAD     # a branch worth of changes
/karpathy:diff src/auth/       # changes under one path
```

---

## Skill 3: `/karpathy:wiki`

### What It Does

`/karpathy:wiki` applies Karpathy's LLM knowledge-base pattern to code
repositories.

The idea:

- The agent creates a local Markdown wiki for your repo.
- The wiki summarizes components, workflows, tests, risks, and important rules.
- The agent reads the wiki before coding so it does not start from zero every
  time.
- After changes, the agent updates only the affected wiki pages.

This is meant to help vibe coders who want the agent to understand a project
without manually writing and maintaining a big documentation site.

The helper script is not part of the normal user workflow. The agent runs it
internally for status, scan, search, doctor, and manifest refresh operations;
users should not have to paste `python3 .../wiki_tool.py` commands into a
terminal just to use the wiki.

The shipped MVP includes:

- A `knowledge/wiki/` scaffold with OKF-style Markdown files.
- A generated wiki manifest at `knowledge/wiki/.karpathy-wiki.json`.
- A deterministic helper for status, search, doctor checks, manifest refresh,
  repo scans, affected-concept plans, and advisory stale reminders.
- A skill workflow that tells the agent how to create starter concepts, answer
  questions, write task briefs, and update only affected wiki pages.

The MVP does **not** include a hosted service, embeddings, a graph database, or
fully automatic semantic repo understanding. The agent still has to read source
files and cite them.

### Why The Command Is Simple

The first design used several commands:

```text
init
compile
brief
ask
update
lint
```

That is too much for a human to remember.

The better UX is:

```text
/karpathy:wiki
karpathy wiki
```

The skill decides what to do based on context. In clients that accept
human-friendly slash phrasing, `/karpathy wiki` should also trigger it. If the
client rejects that as an invalid slash command, use `/karpathy:wiki`.

### User Journeys

| User Enters | Skill Interprets It As | Skill Returns |
| --- | --- | --- |
| `/karpathy:wiki` | No wiki exists | The agent creates a small cited starter wiki after setup is requested or accepted. |
| `/karpathy:wiki` | Scaffold exists but no concepts are indexed | The agent proposes and writes 2-5 starter concepts from cited sources. |
| `/karpathy:wiki add trial expiration handling` | Coding task | A task brief with files, risks, invariants, and tests. |
| `/karpathy:wiki how does auth work?` | Repo question | A cited answer from the wiki and source files. |
| `/karpathy:wiki` after code changes | Wiki update | A proposed update to only affected wiki pages. |
| `/karpathy:wiki doctor` | Health check | Broken links, stale pages, uncited claims, and proposed fixes. |

### Automation

During setup, the wiki skill offers:

| Option | Meaning |
| --- | --- |
| Manual only | User runs `/karpathy:wiki` when they want it. |
| Remind me when stale | A non-blocking git hook warns when changed files may make wiki pages stale. |
| Strict stale reminder | An optional advanced hook mode that blocks commits until the user runs `/karpathy:wiki`. |

The hook never asks an LLM to edit files, never stages wiki changes, and never
updates `CLAUDE.md`, `AGENTS.md`, or rule files. Semantic wiki updates happen
through the normal `/karpathy:wiki` agent flow so the user can review them.

The stale reminder is advisory. It prints something like:

```text
Wiki reminder: 2 concepts may be stale.
- Billing Lifecycle: knowledge/wiki/workflows/billing-lifecycle.md
- Billing Test Surface: knowledge/wiki/tests/billing.md

Run:
  /karpathy:wiki
or type:
  karpathy wiki

Commit is allowed. This reminder is advisory.
```

For the full design, see
[Repo Knowledge Bases for Coding Agents](docs/repo-knowledge-bases.html).

### Dogfood Improvement Notes

When `/karpathy:wiki` exposes friction in the skill itself, the agent can append
a short local note to:

```text
knowledge/outputs/wiki-improvements.md
```

These notes are local by default. They are meant to capture reusable product
lessons like confusing mode selection, noisy starter suggestions, awkward doctor
output, or missing guardrails. Each entry should include the observation,
evidence paths, and a concrete suggested skill change. They should not include
secrets, personal data, raw transcripts, or large source excerpts, and the agent
must never stage them automatically.

If this skill gets broader usage, improvement notes should scale through an
explicit export or issue-filing flow, not background telemetry.

---

## Recommended Workflow

For most vibe coders:

1. Install the plugin.
2. Run `/karpathy:audit` once on your project instructions.
3. Keep using your AI coding agent normally.
4. Run `/karpathy:diff` before accepting or committing AI-generated code.
5. Run `/karpathy:wiki` before larger tasks so the agent starts with better
   repo context.

Simple habit:

```text
Agent writes code -> /karpathy:diff -> fix findings -> commit
```

---

## What This Is Not

This plugin is not a guarantee that AI-generated code is correct.

It does not replace:

- reading important diffs
- running tests
- understanding risky changes
- code review by someone who knows the system

It is a guardrail. It helps the agent slow down, explain itself, and stay inside
the task you actually asked for.

---

## Why This Differs From Related Projects

### Compared To The Original Karpathy CLAUDE.md Repo

[multica-ai/andrej-karpathy-skills][orig-repo] distributes guidance. It gives
you a good instruction file so the agent is told how to behave.

This repo checks behavior:

- `/karpathy:audit` checks whether your instruction file is actually good.
- `/karpathy:diff` checks whether the agent's code changes actually stayed
  inside the task.

Those are different jobs. A static instruction file is useful, but the real
question is whether the agent followed it.

### Compared To Normal Code Review

Normal review asks:

```text
Is this code good?
```

`/karpathy:diff` asks a narrower first question:

```text
Did this change do only what was asked?
```

That narrow question is valuable because AI agents often make unrelated changes
that look reasonable at a glance.

### Compared To Traditional Documentation

Traditional docs rot because humans stop updating them.

`/karpathy:wiki` follows the LLM wiki pattern: let the agent maintain a small
local Markdown wiki, with citations back to source files, so repo knowledge
accumulates over time.

### Compared To OKF, Graphify, And Memory Tools

Google's Open Knowledge Format (OKF) gives a simple file format for Markdown
knowledge bundles. That is useful, and the wiki skill uses the same plain
Markdown plus frontmatter approach rather than inventing a competing format.

Graphify-style tools are strong at turning a folder into a graph you can query.
The wiki skill is narrower: it is about coding-agent behavior before, during,
and after edits.

ByteRover-style tools are broader agent memory systems. The wiki skill is
repo-local, file-based, and tied to the Karpathy audit/diff loop.

---

## Sources And Inspiration

This project is based on several public ideas and tools:

| Source | What We Took From It | What We Changed |
| --- | --- | --- |
| [Andrej Karpathy's public coding-agent observations][karpathy-post] | The core failure modes: silent assumptions, overbuilding, collateral edits, missing verification. | Turned the ideas into runnable audit and diff-review workflows. |
| [multica-ai/andrej-karpathy-skills][orig-repo] | A clear expression of Karpathy-style guidance for agent instruction files. | Built checking tools instead of only distributing guidance. |
| [Open Knowledge Format][okf-spec] | The repo wiki uses plain Markdown, YAML frontmatter, links, indexes, and logs. | Use OKF as a storage pattern, not as the whole product. |
| [Google's OKF announcement][okf-announcement] | The idea that LLM-maintained wikis can be portable, local, and agent-friendly. | Apply the pattern specifically to coding-agent repo workflows. |
| [Graphify][graphify] | Folder-to-graph and codebase Q&A are useful for orientation. | Focus on task briefs, source citations, and diff-aware maintenance. |
| [Graphify token-savings claim][graphify-token-claim] | Public claim that compiling raw files into a wiki/graph can cut repeated query context dramatically. | Treat as directional evidence, not as a benchmark for this repo. |
| [ByteRover CLI][byterover] | Inspectable, file-based agent memory is better than a black box. | Keep the first version repo-local and lightweight. |
| [ByteRover benchmark][byterover-benchmark] | Published memory-retrieval accuracy and latency numbers for an agent memory system. | Use as adjacent evidence for structured memory, not as a direct `/karpathy:wiki` result. |
| [Karpathy LLM Wiki gist][karpathy-llm-wiki] | The maintained-wiki pattern: raw sources are compiled once into a Markdown knowledge base. | Adapt the pattern to repo workflows, task briefs, and diff-aware updates. |
| [Claude Code plugin docs][claude-plugin-docs] | Marketplace packaging, plugin updates, skills, commands, and hooks. | Package the workflows as installable Claude Code skills. |
| [Codex plugin docs][codex-plugin-docs] | Native Codex plugin manifests and marketplace entries. | Ship the same plugin to Codex without requiring users to copy raw skill files. |

---

## Evaluation Results

`/karpathy:audit` was benchmarked before release. Three `CLAUDE.md` test files
were each audited twice, once with the skill and once with an unaided baseline
(capable Claude, no skill), and scored against 16 objective assertions.

The test files:

| Test File | What It Stressed |
| --- | --- |
| Bloated file | Padded with generic advice, repetition, vague rules, no verification commands. |
| Contradictions + stale content | Two flat contradictions, a vague rule, a dated sprint section. |
| Already-good file | A genuinely lean, well-built file that needs nothing. This is a false-positive test. |

Summary:

| Metric | With karpathy skill | Baseline, no skill | Delta |
| --- | --- | --- | --- |
| Pass rate | 100% | 69% | +31 pts |
| Avg time | 62.1s | 31.1s | +31s |
| Avg tokens | 40,274 | 30,707 | +9,567 |

Per-test breakdown:

| Test File | With Skill | Baseline |
| --- | --- | --- |
| Bloated file | 6 / 6 | 4 / 6 |
| Contradictions + stale content | 6 / 6 | 5 / 6 |
| Already-good file | 4 / 4 | 2 / 4 |
| Total | 16 / 16 (100%) | 11 / 16 (69%) |

What the numbers actually show: the unaided baseline is no fool. It caught the
contradictions and the bloat on its own. Where the skill pulls ahead is
consistency and calibration: it always produces a coverage score,
severity-ranked findings, and the global-vs-project-memory nuance, where the
baseline's review format drifted from run to run.

The most telling case is the third test, the file that was already good. The
baseline rated it "good" but still appended five suggestions and skipped
coverage scoring. The skill returned zero quality findings and "ship as-is."
Not manufacturing work on a healthy file is the hardest behavior to get right,
and it is the clearest thing the skill adds.

Honest caveats: this is one run per cell. It is directional evidence, not a
statistically robust benchmark. The skill also roughly doubles wall-clock time
and adds about 30% more tokens, because it does more work. `/karpathy:diff` is
newer and not yet benchmarked; it follows the same report-then-approve design.

### Diff And Wiki Evidence

`/karpathy:diff` has not been formally benchmarked yet. Anecdotally, it has
been one of the highest-impact parts of this workflow for vibe coding because
it reviews the failure mode that normal review often misses:

```text
Does every changed line trace back to the task?
```

That is a narrower question than "is this code good?" and it is useful because
AI agents often make plausible changes that were never asked for: collateral
file edits, drive-by refactors, quiet deletions, broad reformatting, or missing
verification. The advantage is not that `/karpathy:diff` is smarter than a
strong model. The advantage is that it forces the model to review the diff in a
consistent, task-traceable shape before the user accepts it.

The right benchmark for `/karpathy:diff` would be small and concrete:

| What To Measure | Why It Matters |
| --- | --- |
| Traceability recall | Does it catch hunks that do not belong to the task? |
| Traceability precision | Does it avoid flagging clean hunks that do belong? |
| Collateral-file detection | Does it catch files the task did not require? |
| Deletion review | Does it challenge removed comments or code that do not trace? |
| Verification coverage | Does it notice missing tests or checks? |
| Time and token cost | Is the extra review cost worth the caught issues? |

For `/karpathy:wiki`, there are adjacent public numbers from wiki and memory
systems, but not yet project-specific results for this repo:

| Evidence | Reported Result | What It Suggests | Caveat |
| --- | --- | --- | --- |
| [Graphify token-savings claim][graphify-token-claim] | 71.5x fewer tokens per query versus reading raw files cold. | Compiling raw material into a structured wiki or graph can reduce repeated context loading. | Public community/maintainer claim; not independently reproduced here. |
| [ByteRover benchmark][byterover-benchmark] | 92.8% on LongMemEval-S and 1.6s p50 retrieval latency. | Structured agent memory can be measured for retrieval quality and speed. | Different product and benchmark; not a direct test of `/karpathy:wiki`. |
| [Google OKF announcement][okf-announcement] | No performance number. OKF formalizes Markdown plus YAML frontmatter as an interoperable LLM-wiki format. | The storage pattern is becoming standardized. | OKF is a format, not a complete coding-agent workflow. |

The honest read: external numbers support the product bet, but they do not
prove this implementation. This repo should eventually publish two more
benchmarks: a `/karpathy:diff` traceability suite and a `/karpathy:wiki`
orientation suite that measures whether agents find the right files, preserve
invariants, and spend fewer tokens on repeated repo questions.

---

## Repository Layout

```text
karpathy-skills/
|-- .agents/
|   `-- plugins/
|       `-- marketplace.json      # Codex marketplace catalog
|-- .claude-plugin/
|   `-- marketplace.json          # Claude Code marketplace catalog
|-- docs/
|   `-- repo-knowledge-bases.html # wiki skill rationale and longer-term design
`-- plugins/
    `-- karpathy/
        |-- .codex-plugin/
        |   `-- plugin.json       # Codex plugin manifest
        |-- .claude-plugin/
        |   `-- plugin.json       # Claude Code plugin manifest
        |-- commands/
        |   |-- audit.md          # /karpathy:audit command
        |   |-- diff.md           # /karpathy:diff command
        |   `-- wiki.md           # /karpathy:wiki command
        |-- hooks/
        |   `-- hooks.json        # advisory update-check hook
        |-- scripts/
        |   `-- check_update.py   # shared update checker
        `-- skills/
            |-- karpathy-audit/
            |   `-- SKILL.md
            |-- karpathy-diff/
            |   `-- SKILL.md
            `-- karpathy-wiki/
                |-- SKILL.md
                `-- scripts/
                    `-- wiki_tool.py
```

---

## Release Checklist

When publishing a new version:

1. Update the plugin files.
2. Bump the version in:
   - `.claude-plugin/marketplace.json`
   - `plugins/karpathy/.claude-plugin/plugin.json`
   - `plugins/karpathy/.codex-plugin/plugin.json`
3. Validate:

   ```bash
   claude plugin validate .
   claude plugin validate ./plugins/karpathy
   python3 -m json.tool .agents/plugins/marketplace.json >/dev/null
   python3 -m json.tool plugins/karpathy/.codex-plugin/plugin.json >/dev/null
   python3 -m py_compile plugins/karpathy/scripts/check_update.py
   ```

4. Commit, tag, and push.

---

## Background And Attribution

The four principles are distilled from Andrej Karpathy's public comments about
AI coding agents. This is an independent community tool. It is not affiliated
with, authored by, or endorsed by Andrej Karpathy, Anthropic, OpenAI, Google, or
any related project mentioned above.

[karpathy-post]: https://x.com/karpathy/status/2015883857489522876
[orig-repo]: https://github.com/multica-ai/andrej-karpathy-skills
[okf-spec]: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
[okf-announcement]: https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing
[graphify]: https://github.com/safishamsi/graphify
[graphify-token-claim]: https://www.reddit.com/r/ClaudeCode/comments/1sdaakg/715x_token_reduction_by_compiling_your_raw_folder/
[byterover]: https://github.com/campfirein/byterover-cli
[byterover-benchmark]: https://www.byterover.dev/blog/benchmark_ai_agent_memory_real_production_byterover_top_market_accuracy_longmemeval
[karpathy-llm-wiki]: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
[claude-plugin-docs]: https://code.claude.com/docs/en/plugin-marketplaces
[codex-plugin-docs]: https://developers.openai.com/codex/plugins/build

## License

MIT (c) 2026 Joseph Kim
