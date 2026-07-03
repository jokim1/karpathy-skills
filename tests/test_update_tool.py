import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "plugins" / "karpathy" / "scripts" / "check_update.py"
UPDATE_COMMAND = REPO_ROOT / "plugins" / "karpathy" / "commands" / "update.md"
UPDATE_SKILL = REPO_ROOT / "plugins" / "karpathy" / "skills" / "karpathy-update" / "SKILL.md"


class UpdateToolTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.plugin_root = self.root / "plugin"
        self.plugin_root.mkdir()
        (self.plugin_root / ".claude-plugin").mkdir()
        (self.plugin_root / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"version": "1.0.0"}) + "\n",
            encoding="utf-8",
        )
        self.remote = self.root / "remote.json"
        self.remote.write_text(json.dumps({"version": "1.2.0"}) + "\n", encoding="utf-8")
        self.data = self.root / "data"

    def tearDown(self):
        self.tempdir.cleanup()

    def env(self, **extra):
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PLUGIN_ROOT"] = str(self.plugin_root)
        env["KARPATHY_PLUGIN_DATA"] = str(self.data)
        env["KARPATHY_UPDATE_CHECK_URL"] = self.remote.as_uri()
        env["KARPATHY_UPDATE_CHECK_INTERVAL_SECONDS"] = "0"
        for key in ("CODEX_CI", "CODEX_SHELL", "CODEX_THREAD_ID"):
            env.pop(key, None)
        env.update(extra)
        return env

    def run_tool(self, *args, **env):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            text=True,
            capture_output=True,
            check=False,
            env=self.env(**env),
        )

    def test_update_command_and_skill_define_public_surface(self):
        command = UPDATE_COMMAND.read_text(encoding="utf-8")
        skill = UPDATE_SKILL.read_text(encoding="utf-8")

        self.assertIn("karpathy-update", command)
        self.assertIn("/karpathy update", command)
        self.assertIn("/karpathy:update", command)
        self.assertIn("check_update.py --update", skill)
        self.assertIn("manually edit `~/.claude/plugins/cache`", skill)

    def test_hook_notice_points_to_karpathy_update(self):
        result = self.run_tool("--system-message")
        payload = json.loads(result.stdout)

        self.assertEqual(0, result.returncode)
        self.assertIn("Run `/karpathy update`", payload["systemMessage"])
        self.assertIn("/karpathy:update", payload["systemMessage"])
        self.assertNotIn("codex plugin marketplace upgrade", payload["systemMessage"])

    def test_manual_check_reports_update_available(self):
        result = self.run_tool("--check", "--json")
        payload = json.loads(result.stdout)

        self.assertEqual(0, result.returncode)
        self.assertEqual("update_available", payload["status"])
        self.assertTrue(payload["update_available"])
        self.assertIn("Run `/karpathy update`.", payload["instructions"])

    def test_manual_update_outside_codex_prints_fallbacks(self):
        result = self.run_tool("--update", "--json")
        payload = json.loads(result.stdout)

        self.assertEqual(0, result.returncode)
        self.assertEqual("manual_required", payload["action"])
        self.assertTrue(any("/plugin marketplace update karpathy-skills" in item for item in payload["instructions"]))

    def test_manual_update_in_codex_dry_run_lists_codex_commands(self):
        result = self.run_tool("--update", "--json", CODEX_SHELL="1", KARPATHY_UPDATE_DRY_RUN="1")
        payload = json.loads(result.stdout)

        self.assertEqual(0, result.returncode)
        self.assertEqual("dry_run", payload["action"])
        self.assertEqual(
            [
                "codex plugin marketplace upgrade karpathy-skills",
                "codex plugin add karpathy@karpathy-skills",
            ],
            payload["commands"],
        )


if __name__ == "__main__":
    unittest.main()
