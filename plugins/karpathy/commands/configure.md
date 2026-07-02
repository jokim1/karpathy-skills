---
description: Configure optional /karpathy:audit docs checks
argument-hint: "[D1/D2 | --toggle <row> | --enable <check> | --disable <check> | --yes | --reset]"
---

Run Karpathy audit setup using the **karpathy-audit** skill.

Intent: $ARGUMENTS

`/karpathy:configure` is an alias for `/karpathy:setup`. Use the same audit
setup workflow. Resolve `<skill-dir>` to the directory containing
`karpathy-audit/SKILL.md`, then run the same helper internally:

```bash
python3 <skill-dir>/scripts/audit_tool.py setup --repo . $ARGUMENTS
```

If the intent above is empty, print the setup state only. Bare configure is
read-only: it must not write `.karpathy.json`.

If the intent toggles, enables, disables, resets, or accepts recommended checks,
let the helper update `.karpathy.json`, then report the grouped setup state and
the setup actions. Never stage or commit `.karpathy.json` automatically.

The setup UI should stay Pipelane-style: grouped rows, on/off state, row IDs,
and explicit controls. Do not reduce it to a prose summary.

If a client rejects `/karpathy configure` as a slash command, tell the user to
run `/karpathy:configure` or type `karpathy configure` as plain text.
