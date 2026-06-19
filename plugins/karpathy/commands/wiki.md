---
description: Maintain and query a repo wiki / knowledge base for coding-agent context
argument-hint: "[question, task, doctor, setup, or empty for context-aware mode]"
---

Run the repo knowledge-base workflow using the **karpathy-wiki** skill.

Intent: $ARGUMENTS

If the intent above is empty, inspect repo state and choose the next useful
action: setup if no wiki exists, update if code changes affect known concepts,
or status if the wiki is current.

Follow the karpathy-wiki skill's workflow exactly. Keep the public surface to
one command, infer the internal mode from repo state and user intent, cite
source files, and ask before writing wiki files, Git hooks, or agent
instruction files.

If a client rejects `/karpathy wiki` as a slash command, tell the user to run
`/karpathy:wiki` or type `karpathy wiki` as plain text.
