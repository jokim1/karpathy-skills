# TODOS

## Populate the root AGENTS.md (currently a one-line stub)

- **What:** Write real agent instructions in `AGENTS.md` at the repo root (it
  contains only "## Imported Claude Cowork project instructions" and is
  untracked), then dogfood `/karpathy:audit` against it.
- **Why:** This repo ships the audit skill that flags empty/stale agent
  instruction files in other people's repos; its own root file is the empty
  case. Real guidance saves every future agent session an orientation pass.
- **Pros:** 30-second orientation for future sessions; a natural validation
  loop for the audit skill on home turf.
- **Cons:** No demonstrated pain yet; writing good instructions is its own
  small task, not a drive-by.
- **Context:** Surfaced during the 2026-07-05 eng review of the
  karpathy-refactor plan (`coding-improvements/docs/karpathy-refactor-skill-plan.md`).
  Obvious content: test runner (`python3 -m unittest discover -s tests`), the
  three-manifest release surface (`.claude-plugin/plugin.json`,
  `.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json` must stay in
  sync and version-bump together or `check_update.py` never notifies installs),
  skill/command file conventions, contract-test expectations.
- **Depends on / blocked by:** Nothing.
