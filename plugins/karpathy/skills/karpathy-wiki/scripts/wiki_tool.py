#!/usr/bin/env python3
"""Deterministic helpers for the karpathy-wiki skill."""

from __future__ import annotations

import argparse
import hashlib
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
IMPROVEMENTS_PATH = Path("knowledge") / "outputs" / "wiki-improvements.md"
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
SOURCE_FILE_SUFFIXES = {
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".py",
    ".go",
    ".rs",
    ".rb",
    ".java",
    ".kt",
    ".swift",
    ".cs",
    ".php",
}
IGNORED_SCAN_PARTS = {
    ".git",
    ".next",
    ".nuxt",
    ".svelte-kit",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
}
FEATURE_BASE_DIRS = ("src/features", "features", "app/features")
DOMAIN_SIGNAL_KEYWORDS = (
    "api",
    "bootstrap",
    "cache",
    "client",
    "data",
    "loader",
    "mutation",
    "queries",
    "query",
    "repository",
    "route",
    "schema",
    "server",
    "service",
    "store",
)
RAW_MAX_BYTES = 256 * 1024
RAW_FRONTMATTER_FIELDS = (
    "type",
    "source_id",
    "kind",
    "title",
    "timestamp",
    "sha256",
    "source_url",
    "source_commit",
    "supersedes",
    "redacted",
)
RAW_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9]{16,}\b"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[^'\"\s]{8,}", re.IGNORECASE),
)
RAW_REF_RE = re.compile(r"\braw:([a-z0-9][a-z0-9-]*)\b")
COMPILE_SOURCE_SET_LIMIT = 8
DRAFT_TYPES = {"draft", "Draft"}


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


def append_improvement_note(
    repo: Path,
    title: str,
    body: str,
    suggestion: str | None = None,
    evidence: list[str] | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    path = repo / IMPROVEMENTS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = now_iso()
    commit = run_git(repo, ["rev-parse", "--short", "HEAD"]) or "unknown"
    clean_title = " ".join(title.strip().split()) or "Untitled improvement"
    clean_body = body.strip() or "No details provided."
    clean_suggestion = (suggestion or "").strip() or "Review this observation and decide whether it should become a skill, helper, docs, or test change."
    clean_evidence = [item.strip() for item in evidence or [] if item.strip()]
    clean_tags = [item.strip() for item in tags or [] if item.strip()]
    header = ""
    if not path.exists():
        header = """# Karpathy Wiki Improvement Notes

Local, append-only dogfood notes for improving the karpathy-wiki skill.

- No telemetry or network upload is implied by this file.
- Do not include secrets, personal data, raw transcripts, or large source excerpts.
- Do not stage this file automatically.

"""
    tag_line = ", ".join(clean_tags) if clean_tags else "none"
    evidence_block = "\n".join(f"- `{item}`" for item in clean_evidence) if clean_evidence else "- None"
    entry = f"""## {timestamp} - {clean_title}

- Source commit: `{commit}`
- Tags: {tag_line}

### Observation

{clean_body}

### Evidence

{evidence_block}

### Suggested Skill Change

{clean_suggestion}

"""
    with path.open("a", encoding="utf-8") as handle:
        handle.write(header + entry)
    return {
        "path": rel(repo, path),
        "timestamp": timestamp,
        "title": clean_title,
        "suggestion": clean_suggestion,
        "evidence": clean_evidence,
        "tags": clean_tags,
    }


def raw_root(repo: Path) -> Path:
    return repo / "knowledge" / "raw"


def raw_kind_slug(kind: str) -> str:
    if not kind.strip():
        raise SystemExit("Raw source kind is required.")
    return slugify(kind)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def raw_body_from_file(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"Raw body file does not exist: {path}")
    data = path.read_bytes()
    if len(data) > RAW_MAX_BYTES:
        raise SystemExit(f"Raw body file is too large; limit is {RAW_MAX_BYTES} bytes.")
    if b"\x00" in data:
        raise SystemExit("Raw body file appears to be binary; store metadata instead of raw content.")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise SystemExit("Raw body file must be UTF-8 text; store metadata instead of raw content.") from error
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        raise SystemExit("Raw body file is empty.")
    return text.rstrip("\n") + "\n"


def ensure_raw_body_safe(text: str) -> None:
    for pattern in RAW_SECRET_PATTERNS:
        if pattern.search(text):
            raise SystemExit(
                "Raw source appears to contain a secret or sensitive personal data; "
                "summarize sensitive material instead of storing it."
            )


def raw_source_id_base(kind: str, title: str, timestamp: str) -> str:
    clean_title = " ".join(title.strip().split())
    if not clean_title:
        raise SystemExit("Raw source title is required.")
    return slugify(f"{kind}-{clean_title}-{timestamp[:10]}")


def raw_record_paths(repo: Path, source_id: str) -> list[Path]:
    if not raw_root(repo).exists():
        return []
    return sorted(raw_root(repo).glob(f"*/{source_id}.md"))


def raw_record_path(repo: Path, source_id: str) -> Path:
    matches = raw_record_paths(repo, source_id)
    if not matches:
        raise SystemExit(f"Raw source not found: {source_id}")
    if len(matches) > 1:
        raise SystemExit(f"Raw source id is ambiguous: {source_id}")
    return matches[0]


def unique_raw_source_id(repo: Path, kind: str, title: str, timestamp: str) -> str:
    base = raw_source_id_base(kind, title, timestamp)
    source_id = base
    suffix = 2
    while raw_record_paths(repo, source_id):
        source_id = f"{base}-{suffix}"
        suffix += 1
    return source_id


def yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value)
    if not text:
        return '""'
    if text != text.strip() or any(char in text for char in "\n:#[]{}"):
        return json.dumps(text)
    return text


def raw_record_content(frontmatter: dict[str, Any], body: str) -> str:
    lines = ["---"]
    for field in RAW_FRONTMATTER_FIELDS:
        value = frontmatter.get(field)
        if value is None or value == "":
            continue
        lines.append(f"{field}: {yaml_scalar(value)}")
    lines.extend(["---", body.rstrip("\n"), ""])
    return "\n".join(lines)


def raw_record_result(repo: Path, path: Path, frontmatter: dict[str, Any], body: str) -> dict[str, Any]:
    redacted = str(frontmatter.get("redacted", "")).lower() == "true"
    return {
        "path": rel(repo, path),
        "source_id": str(frontmatter.get("source_id", path.stem)),
        "sha256": str(frontmatter.get("sha256", sha256_text(body))),
        "created": str(frontmatter.get("timestamp", "")),
        "supersedes": str(frontmatter.get("supersedes", "")),
        "redacted": redacted,
        "kind": str(frontmatter.get("kind", path.parent.name)),
        "title": str(frontmatter.get("title", path.stem)),
        "body": body,
    }


def read_raw_record(repo: Path, source_id: str) -> tuple[Path, dict[str, Any], str]:
    path = raw_record_path(repo, source_id)
    frontmatter, body = parse_frontmatter(read_text(path))
    if not frontmatter:
        raise SystemExit(f"Raw source has no frontmatter: {rel(repo, path)}")
    return path, frontmatter, body


def raw_add(repo: Path, kind: str, title: str, body_file: Path, source_url: str = "") -> dict[str, Any]:
    clean_kind = raw_kind_slug(kind)
    clean_title = " ".join(title.strip().split())
    body = raw_body_from_file(body_file)
    ensure_raw_body_safe(body)
    timestamp = now_iso()
    source_id = unique_raw_source_id(repo, clean_kind, clean_title, timestamp)
    path = raw_root(repo) / clean_kind / f"{source_id}.md"
    commit = run_git(repo, ["rev-parse", "--short", "HEAD"])
    frontmatter: dict[str, Any] = {
        "type": "Raw Source",
        "source_id": source_id,
        "kind": clean_kind,
        "title": clean_title,
        "timestamp": timestamp,
        "sha256": sha256_text(body),
    }
    if source_url.strip():
        frontmatter["source_url"] = source_url.strip()
    if commit:
        frontmatter["source_commit"] = commit
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(raw_record_content(frontmatter, body), encoding="utf-8")
    return raw_record_result(repo, path, frontmatter, body)


def raw_correct(repo: Path, source_id: str, body_file: Path) -> dict[str, Any]:
    _old_path, old_frontmatter, _old_body = read_raw_record(repo, source_id)
    clean_kind = raw_kind_slug(str(old_frontmatter.get("kind", "")))
    old_title = str(old_frontmatter.get("title", source_id)).strip() or source_id
    title = f"Correction for {old_title}"
    body = raw_body_from_file(body_file)
    ensure_raw_body_safe(body)
    timestamp = now_iso()
    new_source_id = unique_raw_source_id(repo, clean_kind, title, timestamp)
    path = raw_root(repo) / clean_kind / f"{new_source_id}.md"
    commit = run_git(repo, ["rev-parse", "--short", "HEAD"])
    frontmatter: dict[str, Any] = {
        "type": "Raw Source",
        "source_id": new_source_id,
        "kind": clean_kind,
        "title": title,
        "timestamp": timestamp,
        "sha256": sha256_text(body),
        "supersedes": source_id,
    }
    if old_frontmatter.get("source_url"):
        frontmatter["source_url"] = old_frontmatter["source_url"]
    if commit:
        frontmatter["source_commit"] = commit
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(raw_record_content(frontmatter, body), encoding="utf-8")
    return raw_record_result(repo, path, frontmatter, body)


def raw_redact(repo: Path, source_id: str, reason: str) -> dict[str, Any]:
    clean_reason = " ".join(reason.strip().split())
    if not clean_reason:
        raise SystemExit("Redaction reason is required.")
    ensure_raw_body_safe(clean_reason)
    path, frontmatter, body = read_raw_record(repo, source_id)
    timestamp = now_iso()
    if str(frontmatter.get("redacted", "")).lower() == "true":
        redacted_body = body.rstrip("\n") + f"\n\nRedaction reason ({timestamp}): {clean_reason}\n"
    else:
        redacted_body = f"[REDACTED]\n\nRedaction reason ({timestamp}): {clean_reason}\n"
    frontmatter["redacted"] = True
    frontmatter["sha256"] = sha256_text(redacted_body)
    path.write_text(raw_record_content(frontmatter, redacted_body), encoding="utf-8")
    return raw_record_result(repo, path, frontmatter, redacted_body)


def raw_show(repo: Path, source_id: str) -> dict[str, Any]:
    path, frontmatter, body = read_raw_record(repo, source_id)
    return raw_record_result(repo, path, frontmatter, body)


def git_tracked(repo: Path, path: str) -> bool:
    return bool(run_git(repo, ["ls-files", "--error-unmatch", normalize_repo_path(path)]))


def tracked_source_files_under(repo: Path, resource: str, limit: int = COMPILE_SOURCE_SET_LIMIT) -> list[str]:
    normalized = normalize_repo_path(resource)
    output = run_git(repo, ["ls-files", "--", normalized])
    paths = [
        normalize_repo_path(path)
        for path in output.splitlines()
        if normalize_repo_path(path)
        and not scan_path_is_ignored(normalize_repo_path(path))
        and Path(normalize_repo_path(path)).suffix in SOURCE_FILE_SUFFIXES
    ]
    return sorted(dict.fromkeys(paths))[:limit]


def raw_source_ids_for_concept(frontmatter: dict[str, Any], body: str) -> list[str]:
    ids: set[str] = set()
    for key in ("raw_source", "raw_sources"):
        value = frontmatter.get(key)
        values = value if isinstance(value, list) else parse_inline_list(str(value or ""))
        for item in values:
            item = str(item).strip()
            if item.startswith("raw:"):
                item = item[4:]
            if item:
                ids.add(slugify(item))
    for match in RAW_REF_RE.finditer(body):
        ids.add(match.group(1))
    return sorted(ids)


def concept_candidate(path: Path, repo: Path, reason: str) -> dict[str, str]:
    frontmatter, _body = parse_frontmatter(read_text(path))
    return {
        "path": rel(repo, path),
        "type": str(frontmatter.get("type", "")),
        "title": str(frontmatter.get("title", path.stem.replace("-", " ").title())),
        "reason": reason,
    }


def compile_plan_existing_candidates(repo: Path, source_paths: list[str], raw_source_id: str = "") -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()
    manifest = load_manifest(repo) if wiki_dir(repo).exists() else {}
    source_map: dict[str, list[str]] = manifest.get("source_map", {})
    source_kinds: dict[str, str] = manifest.get("source_kinds", {})
    for source_path in source_paths:
        for resource, concept_paths in source_map.items():
            if not resource_matches(repo, source_path, resource, source_kinds.get(resource)):
                continue
            for concept_path in concept_paths:
                concept = repo / concept_path
                if concept.exists() and concept_path not in seen:
                    seen.add(concept_path)
                    candidates.append(concept_candidate(concept, repo, f"already cites {resource}"))
    if raw_source_id:
        for concept in concept_files(repo):
            frontmatter, body = parse_frontmatter(read_text(concept))
            concept_rel = rel(repo, concept)
            if raw_source_id in raw_source_ids_for_concept(frontmatter, body) and concept_rel not in seen:
                seen.add(concept_rel)
                candidates.append(concept_candidate(concept, repo, f"already cites raw:{raw_source_id}"))
    return candidates


def compile_plan(repo: Path, source: str = "", raw_source_id: str = "", limit: int = COMPILE_SOURCE_SET_LIMIT) -> dict[str, Any]:
    if bool(source) == bool(raw_source_id):
        raise SystemExit("Provide exactly one source unit: --source or --source-id.")
    if limit < 1:
        raise SystemExit("Compile source-set limit must be at least 1.")
    source_paths: list[str]
    unit_type: str
    source_id = ""
    if raw_source_id:
        raw_path, _frontmatter, _body = read_raw_record(repo, raw_source_id)
        source_paths = [rel(repo, raw_path)]
        unit_type = "raw-source"
        source_id = raw_source_id
    else:
        normalized = normalize_repo_path(source)
        target = repo / normalized
        if not target.exists():
            raise SystemExit(f"Compile source does not exist: {normalized}")
        if target.is_file():
            if not git_tracked(repo, normalized):
                raise SystemExit(f"Compile source must be a Git-tracked file: {normalized}")
            source_paths = [normalized]
            unit_type = "git-file"
        else:
            source_paths = tracked_source_files_under(repo, normalized, limit=limit)
            if not source_paths:
                raise SystemExit(f"Compile source set has no Git-tracked source files: {normalized}")
            unit_type = "repo-source-set"
    affected = compile_plan_existing_candidates(repo, source_paths, raw_source_id=source_id)
    return {
        "repo": str(repo),
        "wiki_root": "knowledge/wiki",
        "unit_type": unit_type,
        "source_id": source_id,
        "source_paths": source_paths,
        "source_count": len(source_paths),
        "source_limit": limit,
        "affected_concept_candidates": affected,
        "questions": [
            "Which durable concept should this bounded source unit create or update?",
            "Which claims are directly supported by this source unit?",
            "Which citations should the concept include before semantic writing starts?",
            "What verification command or test surface is relevant to this source unit?",
        ],
        "guidance": [
            "Compile exactly one bounded source unit at a time.",
            "The helper only plans scope; the agent writes semantic wiki content after reading the sources.",
            "Repo code stays authoritative through path and commit citations; raw records are for external sources.",
        ],
    }


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


def wiki_markdown_files(repo: Path) -> list[Path]:
    root = wiki_dir(repo)
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.md") if not any(part.startswith(".") for part in path.relative_to(root).parts))


def resolve_wiki_page_link(repo: Path, base_file: Path, target: str) -> Path:
    candidate = resolve_link(base_file, target)
    root = wiki_dir(repo)
    if not is_within(candidate, root):
        return candidate
    if candidate.is_dir():
        index = candidate / "index.md"
        return index.resolve() if index.exists() else candidate
    if not candidate.exists() and (candidate / "index.md").exists():
        return (candidate / "index.md").resolve()
    return candidate


def wiki_link_targets(repo: Path, path: Path) -> list[Path]:
    targets: list[Path] = []
    root = wiki_dir(repo)
    for link in markdown_links(read_text(path)):
        target = resolve_wiki_page_link(repo, path, link)
        if is_within(target, root) and target.is_file():
            targets.append(target.resolve())
    return targets


def reachable_wiki_pages(repo: Path) -> set[Path]:
    index = wiki_dir(repo) / "index.md"
    if not index.exists():
        return set()
    reachable: set[Path] = set()
    pending = [index.resolve()]
    while pending:
        current = pending.pop()
        if current in reachable:
            continue
        reachable.add(current)
        for target in wiki_link_targets(repo, current):
            if target not in reachable:
                pending.append(target)
    return reachable


def wiki_page_is_draft(path: Path) -> bool:
    frontmatter, _body = parse_frontmatter(read_text(path))
    return str(frontmatter.get("status", "")).lower() == "draft" or str(frontmatter.get("type", "")) in DRAFT_TYPES


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


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "concept"


def humanize_name(value: str) -> str:
    parts = [part for part in re.split(r"[^A-Za-z0-9]+", value) if part]
    words: list[str] = []
    for part in parts:
        lower = part.lower()
        if lower in {"ai", "api", "cli", "mcp", "sql", "ui"}:
            words.append(lower.upper())
        else:
            words.append(lower.capitalize())
    return " ".join(words) or "Concept"


def singularize(value: str) -> str:
    if value.endswith("ies") and len(value) > 4:
        return value[:-3] + "y"
    if value.endswith("s") and not value.endswith("ss") and len(value) > 3:
        return value[:-1]
    return value


def first_existing_file(repo: Path, candidates: list[str]) -> str:
    for candidate in candidates:
        path = normalize_repo_path(candidate)
        if (repo / path).is_file():
            return path
    return ""


def first_existing_dir(repo: Path, candidates: list[str]) -> str:
    for candidate in candidates:
        path = normalize_repo_path(candidate)
        if (repo / path).is_dir():
            return path
    return ""


def unique_existing_paths(repo: Path, paths: list[str], limit: int | None = None) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for path in paths:
        normalized = normalize_repo_path(path)
        if not normalized or normalized in seen or not (repo / normalized).exists():
            continue
        seen.add(normalized)
        unique.append(normalized)
        if limit is not None and len(unique) >= limit:
            break
    return unique


def scan_path_is_ignored(path: str) -> bool:
    return any(part in IGNORED_SCAN_PARTS for part in Path(path).parts)


def source_files_under(repo: Path, resource: str, limit: int = 80) -> list[str]:
    normalized = normalize_repo_path(resource)
    path = repo / normalized
    if path.is_file():
        return [normalized]
    if not path.is_dir():
        return []
    files: list[str] = []
    for child in path.rglob("*"):
        if not child.is_file() or child.suffix.lower() not in SOURCE_FILE_SUFFIXES:
            continue
        relative = rel(repo, child)
        if scan_path_is_ignored(relative):
            continue
        files.append(relative)
    return sorted(files)[:limit]


def key_files_for_resource(repo: Path, resource: str, keywords: list[str], limit: int = 8) -> list[str]:
    normalized = normalize_repo_path(resource)
    path = repo / normalized
    if path.is_file():
        return [normalized]
    files = source_files_under(repo, normalized, limit=160)
    scored: list[tuple[int, int, str]] = []
    for file in files:
        lower_path = file.lower()
        name = Path(file).name.lower()
        score = 0
        for keyword in keywords:
            keyword = keyword.lower()
            if keyword in name:
                score += 3
            elif keyword in lower_path:
                score += 1
        if score:
            scored.append((score, len(file), file))
    if scored:
        scored.sort(key=lambda item: (-item[0], item[1], item[2]))
        return [file for _, _, file in scored[:limit]]
    return files[: min(limit, 5)]


def feature_directories(repo: Path) -> list[str]:
    directories: list[str] = []
    for base in FEATURE_BASE_DIRS:
        root = repo / base
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir(), key=lambda item: item.name):
            if child.is_dir() and not child.name.startswith(".") and not scan_path_is_ignored(rel(repo, child)):
                directories.append(rel(repo, child))
    return directories


def feature_signal_score(files: list[str]) -> tuple[int, list[str]]:
    matched: set[str] = set()
    score = 0
    for file in files:
        lower = file.lower()
        for keyword in DOMAIN_SIGNAL_KEYWORDS:
            if keyword in lower:
                matched.add(keyword)
                score += 2 if keyword in {"bootstrap", "queries", "repository", "service", "store"} else 1
    return score, sorted(matched)


def concept_plan_candidate(
    repo: Path,
    path: str,
    concept_type: str,
    title: str,
    resource: str,
    reason: str,
    read: list[str] | None = None,
    questions: list[str] | None = None,
    priority: int = 100,
    stage: str = "starter",
) -> dict[str, Any]:
    normalized_resource = normalize_repo_path(resource) if resource else ""
    read_paths = unique_existing_paths(repo, read or [], limit=10)
    if not read_paths and normalized_resource:
        read_paths = key_files_for_resource(repo, normalized_resource, list(DOMAIN_SIGNAL_KEYWORDS), limit=8)
    return {
        "path": normalize_repo_path(path),
        "type": concept_type,
        "title": title,
        "resource": normalized_resource,
        "reason": reason,
        "read": read_paths,
        "questions": questions or [],
        "priority": priority,
        "stage": stage,
    }


def starter_candidate_as_plan(repo: Path, candidate: dict[str, str], priority: int) -> dict[str, Any]:
    resource = candidate.get("resource", "")
    concept_type = candidate.get("type", "")
    keywords = list(DOMAIN_SIGNAL_KEYWORDS)
    questions = [
        "What does this concept own?",
        "Which files should future agents read before editing it?",
        "What invariants or verification commands matter for changes here?",
    ]
    read: list[str] = []
    if concept_type == "Test Surface":
        read = unique_existing_paths(repo, [resource, *PACKAGE_FILE_NAMES], limit=8)
        keywords = ["test", "typecheck", "lint", "build", "script"]
        questions = [
            "Which commands are the default smoke checks?",
            "Which checks are expensive or environment-dependent?",
            "Which files define the verification scripts?",
        ]
    elif concept_type == "Invariant":
        keywords = ["migration", "sql", "schema", "database"]
        questions = [
            "What rule must future code changes preserve?",
            "Where is the rule documented or enforced?",
            "What mistake should agents avoid?",
        ]
    elif concept_type == "Workflow":
        keywords = ["readme", "setup", "dev", "local", "environment"]
        questions = [
            "What is the shortest local setup path?",
            "What commands are required before coding?",
            "What assumptions are environment-specific?",
        ]
    if not read and resource:
        read = key_files_for_resource(repo, resource, keywords, limit=8)
    return concept_plan_candidate(
        repo,
        candidate.get("path", ""),
        concept_type,
        candidate.get("title", ""),
        resource,
        candidate.get("reason", ""),
        read=read,
        questions=questions,
        priority=priority,
        stage="starter",
    )


def auth_session_candidate(repo: Path) -> dict[str, Any] | None:
    root = first_existing_dir(
        repo,
        [
            "src/features/auth",
            "src/auth",
            "app/auth",
            "lib/auth",
            "server/auth",
            "packages/auth/src",
        ],
    )
    if not root:
        return None
    read = key_files_for_resource(
        repo,
        root,
        ["auth", "session", "login", "redirect", "repository", "data", "provider", "sync", "route"],
        limit=10,
    )
    return concept_plan_candidate(
        repo,
        "knowledge/wiki/components/auth-session.md",
        "Component",
        "Auth Session",
        root,
        "Auth feature directory detected; session and redirect behavior is usually high-risk for agents.",
        read=read,
        questions=[
            "Where is the session loaded, refreshed, or persisted?",
            "How are unauthenticated users redirected?",
            "Which files own auth data access versus UI/provider wiring?",
        ],
        priority=20,
    )


def routing_shell_candidate(repo: Path) -> dict[str, Any] | None:
    routing_file = first_existing_file(
        repo,
        [
            "src/app/router.tsx",
            "src/app/router.ts",
            "src/routes.tsx",
            "src/routes.ts",
            "app/router.tsx",
            "app/router.ts",
            "app/routes.tsx",
            "app/routes.ts",
        ],
    )
    shell_dir = first_existing_dir(repo, ["src/features/shell", "src/app", "app"])
    if not routing_file and not shell_dir:
        return None
    resource = routing_file or shell_dir
    read = unique_existing_paths(repo, [routing_file], limit=2)
    if shell_dir:
        read.extend(
            path
            for path in key_files_for_resource(
                repo,
                shell_dir,
                ["router", "route", "shell", "layout", "nav", "sidebar"],
                limit=8,
            )
            if path not in read
        )
    return concept_plan_candidate(
        repo,
        "knowledge/wiki/components/app-routing-and-shell.md",
        "Component",
        "App Routing And Shell",
        resource,
        "Routing or app shell files detected; route/provider wiring is a common orientation target.",
        read=read,
        questions=[
            "Where are top-level routes declared?",
            "Which shell/layout components wrap authenticated or project views?",
            "What route changes require provider, cache, or navigation updates?",
        ],
        priority=30,
    )


def mcp_server_candidate(repo: Path, docs: list[str]) -> dict[str, Any] | None:
    root = first_existing_dir(
        repo,
        [
            "packages/mcp-server/src",
            "packages/mcp/src",
            "mcp-server/src",
            "src/mcp",
            "server/mcp",
        ],
    )
    doc = next((path for path in docs if "mcp" in path.lower()), "")
    if not root and not doc:
        return None
    resource = root or doc
    read = []
    if root:
        read.extend(
            key_files_for_resource(
                repo,
                root,
                ["server", "service", "tool", "schema", "cli", "hosted", "http", "transport"],
                limit=10,
            )
        )
    read.extend(path for path in unique_existing_paths(repo, [doc], limit=1) if path not in read)
    return concept_plan_candidate(
        repo,
        "knowledge/wiki/components/mcp-server.md",
        "Component",
        "MCP Server",
        resource,
        "MCP package or documentation detected; tool routing and schemas need explicit citations.",
        read=read,
        questions=[
            "Where are MCP tools registered and dispatched?",
            "Which schemas define valid tool inputs?",
            "How should ambiguous tool matches or transport failures be debugged?",
        ],
        priority=45,
    )


def feature_domain_candidates(repo: Path, limit: int = 3) -> list[dict[str, Any]]:
    skip_names = {"app", "auth", "common", "components", "layout", "shared", "shell", "ui"}
    scored: list[tuple[int, str, list[str], list[str]]] = []
    for directory in feature_directories(repo):
        name = Path(directory).name
        if name in skip_names:
            continue
        files = source_files_under(repo, directory, limit=160)
        score, markers = feature_signal_score(files)
        if score < 4:
            continue
        scored.append((score, directory, markers, files))
    scored.sort(key=lambda item: (-item[0], item[1]))

    candidates: list[dict[str, Any]] = []
    for offset, (_, directory, markers, files) in enumerate(scored[:limit]):
        name = Path(directory).name
        if name == "projects" and any("project-shell" in file.lower() for file in files):
            title = "Project Shell Data"
            filename = "project-shell-data"
        else:
            label = humanize_name(singularize(name))
            title = f"{label} Data Flow"
            filename = f"{slugify(label)}-data-flow"
        read = key_files_for_resource(repo, directory, list(DOMAIN_SIGNAL_KEYWORDS), limit=10)
        marker_text = ", ".join(markers[:5]) if markers else "data-flow"
        candidates.append(
            concept_plan_candidate(
                repo,
                f"knowledge/wiki/components/{filename}.md",
                "Component",
                title,
                directory,
                f"Feature directory has durable data-flow signals: {marker_text}.",
                read=read,
                questions=[
                    "Which files load, cache, mutate, or bootstrap this domain?",
                    "What should future agents update when changing this domain?",
                    "Which tests or verification commands cover the domain flow?",
                ],
                priority=40 + offset,
            )
        )
    return candidates


def smoke_test_recipe_candidate(repo: Path) -> dict[str, Any] | None:
    if not wiki_dir(repo).exists():
        return None
    read = unique_existing_paths(
        repo,
        [
            "knowledge/wiki/index.md",
            "knowledge/wiki/.karpathy-wiki.json",
            "knowledge/wiki/log.md",
        ],
        limit=5,
    )
    if not read:
        return None
    return concept_plan_candidate(
        repo,
        "knowledge/wiki/recipes/karpathy-wiki-smoke-test.md",
        "Task Recipe",
        "Karpathy Wiki Smoke Test",
        "knowledge/wiki/index.md",
        "Wiki scaffold detected; a small smoke recipe makes future dogfood checks repeatable.",
        read=read,
        questions=[
            "Which search queries should prove the wiki can answer real repo questions?",
            "Which doctor and manifest commands should stay clean?",
            "What result indicates the wiki is still too thin?",
        ],
        priority=70,
        stage="follow-up",
    )


def concept_plan(repo: Path, limit: int = 8, scan: dict[str, Any] | None = None) -> dict[str, Any]:
    data = scan or scan_repo(repo)
    candidates: list[dict[str, Any]] = []

    starter_priorities = {
        "knowledge/wiki/components/app-boot.md": 10,
        "knowledge/wiki/tests/verification-surface.md": 50,
        "knowledge/wiki/invariants/sql-migrations.md": 60,
        "knowledge/wiki/workflows/local-development.md": 90,
    }
    for starter in data.get("starter_candidates", []):
        priority = starter_priorities.get(starter.get("path", ""), 65)
        candidates.append(starter_candidate_as_plan(repo, starter, priority))

    for candidate in [
        auth_session_candidate(repo),
        routing_shell_candidate(repo),
        *feature_domain_candidates(repo),
        mcp_server_candidate(repo, data.get("docs", [])),
        smoke_test_recipe_candidate(repo),
    ]:
        if candidate:
            candidates.append(candidate)

    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    existing_paths = {rel(repo, path) for path in concept_files(repo)}
    for candidate in sorted(candidates, key=lambda item: (item["priority"], item["path"])):
        path = candidate["path"]
        if not path or path in seen or path in existing_paths or (repo / path).exists():
            continue
        seen.add(path)
        unique.append(candidate)

    concept_count = len(concept_files(repo)) if wiki_dir(repo).exists() else 0
    setup_state, _ = wiki_setup_state(repo, concept_count)
    return {
        "repo": str(repo),
        "wiki_root": "knowledge/wiki",
        "setup_state": setup_state,
        "candidate_count": len(unique[:limit]),
        "candidates": unique[:limit],
        "guidance": [
            "Use these as a ranked plan, not as generated content.",
            "Read each candidate's read list before writing a concept page.",
            "Create only the smallest set that answers near-term repo questions.",
            "Every implementation-relevant claim still needs a source citation.",
        ],
    }


def starter_concept_candidates(repo: Path, scan: dict[str, Any] | None = None) -> list[dict[str, str]]:
    data = scan or scan_repo(repo)
    candidates: list[dict[str, str]] = []
    entrypoints = data.get("source_entrypoints", [])
    if entrypoints:
        entrypoint = entrypoints[0]
        stem = Path(entrypoint).stem.replace("-", " ").replace("_", " ")
        if stem in {"main", "index", "app"}:
            title = "App Boot"
            filename = "app-boot"
        else:
            title = f"{stem.title()} Entry Point"
            filename = slugify(title)
        candidates.append(
            {
                "path": f"knowledge/wiki/components/{filename}.md",
                "type": "Component",
                "title": title,
                "resource": entrypoint,
                "reason": "Source entrypoint detected by scan.",
            }
        )

    package_files = data.get("package_and_build_files", [])
    known_commands = data.get("known_commands", [])
    if known_commands:
        package_resource = "package.json" if "package.json" in package_files else (package_files[0] if package_files else "")
        candidates.append(
            {
                "path": "knowledge/wiki/tests/verification-surface.md",
                "type": "Test Surface",
                "title": "Verification Surface",
                "resource": package_resource,
                "reason": "Verification commands detected by scan.",
            }
        )

    docs = data.get("docs", [])
    migration_doc = (
        next((path for path in docs if Path(path).name.lower() == "sql_migrations.md"), "")
        or next((path for path in docs if "migration" in path.lower()), "")
        or next((path for path in docs if "sql" in path.lower()), "")
    )
    if migration_doc:
        candidates.append(
            {
                "path": "knowledge/wiki/invariants/sql-migrations.md",
                "type": "Invariant",
                "title": "SQL Migrations",
                "resource": migration_doc,
                "reason": "SQL or migration documentation detected by scan.",
            }
        )

    readme = next((path for path in docs if Path(path).name.lower().startswith("readme")), "")
    if readme:
        candidates.append(
            {
                "path": "knowledge/wiki/workflows/local-development.md",
                "type": "Workflow",
                "title": "Local Development",
                "resource": readme,
                "reason": "README detected as high-signal setup documentation.",
            }
        )

    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for candidate in candidates:
        path = candidate["path"]
        if path in seen:
            continue
        seen.add(path)
        unique.append(candidate)
    return unique[:5]


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
    priority_names = {
        "architecture.md",
        "contributing.md",
        "mcp.md",
        "sql_migrations.md",
        "testing.md",
    }
    ordered = sorted(paths)
    priority = [
        path
        for path in ordered
        if Path(path).name.lower() in priority_names or path.lower().startswith("docs/public/")
    ]
    rest = [path for path in ordered if path not in set(priority)]
    return [*priority, *rest][:80]


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
    data = {
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
    data["starter_candidates"] = starter_concept_candidates(repo, data)
    return data


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


def required_wiki_files(repo: Path) -> list[Path]:
    return [wiki_dir(repo) / "index.md", wiki_dir(repo) / "log.md", manifest_path(repo)]


def wiki_setup_state(repo: Path, concept_count: int) -> tuple[str, list[str]]:
    if not wiki_dir(repo).exists():
        return "missing", ["knowledge/wiki"]
    missing = [rel(repo, path) for path in required_wiki_files(repo) if not path.exists()]
    if missing:
        return "incomplete-setup", missing
    if concept_count == 0:
        return "needs-starter-concepts", []
    return "ready", []


def status(repo: Path) -> dict[str, Any]:
    exists = wiki_dir(repo).exists()
    manifest = load_manifest(repo) if exists else {}
    changes = changed_paths(repo)
    affected = affected_concepts(repo, paths_for_scope(changes, "all"), manifest) if exists else {}
    concept_count = len(manifest.get("concepts", [])) if exists else 0
    setup_state, missing_required = wiki_setup_state(repo, concept_count)
    starter_candidates = starter_concept_candidates(repo) if setup_state == "needs-starter-concepts" else []
    return {
        "repo": str(repo),
        "wiki_exists": exists,
        "wiki_root": "knowledge/wiki",
        "manifest_exists": manifest_path(repo).exists(),
        "setup_state": setup_state,
        "missing_required_files": missing_required,
        "concept_count": concept_count,
        "starter_candidates": starter_candidates,
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

    for page in wiki_markdown_files(repo):
        page_rel = rel(repo, page)
        for link in markdown_links(read_text(page)):
            target = resolve_wiki_page_link(repo, page, link)
            if is_within(target, repo) and not target.exists():
                issues.append(Issue("critical", page_rel, f"broken local link: {link}"))

    reachable = reachable_wiki_pages(repo)
    for path in concept_files(repo):
        text = read_text(path)
        frontmatter, body = parse_frontmatter(text)
        concept_rel = rel(repo, path)
        if path.resolve() not in reachable and not wiki_page_is_draft(path):
            issues.append(Issue("warning", concept_rel, "concept page is not reachable from knowledge/wiki/index.md"))
        if not frontmatter:
            issues.append(Issue("warning", concept_rel, "missing YAML frontmatter"))
        for field in REQUIRED_CONCEPT_FIELDS:
            if field not in frontmatter or not str(frontmatter.get(field, "")).strip():
                issues.append(Issue("warning", concept_rel, f"missing frontmatter field: {field}"))
        if "source_commit" not in frontmatter or not str(frontmatter.get("source_commit", "")).strip():
            issues.append(Issue("warning", concept_rel, "missing frontmatter field: source_commit"))
        refs = source_refs_for_concept(repo, path, frontmatter, body)
        if not refs:
            issues.append(Issue("warning", concept_rel, "no source resource or citation detected"))
        for ref in refs:
            if not (repo / ref).exists():
                issues.append(Issue("critical", concept_rel, f"source reference does not exist: {ref}"))
        for source_id in raw_source_ids_for_concept(frontmatter, body):
            if not raw_record_paths(repo, source_id):
                issues.append(Issue("warning", concept_rel, f"raw source id does not resolve: {source_id}"))

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
        and not path.startswith("knowledge/raw/")
        and not path.startswith("knowledge/wiki/")
        and not path.startswith("knowledge/outputs/")
        and path != "knowledge/rules.md"
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
    print(f"Setup state: {data.get('setup_state', 'unknown')}")
    missing = data.get("missing_required_files", [])
    if missing:
        print("Missing required files:")
        for path in missing:
            print(f"- {path}")
    if data["wiki_exists"]:
        print(f"Concepts: {data['concept_count']}")
        candidates = data.get("starter_candidates", [])
        if candidates:
            print("Starter concept candidates:")
            for candidate in candidates:
                resource = f" citing {candidate['resource']}" if candidate.get("resource") else ""
                print(f"- {candidate['path']} ({candidate['type']}: {candidate['title']}){resource}")
            print("Next: create 2-5 cited concept pages, then run refresh-manifest and doctor.")
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
        ("starter_candidates", "Starter Concept Candidates"),
        ("guidance", "Guidance"),
    ]:
        print(f"\n## {title}")
        values = data.get(key, [])
        if values:
            for value in values:
                if isinstance(value, dict):
                    resource = f" citing {value['resource']}" if value.get("resource") else ""
                    print(f"- {value['path']} ({value['type']}: {value['title']}){resource} - {value['reason']}")
                else:
                    print(f"- {value}")
        else:
            print("- None detected")


def print_concept_plan(data: dict[str, Any]) -> None:
    print("# Karpathy Wiki Concept Plan")
    print(f"Repo: {data['repo']}")
    print(f"Setup state: {data.get('setup_state', 'unknown')}")
    candidates = data.get("candidates", [])
    print("\n## Candidates")
    if candidates:
        for candidate in candidates:
            resource = f" citing {candidate['resource']}" if candidate.get("resource") else ""
            print(f"- {candidate['path']} ({candidate['type']}: {candidate['title']}){resource}")
            print(f"  reason: {candidate['reason']}")
            reads = candidate.get("read", [])
            if reads:
                print("  read: " + ", ".join(reads))
    else:
        print("- None detected")
    guidance = data.get("guidance", [])
    if guidance:
        print("\n## Guidance")
        for item in guidance:
            print(f"- {item}")


def print_compile_plan(data: dict[str, Any]) -> None:
    print("# Karpathy Wiki Compile Plan")
    print(f"Unit: {data['unit_type']}")
    if data.get("source_id"):
        print(f"Source id: {data['source_id']}")
    print("\n## Source Paths")
    for path in data.get("source_paths", []):
        print(f"- {path}")
    candidates = data.get("affected_concept_candidates", [])
    print("\n## Affected Concept Candidates")
    if candidates:
        for candidate in candidates:
            print(f"- {candidate['path']} - {candidate['reason']}")
    else:
        print("- None")
    print("\n## Questions")
    for question in data.get("questions", []):
        print(f"- {question}")


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
    concept_plan_parser = sub.add_parser("concept-plan")
    add_common(concept_plan_parser)
    concept_plan_parser.add_argument("--limit", type=int, default=8)
    compile_plan_parser = sub.add_parser("compile-plan")
    add_common(compile_plan_parser)
    compile_plan_group = compile_plan_parser.add_mutually_exclusive_group(required=True)
    compile_plan_group.add_argument("--source", default="")
    compile_plan_group.add_argument("--source-id", default="")
    compile_plan_parser.add_argument("--limit", type=int, default=COMPILE_SOURCE_SET_LIMIT)
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
    raw_add_parser = sub.add_parser("raw-add")
    add_common(raw_add_parser)
    raw_add_parser.add_argument("--kind", required=True)
    raw_add_parser.add_argument("--title", required=True)
    raw_add_parser.add_argument("--body-file", required=True)
    raw_add_parser.add_argument("--source-url", default="")
    raw_correct_parser = sub.add_parser("raw-correct")
    add_common(raw_correct_parser)
    raw_correct_parser.add_argument("--source-id", required=True)
    raw_correct_parser.add_argument("--body-file", required=True)
    raw_redact_parser = sub.add_parser("raw-redact")
    add_common(raw_redact_parser)
    raw_redact_parser.add_argument("--source-id", required=True)
    raw_redact_parser.add_argument("--reason", required=True)
    raw_show_parser = sub.add_parser("raw-show")
    add_common(raw_show_parser)
    raw_show_parser.add_argument("--source-id", required=True)
    improvement_parser = sub.add_parser("note-improvement")
    add_common(improvement_parser)
    improvement_parser.add_argument("--title", required=True)
    improvement_parser.add_argument("--body", required=True)
    improvement_parser.add_argument("--suggestion", default="")
    improvement_parser.add_argument("--evidence", action="append", default=[])
    improvement_parser.add_argument("--tag", action="append", default=[])

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
    if args.command == "concept-plan":
        data = concept_plan(repo, limit=args.limit)
        if json_output:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            print_concept_plan(data)
        return 0
    if args.command == "compile-plan":
        data = compile_plan(repo, source=args.source, raw_source_id=args.source_id, limit=args.limit)
        if json_output:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            print_compile_plan(data)
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
    if args.command == "raw-add":
        data = raw_add(repo, args.kind, args.title, Path(args.body_file), source_url=args.source_url)
        print(json.dumps(data, indent=2, sort_keys=True) if json_output else f"Created {data['path']}")
        return 0
    if args.command == "raw-correct":
        data = raw_correct(repo, args.source_id, Path(args.body_file))
        print(json.dumps(data, indent=2, sort_keys=True) if json_output else f"Created {data['path']}")
        return 0
    if args.command == "raw-redact":
        data = raw_redact(repo, args.source_id, args.reason)
        print(json.dumps(data, indent=2, sort_keys=True) if json_output else f"Redacted {data['path']}")
        return 0
    if args.command == "raw-show":
        data = raw_show(repo, args.source_id)
        print(json.dumps(data, indent=2, sort_keys=True) if json_output else data["body"], end="" if not json_output else "\n")
        return 0
    if args.command == "note-improvement":
        data = append_improvement_note(
            repo,
            args.title,
            args.body,
            suggestion=args.suggestion,
            evidence=args.evidence,
            tags=args.tag,
        )
        print(json.dumps(data, indent=2, sort_keys=True) if json_output else f"Appended {data['path']}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
