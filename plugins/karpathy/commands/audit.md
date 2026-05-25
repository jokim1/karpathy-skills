---
description: Audit a CLAUDE.md / AGENTS.md against Karpathy's four LLM-coding principles
argument-hint: "[path to instruction file — defaults to ./CLAUDE.md]"
---

Run a Karpathy audit using the **karpathy-audit** skill.

Target file: $ARGUMENTS

If the target above is empty, audit `./CLAUDE.md` in the current working
directory. If no `CLAUDE.md` exists, fall back to `AGENTS.md`, then
`.cursor/rules/*.mdc`. If none of those exist, say so and offer to draft one.

Follow the karpathy-audit skill's workflow exactly: run the coverage audit and
the quality audit, produce the report in the skill's report format, then stop
and ask for approval before editing anything.
