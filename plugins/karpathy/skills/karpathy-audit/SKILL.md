---
name: karpathy-audit
description: >-
  Audit a CLAUDE.md, AGENTS.md, .cursor/rules file, or other AI-agent
  instruction/memory file against Andrej Karpathy's four LLM-coding principles.
  Checks two things: whether the file tells the agent to follow the principles
  (coverage), and whether the file itself is lean, unambiguous, current, and
  contradiction-free (quality). Use this whenever the user wants to review,
  audit, critique, tighten, clean up, or improve a CLAUDE.md / AGENTS.md /
  .cursor/rules / agent memory file, says "karpathy audit" or "/karpathy:audit",
  asks whether their agent instructions are any good, or wants to apply Karpathy
  or vibe-coding guidelines to a project. Trigger even if they just say "check
  my CLAUDE.md" without naming Karpathy.
---

# Karpathy Audit

Audit an AI-agent instruction file (`CLAUDE.md`, `AGENTS.md`, `.cursor/rules/*.mdc`,
or a global memory file) against Andrej Karpathy's four principles for LLM coding.

The audit has two independent halves:

- **Coverage** — does the file actually instruct the agent to follow the four
  principles?
- **Quality** — judged *by the same four principles*, is the file itself a good
  artifact: lean, unambiguous, current, internally consistent?

The second half is the interesting one. An instruction file is itself something
an LLM reads on every turn. The same failure modes Karpathy describes in
generated code — bloat, vagueness, stale cruft — show up in the file just as
easily. Audit it the way you would audit code.

Default to **report first, apply on approval**. Never rewrite the file before
the user has seen the findings and a concrete diff.

Never stage or commit `CLAUDE.md`, `AGENTS.md`, `.cursor/rules`, or other
agent instruction / memory files. You may propose changes, and you may edit
them after explicit approval, but the user decides whether those changes belong
in git.

## Scope: what is NOT a defect

Before flagging anything, be clear about what an instruction file is *for*. A
good instruction file legitimately contains:

- Repo architecture, directory maps, key-file tables
- Build / test / lint / deploy commands
- Domain vocabulary and project-specific conventions
- Decisive project defaults (e.g. "treat local data as disposable")

None of that is bloat. Do not tell the user to delete useful context. This
skill audits *behavioral guidance and file hygiene* — not whether a given piece
of project context deserves to exist. When in doubt, leave it and say so.

## The four principles

1. **Think Before Coding** — State assumptions; ask when the request is
   ambiguous; present tradeoffs; never silently pick one interpretation.
2. **Simplicity First** — Write the minimum that solves the actual problem. No
   speculative abstractions, no unrequested features or configurability.
3. **Surgical Changes** — Touch only what the task requires. No drive-by
   refactors, reformatting, or edits to code you weren't asked to change.
4. **Goal-Driven Execution** — Define verifiable success criteria up front
   (usually a test or a command), then loop until they pass.

## Workflow

1. **Locate and read the target file.** If the user named one, use it. Otherwise
   look for `./CLAUDE.md`, then `AGENTS.md`, then `.cursor/rules/*.mdc`. If none
   exists, say so and offer to draft one — don't audit a file that isn't there.
2. **Run the coverage audit** (below).
3. **Run the quality audit** (below).
4. **Write the report** in the format below. Then stop.
5. **Apply on approval.** Only after the user approves, make the edits —
   surgically. Preserve their headings, voice, and ordering; change only the
   lines the findings name; never reformat the whole file. (Yes — the skill
   itself follows principle 3.) Do not stage or commit the instruction file.

## Coverage audit

For each of the four principles, classify it as **Present**, **Partial**, or
**Missing**, and cite the evidence (a quoted line, or its absence).

Judge by *substance, not wording*. A file that says "ask me before making
assumptions you can't verify" covers principle 1 even though it never says
"Think Before Coding". Don't demand the canonical phrasing. Use **Partial**
when the file reaches a principle only as a side effect — e.g. an anti-legacy
project default that happens to bias toward simplicity, without ever telling
the agent to write the minimum.

**Counting rule:** the "N/4" in the report header counts **Present only**.
Partial does not count toward N; show it in the table but not the score.

Coverage gaps belong in the Coverage section **only**. Never also list a
missing principle as a quality finding — that double-counts. The quality audit
judges the file as an artifact; it does not re-score the four principles.

Important nuance: behavioral principles often belong in the **global**
`~/.claude/CLAUDE.md`, not in every project file — that way they apply
everywhere without being repeated. If you're auditing a project-level file and
coverage is Missing, do not assume it's a defect. Flag it, but ask whether the
principles live in the user's global memory file, and recommend global as the
home for them unless the user wants project-specific overrides.

## Quality audit

Turn each principle back on the file itself. Five lenses:

**Simplicity → is the file bloated?**
Flag content that costs context tokens every turn and earns nothing:

- Generic advice that just restates competent default behavior ("write clean
  code", "use meaningful names", "follow best practices"). A capable model does
  this already; the line is noise and dilutes the instructions that matter.
- The same instruction stated in two places.
- A changelog or roadmap living inside the file — long lists of shipped items,
  struck-through "done" entries, PR numbers. That belongs in `docs/`, not in a
  file loaded on every turn.

**Surgical / staleness → will the file rot?**
Flag content that is correct today and misleading in a month:

- Words like "currently", "for now", "this week", "in flight", "transient", "TODO".
- Dated markers: phase numbers, sprint names, specific PR/commit references.
- Struck-through items left in place after completion.

Recommend moving volatile state out of the file and keeping only durable facts.

**Think Before Coding → is the file unambiguous?**
Flag instructions the agent cannot act on without guessing, or check itself
against: "handle errors appropriately", "make it performant", "keep it clean".
Rewrite each into something concrete and checkable.

**Goal-Driven → can the agent verify its work?**
This lens is narrow and informational: does the file *name the commands* that
prove a change is good — test, typecheck, lint, build? That is distinct from
coverage of principle 4 (the behavioral instruction to define success criteria
and loop). A file can list every command yet never tell the agent to use them
as a loop — only that command gap is reported here; the behavioral gap is a
Coverage row. If the commands are absent, flag it; if present, say so.

**Consistency → do any rules contradict?**
Flag pairs of instructions that can't both be followed (e.g. "never delete
data" alongside "treat local data as disposable"). Contradictions are the worst
defect — they guarantee the agent guesses.

Also flag **latent contradictions**: a project default that would collide with
the four principles once they are added (this skill recommends adding them).
Example: a default that licenses deleting legacy code anywhere vs. principle 3's
"no edits to code you weren't asked to change." Rate these Critical — the
skill's own workflow is about to activate the conflict — and resolve them by
scoping the project default to the task, not by dropping it.

## Lessons block maintenance (pipelane repos)

Pipelane seeds a managed `## Lessons` block in CLAUDE.md (and the capture
instruction in AGENTS.md) delimited by `<!-- pipelane:lessons:start -->` /
`<!-- pipelane:lessons:end -->`, with an append-only entries region inside
`<!-- pipelane:lessons:entries:start -->` / `:entries:end -->`. When the audited
file carries a `pipelane:lessons` marker (or the repo otherwise uses pipelane),
run these extra checks. Skip this section entirely for non-pipelane files.

**Coverage (is the block there?):** If the repo uses pipelane but CLAUDE.md has
no `pipelane:lessons:start` marker, or the marker exists but the capture
instruction prose is gone, flag it and route the fix to `/pipelane setup` — that
command owns and re-syncs the block. Do not hand-write the block yourself.

**Quality (operate INSIDE `lessons:entries` only — never edit the
pipelane-owned instruction prose):**

- **Dedupe** near-identical lessons into one; keep the earliest date.
- **Contradictions** — flag pairs that can't both hold ("always X" vs "never
  X"); keep both dates and surface them, don't silently pick a winner.
- **Stale references** — drop a lesson whose referenced file or symbol no longer
  exists in the repo (verify the absence first).
- **Anti-bloat** — if the entries region exceeds ~40 lines, recommend lifting
  the older or narrowly-conditional lessons into a dedicated skill or doc and
  leaving only the broadly-applicable ones inline.

Pruning entries is the one case where this skill edits a managed region: still
report-first, apply on approval, and preserve the markers plus every remaining
entry verbatim.

## Report format

**Consolidate.** Group repeated instances of one problem into a single finding
— flag "staleness throughout" once, not each PR number separately. A report
padded with twenty nits violates the skill's own values; aim for the few
findings that actually change how the file performs.

Use this structure exactly:

```
# Karpathy Audit — <filename>

**Coverage:** <N>/4 principles present
**Quality:** <N> findings (<N> critical, <N> warning, <N> nit)

## Coverage
| Principle | Status | Evidence |
|-----------|--------|----------|
| Think Before Coding   | Present/Partial/Missing | ... |
| Simplicity First      | ...                     | ... |
| Surgical Changes      | ...                     | ... |
| Goal-Driven Execution | ...                     | ... |

## Quality findings
### [CRITICAL] <title>
- **Location:** <line / section>
- **Issue:** <what is wrong>
- **Why it matters:** <concrete consequence for the agent>
- **Fix:** <specific change>

(repeat per finding; order Critical -> Warning -> Nit)

## What's good
<1-3 things the file does well — be specific. Don't skip this; an audit
that only lists faults is not trustworthy and gives the user no baseline.>

## Proposed changes
<A concrete diff, or an exact before/after for each change you would make.>
```

Severity:

- **Critical** — actively causes bad agent behavior: contradictions (including
  latent ones), no verification commands, instructions vague enough to force
  guessing.
- **Warning** — degrades quality: bloat, staleness, redundancy, ambiguity.
- **Nit** — minor: wording, ordering, formatting.

After the report, ask: "Want me to apply the proposed changes?" Then stop.

## Applying changes

When approved:

- Make the smallest edits that resolve the findings. Do not restructure the
  file or restyle untouched sections.
- If injecting principle coverage, merge — extend a partial section rather than
  duplicating it. Never blindly append a second copy of something already there.
- Prefer recommending the global `~/.claude/CLAUDE.md` as the home for the four
  behavioral principles; only write them into a project file if the user asks.
- When you move volatile content out, put it somewhere sensible (`docs/`)
  rather than deleting it, unless the user says delete.
- Leave `CLAUDE.md`, `AGENTS.md`, `.cursor/rules`, and similar agent files
  unstaged and uncommitted. Tell the user what changed and let them decide
  whether to include it in version control.

## Canonical principles block

When the user wants the four principles written into a file, use this block.
It is deliberately compact — principle 2 applies to it too.

```markdown
## Working principles

- **Think before coding.** State assumptions. When the request is ambiguous,
  ask or present the options — don't silently pick one. Surface tradeoffs and
  push back when a simpler path exists.
- **Simplicity first.** Write the minimum that solves the actual problem. No
  speculative abstractions, unrequested features, or configurability.
- **Surgical changes.** Touch only what the task requires. No drive-by
  refactors, reformatting, or edits to code you weren't asked to change.
- **Goal-driven execution.** Define how success will be verified — a test, a
  command — before implementing, then loop until it passes.
```
