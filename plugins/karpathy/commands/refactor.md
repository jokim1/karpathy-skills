---
description: Evidence-gated, behavior-preserving refactor of a subsystem or module
argument-hint: "[path or subsystem — defaults to a scope inferred from the request]"
---

Run a Karpathy refactor using the **karpathy-refactor** skill.

Scope: $ARGUMENTS

If the scope above is empty, infer a narrow scope from the request and state
it. Route intent from the user's phrasing per the skill: analyze-shaped →
report run (no code edits; the ledger is its only write); act-shaped →
autonomous run; ambiguous → report run.

Follow the karpathy-refactor skill's workflow exactly: gather history
evidence, record the verification baseline before any edit, sort candidates
into the two lanes, apply only auto-apply-lane slices within the slice budget
with `[refactor]` markers and snapshot/auto-revert, run the trace review,
write the refactor ledger, and end with the terminal report. Never stage or
commit.
