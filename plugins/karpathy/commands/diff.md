---
description: Review a git diff against Karpathy's principles before you commit
argument-hint: "[git ref/range or path — defaults to all uncommitted changes]"
---

Run a Karpathy diff review using the **karpathy-diff** skill.

Scope: $ARGUMENTS

If the scope above is empty, review all uncommitted changes (`git diff HEAD`).
Otherwise honor it — a staged-only review (`--staged`), a commit range, a
single commit, or a path.

Follow the karpathy-diff skill's workflow exactly: establish the task the change
was meant to accomplish, run the trace test hunk by hunk, produce the report in
the skill's format, then stop and ask for approval before changing anything.
