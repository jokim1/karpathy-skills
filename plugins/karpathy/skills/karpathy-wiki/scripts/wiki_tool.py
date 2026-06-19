#!/usr/bin/env python3
"""Deterministic helpers for the karpathy-wiki skill."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MANIFEST_NAME = ".karpathy-wiki.json"
MANAGED_HOOK_BEGIN = "# >>> karpathy-wiki stale reminder >>>"
MANAGED_HOOK_END = "# <<< karpathy-wiki stale reminder <<<"
CONCEPT_DIRS = {
    "Component": "components",
    "Workflow": "workflows",
    "Invariant": "invariants",
    "Decision": "decisions",
    "Test Surface": "tests",
    "Task Recipe": "recipes",
    "Failure Mode": "failure-modes",
}
REQUIRED_CONCEPT_FIELDS = ("type", "title", "description", "timestamp")
LOCAL_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
PACKAGE_FILE_NAMES = [
    "package.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "package-lock.json",
    "pyproject.toml",
    "requirements.txt",
    "uv.lock",
    "Cargo.toml",
    "Cargo.lock",
    "go.mod",
    "go.sum",
    "Gemfile",
    "Gemfile.lock",
    "Makefile",
    "justfile",
    "Taskfile.yml",
]
SOURCE_DIR_NAMES = ("src", "app", "lib", "packages", "plugins", "cmd", "internal", "server", "client")
TEST_DIR_NAMES = ("tests", "test", "spec", "__tests__", "e2e")


@dataclass
class Issue:
    severity: str
    path: str
    message: str


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_git(repo: Path, args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=repo, text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def resolve_repo(path: str | None) -> Path:
    start = Path(path or ".").resolve()
    if start.is_file():
        start = start.parent
    top = run_git(start, ["rev-parse", "--show-toplevel"])
    return Path(top).resolve() if top else start


def rel(repo: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def normalize_repo_path(path: str) -> str:
    normalized = path.replace(os.sep, "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.strip("/")


def resource_kind(repo: Path, resource: str) -> str:
    path = repo.resolve() / normalize_repo_path(resource)
    if path.is_dir():
        return "directory"
    if path.is_file():
        return "file"
    return "missing"


def resource_matches(repo: Path, changed_path: str, resource: str, kind: str | None = None) -> bool:
    changed = normalize_repo_path(changed_path)
    cited = normalize_repo_path(resource)
    if not changed or not cited:
        return False
    if changed == cited:
        return True
    is_directory = kind == "directory" or (kind is None and (repo.resolve() / cited).is_dir())
    return is_directory and changed.startswith(cited + "/")


def wiki_dir(repo: Path) -> Path:
    return repo / "knowledge" / "wiki"


def manifest_path(repo: Path) -> Path:
    return wiki_dir(repo) / MANIFEST_NAME


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def write_once(path: Path, content: str, force: bool = False) -> bool:
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def parse_inline_list(value: str) -> list[str]:
    value = value.strip()
    if not value:
        return []
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [item.strip().strip("\"'") for item in inner.split(",") if item.strip()]
    return [value.strip().strip("\"'")]


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 5 :]
    data: dict[str, Any] = {}
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            data[key] = parse_inline_list(value)
        else:
            data[key] = value.strip("\"'")
    return data, body


def concept_files(repo: Path) -> list[Path]:
    root = wiki_dir(repo)
    if not root.exists():
        return []
    ignored = {"index.md", "log.md"}
    return sorted(
        path
        for path in root.rglob("*.md")
        if path.name not in ignored and not any(part.startswith(".") for part in path.relative_to(root).parts)
    )


def markdown_links(text: str) -> list[str]:
    links: list[str] = []
    for match in LOCAL_LINK_RE.finditer(text):
        target = match.group(1).strip()
        target = target.split("#", 1)[0]
        if not target or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
            continue
        links.append(target)
    return links


def resolve_link(base_file: Path, target: str) -> Path:
    target = target.split("#", 1)[0]
    return (base_file.parent / target).resolve()


def source_refs_for_concept(repo: Path, concept: Path, frontmatter: dict[str, Any], body: str) -> list[str]:
    refs: set[str] = set()
    repo_root = repo.resolve()
    for key in ("resource", "resources"):
        value = frontmatter.get(key)
        values = value if isinstance(value, list) else parse_inline_list(str(value or ""))
        for item in values:
            if not item:
                continue
            candidate = (concept.parent / item).resolve()
            if repo_root in candidate.parents or candidate == repo_root:
                refs.add(rel(repo, candidate))
    for link in markdown_links(body):
        candidate = resolve_link(concept, link)
        if candidate.exists() and (repo_root in candidate.parents or candidate == repo_root):
            rel_candidate = rel(repo, candidate)
            if not rel_candidate.startswith("knowledge/wiki/"):
                refs.add(rel_candidate)
    return sorted(refs)


def build_manifest(repo: Path) -> dict[str, Any]:
    concepts: list[dict[str, Any]] = []
    source_map: dict[str, list[str]] = {}
    source_kinds: dict[str, str] = {}
    for path in concept_files(repo):
        text = read_text(path)
        frontmatter, body = parse_frontmatter(text)
        concept_rel = rel(repo, path)
        refs = source_refs_for_concept(repo, path, frontmatter, body)
        concept = {
            "path": concept_rel,
            "type": frontmatter.get("type", ""),
            "title": frontmatter.get("title", path.stem.replace("-", " ").title()),
            "description": frontmatter.get("description", ""),
            "resources": refs,
        }
        concepts.append(concept)
        for ref in refs:
            source_map.setdefault(ref, []).append(concept_rel)
            source_kinds[ref] = resource_kind(repo, ref)
    return {
        "version": 1,
        "generated_at": now_iso(),
        "source_commit": run_git(repo, ["rev-parse", "--short", "HEAD"]),
        "wiki_root": "knowledge/wiki",
        "concept_count": len(concepts),
        "concepts": concepts,
        "source_kinds": {key: source_kinds[key] for key in sorted(source_kinds)},
        "source_map": {key: sorted(value) for key, value in sorted(source_map.items())},
    }


def stable_manifest_view(manifest: dict[str, Any]) -> dict[str, Any]:
    concepts: list[dict[str, Any]] = []
    for concept in manifest.get("concepts", []):
        resources = concept.get("resources", [])
        if not isinstance(resources, list):
            resources = []
        concepts.append(
            {
                "path": concept.get("path", ""),
                "type": concept.get("type", ""),
                "title": concept.get("title", ""),
                "description": concept.get("description", ""),
                "resources": sorted(str(item) for item in resources),
            }
        )
    source_map = {
        normalize_repo_path(str(key)): sorted(str(item) for item in value)
        for key, value in manifest.get("source_map", {}).items()
        if isinstance(value, list)
    }
    source_kinds = {
        normalize_repo_path(str(key)): str(value)
        for key, value in manifest.get("source_kinds", {}).items()
    }
    return {
        "version": manifest.get("version"),
        "wiki_root": manifest.get("wiki_root"),
        "concept_count": len(concepts),
        "concepts": sorted(concepts, key=lambda item: item["path"]),
        "source_kinds": {key: source_kinds[key] for key in sorted(source_kinds)},
        "source_map": {key: source_map[key] for key in sorted(source_map)},
    }


def load_manifest(repo: Path) -> dict[str, Any]:
    path = manifest_path(repo)
    if not path.exists():
        return build_manifest(repo)
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError:
        return build_manifest(repo)


def save_manifest(repo: Path) -> dict[str, Any]:
    data = build_manifest(repo)
    path = manifest_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return data


def git_paths(repo: Path, args: list[str]) -> list[str]:
    output = run_git(repo, args)
    return [line.strip() for line in output.splitlines() if line.strip()]


def changed_paths(repo: Path) -> dict[str, list[str]]:
    return {
        "staged": git_paths(repo, ["diff", "--cached", "--name-only"]),
        "unstaged": git_paths(repo, ["diff", "--name-only"]),
        "untracked": git_paths(repo, ["ls-files", "--others", "--exclude-standard"]),
        "head": git_paths(repo, ["diff", "HEAD", "--name-only"]),
    }


def affected_concepts(repo: Path, paths: list[str], manifest: dict[str, Any]) -> dict[str, list[str]]:
    source_map: dict[str, list[str]] = manifest.get("source_map", {})
    source_kinds: dict[str, str] = manifest.get("source_kinds", {})
    affected: dict[str, list[str]] = {}
    for path in paths:
        for resource, concepts in source_map.items():
            if not resource_matches(repo, path, resource, source_kinds.get(resource)):
                continue
            for concept in concepts:
                affected.setdefault(concept, []).append(normalize_repo_path(path))
    return {key: sorted(value) for key, value in sorted(affected.items())}


def detect_commands(repo: Path) -> list[str]:
    commands: list[str] = []
    package_json = repo / "package.json"
    if package_json.exists():
        try:
            data = json.loads(read_text(package_json))
            scripts = data.get("scripts", {})
            for name in ("test", "typecheck", "lint", "build"):
                if name in scripts:
                    commands.append(f"npm run {name}" if name != "test" else "npm test")
        except json.JSONDecodeError:
            pass
    pyproject = repo / "pyproject.toml"
    if pyproject.exists():
        commands.extend(["python -m pytest", "python -m ruff check ."])
    makefile = repo / "Makefile"
    if makefile.exists():
        text = read_text(makefile)
        for name in ("test", "lint", "build"):
            if re.search(rf"^{re.escape(name)}:", text, re.MULTILINE):
                commands.append(f"make {name}")
    seen: set[str] = set()
    return [cmd for cmd in commands if not (cmd in seen or seen.add(cmd))]


def high_signal_files(repo: Path) -> list[str]:
    names = [
        "README.md",
        "README",
        "package.json",
        "pyproject.toml",
        "Cargo.toml",
        "go.mod",
        "Gemfile",
        "Makefile",
        "CLAUDE.md",
        "AGENTS.md",
    ]
    paths = [name for name in names if (repo / name).exists()]
    for dirname in ("docs", "src", "app", "lib", "tests", "test"):
        if (repo / dirname).exists():
            paths.append(dirname + "/")
    return paths


def sorted_existing_dirs(repo: Path, names: tuple[str, ...]) -> list[str]:
    return sorted(name + "/" for name in names if (repo / name).is_dir())


def sorted_existing_files(repo: Path, names: list[str]) -> list[str]:
    return sorted(name for name in names if (repo / name).is_file())


def doc_files(repo: Path) -> list[str]:
    paths: set[str] = set()
    for path in repo.glob("README*"):
        if path.is_file():
            paths.add(rel(repo, path))
    docs = repo / "docs"
    if docs.exists():
        for path in docs.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".md", ".mdx", ".html", ".txt"}:
                paths.add(rel(repo, path))
    return sorted(paths)[:80]


def source_entrypoints(repo: Path) -> list[str]:
    candidates: list[str] = []
    for directory in SOURCE_DIR_NAMES:
        root = repo / directory
        if not root.is_dir():
            continue
        for name in ("index", "main", "app", "server", "cli"):
            for suffix in (".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".rb"):
                path = root / f"{name}{suffix}"
                if path.exists():
                    candidates.append(rel(repo, path))
    for name in ("main.py", "app.py", "server.py", "index.ts", "index.js"):
        if (repo / name).is_file():
            candidates.append(name)
    return sorted(dict.fromkeys(candidates))[:40]


def scan_repo(repo: Path) -> dict[str, Any]:
    package_files = sorted_existing_files(repo, PACKAGE_FILE_NAMES)
    docs = doc_files(repo)
    source_dirs = sorted_existing_dirs(repo, SOURCE_DIR_NAMES)
    test_dirs = sorted_existing_dirs(repo, TEST_DIR_NAMES)
    return {
        "repo": str(repo),
        "high_signal_files": high_signal_files(repo),
        "docs": docs,
        "source_directories": source_dirs,
        "source_entrypoints": source_entrypoints(repo),
        "test_directories": test_dirs,
        "package_and_build_files": package_files,
        "known_commands": detect_commands(repo),
        "guidance": [
            "Create only 2-5 starter concepts unless the user asks for more.",
            "Require source citations for implementation-relevant claims.",
            "Summarize durable behavior; do not copy source files into wiki pages.",
        ],
    }


def init_wiki(repo: Path, force: bool = False) -> dict[str, Any]:
    created: list[str] = []
    skipped: list[str] = []
    for directory in [
        repo / "knowledge" / "raw" / "tickets",
        repo / "knowledge" / "raw" / "screenshots",
        repo / "knowledge" / "raw" / "external-docs",
        repo / "knowledge" / "outputs" / "task-briefs",
        repo / "knowledge" / "outputs" / "qa-reports",
        repo / "knowledge" / "outputs" / "diagrams",
        *[wiki_dir(repo) / dirname for dirname in CONCEPT_DIRS.values()],
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    project = repo.name
    timestamp = now_iso()
    commit = run_git(repo, ["rev-parse", "--short", "HEAD"]) or "unknown"
    commands = detect_commands(repo)
    signal_files = high_signal_files(repo)
    command_block = "\n".join(f"- `{cmd}`" for cmd in commands) or "- Unknown. Add test, lint, typecheck, and build commands when known."
    signal_block = "\n".join(f"- `{path}`" for path in signal_files) or "- No high-signal files detected yet."

    files = {
        repo / "knowledge" / "rules.md": f"""# Repo Wiki Rules

- Source code, tests, and explicit user instructions are authoritative.
- The wiki is advisory: use it to find relevant files, then read those files.
- Cite source files for implementation claims.
- Keep pages short, current, and useful for future coding tasks.
- Update only affected concept pages after code changes.
""",
        wiki_dir(repo) / "index.md": f"""---
type: Index
title: {project} Repo Wiki
description: Entry point for the repo knowledge base.
timestamp: {timestamp}
source_commit: {commit}
---

# {project} Repo Wiki

This wiki is maintained by coding agents. It summarizes durable repo knowledge
and links back to source files, tests, and docs.

## Start Here

- Read this index first.
- Read relevant concept pages next.
- Read cited source files before editing code.

## High-Signal Repo Files

{signal_block}

## Known Verification Commands

{command_block}

## Concept Areas

- [Components](components/)
- [Workflows](workflows/)
- [Invariants](invariants/)
- [Decisions](decisions/)
- [Test Surfaces](tests/)
- [Task Recipes](recipes/)
- [Failure Modes](failure-modes/)
""",
        wiki_dir(repo) / "log.md": f"""---
type: Log
title: Repo Wiki Log
description: Chronological maintenance log for the repo wiki.
timestamp: {timestamp}
source_commit: {commit}
---

# Repo Wiki Log

## {timestamp}

- Initialized repo wiki scaffold at `knowledge/wiki/`.
""",
    }

    for path, content in files.items():
        if write_once(path, content, force=force):
            created.append(rel(repo, path))
        else:
            skipped.append(rel(repo, path))

    manifest = save_manifest(repo)
    created.append(rel(repo, manifest_path(repo)))
    return {"created": created, "skipped": skipped, "manifest": manifest}


def status(repo: Path) -> dict[str, Any]:
    exists = wiki_dir(repo).exists()
    manifest = load_manifest(repo) if exists else {}
    changes = changed_paths(repo)
    affected = affected_concepts(repo, paths_for_scope(changes, "all"), manifest) if exists else {}
    return {
        "repo": str(repo),
        "wiki_exists": exists,
        "wiki_root": "knowledge/wiki",
        "manifest_exists": manifest_path(repo).exists(),
        "concept_count": len(manifest.get("concepts", [])) if exists else 0,
        "changed_paths": changes,
        "affected_concepts": affected,
        "source_commit": run_git(repo, ["rev-parse", "--short", "HEAD"]),
    }


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def doctor(repo: Path) -> dict[str, Any]:
    issues: list[Issue] = []
    clean: list[str] = []
    root = wiki_dir(repo)
    if not root.exists():
        issues.append(Issue("critical", "knowledge/wiki", "wiki directory does not exist"))
        return {"issues": [issue.__dict__ for issue in issues], "clean": clean}

    for required in (root / "index.md", root / "log.md"):
        if required.exists():
            clean.append(f"{rel(repo, required)} exists")
        else:
            issues.append(Issue("critical", rel(repo, required), "required wiki file is missing"))

    for path in concept_files(repo):
        text = read_text(path)
        frontmatter, body = parse_frontmatter(text)
        concept_rel = rel(repo, path)
        if not frontmatter:
            issues.append(Issue("warning", concept_rel, "missing YAML frontmatter"))
        for field in REQUIRED_CONCEPT_FIELDS:
            if field not in frontmatter or not str(frontmatter.get(field, "")).strip():
                issues.append(Issue("warning", concept_rel, f"missing frontmatter field: {field}"))
        refs = source_refs_for_concept(repo, path, frontmatter, body)
        if not refs:
            issues.append(Issue("warning", concept_rel, "no source resource or citation detected"))
        for ref in refs:
            if not (repo / ref).exists():
                issues.append(Issue("critical", concept_rel, f"source reference does not exist: {ref}"))
        for link in markdown_links(body):
            target = resolve_link(path, link)
            if is_within(target, repo) and not target.exists():
                issues.append(Issue("critical", concept_rel, f"broken local link: {link}"))

    manifest = build_manifest(repo)
    if not manifest_path(repo).exists():
        issues.append(Issue("warning", rel(repo, manifest_path(repo)), "manifest is missing; run refresh-manifest"))
    else:
        try:
            saved_manifest = json.loads(read_text(manifest_path(repo)))
            if stable_manifest_view(saved_manifest) != stable_manifest_view(manifest):
                issues.append(
                    Issue(
                        "warning",
                        rel(repo, manifest_path(repo)),
                        "persisted manifest is stale; run refresh-manifest",
                    )
                )
            else:
                clean.append("persisted manifest matches wiki concepts")
        except json.JSONDecodeError:
            issues.append(Issue("critical", rel(repo, manifest_path(repo)), "manifest is invalid JSON"))
    if manifest.get("concept_count", 0) == 0:
        issues.append(Issue("warning", rel(repo, root), "no concept pages found yet"))
    else:
        clean.append(f"{manifest['concept_count']} concept page(s) indexed")

    changes = changed_paths(repo)
    affected = affected_concepts(repo, paths_for_scope(changes, "all"), manifest)
    if affected:
        for concept, paths in affected.items():
            issues.append(Issue("warning", concept, "changed source may require wiki update: " + ", ".join(paths)))
    else:
        clean.append("no changed source files map to indexed concepts")

    return {"issues": [issue.__dict__ for issue in issues], "clean": clean, "manifest": manifest}


def score_file(repo: Path, path: Path, query_terms: list[str]) -> tuple[int, dict[str, Any]]:
    text = read_text(path)
    frontmatter, body = parse_frontmatter(text)
    haystack = " ".join(
        [
            str(frontmatter.get("title", "")),
            str(frontmatter.get("description", "")),
            str(frontmatter.get("type", "")),
            path.stem.replace("-", " "),
            body,
        ]
    ).lower()
    score = sum(haystack.count(term) for term in query_terms)
    return score, {
        "path": path,
        "frontmatter": frontmatter,
        "resources": source_refs_for_concept(repo, path, frontmatter, body),
        "snippet": " ".join(body.strip().split())[:240],
    }


def search(repo: Path, query: str, limit: int) -> list[dict[str, Any]]:
    terms = [term.lower() for term in re.findall(r"[A-Za-z0-9_./-]+", query) if len(term) > 1]
    results: list[tuple[int, dict[str, Any]]] = []
    for path in [wiki_dir(repo) / "index.md", *concept_files(repo)]:
        if not path.exists():
            continue
        score, data = score_file(repo, path, terms)
        if score > 0:
            results.append((score, data))
    results.sort(key=lambda item: (-item[0], rel(repo, item[1]["path"])))
    output: list[dict[str, Any]] = []
    for score, data in results[:limit]:
        frontmatter = data["frontmatter"]
        output.append(
            {
                "score": score,
                "path": rel(repo, data["path"]),
                "type": frontmatter.get("type", ""),
                "title": frontmatter.get("title", data["path"].stem),
                "description": frontmatter.get("description", ""),
                "confidence": frontmatter.get("confidence", "unspecified"),
                "resources": data["resources"],
                "snippet": data["snippet"],
            }
        )
    return output


def paths_for_scope(changes: dict[str, list[str]], scope: str) -> list[str]:
    if scope == "all":
        paths: set[str] = set()
        for values in changes.values():
            paths.update(values)
        return sorted(normalize_repo_path(path) for path in paths)
    return sorted(normalize_repo_path(path) for path in changes.get(scope, []))


def affected_report(repo: Path, scope: str = "all") -> dict[str, Any]:
    manifest = load_manifest(repo) if wiki_dir(repo).exists() else {}
    changes = changed_paths(repo)
    scoped_paths = paths_for_scope(changes, scope)
    affected = affected_concepts(repo, scoped_paths, manifest)
    covered_paths = {path for paths in affected.values() for path in paths}
    source_map: dict[str, list[str]] = manifest.get("source_map", {})
    source_kinds: dict[str, str] = manifest.get("source_kinds", {})
    missing_coverage = [
        path
        for path in scoped_paths
        if path
        and not path.startswith("knowledge/wiki/")
        and not path.startswith("knowledge/outputs/")
        and path not in covered_paths
        and not any(resource_matches(repo, path, resource, source_kinds.get(resource)) for resource in source_map)
    ]
    return {
        "repo": str(repo),
        "scope": scope,
        "changed_paths": scoped_paths,
        "affected_concepts": affected,
        "missing_concept_coverage": missing_coverage,
        "manifest_exists": manifest_path(repo).exists(),
        "concept_count": len(manifest.get("concepts", [])),
    }


def reminder_hook(repo: Path, strict: bool = False) -> int:
    manifest = load_manifest(repo)
    staged = changed_paths(repo)["staged"]
    affected = affected_concepts(repo, staged, manifest)
    staged_set = set(staged)
    pending = {concept: paths for concept, paths in affected.items() if concept not in staged_set}
    if not pending:
        return 0
    print(f"Wiki reminder: {len(pending)} concept(s) may be stale.")
    for concept, paths in pending.items():
        print(f"- {concept}: {', '.join(paths)}")
    print("\nRun:\n  /karpathy:wiki\nor type:\n  karpathy wiki")
    if strict:
        print("\nCommit blocked because strict stale-wiki mode is enabled.")
        return 1
    print("\nCommit is allowed. This reminder is advisory.")
    return 0


def install_hook(repo: Path, script_path: Path, strict: bool = False) -> dict[str, str]:
    hooks_path = run_git(repo, ["config", "--get", "core.hooksPath"])
    git_dir = run_git(repo, ["rev-parse", "--git-dir"])
    if hooks_path:
        hook_dir = Path(hooks_path)
        if not hook_dir.is_absolute():
            hook_dir = repo / hook_dir
        hook_dir = hook_dir.resolve()
    elif git_dir:
        hook_dir = (repo / git_dir).resolve() / "hooks"
    else:
        raise SystemExit("Not a git repository; cannot install pre-commit hook.")
    hook_dir.mkdir(parents=True, exist_ok=True)
    hook = hook_dir / "pre-commit"
    existing = read_text(hook) if hook.exists() else "#!/bin/sh\n"
    first_line = existing.splitlines()[0] if existing.splitlines() else ""
    if hook.exists() and first_line.startswith("#!") and not re.search(r"(sh|bash|zsh|dash)\b", first_line):
        raise SystemExit(
            f"Existing hook is not shell-compatible: {hook}. "
            "Not modifying it; add the karpathy-wiki reminder manually."
        )
    strict_flag = " --strict" if strict else ""
    block = f"""{MANAGED_HOOK_BEGIN}
KARPATHY_WIKI_SCRIPT="{script_path.resolve()}"
if command -v python3 >/dev/null 2>&1 && [ -f "$KARPATHY_WIKI_SCRIPT" ]; then
  python3 "$KARPATHY_WIKI_SCRIPT" reminder-hook --repo "{repo.resolve()}"{strict_flag}
fi
{MANAGED_HOOK_END}
"""
    if MANAGED_HOOK_BEGIN in existing and MANAGED_HOOK_END in existing:
        existing = re.sub(
            rf"{re.escape(MANAGED_HOOK_BEGIN)}.*?{re.escape(MANAGED_HOOK_END)}\n?",
            block,
            existing,
            flags=re.DOTALL,
        )
        action = "updated"
    else:
        if not existing.endswith("\n"):
            existing += "\n"
        existing += "\n" + block
        action = "installed"
    hook.write_text(existing, encoding="utf-8")
    mode = hook.stat().st_mode
    hook.chmod(mode | stat.S_IXUSR)
    return {"hook": rel(repo, hook), "action": action}


def print_text_status(data: dict[str, Any]) -> None:
    print(f"Repo: {data['repo']}")
    print(f"Wiki: {'present' if data['wiki_exists'] else 'missing'} ({data['wiki_root']})")
    if data["wiki_exists"]:
        print(f"Concepts: {data['concept_count']}")
        if data["affected_concepts"]:
            print("Affected concepts:")
            for concept, paths in data["affected_concepts"].items():
                print(f"- {concept}: {', '.join(paths)}")
        else:
            print("Affected concepts: none")


def print_doctor(data: dict[str, Any]) -> None:
    issues = data.get("issues", [])
    print("# Karpathy Wiki Doctor")
    if issues:
        print("\n## Issues")
        for issue in issues:
            print(f"- [{issue['severity'].upper()}] {issue['path']}: {issue['message']}")
    else:
        print("\n## Issues\n- None")
    clean = data.get("clean", [])
    if clean:
        print("\n## Clean Checks")
        for item in clean:
            print(f"- {item}")


def print_scan(data: dict[str, Any]) -> None:
    print("# Karpathy Wiki Repo Scan")
    print(f"Repo: {data['repo']}")
    for key, title in [
        ("high_signal_files", "High-Signal Files"),
        ("docs", "Docs"),
        ("source_directories", "Source Directories"),
        ("source_entrypoints", "Source Entrypoints"),
        ("test_directories", "Test Directories"),
        ("package_and_build_files", "Package And Build Files"),
        ("known_commands", "Known Commands"),
        ("guidance", "Guidance"),
    ]:
        print(f"\n## {title}")
        values = data.get(key, [])
        if values:
            for value in values:
                print(f"- {value}")
        else:
            print("- None detected")


def print_affected(data: dict[str, Any]) -> None:
    print("# Karpathy Wiki Update Plan")
    print(f"Scope: {data['scope']}")
    changed = data.get("changed_paths", [])
    print("\n## Changed Paths")
    if changed:
        for path in changed:
            print(f"- {path}")
    else:
        print("- None")
    affected = data.get("affected_concepts", {})
    print("\n## Affected Concepts")
    if affected:
        for concept, paths in affected.items():
            print(f"- {concept}: {', '.join(paths)}")
    else:
        print("- None")
    missing = data.get("missing_concept_coverage", [])
    print("\n## Missing Concept Coverage")
    if missing:
        for path in missing:
            print(f"- {path}")
    else:
        print("- None")


def main() -> int:
    parser = argparse.ArgumentParser(description="Karpathy wiki helper")
    parser.add_argument("--repo", default=".", help="Repository root or path inside it")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(command_parser: argparse.ArgumentParser) -> None:
        command_parser.add_argument("--repo", dest="repo_after", help=argparse.SUPPRESS)
        command_parser.add_argument("--json", dest="json_after", action="store_true", help=argparse.SUPPRESS)

    status_parser = sub.add_parser("status")
    add_common(status_parser)
    scan_parser = sub.add_parser("scan")
    add_common(scan_parser)
    init_parser = sub.add_parser("init")
    add_common(init_parser)
    init_parser.add_argument("--force", action="store_true")
    doctor_parser = sub.add_parser("doctor")
    add_common(doctor_parser)
    search_parser = sub.add_parser("search")
    add_common(search_parser)
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=8)
    hook_parser = sub.add_parser("reminder-hook")
    add_common(hook_parser)
    hook_parser.add_argument("--strict", action="store_true", default=os.environ.get("KARPATHY_WIKI_STRICT") == "1")
    install_hook_parser = sub.add_parser("install-hook")
    add_common(install_hook_parser)
    install_hook_parser.add_argument("--strict", action="store_true")
    affected_parser = sub.add_parser("affected")
    add_common(affected_parser)
    affected_parser.add_argument("--scope", choices=["staged", "unstaged", "untracked", "head", "all"], default="all")
    update_plan_parser = sub.add_parser("update-plan")
    add_common(update_plan_parser)
    update_plan_parser.add_argument("--scope", choices=["staged", "unstaged", "untracked", "head", "all"], default="all")
    refresh_parser = sub.add_parser("refresh-manifest")
    add_common(refresh_parser)

    args = parser.parse_args()
    repo = resolve_repo(getattr(args, "repo_after", None) or args.repo)
    json_output = args.json or getattr(args, "json_after", False)

    if args.command == "status":
        data = status(repo)
        if json_output:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            print_text_status(data)
        return 0
    if args.command == "scan":
        data = scan_repo(repo)
        if json_output:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            print_scan(data)
        return 0
    if args.command == "init":
        data = init_wiki(repo, force=args.force)
        print(json.dumps(data, indent=2, sort_keys=True) if json_output else "Initialized repo wiki at knowledge/wiki/")
        return 0
    if args.command == "doctor":
        data = doctor(repo)
        if json_output:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            print_doctor(data)
        return 0
    if args.command == "search":
        data = search(repo, args.query, args.limit)
        if json_output:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            for item in data:
                print(f"{item['score']:>3} {item['path']} - {item['title']}")
        return 0
    if args.command == "reminder-hook":
        return reminder_hook(repo, strict=args.strict)
    if args.command == "install-hook":
        data = install_hook(repo, Path(__file__), strict=args.strict)
        print(json.dumps(data, indent=2, sort_keys=True) if json_output else f"{data['action']} {data['hook']}")
        return 0
    if args.command in {"affected", "update-plan"}:
        data = affected_report(repo, scope=args.scope)
        if json_output:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            print_affected(data)
        return 0
    if args.command == "refresh-manifest":
        data = save_manifest(repo)
        print(json.dumps(data, indent=2, sort_keys=True) if json_output else f"Indexed {data['concept_count']} concept(s).")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
