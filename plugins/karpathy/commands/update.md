---
description: Check for and update the Karpathy plugin
argument-hint: "[--check]"
---

Run the Karpathy plugin update workflow using the **karpathy-update** skill.

Intent: $ARGUMENTS

Follow the karpathy-update skill exactly. If the intent is `--check`, `check`,
or empty but the user clearly only wants status, run the helper in read-only
check mode. Otherwise run update mode.

Keep the public surface simple:

- Users should type `/karpathy:update`, or `karpathy update` as plain text.
- Treat `/karpathy update` as client-dependent shorthand: if it is rejected as
  an unknown slash command, immediately offer `/karpathy:update`.
- Do not expose `check_update.py` as the public command.
- Claude Code updates must go through Claude's plugin manager; print the exact
  `/plugin marketplace update karpathy-skills`, `/plugin install
  karpathy@karpathy-skills`, and `/reload-plugins` fallback when the helper
  reports `manual_required`.
- Codex updates may run through the Codex CLI when the helper detects Codex.
  If `/karpathy:update` is missing, tell the user to run
  `codex plugin marketplace upgrade karpathy-skills`, then
  `codex plugin add karpathy@karpathy-skills`, then start a new Codex thread.

After a successful update, tell the user to reload plugins, restart, or start a
new thread so refreshed skills and hooks are loaded.
