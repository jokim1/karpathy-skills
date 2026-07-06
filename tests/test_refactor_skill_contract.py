import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL = REPO_ROOT / "plugins" / "karpathy" / "skills" / "karpathy-refactor" / "SKILL.md"
COMMAND = REPO_ROOT / "plugins" / "karpathy" / "commands" / "refactor.md"
README = REPO_ROOT / "README.md"
CLAUDE_MANIFEST = REPO_ROOT / "plugins" / "karpathy" / ".claude-plugin" / "plugin.json"
CODEX_MANIFEST = REPO_ROOT / "plugins" / "karpathy" / ".codex-plugin" / "plugin.json"
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"


def split_skill():
    text = SKILL.read_text(encoding="utf-8")
    parts = re.split(r"^---$", text, maxsplit=2, flags=re.MULTILINE)
    frontmatter, body = parts[1], parts[2]
    return frontmatter, body


def collapse(text):
    """Collapse whitespace so wrapped YAML/prose phrases match as substrings."""
    return " ".join(text.split())


class RefactorSkillContractTests(unittest.TestCase):
    def test_skill_file_exists(self):
        self.assertTrue(SKILL.is_file())

    def test_frontmatter_name_is_exactly_karpathy_refactor(self):
        frontmatter, _ = split_skill()
        match = re.search(r"^name:\s*(.+)$", frontmatter, flags=re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1).strip(), "karpathy-refactor")

    def test_description_contains_key_trigger_terms(self):
        frontmatter, _ = split_skill()
        description = collapse(frontmatter)

        for term in (
            "refactoring",
            "DRY",
            "SOLID",
            "design patterns",
            "classes",
            "framework",
            "overengineering",
            "simplify",
            "simplification",
            "hotspot",
            "evidence",
            "where refactoring pays off",
        ):
            self.assertIn(term, description)

        # Scoped trigger aliases only — no bare "review this architecture"
        # or "plan a refactor" phrasing.
        self.assertIn("review this architecture for refactoring", description)
        self.assertIn("plan a refactor of this subsystem", description)

    def test_body_includes_intent_routing_and_consent_rule(self):
        _, body = split_skill()
        flat = collapse(body)

        self.assertIn("Analyze-shaped", body)
        self.assertIn("Act-shaped", body)
        self.assertIn("Ambiguous", body)
        self.assertIn("report run", body)
        self.assertIn("autonomous run", body)
        self.assertIn("Invocation is consent", body)
        self.assertIn(
            "Never ask permission to continue or to apply a slice mid-run", flat
        )

    def test_body_contains_no_approval_gate_language(self):
        text = SKILL.read_text(encoding="utf-8")
        for banned in ("should I proceed", "want me to apply"):
            self.assertNotIn(banned, text)
            self.assertNotIn(banned.lower(), text.lower())
            self.assertNotIn(banned.lower(), collapse(text).lower())

    def test_body_includes_two_lanes_and_hard_scoring_rules(self):
        _, body = split_skill()
        flat = collapse(body)

        self.assertIn("Auto-apply lane", body)
        self.assertIn("Report lane", body)
        self.assertIn("Risk high is never auto-apply", flat)
        self.assertIn(
            "verifiability strong, or partial with a test-first prelude", flat
        )
        self.assertIn("Blast radius cross-cutting: the type becomes Escalate", flat)
        self.assertIn("Hot path without a runnable benchmark: report lane", flat)
        self.assertIn("one or two slices per run — or one ladder", flat)
        self.assertIn("The budget wins over lane membership", flat)
        self.assertIn("they land in the Slice Ladder", flat)

    def test_body_includes_evidence_step_and_cold_code_rule(self):
        _, body = split_skill()
        flat = collapse(body)

        self.assertIn("Churn", body)
        self.assertIn("Co-change", body)
        self.assertIn("Fix clusters", body)
        self.assertIn("git log --no-merges", body)
        self.assertIn('defaults to "Do Not Refactor"', body)
        self.assertIn("Cold code needs a stronger reason", flat)

    def test_body_includes_baseline_before_edit_and_downgrades(self):
        _, body = split_skill()
        flat = collapse(body)

        self.assertIn(
            "Record the verification baseline before the first edit", flat
        )
        self.assertIn("A red baseline is load-bearing information", flat)
        self.assertIn("test-first slices only", body)
        self.assertIn("capped at weak", body)
        self.assertIn("downgrade to a report run", flat)
        self.assertIn("not escapable mid-run", flat)

    def test_body_includes_refactor_markers(self):
        _, body = split_skill()

        self.assertIn("[refactor] Mode:", body)
        self.assertIn("[refactor] Baseline:", body)
        self.assertIn("[refactor] Applying", body)
        self.assertIn("[refactor] Verified", body)
        self.assertIn("[refactor] Reverted", body)
        self.assertIn("[refactor] Escalation:", body)
        self.assertIn("[refactor] Ledger updated:", body)

    def test_body_includes_sensitive_area_heads_up_marker(self):
        _, body = split_skill()
        self.assertIn("[refactor] Touching sensitive area", body)

    def test_body_includes_snapshot_flake_rerun_and_auto_revert(self):
        _, body = split_skill()
        flat = collapse(body)

        self.assertIn("Snapshot the worktree", body)
        self.assertIn("rerun once to detect flake", flat)
        self.assertIn("restore the snapshot", flat)
        self.assertIn("pre-slice state restored", body)
        self.assertIn("marks the suite unstable", flat)

    def test_body_includes_payoff_escalate_type_and_slice_ladder(self):
        _, body = split_skill()
        flat = collapse(body)

        self.assertIn("Payoff:", body)
        self.assertIn("No payoff, no refactor", flat)
        self.assertIn("| Escalate |", body)
        self.assertIn("Slice Ladder", body)

    def test_body_includes_contract_file_and_trace_review_steps(self):
        _, body = split_skill()
        flat = collapse(body)

        self.assertIn("contract file", body)
        self.assertIn("trace-test categories", body)
        self.assertIn("traces / doesn't trace / can't tell", flat)

    def test_body_scopes_karpathy_diff_reuse(self):
        _, body = split_skill()
        flat = collapse(body)

        self.assertIn("\"can't tell\" is treated as \"doesn't trace\"", flat)
        self.assertIn("do not apply inside an autonomous run", flat)

    def test_body_includes_ledger_default_write_and_schema(self):
        _, body = split_skill()
        flat = collapse(body)

        self.assertIn("Every run writes the ledger", flat)
        self.assertIn(
            "verdict (applied, reverted, rejected, **proposed**, do-not-refactor)",
            flat,
        )
        self.assertIn("commit hash", body)
        self.assertIn("evidence window", flat)
        self.assertIn("contract block", body)
        self.assertIn("knowledge/wiki/refactor-ledger.md", body)
        self.assertIn("docs/refactor-ledger.md", body)

    def test_body_includes_terminal_report_sections(self):
        _, body = split_skill()

        self.assertIn("# Karpathy Refactor Report", body)
        self.assertIn("## Architecture Map", body)
        self.assertIn("## Evidence", body)
        self.assertIn("## Applied", body)
        self.assertIn("## Reverted", body)
        self.assertIn("## Needs A Human", body)
        self.assertIn("## Slice Ladder", body)
        self.assertIn("## Escalations", body)
        self.assertIn("## Next", body)
        self.assertIn("never a blocking question", body)

    def test_body_includes_do_not_refactor_section(self):
        _, body = split_skill()
        self.assertIn("## Do Not Refactor", body)

    def test_body_includes_snapshot_mechanics_spec(self):
        _, body = split_skill()
        flat = collapse(body)

        self.assertIn("## Snapshot Mechanics", body)
        self.assertIn("git diff --binary --find-renames", body)
        self.assertIn("git ls-files --others --exclude-standard", body)
        self.assertIn("Never `git checkout -- .`", body)
        self.assertIn("Dirty tree at invocation", body)
        self.assertIn("unrevertable", body)
        self.assertIn("scratch directory outside the repo", flat)
        self.assertIn("stale scratch state", body)
        self.assertIn("it covers the worktree", flat)

    def test_body_includes_sensitive_area_strong_verifiability_rule(self):
        _, body = split_skill()
        flat = collapse(body)

        self.assertIn("strong from pre-existing repo tests", flat)
        self.assertIn("Auth, migrations, security boundaries, CI", flat)

    def test_body_includes_two_part_baseline_comparison(self):
        _, body = split_skill()
        flat = collapse(body)

        self.assertIn("The comparison is two-part", flat)
        self.assertIn("reproduce the recorded baseline", flat)
        self.assertIn("tests added by the slice must pass", flat)
        self.assertIn("Only non-interactive commands count as verification", flat)
        self.assertIn("Scope the redness", body)

    def test_body_includes_evidence_hygiene_rules(self):
        _, body = split_skill()
        flat = collapse(body)

        self.assertIn("--no-merges", body)
        self.assertIn("more than ~30 files", body)
        self.assertIn("Exclude lockfiles and generated paths", flat)
        self.assertIn("commit-message heuristic", body)

    def test_body_says_never_stage_or_commit(self):
        _, body = split_skill()
        self.assertIn("Never stage or commit automatically", body)

    def test_skill_line_count_under_500(self):
        lines = SKILL.read_text(encoding="utf-8").splitlines()
        self.assertLess(len(lines), 500)

    def test_command_file_invokes_the_skill(self):
        text = COMMAND.read_text(encoding="utf-8")
        self.assertIn("karpathy-refactor", text)
        self.assertIn("$ARGUMENTS", text)

    def test_readme_lists_the_refactor_command(self):
        self.assertIn("/karpathy:refactor", README.read_text(encoding="utf-8"))

    def test_manifests_mention_refactor_and_versions_match(self):
        claude_text = CLAUDE_MANIFEST.read_text(encoding="utf-8")
        codex_text = CODEX_MANIFEST.read_text(encoding="utf-8")
        marketplace_text = MARKETPLACE.read_text(encoding="utf-8")

        for text in (claude_text, codex_text, marketplace_text):
            self.assertIn("/karpathy:refactor", text)

        claude_version = json.loads(claude_text)["version"]
        codex_version = json.loads(codex_text)["version"]
        marketplace_version = json.loads(marketplace_text)["plugins"][0]["version"]
        self.assertEqual(claude_version, codex_version)
        self.assertEqual(claude_version, marketplace_version)


if __name__ == "__main__":
    unittest.main()
