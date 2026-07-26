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

    def test_context_axes_use_the_authoritative_namespace(self):
        text = SKILL.read_text(encoding="utf-8")
        quality = text.split("## Quality audit", 1)[1].split("## Docs audit", 1)[0]
        setup = text.split("## Audit setup / configure", 1)[1]

        axes = ("A1", "A2", "A3", "A4", "B5", "B6", "B7", "B8", "B9", "B10", "C")
        for axis in axes:
            self.assertIn(f"**{axis} ", quality)
        self.assertNotIn("**CE1 ", quality)
        self.assertIn("(`A1`, `A2`)", setup)

    def test_scope_and_coverage_remain_unchanged(self):
        text = SKILL.read_text(encoding="utf-8")
        scope = text.split("## Scope: what is NOT a defect", 1)[1].split("## The four principles", 1)[0]
        coverage = text.split("## Coverage audit", 1)[1].split("## Quality audit", 1)[0]
        quality = text.split("## Quality audit", 1)[1].split("## Docs audit", 1)[0]

        self.assertNotIn("progressive-disclosure", scope)
        self.assertIn("that way they apply\neverywhere without being repeated", coverage)
        self.assertIn("unless the user wants project-specific overrides", coverage)
        self.assertIn("Exhaustive file/field/config catalogs", quality)
        self.assertIn("Verify inheritance, do not assume it", quality)

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
