# karpathy-skills

Karpathy Skills turns Andrej Karpathy-inspired AI coding practices into
practical skills that vibe coders can use inside Claude Code and Codex.

The goal is simple: when an AI agent writes code for you, these skills help you
catch the common failure modes before they turn into bugs, bloated code, or
messy commits.

This repo currently ships one plugin, `karpathy`, with two implemented skills:

- `/karpathy:audit` - reviews your AI agent instruction files.
- `/karpathy:diff` - reviews AI-generated code changes before you commit.

It also documents the planned third skill:

- `/karpathy:wiki` - a repo wiki / memory layer for helping agents understand
  the codebase before they edit it.

The wiki skill is designed in detail in
[docs/repo-knowledge-bases.html](docs/repo-knowledge-bases.html), but it is not
implemented in the plugin yet.

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
| `/karpathy:wiki` | Designed, not shipped yet | A local repo wiki that the agent maintains and reads before coding. | Helping the agent understand your project without rereading everything every time. | Faster orientation, better task briefs, less repeated context work. |

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
```

You can also ask in normal words:

```text
audit my AGENTS.md
review my changes before I commit
did the agent touch anything it should not have?
```

Claude Code command form:

```text
/karpathy:audit
/karpathy:diff
```

Human-friendly phrasing that should also trigger the skills:

```text
karpathy audit
karpathy diff
```

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

## Skill 3: `/karpathy:wiki` (Designed, Not Shipped Yet)

### What It Will Do

`/karpathy:wiki` is the planned third skill. It applies Karpathy's LLM knowledge
base pattern to code repositories.

The idea:

- The agent creates a local Markdown wiki for your repo.
- The wiki summarizes components, workflows, tests, risks, and important rules.
- The agent reads the wiki before coding so it does not start from zero every
  time.
- After changes, the agent updates only the affected wiki pages.

This is meant to help vibe coders who want the agent to understand a project
without manually writing and maintaining a big documentation site.

### Why The Command Will Be Simple

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
/karpathy wiki
```

The skill decides what to do based on context.

### Planned User Journeys

| User Enters | Skill Interprets It As | Skill Returns |
| --- | --- | --- |
| `/karpathy wiki` | No wiki exists | A setup prompt for `knowledge/wiki/`. |
| `/karpathy wiki add trial expiration handling` | Coding task | A task brief with files, risks, invariants, and tests. |
| `/karpathy wiki how does auth work?` | Repo question | A cited answer from the wiki and source files. |
| `/karpathy wiki` after code changes | Wiki update | A proposed update to only affected wiki pages. |
| `/karpathy wiki doctor` | Health check | Broken links, stale pages, uncited claims, and proposed fixes. |

### Planned Automation

During setup, the wiki skill should offer:

| Option | Meaning |
| --- | --- |
| Manual only | User runs `/karpathy wiki` when they want it. |
| Remind me when stale | A non-blocking git hook warns when changed files may make wiki pages stale. |
| Auto-update before commit | The agent proposes affected wiki updates before commit. |
| Auto-update after commit | The agent refreshes metadata after commit and leaves changes for review. |

The planned stale reminder is advisory. It should print something like:

```text
Wiki reminder: 2 concepts may be stale.
- Billing Lifecycle: knowledge/wiki/workflows/billing-lifecycle.md
- Billing Test Surface: knowledge/wiki/tests/billing.md

Run:
  /karpathy wiki

Commit is allowed. This reminder is advisory.
```

For the full design, see
[Repo Knowledge Bases for Coding Agents](docs/repo-knowledge-bases.html).

---

## Recommended Workflow

For most vibe coders:

1. Install the plugin.
2. Run `/karpathy:audit` once on your project instructions.
3. Keep using your AI coding agent normally.
4. Run `/karpathy:diff` before accepting or committing AI-generated code.
5. When `/karpathy:wiki` ships, use it before larger tasks so the agent starts
   with better repo context.

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

The planned `/karpathy:wiki` skill follows the LLM wiki pattern: let the agent
maintain a small local Markdown wiki, with citations back to source files, so
repo knowledge accumulates over time.

### Compared To OKF, Graphify, And Memory Tools

Google's Open Knowledge Format (OKF) gives a simple file format for Markdown
knowledge bundles. That is useful, and the planned wiki skill should use it
rather than inventing a competing format.

Graphify-style tools are strong at turning a folder into a graph you can query.
The planned wiki skill is narrower: it is about coding-agent behavior before,
during, and after edits.

ByteRover-style tools are broader agent memory systems. The planned wiki skill
is repo-local, file-based, and tied to the Karpathy audit/diff loop.

---

## Sources And Inspiration

This project is based on several public ideas and tools:

| Source | What We Took From It | What We Changed |
| --- | --- | --- |
| [Andrej Karpathy's public coding-agent observations][karpathy-post] | The core failure modes: silent assumptions, overbuilding, collateral edits, missing verification. | Turned the ideas into runnable audit and diff-review workflows. |
| [multica-ai/andrej-karpathy-skills][orig-repo] | A clear expression of Karpathy-style guidance for agent instruction files. | Built checking tools instead of only distributing guidance. |
| [Open Knowledge Format][okf-spec] | The planned repo wiki should use plain Markdown, YAML frontmatter, links, indexes, and logs. | Use OKF as a storage format, not as the whole product. |
| [Google's OKF announcement][okf-announcement] | The idea that LLM-maintained wikis can be portable, local, and agent-friendly. | Apply the pattern specifically to coding-agent repo workflows. |
| [Graphify][graphify] | Folder-to-graph and codebase Q&A are useful for orientation. | Focus on task briefs, source citations, and diff-aware maintenance. |
| [ByteRover CLI][byterover] | Inspectable, file-based agent memory is better than a black box. | Keep the first version repo-local and lightweight. |
| [Claude Code plugin docs][claude-plugin-docs] | Marketplace packaging, plugin updates, skills, commands, and hooks. | Package the workflows as installable Claude Code skills. |
| [Codex plugin docs][codex-plugin-docs] | Native Codex plugin manifests and marketplace entries. | Ship the same plugin to Codex without requiring users to copy raw skill files. |

---

## Evaluation Results

`/karpathy:audit` was benchmarked before release on three instruction-file test
cases:

| Test File | What It Stressed |
| --- | --- |
| Bloated file | Generic advice, repetition, vague rules, no verification commands. |
| Contradictions + stale content | Contradictory rules, vague guidance, dated sprint notes. |
| Already-good file | A lean file that should be left alone. |

Summary:

| Metric | With `karpathy` Skill | Baseline Without Skill |
| --- | --- | --- |
| Pass rate | 100% | 69% |
| Average time | 62.1s | 31.1s |
| Average tokens | 40,274 | 30,707 |

The important result was not just catching bad files. It was leaving the good
file alone. The skill returned zero quality findings on the already-good file,
where the baseline still invented extra suggestions.

Caveat: this was a small benchmark. It is directional evidence, not a full
academic evaluation. `/karpathy:diff` is newer and has not been benchmarked in
the same way yet.

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
|   `-- repo-knowledge-bases.html # planned wiki skill rationale
`-- plugins/
    `-- karpathy/
        |-- .codex-plugin/
        |   `-- plugin.json       # Codex plugin manifest
        |-- .claude-plugin/
        |   `-- plugin.json       # Claude Code plugin manifest
        |-- commands/
        |   |-- audit.md          # /karpathy:audit command
        |   `-- diff.md           # /karpathy:diff command
        |-- hooks/
        |   `-- hooks.json        # advisory update-check hook
        |-- scripts/
        |   `-- check_update.py   # shared update checker
        `-- skills/
            |-- karpathy-audit/
            |   `-- SKILL.md
            `-- karpathy-diff/
                `-- SKILL.md
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
[byterover]: https://github.com/campfirein/byterover-cli
[claude-plugin-docs]: https://code.claude.com/docs/en/plugin-marketplaces
[codex-plugin-docs]: https://developers.openai.com/codex/plugins/build

## License

MIT (c) 2026 Joseph Kim
