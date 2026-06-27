import importlib.util
import json
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

    def write_raw_body(self, name, body):
        path = self.repo / name
        path.write_text(body, encoding="utf-8")
        return path

    def commit_all(self, message):
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", message)

    def test_init_creates_structure_and_does_not_overwrite_existing_files(self):
        first = wiki_tool.init_wiki(self.repo)
        self.assertTrue((self.repo / "knowledge" / "wiki" / "index.md").exists())
        self.assertTrue((self.repo / "knowledge" / "wiki" / "components").is_dir())
        for dirname in wiki_tool.CONCEPT_DIRS.values():
            self.assertTrue((self.repo / "knowledge" / "wiki" / dirname / "index.md").exists())
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

    def test_raw_add_writes_required_frontmatter_json_and_stable_hash(self):
        body_file = self.write_raw_body("ticket.txt", "Customer says search fails.\n")

        result = wiki_tool.raw_add(
            self.repo,
            "tickets",
            "Search Bug",
            body_file,
            source_url="https://example.test/tickets/1",
        )
        path = self.repo / result["path"]
        frontmatter, body = wiki_tool.parse_frontmatter(path.read_text(encoding="utf-8"))

        self.assertRegex(result["source_id"], r"^tickets-search-bug-\d{4}-\d{2}-\d{2}$")
        self.assertEqual("knowledge/raw/tickets/" + result["source_id"] + ".md", result["path"])
        self.assertEqual("Raw Source", frontmatter["type"])
        self.assertEqual(result["source_id"], frontmatter["source_id"])
        self.assertEqual("tickets", frontmatter["kind"])
        self.assertEqual("Search Bug", frontmatter["title"])
        self.assertEqual("https://example.test/tickets/1", frontmatter["source_url"])
        self.assertEqual(git(self.repo, "rev-parse", "--short", "HEAD").stdout.strip(), frontmatter["source_commit"])
        self.assertEqual("Customer says search fails.\n", body)
        self.assertEqual(wiki_tool.sha256_text(body), frontmatter["sha256"])
        self.assertEqual(frontmatter["sha256"], result["sha256"])
        self.assertEqual(frontmatter["timestamp"], result["created"])
        self.assertEqual("", result["supersedes"])
        self.assertFalse(result["redacted"])

    def test_raw_add_never_overwrites_existing_record(self):
        first_body = self.write_raw_body("first.txt", "First ticket body.\n")
        second_body = self.write_raw_body("second.txt", "Second ticket body.\n")

        first = wiki_tool.raw_add(self.repo, "tickets", "Duplicate Title", first_body)
        first_text = (self.repo / first["path"]).read_text(encoding="utf-8")
        second = wiki_tool.raw_add(self.repo, "tickets", "Duplicate Title", second_body)

        self.assertNotEqual(first["source_id"], second["source_id"])
        self.assertTrue(second["source_id"].endswith("-2"))
        self.assertEqual(first_text, (self.repo / first["path"]).read_text(encoding="utf-8"))
        self.assertEqual("Second ticket body.\n", second["body"])

    def test_raw_correct_creates_append_only_record_referencing_prior_source(self):
        original_body = self.write_raw_body("original.txt", "Original meeting note.\n")
        correction_body = self.write_raw_body("correction.txt", "Corrected meeting note.\n")
        original = wiki_tool.raw_add(self.repo, "meeting-notes", "Planning Sync", original_body)

        correction = wiki_tool.raw_correct(self.repo, original["source_id"], correction_body)
        frontmatter, body = wiki_tool.parse_frontmatter((self.repo / correction["path"]).read_text(encoding="utf-8"))
        original_frontmatter, original_stored_body = wiki_tool.parse_frontmatter(
            (self.repo / original["path"]).read_text(encoding="utf-8")
        )

        self.assertNotEqual(original["source_id"], correction["source_id"])
        self.assertEqual(original["source_id"], correction["supersedes"])
        self.assertEqual(original["source_id"], frontmatter["supersedes"])
        self.assertEqual("Correction for Planning Sync", frontmatter["title"])
        self.assertEqual("Corrected meeting note.\n", body)
        self.assertEqual("Original meeting note.\n", original_stored_body)
        self.assertNotIn("supersedes", original_frontmatter)

    def test_raw_redact_replaces_body_sets_redacted_and_preserves_metadata(self):
        body_file = self.write_raw_body("support-note.txt", "Support note that should later be removed.\n")
        original = wiki_tool.raw_add(self.repo, "tickets", "Support Note", body_file)

        redacted = wiki_tool.raw_redact(self.repo, original["source_id"], "User requested removal")
        frontmatter, body = wiki_tool.parse_frontmatter((self.repo / redacted["path"]).read_text(encoding="utf-8"))

        self.assertEqual(original["path"], redacted["path"])
        self.assertEqual(original["source_id"], redacted["source_id"])
        self.assertEqual("Support Note", frontmatter["title"])
        self.assertEqual(original["created"], frontmatter["timestamp"])
        self.assertEqual("true", frontmatter["redacted"])
        self.assertTrue(redacted["redacted"])
        self.assertIn("[REDACTED]", body)
        self.assertIn("User requested removal", body)
        self.assertNotIn("Support note that should later be removed", body)
        self.assertEqual(wiki_tool.sha256_text(body), frontmatter["sha256"])

    def test_raw_add_rejects_large_binary_and_secret_like_inputs(self):
        large = self.repo / "large.txt"
        large.write_text("a" * (wiki_tool.RAW_MAX_BYTES + 1), encoding="utf-8")
        binary = self.repo / "binary.bin"
        binary.write_bytes(b"text\x00more")
        secret = self.write_raw_body("secret.txt", "api_key = '1234567890abcdef'\n")

        for path in (large, binary, secret):
            with self.subTest(path=path.name):
                with self.assertRaises(SystemExit):
                    wiki_tool.raw_add(self.repo, "tickets", "Unsafe Input", path)

    def test_raw_cli_emits_json_contract_for_add_and_show(self):
        body_file = self.write_raw_body("cli-ticket.txt", "CLI captured note.\n")

        add = run(
            [
                sys.executable,
                str(SCRIPT),
                "raw-add",
                "--repo",
                str(self.repo),
                "--json",
                "--kind",
                "tickets",
                "--title",
                "CLI Ticket",
                "--body-file",
                str(body_file),
            ],
            self.repo,
        )
        add_data = json.loads(add.stdout)
        show = run(
            [
                sys.executable,
                str(SCRIPT),
                "raw-show",
                "--repo",
                str(self.repo),
                "--json",
                "--source-id",
                add_data["source_id"],
            ],
            self.repo,
        )
        show_data = json.loads(show.stdout)

        for key in ("path", "source_id", "sha256", "created", "supersedes", "redacted"):
            self.assertIn(key, add_data)
            self.assertIn(key, show_data)
        self.assertEqual(add_data["source_id"], show_data["source_id"])
        self.assertEqual("CLI captured note.\n", show_data["body"])

    def test_compile_plan_for_git_file_returns_single_bounded_unit(self):
        (self.repo / "src").mkdir()
        (self.repo / "src" / "auth.ts").write_text("export const auth = true;\n", encoding="utf-8")
        self.write_concept("knowledge/wiki/components/auth.md", "../../../src/auth.ts")
        wiki_tool.save_manifest(self.repo)
        git(self.repo, "add", "src/auth.ts")

        plan = wiki_tool.compile_plan(self.repo, source="src/auth.ts")

        self.assertEqual("git-file", plan["unit_type"])
        self.assertEqual(["src/auth.ts"], plan["source_paths"])
        self.assertEqual(1, plan["source_count"])
        self.assertEqual(1, plan["source_total_count"])
        self.assertFalse(plan["source_truncated"])
        self.assertEqual("", plan["source_id"])
        self.assertEqual(
            [{"path": "knowledge/wiki/components/auth.md", "type": "Component", "title": "Auth Concept", "reason": "already cites src/auth.ts"}],
            plan["affected_concept_candidates"],
        )
        self.assertIn("Compile exactly one bounded source unit at a time.", plan["guidance"])

    def test_compile_plan_for_directory_caps_repo_source_set(self):
        for index in range(4):
            self.write_source(f"src/auth/file{index}.ts", f"export const value{index} = true;\n")
        git(self.repo, "add", "src")

        plan = wiki_tool.compile_plan(self.repo, source="src/auth", limit=2)

        self.assertEqual("repo-source-set", plan["unit_type"])
        self.assertEqual(["src/auth/file0.ts", "src/auth/file1.ts"], plan["source_paths"])
        self.assertEqual(2, plan["source_count"])
        self.assertEqual(4, plan["source_total_count"])
        self.assertEqual(2, plan["source_limit"])
        self.assertTrue(plan["source_truncated"])

    def test_compile_plan_for_raw_source_returns_single_raw_unit(self):
        body_file = self.write_raw_body("external-note.txt", "External note.\n")
        raw = wiki_tool.raw_add(self.repo, "external-docs", "External Note", body_file)

        plan = wiki_tool.compile_plan(self.repo, raw_source_id=raw["source_id"])

        self.assertEqual("raw-source", plan["unit_type"])
        self.assertEqual(raw["source_id"], plan["source_id"])
        self.assertEqual([raw["path"]], plan["source_paths"])
        self.assertEqual(1, plan["source_count"])
        self.assertEqual(1, plan["source_total_count"])
        self.assertFalse(plan["source_truncated"])

    def test_compile_plan_rejects_untracked_repo_file(self):
        self.write_source("src/untracked.ts")

        with self.assertRaises(SystemExit):
            wiki_tool.compile_plan(self.repo, source="src/untracked.ts")

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

    def test_update_plan_ignores_raw_records_for_source_coverage(self):
        wiki_tool.init_wiki(self.repo)
        body_file = self.write_raw_body("ticket-body.txt", "External ticket.\n")
        raw = wiki_tool.raw_add(self.repo, "tickets", "External Ticket", body_file)
        (self.repo / "knowledge" / "rules.md").write_text("# Rules\n", encoding="utf-8")

        result = wiki_tool.affected_report(self.repo)

        self.assertEqual({}, result["affected_concepts"])
        self.assertNotIn(raw["path"], result["missing_concept_coverage"])
        self.assertNotIn("knowledge/rules.md", result["missing_concept_coverage"])

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

    def test_doctor_reports_unreachable_concept_page_as_warning(self):
        (self.repo / "src").mkdir()
        (self.repo / "src" / "auth.ts").write_text("export const auth = true;\n", encoding="utf-8")
        (self.repo / "knowledge" / "wiki").mkdir(parents=True)
        (self.repo / "knowledge" / "wiki" / "index.md").write_text("# Index\n", encoding="utf-8")
        (self.repo / "knowledge" / "wiki" / "log.md").write_text("# Log\n", encoding="utf-8")
        concept = self.write_concept("knowledge/wiki/components/auth.md", "../../../src/auth.ts")
        concept.write_text(
            concept.read_text(encoding="utf-8").replace("confidence: high", "source_commit: abc123\nconfidence: high"),
            encoding="utf-8",
        )
        wiki_tool.save_manifest(self.repo)

        result = wiki_tool.doctor(self.repo)

        self.assertIn(
            {
                "severity": "warning",
                "path": "knowledge/wiki/components/auth.md",
                "message": "concept page is not reachable from knowledge/wiki/index.md",
            },
            result["issues"],
        )

    def test_doctor_reports_missing_source_commit_and_missing_raw_source_id(self):
        (self.repo / "src").mkdir()
        (self.repo / "src" / "auth.ts").write_text("export const auth = true;\n", encoding="utf-8")
        (self.repo / "knowledge" / "wiki").mkdir(parents=True)
        (self.repo / "knowledge" / "wiki" / "index.md").write_text("[Auth](components/auth.md)\n", encoding="utf-8")
        (self.repo / "knowledge" / "wiki" / "log.md").write_text("# Log\n", encoding="utf-8")
        self.write_concept("knowledge/wiki/components/auth.md", "../../../src/auth.ts", body="raw:missing-ticket\n")
        wiki_tool.save_manifest(self.repo)

        result = wiki_tool.doctor(self.repo)
        issues = [(issue["severity"], issue["path"], issue["message"]) for issue in result["issues"]]

        self.assertIn(
            ("warning", "knowledge/wiki/components/auth.md", "missing frontmatter field: source_commit"),
            issues,
        )
        self.assertIn(
            ("warning", "knowledge/wiki/components/auth.md", "raw source id does not resolve: missing-ticket"),
            issues,
        )

    def test_doctor_treats_directory_index_links_as_reachable(self):
        (self.repo / "src").mkdir()
        (self.repo / "src" / "auth.ts").write_text("export const auth = true;\n", encoding="utf-8")
        (self.repo / "knowledge" / "wiki" / "components").mkdir(parents=True)
        (self.repo / "knowledge" / "wiki" / "index.md").write_text("[Components](components/)\n", encoding="utf-8")
        (self.repo / "knowledge" / "wiki" / "components" / "index.md").write_text("[Auth](auth.md)\n", encoding="utf-8")
        (self.repo / "knowledge" / "wiki" / "log.md").write_text("# Log\n", encoding="utf-8")
        concept = self.write_concept("knowledge/wiki/components/auth.md", "../../../src/auth.ts")
        concept.write_text(
            concept.read_text(encoding="utf-8").replace("confidence: high", "source_commit: abc123\nconfidence: high"),
            encoding="utf-8",
        )
        wiki_tool.save_manifest(self.repo)

        result = wiki_tool.doctor(self.repo)
        messages = [issue["message"] for issue in result["issues"] if issue["path"] == "knowledge/wiki/components/auth.md"]

        self.assertNotIn("concept page is not reachable from knowledge/wiki/index.md", messages)

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
