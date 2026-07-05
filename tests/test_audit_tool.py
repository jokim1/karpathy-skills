import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "plugins" / "karpathy" / "skills" / "karpathy-audit" / "scripts" / "audit_tool.py"

spec = importlib.util.spec_from_file_location("audit_tool", SCRIPT)
audit_tool = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["audit_tool"] = audit_tool
spec.loader.exec_module(audit_tool)


def run(args, cwd, check=True):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=check, env=env)


def tool(repo, *args):
    return run([sys.executable, str(SCRIPT), *args], repo)


class AuditToolTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def write_config(self, **audit):
        config = {"audit": {**audit}}
        (self.repo / ".karpathy.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    def test_setup_bare_is_read_only_and_lists_rows(self):
        result = tool(self.repo, "setup")

        self.assertIn("Karpathy audit setup", result.stdout)
        self.assertIn("A. Agent instruction checks:", result.stdout)
        self.assertIn("D. Documentation checks:", result.stdout)
        self.assertIn("D1  on   stale-docs", result.stdout)
        self.assertIn("D2  on   doc-indexes", result.stdout)
        self.assertIn("Toggle a row: /karpathy setup D1", result.stdout)
        self.assertFalse((self.repo / ".karpathy.json").exists())

    def test_setup_toggle_writes_config(self):
        result = tool(self.repo, "setup", "--toggle", "D1", "--json")
        report = json.loads(result.stdout)
        config = json.loads((self.repo / ".karpathy.json").read_text(encoding="utf-8"))

        self.assertEqual("configured", report["status"])
        self.assertFalse(config["audit"]["staleDocs"])
        self.assertTrue(config["audit"]["indexChecks"])

    def test_setup_yes_enables_recommended_docs_checks(self):
        result = tool(self.repo, "setup", "--yes", "--json")
        report = json.loads(result.stdout)
        config = json.loads((self.repo / ".karpathy.json").read_text(encoding="utf-8"))

        self.assertEqual("configured", report["status"])
        self.assertTrue(config["audit"]["staleDocs"])
        self.assertTrue(config["audit"]["indexChecks"])

    def test_setup_yes_preserves_custom_docs_scope(self):
        self.write_config(
            staleDocs=False,
            indexChecks=False,
            docPaths=["custom-docs"],
            indexThreshold=9,
        )

        result = tool(self.repo, "setup", "--yes", "--json")
        report = json.loads(result.stdout)
        config = json.loads((self.repo / ".karpathy.json").read_text(encoding="utf-8"))

        self.assertEqual("configured", report["status"])
        self.assertTrue(config["audit"]["staleDocs"])
        self.assertTrue(config["audit"]["indexChecks"])
        self.assertEqual(["custom-docs"], config["audit"]["docPaths"])
        self.assertEqual(9, config["audit"]["indexThreshold"])

    def test_docs_check_runs_default_opinionated_checks_without_config(self):
        docs = self.repo / "docs"
        docs.mkdir()
        (docs / "roadmap.md").write_text("TODO: for now this is current sprint work.\n", encoding="utf-8")

        result = tool(self.repo, "docs-check", "--json")
        report = json.loads(result.stdout)

        self.assertEqual("reported", report["status"])
        self.assertTrue(any(issue["check"] == "stale-docs" for issue in report["issues"]))

    def test_docs_check_skips_when_config_disables_both_docs_checks(self):
        docs = self.repo / "docs"
        docs.mkdir()
        (docs / "roadmap.md").write_text("TODO: for now this is current sprint work.\n", encoding="utf-8")
        self.write_config(staleDocs=False, indexChecks=False, docPaths=["docs"], indexThreshold=5)

        result = tool(self.repo, "docs-check", "--json")
        report = json.loads(result.stdout)

        self.assertEqual("skipped", report["status"])
        self.assertEqual([], report["issues"])
        self.assertIn("stale-docs disabled", report["clean"])
        self.assertIn("doc-indexes disabled", report["clean"])

    def test_docs_check_reports_stale_markers_and_missing_index(self):
        docs = self.repo / "docs"
        docs.mkdir()
        for index in range(5):
            body = "Stable doc.\n"
            if index == 0:
                body = "TODO: for now this is current sprint work.\n"
            (docs / f"guide-{index}.md").write_text(body, encoding="utf-8")
        self.write_config(staleDocs=True, indexChecks=True, docPaths=["docs"], indexThreshold=5)

        result = tool(self.repo, "docs-check", "--json")
        report = json.loads(result.stdout)
        messages = [issue["message"] for issue in report["issues"]]

        self.assertEqual("reported", report["status"])
        self.assertTrue(any("possible stale todo marker" in message for message in messages))
        self.assertTrue(any("direct doc files but no README.md or index.md" in message for message in messages))

    def test_docs_check_ignores_lowercase_todo_and_fenced_examples(self):
        docs = self.repo / "docs"
        docs.mkdir()
        (docs / "guide.md").write_text(
            "\n".join(
                [
                    "This explains how stale docs checks find todo-like roadmap text.",
                    "",
                    "```text",
                    "TODO: this current sprint sample is deliberately an example.",
                    "[Missing](missing.md)",
                    "```",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = tool(self.repo, "docs-check", "--json")
        report = json.loads(result.stdout)

        self.assertEqual([], report["issues"])

    def test_index_check_accepts_index_listing_direct_docs(self):
        docs = self.repo / "docs"
        docs.mkdir()
        entries = []
        for index in range(5):
            name = f"guide-{index}.md"
            entries.append(f"- [{name}]({name})")
            (docs / name).write_text("Stable doc.\n", encoding="utf-8")
        (docs / "index.md").write_text("\n".join(entries) + "\n", encoding="utf-8")
        self.write_config(staleDocs=False, indexChecks=True, docPaths=["docs"], indexThreshold=5)

        result = tool(self.repo, "docs-check", "--json")
        report = json.loads(result.stdout)

        self.assertEqual([], report["issues"])
        self.assertIn("doc-indexes found no large unindexed doc folders", report["clean"])


if __name__ == "__main__":
    unittest.main()
