# karpathy-skills

A Claude Code plugin marketplace for working better with LLM coding agents,
derived from [Andrej Karpathy's publicly stated observations][karpathy-post]
on where coding agents go wrong.

Currently ships one plugin: **karpathy**, with two tools —
[`/karpathy:audit`](#karpathyaudit--review-your-instruction-file) for your agent
instruction files and [`/karpathy:diff`](#karpathydiff--review-a-change-before-you-commit)
for the code changes an agent produces.

---

## Background: what Karpathy observed

In January 2026, after an extended stretch of agentic coding, Andrej Karpathy
posted a set of observations on how LLM coding agents fail. Excerpts from
[that post][karpathy-post]:

> "The models make wrong assumptions on your behalf and just run along with
> them without checking. They don't manage their confusion, don't seek
> clarifications, don't surface inconsistencies, don't present tradeoffs, don't
> push back when they should."

> "They really like to overcomplicate code and APIs, bloat abstractions, don't
> clean up dead code... implement a bloated construction over 1000 lines when
> 100 would do."

> "They still sometimes change/remove comments and code they don't sufficiently
> understand as side effects, even if orthogonal to the task."

> "LLMs are exceptionally good at looping until they meet specific goals... Don't
> tell it what to do, give it success criteria and watch it go."

Four failure modes, and their fixes, fall out of that:

| Failure mode | Principle |
| --- | --- |
| Silent assumptions, hidden confusion | **Think Before Coding** |
| Overcomplication, bloated abstractions | **Simplicity First** |
| Collateral edits to unrelated code | **Surgical Changes** |
| No verifiable definition of done | **Goal-Driven Execution** |

### The four principles

1. **Think Before Coding** — state assumptions, ask when ambiguous, surface
   tradeoffs, never silently pick one interpretation.
2. **Simplicity First** — write the minimum that solves the problem; no
   speculative abstractions or unrequested features.
3. **Surgical Changes** — touch only what the task requires; no drive-by
   refactors.
4. **Goal-Driven Execution** — define verifiable success criteria up front,
   then loop until they pass.

---

## The `karpathy` plugin

The principles are easy to nod along to and hard to actually hold an agent to.
This plugin operationalizes them at the two points where they matter, with one
tool each:

- **`/karpathy:audit`** works on your *instruction file* — the `CLAUDE.md` that
  shapes how the agent behaves. A setup-and-hygiene tool.
- **`/karpathy:diff`** works on the *code changes* the agent produces — before
  you commit them. A use-it-every-change tool.

Both follow the same contract: they report findings with severity, say what's
already good, propose a concrete fix, and **stop** — neither changes anything
without your approval.

---

### `/karpathy:audit` — review your instruction file

An agent instruction file — `CLAUDE.md`, `AGENTS.md`, a Cursor rule — is itself
something an LLM reads on **every turn**. The same failure modes Karpathy
describes in *generated code* show up in the instruction file just as easily:
it bloats with generic advice, goes stale, contradicts itself, gives
instructions too vague to act on.

`/karpathy:audit` audits that file along two axes:

- **Coverage** — does the file actually instruct the agent to follow the four
  principles? Each is scored Present / Partial / Missing. Behavioral principles
  often belong in a *global* `~/.claude/CLAUDE.md` rather than every project
  file, so a project file scoring low is flagged, not condemned.
- **Quality** — judged *by those same four principles*, is the file itself a
  good artifact? This turns the principles back on the instruction file and
  treats it the way you'd treat code.

The quality audit applies five lenses:

| Lens | What it flags |
| --- | --- |
| **Simplicity** | Generic advice that restates default model behavior; duplication; a roadmap or changelog living in an every-turn file. |
| **Staleness** | "currently", "for now", "TODO", phase numbers, PR references — content correct today and misleading next month. |
| **Ambiguity** | Instructions the agent can't act on or self-check, like "handle errors appropriately". |
| **Verifiability** | Whether the file names the test / lint / build commands — without them, Goal-Driven Execution is impossible. |
| **Consistency** | Rules that contradict each other, including *latent* contradictions with the four principles. |

It deliberately does **not** flag legitimate project context — architecture
maps, key-file tables, build commands.

#### When and how often to run it

`/karpathy:audit` is a **hygiene tool, not a daily one**. Run it:

- **On adoption** — when you first install this plugin on a project, or first
  write a `CLAUDE.md`.
- **After substantial edits** to the `CLAUDE.md` / `AGENTS.md`.
- **On a cadence — roughly monthly.** Instruction files rot: shipped roadmap
  items, stale "current sprint" notes, dead PR numbers. A periodic audit is
  what the *Staleness* lens exists to catch.
- **When the agent starts misbehaving** — making silent assumptions,
  over-building, ignoring conventions. The instruction file is often the cause;
  audit it before blaming the model.
- **Before onboarding someone** to the repo — the `CLAUDE.md` is onboarding
  document number one.

Running it more often than that is overkill — the file simply doesn't change
fast enough to need it. For the change-by-change loop, that's `/karpathy:diff`.

---

### `/karpathy:diff` — review a change before you commit

Where `/karpathy:audit` is occasional, `/karpathy:diff` is for **every change**.
It reviews an in-progress code change — a git diff — before you commit or accept
it. The governing question:

> **Does every changed line trace to the task that was asked?**

Coding agents reliably do more than they were asked: they refactor adjacent
code, reformat, rename, delete comments and code they don't fully understand,
and over-build the part they *were* asked for. None of that is visible if you
accept diffs without reading them — which is how most changes get accepted.
`/karpathy:diff` is the safety net under that, and it matters most for anyone
who leans on the agent rather than reading every line.

#### What it flags

It walks the diff hunk by hunk and sorts each into *traces to the task*,
*doesn't trace*, or *can't tell*. The hunks that don't trace become findings:

| Category | What it catches |
| --- | --- |
| **Collateral files** | Files changed that the task never required. |
| **Drive-by refactors** | Renaming or restructuring working code next to the task but not part of it. |
| **Reformatting / style drift** | Whitespace, quote-style, reordered imports — noise that bloats the diff and hides the real change. |
| **Unexplained deletions** | Comments or code removed that the task never called for — Karpathy's specific complaint. Every deletion is guilty until it traces. |
| **Over-engineering** | Speculative abstraction, unrequested config, error handling for impossible cases, 200 lines where 50 would do. |
| **Missing verification** | A change — especially a bug fix — with no accompanying test or check. |
| **Orphans** | Imports or variables this change left unused. (Cleaning these up is *in* scope — it's the one removal the skill encourages.) |

It calibrates to the repo: if your `CLAUDE.md` sanctions aggressive deletion of
legacy code, the skill respects that and won't flag it. It also never flags the
intended change itself — the work you asked for is supposed to be there.

#### How to use it

```
/karpathy:diff
```

With no argument it reviews **all uncommitted changes** (`git diff HEAD`). You
can point it somewhere specific:

```
/karpathy:diff --staged          # only staged changes
/karpathy:diff main...HEAD       # a branch's worth of changes
/karpathy:diff src/auth/         # changes under one path
```

It also triggers automatically when you ask Claude to "review my changes" or
"check this before I commit."

The review needs to know **what the change was meant to do** — that's the basis
of the trace test. Run inside the session where the change was made, it reads
the task from the conversation. Run cold, it will ask you one question: what was
this change meant to accomplish.

#### When to run it

Run it **before every commit**, or right after the agent finishes a batch of
edits — especially any batch you didn't read line by line. This is the daily
driver of the plugin. A good habit: `/karpathy:diff`, read the findings, apply
the fixes, *then* commit.

#### The report you get

A structured report: the task it's reviewing against, the size of the change, a
**traceability line** (how many hunks trace to the task), severity-ranked
findings (Critical / Warning / Nit) each with a location and a concrete fix, a
**what's clean** section naming the parts that correctly trace, and a list of
proposed fixes. Then it asks before applying anything.

#### Example

You ask the agent to *"add a `lastLogin` timestamp to the user model."*
`/karpathy:diff` might report:

- **What's clean** — `models/user.ts`: the `lastLogin` field and its migration
  trace directly to the task.
- **[Warning] Reformatting** — `models/user.ts`: the agent also reordered every
  import and switched the file from `'` to `"` quotes. *Revert it — it buries
  one real change under 40 lines of noise.*
- **[Critical] Unexplained deletion** — `auth/session.ts`: a comment explaining
  a session-refresh edge case was deleted. The file wasn't part of the task.
  *Restore it.*

Three findings, one of them genuinely dangerous — none of which you'd see if you
just accepted the diff.

---

## Why not just use the original Karpathy CLAUDE.md repo?

Karpathy's post inspired a popular community repo,
[multica-ai/andrej-karpathy-skills][orig-repo] (100k+ stars), which distills the
same observations into a `CLAUDE.md` file and a Claude Code plugin.

That repo and this one solve **different problems**:

- **The original repo distributes the guidance.** It gives you a well-written
  `CLAUDE.md` to drop into a project (or a plugin that installs it) so the agent
  is *told* to follow the four principles. It's excellent at that, and the
  writing is genuinely good.
- **This plugin checks the work.** It doesn't hand you a template — it audits
  the instruction file you already have (`/karpathy:audit`) and the changes the
  agent actually produces (`/karpathy:diff`), and tells you where they fall
  short of the principles.

In short: the original is *"here is a good instruction file."* This is *"tools
that check whether the principles are actually being followed"* — in your config
and in your diffs. The original is a one-time paste; checking is something you
re-run as things drift.

They also compose. `/karpathy:audit` embeds an equivalent canonical
four-principle block, so when it finds coverage missing it can add the guidance
too — it covers the original repo's use case and adds the diagnostic layer on
top. We built a separate plugin rather than forking theirs because an audit
workflow and a diff-review workflow are different things from a static
guidelines file — not a tweak to one.

---

## Install

In Claude Code:

```
/plugin marketplace add jokim1/karpathy-skills
/plugin install karpathy@karpathy-skills
```

`/plugin marketplace update` pulls future versions.

## Usage

```
/karpathy:audit [path]      # audit a CLAUDE.md / AGENTS.md (defaults to ./CLAUDE.md)
/karpathy:diff  [ref/path]  # review a change before committing (defaults to all uncommitted)
```

Both also trigger automatically — `/karpathy:audit` on "audit my CLAUDE.md",
`/karpathy:diff` on "review my changes before I commit."

---

## Evaluation results

`/karpathy:audit` was benchmarked before release. Three `CLAUDE.md` test files
were each audited twice — once with the skill, once with an unaided baseline
(capable Claude, no skill) — and scored against 16 objective assertions.

**The test files:**

| Test file | What it stresses |
| --- | --- |
| **Bloated file** | Padded with generic advice, repetition, vague rules, no verification commands. |
| **Contradictions + stale content** | Two flat contradictions, a vague rule, a dated sprint section. |
| **Already-good file** | A genuinely lean, well-built file that needs nothing — a false-positive test. |

**Summary:**

| Metric | With `karpathy` skill | Baseline (no skill) | Delta |
| --- | --- | --- | --- |
| Pass rate | **100%** | 69% | **+31 pts** |
| Avg time | 62.1s | 31.1s | +31s |
| Avg tokens | 40,274 | 30,707 | +9,567 |

**Per-test breakdown:**

| Test file | With skill | Baseline |
| --- | --- | --- |
| Bloated file | 6 / 6 | 4 / 6 |
| Contradictions + stale content | 6 / 6 | 5 / 6 |
| Already-good file | 4 / 4 | 2 / 4 |
| **Total** | **16 / 16 (100%)** | **11 / 16 (69%)** |

**What the numbers actually show.** The unaided baseline is no fool — it caught
the contradictions and the bloat on its own. Where the skill pulls ahead is
**consistency and calibration**: it always produces a coverage score,
severity-ranked findings, and the global-vs-project-memory nuance, where the
baseline's review format drifted from run to run. The most telling case is the
third test — the file that was already good. The baseline rated it "good" but
still appended five suggestions and skipped coverage scoring; the skill returned
**zero quality findings and "ship as-is."** Not manufacturing work on a healthy
file is the hardest behavior to get right, and it's the clearest thing the skill
adds.

**Honest caveats.** This is one run per cell — directional evidence, not a
statistically robust benchmark. The skill also roughly doubles wall-clock time
and adds about 30% more tokens, because it does more work. `/karpathy:diff` is
newer and not yet benchmarked; it follows the same report-then-approve design.

---

## Repository layout

```
karpathy-skills/
├── .claude-plugin/
│   └── marketplace.json          # marketplace catalog
└── plugins/
    └── karpathy/
        ├── .claude-plugin/
        │   └── plugin.json       # plugin manifest
        ├── commands/
        │   ├── audit.md          # the /karpathy:audit command
        │   └── diff.md           # the /karpathy:diff command
        └── skills/
            ├── karpathy-audit/
            │   └── SKILL.md      # audit logic (also auto-triggers)
            └── karpathy-diff/
                └── SKILL.md      # diff-review logic (also auto-triggers)
```

To add another plugin later, drop it under `plugins/` and add an entry to
`marketplace.json`.

---

## Background and attribution

The four principles distill observations Andrej Karpathy
[posted publicly][karpathy-post] in January 2026. This is an independent,
community tool. It is **not affiliated with, authored by, or endorsed by Andrej
Karpathy or Anthropic.**

[karpathy-post]: https://x.com/karpathy/status/2015883857489522876
[orig-repo]: https://github.com/multica-ai/andrej-karpathy-skills

## License

MIT © 2026 Joseph Kim
