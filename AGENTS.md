# karpathy-skills

Test from the repo root: `python3 -m unittest discover -s tests`.

Release: set one version on the marketplace plugin named `karpathy` in `.claude-plugin/marketplace.json`, and the same version in `plugins/karpathy/.claude-plugin/plugin.json` and `plugins/karpathy/.codex-plugin/plugin.json`. Run `claude plugin validate .`, `claude plugin validate ./plugins/karpathy`, and the test command. Commit, tag, and push.

Traps: if the two plugin.json versions differ, `check_update.py` reports a partial install instead of an update; latest is read from `plugins/karpathy/.claude-plugin/plugin.json` on main. `docs/karpathy-refactor-skill-plan.md` is a frozen review copy, and the refactor skill deliberately diverges from it.
