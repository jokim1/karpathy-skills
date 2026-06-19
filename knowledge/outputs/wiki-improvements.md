# Karpathy Wiki Improvement Notes

Local, append-only dogfood notes for improving the karpathy-wiki skill.

- No telemetry or network upload is implied by this file.
- Do not include secrets, personal data, raw transcripts, or large source excerpts.
- Do not stage this file automatically.

## 2026-06-19T20:33:58Z - Add local self-improvement notes

- Source commit: `e82e45a`
- Tags: dogfood, ux

### Observation

During Rocketboard dogfooding, the user identified that the skill should capture reusable lessons from real runs without making users manually report every issue. Add a local, sanitized, append-only improvement log and keep scaling explicit rather than telemetry-based.

### Evidence

- `docs/karpathy-wiki-roadmap.md`
- `plugins/karpathy/skills/karpathy-wiki/SKILL.md`

### Suggested Skill Change

Add a local `note-improvement` helper command, document self-improvement notes in the skill and README, and keep collection local unless an explicit export flow is added.
