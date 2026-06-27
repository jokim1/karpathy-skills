---
type: Workflow
title: Wiki Public Surface
description: The user-facing wiki workflow stays on /karpathy:wiki while helpers remain internal.
resources: [../../../plugins/karpathy/skills/karpathy-wiki/SKILL.md, ../../../plugins/karpathy/commands/wiki.md, ../../../README.md]
tags: [wiki, ux, command]
timestamp: 2026-06-27T05:50:00Z
source_commit: ac86a13
confidence: high
verified_by: ["python3 -m unittest tests/test_wiki_skill_contract.py"]
---

# Role

The command wrapper routes user intent into the karpathy-wiki skill and tells
the agent to run helper scripts internally. It explicitly says not to make the
user run `wiki_tool.py` during normal operation. [1]

# Invariants

- Keep one public command: `/karpathy:wiki`, with `karpathy wiki` as plain-text
  fallback where slash parsing rejects the space form. [2]
- Keep raw ingest and compile planning as helper plumbing, not public command
  expansion. [2]
- Ask before Git hook installation or agent-instruction edits. [1] [2]

# Common Changes

When adding helper operations, update skill instructions and contract tests so
agents can use the helper internally without changing the public command surface.
[2] [3]

# Citations

[1] [wiki command wrapper](../../../plugins/karpathy/commands/wiki.md)
[2] [karpathy-wiki skill](../../../plugins/karpathy/skills/karpathy-wiki/SKILL.md)
[3] [README wiki overview](../../../README.md)
