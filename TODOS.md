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

## Reconsider `/karpathy:doctor` only if `/karpathy:update` repair still confuses users

- **What:** After the `/karpathy:update` repair flow ships, watch dogfood runs
  and user reports for remaining install-repair confusion. Add a separate
  `/karpathy:doctor` command only if users still cannot recover from missing,
  stale, partial, or mixed Karpathy installs through `/karpathy:update` plus the
  documented command-not-found bootstrap path.
- **Why:** The preferred product shape is one obvious update command, not a
  growing menu of maintenance commands. A doctor command is justified only if
  the single-command repair flow still leaves users stuck.
- **Pros:** Keeps the public surface small now, while preserving a clear trigger
  for adding deeper diagnostics later if real users need it.
- **Cons:** Defers a possible diagnostic command, so future support cases must
  be checked against the shipped `/karpathy:update` UX before deciding whether
  another command is worth the extra surface area.
- **Context:** Surfaced during the 2026-07-11 eng review of the
  `/karpathy:update` repair plan. Accepted scope: add a formal install-state
  detector, verify required command/skill surfaces, repair through the supported
  plugin manager, archive legacy standalone `~/.codex/skills/karpathy-*`
  directories to a timestamped backup, keep SessionStart hooks read-only, and
  document command-not-found recovery outside the skill runtime. If that plan
  works, `/karpathy:doctor` is redundant. If users still struggle, it may be a
  justified diagnostic entrypoint.
- **Depends on / blocked by:** Ship and dogfood the `/karpathy:update` repair
  flow first; collect at least one concrete failure mode that the update command
  cannot explain or repair.
