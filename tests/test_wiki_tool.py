import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "plugins" / "karpathy" / "skills" / "karpathy-wiki" / "scripts" / "wiki_tool.py"

spec = importlib.util.spec_from_file_location("wiki_tool", SCRIPT)
wiki_tool = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["wiki_tool"] = wiki_tool
spec.loader.exec_module(wiki_tool)


def run(args, cwd, check=True):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=check, env=env)


def git(repo, *args):
    return run(["git", *args], repo)


class WikiToolTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        git(self.repo, "init")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "Test User")
        (self.repo / "README.md").write_text("# Test Repo\n", encoding="utf-8")
        git(self.repo, "add", "README.md")
        git(self.repo, "commit", "-m", "init")

    def tearDown(self):
        self.tempdir.cleanup()

    def write_concept(self, relative_path, resource, title="Auth Concept", body=""):
        path = self.repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(
                [
                    "---",
                    "type: Component",
                    f"title: {title}",
                    "description: Tracks auth behavior.",
                    f"resource: {resource}",
                    "timestamp: 2026-06-19T00:00:00Z",
                    "confidence: high",
                    "---",
                    "",
                    "# Role",
                    body,
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return path

    def write_source(self, relative_path, body="export const value = true;\n"):
        path = self.repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def commit_all(self, message):
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", message)

    def test_init_creates_structure_and_does_not_overwrite_existing_files(self):
        first = wiki_tool.init_wiki(self.repo)
        self.assertTrue((self.repo / "knowledge" / "wiki" / "index.md").exists())
        self.assertTrue((self.repo / "knowledge" / "wiki" / "components").is_dir())
        self.assertIn("knowledge/wiki/.karpathy-wiki.json", first["created"])

        index = self.repo / "knowledge" / "wiki" / "index.md"
        index.write_text("custom index\n", encoding="utf-8")
        second = wiki_tool.init_wiki(self.repo)

        self.assertEqual("custom index\n", index.read_text(encoding="utf-8"))
        self.assertIn("knowledge/wiki/index.md", second["skipped"])

    def test_status_reports_incomplete_setup_when_required_files_are_missing(self):
        (self.repo / "knowledge" / "wiki" / "components").mkdir(parents=True)

        result = wiki_tool.status(self.repo)

        self.assertEqual("incomplete-setup", result["setup_state"])
        self.assertEqual(
            [
                "knowledge/wiki/index.md",
                "knowledge/wiki/log.md",
                "knowledge/wiki/.karpathy-wiki.json",
            ],
            result["missing_required_files"],
        )

    def test_status_reports_needs_starter_concepts_after_init(self):
        (self.repo / "src").mkdir()
        (self.repo / "src" / "main.tsx").write_text("export function main() {}\n", encoding="utf-8")
        (self.repo / "package.json").write_text(
            '{"scripts":{"test":"vitest run","typecheck":"tsc --noEmit"}}\n',
            encoding="utf-8",
        )
        wiki_tool.init_wiki(self.repo)

        result = wiki_tool.status(self.repo)

        self.assertEqual("needs-starter-concepts", result["setup_state"])
        self.assertEqual(0, result["concept_count"])
        self.assertEqual([], result["missing_required_files"])
        candidate_paths = [candidate["path"] for candidate in result["starter_candidates"]]
        self.assertIn("knowledge/wiki/components/app-boot.md", candidate_paths)
        self.assertIn("knowledge/wiki/tests/verification-surface.md", candidate_paths)

    def test_concept_plan_detects_high_value_repo_areas(self):
        self.write_source("src/main.tsx")
        self.write_source("src/app/router.tsx")
        self.write_source("src/features/shell/project-shell.tsx")
        self.write_source("src/features/auth/data.ts")
        self.write_source("src/features/auth/session.repository.ts")
        self.write_source("src/features/auth/AuthSessionSync.tsx")
        self.write_source("src/features/projects/project-shell.queries.ts")
        self.write_source("src/features/projects/project-shell.repository.ts")
        self.write_source("src/features/projects/project-shell.bootstrap.ts")
        self.write_source("packages/mcp-server/src/server.ts")
        self.write_source("packages/mcp-server/src/service.ts")
        self.write_source("packages/mcp-server/src/tool-schemas.ts")
        (self.repo / "docs" / "public").mkdir(parents=True)
        (self.repo / "docs" / "public" / "MCP.md").write_text("# MCP\n", encoding="utf-8")
        (self.repo / "docs" / "public" / "SQL_MIGRATIONS.md").write_text("# SQL migrations\n", encoding="utf-8")
        (self.repo / "package.json").write_text(
            '{"scripts":{"test":"vitest run","typecheck":"tsc --noEmit","build":"vite build"}}\n',
            encoding="utf-8",
        )
        wiki_tool.init_wiki(self.repo)

        plan = wiki_tool.concept_plan(self.repo, limit=10)
        by_path = {candidate["path"]: candidate for candidate in plan["candidates"]}

        self.assertIn("knowledge/wiki/components/app-boot.md", by_path)
        self.assertIn("knowledge/wiki/components/auth-session.md", by_path)
        self.assertIn("knowledge/wiki/components/app-routing-and-shell.md", by_path)
        self.assertIn("knowledge/wiki/components/project-shell-data.md", by_path)
        self.assertIn("knowledge/wiki/components/mcp-server.md", by_path)
        self.assertIn("knowledge/wiki/tests/verification-surface.md", by_path)
        self.assertIn("knowledge/wiki/invariants/sql-migrations.md", by_path)
        self.assertIn("knowledge/wiki/recipes/karpathy-wiki-smoke-test.md", by_path)
        self.assertIn("src/features/auth/session.repository.ts", by_path["knowledge/wiki/components/auth-session.md"]["read"])
        self.assertIn("src/app/router.tsx", by_path["knowledge/wiki/components/app-routing-and-shell.md"]["read"])
        self.assertIn(
            "src/features/projects/project-shell.repository.ts",
            by_path["knowledge/wiki/components/project-shell-data.md"]["read"],
        )
        self.assertIn("packages/mcp-server/src/tool-schemas.ts", by_path["knowledge/wiki/components/mcp-server.md"]["read"])

    def test_concept_plan_cli_outputs_json_candidates(self):
        self.write_source("src/features/auth/session.repository.ts")
        wiki_tool.init_wiki(self.repo)

        result = run(
            [
                sys.executable,
                str(SCRIPT),
                "concept-plan",
                "--repo",
                str(self.repo),
                "--json",
                "--limit",
                "3",
            ],
            self.repo,
        )

        self.assertIn('"candidates"', result.stdout)
        self.assertIn("knowledge/wiki/components/auth-session.md", result.stdout)

    def test_concept_plan_default_output_omits_history_fields(self):
        self.write_source("src/features/auth/session.repository.ts")
        self.commit_all("add auth")
        wiki_tool.init_wiki(self.repo)

        plan = wiki_tool.concept_plan(self.repo, limit=3)

        self.assertNotIn("history_signals", plan)
        self.assertNotIn("planning_tasks", plan)
        self.assertTrue(plan["candidates"])
        self.assertNotIn("score", plan["candidates"][0])
        self.assertNotIn("evidence", plan["candidates"][0])

    def test_concept_plan_include_history_scores_candidates_from_git_history(self):
        self.write_source("src/features/auth/session.repository.ts", "export const session = 'v1';\n")
        self.write_source("src/features/auth/AuthSessionSync.tsx", "export const sync = true;\n")
        self.write_source("src/app/router.tsx", "export const router = true;\n")
        self.write_source("tests/auth/session.test.ts", "test('session redirect', () => {});\n")
        self.write_source("dist/generated.js", "generated\n")
        (self.repo / "package-lock.json").write_text('{"lockfileVersion":3}\n', encoding="utf-8")
        self.commit_all("fix auth session redirect regression")
        self.write_source("src/features/auth/session.repository.ts", "export const session = 'v2';\n")
        self.write_source("src/app/router.tsx", "export const router = 'redirect';\n")
        self.write_source("tests/auth/session.test.ts", "test('session redirect again', () => {});\n")
        self.commit_all("fix broken login redirect")
        wiki_tool.init_wiki(self.repo)

        plan = wiki_tool.concept_plan(self.repo, limit=5, include_history=True)
        by_path = {candidate["path"]: candidate for candidate in plan["candidates"]}

        self.assertIn("history_signals", plan)
        self.assertIn("planning_tasks", plan)
        self.assertIn("scoring_model", plan)
        self.assertIn("knowledge/wiki/components/auth-session.md", by_path)
        auth = by_path["knowledge/wiki/components/auth-session.md"]
        self.assertGreater(auth["score"], 0)
        self.assertIn("score_breakdown", auth)
        self.assertIn("covered_tasks", auth)
        self.assertIn("acceptance_queries", auth)
        self.assertTrue(auth["evidence"])
        history_paths = [item["path"] for item in plan["history_signals"]["high_churn_directories"]]
        self.assertNotIn("dist", history_paths)
        self.assertNotIn("package-lock.json", history_paths)

    def test_concept_plan_include_history_cli_emits_enriched_fields(self):
        self.write_source("src/features/auth/session.repository.ts")
        self.commit_all("fix auth session")
        wiki_tool.init_wiki(self.repo)

        result = run(
            [
                sys.executable,
                str(SCRIPT),
                "concept-plan",
                "--repo",
                str(self.repo),
                "--json",
                "--include-history",
                "--limit",
                "3",
            ],
            self.repo,
        )

        self.assertIn('"history_signals"', result.stdout)
        self.assertIn('"scoring_model"', result.stdout)
        self.assertIn('"score"', result.stdout)

    def test_weighted_set_cover_prefers_one_cohesive_candidate(self):
        self.write_source("src/features/auth/session.repository.ts")
        self.write_source("src/features/auth/redirect.ts")
        self.write_source("src/app/router.tsx")
        broad = wiki_tool.concept_plan_candidate(
            self.repo,
            "knowledge/wiki/components/auth-session.md",
            "Component",
            "Auth Session",
            "src/features/auth",
            "Auth owns session and redirect behavior.",
            read=["src/features/auth/session.repository.ts", "src/features/auth/redirect.ts"],
            priority=20,
        )
        narrow_session = wiki_tool.concept_plan_candidate(
            self.repo,
            "knowledge/wiki/components/session-repository.md",
            "Component",
            "Session Repository",
            "src/features/auth/session.repository.ts",
            "Narrow session repository page.",
            read=["src/features/auth/session.repository.ts"],
            priority=20,
        )
        narrow_redirect = wiki_tool.concept_plan_candidate(
            self.repo,
            "knowledge/wiki/components/auth-redirect.md",
            "Component",
            "Auth Redirect",
            "src/features/auth/redirect.ts",
            "Narrow redirect page.",
            read=["src/features/auth/redirect.ts"],
            priority=20,
        )
        tasks = [
            wiki_tool.PlanningTask(
                id="churn:1",
                kind="churn",
                weight=8,
                paths=["src/features/auth/session.repository.ts"],
                terms=["auth", "session"],
                evidence="session changed frequently",
            ),
            wiki_tool.PlanningTask(
                id="risk:1",
                kind="risk",
                weight=6,
                paths=["src/features/auth/redirect.ts"],
                terms=["auth", "redirect"],
                evidence="redirect is risky",
            ),
        ]
        scored = [wiki_tool.score_candidate(self.repo, candidate, tasks) for candidate in [narrow_session, narrow_redirect, broad]]

        selected = wiki_tool.select_scored_candidates(self.repo, scored, tasks, limit=1)

        self.assertEqual("knowledge/wiki/components/auth-session.md", selected[0].candidate["path"])

    def test_weighted_set_cover_fills_limit_with_static_candidates(self):
        covered = wiki_tool.ScoredCandidate(
            candidate={"path": "knowledge/wiki/components/auth-session.md"},
            score=40,
            evidence={},
            covered_tasks=["churn:auth"],
            score_breakdown={},
        )
        static = wiki_tool.ScoredCandidate(
            candidate={"path": "knowledge/wiki/components/app-boot.md"},
            score=10,
            evidence={},
            covered_tasks=[],
            score_breakdown={},
        )
        tasks = [
            wiki_tool.PlanningTask(
                id="churn:auth",
                kind="churn",
                weight=8,
                paths=["src/features/auth/session.repository.ts"],
                terms=["auth", "session"],
                evidence="auth changed frequently",
            )
        ]

        selected = wiki_tool.select_scored_candidates(self.repo, [covered, static], tasks, limit=2)

        self.assertEqual(
            [
                "knowledge/wiki/components/auth-session.md",
                "knowledge/wiki/components/app-boot.md",
            ],
            [item.candidate["path"] for item in selected],
        )

    def test_history_matching_ignores_generic_feature_terms(self):
        self.write_source("src/features/notes/note.repository.ts")
        self.write_source("src/features/shell/project-shell.tsx")
        notes = wiki_tool.concept_plan_candidate(
            self.repo,
            "knowledge/wiki/components/note-data-flow.md",
            "Component",
            "Note Data Flow",
            "src/features/notes",
            "Feature directory has durable data-flow signals: repository.",
            read=["src/features/notes/note.repository.ts"],
            priority=20,
        )
        shell_task = wiki_tool.PlanningTask(
            id="churn:shell",
            kind="churn",
            weight=8,
            paths=["src/features/shell/project-shell.tsx"],
            terms=wiki_tool.history_match_terms("src/features/shell/project-shell.tsx"),
            evidence="src/features/shell changed frequently",
        )
        notes_task = wiki_tool.PlanningTask(
            id="churn:notes",
            kind="churn",
            weight=8,
            paths=["src/features/notes/note.repository.ts"],
            terms=wiki_tool.history_match_terms("src/features/notes/note.repository.ts"),
            evidence="src/features/notes changed frequently",
        )

        self.assertFalse(wiki_tool.candidate_covers_task(self.repo, notes, shell_task))
        self.assertTrue(wiki_tool.candidate_covers_task(self.repo, notes, notes_task))

    def test_status_reports_ready_when_concepts_exist(self):
        wiki_tool.init_wiki(self.repo)
        (self.repo / "src").mkdir()
        (self.repo / "src" / "auth.ts").write_text("export const auth = true;\n", encoding="utf-8")
        self.write_concept("knowledge/wiki/components/auth.md", "../../../src/auth.ts")
        wiki_tool.save_manifest(self.repo)

        result = wiki_tool.status(self.repo)

        self.assertEqual("ready", result["setup_state"])
        self.assertEqual(1, result["concept_count"])
        self.assertEqual([], result["starter_candidates"])

    def test_refresh_manifest_indexes_file_resources(self):
        (self.repo / "src").mkdir()
        (self.repo / "src" / "auth.ts").write_text("export const auth = true;\n", encoding="utf-8")
        self.write_concept("knowledge/wiki/components/auth.md", "../../../src/auth.ts")

        manifest = wiki_tool.save_manifest(self.repo)

        self.assertIn("src/auth.ts", manifest["source_map"])
        self.assertEqual(["knowledge/wiki/components/auth.md"], manifest["source_map"]["src/auth.ts"])

    def test_refresh_manifest_indexes_directory_resources(self):
        (self.repo / "src" / "auth").mkdir(parents=True)
        (self.repo / "src" / "auth" / "session.ts").write_text("export const session = true;\n", encoding="utf-8")
        self.write_concept("knowledge/wiki/components/auth.md", "../../../src/auth")

        manifest = wiki_tool.save_manifest(self.repo)

        self.assertIn("src/auth", manifest["source_map"])
        self.assertEqual(["knowledge/wiki/components/auth.md"], manifest["source_map"]["src/auth"])
        self.assertEqual("directory", manifest["source_kinds"]["src/auth"])

    def test_affected_concepts_matches_exact_file_resources(self):
        (self.repo / "src").mkdir()
        (self.repo / "src" / "user.ts").write_text("export const user = true;\n", encoding="utf-8")
        self.write_concept("knowledge/wiki/components/user.md", "../../../src/user.ts", title="User Concept")
        manifest = wiki_tool.save_manifest(self.repo)

        affected = wiki_tool.affected_concepts(self.repo, ["src/user.ts"], manifest)

        self.assertEqual({"knowledge/wiki/components/user.md": ["src/user.ts"]}, affected)

    def test_affected_concepts_matches_files_inside_cited_directories(self):
        (self.repo / "src" / "auth").mkdir(parents=True)
        (self.repo / "src" / "auth" / "session.ts").write_text("export const session = true;\n", encoding="utf-8")
        self.write_concept("knowledge/wiki/components/auth.md", "../../../src/auth")
        manifest = wiki_tool.save_manifest(self.repo)

        affected = wiki_tool.affected_concepts(self.repo, ["src/auth/session.ts"], manifest)

        self.assertEqual({"knowledge/wiki/components/auth.md": ["src/auth/session.ts"]}, affected)

    def test_affected_concepts_matches_deleted_files_from_persisted_directory_resources(self):
        (self.repo / "src" / "auth").mkdir(parents=True)
        (self.repo / "src" / "auth" / "session.ts").write_text("export const session = true;\n", encoding="utf-8")
        self.write_concept("knowledge/wiki/components/auth.md", "../../../src/auth")
        manifest = wiki_tool.save_manifest(self.repo)
        shutil.rmtree(self.repo / "src" / "auth")

        affected = wiki_tool.affected_concepts(self.repo, ["src/auth/session.ts"], manifest)

        self.assertEqual({"knowledge/wiki/components/auth.md": ["src/auth/session.ts"]}, affected)

    def test_status_reports_untracked_files_inside_cited_directories(self):
        (self.repo / "src" / "auth").mkdir(parents=True)
        self.write_concept("knowledge/wiki/components/auth.md", "../../../src/auth")
        wiki_tool.save_manifest(self.repo)
        (self.repo / "src" / "auth" / "new.ts").write_text("export const created = true;\n", encoding="utf-8")

        result = wiki_tool.status(self.repo)

        self.assertEqual({"knowledge/wiki/components/auth.md": ["src/auth/new.ts"]}, result["affected_concepts"])

    def test_status_reports_deleted_files_inside_cited_directories(self):
        (self.repo / "src" / "auth").mkdir(parents=True)
        (self.repo / "src" / "auth" / "session.ts").write_text("export const session = true;\n", encoding="utf-8")
        self.write_concept("knowledge/wiki/components/auth.md", "../../../src/auth")
        wiki_tool.save_manifest(self.repo)
        git(self.repo, "add", "src", "knowledge")
        git(self.repo, "commit", "-m", "add wiki")
        shutil.rmtree(self.repo / "src" / "auth")

        result = wiki_tool.status(self.repo)

        self.assertEqual({"knowledge/wiki/components/auth.md": ["src/auth/session.ts"]}, result["affected_concepts"])

    def test_update_plan_default_scope_includes_untracked_files(self):
        (self.repo / "src" / "auth").mkdir(parents=True)
        self.write_concept("knowledge/wiki/components/auth.md", "../../../src/auth")
        wiki_tool.save_manifest(self.repo)
        (self.repo / "src" / "auth" / "new.ts").write_text("export const created = true;\n", encoding="utf-8")

        result = wiki_tool.affected_report(self.repo)

        self.assertEqual("all", result["scope"])
        self.assertEqual({"knowledge/wiki/components/auth.md": ["src/auth/new.ts"]}, result["affected_concepts"])

    def test_doctor_reports_missing_wiki(self):
        result = wiki_tool.doctor(self.repo)

        self.assertIn(
            {"severity": "critical", "path": "knowledge/wiki", "message": "wiki directory does not exist"},
            result["issues"],
        )

    def test_doctor_reports_broken_local_links_and_missing_frontmatter(self):
        (self.repo / "knowledge" / "wiki" / "components").mkdir(parents=True)
        (self.repo / "knowledge" / "wiki" / "index.md").write_text("# Index\n", encoding="utf-8")
        (self.repo / "knowledge" / "wiki" / "log.md").write_text("# Log\n", encoding="utf-8")
        (self.repo / "knowledge" / "wiki" / "components" / "bad.md").write_text(
            "# Bad\n[missing](missing.md)\n",
            encoding="utf-8",
        )

        result = wiki_tool.doctor(self.repo)
        messages = [issue["message"] for issue in result["issues"]]

        self.assertIn("missing YAML frontmatter", messages)
        self.assertIn("broken local link: missing.md", messages)
        self.assertIn("missing frontmatter field: type", messages)

    def test_doctor_reports_stale_persisted_manifest(self):
        (self.repo / "src").mkdir()
        (self.repo / "src" / "old.ts").write_text("old\n", encoding="utf-8")
        (self.repo / "src" / "new.ts").write_text("new\n", encoding="utf-8")
        concept = self.write_concept("knowledge/wiki/components/auth.md", "../../../src/old.ts")
        wiki_tool.save_manifest(self.repo)
        concept.write_text(concept.read_text(encoding="utf-8").replace("../../../src/old.ts", "../../../src/new.ts"), encoding="utf-8")

        result = wiki_tool.doctor(self.repo)
        issues = [(issue["path"], issue["message"]) for issue in result["issues"]]

        self.assertIn(
            ("knowledge/wiki/.karpathy-wiki.json", "persisted manifest is stale; run refresh-manifest"),
            issues,
        )

    def test_reminder_hook_prints_canonical_command_and_exits_zero_by_default(self):
        (self.repo / "src").mkdir()
        source = self.repo / "src" / "auth.ts"
        source.write_text("export const auth = true;\n", encoding="utf-8")
        self.write_concept("knowledge/wiki/components/auth.md", "../../../src/auth.ts")
        wiki_tool.save_manifest(self.repo)
        git(self.repo, "add", "src/auth.ts")

        result = run([sys.executable, str(SCRIPT), "reminder-hook", "--repo", str(self.repo)], self.repo, check=False)

        self.assertEqual(0, result.returncode)
        self.assertIn("/karpathy:wiki", result.stdout)
        self.assertIn("karpathy wiki", result.stdout)
        self.assertIn("Commit is allowed", result.stdout)

    def test_reminder_hook_strict_message_does_not_require_env_var(self):
        (self.repo / "src").mkdir()
        source = self.repo / "src" / "auth.ts"
        source.write_text("export const auth = true;\n", encoding="utf-8")
        self.write_concept("knowledge/wiki/components/auth.md", "../../../src/auth.ts")
        wiki_tool.save_manifest(self.repo)
        git(self.repo, "add", "src/auth.ts")

        result = run([sys.executable, str(SCRIPT), "reminder-hook", "--repo", str(self.repo), "--strict"], self.repo, check=False)

        self.assertEqual(1, result.returncode)
        self.assertIn("strict stale-wiki mode is enabled", result.stdout)
        self.assertNotIn("KARPATHY_WIKI_STRICT=1", result.stdout)

    def test_install_hook_is_idempotent_and_respects_core_hooks_path(self):
        first = wiki_tool.install_hook(self.repo, SCRIPT)
        second = wiki_tool.install_hook(self.repo, SCRIPT)
        hook = self.repo / ".git" / "hooks" / "pre-commit"
        text = hook.read_text(encoding="utf-8")

        self.assertEqual("installed", first["action"])
        self.assertEqual("updated", second["action"])
        self.assertEqual(1, text.count(wiki_tool.MANAGED_HOOK_BEGIN))

        custom_hooks = self.repo / ".githooks"
        git(self.repo, "config", "core.hooksPath", ".githooks")
        result = wiki_tool.install_hook(self.repo, SCRIPT)

        self.assertEqual("installed", result["action"])
        self.assertTrue((custom_hooks / "pre-commit").exists())

    def test_install_hook_refuses_non_shell_hooks(self):
        hook = self.repo / ".git" / "hooks" / "pre-commit"
        hook.write_text("#!/usr/bin/env python3\nprint('custom')\n", encoding="utf-8")

        with self.assertRaises(SystemExit):
            wiki_tool.install_hook(self.repo, SCRIPT)

    def test_append_improvement_note_creates_local_dogfood_log(self):
        result = wiki_tool.append_improvement_note(
            self.repo,
            "Setup leaked helper scripts",
            "The agent asked the user to run wiki_tool.py manually.",
            suggestion="Make the skill run helper scripts internally and summarize results.",
            evidence=["plugins/karpathy/skills/karpathy-wiki/SKILL.md"],
            tags=["ux", "dogfood"],
        )
        path = self.repo / "knowledge" / "outputs" / "wiki-improvements.md"
        text = path.read_text(encoding="utf-8")

        self.assertEqual("knowledge/outputs/wiki-improvements.md", result["path"])
        self.assertIn("# Karpathy Wiki Improvement Notes", text)
        self.assertIn("## ", text)
        self.assertIn("Setup leaked helper scripts", text)
        self.assertIn("The agent asked the user to run wiki_tool.py manually.", text)
        self.assertIn("Make the skill run helper scripts internally and summarize results.", text)
        self.assertIn("plugins/karpathy/skills/karpathy-wiki/SKILL.md", text)
        self.assertIn("Do not stage this file automatically.", text)

    def test_note_improvement_cli_appends_log(self):
        result = run(
            [
                sys.executable,
                str(SCRIPT),
                "note-improvement",
                "--repo",
                str(self.repo),
                "--title",
                "Search result noisy",
                "--body",
                "The top result was right, but unrelated concepts ranked too high.",
                "--suggestion",
                "Tune search scoring or include confidence guidance in answer mode.",
                "--evidence",
                "knowledge/wiki/tests/verification-surface.md",
                "--tag",
                "ranking",
            ],
            self.repo,
        )

        self.assertIn("Appended knowledge/outputs/wiki-improvements.md", result.stdout)
        text = (self.repo / "knowledge" / "outputs" / "wiki-improvements.md").read_text(encoding="utf-8")
        self.assertIn("Search result noisy", text)
        self.assertIn("Tune search scoring or include confidence guidance in answer mode.", text)
        self.assertIn("Tags: ranking", text)


if __name__ == "__main__":
    unittest.main()
