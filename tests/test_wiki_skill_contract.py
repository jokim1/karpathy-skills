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

    def test_skill_declares_user_facing_ux_contract(self):
        text = SKILL.read_text(encoding="utf-8")

        self.assertIn("## UX Contract", text)
        self.assertIn("Do not hand the user a terminal checklist", text)
        self.assertIn("Do not ask the user to paste concept pages into an editor", text)
        self.assertIn("write the pages yourself", text)

    def test_skill_keeps_improvement_notes_local(self):
        text = SKILL.read_text(encoding="utf-8")

        self.assertIn("## Self-Improvement Notes", text)
        self.assertIn("knowledge/outputs/wiki-improvements.md", text)
        self.assertIn("not telemetry", text)
        self.assertIn("background network upload", text)


if __name__ == "__main__":
    unittest.main()
