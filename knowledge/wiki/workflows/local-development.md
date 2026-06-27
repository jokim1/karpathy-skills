---
type: Workflow
title: Local Development
description: Contributor workflow for installing, validating, and publishing the karpathy plugin.
resource: ../../../README.md
tags: [development, release]
timestamp: 2026-06-27T05:50:00Z
source_commit: ac86a13
confidence: medium
verified_by: ["python3 -m unittest tests/test_wiki_tool.py tests/test_wiki_skill_contract.py"]
---

# Role

The README is the high-signal guide for installing the `karpathy` plugin,
understanding `/karpathy:wiki`, and validating release artifacts. It documents
Claude and Codex marketplace installation paths, the one-command wiki UX, and
the release validation checklist. [1]

# Common Commands

- Use `/karpathy:wiki` for the repo wiki workflow. [1]
- Validate the wiki helper and contract tests with `python3 -m unittest
  tests/test_wiki_tool.py tests/test_wiki_skill_contract.py`. [1]
- Release validation includes JSON checks for plugin manifests and Python
  compilation for the shared update checker. [1]

# Citations

[1] [README](../../../README.md)
