# Karpathy Refactor Skill Plan

## Summary

This plan defines a new `karpathy-refactor` skill and `/karpathy:refactor`
command for the Karpathy plugin.

The skill should review a codebase, subsystem, or proposed refactor through a
Karpathy-inspired lens: small code, explicit invariants, behavior-preserving
steps, minimal framework gravity, and verification after every meaningful
change. It should not be a generic "clean code" or SOLID checklist. DRY,
SOLID, classes, design patterns, and frameworks are useful vocabulary, but the
skill should treat them as diagnostic tools, not commandments.

Four properties distinguish it from a taste-based review:

- **Evidence-grounded.** Candidates are targeted with repo history (churn,
  co-change, fix clusters), not just by reading today's code. Refactoring pays
  off where code actually changes and breaks; cold code rarely earns a slice.
- **Baseline-verified.** Behavior preservation is verified against a recorded
  verification baseline, not asserted — and claimed only for what that
  baseline covers.
- **Scope-honest.** Cross-cutting architectural problems are escalated to an
  architecture-level planning pass, never crammed into a "slice."
- **Autonomous.** One invocation produces one terminal report. Approval gates
  are replaced by mechanical gates — scorecard rules, baseline verification,
  auto-revert. Human stops are reserved for what machines genuinely cannot
  decide.

Analyze-shaped requests produce a report only. Act-shaped requests run the
full loop unattended: plan, apply auto-apply-lane candidates up to the per-run
slice budget (one or two slices, or one ladder — workflow step 8), verify, and
report what happened. Qualified candidates beyond the budget are not applied;
they land in the report's Slice Ladder with the exact follow-up invocation.

## Product Thesis

Refactoring fails when it is driven by taste without a concrete problem, or when
an agent edits adjacent code because it noticed something ugly. The skill should
make refactoring inspectable:

- Identify the actual complexity or architectural risk, with evidence from the
  repo's history where available.
- Name the invariant that must be preserved.
- Record the verification baseline before touching anything.
- Propose the smallest behavior-preserving slice.
- Verify the slice against the baseline with tests, type checks, builds, or
  manual checks — and revert it if verification fails.
- Run a trace review after edits so the final diff only contains the approved
  refactor.

Approval prompts in refactor tooling compensate for unverifiability. This
skill makes every slice checkable and revertible, so attended operation adds
friction without decision value: the worst case of an autonomous run is a
report and an unchanged tree, not a broken codebase. Verifiable work is
exactly where autonomy is justified.

The core question:

```text
What complexity can we remove or make obvious without changing behavior?
```

And its qualifier:

```text
...in code whose history shows the complexity is actually costing us.
```

## Product Boundary

This skill is a **refactor executor**, not an architecture planner. The
boundary:

- In scope: scoped, behavior-preserving improvement of a subsystem, module, or
  proposed change — evidence, baseline, gated slices, verified apply, terminal
  report.
- Out of scope: whole-repo restructure planning, migration paths across many
  modules, boundary redesigns whose blast radius is cross-cutting.

When a finding exceeds a behavior-preserving slice, the skill emits an
**escalation**: a short statement of the architecture-scale problem and its
evidence, with a recommendation to run an architecture-level planning pass
(the repo's own rethink/architecture tooling if it has one). It does not write
that plan itself. Conversely, when such a plan exists and the user asks for a
stage of it, each stage is exactly the slice-sized work this skill executes.

**Execution handoff at scale.** In-session apply is for what fits one sitting
and one baseline: one or two slices, or one ladder walked rung by rung. A
multi-candidate campaign — several independent candidates, a long ladder the
user wants executed end to end, a red-baseline test-first program — is better
executed by the repo's orchestrator when one exists (isolated worktrees, fresh
context per slice, blocking review gates). For that case the skill emits an
executor-agnostic plan: each candidate's contract block is self-contained
(invariant, verification commands, re-baseline-at-start instruction, trace
expectation), slices are ordered sequentially, and parallel execution is
marked safe only for disjoint scopes — refactors move structure, the worst
case for parallel merges. The difference between the two paths is isolation
and scale, not permission: both run autonomously within the same gates.

Keeping the boundary tight is what lets each tool be good at its job.

## Source Basis

This skill is inspired by public Karpathy writing and code style, not by a
literal claim that he has published a complete refactoring doctrine.

Primary source signals:

- [Sequoia Ascent 2026](https://karpathy.bearblog.dev/sequoia-ascent-2026/)
  describes AI coding agents as useful but prone to bloated, awkward code, with
  humans still responsible for aesthetics, judgment, taste, and oversight.
- [MenuGen](https://karpathy.bearblog.dev/vibe-coding-menugen/) shows the kind
  of architectural invariant a refactor skill should catch: payment/account
  identity must use a durable user identity, not fragile email matching.
- [A Recipe for Training Neural Networks](https://karpathy.github.io/2019/04/25/recipe/)
  maps directly onto refactoring, and two of its steps are load-bearing here:
  "become one with the data" becomes *read the repo's history — churn,
  co-change, fix clusters — before judging its architecture*, and "get dumb
  baselines before improving" becomes *record the verification baseline before
  the first edit*. Start simple, avoid unverified complexity, make hypotheses,
  validate after each step.
- [Verifiability](https://karpathy.bearblog.dev/verifiability/) argues that
  automation works best when attempts are checkable. This is both the reason
  refactors are decomposed into baseline-checked slices and the reason the
  skill can run unattended: checkable, revertible attempts do not need a
  human confirm.
- [The Unreasonable Effectiveness of RNNs](https://karpathy.github.io/2015/05/21/rnn-effectiveness/)
  includes a pragmatic framework lens: abstractions should improve iteration,
  debugging, transparency, and flexibility. This is the test behind the
  required per-candidate payoff line.
- Reference implementations such as
  [microgpt](https://karpathy.github.io/2026/02/12/microgpt/),
  [nanoGPT](https://github.com/karpathy/nanoGPT),
  [minGPT](https://github.com/karpathy/minGPT),
  [micrograd](https://github.com/karpathy/micrograd), and
  [llama2.c](https://github.com/karpathy/llama2.c) all favor small,
  inspectable, hackable implementations over large framework-heavy systems.
- Public X posts surfaced in the research call out AI-agent failure modes such
  as changing or removing comments and code as side effects, bloated
  abstractions, and excessive copy-paste.

## User Stories

The skill should handle requests like:

- "Review this service for a refactor." (report run)
- "Does this codebase need DRY/SOLID cleanup?" (report run)
- "This React app feels overabstracted. What would you simplify?" (report run)
- "Should this module be split into classes?" (report run)
- "Where does refactoring actually pay off in this repo?" (report run)
- "Simplify `src/payments`." (autonomous run)
- "Refactor this module — keep behavior identical." (autonomous run)
- "Clean up the framework bloat in `src/auth`." (autonomous run — fence and
  isolation slices may auto-apply; framework *removal* candidates land in the
  report lane by rule, and the run's first marker says so)
- "Apply R1 and R2 from the report." (autonomous run, named candidates)
- "Did the refactor stay within scope?" (trace review)
- "Is this too big for a refactor — does it need an architecture pass?"

## Relationship To Existing Skills

`karpathy-refactor` should complement the current plugin instead of duplicating
it:

| Existing skill | Role | Relationship |
| --- | --- | --- |
| `karpathy-audit` | Reviews agent instruction files and repo docs | Refactor does not audit instructions. It may read `AGENTS.md` / `CLAUDE.md` for repo rules. |
| `karpathy-diff` | Reviews a completed diff for traceability | Refactor's apply loop ends by reusing diff's trace mechanics with the candidate contract file as the task; untraceable hunks are reverted. |
| `karpathy-wiki` | Maintains repo knowledge and task orientation | Refactor reads wiki pages when present (verifying claims against source), and records its verdicts — applied, reverted, rejected, do-not-refactor — to the ledger by default so future runs don't re-litigate them. |
| `karpathy-update` | Updates the plugin | No overlap. |

Outside the plugin: repos may have their own architecture-planning tooling
(escalation target) and their own orchestration tooling (execution target at
scale). See Product Boundary.

## Skill Surface

### Skill Name

```text
karpathy-refactor
```

### Command

```text
/karpathy:refactor [scope]
```

Suggested command aliases in normal language:

- `karpathy refactor`
- `review this architecture for refactoring`
- `plan a refactor of this subsystem`
- `simplify this subsystem`
- `DRY/SOLID review`
- `find overengineering`
- `where does refactoring pay off`

### Optional Modes

Modes stay implicit through user phrasing (see Autonomy Model). A later
version can add explicit override flags if real usage shows the routing
misfires:

```text
/karpathy:refactor src/auth              # routed by phrasing
/karpathy:refactor --report-only src/auth
/karpathy:refactor --apply src/auth
/karpathy:refactor --candidate R2
```

Avoid adding flags until real usage proves they reduce confusion.

## Autonomy Model

The skill runs unattended. Visibility comes from heads-up markers in the
transcript, not from stops. **Invocation is consent**: an act-shaped request
authorizes applying candidates that pass the mechanical gates, up to the
per-run slice budget. The budget governs; overflow goes to the Slice Ladder.

### Intent routing

Never ask which mode the user wants. Infer it from phrasing and state the
inference in the first marker line:

- **Analyze-shaped** — "review", "evaluate", "audit", "should this be split",
  "where does refactoring pay off" → **report run**. No edits.
- **Act-shaped** — "refactor", "simplify", "clean up", "apply", "remove the
  bloat" → **autonomous run**: evidence → baseline → candidates → apply the
  auto-apply lane → verify → terminal report.
- **Ambiguous** → report run. A report is a complete deliverable, not a stop.
  It ends with the exact follow-up invocation that would execute — a pointer,
  never a blocking question.

### The two lanes

The scoring rules (workflow step 8) sort every candidate mechanically:

- **Auto-apply lane** — applied without asking: behavior-preserving;
  verifiability strong, or partial with a test-first prelude inside the same
  slice; risk low or medium; blast radius local or subsystem; payoff named;
  green baseline available. Hot-path slices qualify only when a benchmark is
  runnable as part of verification.
- **Report lane** — never applied autonomously; lands in the terminal report
  with its lane reason: weak verifiability without a test-first path, high
  risk, cross-cutting blast radius (escalate), behavior-changing, framework
  removal, hot path without a runnable benchmark, or a red baseline that
  characterization tests cannot cover.

The run never pauses on a report-lane candidate. It applies what qualifies
and reports the rest.

### Heads-up markers

`[refactor]` markers make every load-bearing action visible without stopping.
The transcript is the audit trail:

```text
[refactor] Mode: autonomous — phrasing "simplify src/auth"
[refactor] Baseline: npm test → 212 passed, 0 failed
[refactor] Applying R1 (inline): collapse OneShotAdapter into its caller
[refactor] Touching sensitive area — auth: R1 moves session-refresh helper; no contract change
[refactor] Verified R1: baseline reproduced
[refactor] Reverted R2: npm test 210/212 — pre-slice state restored
[refactor] Chose module split over class extraction for R3: reversible, no state to own
[refactor] Escalation: payments/orders boundary is cross-cutting — architecture pass recommended
[refactor] Ledger updated: <path>
```

Sensitive areas (auth, migrations, security boundaries, CI, code adjacent to
public interfaces) get a mandatory marker before mutation — a heads-up, not a
gate. Changes that would *alter* a public interface are not behavior-preserving
and belong in the report lane regardless.

In sensitive areas, auto-apply additionally requires verifiability **strong**
from pre-existing repo tests. The partial + test-first-prelude path routes to
the report lane there: agent-written characterization tests verify what the
agent noticed, and security properties are exactly what they miss. The marker
still fires on every sensitive-area mutation.

### No mid-run questions

"Should I proceed?" is never asked; the invocation already answered it. At a
genuine fork between two legitimate designs, pick the reversible one and
record the choice with a marker. A clarification question is permitted only
when the options are materially different and neither is a reversible default
— expected to be rare.

### Auto-revert

Snapshot the worktree before each slice. On verification failure, rerun once
to detect flake. A persistent failure restores the exact pre-slice state,
marks the slice reverted, and stops dependent rungs (independent candidates
may continue). A fail-then-pass rerun marks the suite unstable: cap
verifiability at partial for remaining rungs and say so.

### Snapshot mechanics

"Record the patch" is not enough — the unchanged-tree guarantee rests on
these mechanics, so they are specified, not implied:

- **Recorded per slice:** the tracked diff vs `HEAD` (rename-aware, binary-safe
  — `git diff --binary --find-renames`) and the untracked-file list
  (`git ls-files --others --exclude-standard`). The staged/unstaged distinction
  is not preserved; say so once in the report when the index was non-empty.
- **Restore =** delete untracked files the slice created (present now, absent
  from the pre-slice list) → restore the slice's tracked files → re-apply the
  pre-slice patch. Never `git checkout -- .` or stash the whole tree: the
  user's own uncommitted edits must survive a revert byte-for-byte.
- **Dirty tree at invocation** is allowed. Record the pre-run patch and include
  per-slice patches in the terminal report so the user can separate their own
  edits from the run's.
- **Concurrent human edits during the run:** if the reverse-apply fails, stop
  loudly, leave the tree as-is, and mark the slice unrevertable in the report.
  Never force a restore over live edits.
- **Scratch state** (contract file, snapshots, untracked-file lists) lives in
  one run-scoped scratch directory outside the repo. A new invocation that
  finds stale scratch state from an interrupted run says so in its first
  markers before doing anything else.
- **Scope of the guarantee:** it covers the worktree. Verification commands
  with external side effects (databases, caches, snapshot-test auto-updates,
  local services) are outside it — flag side-effectful suites in the report.
- Submodules and lockfiles are restored like any tracked file, but a slice
  that touches them is a smell — note it.

Slice lifecycle:

```text
            ┌─ contract += Rn
            ▼
      SNAPSHOT (tracked diff + untracked list)
            ▼
        apply Rn ──▶ verify vs baseline ──▶ pass ──▶ next rung / trace review
                           │
                        fail once
                           ▼
                      flake rerun ──▶ pass ──▶ suite unstable: cap partial,
                           │                   remaining rungs → report lane
                        fail again
                           ▼
      RESTORE (delete created files → restore tracked → re-apply pre-slice)
                           ▼
             [refactor] Reverted Rn; dependent rungs stop
```

### Downgrades, not stops

The run halts early only on user interrupt. Everything else is an announced
downgrade:

- No runnable verification → report run; verifiability capped at weak.
- Red baseline → test-first slices only, or report run when characterization
  tests cannot cover the target.
- Unstable suite → remaining rungs move to the report lane.

### Commits

Never stage or commit automatically. Slices are snapshot-managed in the
working tree; the final diff is the user's to commit. A `--commit-each`
opt-in is an open decision.

## Core Doctrine

The skill should teach the agent these rules:

1. Refactor only around a named problem.
2. Ground every candidate in evidence: a structural observation plus either
   user-named pain or repo history (churn, co-change, repeated fixes). Cold
   code needs a stronger reason — correctness or security risk, or the user
   naming the pain.
3. Preserve behavior unless the user explicitly asks for behavior change.
4. Record the verification baseline before the first edit. A red or missing
   baseline blocks any behavior-preservation claim.
5. Invocation is consent. Act-shaped requests authorize applying gated slices;
   visibility comes from heads-up markers, never from mid-run approval stops.
6. Mechanical gates replace human gates: the scoring rules, the baseline
   check, and auto-revert are the approval mechanism.
7. Every applied slice is revertible: snapshot before, verify after, restore
   on persistent failure. The worst case of a run is a report and an
   unchanged tree.
8. Read the source before judging the architecture.
9. Find the invariant before moving code.
10. Prefer deleting or inlining weak abstractions over adding new ones.
11. Treat DRY as a timing question: duplication is bad when the concept is
    stable, but useful when concepts are still diverging.
12. Treat SOLID as design questions, not a checklist.
13. Treat design patterns as names for already-existing forces, not goals.
14. Treat classes as useful when they own state, lifecycle, polymorphism, or an
    invariant. Otherwise a function or module may be clearer.
15. Treat frameworks as justified only when they buy leverage greater than their
    conceptual and operational cost.
16. Name the payoff: every candidate states the concrete future change it makes
    easier (iteration, debugging, transparency, flexibility). No payoff, no
    refactor.
17. Escalate, don't stretch: cross-cutting problems get an architecture-pass
    recommendation, not a bigger slice.
18. Degrade loudly: when verification commands or git history are unavailable,
    say so in one visible line and downgrade the affected scores. Never proceed
    as if verified.
19. Include a "Do Not Refactor" section for ugly but stable code.

## Review Workflow

### 1. Establish Scope

If the user names a path, use it. If not, infer a narrow scope from the request
and say what scope is being reviewed. Ask only when the scope cannot be inferred
without a risky guess.

Small targets get a proportionate run: a user-named function or file satisfies
the evidence rule through named pain (doctrine rule 2), and the architecture
map may be three lines. The non-negotiables do not shrink with the target:
baseline before edits, verification after.

Capture:

- Target files or subsystem.
- Intent routing verdict: report run or autonomous run, and the phrasing that
  decided it.
- Whether behavior may change (default no).
- Current pain: velocity, defects, onboarding, framework cost, duplication,
  unclear ownership, performance, tests, or deployment risk.
- Required verification commands (tests, typecheck, build, manual checks) —
  these become the baseline surface.

### 2. Calibrate To Repo Rules And Prior Verdicts

Read project instruction files if present:

- `AGENTS.md`
- `CLAUDE.md`
- `.cursor/rules/*.mdc`
- local docs or wiki pages that describe the subsystem

Use repo-specific rules over generic taste. If the repo says legacy code is
disposable, that affects recommendations. If the repo says migrations are
append-only, that constrains refactors.

Also read the refactor ledger if one exists (a wiki page or docs file from a
previous run). Prior verdicts carry: rejected candidates are not re-proposed
without new evidence, and deferred or do-not-refactor entries stay deferred
unless the user unfreezes them.

### 3. Gather Evidence

Before judging the architecture, read its history. Plain git commands — no
helper script required:

- **Churn.** `git log --no-merges --since="90 days ago" --name-only
  --pretty=format:` restricted to the scope; count commits per file. Overlay
  the last 30 days for recency.
- **Co-change coupling.** From the same log, find file pairs that repeatedly
  change in the same commit. Pairs that cross module boundaries are direct
  evidence a boundary is wrong.
- **Fix clusters.** Count fix-shaped commits per file (`git log --no-merges
  --grep` on fix/revert/bug terms). Files that keep needing fixes are defect
  attractors — the highest-ROI refactor targets.

Evidence hygiene — bad inputs fabricate coupling:

- Always `--no-merges`; a merge commit's file list is not co-change evidence.
- Skip commits touching more than ~30 files for co-change counting (bulk
  renames and format sweeps couple everything to everything).
- Exclude lockfiles and generated paths from churn and co-change counts.
- Label fix-cluster counts as a commit-message heuristic in the report —
  message conventions vary by repo.
- Note the applied exclusions in the report's History window line.

Interpretation rules:

- Hot + complex = the candidate pool. Churn × complexity is where refactoring
  pays for itself.
- Cold code, however ugly, defaults to "Do Not Refactor" unless doctrine
  rule 2's stronger reasons apply.
- Shallow or missing history: say so in one line, downgrade evidence claims,
  and fall back to structural observation plus user-named pain.

### 4. Build An Architecture Map

Before writing findings, identify:

- Entrypoints.
- Core data flow.
- State ownership.
- Side effects.
- External services and frameworks.
- Module boundaries.
- Public APIs.
- Tests and verification surfaces.
- Invariants that must not break.

The map can be short. It exists to prevent taste-only findings, and it should
note where the evidence from step 3 concentrates.

### 5. Baseline The Verification Surface

Run the verification commands captured in step 1 and record the results
verbatim (pass/fail counts, exit codes). This happens before any edit:

- A green baseline is the reference every applied slice must reproduce.
- A red baseline is load-bearing information: behavior preservation cannot be
  claimed against it. Announce it and downgrade — test-first slices only, or
  report run (see Autonomy Model).
- Scope the redness: failures outside the target's verification surface are
  recorded, announced with a marker, and excluded from the baseline surface —
  an unrelated red test elsewhere in the repo does not downgrade the run.
- Only non-interactive commands count as verification. A manual-only check
  cannot run unattended: it caps that candidate's verifiability at weak
  (report lane) unless the check is mechanized into a command.
- No runnable verification: announce it, cap every candidate's verifiability
  at weak, and downgrade to a report run.

### 6. Apply Refactor Lenses

Use these lenses while reading code:

| Lens | Question |
| --- | --- |
| History | What do churn, co-change, and fix clusters say this code actually costs? |
| Invariant clarity | What must always be true, and is that visible in code? |
| Ownership | Which module owns state, lifecycle, persistence, and side effects? |
| Abstraction weight | Is the abstraction smaller than the problem it hides? |
| Duplication | Is this one stable concept repeated, or two concepts still diverging? |
| Class design | Does each class own real state or behavior, or is it a namespace? |
| SOLID | Which principle exposes a concrete risk, and which would add ceremony? |
| Design patterns | Is a pattern already latent, or would adding one create indirection? |
| Framework gravity | Is framework glue heavier than product logic? |
| Data boundaries | Are identity, authorization, money, persistence, and migrations explicit? |
| Verification | Can the proposed change be verified behavior-preserving against the baseline? |

### 7. Classify Candidates

Every recommendation should fit one of these categories:

| Type | Meaning |
| --- | --- |
| Delete | Remove code, layer, config, or dependency that has no current job. |
| Inline | Collapse an abstraction that hides more than it helps. |
| Extract | Pull out duplicated stable logic into one primitive. |
| Split | Separate responsibilities that change for different reasons. |
| Fence | Put vendor, framework, IO, or unstable code behind a thin boundary. |
| Rename | Make the invariant or ownership obvious. |
| Move | Put code where callers and maintainers expect it. |
| Test first | Add characterization tests before moving risky behavior. |
| Escalate | Problem exceeds behavior-preserving slices; recommend an architecture-level planning pass. |
| Leave alone | Document why ugly code should not be touched in this pass. |

### 8. Score Candidates

Use a small scorecard:

| Field | Values |
| --- | --- |
| Impact | low, medium, high |
| Risk | low, medium, high |
| Verifiability | strong, partial, weak |
| Blast radius | local, subsystem, cross-cutting |
| Confidence | low, medium, high |
| Lane | auto-apply, report, escalate |

Scores are the autonomy policy, not decoration. Hard rules:

- Auto-apply requires verifiability strong, or partial with a test-first
  prelude inside the same slice.
- Sensitive areas (auth, migrations, security boundaries, CI, public-interface
  adjacency): auto-apply requires verifiability strong from pre-existing repo
  tests — the prelude path routes to the report lane there.
- Risk high is never auto-apply; it goes to the report lane with the
  de-risking step named.
- Verifiability weak with risk medium or higher: report lane, or convert to
  test-first.
- Blast radius cross-cutting: the type becomes Escalate. It is never a slice.
- Missing payoff line: cut the finding or move it to Do Not Refactor.
- Hot path without a runnable benchmark: report lane.

Apply at most one or two slices per run — or one ladder, walked rung by rung,
each rung individually gated and revertible. The budget wins over lane
membership: auto-apply-lane candidates beyond it are not applied — they land
in the Slice Ladder with the exact follow-up invocation. A run trying to apply
ten candidates is slipping into generic cleanup.

### 9. The Autonomous Apply Loop

Autonomous runs only. For each auto-apply-lane candidate, in ladder order:

1. Append the contract — candidate id, invariant, verification commands,
   recorded baseline — to a scratch contract file. Long apply sessions drift;
   the contract is the fixed reference.
2. Emit `[refactor] Applying Rn (<type>): <one-line>`.
3. Snapshot the worktree state (record the patch).
4. Apply only the named candidate. Run the test-first prelude first when the
   lane rules require it. Avoid formatting churn and unrelated cleanup.
5. Run verification and compare against the recorded baseline — not against a
   general sense of green. The comparison is two-part: the pre-existing
   surface must reproduce the recorded baseline, and tests added by the slice
   must pass. Benchmarks count as verification on hot paths. When the repo
   supports test targeting, scoped tests may verify each rung with the full
   baseline surface rerun once after the last rung; flake reruns double
   worst-case suite time — say so in the report when it bites.
6. Pass → `[refactor] Verified Rn`; continue to the next rung. Fail → flake
   rerun; persistent failure → restore the snapshot, emit
   `[refactor] Reverted Rn`, stop dependent rungs.
7. After the last rung: trace review of the full applied diff against the
   contract file, reusing `karpathy-diff`'s trace-test categories (traces /
   doesn't trace / can't tell) with the contract as the task. In this loop
   "can't tell" is treated as "doesn't trace": the hunk is reverted and noted.
   karpathy-diff's report-first / fix-on-approval protocol and its
   ask-on-can't-tell rule do not apply inside an autonomous run.
8. Update the refactor ledger (default on) — see "The refactor ledger" below.
9. Produce the terminal report.

### The refactor ledger

Every run writes the ledger — for a report run it is the run's only write,
and the report discloses it. Each entry records: date, mode, scope, candidate
id + title + type, verdict (applied, reverted, rejected, **proposed**,
do-not-refactor), the commit hash at run time, the evidence window, and — for
proposed or unapplied candidates — the contract block (invariant +
verification commands), so a later session can resolve "apply R1 from the
report" without the original transcript. Verdicts expire mechanically: new
evidence postdating the recorded commit unfreezes an entry. Location:
`knowledge/wiki/refactor-ledger.md` when `karpathy-wiki` is present (a
dedicated page genre, exempt from the concept template and doctor checks),
else `docs/refactor-ledger.md`.

### 10. Produce The Terminal Report

One report per run, at the end. Report runs omit Applied/Reverted; autonomous
runs include them.

```markdown
# Karpathy Refactor Report

**Mode:** <report | autonomous — phrasing "<...>">
**Scope:** <path/subsystem>
**Baseline:** <command → recorded result; or "not runnable — verifiability capped at weak">
**History window:** <e.g. 90 days / N commits; or "shallow history — evidence degraded">

## Architecture Map
<entrypoints, data flow, ownership, invariants>

## Evidence
<churn leaders, cross-module co-change pairs, fix clusters — with counts>

## Applied
### [R1] <title> — verified
<what changed, verification result vs baseline>

## Reverted
### [R2] <title>
<which check failed; pre-slice state restored>

## Needs A Human
### [R3] <title>
- Type / Impact / Risk / Verifiability / Blast radius
- Evidence: <files/functions + history signal>
- Issue: <concrete problem>
- Payoff: <the specific future change this makes easier>
- Lane reason: <high risk / weak verifiability / behavior-changing / hot path without benchmark>

## Slice Ladder
<the next 2–3 slices unlocked by what was applied — trajectory, not commitment>

## DRY / SOLID / Patterns
<where they help and where they would make the code worse>

## Do Not Refactor
<code that looks imperfect but should stay untouched, including cold code that
failed the evidence bar>

## Escalations
<cross-cutting problems needing an architecture-level plan — omit when none>

## Next
<report runs: the exact invocation that would execute the auto-apply lane;
autonomous runs: the diff left in the working tree and a suggested review step>
```

The Next section is a pointer, never a blocking question.

## Design Guidance Details

### Evidence And Cold Code

The skill should not equate "worst-looking code" with "best refactor target."

Good target profile:

- High churn or fix density, and structurally confusing.
- Cross-module co-change showing a boundary in the wrong place.
- User-named pain corroborated by the history.

Bad target profile:

- Ugly but cold: untouched for months, no defect trail, no named pain. This is
  Do Not Refactor material — polishing it spends risk for zero return.
- Hot but trivially simple: churn from healthy feature work, not structural
  cost.

### DRY

The skill should not blindly remove duplication.

Good DRY candidate:

- Same concept.
- Same invariant.
- Same change cadence.
- Same tests should cover both occurrences.

Bad DRY candidate:

- Similar code with different business meaning.
- Two flows likely to diverge.
- Abstraction would require flags, callbacks, or configuration branches.
- Extracting would hide the thing maintainers need to see.

### SOLID

The skill should translate SOLID into concrete questions:

- Single Responsibility: What reason to change is mixed with another?
- Open/Closed: Is extension actually recurring, or speculative?
- Liskov: Are subclasses substitutable in tests and runtime behavior?
- Interface Segregation: Are callers forced to depend on methods they never use?
- Dependency Inversion: Does inversion clarify a boundary, or just add ceremony?

If a principle does not expose a concrete risk, do not cite it as a finding.

### Classes

Classes are good when they own:

- Mutable state.
- Lifecycle.
- Polymorphic behavior.
- A domain invariant.
- Resource management.
- A stable interface with multiple implementations.

Classes are suspicious when they are:

- Static namespaces.
- One-method wrappers.
- Data bags with no invariant.
- Adapters around adapters.
- Required only because a framework prefers them.

### Design Patterns

Patterns should be used only when they name a real pressure in the code.

Good pattern finding:

- "This is already a strategy problem; the conditional is growing across three
  independently tested policies."

Bad pattern finding:

- "Use Strategy because design patterns are cleaner."

The skill should prefer describing the underlying pressure over naming the
pattern.

### Frameworks

Framework critique should be pragmatic:

- What does the framework buy?
- What concepts does it force into the code?
- Can engineers debug through it?
- Can tests run without it?
- Is framework glue outgrowing domain logic?
- Could a thin adapter isolate it instead of replacing it?

The skill should recommend framework removal only when there is a clear smaller
path and verification coverage — and framework removal is always report-lane,
never auto-applied.

### Performance

Refactoring is not optimization, but it must not silently deoptimize. When a
slice touches a hot path, the benchmark joins the verification surface; if no
benchmark is runnable, the slice goes to the report lane. There are no mid-run
waivers — a waiver requires the user, so it belongs in Needs A Human.
Everywhere else, performance neutrality is assumed under behavior preservation
and does not need ceremony.

## Implementation Plan

### Phase 1: Planning Doc

Add this document to `docs/`.

Acceptance criteria:

- The plan names the skill, command, workflow, resource shape, test plan, and
  launch criteria.
- The plan is explicit about intent routing, the two lanes, markers,
  auto-revert, and the no-mid-run-questions rule.
- The plan is explicit about the evidence step, the baseline step, scoring
  rules as the autonomy policy, the escalation boundary, and the ledger.

### Phase 2: MVP Skill And Command

Add:

```text
plugins/karpathy/skills/karpathy-refactor/SKILL.md
plugins/karpathy/commands/refactor.md
```

MVP contents:

- Lean `SKILL.md` under 500 lines, enforced by a contract test. Compression
  strategy: one home per rule (doctrine states it, workflow references it);
  tables over prose. If required criteria genuinely do not fit, move Design
  Guidance Details to a `references.md` in the skill directory read on demand.
  Never drop criteria to fit the budget.
- No bundled script yet; the evidence step uses plain git commands.
- Command file that invokes the skill and passes the optional scope.
- Packaging surface, named in full: README (all command lists),
  `.claude-plugin/plugin.json` (description), `.codex-plugin/plugin.json`
  (description + `interface.defaultPrompt`), and root
  `.claude-plugin/marketplace.json` (description). Each mentions
  `/karpathy:refactor`.

MVP acceptance criteria:

- Trigger description includes refactoring, architecture review, DRY/SOLID,
  design patterns, classes, frameworks, overengineering, simplification, and
  hotspot/evidence phrasing.
- Skill body includes intent routing by phrasing and states the consent rule
  (invocation is consent; never ask permission to proceed mid-run) — phrased
  without the literal banned strings, so the negative contract test stays a
  plain substring check.
- Skill body includes the evidence step (churn, co-change, fix clusters) with
  the cold-code rule.
- Skill body includes the baseline step, the red-baseline downgrade, and the
  no-verification downgrade.
- Skill body includes the two lanes with the hard gating rules.
- Skill body includes the `[refactor]` marker vocabulary, including the
  sensitive-area heads-up.
- Skill body includes snapshot-before-slice, the flake rerun, and auto-revert.
- Skill body includes the payoff field, the Escalate type, and the slice
  ladder.
- Skill body includes the contract-file and trace-review steps, and the
  ledger default-write.
- Skill body includes the terminal report format with Applied / Reverted /
  Needs A Human sections and a non-blocking Next section.
- Skill includes "Do Not Refactor" as a required report section.
- Skill says never to stage or commit automatically.
- Skill body includes the snapshot-mechanics spec (recorded state, restore
  algorithm, dirty-tree rule, concurrent-edit stop, scratch location +
  stale-run detection, worktree-scoped guarantee).
- Skill body includes the sensitive-area strong-verifiability rule.
- Skill body includes the verification semantics: two-part baseline
  comparison for test-first slices, non-interactive-commands-only, scoped
  red-baseline handling.
- Skill body scopes the karpathy-diff reuse to trace-test categories with
  can't-tell treated as doesn't-trace.
- Skill body includes the ledger schema (verdicts incl. proposed, commit
  hash, evidence window, contract blocks) and its wiki-first location.
- Skill body includes the evidence-hygiene rules (--no-merges, bulk-commit
  skip, lockfile/generated exclusions, heuristic label).

### Phase 3: Contract Tests

Add tests similar to the existing audit and wiki contract tests.

Suggested tests:

- `karpathy-refactor/SKILL.md` exists.
- Frontmatter `name` is exactly `karpathy-refactor`.
- Frontmatter description contains key trigger terms.
- Skill body includes intent routing and the invocation-is-consent rule.
- Skill body contains no approval-gate language: plain substring absence of
  "should I proceed" and "want me to apply" across the whole body, no
  carve-outs (the consent rule is phrased without the literal strings).
- Skill body includes the two lanes and the hard scoring rules.
- Skill body includes the evidence step and cold-code rule.
- Skill body includes the baseline-before-edit requirement and downgrades.
- Skill body includes the `[refactor]` markers.
- Skill body includes snapshot, flake rerun, and auto-revert.
- Skill body includes the payoff field, Escalate type, and slice ladder.
- Skill body includes the contract-file and trace-review apply steps.
- Skill body includes the ledger default-write.
- Skill body includes the terminal report sections.
- Skill body includes "Do Not Refactor".
- Command file invokes `karpathy-refactor`.
- README lists `/karpathy:refactor`.
- Skill says not to stage or commit automatically.
- `SKILL.md` line count is under 500.
- Skill body includes the snapshot-mechanics section, the sensitive-area
  strong-verifiability rule, the two-part baseline comparison, the scoped
  trace reuse, the ledger schema, and the evidence-hygiene flags.
- Each of the three manifests mentions refactor, and their versions are
  identical.
- Skill body includes the sensitive-area heads-up marker.

### Phase 4: Deterministic Helper Evaluation

The MVP shells out to git directly for churn, co-change, and fix clusters. Do
not add a helper script by default. If real usage shows the git one-liners are
repeatedly fiddly — co-change pair counting is the likely candidate — add:

```text
plugins/karpathy/skills/karpathy-refactor/scripts/refactor_tool.py
```

Potential helper commands:

```text
scan --repo . --scope <path> --json
hotspots --repo . --scope <path> --json
cochange --repo . --scope <path> --json
tests --repo . --json
deps --repo . --scope <path> --json
```

Keep the helper deterministic. It may report file size, churn, co-change
pairs, import/dependency edges, test command candidates, duplicate filenames,
and module fan-in/fan-out. It must not make semantic architecture judgments.

Helper acceptance criteria:

- JSON output is stable.
- It works without network access.
- It fails gracefully when language tooling is absent.
- It does not modify files.
- Unit tests cover each command.

### Phase 5: Real-Repo Validation

Validate on at least three project shapes:

- Small script or utility repo.
- Web app with frontend/backend boundaries.
- Framework-heavy app with tests and generated files.

Evaluation questions:

- Did an act-shaped run complete with zero questions between invocation and
  terminal report?
- Did an analyze-shaped run make zero edits?
- Did the skill cite history evidence (or degrade loudly when absent)?
- Did it record a baseline before editing, and downgrade correctly on a red
  or missing baseline?
- Did every applied slice verify against the baseline, and did an injected
  failure revert cleanly to the pre-slice state?
- Did report-lane candidates stay unapplied, each with a lane reason?
- Did every finding carry a concrete payoff line?
- Did it escalate a cross-cutting problem instead of slicing it?
- Did the final diff stay traceable to the contract file?
- Did a second run respect the first run's ledger verdicts?

### Phase 6: Release Update

After validation:

- Update README quick usage.
- Add command docs.
- Add tests to CI expectations.
- Bump the plugin version (1.3.0 → 1.4.0) in `.claude-plugin/plugin.json`,
  `.codex-plugin/plugin.json`, and `.claude-plugin/marketplace.json` — the
  SessionStart update check notifies existing installs only on a version
  change.
- Consider a short example report in docs only if user examples show confusion.

## Validation Strategy

Use two levels of validation.

### Static Contract Validation

Run the full suite — existing tests plus the new skill-contract tests — via
discovery, so the runner does not rot as test files are added:

```bash
python3 -m unittest discover -s tests
```

### Forward Validation

Use fresh tasks with minimal context:

```text
Use karpathy-refactor to review src/auth. (expect: report run, no edits)
Use karpathy-refactor to simplify src/auth. (expect: autonomous run, zero mid-run questions, gated slices applied with markers, including the sensitive-area heads-up)
Use karpathy-refactor with ambiguous phrasing ("can you look at this?"); verify it routes to a report run.
Use karpathy-refactor on a repo with failing tests; verify the red-baseline downgrade fires.
Use karpathy-refactor on a repo with no runnable verification; verify the report-run downgrade and the weak verifiability cap.
Use karpathy-refactor on a repo with 90+ days of history; verify churn and co-change evidence appears.
Use karpathy-refactor with an injected verification failure; verify the slice reverts and the tree matches the pre-slice state.
Use karpathy-refactor with an injected flaky failure (fail then pass); verify the suite is marked unstable and remaining rungs move to the report lane.
Use karpathy-refactor on a hot path with no runnable benchmark; verify the candidate lands in the report lane with its lane reason.
Use karpathy-refactor on a candidate that changes behavior; verify it lands in the report lane regardless of scores.
Use karpathy-refactor on a dirty working tree; verify the user's uncommitted edits survive a revert and per-slice patches appear in the report.
Interrupt an autonomous run mid-slice; verify the next invocation detects the stale scratch state and says so first.
Use karpathy-refactor on a subsystem with a cross-cutting boundary problem; verify it escalates instead of slicing.
Re-run karpathy-refactor after a ledger write; verify rejected candidates are not re-proposed.
In a fresh session, run "apply R1 from the report"; verify the candidate resolves from the ledger's contract block.
```

Judge outputs against:

- Correct intent routing, stated in the first marker.
- Zero approval prompts; markers present for every applied slice.
- Specific evidence paths and history counts.
- Recorded baseline, and per-slice verification against it.
- Lanes obeying the hard rules; report lane carries reasons.
- Payoff line per finding.
- Clean revert behavior on failure.
- Terminal report with Applied / Reverted / Needs A Human.
- No generic pattern advice.

## Failure Modes

| Failure mode | Guardrail |
| --- | --- |
| Generic clean-code advice | Require evidence, candidate type, invariant, payoff, and verification. |
| Polishing cold code | Evidence step + cold-code rule: no history signal and no named pain means Do Not Refactor. |
| Ceremonial confirm creep | Invocation is consent; markers replace stops; contract tests reject approval-gate language. |
| Consent overreach (editing on an analyze-shaped request) | Intent routing; report runs never edit. |
| Broad rewrite proposal | One or two slices (or one gated ladder) per run. |
| Architecture problem crammed into a slice | Cross-cutting blast radius becomes Escalate, never a slice. |
| SOLID cargo culting | Require concrete risk before citing a principle. |
| Premature DRY | Distinguish stable concepts from diverging concepts. |
| Behavior change hidden as refactor | Behavior-changing candidates are report-lane; tests required. |
| Red baseline treated as green | Baseline recorded before edits; red baseline downgrades the run. |
| Failed slice left in the tree | Snapshot before each slice; persistent failure restores it exactly. |
| Flaky suite causes false verdicts | One flake rerun; unstable suite downgrades remaining rungs to the report lane. |
| Silent verification skip | Loud one-line warning; verifiability capped at weak; report run. |
| Hidden performance regression | Hot-path slices need a runnable benchmark or go to the report lane; no mid-run waivers. |
| Framework removal fantasy | Report-lane only; requires smaller replacement path and verification coverage. |
| Scope creep during apply | Contract file + trace review; untraceable hunks reverted. |
| Context drift mid-apply | The contract file is written before the first edit and is the fixed reference. |
| Re-litigating settled candidates | Ledger read in step 2; deferred stays deferred unless the user unfreezes. |
| Formatting churn | Preserve local style; avoid unrelated formatting. |
| False confidence from wiki/docs | Read cited source before claims. |
| Unsafe staging | Never stage or commit automatically. |
| Mid-run user edits clobbered | Reverse-apply failure → loud stop; tree left as-is; slice marked unrevertable in the report. |
| Verification side effects (DBs, caches, snapshots) | Unchanged-tree guarantee scoped to the worktree; side-effectful suites flagged in the report. |
| Stale ledger verdicts ossify | Entries carry commit hash + evidence window; new evidence unfreezes. |

## Open Decisions

These should be resolved after MVP validation, not before:

- Should `--report-only` / `--apply` override flags ship, or does phrasing
  routing hold up?
- Should a `--commit-each` opt-in exist for per-slice commits, or does
  snapshot-in-working-tree suffice?
- Flake rerun budget: one rerun, or two before declaring the suite unstable?
- Ledger location: resolved by the 2026-07-05 eng review — wiki-first
  (`knowledge/wiki/refactor-ledger.md`, lint-exempt) with docs fallback; every
  run writes it. Still open: should default-write have a repo-level opt-out?
- Should the executor-handoff plan (multi-slice campaigns) be a distinct
  output format, or just the report's contract blocks?
- Should co-change counting move into the helper script in v1.1, or do the git
  one-liners hold up?
- Should example reports live in docs, tests, or both?
- Should the skill include language-specific references, or stay framework and
  language agnostic?

## Recommended Next Step

Implement the MVP skill and command without a helper script — the evidence and
baseline steps run on plain git and the repo's own verification commands. Keep
the skill body procedural, under 500 lines, and strict about the four
non-negotiables: evidence before findings, baseline before edits, mechanical
gates with auto-revert instead of approval stops, and escalation instead of
oversized slices. Then add contract tests before running real-repo validation.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 2 | RAN (outside voice, gpt-5.5) | 20 points: 14 accepted, 6 tension decisions resolved, resequencing rejected with rationale |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 3 | CLEAR (PLAN, 2026-07-05, commit 1ee198b) | 17 issues (3 architecture, 4 code quality, 9 test gaps, 1 performance), 0 critical gaps — all folded into this plan |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | — |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

**CROSS-MODEL:** Codex independently converged with 5 of the Claude review's findings
(snapshot spec, line budget, trace-reuse ambiguity, ledger conflict, evidence noise) —
strong signal those were real. Its six novel tensions were each decided explicitly:
verification semantics tightened, sensitive areas require strong pre-existing
verification, slice budget wins over lane membership, framework-bloat story annotated,
autonomous-MVP posture kept (hardened, validated in Phase 5 before release), five
refinement details folded into accepted edit sites.

**VERDICT:** ENG CLEARED — ready to implement. Key accepted decisions: snapshot/revert
mechanics specified (1A), trace reuse scoped (2A), ledger schema with all-runs-write
(3A), packaging + version sync (4A), enforced line budget (5A), assertNotIn-clean
consent phrasing (6A), scoped triggers (7A), 15-scenario validation suite (8A),
evidence hygiene (9A), verification semantics (T1), sensitive-area strong-only (T2-C),
budget-wins consent (T3-A), story annotation (T4-A), autonomous MVP kept (T5-A),
codex refinements folded (T6-A).

NO UNRESOLVED DECISIONS
