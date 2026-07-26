import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL = REPO_ROOT / "plugins" / "karpathy" / "skills" / "karpathy-audit" / "SKILL.md"
SETUP_COMMAND = REPO_ROOT / "plugins" / "karpathy" / "commands" / "setup.md"
CONFIGURE_COMMAND = REPO_ROOT / "plugins" / "karpathy" / "commands" / "configure.md"


class AuditSkillContractTests(unittest.TestCase):
    def test_skill_defines_optional_docs_checks_as_configured_behavior(self):
        text = SKILL.read_text(encoding="utf-8")

        self.assertIn("## Docs audit", text)
        self.assertIn(".karpathy.json", text)
        self.assertIn('"staleDocs": true', text)
        self.assertIn('"indexChecks": true', text)
        self.assertIn("If the config file is absent", text)
        self.assertIn("use the opinionated defaults", text)
        self.assertIn("D1 and D2 on", text)
        self.assertIn("docs-check --repo . --json", text)

    def test_skill_defines_pipelane_style_setup_controls(self):
        text = SKILL.read_text(encoding="utf-8")

        self.assertIn("## Audit setup / configure", text)
        self.assertIn("Bare setup/configure is read-only", text)
        self.assertIn("Always show the always-on instruction rows", text)
        self.assertIn("D1", text)
        self.assertIn("D2", text)
        self.assertIn("--yes", text)
        self.assertIn("--reset", text)
        self.assertIn("Writes are limited to `.karpathy.json`", text)

    def test_context_axes_use_the_ce_namespace(self):
        text = SKILL.read_text(encoding="utf-8")
        quality = text.split("## Quality audit", 1)[1].split("## Docs audit", 1)[0]
        setup = text.split("## Audit setup / configure", 1)[1]

        axes = ("CE1", "CE2", "CE3", "CE4", "CE5", "CE6", "CE7", "CE8", "CE9", "CE10", "CE11")
        for axis in axes:
            self.assertIn(f"**{axis} ", quality)
        # The audit layer owns the CE namespace; the published setup surface
        # keeps its established A1/A2 instruction rows untouched.
        self.assertNotIn("**A1 ", quality)
        self.assertNotIn("**B5 ", quality)
        self.assertIn("(`A1`, `A2`)", setup)

    def test_scope_boundary_and_coverage_verification(self):
        text = SKILL.read_text(encoding="utf-8")
        scope = text.split("## Scope: what is NOT a defect", 1)[1].split("## The four principles", 1)[0]
        coverage = text.split("## Coverage audit", 1)[1].split("## Quality audit", 1)[0]
        quality = text.split("## Quality audit", 1)[1].split("## Docs audit", 1)[0]

        # Scope draws the explicit boundary against the CE6 disclosure defect.
        self.assertIn("progressive-disclosure defect axis CE6", scope)
        # Coverage keeps its global-home nuance but must require verifying
        # which harnesses load the global file before recommending a hoist.
        self.assertIn("that way they apply\neverywhere without being repeated", coverage)
        self.assertIn("unless the user wants project-specific overrides", coverage)
        self.assertIn("verify which harnesses actually load the global file", coverage)
        self.assertIn("Exhaustive file/field/config catalogs", quality)
        self.assertIn("Verify inheritance, do not assume it", quality)

    def test_workflow_bounds_and_reports_cross_layer_discovery(self):
        text = SKILL.read_text(encoding="utf-8")
        workflow = text.split("## Workflow", 1)[1].split("## Coverage audit", 1)[0]
        report = text.split("## Report format", 1)[1].split("## Applying changes", 1)[0]

        self.assertIn("System and developer instructions visible in the current session", workflow)
        self.assertIn("The `SKILL.md` files activated for the current audit", workflow)
        self.assertIn("Project `AGENTS.md` and `CLAUDE.md` files", workflow)
        self.assertIn("Global memory at the harness's known location", workflow)
        self.assertIn("Auto-memory exposed by the active harness", workflow)
        self.assertIn("do not run a recursive filesystem sweep", workflow)
        self.assertIn("Mark a layer **Unreadable**", workflow)
        self.assertIn("## Layer access", report)
        self.assertIn("Unreadable: <reason>", report)

    def test_setup_and_configure_commands_share_the_same_workflow(self):
        setup_text = SETUP_COMMAND.read_text(encoding="utf-8")
        configure_text = CONFIGURE_COMMAND.read_text(encoding="utf-8")

        for text in (setup_text, configure_text):
            self.assertIn("karpathy-audit", text)
            self.assertIn("audit_tool.py setup --repo .", text)
            self.assertIn("read-only", text)
            self.assertIn("grouped rows", text)
            self.assertIn("Never stage or commit `.karpathy.json`", text)


if __name__ == "__main__":
    unittest.main()
