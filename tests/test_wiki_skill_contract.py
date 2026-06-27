import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL = REPO_ROOT / "plugins" / "karpathy" / "skills" / "karpathy-wiki" / "SKILL.md"
COMMAND = REPO_ROOT / "plugins" / "karpathy" / "commands" / "wiki.md"


class WikiSkillContractTests(unittest.TestCase):
    def test_command_keeps_helper_scripts_internal(self):
        text = COMMAND.read_text(encoding="utf-8")

        self.assertIn("run helper scripts yourself", text)
        self.assertIn("Do not tell the user to run", text)
        self.assertIn("wiki_tool.py", text)

    def test_command_does_not_expand_public_raw_helper_surface(self):
        text = COMMAND.read_text(encoding="utf-8")

        self.assertIn("/karpathy:wiki", text)
        for helper in ("raw-add", "raw-correct", "raw-redact", "raw-show", "compile-plan"):
            self.assertNotIn(helper, text)

    def test_skill_declares_user_facing_ux_contract(self):
        text = SKILL.read_text(encoding="utf-8")

        self.assertIn("## UX Contract", text)
        self.assertIn("Do not hand the user a terminal checklist", text)
        self.assertIn("Do not ask the user to paste concept pages into an editor", text)
        self.assertIn("write the pages yourself", text)

    def test_skill_uses_concept_plan_before_starter_pages(self):
        text = SKILL.read_text(encoding="utf-8")

        self.assertIn("concept-plan --repo . --json", text)
        self.assertIn("Read each chosen candidate's `read` files", text)
        self.assertIn("Do not create every candidate", text)

    def test_skill_keeps_improvement_notes_local(self):
        text = SKILL.read_text(encoding="utf-8")

        self.assertIn("## Self-Improvement Notes", text)
        self.assertIn("knowledge/outputs/wiki-improvements.md", text)
        self.assertIn("not telemetry", text)
        self.assertIn("background network upload", text)

    def test_skill_defines_raw_capture_as_external_not_repo_copying(self):
        text = SKILL.read_text(encoding="utf-8")

        self.assertIn("## Raw Source Capture", text)
        self.assertIn("Raw ingest is only for non-Git sources", text)
        self.assertIn("Do not copy Git-tracked", text)
        self.assertIn("Do not expose these as public slash commands", text)

    def test_skill_requires_bounded_compile_scope_and_doctor_graph_lint(self):
        text = SKILL.read_text(encoding="utf-8")

        self.assertIn("## Compile Scope", text)
        self.assertIn("Compile one bounded source unit at a time", text)
        self.assertIn("compile-plan --repo . --source", text)
        self.assertIn("unreachable concept pages", text)
        self.assertIn("Do not run deep graph/index lint from hooks", text)


if __name__ == "__main__":
    unittest.main()
