---
type: Test Surface
title: Wiki Verification Surface
description: Unit tests cover helper behavior and skill/command contracts.
resources: [../../../tests/test_wiki_tool.py, ../../../tests/test_wiki_skill_contract.py]
tags: [wiki, tests]
timestamp: 2026-06-27T05:50:00Z
source_commit: ac86a13
confidence: high
verified_by: ["python3 -m unittest tests/test_wiki_tool.py tests/test_wiki_skill_contract.py"]
---

# Role

`tests/test_wiki_tool.py` imports `wiki_tool.py` directly and exercises the
deterministic helper contracts: init/status, concept planning, manifest source
maps, affected-concept mapping, raw ingest/correction/redaction, compile
planning, doctor lint, hooks, and local improvement notes. [1]

`tests/test_wiki_skill_contract.py` checks text-level product contracts: helper
scripts stay internal, UX guidance exists, raw helper names do not expand the
public command surface, compile scope is bounded, and deep graph lint stays in
doctor rather than hooks. [2]

# Verification

Run:

```bash
python3 -m unittest tests/test_wiki_tool.py tests/test_wiki_skill_contract.py
```

# Citations

[1] [wiki helper tests](../../../tests/test_wiki_tool.py)
[2] [wiki skill contract tests](../../../tests/test_wiki_skill_contract.py)
