# karpathy-skills

A Claude Code plugin marketplace for working better with LLM coding agents,
derived from [Andrej Karpathy's publicly stated observations][karpathy-post]
on where coding agents go wrong.

Currently ships one plugin: **karpathy** — an auditor for your agent
instruction files (`CLAUDE.md`, `AGENTS.md`, Cursor rules).

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

An agent instruction file — `CLAUDE.md`, `AGENTS.md`, a Cursor rule — is itself
something an LLM reads on **every turn**. The same failure modes Karpathy
describes in *generated code* show up in the instruction file just as easily:
it gets bloated with generic advice, it goes stale, it contradicts itself, it
gives instructions too vague to act on.

The `karpathy` plugin audits that file along two independent axes:

- **Coverage** — does the file actually instruct the agent to follow the four
  principles? Each principle is scored Present / Partial / Missing. Behavioral
  principles often belong in a *global* `~/.claude/CLAUDE.md` rather than every
  project file, so a project file scoring low is flagged, not condemned.
- **Quality** — judged *by those same four principles*, is the file itself a
  good artifact? This is the more interesting half: it turns the principles
  back on the instruction file and treats it the way you'd treat code.

It reports findings with severity (Critical / Warning / Nit), says what the
file does well, proposes a concrete diff, and then **stops** — it never edits
the file without your approval.

### How it works

1. Locates the target file (`CLAUDE.md`, then `AGENTS.md`, then a Cursor rule).
2. Runs the **coverage** audit — the four principles, scored with evidence.
3. Runs the **quality** audit — five lenses (below).
4. Writes a structured report: coverage table, severity-ranked findings, a
   "what's good" section, and a proposed diff.
5. Applies the changes only after you approve them — surgically, touching only
   what the findings name.

### The five quality lenses

| Lens | What it flags |
| --- | --- |
| **Simplicity** | Generic advice that restates default model behavior; duplication; a roadmap or changelog living in an every-turn file. |
| **Staleness** | "currently", "for now", "TODO", phase numbers, PR references — content correct today and misleading next month. |
| **Ambiguity** | Instructions the agent can't act on or self-check, like "handle errors appropriately". |
| **Verifiability** | Whether the file names the test / lint / build commands — without them, Goal-Driven Execution is impossible. |
| **Consistency** | Rules that contradict each other, including *latent* contradictions with the four principles. |

It deliberately does **not** flag legitimate project context — architecture
maps, key-file tables, build commands. It audits behavioral guidance and file
hygiene, not whether a given piece of context deserves to exist.

---

## Why not just use the original Karpathy CLAUDE.md repo?

Karpathy's post inspired a popular community repo,
[multica-ai/andrej-karpathy-skills][orig-repo] (100k+ stars), which distills the
same observations into a `CLAUDE.md` file and a Claude Code plugin.

That repo and this one solve **different problems**, and it's worth being
precise about the difference:

- **The original repo distributes the guidance.** It gives you a well-written
  `CLAUDE.md` to drop into a project (or a plugin that installs it) so the agent
  is *told* to follow the four principles. It is excellent at that, and the
  writing is genuinely good.
- **This plugin audits your existing file.** It doesn't hand you a template —
  it reads the `CLAUDE.md` (or `AGENTS.md`) you already have and tells you
  what's wrong with it: missing principle coverage, but also bloat,
  staleness, ambiguity, missing verification commands, and contradictions.
  Then it proposes a concrete diff.

In short: the original is *"here is a good instruction file."* This is *"a
linter for the instruction file you already have."* The original is a one-time
paste; an audit is something you re-run as the file drifts.

They also compose. This plugin embeds an equivalent canonical four-principle
block, so when an audit finds coverage missing it can add the guidance too —
it covers the original repo's use case and adds the diagnostic layer on top.
We built a separate tool rather than forking theirs because the audit workflow,
the quality lenses, and the report-then-approve loop are a different thing from
a static guidelines file — not a tweak to one.

---

## Install

In Claude Code:

```
/plugin marketplace add jokim1/karpathy-skills
/plugin install karpathy@karpathy-skills
```

`/plugin marketplace update` pulls future versions.

## Usage

Run it on a file:

```
/karpathy:audit path/to/CLAUDE.md
```

With no argument it audits `./CLAUDE.md` in the current repo (falling back to
`AGENTS.md`, then `.cursor/rules/*.mdc`). It also triggers automatically when
you ask Claude to "audit my CLAUDE.md" or "check my agent instructions."

---

## Evaluation results

The skill was benchmarked before release. Three `CLAUDE.md` test files were each
audited twice — once with the `karpathy` skill, once with an unaided baseline
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
file is the hardest behavior to get right, and it is the clearest thing the
skill adds.

**Honest caveats.** This is one run per cell — directional evidence, not a
statistically robust benchmark. And the skill is not free: it roughly doubles
wall-clock time and adds about 30% more tokens, because it does more work (the
coverage table, severity ranking, a proposed diff). For an audit you run
occasionally rather than on every turn, that is a fair trade.

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
        │   └── audit.md          # the /karpathy:audit command
        └── skills/
            └── karpathy-audit/
                └── SKILL.md      # the audit logic (also auto-triggers)
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
