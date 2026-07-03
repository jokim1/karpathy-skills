---
description: Configure /karpathy:audit docs checks
argument-hint: "[D1/D2 | --toggle <row> | --enable <check> | --disable <check> | --yes | --reset]"
---

Run Karpathy audit setup using the **karpathy-audit** skill.

Intent: $ARGUMENTS

Use the audit setup workflow from the skill. Resolve `<skill-dir>` to the
directory containing `karpathy-audit/SKILL.md`, then run the helper internally:

```bash
python3 <skill-dir>/scripts/audit_tool.py setup --repo . $ARGUMENTS
```

If the intent above is empty, print the setup state only. Bare setup is
read-only: it must not write `.karpathy.json`.

If the intent toggles, enables, disables, resets, or saves recommended checks,
let the helper update `.karpathy.json`, then report the grouped setup state and
the setup actions. Never stage or commit `.karpathy.json` automatically.

The setup UI should stay Pipelane-style: grouped rows, on/off state, row IDs,
and explicit controls. Do not reduce it to a prose summary.

If a client rejects `/karpathy setup` as a slash command, tell the user to run
`/karpathy:setup` or type `karpathy setup` as plain text.
