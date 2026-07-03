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

- Users may type `/karpathy update`, `/karpathy:update`, or `karpathy update`.
- Do not expose `check_update.py` as the public command.
- Claude Code updates must go through Claude's plugin manager; print the exact
  `/plugin marketplace update karpathy-skills` and `/reload-plugins` fallback
  when the helper reports `manual_required`.
- Codex updates may run through the Codex CLI when the helper detects Codex.

After a successful update, tell the user to reload plugins, restart, or start a
new thread so refreshed skills and hooks are loaded.
