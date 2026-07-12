#!/usr/bin/env python3
"""Advisory update checker and repair helper for the Karpathy plugin.

Hook mode is advisory and non-fatal. Manual mode powers `/karpathy:update` and
uses one normalized install-status payload for both JSON and human output.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


MARKETPLACE_NAME = "karpathy-skills"
PLUGIN_SELECTOR = "karpathy@karpathy-skills"
PLUGIN_NAME = "karpathy"
DEFAULT_CHECK_URL = (
    "https://raw.githubusercontent.com/jokim1/karpathy-skills/main/"
    "plugins/karpathy/.claude-plugin/plugin.json"
)
DEFAULT_UPDATE_COMMAND_TIMEOUT_SECONDS = 120.0
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$"
)

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
REQUIRED_SURFACES = {
    "commands": REQUIRED_COMMANDS,
    "skills": REQUIRED_SKILLS,
    "manifests": REQUIRED_MANIFESTS,
}
LEGACY_STANDALONE_SKILL_NAMES = {
    "karpathy-audit",
    "karpathy-diff",
    "karpathy-wiki",
}
LEGACY_STANDALONE_HASHES = {
    "karpathy-audit": {
        "0062625ad627c7be58e306610c0627ebe4e8ea5841fc5f6d83e6270a2ef02d0e",
        "4767de04c7b958fd96970c0b77822a5f0954edd9d4c2c26ae64fb1ef085694e0",
        "557b4eacc5225389d0dc32cebe0e9e1beb64d2c51673041dbc27003c5ffbaae4",
        "94c5be06fa12339d4f4d75f474533998a0aa5e1ecffabf549c923d9bf22b42e8",
        "9932c5d82cb576145f92e132fe5e72fa69996edccdcac5eef4e5a08c949ac665",
        "b9904139473ecaf20e5fbd669ad24b9d46ae170fd4878a1b313e1dff4368879b",
    },
    "karpathy-diff": {
        "c38fe0ed5ed96ecf2ac010e0c06e92f7eda45bb99aa4fa0739be17615b6e957d",
    },
    "karpathy-wiki": {
        "11fe493fc68adb7469ab221df65ae0f48b668df0fbe51383eba49649f4d2f543",
        "3d1a562ebcfdc8bd05a565bac213e4417b5854eea4debec33a120fa5fcac1668",
        "5189d71a4dbbc59b7e5aba88972d001c0bcf623d39250a7c8677f858b086ac13",
        "7a59880cb1afb730a646d68b74a4c693bb1a5cf8e7a0e2bb055ba8ac450caa08",
        "8e1d3e396e7a6e7e97b2a3fdb5ba2848f7faf029e2f04a0b5979ff6f52401b9b",
        "c8430aa84e35f5334c1242d6c1b3b8a2879644361ba8104dd84a187d7f8cd109",
        "d083d654d1f03321b5161bc1b958edd3f4d2732ac60751be54f565b96c78fb9f",
        "f066f0a7553767c35cb29b05a289d81f29c965efc3370b6e515ff249f4c251a9",
    },
}

HEALTHY_PLUGIN_INSTALL = "healthy_plugin_install"
PLUGIN_UPDATE_AVAILABLE = "plugin_update_available"
PARTIAL_PLUGIN_INSTALL = "partial_plugin_install"
LEGACY_STANDALONE_INSTALL = "legacy_standalone_install"
MIXED_PLUGIN_AND_LEGACY_INSTALL = "mixed_plugin_and_legacy_install"
CURRENT_THREAD_STALE = "current_thread_stale"
UNKNOWN = "unknown"

REPAIRABLE_STATES = {
    PLUGIN_UPDATE_AVAILABLE,
    PARTIAL_PLUGIN_INSTALL,
    LEGACY_STANDALONE_INSTALL,
    MIXED_PLUGIN_AND_LEGACY_INSTALL,
    UNKNOWN,
}


def main() -> int:
    args = sys.argv[1:]
    if "--help" in args or "-h" in args:
        print_usage()
        return 0
    if "--check" in args:
        payload = manual_check()
        emit_result(payload, json_output="--json" in args)
        return 1 if payload["install_state"] == UNKNOWN else 0
    if "--update" in args:
        payload = manual_update()
        emit_result(payload, json_output="--json" in args)
        return 0 if payload.get("ok", False) else 1

    try:
        run(output_mode=read_output_mode(args))
    except Exception:
        # Update checks should never break a user's coding session.
        return 0
    return 0


def read_output_mode(args: list[str]) -> str:
    if "--system-message" in args:
        return "system-message"
    return "text"


def run(output_mode: str = "text") -> None:
    """SessionStart hook entrypoint.

    This path stays bounded and advisory: it does not invoke plugin managers,
    archive legacy directories, or scan the user's home directory for old
    standalone installs.
    """

    if env_truthy("KARPATHY_DISABLE_UPDATE_CHECK"):
        return

    status = collect_install_status(
        include_home_scan=False,
        fetch_latest=False,
    )
    if status.get("skipped"):
        return

    if status["install_state"] == PLUGIN_UPDATE_AVAILABLE:
        print_update_notice(status, output_mode=output_mode)
    elif status["install_state"] == PARTIAL_PLUGIN_INSTALL:
        print_repair_notice(status, output_mode=output_mode)


def manual_check() -> dict[str, Any]:
    status = collect_install_status(include_home_scan=True)
    status["action"] = check_action_for_state(status["install_state"])
    status["ok"] = status["install_state"] != UNKNOWN
    return finalize_payload(status)


def manual_update() -> dict[str, Any]:
    status = collect_install_status(include_home_scan=True)
    state = status["install_state"]
    repair_target_version = status.get("latest_version")

    if state == CURRENT_THREAD_STALE:
        status.update(
            {
                "action": "restart_required",
                "ok": True,
                "next_steps": ["Start a new Codex thread so refreshed Karpathy commands and skills are loaded."],
            }
        )
        return finalize_payload(status)

    if state not in REPAIRABLE_STATES:
        status.update({"action": "none", "ok": True, "next_steps": []})
        return finalize_payload(status)

    status["next_steps"] = next_steps_for_state(status)
    if not running_in_codex():
        status.update({"action": "manual_required", "ok": True})
        return finalize_payload(status)

    if env_truthy("KARPATHY_UPDATE_DRY_RUN"):
        status.update(
            {
                "action": "dry_run",
                "ok": True,
                "commands": codex_update_commands(),
                "next_steps": ["Dry run only. Run `/karpathy:update` without `KARPATHY_UPDATE_DRY_RUN=1` to repair."],
            }
        )
        return finalize_payload(status)

    repair_result = run_codex_repair()
    status.update(repair_result)
    if repair_result["action"] != "repair_commands_completed":
        status.update({"action": "manual_required", "ok": False, "next_steps": next_steps_for_state(status)})
        return finalize_payload(status)

    verification = collect_install_status(include_home_scan=True)
    error = repair_verification_error(
        verification,
        allow_mixed_legacy=True,
        repair_target_version=repair_target_version,
    )
    if error:
        verification.update(
            {
                "action": "manual_required",
                "ok": False,
                "commands": repair_result["commands"],
                "error": error,
                "next_steps": next_steps_for_state(verification),
                "pre_repair_install_state": state,
                "repair_target_version": repair_target_version,
            }
        )
        return finalize_payload(verification)

    archive_result = archive_legacy_standalone_dirs()
    if archive_result.get("archive_failed_dirs"):
        verification.update(
            {
                "action": "manual_required",
                "ok": False,
                "commands": repair_result["commands"],
                "backup_path": archive_result.get("backup_path"),
                "archived_legacy_dirs": archive_result.get("archived_legacy_dirs", []),
                "archive_failed_dirs": archive_result.get("archive_failed_dirs", []),
                "error": "Codex repair commands completed, but legacy standalone archive did not fully complete.",
                "next_steps": [
                    "Review the archive results, then move any remaining legacy `~/.codex/skills/karpathy-*` dirs manually if they are old standalone Karpathy skills.",
                    "Start a new Codex thread so refreshed Karpathy commands and skills are loaded.",
                ],
                "pre_repair_install_state": state,
            }
        )
        return finalize_payload(verification)

    verified = collect_install_status(include_home_scan=True)
    error = repair_verification_error(
        verified,
        allow_mixed_legacy=False,
        repair_target_version=repair_target_version,
    )
    if error:
        verified.update(
            {
                "action": "manual_required",
                "ok": False,
                "commands": repair_result["commands"],
                "backup_path": archive_result.get("backup_path"),
                "archived_legacy_dirs": archive_result.get("archived_legacy_dirs", []),
                "error": error,
                "next_steps": next_steps_for_state(verified),
                "pre_repair_install_state": state,
                "repair_target_version": repair_target_version,
            }
        )
        return finalize_payload(verified)

    verified.update(
        {
            "install_state": CURRENT_THREAD_STALE,
            "status": CURRENT_THREAD_STALE,
            "verified_install_state": verified["install_state"],
            "pre_repair_install_state": state,
            "repair_target_version": repair_target_version,
            "action": "repaired",
            "ok": True,
            "commands": repair_result["commands"],
            "backup_path": archive_result.get("backup_path"),
            "archived_legacy_dirs": archive_result.get("archived_legacy_dirs", []),
            "next_steps": ["Start a new Codex thread so refreshed Karpathy commands and skills are loaded."],
        }
    )
    clear_update_cache()
    return finalize_payload(verified)


def collect_install_status(
    include_home_scan: bool,
    fetch_latest: bool = True,
) -> dict[str, Any]:
    root = plugin_root()
    surfaces = inspect_required_surfaces(root)
    manifest_versions = read_manifest_versions(root)
    installed_version = display_version(manifest_versions)
    manifest_version_problem = has_manifest_version_problem(surfaces, manifest_versions)

    latest_version = fetch_latest_version() if fetch_latest else None

    legacy_dirs = find_legacy_standalone_dirs() if include_home_scan else []
    stale_thread = detect_current_thread_stale(root, installed_version)
    effective_version = (
        stale_thread.get("installed_version")
        if isinstance(stale_thread, dict)
        else installed_version
    )
    update_available = bool(
        latest_version and effective_version and is_newer(latest_version, effective_version)
    )
    has_plugin_surface = bool(surfaces["present"])
    has_missing_surface = bool(surfaces["missing"])

    if has_plugin_surface and legacy_dirs:
        install_state = MIXED_PLUGIN_AND_LEGACY_INSTALL
    elif not has_plugin_surface and legacy_dirs:
        install_state = LEGACY_STANDALONE_INSTALL
    elif stale_thread and update_available:
        install_state = PLUGIN_UPDATE_AVAILABLE
    elif stale_thread:
        install_state = CURRENT_THREAD_STALE
    elif has_plugin_surface and (has_missing_surface or manifest_version_problem):
        install_state = PARTIAL_PLUGIN_INSTALL
    elif has_plugin_surface and update_available:
        install_state = PLUGIN_UPDATE_AVAILABLE
    elif has_plugin_surface and not has_missing_surface and installed_version:
        install_state = HEALTHY_PLUGIN_INSTALL
    else:
        install_state = UNKNOWN

    payload: dict[str, Any] = {
        "client": detect_client(),
        "plugin_root": str(root),
        "homes": {
            "codex": str(codex_home()),
            "claude": str(claude_home()),
        },
        "install_state": install_state,
        "status": install_state,
        "installed_version": installed_version,
        "local_version": installed_version,
        "effective_version": effective_version,
        "latest_version": latest_version,
        "update_available": update_available,
        "manifest_versions": manifest_versions,
        "manifest_version_mismatch": manifest_version_problem,
        "required_surfaces": surfaces,
        "legacy_standalone_dirs": [str(path) for path in legacy_dirs],
        "current_thread_stale_candidate": stale_thread,
        "backup_path": None,
        "commands": [],
        "action": check_action_for_state(install_state),
        "next_steps": [],
        "ok": install_state != UNKNOWN,
    }
    return finalize_payload(payload)


def inspect_required_surfaces(root: Path) -> dict[str, Any]:
    by_kind: dict[str, dict[str, list[str]]] = {}
    all_present: list[str] = []
    all_missing: list[str] = []

    for kind, relatives in REQUIRED_SURFACES.items():
        present = []
        missing = []
        for relative in relatives:
            if (root / relative).is_file():
                present.append(relative)
                all_present.append(relative)
            else:
                missing.append(relative)
                all_missing.append(relative)
        by_kind[kind] = {"present": present, "missing": missing}

    return {
        "by_kind": by_kind,
        "present": all_present,
        "missing": all_missing,
    }


def detect_client() -> str:
    if running_in_codex():
        return "codex"
    if os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("CLAUDECODE") or os.environ.get("CLAUDE_CODE"):
        return "claude_code"
    return "unknown"


def env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def plugin_root() -> Path:
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("PLUGIN_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    return Path(__file__).resolve().parents[1]


def codex_home() -> Path:
    env_home = os.environ.get("KARPATHY_CODEX_HOME")
    if env_home:
        return Path(env_home).expanduser().resolve()
    return Path.home() / ".codex"


def claude_home() -> Path:
    env_home = os.environ.get("KARPATHY_CLAUDE_HOME")
    if env_home:
        return Path(env_home).expanduser().resolve()
    return Path.home() / ".claude"


def read_manifest_versions(root: Path) -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for relative in REQUIRED_MANIFESTS:
        manifest = root / relative
        if not manifest.is_file():
            versions[relative] = None
            continue
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            versions[relative] = None
            continue
        version = payload.get("version")
        if isinstance(version, str) and version.strip():
            versions[relative] = version.strip()
        else:
            versions[relative] = None
    return versions


def read_local_version(root: Path) -> str | None:
    return display_version(read_manifest_versions(root))


def display_version(manifest_versions: dict[str, str | None]) -> str | None:
    versions = [version for version in manifest_versions.values() if version]
    if not versions:
        return None
    return sorted(versions, key=semver_key, reverse=True)[0]


def has_manifest_version_problem(
    surfaces: dict[str, Any],
    manifest_versions: dict[str, str | None],
) -> bool:
    missing_manifests = surfaces["by_kind"]["manifests"]["missing"]
    if missing_manifests:
        return False
    versions = [manifest_versions.get(relative) for relative in REQUIRED_MANIFESTS]
    if any(version is None for version in versions):
        return True
    if any(not is_valid_semver(version) for version in versions):
        return True
    return len(set(versions)) > 1


def update_cache_path(create: bool = True) -> Path:
    data_root = (
        os.environ.get("CLAUDE_PLUGIN_DATA")
        or os.environ.get("PLUGIN_DATA")
        or os.environ.get("KARPATHY_PLUGIN_DATA")
    )
    if data_root:
        path = Path(data_root).expanduser()
    else:
        cache_home = os.environ.get("XDG_CACHE_HOME")
        path = Path(cache_home).expanduser() if cache_home else Path.home() / ".cache"
        path = path / "karpathy-skills"
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path / "update-check.json"


def clear_update_cache() -> None:
    try:
        update_cache_path(create=False).unlink()
    except OSError:
        pass


def read_update_command_timeout_seconds() -> float:
    raw = os.environ.get("KARPATHY_UPDATE_COMMAND_TIMEOUT_SECONDS")
    if raw is None:
        return DEFAULT_UPDATE_COMMAND_TIMEOUT_SECONDS
    try:
        timeout = float(raw)
    except ValueError:
        return DEFAULT_UPDATE_COMMAND_TIMEOUT_SECONDS
    return timeout if timeout > 0 else DEFAULT_UPDATE_COMMAND_TIMEOUT_SECONDS


def fetch_latest_version() -> str | None:
    url = os.environ.get("KARPATHY_UPDATE_CHECK_URL", DEFAULT_CHECK_URL)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "karpathy-skills-update-check"},
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None
    version = payload.get("version") if isinstance(payload, dict) else None
    return version.strip() if isinstance(version, str) and version.strip() else None


def semver_key(version: str | None) -> tuple[Any, ...]:
    if not version:
        return ((0, "0"), (0, "0"), (0, "0"), 0, ())
    match = SEMVER_RE.fullmatch(version)
    if not match or not is_valid_semver(version):
        return ((0, "0"), (0, "0"), (0, "0"), 0, ())

    major, minor, patch = (
        (len(part), part)
        for part in match.groups()[:3]
    )
    prerelease = match.group(4)
    if prerelease is None:
        return (major, minor, patch, 1, ())

    identifiers = tuple(
        (0, len(identifier), identifier)
        if identifier.isdigit()
        else (1, 0, identifier)
        for identifier in prerelease.split(".")
    )
    return (major, minor, patch, 0, identifiers)


def is_valid_semver(version: str | None) -> bool:
    if not version:
        return False
    match = SEMVER_RE.fullmatch(version)
    if not match:
        return False

    prerelease = match.group(4)
    build = match.group(5)
    if prerelease:
        identifiers = prerelease.split(".")
        if any(
            not identifier
            or (identifier.isdigit() and len(identifier) > 1 and identifier.startswith("0"))
            for identifier in identifiers
        ):
            return False
    if build and any(not identifier for identifier in build.split(".")):
        return False
    return True


def is_newer(latest: str, local: str) -> bool:
    return semver_key(latest) > semver_key(local)


def running_in_codex() -> bool:
    return bool(os.environ.get("CODEX_SHELL") or os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_CI"))


def find_legacy_standalone_dirs() -> list[Path]:
    skills_root = codex_home() / "skills"
    try:
        children = list(skills_root.iterdir())
    except OSError:
        return []
    return sorted(path for path in children if is_known_legacy_standalone_dir(path))


def is_known_legacy_standalone_dir(path: Path) -> bool:
    if not path.is_dir() or path.name not in LEGACY_STANDALONE_SKILL_NAMES:
        return False

    skill_file = path / "SKILL.md"
    try:
        digest = hashlib.sha256(skill_file.read_bytes()).hexdigest()
    except OSError:
        return False
    return digest in LEGACY_STANDALONE_HASHES[path.name]


def archive_legacy_standalone_dirs() -> dict[str, Any]:
    legacy_dirs = find_legacy_standalone_dirs()
    if not legacy_dirs:
        return {"backup_path": None, "archived_legacy_dirs": [], "archive_failed_dirs": []}

    backup_root = codex_home() / "backups" / f"karpathy-legacy-{time.strftime('%Y%m%d-%H%M%S')}"
    suffix = 1
    while backup_root.exists():
        backup_root = backup_root.with_name(f"{backup_root.name}-{suffix}")
        suffix += 1
    failed = []
    try:
        backup_root.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        return {
            "backup_path": str(backup_root),
            "archived_legacy_dirs": [],
            "archive_failed_dirs": [
                {"path": str(path), "error": str(exc)}
                for path in legacy_dirs
            ],
        }

    archived = []
    for path in legacy_dirs:
        destination = backup_root / path.name
        try:
            shutil.move(str(path), str(destination))
        except OSError as exc:
            failed.append({"path": str(path), "error": str(exc)})
        else:
            archived.append(str(destination))

    return {
        "backup_path": str(backup_root),
        "archived_legacy_dirs": archived,
        "archive_failed_dirs": failed,
    }


def detect_current_thread_stale(root: Path, installed_version: str | None) -> dict[str, str] | None:
    if not running_in_codex():
        return None

    cache_root = codex_home() / "plugins" / "cache" / MARKETPLACE_NAME / PLUGIN_NAME
    try:
        resolved_root = root.resolve()
        resolved_cache = cache_root.resolve()
    except OSError:
        return None

    if not is_relative_to(resolved_root, resolved_cache):
        return None

    try:
        candidates = [path for path in resolved_cache.iterdir() if path.is_dir()]
    except OSError:
        return None

    best_path = None
    best_version = installed_version
    for candidate in candidates:
        if candidate.resolve() == resolved_root:
            continue
        candidate_surfaces = inspect_required_surfaces(candidate)
        candidate_manifest_versions = read_manifest_versions(candidate)
        candidate_version = read_local_version(candidate)
        if not candidate_version:
            continue
        if best_version and not is_newer(candidate_version, best_version):
            continue
        if candidate_surfaces["missing"] or has_manifest_version_problem(
            candidate_surfaces,
            candidate_manifest_versions,
        ):
            continue
        best_path = candidate
        best_version = candidate_version

    if best_path is None:
        return None
    return {"plugin_root": str(best_path), "installed_version": best_version}


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def codex_update_commands() -> list[str]:
    return [
        f"codex plugin marketplace upgrade {MARKETPLACE_NAME}",
        f"codex plugin add {PLUGIN_SELECTOR}",
    ]


def codex_command_argvs(codex: str) -> list[list[str]]:
    return [
        [codex, "plugin", "marketplace", "upgrade", MARKETPLACE_NAME],
        [codex, "plugin", "add", PLUGIN_SELECTOR],
    ]


def format_seconds(seconds: float) -> str:
    return f"{seconds:g}"


def timeout_output(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip()
    return str(value).strip()


def run_codex_repair() -> dict[str, Any]:
    codex = shutil.which("codex")
    if not codex:
        return {
            "action": "manual_required",
            "commands": [],
            "error": "codex CLI was not found on PATH.",
        }

    command_results = []
    timeout = read_update_command_timeout_seconds()
    for command, command_label in zip(codex_command_argvs(codex), codex_update_commands()):
        try:
            completed = subprocess.run(
                command,
                text=True,
                capture_output=True,
                check=False,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            command_results.append(
                {
                    "command": command_label,
                    "returncode": None,
                    "stdout": timeout_output(exc.stdout),
                    "stderr": timeout_output(exc.stderr),
                }
            )
            return {
                "action": "manual_required",
                "commands": command_results,
                "error": f"{command_label} timed out after {format_seconds(timeout)} seconds.",
            }
        command_results.append(
            {
                "command": command_label,
                "returncode": completed.returncode,
                "stdout": completed.stdout.strip(),
                "stderr": completed.stderr.strip(),
            }
        )
        if completed.returncode != 0:
            return {
                "action": "manual_required",
                "commands": command_results,
                "error": completed.stderr.strip()
                or completed.stdout.strip()
                or f"{command_label} exited {completed.returncode}",
            }

    return {
        "action": "repair_commands_completed",
        "commands": command_results,
    }


def repair_verification_error(
    payload: dict[str, Any],
    allow_mixed_legacy: bool,
    repair_target_version: str | None = None,
) -> str | None:
    state = payload["install_state"]
    missing = payload["required_surfaces"]["missing"]
    if missing:
        return "Codex repair commands completed, but required Karpathy surfaces are still missing."
    if payload.get("manifest_version_mismatch"):
        return "Codex repair commands completed, but Karpathy manifest versions are still inconsistent."
    effective_version = payload.get("effective_version")
    if (
        repair_target_version
        and isinstance(effective_version, str)
        and is_newer(repair_target_version, effective_version)
    ):
        return (
            "Codex repair commands completed, but the installed Karpathy plugin "
            f"is still older than repair target {repair_target_version}."
        )
    if state == PLUGIN_UPDATE_AVAILABLE:
        return "Codex repair commands completed, but the installed Karpathy plugin is still older than the latest version."
    if state in {PARTIAL_PLUGIN_INSTALL, LEGACY_STANDALONE_INSTALL, UNKNOWN}:
        return "Codex repair commands completed, but the Karpathy plugin install is still not healthy."
    if state == MIXED_PLUGIN_AND_LEGACY_INSTALL and not allow_mixed_legacy:
        return "Codex repair commands completed, but legacy standalone Karpathy dirs are still present."
    return None


def check_action_for_state(state: str) -> str:
    if state == HEALTHY_PLUGIN_INSTALL:
        return "none"
    if state == PLUGIN_UPDATE_AVAILABLE:
        return "update_available"
    if state == CURRENT_THREAD_STALE:
        return "restart_required"
    return "repair_required"


def next_steps_for_state(payload: dict[str, Any]) -> list[str]:
    state = payload["install_state"]
    if state == HEALTHY_PLUGIN_INSTALL:
        if payload.get("latest_version"):
            return []
        return ["Required surfaces are present. Latest version is unavailable; run `/karpathy:update --check` again later if needed."]
    if state == CURRENT_THREAD_STALE:
        return ["Start a new Codex thread so refreshed Karpathy commands and skills are loaded."]

    steps = ["Run `/karpathy:update`."]
    if state in {PARTIAL_PLUGIN_INSTALL, LEGACY_STANDALONE_INSTALL, MIXED_PLUGIN_AND_LEGACY_INSTALL, UNKNOWN}:
        steps.append("If slash commands are unavailable, type `karpathy update` as normal text.")

    client = payload.get("client")
    if client == "codex":
        steps.extend(codex_recovery_steps())
    elif client == "claude_code":
        steps.extend(claude_recovery_steps())
    else:
        steps.extend(claude_recovery_steps())
        steps.extend(codex_recovery_steps())
    return steps


def claude_recovery_steps() -> list[str]:
    return [
        "Claude Code: `/plugin marketplace update karpathy-skills`.",
        "Claude Code: `/plugin install karpathy@karpathy-skills`.",
        "Claude Code: `/reload-plugins`.",
    ]


def codex_recovery_steps() -> list[str]:
    return [
        "Codex: `codex plugin marketplace upgrade karpathy-skills`.",
        "Codex: `codex plugin add karpathy@karpathy-skills`.",
        "Codex: start a new Codex thread.",
    ]


def message_for_payload(payload: dict[str, Any]) -> str:
    state = payload["install_state"]
    installed = payload.get("installed_version") or "unknown"
    latest = payload.get("latest_version")

    if payload.get("action") == "repaired":
        return "Karpathy plugin repair completed. Start a new Codex thread so refreshed commands and skills are loaded."
    if state == HEALTHY_PLUGIN_INSTALL and latest:
        return f"Karpathy plugin is healthy and up to date ({installed})."
    if state == HEALTHY_PLUGIN_INSTALL:
        return f"Karpathy plugin surfaces are healthy ({installed}); latest version is unavailable."
    if state == PLUGIN_UPDATE_AVAILABLE:
        return f"Karpathy plugin update available: {installed} -> {latest}."
    if state == PARTIAL_PLUGIN_INSTALL:
        if payload.get("manifest_version_mismatch"):
            return "Karpathy plugin install has inconsistent or unreadable manifest versions."
        return "Karpathy plugin install is incomplete; required command, skill, or manifest surfaces are missing."
    if state == LEGACY_STANDALONE_INSTALL:
        return "Legacy standalone Karpathy skill directories were found without a complete plugin install."
    if state == MIXED_PLUGIN_AND_LEGACY_INSTALL:
        return "Karpathy plugin and legacy standalone skill directories are both present; repair will refresh the plugin and archive legacy dirs."
    if state == CURRENT_THREAD_STALE:
        return "Karpathy plugin appears repaired or updated, but this thread may still have stale commands and skills loaded."
    return "Could not determine the Karpathy plugin install state."


def finalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    payload["status"] = payload["install_state"]
    payload.setdefault("required_surfaces", inspect_required_surfaces(plugin_root()))
    payload.setdefault("commands", [])
    payload.setdefault("backup_path", None)
    payload.setdefault("next_steps", next_steps_for_state(payload))
    if not payload["next_steps"]:
        payload["next_steps"] = next_steps_for_state(payload)
    payload["instructions"] = payload["next_steps"]
    payload["message"] = message_for_payload(payload)
    return payload


def emit_result(payload: dict[str, Any], json_output: bool = False) -> None:
    if json_output:
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return

    sys.stdout.write(f"{payload['message']}\n\n")
    sys.stdout.write(f"Client: {payload.get('client', 'unknown')}\n")
    sys.stdout.write(f"Install state: {payload.get('install_state', UNKNOWN)}\n")
    sys.stdout.write(f"Installed version: {payload.get('installed_version') or 'unknown'}\n")
    sys.stdout.write(f"Latest version: {payload.get('latest_version') or 'unavailable'}\n")
    sys.stdout.write(f"Action: {payload.get('action', 'unknown')}\n")

    backup_path = payload.get("backup_path")
    if backup_path:
        sys.stdout.write(f"Backup path: {backup_path}\n")

    sys.stdout.write("\nRequired surfaces:\n")
    by_kind = payload.get("required_surfaces", {}).get("by_kind", {})
    for kind in ("commands", "skills", "manifests"):
        info = by_kind.get(kind, {"present": [], "missing": []})
        present = info.get("present", [])
        missing = info.get("missing", [])
        missing_label = ", ".join(missing) if missing else "none"
        sys.stdout.write(f"  {kind}: {len(present)} present; missing: {missing_label}\n")

    legacy_dirs = payload.get("legacy_standalone_dirs") or []
    if legacy_dirs:
        sys.stdout.write("\nLegacy standalone dirs:\n")
        for path in legacy_dirs:
            sys.stdout.write(f"  - {path}\n")

    archived = payload.get("archived_legacy_dirs") or []
    if archived:
        sys.stdout.write("\nArchived legacy dirs:\n")
        for path in archived:
            sys.stdout.write(f"  - {path}\n")

    failed = payload.get("archive_failed_dirs") or []
    if failed:
        sys.stdout.write("\nArchive failures:\n")
        for item in failed:
            if isinstance(item, dict):
                sys.stdout.write(f"  - {item.get('path', '')}: {item.get('error', '')}\n")
            else:
                sys.stdout.write(f"  - {item}\n")

    commands = payload.get("commands")
    if isinstance(commands, list) and commands:
        sys.stdout.write("\nCommands:\n")
        for item in commands:
            if isinstance(item, dict):
                sys.stdout.write(f"  - {item.get('command', '')} -> exit {item.get('returncode', '')}\n")
            else:
                sys.stdout.write(f"  - {item}\n")

    error = payload.get("error")
    if error:
        sys.stdout.write(f"\nError: {error}\n")

    next_steps = payload.get("next_steps")
    if isinstance(next_steps, list) and next_steps:
        sys.stdout.write("\nNext steps:\n")
        for item in next_steps:
            sys.stdout.write(f"  - {item}\n")


def print_update_notice(payload: dict[str, Any], output_mode: str = "text") -> None:
    message = f"""Karpathy plugin update available: {payload.get('installed_version') or 'unknown'} -> {payload.get('latest_version') or 'unknown'}

Run `/karpathy:update` to install it.
If slash commands are unavailable, type `karpathy update` as normal text.

Set KARPATHY_DISABLE_UPDATE_CHECK=1 to disable this reminder.
"""
    emit_hook_message(message, output_mode)


def print_repair_notice(payload: dict[str, Any], output_mode: str = "text") -> None:
    missing = ", ".join(payload["required_surfaces"]["missing"])
    message = f"""Karpathy plugin install needs repair.

Missing required surfaces: {missing}

Run `/karpathy:update` to repair it.
If slash commands are unavailable, type `karpathy update` as normal text.

Set KARPATHY_DISABLE_UPDATE_CHECK=1 to disable this reminder.
"""
    emit_hook_message(message, output_mode)


def emit_hook_message(message: str, output_mode: str) -> None:
    if output_mode == "system-message":
        json.dump({"systemMessage": message.strip()}, sys.stdout)
        sys.stdout.write("\n")
        return
    sys.stdout.write(message)


def print_usage() -> None:
    sys.stdout.write(
        """karpathy update helper

Usage:
  check_update.py                 Hook mode: bounded local surface check
  check_update.py --system-message
  check_update.py --check [--json]
  check_update.py --update [--json]

Environment:
  KARPATHY_DISABLE_UPDATE_CHECK=1 disables hook reminders.
  KARPATHY_UPDATE_DRY_RUN=1 prints the Codex update commands without running them.
  KARPATHY_UPDATE_COMMAND_TIMEOUT_SECONDS overrides the Codex command timeout.
  KARPATHY_CODEX_HOME overrides the Codex home path for tests.
  KARPATHY_CLAUDE_HOME overrides the Claude home path for tests.
"""
    )


if __name__ == "__main__":
    raise SystemExit(main())
