import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "plugins" / "karpathy" / "scripts" / "check_update.py"
UPDATE_COMMAND = REPO_ROOT / "plugins" / "karpathy" / "commands" / "update.md"
UPDATE_SKILL = REPO_ROOT / "plugins" / "karpathy" / "skills" / "karpathy-update" / "SKILL.md"
README = REPO_ROOT / "README.md"

REQUIRED_COMMANDS = [
    "commands/audit.md",
    "commands/diff.md",
    "commands/refactor.md",
    "commands/wiki.md",
    "commands/setup.md",
    "commands/configure.md",
    "commands/update.md",
]
REQUIRED_SKILLS = [
    "skills/karpathy-audit/SKILL.md",
    "skills/karpathy-diff/SKILL.md",
    "skills/karpathy-refactor/SKILL.md",
    "skills/karpathy-update/SKILL.md",
    "skills/karpathy-wiki/SKILL.md",
]
REQUIRED_MANIFESTS = [
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
]


class UpdateToolTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.plugin_root = self.root / "plugin"
        self.codex_home = self.root / "codex-home"
        self.claude_home = self.root / "claude-home"
        self.data = self.root / "data"
        self.home = self.root / "home"
        self.write_plugin(version="1.0.0")
        self.write_remote("1.0.0")

    def tearDown(self):
        self.tempdir.cleanup()

    def write_remote(self, version):
        self.remote = self.root / "remote.json"
        self.remote.write_text(json.dumps({"version": version}) + "\n", encoding="utf-8")

    def write_plugin(self, version="1.0.0", omit=()):
        self.write_plugin_at(self.plugin_root, version=version, omit=omit)

    def write_plugin_at(self, root, version="1.0.0", omit=()):
        omit = set(omit)
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)

        for relative in REQUIRED_COMMANDS:
            if relative in omit:
                continue
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {Path(relative).stem}\n", encoding="utf-8")

        for relative in REQUIRED_SKILLS:
            if relative in omit:
                continue
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("---\nname: test\n---\n", encoding="utf-8")

        for relative in REQUIRED_MANIFESTS:
            if relative in omit:
                continue
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"name": "karpathy", "version": version}) + "\n", encoding="utf-8")

    def set_manifest_version(self, relative, version):
        path = self.plugin_root / relative
        path.write_text(json.dumps({"name": "karpathy", "version": version}) + "\n", encoding="utf-8")

    def make_cached_plugin(self, version="1.0.0", omit=()):
        path = self.codex_home / "plugins" / "cache" / "karpathy-skills" / "karpathy" / version
        self.write_plugin_at(path, version=version, omit=omit)
        return path

    def clear_plugin(self):
        if self.plugin_root.exists():
            shutil.rmtree(self.plugin_root)
        self.plugin_root.mkdir(parents=True)

    def env(self, **extra):
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PLUGIN_ROOT"] = str(self.plugin_root)
        env["KARPATHY_PLUGIN_DATA"] = str(self.data)
        env["KARPATHY_UPDATE_CHECK_URL"] = self.remote.as_uri()
        env["KARPATHY_UPDATE_CHECK_INTERVAL_SECONDS"] = "0"
        env["KARPATHY_CODEX_HOME"] = str(self.codex_home)
        env["KARPATHY_CLAUDE_HOME"] = str(self.claude_home)
        env["HOME"] = str(self.home)
        for key in (
            "CLAUDECODE",
            "CLAUDE_CODE",
            "CLAUDE_PLUGIN_DATA",
            "CLAUDE_PLUGIN_ROOT",
            "CODEX_CI",
            "CODEX_SHELL",
            "CODEX_THREAD_ID",
            "KARPATHY_DISABLE_UPDATE_CHECK",
            "KARPATHY_UPDATE_COMMAND_TIMEOUT_SECONDS",
            "KARPATHY_UPDATE_DRY_RUN",
            "PLUGIN_DATA",
        ):
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

    def payload(self, *args, **env):
        result = self.run_tool(*args, "--json", **env)
        self.assertEqual("", result.stderr)
        return result, json.loads(result.stdout)

    def make_legacy_skill(self, name):
        path = self.codex_home / "skills" / name
        path.mkdir(parents=True, exist_ok=True)
        source = REPO_ROOT / "plugins" / "karpathy" / "skills" / name / "SKILL.md"
        shutil.copyfile(source, path / "SKILL.md")
        return path

    def make_fake_codex(self, body):
        bin_dir = self.root / "bin"
        bin_dir.mkdir(exist_ok=True)
        codex = bin_dir / "codex"
        codex.write_text("#!/bin/sh\n" + body, encoding="utf-8")
        codex.chmod(0o755)
        return f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"

    def test_update_command_and_skill_define_public_surface(self):
        command = UPDATE_COMMAND.read_text(encoding="utf-8")
        skill = UPDATE_SKILL.read_text(encoding="utf-8")

        self.assertIn("karpathy-update", command)
        self.assertIn("/karpathy:update", command)
        self.assertIn("client-dependent shorthand", skill)
        self.assertIn("check_update.py --update", skill)
        self.assertIn("manually edit `~/.claude/plugins/cache`", skill)
        self.assertIn("/plugin install karpathy@karpathy-skills", skill)
        self.assertFalse((REPO_ROOT / "plugins" / "karpathy" / "commands" / "doctor.md").exists())

    def test_command_not_found_recovery_docs_include_codex_bootstrap(self):
        readme = README.read_text(encoding="utf-8")
        command = UPDATE_COMMAND.read_text(encoding="utf-8")
        skill = UPDATE_SKILL.read_text(encoding="utf-8")
        combined = "\n".join([readme, command, skill])

        self.assertIn("codex plugin marketplace upgrade karpathy-skills", combined)
        self.assertIn("codex plugin add karpathy@karpathy-skills", combined)
        self.assertIn("start a new Codex thread", combined)
        self.assertNotIn("/karpathy:doctor", command)

    def test_hook_reports_local_surface_repair_without_network_update_check(self):
        self.write_plugin(omit={"commands/update.md"})
        self.write_remote("1.2.0")

        result = self.run_tool("--system-message", KARPATHY_UPDATE_CHECK_URL=(self.root / "missing.json").as_uri())
        payload = json.loads(result.stdout)

        self.assertEqual(0, result.returncode)
        self.assertIn("Karpathy plugin install needs repair", payload["systemMessage"])
        self.assertIn("commands/update.md", payload["systemMessage"])
        self.assertIn("Run `/karpathy:update`", payload["systemMessage"])
        self.assertNotIn("1.0.0 -> 1.2.0", payload["systemMessage"])
        self.assertNotIn("codex plugin marketplace upgrade", payload["systemMessage"])

    def test_healthy_plugin_install(self):
        result, payload = self.payload("--check")

        self.assertEqual(0, result.returncode)
        self.assertEqual("healthy_plugin_install", payload["install_state"])
        self.assertEqual("none", payload["action"])
        self.assertEqual("1.0.0", payload["installed_version"])
        self.assertEqual("1.0.0", payload["latest_version"])
        self.assertEqual([], payload["required_surfaces"]["missing"])

    def test_update_available(self):
        self.write_remote("1.2.0")

        result, payload = self.payload("--check")

        self.assertEqual(0, result.returncode)
        self.assertEqual("plugin_update_available", payload["install_state"])
        self.assertEqual("update_available", payload["action"])
        self.assertTrue(payload["update_available"])
        self.assertIn("Run `/karpathy:update`.", payload["next_steps"])

    def test_partial_plugin_install_missing_command(self):
        self.write_plugin(omit={"commands/update.md"})

        result, payload = self.payload("--check")

        self.assertEqual(0, result.returncode)
        self.assertEqual("partial_plugin_install", payload["install_state"])
        self.assertEqual("repair_required", payload["action"])
        self.assertIn("commands/update.md", payload["required_surfaces"]["missing"])

    def test_partial_plugin_install_missing_skill(self):
        self.write_plugin(omit={"skills/karpathy-refactor/SKILL.md"})

        result, payload = self.payload("--check")

        self.assertEqual(0, result.returncode)
        self.assertEqual("partial_plugin_install", payload["install_state"])
        self.assertIn("skills/karpathy-refactor/SKILL.md", payload["required_surfaces"]["missing"])

    def test_manifest_version_mismatch_is_partial_plugin_install(self):
        self.set_manifest_version(".claude-plugin/plugin.json", "1.4.1")
        self.set_manifest_version(".codex-plugin/plugin.json", "1.4.0")
        self.write_remote("1.4.1")

        result, payload = self.payload("--check")

        self.assertEqual(0, result.returncode)
        self.assertEqual("partial_plugin_install", payload["install_state"])
        self.assertTrue(payload["manifest_version_mismatch"])
        self.assertEqual("1.4.1", payload["manifest_versions"][".claude-plugin/plugin.json"])
        self.assertEqual("1.4.0", payload["manifest_versions"][".codex-plugin/plugin.json"])

    def test_matching_malformed_manifest_versions_are_partial(self):
        self.set_manifest_version(".claude-plugin/plugin.json", "banana")
        self.set_manifest_version(".codex-plugin/plugin.json", "banana")

        result, payload = self.payload("--check")

        self.assertEqual(0, result.returncode)
        self.assertEqual("partial_plugin_install", payload["install_state"])
        self.assertTrue(payload["manifest_version_mismatch"])

    def test_manifest_version_with_trailing_garbage_is_partial(self):
        self.set_manifest_version(".claude-plugin/plugin.json", "1.4.1garbage")
        self.set_manifest_version(".codex-plugin/plugin.json", "1.4.1garbage")

        result, payload = self.payload("--check")

        self.assertEqual(0, result.returncode)
        self.assertEqual("partial_plugin_install", payload["install_state"])
        self.assertTrue(payload["manifest_version_mismatch"])

    def test_prerelease_version_is_older_than_stable_release(self):
        self.set_manifest_version(".claude-plugin/plugin.json", "1.4.1-beta.1")
        self.set_manifest_version(".codex-plugin/plugin.json", "1.4.1-beta.1")
        self.write_remote("1.4.1")

        result, payload = self.payload("--check")

        self.assertEqual(0, result.returncode)
        self.assertEqual("plugin_update_available", payload["install_state"])
        self.assertTrue(payload["update_available"])

    def test_prerelease_versions_use_semver_identifier_order(self):
        self.set_manifest_version(".claude-plugin/plugin.json", "1.4.1-beta.1")
        self.set_manifest_version(".codex-plugin/plugin.json", "1.4.1-beta.1")
        self.write_remote("1.4.1-beta.2")

        result, payload = self.payload("--check")

        self.assertEqual(0, result.returncode)
        self.assertEqual("plugin_update_available", payload["install_state"])
        self.assertTrue(payload["update_available"])

    def test_invalid_semver_identifiers_are_partial(self):
        for version in ("1.4.1-beta..1", "1.4.1-beta.", "1.4.1-01", "1.4.1+build..1"):
            with self.subTest(version=version):
                self.set_manifest_version(".claude-plugin/plugin.json", version)
                self.set_manifest_version(".codex-plugin/plugin.json", version)

                result, payload = self.payload("--check")

                self.assertEqual(0, result.returncode)
                self.assertEqual("partial_plugin_install", payload["install_state"])
                self.assertTrue(payload["manifest_version_mismatch"])

    def test_large_semver_components_do_not_crash(self):
        large = "9" * 5000
        version = f"{large}.0.0"
        self.set_manifest_version(".claude-plugin/plugin.json", version)
        self.set_manifest_version(".codex-plugin/plugin.json", version)
        self.write_remote("1.4.1")

        result, payload = self.payload("--check")

        self.assertEqual(0, result.returncode)
        self.assertEqual("healthy_plugin_install", payload["install_state"])

    def test_stale_thread_wins_over_partial_current_root_when_newer_cache_is_healthy(self):
        old_root = self.codex_home / "plugins" / "cache" / "karpathy-skills" / "karpathy" / "1.0.0"
        self.write_plugin_at(old_root, version="1.0.0", omit={"commands/update.md"})
        self.plugin_root = old_root
        cached = self.make_cached_plugin(version="1.4.1")
        self.write_remote("1.4.1")

        result, payload = self.payload("--check", CODEX_SHELL="1")

        self.assertEqual(0, result.returncode)
        self.assertEqual("current_thread_stale", payload["install_state"])
        self.assertEqual(str(cached.resolve()), payload["current_thread_stale_candidate"]["plugin_root"])
        self.assertIn("commands/update.md", payload["required_surfaces"]["missing"])

    def test_stale_thread_detected_when_current_root_has_no_readable_version(self):
        old_root = self.codex_home / "plugins" / "cache" / "karpathy-skills" / "karpathy" / "broken"
        self.write_plugin_at(
            old_root,
            version="1.0.0",
            omit={".claude-plugin/plugin.json", ".codex-plugin/plugin.json"},
        )
        self.plugin_root = old_root
        cached = self.make_cached_plugin(version="1.4.1")
        self.write_remote("1.4.1")

        result, payload = self.payload("--check", CODEX_SHELL="1")

        self.assertEqual(0, result.returncode)
        self.assertEqual("current_thread_stale", payload["install_state"])
        self.assertIsNone(payload["installed_version"])
        self.assertEqual(str(cached.resolve()), payload["current_thread_stale_candidate"]["plugin_root"])

    def test_stale_thread_ignores_newer_cache_with_manifest_mismatch(self):
        old_root = self.codex_home / "plugins" / "cache" / "karpathy-skills" / "karpathy" / "1.0.0"
        self.write_plugin_at(old_root, version="1.0.0", omit={"commands/update.md"})
        self.plugin_root = old_root
        cached = self.make_cached_plugin(version="1.4.1")
        manifest = cached / ".codex-plugin" / "plugin.json"
        manifest.write_text(json.dumps({"name": "karpathy", "version": "1.4.0"}) + "\n", encoding="utf-8")
        self.write_remote("1.4.1")

        result, payload = self.payload("--check", CODEX_SHELL="1")

        self.assertEqual(0, result.returncode)
        self.assertEqual("partial_plugin_install", payload["install_state"])
        self.assertIsNone(payload["current_thread_stale_candidate"])

    def test_stale_cache_behind_latest_still_reports_update_available(self):
        old_root = self.codex_home / "plugins" / "cache" / "karpathy-skills" / "karpathy" / "1.3.0"
        self.write_plugin_at(old_root, version="1.3.0", omit={"commands/update.md"})
        self.plugin_root = old_root
        self.make_cached_plugin(version="1.4.0")
        self.write_remote("1.4.1")

        result, payload = self.payload("--check", CODEX_SHELL="1")

        self.assertEqual(0, result.returncode)
        self.assertEqual("plugin_update_available", payload["install_state"])
        self.assertTrue(payload["update_available"])
        self.assertEqual("1.4.0", payload["effective_version"])

    def test_legacy_standalone_install(self):
        self.clear_plugin()
        self.make_legacy_skill("karpathy-audit")
        self.make_legacy_skill("karpathy-diff")
        self.make_legacy_skill("karpathy-wiki")

        result, payload = self.payload("--check")

        self.assertEqual(0, result.returncode)
        self.assertEqual("legacy_standalone_install", payload["install_state"])
        self.assertEqual(3, len(payload["legacy_standalone_dirs"]))
        self.assertTrue(any("codex plugin add karpathy@karpathy-skills" in step for step in payload["next_steps"]))

    def test_mixed_plugin_and_legacy_install(self):
        self.make_legacy_skill("karpathy-audit")

        result, payload = self.payload("--check")

        self.assertEqual(0, result.returncode)
        self.assertEqual("mixed_plugin_and_legacy_install", payload["install_state"])
        self.assertEqual("repair_required", payload["action"])
        self.assertEqual(1, len(payload["legacy_standalone_dirs"]))

    def test_archive_safety_and_backup_path(self):
        self.make_legacy_skill("karpathy-audit")
        self.make_legacy_skill("karpathy-wiki")
        unrelated = self.codex_home / "skills" / "not-karpathy"
        unrelated.mkdir(parents=True)
        path = self.make_fake_codex("exit 0\n")

        result, payload = self.payload("--update", CODEX_SHELL="1", PATH=path)

        self.assertEqual(0, result.returncode)
        self.assertEqual("repaired", payload["action"])
        self.assertIsNotNone(payload["backup_path"])
        backup = Path(payload["backup_path"])
        self.assertTrue((backup / "karpathy-audit").is_dir())
        self.assertTrue((backup / "karpathy-wiki").is_dir())
        self.assertTrue(unrelated.is_dir())
        self.assertFalse((self.codex_home / "skills" / "karpathy-audit").exists())

    def test_unrelated_skills_not_moved(self):
        self.make_legacy_skill("karpathy-diff")
        unrelated = self.codex_home / "skills" / "stripe"
        unrelated.mkdir(parents=True)
        path = self.make_fake_codex("exit 0\n")

        result, _payload = self.payload("--update", CODEX_SHELL="1", PATH=path)

        self.assertEqual(0, result.returncode)
        self.assertTrue(unrelated.is_dir())

    def test_custom_karpathy_prefixed_skill_not_moved(self):
        self.make_legacy_skill("karpathy-diff")
        custom = self.codex_home / "skills" / "karpathy-notes"
        custom.mkdir(parents=True)
        (custom / "SKILL.md").write_text("# custom\n", encoding="utf-8")
        path = self.make_fake_codex("exit 0\n")

        result, payload = self.payload("--update", CODEX_SHELL="1", PATH=path)

        self.assertEqual(0, result.returncode)
        self.assertEqual("repaired", payload["action"])
        self.assertTrue(custom.is_dir())
        archived_names = {Path(item).name for item in payload["archived_legacy_dirs"]}
        self.assertEqual({"karpathy-diff"}, archived_names)

    def test_custom_exact_name_skill_without_legacy_signature_is_not_moved(self):
        custom = self.codex_home / "skills" / "karpathy-audit"
        custom.mkdir(parents=True)
        (custom / "SKILL.md").write_text(
            "---\nname: karpathy-audit\n---\n\n# My Custom Audit\n",
            encoding="utf-8",
        )
        self.write_remote("1.2.0")
        path = self.make_fake_codex("exit 0\n")

        result, payload = self.payload("--update", CODEX_SHELL="1", PATH=path)

        self.assertEqual(1, result.returncode)
        self.assertEqual("manual_required", payload["action"])
        self.assertTrue(custom.is_dir())
        self.assertEqual([], payload.get("archived_legacy_dirs", []))

    def test_customized_fork_of_legacy_skill_is_not_moved(self):
        custom = self.make_legacy_skill("karpathy-audit")
        skill_file = custom / "SKILL.md"
        skill_file.write_text(
            skill_file.read_text(encoding="utf-8") + "\n# Local customization\n",
            encoding="utf-8",
        )
        self.write_remote("1.2.0")
        path = self.make_fake_codex("exit 0\n")

        result, payload = self.payload("--update", CODEX_SHELL="1", PATH=path)

        self.assertEqual(1, result.returncode)
        self.assertEqual("manual_required", payload["action"])
        self.assertTrue(custom.is_dir())
        self.assertEqual([], payload.get("archived_legacy_dirs", []))

    def test_archive_failure_reports_json_without_moving_legacy_dir(self):
        legacy = self.make_legacy_skill("karpathy-audit")
        backups = self.codex_home / "backups"
        backups.parent.mkdir(parents=True, exist_ok=True)
        backups.write_text("not a directory\n", encoding="utf-8")
        path = self.make_fake_codex("exit 0\n")

        result, payload = self.payload("--update", CODEX_SHELL="1", PATH=path)

        self.assertEqual(1, result.returncode)
        self.assertEqual("manual_required", payload["action"])
        self.assertIn("archive did not fully complete", payload["error"])
        self.assertTrue(legacy.is_dir())
        self.assertEqual([], payload["archived_legacy_dirs"])
        self.assertEqual(legacy.resolve(), Path(payload["archive_failed_dirs"][0]["path"]).resolve())

    def test_successful_repair_followed_by_surface_verification(self):
        self.write_plugin(omit={"commands/update.md"})
        path = self.make_fake_codex(
            """
if [ "$1" = "plugin" ] && [ "$2" = "add" ]; then
  mkdir -p "$PLUGIN_ROOT/commands"
  printf '# update\\n' > "$PLUGIN_ROOT/commands/update.md"
fi
exit 0
"""
        )

        result, payload = self.payload("--update", CODEX_SHELL="1", PATH=path)

        self.assertEqual(0, result.returncode)
        self.assertEqual("repaired", payload["action"])
        self.assertEqual("current_thread_stale", payload["install_state"])
        self.assertEqual([], payload["required_surfaces"]["missing"])
        self.assertEqual(2, len(payload["commands"]))
        self.assertIn("Start a new Codex thread", payload["next_steps"][0])

    def test_update_repair_fails_when_noop_codex_leaves_plugin_outdated(self):
        self.write_remote("9.0.0")
        path = self.make_fake_codex("exit 0\n")

        result, payload = self.payload("--update", CODEX_SHELL="1", PATH=path)

        self.assertEqual(1, result.returncode)
        self.assertEqual("manual_required", payload["action"])
        self.assertEqual("plugin_update_available", payload["install_state"])
        self.assertEqual("9.0.0", payload["repair_target_version"])
        self.assertIn("still older than repair target 9.0.0", payload["error"])

    def test_update_repair_preserves_target_when_latest_version_becomes_unavailable(self):
        self.write_remote("9.0.0")
        path = self.make_fake_codex('rm -f "$REMOTE_FILE"\nexit 0\n')

        result, payload = self.payload(
            "--update",
            CODEX_SHELL="1",
            PATH=path,
            REMOTE_FILE=str(self.remote),
        )

        self.assertEqual(1, result.returncode)
        self.assertEqual("manual_required", payload["action"])
        self.assertEqual("9.0.0", payload["repair_target_version"])
        self.assertIn("still older than repair target 9.0.0", payload["error"])

    def test_codex_cli_missing(self):
        self.write_remote("1.2.0")
        empty_bin = self.root / "empty-bin"
        empty_bin.mkdir()

        result, payload = self.payload("--update", CODEX_SHELL="1", PATH=str(empty_bin))

        self.assertEqual(1, result.returncode)
        self.assertEqual("manual_required", payload["action"])
        self.assertIn("codex CLI was not found", payload["error"])

    def test_codex_command_timeout(self):
        self.write_remote("1.2.0")
        path = self.make_fake_codex("sleep 2\n")

        result, payload = self.payload(
            "--update",
            CODEX_SHELL="1",
            KARPATHY_UPDATE_COMMAND_TIMEOUT_SECONDS="0.05",
            PATH=path,
        )

        self.assertEqual(1, result.returncode)
        self.assertEqual("manual_required", payload["action"])
        self.assertIn("timed out after 0.05 seconds", payload["error"])
        self.assertEqual(1, len(payload["commands"]))
        self.assertIsNone(payload["commands"][0]["returncode"])

    def test_codex_command_nonzero(self):
        self.write_remote("1.2.0")
        path = self.make_fake_codex("echo failed >&2\nexit 42\n")

        result, payload = self.payload("--update", CODEX_SHELL="1", PATH=path)

        self.assertEqual(1, result.returncode)
        self.assertEqual("manual_required", payload["action"])
        self.assertEqual(42, payload["commands"][0]["returncode"])
        self.assertEqual("failed", payload["error"])

    def test_network_latest_version_unavailable_but_local_surfaces_healthy(self):
        missing_remote = self.root / "does-not-exist.json"

        result, payload = self.payload("--check", KARPATHY_UPDATE_CHECK_URL=missing_remote.as_uri())

        self.assertEqual(0, result.returncode)
        self.assertEqual("healthy_plugin_install", payload["install_state"])
        self.assertIsNone(payload["latest_version"])
        self.assertFalse(payload["update_available"])
        self.assertEqual([], payload["required_surfaces"]["missing"])

    def test_text_and_json_parity_for_key_fields(self):
        _json_result, payload = self.payload("--check")
        text_result = self.run_tool("--check")

        self.assertEqual(0, text_result.returncode)
        self.assertIn(f"Client: {payload['client']}", text_result.stdout)
        self.assertIn(f"Install state: {payload['install_state']}", text_result.stdout)
        self.assertIn(f"Installed version: {payload['installed_version']}", text_result.stdout)
        self.assertIn(f"Latest version: {payload['latest_version']}", text_result.stdout)
        self.assertIn(f"Action: {payload['action']}", text_result.stdout)

    def test_manual_update_in_codex_dry_run_lists_supported_commands_only(self):
        self.write_remote("1.2.0")

        result, payload = self.payload("--update", CODEX_SHELL="1", KARPATHY_UPDATE_DRY_RUN="1")

        self.assertEqual(0, result.returncode)
        self.assertEqual("dry_run", payload["action"])
        self.assertEqual(
            [
                "codex plugin marketplace upgrade karpathy-skills",
                "codex plugin add karpathy@karpathy-skills",
            ],
            payload["commands"],
        )

    def test_manual_update_outside_codex_prints_manual_fallbacks(self):
        self.write_remote("1.2.0")

        result, payload = self.payload("--update")

        self.assertEqual(0, result.returncode)
        self.assertEqual("manual_required", payload["action"])
        self.assertTrue(any("/plugin marketplace update karpathy-skills" in item for item in payload["instructions"]))
        self.assertTrue(any("/plugin install karpathy@karpathy-skills" in item for item in payload["instructions"]))


if __name__ == "__main__":
    unittest.main()
