---
description: Maintain and query a repo wiki / knowledge base for coding-agent context
argument-hint: "[question, task, doctor, setup, or empty for context-aware mode]"
---

Run the repo knowledge-base workflow using the **karpathy-wiki** skill.

Intent: $ARGUMENTS

If the intent above is empty, inspect repo state and choose the next useful
action: setup if no wiki exists or setup is incomplete, starter concepts if the
scaffold exists but no concepts are indexed yet, update if code changes affect
known concepts, or status if the wiki is current.

Follow the karpathy-wiki skill's workflow exactly. Keep the public surface to
one command, infer the internal mode from repo state and user intent, cite
source files, and run helper scripts yourself. Do not tell the user to run
`wiki_tool.py` commands during normal operation; summarize helper results and
perform approved or explicit wiki-file writes directly. Always ask before Git
hook installation or agent-instruction edits.

If the run exposes a reusable issue with the karpathy-wiki skill itself, append
a short local improvement note as described by the skill. Keep it sanitized and
local; never stage it automatically.

If a client rejects `/karpathy wiki` as a slash command, tell the user to run
`/karpathy:wiki` or type `karpathy wiki` as plain text.
