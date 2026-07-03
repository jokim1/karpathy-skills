---
name: karpathy-update
description: >-
  Check for and update the Karpathy plugin itself. Use when the user says
  "karpathy update", "/karpathy update", "/karpathy:update", asks to update or
  upgrade the Karpathy skill/plugin, or asks whether a Karpathy plugin update is
  available. This is for plugin updates, not repo wiki content updates.
---

# Karpathy Update

Update the installed Karpathy plugin with the smallest safe workflow for the
current client.

## Workflow

1. Resolve this skill directory and use the shared helper:

   ```bash
   python3 <skill-dir>/../../scripts/check_update.py --check
   python3 <skill-dir>/../../scripts/check_update.py --update
   ```

2. If the user asked for status only (`--check`, `check`, "is there an update"),
   run `--check` and report the result.
3. Otherwise run `--update`.
4. If the helper reports `updated`, summarize the command results and tell the
   user to start a new Codex thread or restart/reload the client so refreshed
   skills and hooks are loaded.
5. If the helper reports `manual_required`, relay the exact fallback command(s)
   from the helper. Do not invent a manual cache rewrite.

## Client rules

- Codex has a shell plugin manager. In Codex, the helper may run:

  ```bash
  codex plugin marketplace upgrade karpathy-skills
  codex plugin add karpathy@karpathy-skills
  ```

- Claude Code's plugin update path is an interactive slash command. Do not
  manually edit `~/.claude/plugins/cache` or `installed_plugins.json`. Tell the
  user to run:

  ```text
  /plugin marketplace update karpathy-skills
  /reload-plugins
  ```

## UX contract

When an update is available, say:

```text
Run /karpathy update to install it.
```

If the client rejects that spelling, add the fallback:

```text
Use /karpathy:update instead, or type karpathy update as normal text.
```

Keep the explanation short. This command updates the plugin itself; use
`/karpathy:wiki update` for repo wiki content updates.
