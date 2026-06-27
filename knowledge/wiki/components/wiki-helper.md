---
type: Component
title: Karpathy Wiki Helper
description: Deterministic repo/wiki operations for the karpathy-wiki skill.
resource: ../../../plugins/karpathy/skills/karpathy-wiki/scripts/wiki_tool.py
raw_sources: [external-docs-correction-for-llm-wiki-adoption-dogfood-note-2026-06-27]
tags: [wiki, helper, raw-ingest]
timestamp: 2026-06-27T05:50:00Z
source_commit: 58012c4
confidence: high
verified_by: ["python3 -m unittest tests/test_wiki_tool.py tests/test_wiki_skill_contract.py"]
---

# Role

`wiki_tool.py` owns deterministic helper operations for the wiki workflow:
scaffold/status, manifest generation, affected-concept mapping, doctor checks,
raw source capture, and bounded compile planning. It does not write semantic
concept prose for the agent. [1]

# Public Surface

The helper has internal CLI subcommands such as `raw-add`, `raw-correct`,
`raw-redact`, `raw-show`, `compile-plan`, `doctor`, `refresh-manifest`, and
`update-plan`. The public user command remains `/karpathy:wiki`; helper output
is summarized by the agent. [1] [2]

# Raw Ingest

Raw records live under `knowledge/raw/<kind>/`, include `source_id`, `kind`,
`timestamp`, `sha256`, and optional `supersedes`, and reject large, binary, or
secret-like bodies. Corrections create new records; redaction mutates only as a
safety exception. [1]

This dogfood pass created raw source `raw:external-docs-correction-for-llm-wiki-adoption-dogfood-note-2026-06-27`,
which supersedes the initial validation note. [2]

# Compile Planning

`compile-plan` accepts exactly one raw source ID or one Git-tracked source unit.
Directory source units are helper-capped and named explicitly, so a source set
cannot silently mean the whole repo. Directory plans report both
`source_total_count` and `source_truncated`, making capped source sets visible
to the agent before semantic wiki writing starts. [1]

# Wiki Scaffold

`init_wiki` creates indexes for each concept area linked from the root index,
so the generated scaffold has resolvable area navigation before any semantic
concept pages exist. [1]

# Citations

[1] [wiki_tool.py](../../../plugins/karpathy/skills/karpathy-wiki/scripts/wiki_tool.py)
[2] raw:external-docs-correction-for-llm-wiki-adoption-dogfood-note-2026-06-27
